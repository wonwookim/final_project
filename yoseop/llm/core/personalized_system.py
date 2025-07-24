#!/usr/bin/env python3
"""
개인화된 면접 시스템 - 새로운 모듈 구조
기존 995줄 파일을 4개 모듈로 분리하여 재구성
"""

# 새로운 모듈 구조에서 메인 클래스들을 가져옴
from .personalized_system import (
    PersonalizedInterviewSession,
    QuestionPlanner,
    QuestionGenerator, 
    PersonalizedInterviewSystem
)

# 하위 호환성을 위해 기존 import 유지
__all__ = [
    'PersonalizedInterviewSession',
    'PersonalizedInterviewSystem'
]