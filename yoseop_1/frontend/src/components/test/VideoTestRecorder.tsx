import React, { useState, useRef, useEffect } from 'react';
import { RecorderProps } from './types';

const VideoTestRecorder: React.FC<RecorderProps> = ({ onRecordingComplete, onError }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      // 컴포넌트 언마운트 시 정리
      stopRecording();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      // 브라우저 지원 확인
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('이 브라우저는 미디어 녹화를 지원하지 않습니다');
      }

      // 미디어 스트림 요청
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });

      streamRef.current = stream;

      // 비디오 프리뷰 설정
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // MediaRecorder 설정
      const options: MediaRecorderOptions = {};
      if (MediaRecorder.isTypeSupported('video/webm')) {
        options.mimeType = 'video/webm';
      }

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
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
        onError('녹화 중 오류가 발생했습니다');
        console.error('MediaRecorder error:', event);
      };

      // 녹화 시작
      mediaRecorder.start(1000); // 1초마다 데이터 수집
      setIsRecording(true);
      setRecordingTime(0);

      // 타이머 시작
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '녹화를 시작할 수 없습니다';
      onError(errorMessage);
      console.error('Recording start error:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

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
            className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
          >
            <span>🔴</span>
            <span>녹화 시작</span>
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
        {!isRecording && (
          <p>📱 카메라와 마이크 권한을 허용한 후 녹화를 시작하세요</p>
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