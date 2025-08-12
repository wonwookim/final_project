import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useInterviewHistory } from '../hooks/useInterviewHistory';
import { InterviewSettings } from '../services/api';

interface InterviewRecord {
  session_id: string;
  company: string;
  position: string;
  date: string;
  time: string;
  duration: string;
  score: number;
  mode: string;
  status: string;
  settings: InterviewSettings;
}

const InterviewHistory: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFilter, setSelectedFilter] = useState('all');
  
  // Context에서 면접 기록 데이터 가져오기
  const { interviews, stats, isLoading, error } = useInterviewHistory();

  const statistics = {
    totalInterviews: stats.totalInterviews,
    averageScore: stats.averageScore,
    aiCompetitionCount: stats.aiCompetitionCount,
    recentImprovement: stats.recentImprovement
  };

  const filterOptions = [
    { value: 'all', label: '전체' },
    { value: 'completed', label: '완료' },
    { value: 'ai_competition', label: 'AI 경쟁' },
    { value: 'personalized', label: '개인화' },
    { value: 'standard', label: '표준' }
  ];

  // 필터링된 면접 목록
  const filteredInterviews = interviews.filter(interview => {
    if (selectedFilter === 'all') return true;
    if (selectedFilter === 'completed') return interview.status === '완료';
    return interview.mode === selectedFilter;
  });

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 80) return 'text-blue-600 bg-blue-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getModeColor = (mode: string): string => {
    switch (mode) {
      case 'ai_competition': return 'bg-purple-100 text-purple-800';
      case 'personalized': return 'bg-blue-100 text-blue-800';
      case 'standard': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getModeLabel = (mode: string): string => {
    switch (mode) {
      case 'ai_competition': return 'AI 경쟁';
      case 'personalized': return '개인화';
      case 'standard': return '표준';
      default: return mode;
    }
  };

  const handleViewDetails = (sessionId: string) => {
    // 세션 ID를 사용하여 결과 페이지로 이동
    console.log('🔍 DEBUG - handleViewDetails 호출됨, sessionId:', sessionId);
    console.log('🔍 DEBUG - 이동할 URL:', `/interview/results/${sessionId}`);
    navigate(`/interview/results/${sessionId}`);
  };

  const handleViewFeedback = (sessionId: string) => {
    // 피드백 상세 페이지로 이동
    console.log('🔍 DEBUG - handleViewFeedback 호출됨, sessionId:', sessionId);
    console.log('🔍 DEBUG - 이동할 URL:', `/interview/results/${sessionId}`);
    navigate(`/interview/results/${sessionId}`, { state: { tab: 'longterm' } });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <Header 
          title="면접 기록"
          subtitle="면접 기록을 불러오는 중입니다"
        />
        <main className="flex items-center justify-center min-h-[calc(100vh-80px)]">
          <LoadingSpinner size="lg" message="면접 기록을 불러오는 중..." />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 기록"
        subtitle="지금까지 진행한 면접들의 상세 기록을 확인하고 분석하세요"
        showBackButton
      />
      
      <main className="container mx-auto px-6 py-8">
        <div className="max-w-7xl mx-auto">
          {/* 헤더 섹션 */}
          <div className="mb-8 animate-fadeIn">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">면접 기록</h1>
            <p className="text-slate-600">지금까지 진행한 면접들의 상세 기록을 확인하고 분석하세요.</p>
          </div>
          
          {/* 필터 및 통계 */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-6 mb-8 animate-slideUp">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
              <div className="flex flex-wrap gap-2">
                {filterOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setSelectedFilter(option.value)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      selectedFilter === option.value
                        ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              
              <div className="flex gap-8 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-slate-900">{statistics.totalInterviews}</div>
                  <div className="text-slate-600">총 면접</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{statistics.averageScore}</div>
                  <div className="text-slate-600">평균 점수</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{statistics.aiCompetitionCount}</div>
                  <div className="text-slate-600">AI 경쟁</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">+{statistics.recentImprovement}</div>
                  <div className="text-slate-600">최근 향상</div>
                </div>
              </div>
            </div>
          </div>
          
          {/* 면접 목록 */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 overflow-hidden animate-slideUp" style={{ animationDelay: '0.2s' }}>
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-lg font-bold text-slate-900">
                면접 목록 ({filteredInterviews.length}개)
              </h2>
            </div>
            
            {filteredInterviews.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-slate-400" fill="currentColor" viewBox="0 0 256 256">
                    <path d="M216,40H40A16,16,0,0,0,24,56V200a16,16,0,0,0,16,16H216a16,16,0,0,0,16-16V56A16,16,0,0,0,216,40ZM40,56H216V200H40ZM96,116a12,12,0,1,1-12-12A12,12,0,0,1,96,116Zm40,0a12,12,0,1,1-12-12A12,12,0,0,1,136,116Zm40,0a12,12,0,1,1-12-12A12,12,0,0,1,176,116Z"/>
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-slate-900 mb-2">면접 기록이 없습니다</h3>
                <p className="text-slate-600 mb-6">첫 번째 면접을 시작해보세요!</p>
                <button 
                  onClick={() => navigate('/interview/setup')}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:shadow-lg transition-all"
                >
                  면접 시작하기
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">회사/직무</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">일시</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">소요시간</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">모드</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">점수</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">상태</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">액션</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-200">
                    {filteredInterviews.map((interview, index) => (
                      <tr 
                        key={interview.session_id} 
                        className="hover:bg-slate-50 transition-colors animate-slideUp"
                        style={{ animationDelay: `${index * 0.1}s` }}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-slate-900">{interview.company}</div>
                            <div className="text-sm text-slate-500">{interview.position}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-slate-900">{interview.date}</div>
                          <div className="text-sm text-slate-500">{interview.time}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-slate-900">{interview.duration}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getModeColor(interview.mode)}`}>
                            {getModeLabel(interview.mode)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getScoreColor(interview.score)}`}>
                            {interview.score}점
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {interview.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex gap-3">
                            <button 
                              onClick={() => {
                                console.log('🔴 상세보기 버튼 클릭됨! interview.session_id:', interview.session_id);
                                handleViewDetails(interview.session_id);
                              }}
                              className="text-blue-600 hover:text-blue-700 transition-colors"
                            >
                              상세보기
                            </button>
                            <button 
                              onClick={() => {
                                console.log('🔴 피드백 버튼 클릭됨! interview.session_id:', interview.session_id);
                                handleViewFeedback(interview.session_id);
                              }}
                              className="text-green-600 hover:text-green-700 transition-colors"
                            >
                              피드백
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          
          {/* 새 면접 시작 버튼 */}
          {filteredInterviews.length > 0 && (
            <div className="mt-8 text-center animate-slideUp" style={{ animationDelay: '0.4s' }}>
              <button 
                onClick={() => navigate('/interview/setup')}
                className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:shadow-lg hover:scale-105 transition-all"
              >
                새 면접 시작하기
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default InterviewHistory;