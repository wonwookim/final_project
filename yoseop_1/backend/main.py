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
    from routers.user import user_router
    from routers.resume import resume_router
    from routers.history import history_router
    from routers.auth import auth_router
    from routers.company import company_router
    from routers.posting import posting_router

    DATABASE_ENABLED = True
    print("데이터베이스 확장 로드 성공")
    print("마이그레이션 API 로드 성공")
    print("인증 라우터 로드 성공")
except ImportError as e:
    DATABASE_ENABLED = False
    print(f"데이터베이스 확장 로드 실패: {e}")
    print("메모리 기반 모드로 실행됩니다.")

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
    app.include_router(user_router)
    app.include_router(resume_router)
    app.include_router(history_router)
    app.include_router(auth_router)
    app.include_router(company_router)
    app.include_router(posting_router)
    print("데이터베이스 API 라우터 등록 완료")
    print("마이그레이션 API 라우터 등록 완료") 
    print("인증 API 라우터 등록 완료")

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
    posting_id: Optional[int] = None  # 🆕 채용공고 ID - 지정되면 실제 DB 데이터 사용
    use_interviewer_service: Optional[bool] = False  # 🎯 InterviewerService 사용 플래그

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
    
class CompetitionTurnSubmission(BaseModel):
    """경쟁 면접 통합 턴 제출 모델"""
    comparison_session_id: str
    answer: str
    
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

# 채용공고 관련 엔드포인트

@app.get("/api/postings")
async def get_all_postings():
    """모든 채용공고 조회 (회사, 직무 정보 포함)"""
    try:
        from database.services.existing_tables_service import existing_tables_service
        postings = await existing_tables_service.get_all_postings()
        
        # 실제 DB 구조에 맞게 단순화된 데이터 구조
        formatted_postings = []
        for posting in postings:
            formatted_posting = {
                "posting_id": posting.get("posting_id"),
                "company_id": posting.get("company_id"),
                "position_id": posting.get("position_id"),
                "company": posting.get("company", {}).get("name", "Unknown Company"),
                "position": posting.get("position", {}).get("position_name", "Unknown Position"),
                "content": posting.get("content", f"{posting.get('company', {}).get('name', '')} {posting.get('position', {}).get('position_name', '')} 채용공고")
            }
            formatted_postings.append(formatted_posting)
        
        interview_logger.info(f"📋 채용공고 {len(formatted_postings)}개 조회 완료")
        return {"postings": formatted_postings}
        
    except Exception as e:
        interview_logger.error(f"채용공고 조회 오류: {str(e)}")
        # Fallback: 더미 데이터 반환
        return {"postings": []}

@app.get("/api/postings/{posting_id}")
async def get_posting_by_id(posting_id: int):
    """특정 채용공고 상세 조회"""
    try:
        from database.services.existing_tables_service import existing_tables_service
        posting = await existing_tables_service.get_posting_by_id(posting_id)
        
        if not posting:
            raise HTTPException(status_code=404, detail="채용공고를 찾을 수 없습니다")
        
        formatted_posting = {
            "posting_id": posting.get("posting_id"),
            "company_id": posting.get("company_id"),
            "position_id": posting.get("position_id"),
            "company": posting.get("company", {}).get("name", "Unknown Company"),
            "position": posting.get("position", {}).get("position_name", "Unknown Position"),
            "content": posting.get("content", f"{posting.get('company', {}).get('name', '')} {posting.get('position', {}).get('position_name', '')} 상세 채용공고")
        }
        
        interview_logger.info(f"📋 채용공고 상세 조회: posting_id={posting_id}")
        return formatted_posting
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"채용공고 상세 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# AI 경쟁 모드 엔드포인트

@app.post("/api/interview/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자와의 경쟁 면접 시작"""
    try:
        # 🐛 디버깅: FastAPI에서 받은 설정값 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 받은 settings = {settings.dict()}")
        interview_logger.info(f"🐛 FastAPI DEBUG: use_interviewer_service = {settings.use_interviewer_service}")
        
        # 🆕 posting_id가 있으면 DB에서 실제 채용공고 정보를 가져와서 사용
        if settings.posting_id:
            from database.services.existing_tables_service import existing_tables_service
            posting_info = await existing_tables_service.get_posting_by_id(settings.posting_id)
            
            if posting_info:
                interview_logger.info(f"📋 실제 채용공고 사용: posting_id={settings.posting_id}")
                interview_logger.info(f"   회사: {posting_info.get('company', {}).get('name', 'Unknown')}")
                interview_logger.info(f"   직무: {posting_info.get('position', {}).get('position_name', 'Unknown')}")
                
                settings_dict = {
                    "company": posting_info.get('company', {}).get('name', settings.company),
                    "position": posting_info.get('position', {}).get('position_name', settings.position),
                    "candidate_name": settings.candidate_name,
                    "posting_id": settings.posting_id,
                    "company_id": posting_info.get('company_id'),
                    "position_id": posting_info.get('position_id'),
                    "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
                }
            else:
                interview_logger.warning(f"⚠️ 채용공고를 찾을 수 없음: posting_id={settings.posting_id}, fallback to original")
                settings_dict = {
                    "company": settings.company,
                    "position": settings.position,
                    "candidate_name": settings.candidate_name,
                    "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
                }
        else:
            # 기존 방식: company/position 문자열 사용
            settings_dict = {
                "company": settings.company,
                "position": settings.position,
                "candidate_name": settings.candidate_name,
                "use_interviewer_service": settings.use_interviewer_service  # 🎯 플래그 포함
            }
        
        # 🐛 디버깅: 서비스에 전달할 settings_dict 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 서비스에 전달할 settings_dict = {settings_dict}")
        
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

@app.post("/api/interview/comparison/turn")
async def process_competition_turn(
    submission: CompetitionTurnSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """경쟁 면접 통합 턴 처리"""
    try:
        result = await service.process_competition_turn(
            submission.comparison_session_id,
            submission.answer
        )
        return result
    except Exception as e:
        interview_logger.error(f"경쟁 면접 턴 처리 API 오류: {str(e)}")
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

# 🚀 새로운 턴제 면접 엔드포인트

@app.post("/api/interview/turn-based/start")
async def start_turn_based_interview(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 시작 - 새로운 InterviewerService 사용"""
    try:
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name
        }
        
        result = await service.start_turn_based_interview(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/turn-based/question/{session_id}")
async def get_turn_based_question(
    session_id: str,
    user_answer: Optional[str] = None,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 다음 질문 가져오기"""
    try:
        result = await service.get_turn_based_question(session_id, user_answer)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 질문 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    print("Beta-GO Interview FastAPI 시작!")
    print("브라우저에서 http://localhost:8000 접속")
    print("API 문서: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )