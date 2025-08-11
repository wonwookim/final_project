"""
동영상 기반 시선 분석 엔진
MediaPipe를 사용하여 업로드된 동영상에서 시선 안정성을 분석합니다.
"""

import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os
import uuid
from typing import Dict, List, Tuple, Optional
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass


@dataclass
class GazeAnalysisResult:
    """시선 분석 결과 데이터 클래스"""
    gaze_score: int
    total_frames: int
    analyzed_frames: int
    in_range_frames: int
    in_range_ratio: float
    jitter_score: int
    compliance_score: int # 🚀 추가
    stability_rating: str
    feedback: str
    gaze_points: List[Tuple[float, float]]


class GazeAnalyzer:
    """동영상 시선 분석기"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.left_iris_indices = [468, 469, 470, 471, 472]
        self.right_iris_indices = [473, 474, 475, 476, 477]
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
        )

    def download_video(self, bucket: str, key: str) -> str:
        """S3에서 동영상을 임시 파일로 직접 다운로드 (파일 핸들 충돌 방지)"""
        try:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}.webm")

            print(f"📥 [DOWNLOAD] S3에서 다운로드 시작: s3://{bucket}/{key} -> {temp_path}")
            
            self.s3_client.download_file(bucket, key, temp_path)
            
            print(f"✅ [DOWNLOAD] 다운로드 완료: {temp_path}")
            return temp_path
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"S3에서 파일을 찾을 수 없습니다: {key}")
            else:
                raise Exception(f"S3 다운로드 오류: {e}")
        except Exception as e:
            raise Exception(f"동영상 다운로드 중 알 수 없는 오류 발생: {str(e)}")

    def get_gaze_point_3d(self, landmarks, w: int, h: int) -> Optional[Tuple[float, float]]:
        try:
            left_iris_points = np.array([(landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) for i in self.left_iris_indices])
            left_center = np.mean(left_iris_points, axis=0)
            right_iris_points = np.array([(landmarks[i].x * w, landmarks[i].y * h, landmarks[i].z) for i in self.right_iris_indices])
            right_center = np.mean(right_iris_points, axis=0)
            avg_gaze = (left_center + right_center) / 2
            if (np.any(np.isnan(avg_gaze)) or np.any(np.isinf(avg_gaze)) or np.allclose(avg_gaze, 0)):
                return None
            return (float(avg_gaze[0]), float(avg_gaze[1]))
        except Exception:
            return None
    
    def calculate_jitter_score(self, gaze_points: List[Tuple[float, float]]) -> int:
        if len(gaze_points) < 10: return 50
        arr = np.array(gaze_points)
        jitter = (np.std(arr[:, 0]) + np.std(arr[:, 1])) / 2
        max_jitter, min_jitter = 50.0, 0.5
        if jitter <= min_jitter: score = 100
        elif jitter >= max_jitter: score = 0
        else: score = int(100 * (1 - (jitter - min_jitter) / (max_jitter - min_jitter)))
        return max(0, min(100, score))
    
    def calculate_gaze_compliance_score(self, gaze_points: List[Tuple[float, float]], allowed_range: Dict[str, float]) -> int:
        if not gaze_points or not all(allowed_range.values()) or len(gaze_points) < 10: return 50
        in_range_count = sum(1 for x, y in gaze_points if allowed_range['left_bound'] <= x <= allowed_range['right_bound'] and allowed_range['top_bound'] <= y <= allowed_range['bottom_bound'])
        compliance_ratio = in_range_count / len(gaze_points)
        return int(compliance_ratio * 100)
    
    def calculate_allowed_gaze_range(self, calibration_points: List[Tuple[float, float]]) -> Dict[str, float]:
        if len(calibration_points) != 4: raise ValueError("4개의 캘리브레이션 포인트가 필요합니다")
        points = np.array(calibration_points)
        min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
        min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
        x_margin, y_margin = (max_x - min_x) * 0.05, (max_y - min_y) * 0.05
        return {'left_bound': min_x - x_margin, 'right_bound': max_x + x_margin, 'top_bound': min_y - y_margin, 'bottom_bound': max_y + y_margin}
    
    def analyze_video(self, bucket: str, key: str, calibration_points: List[Tuple[float, float]], frame_skip: int = 10) -> GazeAnalysisResult:
        video_path = self.download_video(bucket, key)
        try:
            allowed_range = self.calculate_allowed_gaze_range(calibration_points)
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened(): raise Exception("동영상을 열 수 없습니다")
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            gaze_points, analyzed_count, frame_count = [], 0, 0
            
            while True:
                ret, frame = cap.read()
                if not ret: break
                frame_count += 1
                if frame_count % frame_skip != 0: continue
                
                h, w, _ = frame.shape
                results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        gaze_point = self.get_gaze_point_3d(face_landmarks.landmark, w, h)
                        if gaze_point: gaze_points.append(gaze_point)
            
            analyzed_count = len(gaze_points)
            cap.release()
            
            if analyzed_count < 10: raise Exception("충분한 시선 데이터를 수집하지 못했습니다")
            
            jitter_score = self.calculate_jitter_score(gaze_points)
            compliance_score = self.calculate_gaze_compliance_score(gaze_points, allowed_range)
            final_score = int((jitter_score * 0.4) + (compliance_score * 0.6))
            
            in_range_count = sum(1 for x, y in gaze_points if allowed_range['left_bound'] <= x <= allowed_range['right_bound'] and allowed_range['top_bound'] <= y <= allowed_range['bottom_bound'])
            in_range_ratio = in_range_count / analyzed_count if analyzed_count > 0 else 0
            
            # 🚀 FIX: 개선된 피드백 로직
            if compliance_score < 50:
                stability_rating = "개선 필요"
                feedback = f"시선이 화면 중앙을 벗어나는 비율이 높습니다 (화면 주시 점수: {compliance_score}점). 카메라 렌즈를 면접관의 눈이라고 생각하고 꾸준히 응시하는 연습이 필요합니다."
            elif jitter_score < 60:
                stability_rating = "개선 필요"
                feedback = f"시선이 안정적이지 못하고 흔들리는 경향이 있습니다 (시선 안정 점수: {jitter_score}점). 편안한 자세로 긴장을 풀고 화면의 한 지점에 시선을 고정하는 연습을 해보세요."
            elif final_score >= 85:
                stability_rating = "우수"
                feedback = "매우 안정적인 시선 처리를 보였습니다. 면접관과의 아이컨택이 자연스럽고 집중도가 높습니다."
            elif final_score >= 70:
                stability_rating = "양호"
                feedback = "전반적으로 좋은 시선 처리입니다. 조금 더 안정적인 시선 유지를 연습하면 더욱 좋겠습니다."
            else: # 50 <= final_score < 70
                stability_rating = "보통"
                feedback = "시선 처리에 약간의 개선이 필요합니다. 면접관을 바라보는 연습과 긴장 완화가 도움될 것입니다."

            return GazeAnalysisResult(
                gaze_score=final_score, total_frames=total_frames, analyzed_frames=analyzed_count,
                in_range_frames=in_range_count, in_range_ratio=in_range_ratio, jitter_score=jitter_score,
                compliance_score=compliance_score, stability_rating=stability_rating, feedback=feedback, 
                gaze_points=gaze_points[::max(1, analyzed_count // 50)]
            )
            
        finally:
            if os.path.exists(video_path): os.unlink(video_path)


gaze_analyzer = GazeAnalyzer()