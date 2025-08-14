# === 김원우 작성 시작 ===
"""
시선 분석 시스템 라우터

이 모듈은 시선 분석과 캘리브레이션 관련 API 엔드포인트를 제공합니다.
기존 test/gaze_api.py의 기능을 표준 라우터 구조로 이전했습니다.

주요 기능:
- 4점 시선 캘리브레이션
- 동영상 시선 분석 
- 실시간 진행 상황 모니터링
- 분석 결과 조회

작성자: 김원우
작성일: 2025-08-12
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Form, UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict
import uuid
import shutil
from datetime import datetime
import os
import sys

# 백엔드 서비스 import를 위한 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import AuthService, security
from services.supabase_client import get_user_supabase_client
from schemas.gaze import (
    CalibrationStartRequest, CalibrationStartResponse, CalibrationStatusResponse,
    CalibrationResult, VideoAnalysisRequest, VideoAnalysisResponse, 
    GazeAnalysisResult, AnalysisStatusResponse, FrameFeedbackResponse,
    ErrorResponse
)

# 기존 gaze 모듈들 import (서비스 레이어로 이전 전까지 임시 사용)
try:
    from test.gaze_calibration import calibration_manager
    from test.gaze_analysis import gaze_analyzer, GazeAnalysisResult as GazeAnalyzerResultData
except ImportError as e:
    print(f"[WARNING] 기존 gaze 모듈 import 실패: {e}")
    calibration_manager = None
    gaze_analyzer = None

# 라우터 초기화
router = APIRouter(prefix="/gaze", tags=["Gaze Analysis"])
auth_service = AuthService()

# 분석 작업 상태 저장소 (실제 서비스에서는 Redis나 DB 사용 권장)
analysis_tasks: Dict[str, Dict] = {}
BUCKET_NAME = 'betago-s3'

# 임시 파일 저장 폴더
TEMP_GAZE_FOLDER = "backend/uploads/temp_gaze"


# === 임시 업로드 엔드포인트 ===

@router.post("/upload/temporary/{session_id}", tags=["Upload"])
async def upload_temporary_gaze_video(session_id: int, file: UploadFile = File(...)):
    """
    시선 추적 영상을 임시 폴더에 session_id를 파일명으로 하여 저장합니다.
    
    이 API는 빠른 응답을 위해 로컬 임시 폴더에만 저장하며,
    실제 Supabase 업로드와 분석은 나중에 백그라운드에서 처리됩니다.
    """
    try:
        # 임시 폴더 생성
        os.makedirs(TEMP_GAZE_FOLDER, exist_ok=True)
        
        # 파일 확장자 추출 (보안상 webm만 허용)
        if not file.filename or not file.filename.lower().endswith(('.webm', '.mp4')):
            raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. webm 또는 mp4 파일만 업로드 가능합니다.")
        
        # 파일 크기 제한 (100MB)
        if file.size and file.size > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="파일 크기가 너무 큽니다. 100MB 이하의 파일만 업로드 가능합니다.")
        
        # 파일 확장자 결정
        file_extension = file.filename.split('.')[-1].lower()
        file_path = os.path.join(TEMP_GAZE_FOLDER, f"{session_id}.{file_extension}")
        
        # 기존 파일이 있으면 덮어쓰기
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"✅ 임시 파일 저장 완료: {file_path} (크기: {file.size} bytes)")
        
        return {
            "message": "시선 추적 영상이 임시 저장되었습니다.",
            "session_id": session_id,
            "file_path": file_path,
            "file_size": file.size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 임시 파일 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 임시 저장 실패: {str(e)}")


# === 캘리브레이션 엔드포인트 ===

@router.post("/calibration/start", response_model=CalibrationStartResponse)
async def start_calibration(request: CalibrationStartRequest):
    """
    시선 캘리브레이션 시작
    
    4점 캘리브레이션 세션을 시작합니다.
    사용자는 화면의 네 모서리를 차례대로 응시해야 합니다.
    """
    try:
        if not calibration_manager:
            raise HTTPException(status_code=503, detail="캘리브레이션 서비스를 사용할 수 없습니다")
            
        session_id = calibration_manager.create_session(request.user_id)
        calibration_manager.start_calibration(session_id)
        
        return CalibrationStartResponse(
            session_id=session_id,
            status="started",
            message="캘리브레이션이 시작되었습니다."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캘리브레이션 시작 실패: {str(e)}")


@router.get("/calibration/status/{session_id}", response_model=CalibrationStatusResponse)
async def get_calibration_status(session_id: str):
    """
    캘리브레이션 진행 상태 조회
    
    현재 진행 단계, 진행률, 사용자 안내 메시지를 반환합니다.
    """
    try:
        if not calibration_manager:
            raise HTTPException(status_code=503, detail="캘리브레이션 서비스를 사용할 수 없습니다")
            
        status = calibration_manager.get_session_status(session_id)
        if status is None:
            raise HTTPException(status_code=404, detail="캘리브레이션 세션을 찾을 수 없습니다.")
            
        return CalibrationStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.post("/calibration/frame/{session_id}", response_model=FrameFeedbackResponse)
async def process_calibration_frame(session_id: str, frame_data: str = Form(...)):
    """
    캘리브레이션 프레임 처리
    
    웹캠에서 캡처된 프레임을 처리하여 시선 데이터를 수집합니다.
    실시간 피드백을 제공합니다.
    """
    try:
        if not calibration_manager:
            raise HTTPException(status_code=503, detail="캘리브레이션 서비스를 사용할 수 없습니다")
            
        # Base64 데이터 헤더 제거
        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]
        
        import base64
        import numpy as np
        import cv2
        
        try:
            image_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                raise HTTPException(status_code=400, detail="Failed to decode frame")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 frame data")

        result = calibration_manager.process_frame(session_id, frame)
        if result is None:
            raise HTTPException(status_code=404, detail="Calibration session not found")
            
        return FrameFeedbackResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프레임 처리 실패: {str(e)}")


@router.get("/calibration/result/{session_id}", response_model=CalibrationResult)
async def get_calibration_result(session_id: str):
    """
    캘리브레이션 결과 조회
    
    완료된 캘리브레이션의 4점 좌표와 허용 범위를 반환합니다.
    """
    try:
        if not calibration_manager:
            raise HTTPException(status_code=503, detail="캘리브레이션 서비스를 사용할 수 없습니다")
            
        result = calibration_manager.get_calibration_result(session_id)
        if result is None or not result.get('calibration_points'):
            raise HTTPException(
                status_code=404, 
                detail="캘리브레이션 결과를 찾을 수 없거나 아직 완료되지 않았습니다."
            )
        
        # 허용 범위 계산 (gaze_analyzer 사용)
        calibration_points = result.get('calibration_points', [])
        print(f"🎯 [DEBUG] Calibration points count: {len(calibration_points)}")
        print(f"🎯 [DEBUG] Calibration points: {calibration_points}")
        
        if len(calibration_points) == 4 and gaze_analyzer:
            # GazeAnalyzer의 범위 계산 로직 재사용
            allowed_range = gaze_analyzer.calculate_allowed_gaze_range(calibration_points)
            result['allowed_range'] = allowed_range
            print(f"🎯 [DEBUG] Calculated allowed range: {allowed_range}")
        else:
            print(f"🎯 [DEBUG] Not enough calibration points for range calculation")
        
        return CalibrationResult(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 조회 실패: {str(e)}")


# === 동영상 분석 엔드포인트 ===

@router.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_gaze(
    request: VideoAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(auth_service.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    동영상 시선 분석 시작
    
    업로드된 동영상에서 시선을 분석하여 집중도와 안정성을 측정합니다.
    분석은 백그라운드에서 진행되며, 상태 조회 API로 진행 상황을 확인할 수 있습니다.
    """
    try:
        if not gaze_analyzer or not calibration_manager:
            raise HTTPException(status_code=503, detail="시선 분석 서비스를 사용할 수 없습니다")
            
        # video_url 형식 검증
        if not request.video_url.startswith('http://127.0.0.1:8000/video/play/'):
            raise HTTPException(status_code=400, detail="유효하지 않은 video_url 형식입니다.")
        
        media_id = request.video_url.split('/')[-1]

        # 캘리브레이션 결과 조회
        calib_result = calibration_manager.get_calibration_result(request.session_id)
        if not calib_result or len(calib_result.get('calibration_points', [])) != 4:
            raise HTTPException(
                status_code=404, 
                detail="유효한 캘리브레이션 데이터를 찾을 수 없습니다."
            )
        
        calibration_points = calib_result['calibration_points']
        initial_face_size = calib_result.get('initial_face_size')

        # 미디어 파일 존재 확인
        supabase = get_user_supabase_client(credentials.credentials)
        db_result = supabase.table('media_files').select('s3_key').eq('media_id', media_id).eq('user_id', current_user.user_id).execute()

        if not db_result.data:
            raise HTTPException(
                status_code=404, 
                detail=f"미디어 파일(ID: {media_id})을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        s3_key = db_result.data[0]['s3_key']

        # 분석 작업 생성
        task_id = str(uuid.uuid4())
        analysis_tasks[task_id] = {
            'task_id': task_id,
            'status': 'processing',
            'progress': 0.0,
            'message': '분석 작업을 대기열에 추가했습니다.',
            'started_at': datetime.now()
        }

        # 백그라운드 분석 시작
        background_tasks.add_task(
            run_video_analysis,
            task_id,
            BUCKET_NAME,
            s3_key,
            calibration_points,
            initial_face_size
        )

        return VideoAnalysisResponse(
            task_id=task_id,
            status="processing",
            message="동영상 시선 분석이 시작되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 시작 오류: {str(e)}")


@router.get("/analyze/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """
    시선 분석 진행 상태 조회
    
    분석 진행률, 현재 단계, 결과 등을 조회합니다.
    """
    try:
        if task_id not in analysis_tasks:
            raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
        
        task = analysis_tasks[task_id]
        return AnalysisStatusResponse(**task)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


# === 백그라운드 분석 작업 ===

async def run_video_analysis(
    task_id: str, 
    bucket: str, 
    key: str, 
    calibration_points: list, 
    initial_face_size: float
):
    """
    백그라운드에서 동영상 시선 분석 실행
    
    S3에서 동영상을 다운로드하고 MediaPipe로 시선을 추적하여
    집중도와 안정성 점수를 계산합니다.
    """
    try:
        print(f"🚀 [ANALYSIS] Task ID: {task_id} - 분석 시작")
        print(f"   - S3 Path: s3://{bucket}/{key}")
        start_time = datetime.now()
        
        analysis_tasks[task_id]['progress'] = 0.1
        analysis_tasks[task_id]['message'] = "분석 엔진 초기화 중..."

        if not gaze_analyzer:
            raise ValueError("시선 분석 엔진을 사용할 수 없습니다")

        # 시선 분석 실행
        result: GazeAnalyzerResultData = gaze_analyzer.analyze_video(
            bucket=bucket,
            key=key,
            calibration_points=calibration_points,
            initial_face_size=initial_face_size,
            frame_skip=10
        )
        
        end_time = datetime.now()
        analysis_duration = (end_time - start_time).total_seconds()
        
        print(f"✅ [ANALYSIS] Task ID: {task_id} - 분석 완료 ({analysis_duration:.2f}초)")

        # 최소 데이터 검증
        MIN_ANALYZED_FRAMES = 30
        if result.analyzed_frames < MIN_ANALYZED_FRAMES:
            print(f"⚠️ [ANALYSIS] 데이터 부족: 분석된 프레임 {result.analyzed_frames}개 < 최소 기준 {MIN_ANALYZED_FRAMES}개")
            raise ValueError(
                f"분석에 사용된 데이터가 너무 적습니다({result.analyzed_frames} 프레임). "
                f"10초 이상 선명한 영상을 다시 녹화해주세요."
            )
        
        # 결과 저장
        analysis_tasks[task_id].update({
            'status': 'completed',
            'progress': 1.0,
            'message': '분석이 성공적으로 완료되었습니다.',
            'completed_at': end_time,
            'result': GazeAnalysisResult(
                gaze_score=result.gaze_score,
                total_frames=result.total_frames,
                analyzed_frames=result.analyzed_frames,
                in_range_frames=result.in_range_frames,
                in_range_ratio=result.in_range_ratio,
                jitter_score=result.jitter_score,
                compliance_score=result.compliance_score,
                stability_rating=result.stability_rating,
                feedback=result.feedback,
                gaze_points=result.gaze_points,
                analysis_duration=analysis_duration,
                allowed_range=result.allowed_range,
                calibration_points=result.calibration_points
            )
        })

    except Exception as e:
        import traceback
        print(f"❌ [ANALYSIS] Task ID: {task_id} - 분석 실패")
        traceback.print_exc()
        
        analysis_tasks[task_id].update({
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now()
        })


# === 기타 유틸리티 엔드포인트 ===

@router.get("/tasks")
async def list_analysis_tasks():
    """
    진행 중인 분석 작업 목록 조회 (디버깅용)
    """
    return {
        "active_tasks": len([t for t in analysis_tasks.values() if t['status'] == 'processing']),
        "completed_tasks": len([t for t in analysis_tasks.values() if t['status'] == 'completed']),
        "failed_tasks": len([t for t in analysis_tasks.values() if t['status'] == 'failed']),
        "tasks": list(analysis_tasks.keys())[-10:]  # 최근 10개만 표시
    }


@router.delete("/tasks/{task_id}")
async def delete_analysis_task(task_id: str):
    """
    완료된 분석 작업 삭제
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    
    if analysis_tasks[task_id]['status'] == 'processing':
        raise HTTPException(status_code=400, detail="진행 중인 작업은 삭제할 수 없습니다.")
    
    del analysis_tasks[task_id]
    return {"message": "분석 작업이 삭제되었습니다.", "task_id": task_id}


# 라우터 내보내기 함수 (기존 gaze_api.py 호환성)
def get_gaze_router():
    """기존 gaze_api.py의 get_gaze_router() 함수 호환성"""
    return router


# 라우터 내보내기
gaze_router = router
# === 김원우 작성 끝 ===