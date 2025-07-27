import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';

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

const ResumeSelection: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();
  const [selectedResume, setSelectedResume] = useState<string | null>(null);

  // Mock 이력서 데이터 (실제로는 ProfilePage의 이력서 데이터를 API로 가져와야 함)
  const mockResumes: Resume[] = [
    {
      id: '1',
      name: '김개발',
      email: 'kim@example.com',
      phone: '010-1234-5678',
      academic_record: '2020년 서울대학교 컴퓨터공학과 졸업 (학점: 3.8/4.5)',
      career: '2021-2023 네이버 - 프론트엔드 개발자\n• React 기반 웹 서비스 개발\n• 사용자 경험 개선으로 전환율 20% 향상\n• 팀 내 코드 리뷰 문화 정착',
      tech: 'JavaScript, React, TypeScript, Node.js, Python, Docker, AWS',
      activities: '2020-2021 SOPT 개발 동아리 활동\n2021 해커톤 대상 수상\n개인 프로젝트: 음식 추천 웹 서비스 개발 (1만 사용자)',
      certificate: '정보처리기사 (2020.05)\nAWS Solutions Architect Associate (2022.03)',
      awards: '2021 대학교 졸업작품 우수상\n2022 해커톤 대상',
      created_at: '2025-01-15',
      updated_at: '2025-01-20'
    },
    {
      id: '2',
      name: '김개발',
      email: 'kim@example.com',
      phone: '010-1234-5678',
      academic_record: '2019년 연세대학교 컴퓨터공학과 졸업 (학점: 3.9/4.5)',
      career: '2020-2024 카카오 - 백엔드 개발자\n• Spring Boot 기반 API 서버 개발\n• 대용량 트래픽 처리 시스템 구축\n• MSA 아키텍처 설계 및 구현',
      tech: 'Java, Spring Boot, MySQL, Redis, Kafka, Kubernetes, Jenkins',
      activities: '오픈소스 프로젝트 기여 (Spring Boot Contributors)\n기술 블로그 운영 (월 1만 방문자)\n개발자 컨퍼런스 발표 경험',
      certificate: '정보처리기사 (2019.11)\nCKA (Certified Kubernetes Administrator) (2023.06)',
      awards: '2023 카카오 사내 해커톤 최우수상\n2024 개발자 컨퍼런스 베스트 스피커',
      created_at: '2025-01-10',
      updated_at: '2025-01-18'
    }
  ];

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const calculateCompletionRate = (resume: Resume): number => {
    const fields = ['name', 'academic_record', 'career', 'tech'];
    const filledFields = fields.filter(field => resume[field as keyof Resume]?.toString().trim());
    return Math.round((filledFields.length / fields.length) * 100);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  const handleSelectResume = (resumeId: string) => {
    setSelectedResume(resumeId);
  };

  const handlePrevious = () => {
    navigate('/interview/job-posting');
  };

  const handleNext = () => {
    if (!selectedResume) return;
    
    const selectedResumeData = mockResumes.find(resume => resume.id === selectedResume);
    if (selectedResumeData) {
      // Context에 선택된 이력서 정보 저장
      dispatch({ 
        type: 'SET_RESUME', 
        payload: selectedResumeData
      });
      
      navigate('/interview/interview-mode-selection');
    }
  };

  const handleCreateResume = () => {
    navigate('/profile', { state: { activeTab: 'resume', action: 'create' } });
  };

  const selectedResumeData = mockResumes.find(resume => resume.id === selectedResume);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="사용할 이력서를 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={2} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              어떤 이력서로 면접을 볼까요?
            </h2>
            <p className="text-slate-600">
              {state.jobPosting?.company} {state.jobPosting?.position} 포지션에 맞는 이력서를 선택해주세요.
            </p>
          </div>

          {mockResumes.length === 0 ? (
            // 이력서가 없는 경우
            <div className="text-center py-16">
              <div className="text-8xl mb-6">📄</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">등록된 이력서가 없습니다</h3>
              <p className="text-slate-600 mb-6">
                면접을 시작하기 전에 마이페이지에서 이력서를 먼저 작성해주세요.
              </p>
              <button
                onClick={handleCreateResume}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700 transition-colors"
              >
                📝 이력서 작성하러 가기
              </button>
            </div>
          ) : (
            <>
              {/* 이력서 목록 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {mockResumes.map(resume => {
                  const completionRate = calculateCompletionRate(resume);
                  return (
                    <div
                      key={resume.id}
                      onClick={() => handleSelectResume(resume.id)}
                      className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg ${
                        selectedResume === resume.id
                          ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 transform scale-105'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
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
                        <div className="flex items-center gap-2">
                          <span>💼</span>
                          <span className="truncate">
                            {resume.career ? resume.career.split('\n')[0] : '경력 미입력'}
                          </span>
                        </div>
                      </div>

                      {selectedResume === resume.id && (
                        <div className="mt-4 pt-4 border-t border-slate-200">
                          <div className="flex items-center gap-2 text-blue-600">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            <span className="font-medium">선택됨</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* 이력서 추가 버튼 */}
              <div className="text-center mb-8">
                <button
                  onClick={handleCreateResume}
                  className="bg-slate-100 text-slate-600 px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors"
                >
                  ➕ 새 이력서 만들기
                </button>
              </div>

              {/* 선택된 이력서 미리보기 */}
              {selectedResumeData && (
                <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 mb-8">
                  <h3 className="text-xl font-bold text-slate-900 mb-4">선택된 이력서 미리보기</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="font-medium text-slate-700 mb-2">기본 정보</h4>
                      <div className="space-y-1 text-sm text-slate-600">
                        <div>이름: {selectedResumeData.name}</div>
                        <div>이메일: {selectedResumeData.email}</div>
                        <div>연락처: {selectedResumeData.phone}</div>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-700 mb-2">주요 기술스택</h4>
                      <div className="flex flex-wrap gap-1">
                        {selectedResumeData.tech.split(',').slice(0, 5).map((tech, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                            {tech.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4">
                    <h4 className="font-medium text-slate-700 mb-2">주요 경력</h4>
                    <p className="text-sm text-slate-600 line-clamp-2">
                      {selectedResumeData.career.split('\n')[0]}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onPrevious={handlePrevious}
              onNext={handleNext}
              previousLabel="공고 다시 선택"
              nextLabel="면접 모드 선택하기"
              canGoNext={!!selectedResume}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default ResumeSelection;