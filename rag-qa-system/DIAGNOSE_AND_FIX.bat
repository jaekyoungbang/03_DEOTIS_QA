@echo off
echo ========================================
echo 시스템 진단 및 문제 해결
echo ========================================

cd /d D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system

echo.
echo 1. 현재 Python 버전 확인:
python --version

echo.
echo 2. 가상환경 활성화:
call venv_windows\Scripts\activate

echo.
echo 3. 활성화 후 Python 경로:
where python

echo.
echo 4. 현재 설치된 패키지 목록:
pip list | findstr docx

echo.
echo 5. docx2txt 강제 설치:
pip install --force-reinstall docx2txt==0.8

echo.
echo 6. 설치 확인:
python -c "import docx2txt; print('docx2txt 설치 성공!')"

echo.
echo 7. langchain_community 확인:
python -c "from langchain_community.document_loaders import Docx2txtLoader; print('Docx2txtLoader 가져오기 성공!')"

echo.
echo ========================================
echo 진단 완료! 위 결과를 확인하세요.
echo ========================================
pause