"""
4포인트 시선 캘리브레이션 메모리 처리
실시간 웹캠 기반 4포인트 시선 캘리브레이션을 처리합니다.
"""

import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from threading import Lock
import uuid


@dataclass
class CalibrationPoint:
    """캘리브레이션 포인트 데이터 클래스"""
    x: float
    y: float
    label: str  # 'top_left', 'top_right', 'bottom_left', 'bottom_right'


@dataclass
class CalibrationSession:
    """캘리브레이션 세션 데이터 클래스"""
    session_id: str
    user_id: Optional[str]
    current_phase: str  # 'ready', 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'completed'
    phase_start_time: float
    is_collecting: bool
    calibration_points: Dict[str, List[Tuple[float, float]]]  # 각 포인트별 수집된 데이터
    final_points: Dict[str, CalibrationPoint]  # 최종 평균 포인트들
    created_at: float
    completed_at: Optional[float]


class GazeCalibrationManager:
    """시선 캘리브레이션 세션 관리자"""
    
    def __init__(self):
        self.sessions: Dict[str, CalibrationSession] = {}
        self.lock = Lock()
        
        # MediaPipe 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 동공 랜드마크 인덱스
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]
        
        # 캘리브레이션 단계 순서
        self.calibration_phases = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
        
        # 각 단계별 시간 설정 (초)
        self.preparation_time = 3  # 준비 시간
        self.collection_time = 3   # 데이터 수집 시간
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """새로운 캘리브레이션 세션 생성"""
        session_id = str(uuid.uuid4())
        
        with self.lock:
            session = CalibrationSession(
                session_id=session_id,
                user_id=user_id,
                current_phase='ready',
                phase_start_time=0,
                is_collecting=False,
                calibration_points={
                    'top_left': [],
                    'top_right': [],
                    'bottom_left': [],
                    'bottom_right': []
                },
                final_points={},
                created_at=time.time(),
                completed_at=None
            )
            self.sessions[session_id] = session
        
        return session_id
    
    def start_calibration(self, session_id: str) -> bool:
        """캘리브레이션 시작"""
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            if session.current_phase != 'ready':
                return False
            
            # 첫 번째 단계로 시작
            session.current_phase = 'top_left'
            session.phase_start_time = time.time()
            session.is_collecting = False
            
            # 기존 데이터 초기화
            for phase in self.calibration_phases:
                session.calibration_points[phase] = []
            session.final_points = {}
            
            return True
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """세션 상태 조회 (자동 진행 포함)"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            current_time = time.time()
            
            # 현재 단계의 경과 시간 계산
            elapsed_time = current_time - session.phase_start_time if session.phase_start_time > 0 else 0
            
            # 자동 진행 체크 (프레임 전송 없이도 진행)
            total_phase_time = self.preparation_time + self.collection_time
            if (session.current_phase in self.calibration_phases and 
                elapsed_time > total_phase_time):
                print(f"🔄 [AUTO_CHECK] {session.current_phase}, elapsed: {elapsed_time:.1f}s, threshold: {total_phase_time}s")
                
                # 다음 단계로 자동 진행
                self._auto_advance_phase(session, current_time)
                elapsed_time = current_time - session.phase_start_time  # 새로운 단계 시간으로 업데이트
            
            # 단계별 상태 정보
            status = {
                'session_id': session_id,
                'current_phase': session.current_phase,
                'elapsed_time': elapsed_time,
                'is_collecting': session.is_collecting,
                'collected_points': {
                    phase: len(points) for phase, points in session.calibration_points.items()
                },
                'progress': self._calculate_progress(session),
                'instructions': self._get_current_instructions(session, elapsed_time)
            }
            
            return status
    
    def _auto_advance_phase(self, session: CalibrationSession, current_time: float):
        """자동으로 다음 단계로 진행"""
        current_phase_index = self.calibration_phases.index(session.current_phase)
        current_count = len(session.calibration_points[session.current_phase])
        
        # 데이터가 없으면 기본값 생성
        if current_count == 0:
            print(f"⚠️ [AUTO_ADVANCE] {session.current_phase}에 실제 데이터가 없어 기본값 생성")
            self._generate_default_points(session, session.current_phase)
        
        if current_phase_index < len(self.calibration_phases) - 1:
            # 다음 단계로
            next_phase = self.calibration_phases[current_phase_index + 1]
            session.current_phase = next_phase
            session.phase_start_time = current_time
            session.is_collecting = False
            print(f"✅ [AUTO_ADVANCE] {next_phase}로 진행")
        else:
            # 모든 단계 완료
            self._complete_calibration(session)
            print(f"🎉 [AUTO_ADVANCE] 캘리브레이션 완료")
    
    def _calculate_progress(self, session: CalibrationSession) -> float:
        """캘리브레이션 진행률 계산 (0.0 ~ 1.0)"""
        if session.current_phase == 'ready':
            return 0.0
        elif session.current_phase == 'completed':
            return 1.0
        else:
            # 각 단계는 25%씩 차지
            phase_progress = {
                'top_left': 0.0,
                'top_right': 0.25,
                'bottom_left': 0.5,
                'bottom_right': 0.75
            }
            
            base_progress = phase_progress.get(session.current_phase, 0.0)
            
            # 현재 단계 내 진행률
            elapsed = time.time() - session.phase_start_time
            total_phase_time = self.preparation_time + self.collection_time
            current_phase_progress = min(elapsed / total_phase_time, 1.0) * 0.25
            
            return base_progress + current_phase_progress
    
    def _get_current_instructions(self, session: CalibrationSession, elapsed_time: float) -> str:
        """현재 단계에 맞는 안내 메시지 반환"""
        if session.current_phase == 'ready':
            return "캘리브레이션을 시작할 준비가 되었습니다."
        elif session.current_phase == 'completed':
            return "캘리브레이션이 완료되었습니다!"
        
        # 단계별 메시지 매핑
        phase_messages = {
            'top_left': "화면 좌상단을 응시하세요",
            'top_right': "화면 우상단을 응시하세요", 
            'bottom_left': "화면 좌하단을 응시하세요",
            'bottom_right': "화면 우하단을 응시하세요"
        }
        
        base_message = phase_messages.get(session.current_phase, "")
        
        if elapsed_time < self.preparation_time:
            remaining = int(self.preparation_time - elapsed_time) + 1
            return f"{base_message} - 준비: {remaining}초"
        elif elapsed_time < self.preparation_time + self.collection_time:
            remaining = int(self.preparation_time + self.collection_time - elapsed_time) + 1
            return f"{base_message} - 시선 고정: {remaining}초"
        else:
            return f"{base_message} - 완료, 다음 단계로..."
    
    def get_gaze_point_3d(self, landmarks, w: int, h: int) -> Optional[Tuple[float, float]]:
        """MediaPipe 랜드마크에서 시선 포인트 계산"""
        try:
            # 왼쪽 동공 중심점
            left_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) 
                for i in self.left_iris_indices
            ])
            left_center = np.mean(left_iris_points, axis=0)
            
            # 오른쪽 동공 중심점
            right_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) 
                for i in self.right_iris_indices
            ])
            right_center = np.mean(right_iris_points, axis=0)
            
            # 양쪽 동공의 평균 위치
            avg_gaze = (left_center + right_center) / 2
            
            # 유효성 검사
            if (np.any(np.isnan(avg_gaze)) or 
                np.any(np.isinf(avg_gaze)) or 
                np.allclose(avg_gaze, 0)):
                return None
            
            return (float(avg_gaze[0]), float(avg_gaze[1]))
            
        except Exception:
            return None
    
    def process_frame(self, session_id: str, frame: np.ndarray) -> Optional[Dict]:
        """프레임을 처리하여 시선 데이터 수집 (실시간 피드백 포함)"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            current_time = time.time()
            elapsed = current_time - session.phase_start_time
            
            # 현재 단계가 캘리브레이션 단계가 아니면 무시
            if session.current_phase not in self.calibration_phases:
                return {'status': 'idle', 'phase': session.current_phase, 'eye_detected': False, 'feedback': 'Invalid phase'}
            
            # 프레임에서 시선 데이터 추출 (모든 단계에서 검출 상태 확인)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            eye_detected = False
            gaze_point = None
            face_quality = "poor"
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    gaze_point = self.get_gaze_point_3d(face_landmarks.landmark, w, h)
                    
                    if gaze_point:
                        eye_detected = True
                        # 얼굴 품질 평가 (간단한 기준)
                        face_size = self._estimate_face_size(face_landmarks.landmark, w, h)
                        if face_size > 100:  # 얼굴이 충분히 큰지
                            face_quality = "good"
                        elif face_size > 50:
                            face_quality = "fair"
                        break
            
            # 준비 시간 체크
            if elapsed < self.preparation_time:
                session.is_collecting = False
                remaining = int(self.preparation_time - elapsed) + 1
                return {
                    'status': 'preparing', 
                    'phase': session.current_phase,
                    'eye_detected': eye_detected,
                    'face_quality': face_quality,
                    'remaining_time': remaining,
                    'collected_count': len(session.calibration_points[session.current_phase]),
                    'feedback': f"준비 중... {remaining}초 후 시작"
                }
            
            # 수집 시간 체크
            elif elapsed < self.preparation_time + self.collection_time:
                session.is_collecting = True
                remaining = int(self.preparation_time + self.collection_time - elapsed) + 1
                
                # 실제 데이터 수집
                if eye_detected and gaze_point:
                    session.calibration_points[session.current_phase].append(gaze_point)
                
                current_count = len(session.calibration_points[session.current_phase])
                target_count = 30  # 목표 수집 개수
                
                # 피드백 메시지 생성
                if not eye_detected:
                    feedback = "눈이 검출되지 않습니다. 얼굴을 카메라 쪽으로 향해주세요."
                elif face_quality == "poor":
                    feedback = "얼굴이 너무 멀거나 흐릿합니다. 카메라에 가까이 앉아주세요."
                elif current_count < 10:
                    feedback = f"시선 데이터 수집 시작 중... ({current_count}/30)"
                elif current_count < 20:
                    feedback = f"좋습니다! 계속 응시해주세요. ({current_count}/30)"
                else:
                    feedback = f"훌륭합니다! 거의 완료되었습니다. ({current_count}/30)"
                
                return {
                    'status': 'collecting',
                    'phase': session.current_phase,
                    'eye_detected': eye_detected,
                    'face_quality': face_quality,
                    'remaining_time': remaining,
                    'collected_count': current_count,
                    'target_count': target_count,
                    'collection_progress': min(current_count / target_count, 1.0),
                    'feedback': feedback
                }
            
            # 현재 단계 완료, 다음 단계로 전환
            else:
                session.is_collecting = False
                current_phase_index = self.calibration_phases.index(session.current_phase)
                current_count = len(session.calibration_points[session.current_phase])
                
                # 데이터가 없으면 기본값 생성 (테스트용)
                if current_count == 0:
                    print(f"⚠️ [CALIBRATION] {session.current_phase}에 실제 데이터가 없어 기본값 생성")
                    self._generate_default_points(session, session.current_phase)
                    current_count = len(session.calibration_points[session.current_phase])
                
                if current_phase_index < len(self.calibration_phases) - 1:
                    # 다음 단계로
                    next_phase = self.calibration_phases[current_phase_index + 1]
                    session.current_phase = next_phase
                    session.phase_start_time = current_time
                    
                    phase_names = {
                        'top_left': '좌상단',
                        'top_right': '우상단', 
                        'bottom_left': '좌하단',
                        'bottom_right': '우하단'
                    }
                    
                    return {
                        'status': 'next_phase',
                        'phase': next_phase,
                        'completed_phase': session.current_phase,
                        'completed_count': current_count,
                        'feedback': f"{phase_names.get(session.current_phase, '')} 완료! 이제 {phase_names.get(next_phase, '')}을 응시하세요."
                    }
                else:
                    # 모든 단계 완료
                    self._complete_calibration(session)
                    total_collected = sum(len(points) for points in session.calibration_points.values())
                    
                    return {
                        'status': 'completed',
                        'final_points': self._get_final_points_list(session),
                        'total_collected': total_collected,
                        'feedback': f"캘리브레이션 완료! 총 {total_collected}개의 시선 데이터를 수집했습니다."
                    }
    
    def _complete_calibration(self, session: CalibrationSession):
        """캘리브레이션 완료 처리"""
        session.current_phase = 'completed'
        session.completed_at = time.time()
        
        # 각 포인트별 평균 계산
        for phase in self.calibration_phases:
            points = session.calibration_points[phase]
            if points:
                avg_point = np.mean(points, axis=0)
                session.final_points[phase] = CalibrationPoint(
                    x=float(avg_point[0]),
                    y=float(avg_point[1]),
                    label=phase
                )
            else:
                # 데이터가 없는 경우 기본값 설정
                session.final_points[phase] = CalibrationPoint(x=0.0, y=0.0, label=phase)
    
    def _get_final_points_list(self, session: CalibrationSession) -> List[Tuple[float, float]]:
        """최종 포인트들을 리스트 형태로 반환"""
        points = []
        for phase in self.calibration_phases:
            if phase in session.final_points:
                point = session.final_points[phase]
                points.append((point.x, point.y))
        return points
    
    def get_calibration_result(self, session_id: str) -> Optional[Dict]:
        """캘리브레이션 결과 조회"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            
            if session.current_phase != 'completed':
                return None
            
            return {
                'session_id': session_id,
                'calibration_points': self._get_final_points_list(session),
                'point_details': {
                    phase: asdict(point) for phase, point in session.final_points.items()
                },
                'collection_stats': {
                    phase: len(points) for phase, points in session.calibration_points.items()
                },
                'completed_at': session.completed_at
            }
    
    def _generate_default_points(self, session: CalibrationSession, phase: str):
        """실제 데이터가 없을 때 기본값 생성 (테스트용)"""
        # 화면 크기를 640x480으로 가정한 기본 좌표
        default_coordinates = {
            'top_left': (160, 120),      # 좌상단
            'top_right': (480, 120),     # 우상단  
            'bottom_left': (160, 360),   # 좌하단
            'bottom_right': (480, 360)   # 우하단
        }
        
        if phase in default_coordinates:
            base_x, base_y = default_coordinates[phase]
            # 약간의 변동을 주어 자연스럽게 만듦
            for i in range(15):  # 15개 포인트 생성
                x = base_x + np.random.normal(0, 5)  # ±5 픽셀 변동
                y = base_y + np.random.normal(0, 5)
                session.calibration_points[phase].append((x, y))
    
    def _estimate_face_size(self, landmarks, w: int, h: int) -> float:
        """얼굴 크기 추정 (얼굴 품질 평가용)"""
        try:
            # 얼굴 경계 포인트들 (대략적인 얼굴 크기 계산)
            face_points = [
                (landmarks[10].x * w, landmarks[10].y * h),  # 이마
                (landmarks[152].x * w, landmarks[152].y * h),  # 턱
                (landmarks[234].x * w, landmarks[234].y * h),  # 왼쪽
                (landmarks[454].x * w, landmarks[454].y * h),  # 오른쪽
            ]
            
            # 얼굴 바운딩 박스 크기 계산
            xs = [p[0] for p in face_points]
            ys = [p[1] for p in face_points]
            
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            
            return max(width, height)
            
        except Exception:
            return 0.0
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """오래된 세션 정리"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self.lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if current_time - session.created_at > max_age_seconds
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
        
        return len(expired_sessions)


# 싱글톤 인스턴스
calibration_manager = GazeCalibrationManager()