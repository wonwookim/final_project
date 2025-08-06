import time
import json
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Metadata:
    interview_id: str
    step: int
    task: str
    from_agent: str 
    next_agent: str
    status_code: int

@dataclass
class Content:
    type: str
    content: str

@dataclass
class Metrics:
    total_time: Optional[float] = None
    duration: Optional[float] = None
    answer_seq: Optional[int] = None

@dataclass
class AgentMessage:
    metadata: Metadata
    content: Content
    metrics: Metrics = field(default_factory=Metrics)

class Orchestrator:
    def __init__(self, session_id: str, initial_settings: Dict[str, Any]):
        self.state: Dict[str, Any] = {
            "session_id": session_id,
            "turn_count": 0,
            "answer_seq": 0,  # 0: 질문생성, 1: 첫 답변, 2: 두 번째 답변
            "current_question": None,
            "qa_history": [],
            "who_answers_first": None, # 'user' 또는 'ai'
            "is_completed": False,
            **initial_settings
        }
        self.start_time = time.perf_counter()
        self.random_choice: Optional[int] = None # 랜덤 선택 값을 저장할 인스턴스 변수 추가

    def get_current_state(self) -> Dict[str, Any]:
        return self.state

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        from_agent = message.get("metadata", {}).get("from_agent", "unknown")
        print(f"[Orchestrator] ⬅️ [Agent: {from_agent}]")
        print(json.dumps(message, indent=2, ensure_ascii=False))

        task = message.get("metadata", {}).get("task")
        content = message.get("content", {}).get("content")

        if task == "question_generated":
            self.state['current_question'] = content
            self.state['answer_seq'] = 1
            self.state['who_answers_first'] = 'user' if self.state['turn_count'] % 2 == 0 else 'ai'
            
        if task == "question_generated":
            self.state['current_question'] = content
            self.state['answer_seq'] = 1
            # self.state['who_answers_first'] = random.choice(['user', 'ai']) # 이 라인 제거
            
        elif task == "answer_generated":
            self.state['qa_history'].append({
                "question": self.state['current_question'],
                "answerer": from_agent,
                "answer": content
            })
            
            if self.state['answer_seq'] == 1:
                self.state['answer_seq'] = 2
            else:
                self.state['answer_seq'] = 0
                self.state['turn_count'] += 1
                self.state['current_question'] = None

        next_message = self._decide_next_message()
        next_agent = next_message.get("metadata", {}).get("next_agent", "unknown")
        print(f"[Orchestrator] ➡️ [Agent: {next_agent}]")
        print(json.dumps(next_message, indent=2, ensure_ascii=False))
        return next_message

    def _decide_next_message(self) -> Dict[str, Any]:
        next_agent_options = ['user', 'ai'] # 'candidate' 대신 'ai' 사용

        if self.state['turn_count'] >= self.state.get('total_question_limit', 15):
            self.state['is_completed'] = True
            return self.create_message(content_text="면접이 종료되었습니다.", task="end_interview", next_agent="system")

        if self.state['answer_seq'] == 0:
            # 첫 번째: 면접관이 질문 생성
            self.random_choice = self.random_select()  # 인스턴스 변수로 저장
            # self.state['who_answers_first'] = next_agent_options[0] if self.random_choice == -1 else next_agent_options[1]
            return self.create_message(content_text="다음 질문을 생성해주세요.", task="generate_question", next_agent="interviewer")
        
        elif self.state['answer_seq'] == 1:
            # 두 번째: 랜덤 선택된 에이전트가 답변
            selected_agent = next_agent_options[0] if self.random_choice == -1 else next_agent_options[1]
            self.state['who_answers_first'] = selected_agent # state에 저장
            return self.create_message(content_text=self.state['current_question'], task="generate_answer", next_agent=selected_agent)
            
        elif self.state['answer_seq'] == 2:
            # 세 번째: 반대 에이전트가 답변
            selected_agent = next_agent_options[1] if self.random_choice == -1 else next_agent_options[0]
            return self.create_message(content_text=self.state['current_question'], task="generate_answer", next_agent=selected_agent)

    def create_message(self, content_text: str, task: str, next_agent: str, content_type: str = "text") -> Dict[str, Any]:
        current_time = time.perf_counter()
        return {
            "metadata": {
                "interview_id": self.state['session_id'],
                "step": self.state['turn_count'],
                "task": task,
                "from_agent": "orchestrator",
                "next_agent": next_agent,
                "status_code": 200
            },
            "content": {
                "type": content_type,
                "content": content_text
            },
            "metrics": {
                "total_time": current_time - self.start_time,
                "duration": 0, # 이 값은 agent가 채워야 함
                "answer_seq": self.state['answer_seq']
            }
        }

    @staticmethod
    def create_agent_message(session_id: str, task: str, from_agent: str, content_text: str, 
                             turn_count: int, duration: float = 0, content_type: str = "text") -> Dict[str, Any]:
        """외부(Agent)에서 Orchestrator로 보낼 메시지를 생성하는 정적 메서드"""
        return {
            "metadata": {
                "interview_id": session_id,
                "step": turn_count,
                "task": task,
                "from_agent": from_agent,
                "next_agent": "orchestrator",
                "status_code": 200
            },
            "content": {
                "type": content_type,
                "content": content_text
            },
            "metrics": {
                "duration": duration
            }
        }

    def random_select(self):
        """사용자와 AI 중 랜덤으로 선택하는 메서드"""
        return random.choice([-1, 1])
