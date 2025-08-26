@echo off
echo ========================================
echo 임베딩 차원 불일치 해결
echo ========================================
echo.

cd /d "%~dp0"

echo 1. OpenAI 임베딩으로 전환...
echo USE_OLLAMA_BGE_M3=false > .env

echo.
echo ✅ 완료! 
echo.
echo 다음 단계:
echo 1. 서버 종료 (Ctrl+C)
echo 2. 서버 재시작: python app.py
echo.
pause