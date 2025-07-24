"""
AI 면접 시스템 데이터베이스 모델 정의
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum

class InterviewMode(str, Enum):
    """면접 모드"""
    NORMAL = "normal"
    AI_COMPETITION = "ai_competition"
    GROUP = "group"
    VIDEO = "video"

class InterviewStatus(str, Enum):
    """면접 상태"""
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class QuestionType(str, Enum):
    """질문 유형"""
    INTRO = "INTRO"
    MOTIVATION = "MOTIVATION"
    HR = "HR"
    TECH = "TECH"
    COLLABORATION = "COLLABORATION"
    PROJECT = "PROJECT"
    CULTURE = "CULTURE"

class ParticipantType(str, Enum):
    """참여자 유형"""
    USER = "user"
    AI = "ai"

# ===================
# 사용자 관련 모델
# ===================

class User(BaseModel):
    """사용자 모델"""
    id: Optional[str] = None
    email: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 프로필 정보
    phone: Optional[str] = None
    birth_date: Optional[datetime] = None
    education: Optional[str] = None
    experience_years: Optional[int] = None
    
    # 선호 설정
    preferred_companies: Optional[List[str]] = None
    preferred_positions: Optional[List[str]] = None
    notification_enabled: bool = True

# ===================
# 면접 세션 관련 모델
# ===================

class InterviewSession(BaseModel):
    """면접 세션 모델"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    
    # 기본 정보
    company: str
    position: str
    mode: InterviewMode
    status: InterviewStatus = InterviewStatus.SETUP
    difficulty: str = "중간"
    
    # 메타데이터
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 설정 정보
    total_questions: int = 20
    current_question_index: int = 0
    time_limit: Optional[int] = None  # 분 단위
    
    # 결과 정보
    total_score: Optional[float] = None
    category_scores: Optional[Dict[str, float]] = None
    feedback: Optional[str] = None
    
    # AI 경쟁 모드 전용
    comparison_session_id: Optional[str] = None
    ai_session_id: Optional[str] = None
    ai_name: Optional[str] = "춘식이"

class ComparisonSession(BaseModel):
    """AI 경쟁 면접 세션 모델"""
    id: str
    user_session_id: str
    ai_session_id: str
    
    # 진행 상황
    current_question_index: int = 1
    current_phase: str = "user_turn"  # user_turn, ai_turn
    total_questions: int = 20
    
    # 참여자 정보
    user_name: str
    ai_name: str = "춘식이"
    starts_with_user: bool = True
    
    # 메타데이터
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 결과 비교
    user_total_score: Optional[float] = None
    ai_total_score: Optional[float] = None
    winner: Optional[str] = None

# ===================
# 질문 및 답변 모델
# ===================

class Question(BaseModel):
    """질문 모델"""
    id: Optional[str] = None
    session_id: str
    
    # 질문 내용
    question: str
    question_type: QuestionType
    question_intent: Optional[str] = None
    category: Optional[str] = None
    
    # 메타데이터
    question_index: int
    is_fixed: bool = False  # 고정 질문 여부
    created_at: Optional[datetime] = None
    
    # 난이도 및 설정
    difficulty_level: Optional[str] = None
    time_limit: Optional[int] = None  # 초 단위
    
    # 기업별 커스터마이징
    company_specific: Optional[Dict[str, Any]] = None

class Answer(BaseModel):
    """답변 모델"""
    id: Optional[str] = None
    session_id: str
    question_id: str
    
    # 답변 내용
    answer: str
    participant_type: ParticipantType
    participant_name: str
    
    # 시간 정보
    time_spent: int  # 초 단위
    submitted_at: Optional[datetime] = None
    
    # 평가 정보
    score: Optional[float] = None
    detailed_scores: Optional[Dict[str, float]] = None  # 세부 평가 항목별 점수
    feedback: Optional[str] = None
    
    # AI 관련 (AI 답변인 경우)
    ai_persona: Optional[str] = None
    quality_level: Optional[str] = None
    
    # 분석 데이터
    word_count: Optional[int] = None
    sentiment: Optional[str] = None
    keywords: Optional[List[str]] = None

# ===================
# 이력서 및 문서 모델
# ===================

class Resume(BaseModel):
    """이력서 모델"""
    id: Optional[str] = None
    user_id: str
    
    # 파일 정보
    filename: str
    file_path: str
    file_size: int
    file_type: str  # pdf, docx, txt
    
    # 분석 결과
    parsed_content: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    experience_summary: Optional[str] = None
    education_info: Optional[List[Dict[str, Any]]] = None
    
    # 메타데이터
    uploaded_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    is_active: bool = True

# ===================
# AI 후보자 모델
# ===================

class AICandidate(BaseModel):
    """AI 후보자 모델"""
    id: str
    name: str
    
    # 페르소나 정보
    persona_type: str  # junior, mid_level, senior
    personality: str  # confident, humble, analytical, etc.
    background: Dict[str, Any]
    
    # 성능 설정
    skill_level: str  # beginner, intermediate, advanced, expert
    answer_quality: str  # basic, good, excellent
    
    # 통계
    total_interviews: int = 0
    win_rate: Optional[float] = None
    average_score: Optional[float] = None
    
    # 메타데이터
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

# ===================
# 통계 및 분석 모델
# ===================

class InterviewStatistics(BaseModel):
    """면접 통계 모델"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    
    # 기간별 통계
    period_type: str  # daily, weekly, monthly, yearly
    period_start: datetime
    period_end: datetime
    
    # 면접 통계
    total_interviews: int = 0
    completed_interviews: int = 0
    ai_competition_count: int = 0
    
    # 성과 통계
    average_score: Optional[float] = None
    best_score: Optional[float] = None
    improvement_rate: Optional[float] = None
    
    # 카테고리별 통계
    category_performance: Optional[Dict[str, float]] = None
    
    # 기업별 통계
    company_performance: Optional[Dict[str, Dict[str, Any]]] = None
    
    # 메타데이터
    calculated_at: Optional[datetime] = None

# ===================
# 시스템 로그 모델
# ===================

class SystemLog(BaseModel):
    """시스템 로그 모델"""
    id: Optional[str] = None
    
    # 로그 기본 정보
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: str
    module: str
    function: Optional[str] = None
    
    # 컨텍스트 정보
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 상세 정보
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    # 메타데이터
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None