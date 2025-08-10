"""
시선 분석 FastAPI 엔드포인트
4포인트 캘리브레이션과 동영상 시선 분석 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
import asyncio
import json
import cv2
import numpy as np
import base64
from datetime import datetime
import uuid

from .gaze_calibration import calibration_manager
from .gaze_analysis import gaze_analyzer


# Pydantic 모델들
class CalibrationStartRequest(BaseModel):
    user_id: Optional[str] = None


class CalibrationStartResponse(BaseModel):
    session_id: str
    status: str
    message: str


class CalibrationStatusResponse(BaseModel):
    session_id: str
    current_phase: str
    elapsed_time: float
    is_collecting: bool
    collected_points: Dict[str, int]
    progress: float
    instructions: str
    # 실시간 피드백 필드 추가
    eye_detected: Optional[bool] = None
    face_quality: Optional[str] = None
    remaining_time: Optional[int] = None
    collected_count: Optional[int] = None
    target_count: Optional[int] = None
    collection_progress: Optional[float] = None
    feedback: Optional[str] = None


class FrameProcessResponse(BaseModel):
    status: str
    phase: str
    eye_detected: bool
    face_quality: str
    feedback: str
    collected_count: Optional[int] = None
    target_count: Optional[int] = None
    remaining_time: Optional[int] = None
    collection_progress: Optional[float] = None


class CalibrationResult(BaseModel):
    session_id: str
    calibration_points: List[Tuple[float, float]]
    point_details: Dict[str, Dict]
    collection_stats: Dict[str, int]
    completed_at: float


class VideoAnalysisRequest(BaseModel):
    video_url: str
    session_id: str  # 캘리브레이션 세션 ID


class VideoAnalysisResponse(BaseModel):
    task_id: str
    status: str
    message: str


class GazeAnalysisResult(BaseModel):
    gaze_score: int
    total_frames: int
    analyzed_frames: int
    in_range_frames: int
    in_range_ratio: float
    jitter_score: int
    stability_rating: str
    feedback: str
    gaze_points: List[Tuple[float, float]]
    analysis_duration: float


class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: str  # 'processing', 'completed', 'failed'
    progress: Optional[float] = None
    result: Optional[GazeAnalysisResult] = None
    error: Optional[str] = None


# 분석 작업 상태 관리
analysis_tasks: Dict[str, Dict] = {}


# FastAPI 라우터 생성
router = APIRouter(prefix="/test/gaze", tags=["Gaze Analysis"])


@router.post("/calibration/start", response_model=CalibrationStartResponse)
async def start_calibration(request: CalibrationStartRequest):
    """새로운 캘리브레이션 세션 시작"""
    try:
        session_id = calibration_manager.create_session(request.user_id)
        success = calibration_manager.start_calibration(session_id)
        
        if success:
            return CalibrationStartResponse(
                session_id=session_id,
                status="started",
                message="캘리브레이션이 시작되었습니다. 화면 좌상단을 응시하세요."
            )
        else:
            raise HTTPException(status_code=500, detail="캘리브레이션 시작에 실패했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캘리브레이션 시작 오류: {str(e)}")


@router.get("/calibration/status/{session_id}", response_model=CalibrationStatusResponse)
async def get_calibration_status(session_id: str):
    """캘리브레이션 세션 상태 조회"""
    status = calibration_manager.get_session_status(session_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="캘리브레이션 세션을 찾을 수 없습니다.")
    
    return CalibrationStatusResponse(**status)


@router.get("/calibration/result/{session_id}", response_model=CalibrationResult)
async def get_calibration_result(session_id: str):
    """캘리브레이션 결과 조회"""
    result = calibration_manager.get_calibration_result(session_id)
    
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail="캘리브레이션 결과를 찾을 수 없거나 아직 완료되지 않았습니다."
        )
    
    return CalibrationResult(**result)


@router.post("/calibration/frame/{session_id}", response_model=FrameProcessResponse)
async def process_frame(session_id: str, frame_data: str = Form(...)):
    """웹캠 프레임을 받아서 시선 추적 처리"""
    try:
        # Base64 디코딩
        try:
            # data:image/jpeg;base64, 접두사 제거
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]
            
            # Base64 디코딩
            image_bytes = base64.b64decode(frame_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid frame data: {str(e)}")
        
        # 이미지 디코딩
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Failed to decode frame")
        
        # 캘리브레이션 처리
        result = calibration_manager.process_frame(session_id, frame)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Calibration session not found")
        
        # 응답 데이터 구성
        response_data = {
            'status': result.get('status', 'unknown'),
            'phase': result.get('phase', 'unknown'),
            'eye_detected': result.get('eye_detected', False),
            'face_quality': result.get('face_quality', 'unknown'),
            'feedback': result.get('feedback', 'No feedback available')
        }
        
        # 선택적 필드들 추가
        optional_fields = ['collected_count', 'target_count', 'remaining_time', 'collection_progress']
        for field in optional_fields:
            if field in result:
                response_data[field] = result[field]
        
        return FrameProcessResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame processing error: {str(e)}")


def process_calibration_frame(session_id: str, frame_data: bytes):
    """캘리브레이션 프레임 처리 (웹캠 스트림용)"""
    try:
        # bytes를 numpy array로 변환
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return None
        
        # 캘리브레이션 처리
        result = calibration_manager.process_frame(session_id, frame)
        return result
        
    except Exception as e:
        print(f"프레임 처리 오류: {e}")
        return None


@router.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest, background_tasks: BackgroundTasks):
    """동영상 시선 분석 시작"""
    try:
        # 캘리브레이션 결과 확인 (완화된 버전)
        calibration_result = calibration_manager.get_calibration_result(request.session_id)
        if calibration_result is None:
            print(f"⚠️ [ANALYSIS] 캘리브레이션 데이터 없음, 기본값으로 진행")
            # 기본 캘리브레이션 결과 생성
            calibration_result = {
                'calibration_points': [
                    (160, 120),   # 좌상단
                    (480, 120),   # 우상단  
                    (160, 360),   # 좌하단
                    (480, 360)    # 우하단
                ]
            }
        
        # 분석 작업 ID 생성
        task_id = str(uuid.uuid4())
        
        # 작업 상태 초기화
        analysis_tasks[task_id] = {
            'status': 'processing',
            'progress': 0.0,
            'started_at': datetime.now(),
            'video_url': request.video_url,
            'session_id': request.session_id,
            'calibration_points': calibration_result['calibration_points']
        }
        
        # 백그라운드에서 분석 시작
        background_tasks.add_task(
            run_video_analysis, 
            task_id, 
            request.video_url, 
            calibration_result['calibration_points']
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


async def run_video_analysis(task_id: str, video_url: str, calibration_points: List[Tuple[float, float]]):
    """백그라운드에서 동영상 분석 실행 (향상된 로깅 포함)"""
    try:
        print(f"🔍 [ANALYSIS] 분석 시작 - Task ID: {task_id}")
        print(f"🔍 [ANALYSIS] Video URL: {video_url}")
        print(f"🔍 [ANALYSIS] Calibration Points: {calibration_points}")
        
        start_time = datetime.now()
        
        # 캘리브레이션 데이터 유효성 검증 (완화된 버전)
        if not calibration_points or len(calibration_points) != 4:
            print(f"⚠️ [ANALYSIS] 캘리브레이션 데이터 부족: {len(calibration_points) if calibration_points else 0}개 포인트, 기본값 사용")
            # 기본 캘리브레이션 포인트 생성
            calibration_points = [
                (160, 120),   # 좌상단
                (480, 120),   # 우상단  
                (160, 360),   # 좌하단
                (480, 360)    # 우하단
            ]
            print(f"✅ [ANALYSIS] 기본 캘리브레이션 포인트 적용: {calibration_points}")
        
        # 진행 상황 업데이트
        analysis_tasks[task_id]['progress'] = 0.1
        analysis_tasks[task_id]['message'] = "동영상 다운로드 중..."
        print(f"📥 [ANALYSIS] 동영상 다운로드 시작")
        
        # 동영상 분석 실행
        print(f"🔄 [ANALYSIS] gaze_analyzer.analyze_video 호출")
        analysis_tasks[task_id]['progress'] = 0.2
        analysis_tasks[task_id]['message'] = "동영상 분석 중..."
        
        result = gaze_analyzer.analyze_video(
            video_path_or_url=video_url,
            calibration_points=calibration_points,
            frame_skip=10  # 성능 최적화
        )
        
        print(f"✅ [ANALYSIS] 분석 완료")
        
        end_time = datetime.now()
        analysis_duration = (end_time - start_time).total_seconds()
        
        # 결과 저장
        analysis_tasks[task_id].update({
            'status': 'completed',
            'progress': 1.0,
            'completed_at': end_time,
            'result': GazeAnalysisResult(
                gaze_score=result.gaze_score,
                total_frames=result.total_frames,
                analyzed_frames=result.analyzed_frames,
                in_range_frames=result.in_range_frames,
                in_range_ratio=result.in_range_ratio,
                jitter_score=result.jitter_score,
                stability_rating=result.stability_rating,
                feedback=result.feedback,
                gaze_points=result.gaze_points,
                analysis_duration=analysis_duration
            )
        })
        
        print(f"🎉 [ANALYSIS] 결과 저장 완료 - 점수: {result.gaze_score}")
        
    except Exception as e:
        # 오류 처리
        error_msg = str(e)
        print(f"❌ [ANALYSIS] 분석 실패: {error_msg}")
        print(f"❌ [ANALYSIS] 예외 타입: {type(e).__name__}")
        
        import traceback
        traceback.print_exc()
        
        analysis_tasks[task_id].update({
            'status': 'failed',
            'error': error_msg,
            'failed_at': datetime.now()
        })


@router.get("/analyze/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """분석 작업 상태 조회"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    
    task = analysis_tasks[task_id]
    
    response = AnalysisStatusResponse(
        task_id=task_id,
        status=task['status'],
        progress=task.get('progress'),
        error=task.get('error')
    )
    
    # 완료된 경우 결과 포함
    if task['status'] == 'completed' and 'result' in task:
        response.result = task['result']
    
    return response


@router.delete("/analyze/{task_id}")
async def cleanup_analysis_task(task_id: str):
    """분석 작업 정리"""
    if task_id in analysis_tasks:
        del analysis_tasks[task_id]
        return {"message": "작업이 정리되었습니다."}
    else:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")


@router.get("/debug/tasks")
async def get_all_tasks():
    """디버그: 현재 모든 분석 작업 상태 조회"""
    return {
        "total_tasks": len(analysis_tasks),
        "tasks": {
            task_id: {
                "status": task.get("status"),
                "progress": task.get("progress"),
                "started_at": task.get("started_at").isoformat() if task.get("started_at") else None,
                "error": task.get("error"),
                "video_url": task.get("video_url"),
                "session_id": task.get("session_id")
            }
            for task_id, task in analysis_tasks.items()
        }
    }


@router.get("/debug/calibration/{session_id}")
async def get_calibration_debug(session_id: str):
    """디버그: 캘리브레이션 데이터 상세 조회"""
    result = calibration_manager.get_calibration_result(session_id)
    if result is None:
        return {"error": "캘리브레이션 세션을 찾을 수 없습니다."}
    
    return {
        "session_id": session_id,
        "calibration_result": result,
        "points_count": len(result.get('calibration_points', [])),
        "is_valid": len(result.get('calibration_points', [])) == 4
    }


@router.post("/test/force_complete/{session_id}")
async def force_complete_calibration(session_id: str):
    """테스트: 캘리브레이션 강제 완료"""
    try:
        # 세션 직접 접근
        if session_id in calibration_manager.sessions:
            session = calibration_manager.sessions[session_id]
            
            # 모든 단계에 기본 데이터 생성
            for phase in calibration_manager.calibration_phases:
                if len(session.calibration_points[phase]) == 0:
                    calibration_manager._generate_default_points(session, phase)
            
            # 강제 완료
            calibration_manager._complete_calibration(session)
            
            return {
                "message": "캘리브레이션 강제 완료됨",
                "session_id": session_id,
                "final_points": calibration_manager._get_final_points_list(session)
            }
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"강제 완료 실패: {str(e)}")


@router.get("/calibration/cleanup")
async def cleanup_old_sessions():
    """오래된 캘리브레이션 세션 정리"""
    cleaned_count = calibration_manager.cleanup_old_sessions(max_age_hours=24)
    return {"message": f"{cleaned_count}개의 오래된 세션이 정리되었습니다."}


@router.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_calibration_sessions": len(calibration_manager.sessions),
        "active_analysis_tasks": len(analysis_tasks)
    }


# 웹캠 스트림용 엔드포인트 (선택적)
@router.get("/calibration/stream/{session_id}")
async def calibration_video_stream(session_id: str):
    """캘리브레이션용 웹캠 스트림 (선택적 구현)"""
    # 실시간 웹캠 스트림은 프론트엔드에서 직접 처리하는 것이 더 효율적
    # 이 엔드포인트는 필요시 구현
    raise HTTPException(status_code=501, detail="웹캠 스트림은 프론트엔드에서 처리됩니다.")


# 라우터를 main.py에 등록할 때 사용
def get_gaze_router():
    """시선 분석 라우터 반환"""
    return router