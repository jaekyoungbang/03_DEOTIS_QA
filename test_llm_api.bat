@echo off
chcp 65001 > nul
echo === LLM API 테스트 ===

echo.
echo 1. 서버 상태 확인...
curl -s -w "상태코드: %%{http_code}\n" http://192.168.0.224:8412/health

echo.
echo 2. 사용 가능한 모델 목록...
curl -s http://192.168.0.224:8412/v1/models

echo.
echo 3. Chat Completions 테스트 (kanana8b)...
curl -X POST http://192.168.0.224:8412/v1/chat/completions ^
-H "Content-Type: application/json" ^
-d "{\"model\": \"./models/kanana8b\", \"messages\": [{\"role\": \"user\", \"content\": \"안녕!\"}], \"max_tokens\": 50}"

echo.
echo.
echo 4. Chat Completions 테스트 (EEVE-Korean)...
curl -X POST http://192.168.0.224:8412/v1/chat/completions ^
-H "Content-Type: application/json" ^
-d "{\"model\": \"yanolja/EEVE-Korean-Instruct-10.8B-v1.0\", \"messages\": [{\"role\": \"user\", \"content\": \"안녕하세요!\"}], \"max_tokens\": 50}"

echo.
echo === 테스트 완료 ===
pause