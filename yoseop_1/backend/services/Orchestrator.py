import time
import json
import random
import asyncio
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
    def __init__(self, session_id: str, session_state: Dict[str, Any], 
                 question_generator=None, ai_candidate_model=None):
        """
        Orchestrator: 모든 면접 비즈니스 로직 담당
        - 플로우 제어
        - 에이전트 조율
        - 메시지 처리
        - 상태 업데이트
        """
        self.session_id = session_id
        self.session_state = session_state  # InterviewService의 session_state 참조
        self.question_generator = question_generator
        self.ai_candidate_model = ai_candidate_model

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지를 받아서 상태를 업데이트하고 다음 액션을 결정"""
        from_agent = message.get("metadata", {}).get("from_agent", "unknown")
        print(f"[{from_agent}] -> [Orchestrator]")
        print(json.dumps(message, indent=2, ensure_ascii=False))

        task = message.get("metadata", {}).get("task")
        content = message.get("content", {}).get("content")

        # 상태 업데이트
        self._update_state_from_message(task, content, from_agent)

        # 다음 메시지 결정
        next_message = self._decide_next_message()
        next_agent = next_message.get("metadata", {}).get("next_agent", "unknown")
        print(f"[Orchestrator] -> [{next_agent}]")
        print(json.dumps(next_message, indent=2, ensure_ascii=False))
        return next_message

    def _update_state_from_message(self, task: str, content: str, from_agent: str) -> None:
        """메시지로부터 세션 상태 업데이트"""
        if task == "question_generated":
            self.session_state['current_question'] = content
            self.session_state['answer_seq'] = 1
            self.session_state['who_answers_first'] = 'user' if self.session_state['turn_count'] % 2 == 0 else 'ai'
            
        elif task == "answer_generated":
            self.session_state['qa_history'].append({
                "question": self.session_state['current_question'],
                "answerer": from_agent,
                "answer": content
            })
            
            if self.session_state['answer_seq'] == 1:
                self.session_state['answer_seq'] = 2
            else:
                self.session_state['answer_seq'] = 0
                self.session_state['turn_count'] += 1
                self.session_state['current_question'] = None

    def _decide_next_message(self) -> Dict[str, Any]:
        """다음 메시지 결정 - 실제 플로우 제어 로직"""
        next_agent_options = ['user', 'ai']

        # 완료 조건 체크
        if self.session_state['turn_count'] >= self.session_state.get('total_question_limit', 15):
            self.session_state['is_completed'] = True
            return self.create_message("면접이 종료되었습니다.", "end_interview", "system")

        # answer_seq에 따른 다음 액션 결정
        if self.session_state['answer_seq'] == 0:
            # 첫 번째: 면접관이 질문 생성
            self.session_state['random_choice'] = self._random_select()
            return self.create_message("다음 질문을 생성해주세요.", "generate_question", "interviewer")
        
        elif self.session_state['answer_seq'] == 1:
            # 두 번째: 랜덤 선택된 에이전트가 답변
            selected_agent = next_agent_options[0] if self.session_state['random_choice'] == -1 else next_agent_options[1]
            self.session_state['who_answers_first'] = selected_agent
            return self.create_message(self.session_state['current_question'], "generate_answer", selected_agent)
            
        elif self.session_state['answer_seq'] == 2:
            # 세 번째: 반대 에이전트가 답변
            selected_agent = next_agent_options[1] if self.session_state['random_choice'] == -1 else next_agent_options[0]
            return self.create_message(self.session_state['current_question'], "generate_answer", selected_agent)

    def create_message(self, content_text: str, task: str, next_agent: str, content_type: str = "text") -> Dict[str, Any]:
        """메시지 생성"""
        current_time = time.perf_counter()
        return {
            "metadata": {
                "interview_id": self.session_id,
                "step": self.session_state['turn_count'],
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
                "total_time": current_time - self.session_state.get('start_time', current_time),
                "duration": 0,
                "answer_seq": self.session_state['answer_seq']
            }
        }

    def _random_select(self) -> int:
        """사용자와 AI 중 랜덤으로 선택"""
        return random.choice([-1, 1])

    # 에이전트 조율 메서드들 (내부 처리용)
    async def _request_question_from_interviewer(self) -> str:
        """면접관(QuestionGenerator)에게 질문 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            from llm.shared.logging_config import interview_logger
            interview_logger.info(f"📤 면접관에게 질문 생성 요청: {self.session_id}")
            
            # QuestionGenerator에게 상태 객체(state)를 전달하여 질문 생성
            question_data = await asyncio.to_thread(
                self.question_generator.generate_question_with_orchestrator_state,
                self.session_state
            )
            return question_data.get('question', '다음 질문이 무엇인가요?')
            
        except Exception as e:
            from llm.shared.logging_config import interview_logger
            interview_logger.error(f"면접관 질문 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 질문을 생성하는 데 문제가 발생했습니다."

    async def _request_answer_from_ai_candidate(self, question: str) -> str:
        """AI 지원자에게 답변 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            from llm.shared.logging_config import interview_logger
            interview_logger.info(f"📤 AI 지원자에게 답변 요청: {self.session_id}")
            
            ai_persona = self.session_state.get('ai_persona')
            
            # 답변 생성 요청 구성
            from llm.shared.models import AnswerRequest, QuestionType, LLMProvider
            from llm.candidate.quality_controller import QualityLevel
            
            answer_request = AnswerRequest(
                question_content=question,
                question_type=QuestionType.HR, # TODO: 질문 유형을 state에서 가져오도록 개선
                question_intent="면접관의 질문",
                company_id=self.session_state.get('company_id'),
                position=self.session_state.get('position'),
                quality_level=QualityLevel.AVERAGE,
                llm_provider=LLMProvider.OPENAI_GPT4O
            )
            
            response = await asyncio.to_thread(
                self.ai_candidate_model.generate_answer,
                request=answer_request,
                persona=ai_persona
            )
            return response.answer_content
            
        except Exception as e:
            from llm.shared.logging_config import interview_logger
            interview_logger.error(f"AI 지원자 답변 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 답변을 생성하는 데 문제가 발생했습니다."

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

    async def process_user_answer(self, user_answer: str, time_spent: float = None) -> Dict[str, Any]:
        """사용자 답변을 처리하고 전체 플로우를 완료하여 최종 결과 반환"""
        print(f"[Orchestrator] 🔄 사용자 답변 처리 시작: {self.session_id}")
        
        # 1. 사용자 답변 메시지 생성 및 처리
        user_message = self.create_agent_message(
            session_id=self.session_id,
            task="answer_generated",
            from_agent="user",
            content_text=user_answer,
            turn_count=self.session_state.get('turn_count', 0),
            duration=time_spent
        )
        
        # 2. 사용자 답변으로 상태 업데이트 (handle_message에서 JSON 출력됨)
        self.handle_message(user_message)
        
        # 3. 다음 액션 결정 및 전체 플로우 처리
        return await self._process_complete_flow()
    
    async def _process_complete_flow(self) -> Dict[str, Any]:
        """완전한 플로우를 처리하여 최종 결과 반환"""
        while True:
            # 다음 메시지 결정
            next_message = self._decide_next_message()
            next_agent = next_message.get("metadata", {}).get("next_agent")
            task = next_message.get("metadata", {}).get("task")
            
            # 완료 조건 체크
            if task == "end_interview":
                result = {
                    "status": "completed",
                    "message": "면접이 종료되었습니다.",
                    "qa_history": self.session_state.get('qa_history', []),
                    "session_id": self.session_id
                }
                print(f"[Orchestrator] -> [Client]")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # 사용자 입력 대기 상태인 경우
            if next_agent == "user":
                result = self.create_user_waiting_message()
                print(f"[Orchestrator] -> [Client]")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # 에이전트 작업 수행 (handle_message에서 JSON 출력됨)
            if next_agent == "interviewer":
                await self._process_interviewer_task()
            elif next_agent == "ai":
                await self._process_ai_task(next_message.get("content", {}).get("content"))
    
    async def _process_interviewer_task(self):
        """면접관 작업 처리"""
        print(f"[Orchestrator] -> [Interviewer] (질문 생성 요청)")
        
        question_content = await self._request_question_from_interviewer()
        
        question_message = self.create_agent_message(
            session_id=self.session_id,
            task="question_generated",
            from_agent="interviewer",
            content_text=question_content,
            turn_count=self.session_state.get('turn_count', 0)
        )
        
        # handle_message에서 JSON 출력됨
        self.handle_message(question_message)
    
    async def _process_ai_task(self, question: str):
        """AI 지원자 작업 처리"""
        print(f"[Orchestrator] -> [AI Candidate] (질문: {question[:50]}...)")
        
        ai_answer = await self._request_answer_from_ai_candidate(question)
        
        ai_message = self.create_agent_message(
            session_id=self.session_id,
            task="answer_generated",
            from_agent="ai",
            content_text=ai_answer,
            turn_count=self.session_state.get('turn_count', 0)
        )
        
        # handle_message에서 JSON 출력됨
        self.handle_message(ai_message)
    
    def create_user_waiting_message(self) -> Dict[str, Any]:
        """사용자 입력 대기 메시지 생성"""
        response = self.create_agent_message(
            session_id=self.session_id,
            task="wait_for_user_input",
            from_agent="orchestrator",
            content_text=self.session_state.get('current_question'),
            turn_count=self.session_state.get('turn_count', 0)
        )
        # next_agent를 'user'로 수정하여 프론트엔드가 올바르게 인식하도록 함
        response['metadata']['next_agent'] = 'user'
        response['status'] = 'waiting_for_user'
        response['message'] = '답변을 입력해주세요.'
        response['session_id'] = self.session_id
        
        # 턴 정보 추가
        response['turn_info'] = {
            'current_turn': self.session_state.get('turn_count', 0),
            'answer_seq': self.session_state.get('answer_seq', 0),
            'who_answers_first': self.session_state.get('who_answers_first', 'user'),
            'is_user_turn': True
        }
        
        return response
