#!/usr/bin/env python3
"""
공용 데이터 모델
모든 모듈에서 사용하는 공통 데이터 클래스들
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 기존 llm.core.llm_manager의 enum들 import
from ..core.llm_manager import LLMProvider
from ..candidate.quality_controller import QualityLevel

class QuestionType(Enum):
    """질문 유형"""
    INTRO = "자기소개"
    MOTIVATION = "지원동기"
    MOTIVE = "동기"
    HR = "인사"
    TECH = "기술"
    COLLABORATION = "협업"
    FOLLOWUP = "심화"
    GENERAL = "일반"
    BASIC = "기본"
    FUTURE = "미래"

@dataclass
class QuestionAnswer:
    """질문-답변 쌍"""
    question_id: str
    question_type: QuestionType
    question_content: str
    answer_content: str
    timestamp: datetime
    question_intent: str = ""
    individual_score: int = 0
    individual_feedback: str = ""

@dataclass
class CandidatePersona:
    """지원자 페르소나 데이터 클래스"""
    company_id: str
    name: str
    background: Dict[str, Any]
    technical_skills: List[str]
    projects: List[Dict[str, Any]]
    experiences: List[Dict[str, Any]]
    strengths: List[str]
    achievements: List[str]
    career_goal: str
    personality_traits: List[str]
    interview_style: str
    success_factors: List[str]

@dataclass
class AnswerRequest:
    """답변 생성 요청"""
    question_content: str
    question_type: QuestionType
    question_intent: str
    company_id: str
    position: str
    quality_level: QualityLevel
    llm_provider: LLMProvider
    additional_context: Optional[str] = None

@dataclass
class AnswerResponse:
    """답변 생성 응답"""
    answer_content: str
    quality_level: QualityLevel
    llm_provider: LLMProvider
    persona_name: str
    confidence_score: float
    response_time: float
    reasoning: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

# 🆕 세션 관련 클래스들은 llm.session 모듈로 이동되었습니다.
# InterviewSession, ComparisonSession 등은 llm.session에서 import하여 사용하세요.

@dataclass
class AICandidatePersonaContext:
    """AI 지원자 페르소나 컨텍스트 (기존 AICandidateSession의 컨텍스트 기능만 분리)"""
    persona: CandidatePersona
    
    def get_persona_context(self) -> str:
        """페르소나 컨텍스트 구성"""
        context = f"""
=== AI 지원자 페르소나 정보 ===
이름: {self.persona.name}
경력: {self.persona.background.get('career_years', '0')}년
현재 직책: {self.persona.background.get('current_position', '지원자')}
주요 기술: {', '.join(self.persona.technical_skills[:5])}
강점: {', '.join(self.persona.strengths[:3])}
커리어 목표: {self.persona.career_goal}
성격 특성: {', '.join(self.persona.personality_traits)}
면접 스타일: {self.persona.interview_style}

=== 주요 프로젝트 ===
"""
        for i, project in enumerate(self.persona.projects[:2], 1):
            context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
            context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            if project.get('achievements'):
                context += f"   성과: {', '.join(project['achievements'])}\n"
        
        context += f"""
=== 업무 경험 ===
"""
        for i, exp in enumerate(self.persona.experiences[:2], 1):
            context += f"{i}. {exp.get('company', '회사')}: {exp.get('position', '직책')} ({exp.get('period', '기간')})\n"
            if exp.get('achievements'):
                context += f"   주요 성과: {', '.join(exp['achievements'])}\n"
        
        return context