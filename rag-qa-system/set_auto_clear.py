#!/usr/bin/env python3
"""
RAG 시스템 자동 초기화 설정 스크립트

서버 시작 시 자동으로 모든 데이터를 삭제하고 문서를 다시 로드하는 기능을 
활성화/비활성화할 수 있습니다.

사용법:
    python set_auto_clear.py --enable   # 자동 초기화 활성화
    python set_auto_clear.py --disable  # 자동 초기화 비활성화
    python set_auto_clear.py --status   # 현재 상태 확인
"""

import os
import argparse
import sys

def set_auto_clear(enable=True):
    """자동 초기화 설정"""
    if enable:
        os.environ['RAG_AUTO_CLEAR_ON_STARTUP'] = 'true'
        print("✅ 자동 초기화가 활성화되었습니다.")
        print("   서버 시작 시 모든 데이터가 삭제되고 문서가 다시 로드됩니다.")
        print("   환경 변수: RAG_AUTO_CLEAR_ON_STARTUP=true")
    else:
        os.environ['RAG_AUTO_CLEAR_ON_STARTUP'] = 'false'
        print("✅ 자동 초기화가 비활성화되었습니다.")
        print("   서버 시작 시 기존 데이터가 유지됩니다.")
        print("   환경 변수: RAG_AUTO_CLEAR_ON_STARTUP=false")

def get_auto_clear_status():
    """현재 자동 초기화 상태 확인"""
    current_value = os.environ.get('RAG_AUTO_CLEAR_ON_STARTUP', 'false')
    is_enabled = current_value.lower() == 'true'
    
    print("=" * 50)
    print("📊 자동 초기화 상태")
    print("=" * 50)
    print(f"현재 상태: {'활성화' if is_enabled else '비활성화'}")
    print(f"환경 변수: RAG_AUTO_CLEAR_ON_STARTUP={current_value}")
    
    if is_enabled:
        print("\n⚠️  주의사항:")
        print("   - 서버 시작 시 모든 데이터가 삭제됩니다")
        print("   - 벡터 DB, Redis, SQLite 모두 초기화됩니다")
        print("   - S3 폴더에서 문서가 자동으로 다시 로드됩니다")
    else:
        print("\nℹ️  정보:")
        print("   - 서버 시작 시 기존 데이터가 보존됩니다")
        print("   - 필요시 관리자 페이지에서 수동으로 초기화할 수 있습니다")
    
    print("=" * 50)

def main():
    parser = argparse.ArgumentParser(
        description='RAG 시스템 자동 초기화 설정',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python set_auto_clear.py --enable   # 자동 초기화 활성화
  python set_auto_clear.py --disable  # 자동 초기화 비활성화
  python set_auto_clear.py --status   # 현재 상태 확인

주의사항:
  자동 초기화를 활성화하면 서버 시작할 때마다 모든 데이터가 삭제됩니다!
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--enable', action='store_true', help='자동 초기화 활성화')
    group.add_argument('--disable', action='store_true', help='자동 초기화 비활성화') 
    group.add_argument('--status', action='store_true', help='현재 상태 확인')
    
    args = parser.parse_args()
    
    try:
        if args.enable:
            set_auto_clear(enable=True)
        elif args.disable:
            set_auto_clear(enable=False)
        elif args.status:
            get_auto_clear_status()
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()