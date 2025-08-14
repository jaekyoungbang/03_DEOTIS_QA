from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
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
        
        # Local LLM (Ollama)
        local_config = Config.LLM_MODELS['local']
        if local_config['provider'] == 'ollama':
            try:
                self.local_llm = Ollama(
                    model=local_config['model_name'],
                    base_url=local_config['base_url'],
                    temperature=local_config['temperature'],
                    num_predict=local_config['max_tokens']
                )
            except Exception as e:
                print(f"로컬 LLM 초기화 실패: {e}")
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
            
            self.local_chain = (
                {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                | local_prompt
                | self.local_llm
                | StrOutputParser()
            )
    
    def get_api_chain(self):
        """API 체인 반환"""
        if not self.api_chain:
            raise ValueError("API LLM이 초기화되지 않았습니다. API 키를 확인하세요.")
        return self.api_chain
    
    def get_local_chain(self):
        """로컬 체인 반환"""
        if not self.local_chain:
            raise ValueError("로컬 LLM이 초기화되지 않았습니다. Ollama가 실행 중인지 확인하세요.")
        return self.local_chain
    
    def get_available_models(self) -> Dict[str, bool]:
        """사용 가능한 모델 확인"""
        return {
            'api': self.api_llm is not None,
            'local': self.local_llm is not None
        }
    
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