#!/usr/bin/env python3
"""
개인화된 면접 시스템 메인 클래스
"""

import random
import os
from typing import Dict, List, Any, Optional, Tuple
import openai
from dotenv import load_dotenv

load_dotenv()

from ..interview_system import FinalInterviewSystem, QuestionType
from ..document_processor import DocumentProcessor, UserProfile
from ..constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE, QUESTION_SECTIONS
from ..utils import safe_json_load, extract_question_and_intent
from .session import PersonalizedInterviewSession

class PersonalizedInterviewSystem(FinalInterviewSystem):
    """개인화된 면접 시스템"""
    
    def __init__(self, api_key: str = None, companies_data_path: str = "llm/data/companies_data.json"):
        super().__init__(api_key, companies_data_path)
        self.document_processor = DocumentProcessor(api_key or os.getenv('OPENAI_API_KEY'))
        self.fixed_questions = self._load_fixed_questions()
        self.question_cache = {}  # 질문 캐시 추가
    
    def _load_fixed_questions(self) -> Dict[str, List[Dict]]:
        """고정 질문 데이터 로드"""
        default_structure = {
            "hr_questions": [], 
            "technical_questions": [], 
            "collaboration_questions": []
        }
        return safe_json_load("llm/data/fixed_questions.json", default_structure)
    
    def _get_fixed_question(self, section: str, difficulty_level: int = None) -> Optional[Dict]:
        """섹션별 고정 질문 캐시된 선택"""
        cache_key = f"{section}_{difficulty_level or 'all'}"
        
        # 캐시에서 먼저 확인
        if cache_key in self.question_cache:
            return self.question_cache[cache_key]
            
        questions = self.fixed_questions.get(QUESTION_SECTIONS.get(section, ""), [])
        if not questions:
            return None
            
        # 난이도별 필터링 (선택사항)
        if difficulty_level:
            filtered_questions = [q for q in questions if q.get("level", 1) == difficulty_level]
            questions = filtered_questions if filtered_questions else questions
        
        selected_question = random.choice(questions) if questions else None
        
        # 캐시에 저장 (간단한 캐싱)
        if selected_question:
            self.question_cache[cache_key] = selected_question
            
        return selected_question
    
    def _build_previous_answers_context(self, session: PersonalizedInterviewSession) -> str:
        """이전 답변에서 참고할 만한 내용 추출"""
        if not session.conversation_history:
            return ""
        
        context_parts = []
        for i, qa in enumerate(session.conversation_history[-3:]):  # 최근 3개 답변만
            if qa.answer_content and len(qa.answer_content.strip()) > 20:  # 의미있는 답변만
                context_parts.append(f"- {qa.question_content[:50]}... → {qa.answer_content[:100]}...")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def start_personalized_interview(self, company_id: str, position: str, candidate_name: str, 
                                   user_profile: UserProfile) -> str:
        """개인화된 면접 시작"""
        
        company_data = self.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        session = PersonalizedInterviewSession(company_id, position, candidate_name, user_profile)
        self.sessions[session.session_id] = session
        
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[PersonalizedInterviewSession]:
        """세션 가져오기"""
        return self.sessions.get(session_id)
    
    def get_current_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """현재 질문 가져오기"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # 현재 질문이 있으면 반환
        if session.conversation_history:
            last_qa = session.conversation_history[-1]
            return {
                "question_id": f"q_{len(session.conversation_history)}",
                "question_type": "current",
                "question_content": last_qa.question_content,
                "question_intent": last_qa.question_intent or "현재 질문",
                "progress": f"{len(session.conversation_history)}/{len(session.question_plan)}",
                "personalized": True
            }
        
        # 현재 질문이 없으면 첫 번째 질문 생성
        return self.get_next_question(session_id)