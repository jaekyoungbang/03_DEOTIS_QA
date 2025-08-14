@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ✅ 1) 한글 깨짐 방지: UTF-8 코드페이지로 전환 (콘솔 폰트는 Consolas 권장)
chcp 65001 >nul

REM === 사용자 설정 ===
set "PORTS=5000"
REM ===================

REM ✅ 2) 관리자 권한 자동 승격
net session >nul 2>&1
if %errorlevel% NEQ 0 (
  echo 관리자 권한으로 재시작합니다...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo ==============================
echo [0] WSL IP 조회
echo ==============================
for /f "tokens=1" %%i in ('wsl hostname -I') do (set "WSL_IP=%%i")
if not defined WSL_IP (
  echo ❌ WSL IP를 가져오지 못했습니다. WSL이 실행 중인지 확인하세요.
  goto :KEEP
)
echo ▶ 현재 WSL IP: %WSL_IP%
echo.

echo ==============================
echo [1] IP Helper 서비스 확인/시작
echo ==============================
sc query iphlpsvc | findstr /I "RUNNING" >nul
if errorlevel 1 (
  echo ▶ IP Helper 서비스 시작 중...
  sc start iphlpsvc >nul
  timeout /t 1 >nul
) else (
  echo ▶ IP Helper 이미 실행 중
)
echo.

echo ==============================
echo [2] PortProxy 재설정
echo ==============================
for %%P in (%PORTS%) do (
  echo  - 포트 %%P 기존 설정 제거 시도...
  netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=%%P >nul 2>&1
)
for %%P in (%PORTS%) do (
  echo  - 포트 %%P 새로 등록: 0.0.0.0:%%P -> %WSL_IP%:%%P
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=%%P connectaddress=%WSL_IP% connectport=%%P
)
echo.
echo 현재 PortProxy 테이블:
netsh interface portproxy show all
echo.

echo ==============================
echo [3] 방화벽 인바운드 규칙(없으면 생성)
echo ==============================
for %%P in (%PORTS%) do (
  netsh advfirewall firewall show rule name="WSL-%%P" >nul 2>&1
  if errorlevel 1 (
    echo  - 규칙 생성: WSL-%%P (TCP/%%P)
    netsh advfirewall firewall add rule name="WSL-%%P" dir=in action=allow p
