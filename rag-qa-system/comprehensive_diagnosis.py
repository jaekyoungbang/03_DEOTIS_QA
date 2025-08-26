"""
종합 진단 스크립트 - 벡터DB, 문서, 청킹 상태 전체 확인
"""
import os
import sys
from pathlib import Path
import json

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def check_source_documents():
    """원본 문서 확인"""
    print("=" * 60)
    print("📁 원본 문서 상태 확인")
    print("=" * 60)
    
    # s3 폴더 확인
    s3_path = Path("../s3")
    print(f"\n📂 s3 폴더: {s3_path.absolute()}")
    if s3_path.exists():
        files = list(s3_path.glob("*.docx"))
        print(f"   DOCX 파일: {len(files)}개")
        for file in files:
            size = file.stat().st_size / 1024  # KB
            print(f"   - {file.name}: {size:.1f}KB")
    else:
        print("   ❌ s3 폴더가 없습니다!")
    
    # s3-chunking 폴더 확인
    s3_chunking_path = Path("../s3-chunking")
    print(f"\n📂 s3-chunking 폴더: {s3_chunking_path.absolute()}")
    if s3_chunking_path.exists():
        files = list(s3_chunking_path.glob("*.docx"))
        print(f"   DOCX 파일: {len(files)}개")
        for file in files:
            size = file.stat().st_size / 1024  # KB
            print(f"   - {file.name}: {size:.1f}KB")
    else:
        print("   ❌ s3-chunking 폴더가 없습니다!")

def check_vectordb_structure():
    """벡터DB 구조 확인"""
    print("\n" + "=" * 60)
    print("🗄️ 벡터DB 구조 확인")
    print("=" * 60)
    
    vectordb_path = Path("./data/vectordb")
    if not vectordb_path.exists():
        print("❌ 벡터DB 폴더가 없습니다!")
        return
    
    # SQLite 파일 확인
    sqlite_file = vectordb_path / "chroma.sqlite3"
    if sqlite_file.exists():
        size = sqlite_file.stat().st_size / 1024 / 1024  # MB
        print(f"📋 SQLite DB: {size:.2f}MB")
    else:
        print("❌ SQLite DB 파일이 없습니다!")
    
    # 컬렉션 폴더 확인
    collection_dirs = [d for d in vectordb_path.iterdir() if d.is_dir()]
    print(f"📁 컬렉션 폴더: {len(collection_dirs)}개")
    
    for i, collection_dir in enumerate(collection_dirs):
        if i >= 3:  # 최대 3개만 표시
            break
        files = list(collection_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024  # MB
        print(f"   - {collection_dir.name}: {len(files)}개 파일, {total_size:.2f}MB")

def check_vectordb_content():
    """벡터DB 내용 확인"""
    print("\n" + "=" * 60)
    print("📊 벡터DB 내용 분석")
    print("=" * 60)
    
    try:
        from models.embeddings import EmbeddingManager
        from models.dual_vectorstore import DualVectorStoreManager
        
        # 임베딩 매니저 초기화
        embedding_manager = EmbeddingManager()
        embedding_info = embedding_manager.get_embedding_info()
        print(f"🔧 임베딩 모델: {embedding_info['type']} ({embedding_info['dimension']}차원)")
        print(f"   상태: {embedding_info['status']}")
        if 'server' in embedding_info:
            print(f"   서버: {embedding_info['server']}")
        
        # 듀얼 벡터스토어 매니저 초기화
        dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # Basic 컬렉션 분석
        print(f"\n📂 Basic 컬렉션 (s3 폴더)")
        print("-" * 40)
        basic_store = dual_manager.get_vectorstore("basic")
        if basic_store and hasattr(basic_store, '_collection'):
            try:
                results = basic_store._collection.get()
                total_docs = len(results['ids'])
                print(f"   📄 총 문서: {total_docs}개")
                
                # 고유 내용 분석
                unique_contents = set()
                source_files = {}
                
                for i, content in enumerate(results['documents']):
                    # 내용 고유성 체크
                    content_preview = content[:100]
                    unique_contents.add(content_preview)
                    
                    # 소스 파일 분석
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    source = metadata.get('source_file', 'Unknown')
                    source_files[source] = source_files.get(source, 0) + 1
                
                print(f"   🔍 고유 내용: {len(unique_contents)}개")
                print(f"   📁 소스 파일별 분포:")
                for source, count in sorted(source_files.items()):
                    print(f"      - {source}: {count}개")
                
                # 샘플 내용 표시
                if total_docs > 0:
                    print(f"\n   📋 샘플 내용 (최대 3개):")
                    for i in range(min(3, total_docs)):
                        metadata = results['metadatas'][i] if results['metadatas'] else {}
                        content = results['documents'][i][:150] + "..."
                        source = metadata.get('source_file', 'Unknown')
                        print(f"      {i+1}. [{source}] {content}")
                        
            except Exception as e:
                print(f"   ❌ Basic 컬렉션 조회 오류: {e}")
        else:
            print("   ❌ Basic 컬렉션이 없습니다!")
        
        # Custom 컬렉션 분석
        print(f"\n📂 Custom 컬렉션 (s3-chunking 폴더)")
        print("-" * 40)
        custom_store = dual_manager.get_vectorstore("custom")
        if custom_store and hasattr(custom_store, '_collection'):
            try:
                results = custom_store._collection.get()
                total_docs = len(results['ids'])
                print(f"   📄 총 문서: {total_docs}개")
                
                # 고유 내용 분석
                unique_contents = set()
                source_files = {}
                
                for i, content in enumerate(results['documents']):
                    content_preview = content[:100]
                    unique_contents.add(content_preview)
                    
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    source = metadata.get('source_file', 'Unknown')
                    source_files[source] = source_files.get(source, 0) + 1
                
                print(f"   🔍 고유 내용: {len(unique_contents)}개")
                print(f"   📁 소스 파일별 분포:")
                for source, count in sorted(source_files.items()):
                    print(f"      - {source}: {count}개")
                
                # 샘플 내용 표시
                if total_docs > 0:
                    print(f"\n   📋 샘플 내용 (최대 3개):")
                    for i in range(min(3, total_docs)):
                        metadata = results['metadatas'][i] if results['metadatas'] else {}
                        content = results['documents'][i][:150] + "..."
                        source = metadata.get('source_file', 'Unknown')
                        print(f"      {i+1}. [{source}] {content}")
                        
            except Exception as e:
                print(f"   ❌ Custom 컬렉션 조회 오류: {e}")
        else:
            print("   ❌ Custom 컬렉션이 없습니다!")
            
    except Exception as e:
        print(f"❌ 벡터DB 내용 확인 오류: {e}")

def check_search_quality():
    """검색 품질 테스트"""
    print("\n" + "=" * 60)
    print("🔍 검색 품질 테스트")
    print("=" * 60)
    
    try:
        from models.embeddings import EmbeddingManager
        from models.dual_vectorstore import DualVectorStoreManager
        
        embedding_manager = EmbeddingManager()
        dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        test_queries = [
            "카드발급",
            "BC카드",
            "신용카드",
            "포인트",
            "할부"
        ]
        
        for query in test_queries:
            print(f"\n🔍 검색어: '{query}'")
            print("-" * 30)
            
            # Basic 검색
            try:
                basic_results = dual_manager.similarity_search_with_score(query, "basic", k=3)
                print(f"   Basic: {len(basic_results)}개 결과")
                if basic_results:
                    max_score = max(score for _, score in basic_results)
                    print(f"   최고 유사도: {max_score:.1%}")
                    # 중복 체크
                    contents = [doc.page_content[:50] for doc, _ in basic_results]
                    unique_contents = set(contents)
                    if len(unique_contents) < len(contents):
                        print(f"   ⚠️ 중복 발견: {len(contents) - len(unique_contents)}개")
            except Exception as e:
                print(f"   Basic 검색 오류: {e}")
            
            # Custom 검색
            try:
                custom_results = dual_manager.similarity_search_with_score(query, "custom", k=3)
                print(f"   Custom: {len(custom_results)}개 결과")
                if custom_results:
                    max_score = max(score for _, score in custom_results)
                    print(f"   최고 유사도: {max_score:.1%}")
                    # 중복 체크
                    contents = [doc.page_content[:50] for doc, _ in custom_results]
                    unique_contents = set(contents)
                    if len(unique_contents) < len(contents):
                        print(f"   ⚠️ 중복 발견: {len(contents) - len(unique_contents)}개")
            except Exception as e:
                print(f"   Custom 검색 오류: {e}")
                
    except Exception as e:
        print(f"❌ 검색 품질 테스트 오류: {e}")

def check_logs():
    """로그 파일 확인"""
    print("\n" + "=" * 60)
    print("📋 최근 로그 확인")
    print("=" * 60)
    
    log_files = [
        "app.log",
        "server.log", 
        "server_debug.log",
        "app_latest.log"
    ]
    
    for log_file in log_files:
        log_path = Path(log_file)
        if log_path.exists():
            size = log_path.stat().st_size / 1024  # KB
            print(f"\n📄 {log_file}: {size:.1f}KB")
            
            # 최근 20줄 읽기
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    
                print("   최근 로그:")
                for line in recent_lines:
                    line = line.strip()
                    if line and ('error' in line.lower() or 'fail' in line.lower() or 'exception' in line.lower()):
                        print(f"   ❌ {line[:100]}")
                    elif line and ('success' in line.lower() or 'complete' in line.lower()):
                        print(f"   ✅ {line[:100]}")
                    elif line and len(line) > 10:
                        print(f"   ℹ️  {line[:100]}")
                        
            except Exception as e:
                print(f"   로그 읽기 오류: {e}")
        else:
            print(f"❌ {log_file}: 파일 없음")

def main():
    """메인 진단 함수"""
    print("🔍 RAG 시스템 종합 진단 시작")
    print("현재 시간:", __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        check_source_documents()
        check_vectordb_structure()
        check_vectordb_content()
        check_search_quality()
        check_logs()
        
        print("\n" + "=" * 60)
        print("✅ 진단 완료!")
        print("=" * 60)
        print("\n💡 문제 해결 방법:")
        print("1. 벡터DB 초기화: rd /s /q data\\vectordb")
        print("2. 서버 재시작: python app.py")
        print("3. 관리자 페이지에서 문서 재로딩")
        print("4. 이 스크립트로 다시 확인")
        
    except Exception as e:
        print(f"\n❌ 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()