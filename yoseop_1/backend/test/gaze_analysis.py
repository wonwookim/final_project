"""
동영상 기반 시선 분석 엔진
MediaPipe를 사용하여 업로드된 동영상에서 시선 안정성을 분석합니다.
"""

import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
from typing import Dict, List, Tuple, Optional
import requests
from dataclasses import dataclass


@dataclass
class GazeAnalysisResult:
    """시선 분석 결과 데이터 클래스"""
    gaze_score: int  # 0-100 시선 안정성 점수
    total_frames: int  # 총 프레임 수
    analyzed_frames: int  # 분석된 프레임 수
    in_range_frames: int  # 허용 범위 내 프레임 수
    in_range_ratio: float  # 범위 내 비율
    jitter_score: int  # 시선 흔들림 점수
    stability_rating: str  # 안정성 등급
    feedback: str  # 피드백 메시지
    gaze_points: List[Tuple[float, float]]  # 시선 좌표들 (시각화용)


class GazeAnalyzer:
    """동영상 시선 분석기"""
    
    def __init__(self):
        # MediaPipe 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 동공 랜드마크 인덱스 (MediaPipe Iris 모델)
        self.left_iris_indices = [468, 469, 470, 471, 472]   # 왼쪽 동공
        self.right_iris_indices = [473, 474, 475, 476, 477]  # 오른쪽 동공
    
    def download_video_from_s3(self, s3_url: str) -> str:
        """S3에서 동영상을 임시 파일로 다운로드 (타임아웃 및 진행률 포함)"""
        try:
            print(f"🌐 [DOWNLOAD] 다운로드 시작: {s3_url}")
            
            # 타임아웃 설정 (30초)
            response = requests.get(s3_url, stream=True, timeout=(10, 30))
            response.raise_for_status()
            
            total_size = int(response.headers.get('Content-Length', 0))
            print(f"📏 [DOWNLOAD] 파일 크기: {total_size} bytes")
            
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
            
            # 스트리밍 다운로드 (진행률 표시)
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # 진행률 출력 (10MB마다)
                    if downloaded % (10 * 1024 * 1024) == 0:
                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                        print(f"📥 [DOWNLOAD] 진행률: {progress:.1f}% ({downloaded}/{total_size})")
            
            temp_file.close()
            print(f"✅ [DOWNLOAD] 다운로드 완료: {temp_file.name}")
            return temp_file.name
            
        except requests.exceptions.Timeout:
            raise Exception("동영상 다운로드 시간 초과 (30초)")
        except requests.exceptions.ConnectionError:
            raise Exception("동영상 다운로드 연결 실패")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise Exception("동영상 접근 권한이 없습니다. 인증 토큰을 확인하세요.")
            elif e.response.status_code == 401:
                raise Exception("인증이 만료되었습니다. 다시 로그인하세요.")
            elif e.response.status_code == 404:
                raise Exception("동영상 파일을 찾을 수 없습니다.")
            else:
                raise Exception(f"동영상 다운로드 HTTP 오류: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"동영상 다운로드 실패: {str(e)}")
    
    def get_gaze_point_3d(self, landmarks, w: int, h: int) -> Optional[Tuple[float, float]]:
        """MediaPipe 랜드마크에서 3D 시선 포인트 계산"""
        try:
            # 왼쪽 동공 3D 중심점
            left_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) 
                for i in self.left_iris_indices
            ])
            left_center = np.mean(left_iris_points, axis=0)
            
            # 오른쪽 동공 3D 중심점
            right_iris_points = np.array([
                (landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) 
                for i in self.right_iris_indices
            ])
            right_center = np.mean(right_iris_points, axis=0)
            
            # 양쪽 동공의 평균 위치 계산
            avg_gaze = (left_center + right_center) / 2
            
            # NaN이나 비정상 값 체크
            if (np.any(np.isnan(avg_gaze)) or 
                np.any(np.isinf(avg_gaze)) or 
                np.allclose(avg_gaze, 0)):
                return None
            
            return (float(avg_gaze[0]), float(avg_gaze[1]))
            
        except Exception:
            return None
    
    def calculate_jitter_score(self, gaze_points: List[Tuple[float, float]]) -> int:
        """시선 흔들림(jitter) 기반 점수 계산"""
        if len(gaze_points) < 10:
            return 50  # 기본 점수
        
        # 3D 포인트들의 표준편차 계산
        arr = np.array(gaze_points)
        
        # 각 축별 표준편차 계산
        jitter_x = np.std(arr[:, 0])
        jitter_y = np.std(arr[:, 1])
        
        # 전체 jitter는 x, y축의 평균
        jitter = (jitter_x + jitter_y) / 2
        
        # 실제 동공 움직임에 맞는 jitter 범위로 조정
        max_jitter = 50.0  # 매우 불안정한 시선
        min_jitter = 0.5   # 매우 안정적인 시선
        
        if jitter <= min_jitter:
            score = 100
        elif jitter >= max_jitter:
            score = 0
        else:
            # 선형 변환: jitter가 낮을수록 높은 점수
            score = int(100 * (1 - (jitter - min_jitter) / (max_jitter - min_jitter)))
        
        return max(0, min(100, score))
    
    def calculate_gaze_compliance_score(
        self, 
        gaze_points: List[Tuple[float, float]], 
        allowed_range: Dict[str, float]
    ) -> int:
        """시선 범위 준수 기반 점수 계산"""
        if not gaze_points or not all(allowed_range.values()):
            return 50  # 기본 점수
        
        if len(gaze_points) < 10:
            return 50
        
        in_range_count = 0
        total_violation_severity = 0
        
        for x, y in gaze_points:
            x_in_range = allowed_range['left_bound'] <= x <= allowed_range['right_bound']
            y_in_range = allowed_range['top_bound'] <= y <= allowed_range['bottom_bound']
            
            if x_in_range and y_in_range:
                in_range_count += 1
            else:
                # 이탈 정도 계산
                x_violation = 0
                y_violation = 0
                
                if not x_in_range:
                    if x < allowed_range['left_bound']:
                        x_violation = allowed_range['left_bound'] - x
                    else:
                        x_violation = x - allowed_range['right_bound']
                
                if not y_in_range:
                    if y < allowed_range['top_bound']:
                        y_violation = allowed_range['top_bound'] - y
                    else:
                        y_violation = y - allowed_range['bottom_bound']
                
                violation_severity = np.sqrt(x_violation**2 + y_violation**2)
                total_violation_severity += min(violation_severity * 5, 5)  # 최대 5점 누적
        
        total_points = len(gaze_points)
        compliance_ratio = in_range_count / total_points
        avg_violation_severity = total_violation_severity / total_points
        
        # 기본 점수 계산
        if compliance_ratio >= 0.9:
            base_score = 90 + int((compliance_ratio - 0.9) * 100)
        elif compliance_ratio >= 0.7:
            base_score = 70 + int((compliance_ratio - 0.7) * 100)
        elif compliance_ratio >= 0.5:
            base_score = 50 + int((compliance_ratio - 0.5) * 100)
        elif compliance_ratio >= 0.3:
            base_score = 30 + int((compliance_ratio - 0.3) * 100)
        else:
            base_score = int(compliance_ratio * 100)
        
        # 이탈 페널티
        penalty = min(int(avg_violation_severity), 10)
        final_score = max(0, base_score - penalty)
        
        return final_score
    
    def calculate_allowed_gaze_range(self, calibration_points: List[Tuple[float, float]]) -> Dict[str, float]:
        """4포인트 캘리브레이션 데이터에서 허용 시선 범위 계산"""
        if len(calibration_points) != 4:
            raise ValueError("4개의 캘리브레이션 포인트가 필요합니다")
        
        # 4포인트 데이터를 numpy 배열로 변환
        points = np.array(calibration_points)
        
        # X축(좌우), Y축(상하) 범위 계산
        min_x = np.min(points[:, 0])
        max_x = np.max(points[:, 0])
        min_y = np.min(points[:, 1])
        max_y = np.max(points[:, 1])
        
        # 여유 공간 추가 (5% 마진)
        x_range = max_x - min_x
        y_range = max_y - min_y
        x_margin = x_range * 0.05
        y_margin = y_range * 0.05
        
        return {
            'left_bound': min_x - x_margin,
            'right_bound': max_x + x_margin,
            'top_bound': min_y - y_margin,
            'bottom_bound': max_y + y_margin
        }
    
    def analyze_video(
        self, 
        video_path_or_url: str, 
        calibration_points: List[Tuple[float, float]],
        frame_skip: int = 10  # 성능 최적화를 위한 프레임 스킵
    ) -> GazeAnalysisResult:
        """동영상 시선 분석 메인 함수"""
        
        # S3 URL인 경우 다운로드
        if video_path_or_url.startswith('http'):
            video_path = self.download_video_from_s3(video_path_or_url)
            cleanup_file = True
        else:
            video_path = video_path_or_url
            cleanup_file = False
        
        try:
            # 캘리브레이션 범위 계산
            allowed_range = self.calculate_allowed_gaze_range(calibration_points)
            
            # 동영상 열기
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("동영상을 열 수 없습니다")
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            gaze_points = []
            frame_count = 0
            analyzed_count = 0
            
            print(f"동영상 분석 시작: 총 {total_frames} 프레임")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # 프레임 스킵으로 성능 최적화
                if frame_count % frame_skip != 0:
                    continue
                
                # 프레임 크기
                h, w, _ = frame.shape
                
                # RGB 변환
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # MediaPipe 얼굴 처리
                results = self.face_mesh.process(rgb_frame)
                
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        # 시선 포인트 계산
                        gaze_point = self.get_gaze_point_3d(face_landmarks.landmark, w, h)
                        
                        if gaze_point:
                            gaze_points.append(gaze_point)
                            analyzed_count += 1
                
                # 진행 상황 출력 (매 1000프레임마다)
                if frame_count % 1000 == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"분석 진행률: {progress:.1f}% ({analyzed_count}개 시선 포인트 수집)")
            
            cap.release()
            
            print(f"분석 완료: {analyzed_count}개 시선 포인트 수집")
            
            # 분석 결과 계산
            if len(gaze_points) < 10:
                raise Exception("충분한 시선 데이터를 수집하지 못했습니다")
            
            # 시선 안정성 점수 계산
            jitter_score = self.calculate_jitter_score(gaze_points)
            compliance_score = self.calculate_gaze_compliance_score(gaze_points, allowed_range)
            
            # 최종 점수 (두 점수의 가중 평균)
            final_score = int((jitter_score * 0.4) + (compliance_score * 0.6))
            
            # 범위 내 프레임 수 계산
            in_range_count = 0
            for x, y in gaze_points:
                x_in_range = allowed_range['left_bound'] <= x <= allowed_range['right_bound']
                y_in_range = allowed_range['top_bound'] <= y <= allowed_range['bottom_bound']
                if x_in_range and y_in_range:
                    in_range_count += 1
            
            in_range_ratio = in_range_count / len(gaze_points)
            
            # 안정성 등급 결정
            if final_score >= 85:
                stability_rating = "우수"
                feedback = "매우 안정적인 시선 처리를 보였습니다. 면접관과의 아이컨택이 자연스럽고 집중도가 높습니다."
            elif final_score >= 70:
                stability_rating = "양호"
                feedback = "전반적으로 좋은 시선 처리입니다. 조금 더 안정적인 시선 유지를 연습하면 더욱 좋겠습니다."
            elif final_score >= 50:
                stability_rating = "보통"
                feedback = "시선 처리에 개선이 필요합니다. 면접관을 바라보는 연습과 긴장 완화가 도움될 것입니다."
            else:
                stability_rating = "개선 필요"
                feedback = "시선이 많이 불안정합니다. 충분한 연습을 통해 안정적인 아이컨택을 개발하시기 바랍니다."
            
            # 시각화용 샘플 포인트 (최대 50개)
            sample_points = gaze_points[::max(1, len(gaze_points) // 50)]
            
            return GazeAnalysisResult(
                gaze_score=final_score,
                total_frames=total_frames,
                analyzed_frames=analyzed_count,
                in_range_frames=in_range_count,
                in_range_ratio=in_range_ratio,
                jitter_score=jitter_score,
                stability_rating=stability_rating,
                feedback=feedback,
                gaze_points=sample_points
            )
            
        finally:
            # 임시 파일 정리
            if cleanup_file and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                except:
                    pass


# 싱글톤 인스턴스
gaze_analyzer = GazeAnalyzer()