@echo off
echo ========================================
echo DOCX2TXT 모듈 긴급 설치
echo ========================================

cd /d D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system

echo 가상환경 활성화 중...
call venv_windows\Scripts\activate

echo docx2txt 설치 중...
pip install docx2txt==0.8

echo.
echo ========================================
echo 설치 완료! 서버를 재시작하세요.
echo ========================================
echo.
echo 서버 재시작 명령:
echo python app.py
echo.
pause