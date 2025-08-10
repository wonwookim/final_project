import React, { useState, useEffect, useRef } from 'react';
import { GazeAnalysisProps, AnalysisStatusResponse } from './types';

const API_BASE_URL = 'http://127.0.0.1:8000';

const VideoGazeAnalysis: React.FC<GazeAnalysisProps> = ({ 
  videoUrl, 
  calibrationSessionId, 
  onAnalysisComplete, 
  onProgress, 
  onError 
}) => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [currentMessage, setCurrentMessage] = useState<string>('분석 준비 중...');
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null);
  const hasStartedRef = useRef<boolean>(false);

  // 분석 시작
  const startAnalysis = async () => {
    try {
      console.log('🔍 시선 분석 시작:', { videoUrl, calibrationSessionId });
      
      const response = await fetch(`${API_BASE_URL}/test/gaze/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_url: videoUrl,
          session_id: calibrationSessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `분석 시작 실패: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ 분석 작업 시작됨:', data);
      
      setTaskId(data.task_id);
      setCurrentMessage('동영상 시선 분석이 시작되었습니다...');
      
      // 상태 체크 시작
      startStatusCheck(data.task_id);
      
    } catch (error) {
      console.error('❌ 분석 시작 오류:', error);
      onError(error instanceof Error ? error.message : '시선 분석을 시작할 수 없습니다.');
    }
  };

  // 상태 체크 시작
  const startStatusCheck = (taskId: string) => {
    if (statusCheckInterval.current) {
      clearInterval(statusCheckInterval.current);
    }

    statusCheckInterval.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/test/gaze/analyze/status/${taskId}`);
        
        if (!response.ok) {
          throw new Error(`상태 체크 실패: ${response.status}`);
        }

        const statusData: AnalysisStatusResponse = await response.json();
        console.log('📊 분석 상태:', statusData);
        
        setStatus(statusData);
        
        // 진행률 업데이트
        if (statusData.progress !== undefined) {
          onProgress(statusData.progress);
        }
        
        // 상태별 메시지 업데이트
        updateMessage(statusData);

        // 완료 또는 실패 체크
        if (statusData.status === 'completed') {
          console.log('🎉 시선 분석 완료!');
          
          if (statusCheckInterval.current) {
            clearInterval(statusCheckInterval.current);
            statusCheckInterval.current = null;
          }
          
          if (statusData.result) {
            onAnalysisComplete(statusData.result);
          } else {
            onError('분석 결과를 받을 수 없습니다.');
          }
          
        } else if (statusData.status === 'failed') {
          console.error('❌ 시선 분석 실패:', statusData.error);
          
          if (statusCheckInterval.current) {
            clearInterval(statusCheckInterval.current);
            statusCheckInterval.current = null;
          }
          
          onError(statusData.error || '시선 분석에 실패했습니다.');
        }
        
      } catch (error) {
        console.error('❌ 상태 체크 오류:', error);
      }
    }, 2000); // 2초마다 체크
  };

  // 상태별 메시지 업데이트
  const updateMessage = (statusData: AnalysisStatusResponse) => {
    const progress = statusData.progress || 0;
    
    if (progress < 0.2) {
      setCurrentMessage('동영상 다운로드 중...');
    } else if (progress < 0.4) {
      setCurrentMessage('동영상 분석 준비 중...');
    } else if (progress < 0.8) {
      setCurrentMessage('MediaPipe로 시선 추적 중...');
    } else if (progress < 0.95) {
      setCurrentMessage('시선 안정성 점수 계산 중...');
    } else {
      setCurrentMessage('분석 완료 중...');
    }
  };

  // 컴포넌트 마운트 시 자동으로 분석 시작
  useEffect(() => {
    if (!hasStartedRef.current && videoUrl && calibrationSessionId) {
      hasStartedRef.current = true;
      startAnalysis();
    }
    
    return () => {
      // 정리
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
      }
    };
  }, [videoUrl, calibrationSessionId]);

  const progress = status?.progress || 0;

  return (
    <div className="space-y-6">
      {/* 분석 상태 헤더 */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6 text-center">
        <h4 className="font-bold text-gray-900 text-lg mb-2">👁️ 시선 분석 진행 중</h4>
        <p className="text-gray-700 mb-4">{currentMessage}</p>
        
        {/* 진행률 바 */}
        <div className="w-full bg-gray-200 rounded-full h-4 mb-3">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-4 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
        
        <div className="flex justify-between text-sm text-gray-600">
          <span>진행률</span>
          <span className="font-bold">{Math.round(progress * 100)}%</span>
        </div>
      </div>

      {/* 분석 단계 표시 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { step: 1, label: '동영상 다운로드', threshold: 0.2, icon: '📥' },
          { step: 2, label: '프레임 분석', threshold: 0.4, icon: '🎬' },
          { step: 3, label: '시선 추적', threshold: 0.8, icon: '👁️' },
          { step: 4, label: '점수 계산', threshold: 1.0, icon: '📊' }
        ].map(({ step, label, threshold, icon }) => {
          const isActive = progress >= (threshold - 0.2);
          const isComplete = progress >= threshold;
          
          return (
            <div
              key={step}
              className={`
                p-4 rounded-lg border text-center transition-all duration-300
                ${isComplete 
                  ? 'bg-green-50 border-green-200 text-green-800' 
                  : isActive 
                    ? 'bg-blue-50 border-blue-200 text-blue-800' 
                    : 'bg-gray-50 border-gray-200 text-gray-500'
                }
              `}
            >
              <div className="text-2xl mb-2">
                {isComplete ? '✅' : isActive ? icon : '⏳'}
              </div>
              <div className="font-medium text-sm">{label}</div>
              <div className="text-xs mt-1">단계 {step}</div>
            </div>
          );
        })}
      </div>

      {/* 분석 정보 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h5 className="font-medium text-gray-900 mb-3">🔍 분석 정보</h5>
        <div className="space-y-2 text-sm text-gray-600">
          <div className="flex justify-between">
            <span>동영상 URL:</span>
            <span className="font-mono text-xs">{videoUrl.split('?')[0]}...</span>
          </div>
          <div className="flex justify-between">
            <span>캘리브레이션 세션:</span>
            <span className="font-mono text-xs">{calibrationSessionId?.substring(0, 8)}...</span>
          </div>
          {taskId && (
            <div className="flex justify-between">
              <span>분석 작업 ID:</span>
              <span className="font-mono text-xs">{taskId.substring(0, 8)}...</span>
            </div>
          )}
          {status && (
            <div className="flex justify-between">
              <span>분석 상태:</span>
              <span className={`font-medium ${
                status.status === 'processing' ? 'text-blue-600' :
                status.status === 'completed' ? 'text-green-600' :
                'text-red-600'
              }`}>
                {status.status === 'processing' ? '진행 중' :
                 status.status === 'completed' ? '완료' :
                 '실패'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 로딩 스피너 */}
      <div className="flex justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>

      {/* 분석 팁 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h5 className="font-medium text-blue-900 mb-2">💡 분석 중 알아두세요</h5>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• MediaPipe AI로 프레임별 동공 위치를 정밀 추적합니다</li>
          <li>• 캘리브레이션 데이터를 기반으로 시선 범위를 계산합니다</li>
          <li>• 시선 안정성과 집중도를 종합적으로 평가합니다</li>
          <li>• 분석 시간은 동영상 길이에 따라 달라집니다</li>
        </ul>
      </div>
    </div>
  );
};

export default VideoGazeAnalysis;