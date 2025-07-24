"""
답변 평가 모델
"""
import json
from typing import Dict, Any
from ..base_model import BaseLLMModel
from ...core.interview_system import QuestionAnswer

class AnswerEvaluator(BaseLLMModel):
    """답변 평가자"""
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """BaseLLMModel 추상 메서드 구현"""
        return await self._call_llm(prompt, "당신은 면접 평가 전문가입니다.", **kwargs)
    
    async def evaluate_answer(self, qa_pair: QuestionAnswer, company_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """개별 답변 평가"""
        answer = qa_pair.answer_content.strip()
        
        # 기본 검증
        if len(answer) < 5:
            return {
                "score": 10,
                "feedback": f"📝 질문 의도: {qa_pair.question_intent}\n\n💬 평가: 답변이 너무 짧습니다.\n\n🔧 개선 방법: 구체적인 경험이나 생각을 3-4문장으로 설명해 주세요."
            }
        
        prompt = f"""
다음 면접 질문과 답변을 평가해주세요.

=== 질문 정보 ===
질문 유형: {qa_pair.question_type.value}
질문: {qa_pair.question_content}
질문 의도: {qa_pair.question_intent}

=== 지원자 답변 ===
{answer}

=== 평가 기준 ===
- 0-20점: 부적절하거나 성의없는 답변
- 21-40점: 기본적이지만 구체성 부족
- 41-60점: 적절하지만 평범함
- 61-80점: 구체적이고 좋은 답변
- 81-100점: 탁월하고 인상적인 답변

JSON 형식으로 응답:
{{
  "score": 점수,
  "feedback": "📝 질문 의도: {qa_pair.question_intent}\\n\\n💬 평가: 구체적인 평가 내용\\n\\n🔧 개선 방법: 실질적이고 구체적인 개선 제안"
}}
"""
        
        try:
            response = await self._call_llm(prompt, "당신은 면접 평가 전문가입니다.")
            
            # JSON 파싱
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                evaluation = json.loads(json_str)
                return evaluation
            else:
                raise ValueError("JSON 형식을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"답변 평가 오류: {str(e)}")
            # 기본 평가
            score = 25 if len(answer) < 30 else 45 if len(answer) < 100 else 55
            return {
                "score": score,
                "feedback": f"📝 질문 의도: {qa_pair.question_intent}\n\n💬 평가: 기본 평가가 적용되었습니다.\n\n🔧 개선 방법: 더 구체적이고 상세한 답변을 제공해 주세요."
            }