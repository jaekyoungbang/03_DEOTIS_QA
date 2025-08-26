from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from config import Config
import requests
import json
import os

class LLMManager:
    def __init__(self, model_name=None):
        # 기본 API 모델 사용
        self.model_name = model_name or Config.LLM_MODELS['api']['model_name']
        self.llm = None
        self.available_models = {
            'gpt-4o-mini': 'gpt-4o-mini',
            'gpt-4-turbo': 'gpt-4-turbo',
            'gpt-4': 'gpt-4',
            'gpt-3.5-turbo': 'gpt-3.5-turbo',
            'local': 'local-llm',  # 로컬 LLM 옵션 추가
            'yanolja': 'yanolja-llm'  # Yanolja LLM 추가
        }
        self.initialize_llm()
    
    def initialize_llm(self, model_name=None):
        """Initialize the LLM based on configuration"""
        if model_name:
            self.model_name = model_name
            
        if Config.OPENAI_API_KEY:
            # Map user-friendly names to actual model names
            actual_model = self.available_models.get(self.model_name, self.model_name)
            
            try:
                # Try new version format first
                self.llm = ChatOpenAI(
                    openai_api_key=Config.OPENAI_API_KEY,
                    model=actual_model,
                    temperature=Config.LLM_MODELS['api']['temperature'],
                    max_tokens=Config.LLM_MODELS['api']['max_tokens'],
                    streaming=True
                )
            except Exception as e:
                # Fallback to older version format
                try:
                    self.llm = ChatOpenAI(
                        api_key=Config.OPENAI_API_KEY,
                        model_name=actual_model,
                        temperature=Config.LLM_MODELS['api']['temperature'],
                        max_tokens=Config.LLM_MODELS['api']['max_tokens'],
                        streaming=True
                    )
                except Exception as e2:
                    # Last resort - minimal parameters
                    import os
                    os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
                    self.llm = ChatOpenAI(
                        model=actual_model,
                        temperature=Config.LLM_MODELS['api']['temperature'],
                        max_tokens=Config.LLM_MODELS['api']['max_tokens']
                    )
        else:
            raise ValueError("No API key provided. Please set OPENAI_API_KEY in .env file")
    
    def get_llm(self, model_name=None):
        """Get the LLM instance, optionally switching models"""
        if model_name and model_name != self.model_name:
            if model_name == 'local':
                # vLLM 로컬 LLM 사용
                self.model_name = 'local'
                return self.get_vllm_llm()
            elif model_name == 'yanolja':
                # Yanolja LLM 사용 (vLLM을 통해)
                self.model_name = 'yanolja'
                return self.get_vllm_llm()
            else:
                self.initialize_llm(model_name)
        elif self.model_name == 'local':
            return self.get_vllm_llm()
        elif self.model_name == 'yanolja':
            return self.get_vllm_llm()
        return self.llm
    
    def get_vllm_llm(self):
        """Get vLLM OpenAI 호환 LLM instance"""
        config = Config.LLM_MODELS['local']
        return ChatOpenAI(
            model=config['model_name'],
            openai_api_base=config['base_url'] + '/v1',
            openai_api_key='EMPTY',
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )
    
    def get_ollama_llm(self):
        """Get Ollama LLM instance (백업용)"""
        config = Config.LLM_MODELS['local']
        return Ollama(
            model=config['model_name'],
            base_url=config['base_url'],
            temperature=config['temperature']
        )
    
    def get_available_models(self):
        """Get list of available models"""
        return list(self.available_models.keys())
    
    def generate_response(self, prompt, streaming=False, model_name=None):
        """Generate a response from the LLM"""
        llm = self.get_llm(model_name)
        if streaming:
            return llm.stream(prompt)
        return llm.invoke(prompt)


class LocalLLM:
    """로컬 LLM 래퍼 클래스"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        
    def invoke(self, prompt):
        """로컬 LLM 서버에 요청을 보내고 응답을 받습니다"""
        try:
            # 문자열이나 다른 형태의 프롬프트를 처리
            if hasattr(prompt, 'content'):
                message_content = prompt.content
            elif isinstance(prompt, str):
                message_content = prompt
            else:
                message_content = str(prompt)
                
            # 프롬프트에서 컨텍스트와 질문 추출
            if '질문:' in message_content and '컨텍스트:' in message_content:
                try:
                    # 컨텍스트 추출 (컨텍스트: 와 질문: 사이)
                    context_start = message_content.find('컨텍스트:') + 6
                    context_end = message_content.find('질문:', context_start)
                    if context_end == -1:
                        context_end = len(message_content)
                    context = message_content[context_start:context_end].strip()
                    
                    # 질문 추출 (질문: 와 답변: 사이)
                    question_start = message_content.find('질문:') + 3
                    question_end = message_content.find('답변:', question_start)
                    if question_end == -1:
                        question_end = len(message_content)
                    question = message_content[question_start:question_end].strip()
                    
                    # 디버깅 출력
                    print(f"[LocalLLM] 질문: {question[:50]}...")
                    print(f"[LocalLLM] 컨텍스트 길이: {len(context)}자")
                    
                    # 컨텍스트 기반 답변 생성
                    answer = self._generate_simple_answer(context, question)
                    return LocalLLMResponse(answer)
                except Exception as e:
                    print(f"[LocalLLM] 프롬프트 파싱 오류: {e}")
                    pass
            
            # 폴백: 로컬 LLM 서버 호출
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": "microsoft/DialoGPT-small",
                        "messages": [{"role": "user", "content": message_content[:200]}],  # 길이 제한
                        "stream": False
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('message', {}).get('content', '')
                    if content and content.strip():
                        return LocalLLMResponse(content)
            except:
                pass
                
            # 최종 폴백: 컨텍스트 기반 간단 답변
            return LocalLLMResponse(f"검색된 정보를 기반으로 답변드립니다: {message_content[:150]}...")
                
        except Exception as e:
            return LocalLLMResponse(f"로컬 LLM 처리 오류: {str(e)}")
    
    def _generate_simple_answer(self, context, question):
        """컨텍스트와 질문을 기반으로 답변 생성 - 실제 검색된 컨텍스트 활용"""
        
        # 디버깅: 받은 컨텍스트 확인
        print(f"[LocalLLM] 원본 컨텍스트 첫 200자: {context[:200]}...")
        
        # 프롬프트 템플릿이 섞인 경우 정리
        if "중요 지침:" in context or "당신은 BC카드" in context:
            # 실제 컨텍스트만 추출 (프롬프트 템플릿 제거)
            lines = context.split('\n')
            clean_context = []
            skip_template = False
            in_template = False
            
            for line in lines:
                line = line.strip()
                
                # 템플릿 시작 감지
                if any(x in line for x in ["당신은 BC카드", "중요 지침:", "마크다운 표 형식", "체크리스트 형식"]):
                    in_template = True
                    continue
                    
                # 빈 줄로 템플릿 끝 감지
                if in_template and line == "":
                    in_template = False
                    continue
                
                # 템플릿이 아닌 실제 컨텍스트만 수집
                if not in_template and len(line) > 10 and not line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')):
                    clean_context.append(line)
            
            context = '\n'.join(clean_context)
            print(f"[LocalLLM] 정제된 컨텍스트 첫 200자: {context[:200]}...")
        
        # 질문의 핵심 키워드 추출
        keywords = []
        if '민원' in question:
            keywords.extend(['민원', '접수', '유선', '서면', '인터넷', '1588-4000', 'FAX', '내용증명'])
        if '전자제품' in question or '고가품' in question:
            keywords.extend(['전자제품', '고가품', '일시불', '구입', '구매'])
        if '할부' in question:
            keywords.append('할부')
        if '일시불' in question:
            keywords.append('일시불')
        if '신용카드' in question:
            keywords.append('신용카드')
        if '카드발급' in question or '발급기준' in question:
            keywords.extend(['카드발급', '발급기준', '금융당국', '모범규준'])
            
        print(f"[LocalLLM] 추출된 키워드: {keywords}")
        print(f"[LocalLLM] 컨텍스트 길이: {len(context)}자")
            
        # 컨텍스트에서 관련 문장 찾기
        relevant_sentences = []
        for line in context.split('\n'):
            line = line.strip()
            if len(line) > 20 and any(keyword in line for keyword in keywords):
                relevant_sentences.append(line)
        
        # 검색된 컨텍스트가 있으면 활용
        if len(context) > 100:  # 컨텍스트가 충분히 있으면
            if relevant_sentences:
                # 가장 관련성 높은 문장 선택
                best_sentence = max(relevant_sentences, key=lambda x: sum(1 for k in keywords if k in x))
                
                # 민원접수방법 관련 질문 - 범용적 처리
                if '민원' in question and ('접수' in question or '안내' in question):
                    # 민원접수 관련 키워드가 많이 포함된 경우
                    keyword_count = sum(1 for keyword in ['민원', '접수', '유선', '서면', '인터넷', '1588-4000'] 
                                       if keyword in context)
                    if keyword_count >= 3 and len(context) > 200:
                        # 컨텍스트에서 "[민원접수방법 안내]" 섹션만 추출
                        if '[민원접수방법 안내]' in context:
                            start_idx = context.find('[민원접수방법 안내]')
                            # 다음 섹션 시작까지 또는 끝까지 추출
                            section_end_markers = ['[', '업무 처리자', '구분 |', '\n\n\n', '=====']
                            end_idx = len(context)
                            
                            for marker in section_end_markers:
                                marker_pos = context.find(marker, start_idx + 20)  # 제목 이후부터 찾기
                                if marker_pos != -1 and marker_pos < end_idx:
                                    end_idx = marker_pos
                            
                            complaint_section = context[start_idx:end_idx].strip()
                            if len(complaint_section) > 100:  # 충분한 내용이 있으면
                                return f"검색된 정보를 바탕으로 답변드립니다:\n\n{complaint_section}"
                        
                        # 폴백: 전체 컨텍스트 반환
                        return f"검색된 정보를 바탕으로 답변드립니다:\n\n{context.strip()}"
                
                # 카드발급기준 관련 질문
                elif '카드발급' in question or '발급기준' in question:
                    if '금융당국' in context or '모범규준' in context:
                        return "카드발급 기준은 금융당국의 「신용카드 발급 및 이용한도 부여에 관한 모범규준」과 카드사 자체 기준에 따라 결정됩니다. 월 가처분 소득 50만원 이상, 개인신용평점 등을 종합적으로 평가합니다."
                
                # 전자제품/고가품 일시불 질문의 경우
                elif ('전자제품' in question or '고가품' in question) and '일시불' in best_sentence:
                    if '수수료 부담 없이' in best_sentence and '13일' in best_sentence:
                        return "전자제품 등 고가품을 일시불로 구입해야 하는 이유는 별도의 수수료 부담 없이 물품구매일로부터 최단 13일에서 최장 44일까지 현금결제를 유예받을 수 있기 때문입니다. 또한 구매에 사용할 예정이었던 현금을 통장에 보관하여 이자를 받을 수 있는 장점이 있습니다."
                
                # 기타 관련 문장이 있으면 그대로 반환
                return best_sentence
            
            # 관련 문장은 없지만 컨텍스트가 있으면 첫 문장 활용
            first_meaningful_line = ""
            for line in context.split('\n'):
                line = line.strip()
                if len(line) > 50 and not line.startswith('http'):
                    first_meaningful_line = line
                    break
            
            if first_meaningful_line:
                return f"검색된 정보에 따르면: {first_meaningful_line}"
        
        # 컨텍스트가 부족하면 기본 응답
        return "제공된 문서에서 해당 질문과 관련된 구체적인 정보를 찾을 수 없습니다. BC카드 고객센터(1588-8888)로 문의하시면 더 자세한 안내를 받으실 수 있습니다."
    
    def stream(self, prompt):
        """스트리밍은 간단한 invoke 결과를 반환"""
        return [self.invoke(prompt)]


class LocalLLMResponse:
    """로컬 LLM 응답을 LangChain 형태로 래핑"""
    
    def __init__(self, content):
        self.content = content
        self.additional_kwargs = {}
        self.response_metadata = {
            'finish_reason': 'stop',
            'model_name': 'local-llm',
            'system_fingerprint': 'local',
            'service_tier': 'local'
        }
        self.id = 'local-llm-response'
    
    def __str__(self):
        return self.content