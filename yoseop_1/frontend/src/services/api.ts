import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    console.log('API 요청:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('요청 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => {
    console.log('API 응답:', response.status, response.data);
    return response;
  },
  (error) => {
    console.error('응답 오류:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

// 타입 정의
export interface InterviewSettings {
  company: string;
  position: string;
  mode: string;
  difficulty: string;
  candidate_name: string;
  documents?: string[];
}

export interface Question {
  id: string;
  question: string;
  category: string;
  time_limit: number;
  keywords: string[];
}

export interface AnswerSubmission {
  session_id: string;
  question_id: string;
  answer: string;
  time_spent: number;
}

export interface InterviewResult {
  session_id: string;
  total_score: number;
  category_scores: Record<string, number>;
  detailed_feedback: Array<{
    question: string;
    answer: string;
    score: number;
    feedback: string;
    strengths: string[];
    improvements: string[];
  }>;
  recommendations: string[];
  interview_info: InterviewSettings;
}

export interface InterviewHistory {
  total_interviews: number;
  interviews: Array<{
    session_id: string;
    settings: InterviewSettings;
    completed_at: string;
    total_score: number;
  }>;
}

// API 함수들
export const interviewApi = {
  // 면접 시작
  async startInterview(settings: InterviewSettings): Promise<{
    session_id: string;
    total_questions: number;
    message: string;
  }> {
    const response = await apiClient.post('/interview/start', settings);
    return response.data as {
      session_id: string;
      total_questions: number;
      message: string;
    };
  },

  // 문서 업로드
  async uploadDocument(file: File): Promise<{
    file_id: string;
    analyzed_content: any;
    message: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/interview/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data as {
      file_id: string;
      analyzed_content: any;
      message: string;
    };
  },

  // 다음 질문 가져오기
  async getNextQuestion(sessionId: string): Promise<{
    question?: Question;
    question_index?: number;
    total_questions?: number;
    progress?: number;
    completed?: boolean;
    message?: string;
  }> {
    const response = await apiClient.get(`/interview/question?session_id=${sessionId}`);
    return response.data as {
      question?: Question;
      question_index?: number;
      total_questions?: number;
      progress?: number;
      completed?: boolean;
      message?: string;
    };
  },

  // 답변 제출
  async submitAnswer(answerData: AnswerSubmission): Promise<{
    score: number;
    message: string;
    detailed_evaluation: string;
  }> {
    const response = await apiClient.post('/interview/answer', answerData);
    return response.data as {
      score: number;
      message: string;
      detailed_evaluation: string;
    };
  },

  // 면접 결과 조회
  async getInterviewResults(sessionId: string): Promise<InterviewResult> {
    const response = await apiClient.get(`/interview/results/${sessionId}`);
    return response.data as InterviewResult;
  },

  // 면접 기록 조회
  async getInterviewHistory(userId?: string): Promise<InterviewHistory> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get('/interview/history', { params });
    return response.data as InterviewHistory;
  },

  // AI 경쟁 면접 시작
  async startAICompetition(settings: InterviewSettings): Promise<{
    session_id: string;
    comparison_session_id: string;
    user_session_id: string;
    ai_session_id: string;
    question?: Question;
    current_phase: string;
    current_respondent: string;
    question_index: number;
    total_questions: number;
    ai_name: string;
    user_name?: string;
    starts_with_user: boolean;
    message: string;
  }> {
    const response = await apiClient.post('/interview/ai/start', settings);
    return response.data as {
      session_id: string;
      comparison_session_id: string;
      user_session_id: string;
      ai_session_id: string;
      question?: Question;
      current_phase: string;
      current_respondent: string;
      question_index: number;
      total_questions: number;
      ai_name: string;
      user_name?: string;
      starts_with_user: boolean;
      message: string;
    };
  },

  // 비교 면접 사용자 턴 제출
  async submitComparisonUserTurn(comparisonSessionId: string, answer: string): Promise<{
    status: string;
    message: string;
    next_phase: string;
    submission_result: any;
    next_user_question?: Question;
    next_question?: Question;
  }> {
    const response = await apiClient.post('/interview/comparison/user-turn', {
      comparison_session_id: comparisonSessionId,
      answer: answer
    });
    return response.data as {
      status: string;
      message: string;
      next_phase: string;
      submission_result: any;
      next_user_question?: Question;
      next_question?: Question;
    };
  },

  // 비교 면접 AI 턴 처리
  async processComparisonAITurn(comparisonSessionId: string, step: string = 'question'): Promise<{
    status: string;
    step: string;
    interview_status?: string;
    ai_question?: any;
    ai_answer?: {
      content: string;
      persona_name: string;
      confidence: number;
    };
    next_user_question?: Question;
    next_phase?: string;
    current_question_index?: number;
    message: string;
  }> {
    const response = await apiClient.post('/interview/comparison/ai-turn', {
      comparison_session_id: comparisonSessionId,
      step: step
    });
    return response.data as {
      status: string;
      step: string;
      interview_status?: string;
      ai_question?: any;
      ai_answer?: {
        content: string;
        persona_name: string;
        confidence: number;
      };
      next_user_question?: Question;
      next_phase?: string;
      current_question_index?: number;
      message: string;
    };
  },

  // AI 답변 생성
  async getAIAnswer(sessionId: string, questionId: string): Promise<{
    question: string;
    questionType: string;
    questionIntent: string;
    answer: string;
    time_spent: number;
    score: number;
    quality_level: string;
    persona_name: string;
  }> {
    const response = await apiClient.get(`/interview/ai-answer/${sessionId}/${questionId}`);
    return response.data as {
      question: string;
      questionType: string;
      questionIntent: string;
      answer: string;
      time_spent: number;
      score: number;
      quality_level: string;
      persona_name: string;
    };
  },

  // 서버 상태 확인
  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
  }> {
    const response = await apiClient.get('/health');
    return response.data as {
      status: string;
      timestamp: string;
    };
  },
};

// 에러 처리 유틸리티
export const handleApiError = (error: any): string => {
  if (error.response) {
    // 서버 응답 에러
    return error.response.data?.detail || '서버 오류가 발생했습니다.';
  } else if (error.request) {
    // 네트워크 에러
    return '네트워크 연결을 확인해주세요.';
  } else {
    // 기타 에러
    return '알 수 없는 오류가 발생했습니다.';
  }
};

// 파일 크기 검증
export const validateFileSize = (file: File, maxSize: number = 16 * 1024 * 1024): boolean => {
  return file.size <= maxSize;
};

// 파일 확장자 검증
export const validateFileExtension = (file: File, allowedExtensions: string[] = ['pdf', 'doc', 'docx']): boolean => {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return extension ? allowedExtensions.includes(extension) : false;
};

export default apiClient;