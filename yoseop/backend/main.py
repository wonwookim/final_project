"""
FastAPI 기반 AI 면접 시스템
Flask에서 FastAPI로 변환된 고성능 비동기 웹 서버
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

# LLM 시스템 임포트 (새로운 구조)
from llm.core.config import config
from llm.core.logging_config import interview_logger, performance_logger
from llm.core.personalized_system import PersonalizedInterviewSystem
from llm.core.document_processor import DocumentProcessor, UserProfile
from llm.core.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE
from llm.core.ai_candidate_model import AICandidateModel, AnswerRequest
from llm.core.answer_quality_controller import QualityLevel
from llm.core.interview_system import QuestionType, QuestionAnswer
from llm.core.llm_manager import LLMProvider
# UnifiedInterviewSession 제거 - 원래 설계 복구

# 회사 이름 매핑
COMPANY_NAME_MAP = {
    "네이버": "naver",
    "카카오": "kakao", 
    "라인": "line",
    "쿠팡": "coupang",
    "배달의민족": "baemin",
    "당근마켓": "daangn", 
    "토스": "toss"
}

def get_company_id(company_name: str) -> str:
    """회사 이름을 ID로 변환"""
    return COMPANY_NAME_MAP.get(company_name, company_name.lower())

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

# 정적 파일 서빙 (React 빌드 파일)
# app.mount("/static", StaticFiles(directory="../demo_react"), name="static")

# 전역 상태 관리 - 단순화
class ApplicationState:
    """애플리케이션 상태 관리 - 기존 Flask 방식 유지"""
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.personalized_system = PersonalizedInterviewSystem()  # 기존 core 그대로 사용
        self.ai_candidate_model = AICandidateModel()  # AI 답변용

# 전역 상태 인스턴스
app_state = ApplicationState()

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

# 의존성 주입
def get_app_state():
    return app_state

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
    state: ApplicationState = Depends(get_app_state)
):
    """면접 시작 - 기존 core 기능 직접 사용"""
    try:
        # 회사 ID 변환
        company_id = get_company_id(settings.company)
        
        # 문서 기반 프로필 생성 (기존 방식)
        if settings.documents:
            profile = await generate_personalized_profile(settings.documents, state)
        else:
            # 기본 프로필 생성
            from core.document_processor import UserProfile
            profile = UserProfile(
                name=settings.candidate_name,
                background={"career_years": "1", "current_position": "신입"},
                technical_skills=[],
                projects=[],
                experiences=[],
                strengths=["학습능력", "열정"],
                keywords=["신입", "개발"],
                career_goal="전문 개발자로 성장",
                unique_points=["빠른 적응력"]
            )
        
        # PersonalizedInterviewSystem으로 면접 시작 (기존 core 그대로)
        session_id = state.personalized_system.start_personalized_interview(
            company_id=company_id,
            position=settings.position,
            candidate_name=settings.candidate_name,
            user_profile=profile
        )
        
        interview_logger.info(f"면접 시작 - 세션 ID: {session_id}")
        
        return {
            "session_id": session_id,
            "message": "면접이 시작되었습니다."
        }
        
    except Exception as e:
        interview_logger.error(f"면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"면접 시작 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/interview/upload")
async def upload_document(
    file: UploadFile = File(...),
    state: ApplicationState = Depends(get_app_state)
):
    """문서 업로드 및 분석"""
    try:
        # 파일 검증
        if not file.filename.lower().endswith(tuple(ALLOWED_FILE_EXTENSIONS)):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
        
        # 파일 저장
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 문서 분석
        analyzed_content = await analyze_document_async(file_path, state)
        
        return {
            "file_id": str(file_path),
            "analyzed_content": analyzed_content,
            "message": "문서 업로드 및 분석이 완료되었습니다."
        }
        
    except Exception as e:
        interview_logger.error(f"문서 업로드 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문서 업로드 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/interview/question")
async def get_next_question(
    session_id: str,
    state: ApplicationState = Depends(get_app_state)
):
    """다음 질문 가져오기 - 기존 core 기능 직접 사용"""
    try:
        # PersonalizedInterviewSystem에서 직접 질문 가져오기
        question_data = state.personalized_system.get_next_question(session_id)
        
        if not question_data:
            return {"completed": True, "message": "모든 질문이 완료되었습니다."}
        
        # 진행률 정보 계산
        session = state.personalized_system.get_session(session_id)
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
        
    except Exception as e:
        interview_logger.error(f"질문 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"질문을 가져오는 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/interview/answer")
async def submit_answer(
    answer_data: AnswerSubmission,
    state: ApplicationState = Depends(get_app_state)
):
    """답변 제출 - 기존 core 평가 시스템 사용"""
    try:
        # PersonalizedInterviewSystem의 기존 submit_answer 사용 (평가 포함)
        result = state.personalized_system.submit_answer(answer_data.session_id, answer_data.answer)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # 기존 core에서 반환하는 결과 그대로 사용
        return {
            "status": result.get("status", "success"),
            "message": result.get("message", "답변이 성공적으로 제출되었습니다."),
            "question": result.get("question"),
            "answered_count": result.get("answered_count", 0),
            "total_questions": result.get("total_questions", 0)
        }
        
    except Exception as e:
        interview_logger.error(f"답변 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"답변 제출 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/interview/results/{session_id}")
async def get_interview_results(
    session_id: str,
    state: ApplicationState = Depends(get_app_state)
):
    """면접 결과 조회"""
    try:
        session_mapping = state.get_session_mapping(session_id)
        if not session_mapping:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 결과 생성
        results = await generate_interview_results(session_mapping, state)
        
        return results
        
    except Exception as e:
        interview_logger.error(f"결과 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"결과를 조회하는 중 오류가 발생했습니다: {str(e)}")

# AI 경쟁 모드 엔드포인트 - web/app.py 방식으로 구현
@app.post("/api/interview/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    state: ApplicationState = Depends(get_app_state)
):
    """AI 지원자와의 경쟁 면접 시작 - web/app.py와 동일한 방식"""
    try:
        interview_logger.info("AI 비교 면접 시작")
        
        # 기본 프로필 생성
        from core.document_processor import UserProfile
        quick_profile = UserProfile(
            name=settings.candidate_name,
            background={"career_years": "3", "current_position": "개발자"},
            technical_skills=["Python", "JavaScript"],
            projects=[],
            experiences=[],
            strengths=["문제해결", "소통"],
            keywords=["개발", "기술"],
            career_goal="성장하는 개발자",
            unique_points=["열정적인 학습"]
        )
        
        # 사용자 세션 시작 먼저 (PersonalizedInterviewSystem 사용)
        company_id = get_company_id(settings.company)
        import uuid
        
        # 완전 고유한 세션 ID 생성 (사용자용)
        user_unique_id = str(uuid.uuid4())[:8]  # 8자리 고유 ID
        user_unique_position = f"USER_{settings.position.replace(' ', '_')}_{user_unique_id}"
        
        print(f"🔍 사용자 세션 생성 중 - 이름: {settings.candidate_name}")
        user_session_id = state.personalized_system.start_personalized_interview(
            company_id=company_id,
            position=user_unique_position,  # 사용자 전용 포지션명
            candidate_name=settings.candidate_name,  # 사용자 실제 이름
            user_profile=quick_profile
        )
        print(f"✅ 사용자 세션 생성 완료 - ID: {user_session_id}")
        
        # 사용자 첫 질문 생성해서 확인
        user_first_question = state.personalized_system.get_next_question(user_session_id)
        print(f"🔍 사용자 세션에서 질문 요청: {user_session_id}")
        print(f"📝 생성된 사용자 질문: {user_first_question}")
        
        # AI 세션 시작 (완전히 다른 세션 ID로)
        from core.document_processor import UserProfile
        
        # 완전 고유한 세션 ID 생성 (AI용)
        ai_unique_id = str(uuid.uuid4())[:8]  # 8자리 고유 ID
        ai_unique_position = f"AI_{settings.position.replace(' ', '_')}_{ai_unique_id}"
        
        ai_profile = UserProfile(
            name="춘식이",
            background={
                "career_years": "3",
                "current_position": "AI 지원자",
                "education": ["AI 대학교 졸업"]
            },
            technical_skills=["Python", "AI", "Machine Learning"],
            projects=[{
                "name": "AI 면접 시스템",
                "description": "AI 기반 면접 시스템 개발",
                "tech_stack": ["Python", "AI"]
            }],
            experiences=[{
                "company": "AI Corp",
                "position": "AI 개발자",
                "period": "3년"
            }],
            strengths=["빠른 학습", "문제해결"],
            keywords=["AI", "개발", "면접"],
            career_goal="AI 전문가",
            unique_points=["AI 특화"]
        )
        
        print(f"🔍 AI 세션 생성 중 - 이름: 춘식이")
        ai_session_id = state.personalized_system.start_personalized_interview(
            company_id=company_id,
            position=ai_unique_position,  # AI 전용 포지션명
            candidate_name="춘식이",  # AI 이름
            user_profile=ai_profile
        )
        print(f"✅ AI 세션 생성 완료 - ID: {ai_session_id}")
        
        # AI 첫 질문 생성해서 확인
        ai_first_question = state.personalized_system.get_next_question(ai_session_id)
        print(f"📝 생성된 AI 질문: {ai_first_question}")
        
        # 사용자 세션 재확인 (AI 세션 생성 후)
        user_recheck_question = state.personalized_system.get_next_question(user_session_id)
        print(f"🔍 사용자 세션 재확인: {user_recheck_question}")
        
        # 세션 분리 검증
        print(f"🔍 세션 분리 검증:")
        print(f"   - 사용자 세션 ID: {user_session_id}")
        print(f"   - AI 세션 ID: {ai_session_id}")
        print(f"   - 세션 분리됨: {user_session_id != ai_session_id}")
        
        # AI 이름 가져오기
        from core.llm_manager import LLMProvider
        ai_name = state.ai_candidate_model.get_ai_name(LLMProvider.OPENAI_GPT4O_MINI)
        
        # 랜덤으로 시작자 결정 (50% 확률)
        import random
        starts_with_user = random.choice([True, False])
        initial_phase = 'user_turn' if starts_with_user else 'ai_turn'
        
        # 비교 세션 생성
        comparison_session_id = f"comp_{user_session_id}"
        
        # 전역 상태에 비교 세션 저장
        if not hasattr(state, 'comparison_sessions'):
            state.comparison_sessions = {}
            
        state.comparison_sessions[comparison_session_id] = {
            'user_session_id': user_session_id,
            'ai_session_id': ai_session_id,
            'current_question_index': 1,
            'current_phase': initial_phase,
            'total_questions': 20,
            'user_name': settings.candidate_name,
            'ai_name': ai_name,
            'user_answers': [],
            'ai_answers': [],
            'starts_with_user': starts_with_user
        }
        
        print(f"✅ 비교 면접 세션 생성: {comparison_session_id}")
        print(f"🎲 시작자: {'사용자' if starts_with_user else 'AI'}")
        
        if starts_with_user:
            # 사용자부터 시작
            print(f"🔍 사용자 세션에서 질문 요청: {user_session_id}")
            user_question = state.personalized_system.get_next_question(user_session_id)
            print(f"📝 생성된 사용자 질문: {user_question}")
            
            if user_question:
                return {
                    "session_id": user_session_id,
                    "comparison_session_id": comparison_session_id,
                    "user_session_id": user_session_id,
                    "ai_session_id": ai_session_id,
                    "question": user_question,
                    "current_phase": "user_turn",
                    "current_respondent": settings.candidate_name,
                    "question_index": 1,
                    "total_questions": 20,
                    "ai_name": ai_name,
                    "starts_with_user": True,
                    "message": f"{settings.candidate_name}님부터 시작합니다"
                }
            else:
                raise HTTPException(status_code=500, detail="질문을 생성할 수 없습니다")
        else:
            # AI부터 시작
            return {
                "session_id": user_session_id,
                "comparison_session_id": comparison_session_id,
                "user_session_id": user_session_id,
                "ai_session_id": ai_session_id,
                "current_phase": "ai_turn",
                "current_respondent": ai_name,
                "question_index": 1,
                "total_questions": 20,
                "ai_name": ai_name,
                "user_name": settings.candidate_name,
                "starts_with_user": False,
                "message": f"{ai_name}부터 시작합니다"
            }
        
    except Exception as e:
        interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 경쟁 면접 시작 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/interview/ai-answer/{session_id}/{question_id}")
async def get_ai_answer(
    session_id: str,
    question_id: str,
    state: ApplicationState = Depends(get_app_state)
):
    """AI 지원자의 답변 생성 - 기존 core 기능 직접 사용"""
    try:
        # URL 디코딩
        import urllib.parse
        decoded_session_id = urllib.parse.unquote(session_id)
        print(f"🔍 AI 답변 생성 요청 - session_id: {decoded_session_id}, question_id: {question_id}")
        
        # 간단한 방법으로 춘식이 답변 생성
        # 회사와 포지션을 세션 ID에서 파싱
        session_parts = decoded_session_id.split('_')
        company_id = session_parts[0] if len(session_parts) > 0 else "naver"
        position = "_".join(session_parts[1:-1]) if len(session_parts) > 2 else "백엔드 개발"
        
        print(f"📋 파싱된 정보 - company: {company_id}, position: {position}")
        
        # 춘식이 전용 AI 세션 시작하고 질문 가져오기
        ai_session_id = state.ai_candidate_model.start_ai_interview(company_id, position)
        
        # 춘식이에게 줄 질문 가져오기 (AI 전용, question_id 기반으로 순서 맞춤)
        ai_question_data = state.ai_candidate_model.get_ai_next_question(ai_session_id)
        
        if ai_question_data:
            question_content = ai_question_data["question_content"]
            question_intent = ai_question_data["question_intent"]
            question_type = ai_question_data["question_type"]
        else:
            # question_id 기반 폴백 질문 (춘식이용) - 강제 타입 설정
            if question_id == "q_1":
                question_content = "춘식이, 자기소개를 부탁드립니다."
                question_intent = "지원자의 기본 정보와 성격, 역량을 파악"
                question_type = "INTRO"
            elif question_id == "q_2":
                question_content = f"춘식이께서 네이버에 지원하게 된 동기는 무엇인가요?"
                question_intent = "회사에 대한 관심도와 지원 동기 파악"
                question_type = "MOTIVATION"
            else:
                question_content = "춘식이에 대해 더 알려주세요."
                question_intent = "일반적인 평가"
                question_type = "HR"
        
        # 강제로 q_1은 INTRO로 설정
        if question_id == "q_1":
            question_type = "INTRO"
        elif question_id == "q_2":
            question_type = "MOTIVATION"
        
        # core의 기존 답변 생성 기능 사용
        from core.ai_candidate_model import AnswerRequest
        from core.interview_system import QuestionType
        from core.answer_quality_controller import QualityLevel
        from core.llm_manager import LLMProvider
        
        # QuestionType 매핑
        question_type_map = {
            "INTRO": QuestionType.INTRO,
            "MOTIVATION": QuestionType.MOTIVATION,
            "HR": QuestionType.HR,
            "TECH": QuestionType.TECH,
            "COLLABORATION": QuestionType.COLLABORATION
        }
        
        # 답변 요청 생성
        print(f"🎯 질문 타입 매핑: {question_type} → {question_type_map.get(question_type, QuestionType.HR)}")
        print(f"🎯 질문 내용: {question_content}")
        
        answer_request = AnswerRequest(
            question_content=question_content,
            question_type=question_type_map.get(question_type, QuestionType.HR),
            question_intent=question_intent,
            company_id=company_id,
            position=position,
            quality_level=QualityLevel.GOOD,  # 춘식이는 좋은 품질로
            llm_provider=LLMProvider.OPENAI_GPT4O_MINI
        )
        
        # AI 답변 생성 (기존 core 기능)
        ai_answer = state.ai_candidate_model.generate_answer(answer_request)
        
        if not ai_answer:
            raise HTTPException(status_code=500, detail="AI 답변 생성에 실패했습니다.")
        
        print(f"✅ AI 답변 생성 완료: {ai_answer.answer_content[:50]}...")
        
        return {
            "question": question_content,
            "questionType": question_type,
            "questionIntent": question_intent,
            "answer": ai_answer.answer_content,
            "time_spent": 60,
            "score": 85,
            "quality_level": ai_answer.quality_level.value,
            "persona_name": ai_answer.persona_name
        }
        
    except Exception as e:
        interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")

# 비교 면접 엔드포인트들
class ComparisonAnswerSubmission(BaseModel):
    """비교 면접 답변 제출 모델"""
    comparison_session_id: str
    answer: str

class AITurnRequest(BaseModel):
    """AI 턴 처리 요청 모델"""
    comparison_session_id: str
    step: str = "question"  # "question" 또는 "answer"

@app.post("/api/interview/comparison/user-turn")
async def submit_comparison_user_turn(
    answer_data: ComparisonAnswerSubmission,
    state: ApplicationState = Depends(get_app_state)
):
    """비교 면접 사용자 턴 답변 제출 - web/app.py와 동일한 방식"""
    try:
        comparison_session_id = answer_data.comparison_session_id
        answer = answer_data.answer
        
        if not all([comparison_session_id, answer]):
            raise HTTPException(status_code=400, detail="모든 필드가 필요합니다")
        
        # 비교 세션 확인
        if not hasattr(state, 'comparison_sessions'):
            raise HTTPException(status_code=404, detail="비교 세션을 찾을 수 없습니다")
            
        comp_session = state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            raise HTTPException(status_code=404, detail="비교 세션을 찾을 수 없습니다")
        
        if comp_session['current_phase'] != 'user_turn':
            raise HTTPException(status_code=400, detail="현재 사용자 턴이 아닙니다")
        
        # 사용자 답변 제출 (기존 core 시스템 사용)
        system_result = state.personalized_system.submit_answer(comp_session['user_session_id'], answer)
        
        # 답변 저장
        comp_session['user_answers'].append({
            'question_index': comp_session['current_question_index'],
            'answer': answer
        })
        
        # AI 턴으로 전환
        comp_session['current_phase'] = 'ai_turn'
        
        # 다음 사용자 질문 가져오기 (제출 후 생성된 질문)
        next_user_question = None
        if system_result and system_result.get('question'):
            next_user_question = system_result['question']
        else:
            # system_result에 질문이 없으면 직접 가져오기
            next_user_question = state.personalized_system.get_next_question(comp_session['user_session_id'])
        
        return {
            "status": "success",
            "message": "사용자 답변이 제출되었습니다",
            "next_phase": "ai_turn",
            "submission_result": system_result,
            "next_user_question": next_user_question  # 다음 사용자 질문 추가
        }
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"사용자 턴 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"답변 제출 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/interview/comparison/ai-turn")
async def process_comparison_ai_turn(
    ai_turn_data: AITurnRequest,
    state: ApplicationState = Depends(get_app_state)
):
    """비교 면접 AI 턴 처리 - web/app.py와 동일한 방식"""
    try:
        comparison_session_id = ai_turn_data.comparison_session_id
        step = ai_turn_data.step
        
        if not comparison_session_id:
            raise HTTPException(status_code=400, detail="비교 세션 ID가 필요합니다")
        
        # 비교 세션 확인
        if not hasattr(state, 'comparison_sessions'):
            raise HTTPException(status_code=404, detail="비교 세션을 찾을 수 없습니다")
            
        comp_session = state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            raise HTTPException(status_code=404, detail="비교 세션을 찾을 수 없습니다")
        
        if comp_session['current_phase'] != 'ai_turn':
            raise HTTPException(status_code=400, detail="현재 AI 턴이 아닙니다")
        
        ai_session_id = comp_session['ai_session_id']
        
        if step == 'question':
            # 1단계: AI 질문만 생성 (PersonalizedInterviewSystem 사용)
            ai_question = state.personalized_system.get_next_question(ai_session_id)
            
            if not ai_question:
                raise HTTPException(status_code=500, detail="AI 질문을 생성할 수 없습니다")
            
            # 질문을 세션에 임시 저장
            comp_session['temp_ai_question'] = ai_question
            
            return {
                "status": "success",
                "step": "question_generated",
                "ai_question": ai_question,
                "message": "AI 질문이 생성되었습니다. 2-3초 후 답변이 생성됩니다."
            }
            
        elif step == 'answer':
            # 2단계: AI 답변 생성 (임시 저장된 질문 사용)
            ai_question = comp_session.get('temp_ai_question')
            if not ai_question:
                raise HTTPException(status_code=400, detail="저장된 AI 질문이 없습니다")
            
            # AI 답변을 PersonalizedInterviewSystem을 통해 생성
            # 먼저 AICandidateModel로 답변 생성
            try:
                from core.ai_candidate_model import AnswerRequest
                from core.interview_system import QuestionType
                from core.answer_quality_controller import QualityLevel
                from core.llm_manager import LLMProvider
                
                # QuestionType 매핑
                question_type_map = {
                    "자기소개": QuestionType.INTRO,
                    "지원동기": QuestionType.MOTIVATION,
                    "INTRO": QuestionType.INTRO,
                    "MOTIVATION": QuestionType.MOTIVATION,
                    "HR": QuestionType.HR,
                    "TECH": QuestionType.TECH,
                    "COLLABORATION": QuestionType.COLLABORATION
                }
                
                # AI 답변 요청 생성
                answer_request = AnswerRequest(
                    question_content=ai_question["question_content"],
                    question_type=question_type_map.get(ai_question["question_type"], QuestionType.HR),
                    question_intent=ai_question["question_intent"],
                    company_id=comp_session.get('user_session_id', 'naver').split('_')[0],  # company 추출
                    position="AI지원자",
                    quality_level=QualityLevel.GOOD,
                    llm_provider=LLMProvider.OPENAI_GPT4O_MINI
                )
                
                # AI 답변 생성
                ai_answer_response = state.ai_candidate_model.generate_answer(answer_request)
                
                # PersonalizedInterviewSystem에 답변 제출 (간단한 문자열 답변만)
                submission_result = state.personalized_system.submit_answer(ai_session_id, ai_answer_response.answer_content)
                
            except Exception as e:
                print(f"❌ AI 답변 생성 오류: {str(e)}")
                raise HTTPException(status_code=500, detail=f"AI 답변 생성 실패: {str(e)}")
            
            if ai_answer_response.error:
                raise HTTPException(status_code=500, detail=f"AI 답변 생성 실패: {ai_answer_response.error}")
            
            # 답변 저장
            comp_session['ai_answers'].append({
                'question_index': comp_session['current_question_index'],
                'question': ai_question['question_content'],
                'answer': ai_answer_response.answer_content
            })
            
            # 임시 질문 삭제
            if 'temp_ai_question' in comp_session:
                del comp_session['temp_ai_question']
            
            # 다음 질문으로 진행
            comp_session['current_question_index'] += 1
            
            # 면접 완료 확인
            if comp_session['current_question_index'] > comp_session['total_questions']:
                comp_session['current_phase'] = 'completed'
                return {
                    "status": "success",
                    "step": "answer_generated",
                    "interview_status": "completed",
                    "ai_question": ai_question,
                    "ai_answer": {
                        "content": ai_answer_response.answer_content,
                        "persona_name": ai_answer_response.persona_name,
                        "confidence": ai_answer_response.confidence_score
                    },
                    "message": "비교 면접이 완료되었습니다"
                }
            else:
                # 다음 사용자 턴 준비
                comp_session['current_phase'] = 'user_turn'
                
                # 다음 사용자 질문 가져오기
                next_user_question = state.personalized_system.get_next_question(comp_session['user_session_id'])
                
                print(f"🔍 AI 턴 완료 후 다음 사용자 질문: {next_user_question}")
                
                return {
                    "status": "success",
                    "step": "answer_generated", 
                    "interview_status": "continue",
                    "ai_question": ai_question,
                    "ai_answer": {
                        "content": ai_answer_response.answer_content,
                        "persona_name": ai_answer_response.persona_name,
                        "confidence": ai_answer_response.confidence_score
                    },
                    "next_user_question": next_user_question,
                    "next_phase": "user_turn",
                    "current_question_index": comp_session['current_question_index']
                }
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 step 값입니다")
            
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"AI 턴 처리 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 턴 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/interview/history")
async def get_interview_history(
    user_id: Optional[str] = None,
    state: ApplicationState = Depends(get_app_state)
):
    """면접 기록 조회"""
    try:
        # 완료된 세션들 필터링 - 원래 설계 복구
        completed_sessions = []
        
        # PersonalizedInterviewSystem의 완료된 세션들 가져오기
        for session_id, session in state.personalized_system.sessions.items():
            if session.is_completed():
                completed_sessions.append({
                    "session_id": session_id,
                    "settings": {
                        "company": session.company_id,
                        "position": session.position,
                        "user_name": session.candidate_name
                    },
                    "completed_at": session.created_at,
                    "total_score": 85,  # 기본값
                    "type": "personalized"
                })
        
        return {
            "total_interviews": len(completed_sessions),
            "interviews": completed_sessions
        }
        
    except Exception as e:
        interview_logger.error(f"기록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"기록을 조회하는 중 오류가 발생했습니다: {str(e)}")

# 헬퍼 함수들

async def generate_personalized_profile(documents: List[str], state: ApplicationState) -> Dict:
    """문서 기반 사용자 프로필 생성"""
    try:
        doc_processor = state.document_processor
        profile = None
        
        for doc_path in documents:
            if os.path.exists(doc_path):
                profile = await asyncio.to_thread(doc_processor.process_document, doc_path)
                break
        
        if not profile:
            # 기본 프로필 생성
            profile = {
                "name": "지원자",
                "background": {"career_years": 3, "education": "대학교 졸업"},
                "technical_skills": ["Java", "Spring", "MySQL"],
                "projects": [{"name": "웹 서비스 개발", "description": "백엔드 API 개발"}],
                "experiences": [{"company": "이전 회사", "role": "백엔드 개발자", "duration": "2년"}],
                "strengths": ["문제해결능력", "커뮤니케이션"],
                "keywords": ["개발", "협업", "성장"],
                "career_goal": "시니어 개발자로 성장",
                "unique_points": ["빠른 학습 능력"]
            }
        
        return profile
        
    except Exception as e:
        interview_logger.error(f"프로필 생성 오류: {str(e)}")
        return None

async def generate_personalized_questions(profile: Dict, settings: InterviewSettings, state: ApplicationState) -> List[Dict]:
    """개인화된 질문 생성"""
    try:
        personalized_system = state.personalized_system
        
        # 개인화된 면접 시작
        session_id = await asyncio.to_thread(
            personalized_system.start_personalized_interview,
            settings.company,
            settings.position,
            profile.get('name', '지원자'),
            profile
        )
        
        questions = []
        question_count = 0
        max_questions = 15  # 최대 질문 수
        
        while question_count < max_questions:
            try:
                question_data = await asyncio.to_thread(
                    personalized_system.get_next_question,
                    session_id
                )
                
                if not question_data or 'question_content' not in question_data:
                    break
                
                # 고유한 ID 생성
                import uuid
                unique_id = f"q{question_count + 1}_{uuid.uuid4().hex[:8]}"
                
                question = {
                    "id": unique_id,
                    "question": question_data['question_content'],
                    "category": question_data.get('question_intent', '기본'),
                    "time_limit": 180,
                    "keywords": question_data.get('keywords', []),
                    "personalized": question_data.get('personalized', False),
                    "progress": question_data.get('progress', 0)
                }
                
                print(f"📝 질문 #{question_count + 1} 생성: ID={unique_id}, Q={question_data['question_content'][:50]}...")
                questions.append(question)
                question_count += 1
                
            except Exception as e:
                interview_logger.error(f"질문 생성 오류: {str(e)}")
                break
        
        # 최소 질문 수 보장
        if len(questions) < 5:
            standard_questions, _ = await generate_standard_interview_questions(settings, state)
            questions.extend(standard_questions[len(questions):])
        
        return questions[:max_questions], session_id
        
    except Exception as e:
        interview_logger.error(f"개인화 질문 생성 오류: {str(e)}")
        return await generate_basic_questions(settings, state), None

async def generate_standard_interview_questions(settings: InterviewSettings, state: ApplicationState):
    """표준 면접 질문 생성 (Fixed + LLM 조합)"""
    try:
        personalized_system = state.personalized_system
        company_id = get_company_id(settings.company)
        
        # DocumentProcessor의 UserProfile 형식으로 생성
        from core.document_processor import UserProfile
        
        basic_profile = UserProfile(
            name=settings.user_name,
            background={"career_years": 3, "education": "대학교 졸업"},
            technical_skills=["Java", "Python", "JavaScript"],
            projects=[{"name": "웹 개발 프로젝트", "description": "기본 웹 애플리케이션 개발"}],
            experiences=[{"company": "이전 회사", "role": "개발자", "duration": "2년"}],
            strengths=["문제해결", "커뮤니케이션"],
            keywords=["개발", "협업", "성장"],
            career_goal="시니어 개발자로 성장",
            unique_points=["빠른 학습 능력"]
        )
        
        # PersonalizedInterviewSystem으로 질문 생성
        session_id = await asyncio.to_thread(
            personalized_system.start_personalized_interview,
            company_id,
            settings.position,
            settings.user_name,
            basic_profile
        )
        
        questions = []
        question_count = 0
        max_questions = 10
        
        print(f"🚀 PersonalizedInterviewSystem 질문 생성 시작 - session_id: {session_id}")
        
        while question_count < max_questions:
            try:
                print(f"🔄 질문 #{question_count + 1} 생성 시도 중...")
                question_data = await asyncio.to_thread(
                    personalized_system.get_next_question,
                    session_id
                )
                
                print(f"📝 질문 데이터 받음: {question_data}")
                
                if not question_data or 'question_content' not in question_data:
                    print(f"❌ 질문 데이터 없음 또는 invalid: {question_data}")
                    break
                
                # 고유한 ID 생성
                import uuid
                unique_id = f"q{question_count + 1}_{uuid.uuid4().hex[:8]}"
                
                question = {
                    "id": unique_id,
                    "question": question_data['question_content'],
                    "category": question_data.get('question_intent', '기본'),
                    "time_limit": 180,
                    "keywords": question_data.get('keywords', []),
                    "personalized": question_data.get('personalized', False),
                    "progress": question_data.get('progress', 0)
                }
                
                print(f"📝 질문 #{question_count + 1} 생성: ID={unique_id}, Q={question_data['question_content'][:50]}...")
                questions.append(question)
                question_count += 1
                
            except Exception as e:
                interview_logger.error(f"표준 질문 생성 오류: {str(e)}")
                break
        
        # 최소 질문 수 보장 (중복 제거)
        if len(questions) < 5:
            basic_questions = await generate_basic_questions(settings, state)
            
            # 기존 질문 내용과 중복되지 않는 질문만 추가
            existing_questions = {q["question"].lower() for q in questions}
            
            for basic_q in basic_questions:
                if len(questions) >= 10:  # 최대 10개 제한
                    break
                if basic_q["question"].lower() not in existing_questions:
                    questions.append(basic_q)
        
        return questions[:max_questions], session_id
        
    except Exception as e:
        interview_logger.error(f"표준 면접 질문 생성 오류: {str(e)}")
        return await generate_basic_questions(settings, state), None

async def generate_basic_questions(settings: InterviewSettings, state: ApplicationState) -> List[Dict]:
    """기본 질문 생성 (Fallback)"""
    import uuid
    # 기본 질문 템플릿 (고유 ID 생성)
    base_questions = [
        {
            "id": f"basic_{uuid.uuid4().hex[:8]}_1",
            "question": "자기소개를 해주세요.",
            "category": "기본",
            "time_limit": 120,
            "keywords": ["경험", "기술", "역할", "프로젝트", "성과"]
        },
        {
            "id": f"basic_{uuid.uuid4().hex[:8]}_2",
            "question": f"{settings.company}에 지원한 이유가 무엇인가요?",
            "category": "동기",
            "time_limit": 90,
            "keywords": ["관심", "기여", "성장", "비전", "목표"]
        },
        {
            "id": f"basic_{uuid.uuid4().hex[:8]}_3",
            "question": "가장 어려웠던 기술적 문제를 어떻게 해결했나요?",
            "category": "기술",
            "time_limit": 180,
            "keywords": ["문제", "해결", "접근", "결과", "학습"]
        },
        {
            "id": f"basic_{uuid.uuid4().hex[:8]}_4",
            "question": "팀워크 경험에 대해 말씀해주세요.",
            "category": "협업",
            "time_limit": 120,
            "keywords": ["협업", "소통", "갈등", "해결", "성과"]
        },
        {
            "id": f"basic_{uuid.uuid4().hex[:8]}_5",
            "question": "5년 후 자신의 모습을 어떻게 그리고 있나요?",
            "category": "미래",
            "time_limit": 90,
            "keywords": ["목표", "계획", "성장", "전문성", "비전"]
        }
    ]
    
    return base_questions

async def analyze_document_async(file_path: Path, state: ApplicationState) -> Dict:
    """문서 분석 (비동기)"""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            state.document_processor.process_document,
            str(file_path)
        )
        return result
    except Exception as e:
        interview_logger.error(f"문서 분석 오류: {str(e)}")
        return {}

async def evaluate_answer_async(answer_record: Dict, session: Dict, state: ApplicationState):
    """답변 평가 (비동기)"""
    try:
        # AI 평가 수행
        evaluation = await asyncio.get_event_loop().run_in_executor(
            None,
            state.ai_candidate_model.evaluate_answer,
            answer_record["answer"]
        )
        
        # 평가 결과 저장
        answer_record["evaluation"] = evaluation
        
        interview_logger.info(f"답변 평가 완료", question_id=answer_record["question_id"])
        
    except Exception as e:
        interview_logger.error(f"답변 평가 오류: {str(e)}")

def calculate_basic_score(answer: str, time_spent: int) -> int:
    """기본 점수 계산"""
    score = 0
    
    # 답변 길이 점수 (30점)
    answer_length = len(answer)
    if answer_length > 200:
        score += 30
    elif answer_length > 100:
        score += 20
    elif answer_length > 50:
        score += 10
    
    # 시간 활용 점수 (30점)
    time_ratio = time_spent / 120  # 기본 2분 가정
    if time_ratio > 0.7:
        score += 30
    elif time_ratio > 0.5:
        score += 20
    elif time_ratio > 0.3:
        score += 10
    
    # 기본 점수 (40점)
    score += 40
    
    return min(score, 100)

async def generate_interview_results(session_mapping: Dict[str, str], state: ApplicationState) -> Dict:
    """면접 결과 생성 - 원래 설계 복구"""
    try:
        human_session_id = session_mapping["human_session_id"]
        human_session = state.personalized_system.get_session(human_session_id)
        
        if not human_session:
            raise ValueError("세션을 찾을 수 없습니다.")
        
        # 기본 결과 생성
        answers = human_session.question_answers
        total_score = 85  # 기본값
        
        # 카테고리별 점수 (간단 버전)
        category_scores = {
            "인사": 80,
            "기술": 85, 
            "협업": 90
        }
        
        # 상세 피드백 (간단 버전)
        detailed_feedback = []
        for qa in answers:
            feedback = {
                "question": qa.question_content,
                "answer": qa.answer_content,
                "score": 85,
                "feedback": "잘 답변하셨습니다.",
                "strengths": ["구체적인 설명"],
                "improvements": ["더 자세한 예시"]
            }
            detailed_feedback.append(feedback)
        
        # 추천사항
        recommendations = [
            "구체적인 사례를 더 많이 준비하세요",
            "기술적 깊이를 더 보완하세요", 
            "회사에 대한 이해도를 높이세요"
        ]
        
        return {
            "session_id": human_session_id,
            "total_score": total_score,
            "category_scores": category_scores,
            "detailed_feedback": detailed_feedback,
            "recommendations": recommendations,
            "interview_info": {
                "company": human_session.company_id,
                "position": human_session.position,
                "user_name": human_session.candidate_name
            }
        }
        
    except Exception as e:
        interview_logger.error(f"결과 생성 오류: {str(e)}")
        raise

async def get_ai_candidate_info(company: str, quality_level: int, state: ApplicationState) -> Dict:
    """AI 지원자 정보 조회"""
    try:
        # 회사별 AI 지원자 데이터 로드
        companies_data_path = Path("data/companies_data.json")
        if companies_data_path.exists():
            with open(companies_data_path, 'r', encoding='utf-8') as f:
                companies_data = json.load(f)
            
            # companies_data 구조가 list 형태일 수 있음
            companies_list = companies_data.get("companies", []) if isinstance(companies_data.get("companies"), list) else []
            company_data = next((c for c in companies_list if c.get("id") == company.lower()), {})
            ai_personas = company_data.get("ai_personas", [])
            
            if ai_personas:
                persona = ai_personas[0]  # 첫 번째 AI 지원자 사용
                return {
                    "name": persona.get("name", "춘식이"),
                    "experience": persona.get("experience", "3년"),
                    "specialties": persona.get("specialties", ["개발", "문제해결"]),
                    "quality_level": quality_level,
                    "quality_description": get_quality_description(quality_level),
                    "avatar": "🤖",
                    "company": company
                }
        
        # 기본 AI 지원자 정보
        return {
            "name": "춘식이",
            "experience": "3년",
            "specialties": ["백엔드 개발", "시스템 설계"],
            "quality_level": quality_level,
            "quality_description": get_quality_description(quality_level),
            "avatar": "🤖",
            "company": company
        }
        
    except Exception as e:
        interview_logger.error(f"AI 지원자 정보 조회 오류: {str(e)}")
        return {
            "name": "춘식이",
            "experience": "3년",
            "specialties": ["개발"],
            "quality_level": quality_level,
            "quality_description": "중급",
            "avatar": "🤖",
            "company": company
        }

def get_quality_description(level: int) -> str:
    """품질 레벨 설명"""
    quality_map = {
        1: "매우 부족함",
        2: "부족함", 
        3: "보통 이하",
        4: "보통",
        5: "보통 이상",
        6: "좋음",
        7: "매우 좋음",
        8: "우수함",
        9: "매우 우수함",
        10: "최고 수준"
    }
    return quality_map.get(level, "보통")

# 답변 평가
async def evaluate_answer_async(answer: str, question: Dict, session_id: str, state: ApplicationState):
    """비동기 답변 평가"""
    try:
        # PersonalizedInterviewSystem을 사용한 실제 평가
        session = state.get_session(session_id)
        personalized_session_id = session.get("personalized_session_id")
        
        if personalized_session_id:
            personalized_system = state.personalized_system
            
            # 답변 제출 및 평가
            evaluation = await asyncio.to_thread(
                personalized_system.submit_answer,
                personalized_session_id,
                question['id'],
                answer
            )
            
            if evaluation:
                return {
                    "score": evaluation.get('score', 70),
                    "feedback": evaluation.get('feedback', '답변이 제출되었습니다.'),
                    "detailed_evaluation": evaluation.get('detailed_feedback', '평가 완료'),
                    "strengths": evaluation.get('strengths', []),
                    "improvements": evaluation.get('improvements', []),
                    "category_scores": evaluation.get('category_scores', {})
                }
        
        # 기본 평가 로직
        score = 70
        if len(answer) > 100:
            score += 10
        if any(keyword in answer for keyword in question.get('keywords', [])):
            score += 15
        
        return {
            "score": min(score, 100),
            "feedback": "답변이 제출되었습니다.",
            "detailed_evaluation": "기본 평가 완료",
            "strengths": ["답변 제출 완료"],
            "improvements": ["더 자세한 설명 추가"],
            "category_scores": {}
        }
        
    except Exception as e:
        interview_logger.error(f"답변 평가 오류: {str(e)}")
        return {
            "score": 0,
            "feedback": "평가 중 오류가 발생했습니다.",
            "detailed_evaluation": "오류",
            "strengths": [],
            "improvements": [],
            "category_scores": {}
        }

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