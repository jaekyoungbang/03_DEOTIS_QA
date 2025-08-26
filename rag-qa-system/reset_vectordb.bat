@echo off
echo ========================================
echo 벡터 데이터베이스 초기화 스크립트
echo ========================================
echo.

REM 현재 디렉토리 저장
set CURRENT_DIR=%CD%

REM 스크립트 디렉토리로 이동
cd /d "%~dp0"

echo 1. 서버가 실행 중이면 먼저 종료해주세요 (Ctrl+C)
echo    계속하려면 아무 키나 누르세요...
pause > nul

echo.
echo 2. 기존 벡터DB 백업 중...
if exist "data\vectordb" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set backup_name=vectordb_backup_%datetime:~0,14%
    move "data\vectordb" "data\%backup_name%" 2>nul
    if errorlevel 1 (
        echo    [오류] 백업 실패 - 파일이 사용 중입니다.
        echo    서버를 종료하고 다시 시도해주세요.
        goto :end
    )
    echo    [성공] 백업 완료: data\%backup_name%
) else (
    echo    [정보] 기존 벡터DB가 없습니다.
)

echo.
echo 3. 새 벡터DB 디렉토리 생성...
mkdir "data\vectordb" 2>nul
echo    [성공] 디렉토리 생성 완료

echo.
echo 4. 환경 변수 설정...
set USE_OLLAMA_BGE_M3=true
echo    [성공] BGE-M3 임베딩 모델 설정

echo.
echo ========================================
echo 초기화 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. 서버 재시작: python app.py
echo 2. 웹 브라우저에서 http://localhost:5000/admin 접속
echo 3. "문서 재로딩" 버튼 클릭
echo.
echo 또는 직접 실행: python load_documents_new.py
echo.

:end
cd /d "%CURRENT_DIR%"
pause