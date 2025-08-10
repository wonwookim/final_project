import React, { useState, useRef, useEffect, useCallback } from 'react';
import { RecorderProps } from './types';

// MediaRecorder state type definition
type RecordingState = 'inactive' | 'recording' | 'paused';

const VideoTestRecorder: React.FC<RecorderProps> = ({ onRecordingComplete, onError }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const recordingStartTimeRef = useRef<number | null>(null); // 녹화 시작 시간 추적
  const isInitializingRef = useRef<boolean>(false); // MediaRecorder 초기화 중인지 추적

  const stopRecording = useCallback(() => {
    console.log('🛑 stopRecording 호출됨:', { 
      hasMediaRecorder: !!mediaRecorderRef.current, 
      isRecording,
      state: mediaRecorderRef.current?.state,
      timestamp: new Date().toISOString(),
      stackTrace: new Error().stack
    });
    
    // MediaRecorder 상태를 우선적으로 확인 (React 상태보다 신뢰성 높음)
    const mediaRecorder = mediaRecorderRef.current;
    if (mediaRecorder && (mediaRecorder.state as RecordingState) === 'recording') {
      // 최소 녹화 시간 보호 (500ms)
      const recordingDuration = recordingStartTimeRef.current ? 
        Date.now() - recordingStartTimeRef.current : 0;
      
      if (recordingDuration < 500) {
        console.warn('⚠️ 녹화 시간이 너무 짧아 중단 무시:', {
          duration: recordingDuration,
          minRequired: 500
        });
        return;
      }

      console.log('✋ MediaRecorder 중단 실행 중... (실제 녹화 중 상태)', {
        recordingDuration
      });
      mediaRecorder.stop();
      setIsRecording(false);
      recordingStartTimeRef.current = null;
      isInitializingRef.current = false; // 정상 종료 시에도 플래그 해제
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } else {
      console.log('⚠️ stopRecording 호출되었지만 조건 불충족:', {
        hasMediaRecorder: !!mediaRecorder,
        isRecording,
        mediaRecorderState: mediaRecorder?.state,
        recordingDuration: recordingStartTimeRef.current ? 
          Date.now() - recordingStartTimeRef.current : 'null',
        reason: !mediaRecorder ? 'MediaRecorder 없음' : 
                (mediaRecorder.state as RecordingState) !== 'recording' ? `상태가 '${mediaRecorder.state}'` : '기타'
      });
    }
  }, [isRecording]);

  useEffect(() => {
    // 컴포넌트 마운트 시 미디어 지원 확인
    checkMediaSupport();
    
    return () => {
      console.log('🧹 VideoTestRecorder cleanup 시작:', {
        hasMediaRecorder: !!mediaRecorderRef.current,
        mediaRecorderState: mediaRecorderRef.current?.state,
        isRecording,
        timestamp: new Date().toISOString()
      });

      // MediaRecorder가 실제로 녹화 중이고 초기화 중이 아닐 때만 정리
      if (mediaRecorderRef.current && 
          (mediaRecorderRef.current.state as RecordingState) === 'recording' && 
          !isInitializingRef.current) {
        console.log('🛑 cleanup에서 MediaRecorder 중단');
        try {
          mediaRecorderRef.current.stop();
        } catch (error) {
          console.error('❌ cleanup 중 MediaRecorder 중단 실패:', error);
        }
      } else if (isInitializingRef.current) {
        console.log('⚠️ cleanup 중 MediaRecorder 초기화 중이므로 중단 건너뜀');
      }

      // 스트림 정리
      if (streamRef.current) {
        console.log('📡 cleanup에서 MediaStream 트랙 정리');
        streamRef.current.getTracks().forEach(track => {
          if (track.readyState === 'live') {
            track.stop();
          }
        });
        streamRef.current = null;
      }

      // 타이머 정리
      if (timerRef.current) {
        console.log('⏰ cleanup에서 타이머 정리');
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []); // 의존성 배열을 빈 배열로 변경하여 cleanup 중 재실행 방지

  const checkMediaSupport = async () => {
    try {
      // 브라우저 지원 확인
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setPermissionError('이 브라우저는 미디어 녹화를 지원하지 않습니다');
        return;
      }

      // 미디어 장치 권한 상태 확인
      if (navigator.permissions) {
        try {
          const cameraPermission = await navigator.permissions.query({ name: 'camera' as PermissionName });
          const microphonePermission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
          
          if (cameraPermission.state === 'denied' || microphonePermission.state === 'denied') {
            setPermissionError('카메라 또는 마이크 권한이 거부되었습니다. 브라우저 설정에서 권한을 허용해주세요.');
          }
        } catch (permError) {
          console.log('권한 조회 실패:', permError);
          // 권한 조회 실패는 무시하고 계속 진행
        }
      }

      setIsInitialized(true);
    } catch (error) {
      console.error('미디어 지원 확인 실패:', error);
      setPermissionError('미디어 장치 확인 중 오류가 발생했습니다');
    }
  };

  const startRecording = async () => {
    try {
      console.log('🚀 startRecording 시작 - 초기화 플래그 설정');
      isInitializingRef.current = true; // 초기화 시작
      setIsLoading(true);
      setPermissionError(null);

      // 브라우저 지원 확인
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('이 브라우저는 미디어 녹화를 지원하지 않습니다');
      }

      console.log('🎥 미디어 스트림 요청 중...');

      // 미디어 스트림 요청
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });

      console.log('✅ 미디어 스트림 획득 성공:', stream);

      streamRef.current = stream;

      // 비디오 프리뷰 설정
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // MediaRecorder 설정 및 지원 형식 확인
      console.log('🔧 MediaRecorder 지원 형식 확인:');
      console.log('- video/webm:', MediaRecorder.isTypeSupported('video/webm'));
      console.log('- video/webm;codecs=vp9:', MediaRecorder.isTypeSupported('video/webm;codecs=vp9'));
      console.log('- video/webm;codecs=vp8:', MediaRecorder.isTypeSupported('video/webm;codecs=vp8'));
      console.log('- video/mp4:', MediaRecorder.isTypeSupported('video/mp4'));

      const options: MediaRecorderOptions = {};
      
      // 지원되는 형식 우선순위로 설정
      if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
        options.mimeType = 'video/webm;codecs=vp8';
      } else if (MediaRecorder.isTypeSupported('video/webm')) {
        options.mimeType = 'video/webm';
      } else if (MediaRecorder.isTypeSupported('video/mp4')) {
        options.mimeType = 'video/mp4';
      }

      console.log('🎬 선택된 MediaRecorder 설정:', options);

      // 스트림 상태 확인
      console.log('📡 MediaStream 상태:', {
        id: stream.id,
        active: stream.active,
        videoTracks: stream.getVideoTracks().length,
        audioTracks: stream.getAudioTracks().length
      });

      stream.getVideoTracks().forEach((track, index) => {
        console.log(`📹 비디오 트랙 ${index}:`, {
          id: track.id,
          kind: track.kind,
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState
        });

        // 트랙 이벤트 리스너 추가
        track.addEventListener('ended', () => {
          console.error('❌ 비디오 트랙이 예상치 않게 종료됨:', {
            trackId: track.id,
            timestamp: new Date().toISOString(),
            mediaRecorderState: mediaRecorderRef.current?.state
          });
        });

        track.addEventListener('mute', () => {
          console.warn('🔇 비디오 트랙이 음소거됨:', track.id);
        });
      });

      stream.getAudioTracks().forEach((track, index) => {
        console.log(`🎤 오디오 트랙 ${index}:`, {
          id: track.id,
          kind: track.kind,
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState
        });

        // 트랙 이벤트 리스너 추가
        track.addEventListener('ended', () => {
          console.error('❌ 오디오 트랙이 예상치 않게 종료됨:', {
            trackId: track.id,
            timestamp: new Date().toISOString(),
            mediaRecorderState: mediaRecorderRef.current?.state
          });
        });
      });

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      console.log('📱 MediaRecorder 생성됨:', {
        state: mediaRecorder.state,
        mimeType: mediaRecorder.mimeType,
        videoBitsPerSecond: mediaRecorder.videoBitsPerSecond,
        audioBitsPerSecond: mediaRecorder.audioBitsPerSecond
      });

      // 이벤트 리스너는 start() 호출 전에 등록해야 함
      mediaRecorder.ondataavailable = (event) => {
        console.log('📊 MediaRecorder 데이터 수신:', { size: event.data.size, type: event.data.type });
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstart = () => {
        console.log('🎬 MediaRecorder 시작됨:', { state: mediaRecorder.state, timestamp: new Date().toISOString() });
      };

      mediaRecorder.onstop = () => {
        console.log('⏹️ MediaRecorder 중단됨:', { 
          state: mediaRecorder.state,
          chunksCount: chunksRef.current.length,
          totalSize: chunksRef.current.reduce((total, chunk) => total + chunk.size, 0),
          recordingTime,
          timestamp: new Date().toISOString()
        });

        const mimeType = mediaRecorder.mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        
        console.log('📦 생성된 Blob:', { 
          size: blob.size, 
          type: blob.type,
          recordingDuration: recordingTime,
          timestamp: new Date().toISOString()
        });

        // 최소 녹화 조건 확인
        if (blob.size === 0) {
          console.error('❌ 녹화된 데이터가 없습니다 (0바이트)');
          onError('녹화에 실패했습니다. 다시 시도해주세요.');
          return;
        }

        if (recordingTime < 1) {
          console.warn('⚠️ 녹화 시간이 너무 짧습니다:', recordingTime, '초');
          onError('최소 1초 이상 녹화해주세요.');
          return;
        }

        onRecordingComplete(blob);
        
        // 스트림 정리
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('❌ MediaRecorder 오류:', event);
        onError('녹화 중 오류가 발생했습니다');
      };

      // 녹화 시작 전 상태 확인
      if ((mediaRecorder.state as RecordingState) !== 'inactive') {
        console.error('❌ MediaRecorder가 비활성 상태가 아님:', mediaRecorder.state);
        throw new Error('MediaRecorder 상태가 올바르지 않습니다');
      }

      // React 상태를 먼저 업데이트 (동기화 문제 해결)
      setIsRecording(true);
      setRecordingTime(0);
      setIsLoading(false);
      recordingStartTimeRef.current = Date.now(); // 녹화 시작 시간 기록

      // 녹화 시작
      console.log('🎬 녹화 시작 시도...', { timestamp: new Date().toISOString() });
      mediaRecorder.start(1000); // 1초마다 데이터 수집
      
      // 짧은 지연 후 상태 확인
      await new Promise(resolve => setTimeout(resolve, 100));
      console.log('🔴 녹화 시작 후 상태:', mediaRecorder.state);
      
      if ((mediaRecorder.state as RecordingState) !== 'recording') {
        console.error('❌ 녹화가 시작되지 않음. 현재 상태:', mediaRecorder.state);
        setIsRecording(false); // 실패 시 상태 되돌리기
        recordingStartTimeRef.current = null;
        isInitializingRef.current = false; // 초기화 실패 시 플래그 해제
        throw new Error('녹화를 시작할 수 없습니다. 브라우저 호환성을 확인하세요.');
      }
      
      // 초기화 완료
      isInitializingRef.current = false;
      console.log('✅ MediaRecorder 초기화 완료 - 보호 플래그 해제');

      // 타이머 시작
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      console.log('✅ 녹화 성공적으로 시작됨');

    } catch (error) {
      setIsLoading(false);
      isInitializingRef.current = false; // 에러 시에도 플래그 해제
      const errorMessage = error instanceof Error ? error.message : '녹화를 시작할 수 없습니다';
      
      // 권한 관련 오류인지 확인
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError' || error.message.includes('Permission denied')) {
          setPermissionError('카메라와 마이크 접근 권한이 필요합니다. 브라우저에서 권한을 허용해주세요.');
        } else if (error.name === 'NotFoundError') {
          setPermissionError('카메라나 마이크를 찾을 수 없습니다. 장치가 연결되어 있는지 확인해주세요.');
        } else {
          setPermissionError(errorMessage);
        }
      } else {
        setPermissionError(errorMessage);
      }
      
      onError(errorMessage);
      console.error('Recording start error:', error);
    }
  };


  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // 로딩 중이면 로딩 화면 표시
  if (!isInitialized) {
    return (
      <div className="space-y-4">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">미디어 장치 확인 중...</p>
        </div>
      </div>
    );
  }

  // 권한 오류가 있으면 오류 화면 표시
  if (permissionError) {
    return (
      <div className="space-y-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="text-center">
            <div className="text-red-500 text-4xl mb-4">🚫</div>
            <h3 className="text-red-800 font-medium text-lg mb-2">미디어 접근 오류</h3>
            <p className="text-red-700 text-sm mb-4">{permissionError}</p>
            <div className="space-y-2 text-xs text-red-600">
              <p>💡 해결 방법:</p>
              <p>1. 브라우저 주소창 옆의 카메라/마이크 아이콘 클릭</p>
              <p>2. "허용"으로 설정 후 페이지 새로고침</p>
              <p>3. 또는 브라우저 설정에서 카메라/마이크 권한 허용</p>
            </div>
            <button
              onClick={() => {
                setPermissionError(null);
                checkMediaSupport();
              }}
              className="mt-4 bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition-colors"
            >
              🔄 다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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
        
        {isRecording && (
          <div className="absolute top-2 left-2 bg-red-500 text-white px-2 py-1 rounded text-sm font-bold animate-pulse">
            🔴 REC {formatTime(recordingTime)}
          </div>
        )}
      </div>

      {/* 녹화 제어 버튼 */}
      <div className="flex justify-center space-x-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={isLoading}
            className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>권한 요청 중...</span>
              </>
            ) : (
              <>
                <span>🔴</span>
                <span>녹화 시작</span>
              </>
            )}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-6 py-3 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2 animate-pulse"
          >
            <span>⏹️</span>
            <span>녹화 정지</span>
          </button>
        )}
      </div>

      {/* 상태 정보 */}
      <div className="text-center text-sm text-gray-600">
        {!isRecording && !isLoading && (
          <p>📱 카메라와 마이크 권한을 허용한 후 녹화를 시작하세요</p>
        )}
        {isLoading && (
          <p className="text-blue-600 font-medium">🔄 미디어 권한 요청 중...</p>
        )}
        {isRecording && (
          <p className="text-red-600 font-medium">
            🔴 녹화 중... ({formatTime(recordingTime)})
          </p>
        )}
      </div>
    </div>
  );
};

export default VideoTestRecorder;