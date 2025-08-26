"""
벡터DB 내용 확인 스크립트
"""
import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def check_vectordb_content():
    """벡터DB에 저장된 문서 내용 확인"""
    try:
        from models.embeddings import EmbeddingManager
        from models.dual_vectorstore import DualVectorStoreManager
        
        # 임베딩 매니저 초기화
        embedding_manager = EmbeddingManager()
        embedding_info = embedding_manager.get_embedding_info()
        
        print("=" * 60)
        print("벡터DB 내용 확인")
        print("=" * 60)
        print(f"임베딩 모델: {embedding_info['type']} ({embedding_info['dimension']}차원)")
        print()
        
        # 듀얼 벡터스토어 매니저 초기화
        dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
        
        # Basic 벡터스토어 확인
        print("📂 Basic 벡터스토어 (s3 폴더)")
        print("-" * 40)
        basic_store = dual_manager.get_vectorstore("basic")
        if basic_store and hasattr(basic_store, '_collection'):
            try:
                results = basic_store._collection.get()
                doc_count = len(results['ids'])
                print(f"문서 수: {doc_count}개")
                
                if doc_count > 0:
                    print("\n상위 3개 문서:")
                    for i in range(min(3, doc_count)):
                        metadata = results['metadatas'][i] if results['metadatas'] else {}
                        content = results['documents'][i][:200] + "..." if len(results['documents'][i]) > 200 else results['documents'][i]
                        
                        print(f"\n{i+1}. ID: {results['ids'][i]}")
                        print(f"   소스: {metadata.get('source', 'Unknown')}")
                        print(f"   파일: {metadata.get('source_file', 'Unknown')}")
                        print(f"   내용: {content}")
                        
            except Exception as e:
                print(f"Basic 벡터스토어 조회 오류: {e}")
        else:
            print("Basic 벡터스토어가 없습니다.")
        
        print("\n" + "=" * 60)
        
        # Custom 벡터스토어 확인
        print("📂 Custom 벡터스토어 (s3-chunking 폴더)")
        print("-" * 40)
        custom_store = dual_manager.get_vectorstore("custom")
        if custom_store and hasattr(custom_store, '_collection'):
            try:
                results = custom_store._collection.get()
                doc_count = len(results['ids'])
                print(f"문서 수: {doc_count}개")
                
                if doc_count > 0:
                    print("\n상위 3개 문서:")
                    for i in range(min(3, doc_count)):
                        metadata = results['metadatas'][i] if results['metadatas'] else {}
                        content = results['documents'][i][:200] + "..." if len(results['documents'][i]) > 200 else results['documents'][i]
                        
                        print(f"\n{i+1}. ID: {results['ids'][i]}")
                        print(f"   소스: {metadata.get('source', 'Unknown')}")
                        print(f"   파일: {metadata.get('source_file', 'Unknown')}")
                        print(f"   내용: {content}")
                        
            except Exception as e:
                print(f"Custom 벡터스토어 조회 오류: {e}")
        else:
            print("Custom 벡터스토어가 없습니다.")
            
        # 검색 테스트
        print("\n" + "=" * 60)
        print("🔍 검색 테스트: '카드발급'")
        print("-" * 40)
        
        test_results = dual_manager.similarity_search_with_score("카드발급", "basic", k=3)
        print(f"검색 결과: {len(test_results)}개")
        
        for i, (doc, score) in enumerate(test_results):
            print(f"\n{i+1}. 유사도: {score:.3f}")
            print(f"   소스: {doc.metadata.get('source', 'Unknown')}")
            print(f"   내용: {doc.page_content[:100]}...")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_vectordb_content()