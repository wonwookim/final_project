"""
면접 관련 API 라우터
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import Optional

from ..models import InterviewSettings, AnswerSubmission
from ...services.interview_service import InterviewService

router = APIRouter(prefix="/api/interview", tags=["interview"])

# 서비스 의존성
def get_interview_service() -> InterviewService:
    return InterviewService()

@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now()}

@router.post("/start")
async def start_interview(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 시작"""
    try:
        session_id = await service.start_interview(
            company=settings.company,
            position=settings.position,
            candidate_name=settings.candidate_name,
            documents=settings.documents
        )
        
        return {
            "session_id": session_id,
            "message": "면접이 시작되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"면접 시작 중 오류가 발생했습니다: {str(e)}")

@router.get("/question")
async def get_next_question(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """다음 질문 가져오기"""
    try:
        question_data = await service.get_next_question(session_id)
        
        if not question_data:
            return {"completed": True, "message": "모든 질문이 완료되었습니다."}
        
        return question_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문을 가져오는 중 오류가 발생했습니다: {str(e)}")

@router.post("/answer")
async def submit_answer(
    answer_data: AnswerSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """답변 제출"""
    try:
        result = await service.submit_answer(answer_data.session_id, answer_data.answer)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 제출 중 오류가 발생했습니다: {str(e)}")

@router.get("/results/{session_id}")
async def get_interview_results(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 결과 조회"""
    try:
        # 결과 생성 로직 (추후 구현)
        return {"message": "결과 조회 기능 구현 중"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과를 조회하는 중 오류가 발생했습니다: {str(e)}")

@router.get("/history")
async def get_interview_history(
    user_id: Optional[str] = None,
    service: InterviewService = Depends(get_interview_service)
):
    """면접 기록 조회"""
    try:
        # 기록 조회 로직 (추후 구현)
        return {
            "total_interviews": 0,
            "interviews": []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기록을 조회하는 중 오류가 발생했습니다: {str(e)}")