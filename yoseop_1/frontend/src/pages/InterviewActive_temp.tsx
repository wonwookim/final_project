import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../contexts/InterviewContext';

const InterviewActiveTemp: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_turn'>('user_turn');
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [timeLeft, setTimeLeft] = useState(120);
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [currentQuestion] = useState({
    question: "자기소개를 간단히 해주세요. 본인의 강점과 이 회사에 지원한 이유를 포함해서 말씀해주세요.",
    category: "인사"
  });

  const answerRef = useRef<HTMLTextAreaElement>(null);

  // Initialize check
  useEffect(() => {
    if (!state.sessionId || !state.settings) {
      navigate('/interview/setup');
      return;
    }
  }, [state.sessionId, state.settings, navigate]);

  // Mock timer for demo
  useEffect(() => {
    if (currentPhase === 'user_turn' && timeLeft > 0) {
      const timer = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [currentPhase, timeLeft]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-400';
    if (timeLeft > 30) return 'text-yellow-400';
    return 'text-red-400';
  };

  // AI 답변 템플릿
  const getAIAnswer = (category: string): string => {
    const aiAnswers: Record<string, string> = {
      "인사": "안녕하세요. 저는 지속적으로 학습하고 성장하는 개발자입니다. 제가 가진 가장 큰 강점은 문제 해결 능력과 팀워크입니다. 이전 프로젝트에서 복잡한 버그를 해결하며 팀의 개발 효율성을 30% 향상시킨 경험이 있습니다. 이 회사를 선택한 이유는 혁신적인 기술로 사용자 경험을 개선하는 비전에 공감했기 때문입니다.",
      "기술": "프론트엔드 개발에서 가장 중요한 기술은 React와 TypeScript라고 생각합니다. React는 컴포넌트 기반 아키텍처로 재사용성과 유지보수성을 높여주고, TypeScript는 타입 안정성을 제공하여 런타임 오류를 사전에 방지할 수 있습니다. 또한 Next.js를 활용한 SSR/SSG 경험과 상태 관리 라이브러리 활용 능력도 중요하다고 봅니다.",
      "협업": "효과적인 협업을 위해 코드 리뷰 문화 정착에 노력했습니다. 이전 프로젝트에서 팀원들과 매일 15분 스탠드업 미팅을 진행하고, PR 리뷰를 통해 코드 품질을 향상시켰습니다. 또한 Slack과 Notion을 활용해 비동기 커뮤니케이션을 원활하게 했고, 결과적으로 프로젝트 일정을 2주 단축시킬 수 있었습니다."
    };
    return aiAnswers[category] || "질문에 대해 체계적으로 접근하여 답변드리겠습니다. 제 경험과 지식을 바탕으로 구체적인 사례를 들어 설명할 수 있습니다.";
  };

  const handleAnswerSubmit = () => {
    console.log('답변 제출:', currentAnswer);
    
    // 1. 사용자 답변 저장
    const userAnswer = {
      question_id: "q1",
      answer: currentAnswer,
      time_spent: 120 - timeLeft,
      score: Math.floor(Math.random() * 20) + 75 // 75-95점 랜덤
    };
    dispatch({ type: 'ADD_ANSWER', payload: userAnswer });
    
    // 2. 현재 질문을 questions 배열에 추가
    const questionData = {
      id: "q1",
      question: currentQuestion.question,
      category: currentQuestion.category,
      type: "text",
      level: 1,
      time_limit: 120,
      keywords: ["자기소개", "강점", "지원동기"]
    };
    dispatch({ type: 'ADD_QUESTION', payload: questionData });
    
    setCurrentAnswer('');
    setCurrentPhase('ai_turn');
    setIsProcessingAI(true);
    
    // 3. AI 답변 생성 및 저장
    setTimeout(() => {
      const aiAnswer = {
        question_id: "q1",
        answer: getAIAnswer(currentQuestion.category),
        score: Math.floor(Math.random() * 20) + 70, // 70-90점 랜덤
        persona_name: "춘식이",
        time_spent: Math.floor(Math.random() * 60) + 30 // 30-90초 랜덤
      };
      dispatch({ type: 'ADD_AI_ANSWER', payload: aiAnswer });
      
      // 4. 면접 완료 상태로 변경
      dispatch({ type: 'SET_INTERVIEW_STATUS', payload: 'completed' });
      
      setIsProcessingAI(false);
      
      // 5. 결과 페이지로 이동 (temp 모드 표시)
      setTimeout(() => {
        navigate('/interview/results', { 
          state: { 
            tempMode: true,
            skipApiCall: true 
          }
        });
      }, 1500);
      
    }, 3000);
  };

  if (!state.settings) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
        <div className="text-white text-center">
          <p className="text-xl mb-4">면접 설정이 없습니다.</p>
          <button
            onClick={() => navigate('/interview/setup')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            설정으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-black overflow-hidden">
      {/* 상단 면접관 영역 - 60% */}
      <div className="grid grid-cols-3 gap-6 p-6" style={{ height: '60vh' }}>
        {/* 인사 면접관 */}
        <div className={`bg-gradient-to-b from-gray-800 to-gray-900 rounded-2xl overflow-hidden relative border-2 transition-all duration-500 ${
          currentQuestion.category === '인사' || currentQuestion.category === 'HR'
            ? 'border-blue-400 shadow-2xl shadow-blue-500/30 scale-105' 
            : 'border-gray-600 hover:border-gray-500'
        }`}>
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-500"></div>
          <div className={`absolute top-6 left-6 font-bold text-lg ${
            currentQuestion.category === '인사' || currentQuestion.category === 'HR'
              ? 'text-blue-300' 
              : 'text-gray-300'
          }`}>
            👔 인사 면접관
          </div>
          
          <div className="h-full flex items-center justify-center relative">
            <div className="text-center">
              <div className={`w-32 h-32 rounded-full mx-auto mb-4 flex items-center justify-center ${
                currentQuestion.category === '인사' || currentQuestion.category === 'HR'
                  ? 'bg-blue-500/20 border-4 border-blue-400' 
                  : 'bg-gray-700/50 border-4 border-gray-600'
              }`}>
                <span className="text-5xl">👩‍💼</span>
              </div>
              {currentQuestion.category === '인사' || currentQuestion.category === 'HR' ? (
                <div className="text-blue-300 font-semibold text-lg animate-pulse">
                  🎤 질문 중
                </div>
              ) : (
                <div className="text-gray-500 text-sm">대기 중</div>
              )}
            </div>
            
            <div className="absolute bottom-6 left-6">
              <div className={`w-4 h-4 rounded-full animate-pulse ${
                currentQuestion.category === '인사' || currentQuestion.category === 'HR'
                  ? 'bg-blue-400' 
                  : 'bg-gray-600'
              }`}></div>
            </div>
          </div>
        </div>

        {/* 협업 면접관 */}
        <div className={`bg-gradient-to-b from-gray-800 to-gray-900 rounded-2xl overflow-hidden relative border-2 transition-all duration-500 ${
          currentQuestion.category === '협업'
            ? 'border-green-400 shadow-2xl shadow-green-500/30 scale-105' 
            : 'border-gray-600 hover:border-gray-500'
        }`}>
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-green-500 to-emerald-500"></div>
          <div className={`absolute top-6 left-6 font-bold text-lg ${
            currentQuestion.category === '협업'
              ? 'text-green-300' 
              : 'text-gray-300'
          }`}>
            🤝 협업 면접관
          </div>
          
          <div className="h-full flex items-center justify-center relative">
            <div className="text-center">
              <div className={`w-32 h-32 rounded-full mx-auto mb-4 flex items-center justify-center ${
                currentQuestion.category === '협업'
                  ? 'bg-green-500/20 border-4 border-green-400' 
                  : 'bg-gray-700/50 border-4 border-gray-600'
              }`}>
                <span className="text-5xl">👨‍💼</span>
              </div>
              {currentQuestion.category === '협업' ? (
                <div className="text-green-300 font-semibold text-lg animate-pulse">
                  🎤 질문 중
                </div>
              ) : (
                <div className="text-gray-500 text-sm">대기 중</div>
              )}
            </div>
            
            <div className="absolute bottom-6 left-6">
              <div className={`w-4 h-4 rounded-full animate-pulse ${
                currentQuestion.category === '협업'
                  ? 'bg-green-400' 
                  : 'bg-gray-600'
              }`}></div>
            </div>
          </div>
        </div>

        {/* 기술 면접관 */}
        <div className={`bg-gradient-to-b from-gray-800 to-gray-900 rounded-2xl overflow-hidden relative border-2 transition-all duration-500 ${
          currentQuestion.category === '기술'
            ? 'border-purple-400 shadow-2xl shadow-purple-500/30 scale-105' 
            : 'border-gray-600 hover:border-gray-500'
        }`}>
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
          <div className={`absolute top-6 left-6 font-bold text-lg ${
            currentQuestion.category === '기술'
              ? 'text-purple-300' 
              : 'text-gray-300'
          }`}>
            💻 기술 면접관
          </div>
          
          <div className="h-full flex items-center justify-center relative">
            <div className="text-center">
              <div className={`w-32 h-32 rounded-full mx-auto mb-4 flex items-center justify-center ${
                currentQuestion.category === '기술'
                  ? 'bg-purple-500/20 border-4 border-purple-400' 
                  : 'bg-gray-700/50 border-4 border-gray-600'
              }`}>
                <span className="text-5xl">👨‍💻</span>
              </div>
              {currentQuestion.category === '기술' ? (
                <div className="text-purple-300 font-semibold text-lg animate-pulse">
                  🎤 질문 중
                </div>
              ) : (
                <div className="text-gray-500 text-sm">대기 중</div>
              )}
            </div>
            
            <div className="absolute bottom-6 left-6">
              <div className={`w-4 h-4 rounded-full animate-pulse ${
                currentQuestion.category === '기술'
                  ? 'bg-purple-400' 
                  : 'bg-gray-600'
              }`}></div>
            </div>
          </div>
        </div>
      </div>

      {/* 하단 참여자 영역 - 40% */}
      <div className="grid grid-cols-5 gap-6 p-6" style={{ height: '40vh' }}>
        {/* 사용자 영역 - 3칸 (60%) */}
        <div className="col-span-3 bg-gradient-to-b from-slate-800 to-slate-900 rounded-2xl overflow-hidden relative border-2 border-yellow-400 shadow-2xl shadow-yellow-500/20">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-yellow-400 to-orange-500"></div>
          <div className="absolute top-6 left-6 text-yellow-300 font-bold text-xl">
            👤 {state.settings.candidate_name || '지원자'} (나)
          </div>
          
          <div className="h-full flex flex-col justify-center p-8 pt-16">
            {currentPhase === 'user_turn' ? (
              <>
                <div className="mb-6">
                  <div className="text-white/80 text-lg mb-4 p-4 bg-slate-700/50 rounded-lg border-l-4 border-yellow-400">
                    <div className="text-yellow-300 text-sm font-semibold mb-2">현재 질문</div>
                    {currentQuestion.question}
                  </div>
                </div>
                
                <textarea
                  ref={answerRef}
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  className="w-full h-32 p-4 bg-slate-700/70 text-white border-2 border-slate-600 rounded-xl focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 resize-none text-lg transition-all duration-300"
                  placeholder="답변을 입력하세요... (춘식이를 이겨보세요! 💪)"
                />
                
                <div className="flex items-center justify-between mt-4">
                  <div className="text-slate-400 text-sm">
                    {currentAnswer.length}자 입력됨
                  </div>
                  <div className={`text-2xl font-bold ${getTimerColor()}`}>
                    ⏱️ {formatTime(timeLeft)}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-white/60">
                <div className="text-2xl mb-2">⏳</div>
                <div className="text-lg">대기 중...</div>
                <div className="text-sm text-slate-400 mt-2">답변 완료 후 결과 페이지로 이동합니다</div>
              </div>
            )}
          </div>
        </div>

        {/* 중앙 컨트롤 패널 */}
        <div className="bg-gradient-to-b from-gray-800 to-gray-900 rounded-2xl p-6 flex flex-col justify-center border-2 border-gray-600">
          <div className="text-center mb-6">
            <div className="text-gray-300 text-sm mb-2">면접 진행률</div>
            <div className="w-full bg-gray-700 rounded-full h-3 mb-2">
              <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500" style={{ width: '25%' }}></div>
            </div>
            <div className="text-white text-sm">25% 완료</div>
          </div>

          <div className="space-y-3">
            <button 
              className={`w-full py-3 rounded-xl font-bold text-lg transition-all duration-300 ${
                currentPhase === 'user_turn' && currentAnswer.trim()
                  ? 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white transform hover:scale-105 shadow-lg'
                  : 'bg-gray-600 text-gray-400 cursor-not-allowed'
              }`}
              onClick={handleAnswerSubmit}
              disabled={currentPhase !== 'user_turn' || !currentAnswer.trim()}
            >
              {currentPhase === 'user_turn' ? '🚀 답변 제출' : '⏳ 대기 중...'}
            </button>
            
            <div className="grid grid-cols-2 gap-2">
              <button 
                className="py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors text-sm"
                onClick={() => navigate('/interview/setup')}
              >
                ⚙️ 설정
              </button>
              <button 
                className="py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors text-sm"
              >
                📊 현황
              </button>
            </div>
          </div>
        </div>

        {/* AI 지원자 춘식이 */}
        <div className="bg-gradient-to-b from-blue-800 to-blue-900 rounded-2xl overflow-hidden relative border-2 border-cyan-400 shadow-2xl shadow-cyan-500/20">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 to-blue-500"></div>
          <div className="absolute top-6 left-6 text-cyan-300 font-bold text-lg">
            🤖 AI 춘식이
          </div>
          
          <div className="h-full flex flex-col justify-center items-center p-6 pt-16">
            <div className={`w-24 h-24 rounded-full mb-4 flex items-center justify-center border-4 transition-all duration-500 ${
              currentPhase === 'ai_turn' 
                ? 'bg-cyan-400/20 border-cyan-300 animate-pulse' 
                : 'bg-blue-700/50 border-cyan-400'
            }`}>
              <span className="text-4xl">🧑‍💼</span>
            </div>
            
            {currentPhase === 'ai_turn' ? (
              <div className="text-center">
                <div className="text-cyan-300 text-lg font-bold mb-3">답변 생성 중...</div>
                <div className="w-8 h-8 border-3 border-cyan-300 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                {isProcessingAI && (
                  <div className="text-xs text-cyan-400 space-y-1">
                    <div>🧠 AI 분석 중</div>
                    <div>📊 면접 결과 준비 중...</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center">
                <div className="text-blue-300 text-sm mb-1">대기 중</div>
                <div className="text-xs text-blue-400">난이도: {state.settings.difficulty}</div>
                <div className="text-xs text-cyan-400 mt-1">⚡ 준비 완료</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 상태 표시줄 */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-r from-gray-800 to-gray-900 p-4 border-t border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-6 text-gray-300">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-400 rounded-full mr-2 animate-pulse"></div>
              {currentPhase === 'ai_turn' ? '면접 완료 처리 중' : '면접 진행 중'}
            </div>
            <div>{state.settings.company} - {state.settings.position}</div>
            <div>AI 경쟁 모드 (1문제)</div>
          </div>
          
          <div className="flex items-center space-x-4 text-gray-400">
            <div>{currentPhase === 'user_turn' ? '👤 사용자 차례' : '🤖 AI 처리 중'}</div>
            <div>|</div>
            <div className="text-xs">
              {currentPhase === 'ai_turn' ? '곧 결과 페이지로 이동합니다' : 'Powered by 새로운 면접 시스템'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewActiveTemp;