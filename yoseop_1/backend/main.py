#!/usr/bin/env python3
"""
FastAPI 기반 AI 면접 시스템
새로운 서비스 계층 구조 적용
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import sys
import json
from datetime import datetime
import uuid
from pathlib import Path
import time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 새로운 서비스 계층 사용
from backend.services.interview_service import InterviewService

# 기존 시스템 (필요 시 사용)
from llm.shared.config import config
from llm.shared.logging_config import interview_logger, performance_logger
from llm.shared.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE
from llm.shared.models import QuestionType, QuestionAnswer
from llm.candidate.quality_controller import QualityLevel
from llm.core.llm_manager import LLMProvider

# 데이터베이스 확장 임포트
try:
    from extensions.database_integration import database_router
    from extensions.migration_api import migration_router
    DATABASE_ENABLED = True
    print("✅ 데이터베이스 확장 로드 성공")
    print("✅ 마이그레이션 API 로드 성공")
except ImportError as e:
    DATABASE_ENABLED = False
    print(f"⚠️ 데이터베이스 확장 로드 실패: {e}")
    print("   메모리 기반 모드로 실행됩니다.")

# FastAPI 앱 초기화
app = FastAPI(
    title="Beta-GO Interview API",
    description="AI 기반 개인화된 면접 시스템",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서만 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 라우터 등록
if DATABASE_ENABLED:
    app.include_router(database_router)
    app.include_router(migration_router)
    print("✅ 데이터베이스 API 라우터 등록 완료")
    print("✅ 마이그레이션 API 라우터 등록 완료")

# 서비스 계층 사용
interview_service = InterviewService()

# Pydantic 모델 정의
class InterviewSettings(BaseModel):
    """면접 설정 모델"""
    company: str
    position: str
    mode: str
    difficulty: str = "중간"
    candidate_name: str
    documents: Optional[List[str]] = None

class QuestionRequest(BaseModel):
    """질문 요청 모델"""
    session_id: str
    question_index: int

class AnswerSubmission(BaseModel):
    """답변 제출 모델"""
    session_id: str
    question_id: str
    answer: str
    time_spent: int

class InterviewResult(BaseModel):
    """면접 결과 모델"""
    session_id: str
    total_score: int
    category_scores: Dict[str, int]
    detailed_feedback: List[Dict]
    recommendations: List[str]

class ComparisonAnswerSubmission(BaseModel):
    """비교 면접 답변 제출 모델"""
    comparison_session_id: str
    answer: str

class AITurnRequest(BaseModel):
    """AI 턴 처리 요청 모델"""
    comparison_session_id: str
    step: str = "question"  # "question" 또는 "answer"

# 의존성 주입
def get_interview_service():
    return interview_service

# API 엔드포인트

@app.get("/")
async def root():
    """루트 엔드포인트 - API 정보 반환"""
    return {
        "message": "Beta-GO Interview API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/api/interview/start")
async def start_interview(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 시작 - 서비스 계층 사용"""
    try:
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name,
            "documents": settings.documents
        }
        
        result = await service.start_interview(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/upload")
async def upload_document(
    file: UploadFile = File(...),
    service: InterviewService = Depends(get_interview_service)
):
    """문서 업로드 및 분석"""
    try:
        content = await file.read()
        file_data = {
            "filename": file.filename,
            "content": content
        }
        
        result = await service.upload_document(file_data)
        return result
        
    except Exception as e:
        interview_logger.error(f"문서 업로드 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/question")
async def get_next_question(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """다음 질문 가져오기 - 서비스 계층 사용"""
    try:
        result = await service.get_next_question(session_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"질문 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/answer")
async def submit_answer(
    answer_data: AnswerSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """답변 제출 - 서비스 계층 사용"""
    try:
        answer_dict = {
            "session_id": answer_data.session_id,
            "answer": answer_data.answer,
            "time_spent": answer_data.time_spent
        }
        
        result = await service.submit_answer(answer_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"답변 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/results/{session_id}")
async def get_interview_results(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 결과 조회"""
    try:
        result = await service.get_interview_results(session_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"결과 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# AI 경쟁 모드 엔드포인트

@app.post("/api/interview/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자와의 경쟁 면접 시작"""
    try:
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name
        }
        
        result = await service.start_ai_competition(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/ai-answer/{session_id}/{question_id}")
async def get_ai_answer(
    session_id: str,
    question_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자의 답변 생성"""
    try:
        result = await service.get_ai_answer(session_id, question_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/comparison/user-turn")
async def submit_comparison_user_turn(
    answer_data: ComparisonAnswerSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """비교 면접 사용자 턴 답변 제출"""
    try:
        answer_dict = {
            "comparison_session_id": answer_data.comparison_session_id,
            "answer": answer_data.answer
        }
        
        result = await service.submit_comparison_user_turn(answer_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"사용자 턴 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/comparison/ai-turn")
async def process_comparison_ai_turn(
    ai_turn_data: AITurnRequest,
    service: InterviewService = Depends(get_interview_service)
):
    """비교 면접 AI 턴 처리"""
    try:
        turn_dict = {
            "comparison_session_id": ai_turn_data.comparison_session_id,
            "step": ai_turn_data.step
        }
        
        result = await service.process_comparison_ai_turn(turn_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 턴 처리 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/history")
async def get_interview_history(
    user_id: Optional[str] = None,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 기록 조회"""
    try:
        result = await service.get_interview_history(user_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"기록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Beta-GO Interview FastAPI 시작!")
    print("📱 브라우저에서 http://localhost:8000 접속")
    print("📚 API 문서: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )