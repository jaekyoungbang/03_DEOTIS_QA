#!/usr/bin/env python3
"""
ChromaDB 호환성 문제 해결 스크립트
Windows에서 파일 잠금 문제를 해결합니다.
"""

import os
import shutil
import time
from pathlib import Path

def fix_chromadb_lock():
    """ChromaDB 파일 잠금 문제 해결"""
    print("🔧 ChromaDB 호환성 문제 해결 중...")
    
    vectordb_path = "./data/vectordb"
    
    if os.path.exists(vectordb_path):
        # 백업 디렉토리 생성
        backup_path = f"./data/vectordb_backup_{int(time.time())}"
        
        try:
            # 파일을 개별적으로 처리
            print(f"📦 기존 벡터DB 백업: {vectordb_path} -> {backup_path}")
            shutil.move(vectordb_path, backup_path)
            print("✅ 백업 완료")
            
        except Exception as e:
            print(f"⚠️ 백업 실패: {e}")
            
            # Plan B: 개별 파일 삭제 시도
            try:
                for root, dirs, files in os.walk(vectordb_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.chmod(file_path, 0o777)  # 권한 변경
                            os.remove(file_path)
                            print(f"  삭제됨: {file}")
                        except Exception as file_err:
                            print(f"  삭제 실패: {file} - {file_err}")
                
                # 빈 디렉토리 삭제
                shutil.rmtree(vectordb_path, ignore_errors=True)
                print("✅ 개별 파일 삭제 완료")
                
            except Exception as plan_b_error:
                print(f"❌ Plan B도 실패: {plan_b_error}")
                print("💡 수동으로 data/vectordb 폴더를 삭제해주세요.")
                return False
    
    # 새 디렉토리 생성
    os.makedirs(vectordb_path, exist_ok=True)
    print(f"✅ 새 벡터DB 디렉토리 생성: {vectordb_path}")
    
    return True

if __name__ == "__main__":
    if fix_chromadb_lock():
        print("🎉 ChromaDB 수정 완료! 이제 app.py를 실행할 수 있습니다.")
    else:
        print("❌ 수동 작업이 필요합니다.")