import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { InterviewSettings, Question, InterviewResult } from '../services/api';

// 새로운 타입 정의
interface JobPosting {
  company: string;       // 표시용 회사명
  companyCode: string;   // API용 회사 코드
  position: string;
  postingId: string;
}

interface Resume {
  id: string;
  name: string;
  email: string;
  phone: string;
  academic_record: string;
  career: string;
  tech: string;
  activities: string;
  certificate: string;
  awards: string;
  created_at: string;
  updated_at: string;
}

interface AISettings {
  mode: string;
  aiQualityLevel: number;
  interviewers: Array<{
    id: string;
    name: string;
    role: string;
  }>;
}

// 상태 타입 정의
interface InterviewState {
  // 새로운 4단계 플로우 데이터
  jobPosting: JobPosting | null;
  resume: Resume | null;
  interviewMode: string | null;
  aiSettings: AISettings | null;
  
  // 카메라 스트림
  cameraStream: MediaStream | null;
  
  // 면접 설정
  settings: InterviewSettings | null;
  
  // 세션 정보
  sessionId: string | null;
  
  // 질문 관련
  questions: Question[];
  currentQuestionIndex: number;
  totalQuestions: number;
  
  // 답변 관련
  answers: Array<{
    session_id?: string;
    question_id?: string;
    questionId?: string;
    answer: string;
    time_spent?: number;
    timeSpent?: number;
    score?: number;
  }>;
  
  // AI 답변 관련
  aiAnswers: Array<{
    question_id: string;
    answer: string;
    score: number;
    persona_name: string;
    time_spent: number;
  }>;
  
  // 면접 진행 상태
  interviewStatus: 'idle' | 'setup' | 'ready' | 'active' | 'paused' | 'completed';
  
  // 결과
  results: InterviewResult | null;
  
  // UI 상태
  isLoading: boolean;
  error: string | null;
  
  // 타이머
  timeLeft: number;
  
  // 진행률
  progress: number;
}

// 액션 타입 정의
type InterviewAction =
  | { type: 'SET_JOB_POSTING'; payload: JobPosting }
  | { type: 'SET_RESUME'; payload: Resume }
  | { type: 'SET_INTERVIEW_MODE'; payload: string }
  | { type: 'SET_AI_SETTINGS'; payload: AISettings }
  | { type: 'SET_CAMERA_STREAM'; payload: MediaStream | null }
  | { type: 'SET_SETTINGS'; payload: InterviewSettings }
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'SET_QUESTIONS'; payload: Question[] }
  | { type: 'ADD_QUESTION'; payload: Question }
  | { type: 'SET_CURRENT_QUESTION'; payload: number }
  | { type: 'SET_CURRENT_QUESTION_INDEX'; payload: number }
  | { type: 'ADD_ANSWER'; payload: { session_id?: string; question_id?: string; questionId?: string; answer: string; time_spent?: number; timeSpent?: number; score?: number } }
  | { type: 'ADD_AI_ANSWER'; payload: { question_id: string; answer: string; score: number; persona_name: string; time_spent: number } }
  | { type: 'SET_INTERVIEW_STATUS'; payload: InterviewState['interviewStatus'] }
  | { type: 'SET_RESULTS'; payload: InterviewResult }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_TIME_LEFT'; payload: number }
  | { type: 'SET_PROGRESS'; payload: number }
  | { type: 'RESET_INTERVIEW' };

// 초기 상태
const initialState: InterviewState = {
  jobPosting: null,
  resume: null,
  interviewMode: null,
  aiSettings: null,
  cameraStream: null,
  settings: null,
  sessionId: null,
  questions: [],
  currentQuestionIndex: 0,
  totalQuestions: 0,
  answers: [],
  aiAnswers: [],
  interviewStatus: 'idle',
  results: null,
  isLoading: false,
  error: null,
  timeLeft: 0,
  progress: 0,
};

// 리듀서 함수
function interviewReducer(state: InterviewState, action: InterviewAction): InterviewState {
  switch (action.type) {
    case 'SET_JOB_POSTING':
      return { ...state, jobPosting: action.payload };
    
    case 'SET_RESUME':
      return { ...state, resume: action.payload };
    
    case 'SET_INTERVIEW_MODE':
      return { ...state, interviewMode: action.payload };
    
    case 'SET_AI_SETTINGS':
      return { ...state, aiSettings: action.payload };
    
    case 'SET_CAMERA_STREAM':
      return { ...state, cameraStream: action.payload };
    
    case 'SET_SETTINGS':
      return { ...state, settings: action.payload };
    
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    
    case 'SET_QUESTIONS':
      return { 
        ...state, 
        questions: action.payload, 
        totalQuestions: action.payload.length,
        progress: state.totalQuestions > 0 ? (state.currentQuestionIndex / action.payload.length) * 100 : 0
      };
    
    case 'ADD_QUESTION':
      // 중복 질문 방지: 같은 ID의 질문이 이미 있으면 추가하지 않음
      const questionExists = state.questions.some(q => q.id === action.payload.id);
      if (questionExists) {
        console.log('🚫 중복 질문 방지:', action.payload.id);
        return state;
      }
      
      const newQuestions = [...state.questions, action.payload];
      console.log('✅ 새 질문 추가:', action.payload.id, action.payload.category);
      return {
        ...state,
        questions: newQuestions,
        totalQuestions: newQuestions.length
      };
    
    case 'SET_CURRENT_QUESTION':
      return { 
        ...state, 
        currentQuestionIndex: action.payload,
        progress: state.totalQuestions > 0 ? ((action.payload + 1) / state.totalQuestions) * 100 : 0
      };
    
    case 'SET_CURRENT_QUESTION_INDEX':
      return {
        ...state,
        currentQuestionIndex: action.payload,
        progress: state.totalQuestions > 0 ? ((action.payload + 1) / state.totalQuestions) * 100 : 0
      };
    
    case 'ADD_ANSWER':
      const newAnswers = [...state.answers, action.payload];
      return { 
        ...state, 
        answers: newAnswers
      };
    
    case 'ADD_AI_ANSWER':
      const newAiAnswers = [...state.aiAnswers, action.payload];
      return { 
        ...state, 
        aiAnswers: newAiAnswers
      };
    
    case 'SET_INTERVIEW_STATUS':
      return { ...state, interviewStatus: action.payload };
    
    case 'SET_RESULTS':
      return { ...state, results: action.payload };
    
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    
    case 'SET_TIME_LEFT':
      return { ...state, timeLeft: action.payload };
    
    case 'SET_PROGRESS':
      return { ...state, progress: action.payload };
    
    case 'RESET_INTERVIEW':
      return initialState;
    
    default:
      return state;
  }
}

// Context 생성
const InterviewContext = createContext<{
  state: InterviewState;
  dispatch: React.Dispatch<InterviewAction>;
} | null>(null);

// Provider 컴포넌트
export function InterviewProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(interviewReducer, initialState);
  
  return (
    <InterviewContext.Provider value={{ state, dispatch }}>
      {children}
    </InterviewContext.Provider>
  );
}

// 커스텀 훅
export function useInterview() {
  const context = useContext(InterviewContext);
  if (!context) {
    throw new Error('useInterview must be used within an InterviewProvider');
  }
  return context;
}

// 헬퍼 함수들
export const interviewHelpers = {
  // 현재 질문 가져오기
  getCurrentQuestion: (state: InterviewState): Question | null => {
    if (state.currentQuestionIndex < state.questions.length) {
      return state.questions[state.currentQuestionIndex];
    }
    return null;
  },
  
  // 다음 질문 여부 확인
  hasNextQuestion: (state: InterviewState): boolean => {
    return state.currentQuestionIndex < state.questions.length - 1;
  },
  
  // 면접 완료 여부 확인
  isInterviewCompleted: (state: InterviewState): boolean => {
    return state.currentQuestionIndex >= state.questions.length && state.questions.length > 0;
  },
  
  // 진행률 계산
  calculateProgress: (state: InterviewState): number => {
    if (state.totalQuestions === 0) return 0;
    return ((state.currentQuestionIndex + 1) / state.totalQuestions) * 100;
  },
  
  // 평균 점수 계산
  calculateAverageScore: (state: InterviewState): number => {
    const answersWithScores = state.answers.filter(answer => answer.score !== undefined);
    if (answersWithScores.length === 0) return 0;
    
    const totalScore = answersWithScores.reduce((sum, answer) => sum + (answer.score || 0), 0);
    return Math.round(totalScore / answersWithScores.length);
  },
  
  // 총 소요 시간 계산
  calculateTotalTime: (state: InterviewState): number => {
    return state.answers.reduce((total, answer) => total + (answer.timeSpent || answer.time_spent || 0), 0);
  },
  
  // 시간 포맷팅
  formatTime: (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  },
  
  // 타이머 색상 결정
  getTimerColor: (timeLeft: number): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  },
  
  // 점수 색상 결정
  getScoreColor: (score: number): string => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  },
  
  // 면접 상태 메시지
  getStatusMessage: (status: InterviewState['interviewStatus']): string => {
    switch (status) {
      case 'idle':
        return '면접 준비 중';
      case 'setup':
        return '면접 설정 중';
      case 'active':
        return '면접 진행 중';
      case 'paused':
        return '면접 일시정지';
      case 'completed':
        return '면접 완료';
      default:
        return '알 수 없음';
    }
  },
  
  // 로컬 스토리지에 상태 저장
  saveToLocalStorage: (state: InterviewState): void => {
    try {
      localStorage.setItem('interview_state', JSON.stringify(state));
    } catch (error) {
      console.error('로컬 스토리지 저장 오류:', error);
    }
  },
  
  // 로컬 스토리지에서 상태 복원
  loadFromLocalStorage: (): Partial<InterviewState> | null => {
    try {
      const saved = localStorage.getItem('interview_state');
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.error('로컬 스토리지 로드 오류:', error);
      return null;
    }
  },
  
  // 로컬 스토리지 정리
  clearLocalStorage: (): void => {
    try {
      localStorage.removeItem('interview_state');
    } catch (error) {
      console.error('로컬 스토리지 정리 오류:', error);
    }
  },
};