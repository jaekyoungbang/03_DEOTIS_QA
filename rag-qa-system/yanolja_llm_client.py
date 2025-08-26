import ollama
import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Generator
from yanolja_config import YanoljaConfig
import json
import time

logger = logging.getLogger(__name__)

class YanoljaLLMClient:
    """야놀자 LLM 클라이언트 클래스"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
        self.config = YanoljaConfig()
        
    def check_health(self) -> Dict:
        """야놀자 LLM 서비스 상태 체크"""
        try:
            models = self.client.list()
            available_models = [m['name'] for m in models.get('models', [])]
            
            # 야놀자 모델 체크
            yanolja_models = []
            configured_models = []
            
            for model_type, model_config in self.config.YANOLJA_MODELS.items():
                model_name = model_config['model_name']
                configured_models.append(model_name)
                if model_name in available_models:
                    yanolja_models.append(model_name)
            
            return {
                'status': 'healthy' if yanolja_models else 'warning',
                'ollama_url': self.base_url,
                'total_models': len(available_models),
                'configured_models': configured_models,
                'available_models': yanolja_models,
                'missing_models': list(set(configured_models) - set(yanolja_models))
            }
        except Exception as e:
            logger.error(f"야놀자 LLM 헬스체크 실패: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'ollama_url': self.base_url
            }
    
    def chat(self, 
             message: str, 
             model_type: str = 'travel',
             context: Optional[List[str]] = None,
             stream: bool = False) -> str:
        """야놀자 LLM과 채팅 (동기 방식)"""
        try:
            model_config = self.config.get_model_config(model_type)
            model_name = model_config['model_name']
            
            # 시스템 프롬프트와 컨텍스트 구성
            system_prompt = model_config['system_prompt']
            
            # 컨텍스트가 있으면 메시지에 추가
            if context:
                context_text = "\n\n".join(context)
                full_message = f"""참고 문서:
{context_text}

질문: {message}

위 참고 문서를 바탕으로 정확하고 도움이 되는 답변을 해주세요."""
            else:
                full_message = message
            
            # Ollama 채팅 호출
            response = self.client.chat(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': full_message}
                ],
                stream=stream,
                options={
                    'temperature': model_config['temperature'],
                    'top_p': 0.9,
                    'top_k': 40,
                    'num_predict': model_config['max_tokens'],
                    'stop': ['</s>', '<|im_end|>']
                }
            )
            
            if stream:
                return response  # Generator 반환
            else:
                return response['message']['content']
                
        except ollama.ResponseError as e:
            logger.error(f"Ollama 응답 에러 (모델: {model_type}): {e}")
            return f"죄송합니다. 야놀자 AI 서비스에서 오류가 발생했습니다: {str(e)}"
        except Exception as e:
            logger.error(f"야놀자 LLM 에러 (모델: {model_type}): {e}")
            return f"죄송합니다. 야놀자 AI 서비스에 일시적인 문제가 발생했습니다."
    
    def chat_stream(self, 
                   message: str, 
                   model_type: str = 'travel',
                   context: Optional[List[str]] = None) -> Generator[str, None, None]:
        """야놀자 LLM 스트리밍 채팅"""
        try:
            response_generator = self.chat(message, model_type, context, stream=True)
            
            for chunk in response_generator:
                if chunk.get('message', {}).get('content'):
                    yield chunk['message']['content']
                    
        except Exception as e:
            logger.error(f"야놀자 LLM 스트리밍 에러: {e}")
            yield f"스트리밍 중 오류가 발생했습니다: {str(e)}"
    
    async def async_chat(self, 
                        message: str, 
                        model_type: str = 'travel',
                        context: Optional[List[str]] = None) -> str:
        """야놀자 LLM 비동기 채팅"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, message, model_type, context, False)
    
    def get_model_info(self, model_type: str = 'travel') -> Dict:
        """모델 정보 조회"""
        try:
            model_config = self.config.get_model_config(model_type)
            model_name = model_config['model_name']
            
            # Ollama에서 모델 정보 가져오기
            try:
                model_info = self.client.show(model_name)
                return {
                    'type': model_type,
                    'name': model_name,
                    'display_name': model_config['display_name'],
                    'size': model_info.get('size', 'Unknown'),
                    'family': model_info.get('details', {}).get('family', 'Unknown'),
                    'parameters': model_info.get('details', {}).get('parameter_size', 'Unknown'),
                    'quantization': model_info.get('details', {}).get('quantization_level', 'Unknown')
                }
            except:
                return {
                    'type': model_type,
                    'name': model_name,
                    'display_name': model_config['display_name'],
                    'status': 'not_found'
                }
                
        except Exception as e:
            logger.error(f"모델 정보 조회 실패: {e}")
            return {'error': str(e)}
    
    def benchmark_model(self, model_type: str = 'travel', test_query: str = "안녕하세요") -> Dict:
        """모델 성능 벤치마크"""
        try:
            start_time = time.time()
            
            response = self.chat(test_query, model_type)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'model_type': model_type,
                'test_query': test_query,
                'response': response[:100] + "..." if len(response) > 100 else response,
                'response_time_seconds': round(response_time, 2),
                'tokens_per_second': round(len(response.split()) / response_time, 2) if response_time > 0 else 0,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'model_type': model_type,
                'status': 'failed',
                'error': str(e)
            }

# 전역 인스턴스
_yanolja_client = None

def get_yanolja_client() -> YanoljaLLMClient:
    """야놀자 LLM 클라이언트 싱글톤"""
    global _yanolja_client
    if _yanolja_client is None:
        config = YanoljaConfig()
        _yanolja_client = YanoljaLLMClient(config.OLLAMA_BASE_URL)
    return _yanolja_client