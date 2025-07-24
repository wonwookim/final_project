"""
인사 면접관 모델
"""
from typing import Dict, Any
from .base_interviewer import BaseInterviewer
from ...core.interview_system import QuestionType

class HRInterviewer(BaseInterviewer):
    """인사 면접관"""
    
    def _create_question_prompt(self, question_type: QuestionType, context: str, candidate_name: str) -> str:
        """인사 영역 질문 프롬프트"""
        return f"""
{context}

{candidate_name}님의 인사 영역(개인적 특성, 성격, 가치관, 성장 의지)을 평가하는 질문을 만들어주세요.

=== 기업 정보 ===
- 인재상: {self.company_data['talent_profile']}
- 핵심 역량: {', '.join(self.company_data['core_competencies'])}

협업과 구분되는 개인적 측면에 집중하세요.
간결한 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""