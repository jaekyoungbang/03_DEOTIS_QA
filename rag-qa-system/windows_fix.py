#!/usr/bin/env python3
"""
Windows 환경에서 패키지 호환성을 위한 패치 스크립트
"""

import subprocess
import sys
import os

def install_compatible_packages():
    """Windows에서 호환되는 패키지 버전들을 설치"""
    
    print("🔧 Windows 호환 패키지 설치 중...")
    
    # 호환되는 패키지 버전들
    packages = [
        "openai==1.3.0",
        "langchain==0.1.0", 
        "langchain-community==0.0.10",
        "langchain-openai==0.0.2",
        "pydantic==2.5.0",
        "flask-restx==1.3.0",
        "docx2txt==0.9",
        "redis==5.0.1"
    ]
    
    for package in packages:
        print(f"📦 설치 중: {package}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--upgrade"])
            print(f"✅ {package} 설치 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} 설치 실패: {e}")
    
    print("\n🎉 패키지 설치 완료!")
    print("이제 'python app.py' 명령어로 실행해보세요.")

if __name__ == "__main__":
    install_compatible_packages()