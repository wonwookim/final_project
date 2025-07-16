#!/usr/bin/env python3
"""
세션 복원 체크 스크립트
프로젝트 시작 시 이전 세션 상태를 확인하고 복원 여부를 결정
"""

import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.claude_state.session_manager import check_and_restore_session

def main():
    """메인 함수"""
    print("🔍 Claude 세션 상태 확인 중...")
    
    # 이전 세션 복원 체크
    should_restore = check_and_restore_session()
    
    if should_restore:
        print("✅ 이전 세션이 복원되었습니다.")
        print("💡 이제 이전 작업을 이어서 진행할 수 있습니다.")
    else:
        print("🆕 새로운 세션을 시작합니다.")
    
    return should_restore

if __name__ == "__main__":
    main()