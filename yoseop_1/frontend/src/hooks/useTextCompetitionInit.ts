import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { textCompetitionApi } from '../services/textCompetitionApi';
import { handleApiError } from '../services/api';

interface InitializationState {
  isInitialized: boolean;
  isLoading: boolean;
  error: string | null;
  currentQuestion: any | null;
  aiPersona: any | null;
  progress: { current: number; total: number; percentage: number } | null;
  sessionId: string | null;
}

interface UseTextCompetitionInitProps {
  sessionId: string | null;
  settings: any;
  textCompetitionData: any;
  onSessionIdUpdate: (sessionId: string) => void;
}

export const useTextCompetitionInit = ({
  sessionId,
  settings,
  textCompetitionData,
  onSessionIdUpdate
}: UseTextCompetitionInitProps) => {
  const navigate = useNavigate();
  const initializationAttempted = useRef(false);
  const [state, setState] = useState<InitializationState>({
    isInitialized: false,
    isLoading: false,
    error: null,
    currentQuestion: null,
    aiPersona: null,
    progress: null,
    sessionId: null
  });

  const initialize = async () => {
    // 중복 초기화 방지
    if (initializationAttempted.current || state.isInitialized) {
      console.log('🚫 이미 초기화 시도됨 또는 완료됨');
      return;
    }

    // 필수 조건 확인
    if (!sessionId || !settings) {
      console.log('🚫 초기화 조건 미충족:', { sessionId: !!sessionId, settings: !!settings });
      navigate('/interview/setup');
      return;
    }

    // 텍스트 경쟁 모드가 아니면 초기화하지 않음
    if (settings.mode !== 'text_competition') {
      console.log('🚫 텍스트 경쟁 모드가 아님:', settings.mode);
      return;
    }

    initializationAttempted.current = true;
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      console.log('🎯 텍스트 경쟁 모드 초기화 시작');

      // Context에 저장된 데이터가 있는지 확인
      if (textCompetitionData) {
        console.log('✨ Context에서 초기 데이터 사용');
        
        setState(prev => ({
          ...prev,
          isInitialized: true,
          isLoading: false,
          currentQuestion: textCompetitionData.initialQuestion,
          aiPersona: textCompetitionData.aiPersona,
          progress: textCompetitionData.progress || { current: 0, total: 15, percentage: 0 },
          sessionId
        }));

        console.log('✅ Context 데이터로 초기화 완료');
        return;
      }

      // 다단계 플로우에서 온 경우: 텍스트 경쟁 면접을 새로 시작
      console.log('🔄 다단계 플로우 - 텍스트 경쟁 면접 시작');

      const response = await textCompetitionApi.startTextCompetition(settings);
      console.log('✅ 텍스트 경쟁 면접 시작 응답:', response);

      // 세션 ID 업데이트 (새로 생성된 세션 ID 사용)
      if (response.session_id && response.session_id !== sessionId) {
        console.log('🔄 세션 ID 업데이트:', sessionId, '→', response.session_id);
        onSessionIdUpdate(response.session_id);
      }

      setState(prev => ({
        ...prev,
        isInitialized: true,
        isLoading: false,
        currentQuestion: response.question || null,
        aiPersona: response.ai_persona || null,
        progress: response.progress || { current: 0, total: 15, percentage: 0 },
        sessionId: response.session_id || sessionId
      }));

      console.log('✅ 텍스트 경쟁 면접 초기화 완료');

    } catch (error) {
      console.error('❌ 텍스트 경쟁 모드 초기화 실패:', error);
      const errorMessage = `면접 초기화 실패: ${handleApiError(error)}`;
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }));

      alert(errorMessage);
      navigate('/interview/setup');
    }
  };

  useEffect(() => {
    initialize();
  }, []); // 의존성 배열을 비워서 최초 1회만 실행

  return {
    ...state,
    retry: () => {
      initializationAttempted.current = false;
      setState(prev => ({ ...prev, isInitialized: false, error: null }));
      initialize();
    }
  };
};