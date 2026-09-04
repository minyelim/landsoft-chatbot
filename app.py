"""
랜드소프트 질문 챗봇
------------------------------------------------------
회사 규정(회사규정_2024_12.pdf)과 신규입사자 온보딩 가이드(pptx)를
근거로 질문에 답하는 사내 규정 챗봇입니다.

실행 방법: streamlit run app.py
(자세한 설치/실행 방법은 README.md 참고)
"""

import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai

# ------------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------------
APP_TITLE = "🏢 랜드소프트 질문 챗봇"
KB_DIR = Path(__file__).parent / "knowledge_base"
MODEL_CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]  # 앞 모델이 혼잡하면 자동으로 다음 모델로 넘어갑니다.

load_dotenv()  # .env 파일에 GEMINI_API_KEY 가 있으면 자동으로 불러옵니다.

st.set_page_config(page_title=APP_TITLE, page_icon="🏢", layout="centered")


def get_secret(name: str) -> str:
    """Streamlit Cloud의 secrets, 없으면 환경변수(.env) 순서로 값을 찾습니다."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, "")


# 배포 환경(Streamlit Cloud secrets)에 APP_PASSWORD가 설정되어 있으면
# 비밀번호를 입력해야만 챗봇을 사용할 수 있도록 합니다. (사내 전용 배포 시 사용)
APP_PASSWORD = get_secret("APP_PASSWORD")
if APP_PASSWORD:
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if not st.session_state.authed:
        st.title(APP_TITLE)
        pw = st.text_input("접속 비밀번호를 입력하세요", type="password")
        if st.button("입장"):
            if pw == APP_PASSWORD:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()


# ------------------------------------------------------------------
# 지식베이스(회사 규정 + 온보딩 가이드) 불러오기
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_knowledge_base() -> str:
    """knowledge_base 폴더 안의 모든 .txt 파일을 하나의 문자열로 합칩니다."""
    parts = []
    for path in sorted(KB_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        parts.append(f"\n\n########## 문서: {path.stem} ##########\n{text}")
    return "".join(parts)


KNOWLEDGE_BASE = load_knowledge_base()

SYSTEM_PROMPT = f"""당신은 '랜드소프트 주식회사'의 사내 규정 안내 챗봇 '랜드소프트 질문 챗봇'입니다.

아래 <문서> 안에는 두 종류의 자료가 들어 있습니다.
1) 01_회사규정 : 여비규정, 연장근로규정, 재택근무규정, 전월세보증금 지원규정,
   사외교육훈련비 지원규정, PC지급 및 관리규정, 전결규정, 경조휴가 및 경조금 지급규정,
   근태관리규정, 휴가사용규정
2) 02_온보딩가이드 : 신규입사자 온보딩 가이드(회사 소개, 근무제도, 복리후생, 하이웍스 사용법 등)

<문서>
{KNOWLEDGE_BASE}
</문서>

답변 규칙:
- 반드시 위 <문서> 안에 있는 내용만 근거로 답변하세요. 문서에 없는 내용을 추측하거나 지어내지 마세요.
- 문서에서 답을 찾을 수 없으면 "제공된 자료에서는 확인할 수 없습니다. 경영관리팀에 문의해 주세요."라고 답하세요.
- 가능하면 답변 끝에 근거가 된 문서와 항목(예: "[출처: 회사규정 Ⅱ. 연장근로규정]" 또는
  "[출처: 온보딩가이드 APPENDIX 4 재택근무제도]")을 함께 표시하세요.
- 표(금액, 기간, 한도 등 숫자)를 물어보면 표의 값을 정확히 인용하세요.
- 문서 내에 "최신 사내공지·취업규칙을 우선 확인하라"는 단서가 있는 항목은, 답변 뒤에
  그 내용이 변경되었을 수 있으니 최신 사내공지를 확인하라고 안내하세요.
- 항상 정중한 존댓말로, 간결하고 명확하게 답변하세요.
"""


# ------------------------------------------------------------------
# 사이드바: API 키 입력
# ------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    default_key = get_secret("GEMINI_API_KEY")
    if default_key:
        # 배포 환경에 키가 이미 설정되어 있으면 사용자가 직접 입력할 필요가 없습니다.
        api_key = default_key
        st.success("✅ API 키가 설정되어 있습니다.")
    else:
        api_key = st.text_input(
            "Gemini API Key",
            value="",
            type="password",
            help="https://aistudio.google.com/apikey 에서 무료로 발급받을 수 있습니다.",
        )
        st.caption(
            "API 키는 서버에 저장되지 않고 이번 대화(브라우저 세션)에서만 사용됩니다."
        )
    st.divider()
    st.markdown("**참고 자료**")
    for path in sorted(KB_DIR.glob("*.txt")):
        st.markdown(f"- {path.stem}")
    st.divider()
    if st.button("🗑️ 대화 초기화"):
        st.session_state.pop("messages", None)
        st.session_state.pop("chat_session", None)
        st.session_state.pop("chat_history", None)
        st.session_state.pop("model_index", None)
        st.rerun()


st.title(APP_TITLE)
st.caption("회사규정과 신규입사자 온보딩 가이드를 기반으로 질문에 답변합니다.")

if not api_key:
    st.info(
        "먼저 왼쪽 사이드바에 **Gemini API Key**를 입력해주세요.\n\n"
        "키가 없다면 https://aistudio.google.com/apikey 에서 무료로 발급받을 수 있습니다."
    )
    st.stop()


# ------------------------------------------------------------------
# Gemini 클라이언트 및 대화 세션 준비
# ------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_client(key: str) -> genai.Client:
    return genai.Client(api_key=key)


try:
    client = get_client(api_key)
except Exception as e:
    st.error(f"Gemini 클라이언트 생성에 실패했습니다: {e}")
    st.stop()

if "chat_history" not in st.session_state:
    # (role, text) 튜플로 대화 내역을 직접 보관 -> 필요시 다른 모델로 그대로 재생(replay) 가능
    st.session_state.chat_history = []

if "model_index" not in st.session_state:
    st.session_state.model_index = 0

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 랜드소프트 사내 규정과 온보딩 가이드에 대해 무엇이든 물어보세요. 😊\n"
            "예) '연장근로 시 식대는 얼마까지 지원되나요?', '재택근무는 누가 신청할 수 있나요?'",
        }
    ]


def build_chat(model_name: str):
    """지정된 모델로 새 대화 세션을 만들고, 지금까지의 대화 내역을 그대로 재생해줍니다."""
    chat = client.chats.create(
        model=model_name,
        config={"system_instruction": SYSTEM_PROMPT},
    )
    for role, text in st.session_state.chat_history:
        if role == "user":
            chat.send_message(text)
    return chat


def is_retryable(err: Exception) -> bool:
    msg = str(err)
    return any(code in msg for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"])


def ask(question: str):
    """현재 모델로 질문을 시도하고, 계속 실패하면 다음 후보 모델로 자동 전환합니다."""
    last_error = None
    while st.session_state.model_index < len(MODEL_CANDIDATES):
        model_name = MODEL_CANDIDATES[st.session_state.model_index]
        if "chat_session" not in st.session_state:
            st.session_state.chat_session = build_chat(model_name)

        delay = 1.5
        for attempt in range(3):  # 같은 모델로 최대 3번 재시도
            try:
                response = st.session_state.chat_session.send_message(question)
                return response.text
            except Exception as e:
                last_error = e
                if is_retryable(e) and attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break

        # 이 모델로는 계속 안 되니, 다음 모델로 넘어가서 새로 시도
        st.session_state.model_index += 1
        st.session_state.pop("chat_session", None)

    raise last_error


# ------------------------------------------------------------------
# 채팅 UI
# ------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("규정에 대해 궁금한 점을 입력하세요...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.chat_history.append(("user", question))
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        current_model = MODEL_CANDIDATES[min(st.session_state.model_index, len(MODEL_CANDIDATES) - 1)]
        placeholder.markdown(f"답변을 생성하는 중입니다... _(모델: {current_model})_")
        try:
            answer = ask(question)
        except Exception as e:
            msg = str(e)
            if is_retryable(e):
                answer = (
                    "😥 지금 Gemini 서버 전체가 일시적으로 혼잡해서 답변을 받아오지 못했습니다.\n\n"
                    "잠시(1~2분) 후 같은 질문을 다시 보내주세요."
                )
            else:
                answer = f"죄송합니다, 답변 생성 중 오류가 발생했습니다: {e}"
        placeholder.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.chat_history.append(("assistant", answer))
