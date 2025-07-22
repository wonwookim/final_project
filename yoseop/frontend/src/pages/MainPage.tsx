import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { interviewApi } from '../services/api';

const MainPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState({
    totalInterviews: 0,
    averageScore: 0,
    lastInterviewDate: null as string | null
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const history = await interviewApi.getInterviewHistory();
      const totalInterviews = history.total_interviews;
      const averageScore = history.interviews.length > 0 
        ? Math.round(history.interviews.reduce((sum, interview) => sum + interview.total_score, 0) / history.interviews.length)
        : 0;
      const lastInterviewDate = history.interviews.length > 0 
        ? history.interviews[0].completed_at
        : null;

      setStats({
        totalInterviews,
        averageScore,
        lastInterviewDate
      });
    } catch (error) {
      console.error('통계 로드 실패:', error);
    }
  };

  const handleStartInterview = () => {
    setIsLoading(true);
    setTimeout(() => {
      navigate('/interview/setup');
    }, 1000);
  };

  const features = [
    {
      icon: "🤖",
      title: "AI 개인화 면접",
      description: "당신의 이력서와 자기소개서를 분석하여 맞춤형 질문을 생성합니다.",
      color: "from-blue-500 to-cyan-500"
    },
    {
      icon: "📊",
      title: "실시간 피드백",
      description: "면접 진행 중 실시간으로 답변을 분석하고 개선점을 제시합니다.",
      color: "from-green-500 to-emerald-500"
    },
    {
      icon: "🎯",
      title: "3명 면접관 시뮬레이션",
      description: "인사, 실무, 협업 담당자 역할의 3명 면접관이 다각도로 평가합니다.",
      color: "from-purple-500 to-pink-500"
    },
    {
      icon: "📈",
      title: "상세한 분석 리포트",
      description: "면접 후 상세한 분석과 개선 방안을 제공하는 리포트를 받아보세요.",
      color: "from-orange-500 to-red-500"
    }
  ];

  const recentCompanies = [
    { name: "네이버", logo: "🔵", color: "bg-green-100" },
    { name: "카카오", logo: "💛", color: "bg-yellow-100" },
    { name: "라인", logo: "💚", color: "bg-green-100" },
    { name: "쿠팡", logo: "🔴", color: "bg-red-100" },
    { name: "배민", logo: "🍴", color: "bg-blue-100" },
    { name: "토스", logo: "💙", color: "bg-blue-100" }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header />
      
      <main className="container mx-auto px-6 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16 animate-fadeIn">
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6">
            AI와 함께하는
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {" "}스마트 면접{" "}
            </span>
            준비
          </h1>
          
          <p className="text-xl text-slate-600 mb-8 max-w-3xl mx-auto">
            개인화된 AI 면접관과 함께 실전같은 면접을 연습하고, 
            상세한 피드백으로 면접 실력을 한 단계 업그레이드하세요.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={handleStartInterview}
              disabled={isLoading}
              className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-full text-lg font-bold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <LoadingSpinner size="sm" color="white" />
                  준비 중...
                </div>
              ) : (
                "면접 시작하기"
              )}
            </button>
            
            <button
              onClick={() => navigate('/demo')}
              className="border-2 border-slate-300 text-slate-700 px-8 py-4 rounded-full text-lg font-bold hover:border-slate-400 hover:bg-slate-50 transition-all"
            >
              데모 체험하기
            </button>
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 text-center">
            <div className="text-3xl font-bold text-blue-600 mb-2">{stats.totalInterviews}</div>
            <div className="text-slate-600">총 면접 횟수</div>
          </div>
          
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 text-center">
            <div className="text-3xl font-bold text-green-600 mb-2">{stats.averageScore}</div>
            <div className="text-slate-600">평균 점수</div>
          </div>
          
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 text-center">
            <div className="text-3xl font-bold text-purple-600 mb-2">
              {stats.lastInterviewDate ? '최근' : '첫'}
            </div>
            <div className="text-slate-600">면접 기록</div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-slate-900 text-center mb-12">
            왜 Beta-GO Interview를 선택해야 할까요?
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 hover:shadow-lg transition-all duration-300"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className={`w-16 h-16 rounded-full bg-gradient-to-r ${feature.color} flex items-center justify-center text-2xl mb-4`}>
                  {feature.icon}
                </div>
                
                <h3 className="text-lg font-bold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                
                <p className="text-slate-600 text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Companies Section */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-slate-900 text-center mb-8">
            다양한 기업 면접을 연습하세요
          </h2>
          
          <div className="flex flex-wrap justify-center gap-4">
            {recentCompanies.map((company, index) => (
              <div
                key={index}
                className={`${company.color} rounded-full px-6 py-3 flex items-center gap-2 hover:scale-105 transition-transform cursor-pointer`}
              >
                <span className="text-2xl">{company.logo}</span>
                <span className="font-medium text-slate-800">{company.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">
            지금 바로 시작해보세요!
          </h2>
          
          <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
            5분만 투자하면 당신만의 맞춤형 면접 연습을 시작할 수 있습니다. 
            AI가 실시간으로 분석하고 피드백을 제공합니다.
          </p>
          
          <button
            onClick={handleStartInterview}
            disabled={isLoading}
            className="bg-white text-blue-600 px-8 py-4 rounded-full text-lg font-bold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" color="primary" />
                준비 중...
              </div>
            ) : (
              "무료로 시작하기"
            )}
          </button>
        </div>
      </main>
    </div>
  );
};

export default MainPage;