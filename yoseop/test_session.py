#!/usr/bin/env python3
"""
세션 상태 저장/복원 테스트
"""

import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.claude_state.session_manager import create_session_manager

def test_session_state():
    """세션 상태 테스트"""
    print("🧪 세션 상태 저장/복원 테스트")
    print("=" * 50)
    
    # 세션 매니저 생성
    manager = create_session_manager()
    
    # 1. 플랜 상태 저장
    print("\n1️⃣ 플랜 상태 저장 테스트")
    plan_content = """
## AI 지원자 시스템 확장 계획

### 1. 모든 회사 페르소나 추가 (라인플러스, 쿠팡, 배민, 당근마켓)
### 2. 회사별 인재상 기반 답변 생성 강화
### 3. 웹 인터페이스에 AI 지원자 기능 추가
### 4. 품질별 답변 비교 기능 구현
"""
    manager.save_plan_state(plan_content, "approved")
    
    # 2. TODO 상태 저장
    print("\n2️⃣ TODO 상태 저장 테스트")
    test_todos = [
        {"id": "1", "content": "라인플러스 페르소나 추가", "status": "pending", "priority": "high"},
        {"id": "2", "content": "쿠팡 페르소나 추가", "status": "pending", "priority": "high"},
        {"id": "3", "content": "배민 페르소나 추가", "status": "in_progress", "priority": "medium"},
        {"id": "4", "content": "당근마켓 페르소나 추가", "status": "pending", "priority": "medium"},
        {"id": "5", "content": "회사별 인재상 반영 로직 개선", "status": "pending", "priority": "high"},
        {"id": "6", "content": "웹 인터페이스 API 엔드포인트 추가", "status": "pending", "priority": "medium"}
    ]
    manager.save_todo_state(test_todos)
    
    # 3. 세션 정보 저장
    print("\n3️⃣ 세션 정보 저장 테스트")
    session_info = {
        "action": "AI 지원자 시스템 확장 작업",
        "current_task": "페르소나 데이터 추가",
        "notes": "회사별 인재상을 더 잘 반영하는 답변 생성이 목표"
    }
    manager.save_session_info(session_info)
    
    # 4. 상태 확인
    print("\n4️⃣ 저장된 상태 확인")
    print(manager.get_state_summary())
    
    print("\n✅ 세션 상태 저장 완료!")
    print("💡 이제 다른 터미널에서 `python check_session.py`를 실행해보세요.")

if __name__ == "__main__":
    test_session_state()