#!/usr/bin/env python3
"""
Claude 세션 상태 관리자
세션 간 플랜모드와 TODO 상태를 유지하는 시스템
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class SessionStateManager:
    """세션 상태 관리 클래스"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.getcwd()
        
        self.project_root = Path(project_root)
        self.state_dir = self.project_root / ".claude_state"
        self.state_dir.mkdir(exist_ok=True)
        
        # 상태 파일 경로
        self.plan_file = self.state_dir / "current_plan.json"
        self.todo_file = self.state_dir / "todo_state.json"
        self.session_file = self.state_dir / "session_info.json"
        
        # .gitignore에 상태 디렉토리 추가
        self._update_gitignore()
    
    def _update_gitignore(self):
        """상태 디렉토리를 .gitignore에 추가"""
        gitignore_path = self.project_root / ".gitignore"
        
        try:
            if gitignore_path.exists():
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = ""
            
            if ".claude_state/" not in content:
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    if content and not content.endswith('\n'):
                        f.write('\n')
                    f.write('# Claude 세션 상태 (개인용)\n')
                    f.write('.claude_state/\n')
                    
        except Exception as e:
            print(f"⚠️ .gitignore 업데이트 실패: {e}")
    
    def save_plan_state(self, plan_content: str, status: str = "pending"):
        """플랜 상태 저장"""
        plan_data = {
            "is_active": True,
            "plan_content": plan_content,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.plan_file, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 플랜 상태 저장 완료: {self.plan_file}")
            
        except Exception as e:
            print(f"❌ 플랜 상태 저장 실패: {e}")
    
    def load_plan_state(self) -> Optional[Dict[str, Any]]:
        """플랜 상태 로드"""
        if not self.plan_file.exists():
            return None
        
        try:
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
            
            if plan_data.get("is_active", False):
                return plan_data
            
        except Exception as e:
            print(f"❌ 플랜 상태 로드 실패: {e}")
        
        return None
    
    def update_plan_status(self, status: str):
        """플랜 상태 업데이트"""
        plan_data = self.load_plan_state()
        if plan_data:
            plan_data["status"] = status
            plan_data["last_updated"] = datetime.now().isoformat()
            
            if status in ["completed", "cancelled"]:
                plan_data["is_active"] = False
            
            try:
                with open(self.plan_file, 'w', encoding='utf-8') as f:
                    json.dump(plan_data, f, ensure_ascii=False, indent=2)
                print(f"✅ 플랜 상태 업데이트: {status}")
                
            except Exception as e:
                print(f"❌ 플랜 상태 업데이트 실패: {e}")
    
    def save_todo_state(self, todos: List[Dict[str, Any]]):
        """TODO 상태 저장"""
        todo_data = {
            "todos": todos,
            "last_updated": datetime.now().isoformat(),
            "total_count": len(todos),
            "completed_count": len([t for t in todos if t.get("status") == "completed"]),
            "in_progress_count": len([t for t in todos if t.get("status") == "in_progress"])
        }
        
        try:
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                json.dump(todo_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"❌ TODO 상태 저장 실패: {e}")
    
    def load_todo_state(self) -> Optional[Dict[str, Any]]:
        """TODO 상태 로드"""
        if not self.todo_file.exists():
            return None
        
        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"❌ TODO 상태 로드 실패: {e}")
            return None
    
    def save_session_info(self, info: Dict[str, Any]):
        """세션 정보 저장"""
        session_data = {
            **info,
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root)
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ 세션 정보 저장 실패: {e}")
    
    def load_session_info(self) -> Optional[Dict[str, Any]]:
        """세션 정보 로드"""
        if not self.session_file.exists():
            return None
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"❌ 세션 정보 로드 실패: {e}")
            return None
    
    def check_previous_session(self) -> Dict[str, Any]:
        """이전 세션 상태 확인"""
        result = {
            "has_active_plan": False,
            "has_todos": False,
            "plan_data": None,
            "todo_data": None,
            "session_data": None,
            "summary": ""
        }
        
        # 플랜 상태 확인
        plan_data = self.load_plan_state()
        if plan_data:
            result["has_active_plan"] = True
            result["plan_data"] = plan_data
        
        # TODO 상태 확인
        todo_data = self.load_todo_state()
        if todo_data and todo_data.get("todos"):
            result["has_todos"] = True
            result["todo_data"] = todo_data
        
        # 세션 정보 확인
        session_data = self.load_session_info()
        if session_data:
            result["session_data"] = session_data
        
        # 요약 메시지 생성
        summary_parts = []
        
        if result["has_active_plan"]:
            status = plan_data.get("status", "unknown")
            created_at = plan_data.get("created_at", "")
            if created_at:
                created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
                summary_parts.append(f"📋 활성 플랜: {status} ({created_date})")
        
        if result["has_todos"]:
            total = todo_data.get("total_count", 0)
            completed = todo_data.get("completed_count", 0)
            in_progress = todo_data.get("in_progress_count", 0)
            summary_parts.append(f"✅ TODO: {completed}/{total} 완료, {in_progress}개 진행중")
        
        if summary_parts:
            result["summary"] = "\n".join(summary_parts)
        
        return result
    
    def clear_all_state(self):
        """모든 상태 파일 삭제"""
        files_to_remove = [self.plan_file, self.todo_file, self.session_file]
        
        for file_path in files_to_remove:
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"🗑️ 삭제됨: {file_path.name}")
            except Exception as e:
                print(f"❌ 삭제 실패 {file_path.name}: {e}")
        
        print("✅ 모든 세션 상태가 초기화되었습니다.")
    
    def get_state_summary(self) -> str:
        """현재 상태 요약"""
        previous_session = self.check_previous_session()
        
        if not (previous_session["has_active_plan"] or previous_session["has_todos"]):
            return "현재 저장된 세션 상태가 없습니다."
        
        summary = "📊 현재 세션 상태:\n"
        summary += "=" * 50 + "\n"
        
        if previous_session["summary"]:
            summary += previous_session["summary"] + "\n"
        
        if previous_session["session_data"]:
            last_session = previous_session["session_data"].get("timestamp", "")
            if last_session:
                last_date = datetime.fromisoformat(last_session).strftime("%Y-%m-%d %H:%M")
                summary += f"🕒 마지막 세션: {last_date}\n"
        
        return summary


def create_session_manager(project_root: str = None) -> SessionStateManager:
    """세션 매니저 팩토리 함수"""
    return SessionStateManager(project_root)


def check_and_restore_session(project_root: str = None) -> bool:
    """세션 복원 대화형 인터페이스"""
    manager = create_session_manager(project_root)
    previous_session = manager.check_previous_session()
    
    if not (previous_session["has_active_plan"] or previous_session["has_todos"]):
        return False
    
    print("\n" + "="*60)
    print("🔄 이전 세션 발견!")
    print("="*60)
    print(previous_session["summary"])
    print("="*60)
    
    while True:
        choice = input("\n다음 중 선택하세요:\n1. 이전 작업 계속하기\n2. 새로 시작하기\n3. 상태 삭제하기\n선택 (1-3): ").strip()
        
        if choice == "1":
            print("✅ 이전 세션을 복원합니다.")
            return True
        elif choice == "2":
            print("🆕 새로운 세션을 시작합니다.")
            return False
        elif choice == "3":
            confirm = input("⚠️ 모든 상태를 삭제하시겠습니까? (y/N): ").strip().lower()
            if confirm == 'y':
                manager.clear_all_state()
                return False
        else:
            print("❌ 올바른 선택지를 입력하세요.")


if __name__ == "__main__":
    # 세션 매니저 테스트
    print("🧪 세션 상태 관리자 테스트")
    
    manager = create_session_manager()
    
    # 테스트 데이터 저장
    manager.save_plan_state("AI 지원자 모델 구현 계획", "approved")
    
    test_todos = [
        {"id": "1", "content": "LLM 관리자 구현", "status": "completed", "priority": "high"},
        {"id": "2", "content": "답변 품질 제어", "status": "in_progress", "priority": "high"},
        {"id": "3", "content": "웹 인터페이스", "status": "pending", "priority": "medium"}
    ]
    manager.save_todo_state(test_todos)
    
    manager.save_session_info({"action": "AI 지원자 시스템 개발"})
    
    # 상태 확인
    print("\n" + manager.get_state_summary())
    
    # 복원 테스트
    check_and_restore_session()