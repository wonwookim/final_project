import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import VoiceControls from '../components/voice/VoiceControls';
import SpeechIndicator from '../components/voice/SpeechIndicator';
import { useInterview } from '../contexts/InterviewContext';
import { sessionApi, interviewApi } from '../services/api';

const InterviewGO: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();

  // sessionId를 InterviewService 상태에서 가져오기
  React.useEffect(() => {
    const loadSessionFromService = async () => {
      try {
        // 1. 이미 Context에 sessionId가 있으면 OK
        if (state.sessionId) {
          console.log('✅ Context에 sessionId 존재:', state.sessionId);
          setIsRestoring(false);
          return;
        }

        // 2. InterviewService의 활성 세션에서 sessionId 가져오기
        console.log('🔍 InterviewService에서 활성 세션 조회 중...');
        const latestSessionId = await sessionApi.getLatestSessionId();
        
        if (latestSessionId) {
          console.log('✅ InterviewService에서 sessionId 발견:', latestSessionId);
          
          // 세션 상태도 함께 가져오기
          const sessionState = await sessionApi.getSessionState(latestSessionId);
          console.log('📋 세션 상태:', sessionState);
          
          // Context에 sessionId 설정
          dispatch({ type: 'SET_SESSION_ID', payload: latestSessionId });
          setIsRestoring(false);
          return;
        }

        // 3. localStorage에서 sessionId 복원 시도 (fallback)
        const saved = localStorage.getItem('interview_state');
        if (saved) {
          const parsedState = JSON.parse(saved);
          console.log('📦 localStorage에서 상태 복원 시도:', parsedState.sessionId);
          
          if (parsedState.sessionId) {
            dispatch({ type: 'SET_SESSION_ID', payload: parsedState.sessionId });
            console.log('✅ localStorage에서 sessionId 복원 완료:', parsedState.sessionId);
            setIsRestoring(false);
            return;
          }
        }

        // 4. sessionId가 없으면 환경 체크로 이동
        console.log('❌ sessionId를 찾을 수 없습니다. 환경 체크 페이지로 이동합니다.');
        navigate('/interview/environment-check');
        
      } catch (error) {
        console.error('❌ sessionId 로드 실패:', error);
        navigate('/interview/environment-check');
      } finally {
        setIsRestoring(false);
      }
    };

    loadSessionFromService();
  }, [state.sessionId, dispatch, navigate]);

  // 난이도별 AI 지원자 이미지 매핑 함수
  const getAICandidateImage = (level: number): string => {
    if (level <= 3) return '/img/candidate_1.png'; // 초급자
    if (level <= 7) return '/img/candidate_2.png'; // 중급자
    return '/img/candidate_3.png'; // 고급자
  };

  // 난이도별 AI 지원자 이름 매핑 함수
  const getAICandidateName = (level: number): string => {
    if (level <= 3) return '춘식이 (초급)';
    if (level <= 7) return '춘식이 (중급)';
    return '춘식이 (고급)';
  };
  
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true); // 복원 상태 추가
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const submitAnswer = async () => {
    if (!currentAnswer.trim()) {
      console.log('❌ 답변이 입력되지 않았습니다.');
      return;
    }

    if (isLoading) {
      console.log('❌ 이미 제출 중입니다.');
      return;
    }

    // InterviewService에서 sessionId 확인
    let sessionId = state.sessionId;
    if (!sessionId) {
      console.log('🔍 Context에 sessionId가 없습니다. InterviewService에서 재조회...');
      try {
        sessionId = await sessionApi.getLatestSessionId();
        if (sessionId) {
          dispatch({ type: 'SET_SESSION_ID', payload: sessionId });
          console.log('✅ InterviewService에서 sessionId 복원:', sessionId);
        }
      } catch (error) {
        console.error('❌ sessionId 조회 실패:', error);
      }
    }

    if (!sessionId) {
      console.log('❌ sessionId가 없습니다. 면접을 다시 시작해주세요.');
      alert('세션이 만료되었습니다. 면접을 다시 시작해주세요.');
      navigate('/interview/environment-check');
      return;
    }

    try {
      setIsLoading(true);
      console.log('🚀 답변 제출 시작:', {
        sessionId: sessionId,
        answer: currentAnswer,
        answerLength: currentAnswer.length,
        apiBaseUrl: 'http://127.0.0.1:8000'
      });

      // interviewApi를 사용해 답변 제출
      const result = await interviewApi.submitUserAnswer(
        sessionId,
        currentAnswer.trim(),
        0 // 시간 측정 기능 제거로 기본값 사용
      );

      console.log('✅ 답변 제출 성공:', result);

      // 답변 초기화
      setCurrentAnswer('');
      
      // TODO: 실제 결과에 따른 상태 업데이트 로직 추가

    } catch (error: any) {
      console.error('❌ 답변 제출 오류:', error);
      
      let errorMessage = '알 수 없는 오류';
      if (error.response) {
        // 서버가 응답했지만 에러 상태 코드
        console.error('서버 응답 에러:', {
          status: error.response.status,
          data: error.response.data,
          url: error.config?.url
        });
        errorMessage = `HTTP ${error.response.status}: ${error.response.data?.detail || error.response.statusText}`;
      } else if (error.request) {
        // 요청이 만들어졌지만 응답을 받지 못함
        console.error('네트워크 에러:', error.request);
        errorMessage = '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
      } else {
        // 요청 설정 중 에러 발생
        console.error('요청 설정 에러:', error.message);
        errorMessage = error.message;
      }
      
      alert(`답변 제출 실패: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">
      <Header 
        title={`${state.settings?.company || '쿠팡'} 면접`}
        subtitle={`${state.settings?.position || '개발자'} - 춘식이와의 실시간 경쟁`}
      />

      {/* 메인 인터페이스 */}
      <div className="flex-1 flex flex-col">
        {/* 상단 면접관 영역 */}
        <div className="grid grid-cols-3 gap-4 p-4" style={{ height: '40vh' }}>
          {/* 인사 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_1.jpg"
                alt="인사 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 협업 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_2.jpg"
                alt="협업 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 기술 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_3.jpg"
                alt="기술 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>

        {/* 하단 영역 */}
        <div className="grid gap-4 p-4" style={{ height: '60vh', gridTemplateColumns: '2fr 1fr 2fr' }}>
          {/* 사용자 영역 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-yellow-500 shadow-lg shadow-yellow-500/50">
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold z-10">
              사용자: {state.settings?.candidate_name || 'You'}
            </div>
            
            {/* 실제 사용자 비디오 - 항상 렌더링 */}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }}
            />
            
            {/* 📹 카메라 연결 상태 오버레이 */}
            {!state.cameraStream && (
              <div className="absolute inset-0 h-full flex items-center justify-center bg-gray-800">
                <div className="text-white text-lg opacity-50">
                  카메라 대기 중...
                </div>
              </div>
            )}
            
            {/* 라이브 표시 */}
            <div className="absolute top-4 right-4 bg-red-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
              LIVE
            </div>

            {/* 답변 입력 오버레이 */}
            <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4">
              <textarea
                ref={answerRef}
                value={currentAnswer}
                onChange={(e) => setCurrentAnswer(e.target.value)}
                className="w-full h-20 p-2 bg-gray-800 text-white border border-gray-600 rounded-lg resize-none text-sm"
                placeholder="답변을 입력해주세요..."
              />
              <div className="flex items-center justify-between mt-2">
                <div className="text-gray-400 text-xs">{currentAnswer.length}자</div>
              </div>
            </div>
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
            {/* 현재 질문 표시 */}
            <div className="text-center mb-6">
              <div className="text-gray-400 text-sm mb-2">현재 질문</div>
              <div className="text-white text-base leading-relaxed line-clamp-2 mb-3">
                Context에서 질문을 가져올 예정입니다.
              </div>
            </div>

            {/* 컨트롤 버튼 */}
            <div className="space-y-3">
              {(() => {
                const hasAnswer = !!currentAnswer.trim();
                const hasSessionId = !!state.sessionId || !isRestoring;
                const isButtonDisabled = !hasAnswer || isLoading || isRestoring;
                
                return (
                  <button 
                    className={`w-full py-3 text-white rounded-lg font-semibold transition-colors ${
                      isButtonDisabled 
                        ? 'bg-gray-600 cursor-not-allowed' 
                        : 'bg-green-600 hover:bg-green-500'
                    }`}
                    onClick={submitAnswer}
                    disabled={isButtonDisabled}
                  >
                    {isLoading 
                      ? '제출 중...' 
                      : isRestoring
                      ? '세션 로드 중...'
                      : !hasSessionId 
                      ? '세션 없음' 
                      : '🚀 답변 제출'
                    }
                  </button>
                );
              })()}
            </div>
          </div>

          {/* AI 지원자 춘식이 */}
          <div className="bg-blue-900 rounded-lg overflow-hidden relative border-2 border-gray-600">
            <div className="absolute top-4 left-4 text-green-400 font-semibold z-10">
              AI 지원자 {getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
            </div>
            
            {/* AI 지원자 전체 이미지 */}
            <div className="h-full flex items-center justify-center relative">
              <img 
                src={getAICandidateImage(state.aiSettings?.aiQualityLevel || 6)}
                alt={getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
                className="w-full h-full object-cover"
              />
              
              {/* 상태 표시 오버레이 */}
              <div className="absolute bottom-4 right-4 bg-black/70 rounded-lg p-2">
                <div className="text-blue-300 text-sm">대기 중</div>
              </div>
              
              {/* 라이브 표시 */}
              <div className="absolute top-4 right-4 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
                AI
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewGO;
