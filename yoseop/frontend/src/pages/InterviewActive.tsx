import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useInterview } from '../contexts/InterviewContext';
import { interviewApi, handleApiError } from '../services/api';

const InterviewActive: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  
  const [interviewState, setInterviewState] = useState<'ready' | 'active' | 'paused' | 'completed' | 'ai_answering' | 'comparison_mode'>('ready');
  const [comparisonMode, setComparisonMode] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_turn'>('user_turn');
  const [comparisonSessionId, setComparisonSessionId] = useState<string>('');
  const [hasInitialized, setHasInitialized] = useState(false);  // 중복 초기화 방지
  const [timeline, setTimeline] = useState<Array<{
    id: string;
    type: 'user' | 'ai';
    question: string;
    answer?: string;
    questionType?: string;
    isAnswering?: boolean;
  }>>([]);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [timeLeft, setTimeLeft] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const initializationRef = useRef<boolean>(false);  // 초기화 완료 여부

  // Initialize interview if not already set
  useEffect(() => {
    if (!state.sessionId || !state.settings) {
      navigate('/interview/setup');
      return;
    }
    
    console.log('🔍 면접 설정 확인:', state.settings);
    console.log('🔍 모드:', state.settings?.mode);
    console.log('🔍 comparisonMode:', comparisonMode);
    console.log('🔍 comparisonSessionId:', comparisonSessionId);
    
    // AI 경쟁 모드 확인 - useRef로 한 번만 실행
    if (state.settings?.mode === 'ai_competition' && !initializationRef.current) {
      console.log('✅ AI 경쟁 모드 시작');
      initializationRef.current = true;
      setHasInitialized(true);
      setComparisonMode(true);
      initializeComparisonMode();
    } else if (state.settings?.mode !== 'ai_competition' && !initializationRef.current) {
      console.log('✅ 일반 모드 시작');
      initializationRef.current = true;
      setHasInitialized(true);
      // 일반 모드 초기화
      if (state.questions.length === 0 && !isLoading) {
        loadFirstQuestion();
      } else if (state.questions.length > 0) {
        const currentQuestion = state.questions[state.currentQuestionIndex];
        if (currentQuestion) {
          setTimeLeft(currentQuestion.time_limit || 120);
        }
      }
    }
  }, [state.sessionId, state.settings]);

  // Timer management - 사용자 턴에서만 활성화
  useEffect(() => {
    if ((interviewState === 'active' || interviewState === 'comparison_mode') && currentPhase === 'user_turn') {
      console.log('⏱️ 타이머 시작 - 사용자 턴');
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
      console.log('⏸️ 타이머 정지 - AI 턴이거나 비활성 상태');
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [interviewState, currentPhase]);

  const handleTimeUp = () => {
    // AI 턴 중이거나 타이머가 제대로 설정되지 않은 경우 무시
    if (currentPhase === 'ai_turn' || timeLeft <= 0) {
      console.log('🚫 시간 만료 무시 - AI 턴이거나 타이머 미설정');
      return;
    }
    
    console.log('⏰ 시간 만료!');
    setInterviewState('paused');
    alert('시간이 만료되었습니다!');
  };

  const initializeComparisonMode = async () => {
    if (!state.settings) return;
    
    // 이미 초기화 중이거나 완료된 경우 중단
    if (isLoading || comparisonSessionId) {
      console.log('🚫 이미 초기화 중이거나 완료됨, 중단');
      return;
    }
    
    try {
      setIsLoading(true);
      console.log('🔄 비교 면접 모드 초기화 시작');
      
      // AI 경쟁 면접 시작 - web/app.py 방식
      const response = await interviewApi.startAICompetition(state.settings);
      
      console.log('✅ 비교 면접 응답:', response);
      
      // 상태 업데이트
      setComparisonSessionId(response.comparison_session_id);
      setCurrentPhase(response.current_phase as 'user_turn' | 'ai_turn');
      
      // 세션 ID 업데이트
      dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
      
      console.log(`👥 면접 시작: ${response.current_respondent}가 먼저 시작`);
      
      if (response.current_phase === 'user_turn') {
        // 사용자부터 시작하는 경우
        console.log('📝 사용자 질문 데이터:', response.question);
        console.log('📝 전체 응답 데이터:', response);
        
        if (!response.question) {
          console.error('❌ 질문 데이터가 없습니다!');
          alert('질문을 불러오는데 실패했습니다. 다시 시도해주세요.');
          return;
        }
        
        const questionData = response.question as any;
        const newTurn = {
          id: `user_${Date.now()}`,
          type: 'user' as const,
          question: questionData.question_content || questionData.question || '질문을 불러올 수 없습니다',
          questionType: questionData.question_type || questionData.category || '일반'
        };
        
        // 서버 응답을 프론트엔드 형식으로 변환
        const normalizedQuestion = {
          id: questionData.question_id || `q_${Date.now()}`,
          question: questionData.question_content || questionData.question || '질문을 불러올 수 없습니다',
          category: questionData.question_type || questionData.category || '일반',
          time_limit: questionData.time_limit || 120,
          keywords: questionData.keywords || []
        };
        
        setTimeline([newTurn]);
        dispatch({ type: 'ADD_QUESTION', payload: normalizedQuestion });
        setTimeLeft(response.question.time_limit || 120);
        setInterviewState('comparison_mode');  // 비교 면접 모드로 설정
      } else if (response.current_phase === 'ai_turn') {
        // AI부터 시작하는 경우
        console.log('🤖 AI가 먼저 시작하는 경우');
        setCurrentPhase('ai_turn');
        setTimeLeft(120); // AI 턴에서도 기본 타이머 시간 설정 (타이머는 활성화하지 않음)
        setInterviewState('comparison_mode');
        // comparisonSessionId가 설정된 후에 processAITurn 호출
        setTimeout(async () => {
          console.log('🔄 AI 턴 처리 시작 예약, sessionId:', response.comparison_session_id);
          await processAITurnWithSessionId(response.comparison_session_id);
        }, 100);
      }
      
    } catch (error) {
      console.error('비교 면접 초기화 실패:', error);
      alert(`비교 면접 시작 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const processAITurnWithSessionId = async (sessionId: string) => {
    // 중복 처리 방지
    if (isProcessingAI) {
      console.log('🚫 AI 턴 이미 처리 중, 스킵');
      return;
    }
    
    // 현재 페이즈 확인 (디버깅)
    console.log('🔍 현재 페이즈:', currentPhase, '세션ID:', sessionId);
    
    try {
      setIsProcessingAI(true);
      console.log('🤖 AI 턴 처리 시작, sessionId:', sessionId);
      
      // 1단계: AI 질문 생성
      const questionResponse = await interviewApi.processComparisonAITurn(sessionId, 'question');
      
      if (questionResponse.ai_question) {
        // 타임라인에 AI 턴 추가 (답변 대기 상태)
        const newTurn = {
          id: `ai_${Date.now()}`,
          type: 'ai' as const,
          question: questionResponse.ai_question.question_content,
          questionType: questionResponse.ai_question.question_type || '일반',
          isAnswering: true
        };
        
        setTimeline(prev => [...prev, newTurn]);
        
        // 2-3초 후 AI 답변 생성
        setTimeout(async () => {
          try {
            // 2단계: AI 답변 생성
            const answerResponse = await interviewApi.processComparisonAITurn(sessionId, 'answer');
            
            // AI 답변을 타임라인에 업데이트
            setTimeline(prev => prev.map(turn => 
              turn.id === newTurn.id 
                ? { ...turn, answer: answerResponse.ai_answer?.content || 'AI 답변을 가져올 수 없습니다.', isAnswering: false }
                : turn
            ));
            
            console.log('✅ AI 답변 완료');
            
            // 면접 완료 확인
            if (answerResponse.interview_status === 'completed') {
              setInterviewState('completed');
              return;
            }
            
            // 다음 사용자 턴으로 전환 - 사용자 답변 제출 시 저장된 질문 사용
            const pendingQuestion = (window as any).pendingUserQuestion || answerResponse.next_user_question;
            if (pendingQuestion) {
              console.log('📝 다음 사용자 질문 데이터:', pendingQuestion);
              setTimeout(() => {
                setCurrentPhase('user_turn');
                
                // 다음 사용자 질문을 타임라인에 추가
                const nextQuestionData = pendingQuestion as any;
                const nextUserTurn = {
                  id: `user_${Date.now()}`,
                  type: 'user' as const,
                  question: nextQuestionData.question_content || nextQuestionData.question || '질문을 불러올 수 없습니다',
                  questionType: nextQuestionData.question_type || nextQuestionData.category || '일반'
                };
                
                // 서버 응답을 프론트엔드 형식으로 변환
                const normalizedNextQuestion = {
                  id: nextQuestionData.question_id || `q_${Date.now()}`,
                  question: nextQuestionData.question_content || nextQuestionData.question || '질문을 불러올 수 없습니다',
                  category: nextQuestionData.question_type || nextQuestionData.category || '일반',
                  time_limit: nextQuestionData.time_limit || 120,
                  keywords: nextQuestionData.keywords || []
                };
                
                setTimeline(prev => [...prev, nextUserTurn]);
                dispatch({ type: 'ADD_QUESTION', payload: normalizedNextQuestion });
                setTimeLeft(pendingQuestion.time_limit || 120);
                setInterviewState('active');  // 타이머 시작을 위해 active로 설정
                
                // 사용된 질문 삭제
                delete (window as any).pendingUserQuestion;
              }, 2000);
            }
            
          } catch (error) {
            console.error('AI 답변 생성 실패:', error);
            setTimeline(prev => prev.map(turn => 
              turn.id === newTurn.id 
                ? { ...turn, answer: 'AI 답변 생성에 실패했습니다.', isAnswering: false }
                : turn
            ));
          } finally {
            setIsProcessingAI(false);
          }
        }, 2500);
      }
      
    } catch (error) {
      console.error('AI 턴 처리 실패:', error);
      setIsProcessingAI(false);
    }
  };

  const processAITurn = async () => {
    if (!comparisonSessionId) {
      console.error('❌ comparisonSessionId가 없습니다:', comparisonSessionId);
      return;
    }
    
    await processAITurnWithSessionId(comparisonSessionId);
  };

  const loadFirstQuestion = async () => {
    if (!state.sessionId) return;
    if (isLoading) return;
    
    if (state.questions.length > 0) {
      console.log('🚫 이미 질문이 로드됨, 중복 방지');
      return;
    }
    
    try {
      setIsLoading(true);
      console.log('📝 첫 번째 질문 로드 시작');
      const response = await interviewApi.getNextQuestion(state.sessionId);
      
      if (response.question) {
        dispatch({ type: 'ADD_QUESTION', payload: response.question });
        setTimeLeft(response.question.time_limit || 120);
        console.log('✅ 첫 번째 질문 로드 완료:', response.question.category);
      } else if (response.completed) {
        setInterviewState('completed');
      }
    } catch (error) {
      console.error('질문 로드 실패:', error);
      alert(`질문 로드 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const startInterview = () => {
    setInterviewState('active');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
    
    setTimeout(() => {
      answerRef.current?.focus();
    }, 100);
  };

  const pauseInterview = () => {
    setInterviewState('paused');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'paused' });
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const resumeInterview = () => {
    setInterviewState('active');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'active' });
    answerRef.current?.focus();
  };

  const submitAnswer = async () => {
    if (!state.sessionId) return;
    
    if (comparisonMode) {
      await submitComparisonAnswer();
    } else {
      await submitNormalAnswer();
    }
  };

  const submitComparisonAnswer = async () => {
    if (!comparisonSessionId) return;
    
    try {
      setIsLoading(true);
      
      // 현재 사용자 턴의 타임라인 업데이트
      const currentTurnIndex = timeline.findIndex(turn => 
        turn.type === 'user' && !turn.answer
      );
      
      if (currentTurnIndex !== -1) {
        setTimeline(prev => prev.map((turn, index) => 
          index === currentTurnIndex 
            ? { ...turn, answer: currentAnswer }
            : turn
        ));
        
        // 비교 면접 사용자 턴 제출
        const response = await interviewApi.submitComparisonUserTurn(comparisonSessionId, currentAnswer);
        
        console.log('✅ 사용자 답변 제출 완료:', response);
        console.log('🔍 다음 사용자 질문 데이터:', response.next_user_question);
        
        // 다음 사용자 질문이 있으면 미리 저장 (AI 턴 후 사용)
        if (response.next_user_question) {
          (window as any).pendingUserQuestion = response.next_user_question;
          console.log('📝 다음 사용자 질문 저장됨');
        }
        
        setCurrentAnswer('');
        
        // AI 턴으로 전환
        setTimeout(() => {
          setCurrentPhase('ai_turn');
          processAITurn();
        }, 1500);
      }
      
    } catch (error) {
      console.error('답변 제출 실패:', error);
      alert(`답변 제출 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const submitNormalAnswer = async () => {
    if (!state.sessionId) return;
    
    const currentQuestion = state.questions[state.currentQuestionIndex];
    if (!currentQuestion) return;

    try {
      setIsLoading(true);
      
      const answerData = {
        session_id: state.sessionId,
        question_id: currentQuestion.id,
        answer: currentAnswer,
        time_spent: (currentQuestion.time_limit || 120) - timeLeft
      };

      const response = await interviewApi.submitAnswer(answerData);
      dispatch({ type: 'ADD_ANSWER', payload: answerData });
      setCurrentAnswer('');
      
      // AI 경쟁 모드인 경우 AI 답변 생성
      if (state.settings?.mode === 'ai_competition' && state.sessionId) {
        try {
          const aiResponse = await interviewApi.getAIAnswer(state.sessionId, currentQuestion.id);
          
          dispatch({ 
            type: 'ADD_AI_ANSWER', 
            payload: {
              question_id: currentQuestion.id,
              answer: aiResponse.answer,
              score: aiResponse.score,
              persona_name: aiResponse.persona_name,
              time_spent: aiResponse.time_spent
            }
          });
          
          setInterviewState('ai_answering');
          
          setTimeout(() => {
            proceedToNextQuestion();
          }, 3000);
        } catch (aiError) {
          console.error('AI 답변 생성 실패:', aiError);
          proceedToNextQuestion();
        }
      } else {
        proceedToNextQuestion();
      }
      
    } catch (error) {
      console.error('답변 제출 실패:', error);
      alert(`답변 제출 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const proceedToNextQuestion = async () => {
    if (!state.sessionId) return;
    
    try {
      const nextResponse = await interviewApi.getNextQuestion(state.sessionId);
      
      if (nextResponse.question) {
        dispatch({ type: 'ADD_QUESTION', payload: nextResponse.question });
        dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: state.currentQuestionIndex + 1 });
        setTimeLeft(nextResponse.question.time_limit || 120);
        setInterviewState('active');
        
        setTimeout(() => {
          answerRef.current?.focus();
        }, 100);
      } else if (nextResponse.completed) {
        completeInterview();
      }
    } catch (error) {
      console.error('다음 질문 로드 실패:', error);
      alert(`다음 질문 로드 실패: ${handleApiError(error)}`);
    }
  };

  const completeInterview = () => {
    setInterviewState('completed');
    dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'completed' });
    
    setTimeout(() => {
      navigate('/interview/results');
    }, 3000);
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  };

  const progress = state.questions.length > 0 
    ? ((state.currentQuestionIndex + 1) / state.questions.length) * 100 
    : 0;

  // 비교 면접 모드에서는 타임라인의 마지막 미완료 질문 사용
  const currentQuestion = comparisonMode && timeline.length > 0
    ? (() => {
        // 타임라인에서 마지막 사용자 턴의 미완료 질문 찾기
        const lastUserTurn = [...timeline].reverse().find(turn => 
          turn.type === 'user' && (!turn.answer || turn.answer === '')
        );
        if (lastUserTurn) {
          return {
            id: `timeline_${lastUserTurn.id}`,
            question: lastUserTurn.question,
            category: lastUserTurn.questionType,
            time_limit: 120,
            keywords: []
          };
        }
        return null;
      })()
    : state.questions[state.currentQuestionIndex];

  // Ready State
  if (interviewState === 'ready') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="mb-8">
              <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 준비 완료</h1>
              <p className="text-lg text-gray-600">
                {comparisonMode ? '춘식이와의 경쟁 면접' : '일반 면접'}이 곧 시작됩니다.
              </p>
            </div>

            <div className="mb-8 p-6 bg-gray-50 rounded-xl">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">면접 정보</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">회사:</span>
                  <span className="ml-2 font-medium">{state.settings?.company}</span>
                </div>
                <div>
                  <span className="text-gray-500">직군:</span>
                  <span className="ml-2 font-medium">{state.settings?.position}</span>
                </div>
                <div>
                  <span className="text-gray-500">모드:</span>
                  <span className="ml-2 font-medium">
                    {comparisonMode ? 'AI 경쟁 면접' : '일반 면접'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">난이도:</span>
                  <span className="ml-2 font-medium">{state.settings?.difficulty}</span>
                </div>
              </div>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
                <span className="ml-3 text-gray-600">면접 준비 중...</span>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600 mb-6">
                  준비가 되었으면 아래 버튼을 클릭해 면접을 시작하세요.
                </p>
                <button
                  onClick={startInterview}
                  className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                  면접 시작
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Paused State
  if (interviewState === 'paused') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 일시정지</h1>
            <p className="text-lg text-gray-600 mb-8">
              면접이 일시정지되었습니다. 준비가 되면 계속 진행하세요.
            </p>
            <button
              onClick={resumeInterview}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              면접 재개
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Completed State
  if (interviewState === 'completed') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">면접 완료!</h1>
            <p className="text-lg text-gray-600 mb-8">
              수고하셨습니다. 곧 결과 페이지로 이동합니다.
            </p>
            <div className="flex items-center justify-center">
              <LoadingSpinner />
              <span className="ml-3 text-gray-600">결과 분석 중...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Comparison Mode State - 화상회의 스타일
  console.log('🔍 Debug:', { interviewState, comparisonMode, hasInitialized });
  
  if (comparisonMode && hasInitialized) {
    return (
      <div className="min-h-screen bg-black">
        {/* 상단 면접관 3명 */}
        <div className="grid grid-cols-3 gap-4 p-4" style={{ height: '60vh' }}>
          {/* 인사 면접관 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사'
              ? 'border-blue-500 shadow-lg shadow-blue-500/50' 
              : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              currentQuestion?.category === '자기소개' || currentQuestion?.category === '지원동기' || currentQuestion?.category === 'HR' || currentQuestion?.category === '인사'
                ? 'text-blue-400' 
                : 'text-white'
            }`}>
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg opacity-50">Video Player</div>
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
            currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION'
              ? 'border-green-500 shadow-lg shadow-green-500/50' 
              : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              currentQuestion?.category === '협업' || currentQuestion?.category === 'COLLABORATION'
                ? 'text-green-400' 
                : 'text-white'
            }`}>
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg opacity-50">Video Player</div>
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
            currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH'
              ? 'border-purple-500 shadow-lg shadow-purple-500/50' 
              : 'border-gray-700'
          }`}>
            <div className={`absolute top-4 left-4 font-semibold ${
              currentQuestion?.category === '기술' || currentQuestion?.category === 'TECH'
                ? 'text-purple-400' 
                : 'text-white'
            }`}>
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg opacity-50">Video Player</div>
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
        <div className="grid grid-cols-4 gap-4 p-4" style={{ height: '40vh' }}>
          {/* 사용자 영역 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-yellow-500">
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold">
              사용자 답변: {state.settings?.candidate_name || 'You'}
            </div>
            <div className="h-full flex flex-col justify-center p-6">
              {currentPhase === 'user_turn' ? (
                <>
                  <div className="text-white text-sm mb-4 opacity-75">
                    {currentQuestion?.question || '질문을 불러오는 중...'}
                  </div>
                  <textarea
                    ref={answerRef}
                    value={currentAnswer}
                    onChange={(e) => setCurrentAnswer(e.target.value)}
                    className="w-full h-24 p-3 bg-gray-800 text-white border border-gray-600 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none text-sm"
                    placeholder="답변을 입력하세요..."
                  />
                  <div className="flex items-center justify-between mt-3">
                    <div className="text-gray-400 text-xs">{currentAnswer.length}자</div>
                    <div className={`text-xl font-bold ${getTimerColor()}`}>
                      {formatTime(timeLeft)}
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center text-white opacity-50">
                  <div>대기 중...</div>
                  <div className="text-xs text-gray-400 mt-2">AI 차례입니다</div>
                </div>
              )}
            </div>
          </div>

          {/* 중앙 컨트롤 */}
          <div className="col-span-2 bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
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
                  <div className="text-white text-lg leading-relaxed">
                    {currentQuestion.question}
                  </div>
                </>
              ) : (
                <div className="text-gray-500">질문을 불러오는 중...</div>
              )}
            </div>

            {/* 컨트롤 버튼 */}
            <div className="space-y-3">
              <button 
                className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-colors font-semibold"
                onClick={submitAnswer}
                disabled={!currentAnswer.trim() || isLoading || currentPhase !== 'user_turn'}
              >
                {isLoading ? '제출 중...' : currentPhase === 'user_turn' ? '🚀 답변 제출' : '대기 중...'}
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button 
                  className="py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors text-sm"
                  onClick={pauseInterview}
                >
                  면접 종료
                </button>
                <button 
                  className="py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors text-sm"
                  onClick={() => {
                    const panel = document.getElementById('history-panel');
                    if (panel) {
                      panel.classList.toggle('hidden');
                    }
                  }}
                >
                  히스토리
                </button>
              </div>
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
          <div className="bg-blue-900 rounded-lg overflow-hidden relative border-2 border-green-500">
            <div className="absolute top-4 left-4 text-green-400 font-semibold">
              AI 지원자 춘식이
            </div>
            <div className="h-full flex flex-col justify-center items-center p-4">
              {/* 춘식이 아바타 */}
              <div className="w-24 h-24 bg-yellow-400 rounded-full mb-4 flex items-center justify-center border-4 border-green-400">
                <span className="text-3xl">🧑‍💼</span>
              </div>
              
              {currentPhase === 'ai_turn' ? (
                <div className="text-center">
                  <div className="text-green-400 text-sm font-semibold mb-2">답변 중...</div>
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  {isProcessingAI && (
                    <div className="text-xs text-green-300 mt-2">분석 중</div>
                  )}
                </div>
              ) : (
                <div className="text-center">
                  <div className="text-blue-300 text-sm">대기 중</div>
                  <div className="text-xs text-blue-400 mt-1">사용자 차례</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 히스토리 패널 (숨겨져 있다가 토글 가능) */}
        {timeline.length > 0 && (
          <div className="absolute bottom-4 right-4">
            <button 
              className="bg-gray-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-700 transition-colors"
              onClick={() => {
                const panel = document.getElementById('history-panel');
                if (panel) {
                  panel.classList.toggle('hidden');
                }
              }}
            >
              📋 히스토리 ({timeline.length})
            </button>
            
            <div id="history-panel" className="hidden absolute bottom-12 right-0 w-80 bg-white rounded-lg shadow-xl p-4 max-h-64 overflow-y-auto">
              <h3 className="font-semibold text-gray-900 mb-3">면접 히스토리</h3>
              <div className="space-y-2">
                {timeline.map((turn, index) => (
                  <div key={turn.id} className={`p-2 rounded text-xs ${
                    turn.type === 'user' 
                      ? 'bg-yellow-50 border-l-4 border-yellow-400' 
                      : 'bg-green-50 border-l-4 border-green-400'
                  }`}>
                    <div className="font-medium">
                      {turn.type === 'user' ? '👤 사용자' : '🤖 춘식이'} - {turn.questionType}
                    </div>
                    <div className="text-gray-600 mt-1">
                      ❓ {turn.question.substring(0, 50)}...
                    </div>
                    {turn.answer && (
                      <div className="text-gray-700 mt-1">
                        💬 {turn.answer.substring(0, 50)}...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Loading state for normal mode
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <LoadingSpinner />
            <p className="mt-4 text-gray-600">질문을 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  // Active Interview State
  if (!currentQuestion && !comparisonMode) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title={`${state.settings?.company || '쿠팡'} 면접`}
          subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
        />
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <p className="text-gray-600">질문을 불러올 수 없습니다.</p>
            <button
              onClick={() => navigate('/interview/setup')}
              className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              설정으로 돌아가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title={`${state.settings?.company || '쿠팡'} 면접`}
        subtitle={`${state.settings?.position || '개발자'} ${comparisonMode ? '- 춘식이와의 실시간 경쟁' : ''}`}
      />
      
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between items-center text-sm text-gray-600 mb-2">
            <span>질문 {state.currentQuestionIndex + 1} / {state.questions.length}</span>
            <span>{Math.round(progress)}% 완료</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* 비교 면접 모드일 때 타임라인 표시 */}
        {comparisonMode && timeline.length > 0 && (
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">📋 면접 진행 히스토리</h3>
            <div className="max-h-96 overflow-y-auto space-y-4">
              {timeline.map((turn, index) => (
                <div 
                  key={turn.id} 
                  className={`p-4 rounded-lg border-l-4 ${
                    turn.type === 'user' 
                      ? 'bg-blue-50 border-blue-400' 
                      : 'bg-green-50 border-green-400'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">
                      {turn.type === 'user' 
                        ? `👤 ${state.settings?.candidate_name || '사용자'}` 
                        : '🤖 춘식이'
                      } - {turn.questionType}
                    </span>
                    <span className="text-xs text-gray-500">#{index + 1}</span>
                  </div>
                  <div className="mb-2 text-sm font-medium text-gray-700">
                    ❓ {turn.question}
                  </div>
                  {turn.answer ? (
                    <div className="text-sm text-gray-600">
                      💬 {turn.answer}
                    </div>
                  ) : turn.isAnswering ? (
                    <div className="text-sm text-gray-500 italic">
                      ⏳ 답변 생성 중...
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400">
                      ⏸️ 답변 대기중
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Question Section */}
          <div className="p-8 border-b border-gray-200">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${
                  comparisonMode 
                    ? (currentPhase === 'user_turn' ? 'bg-blue-100' : 'bg-green-100')
                    : 'bg-blue-100'
                }`}>
                  <span className={`font-bold ${
                    comparisonMode 
                      ? (currentPhase === 'user_turn' ? 'text-blue-600' : 'text-green-600')
                      : 'text-blue-600'
                  }`}>
                    {comparisonMode 
                      ? (currentPhase === 'user_turn' ? '👤' : '🤖')
                      : `Q${state.currentQuestionIndex + 1}`
                    }
                  </span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {comparisonMode 
                      ? (currentPhase === 'user_turn' 
                          ? `${state.settings?.candidate_name || '사용자'}님의 차례` 
                          : '춘식이의 차례'
                        )
                      : `${currentQuestion?.category || '일반'} 질문`
                    }
                  </h2>
                  <p className="text-gray-600">
                    {comparisonMode 
                      ? `${currentQuestion?.category || '일반'} 질문 - ${currentPhase === 'user_turn' ? '신중하게 답변해주세요' : 'AI가 답변 중입니다'}`
                      : '신중하게 답변해주세요'
                    }
                  </p>
                </div>
              </div>
              <div className={`text-3xl font-bold ${getTimerColor()}`}>
                {comparisonMode && currentPhase === 'ai_turn' ? '⏳' : formatTime(timeLeft)}
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-xl p-6">
              <p className="text-lg text-gray-900 leading-relaxed">
                {currentQuestion?.question}
              </p>
            </div>
          </div>

          {/* Answer Section */}
          <div className="p-8">
            {comparisonMode && currentPhase === 'ai_turn' ? (
              /* AI 답변 중 표시 */
              <div className="text-center py-8">
                <div className="animate-pulse">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">🤖</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">춘식이가 답변 중입니다</h3>
                  <p className="text-gray-600">잠시만 기다려주세요...</p>
                  {isProcessingAI && (
                    <div className="mt-4">
                      <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* 사용자 답변 입력 */
              <div className="mb-6">
                <label htmlFor="answer" className="block text-sm font-medium text-gray-700 mb-2">
                  {comparisonMode 
                    ? `${state.settings?.candidate_name || '사용자'}님의 답변을 입력해주세요 (최소 50자 이상 권장)`
                    : '답변을 입력해주세요 (최소 50자 이상 권장)'
                  }
                </label>
                <textarea
                  ref={answerRef}
                  id="answer"
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  disabled={comparisonMode && currentPhase !== 'user_turn'}
                  className={`w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
                    comparisonMode && currentPhase !== 'user_turn' ? 'bg-gray-100 cursor-not-allowed' : ''
                  }`}
                  placeholder={comparisonMode 
                    ? "춘식이와 경쟁하세요! 구체적이고 명확한 답변을 작성해주세요..."
                    : "구체적이고 명확한 답변을 작성해주세요..."
                  }
                />
                <div className="mt-2 text-sm text-gray-500">
                  {currentAnswer.length}자 입력됨
                </div>
              </div>
            )}

            {comparisonMode && currentPhase === 'ai_turn' ? (
              /* AI 턴일 때는 버튼 없음 */
              null
            ) : (
              /* 사용자 턴일 때 답변 제출 버튼 */
              <div className="flex justify-between">
                <button
                  onClick={pauseInterview}
                  className="px-6 py-3 text-gray-600 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                  disabled={comparisonMode && currentPhase !== 'user_turn'}
                >
                  일시정지
                </button>
                
                <button
                  onClick={submitAnswer}
                  disabled={!currentAnswer.trim() || isLoading || (comparisonMode && currentPhase !== 'user_turn')}
                  className={`px-8 py-3 text-white rounded-lg font-medium transition-colors ${
                    comparisonMode 
                      ? 'bg-green-600 hover:bg-green-700' 
                      : 'bg-blue-600 hover:bg-blue-700'
                  } disabled:bg-gray-400 disabled:cursor-not-allowed`}
                >
                  {isLoading 
                    ? '제출 중...' 
                    : comparisonMode 
                      ? '🏃‍♂️ 춘식이와 경쟁!'
                      : '답변 제출'
                  }
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewActive;