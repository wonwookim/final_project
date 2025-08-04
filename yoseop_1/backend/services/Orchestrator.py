import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Metadata:
    interview_id: str
    step: int
    task: str
    from_agent: str 
    next_agent: str

@dataclass
class Content:
    type: str  # HR, TECH, COLLABORATION
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
    # 메시지 템플릿 (클래스 변수)
    MESSAGE_TEMPLATE = {
        "metadata": {
            "interview_id": "",
            "step": 1,
            "task": "",
            "from_agent": "",
            "next_agent": ""
        },
        "content": {
            "type": "",  # HR, TECH, COLLABORATION
            "content": ""
        },
        "metrics": {
            "total_time": 0.0,
            "duration": 0.0,
            "answer_seq": 0
        }
    }
    
    def __init__(self, session_id):
        self.sessions = {}
        self.start_time = time.perf_counter()
        self.session_id = session_id
        self.step_counter = 0  # step 추적을 위한 카운터 추가
        self.random_choice = 0  # 랜덤 선택 값을 저장할 인스턴스 변수

    def create_message(self, content_type: str, content_text: str, task: str, from_agent: str, next_agent: str) -> dict:
        """템플릿을 사용해 새로운 메시지 생성"""
        current_time = time.perf_counter()
        
        # 템플릿 복사 후 값 설정
        message = self.MESSAGE_TEMPLATE.copy()
        message["metadata"] = {
            "interview_id": self.session_id,
            "step": self.step_counter // 3,
            "task": task,
            "from_agent": from_agent,
            "next_agent": next_agent
        }
        message["content"] = {
            "type": content_type,
            "content": content_text
        }
        message["metrics"] = {
            "total_time": current_time - self.start_time,
            "duration": current_time - self.start_time,
            "answer_seq": self.step_counter % 3
        }
        self.step_counter += 1
        return message

    # orchestrator가 전달받은 메시지를 처리하는 메서드
    def handle_message(self, message: dict) -> dict:
        new_msg = self._decide_next_agent(message)
        ## new_msg에 따라 다음 에이전트에게 전달
        pass
    
    # 다음 에이전트를 결정하는 메서드
    def _decide_next_agent(self, msg):
        next_agent = ['user', 'candidate']
        question_type = self._decide_next_type()
        
        if msg["metrics"]["answer_seq"] == 0:
            # 첫 번째: 면접관이 질문 생성
            self.random_choice = self.random_select()  # 인스턴스 변수로 저장
            return self.send_to_interviewer(msg["content"]["content"], question_type)
        elif msg["metrics"]["answer_seq"] == 1:
            # 두 번째: 랜덤 선택된 에이전트가 답변
            selected_agent = next_agent[0] if self.random_choice == -1 else next_agent[1]
            return self.send_to_candidate(msg["content"]["content"], question_type, selected_agent)
        elif msg["metrics"]["answer_seq"] == 2:
            # 세 번째: 반대 에이전트가 답변
            selected_agent = next_agent[1] if self.random_choice == -1 else next_agent[0]
            return self.send_to_candidate(msg["content"]["content"], question_type, selected_agent)

    # 면접관한테 전달할 메시지를 생성하는 메서드
    def send_to_interviewer(self, content_text: str, content_type: str = "HR") -> dict:
        return self.create_message(
            content_type=content_type,
            content_text=content_text,
            task="generate_question",
            from_agent="orchestrator",
            next_agent="interviewer"
        )

    # AI 지원자한테 전달할 메시지를 생성하는 메서드
    def send_to_candidate(self, content_text: str, content_type: str, next_agent: str) -> dict:
        return self.create_message(
            content_type=content_type,
            content_text=content_text,
            task="generate_answer",
            from_agent="orchestrator",
            next_agent=next_agent
        )

    # 질문 타입 정하기
    def _decide_next_type(self):
        if self.step_counter // 3 == 0:
            return "자기소개"
        elif self.step_counter // 3 == 1:
            return "지원동기"
        else:
            return "기타 질문"

    # 사용자와 질문자 중 랜덤으로 선택하는 메서드
    def random_select(self):
        import random
        return random.choice([-1, 1])
