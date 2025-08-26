#!/bin/bash

echo "🚀 VLLM 설치 스크립트"
echo "========================"

# Python 버전 확인
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python 버전: $python_version"

# GPU 확인
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU 감지됨"
    GPU_AVAILABLE=true
else
    echo "⚠️  GPU 없음 - CPU 모드로 설치"
    GPU_AVAILABLE=false
fi

# 메모리 확인
total_mem=$(free -g | awk '/^Mem:/{print $2}')
echo "✅ 총 메모리: ${total_mem}GB"

# 의존성 설치
echo -e "\n📦 의존성 설치 중..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# VLLM 설치
if [ "$GPU_AVAILABLE" = true ]; then
    echo -e "\n🎮 GPU용 VLLM 설치..."
    pip install vllm
else
    echo -e "\n💻 CPU용 VLLM 설치..."
    # CPU 버전은 아직 공식 지원이 제한적
    echo "⚠️  주의: VLLM은 주로 GPU용으로 설계되었습니다."
    echo "💡 대안: llama.cpp, CTransformers, GGUF 형식 사용 권장"
    
    # llama-cpp-python 설치 (CPU 지원)
    pip install llama-cpp-python
fi

# 추가 도구 설치
echo -e "\n🔧 추가 도구 설치..."
pip install transformers accelerate sentencepiece

echo -e "\n✅ 설치 완료!"
echo "📝 사용 가능한 옵션:"
echo "   1. llama-cpp-python (CPU 최적화)"
echo "   2. Transformers + accelerate"
echo "   3. GGUF 형식 모델 사용"