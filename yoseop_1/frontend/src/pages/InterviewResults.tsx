import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { interviewApi } from '../services/api';

interface FeedbackData {
  question: string;
  userAnswer: string;
  aiAnswer: string;
  userEvaluation: string;
  userImprovement: string;
  aiFeedback: string;
  aiEvaluation: string;
  aiImprovement: string;
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
  feedback: string;
  summary: string;
}

interface LongTermFeedback {
  shortTerm: {
    title: string;
    improvements: {
      category: string;
      items: any[];
    }[];
  };
  longTerm: {
    title: string;
    improvements: {
      category: string;
      items: any[];
    }[];
  };
}

const InterviewResults: React.FC = () => {
  const navigate = useNavigate();
  const { interviewId } = useParams<{ interviewId: string }>();
  const location = useLocation();
  
  // 강화된 디버깅 - 백엔드 로그로도 출력
  useEffect(() => {
    const debugInfo = {
      componentMounted: 'InterviewResults',
      currentURL: window.location.href,
      interviewId: interviewId,
      interviewIdType: typeof interviewId,
      locationPathname: location.pathname,
      interviewIdExists: !!interviewId,
      timestamp: new Date().toISOString()
    };
    
    console.log('🚀 =====InterviewResults 컴포넌트 마운트=====');
    console.log('🔍 디버깅 정보:', debugInfo);
    
    // API 호출해서 백엔드 로그에도 출력
    fetch('/api', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        log: 'FRONTEND_DEBUG',
        component: 'InterviewResults', 
        data: debugInfo 
      })
    }).catch(e => console.log('백엔드 로그 전송 실패:', e));
    
  }, [interviewId, location.pathname]);
  const [activeTab, setActiveTab] = useState<'user' | 'ai' | 'longterm'>('user');
  const [isLoading, setIsLoading] = useState(true);
  const [feedbackData, setFeedbackData] = useState<FeedbackData[]>([]);
  const [userSummary, setUserSummary] = useState<SummaryData | null>(null);
  const [aiSummary, setAiSummary] = useState<SummaryData | null>(null);
  const [longTermFeedback, setLongTermFeedback] = useState<LongTermFeedback | null>(null);
  const [interviewData, setInterviewData] = useState<any>(null);
  const [memos, setMemos] = useState<{[key: string]: {user: string, ai: string}}>({});
  
  // 영상 관련 상태 관리
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoMetadata, setVideoMetadata] = useState<any>(null);

  // 메모 저장 함수
  const saveMemo = async (questionIndex: number, type: 'user' | 'ai', memo: string) => {
    try {
      const response = await fetch(`/interview/memo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          interview_id: parseInt(interviewId || '0'),
          question_index: questionIndex,
          who: type === 'user' ? 'user' : 'ai_interviewer',
          memo: memo
        })
      });

      if (response.ok) {
        console.log('메모 저장 성공');
        alert('메모가 성공적으로 저장되었습니다.'); // Success alert
        // 로컬 state도 업데이트
        setMemos(prev => ({
          ...prev,
          [`${questionIndex}`]: {
            ...prev[`${questionIndex}`],
            [type]: memo
          }
        }));
      } else {
        console.error('메모 저장 실패');
        alert('메모 저장에 실패했습니다. 다시 시도해주세요.'); // Failure alert
      }
    } catch (error) {
      console.error('메모 저장 오류:', error);
      alert('메모 저장 중 오류가 발생했습니다. 네트워크 연결을 확인해주세요.'); // Error alert
    }
  };

  // 가라 데이터
  const mockFeedbackData: FeedbackData[] = [
    {
      question: "자기소개를 해주세요",
      userAnswer: "안녕하세요. 저는 3년간 웹 개발 경험을 가진 김개발입니다. React와 Node.js를 주로 사용하여 사용자 친화적인 웹 애플리케이션을 개발해왔습니다. 팀 협업을 통해 프로젝트를 성공적으로 완료한 경험이 있으며, 지속적인 학습을 통해 새로운 기술을 습득하는 것을 즐깁니다.",
      aiAnswer: "안녕하세요. 저는 춘식이입니다. 5년간 다양한 프로젝트에서 풀스택 개발자로 활동해왔습니다. 특히 마이크로서비스 아키텍처와 클라우드 기술에 전문성을 가지고 있으며, 팀 리딩 경험도 있습니다. 사용자 중심의 솔루션을 제공하는 것을 목표로 하고 있습니다.",
      userEvaluation: "전반적으로 좋은 자기소개입니다. 구체적인 성과나 수치를 포함하면 더욱 설득력 있는 답변이 될 것입니다.",
      userImprovement: "예를 들어 '사용자 만족도 20% 향상' 같은 구체적인 결과를 언급해보세요.",
      aiFeedback: "춘식이의 답변은 경험과 전문성을 잘 보여줍니다. 다만 너무 일반적인 표현보다는 구체적인 프로젝트나 성과를 언급하면 더욱 효과적일 것입니다.",
      aiEvaluation: "답변이 체계적이고 경험을 잘 보여줍니다.",
      aiImprovement: "구체적인 성과 수치를 포함하면 더 좋겠습니다.",
      userScore: 85,
      aiScore: 90,
      userMemo: "구체적인 수치와 성과를 더 포함해야겠다.",
      aiMemo: "춘식이의 경험 수준이 높아 보인다. 나도 더 구체적인 성과를 준비해야겠다."
    },
    {
      question: "이 직무에 왜 관심이 있나요?",
      userAnswer: "사용자 경험을 개선하는 것에 관심이 많고, 이 회사의 혁신적인 제품과 문화가 매력적입니다. 또한 제가 가진 기술을 활용하여 회사에 기여할 수 있다고 생각합니다.",
      aiAnswer: "이 회사의 기술적 도전과 사회적 임팩트에 깊이 공감합니다. 제가 가진 마이크로서비스와 클라우드 경험이 회사의 확장 계획에 도움이 될 것이라 확신합니다. 또한 지속적인 혁신 문화가 개인의 성장과 잘 맞는다고 생각합니다.",
      userEvaluation: "관심을 명확하게 표현했습니다. 회사의 구체적인 제품이나 서비스에 대한 언급을 추가하면 더욱 설득력 있는 답변이 될 것입니다.",
      userImprovement: "회사의 구체적인 제품이나 서비스에 대한 언급을 추가하면 더욱 설득력 있는 답변이 될 것입니다.",
      aiFeedback: "춘식이는 회사에 대한 이해도가 높고, 자신의 경험과 회사의 니즈를 잘 연결시켰습니다. 다만 너무 형식적인 느낌이 있습니다.",
      aiEvaluation: "회사에 대한 이해도가 높고 경험과 연결점을 잘 찾았습니다.",
      aiImprovement: "더 개인적이고 진정성 있는 답변이 필요합니다.",
      userScore: 80,
      aiScore: 88,
      userMemo: "회사에 대한 더 깊은 조사가 필요하다.",
      aiMemo: "춘식이의 회사 이해도가 높다. 나도 더 구체적으로 준비해야겠다."
    },
    {
      question: "실패한 경험을 말해주세요",
      userAnswer: "프로젝트 일정을 맞추지 못한 경험이 있습니다. 초기 계획이 부족했고, 팀원들과의 소통이 원활하지 않았습니다. 이후에는 더 철저한 계획 수립과 정기적인 미팅을 통해 개선했습니다.",
      aiAnswer: "새로운 기술 스택 도입 과정에서 예상보다 많은 시간이 소요된 경험이 있습니다. 충분한 학습 시간을 확보하지 못했고, 팀 전체의 이해도가 낮았습니다. 이후 단계적 도입과 교육 프로그램을 통해 해결했습니다.",
      userEvaluation: "실패를 인정하고 개선점을 찾아낸 점이 좋습니다.",
      userImprovement: "구체적인 개선 결과나 학습한 점을 더 자세히 설명하면 더욱 효과적일 것입니다.",
      aiFeedback: "춘식이는 실패 경험을 통해 얻은 학습과 개선 방안을 잘 제시했습니다. 다만 너무 완벽한 해결책처럼 보일 수 있습니다.",
      aiEvaluation: "실패 경험을 통해 얻은 학습과 개선 방안을 잘 제시했습니다.",
      aiImprovement: "너무 완벽한 해결책처럼 보이지 않도록, 어려웠던 점을 더 강조하면 좋겠습니다.",
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
    ],
    feedback: "전반적으로 좋은 답변이었습니다.",
    summary: "면접 준비가 잘 되어 있습니다."
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
    ],
    feedback: "기술적 전문성이 우수합니다.",
    summary: "매우 인상적인 답변이었습니다."
  };

  const mockLongTermFeedback: LongTermFeedback = {
    shortTerm: {
      title: "단기 개선 계획 (1-3개월)",
      improvements: [
        {
          category: "immediate actions",
          items: [
            "구체적인 성과 수치를 포함한 답변 준비",
            "지원 회사에 대한 더 깊은 조사",
            "자신감 있는 어조로 연습"
          ]
        },
        {
          category: "next interview prep",
          items: [
            "STAR 방법론을 활용한 답변 구조화",
            "회사별 맞춤 답변 준비",
            "모의 면접 연습 강화"
          ]
        }
      ]
    },
    longTerm: {
      title: "장기 개선 계획 (6-12개월)",
      improvements: [
        {
          category: "skill development",
          items: [
            "프로젝트 관리 및 리더십 경험 축적",
            "기술적 전문성 심화",
            "비즈니스 이해도 향상"
          ]
        },
        {
          category: "career path",
          items: [
            "시니어 개발자 역할 준비",
            "기술 리더십 역량 개발",
            "전문 분야 특화 및 브랜딩"
          ]
        }
      ]
    }
  };

  // 면접 데이터 로드 함수 (먼저 선언)
  const loadInterviewData = useCallback(async () => {
    if (!interviewId) {
      console.error('Interview ID가 없습니다');
      setIsLoading(false);
      return;
    }

    // string을 int로 변환 및 유효성 검사
    const interviewIdInt = parseInt(interviewId, 10);
    if (isNaN(interviewIdInt) || interviewIdInt <= 0) {
      console.error('유효하지 않은 Interview ID:', interviewId);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      console.log('🔄 면접 상세 데이터 로딩 시작');
      console.log('🔄 interviewId (string):', interviewId, typeof interviewId);
      console.log('🔄 interviewId (int):', interviewIdInt, typeof interviewIdInt);
      console.log('🔄 호출할 API URL:', `/interview/history/${interviewIdInt}`);
      
      // /interview/history/{interview_id} API 호출 (유효성 검증 후 원래 string으로 전달)
      const response = await interviewApi.getInterviewDetails(interviewId!);
      console.log('✅ 받은 면접 응답:', response);
      console.log('✅ 응답 구조:', {
        hasDetails: !!response.details,
        detailsLength: response.details?.length || 0,
        hasTotalFeedback: !!response.total_feedback,
        hasPlans: !!response.plans,
        hasVideoUrl: !!response.video_url,
        hasVideoMetadata: !!response.video_metadata
      });
      
      // 영상 데이터 처리 - API 응답 기반 처리
      if (response.video_url) {
        // 백엔드에서 제공한 스트리밍 URL 사용
        console.log('🎬 영상 파일 발견, 스트리밍 URL 설정:', response.video_url);
        setVideoUrl(response.video_url);
        setVideoError(null);
        setVideoLoading(true);
        
        if (response.video_metadata) {
          setVideoMetadata(response.video_metadata);
          console.log('📄 영상 메타데이터:', response.video_metadata);
        }
      } else {
        console.log('ℹ️ 이 면접에는 녹화된 영상이 없습니다');
        setVideoUrl(null);
        setVideoError('이 면접에는 녹화된 영상이 없습니다.');
        setVideoLoading(false);
      }
      
      const details = response.details || response; // 이전 API 호환성을 위한 fallback
      setInterviewData(details);
      
      // DB 데이터를 UI 형식으로 변환 (question_index 별로 그룹핑)
      const groupedData: { [key: number]: any } = {};
      
      console.log('🔧 details 원본 데이터:', details);
      console.log('🔧 details 길이:', details.length);
      
      details.forEach((item: any, index: number) => {
        console.log(`🔧 처리 중인 item ${index}:`, item);
        console.log(`🔧 item.who: ${item.who}`);
        
        const questionIndex = item.question_index || item.sequence || index + 1;
        
        if (!groupedData[questionIndex]) {
          groupedData[questionIndex] = {
            question: item.question_content || '질문이 없습니다',
            userAnswer: '',
            aiAnswer: '',
            userEvaluation: '',
            userImprovement: '',
            aiEvaluation: '',
            aiImprovement: '',
            userScore: 0,
            aiScore: 0,
            userMemo: '',
            aiMemo: ''
          };
        }
        
        // who 컬럼으로 역할별 데이터 분류
        if (item.who === 'user') {
          groupedData[questionIndex].userAnswer = item.answer || '';
          try {
            const userFeedback = JSON.parse(item.feedback || '{}');
            console.log(`🔧 question ${questionIndex} user feedback:`, userFeedback);
            
            groupedData[questionIndex].userEvaluation = userFeedback.evaluation || userFeedback.detailed_feedback || '';
            groupedData[questionIndex].userImprovement = userFeedback.improvement || '';
            groupedData[questionIndex].userScore = userFeedback.final_score || userFeedback.score || 0;
            groupedData[questionIndex].userMemo = item.memo || '';
          } catch (error) {
            console.log(`🔧 question ${questionIndex} user feedback 파싱 실패:`, error);
            groupedData[questionIndex].userEvaluation = item.feedback || '';
            groupedData[questionIndex].userImprovement = '';
          }
        } else if (item.who === 'ai_interviewer') {
          groupedData[questionIndex].aiAnswer = item.answer || '';
          try {
            const aiFeedback = JSON.parse(item.feedback || '{}');
            console.log(`🔧 question ${questionIndex} ai feedback:`, aiFeedback);
            
            groupedData[questionIndex].aiEvaluation = aiFeedback.evaluation || '';
            groupedData[questionIndex].aiImprovement = aiFeedback.improvement || '';
            groupedData[questionIndex].aiScore = aiFeedback.final_score || aiFeedback.score || 0;
            groupedData[questionIndex].aiMemo = item.memo || '';
          } catch (error) {
            console.log(`🔧 question ${questionIndex} ai feedback 파싱 실패:`, error);
            groupedData[questionIndex].aiFeedback = item.feedback || '';
          }
        }
      });
      
      // UI 상태 업데이트
      if (Object.keys(groupedData).length > 0) {
        const feedbackArray = Object.values(groupedData).map((item, index) => ({
          ...item,
          questionIndex: index + 1
        }));
        
        console.log('🔧 feedbackArray 생성됨:', feedbackArray);
        console.log('🔧 feedbackArray 길이:', feedbackArray.length);
        setFeedbackData(feedbackArray);
        console.log('🔧 setFeedbackData 호출 완료');
        
        // fallback 함수 정의
        const generateFallbackSummaries = () => {
          const userScores = details.map((item: any) => {
            try {
              const feedback = JSON.parse(item.feedback || '{}');
              return feedback.final_score || 0;
            } catch {
              return 0;
            }
          }).filter((score: number) => score > 0);
          
          if (userScores.length > 0) {
            const avgScore = userScores.reduce((acc: number, score: number) => acc + score, 0) / userScores.length;
            setUserSummary({
              clarity: Math.round(avgScore * 0.9),
              structure: Math.round(avgScore * 0.95),
              confidence: Math.round(avgScore * 0.85),
              overallScore: Math.round(avgScore),
              strengths: ['구체적인 경험 사례', '논리적 답변 구조'],
              weaknesses: ['답변 시간 관리', '핵심 포인트 강조'],
              feedback: 'fallback 피드백입니다.',
              summary: 'fallback 요약입니다.'
            });
          } else {
            setUserSummary({
              clarity: 70, structure: 75, confidence: 65, overallScore: 70,
              strengths: ['면접 참여 의지'], weaknesses: ['답변 준비 부족'],
              feedback: 'fallback 피드백입니다.',
              summary: 'fallback 요약입니다.'
            });
          }
          
          setAiSummary({
            clarity: 85, structure: 88, confidence: 82, overallScore: 85,
            strengths: ['논리적 답변 구조'], weaknesses: ['구체적 사례 부족'],
            feedback: 'AI fallback 피드백입니다.',
            summary: 'AI fallback 요약입니다.'
          });
          
          console.log('🔧 fallback summary 생성 완료');
        };
        
        // setDefaultLongTermFeedback 함수 정의
        const setDefaultLongTermFeedback = () => {
          setLongTermFeedback({
            shortTerm: {
              title: "단기 개선 계획 (1-3개월)",
              improvements: [
                {
                  category: "답변 스킬 개선",
                  items: ["STAR 기법 활용", "모의 면접 실시", "자기소개 연습"]
                },
                {
                  category: "의사소통 능력 향상",
                  items: ["언어적 표현 연습", "청중 고려하기"]
                }
              ]
            },
            longTerm: {
              title: "장기 개선 계획 (6-12개월)",
              improvements: [
                {
                  category: "전문성 강화", 
                  items: ["심화 학습", "프로젝트 수행", "멘토링 받기"]
                },
                {
                  category: "실무 역량 개발",
                  items: ["인턴십 참여", "오픈소스 기여"]
                }
              ]
            }
          });
          console.log('🔧 longTermFeedback (기본값) 설정 완료');
        };
        
        // 새로운 API 응답에서 total_feedback 사용
        console.log('🔧 total_feedback:', response.total_feedback);
        
        if (response.total_feedback) {
          try {
            const totalFeedback = typeof response.total_feedback === 'string' 
              ? JSON.parse(response.total_feedback)
              : response.total_feedback;
            
            console.log('🔧 파싱된 total_feedback:', totalFeedback);
            
            // 사용자 피드백 처리
            if (totalFeedback.user) {
              const userScore = totalFeedback.user.overall_score || 0;
              setUserSummary({
                clarity: Math.round(userScore * 0.9),
                structure: Math.round(userScore * 0.95),
                confidence: Math.round(userScore * 0.85),
                overallScore: userScore,
                strengths: ['구체적인 경험 사례', '논리적 답변 구조'],
                weaknesses: ['답변 시간 관리', '핵심 포인트 강조'],
                feedback: totalFeedback.user.overall_feedback || '',
                summary: totalFeedback.user.summary || ''
              });
              console.log('🔧 userSummary (total_feedback 기반) 생성 완료:', userScore);
            }
            
            // AI 지원자 피드백 처리  
            if (totalFeedback.ai_interviewer) {
              const aiScore = totalFeedback.ai_interviewer.overall_score || 0;
              setAiSummary({
                clarity: Math.round(aiScore * 0.9),
                structure: Math.round(aiScore * 0.95),
                confidence: Math.round(aiScore * 0.85),
                overallScore: aiScore,
                strengths: ['논리적 답변 구조', '기술적 깊이'],
                weaknesses: ['구체적 사례 부족', '회사 연관성 부족'],
                feedback: totalFeedback.ai_interviewer.overall_feedback || '',
                summary: totalFeedback.ai_interviewer.summary || ''
              });
              console.log('🔧 aiSummary (total_feedback 기반) 생성 완료:', aiScore);
            }
            
          } catch (error) {
            console.error('🔧 total_feedback 파싱 오류:', error);
            // fallback: history_detail에서 점수 계산
            generateFallbackSummaries();
          }
        } else {
          // fallback: history_detail에서 점수 계산
          generateFallbackSummaries();
        }
        
        console.log('🔧 summary 생성 완료');
        
        // plans 테이블 데이터를 사용하여 장기 피드백 설정 (shortly_plan 컬럼에서만 파싱)
        if (response.plans && response.plans.shortly_plan) {
          try {
            const planData = typeof response.plans.shortly_plan === 'string'
              ? JSON.parse(response.plans.shortly_plan)
              : response.plans.shortly_plan;
            
            console.log('🔧 plans 원본 데이터 (shortly_plan 컬럼):', planData);
            console.log('🔧 planData.user:', planData?.user);
            
            // shortly_plan 컬럼에서 user의 단기/장기 계획 추출
            const userShortPlan = planData?.user?.shortly_plan || {};
            const userLongPlan = planData?.user?.long_plan || {};
            
            console.log('🔧 파싱된 사용자 계획:', { userShortPlan, userLongPlan });
            
            setLongTermFeedback({
              shortTerm: {
                title: "단기 개선 계획 (1-3개월)",
                improvements: Object.entries(userShortPlan).map(([category, items]) => ({
                  category: category.replace(/_/g, ' '),
                  items: Array.isArray(items) ? items : []
                }))
              },
              longTerm: {
                title: "장기 개선 계획 (6-12개월)", 
                improvements: Object.entries(userLongPlan).map(([category, items]) => ({
                  category: category.replace(/_/g, ' '),
                  items: Array.isArray(items) ? items : []
                }))
              }
            });
            
            console.log('🔧 longTermFeedback (plans 기반) 설정 완료');
            
          } catch (error) {
            console.error('🔧 plans 파싱 오류:', error);
            // fallback으로 기본 계획 설정
            setDefaultLongTermFeedback();
          }
        } else {
          // plans 데이터가 없으면 기본 계획 설정
          setDefaultLongTermFeedback();
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
      console.log('🔧 데이터 로딩 완료, isLoading을 false로 설정');
      setIsLoading(false);
    }
  }, [interviewId]);

  // 면접 결과 데이터 로드 함수
  const loadInterviewResults = useCallback(async (interviewId: string) => {
    console.log('🔄 loadInterviewResults 시작:', interviewId);
    setIsLoading(true);
    try {
      // 실제 면접 데이터 로드
      await loadInterviewData();
    } catch (error) {
      console.error('면접 결과 로드 실패:', error);
      // 에러 시 mock 데이터 사용
      setFeedbackData(mockFeedbackData);
      setUserSummary(mockUserSummary);
      setAiSummary(mockAiSummary);
      setLongTermFeedback(mockLongTermFeedback);
      setIsLoading(false);
    }
  }, [loadInterviewData]); // mock 데이터는 의존성에서 제거

  // interview ID가 없으면 기본 결과 페이지로 리다이렉트
  useEffect(() => {
    if (!interviewId) {
      // interview ID가 없는 경우 (직접 접근) - 가라 데이터 사용
      setFeedbackData(mockFeedbackData);
      setUserSummary(mockUserSummary);
      setAiSummary(mockAiSummary);
      setLongTermFeedback(mockLongTermFeedback);
      setIsLoading(false);
    } else {
      // interview ID가 있는 경우 - 실제 데이터 로드
      loadInterviewResults(interviewId);
    }
  }, [interviewId]); // mock 데이터는 의존성에서 제거하여 무한 루프 방지

  // 중복 호출 방지: loadInterviewResults에서 이미 loadInterviewData를 호출함

  // 중복 호출 방지: loadInterviewResults에서 이미 loadInterviewData를 호출함

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
            
            {/* 영상 로딩 상태 */}
            {videoLoading && (
              <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p className="text-sm text-gray-600">영상을 불러오는 중...</p>
                </div>
              </div>
            )}
            
            {/* 영상 에러 상태 */}
            {videoError && !videoLoading && (
              <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center">
                <div className="text-center p-4">
                  <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-sm text-gray-600 mb-2">{videoError}</p>
                  <p className="text-xs text-gray-500">면접 진행 중 녹화에 문제가 있었을 수 있습니다.</p>
                </div>
              </div>
            )}
            
            {/* 실제 비디오 플레이어 */}
            {videoUrl && !videoError && (
              <div className="relative">
                <video 
                  className="w-full aspect-video bg-black rounded-lg"
                  controls
                  preload="metadata"
                  onLoadStart={() => {
                    console.log('🎬 비디오 로딩 시작');
                    setVideoLoading(true);
                  }}
                  onLoadedData={() => {
                    console.log('🎬 비디오 로딩 완료');
                    setVideoLoading(false);
                  }}
                  onCanPlay={() => {
                    console.log('🎬 비디오 재생 준비 완료');
                    setVideoLoading(false);
                  }}
                  onError={(e) => {
                    console.error('🎬 비디오 로딩 에러:', e);
                    setVideoLoading(false);
                    setVideoError('영상을 재생할 수 없습니다. S3 접근 권한을 확인해주세요.');
                  }}
                  onLoadedMetadata={() => {
                    console.log('🎬 비디오 메타데이터 로딩 완료');
                  }}
                >
                  <source src={videoUrl} type="video/webm" />
                  <source src={videoUrl} type="video/mp4" />
                  브라우저가 비디오를 지원하지 않습니다.
                </video>
                
                {/* 영상 메타정보 */}
                {videoMetadata && (
                  <div className="mt-2 text-xs text-gray-500 flex justify-between">
                    <span>
                      {videoMetadata.duration ? `재생시간: ${Math.floor(videoMetadata.duration / 60)}:${String(videoMetadata.duration % 60).padStart(2, '0')}` : ''}
                    </span>
                    <span>
                      {videoMetadata.file_size ? `크기: ${(videoMetadata.file_size / (1024 * 1024)).toFixed(1)}MB` : ''}
                    </span>
                  </div>
                )}
              </div>
            )}
            
            {/* 다운로드 버튼 */}
            <div className="mt-3 flex gap-2">
              {videoUrl ? (
                <a
                  href={videoUrl}
                  download={`interview_${interviewId}_video.webm`}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium text-center"
                >
                  영상 다운로드
                </a>
              ) : (
                <button
                  disabled
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed text-sm font-medium"
                >
                  영상 없음
                </button>
              )}
            </div>
          </div>



          {/* 전체적인 피드백 */}
          {userSummary.feedback && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">전체적인 피드백</h3>
              <div className="prose prose-sm text-gray-700">
                <p>{userSummary.feedback}</p>
              </div>
            </div>
          )}

          {/* 요약 */}
          {userSummary.summary && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">요약</h3>
              <div className="prose prose-sm text-gray-700">
                <p>{userSummary.summary}</p>
              </div>
            </div>
          )}
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
                    평가
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.userEvaluation}
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    보완할점
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.userImprovement}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  내 메모
                </label>
                <div className="flex gap-2">
                  <textarea
                    id={`user-memo-${index}`}
                    className="flex-1 rounded-lg border border-gray-300 bg-white p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                    rows={3}
                    placeholder="개인 메모와 생각을 여기에 추가하세요..."
                    defaultValue={memos[`${index + 1}`]?.user || feedback.userMemo || ''}
                  />
                  <button
                    onClick={() => {
                      const textarea = document.getElementById(`user-memo-${index}`) as HTMLTextAreaElement;
                      if (textarea) {
                        saveMemo(index + 1, 'user', textarea.value);
                      }
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
                  >
                    저장
                  </button>
                </div>
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


          {/* 전체적인 피드백 */}
          {aiSummary.feedback && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">전체적인 피드백</h3>
              <div className="prose prose-sm text-gray-700">
                <p>{aiSummary.feedback}</p>
              </div>
            </div>
          )}

          {/* 요약 */}
          {aiSummary.summary && (
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">요약</h3>
              <div className="prose prose-sm text-gray-700">
                <p>{aiSummary.summary}</p>
              </div>
            </div>
          )}
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
                    평가
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.aiEvaluation}
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    보완할점
                  </label>
                  <div className="rounded-lg border border-gray-300 bg-gray-50 p-4">
                    <p className="text-sm text-gray-900 leading-relaxed">
                      {feedback.aiImprovement}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  내 메모
                </label>
                <div className="flex gap-2">
                  <textarea
                    id={`ai-memo-${index}`}
                    className="flex-1 rounded-lg border border-gray-300 bg-white p-4 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 resize-none"
                    rows={3}
                    placeholder="AI 답변에 대한 개인적인 생각을 여기에 기록하세요..."
                    defaultValue={memos[`${index + 1}`]?.ai || feedback.aiMemo || ''}
                  />
                  <button
                    onClick={() => {
                      const textarea = document.getElementById(`ai-memo-${index}`) as HTMLTextAreaElement;
                      if (textarea) {
                        saveMemo(index + 1, 'ai', textarea.value);
                      }
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
                  >
                    저장
                  </button>
                </div>
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
                {longTermFeedback.shortTerm.improvements[0]?.items.map((action, index) => (
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
                {longTermFeedback.shortTerm.improvements[1]?.items.map((prep, index) => (
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
                {longTermFeedback.shortTerm.improvements[2]?.items.map((improvement, index) => (
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
                {longTermFeedback.longTerm.improvements[0]?.items.map((skill, index) => (
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
                {longTermFeedback.longTerm.improvements[1]?.items.map((experience, index) => (
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
                {longTermFeedback.longTerm.improvements[1]?.items.map((path, index) => (
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

  // 현재 상태 디버깅
  console.log('🔧 렌더링 시점 상태 확인:', {
    isLoading,
    feedbackDataLength: feedbackData.length,
    hasUserSummary: !!userSummary,
    hasAiSummary: !!aiSummary,
    hasLongTermFeedback: !!longTermFeedback,
    longTermFeedbackData: longTermFeedback,
    activeTab
  });

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
            </nav>
          </div>
        </div>

        {/* 탭 컨텐츠 */}
        <div>
          {activeTab === 'user' && renderUserFeedback()}
          {activeTab === 'ai' && renderAiFeedback()}
          {activeTab === 'longterm' && renderLongTermFeedback()}
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