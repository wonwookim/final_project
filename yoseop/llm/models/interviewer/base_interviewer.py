"""
면접관 기본 모델
"""
from typing import Dict, Any, List
from ..base_model import BaseLLMModel
from ...core.interview_system import QuestionType

class BaseInterviewer(BaseLLMModel):
    """면접관 기본 클래스"""
    
    def __init__(self, company_data: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.company_data = company_data
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """BaseLLMModel 추상 메서드 구현"""
        system_message = f"당신은 {self.company_data['name']}의 면접관입니다."
        return await self._call_llm(prompt, system_message, **kwargs)
    
    async def generate_question(self, 
                              question_type: QuestionType,
                              context: str,
                              candidate_name: str) -> tuple[str, str]:
        """질문 생성"""
        prompt = self._create_question_prompt(question_type, context, candidate_name)
        system_message = f"당신은 {self.company_data['name']}의 면접관입니다. 지원자를 존중하며 ~님으로 호칭하세요."
        
        response = await self._call_llm(prompt, system_message)
        
        if "의도:" in response:
            parts = response.split("의도:")
            question_content = parts[0].strip()
            question_intent = parts[1].strip() if len(parts) > 1 else ""
        else:
            question_content = response
            question_intent = f"{question_type.value} 역량 평가"
        
        return question_content, question_intent
    
    def _create_question_prompt(self, question_type: QuestionType, context: str, candidate_name: str) -> str:
        """질문 프롬프트 생성 (하위 클래스에서 오버라이드)"""
        return f"{candidate_name}님에 대한 {question_type.value} 질문을 생성해주세요."