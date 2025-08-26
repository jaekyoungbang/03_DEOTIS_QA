"""
벡터 데이터베이스 초기화 스크립트
BGE-M3 임베딩으로 새로 생성
"""
import os
import shutil
import time
from pathlib import Path

def reset_vectordb():
    """벡터 DB 초기화 및 재생성"""
    vectordb_path = Path("./data/vectordb")
    
    print("🔄 벡터 데이터베이스 초기화 시작...")
    
    # 1. 기존 벡터 DB 백업
    if vectordb_path.exists():
        backup_path = Path(f"./data/vectordb_backup_{int(time.time())}")
        print(f"📦 기존 데이터 백업: {backup_path}")
        try:
            shutil.move(str(vectordb_path), str(backup_path))
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            print("💡 서버를 종료하고 다시 시도해주세요.")
            return False
    
    # 2. 새 디렉토리 생성
    vectordb_path.mkdir(parents=True, exist_ok=True)
    print("✅ 새 벡터 DB 디렉토리 생성 완료")
    
    # 3. BGE-M3 사용 설정 확인
    os.environ['USE_OLLAMA_BGE_M3'] = 'true'
    print("✅ BGE-M3 임베딩 모델 설정 완료")
    
    return True

if __name__ == "__main__":
    if reset_vectordb():
        print("\n🎉 벡터 DB 초기화 완료!")
        print("📝 다음 단계:")
        print("1. 서버 재시작: python app.py")
        print("2. 관리자 페이지에서 '문서 재로딩' 실행")
        print("3. 또는 직접 실행: python load_documents_new.py")
    else:
        print("\n❌ 초기화 실패")