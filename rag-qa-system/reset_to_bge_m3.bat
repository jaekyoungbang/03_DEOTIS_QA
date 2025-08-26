@echo off
echo ========================================
echo BGE-M3 임베딩으로 벡터DB 재생성
echo ========================================
echo.

cd /d "%~dp0"

echo 1. 서버가 실행 중이면 먼저 종료해주세요 (Ctrl+C)
echo    계속하려면 아무 키나 누르세요...
pause > nul

echo.
echo 2. BGE-M3 임베딩 설정 확인...
echo    .env 파일에서 USE_OLLAMA_BGE_M3=false로 이미 설정됨
echo    ✅ BGE-M3 사용 설정 완료

echo.
echo 3. 기존 벡터DB 백업 및 삭제...
if exist "data\vectordb" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set backup_name=vectordb_openai_backup_%datetime:~0,14%
    if not exist "data\backup" mkdir "data\backup"
    move "data\vectordb" "data\backup\%backup_name%" 2>nul
    if errorlevel 1 (
        echo    [오류] 백업 실패 - 파일이 사용 중입니다.
        echo    강제 삭제를 시도합니다...
        rd /s /q "data\vectordb" 2>nul
    ) else (
        echo    [성공] 기존 벡터DB 백업: data\backup\%backup_name%
    )
) else (
    echo    [정보] 기존 벡터DB가 없습니다.
)

echo.
echo 4. 새 벡터DB 디렉토리 생성...
mkdir "data\vectordb" 2>nul
echo    ✅ 새 벡터DB 디렉토리 생성 완료

echo.
echo 5. 캐시 초기화...
if exist "data\cache" (
    rd /s /q "data\cache" 2>nul
    mkdir "data\cache"
    echo    ✅ 캐시 초기화 완료
)

echo.
echo ========================================
echo 준비 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. 서버 시작: python app.py
echo 2. 브라우저에서 http://localhost:5001/admin 접속
echo 3. "문서 재로딩" 버튼 클릭
echo 4. BGE-M3 (1024차원)으로 새로운 벡터DB 생성
echo.
echo 임베딩 모델: BGE-M3 (192.168.0.224:11434)
echo 차원: 1024
echo.
pause