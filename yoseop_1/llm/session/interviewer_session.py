# llm/session/interviewer_session.py

import uuid
from typing import Dict, List, Any, Optional
from llm.interviewer.service import InterviewerService
from llm.candidate.model import CandidatePersona, AICandidateModel

class InterviewerSession:
    """
    InterviewerService를 기반으로 한 동적 턴제 면접의 상태를 관리하는 세션 클래스.
    """
    def __init__(self, company_id: str, position: str, user_name: str):
        self.session_id = f"interviewer_comp_{uuid.uuid4().hex[:8]}"
        self.company_id = company_id
        self.position = position
        self.user_name = user_name

        # 의존성 객체 초기화
        self.interviewer_service = InterviewerService(total_question_limit=15)
        self.ai_candidate_model = AICandidateModel()

        # 세션 상태
        self.user_resume: Dict[str, Any] = {'name': user_name, 'position': position}
        self.ai_persona: Optional[CandidatePersona] = None
        self.qa_history: List[Dict[str, Any]] = []
        self.last_question: Optional[Dict[str, Any]] = None

        # 턴 관리 상태
        self.user_answer: Optional[str] = None
        self.ai_answer: Optional[str] = None

    def start(self) -> Dict[str, Any]:
        """면접을 시작하고 첫 질문을 생성합니다."""
        self.ai_persona = self.ai_candidate_model.create_persona_for_interview(self.company_id, self.position)
        if not self.ai_persona:
            raise ValueError(f"AI 페르소나 생성에 실패했습니다: {self.company_id} - {self.position}")

        return self.get_next_question()

    def get_next_question(self) -> Dict[str, Any]:
        """다음 질문을 생성하고 세션 상태를 업데이트합니다."""
        next_question_data = self.interviewer_service.generate_next_question(
            user_resume=self.user_resume,
            chun_sik_persona=self.ai_persona,
            company_id=self.company_id,
            previous_qa_pairs=self.qa_history,
            user_answer=self.user_answer,
            chun_sik_answer=self.ai_answer
        )

        # 다음 턴을 위해 답변 초기화
        self.user_answer = None
        self.ai_answer = None

        if not next_question_data.get('is_final'):
            self.last_question = next_question_data
            self.qa_history.append({
                "question": next_question_data.get('question'),
                "interviewer": next_question_data.get('interviewer_type'),
                "user_answer": None,
                "ai_answer": None
            })

        return next_question_data

    def record_user_answer(self, answer: str):
        """사용자 답변을 기록합니다."""
        self.user_answer = answer
        if self.qa_history:
            self.qa_history[-1]['user_answer'] = answer

    def generate_and_record_ai_answer(self) -> str:
        """현재 질문에 대한 AI 답변을 생성하고 기록합니다."""
        from llm.shared.models import AnswerRequest, QuestionType, QualityLevel, LLMProvider

        if not self.last_question:
            raise ValueError("AI의 답변을 생성할 질문이 없습니다.")

        request = AnswerRequest(
            question_content=self.last_question['question'],
            question_type=QuestionType.from_str(self.last_question.get('interviewer_type', 'HR')),
            question_intent=self.last_question.get('intent', ''),
            company_id=self.company_id,
            position=self.position,
            quality_level=QualityLevel.GOOD,
            llm_provider=LLMProvider.OPENAI_GPT4O_MINI
        )

        response = self.ai_candidate_model.generate_answer(request, persona=self.ai_persona)
        if response.error:
            raise RuntimeError(f"AI 답변 생성 실패: {response.error}")

        self.ai_answer = response.answer_content
        if self.qa_history:
            self.qa_history[-1]['ai_answer'] = self.ai_answer

        return self.ai_answer

    def is_complete(self) -> bool:
        """면접이 종료되었는지 확인합니다."""
        return self.interviewer_service.questions_asked_count >= self.interviewer_service.total_question_limit