#!/usr/bin/env python3
"""
설정 관리 모듈
환경변수 및 애플리케이션 설정을 중앙에서 관리
"""

import os
from dotenv import load_dotenv
from typing import Optional

# .env 파일 로드
load_dotenv()

class Config:
    """기본 설정 클래스"""
    
    # OpenAI API 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4o")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "800"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # 서버 설정
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "8888"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "16777216"))  # 16MB
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS: set = {'txt', 'pdf', 'docx', 'doc'}
    
    # 면접 시스템 설정
    DEFAULT_TOTAL_QUESTIONS: int = int(os.getenv("DEFAULT_TOTAL_QUESTIONS", "20"))
    QUESTION_SIMILARITY_THRESHOLD: float = float(os.getenv("QUESTION_SIMILARITY_THRESHOLD", "0.5"))
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/server.log")
    
    # 세션 설정
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1시간
    
    # 성능 설정
    API_RETRY_COUNT: int = int(os.getenv("API_RETRY_COUNT", "3"))
    API_RETRY_DELAY: float = float(os.getenv("API_RETRY_DELAY", "1.0"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # 개발/테스트 설정
    DEVELOPMENT_MODE: bool = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"
    MOCK_API_RESPONSES: bool = os.getenv("MOCK_API_RESPONSES", "False").lower() == "true"
    
    # 지원 기업 목록
    SUPPORTED_COMPANIES: list = [
        'naver', 'kakao', 'line', 'coupang', 
        'baemin', 'danggeun', 'toss'
    ]
    
    # 질문 타입 매핑
    QUESTION_TYPE_MAPPING: dict = {
        'hr': 'hr_questions',
        'technical': 'technical_questions',
        'collaboration': 'collaboration_questions'
    }
    
    # 경력 단계 구분
    CAREER_LEVELS: dict = {
        'ENTRY': {'min': 0, 'max': 0, 'label': '신입'},
        'JUNIOR': {'min': 1, 'max': 3, 'label': '주니어'},
        'SENIOR': {'min': 4, 'max': float('inf'), 'label': '시니어'}
    }
    
    @classmethod
    def validate_config(cls) -> bool:
        """설정 유효성 검사"""
        if not cls.OPENAI_API_KEY:
            print("⚠️  WARNING: OPENAI_API_KEY가 설정되지 않았습니다.")
            return False
        
        if not os.path.exists(cls.UPLOAD_FOLDER):
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            print(f"📁 업로드 폴더 생성: {cls.UPLOAD_FOLDER}")
        
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"📁 로그 폴더 생성: {log_dir}")
        
        return True
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """설정 요약 정보 반환"""
        return {
            "server": {
                "host": cls.FLASK_HOST,
                "port": cls.FLASK_PORT,
                "debug": cls.FLASK_DEBUG
            },
            "ai": {
                "model": cls.GPT_MODEL,
                "max_tokens": cls.MAX_TOKENS,
                "temperature": cls.TEMPERATURE
            },
            "limits": {
                "max_file_size": f"{cls.MAX_FILE_SIZE / (1024*1024):.1f}MB",
                "total_questions": cls.DEFAULT_TOTAL_QUESTIONS,
                "session_timeout": f"{cls.SESSION_TIMEOUT / 60:.0f}분"
            },
            "features": {
                "development_mode": cls.DEVELOPMENT_MODE,
                "mock_api": cls.MOCK_API_RESPONSES,
                "supported_companies": len(cls.SUPPORTED_COMPANIES)
            }
        }

class DevelopmentConfig(Config):
    """개발 환경 설정"""
    FLASK_DEBUG = True
    LOG_LEVEL = "DEBUG"
    DEVELOPMENT_MODE = True
    
class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    FLASK_DEBUG = False
    LOG_LEVEL = "INFO"
    DEVELOPMENT_MODE = False
    
    # 프로덕션 보안 설정
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    def __init__(self):
        super().__init__()
        # 더 강력한 비밀키 요구 (인스턴스 생성 시 검증)
        if not self.SECRET_KEY or self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError("프로덕션 환경에서는 강력한 SECRET_KEY가 필요합니다.")

class TestingConfig(Config):
    """테스트 환경 설정"""
    FLASK_DEBUG = True
    MOCK_API_RESPONSES = True
    DEVELOPMENT_MODE = True
    UPLOAD_FOLDER = "test_uploads"
    LOG_LEVEL = "DEBUG"

# 환경에 따른 설정 선택
def get_config():
    """환경 변수에 따라 적절한 설정 클래스 반환"""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()

# 기본 설정 인스턴스
config = get_config()

# 설정 검증
if not config.validate_config():
    print("⚠️  설정 검증 실패. 일부 기능이 제한될 수 있습니다.")