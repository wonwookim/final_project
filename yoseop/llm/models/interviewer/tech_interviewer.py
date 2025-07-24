"""
기술 면접관 모델
"""
from typing import Dict, Any
from .base_interviewer import BaseInterviewer
from ...core.interview_system import QuestionType

class TechInterviewer(BaseInterviewer):
    """기술 면접관"""
    
    def _create_question_prompt(self, question_type: QuestionType, context: str, candidate_name: str) -> str:
        """기술 영역 질문 프롬프트"""
        return f"""
{context}

{candidate_name}님의 기술 역량을 평가하는 질문을 만들어주세요.

=== 기술 정보 ===
- 기술 중점: {', '.join(self.company_data['tech_focus'])}

구체적이고 실무 중심의 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""