#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[1/3] 가상환경을 생성합니다..."
    python3 -m venv venv
fi

echo "[2/3] 필요한 패키지를 설치합니다..."
source venv/bin/activate
pip install -r requirements.txt -q

echo "[3/3] 챗봇을 실행합니다. 잠시 후 브라우저가 자동으로 열립니다..."
streamlit run app.py
