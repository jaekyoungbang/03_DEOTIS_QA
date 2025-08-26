from typing import List, Dict, Tuple, Any, Optional
import numpy as np
from services.enhanced_rag_chain import EnhancedRAGChain
from models.dual_llm import DualLLMManager
from config import Config
import re


class EnhancedRAGChainWithImages(EnhancedRAGChain):
    """이미지 경로 처리가 추가된 개선된 RAG 체인"""
    
    def __init__(self, vectorstore):
        super().__init__(vectorstore)
        self.image_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        
    def _extract_images_from_documents(self, documents: List) -> List[Dict]:
        """문서에서 이미지 정보 추출"""
        all_images = []
        seen_paths = set()  # 중복 제거
        
        for doc in documents:
            # 메타데이터에서 이미지 정보 확인
            if hasattr(doc, 'metadata'):
                images_in_metadata = doc.metadata.get('images', [])
                for img in images_in_metadata:
                    if img['path'] not in seen_paths:
                        seen_paths.add(img['path'])
                        all_images.append({
                            'path': img['path'],
                            'source': doc.metadata.get('filename', 'unknown'),
                            'section': doc.metadata.get('section', ''),
                            'type': 'metadata'
                        })
            
            # 콘텐츠에서도 이미지 경로 추출 (추가 안전장치)
            if hasattr(doc, 'page_content'):
                for match in self.image_pattern.finditer(doc.page_content):
                    path = match.group(1)
                    if path not in seen_paths:
                        seen_paths.add(path)
                        all_images.append({
                            'path': path,
                            'source': doc.metadata.get('filename', 'unknown') if hasattr(doc, 'metadata') else 'unknown',
                            'section': doc.metadata.get('section', '') if hasattr(doc, 'metadata') else '',
                            'type': 'content'
                        })
        
        return all_images
    
    def _create_context_with_images(self, documents: List, images: List[Dict]) -> str:
        """이미지 정보를 포함한 컨텍스트 생성"""
        context_parts = []
        
        # 문서 내용 추가
        for i, doc in enumerate(documents):
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            
            context_parts.append(f"[문서 {i+1}]")
            if metadata.get('section'):
                context_parts.append(f"섹션: {metadata['section']}")
            context_parts.append(content)
            context_parts.append("")
        
        # 이미지 정보 추가
        if images:
            context_parts.append("\n[관련 이미지 정보]")
            for img in images:
                context_parts.append(f"- 이미지 경로: {img['path']}")
                if img['section']:
                    context_parts.append(f"  섹션: {img['section']}")
                if img['source']:
                    context_parts.append(f"  출처: {img['source']}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def process_query(self, query: str, top_k: int = 3, chunking_type: str = None) -> Dict:
        """질의 처리 - 이미지 정보 포함"""
        
        # 1. 관련 문서 검색
        results = self._search_documents(query, top_k, chunking_type)
        
        if not results:
            return {
                'type': 'error',
                'message': '관련 문서를 찾을 수 없습니다.'
            }
        
        # 2. 문서에서 이미지 정보 추출
        documents = [doc for doc, _ in results[:top_k]]
        images = self._extract_images_from_documents(documents)
        
        # 3. 이미지 포함 컨텍스트 생성
        context = self._create_context_with_images(documents, images)
        
        # 4. LLM에 전달할 프롬프트 구성
        if chunking_type == 'custom':
            # s3-chunking 모드용 프롬프트
            prompt_template = """당신은 BC카드 고객 상담 전문가입니다. 
주어진 문서와 이미지 정보를 바탕으로 고객의 질문에 정확하고 친절하게 답변해주세요.

문서에 테이블이나 표가 있는 경우, 구조를 유지하여 보기 좋게 표시해주세요.
이미지가 관련된 경우, 이미지 정보도 함께 언급해주세요.

컨텍스트:
{context}

질문: {query}

답변:"""
        else:
            # 기본 모드용 프롬프트
            prompt_template = """당신은 BC카드 고객 상담 전문가입니다.
주어진 문서를 바탕으로 고객의 질문에 정확하고 친절하게 답변해주세요.

컨텍스트:
{context}

질문: {query}

답변:"""
        
        # 5. LLM 응답 생성
        try:
            if self.use_benchmarking:
                # 벤치마킹 모드
                response = self._generate_benchmarking_response(query, context, prompt_template, images)
            else:
                # 일반 모드
                response = self._generate_normal_response(query, context, prompt_template, images)
            
            # 이미지 정보 추가
            if images:
                response['images'] = images
                response['has_images'] = True
            
            return response
            
        except Exception as e:
            print(f"[ENHANCED_RAG_IMAGES] 응답 생성 오류: {e}")
            return {
                'type': 'error',
                'message': f'응답 생성 중 오류가 발생했습니다: {str(e)}'
            }
    
    def _generate_normal_response(self, query: str, context: str, prompt_template: str, images: List[Dict]) -> Dict:
        """일반 모드 응답 생성"""
        try:
            # 현재 활성 LLM 확인
            current_llm_type = Config.LLM_TYPE
            
            # 프롬프트 생성
            prompt = prompt_template.format(context=context, query=query)
            
            # LLM 응답 생성
            if current_llm_type == "local":
                llm_response = self.dual_llm.local_llm.invoke(prompt)
                answer = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                llm_name = "사내서버 vLLM"
            else:
                llm_response = self.dual_llm.openai_llm.invoke(prompt)
                answer = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                llm_name = "ChatGPT"
            
            # 이미지 참조 추가 (답변에 이미지 언급이 있을 경우)
            if images and "이미지" in answer:
                answer += "\n\n📷 관련 이미지가 문서에 포함되어 있습니다."
            
            return {
                'type': 'normal',
                'answer': answer,
                'llm_used': llm_name,
                'context_length': len(context),
                'images_found': len(images)
            }
            
        except Exception as e:
            print(f"[ENHANCED_RAG_IMAGES] 일반 응답 생성 오류: {e}")
            raise
    
    def _generate_benchmarking_response(self, query: str, context: str, prompt_template: str, images: List[Dict]) -> Dict:
        """벤치마킹 모드 응답 생성"""
        try:
            prompt = prompt_template.format(context=context, query=query)
            
            # 두 LLM에서 응답 생성
            benchmark_result = self.benchmarker.benchmark_query(
                query=query,
                context=context,
                prompt=prompt
            )
            
            # 이미지 정보 추가
            if images:
                benchmark_result['images_found'] = len(images)
                
                # 각 LLM 응답에 이미지 참조 추가
                for llm_type in ['local_llm', 'openai_llm']:
                    if llm_type in benchmark_result and "이미지" in benchmark_result[llm_type].get('answer', ''):
                        benchmark_result[llm_type]['answer'] += "\n\n📷 관련 이미지가 문서에 포함되어 있습니다."
            
            return benchmark_result
            
        except Exception as e:
            print(f"[ENHANCED_RAG_IMAGES] 벤치마킹 응답 생성 오류: {e}")
            raise


def create_enhanced_rag_chain_with_images(vectorstore):
    """이미지 처리가 포함된 개선된 RAG 체인 생성"""
    return EnhancedRAGChainWithImages(vectorstore)