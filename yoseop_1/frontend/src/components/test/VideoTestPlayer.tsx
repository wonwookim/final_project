import React, { useState, useEffect, useRef } from 'react';
import { PlayerProps, TestPlayResponse } from './types';

const VideoTestPlayer: React.FC<PlayerProps> = ({ testId, onError }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoInfo, setVideoInfo] = useState<TestPlayResponse | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (testId) {
      loadVideo();
    }
  }, [testId]);

  const loadVideo = async () => {
    setIsLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('로그인이 필요합니다');
      }

      const response = await fetch(`/video/test/play/${testId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`비디오 로드 실패: ${response.status}`);
      }

      const data: TestPlayResponse = await response.json();
      setVideoInfo(data);
      setVideoUrl(data.play_url);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '비디오를 로드할 수 없습니다';
      onError(errorMessage);
      console.error('Video load failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlay = () => {
    if (videoRef.current) {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleVideoEnded = () => {
    setIsPlaying(false);
  };

  const downloadVideo = () => {
    if (videoUrl && videoInfo) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = videoInfo.file_name || 'test-video.webm';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">비디오를 로드하는 중...</p>
        </div>
      </div>
    );
  }

  if (!videoUrl || !videoInfo) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600 mb-4">비디오를 로드할 수 없습니다.</p>
        <button
          onClick={loadVideo}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 비디오 정보 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-2">🎬 비디오 정보</h4>
        <div className="text-sm text-gray-600 space-y-1">
          <p>파일명: {videoInfo.file_name}</p>
          <p>형식: {videoInfo.file_type}</p>
          <p>테스트 ID: {videoInfo.test_id}</p>
        </div>
      </div>

      {/* 비디오 플레이어 */}
      <div className="relative">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          className="w-full max-w-md mx-auto rounded-lg bg-gray-900"
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={handleVideoEnded}
          preload="metadata"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      {/* 제어 버튼들 */}
      <div className="flex justify-center space-x-4">
        <button
          onClick={isPlaying ? handlePause : handlePlay}
          className="bg-gradient-to-r from-green-500 to-green-600 text-white px-4 py-2 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
        >
          <span>{isPlaying ? '⏸️' : '▶️'}</span>
          <span>{isPlaying ? '일시정지' : '재생'}</span>
        </button>

        <button
          onClick={downloadVideo}
          className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-4 py-2 rounded-full font-bold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
        >
          <span>⬇️</span>
          <span>다운로드</span>
        </button>
      </div>

      {/* 재생 상태 */}
      <div className="text-center text-sm text-gray-600">
        {isPlaying ? (
          <p className="text-green-600 font-medium">🎬 재생 중...</p>
        ) : (
          <p>📱 재생 버튼을 눌러 비디오를 시청하세요</p>
        )}
      </div>
    </div>
  );
};

export default VideoTestPlayer;