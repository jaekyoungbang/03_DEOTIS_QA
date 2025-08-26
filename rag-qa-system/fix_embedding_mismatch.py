"""
임베딩 차원 불일치 문제 해결 스크립트
"""
import os
import sys
import shutil
from pathlib import Path

def fix_embedding_mismatch():
    print("=" * 60)
    print("임베딩 차원 불일치 문제 해결")
    print("=" * 60)
    print()
    
    # 1. 현재 설정 확인
    print("1. 현재 임베딩 설정 확인...")
    use_bge_m3 = os.getenv('USE_OLLAMA_BGE_M3', 'true').lower() == 'true'
    print(f"   - USE_OLLAMA_BGE_M3: {use_bge_m3}")
    print(f"   - BGE-M3 차원: 1024")
    print(f"   - OpenAI 차원: 1536")
    print()
    
    # 2. 문제 진단
    print("2. 문제 진단:")
    print("   - 현재 벡터DB는 OpenAI (1536차원)로 생성됨")
    print("   - 하지만 BGE-M3 (1024차원)을 사용하려고 함")
    print("   - 해결: OpenAI 임베딩으로 전환 또는 벡터DB 재생성")
    print()
    
    # 3. 해결 방법 제시
    print("3. 해결 방법 선택:")
    print("   A. OpenAI 임베딩 사용 (빠른 해결)")
    print("   B. BGE-M3로 벡터DB 재생성 (시간 소요)")
    print()
    
    choice = input("선택하세요 (A/B): ").strip().upper()
    
    if choice == 'A':
        # OpenAI 임베딩 사용
        print("\n4. OpenAI 임베딩으로 전환...")
        
        # .env 파일 업데이트
        env_path = Path('.env')
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # USE_OLLAMA_BGE_M3 설정 변경
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('USE_OLLAMA_BGE_M3'):
                    lines[i] = 'USE_OLLAMA_BGE_M3=false\n'
                    updated = True
                    break
            
            if not updated:
                lines.append('\nUSE_OLLAMA_BGE_M3=false\n')
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print("   ✅ .env 파일 업데이트 완료")
        else:
            # .env 파일 생성
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('USE_OLLAMA_BGE_M3=false\n')
            print("   ✅ .env 파일 생성 완료")
        
        print("\n✅ 설정 완료! 서버를 재시작하세요.")
        
    elif choice == 'B':
        # BGE-M3로 재생성
        print("\n4. 벡터DB 재생성 준비...")
        vectordb_path = Path('./data/vectordb')
        
        if vectordb_path.exists():
            import time
            backup_name = f"vectordb_backup_{int(time.time())}"
            backup_path = Path(f'./data/{backup_name}')
            
            try:
                shutil.move(str(vectordb_path), str(backup_path))
                print(f"   ✅ 기존 DB 백업: {backup_path}")
            except Exception as e:
                print(f"   ❌ 백업 실패: {e}")
                print("   💡 서버를 종료하고 다시 시도하세요.")
                return
        
        # 새 디렉토리 생성
        vectordb_path.mkdir(parents=True, exist_ok=True)
        print("   ✅ 새 벡터DB 디렉토리 생성")
        
        # .env 파일 확인/생성
        env_path = Path('.env')
        if not env_path.exists():
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('USE_OLLAMA_BGE_M3=true\n')
            print("   ✅ .env 파일 생성 (BGE-M3 사용)")
        
        print("\n✅ 준비 완료!")
        print("\n다음 단계:")
        print("1. 서버 재시작: python app.py")
        print("2. 관리자 페이지에서 '문서 재로딩' 클릭")
        print("   또는 python load_documents_new.py 실행")
    
    else:
        print("\n❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    fix_embedding_mismatch()