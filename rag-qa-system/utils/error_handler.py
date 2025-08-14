"""
Error handling and user-friendly error messages
"""

class ErrorCodes:
    # Vector Database Errors (VDB)
    VDB_NO_COLLECTION = "VDB001"
    VDB_EMPTY = "VDB002"
    VDB_CONNECTION_ERROR = "VDB003"
    
    # Document Processing Errors (DOC)
    DOC_NOT_FOUND = "DOC001"
    DOC_INVALID_FORMAT = "DOC002"
    DOC_SIZE_TOO_LARGE = "DOC003"
    DOC_PROCESSING_ERROR = "DOC004"
    
    # LLM Errors (LLM)
    LLM_API_KEY_MISSING = "LLM001"
    LLM_API_ERROR = "LLM002"
    LLM_TIMEOUT = "LLM003"
    
    # General Errors (GEN)
    GEN_UNKNOWN = "GEN001"
    GEN_NETWORK_ERROR = "GEN002"

class ErrorMessages:
    """User-friendly error messages in Korean"""
    
    ERROR_MAP = {
        # Vector Database Errors
        ErrorCodes.VDB_NO_COLLECTION: {
            "title": "문서가 로드되지 않음",
            "message": "아직 문서가 로드되지 않았습니다. S3 폴더 로드 버튼을 클릭하거나 문서를 업로드해주세요.",
            "solution": "1. 'S3 폴더 로드' 버튼 클릭\n2. 또는 직접 파일 업로드\n3. 문서 로드 완료 후 다시 시도"
        },
        ErrorCodes.VDB_EMPTY: {
            "title": "문서 데이터베이스가 비어있음",
            "message": "벡터 데이터베이스에 문서가 없습니다. 문서를 먼저 업로드해주세요.",
            "solution": "1. S3 폴더에서 문서 로드\n2. 파일 직접 업로드\n3. 텍스트 직접 입력"
        },
        ErrorCodes.VDB_CONNECTION_ERROR: {
            "title": "데이터베이스 연결 오류",
            "message": "벡터 데이터베이스에 연결할 수 없습니다.",
            "solution": "1. 잠시 후 다시 시도\n2. 문제 지속 시 관리자에게 문의"
        },
        
        # Document Processing Errors
        ErrorCodes.DOC_NOT_FOUND: {
            "title": "문서를 찾을 수 없음",
            "message": "요청한 문서를 찾을 수 없습니다.",
            "solution": "1. 파일 경로 확인\n2. 파일이 존재하는지 확인\n3. 다시 업로드 시도"
        },
        ErrorCodes.DOC_INVALID_FORMAT: {
            "title": "지원하지 않는 파일 형식",
            "message": "지원하지 않는 파일 형식입니다. PDF, DOCX, TXT, MD 파일만 업로드 가능합니다.",
            "solution": "1. 지원 형식: PDF, DOCX, TXT, MD\n2. 파일 형식 변환 후 재시도"
        },
        ErrorCodes.DOC_SIZE_TOO_LARGE: {
            "title": "파일 크기 초과",
            "message": "파일 크기가 너무 큽니다. 10MB 이하의 파일만 업로드 가능합니다.",
            "solution": "1. 파일 크기를 10MB 이하로 줄이기\n2. 파일을 분할하여 개별 업로드"
        },
        ErrorCodes.DOC_PROCESSING_ERROR: {
            "title": "문서 처리 오류",
            "message": "문서 처리 중 오류가 발생했습니다.",
            "solution": "1. 문서 파일 확인\n2. 다른 파일로 시도\n3. 잠시 후 다시 시도"
        },
        
        # LLM Errors
        ErrorCodes.LLM_API_KEY_MISSING: {
            "title": "API 키 설정 오류",
            "message": "OpenAI API 키가 설정되지 않았습니다.",
            "solution": "1. 관리자에게 API 키 설정 요청"
        },
        ErrorCodes.LLM_API_ERROR: {
            "title": "AI 모델 응답 오류",
            "message": "AI 모델에서 응답을 받는 중 오류가 발생했습니다.",
            "solution": "1. 잠시 후 다시 시도\n2. 다른 모델 선택\n3. 질문을 단순하게 재작성"
        },
        ErrorCodes.LLM_TIMEOUT: {
            "title": "응답 시간 초과",
            "message": "AI 모델 응답 시간이 초과되었습니다.",
            "solution": "1. 잠시 후 다시 시도\n2. 질문을 더 간단하게 작성"
        },
        
        # General Errors
        ErrorCodes.GEN_UNKNOWN: {
            "title": "알 수 없는 오류",
            "message": "예상치 못한 오류가 발생했습니다.",
            "solution": "1. 페이지 새로고침\n2. 잠시 후 다시 시도\n3. 문제 지속 시 관리자에게 문의"
        },
        ErrorCodes.GEN_NETWORK_ERROR: {
            "title": "네트워크 연결 오류",
            "message": "네트워크 연결에 문제가 있습니다.",
            "solution": "1. 인터넷 연결 확인\n2. 페이지 새로고침\n3. 잠시 후 다시 시도"
        }
    }

def format_error_response(error_code: str, original_error: str = None):
    """Format error response with user-friendly message"""
    
    error_info = ErrorMessages.ERROR_MAP.get(error_code, ErrorMessages.ERROR_MAP[ErrorCodes.GEN_UNKNOWN])
    
    response = {
        "error": True,
        "error_code": error_code,
        "title": error_info["title"],
        "message": error_info["message"],
        "solution": error_info["solution"],
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    # 개발 모드에서는 원본 오류도 포함
    if original_error:
        response["debug_info"] = str(original_error)
    
    return response

def detect_error_type(error_message: str) -> str:
    """Detect error type from error message"""
    error_lower = str(error_message).lower()
    
    # Vector Database Errors
    if "collection" in error_lower and "does not exist" in error_lower:
        return ErrorCodes.VDB_NO_COLLECTION
    elif "empty" in error_lower and ("vector" in error_lower or "database" in error_lower):
        return ErrorCodes.VDB_EMPTY
    elif "chroma" in error_lower or "vector" in error_lower:
        return ErrorCodes.VDB_CONNECTION_ERROR
    
    # Document Errors
    elif "file not found" in error_lower or "no such file" in error_lower:
        return ErrorCodes.DOC_NOT_FOUND
    elif "unsupported" in error_lower and "format" in error_lower:
        return ErrorCodes.DOC_INVALID_FORMAT
    elif "file size" in error_lower or "too large" in error_lower:
        return ErrorCodes.DOC_SIZE_TOO_LARGE
    elif "document" in error_lower and "process" in error_lower:
        return ErrorCodes.DOC_PROCESSING_ERROR
    
    # LLM Errors
    elif "api key" in error_lower:
        return ErrorCodes.LLM_API_KEY_MISSING
    elif "openai" in error_lower or "llm" in error_lower:
        return ErrorCodes.LLM_API_ERROR
    elif "timeout" in error_lower:
        return ErrorCodes.LLM_TIMEOUT
    
    # Network Errors
    elif "network" in error_lower or "connection" in error_lower or "fetch" in error_lower:
        return ErrorCodes.GEN_NETWORK_ERROR
    
    # Default
    else:
        return ErrorCodes.GEN_UNKNOWN