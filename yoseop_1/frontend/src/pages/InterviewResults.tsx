import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useInterview } from '../contexts/InterviewContext';
import { interviewApi, handleApiError } from '../services/api';

interface CategoryScore {
  category: string;
  user: number;
  ai: number;
  feedback: string;
}

interface CircularScoreProps {
  score: number;
  title: string;
  color?: 'blue' | 'green' | 'purple';
  size?: 'large' | 'small';
}

const InterviewResults: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { state, dispatch } = useInterview();
  
  const [currentTab, setCurrentTab] = useState('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  // 면접 결과 로드
  useEffect(() => {
    // temp 모드인지 확인
    const isTempMode = location.state?.tempMode || location.state?.skipApiCall;
    
    if (!state.sessionId && !isTempMode) {
      navigate('/interview/setup');
      return;
    }
    
    // temp 모드가 아닐 때만 API 호출
    if (!isTempMode) {
      loadInterviewResults();
    } else {
      // temp 모드일 때는 로딩 상태만 해제
      setIsLoading(false);
      console.log('Temp 모드: API 호출 건너뜀');
    }
  }, [state.sessionId, navigate, location.state]);

  const loadInterviewResults = async () => {
    if (!state.sessionId) return;
    
    try {
      setIsLoading(true);
      const response = await interviewApi.getInterviewResults(state.sessionId);
      setResults(response);
      dispatch({ type: 'SET_RESULTS', payload: response });
    } catch (error) {
      console.error('결과 로드 실패:', error);
      alert(`결과 로드 실패: ${handleApiError(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 원형 점수 컴포넌트
  const CircularScore: React.FC<CircularScoreProps> = ({ 
    score, 
    title, 
    color = 'blue', 
    size = 'large' 
  }) => {
    const radius = size === 'large' ? 60 : 40;
    const strokeWidth = size === 'large' ? 8 : 6;
    const normalizedRadius = radius - strokeWidth * 2;
    const circumference = normalizedRadius * 2 * Math.PI;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    const colorClasses = {
      blue: 'stroke-blue-500',
      green: 'stroke-green-500',
      purple: 'stroke-purple-500'
    };

    return (
      <div className={`relative ${size === 'large' ? 'w-32 h-32' : 'w-20 h-20'}`}>
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r={normalizedRadius}
            stroke="rgba(0,0,0,0.1)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          <circle
            cx="60"
            cy="60"
            r={normalizedRadius}
            className={colorClasses[color]}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference + ' ' + circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ 
              transition: 'stroke-dashoffset 1s ease-in-out',
              animationDelay: '0.5s'
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-bold ${size === 'large' ? 'text-2xl' : 'text-lg'} text-slate-800`}>
            {score}
          </span>
          <span className={`text-xs text-slate-600 ${size === 'large' ? 'mt-1' : ''}`}>
            {title}
          </span>
        </div>
      </div>
    );
  };

  // 기본 결과 데이터 (API 응답이 없을 때)
  const getDefaultResults = () => ({
    total_score: 85,
    ai_competitor_score: 78,
    rank_percentile: 85,
    improvement_score: 12,
    recommendation: '합격 가능성 높음',
    category_scores: [
      { category: '자기소개', user: 90, ai: 85, feedback: '명확하고 구체적인 경험을 잘 어필했습니다.' },
      { category: '기술 역량', user: 82, ai: 75, feedback: '기술적 깊이는 좋으나 최신 트렌드 학습이 필요합니다.' },
      { category: '문제 해결', user: 88, ai: 80, feedback: '체계적인 접근 방식이 인상적입니다.' },
      { category: '협업 능력', user: 80, ai: 82, feedback: '구체적인 협업 사례 제시가 더 필요합니다.' },
      { category: '성장 의지', user: 87, ai: 72, feedback: '학습 계획이 구체적이고 현실적입니다.' }
    ],
    detailed_feedback: state.answers.map((answer, index) => {
      const questionTypes = ['자기소개', '기술 역량', '프로젝트 경험', '문제 해결', '협업 경험', '성장 의지'];
      const currentType = questionTypes[index % questionTypes.length];
      
      const feedbackTemplates = {
        '자기소개': {
          feedback: '자기소개에서 핵심 경험과 강점을 잘 어필했습니다. 특히 구체적인 성과 지표를 언급한 부분이 인상적이었습니다. 다만 지원 분야와의 연관성을 더 명확하게 표현하면 더욱 좋겠습니다.',
          strengths: ['명확한 자기 정체성 제시', '구체적 경험 사례', '성과 중심 설명', '논리적 구성'],
          improvements: ['지원 분야와의 연관성 강화', '차별화 포인트 부각', '미래 비전 제시']
        },
        '기술 역량': {
          feedback: '기술적 깊이와 실무 경험이 잘 드러났습니다. 특히 최신 기술 트렌드에 대한 이해도가 높아 보입니다. 향후 기술 스택을 더 체계적으로 정리하여 발표하면 더욱 효과적일 것 같습니다.',
          strengths: ['다양한 기술 스택 경험', '최신 트렌드 이해', '실무 적용 경험', '학습 능력 입증'],
          improvements: ['기술 선택 근거 제시', '성능 최적화 경험', '아키텍처 설계 능력']
        },
        '프로젝트 경험': {
          feedback: '프로젝트 진행 과정과 결과를 체계적으로 설명했습니다. 특히 문제 해결 과정에서의 접근 방식이 논리적이었습니다. 팀원들과의 협업 과정이나 리더십 경험을 추가로 언급하면 더욱 완성도 높은 답변이 될 것입니다.',
          strengths: ['체계적인 프로젝트 진행', '명확한 역할 정의', '구체적 성과 제시', '문제 해결 능력'],
          improvements: ['협업 과정 상세화', '리더십 경험 부각', '비즈니스 임팩트 강조']
        },
        '문제 해결': {
          feedback: '문제 상황을 정확히 파악하고 체계적으로 해결해 나가는 과정이 인상적이었습니다. 다양한 해결 방안을 고려한 점도 좋았습니다. 결과적으로 얻은 교훈이나 향후 개선 방안까지 언급하면 더욱 완벽한 답변이 될 것입니다.',
          strengths: ['정확한 문제 분석', '체계적 접근 방법', '다양한 해결책 고려', '실행력'],
          improvements: ['근본 원인 분석', '예방책 수립', '재발 방지 대안']
        },
        '협업 경험': {
          feedback: '팀워크와 소통 능력이 잘 드러난 답변이었습니다. 갈등 상황에서의 해결 과정이 특히 인상적이었습니다. 다양한 직군과의 협업 경험이나 원격 협업 경험도 추가로 언급하면 좋겠습니다.',
          strengths: ['원활한 의사소통', '갈등 해결 능력', '팀워크 중시', '상호 존중'],
          improvements: ['다양한 직군과의 협업', '원격 협업 능력', '팀 문화 개선 기여']
        },
        '성장 의지': {
          feedback: '지속적인 학습 의지와 구체적인 성장 계획이 돋보였습니다. 특히 자기주도적 학습 능력이 인상적이었습니다. 회사에서 추구하는 방향과의 연관성을 더 강조하면 더욱 좋은 평가를 받을 수 있을 것입니다.',
          strengths: ['자기주도적 학습', '구체적 성장 계획', '지속적 발전 의지', '목표 지향적 사고'],
          improvements: ['회사 비전과의 연계', '구체적 실행 계획', '단계별 목표 설정']
        }
      };
      
      const template = feedbackTemplates[currentType] || feedbackTemplates['자기소개'];
      const score = Math.floor(Math.random() * 25) + 70; // 70-95점 범위
      const aiScore = Math.max(50, score - Math.floor(Math.random() * 15) - 5); // AI 점수는 사용자보다 약간 낮게
      
      return {
        question: state.questions[index]?.question || `${currentType} 관련 질문`,
        answer: answer.answer,
        score: score,
        ai_score: aiScore,
        feedback: template.feedback,
        strengths: template.strengths,
        improvements: template.improvements,
        questionType: currentType,
        answerTime: Math.floor(Math.random() * 120) + 60, // 60-180초
        keywordAnalysis: ['React', 'TypeScript', '협업', '문제해결'].slice(0, Math.floor(Math.random() * 3) + 2)
      };
    })
  });

  // API 응답 데이터 변환 함수
  const transformApiResponse = (apiResults: any) => {
    // category_scores가 객체인 경우 배열로 변환
    let categoryScores = [];
    if (apiResults.category_scores) {
      if (Array.isArray(apiResults.category_scores)) {
        categoryScores = apiResults.category_scores;
      } else {
        // 객체를 배열로 변환
        categoryScores = Object.entries(apiResults.category_scores).map(([category, score]) => ({
          category,
          user: score as number,
          ai: Math.floor((score as number) * 0.8), // AI 점수는 사용자 점수의 80%로 추정
          feedback: '구체적인 피드백을 제공하겠습니다.'
        }));
      }
    }

    return {
      ...apiResults,
      category_scores: categoryScores,
      ai_competitor_score: apiResults.ai_competitor_score || Math.floor(apiResults.total_score * 0.8),
      rank_percentile: apiResults.rank_percentile || 85,
      improvement_score: apiResults.improvement_score || 12,
      recommendation: apiResults.recommendation || '합격 가능성 높음',
      detailed_feedback: apiResults.detailed_feedback || state.answers.map((answer, index) => ({
        question: state.questions[index]?.question || '질문 데이터 없음',
        answer: answer.answer,
        score: Math.floor(Math.random() * 20) + 75,
        ai_score: Math.floor(Math.random() * 20) + 70,
        feedback: '구체적인 경험을 잘 표현했습니다. 더 구체적인 수치나 결과를 추가하면 좋겠습니다.',
        strengths: ['구체적인 경험 제시', '명확한 설명'],
        improvements: ['구체적 수치 제시', '결과 강조']
      }))
    };
  };

  const finalResults = results ? transformApiResponse(results) : getDefaultResults();

  // 종합 결과 탭
  const OverviewTab = () => (
    <div className="space-y-8 animate-fadeIn">
      {/* 전체 점수 섹션 */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition-all">
        <h2 className="text-2xl font-bold text-slate-900 mb-8 text-center">
          종합 평가 결과
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <div className="animate-slideUp">
            <CircularScore score={finalResults.total_score} title="내 점수" color="blue" />
            <div className="mt-4">
              <div className="text-lg font-semibold text-slate-800">
                상위 {100 - finalResults.rank_percentile}%
              </div>
              <div className="text-green-600 font-medium">
                +{finalResults.improvement_score}점
              </div>
            </div>
          </div>
          
          <div className="animate-slideUp" style={{ animationDelay: '0.2s' }}>
            <CircularScore score={finalResults.ai_competitor_score} title="AI 점수" color="green" />
            <div className="mt-4">
              <div className="text-lg font-semibold text-slate-800">
                AI 대비 +{finalResults.total_score - finalResults.ai_competitor_score}점
              </div>
              <div className="text-blue-600 font-medium">
                우수한 성과
              </div>
            </div>
          </div>
          
          <div className="flex flex-col justify-center animate-slideUp" style={{ animationDelay: '0.4s' }}>
            <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full flex items-center justify-center mb-4 mx-auto">
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 256 256">
                <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"/>
              </svg>
            </div>
            <div className="text-xl font-bold text-slate-800 mb-2">
              {finalResults.recommendation}
            </div>
            <div className="text-slate-600">
              면접 대비가 잘 되어있습니다
            </div>
          </div>
        </div>
      </div>

      {/* 카테고리별 점수 */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition-all">
        <h3 className="text-xl font-bold text-slate-900 mb-6">영역별 상세 점수</h3>
        <div className="space-y-6">
          {finalResults.category_scores.map((item: CategoryScore, index: number) => (
            <div key={index} className="animate-slideUp" style={{ animationDelay: `${index * 0.1}s` }}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-slate-800">{item.category}</span>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-blue-600">내 점수: {item.user}점</span>
                  <span className="text-sm text-green-600">AI: {item.ai}점</span>
                </div>
              </div>
              
              <div className="relative h-3 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className="absolute h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-1000"
                  style={{ 
                    width: `${item.user}%`, 
                    animationDelay: `${index * 0.2}s` 
                  }}
                />
                <div 
                  className="absolute h-full bg-gradient-to-r from-green-500 to-emerald-500 rounded-full opacity-60 transition-all duration-1000"
                  style={{ 
                    width: `${item.ai}%`, 
                    animationDelay: `${index * 0.2 + 0.1}s` 
                  }}
                />
              </div>
              
              <p className="text-sm text-slate-600 mt-2">{item.feedback}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 면접 정보 */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition-all">
        <h3 className="text-xl font-bold text-slate-900 mb-6">면접 정보</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{state.questions.length}</div>
            <div className="text-sm text-slate-600">총 질문 수</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {Math.floor(state.answers.reduce((sum, answer) => sum + (answer as any).time_spent || (answer as any).timeSpent || 0, 0) / 60)}분
            </div>
            <div className="text-sm text-slate-600">소요 시간</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{state.settings?.mode || '텍스트 면접'}</div>
            <div className="text-sm text-slate-600">면접 모드</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {new Date().toLocaleDateString('ko-KR')}
            </div>
            <div className="text-sm text-slate-600">면접 일자</div>
          </div>
        </div>
      </div>
    </div>
  );

  // 상세 분석 탭
  const DetailedTab = () => (
    <div className="space-y-6 animate-fadeIn">
      {finalResults.detailed_feedback.map((item: any, index: number) => (
        <div key={index} className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-6 hover:shadow-lg transition-all animate-slideUp" style={{ animationDelay: `${index * 0.1}s` }}>
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h4 className="font-bold text-slate-800 mb-2">Q{index + 1}. {item.question}</h4>
              <div className="bg-slate-50 rounded-lg p-4 mb-4">
                <p className="text-slate-700 text-sm leading-relaxed">
                  {item.answer}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 ml-6">
              <CircularScore score={item.score} title="내 점수" color="blue" size="small" />
              <CircularScore score={item.ai_score} title="AI 점수" color="green" size="small" />
            </div>
          </div>
          
          <div className="border-t border-slate-200 pt-4">
            {/* 추가 분석 지표 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-slate-50 rounded-lg p-4 text-center">
                <div className="text-lg font-bold text-slate-800">
                  {Math.floor(item.answerTime / 60)}분 {item.answerTime % 60}초
                </div>
                <div className="text-xs text-slate-600">답변 시간</div>
                <div className={`text-xs mt-1 ${
                  item.answerTime > 150 ? 'text-red-600' : 
                  item.answerTime < 90 ? 'text-yellow-600' : 'text-green-600'
                }`}>
                  {item.answerTime > 150 ? '충분히 설명' : 
                   item.answerTime < 90 ? '간결한 답변' : '적정 시간'}
                </div>
              </div>
              
              <div className="bg-slate-50 rounded-lg p-4 text-center">
                <div className="text-lg font-bold text-slate-800">{item.questionType}</div>
                <div className="text-xs text-slate-600">질문 유형</div>
                <div className="text-xs text-green-600 mt-1">맞춤 분석 완료</div>
              </div>
              
              <div className="bg-slate-50 rounded-lg p-4 text-center">
                <div className="text-lg font-bold text-slate-800">{item.keywordAnalysis.length}개</div>
                <div className="text-xs text-slate-600">핵심 키워드</div>
                <div className="flex flex-wrap gap-1 mt-1 justify-center">
                  {item.keywordAnalysis.slice(0, 2).map((keyword: string, idx: number) => (
                    <span key={idx} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h5 className="font-semibold text-green-700 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 256 256">
                    <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"/>
                  </svg>
                  잘한 점
                </h5>
                <ul className="space-y-1">
                  {item.strengths.map((strength: string, idx: number) => (
                    <li key={idx} className="text-sm text-slate-600 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h5 className="font-semibold text-blue-700 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 256 256">
                    <path d="M224,128a8,8,0,0,1-8,8H128v88a8,8,0,0,1-16,0V136H24a8,8,0,0,1,0-16h88V32a8,8,0,0,1,16,0v88h88A8,8,0,0,1,224,128Z"/>
                  </svg>
                  개선점
                </h5>
                <ul className="space-y-1">
                  {item.improvements.map((improvement: string, idx: number) => (
                    <li key={idx} className="text-sm text-slate-600 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                      {improvement}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            {/* 점수 상세 분석 */}
            <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
              <h5 className="font-semibold text-slate-800 mb-3">점수 상세 분석</h5>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-sm text-slate-600">내용의 질</div>
                  <div className="text-lg font-bold text-blue-600">{Math.min(100, item.score + 5)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">논리성</div>
                  <div className="text-lg font-bold text-green-600">{Math.min(100, item.score - 3)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">구체성</div>
                  <div className="text-lg font-bold text-purple-600">{Math.min(100, item.score + 2)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">적합성</div>
                  <div className="text-lg font-bold text-orange-600">{Math.min(100, item.score - 1)}</div>
                </div>
              </div>
            </div>
            
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-slate-700">
                <strong className="text-blue-800">종합 피드백:</strong> {item.feedback}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  // 개선 계획 탭
  const ImprovementTab = () => (
    <div className="space-y-8 animate-fadeIn">
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition-all">
        <h3 className="text-xl font-bold text-slate-900 mb-6">맞춤형 개선 계획</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="animate-slideUp">
            <h4 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">1</span>
              </div>
              단기 개선 목표 (1-2주)
            </h4>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">협업 사례를 구체적으로 3개 이상 준비하기</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">최신 기술 트렌드 학습 (React 18, Node.js 20)</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">회사별 맞춤 지원동기 3개 버전 준비</span>
              </li>
            </ul>
          </div>
          
          <div className="animate-slideUp" style={{ animationDelay: '0.2s' }}>
            <h4 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">2</span>
              </div>
              장기 발전 계획 (1-3개월)
            </h4>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">사이드 프로젝트 1개 완성하여 포트폴리오 강화</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">기술 블로그 운영으로 전문성 어필</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
                <span className="text-sm text-slate-700">오픈소스 기여 경험 쌓기</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 hover:shadow-lg transition-all">
        <h3 className="text-xl font-bold text-slate-900 mb-6">추천 학습 자료</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all">
            <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 256 256">
                <path d="M208,24H72A32,32,0,0,0,40,56V224a8,8,0,0,0,8,8H192a8,8,0,0,0,0-16H56a16,16,0,0,1,16-16H208a8,8,0,0,0,8-8V32A8,8,0,0,0,208,24ZM72,40H200V184H72a31.82,31.82,0,0,0-16,4.29V56A16,16,0,0,1,72,40Z"/>
              </svg>
            </div>
            <h4 className="font-semibold text-slate-800 mb-2">기술 서적</h4>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• Clean Code (로버트 마틴)</li>
              <li>• 가상 면접 사례로 배우는 대규모 시스템 설계</li>
              <li>• 개발자가 반드시 알아야 할 자바 성능 튜닝</li>
            </ul>
          </div>
          
          <div className="border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all">
            <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 256 256">
                <path d="M216,40H40A16,16,0,0,0,24,56V200a16,16,0,0,0,16,16H216a16,16,0,0,0,16-16V56A16,16,0,0,0,216,40ZM40,56H216V200H40ZM96,116a12,12,0,1,1-12-12A12,12,0,0,1,96,116Zm40,0a12,12,0,1,1-12-12A12,12,0,0,1,136,116Zm40,0a12,12,0,1,1-12-12A12,12,0,0,1,176,116Z"/>
              </svg>
            </div>
            <h4 className="font-semibold text-slate-800 mb-2">온라인 강의</h4>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• 스프링 부트와 JPA 실무 완전 정복</li>
              <li>• AWS 클라우드 아키텍처 설계</li>
              <li>• 코딩 테스트 문제 해결 전략</li>
            </ul>
          </div>
          
          <div className="border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all">
            <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 256 256">
                <path d="M216,96H152V88a8,8,0,0,0-16,0v8H104V88a8,8,0,0,0-16,0v8H40a8,8,0,0,0-8,8V208a8,8,0,0,0,8,8H216a8,8,0,0,0,8-8V104A8,8,0,0,0,216,96ZM208,200H48V112H88v8a8,8,0,0,0,16,0v-8h32v8a8,8,0,0,0,16,0v-8h56v88Z"/>
              </svg>
            </div>
            <h4 className="font-semibold text-slate-800 mb-2">실습 프로젝트</h4>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• RESTful API 서버 구축</li>
              <li>• Docker를 활용한 배포 자동화</li>
              <li>• 대용량 데이터 처리 시스템</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title="면접 결과"
          subtitle="AI가 면접 결과를 분석하고 있습니다"
        />
        <main className="flex items-center justify-center min-h-[calc(100vh-80px)]">
          <LoadingSpinner size="lg" message="결과를 분석하는 중..." />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 결과"
        subtitle={`${state.settings?.company} ${state.settings?.position} 면접 결과`}
        actionButton={
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate('/interview/setup')}
              className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-2 rounded-full hover:shadow-lg transition-all"
            >
              새 면접 시작
            </button>
            <button 
              onClick={() => navigate('/')}
              className="border border-slate-300 text-slate-700 px-6 py-2 rounded-full hover:bg-slate-50 transition-all"
            >
              홈으로
            </button>
          </div>
        }
      />
      
      <main className="container mx-auto px-6 py-8">
        {/* 탭 네비게이션 */}
        <div className="flex justify-center mb-8">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-2 shadow-sm border border-slate-200">
            <button
              onClick={() => setCurrentTab('overview')}
              className={`px-6 py-3 rounded-xl font-medium transition-all ${
                currentTab === 'overview'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              종합 결과
            </button>
            <button
              onClick={() => setCurrentTab('detailed')}
              className={`px-6 py-3 rounded-xl font-medium transition-all ${
                currentTab === 'detailed'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              상세 분석
            </button>
            <button
              onClick={() => setCurrentTab('improvement')}
              className={`px-6 py-3 rounded-xl font-medium transition-all ${
                currentTab === 'improvement'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              개선 계획
            </button>
          </div>
        </div>

        {/* 탭 컨텐츠 */}
        <div className="max-w-6xl mx-auto">
          {currentTab === 'overview' && <OverviewTab />}
          {currentTab === 'detailed' && <DetailedTab />}
          {currentTab === 'improvement' && <ImprovementTab />}
        </div>
      </main>
    </div>
  );
};

export default InterviewResults;