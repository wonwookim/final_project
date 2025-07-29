from database.services.existing_tables_service import existing_tables_service
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from database.supabase_client import supabase_client
from backend.schemas.posting import PostingResponse
from typing import List

posting_router = APIRouter(prefix="/posting", tags=["Posting"])

# 🟢 GET /posting – 채용공고 목록 조회
@posting_router.get("/", response_model=List[PostingResponse])
def get_posting_list():
    res = supabase_client.client.from_("posting").select("*").execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No postings found")
    return res.data

# 🟢 GET /posting/{posting_id} – 채용공고 상세 조회
@posting_router.get("/{posting_id}", response_model=PostingResponse)
def get_posting_detail(posting_id: int):
    res = supabase_client.client.from_("posting").select("*").eq("posting_id", posting_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No posting found")
    return res.data