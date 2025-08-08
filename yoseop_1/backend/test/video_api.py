"""
간단한 비디오 업로드/재생 API
"""

import os
import sys
import boto3
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

# 백엔드 서비스 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
from services.auth_service import AuthService, security
from services.supabase_client import get_supabase_client, get_user_supabase_client

router = APIRouter(prefix="/video", tags=["Video"])
auth_service = AuthService()

# AWS S3 클라이언트
print(f"[DEBUG] AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID', 'NOT SET')[:10]}...")
print(f"[DEBUG] AWS_SECRET_ACCESS_KEY: {'SET' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
print(f"[DEBUG] AWS_REGION: {os.getenv('AWS_REGION', 'ap-northeast-2')}")

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
    file_type: str = "video"  # video 또는 audio
    file_size: int = None
    duration: int = None

class TestUploadRequest(BaseModel):
    interview_id: int
    file_name: str
    file_type: str = "video"  # video 또는 audio
    file_size: int = None

@router.post("/upload-url")
async def get_upload_url(request: UploadRequest, current_user=Depends(auth_service.get_current_user)):
    """업로드용 Presigned URL 생성"""
    
    # S3 키 생성
    s3_key = f"interviews/{current_user.user_id}/{request.interview_id}/{request.file_name}"
    
    # Presigned URL 생성 (1시간 유효)
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME, 
            'Key': s3_key,
            'ContentType': 'video/webm' if request.file_type == 'video' else 'audio/webm'
        },
        ExpiresIn=3600
    )
    
    # DB에 레코드 생성
    supabase = get_supabase_client()
    try:
        result = supabase.table('media_files').insert({
            'user_id': current_user.user_id,
            'interview_id': request.interview_id,
            'file_name': request.file_name,
            'file_type': request.file_type,
            's3_key': s3_key,
            's3_url': f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
            'file_size': request.file_size,
            'duration': request.duration
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="DB 레코드 생성 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    
    return {
        'upload_url': upload_url,
        'media_id': result.data[0]['media_id']
    }

@router.post("/test/upload-url")
async def get_test_upload_url(
    request: TestUploadRequest, 
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """테스트용 업로드 Presigned URL 생성"""
    
    # S3 키 생성 (테스트용)
    print(f"[DEBUG] Current user info: {current_user}")
    s3_key = f"test-videos/{current_user.user_id}/{request.interview_id}/{request.file_name}"
    
    # Presigned URL 생성 (1시간 유효)
    print(f"[DEBUG] Generating presigned URL for: {s3_key}")
    print(f"[DEBUG] Bucket: {BUCKET_NAME}")
    
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME, 
            'Key': s3_key,
            'ContentType': 'video/webm' if request.file_type == 'video' else 'audio/webm'
        },
        ExpiresIn=3600
    )
    
    print(f"[DEBUG] Generated presigned URL: {upload_url[:100]}...")
    
    # 사용자 토큰을 사용한 테스트용 DB 레코드 생성
    user_token = credentials.credentials
    supabase = get_user_supabase_client(user_token)
    print(f"[DEBUG] Using user token for DB access: {user_token[:50]}...")
    
    try:
        result = supabase.table('media_files').insert({
            'user_id': current_user.user_id,
            'interview_id': 110,  # 테스트용으로 기존 interview_id 사용
            'file_name': request.file_name,
            'file_type': request.file_type,
            's3_key': s3_key,
            's3_url': f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{s3_key}",
            'file_size': request.file_size,
            'duration': None
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="DB 레코드 생성 실패")
            
    except Exception as e:
        print(f"[ERROR] DB insertion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    
    return {
        'upload_url': upload_url,
        'media_id': result.data[0]['media_id']
    }

@router.get("/play/{interview_id}")
async def get_play_url(interview_id: int, current_user=Depends(auth_service.get_current_user)):
    """재생용 Presigned URL 생성"""
    
    try:
        # DB에서 파일 정보 조회
        supabase = get_supabase_client()
        result = supabase.table('media_files').select('s3_key, file_name, file_type').eq('user_id', current_user.user_id).eq('interview_id', interview_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="비디오를 찾을 수 없습니다")
        
        # 가장 최근 파일 선택 (여러 파일이 있을 경우)
        file_info = result.data[0] if result.data else None
        if not file_info:
            raise HTTPException(status_code=404, detail="비디오를 찾을 수 없습니다")
            
        s3_key = file_info['s3_key']
        
        # Presigned URL 생성 (1시간 유효)  
        play_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        return {
            'play_url': play_url,
            'file_name': file_info['file_name'],
            'file_type': file_info['file_type']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재생 URL 생성 오류: {str(e)}")

@router.patch("/complete/{media_id}")
async def complete_upload(media_id: str, file_size: int = None, duration: int = None):
    """업로드 완료 처리 - 파일 크기와 지속시간 업데이트"""
    
    try:
        supabase = get_supabase_client()
        update_data = {'updated_at': 'now()'}
        
        if file_size:
            update_data['file_size'] = file_size
        if duration:
            update_data['duration'] = duration
            
        result = supabase.table('media_files').update(update_data).eq('media_id', media_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="미디어 파일을 찾을 수 없습니다")
            
        return {'message': '업로드 완료', 'media_id': media_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 완료 처리 오류: {str(e)}")