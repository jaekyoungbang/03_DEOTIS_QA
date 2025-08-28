# 🧪 RAG QA 시스템 실행 및 테스트 가이드

## 🚀 빠른 실행 (5분 안에 확인)

### 1단계: 환경 준비
```bash
cd /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system

# 환경 변수 설정 (최소한)
cat > .env.test << 'EOF'
FLASK_ENV=development
OPENAI_API_KEY=your-key-here
PYTHONPATH=/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system
EOF

# 권한 설정
chmod +x scripts/*.sh
```

### 2단계: 의존성 설치 (WSL/Linux)
```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 핵심 라이브러리만 설치
pip install flask langchain openai chromadb sentence-transformers python-docx PyPDF2 markdown requests python-dotenv pydantic psutil sqlite3
```

### 3단계: 테스트 문서 준비
```bash
# 테스트 문서 생성
mkdir -p s3 s3-chunking s3-common data logs

# BC카드 샘플 문서 생성
cat > s3/bc_card_guide.txt << 'EOF'
BC카드 발급 안내

1. 발급 대상
- 만 19세 이상 국내 거주자
- 정기소득이 있는 개인

2. 신청 방법
- 온라인: BC카드 홈페이지
- 오프라인: 회원은행 영업점 방문
- 전화: 고객센터 1588-4000

3. 필요 서류
- 신분증 (주민등록증, 운전면허증)
- 소득증명서류
- 재직증명서

4. 심사 기준
- 신용등급 4등급 이상
- 연소득 2천만원 이상
- 기존 연체 이력 없음

5. 발급 절차
STEP 1: 온라인/오프라인 신청
STEP 2: 서류 제출 및 확인
STEP 3: 신용 심사 (1-3일)
STEP 4: 승인 시 카드 제작 및 발송 (3-5일)

6. 고객센터
- 전화: 1588-4000 (24시간)
- 홈페이지: www.bccard.com
EOF

cat > s3-chunking/kim_myeongjung_info.md << 'EOF'
# 김명정 고객 개인화 정보

## 현재 보유카드
- ✅ 우리카드 (2019년 발급)
- ✅ 하나카드 (2021년 발급) 
- ✅ NH농협카드 (2022년 발급)

## 발급 가능 카드
### 미보유 회원은행 카드
- 🆕 KB국민카드 (높은 승인률 예상)
- 🆕 신한카드 (우수 신용등급)
- 🆕 IBK기업은행카드
- 🆕 DGB대구은행카드
- 🆕 BNK부산은행카드
- 🆕 BNK경남은행카드
- 🆕 citi카드
- 🆕 BC바로카드

## 개인 신용정보
- 신용등급: 1등급 (우수)
- 연소득: 5,500만원
- 직장: 삼성전자 (정규직)
- 거주지: 서울시 강남구

## 추천 카드
1. **KB국민카드**: 급여이체 시 연회비 면제
2. **신한카드**: 온라인쇼핑 5% 적립
3. **BC바로카드**: 교통비 10% 할인

![KB국민카드](/images/kb_card.gif)
![신한카드](/images/shinhan_card.gif)
![BC바로카드](/images/bc_direct_card.gif)
EOF

echo "📚 테스트 문서 생성 완료"
```

## 🔧 시스템 실행

### A. 단순 실행 (기본 기능만)
```bash
# 기본 앱 실행
source venv/bin/activate
export PYTHONPATH=/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system
python app.py
```

### B. 성능 최적화 포함 실행
```bash
# 문서 로딩 먼저
python load_documents.py

# 최적화된 앱 실행  
python app.py
```

## 🧪 기능별 테스트 방법

### 1. 웹 인터페이스 테스트
**브라우저에서 접속:**
- http://localhost:5001/deotisrag

**테스트할 질문들:**
```
1. "BC카드 발급 절차 알려주세요"
2. "김명정 고객님의 보유카드는 무엇인가요?"  
3. "고객센터 연락처 알려주세요"
4. "카드 발급에 필요한 서류는?"
```

### 2. API 직접 테스트
```bash
# 기본 쿼리 테스트
curl -X POST http://localhost:5001/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "BC카드 발급 절차를 알려주세요",
    "llm_model": "gpt-4o-mini",
    "search_mode": "basic"
  }'

# 개인화 쿼리 테스트  
curl -X POST http://localhost:5001/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "김명정님의 현재 보유카드와 추천카드를 알려주세요",
    "llm_model": "gpt-4o-mini",
    "search_mode": "advanced"
  }'
```

### 3. 성능 최적화 확인
```bash
# SmartQueryRouter 테스트
python -c "
from services.performance_optimizer import query_router

# 다양한 쿼리 분류 테스트
test_queries = [
    'BC카드 고객센터 연락처',  # cached
    '안녕하세요',              # simple  
    '김명정님의 카드발급 절차를 자세히 설명해주세요',  # complex
    '카드발급 안내'            # standard
]

for query in test_queries:
    classification = query_router.classify_query(query)
    print(f'질문: {query}')
    print(f'분류: {classification}')
    print('-' * 40)
"
```

### 4. 고급 검색 엔진 테스트
```bash
# 고급 검색 테스트
python -c "
import sys
sys.path.append('/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system')

from services.advanced_search_engine import AdvancedSearchEngine
from langchain.schema import Document

# 샘플 문서
docs = [
    Document(page_content='BC카드 발급 절차: 1단계 신청서 작성, 2단계 서류 준비', metadata={'source': 'guide'}),
    Document(page_content='김명정 고객님의 보유카드: 우리카드, 하나카드, NH농협카드', metadata={'source': 'personal'}),
    Document(page_content='고객센터 연락처: 1588-4000, 24시간 상담 가능', metadata={'source': 'contact'})
]

engine = AdvancedSearchEngine()
engine.initialize_with_documents(docs)

# 검색 테스트
query = '김명정 고객의 카드발급 안내'
results, explanation = engine.search_with_explanation(query, docs, top_k=3)

print('=== 고급 검색 결과 ===')
for result in results:
    print(f'순위 {result.final_rank}: 점수 {result.relevance_score:.3f}')
    print(f'키워드: {result.matched_keywords}')
    print(f'내용: {result.document.page_content[:100]}...')
    print('-' * 50)

print('\\n=== 검색 설명 ===')
print(f'검색된 문서 수: {explanation[\"total_documents_searched\"]}')
print(f'쿼리 분석: {explanation[\"query_analysis\"]}')
"
```

### 5. 상업화 기능 테스트
```bash
# 사용자 계정 생성 및 API 키 테스트
python -c "
from services.commercial_features import commercial_system

# 테스트 사용자 생성
user = commercial_system.user_db.create_user('testuser', 'test@example.com', 'basic')
print(f'생성된 사용자: {user.username}')
print(f'API 키: {user.api_key}')
print(f'사용 제한: {user.usage_limits}')

# API 인증 테스트
auth_user = commercial_system.authenticate_request(user.api_key)
print(f'인증 결과: {auth_user.username if auth_user else \"실패\"}')

# 사용량 추적 테스트
from services.commercial_features import UsageType
success = commercial_system.usage_tracker.record_usage(
    user.user_id, UsageType.QUERY, 1, {'test': 'query'}
)
print(f'사용량 기록: {success}')

# 대시보드 데이터
dashboard = commercial_system.generate_user_dashboard(user.user_id)
print(f'이번 달 사용량: {dashboard[\"usage_summary\"][\"total_cost\"]}')
"
```

### 6. 보안 모니터링 테스트
```bash
# 보안 분석 테스트
python -c "
from services.security_monitoring import monitoring_system

# 정상 요청 테스트
is_allowed, reason = monitoring_system.analyze_request_security(
    '192.168.1.100', 'Mozilla/5.0', '/api/query', 
    {'question': 'BC카드 안내'}, 'basic'
)
print(f'정상 요청: 허용={is_allowed}, 사유={reason}')

# 악성 요청 테스트  
is_allowed, reason = monitoring_system.analyze_request_security(
    '10.0.0.1', 'sqlmap/1.0', '/api/query',
    {'question': \"'; DROP TABLE users; --\"}, 'free'
)
print(f'악성 요청: 허용={is_allowed}, 사유={reason}')

# 보안 대시보드
dashboard = monitoring_system.get_security_dashboard(1)
print(f'보안 이벤트: {dashboard[\"total_events\"]}개')
"
```

## 📊 실시간 모니터링 확인

### 시스템 상태 실시간 확인
```bash
# 터미널 1: 메인 앱 실행
python app.py

# 터미널 2: 시스템 모니터링
watch -n 2 'echo "=== 시스템 상태 ===" && python -c "
import psutil
print(f\"CPU: {psutil.cpu_percent()}%\")
print(f\"메모리: {psutil.virtual_memory().percent}%\")
print(f\"디스크: {psutil.disk_usage(\"/\").percent}%\")
"'

# 터미널 3: 로그 실시간 확인  
tail -f app.log
```

### 성능 테스트
```bash
# 동시 요청 부하 테스트 (Apache Bench)
ab -n 100 -c 10 -T 'application/json' -p test_query.json http://localhost:5001/api/chat/query

# test_query.json 파일:
echo '{"question":"BC카드 발급 절차","llm_model":"gpt-4o-mini"}' > test_query.json
```

## 🎯 확인 포인트 체크리스트

### ✅ 기본 기능
- [ ] 웹 페이지 정상 로딩 (http://localhost:5001/deotisrag)
- [ ] 기본 질문 응답 작동
- [ ] 문서 검색 기능 작동
- [ ] 이미지 표시 기능

### ✅ 성능 최적화
- [ ] 캐시된 응답 0.1초 이내
- [ ] 일반 응답 2초 이내  
- [ ] 메모리 사용량 적정 수준
- [ ] 쿼리 분류 정확도

### ✅ 고급 기능
- [ ] 개인화 응답 (김명정님 질문)
- [ ] 의미적 검색 정확도
- [ ] 다중 모델 앙상블 작동
- [ ] 실시간 학습 시스템

### ✅ 상업화 기능
- [ ] 사용자 계정 생성/관리
- [ ] API 키 인증 시스템
- [ ] 사용량 추적 및 과금
- [ ] 관리자 대시보드

### ✅ 보안 및 모니터링
- [ ] 악성 요청 탐지/차단
- [ ] 성능 메트릭 수집
- [ ] 알림 시스템 작동
- [ ] 로그 기록 및 분석

## 🚨 문제 해결

### 자주 발생하는 문제들
1. **ModuleNotFoundError**: `pip install -r requirements.txt`
2. **OpenAI API 에러**: API 키 확인 및 설정
3. **포트 충돌**: 다른 포트 사용 (5002, 5003 등)
4. **메모리 부족**: 가상환경 메모리 할당량 증가

### 디버그 모드
```bash
# 상세 로그와 함께 실행
FLASK_ENV=development python app.py --debug
```

이제 실제로 실행해서 모든 기능을 확인할 수 있습니다! 🚀