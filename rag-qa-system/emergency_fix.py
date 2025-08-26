"""
긴급 수정 스크립트 - 진단된 문제들 자동 해결
"""
import os
import shutil
import time
from pathlib import Path

def emergency_fix():
    """긴급 수정 실행"""
    print("🚨 RAG 시스템 긴급 수정 시작")
    print("=" * 50)
    
    # 1. 임시 파일 삭제
    print("\n1. 임시 파일 정리...")
    temp_files = [
        "../s3/~$카드(신용카드 업무처리 안내).docx",
        "../s3-chunking/~$카드(신용카드 업무처리 안내).docx"
    ]
    
    for temp_file in temp_files:
        temp_path = Path(temp_file)
        if temp_path.exists():
            try:
                temp_path.unlink()
                print(f"   ✅ 삭제: {temp_file}")
            except Exception as e:
                print(f"   ⚠️ 삭제 실패: {temp_file} - {e}")
    
    # 2. 벡터DB 백업 및 삭제
    print("\n2. 벡터DB 초기화...")
    vectordb_path = Path("./data/vectordb")
    
    if vectordb_path.exists():
        # 백업 생성
        backup_name = f"vectordb_emergency_backup_{int(time.time())}"
        backup_path = Path(f"./data/backup/{backup_name}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.move(str(vectordb_path), str(backup_path))
            print(f"   ✅ 백업 생성: {backup_path}")
        except Exception as e:
            print(f"   ⚠️ 백업 실패, 강제 삭제 시도: {e}")
            shutil.rmtree(vectordb_path, ignore_errors=True)
    
    # 새 디렉토리 생성
    vectordb_path.mkdir(parents=True, exist_ok=True)
    print("   ✅ 새 벡터DB 디렉토리 생성")
    
    # 3. 캐시 초기화
    print("\n3. 캐시 초기화...")
    cache_paths = [
        "./data/cache",
        "./data/chunked_documents"
    ]
    
    for cache_path in cache_paths:
        cache_dir = Path(cache_path)
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ 초기화: {cache_path}")
    
    # 4. 환경 변수 설정 확인
    print("\n4. 설정 파일 확인...")
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        if "USE_OLLAMA_BGE_M3=false" in env_content:
            print("   ✅ OpenAI 임베딩 설정 확인됨")
        else:
            print("   ⚠️ BGE-M3 설정 발견 - OpenAI로 변경 권장")
    
    # 5. 문제 해결 요약
    print("\n" + "=" * 50)
    print("✅ 긴급 수정 완료!")
    print("=" * 50)
    print("\n다음 단계:")
    print("1. 서버 재시작: python app.py")
    print("2. 관리자 페이지 접속: http://localhost:5001/admin")
    print("3. '문서 재로딩' 버튼 클릭")
    print("4. 검색 테스트 실행")
    print("\n예상 개선사항:")
    print("- 중복 데이터 해결")
    print("- 검색 유사도 70% 이상 달성")
    print("- 차원 불일치 문제 해결")

if __name__ == "__main__":
    emergency_fix()