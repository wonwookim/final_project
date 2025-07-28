from fastapi import APIRouter, HTTPException
from typing import List
from database.supabase_client import supabase_client
from backend.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse

resume_router = APIRouter(prefix="/resume", tags=["Resume"])

# 🟢 GET /resume – 내 이력서 목록 조회
@resume_router.get("/", response_model=List[ResumeResponse])
def get_resumes(user_id: int):
    res = supabase_client.client.from_("user_resume").select("*").eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No resumes found")
    return res.data

# 🟡 POST /resume – 이력서 생성
@resume_router.post("/", response_model=ResumeResponse)
def create_resume(user_id: int, resume: ResumeCreate):
    data = {**resume.dict(), "user_id": user_id}
    res = supabase_client.client.from_("user_resume").insert(data).execute()
    return res.data[0]

# 🟢 GET /resume/{resume_id} – 이력서 상세 조회
@resume_router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int):
    res = supabase_client.client.from_("user_resume").select("*").eq("user_resume_id", resume_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    return res.data

# 🔵 PUT /resume/{resume_id} – 이력서 수정
@resume_router.put("/{resume_id}", response_model=ResumeResponse)
def update_resume(resume_id: int, resume: ResumeUpdate):
    res = supabase_client.client.from_("user_resume").update(resume.dict()).eq("user_resume_id", resume_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    return res.data[0]

# 🔴 DELETE /resume/{resume_id} – 이력서 삭제
@resume_router.delete("/{resume_id}")
def delete_resume(resume_id: int):
    res = supabase_client.client.from_("user_resume").delete().eq("user_resume_id", resume_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"message": "Resume deleted"}
