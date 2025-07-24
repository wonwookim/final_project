"""
AI 관련 서비스 - 새로운 모델 구조 활용
"""
import os
import sys
from typing import Dict, Any, Optional

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.models.candidate.base_candidate import BaseCandidate, AnswerResponse
from llm.models.evaluator.answer_evaluator import AnswerEvaluator
from llm.models.interviewer.hr_interviewer import HRInterviewer
from llm.models.interviewer.tech_interviewer import TechInterviewer
from llm.core.interview_system import QuestionType, QuestionAnswer
from llm.core.answer_quality_controller import QualityLevel
from llm.core.logging_config import interview_logger

class AIService:
    """AI 관련 통합 서비스"""
    
    def __init__(self):
        self.candidates = {}  # 회사별 AI 지원자 캐시
        self.evaluator = AnswerEvaluator()
        self.interviewers = {}  # 면접관 캐시
    
    def get_ai_candidate(self, company_id: str) -> BaseCandidate:
        """회사별 AI 지원자 가져오기"""
        if company_id not in self.candidates:
            self.candidates[company_id] = BaseCandidate(company_id=company_id)
        return self.candidates[company_id]
    
    async def generate_ai_answer(self, 
                               company_id: str,
                               question: str,
                               question_type: QuestionType,
                               position: str,
                               quality_level: QualityLevel = QualityLevel.GOOD) -> AnswerResponse:
        """AI 답변 생성"""
        try:
            candidate = self.get_ai_candidate(company_id)
            return await candidate.generate_answer(
                question=question,
                question_type=question_type,
                company_id=company_id,
                position=position,
                quality_level=quality_level
            )
        except Exception as e:
            interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
            # 폴백 응답
            return AnswerResponse(
                answer_content="죄송합니다. 시스템 문제로 답변을 생성할 수 없습니다.",
                quality_level=QualityLevel.POOR,
                llm_provider=candidate.provider,
                persona_name="춘식이",
                confidence_score=0.0,
                error=str(e)
            )
    
    async def evaluate_answer(self, qa_pair: QuestionAnswer, company_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """답변 평가"""
        try:
            return await self.evaluator.evaluate_answer(qa_pair, company_data)
        except Exception as e:
            interview_logger.error(f"답변 평가 오류: {str(e)}")
            return {
                "score": 50,
                "feedback": "시스템 오류로 기본 평가가 적용되었습니다."
            }
    
    def get_interviewer(self, question_type: QuestionType, company_data: Dict[str, Any]):
        """질문 유형별 면접관 가져오기"""
        interviewer_key = f"{question_type.value}_{company_data.get('id', 'default')}"
        
        if interviewer_key not in self.interviewers:
            if question_type in [QuestionType.HR, QuestionType.INTRO, QuestionType.MOTIVATION]:
                self.interviewers[interviewer_key] = HRInterviewer(company_data)
            elif question_type == QuestionType.TECH:
                self.interviewers[interviewer_key] = TechInterviewer(company_data)
            else:
                # 기본적으로 HR 면접관 사용
                self.interviewers[interviewer_key] = HRInterviewer(company_data)
        
        return self.interviewers[interviewer_key]
    
    async def generate_question(self, 
                              question_type: QuestionType,
                              context: str,
                              candidate_name: str,
                              company_data: Dict[str, Any]) -> tuple[str, str]:
        """질문 생성"""
        try:
            interviewer = self.get_interviewer(question_type, company_data)
            return await interviewer.generate_question(question_type, context, candidate_name)
        except Exception as e:
            interview_logger.error(f"질문 생성 오류: {str(e)}")
            # 폴백 질문
            return f"{candidate_name}님에 대해 더 알고 싶습니다.", f"{question_type.value} 기본 질문"