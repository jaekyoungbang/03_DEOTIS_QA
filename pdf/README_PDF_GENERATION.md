# 📄 PDF 생성 가이드

## 🎯 생성된 파일들

다음 파일들이 `D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\pdf\` 폴더에 생성되었습니다:

1. **RAG_QA_SYSTEM_DOCUMENTATION.md** - 전체 시스템 문서
2. **LINUX_INSTALLATION_GUIDE.md** - 기본 Linux 설치 가이드  
3. **YANOLJA_LLM_INSTALLATION_GUIDE.md** - 야놀자 LLM 특화 설치 가이드
4. **generate_pdf.html** - PDF 변환용 통합 HTML 파일
5. **README_PDF_GENERATION.md** - 이 파일

## 🖨 PDF 생성 방법

### 방법 1: HTML 파일을 통한 PDF 생성 (권장)

1. **`generate_pdf.html` 파일을 브라우저에서 열기**
   - 파일 탐색기에서 `generate_pdf.html` 더블클릭
   - 또는 브라우저 주소창에 `file:///D:/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/pdf/generate_pdf.html` 입력

2. **PDF로 저장**
   - 브라우저에서 `Ctrl + P` (인쇄)
   - 대상을 "PDF로 저장" 선택
   - 파일명: `야놀자_RAG_시스템_통합문서.pdf`
   - 저장

### 방법 2: 온라인 변환 도구 사용

**추천 사이트:**
- https://markdown-pdf.com/
- https://www.markdowntopdf.com/
- https://dillinger.io/ (Markdown 편집 + PDF 내보내기)

**사용방법:**
1. 위 사이트 중 하나 접속
2. MD 파일 내용 복사 → 붙여넣기
3. PDF 다운로드

### 방법 3: VS Code 확장 사용

1. **VS Code에서 확장 설치**
   - "Markdown PDF" 확장 설치
   - "Markdown All in One" 확장 설치 (선택사항)

2. **PDF 변환**
   - MD 파일을 VS Code로 열기
   - `Ctrl + Shift + P` → "Markdown PDF: Export (pdf)" 선택
   - 자동으로 PDF 생성

### 방법 4: Pandoc 사용 (고급)

```bash
# Pandoc 설치 후
pandoc YANOLJA_LLM_INSTALLATION_GUIDE.md -o 야놀자LLM설치가이드.pdf --pdf-engine=wkhtmltopdf

# 또는 모든 파일 통합
pandoc RAG_QA_SYSTEM_DOCUMENTATION.md YANOLJA_LLM_INSTALLATION_GUIDE.md -o 야놀자_통합문서.pdf
```

## 📋 추천 PDF 파일명

- `야놀자_RAG_시스템_개요.pdf` (RAG_QA_SYSTEM_DOCUMENTATION.md)
- `야놀자_LLM_설치가이드.pdf` (YANOLJA_LLM_INSTALLATION_GUIDE.md)  
- `야놀자_RAG_통합문서.pdf` (generate_pdf.html)

## 🎨 PDF 최적화 팁

### Chrome/Edge 브라우저 PDF 설정:
- **용지 크기**: A4
- **여백**: 최소
- **배경 그래픽**: 체크
- **머리글/바닥글**: 해제
- **축척**: 100% (또는 맞춤)

### 문서 품질 향상:
- 목차와 페이지 번호 포함
- 코드 블록 구문 강조
- 표와 다이어그램 선명도 유지
- 한글 폰트 최적화

## ✅ 최종 체크리스트

- [ ] HTML 파일이 브라우저에서 정상 표시
- [ ] PDF 인쇄 미리보기에서 레이아웃 확인
- [ ] 한글 폰트가 제대로 표시
- [ ] 코드 블록이 읽기 쉬움
- [ ] 페이지 분할이 자연스러움
- [ ] 파일 크기가 적당함 (10MB 이하)

---

**📧 문의사항**
PDF 생성에 문제가 있으면 야놀자 AI팀으로 연락주세요.

**생성일**: 2024년 12월 19일
**버전**: 1.0