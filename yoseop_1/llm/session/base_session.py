#!/usr/bin/env python3
"""
기본 면접 세션 관리자
기존 llm/core/interview_system.py의 FinalInterviewSystem 기능을 담당
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import InterviewSession, SessionState
from ..shared.models import QuestionAnswer, QuestionType
from ..shared.company_data_loader import get_company_loader


class BaseInterviewSession:
    """
    기본 면접 세션 관리자
    기존 FinalInterviewSystem의 핵심 기능을 담당
    """
    
    def __init__(self):
        self.sessions: Dict[str, InterviewSession] = {}
        self.company_loader = get_company_loader()
        
    def get_company_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사 데이터 조회"""
        return self.company_loader.get_company_data(company_id)
    
    def list_companies(self) -> List[Dict[str, str]]:
        """지원 가능한 회사 목록 반환"""
        return self.company_loader.get_company_list()
    
    def start_interview(self, company_id: str, position: str, candidate_name: str) -> str:
        """면접 시작"""
        company_data = self.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        session = InterviewSession(company_id, position, candidate_name)
        session.start_session()
        self.sessions[session.session_id] = session
        
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """세션 조회"""
        return self.sessions.get(session_id)
    
    def submit_answer(self, session_id: str, answer_content: str) -> Dict[str, Any]:
        """답변 제출"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
        
        if session.state != SessionState.ACTIVE:
            raise ValueError(f"활성화된 세션이 아닙니다: {session.state}")
        
        # 현재 질문이 없으면 오류
        if not session.conversation_history:
            raise ValueError("현재 진행 중인 질문이 없습니다")
        
        # 마지막 질문에 답변 추가
        last_qa = session.conversation_history[-1]
        last_qa.answer_content = answer_content
        last_qa.timestamp = datetime.now()
        
        # 세션 완료 확인
        if session.is_complete():
            session.complete_session()
        
        return {
            "session_id": session_id,
            "question_number": session.current_question_count,
            "total_questions": len(session.question_plan),
            "is_complete": session.is_complete(),
            "state": session.state.value
        }
    
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """다음 질문 가져오기"""
        session = self.get_session(session_id)
        if not session or session.is_complete():
            return None
        
        question_plan = session.get_next_question_plan()
        if not question_plan:
            return None
        
        # 기본 질문 생성 (실제 질문 생성은 interviewer 모듈에서 담당)
        question_type = question_plan["type"]
        
        if question_type == QuestionType.INTRO:
            question_content = f"{session.candidate_name}님, 자기소개를 부탁드립니다."
            question_intent = "지원자의 기본 정보와 성격, 역량을 파악"
        elif question_type == QuestionType.MOTIVATION:
            company_data = self.get_company_data(session.company_id)
            company_name = company_data.get('name', '회사') if company_data else '회사'
            question_content = f"저희 {company_name}에 지원하신 동기를 말씀해 주세요."
            question_intent = "회사에 대한 관심도와 지원 동기 파악"
        else:
            # 다른 질문들은 기본 템플릿
            question_content = f"{question_type.value} 관련 질문입니다."
            question_intent = f"{question_type.value} 역량 평가"
        
        # 질문-답변 쌍 생성 및 추가
        qa_pair = QuestionAnswer(
            question_id=f"q_{session.current_question_count + 1}",
            question_type=question_type,
            question_content=question_content,
            answer_content="",  # 아직 답변 없음
            timestamp=datetime.now(),
            question_intent=question_intent
        )
        
        session.add_qa_pair(qa_pair)
        
        return {
            "question_id": qa_pair.question_id,
            "question_type": question_type.value,
            "question_content": question_content,
            "question_intent": question_intent,
            "progress": f"{session.current_question_count}/{len(session.question_plan)}",
            "session_state": session.state.value
        }
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """세션 요약 정보"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session.session_id,
            "company_id": session.company_id,
            "position": session.position,
            "candidate_name": session.candidate_name,
            "state": session.state.value,
            "created_at": session.created_at.isoformat(),
            "total_questions": len(session.question_plan),
            "answered_questions": session.current_question_count,
            "conversation_history_count": len(session.conversation_history)
        }