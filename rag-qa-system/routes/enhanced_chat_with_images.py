from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import time
from config import Config
from services.enhanced_rag_chain_with_images import create_enhanced_rag_chain_with_images
from services.similarity_suggestions import SimilarityBasedSuggestions
from models.dual_vectorstore import get_dual_vectorstore
import hashlib
import json

router = APIRouter()

# 글로벌 RAG 체인 인스턴스
rag_chain = None
suggestions_service = None

class ChatRequest(BaseModel):
    query: str
    mode: int = 1  # 1: local+basic, 2: local+custom, 3: openai+basic, 4: openai+custom
    benchmarking: bool = False

class ChatResponse(BaseModel):
    answer: str
    mode_description: str
    processing_time: float
    benchmarking_results: Optional[dict] = None
    suggestions: Optional[List[str]] = None
    images: Optional[List[Dict]] = None
    has_images: bool = False

def get_rag_chain():
    """RAG 체인 인스턴스 반환 (이미지 처리 포함)"""
    global rag_chain
    if rag_chain is None:
        vectorstore = get_dual_vectorstore()
        rag_chain = create_enhanced_rag_chain_with_images(vectorstore)
    return rag_chain

def get_suggestions_service():
    """추천 서비스 인스턴스 반환"""
    global suggestions_service
    if suggestions_service is None:
        vectorstore = get_dual_vectorstore()
        suggestions_service = SimilarityBasedSuggestions(vectorstore)
    return suggestions_service

def get_mode_info(mode: int) -> tuple:
    """모드에 따른 LLM과 청킹 타입 반환"""
    mode_map = {
        1: ("local", "basic", "사내서버 vLLM + s3-기본"),
        2: ("local", "custom", "사내서버 vLLM + s3-chunking"),
        3: ("openai", "basic", "ChatGPT + s3-기본"),
        4: ("openai", "custom", "ChatGPT + s3-chunking")
    }
    return mode_map.get(mode, ("local", "basic", "사내서버 vLLM + s3-기본"))

@router.post("/chat/with-images", response_model=ChatResponse)
async def chat_with_images(request: ChatRequest):
    """이미지 정보를 포함한 채팅 엔드포인트"""
    try:
        start_time = time.time()
        
        # 모드 정보 설정
        llm_type, chunking_type, mode_description = get_mode_info(request.mode)
        Config.LLM_TYPE = llm_type
        Config.BENCHMARKING_MODE = request.benchmarking
        
        # RAG 체인 가져오기
        chain = get_rag_chain()
        suggestions_service = get_suggestions_service()
        
        print(f"\n[CHAT_WITH_IMAGES] 요청 처리 시작")
        print(f"  - 질문: {request.query}")
        print(f"  - 모드: {mode_description}")
        print(f"  - 벤치마킹: {request.benchmarking}")
        
        # 응답 생성
        response = chain.process_query(
            query=request.query,
            top_k=5,
            chunking_type=chunking_type
        )
        
        # 응답 유형 확인
        if response.get('type') == 'error':
            raise HTTPException(status_code=500, detail=response['message'])
        
        # 이미지 정보 추출
        images = response.get('images', [])
        has_images = len(images) > 0
        
        # 이미지 정보가 있을 경우 응답에 추가
        if has_images:
            print(f"[CHAT_WITH_IMAGES] {len(images)}개의 이미지 발견")
            # 응답에 이미지 참조 추가
            if not request.benchmarking:
                answer = response.get('answer', '')
                if images and "이미지" not in answer:
                    answer += f"\n\n📷 관련 이미지 {len(images)}개가 문서에 포함되어 있습니다."
                    response['answer'] = answer
        
        # 벤치마킹 모드 처리
        if request.benchmarking and response.get('type') == 'benchmark':
            # 각 LLM 결과 정리
            benchmark_data = {
                'local_llm': response.get('local_llm', {}),
                'openai_llm': response.get('openai_llm', {}),
                'comparison': response.get('comparison', {})
            }
            
            # 이미지 정보 추가
            if has_images:
                benchmark_data['images_found'] = len(images)
            
            # 우선 응답 결정
            if llm_type == "local":
                primary_answer = benchmark_data['local_llm'].get('answer', '')
            else:
                primary_answer = benchmark_data['openai_llm'].get('answer', '')
            
            final_response = ChatResponse(
                answer=primary_answer,
                mode_description=mode_description,
                processing_time=time.time() - start_time,
                benchmarking_results=benchmark_data,
                images=images if has_images else None,
                has_images=has_images
            )
        else:
            # 일반 모드 응답
            answer = response.get('answer', '')
            
            # 유사 질문 추천 (이미지 관련 질문 포함)
            suggestions = None
            if chunking_type == 'custom' and has_images:
                # 이미지 관련 추천 질문 추가
                base_suggestions = suggestions_service.get_suggestions(request.query, chunking_type)
                image_suggestions = [
                    "이 문서에 포함된 이미지를 설명해주세요",
                    "관련 그림이나 도표가 있나요?"
                ]
                suggestions = base_suggestions[:3] + image_suggestions[:1]
            else:
                suggestions = suggestions_service.get_suggestions(request.query, chunking_type)
            
            final_response = ChatResponse(
                answer=answer,
                mode_description=mode_description,
                processing_time=time.time() - start_time,
                suggestions=suggestions[:5] if suggestions else None,
                images=images if has_images else None,
                has_images=has_images
            )
        
        print(f"[CHAT_WITH_IMAGES] 응답 생성 완료 (처리시간: {final_response.processing_time:.2f}초)")
        if has_images:
            print(f"[CHAT_WITH_IMAGES] 이미지 정보 포함됨: {len(images)}개")
        
        return final_response
        
    except Exception as e:
        print(f"[CHAT_WITH_IMAGES] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/chat/images/search")
async def search_images(query: str = Query(..., description="검색 쿼리")):
    """이미지가 포함된 문서 검색"""
    try:
        vectorstore = get_dual_vectorstore()
        
        # custom 컬렉션에서 검색 (s3-chunking)
        results = vectorstore.similarity_search_with_score(query, "custom", k=10)
        
        image_documents = []
        for doc, score in results:
            if doc.metadata.get('has_images', False):
                images = doc.metadata.get('images', [])
                image_documents.append({
                    'content_preview': doc.page_content[:200] + '...',
                    'section': doc.metadata.get('section', ''),
                    'filename': doc.metadata.get('filename', ''),
                    'images': images,
                    'image_count': len(images),
                    'score': float(score)
                })
        
        return {
            'query': query,
            'total_results': len(results),
            'image_documents': image_documents,
            'image_document_count': len(image_documents)
        }
        
    except Exception as e:
        print(f"[IMAGE_SEARCH] 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"이미지 검색 중 오류가 발생했습니다: {str(e)}"
        )