"""
중복 청크 문제 해결 스크립트
"""
import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def check_and_fix_duplicates():
    """중복 청크 확인 및 수정"""
    try:
        from models.embeddings import EmbeddingManager
        from models.dual_vectorstore import DualVectorStoreManager
        
        print("=" * 60)
        print("중복 청크 문제 진단 및 해결")
        print("=" * 60)
        
        # 임베딩 매니저 초기화
        embedding_manager = EmbeddingManager()
        embedding_info = embedding_manager.get_embedding_info()
        print(f"임베딩 모델: {embedding_info['type']} ({embedding_info['dimension']}차원)")
        
        # 듀얼 벡터스토어 매니저 초기화
        dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # Basic 벡터스토어 검사
        print("\n📂 Basic 벡터스토어 중복 검사")
        print("-" * 40)
        basic_store = dual_manager.get_vectorstore("basic")
        if basic_store and hasattr(basic_store, '_collection'):
            try:
                results = basic_store._collection.get()
                total_docs = len(results['ids'])
                print(f"전체 문서 수: {total_docs}개")
                
                # 내용별 그룹화로 중복 확인
                content_groups = {}
                for i, content in enumerate(results['documents']):
                    content_hash = hash(content[:100])  # 앞 100자로 해시
                    if content_hash not in content_groups:
                        content_groups[content_hash] = []
                    content_groups[content_hash].append({
                        'id': results['ids'][i],
                        'content': content[:200] + "...",
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })
                
                # 중복 그룹 찾기
                duplicate_groups = {k: v for k, v in content_groups.items() if len(v) > 1}
                print(f"고유 내용 그룹: {len(content_groups)}개")
                print(f"중복 그룹: {len(duplicate_groups)}개")
                
                if duplicate_groups:
                    print("\n🔍 중복 그룹 상세:")
                    for i, (hash_key, group) in enumerate(duplicate_groups.items()):
                        if i >= 3:  # 상위 3개만 표시
                            break
                        print(f"\n{i+1}. 중복 {len(group)}개:")
                        print(f"   내용: {group[0]['content']}")
                        for doc in group:
                            source = doc['metadata'].get('source', 'Unknown')
                            print(f"   - ID: {doc['id'][:20]}... 소스: {source}")
                
            except Exception as e:
                print(f"Basic 벡터스토어 검사 오류: {e}")
        
        # Custom 벡터스토어 검사
        print(f"\n📂 Custom 벡터스토어 중복 검사")
        print("-" * 40)
        custom_store = dual_manager.get_vectorstore("custom")
        if custom_store and hasattr(custom_store, '_collection'):
            try:
                results = custom_store._collection.get()
                total_docs = len(results['ids'])
                print(f"전체 문서 수: {total_docs}개")
                
                # 내용별 그룹화로 중복 확인
                content_groups = {}
                for i, content in enumerate(results['documents']):
                    content_hash = hash(content[:100])
                    if content_hash not in content_groups:
                        content_groups[content_hash] = []
                    content_groups[content_hash].append({
                        'id': results['ids'][i],
                        'content': content[:200] + "...",
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })
                
                # 중복 그룹 찾기
                duplicate_groups = {k: v for k, v in content_groups.items() if len(v) > 1}
                print(f"고유 내용 그룹: {len(content_groups)}개")
                print(f"중복 그룹: {len(duplicate_groups)}개")
                
                if duplicate_groups:
                    print("\n🔍 중복 그룹 상세:")
                    for i, (hash_key, group) in enumerate(duplicate_groups.items()):
                        if i >= 3:
                            break
                        print(f"\n{i+1}. 중복 {len(group)}개:")
                        print(f"   내용: {group[0]['content']}")
                        for doc in group:
                            source = doc['metadata'].get('source', 'Unknown')
                            print(f"   - ID: {doc['id'][:20]}... 소스: {source}")
                            
            except Exception as e:
                print(f"Custom 벡터스토어 검사 오류: {e}")
        
        print("\n" + "=" * 60)
        print("💡 해결 방법:")
        print("1. 관리자 페이지에서 '🔄 BGE-M3로 벡터DB 초기화' 클릭")
        print("2. 또는 수동으로: rd /s /q data\\vectordb")
        print("3. 서버 재시작 후 문서 재로딩")
        print("4. 중복 제거 로직 개선 필요")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_fix_duplicates()