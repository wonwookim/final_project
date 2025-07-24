"""
면접 서비스 - 비즈니스 로직 통합
"""
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.core.personalized_system.system import PersonalizedInterviewSystem
from llm.core.document_processor import DocumentProcessor, UserProfile
from llm.models.candidate.base_candidate import BaseCandidate
from .ai_service import AIService
from llm.core.logging_config import interview_logger

# 회사 이름 매핑
COMPANY_NAME_MAP = {
    "네이버": "naver", "카카오": "kakao", "라인": "line", "쿠팡": "coupang",
    "배달의민족": "baemin", "당근마켓": "daangn", "토스": "toss"
}

class InterviewService:
    """면접 관련 비즈니스 로직 통합 서비스"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.personalized_system = PersonalizedInterviewSystem()
        self.ai_service = AIService()
    
    def get_company_id(self, company_name: str) -> str:
        """회사 이름을 ID로 변환"""
        return COMPANY_NAME_MAP.get(company_name, company_name.lower())
    
    async def start_interview(self, company: str, position: str, candidate_name: str, documents: Optional[List[str]] = None) -> str:
        """면접 시작"""
        company_id = self.get_company_id(company)
        
        # 프로필 생성
        if documents:
            profile = await self._generate_personalized_profile(documents)
        else:
            profile = self._create_default_profile(candidate_name)
        
        # 면접 세션 시작
        session_id = self.personalized_system.start_personalized_interview(
            company_id=company_id,
            position=position,
            candidate_name=candidate_name,
            user_profile=profile
        )
        
        interview_logger.info(f"면접 시작 - 세션 ID: {session_id}")
        return session_id
    
    async def get_next_question(self, session_id: str) -> Optional[Dict]:
        """다음 질문 가져오기"""
        question_data = self.personalized_system.get_next_question(session_id)
        if not question_data:
            return None
            
        # 진행률 계산
        session = self.personalized_system.get_session(session_id)
        if session:
            current_index = len(session.conversation_history)
            total_questions = len(session.question_plan)
            progress = (current_index / total_questions) * 100 if total_questions > 0 else 0
        else:
            current_index = 0
            total_questions = 10
            progress = 0
        
        return {
            "question": {
                "id": question_data["question_id"],
                "question": question_data["question_content"],
                "category": question_data["question_type"],
                "time_limit": question_data.get("time_limit", 120),
                "keywords": question_data.get("keywords", [])
            },
            "question_index": current_index,
            "total_questions": total_questions,
            "progress": progress
        }
    
    async def submit_answer(self, session_id: str, answer: str) -> Dict:
        """답변 제출"""
        result = self.personalized_system.submit_answer(session_id, answer)
        return {
            "status": result.get("status", "success"),
            "message": result.get("message", "답변이 성공적으로 제출되었습니다."),
            "question": result.get("question"),
            "answered_count": result.get("answered_count", 0),
            "total_questions": result.get("total_questions", 0)
        }
    
    def _create_default_profile(self, candidate_name: str) -> UserProfile:
        """기본 프로필 생성"""
        return UserProfile(
            name=candidate_name,
            background={"career_years": "1", "current_position": "신입"},
            technical_skills=[],
            projects=[],
            experiences=[],
            strengths=["학습능력", "열정"],
            keywords=["신입", "개발"],
            career_goal="전문 개발자로 성장",
            unique_points=["빠른 적응력"]
        )
    
    async def _generate_personalized_profile(self, documents: List[str]) -> UserProfile:
        """문서 기반 개인화 프로필 생성"""
        # 문서 처리 로직 (기존과 동일)
        for doc_path in documents:
            if os.path.exists(doc_path):
                return await self.document_processor.process_document(doc_path)
        
        # 기본 프로필 반환
        return self._create_default_profile("지원자")