from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from config import Config

class LLMManager:
    def __init__(self, model_name=None):
        # 기본 API 모델 사용
        self.model_name = model_name or Config.LLM_MODELS['api']['model_name']
        self.llm = None
        self.available_models = {
            'gpt-4o-mini': 'gpt-4o-mini',
            'gpt-4-turbo': 'gpt-4-turbo',
            'gpt-4': 'gpt-4',
            'gpt-3.5-turbo': 'gpt-3.5-turbo'
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
            self.initialize_llm(model_name)
        return self.llm
    
    def get_available_models(self):
        """Get list of available models"""
        return list(self.available_models.keys())
    
    def generate_response(self, prompt, streaming=False, model_name=None):
        """Generate a response from the LLM"""
        llm = self.get_llm(model_name)
        if streaming:
            return llm.stream(prompt)
        return llm.invoke(prompt)