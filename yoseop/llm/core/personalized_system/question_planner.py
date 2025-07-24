#!/usr/bin/env python3
"""
질문 계획 생성기
사용자 프로필에 따른 개인화된 질문 계획을 생성
"""

from typing import Dict, List, Any
from ..interview_system import QuestionType
from ..document_processor import UserProfile
from ..utils import parse_career_years

class QuestionPlanner:
    """질문 계획 생성기"""
    
    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
    
    def create_personalized_plan(self) -> List[Dict[str, Any]]:
        """사용자 프로필에 따른 개인화된 질문 계획"""
        
        # 기본 질문 (모든 면접자 공통)
        base_plan = [
            {"type": QuestionType.INTRO, "focus": "self_introduction", "personalized": False, "fixed": True},
            {"type": QuestionType.MOTIVATION, "focus": "application_reason", "personalized": False, "fixed": True}
        ]
        
        # 경력 년수 파싱
        career_years_str = self.user_profile.background.get("career_years", "0")
        career_years = parse_career_years(career_years_str)
        
        if career_years >= 3:  # 경력자 (총 18개 질문)
            additional_questions = self._create_senior_plan()
        elif career_years >= 1:  # 주니어 (총 16개 질문)
            additional_questions = self._create_junior_plan()
        else:  # 신입 (총 13개 질문)
            additional_questions = self._create_entry_plan()
        
        return base_plan + additional_questions
    
    def _create_senior_plan(self) -> List[Dict[str, Any]]:
        """경력자용 질문 계획"""
        return [
            # 인사 영역 (2개 고정 + 2개 생성)
            {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "growth_mindset", "personalized": True, "fixed": False},
            {"type": QuestionType.HR, "focus": "leadership_style", "personalized": True, "fixed": False},
            
            # 기술 영역 (2개 고정 + 3개 생성)
            {"type": QuestionType.TECH, "focus": "expertise", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "architecture", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "problem_solving", "personalized": True, "fixed": False},
            {"type": QuestionType.TECH, "focus": "innovation", "personalized": True, "fixed": False},
            {"type": QuestionType.TECH, "focus": "learning", "personalized": True, "fixed": False},
            
            # 협업 영역 (1개 고정 + 2개 생성)
            {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
            {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": True, "fixed": False},
            {"type": QuestionType.COLLABORATION, "focus": "conflict_resolution", "personalized": True, "fixed": False},
            
            # 심화 질문 (3개 생성)
            {"type": QuestionType.FOLLOWUP, "focus": "career", "personalized": True, "fixed": False},
            {"type": QuestionType.FOLLOWUP, "focus": "future_goals", "personalized": True, "fixed": False},
            {"type": QuestionType.FOLLOWUP, "focus": "company_contribution", "personalized": True, "fixed": False}
        ]
    
    def _create_junior_plan(self) -> List[Dict[str, Any]]:
        """주니어용 질문 계획"""
        return [
            # 인사 영역 (2개 고정 + 2개 생성)
            {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "growth", "personalized": True, "fixed": False},
            {"type": QuestionType.HR, "focus": "adaptability", "personalized": True, "fixed": False},
            
            # 기술 영역 (2개 고정 + 3개 생성)
            {"type": QuestionType.TECH, "focus": "skills", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "recent_learning", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "problem_solving", "personalized": True, "fixed": False},
            {"type": QuestionType.TECH, "focus": "technical_depth", "personalized": True, "fixed": False},
            {"type": QuestionType.TECH, "focus": "learning_ability", "personalized": True, "fixed": False},
            
            # 협업 영역 (2개 고정 + 2개 생성)
            {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
            {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": False, "fixed": True, "section": "collaboration"},
            {"type": QuestionType.COLLABORATION, "focus": "team_contribution", "personalized": True, "fixed": False},
            {"type": QuestionType.COLLABORATION, "focus": "peer_learning", "personalized": True, "fixed": False},
            
            # 심화 질문 (1개 생성)
            {"type": QuestionType.FOLLOWUP, "focus": "career_growth", "personalized": True, "fixed": False}
        ]
    
    def _create_entry_plan(self) -> List[Dict[str, Any]]:
        """신입용 질문 계획"""
        return [
            # 인사 영역 (2개 고정 + 2개 생성)
            {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
            {"type": QuestionType.HR, "focus": "potential", "personalized": True, "fixed": False},
            {"type": QuestionType.HR, "focus": "enthusiasm", "personalized": True, "fixed": False},
            
            # 기술 영역 (2개 고정 + 2개 생성)
            {"type": QuestionType.TECH, "focus": "fundamentals", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "learning", "personalized": False, "fixed": True, "section": "technical"},
            {"type": QuestionType.TECH, "focus": "project_experience", "personalized": True, "fixed": False},
            {"type": QuestionType.TECH, "focus": "passion", "personalized": True, "fixed": False},
            
            # 협업 영역 (1개 고정 + 2개 생성)
            {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
            {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": True, "fixed": False},
            {"type": QuestionType.COLLABORATION, "focus": "willingness_to_learn", "personalized": True, "fixed": False},
            
            # 심화 질문 (1개 생성)
            {"type": QuestionType.FOLLOWUP, "focus": "growth_mindset", "personalized": True, "fixed": False}
        ]