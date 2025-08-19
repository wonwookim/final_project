import sys
import os
from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.posting import PostingResponse
from backend.services.existing_tables_service import existing_tables_service

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

posting_router = APIRouter(prefix="/posting", tags=["Posting"])

# 🟢 GET /posting – 채용공고 목록 조회
@posting_router.get("", response_model=List[PostingResponse])
async def get_posting_list():
    """모든 채용공고 조회 (회사, 직무 정보 포함)"""
    try:
        postings = await existing_tables_service.get_all_postings()
        
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
            
        return formatted_postings

    except Exception as e:
        # 로그 출력 (interview_logger 사용 시 추가)
        print(f"채용공고 조회 오류: {str(e)}")
        return []


# 🟢 GET /posting/{posting_id} – 채용공고 상세 조회
@posting_router.get("/{posting_id}", response_model=PostingResponse)
async def get_posting_detail(posting_id: int):
    """특정 채용공고 상세 조회"""
    try:
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

        return formatted_posting

    except HTTPException:
        raise
    except Exception as e:
        print(f"채용공고 상세 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 🟢 GET /posting/company/{company_id}/position/{position_id} – 회사+직군으로 채용공고 조회
@posting_router.get("/company/{company_id}/position/{position_id}", response_model=PostingResponse)
async def get_posting_by_company_and_position(company_id: int, position_id: int):
    """company_id와 position_id로 채용공고 조회"""
    try:
        posting = await existing_tables_service.get_posting_by_company_and_position_ids(company_id, position_id)

        if not posting:
            raise HTTPException(
                status_code=404, 
                detail=f"해당 회사(ID: {company_id})와 직군(ID: {position_id})에 맞는 채용공고를 찾을 수 없습니다"
            )

        formatted_posting = {
            "posting_id": posting.get("posting_id"),
            "company_id": posting.get("company_id"),
            "position_id": posting.get("position_id"),
            "company": posting.get("company", {}).get("name", "Unknown Company"),
            "position": posting.get("position", {}).get("position_name", "Unknown Position"),
            "content": posting.get("content", f"{posting.get('company', {}).get('name', '')} {posting.get('position', {}).get('position_name', '')} 채용공고")
        }

        return formatted_posting

    except HTTPException:
        raise
    except Exception as e:
        print(f"회사+직군별 채용공고 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
