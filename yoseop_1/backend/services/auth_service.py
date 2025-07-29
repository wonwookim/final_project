# backend/services/auth_service.py
import sys
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.supabase_client import get_supabase_client
from backend.schemas.user import UserCreate, UserLogin, UserResponse, AuthResponse

# JWT 토큰 검증을 위한 보안 스키마
security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def signup(self, user_data: UserCreate) -> AuthResponse:
        """Supabase Auth를 이용한 회원가입 + User 테이블 동기화"""
        try:
            # 1. Supabase Auth에 사용자 등록 (이메일 인증 필요)
            auth_response = self.supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.pw,
                "options": {
                    "email_redirect_to": None,  # 이메일 인증 후 리다이렉트 없음
                    "data": {
                        "name": user_data.name
                    }
                }
            })
            
            if auth_response.user is None:
                raise HTTPException(
                    status_code=400, 
                    detail="회원가입에 실패했습니다. 이미 존재하는 이메일일 수 있습니다."
                )
            
            # 2. 이메일 인증이 필요한 경우 (session이 없는 경우)
            if auth_response.session is None:
                return {
                    "access_token": "",
                    "refresh_token": None,
                    "token_type": "bearer",
                    "user": {
                        "user_id": 0,  # 임시값 - 이메일 인증 완료 후 실제 ID 할당
                        "name": user_data.name,
                        "email": user_data.email
                    }
                }
            
            # 3. 이메일 인증이 완료된 경우 User 테이블에 저장
            auth_user_id = auth_response.user.id
            
            # User 테이블에 사용자 정보 저장 (auth_id 연결)
            user_insert = self.supabase.from_("User").insert({
                "auth_id": auth_user_id,
                "name": user_data.name,
                "email": user_data.email,
                "pw": ""  # Supabase Auth에서 관리하므로 빈 값
            }).execute()
            
            if not user_insert.data:
                raise HTTPException(status_code=500, detail="사용자 정보 저장에 실패했습니다.")
            
            user_info = user_insert.data[0]
            
            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
                user=UserResponse(
                    user_id=user_info["user_id"],
                    name=user_info["name"],
                    email=user_info["email"]
                )
            )
            
        except Exception as e:
            if "already been registered" in str(e):
                raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
            raise HTTPException(status_code=500, detail=f"회원가입 오류: {str(e)}")
    
    async def login(self, user_data: UserLogin) -> AuthResponse:
        """Supabase Auth를 이용한 로그인"""
        try:
            # Supabase Auth 로그인
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.pw
            })
            
            if auth_response.user is None or auth_response.session is None:
                raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
            
            # User 테이블에서 auth_id로 사용자 정보 조회
            auth_user_id = auth_response.user.id
            user_query = self.supabase.from_("User").select("*").eq("auth_id", auth_user_id).single().execute()
            
            if user_query.data:
                user_info = user_query.data
            else:
                # User 테이블에 정보가 없으면 생성 (이메일 인증 완료된 사용자)
                user_insert = self.supabase.from_("User").insert({
                    "auth_id": auth_user_id,
                    "name": auth_response.user.user_metadata.get("name", "사용자"),
                    "email": auth_response.user.email,
                    "pw": ""  # Supabase Auth에서 관리하므로 빈 값
                }).execute()
                
                if user_insert.data:
                    user_info = user_insert.data[0]
                else:
                    raise HTTPException(status_code=500, detail="사용자 정보 생성에 실패했습니다.")
            
            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
                user=UserResponse(
                    user_id=user_info["user_id"],
                    name=user_info["name"],
                    email=user_info["email"]
                )
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"로그인 오류: {str(e)}")
    
    async def logout(self, token: str) -> Dict[str, str]:
        """Supabase Auth 로그아웃"""
        try:
            # Supabase Auth 로그아웃
            self.supabase.auth.sign_out()
            return {"message": "로그아웃되었습니다."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"로그아웃 오류: {str(e)}")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Supabase JWT 토큰 검증"""
        try:
            # Supabase JWT 토큰 검증
            user_response = self.supabase.auth.get_user(token)
            
            if user_response.user is None:
                raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
            
            return {
                "user_id": user_response.user.id,
                "email": user_response.user.email,
                "name": user_response.user.user_metadata.get("name", "사용자")
            }
            
        except Exception as e:
            raise HTTPException(status_code=401, detail="토큰 검증에 실패했습니다.")
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
        """현재 인증된 사용자 정보 반환 (Depends로 사용)"""
        try:
            token = credentials.credentials
            
            # Supabase JWT 토큰 검증
            user_response = self.supabase.auth.get_user(token)
            
            if user_response.user is None:
                raise HTTPException(status_code=401, detail="인증이 필요합니다.")
            
            # User 테이블에서 auth_id로 상세 정보 조회
            auth_user_id = user_response.user.id
            user_query = self.supabase.from_("User").select("*").eq("auth_id", auth_user_id).single().execute()
            
            if not user_query.data:
                raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
            
            user_info = user_query.data
            return UserResponse(
                user_id=user_info["user_id"],
                name=user_info["name"],
                email=user_info["email"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail="사용자 인증에 실패했습니다.")

# 전역 서비스 인스턴스
auth_service = AuthService()

# 의존성 주입용 함수들
def get_auth_service() -> AuthService:
    return auth_service

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """현재 인증된 사용자 정보 반환 (FastAPI Depends용)"""
    return auth_service.get_current_user(credentials)