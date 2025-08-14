# DOCX 문서 로딩 오류 해결 가이드

## 문제 상황
```
❌ 오류 발생: Error loading document: No module named 'docx2txt'
- 처리된 문서: 0개
- 생성된 청크: 0개
- 전체 벡터 DB 문서 수: 0개
```

## 원인
- `langchain_community.document_loaders.Docx2txtLoader`가 `docx2txt` 패키지를 필요로 함
- `requirements.txt`에 `docx2txt` 패키지가 누락됨

## 해결 방법

### 1. 즉시 해결 (Windows)
```cmd
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system
call venv_windows\Scripts\activate
pip install docx2txt==0.8
```

### 2. 배치 파일 실행
```cmd
install_docx2txt.bat
```

### 3. Linux/WSL
```bash
cd /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system
source venv_new/bin/activate
pip install docx2txt==0.8
```

### 4. 전체 requirements 재설치
```cmd
pip install -r requirements.txt
```

## 설치 후 확인

### 1. 서버 재시작
```cmd
python app.py
```

### 2. 문서 로딩 테스트
브라우저에서 문서 로딩 버튼 클릭하여 확인

### 3. 예상 결과
```
📄 처리 중: BC카드(신용카드 업무처리 안내).docx
✅ 문서 로드 완료: BC카드(신용카드 업무처리 안내).docx

📄 처리 중: BC카드(카드이용안내).docx  
✅ 문서 로드 완료: BC카드(카드이용안내).docx

📊 로딩 완료!
- 처리된 문서: 2개
- 생성된 청크: XX개
- 전체 벡터 DB 문서 수: XX개
```

## 추가 정보
- `requirements.txt`에 `docx2txt==0.8` 추가됨
- DOCX 파일 처리를 위한 필수 패키지
- 설치 후 즉시 문서 로딩 가능