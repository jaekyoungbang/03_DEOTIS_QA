#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 MD 로더 - 애플리케이션 시작시 실행
s3-chunking MD 파일들을 자동으로 벡터 DB에 로드
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 현재 디렉토리 설정
current_dir = Path(__file__).parent
rag_system_dir = current_dir.parent / "rag-qa-system"
sys.path.append(str(rag_system_dir))

# 통합 청킹 로더 import
try:
    from integrated_md_chunking_loader import IntegratedMDChunkingLoader
except ImportError:
    print("❌ integrated_md_chunking_loader를 찾을 수 없습니다.")
    sys.exit(1)

class AutoMDLoaderStartup:
    """애플리케이션 시작시 자동 MD 로딩 클래스"""
    
    def __init__(self, config_file: str = "auto_loader_config.json"):
        self.config_file = os.path.join(current_dir, config_file)
        self.config = self.load_config()
        self.loader = IntegratedMDChunkingLoader()
    
    def load_config(self) -> dict:
        """설정 파일 로드"""
        default_config = {
            "auto_load_on_startup": True,
            "check_file_updates": True,
            "target_collection": "custom",
            "md_files_directory": str(current_dir),
            "last_update_check": None,
            "force_reload": False,
            "enable_logging": True
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 기본 설정과 병합
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # 기본 설정 파일 생성
                self.save_config(default_config)
                return default_config
                
        except Exception as e:
            print(f"⚠️ 설정 파일 로드 실패: {e}, 기본 설정 사용")
            return default_config
    
    def save_config(self, config: dict = None):
        """설정 파일 저장"""
        try:
            if config is None:
                config = self.config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"⚠️ 설정 파일 저장 실패: {e}")
    
    def check_file_updates(self) -> bool:
        """MD 파일 업데이트 확인"""
        md_files = [
            os.path.join(self.config["md_files_directory"], "BC카드_카드이용안내_완전판.md"),
            os.path.join(self.config["md_files_directory"], "BC카드_신용카드업무처리안내_완전판.md")
        ]
        
        latest_mtime = 0
        existing_files = 0
        
        for md_file in md_files:
            if os.path.exists(md_file):
                existing_files += 1
                mtime = os.path.getmtime(md_file)
                latest_mtime = max(latest_mtime, mtime)
        
        if existing_files == 0:
            print("⚠️ MD 파일을 찾을 수 없습니다.")
            return False
        
        # 이전 업데이트 시간과 비교
        last_update = self.config.get("last_update_check")
        if last_update is None or latest_mtime > last_update or self.config.get("force_reload", False):
            self.config["last_update_check"] = latest_mtime
            self.save_config()
            return True
        
        return False
    
    def run_auto_load(self) -> bool:
        """자동 로딩 실행"""
        try:
            if not self.config["auto_load_on_startup"]:
                print("🔄 자동 로딩이 비활성화되어 있습니다.")
                return False
            
            print("🚀 애플리케이션 시작시 자동 MD 로딩 시작")
            print("=" * 60)
            
            # 파일 업데이트 확인
            if self.config["check_file_updates"]:
                if not self.check_file_updates():
                    print("📋 MD 파일 업데이트가 없습니다. 로딩을 건너뜁니다.")
                    return True
            
            # MD 파일 로딩
            print("📖 MD 파일 로딩 및 청킹 처리...")
            chunk_results = self.loader.load_all_md_files(self.config["md_files_directory"])
            
            if not chunk_results:
                print("❌ 로딩할 MD 파일이 없습니다.")
                return False
            
            # 벡터 DB 저장
            print("💾 벡터 DB 저장...")
            success = self.loader.store_to_vectordb(chunk_results)
            
            if success:
                # 로딩 완료 로그
                if self.config["enable_logging"]:
                    self.log_loading_result(chunk_results, True)
                
                print("\n✅ 자동 MD 로딩 완료!")
                print("🎯 s3-chunking 모드에서 최적화된 검색 가능")
                return True
            else:
                print("\n❌ 벡터 DB 저장 실패")
                return False
                
        except Exception as e:
            print(f"💥 자동 로딩 중 오류: {e}")
            if self.config["enable_logging"]:
                self.log_loading_result([], False, str(e))
            return False
    
    def log_loading_result(self, chunk_results: list, success: bool, error_msg: str = None):
        """로딩 결과 로그 저장"""
        try:
            log_file = os.path.join(current_dir, "auto_loading_log.json")
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "files_count": len(chunk_results),
                "total_chunks": sum(r['total_chunks'] for r in chunk_results) if chunk_results else 0,
                "files_processed": [r['source_file'] for r in chunk_results] if chunk_results else [],
                "error_message": error_msg
            }
            
            # 기존 로그 로드
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 새 로그 추가 (최근 10개만 유지)
            logs.append(log_entry)
            logs = logs[-10:]
            
            # 로그 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            print(f"📄 자동 로딩 로그 저장: {log_file}")
            
        except Exception as e:
            print(f"⚠️ 로그 저장 실패: {e}")

def integrate_with_main_app():
    """메인 애플리케이션과 통합"""
    print("\n🔗 메인 애플리케이션 통합 가이드:")
    print("=" * 50)
    
    integration_code = '''
# load_documents_new.py 또는 메인 애플리케이션에 추가:

import sys
from pathlib import Path

# s3-chunking 경로 추가
s3_chunking_path = Path(__file__).parent / "s3-chunking"
sys.path.append(str(s3_chunking_path))

from auto_md_loader_startup import AutoMDLoaderStartup

def load_s3_chunking_on_startup():
    """애플리케이션 시작시 s3-chunking MD 파일 자동 로딩"""
    try:
        auto_loader = AutoMDLoaderStartup()
        return auto_loader.run_auto_load()
    except Exception as e:
        print(f"s3-chunking 자동 로딩 실패: {e}")
        return False

# 애플리케이션 시작 시 호출
if __name__ == "__main__":
    # 기존 로딩 로직...
    
    # s3-chunking 자동 로딩
    load_s3_chunking_on_startup()
    
    # 나머지 애플리케이션 로직...
'''
    
    print(integration_code)
    
    # 통합 파일 생성
    integration_file = os.path.join(parent_dir, "s3_chunking_integration.py")
    try:
        with open(integration_file, 'w', encoding='utf-8') as f:
            f.write(integration_code.strip())
        print(f"\n📁 통합 코드 파일 생성: {integration_file}")
    except Exception as e:
        print(f"⚠️ 통합 파일 생성 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🎯 자동 MD 로더 스타트업")
    print("=" * 60)
    
    try:
        # 자동 로더 실행
        auto_loader = AutoMDLoaderStartup()
        success = auto_loader.run_auto_load()
        
        if success:
            print("\n🎊 자동 MD 로딩 성공!")
            
            # 메인 애플리케이션과 통합 가이드 제공
            integrate_with_main_app()
            
            print("\n💡 설정 파일 위치:", auto_loader.config_file)
            print("   - auto_load_on_startup: 자동 로딩 활성화/비활성화")
            print("   - check_file_updates: 파일 변경사항 확인")
            print("   - force_reload: 강제 재로딩")
            
        else:
            print("\n💥 자동 MD 로딩 실패")
            
    except KeyboardInterrupt:
        print("\n⏸️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()