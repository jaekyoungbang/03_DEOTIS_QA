#!/bin/bash

echo "🚀 Ollama 원격 서버로 RAG 시스템 시작"
echo "=================================="
echo "서버: 192.168.0.224:11434"
echo "LLM: Yanolja EEVE Korean 10.8B"
echo "임베딩: BGE-M3"
echo "=================================="

# 환경변수 설정
export OLLAMA_BASE_URL=http://192.168.0.224:11434
export USE_OLLAMA_BGE_M3=true
export DEFAULT_LLM_MODEL=yanolja

# .env 파일 백업 및 ollama 설정 적용
if [ -f .env ]; then
    cp .env .env.backup
    echo "✅ 기존 .env 백업 완료 (.env.backup)"
fi

# .env.ollama 내용을 .env에 추가
if [ -f .env.ollama ]; then
    cat .env.ollama >> .env
    echo "✅ Ollama 설정 적용됨"
fi

# 서버 시작
echo "🌐 Flask 서버 시작..."
python app.py