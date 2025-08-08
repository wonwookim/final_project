import React, { useState, useRef } from 'react';

interface RecorderProps {
  interviewId: number;
  onUploadComplete?: () => void;
}

const InterviewRecorder: React.FC<RecorderProps> = ({ interviewId, onUploadComplete }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // 녹화 시작
  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: true, 
      audio: true 
    });
    
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    chunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      chunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      await uploadVideo(blob);
      
      // 스트림 정리
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start();
    setIsRecording(true);
  };

  // 녹화 정지
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // 비디오 업로드
  const uploadVideo = async (blob: Blob) => {
    setIsUploading(true);
    
    try {
      // 1. 업로드 URL 요청
      const response = await fetch('/video/upload-url', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          interview_id: interviewId,
          file_name: `interview-${interviewId}-${Date.now()}.webm`
        })
      });
      
      const { upload_url, media_id } = await response.json();
      
      // 2. S3에 직접 업로드
      await fetch(upload_url, {
        method: 'PUT',
        body: blob
      });
      
      // 3. 업로드 완료 처리
      await fetch(`/video/complete/${media_id}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      onUploadComplete?.();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-bold mb-4">면접 녹화</h3>
      
      {!isRecording && !isUploading && (
        <button 
          onClick={startRecording}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          🔴 녹화 시작
        </button>
      )}
      
      {isRecording && (
        <button 
          onClick={stopRecording}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
        >
          ⏹️ 녹화 정지
        </button>
      )}
      
      {isUploading && (
        <div className="text-blue-600">
          📤 업로드 중...
        </div>
      )}
    </div>
  );
};

export default InterviewRecorder;