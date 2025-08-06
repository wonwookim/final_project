import React, { useState, useRef, useEffect } from 'react';
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
  
  // 🆕 새로운 상태들 추가
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true); // 복원 상태 추가
  
  // 🆕 턴 관리 상태
  const [currentTurn, setCurrentTurn] = useState<'user' | 'ai' | 'waiting'>('waiting');
  const [timeLeft, setTimeLeft] = useState(120); // 2분 타이머
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [canSubmit, setCanSubmit] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // 🆕 타이머 관리
  useEffect(() => {
    // 사용자 턴이고 타이머가 활성화되어 있을 때만 타이머 실행
    if (currentTurn === 'user' && isTimerActive && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            handleTimeUp();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      // 타이머 정지
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [currentTurn, isTimerActive, timeLeft]);

  // 🆕 시간 만료 핸들러
  const handleTimeUp = () => {
    console.log('⏰ 시간 만료!');
    setIsTimerActive(false);
    setCanSubmit(false);
    alert('시간이 만료되었습니다!');
    // 자동으로 답변 제출
    submitAnswer();
  };

  // 🆕 타이머 포맷 함수
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // 🆕 타이머 색상 함수
  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  };

  // 🆕 턴 상태 업데이트 함수 (JSON 응답 기반)
  const updateTurnFromResponse = (response: any) => {
    console.log('🔄 턴 상태 업데이트:', response);
    
    // JSON 응답에서 턴 정보 추출 (실제 응답 구조에 맞게 수정)
    const status = response?.status || '';
    const isUserTurn = status === 'waiting_for_user' || 
                      status === 'waiting_for_user_answer' || 
                      status === 'user_turn' || 
                      status === 'user';
    
    const isAITurn = status === 'ai_answering' || 
                     status === 'ai_turn' || 
                     status === 'ai' ||
                     status === 'waiting_for_ai';
    
    console.log('🔍 턴 판단:', {
      status,
      isUserTurn,
      isAITurn,
      responseKeys: Object.keys(response || {})
    });
    
    if (isUserTurn) {
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120); // 2분으로 재설정
      setCanSubmit(true);
      console.log('✅ 사용자 턴으로 설정됨');
    } else if (isAITurn) {
      setCurrentTurn('ai');
      setIsTimerActive(false);
      setCanSubmit(false);
      console.log('✅ AI 턴으로 설정됨');
    } else {
      // 기본적으로 사용자 턴으로 설정 (대기 상태 방지)
      console.log('⚠️ 명확한 턴 정보가 없어서 사용자 턴으로 기본 설정');
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120);
      setCanSubmit(true);
    }

    // 현재 질문 업데이트
    if (response?.question) {
      setCurrentQuestion(response.question);
      console.log('📝 질문 업데이트:', response.question);
    }
  };

  // 🆕 주기적으로 턴 상태 확인
  useEffect(() => {
    if (!state.sessionId || isRestoring) return;

    const checkTurnStatus = async () => {
      try {
        console.log('🔍 턴 상태 확인 시작...');
        // 세션 상태 확인 API 호출 (실제 API에 맞게 수정 필요)
        const response = await sessionApi.getSessionState(state.sessionId!);
        console.log('📋 세션 상태 응답:', response);
        updateTurnFromResponse(response);
      } catch (error) {
        console.error('❌ 턴 상태 확인 실패:', error);
        // API 실패 시 기본적으로 사용자 턴으로 설정
        console.log('🔄 API 실패로 인한 기본 사용자 턴 설정');
        setCurrentTurn('user');
        setIsTimerActive(true);
        setTimeLeft(120);
        setCanSubmit(true);
      }
    };

    // 초기 확인
    checkTurnStatus();

    // 5초마다 상태 확인
    const interval = setInterval(checkTurnStatus, 5000);

    return () => clearInterval(interval);
  }, [state.sessionId, isRestoring]);

  // 🆕 초기 턴 상태 설정 (세션 로드 완료 후)
  useEffect(() => {
    if (!isRestoring && state.sessionId) {
      console.log('🚀 초기 턴 상태 설정');
      // 기본적으로 사용자 턴으로 시작
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120);
      setCanSubmit(true);
      
      // 테스트용 질문 설정
      setCurrentQuestion("자기소개를 해주세요.");
    }
  }, [isRestoring, state.sessionId]);

  const submitAnswer = async () => {
    if (!currentAnswer.trim()) {
      console.log('❌ 답변이 입력되지 않았습니다.');
      return;
    }

    if (isLoading) {
      console.log('❌ 이미 제출 중입니다.');
      return;
    }

    // 사용자 턴이 아니면 제출 불가
    if (currentTurn !== 'user') {
      console.log('❌ 사용자 턴이 아닙니다.');
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
      setIsTimerActive(false); // 타이머 정지
      setCanSubmit(false); // 제출 버튼 비활성화
      
      console.log('🚀 답변 제출 시작:', {
        sessionId: sessionId,
        answer: currentAnswer,
        answerLength: currentAnswer.length,
        timeSpent: 120 - timeLeft, // 사용한 시간
        apiBaseUrl: 'http://127.0.0.1:8000'
      });

      // interviewApi를 사용해 답변 제출
      const result = await interviewApi.submitUserAnswer(
        sessionId,
        currentAnswer.trim(),
        120 - timeLeft // 실제 사용한 시간
      );

      console.log('✅ 답변 제출 성공:', result);

      // 답변 초기화
      setCurrentAnswer('');
      
      // 응답에 따른 턴 상태 업데이트
      updateTurnFromResponse(result);

    } catch (error: any) {
      console.error('❌ 답변 제출 오류:', error);
      
      // 에러 발생 시 사용자 턴 상태 복구
      setCurrentTurn('user');
      setIsTimerActive(true);
      setCanSubmit(true);
      
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
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // 사용자 턴일 때
            currentTurn === 'user'
              ? 'border-yellow-500 shadow-lg shadow-yellow-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold z-10">
              사용자: {state.settings?.candidate_name || 'You'}
            </div>
            
            {/* 🆕 턴 상태 표시 */}
            {currentTurn === 'user' && (
              <div className="absolute top-4 right-4 bg-yellow-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🎯 답변 차례
              </div>
            )}
            
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
                disabled={currentTurn !== 'user'}
                className={`w-full h-20 p-2 bg-gray-800 text-white border border-gray-600 rounded-lg resize-none text-sm ${
                  currentTurn !== 'user' ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                placeholder={currentTurn === 'user' ? "답변을 입력해주세요..." : "대기 중..."}
              />
              <div className="flex items-center justify-between mt-2">
                <div className="text-gray-400 text-xs">{currentAnswer.length}자</div>
                {/* 🆕 타이머 표시 */}
                {currentTurn === 'user' && isTimerActive && (
                  <div className={`text-lg font-bold ${getTimerColor()}`}>
                    {formatTime(timeLeft)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
            {/* 🆕 현재 턴 상태 표시 */}
            <div className="text-center mb-4">
              <div className={`text-sm font-bold mb-2 ${
                currentTurn === 'user' ? 'text-yellow-400' : 
                currentTurn === 'ai' ? 'text-green-400' : 
                'text-gray-400'
              }`}>
                {currentTurn === 'user' ? '🎯 사용자 답변 차례' :
                 currentTurn === 'ai' ? '🤖 AI 답변 중' :
                 '⏳ 대기 중'}
              </div>
              
              {/* 🆕 타이머 표시 */}
              {currentTurn === 'user' && isTimerActive && (
                <div className={`text-2xl font-bold ${getTimerColor()} mb-2`}>
                  {formatTime(timeLeft)}
                </div>
              )}
            </div>

            {/* 현재 질문 표시 */}
            <div className="text-center mb-6">
              <div className="text-gray-400 text-sm mb-2">현재 질문</div>
              <div className="text-white text-base leading-relaxed line-clamp-2 mb-3">
                {currentQuestion || "질문을 불러오는 중..."}
              </div>
            </div>

            {/* 컨트롤 버튼 */}
            <div className="space-y-3">
              {(() => {
                const hasAnswer = !!currentAnswer.trim();
                const hasSessionId = !!state.sessionId || !isRestoring;
                const isUserTurn = currentTurn === 'user';
                const isButtonDisabled = !hasAnswer || isLoading || isRestoring || !isUserTurn || !canSubmit;
                
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
                      : !isUserTurn
                      ? '대기 중...'
                      : !canSubmit
                      ? '준비 중...'
                      : '🚀 답변 제출'
                    }
                  </button>
                );
              })()}
            </div>

            {/* 🆕 진행 상황 표시 */}
            <div className="mt-4 text-center">
              <div className="text-white text-sm mb-2">
                상태: {currentTurn === 'user' ? '사용자 턴' : currentTurn === 'ai' ? 'AI 턴' : '대기'}
              </div>
              
              {/* 🆕 디버깅 정보 */}
              <div className="text-gray-400 text-xs space-y-1">
                <div>세션: {state.sessionId ? '✅' : '❌'}</div>
                <div>복원: {isRestoring ? '🔄' : '✅'}</div>
                <div>타이머: {isTimerActive ? '⏰' : '⏸️'}</div>
                <div>제출: {canSubmit ? '✅' : '❌'}</div>
              </div>
              
              {/* 🆕 테스트 버튼들 */}
              <div className="mt-2 space-y-1">
                <button
                  onClick={() => {
                    setCurrentTurn('user');
                    setIsTimerActive(true);
                    setTimeLeft(120);
                    setCanSubmit(true);
                    console.log('🧪 수동으로 사용자 턴 설정');
                  }}
                  className="w-full py-1 px-2 bg-yellow-600 hover:bg-yellow-500 text-white text-xs rounded"
                >
                  🧪 사용자 턴 테스트
                </button>
                <button
                  onClick={() => {
                    setCurrentTurn('ai');
                    setIsTimerActive(false);
                    setCanSubmit(false);
                    console.log('🧪 수동으로 AI 턴 설정');
                  }}
                  className="w-full py-1 px-2 bg-green-600 hover:bg-green-500 text-white text-xs rounded"
                >
                  🧪 AI 턴 테스트
                </button>
              </div>
            </div>
          </div>

          {/* AI 지원자 춘식이 */}
          <div className={`bg-blue-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // AI 턴일 때
            currentTurn === 'ai'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-green-400 font-semibold z-10">
              AI 지원자 {getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
            </div>
            
            {/* 🆕 AI 턴 상태 표시 */}
            {currentTurn === 'ai' && (
              <div className="absolute top-4 right-4 bg-green-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🤖 답변 중
              </div>
            )}
            
            {/* AI 지원자 전체 이미지 */}
            <div className="h-full flex items-center justify-center relative">
              <img 
                src={getAICandidateImage(state.aiSettings?.aiQualityLevel || 6)}
                alt={getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
                className="w-full h-full object-cover"
              />
              
              {/* 상태 표시 오버레이 */}
              {currentTurn === 'ai' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-green-400 text-sm font-semibold mb-2">답변 중...</div>
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                </div>
              ) : (
                <div className="absolute bottom-4 right-4 bg-black/70 rounded-lg p-2">
                  <div className="text-blue-300 text-sm">대기 중</div>
                </div>
              )}
              
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
