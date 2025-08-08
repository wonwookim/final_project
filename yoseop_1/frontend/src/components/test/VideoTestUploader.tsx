import React, { useState, useEffect, useRef } from 'react';
import { UploaderProps, TestUploadResponse } from './types';

const API_BASE_URL = 'http://127.0.0.1:8000';

const VideoTestUploader: React.FC<UploaderProps> = ({ 
  blob, 
  onUploadComplete, 
  onUploadProgress, 
  onError 
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const useEffectExecutedRef = useRef<boolean>(false); // React.StrictMode 중복 실행 방지

  useEffect(() => {
    // React.StrictMode 중복 실행 방지
    if (useEffectExecutedRef.current) {
      console.log('⚠️ useEffect 이미 실행됨 - StrictMode 중복 방지');
      return;
    }
    useEffectExecutedRef.current = true;
    
    if (blob && !isUploading) {
      startUpload();
    }
  }, [blob]);

  const startUpload = async () => {
    if (!blob) return;

    setIsUploading(true);
    setProgress(0);
    setUploadStatus('업로드 준비 중...');

    try {
      const token = localStorage.getItem('auth_token');
      console.log('🔍 Retrieved token:', token ? `${token.substring(0, 50)}...` : 'null');
      if (!token) {
        throw new Error('로그인이 필요합니다');
      }

      // 파일 정보 준비
      const fileExtension = blob.type.includes('webm') ? 'webm' : 'mp4';
      const fileName = `test-video-${Date.now()}.${fileExtension}`;

      // 1. 업로드 URL 요청
      setProgress(10);
      setUploadStatus('업로드 URL 요청 중...');
      onUploadProgress(10);

      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
      console.log('🔍 Request headers:', headers);
      
      const response = await fetch(`${API_BASE_URL}/video/test/upload-url`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          interview_id: 999,  // 테스트용 고정 ID
          file_name: fileName,
          file_type: 'video',
          file_size: blob.size
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: null }));
        throw new Error((errorData as any).detail || `업로드 URL 요청 실패: ${response.status}`);
      }

      const { upload_url, media_id, test_id }: TestUploadResponse = await response.json();

      // 2. S3에 직접 업로드
      setProgress(30);
      setUploadStatus('S3에 업로드 중...');
      onUploadProgress(30);

      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        headers: {
          'Content-Type': blob.type
        },
        body: blob
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 업로드 실패: ${uploadResponse.status}`);
      }

      // 3. 업로드 완료 처리
      setProgress(90);
      setUploadStatus('업로드 완료 처리 중...');
      onUploadProgress(90);

      const completeResponse = await fetch(`/video/test/complete/${media_id}?file_size=${blob.size}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!completeResponse.ok) {
        console.warn('업로드 완료 처리 실패, 하지만 파일은 업로드됨');
      }

      // 4. 완료
      setProgress(100);
      setUploadStatus('업로드 완료!');
      onUploadProgress(100);
      onUploadComplete(test_id, media_id);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '업로드 중 오류가 발생했습니다';
      onError(errorMessage);
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 파일 정보 */}
      {blob && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">📁 파일 정보</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <p>크기: {(blob.size / (1024 * 1024)).toFixed(2)} MB</p>
            <p>형식: {blob.type}</p>
          </div>
        </div>
      )}

      {/* 업로드 진행상황 */}
      {isUploading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-blue-600 font-medium">📤 {uploadStatus}</span>
            <span className="text-blue-600 font-bold">{progress}%</span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          <div className="text-center text-sm text-gray-500">
            {progress < 100 ? '업로드가 진행 중입니다...' : '업로드가 완료되었습니다!'}
          </div>
        </div>
      )}

      {/* 완료 상태 */}
      {!isUploading && progress === 100 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="text-green-600 font-bold text-lg mb-2">
            ✅ 업로드 성공!
          </div>
          <div className="text-green-700 text-sm">
            S3에 성공적으로 업로드되었습니다.
          </div>
        </div>
      )}

      {/* 수동 재시도 버튼 (에러 시) */}
      {!isUploading && progress === 0 && blob && (
        <button
          onClick={startUpload}
          className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all"
        >
          📤 업로드 시작
        </button>
      )}
    </div>
  );
};

export default VideoTestUploader;