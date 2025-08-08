import React, { useState } from 'react';
import VideoTestRecorder from './VideoTestRecorder';
import VideoTestUploader from './VideoTestUploader';
import VideoTestPlayer from './VideoTestPlayer';
import { TestSessionState } from './types';

interface VideoTestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const VideoTestModal: React.FC<VideoTestModalProps> = ({ isOpen, onClose }) => {
  const [sessionState, setSessionState] = useState<TestSessionState>({
    step: 'record',
    isRecording: false,
    isUploading: false,
    uploadProgress: 0,
    error: null,
    recordedBlob: null,
    testId: null,
    mediaId: null
  });

  const resetSession = () => {
    setSessionState({
      step: 'record',
      isRecording: false,
      isUploading: false,
      uploadProgress: 0,
      error: null,
      recordedBlob: null,
      testId: null,
      mediaId: null
    });
  };

  const handleRecordingComplete = (blob: Blob) => {
    setSessionState(prev => ({
      ...prev,
      step: 'upload',
      recordedBlob: blob,
      error: null
    }));
  };

  const handleUploadComplete = (testId: string, mediaId: string) => {
    setSessionState(prev => ({
      ...prev,
      step: 'play',
      testId,
      mediaId,
      error: null
    }));
  };

  const handleUploadProgress = (progress: number) => {
    setSessionState(prev => ({
      ...prev,
      uploadProgress: progress
    }));
  };

  const handleError = (error: string) => {
    setSessionState(prev => ({
      ...prev,
      error
    }));
  };

  const handleClose = () => {
    resetSession();
    onClose();
  };

  const goBackToRecord = () => {
    setSessionState(prev => ({
      ...prev,
      step: 'record',
      recordedBlob: null,
      testId: null,
      mediaId: null,
      error: null,
      uploadProgress: 0
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">🎬 S3 비디오 테스트</h2>
              <p className="text-gray-600 text-sm mt-1">동영상 녹화, 업로드, 재생 기능을 테스트합니다</p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
            >
              ×
            </button>
          </div>
          
          {/* 진행 단계 표시 */}
          <div className="flex justify-center mt-6">
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 ${sessionState.step === 'record' ? 'text-blue-600' : sessionState.step === 'upload' || sessionState.step === 'play' ? 'text-green-600' : 'text-gray-400'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${sessionState.step === 'record' ? 'bg-blue-100' : sessionState.step === 'upload' || sessionState.step === 'play' ? 'bg-green-100' : 'bg-gray-100'}`}>
                  1
                </div>
                <span className="text-sm font-medium">녹화</span>
              </div>
              
              <div className="w-8 h-0.5 bg-gray-300"></div>
              
              <div className={`flex items-center space-x-2 ${sessionState.step === 'upload' ? 'text-blue-600' : sessionState.step === 'play' ? 'text-green-600' : 'text-gray-400'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${sessionState.step === 'upload' ? 'bg-blue-100' : sessionState.step === 'play' ? 'bg-green-100' : 'bg-gray-100'}`}>
                  2
                </div>
                <span className="text-sm font-medium">업로드</span>
              </div>
              
              <div className="w-8 h-0.5 bg-gray-300"></div>
              
              <div className={`flex items-center space-x-2 ${sessionState.step === 'play' ? 'text-blue-600' : 'text-gray-400'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${sessionState.step === 'play' ? 'bg-blue-100' : 'bg-gray-100'}`}>
                  3
                </div>
                <span className="text-sm font-medium">재생</span>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-6">
          {/* 에러 메시지 */}
          {sessionState.error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <span className="text-red-500 text-xl mr-3">❌</span>
                <div>
                  <h4 className="text-red-800 font-medium">오류가 발생했습니다</h4>
                  <p className="text-red-700 text-sm mt-1">{sessionState.error}</p>
                </div>
              </div>
            </div>
          )}

          {/* 단계별 컴포넌트 */}
          {sessionState.step === 'record' && (
            <VideoTestRecorder
              onRecordingComplete={handleRecordingComplete}
              onError={handleError}
            />
          )}

          {sessionState.step === 'upload' && sessionState.recordedBlob && (
            <VideoTestUploader
              blob={sessionState.recordedBlob}
              onUploadComplete={handleUploadComplete}
              onUploadProgress={handleUploadProgress}
              onError={handleError}
            />
          )}

          {sessionState.step === 'play' && sessionState.testId && (
            <VideoTestPlayer
              testId={sessionState.testId}
              onError={handleError}
            />
          )}
        </div>

        {/* 푸터 */}
        <div className="border-t border-gray-200 p-6">
          <div className="flex justify-between">
            <div className="flex space-x-3">
              {sessionState.step !== 'record' && (
                <button
                  onClick={goBackToRecord}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  🔄 다시 녹화
                </button>
              )}
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleClose}
                className="px-6 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoTestModal;