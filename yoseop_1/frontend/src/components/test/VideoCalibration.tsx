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
  const [testMode, setTestMode] = useState(false);
  const [realtimeFeedback, setRealtimeFeedback] = useState<FrameFeedback | null>(null);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null);
  const frameStreamInterval = useRef<NodeJS.Timeout | null>(null);

  const startCamera = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setTestMode(true);
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (error) {
      if ((error as Error)?.name === 'NotAllowedError' || (error as Error)?.name === 'PermissionDeniedError') {
        setTestMode(true);
        return;
      }
      onError('웹캠에 접근할 수 없습니다. 권한을 확인하거나 테스트 모드를 사용하세요.');
    }
  }, [onError]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (frameStreamInterval.current) {
      clearInterval(frameStreamInterval.current);
      frameStreamInterval.current = null;
    }
  }, []);

  const captureAndSendFrame = useCallback(async (sessionId: string) => {
    if (!videoRef.current || !canvasRef.current) return;
    try {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      const formData = new FormData();
      formData.append('frame_data', imageData);
      const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/frame/${sessionId}`, { method: 'POST', body: formData });
      if (response.ok) {
        const feedback: FrameFeedback = await response.json();
        setRealtimeFeedback(feedback);
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
  
  const startFrameStreaming = useCallback((sessionId: string) => {
    if (frameStreamInterval.current) clearInterval(frameStreamInterval.current);
    if (testMode) {
      startTestModeFrameStreaming(sessionId);
      return;
    }
    frameStreamInterval.current = setInterval(() => { captureAndSendFrame(sessionId); }, 200);
  }, [captureAndSendFrame, testMode]);

  const startTestModeFrameStreaming = useCallback((sessionId: string) => {
    let phase = 0;
    const phases = ['top_left', 'top_right', 'bottom_left', 'bottom_right'];
    let collectCount = 0;
    frameStreamInterval.current = setInterval(() => {
      const currentPhase = phases[phase];
      const progress = collectCount / 30;
      const feedback = { status: collectCount >= 30 ? 'completed' : 'collecting', phase: currentPhase, eye_detected: true, face_quality: 'good', feedback: `${currentPhase} 단계 ${collectCount}/30 수집 중`, collected_count: collectCount, target_count: 30, collection_progress: Math.min(progress, 1.0) };
      setRealtimeFeedback(feedback);
      collectCount++;
      if (collectCount >= 30) {
        collectCount = 0;
        phase++;
        if (phase >= phases.length) {
          setIsCompleted(true);
          if (frameStreamInterval.current) clearInterval(frameStreamInterval.current);
          onCalibrationComplete(sessionId);
          return;
        }
      }
    }, 100);
  }, [onCalibrationComplete]);

  const startCalibration = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/start`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify({ user_id: null }), signal: AbortSignal.timeout(10000) });
      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        let errorMessage = `캘리브레이션 시작 실패 (${response.status}): ${errorText}`;
        if (response.status === 404) errorMessage = '캘리브레이션 API 엔드포인트를 찾을 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.';
        else if (response.status >= 500) errorMessage = '서버 내부 오류가 발생했습니다. 백엔드 로그를 확인하세요.';
        throw new Error(errorMessage);
      }
      const data = await response.json();
      if (!data.session_id) throw new Error('세션 ID를 받지 못했습니다.');
      setSessionId(data.session_id);
      setIsStarted(true);
      if (!testMode) await startCamera();
      startStatusCheck(data.session_id);
      startFrameStreaming(data.session_id);
    } catch (error) {
      let userMessage = error instanceof Error ? error.message : '❌ 캘리브레이션을 시작할 수 없습니다.';
      if (error instanceof TypeError && error.message.includes('fetch')) userMessage = `❌ 백엔드 서버 연결 실패

🔧 해결 방법:
1. 백엔드 서버를 실행하세요:
   • 터미널에서 backend 폴더로 이동
   • "uvicorn main:app --reload --port 8000" 실행
   
2. 또는 테스트 모드를 사용하세요:
   • 아래 "테스트 모드" 체크박스를 선택
   • 가상으로 캘리브레이션을 진행할 수 있습니다

🌐 서버 URL: http://127.0.0.1:8000`;
      else if ((error as Error)?.name === 'TimeoutError') userMessage = '⏰ 요청 시간 초과: 서버 응답이 너무 느립니다. 서버 상태를 확인하고 다시 시도하세요.';
      onError(userMessage);
    }
  };

  const startStatusCheck = (sessionId: string) => {
    if (statusCheckInterval.current) clearInterval(statusCheckInterval.current);
    statusCheckInterval.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/test/gaze/calibration/status/${sessionId}`);
        if (!response.ok) throw new Error(`상태 체크 실패: ${response.status}`);
        const statusData: CalibrationStatusResponse = await response.json();
        setStatus(statusData);
        if (statusData.current_phase === 'completed') {
          setIsCompleted(true);
          if (statusCheckInterval.current) clearInterval(statusCheckInterval.current);
          onCalibrationComplete(sessionId);
        }
      } catch (error) {
        console.error('❌ 상태 체크 오류:', error);
      }
    }, 500);
  };

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
      if (statusCheckInterval.current) clearInterval(statusCheckInterval.current);
      if (frameStreamInterval.current) clearInterval(frameStreamInterval.current);
    };
  }, [startCamera, stopCamera]);

  const getPhaseInfo = () => {
    if (!status) return { message: '캘리브레이션을 시작하려면 아래 버튼을 클릭하세요', indicator: null, bgColor: 'bg-blue-50' };
    const phaseMessages: { [key: string]: string } = { 'ready': '캘리브레이션 준비 중...', 'top_left': '화면 좌상단 모서리를 응시하세요', 'top_right': '화면 우상단 모서리를 응시하세요', 'bottom_left': '화면 좌하단 모서리를 응시하세요', 'bottom_right': '화면 우하단 모서리를 응시하세요', 'completed': '캘리브레이션이 완료되었습니다!' };
    const phaseColors: { [key: string]: string } = { 'ready': 'bg-blue-50', 'top_left': 'bg-green-50', 'top_right': 'bg-yellow-50', 'bottom_left': 'bg-purple-50', 'bottom_right': 'bg-red-50', 'completed': 'bg-emerald-50' };
    const getIndicator = () => {
      if (!status.is_collecting) return null;
      const positions: { [key: string]: string } = { 'top_left': 'top-4 left-4', 'top_right': 'top-4 right-4', 'bottom_left': 'bottom-4 left-4', 'bottom_right': 'bottom-4 right-4' };
      const position = positions[status.current_phase];
      if (!position) return null;
      return <div className={`absolute ${position} w-8 h-8 bg-red-500 rounded-full animate-pulse border-4 border-white shadow-lg`}><div className="absolute inset-0 bg-red-400 rounded-full animate-ping"></div></div>;
    };
    return { message: phaseMessages[status.current_phase] || status.instructions, indicator: getIndicator(), bgColor: phaseColors[status.current_phase] || 'bg-gray-50' };
  };

  const phaseInfo = getPhaseInfo();

  return (
    <div className="space-y-4">
      <div className={`${phaseInfo.bgColor} border border-gray-200 rounded-lg p-4 text-center`}>
        <h4 className="font-medium text-gray-900 mb-2">👁️ 시선 캘리브레이션</h4>
        <p className="text-gray-700 text-sm mb-2">{phaseInfo.message}</p>
        {status && <><p className="text-xs text-gray-500 mb-2">{status.instructions}</p><div className="w-full bg-gray-200 rounded-full h-2 mb-2"><div className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out" style={{ width: `${Math.round(status.progress * 100)}%` }} /></div><p className="text-xs text-gray-500">진행률: {Math.round(status.progress * 100)}%</p></>}
      </div>

      {/* 🚀 추가된 중요 안내 문구 */}
      {!isStarted && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 p-4" role="alert">
          <p className="font-bold">중요 안내</p>
          <p className="text-sm">정확한 분석을 위해, 캘리브레이션부터 녹화 종료 시까지 <strong>동일한 자세와 거리</strong>를 유지해주세요.</p>
        </div>
      )}

      {realtimeFeedback && isStarted && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center space-x-2"><span className={`w-3 h-3 rounded-full ${realtimeFeedback.eye_detected ? 'bg-green-500' : 'bg-red-500'}`}></span><span className="font-medium">{realtimeFeedback.eye_detected ? '👁️ 눈 검출: 성공' : '❌ 눈 검출: 실패'}</span></div>
            <div className="flex items-center space-x-2"><span className={`w-3 h-3 rounded-full ${realtimeFeedback.face_quality === 'good' ? 'bg-green-500' : realtimeFeedback.face_quality === 'fair' ? 'bg-yellow-500' : 'bg-red-500'}`}></span><span className="font-medium">화질: {realtimeFeedback.face_quality === 'good' ? '양호' : realtimeFeedback.face_quality === 'fair' ? '보통' : '불량'}</span></div>
            {realtimeFeedback.collected_count !== undefined && <div className="col-span-2"><div className="flex justify-between text-xs mb-1"><span>수집된 데이터:</span><span className="font-bold">{realtimeFeedback.collected_count}/{realtimeFeedback.target_count || 30}개</span></div>{realtimeFeedback.collection_progress !== undefined && <div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-blue-500 h-2 rounded-full transition-all duration-300" style={{ width: `${realtimeFeedback.collection_progress * 100}%` }} /></div>}</div>}
          </div>
          {realtimeFeedback.feedback && <div className="mt-3 p-3 bg-blue-50 rounded-lg"><p className="text-blue-800 text-sm font-medium">💬 {realtimeFeedback.feedback}</p></div>}
        </div>
      )}

      <div className="relative">
        {testMode ? <div className="w-full max-w-md mx-auto rounded-lg bg-gradient-to-br from-gray-700 to-gray-900 h-64 flex items-center justify-center text-white"><div className="text-center"><div className="text-4xl mb-4">🧪</div><div className="font-bold text-lg">테스트 모드</div><div className="text-sm opacity-75">가상 캘리브레이션 진행 중</div></div></div> : <video ref={videoRef} autoPlay muted playsInline className="w-full max-w-md mx-auto rounded-lg bg-gray-900" style={{ transform: 'scaleX(-1)' }} />}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        {phaseInfo.indicator}
        {isStarted && !isCompleted && <><div className="absolute top-2 left-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div><div className="absolute top-2 right-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div><div className="absolute bottom-2 left-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div><div className="absolute bottom-2 right-2 w-3 h-3 bg-blue-400 rounded-full opacity-50"></div></>}
      </div>

      {status && status.collected_points && <div className="grid grid-cols-2 gap-2 text-xs"><div className="bg-gray-50 p-2 rounded text-center">좌상단: {status.collected_points.top_left || 0}개</div><div className="bg-gray-50 p-2 rounded text-center">우상단: {status.collected_points.top_right || 0}개</div><div className="bg-gray-50 p-2 rounded text-center">좌하단: {status.collected_points.bottom_left || 0}개</div><div className="bg-gray-50 p-2 rounded text-center">우하단: {status.collected_points.bottom_right || 0}개</div></div>}

      {!isStarted && <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3"><label className="flex items-center space-x-2 cursor-pointer"><input type="checkbox" checked={testMode} onChange={(e) => setTestMode(e.target.checked)} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" /><span className="text-sm text-yellow-800">🧪 테스트 모드 (웹캠 없이 가상으로 진행)</span></label></div>}

      {!isStarted && <div className="space-y-3"><button onClick={startCalibration} className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all">🎯 시선 캘리브레이션 시작 {testMode ? '(테스트 모드)' : ''}</button><div className="bg-blue-50 border border-blue-200 rounded-lg p-3"><div className="text-sm text-blue-800"><div className="font-medium mb-1">💡 시작하기 전에 확인하세요:</div><ol className="list-decimal list-inside space-y-1 text-xs"><li>백엔드 서버가 실행 중인지 확인 (포트 8000)</li><li>웹캠 권한이 허용되어 있는지 확인</li><li>문제 발생시 브라우저 콘솔(F12)에서 상세 로그 확인</li><li>서버가 꺼져있다면 테스트 모드로 진행 가능</li></ol></div></div></div>}

      {isCompleted && <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center"><div className="text-green-600 font-bold text-lg mb-2">✅ 캘리브레이션 완료!</div><div className="text-green-700 text-sm">이제 면접을 녹화할 수 있습니다.</div></div>}
    </div>
  );
};

export default VideoCalibration;
