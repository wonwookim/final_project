import React, { useState, useRef, useEffect, useCallback } from 'react';
import { CalibrationProps, CalibrationStatusResponse } from './types';

const API_BASE_URL = 'http://127.0.0.1:8000';

// 실시간 피드백 인터페이스
interface FrameFeedback {
  status: string;
  phase: string;
  eye_detected: boolean;
  face_quality: string;
  feedback: string;
  collected_count?: number;
  target_count?: number;
  remaining_time?: number;
  collection_progress?: number;
}

const VideoCalibration: React.FC<CalibrationProps> = ({ onCalibrationComplete, onError }) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<CalibrationStatusResponse | null>(null);
  const [isStarted, setIsStarted] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  
  // 실시간 피드백 상태
  const [realtimeFeedback, setRealtimeFeedback] = useState<FrameFeedback | null>(null);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null);
  const frameStreamInterval = useRef<NodeJS.Timeout | null>(null);

  // 웹캠 스트림 시작
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 }, 
        audio: false 
      });
      
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      console.log('✅ 웹캠 스트림 시작됨');
    } catch (error) {
      console.error('❌ 웹캠 접근 실패:', error);
      onError('웹캠에 접근할 수 없습니다. 권한을 확인해주세요.');
    }
  }, [onError]);

  // 웹캠 스트림 정리
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    // 프레임 스트리밍 정리
    if (frameStreamInterval.current) {
      clearInterval(frameStreamInterval.current);
      frameStreamInterval.current = null;
    }
  }, []);

  // 프레임 캡처 및 전송
  const captureAndSendFrame = useCallback(async (sessionId: string) => {
    if (!videoRef.current || !canvasRef.current) return;
    
    try {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) return;
      
      // 캔버스 크기를 비디오 크기에 맞춤
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // 비디오 프레임을 캔버스에 그리기
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Canvas를 Base64로 변환
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      
      // 백엔드로 전송
      const formData = new FormData();
      formData.append('frame_data', imageData);
      
      const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/frame/${sessionId}`, {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        const feedback: FrameFeedback = await response.json();
        setRealtimeFeedback(feedback);
        
        // 완료 상태 체크
        if (feedback.status === 'completed') {
          setIsCompleted(true);
          if (frameStreamInterval.current) {
            clearInterval(frameStreamInterval.current);
            frameStreamInterval.current = null;
          }
          onCalibrationComplete(sessionId);
        }
      }
    } catch (error) {
      console.error('프레임 전송 오류:', error);
    }
  }, [onCalibrationComplete]);
  
  // 프레임 스트리밍 시작
  const startFrameStreaming = useCallback((sessionId: string) => {
    if (frameStreamInterval.current) {
      clearInterval(frameStreamInterval.current);
    }
    
    frameStreamInterval.current = setInterval(() => {
      captureAndSendFrame(sessionId);
    }, 200); // 200ms마다 프레임 전송 (5fps)
  }, [captureAndSendFrame]);

  // 캘리브레이션 시작
  const startCalibration = async () => {
    try {
      console.log('🎯 캘리브레이션 시작 요청');
      
      const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: null })
      });

      if (!response.ok) {
        throw new Error(`캘리브레이션 시작 실패: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ 캘리브레이션 세션 생성:', data);
      
      setSessionId(data.session_id);
      setIsStarted(true);
      
      // 상태 체크 시작
      startStatusCheck(data.session_id);
      
      // 프레임 스트리밍 시작
      startFrameStreaming(data.session_id);
      
    } catch (error) {
      console.error('❌ 캘리브레이션 시작 오류:', error);
      onError(error instanceof Error ? error.message : '캘리브레이션을 시작할 수 없습니다.');
    }
  };

  // 상태 체크 시작
  const startStatusCheck = (sessionId: string) => {
    if (statusCheckInterval.current) {
      clearInterval(statusCheckInterval.current);
    }

    statusCheckInterval.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/status/${sessionId}`);
        
        if (!response.ok) {
          throw new Error(`상태 체크 실패: ${response.status}`);
        }

        const statusData: CalibrationStatusResponse = await response.json();
        console.log('📊 캘리브레이션 상태:', statusData);
        
        setStatus(statusData);

        // 완료 체크
        if (statusData.current_phase === 'completed') {
          console.log('🎉 캘리브레이션 완료!');
          setIsCompleted(true);
          
          if (statusCheckInterval.current) {
            clearInterval(statusCheckInterval.current);
            statusCheckInterval.current = null;
          }
          
          // 완료 콜백 호출
          onCalibrationComplete(sessionId);
        }
        
      } catch (error) {
        console.error('❌ 상태 체크 오류:', error);
      }
    }, 500); // 500ms마다 체크
  };

  // 컴포넌트 마운트 시 웹캠 시작
  useEffect(() => {
    startCamera();
    
    return () => {
      // 정리
      stopCamera();
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
      }
      if (frameStreamInterval.current) {
        clearInterval(frameStreamInterval.current);
      }
    };
  }, [startCamera, stopCamera]);

  // 단계별 안내 메시지 및 스타일
  const getPhaseInfo = () => {
    if (!status) {
      return {
        message: '캘리브레이션을 시작하려면 아래 버튼을 클릭하세요',
        indicator: null,
        bgColor: 'bg-blue-50'
      };
    }

    const phaseMessages: { [key: string]: string } = {
      'ready': '캘리브레이션 준비 중...',
      'top_left': '화면 좌상단 모서리를 응시하세요',
      'top_right': '화면 우상단 모서리를 응시하세요',
      'bottom_left': '화면 좌하단 모서리를 응시하세요',
      'bottom_right': '화면 우하단 모서리를 응시하세요',
      'completed': '캘리브레이션이 완료되었습니다!'
    };

    const phaseColors: { [key: string]: string } = {
      'ready': 'bg-blue-50',
      'top_left': 'bg-green-50',
      'top_right': 'bg-yellow-50', 
      'bottom_left': 'bg-purple-50',
      'bottom_right': 'bg-red-50',
      'completed': 'bg-emerald-50'
    };

    // 시선 방향 표시기
    const getIndicator = () => {
      if (!status.is_collecting) return null;
      
      const positions: { [key: string]: string } = {
        'top_left': 'top-4 left-4',
        'top_right': 'top-4 right-4',
        'bottom_left': 'bottom-4 left-4',
        'bottom_right': 'bottom-4 right-4'
      };
      
      const position = positions[status.current_phase];
      if (!position) return null;

      return (
        <div className={`absolute ${position} w-8 h-8 bg-red-500 rounded-full animate-pulse border-4 border-white shadow-lg`}>
          <div className="absolute inset-0 bg-red-400 rounded-full animate-ping"></div>
        </div>
      );
    };

    return {
      message: phaseMessages[status.current_phase] || status.instructions,
      indicator: getIndicator(),
      bgColor: phaseColors[status.current_phase] || 'bg-gray-50'
    };
  };

  const phaseInfo = getPhaseInfo();

  return (
    <div className="space-y-4">
      {/* 안내 메시지 */}
      <div className={`${phaseInfo.bgColor} border border-gray-200 rounded-lg p-4 text-center`}>
        <h4 className="font-medium text-gray-900 mb-2">👁️ 시선 캘리브레이션</h4>
        <p className="text-gray-700 text-sm mb-2">{phaseInfo.message}</p>
        
        {status && (
          <>
            <p className="text-xs text-gray-500 mb-2">{status.instructions}</p>
            
            {/* 진행률 바 */}
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.round(status.progress * 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500">
              진행률: {Math.round(status.progress * 100)}%
            </p>
          </>
        )}
      </div>
      
      {/* 실시간 피드백 */}
      {realtimeFeedback && isStarted && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <span className={`w-3 h-3 rounded-full ${
                realtimeFeedback.eye_detected ? 'bg-green-500' : 'bg-red-500'
              }`}></span>
              <span className="font-medium">
                {realtimeFeedback.eye_detected ? '👁️ 눈 검출: 성공' : '❌ 눈 검출: 실패'}
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className={`w-3 h-3 rounded-full ${
                realtimeFeedback.face_quality === 'good' ? 'bg-green-500' :
                realtimeFeedback.face_quality === 'fair' ? 'bg-yellow-500' : 'bg-red-500'
              }`}></span>
              <span className="font-medium">
                화질: {realtimeFeedback.face_quality === 'good' ? '양호' :
                      realtimeFeedback.face_quality === 'fair' ? '보통' : '불량'}
              </span>
            </div>
            
            {realtimeFeedback.collected_count !== undefined && (
              <div className="col-span-2">
                <div className="flex justify-between text-xs mb-1">
                  <span>수집된 데이터:</span>
                  <span className="font-bold">
                    {realtimeFeedback.collected_count}/{realtimeFeedback.target_count || 30}개
                  </span>
                </div>
                {realtimeFeedback.collection_progress !== undefined && (
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${realtimeFeedback.collection_progress * 100}%` }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
          
          {realtimeFeedback.feedback && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-blue-800 text-sm font-medium">
                💬 {realtimeFeedback.feedback}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 비디오 프리뷰 */}
      <div className="relative">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full max-w-md mx-auto rounded-lg bg-gray-900"
          style={{ transform: 'scaleX(-1)' }} // 거울 효과
        />
        
        {/* 숨겨진 캔버스 (프레임 캡처용) */}
        <canvas
          ref={canvasRef}
          style={{ display: 'none' }}
        />
        
        {/* 시선 방향 표시기 */}
        {phaseInfo.indicator}
        
        {/* 화면 모서리 가이드 점들 */}
        {isStarted && !isCompleted && (
          <>
            <div className="absolute top-2 left-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div>
            <div className="absolute top-2 right-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div>
            <div className="absolute bottom-2 left-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div>
            <div className="absolute bottom-2 right-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div>
          </>
        )}
      </div>

      {/* 컬렉션 통계 */}
      {status && status.collected_points && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-gray-50 p-2 rounded text-center">
            좌상단: {status.collected_points.top_left || 0}개
          </div>
          <div className="bg-gray-50 p-2 rounded text-center">
            우상단: {status.collected_points.top_right || 0}개
          </div>
          <div className="bg-gray-50 p-2 rounded text-center">
            좌하단: {status.collected_points.bottom_left || 0}개
          </div>
          <div className="bg-gray-50 p-2 rounded text-center">
            우하단: {status.collected_points.bottom_right || 0}개
          </div>
        </div>
      )}

      {/* 시작 버튼 */}
      {!isStarted && (
        <button
          onClick={startCalibration}
          className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all"
        >
          🎯 시선 캘리브레이션 시작
        </button>
      )}

      {/* 완료 상태 */}
      {isCompleted && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="text-green-600 font-bold text-lg mb-2">
            ✅ 캘리브레이션 완료!
          </div>
          <div className="text-green-700 text-sm">
            이제 면접을 녹화할 수 있습니다.
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoCalibration;