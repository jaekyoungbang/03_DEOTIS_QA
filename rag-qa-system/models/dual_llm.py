from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema import StrOutputParser
from typing import Dict, Any
import os
from config import Config

class DualLLMManager:
    """API와 로컬 LLM을 동시에 관리하는 클래스"""
    
    def __init__(self):
        self.api_llm = None
        self.local_llm = None
        self.api_chain = None
        self.local_chain = None
        self._initialize_llms()
        self._create_chains()
    
    def _initialize_llms(self):
        """LLM 초기화"""
        # API LLM (OpenAI)
        api_config = Config.LLM_MODELS['api']
        if api_config['provider'] == 'openai' and Config.OPENAI_API_KEY:
            self.api_llm = ChatOpenAI(
                model_name=api_config['model_name'],
                temperature=api_config['temperature'],
                max_tokens=api_config['max_tokens'],
                api_key=Config.OPENAI_API_KEY
            )
        
        # Local LLM (vLLM OpenAI 호환)
        local_config = Config.LLM_MODELS['local']
        if local_config['provider'] == 'vllm':
            try:
                self.local_llm = ChatOpenAI(
                    model=local_config['model_name'],
                    openai_api_base=local_config['base_url'] + '/v1',
                    openai_api_key='EMPTY',
                    temperature=local_config['temperature'],
                    max_tokens=local_config['max_tokens']
                )
            except Exception as e:
                print(f"로컬 LLM 초기화 실패: {e}")
                self.local_llm = None
        else:
            print(f"지원하지 않는 로컬 LLM provider: {local_config['provider']}")
            self.local_llm = None
    
    def _create_chains(self):
        """RAG 체인 생성"""
        # API Chain
        if self.api_llm:
            api_prompt = ChatPromptTemplate.from_messages([
                ("system", Config.LLM_MODELS['api']['system_prompt']),
                ("human", """다음 문서를 참고하여 질문에 답변해주세요.

문서:
{context}

질문: {question}

답변:""")
            ])
            
            self.api_chain = (
                {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                | api_prompt
                | self.api_llm
                | StrOutputParser()
            )
        
        # Local Chain
        if self.local_llm:
            local_prompt = ChatPromptTemplate.from_template(
                Config.LLM_MODELS['local']['system_prompt'] + """
                
Context:
{context}

Question: {question}

Answer:"""
            )
            
            # vLLM용 커스텀 출력 파서 추가
            def parse_vllm_output(output):
                """vLLM 출력에서 content 추출"""
                if hasattr(output, 'content'):
                    return output.content
                elif isinstance(output, str):
                    return output
                else:
                    return str(output)
            
            self.local_chain = (
                {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                | local_prompt
                | self.local_llm
                | parse_vllm_output
            )
    
    def get_api_chain(self):
        """API 체인 반환"""
        if not self.api_chain:
            raise ValueError("API LLM이 초기화되지 않았습니다. API 키를 확인하세요.")
        return self.api_chain
    
    def get_local_chain(self, model_name=None):
        """로컬 체인 반환 (동적 모델 지원)"""
        if model_name and model_name != getattr(self.local_llm, 'model', None):
            # 동적으로 모델 변경
            local_config = Config.LLM_MODELS['local']
            if local_config['provider'] == 'vllm':
                try:
                    print(f"🔄 동적 로컬 모델 전환: {model_name}")
                    dynamic_llm = ChatOpenAI(
                        model=model_name,
                        openai_api_base=local_config['base_url'] + '/v1',
                        openai_api_key='EMPTY',
                        temperature=local_config['temperature'],
                        max_tokens=local_config['max_tokens']
                    )
                    
                    # 동적 체인 생성
                    local_prompt = ChatPromptTemplate.from_template(
                        Config.LLM_MODELS['local']['system_prompt'] + """
                        
Context:
{context}

Question: {question}

Answer:"""
                    )
                    
                    def parse_vllm_output(output):
                        if hasattr(output, 'content'):
                            return output.content
                        elif isinstance(output, str):
                            return output
                        else:
                            return str(output)
                    
                    dynamic_chain = (
                        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                        | local_prompt
                        | dynamic_llm
                        | parse_vllm_output
                    )
                    
                    return dynamic_chain
                    
                except Exception as e:
                    print(f"동적 로컬 LLM({model_name}) 초기화 실패: {e}")
                    # 기본 체인 사용
                    pass
        
        if not self.local_chain:
            raise ValueError("사내서버 vLLM이 초기화되지 않았습니다. vLLM 서버가 실행 중인지 확인하세요.")
        return self.local_chain
    
    def get_available_models(self) -> Dict[str, bool]:
        """사용 가능한 모델 확인 (실제 연결 테스트)"""
        api_available = False
        local_available = False
        
        # API LLM 테스트
        if self.api_llm:
            try:
                import openai
                # OpenAI API 키 테스트
                if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.strip() == "":
                    print("OpenAI API 키가 설정되지 않음")
                    api_available = False
                else:
                    # 간단한 테스트 메시지로 연결 확인
                    test_response = self.api_llm.invoke("테스트")
                    api_available = True
                    print("[LLM] ChatGPT API 연결 성공")
            except Exception as e:
                print(f"API LLM 연결 실패: {e}")
                api_available = False
        else:
            print("API LLM 객체가 없음")
        
        # 로컬 LLM 테스트 (vLLM 서버)
        if self.local_llm:
            try:
                import requests
                local_config = Config.LLM_MODELS['local']
                
                if local_config['provider'] == 'vllm':
                    # vLLM 서버 연결 테스트
                    test_url = local_config['base_url'] + '/v1/models'
                    response = requests.get(test_url, timeout=3)
                    if response.status_code == 200:
                        # 실제 LLM 호출 테스트
                        test_response = self.local_llm.invoke("테스트")
                        local_available = True
                        print(f"[LLM] vLLM 서버 연결 성공 - {local_config['base_url']}")
                    else:
                        print(f"vLLM 서버가 응답하지 않음: {response.status_code}")
                        local_available = False
                elif local_config['provider'] == 'ollama':
                    # Ollama 서버 연결 테스트 (백업)
                    response = requests.get(local_config['base_url'], timeout=2)
                    if response.status_code == 200:
                        test_response = self.local_llm.invoke("테스트")
                        local_available = True
                        print("Ollama 서버 연결 성공")
                    else:
                        print("Ollama 서버가 응답하지 않음")
                        local_available = False
            except requests.exceptions.ConnectionError:
                print(f"로컬 LLM 서버에 연결할 수 없음 ({local_config['base_url']})")
                local_available = False
            except requests.exceptions.Timeout:
                print("로컬 LLM 서버 연결 타임아웃")
                local_available = False
            except Exception as e:
                print(f"로컬 LLM 연결 실패: {e}")
                local_available = False
        else:
            print("로컬 LLM 객체가 없음")
        
        result = {
            'api': api_available,
            'local': local_available
        }
        print(f"모델 가용성 결과: {result}")
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        info = {}
        
        if self.api_llm:
            info['api'] = {
                'provider': Config.LLM_MODELS['api']['provider'],
                'model': Config.LLM_MODELS['api']['model_name'],
                'display_name': Config.LLM_MODELS['api']['display_name'],
                'temperature': Config.LLM_MODELS['api']['temperature'],
                'status': 'ready'
            }
        else:
            info['api'] = {'status': 'not_initialized'}
        
        if self.local_llm:
            info['local'] = {
                'provider': Config.LLM_MODELS['local']['provider'],
                'model': Config.LLM_MODELS['local']['model_name'],
                'display_name': Config.LLM_MODELS['local']['display_name'],
                'temperature': Config.LLM_MODELS['local']['temperature'],
                'status': 'ready'
            }
        else:
            info['local'] = {'status': 'not_initialized'}
        
        return info