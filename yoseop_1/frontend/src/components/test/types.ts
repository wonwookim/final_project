// 테스트 관련 타입 정의

export interface TestUploadRequest {
  file_name: string;
  file_type: 'video' | 'audio';
  file_size?: number;
  duration?: number;
}

export interface TestUploadResponse {
  upload_url: string;
  media_id: string;
  test_id: string;
}

export interface TestPlayResponse {
  play_url: string;
  file_name: string;
  file_type: string;
  test_id: string;
}

export interface TestVideo {
  media_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  created_at: string;
  test_id: string;
}

export interface TestSessionState {
  step: 'record' | 'upload' | 'play' | 'complete';
  isRecording: boolean;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;
  recordedBlob: Blob | null;
  testId: string | null;
  mediaId: string | null;
}

export interface RecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  onError: (error: string) => void;
}

export interface UploaderProps {
  blob: Blob;
  onUploadComplete: (testId: string, mediaId: string) => void;
  onUploadProgress: (progress: number) => void;
  onError: (error: string) => void;
}

export interface PlayerProps {
  testId: string;
  onError: (error: string) => void;
}