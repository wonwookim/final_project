from fastapi import APIRouter, HTTPException
from typing import List
from database.supabase_client import supabase_client
from backend.schemas.history import InterviewHistoryResponse

history_router = APIRouter(prefix="/interview", tags=["Interview"])

# 🟢 GET /interview/history – 면접 히스토리 조회
@history_router.get("/history", response_model=List[InterviewHistoryResponse])
def get_interview_history(interview_id: int):
    res = supabase_client.table("interview_detail").select("*").eq("interview_id", interview_id).order("sequence").execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No interview history found")
    return res.data
