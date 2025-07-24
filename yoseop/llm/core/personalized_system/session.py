#!/usr/bin/env python3
"""
개인화된 면접 세션 클래스
사용자 프로필을 기반으로 맞춤형 질문을 생성하는 세션
"""

from typing import Dict, List, Any
from ..interview_system import InterviewSession, QuestionAnswer, QuestionType
from ..document_processor import UserProfile
from ..conversation_context import ConversationContext
from .question_planner import QuestionPlanner

class PersonalizedInterviewSession(InterviewSession):
    """개인화된 면접 세션"""
    
    def __init__(self, company_id: str, position: str, candidate_name: str, user_profile: UserProfile):
        super().__init__(company_id, position, candidate_name)
        self.user_profile = user_profile
        
        # 대화 컨텍스트 관리자 초기화
        self.conversation_context = ConversationContext(
            company_id=company_id,
            position=position,
            persona_name=candidate_name
        )
        
        # 질문 계획 생성기
        self.question_planner = QuestionPlanner(user_profile)
        
        # 개인화된 질문 계획 (사용자 배경에 따라 동적 조정)
        self.question_plan = self.question_planner.create_personalized_plan()
    
    def add_qa_pair(self, qa_pair: QuestionAnswer):
        """질문-답변 쌍 추가 (컨텍스트 추적 포함)"""
        super().add_qa_pair(qa_pair)
        
        # 대화 컨텍스트에 질문-답변 추가
        if hasattr(self, 'conversation_context'):
            self.conversation_context.add_question_answer(
                qa_pair.question_content,
                qa_pair.answer_content,
                qa_pair.question_type
            )