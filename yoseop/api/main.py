"""
FastAPI 메인 애플리케이션 - 간소화된 버전
"""
import os
import sys
from fastapi import FastAPI

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .middleware import setup_middleware
from .routes.interview import router as interview_router

# 데이터베이스 확장 임포트 (기존 유지)
try:
    from backend.extensions.database_integration import database_router
    from backend.extensions.migration_api import migration_router
    DATABASE_ENABLED = True
    print("✅ 데이터베이스 확장 로드 성공")
except ImportError as e:
    DATABASE_ENABLED = False
    print(f"⚠️ 데이터베이스 확장 로드 실패: {e}")

# FastAPI 앱 초기화
app = FastAPI(
    title="Beta-GO Interview API",
    description="AI 기반 개인화된 면접 시스템",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 미들웨어 설정
setup_middleware(app)

# 라우터 등록
app.include_router(interview_router)

# 데이터베이스 라우터 등록 (기존 유지)
if DATABASE_ENABLED:
    app.include_router(database_router)
    app.include_router(migration_router)
    print("✅ 데이터베이스 API 라우터 등록 완료")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Beta-GO Interview API v2.1",
        "version": "2.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/interview/health"
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Beta-GO Interview FastAPI v2.1 시작!")
    print("📱 브라우저에서 http://localhost:8000 접속")
    print("📚 API 문서: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )