#!/usr/bin/env python3
"""
AI vs Human 비교 세션 관리자
기존 unified_interview_session.py 기능을 담당
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import ComparisonSession, SessionState, AnswerData
from ..shared.company_data_loader import get_company_loader


class ComparisonSessionManager:
    """
    AI vs Human 비교 세션 관리자
    기존 UnifiedInterviewSession 기능을 담당
    """
    
    def __init__(self):
        self.sessions: Dict[str, ComparisonSession] = {}
        self.company_loader = get_company_loader()
        
    def start_comparison_session(self, company_id: str, position: str, user_name: str, ai_name: str = "춘식이") -> str:
        """비교 세션 시작"""
        company_data = self.company_loader.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        comparison_id = f"comp_{uuid.uuid4().hex[:8]}"
        user_session_id = f"user_{uuid.uuid4().hex[:8]}"
        ai_session_id = f"ai_{uuid.uuid4().hex[:8]}"
        
        session = ComparisonSession(
            comparison_id=comparison_id,
            user_session_id=user_session_id,
            ai_session_id=ai_session_id,
            company_id=company_id,
            position=position,
            user_name=user_name,
            ai_name=ai_name,
            state=SessionState.ACTIVE
        )
        
        self.sessions[comparison_id] = session
        return comparison_id
    
    def get_session(self, comparison_id: str) -> Optional[ComparisonSession]:
        """비교 세션 조회"""
        return self.sessions.get(comparison_id)
    
    def submit_answer(self, comparison_id: str, answer_content: str, answer_type: str) -> Dict[str, Any]:
        """답변 제출 (user 또는 ai)"""
        session = self.get_session(comparison_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {comparison_id}")
        
        if session.state != SessionState.ACTIVE:
            raise ValueError(f"활성화된 세션이 아닙니다: {session.state}")
        
        # 답변 데이터 생성
        answer_data = AnswerData(
            question_id=f"q_{session.current_question_index + 1}",
            content=answer_content,
            time_spent=0,  # TODO: 실제 시간 측정
            timestamp=datetime.now(),
            answer_type=answer_type
        )
        
        # 답변 타입에 따라 저장
        if answer_type == "human":
            session.user_answers.append(answer_data)
        elif answer_type == "ai":
            session.ai_answers.append(answer_data)
        else:
            raise ValueError(f"잘못된 답변 타입: {answer_type}")
        
        # 턴 전환 또는 다음 질문으로 이동
        if len(session.user_answers) == len(session.ai_answers):
            # 둘 다 답변했으면 다음 질문으로
            session.next_question()
            session.current_phase = "user_turn"  # 기본적으로 사용자부터 시작
        else:
            # 한쪽만 답변했으면 턴 전환
            session.switch_phase()
        
        return {
            "comparison_id": comparison_id,
            "answer_type": answer_type,
            "current_phase": session.current_phase,
            "progress": session.get_progress(),
            "is_complete": session.is_complete()
        }
    
    def get_next_question(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """다음 질문 가져오기"""
        session = self.get_session(comparison_id)
        if not session or session.is_complete():
            return None
        
        # 현재 질문 번호 기반으로 질문 생성
        # (실제 질문 생성은 interviewer 모듈에서 담당)
        question_number = session.current_question_index + 1
        
        # 간단한 질문 템플릿
        question_templates = [
            "자기소개를 부탁드립니다.",
            f"저희 회사에 지원하신 동기를 말씀해 주세요.",
            "본인의 장점과 단점은 무엇인가요?",
            "지금까지의 경력에 대해 말씀해 주세요.",
            "기술적으로 도전적이었던 프로젝트가 있다면 소개해 주세요."
        ]
        
        question_content = question_templates[min(question_number - 1, len(question_templates) - 1)]
        
        return {
            "question_id": f"q_{question_number}",
            "question_number": question_number,
            "question_content": question_content,
            "current_phase": session.current_phase,
            "progress": session.get_progress(),
            "company_name": self.company_loader.get_company_data(session.company_id).get('name', '회사')
        }
    
    def switch_turn(self, comparison_id: str) -> Dict[str, Any]:
        """턴 수동 전환"""
        session = self.get_session(comparison_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {comparison_id}")
        
        session.switch_phase()
        
        return {
            "comparison_id": comparison_id,
            "current_phase": session.current_phase,
            "progress": session.get_progress()
        }
    
    def get_session_summary(self, comparison_id: str) -> Dict[str, Any]:
        """세션 요약 정보"""
        session = self.get_session(comparison_id)
        if not session:
            return {}
        
        return {
            "comparison_id": session.comparison_id,
            "user_session_id": session.user_session_id,
            "ai_session_id": session.ai_session_id,
            "company_id": session.company_id,
            "position": session.position,
            "user_name": session.user_name,
            "ai_name": session.ai_name,
            "state": session.state.value,
            "created_at": session.created_at.isoformat(),
            "progress": session.get_progress(),
            "user_answers_count": len(session.user_answers),
            "ai_answers_count": len(session.ai_answers)
        }
    
    def get_comparison_results(self, comparison_id: str) -> Dict[str, Any]:
        """비교 결과 생성"""
        session = self.get_session(comparison_id)
        if not session or not session.is_complete():
            return {}
        
        return {
            "comparison_id": comparison_id,
            "user_performance": {
                "name": session.user_name,
                "total_answers": len(session.user_answers),
                "average_score": sum(a.score for a in session.user_answers if a.score) / len(session.user_answers) if session.user_answers else 0
            },
            "ai_performance": {
                "name": session.ai_name,
                "total_answers": len(session.ai_answers),
                "average_score": sum(a.score for a in session.ai_answers if a.score) / len(session.ai_answers) if session.ai_answers else 0
            },
            "completed_at": datetime.now().isoformat()
        }