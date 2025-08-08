"""
간단한 비디오 업로드/재생 API
"""

import os
import boto3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.services.auth_service import AuthService
from backend.services.supabase_client import get_supabase_client

router = APIRouter(prefix="/video", tags=["Video"])
auth_service = AuthService()

# AWS S3 클라이언트
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
)

BUCKET_NAME = 'betago-s3'

class UploadRequest(BaseModel):
    interview_id: int
    file_name: str

@router.post("/upload-url")
async def get_upload_url(request: UploadRequest, current_user=Depends(auth_service.get_current_user_dependency)):
    """업로드용 Presigned URL 생성"""
    
    # S3 키 생성
    s3_key = f"interviews/{current_user.user_id}/{request.interview_id}/{request.file_name}"
    
    # Presigned URL 생성 (1시간 유효)
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600
    )
    
    # DB에 레코드 생성
    supabase = get_supabase_client()
    result = supabase.table('media_files').insert({
        'user_id': current_user.user_id,
        'interview_id': request.interview_id,
        'file_name': request.file_name,
        's3_key': s3_key,
        's3_url': f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
        'upload_status': 'uploading'
    }).execute()
    
    return {
        'upload_url': upload_url,
        'media_id': result.data[0]['media_id']
    }

@router.get("/play/{interview_id}")
async def get_play_url(interview_id: int, current_user=Depends(auth_service.get_current_user_dependency)):
    """재생용 Presigned URL 생성"""
    
    # DB에서 파일 정보 조회
    supabase = get_supabase_client()
    result = supabase.table('media_files').select('s3_key').eq('user_id', current_user.user_id).eq('interview_id', interview_id).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="비디오를 찾을 수 없습니다")
    
    s3_key = result.data['s3_key']
    
    # Presigned URL 생성 (1시간 유효)  
    play_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600
    )
    
    return {'play_url': play_url}

@router.patch("/complete/{media_id}")
async def complete_upload(media_id: str):
    """업로드 완료 처리"""
    
    supabase = get_supabase_client()
    supabase.table('media_files').update({
        'upload_status': 'completed'
    }).eq('media_id', media_id).execute()
    
    return {'message': '업로드 완료'}