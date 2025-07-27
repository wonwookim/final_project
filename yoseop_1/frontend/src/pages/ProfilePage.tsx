import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';

interface InterviewRecord {
  id: string;
  company: string;
  position: string;
  date: string;
  score: number;
  status: 'completed' | 'in_progress' | 'failed';
}

interface UserResume {
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

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('resume');
  const [currentView, setCurrentView] = useState<'list' | 'create' | 'edit'>('list');
  const [isLoading, setIsLoading] = useState(false);
  const [editingResumeId, setEditingResumeId] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState({
    name: '김개발',
    email: 'kim@example.com',
    profileImage: null as string | null
  });

  const [interviewHistory, setInterviewHistory] = useState<InterviewRecord[]>([
    {
      id: '1',
      company: '네이버',
      position: '프론트엔드 개발자',
      date: '2025-07-20',
      score: 87,
      status: 'completed'
    },
    {
      id: '2', 
      company: '카카오',
      position: '백엔드 개발자',
      date: '2025-07-18',
      score: 92,
      status: 'completed'
    },
    {
      id: '3',
      company: '라인',
      position: '풀스택 개발자', 
      date: '2025-07-15',
      score: 78,
      status: 'completed'
    }
  ]);

  const [resumeList, setResumeList] = useState<UserResume[]>([]);

  const [currentResume, setCurrentResume] = useState<UserResume>({
    id: '',
    name: '김개발',
    email: 'kim@example.com',
    phone: '010-1234-5678',
    academic_record: '',
    career: '',
    tech: '',
    activities: '',
    certificate: '',
    awards: '',
    created_at: '',
    updated_at: ''
  });

  const sidebarMenus = [
    { id: 'resume', label: '이력서 관리', icon: '📄', color: 'text-blue-600' },
    { id: 'interview-history', label: '면접 히스토리', icon: '📊', color: 'text-purple-600' },
    { id: 'personal-info', label: '개인정보 관리', icon: '👤', color: 'text-orange-600' }
  ];

  // 이력서 관련 유틸리티 함수들
  const calculateCompletionRate = (resume: UserResume): number => {
    // 이메일, 전화번호 제외하고 필수 필드만 체크
    const fields = ['name', 'academic_record', 'career', 'tech'];
    const filledFields = fields.filter(field => resume[field as keyof UserResume]?.toString().trim());
    return Math.round((filledFields.length / fields.length) * 100);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  // 이력서 네비게이션 함수들
  const handleCreateResume = () => {
    setCurrentResume({
      id: '',
      name: userInfo.name,
      email: userInfo.email,
      phone: '',
      academic_record: '',
      career: '',
      tech: '',
      activities: '',
      certificate: '',
      awards: '',
      created_at: '',
      updated_at: ''
    });
    setCurrentView('create');
  };

  const handleEditResume = (resume: UserResume) => {
    setCurrentResume(resume);
    setEditingResumeId(resume.id);
    setCurrentView('edit');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setEditingResumeId(null);
  };

  const handleResumeUpdate = (field: keyof UserResume, value: string) => {
    setCurrentResume(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleResumeSave = async () => {
    setIsLoading(true);
    try {
      const now = new Date().toISOString().split('T')[0];
      
      if (currentView === 'create') {
        // 새 이력서 생성
        const newResume: UserResume = {
          ...currentResume,
          id: Date.now().toString(),
          created_at: now,
          updated_at: now
        };
        setResumeList(prev => [...prev, newResume]);
        alert('이력서가 생성되었습니다.');
      } else if (currentView === 'edit') {
        // 기존 이력서 수정
        const updatedResume: UserResume = {
          ...currentResume,
          updated_at: now
        };
        setResumeList(prev => prev.map(resume => 
          resume.id === editingResumeId ? updatedResume : resume
        ));
        alert('이력서가 수정되었습니다.');
      }
      
      // TODO: user_resume 테이블에 저장하는 API 호출
      console.log('이력서 저장:', currentResume);
      
      handleBackToList();
    } catch (error) {
      console.error('이력서 저장 실패:', error);
      alert('이력서 저장에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteResume = (resumeId: string) => {
    if (window.confirm('정말로 이 이력서를 삭제하시겠습니까?')) {
      setResumeList(prev => prev.filter(resume => resume.id !== resumeId));
      alert('이력서가 삭제되었습니다.');
    }
  };

  const handleCopyResume = (resume: UserResume) => {
    const copiedResume: UserResume = {
      ...resume,
      id: Date.now().toString(),
      name: `${resume.name} (복사본)`,
      created_at: new Date().toISOString().split('T')[0],
      updated_at: new Date().toISOString().split('T')[0]
    };
    setResumeList(prev => [...prev, copiedResume]);
    alert('이력서가 복사되었습니다.');
  };

  const handleUserInfoUpdate = (field: string, value: string) => {
    setUserInfo(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 80) return 'text-blue-600 bg-blue-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'completed':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">완료</span>;
      case 'in_progress':
        return <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">진행중</span>;
      case 'failed':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">실패</span>;
      default:
        return null;
    }
  };

  const renderContent = () => {
    switch(activeTab) {
      case 'resume':
        if (currentView === 'list') {
          return (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-slate-900">이력서 관리</h2>
                {resumeList.length > 0 && (
                  <button
                    onClick={handleCreateResume}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    ➕ 새 이력서 만들기
                  </button>
                )}
              </div>

              {resumeList.length === 0 ? (
                // 빈 상태
                <div className="text-center py-16">
                  <div className="text-8xl mb-6">📄</div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">첫 이력서를 만들어보세요!</h3>
                  <p className="text-slate-600 mb-6">AI 맞춤형 면접을 위한 이력서를 작성해주세요</p>
                  <button
                    onClick={handleCreateResume}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
                  >
                    📝 이력서 만들기
                  </button>
                </div>
              ) : (
                // 이력서 목록
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {resumeList.map(resume => {
                    const completionRate = calculateCompletionRate(resume);
                    return (
                      <div key={resume.id} className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-all duration-300 hover:border-blue-300">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="font-semibold text-slate-900 truncate">{resume.name}_이력서</h3>
                          <span className="text-xs text-slate-500">{formatDate(resume.updated_at)}</span>
                        </div>
                        
                        <div className="mb-4">
                          <div className="text-sm text-slate-600 mb-2 flex items-center justify-between">
                            <span>작성 완료도</span>
                            <span className="font-medium">{completionRate}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full transition-all duration-500 ${
                                completionRate === 100 ? 'bg-green-500' : 
                                completionRate >= 75 ? 'bg-blue-500' : 
                                completionRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{width: `${completionRate}%`}}
                            />
                          </div>
                        </div>
                        
                        <div className="text-sm text-slate-600 mb-4 space-y-1">
                          <div className="flex items-center gap-2">
                            <span>🎓</span>
                            <span className="truncate">{resume.academic_record || '학력 미입력'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span>💻</span>
                            <span className="truncate">{resume.tech || '기술스택 미입력'}</span>
                          </div>
                        </div>
                        
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEditResume(resume)}
                            className="flex-1 bg-blue-50 text-blue-600 py-2 px-3 rounded text-sm font-medium hover:bg-blue-100 transition-colors"
                          >
                            ✏️ 수정
                          </button>
                          <button
                            onClick={() => handleCopyResume(resume)}
                            className="flex-1 bg-green-50 text-green-600 py-2 px-3 rounded text-sm font-medium hover:bg-green-100 transition-colors"
                          >
                            📋 복사
                          </button>
                          <button
                            onClick={() => handleDeleteResume(resume.id)}
                            className="flex-1 bg-red-50 text-red-600 py-2 px-3 rounded text-sm font-medium hover:bg-red-100 transition-colors"
                          >
                            🗑️ 삭제
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        } else if (currentView === 'create' || currentView === 'edit') {
          return (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <button
                  onClick={handleBackToList}
                  className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                >
                  ←
                </button>
                <h2 className="text-2xl font-bold text-slate-900">
                  {currentView === 'create' ? '이력서 작성' : '이력서 수정'}
                </h2>
                <div className="flex-1" />
                <button
                  onClick={handleResumeSave}
                  disabled={isLoading}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <LoadingSpinner size="sm" color="white" />
                      저장 중...
                    </div>
                  ) : (
                    '💾 저장하기'
                  )}
                </button>
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-6">
                {/* 기본 정보 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    👤 기본 정보
                  </h3>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">이름 *</label>
                    <input
                      type="text"
                      value={currentResume.name}
                      onChange={(e) => handleResumeUpdate('name', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="이름을 입력하세요"
                    />
                  </div>
                </div>

                {/* 학력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🎓 학력 *
                  </h3>
                  <textarea
                    value={currentResume.academic_record}
                    onChange={(e) => handleResumeUpdate('academic_record', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 2020년 서울대학교 컴퓨터공학과 졸업 (학점: 3.8/4.5)"
                  />
                </div>

                {/* 경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💼 경력 *
                  </h3>
                  <textarea
                    value={currentResume.career}
                    onChange={(e) => handleResumeUpdate('career', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-32"
                    placeholder="예: 2021-2023 네이버 - 프론트엔드 개발자&#10;• React 기반 웹 서비스 개발&#10;• 사용자 경험 개선으로 전환율 20% 향상"
                  />
                </div>

                {/* 기술스택 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    💻 기술스택 *
                  </h3>
                  <textarea
                    value={currentResume.tech}
                    onChange={(e) => handleResumeUpdate('tech', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: JavaScript, React, TypeScript, Node.js, Python, Docker"
                  />
                </div>

                {/* 활동/경험 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🚀 활동/경험
                  </h3>
                  <textarea
                    value={currentResume.activities}
                    onChange={(e) => handleResumeUpdate('activities', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-32"
                    placeholder="예: 오픈소스 프로젝트 기여, 개발 동아리 활동, 사이드 프로젝트 등"
                  />
                </div>

                {/* 자격증 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🏆 자격증
                  </h3>
                  <textarea
                    value={currentResume.certificate}
                    onChange={(e) => handleResumeUpdate('certificate', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 정보처리기사 (2021.05), AWS SAA (2022.03)"
                  />
                </div>

                {/* 수상경력 */}
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    🥇 수상경력
                  </h3>
                  <textarea
                    value={currentResume.awards}
                    onChange={(e) => handleResumeUpdate('awards', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-24"
                    placeholder="예: 2022 해커톤 대상, 2021 프로그래밍 경진대회 우수상"
                  />
                </div>
              </div>

              <div className="text-sm text-slate-500 text-center">
                * 표시된 항목은 필수 입력 사항입니다.
              </div>
            </div>
          );
        }
        break;


      case 'interview-history':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-slate-900">면접 히스토리</h2>
              <button 
                onClick={() => navigate('/interview/job-posting')}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
              >
                🚀 새 면접 시작
              </button>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">면접 통계</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{interviewHistory.length}</div>
                  <div className="text-sm text-slate-600">총 면접 횟수</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {Math.round(interviewHistory.reduce((sum, interview) => sum + interview.score, 0) / interviewHistory.length)}
                  </div>
                  <div className="text-sm text-slate-600">평균 점수</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {interviewHistory.filter(interview => interview.score >= 80).length}
                  </div>
                  <div className="text-sm text-slate-600">80점 이상</div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {interviewHistory.map(interview => (
                <div key={interview.id} className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold">
                        {interview.company.charAt(0)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">{interview.company}</h3>
                        <p className="text-slate-600">{interview.position}</p>
                        <p className="text-sm text-slate-500">{interview.date}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(interview.score)}`}>
                        {interview.score}점
                      </div>
                      {getStatusBadge(interview.status)}
                      <button 
                        onClick={() => navigate('/interview/results', { 
                          state: { 
                            interviewId: interview.id,
                            skipApiCall: true 
                          }
                        })}
                        className="text-blue-600 hover:text-blue-700 px-3 py-1 rounded text-sm"
                      >
                        결과 보기
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'personal-info':
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">개인정보 관리</h2>
            
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <div className="flex items-center space-x-6 mb-6">
                <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center">
                  {userInfo.profileImage ? (
                    <img src={userInfo.profileImage} alt="프로필" className="w-20 h-20 rounded-full object-cover" />
                  ) : (
                    <span className="text-gray-500 text-2xl">👤</span>
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{userInfo.name}</h3>
                  <p className="text-slate-600">{userInfo.email}</p>
                  <button className="text-blue-600 hover:text-blue-700 text-sm mt-1">
                    프로필 사진 변경
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">이름</label>
                  <input
                    type="text"
                    value={userInfo.name}
                    onChange={(e) => handleUserInfoUpdate('name', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">이메일</label>
                  <input
                    type="email"
                    value={userInfo.email}
                    onChange={(e) => handleUserInfoUpdate('email', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-200">
                <h4 className="text-lg font-semibold text-slate-900 mb-4">계정 설정</h4>
                <div className="space-y-4">
                  <button className="w-full md:w-auto bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    정보 저장
                  </button>
                  <button className="w-full md:w-auto ml-0 md:ml-2 border border-slate-300 text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors">
                    비밀번호 변경
                  </button>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-200">
                <h4 className="text-lg font-semibold text-red-600 mb-4">위험한 작업</h4>
                <button className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors">
                  계정 삭제
                </button>
                <p className="text-sm text-slate-500 mt-2">
                  계정을 삭제하면 모든 데이터가 영구적으로 삭제됩니다.
                </p>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="마이페이지"
        subtitle="내 프로필과 면접 기록을 관리하세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* 사이드바 */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-6 sticky top-24">
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3">
                  {userInfo.name.charAt(0)}
                </div>
                <h3 className="font-bold text-slate-900">{userInfo.name}</h3>
              </div>

              <nav className="space-y-2">
                {sidebarMenus.map(menu => (
                  <button
                    key={menu.id}
                    onClick={() => setActiveTab(menu.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                      activeTab === menu.id
                        ? 'bg-blue-50 border-2 border-blue-200 text-blue-700'
                        : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <span className="text-lg">{menu.icon}</span>
                    <span className="font-medium">{menu.label}</span>
                  </button>
                ))}
              </nav>

            </div>
          </div>

          {/* 메인 콘텐츠 */}
          <div className="flex-1">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 min-h-[600px]">
              {isLoading ? (
                <div className="flex items-center justify-center h-96">
                  <LoadingSpinner size="lg" message="로딩 중..." />
                </div>
              ) : (
                renderContent()
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;