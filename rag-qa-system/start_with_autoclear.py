#!/usr/bin/env python3
"""
RAG 시스템 자동 초기화 시작 스크립트

이 스크립트는 RAG_AUTO_CLEAR_ON_STARTUP 환경 변수를 설정하고
Flask 애플리케이션을 시작합니다.

사용법:
    python start_with_autoclear.py        # 자동 초기화 비활성화로 시작
    python start_with_autoclear.py --clear # 자동 초기화 활성화로 시작
"""

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='RAG 시스템 시작 (자동 초기화 옵션 포함)')
    parser.add_argument(
        '--clear', 
        action='store_true', 
        help='서버 시작 시 모든 데이터를 삭제하고 문서를 다시 로드'
    )
    
    args = parser.parse_args()
    
    # 환경 변수 설정
    if args.clear:
        os.environ['RAG_AUTO_CLEAR_ON_STARTUP'] = 'true'
        print("🗑️ 자동 초기화 모드로 서버를 시작합니다...")
        print("   서버 시작 시 모든 데이터가 삭제되고 문서가 다시 로드됩니다.")
    else:
        os.environ['RAG_AUTO_CLEAR_ON_STARTUP'] = 'false'
        print("📚 일반 모드로 서버를 시작합니다...")
        print("   기존 데이터를 유지하면서 서버가 시작됩니다.")
    
    print("="*60)
    
    # Flask 앱 실행
    try:
        from app import app
        from config import Config
        
        # 필요한 디렉토리 생성
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        
        # 서버 시작
        print("🚀 RAG QA 시스템을 시작합니다...")
        print(f"   서버 주소: http://localhost:{Config.PORT}")
        print(f"   관리자 페이지: http://localhost:{Config.PORT}/admin")
        print(f"   메인 앱: http://localhost:{Config.PORT}/deotisrag")
        print("="*60)
        
        app.run(debug=False, host='0.0.0.0', port=Config.PORT)
        
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()