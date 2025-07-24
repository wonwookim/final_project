"""
FastAPI 미들웨어 설정
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app: FastAPI):
    """미들웨어 설정"""
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 개발 환경에서만 사용
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )