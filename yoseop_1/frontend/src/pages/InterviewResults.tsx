import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { interviewApi } from '../services/api';
import apiClient, { handleApiError } from '../services/api';

interface FeedbackData {
  question: string;
  userAnswer: string;
  aiAnswer: string;
  userFeedback: string;
  aiFeedback: string;
  userScore: number;
  aiScore: number;
  userMemo: string;
  aiMemo: string;
}

interface SummaryData {
  clarity: number;
  structure: number;
  confidence: number;
  overallScore: number;
  strengths: string[];
  weaknesses: string[];
}

interface LongTermFeedback {
  shortTerm: {
    immediateActions: string[];
    nextInterviewPrep: string[];
    specificImprovements: string[];
  };
  longTerm: {
    skillDevelopment: string[];
    experienceAreas: string[];
    careerPath: string[];
  };
}

// 👁️ 시선 분석 결과 타입
interface GazeAnalysisData {
  gaze_score: number;
  jitter_score: number;
  compliance_score: number;
  stability_rating: string;
  created_at: string;
}

const InterviewResults: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();
  
  // 디버깅: URL 파라미터 확인
  console.log('🔍 DEBUG - URL params:', useParams());
  console.log('🔍 DEBUG - sessionId:', sessionId);
  console.log('🔍 DEBUG - location pathname:', location.pathname);
  const [activeTab, setActiveTab] = useState<'user' | 'ai' | 'longterm' | 'gaze'>('user');
  const [isLoading, setIsLoading] = useState(true);
  const [feedbackData, setFeedbackData] = useState<FeedbackData[]>([]);
  const [userSummary, setUserSummary] = useState<SummaryData | null>(null);
  const [aiSummary, setAiSummary] = useState<SummaryData | null>(null);
  const [longTermFeedback, setLongTermFeedback] = useState<LongTermFeedback | null>(null);
  const [interviewData, setInterviewData] = useState<any>(null);
  
  // 👁️ 시선 분석 결과 상태
  const [gazeAnalysis, setGazeAnalysis] = useState<GazeAnalysisData | null>(null);
  const [gazeLoading, setGazeLoading] = useState(false);

  // 가라 데이터
  const mockFeedbackData: FeedbackData[] = [
    {
      question: "자기소개를 해주세요",
      userAnswer: "안녕하세요. 저는 3년간 웹 개발 경험을 가진 김개발입니다. React와 Node.js를 주로 사용하여 사용자 친화적인 웹 애플리케이션을 개발해왔습니다. 팀 협업을 통해 프로젝트를 성공적으로 완료한 경험이 있으며, 지속적인 학습을 통해 새로운 기술을 습득하는 것을 즐깁니다.",
      aiAnswer: "안녕하세요. 저는 춘식이입니다. 5년간 다양한 프로젝트에서 풀스택 개발자로 활동해왔습니다. 특히 마이크로서비스 아키텍처와 클라우드 기술에 전문성을 가지고 있으며, 팀 리딩 경험도 있습니다. 사용자 중심의 솔루션을 제공하는 것을 목표로 하고 있습니다.",
      userFeedback: "전반적으로 좋은 자기소개입니다. 구체적인 성과나 수치를 포함하면 더욱 설득력 있는 답변이 될 것입니다. 예를 들어 '사용자 만족도 20% 향상' 같은 구체적인 결과를 언급해보세요.",
      aiFeedback: "춘식이의 답변은 경험과 전문성을 잘 보여줍니다. 다만 너무 일반적인 표현보다는 구체적인 프로젝트나 성과를 언급하면 더욱 효과적일 것입니다.",
      userScore: 85,
      aiScore: 90,
      userMemo: "구체적인 수치와 성과를 더 포함해야겠다.",
      aiMemo: "춘식이의 경험 수준이 높아 보인다. 나도 더 구체적인 성과를 준비해야겠다."
    },
    {
      question: "이 직무에 왜 관심이 있나요?",
      userAnswer: "사용자 경험을 개선하는 것에 관심이 많고, 이 회사의 혁신적인 제품과 문화가 매력적입니다. 또한 제가 가진 기술을 활용하여 회사에 기여할 수 있다고 생각합니다.",
      aiAnswer: "이 회사의 기술적 도전과 사회적 임팩트에 깊이 공감합니다. 제가 가진 마이크로서비스와 클라우드 경험이 회사의 확장 계획에 도움이 될 것이라 확신합니다. 또한 지속적인 혁신 문화가 개인의 성장과 잘 맞는다고 생각합니다.",
      userFeedback: "관심을 명확하게 표현했습니다. 회사의 구체적인 제품이나 서비스에 대한 언급을 추가하면 더욱 설득력 있는 답변이 될 것입니다.",
      aiFeedback: "춘식이는 회사에 대한 이해도가 높고, 자신의 경험과 회사의 니즈를 잘 연결시켰습니다. 다만 너무 형식적인 느낌이 있습니다.",
      userScore: 80,
      aiScore: 88,
      userMemo: "회사에 대한 더 깊은 조사가 필요하다.",
      aiMemo: "춘식이의 회사 이해도가 높다. 나도 더 구체적으로 준비해야겠다."
    },
    {
      question: "실패한 경험을 말해주세요",
      userAnswer: "프로젝트 일정을 맞추지 못한 경험이 있습니다. 초기 계획이 부족했고, 팀원들과의 소통이 원활하지 않았습니다. 이후에는 더 철저한 계획 수립과 정기적인 미팅을 통해 개선했습니다.",
      aiAnswer: "새로운 기술 스택 도입 과정에서 예상보다 많은 시간이 소요된 경험이 있습니다. 충분한 학습 시간을 확보하지 못했고, 팀 전체의 이해도가 낮았습니다. 이후 단계적 도입과 교육 프로그램을 통해 해결했습니다.",
      userFeedback: "실패를 인정하고 개선점을 찾아낸 점이 좋습니다. 구체적인 개선 결과나 학습한 점을 더 자세히 설명하면 더욱 효과적일 것입니다.",
      aiFeedback: "춘식이는 실패 경험을 통해 얻은 학습과 개선 방안을 잘 제시했습니다. 다만 너무 완벽한 해결책처럼 보일 수 있습니다.",
      userScore: 82,
      aiScore: 85,
      userMemo: "실패 경험에서 배운 점을 더 구체적으로 정리해야겠다.",
      aiMemo: "춘식이의 문제 해결 능력이 인상적이다."
    }
  ];

  const mockUserSummary: SummaryData = {
    clarity: 85,
    structure: 80,
    confidence: 78,
    overallScore: 81,
    strengths: [
      "명확한 의사소통 능력",
      "팀워크에 대한 이해",
      "지속적인 학습 의지"
    ],
    weaknesses: [
      "구체적인 성과 수치 부족",
      "회사에 대한 이해도 개선 필요",
      "자신감 있는 어조 연습 필요"
    ]
  };

  const mockAiSummary: SummaryData = {
    clarity: 90,
    structure: 88,
    confidence: 92,
    overallScore: 90,
    strengths: [
      "풍부한 경험과 전문성",
      "구체적인 기술적 지식",
      "자신감 있는 표현"
    ],
    weaknesses: [
      "너무 형식적인 답변",
      "개인적 특색 부족",
      "감정적 연결 부족"
    ]
  };

  const mockLongTermFeedback: LongTermFeedback = {
    shortTerm: {
      immediateActions: [
        "구체적인 성과 수치를 포함한 답변 준비",
        "지원 회사에 대한 더 깊은 조사",
        "자신감 있는 어조로 연습"
      ],
      nextInterviewPrep: [
        "STAR 방법론을 활용한 답변 구조화",
        "회사별 맞춤 답변 준비",
        "모의 면접 연습 강화"
      ],
      specificImprovements: [
        "답변 시간 관리 연습",
        "비언어적 커뮤니케이션 개선",
        "질문 예상 및 준비"
      ]
    },
    longTerm: {
      skillDevelopment: [
        "프로젝트 관리 및 리더십 경험 축적",
        "기술적 전문성 심화",
        "비즈니스 이해도 향상"
      ],
      experienceAreas: [
        "다양한 프로젝트 유형 경험",
        "팀 리딩 및 멘토링 경험",
        "업계 트렌드 및 최신 기술 습득"
      ],
      careerPath: [
        "시니어 개발자 역할 준비",
        "기술 리더십 역량 개발",
        "전문 분야 특화 및 브랜딩"
      ]
    }
  };

  // 면접 결과 데이터 로드 함수
  const loadInterviewResults = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    try {
      // TODO: 실제 API 호출로 대체
      // const response = await interviewApi.getInterviewResults(sessionId);
      // setFeedbackData(response.feedbackData);
      // setUserSummary(response.userSummary);
      // setAiSummary(response.aiSummary);
      // setLongTermFeedback(response.longTermFeedback);
      
      // 임시로 가라 데이터 사용
      setTimeout(() => {
        setFeedbackData(mockFeedbackData);
        setUserSummary(mockUserSummary);
        setAiSummary(mockAiSummary);
        setLongTermFeedback(mockLongTermFeedback);
        setIsLoading(false);
      }, 1000);
    } catch (error) {
      console.error('면접 결과 로드 실패:', error);
      setIsLoading(false);
    }
  }, [mockFeedbackData, mockUserSummary, mockAiSummary, mockLongTermFeedback]);

  // 👁️ 시선 분석 결과 로드 함수
  const loadGazeAnalysis = useCallback(async (sessionId: string) => {
    setGazeLoading(true);
    try {
      console.log('👁️ 시선 분석 결과 조회 시작:', sessionId);
      const response = await apiClient.get(`/gaze/analysis/${sessionId}`);
      
      if (response.data) {
        setGazeAnalysis(response.data);
        console.log('✅ 시선 분석 결과 로드 완료:', response.data);
      } else {
        console.log('ℹ️ 시선 분석 결과가 없습니다 (시선 추적을 하지 않은 면접)');
        setGazeAnalysis(null);
      }
    } catch (error) {
      console.error('❌ 시선 분석 결과 로드 실패:', error);
      setGazeAnalysis(null);
    } finally {
      setGazeLoading(false);
    }
  }, []);

  // 👁️ 시선 분석 피드백 생성 함수
  const generateGazeFeedback = (gazeData: GazeAnalysisData): string => {
    const { gaze_score, jitter_score, compliance_score, stability_rating } = gazeData;
    
    let feedback = "";
    
    // 전체 점수에 따른 기본 피드백
    if (gaze_score >= 80) {
      feedback = "🎉 우수합니다! 면접 중 시선 처리가 매우 안정적이었습니다.";
    } else if (gaze_score >= 60) {
      feedback = "👍 좋습니다! 전반적으로 안정적이나 조금 더 개선할 수 있습니다.";
    } else {
      feedback = "💪 개선이 필요합니다. 면접관을 직접 바라보는 연습을 해보세요.";
    }
    
    // 세부 점수별 추가 피드백
    const details = [];
    
    if (jitter_score < 30) {
      details.push("시선 움직임이 불안정했습니다. 한 곳에 집중하여 안정감을 높여보세요.");
    } else if (jitter_score >= 70) {
      details.push("시선이 매우 안정적이었습니다.");
    }
    
    if (compliance_score < 50) {
      details.push("화면을 벗어나는 시간이 많았습니다. 카메라 방향을 더 의식해보세요.");
    } else if (compliance_score >= 80) {
      details.push("카메라 방향을 잘 의식하고 계셨습니다.");
    }
    
    // 안정성 등급별 추가 조언
    if (stability_rating === 'poor') {
      details.push("다음 면접에서는 카메라 위치를 조정하고 시선 연습을 해보세요.");
    } else if (stability_rating === 'excellent') {
      details.push("시선 처리가 매우 전문적이었습니다.");
    }
    
    if (details.length > 0) {
      feedback += " " + details.join(" ");
    }
    
    return feedback;
  };

  // 세션 ID가 없으면 기본 결과 페이지로 리다이렉트
  useEffect(() => {
    if (!sessionId) {
      // 세션 ID가 없는 경우 (직접 접근) - 가라 데이터 사용
      setFeedbackData(mockFeedbackData);
      setUserSummary(mockUserSummary);
      setAiSummary(mockAiSummary);
      setLongTermFeedback(mockLongTermFeedback);
      setIsLoading(false);
    } else {
      // 세션 ID가 있는 경우 - 실제 데이터 로드
      loadInterviewResults(sessionId);
      // 👁️ 시선 분석 결과도 함께 로드
      loadGazeAnalysis(sessionId);
    }
  }, [sessionId, loadInterviewResults, loadGazeAnalysis, mockAiSummary, mockFeedbackData, mockLongTermFeedback, mockUserSummary]);

  // 면접 데이터 로드
  const loadInterviewData = useCallback(async () => {
    if (!sessionId) {
      console.error('Session ID가 없습니다');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      console.log('면접 상세 데이터 로딩:', sessionId);
      
      // /interview/history/{interview_id} API 호출
      const details = await interviewApi.getInterviewDetails(sessionId);
      console.log('받은 면접 데이터:', details);
      
      setInterviewData(details);
      
      // DB 데이터를 UI 형식으로 변환 (question_index 별로 그룹핑)
      const groupedData: { [key: number]: any } = {};
      
      details.forEach((item: any) => {
        const questionIndex = item.question_index || item.sequence || 1;
        
        if (!groupedData[questionIndex]) {
          groupedData[questionIndex] = {
            question: item.question_content || '질문이 없습니다',
            userAnswer: '',
            aiAnswer: '',
            userFeedback: '',
            aiFeedback: '',
            userScore: 0,
            aiScore: 0,
            userMemo: '',
            aiMemo: ''
          };
        }
        
        if (item.who === 'user') {
          groupedData[questionIndex].userAnswer = item.answer || '';
          const userFeedbackData = JSON.parse(item.feedback || '{}');
          groupedData[questionIndex].userFeedback = userFeedbackData.evaluation || '';
          groupedData[questionIndex].userScore = userFeedbackData.final_score || 0;
        } else if (item.who === 'ai_interviewer') {
          groupedData[questionIndex].aiAnswer = item.answer || '';
          const aiFeedbackData = JSON.parse(item.feedback || '{}');
          groupedData[questionIndex].aiFeedback = aiFeedbackData.evaluation || '';
          groupedData[questionIndex].aiScore = aiFeedbackData.final_score || 0;
        }
      });
      
      const processedData = Object.values(groupedData);
      
      setFeedbackData(processedData);
      
      // 사용자/AI 요약 데이터 생성
      if (details.length > 0) {
        const userItems = details.filter((item: any) => item.who === 'user');
        const aiItems = details.filter((item: any) => item.who === 'ai_interviewer');
        
        if (userItems.length > 0) {
          const avgScore = userItems.reduce((acc: number, item: any) => {
            const feedback = JSON.parse(item.feedback || '{}');
            return acc + (feedback.final_score || 0);
          }, 0) / userItems.length;
          
          setUserSummary({
            clarity: Math.round(avgScore * 0.9),
            structure: Math.round(avgScore * 0.85),
            confidence: Math.round(avgScore * 0.8),
            overallScore: Math.round(avgScore),
            strengths: ['구체적인 경험 언급', '논리적 구조', '성실한 답변'],
            weaknesses: ['자신감 부족', '구체성 개선 필요', '시간 관리']
          });
        }
        
        if (aiItems.length > 0) {
          const avgScore = aiItems.reduce((acc: number, item: any) => {
            const feedback = JSON.parse(item.feedback || '{}');
            return acc + (feedback.final_score || 0);
          }, 0) / aiItems.length;
          
          setAiSummary({
            clarity: Math.round(avgScore * 0.95),
            structure: Math.round(avgScore * 0.9),
            confidence: Math.round(avgScore * 0.92),
            overallScore: Math.round(avgScore),
            strengths: ['전문적 지식', '명확한 표현', '자신감 있는 태도'],
            weaknesses: ['감정적 연결 부족', '형식적 답변', '개인적 특색 부족']
          });
        }
      } else {
        // 데이터가 없는 경우 빈 상태로 설정
        console.log('면접 상세 데이터가 없습니다');
        setFeedbackData([]);
        setUserSummary(null);
        setAiSummary(null);
      }
      
    } catch (error) {
      console.error('면접 데이터 로딩 실패:', error);
      // 에러 시 목 데이터 사용
      setFeedbackData(mockFeedbackData);
      setUserSummary(mockUserSummary);
      setAiSummary(mockAiSummary);
      setLongTermFeedback(mockLongTermFeedback);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadInterviewData();
  }, [loadInterviewData]);

  // location state에서 탭 설정 확인
  useEffect(() => {
    if (location.state?.tab) {
      setActiveTab(location.state.tab);
    }
  }, [location.state]);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 90) return 'bg-green-100';
    if (score >= 80) return 'bg-blue-100';
    if (score >= 70) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const renderUserFeedback = () => {
    if (!userSummary) return null;
    
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 좌측 패널 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 비디오 영역 */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">면접 영상</h3>
            <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center">
                <button className="flex items-center justify-center w-14 h-14 rounded-full bg-white/80 text-gray-700 hover:bg-white transition-colors">
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                </button>
              </div>
            </div>
            <button className="w-full mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
              영상 저장
            </button>
          </div>

          {/* 최종 피드백 요약 */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">최종 피드백</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">명확성</span>
                <span className={`text-sm font-semibold ${getScoreColor(userSummary.clarity)}`}>
                  {userSummary.clarity}점
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">구조</span>
                <span className={`text-sm font-semibold ${getScoreColor(userSummary.structure)}`}>
                  {userSummary.structure}점
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">자신감</span>
                <span className={`text-sm font-semibold ${getScoreColor(userSummary.confidence)}`}>
                  {userSummary.confidence}점
                </span>
              </div>
              <div className="border-t pt-3">
                <div className="flex items-center justify-between">
                  <span className="text-base font-semibold text-gray-900">종합 점수</span>
                  <span className={`text-lg font-bold ${getScoreColor(userSummary.overallScore)}`}>
                    {userSummary.overallScore}점
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 강점 및 개선점 */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">강점 및 개선점</h3>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-green-700 mb-2">강점</h4>
                <ul className="space-y-1">
                  {userSummary.strengths.map((strength, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="text-green-500 mr-2">•</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-medium text-red-700 mb-2">개선점</h4>
                <ul className="space-y-1">
                  {userSummary.weaknesses.map((weakness, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="text-red-500 mr-2">•</span>
                      {weakness}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* 우측 패널 - 질문별 상세 피드백 */}
        <div className="lg:col-span-2 space-y-6">
          {feedbackData.map((feedback, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">
                  질문 {index + 1}: {feedback.question}
                </h3>
                <div className="text-center">
                  <span className="text-xs text-gray-500">점수</span>
                  <div className={`text-lg font-bold ${getScoreColor(feedback.userScore)}`}>
                    {feedback.userScore}점
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    내 답변
                  </label>
                  <textarea
                    className="w-full rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                    rows={6}
                    value={feedback.userAnswer}
                    readOnly
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    AI 피드백
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.userFeedback}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  내 메모
                </label>
                <textarea
                  className="w-full rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                  rows={3}
                  placeholder="개인 메모와 생각을 여기에 추가하세요..."
                  defaultValue={feedback.userMemo}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderAiFeedback = () => {
    if (!aiSummary) return null;
    
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 좌측 패널 */}
        <div className="lg:col-span-1 space-y-6">
          {/* AI 지원자 최종 피드백 요약 */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">AI 지원자 최종 피드백</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">명확성</span>
                <span className={`text-sm font-semibold ${getScoreColor(aiSummary.clarity)}`}>
                  {aiSummary.clarity}점
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">구조</span>
                <span className={`text-sm font-semibold ${getScoreColor(aiSummary.structure)}`}>
                  {aiSummary.structure}점
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">자신감</span>
                <span className={`text-sm font-semibold ${getScoreColor(aiSummary.confidence)}`}>
                  {aiSummary.confidence}점
                </span>
              </div>
              <div className="border-t pt-3">
                <div className="flex items-center justify-between">
                  <span className="text-base font-semibold text-gray-900">종합 점수</span>
                  <span className={`text-lg font-bold ${getScoreColor(aiSummary.overallScore)}`}>
                    {aiSummary.overallScore}점
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* AI 지원자 강점 및 개선점 */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">AI 지원자 분석</h3>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-green-700 mb-2">강점</h4>
                <ul className="space-y-1">
                  {aiSummary.strengths.map((strength, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="text-green-500 mr-2">•</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-medium text-red-700 mb-2">개선점</h4>
                <ul className="space-y-1">
                  {aiSummary.weaknesses.map((weakness, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="text-red-500 mr-2">•</span>
                      {weakness}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* 우측 패널 - AI 지원자 질문별 상세 피드백 */}
        <div className="lg:col-span-2 space-y-6">
          {feedbackData.map((feedback, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">
                  질문 {index + 1}: {feedback.question}
                </h3>
                <div className="text-center">
                  <span className="text-xs text-gray-500">점수</span>
                  <div className={`text-lg font-bold ${getScoreColor(feedback.aiScore)}`}>
                    {feedback.aiScore}점
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    AI 지원자 답변
                  </label>
                  <textarea
                    className="w-full rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                    rows={6}
                    value={feedback.aiAnswer}
                    readOnly
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    AI 답변 분석
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.aiFeedback}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  내 메모
                </label>
                <textarea
                  className="w-full rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                  rows={3}
                  placeholder="AI 답변에 대한 개인적인 생각을 여기에 기록하세요..."
                  defaultValue={feedback.aiMemo}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderLongTermFeedback = () => {
    if (!longTermFeedback) return null;
    
    return (
      <div className="space-y-8">
        {/* 단기 피드백 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">단기 피드백</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h4 className="text-lg font-semibold text-blue-600 mb-4">즉시 개선 가능한 부분</h4>
              <ul className="space-y-3">
                {longTermFeedback.shortTerm.immediateActions.map((action, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-blue-500 mr-2">•</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-green-600 mb-4">다음 면접 준비</h4>
              <ul className="space-y-3">
                {longTermFeedback.shortTerm.nextInterviewPrep.map((prep, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-green-500 mr-2">•</span>
                    {prep}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-purple-600 mb-4">구체적 개선사항</h4>
              <ul className="space-y-3">
                {longTermFeedback.shortTerm.specificImprovements.map((improvement, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-purple-500 mr-2">•</span>
                    {improvement}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* 장기 피드백 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">장기 피드백</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h4 className="text-lg font-semibold text-orange-600 mb-4">기술 개발</h4>
              <ul className="space-y-3">
                {longTermFeedback.longTerm.skillDevelopment.map((skill, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-orange-500 mr-2">•</span>
                    {skill}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-indigo-600 mb-4">경험 영역</h4>
              <ul className="space-y-3">
                {longTermFeedback.longTerm.experienceAreas.map((experience, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-indigo-500 mr-2">•</span>
                    {experience}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-teal-600 mb-4">경력 경로</h4>
              <ul className="space-y-3">
                {longTermFeedback.longTerm.careerPath.map((path, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start">
                    <span className="text-teal-500 mr-2">•</span>
                    {path}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 👁️ 시선 분석 결과 렌더링
  const renderGazeAnalysis = () => {
    if (gazeLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-3 text-gray-600">시선 분석 결과를 불러오는 중...</span>
        </div>
      );
    }

    if (!gazeAnalysis) {
      return (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="text-gray-400 text-6xl mb-4">👁️</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">시선 분석 데이터 없음</h3>
          <p className="text-gray-600">이 면접에서는 시선 추적이 진행되지 않았습니다.</p>
        </div>
      );
    }

    const feedback = generateGazeFeedback(gazeAnalysis);
    const scoreColor = gazeAnalysis.gaze_score >= 80 ? 'text-green-600' : 
                      gazeAnalysis.gaze_score >= 60 ? 'text-blue-600' : 'text-orange-600';

    return (
      <div className="space-y-6">
        {/* 전체 점수 카드 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 mb-4">
              <span className={`text-3xl font-bold ${scoreColor}`}>
                {Math.round(gazeAnalysis.gaze_score)}
              </span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">전체 시선 점수</h3>
            <div className="inline-flex items-center px-3 py-1 rounded-full text-sm">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                gazeAnalysis.stability_rating === 'excellent' ? 'bg-green-100 text-green-800' :
                gazeAnalysis.stability_rating === 'good' ? 'bg-blue-100 text-blue-800' :
                'bg-orange-100 text-orange-800'
              }`}>
                {gazeAnalysis.stability_rating === 'excellent' ? '우수' :
                 gazeAnalysis.stability_rating === 'good' ? '양호' : '개선필요'}
              </span>
            </div>
          </div>
        </div>

        {/* 세부 점수 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 시선 안정성 */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">🎯 시선 안정성</h4>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">안정성 점수</span>
              <span className="font-semibold">{Math.round(gazeAnalysis.jitter_score)}/100</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${gazeAnalysis.jitter_score}%` }}
              />
            </div>
            <p className="text-sm text-gray-600 mt-3">
              {gazeAnalysis.jitter_score >= 70 ? '시선 움직임이 매우 안정적입니다.' :
               gazeAnalysis.jitter_score >= 50 ? '시선 움직임이 적당히 안정적입니다.' :
               '시선 움직임이 불안정합니다. 집중도를 높여보세요.'}
            </p>
          </div>

          {/* 준수도 점수 */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">📹 카메라 시선</h4>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">준수도 점수</span>
              <span className="font-semibold">{Math.round(gazeAnalysis.compliance_score)}/100</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${gazeAnalysis.compliance_score}%` }}
              />
            </div>
            <p className="text-sm text-gray-600 mt-3">
              {gazeAnalysis.compliance_score >= 80 ? '카메라 방향을 잘 바라보셨습니다.' :
               gazeAnalysis.compliance_score >= 60 ? '대체로 카메라 방향을 의식하셨습니다.' :
               '카메라 방향을 더 의식해보세요.'}
            </p>
          </div>
        </div>

        {/* 피드백 메시지 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">💡 시선 분석 피드백</h4>
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
            <p className="text-gray-700 leading-relaxed">{feedback}</p>
          </div>
        </div>

        {/* 분석 정보 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h5 className="text-sm font-medium text-gray-900 mb-2">분석 정보</h5>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• 분석 시간: {new Date(gazeAnalysis.created_at).toLocaleString()}</p>
            <p>• MediaPipe AI를 사용한 정밀 시선 추적</p>
            <p>• 면접 전체 과정에 대한 종합 분석</p>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="면접 결과" subtitle="피드백 분석" />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner />
            <span className="ml-3 text-gray-600">결과를 분석하는 중...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="면접 결과" subtitle="피드백 분석" />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* 탭 네비게이션 */}
        <div className="mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('user')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'user'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                내 피드백
              </button>
              <button
                onClick={() => setActiveTab('ai')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'ai'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                AI 지원자 피드백
              </button>
              <button
                onClick={() => setActiveTab('longterm')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'longterm'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                단기/장기 피드백
              </button>
              {/* 👁️ 시선 분석 탭 - 데이터가 있을 때만 표시 */}
              {gazeAnalysis && (
                <button
                  onClick={() => setActiveTab('gaze')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'gaze'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  👁️ 시선 분석
                </button>
              )}
            </nav>
          </div>
        </div>

        {/* 탭 컨텐츠 */}
        <div>
          {activeTab === 'user' && renderUserFeedback()}
          {activeTab === 'ai' && renderAiFeedback()}
          {activeTab === 'longterm' && renderLongTermFeedback()}
          {activeTab === 'gaze' && renderGazeAnalysis()}
        </div>

        {/* 하단 액션 버튼 */}
        <div className="mt-12 flex justify-center">
          <button
            onClick={() => navigate(-1)}
            className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            뒤로 가기
          </button>
        </div>
      </div>
    </div>
  );
};

export default InterviewResults;