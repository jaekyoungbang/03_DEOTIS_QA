"""
CPU 최적화 LLM 모델 (llama.cpp 기반)
VLLM 대신 CPU에서 효율적으로 작동
"""
import os
from typing import List, Optional
from llama_cpp import Llama

class CPUOptimizedLLM:
    """CPU에서 최적화된 LLM 실행"""
    
    def __init__(self, 
                 model_path: str = None,
                 n_ctx: int = 2048,      # 컨텍스트 길이
                 n_threads: int = 4,     # CPU 스레드 수
                 n_gpu_layers: int = 0): # GPU 레이어 (0 = CPU only)
        
        # 기본 모델 경로
        if not model_path:
            model_path = os.getenv('LLM_MODEL_PATH', './models/llama-2-7b-chat.Q4_K_M.gguf')
        
        self.model_path = model_path
        self.llm = None
        
        # 모델 초기화
        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            print(f"✅ CPU LLM 모델 로드 완료: {os.path.basename(model_path)}")
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            print("💡 GGUF 형식 모델을 다운로드하세요:")
            print("   https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF")
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """텍스트 생성"""
        if not self.llm:
            return "모델이 로드되지 않았습니다."
        
        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "\n\n"],
            echo=False
        )
        
        return response['choices'][0]['text'].strip()
    
    def invoke(self, prompt: str) -> 'LLMResponse':
        """LangChain 호환 인터페이스"""
        text = self.generate(prompt)
        return LLMResponse(text)

class LLMResponse:
    """LangChain 호환 응답 객체"""
    def __init__(self, content: str):
        self.content = content
        self.additional_kwargs = {}
        
    def __str__(self):
        return self.content

# 사용 가능한 모델 목록
AVAILABLE_MODELS = {
    "llama2-7b": {
        "name": "Llama 2 7B Chat",
        "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
        "size": "3.8GB",
        "description": "Meta의 Llama 2 7B 대화형 모델"
    },
    "mistral-7b": {
        "name": "Mistral 7B Instruct",
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size": "4.1GB",
        "description": "Mistral AI의 고성능 모델"
    },
    "korean-llm": {
        "name": "KULLM v2",
        "url": "https://huggingface.co/nlpai-lab/kullm-polyglot-5.8b-v2-gguf/resolve/main/kullm-polyglot-5.8b-v2.Q4_K_M.gguf",
        "size": "3.5GB",
        "description": "한국어 특화 LLM"
    }
}