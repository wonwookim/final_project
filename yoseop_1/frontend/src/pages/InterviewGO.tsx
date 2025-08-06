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
  
  const [interviewState, setInterviewState] = useState<'ready' | 'active' | 'paused' | 'completed' | 'ai_answering' | 'comparison_mode'>('active');
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_turn' | 'interviewer_question'>('user_turn');
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [timeLeft, setTimeLeft] = useState(120);
  const [isLoading, setIsLoading] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [showQuestionModal, setShowQuestionModal] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true); // 복원 상태 추가
  
  // STT/TTS 관련 상태
  const [isSTTActive, setIsSTTActive] = useState(false);
  const [isTTSActive, setIsTTSActive] = useState(false);
  const [ttsType, setTtsType] = useState<'question' | 'ai_answer' | 'general'>('general');
  const [currentInterviewerType, setCurrentInterviewerType] = useState<'hr' | 'tech' | 'collaboration' | null>(null);
  const [interimText, setInterimText] = useState('');
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // 더미 질문 데이터
  const currentQuestion = {
    question: "자기소개를 해주세요.",
    category: "자기소개"
  };

  // 더미 타임라인 데이터
  const timeline = [
    { id: '1', type: 'interviewer' as const, question: '자기소개를 해주세요.', answer: '안녕하세요...', questionType: 'HR' },
    { id: '2', type: 'user' as const, question: '지원동기는 무엇인가요?', questionType: 'HR' },
    { id: '3', type: 'ai' as const, question: '협업 경험에 대해 말해주세요.', questionType: 'COLLABORATION' }
  ];

  // 더미 핸들러 함수들 (기능 없음)
  const handleStartSTT = () => {
    console.log('STT 시작 (더미)');
    setIsSTTActive(true);
  };

  const handleStopSTT = () => {
    console.log('STT 중지 (더미)');
    setIsSTTActive(false);
  };

  const handlePlayTTS = () => {
    console.log('TTS 재생 (더미)');
    setIsTTSActive(true);
  };

  const handleStopTTS = () => {
    console.log('TTS 중지 (더미)');
    setIsTTSActive(false);
  };

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
        120 - timeLeft // 소요 시간 계산
      );

      console.log('✅ 답변 제출 성공:', result);

      // 답변 초기화
      setCurrentAnswer('');
      
      // 상태 업데이트 (응답에 따라)
      if (result.status === 'waiting_for_user') {
        // 아직 사용자 차례
        setCurrentPhase('user_turn');
      } else if (result.status === 'completed') {
        // 면접 완료
        setInterviewState('completed');
      } else {
        // AI 차례로 변경
        setCurrentPhase('ai_turn');
      }

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

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimerColor = (): string => {
    if (timeLeft <= 30) return 'text-red-500';
    if (timeLeft <= 60) return 'text-yellow-500';
    return 'text-white';
  };

  const renderQuestionModal = () => {
    if (!showQuestionModal) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">현재 질문</h3>
            <button
              onClick={() => setShowQuestionModal(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>
          <div className="text-gray-700 text-base leading-relaxed">
            {currentQuestion.question}
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setShowQuestionModal(false)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              확인
            </button>
          </div>
        </div>
      </div>
    );
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
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 인사 면접관일 때
            isTTSActive && currentInterviewerType === 'hr'
              ? 'border-blue-500 shadow-lg shadow-blue-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'hr'
                ? 'text-blue-400' 
                : 'text-white'
            }`}>
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_1.jpg"
                alt="인사 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사'
                    ? 'bg-blue-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-blue-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>

          {/* 협업 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 협업 면접관일 때
            isTTSActive && currentInterviewerType === 'collaboration'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'collaboration'
                ? 'text-green-400' 
                : 'text-white'
            }`}>
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_2.jpg"
                alt="협업 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION'
                    ? 'bg-green-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-green-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>

          {/* 기술 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // TTS 재생 중이고 기술 면접관일 때
            isTTSActive && currentInterviewerType === 'tech'
              ? 'border-purple-500 shadow-lg shadow-purple-500/50 animate-pulse'
            // 기본 상태
            : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              isTTSActive && currentInterviewerType === 'tech'
                ? 'text-purple-400' 
                : 'text-white'
            }`}>
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_3.jpg"
                alt="기술 면접관"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 left-4">
                <div className={`w-4 h-4 rounded-full animate-pulse ${
                  currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH'
                    ? 'bg-purple-500' 
                    : 'bg-red-500'
                }`}></div>
              </div>
              {/* 질문 중 표시 */}
              {(currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH') && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-purple-400 font-semibold">
                  🎤 질문 중
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 하단 영역 */}
        <div className="grid gap-4 p-4" style={{ height: '60vh', gridTemplateColumns: '2fr 1fr 2fr' }}>
          {/* 사용자 영역 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // STT 활성화 시 (사용자가 말하는 중)
            isSTTActive
              ? 'border-red-500 shadow-lg shadow-red-500/50 animate-pulse'
            // 사용자 차례이지만 말하지 않는 중
            : currentPhase === 'user_turn'
              ? 'border-yellow-500 shadow-lg shadow-yellow-500/50'
            // 대기 상태
            : 'border-gray-600'
          }`}>
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

            {/* 답변 입력 오버레이 (사용자 턴일 때만) */}
            {currentPhase === 'user_turn' && (
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
                  <div className={`text-lg font-bold ${getTimerColor()}`}>
                    {formatTime(timeLeft)}
                  </div>
                </div>
              </div>
            )}
            
            {/* 대기 중 오버레이 */}
            {currentPhase === 'ai_turn' && (
              <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4 text-center">
                <div className="text-white opacity-75">대기 중...</div>
                <div className="text-xs text-gray-400 mt-1">AI 차례입니다</div>
              </div>
            )}
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
            {/* 현재 질문 표시 */}
            <div className="text-center mb-6">
              <div className="text-gray-400 text-sm mb-2">현재 질문</div>
              {currentQuestion ? (
                <>
                  <div className={`text-sm font-semibold mb-2 ${
                    currentQuestion.category === '자기소개' || currentQuestion.category === '지원동기' || currentQuestion.category === 'HR' || currentQuestion.category === '인사'
                      ? 'text-blue-400' 
                      : currentQuestion.category === '협업' || currentQuestion.category === 'COLLABORATION'
                      ? 'text-green-400'
                      : currentQuestion.category === '기술' || currentQuestion.category === 'TECH'
                      ? 'text-purple-400'
                      : 'text-gray-400'
                  }`}>
                    {currentQuestion.category === '자기소개' || currentQuestion.category === '지원동기' || currentQuestion.category === 'HR' || currentQuestion.category === '인사'
                      ? '👔 인사 면접관' 
                      : currentQuestion.category === '협업' || currentQuestion.category === 'COLLABORATION'
                      ? '🤝 협업 면접관'
                      : currentQuestion.category === '기술' || currentQuestion.category === 'TECH'
                      ? '💻 기술 면접관'
                      : '❓ 면접관'
                    }
                  </div>
                  <div className="text-white text-base leading-relaxed line-clamp-2 mb-3">
                    {currentQuestion.question && currentQuestion.question.length > 60 
                      ? `${currentQuestion.question.substring(0, 60)}...` 
                      : currentQuestion.question
                    }
                  </div>
                  <button
                    onClick={() => setShowQuestionModal(true)}
                    className="px-3 py-1 bg-white/20 hover:bg-white/30 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    📋 전체 질문 보기
                  </button>
                </>
              ) : (
                <div className="text-gray-500">질문을 불러오는 중...</div>
              )}
            </div>

            {/* 음성 컨트롤 */}
            <div className="mb-4">
              <VoiceControls
                onStartSTT={handleStartSTT}
                onStopSTT={handleStopSTT}
                onPlayTTS={handlePlayTTS}
                onStopTTS={handleStopTTS}
                isSTTActive={isSTTActive}
                isTTSActive={isTTSActive}
                disabled={currentPhase !== 'user_turn' && currentPhase !== 'interviewer_question'}
                className="justify-center"
              />
            </div>

            {/* 음성 상태 표시 */}
            {(isSTTActive || isTTSActive || interimText) && (
              <div className="mb-4">
                <SpeechIndicator
                  isListening={isSTTActive}
                  isSpeaking={isTTSActive}
                  interimText={interimText}
                />
              </div>
            )}

            {/* 컨트롤 버튼 */}
            <div className="space-y-3">
              {(() => {
                const hasAnswer = !!currentAnswer.trim();
                const hasSessionId = !!state.sessionId || !isRestoring; // 복원 중이 아니면 허용
                const isValidPhase = (currentPhase === 'user_turn' || currentPhase === 'interviewer_question');
                const isButtonDisabled = !hasAnswer || isLoading || !isValidPhase || isRestoring;
                
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
                      : currentPhase === 'user_turn' 
                      ? '🚀 답변 제출' 
                      : '대기 중...'
                    }
                  </button>
                );
              })()}
            </div>

            {/* 진행 상황 */}
            <div className="mt-4 text-center">
              <div className="text-white text-sm mb-2">
                진행상황: {timeline.filter(t => t.answer).length} / {timeline.length}
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-yellow-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${timeline.length > 0 ? (timeline.filter(t => t.answer).length / timeline.length) * 100 : 0}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* AI 지원자 춘식이 */}
          <div className={`bg-blue-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // AI 답변 TTS 재생 중일 때
            isTTSActive && ttsType === 'ai_answer'
              ? 'border-orange-500 shadow-lg shadow-orange-500/50 animate-pulse'
            // AI가 답변 생성 중일 때
            : currentPhase === 'ai_turn'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
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
              {currentPhase === 'ai_turn' ? (
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

        {/* 질문 모달 */}
        {renderQuestionModal()}
      </div>
    </div>
  );
};

export default InterviewGO;
