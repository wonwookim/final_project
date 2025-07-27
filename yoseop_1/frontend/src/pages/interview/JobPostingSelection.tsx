import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';

interface JobPosting {
  id: string;
  company: string;        // 표시용 회사명
  companyCode: string;    // API용 회사 코드 (백엔드와 일치)
  logo: string;
  position: string;
  description: string;
  techStack: string[];
  requirements: string[];
  experience: string;
  type: string;
  location: string;
}

const JobPostingSelection: React.FC = () => {
  const navigate = useNavigate();
  const { dispatch } = useInterview();
  const [selectedPosting, setSelectedPosting] = useState<string | null>(null);

  const jobPostings: JobPosting[] = [
    {
      id: 'naver-frontend',
      company: '네이버',
      companyCode: 'naver',
      logo: '/img/naver.png',
      position: '프론트엔드 개발자',
      description: '네이버 메인 서비스의 프론트엔드 개발을 담당할 인재를 모집합니다.',
      techStack: ['React', 'TypeScript', 'Next.js', 'Redux'],
      requirements: ['React 3년 이상 경험', 'TypeScript 능숙', '웹 성능 최적화 경험'],
      experience: '경력 3년 이상',
      type: '정규직',
      location: '경기 성남시'
    },
    {
      id: 'kakao-backend',
      company: '카카오',
      companyCode: 'kakao',
      logo: '/img/kakao.svg',
      position: '백엔드 개발자',
      description: '카카오톡 메시징 시스템의 백엔드 개발을 담당할 개발자를 찾습니다.',
      techStack: ['Java', 'Spring Boot', 'MySQL', 'Redis'],
      requirements: ['Java Spring 3년 이상', '대용량 트래픽 처리 경험', 'MSA 아키텍처 이해'],
      experience: '경력 3~7년',
      type: '정규직',
      location: '경기 성남시'
    },
    {
      id: 'line-fullstack',
      company: '라인',
      companyCode: 'line',
      logo: '/img/line.svg',
      position: '풀스택 개발자',
      description: '라인 플랫폼의 다양한 서비스 개발에 참여할 풀스택 개발자를 모집합니다.',
      techStack: ['Vue.js', 'Node.js', 'Python', 'PostgreSQL'],
      requirements: ['풀스택 개발 경험 2년 이상', '클라우드 서비스 활용 경험', '영어 커뮤니케이션 가능'],
      experience: '경력 2~5년',
      type: '정규직',
      location: '서울 강남구'
    },
    {
      id: 'coupang-devops',
      company: '쿠팡',
      companyCode: 'coupang',
      logo: '/img/coupang.svg',
      position: 'DevOps 엔지니어',
      description: '쿠팡의 글로벌 인프라 운영 및 자동화를 담당할 DevOps 엔지니어를 모집합니다.',
      techStack: ['AWS', 'Kubernetes', 'Terraform', 'Jenkins'],
      requirements: ['AWS 클라우드 3년 이상', 'Kubernetes 운영 경험', 'CI/CD 구축 경험'],
      experience: '경력 3년 이상',
      type: '정규직',
      location: '서울 송파구'
    },
    {
      id: 'toss-data',
      company: '토스',
      companyCode: 'toss',
      logo: '/img/toss.png',
      position: '데이터 엔지니어',
      description: '토스의 금융 데이터를 활용한 인사이트 도출 및 데이터 파이프라인 구축을 담당합니다.',
      techStack: ['Python', 'Spark', 'Airflow', 'BigQuery'],
      requirements: ['데이터 파이프라인 구축 경험', 'SQL 고급 활용', '금융 도메인 이해'],
      experience: '경력 2~6년',
      type: '정규직',
      location: '서울 강남구'
    },
    {
      id: 'baemin-mobile',
      company: '배달의민족',
      companyCode: 'baemin',
      logo: '/img/baemin.svg',
      position: '모바일 개발자 (Android)',
      description: '배민 앱의 안드로이드 개발을 담당할 모바일 개발자를 찾습니다.',
      techStack: ['Kotlin', 'Android SDK', 'RxJava', 'Retrofit'],
      requirements: ['Android 개발 3년 이상', 'Kotlin 능숙', '앱 성능 최적화 경험'],
      experience: '경력 3~5년',
      type: '정규직',
      location: '서울 송파구'
    }
  ];

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  const handleSelectPosting = (postingId: string) => {
    setSelectedPosting(postingId);
  };

  const handleNext = () => {
    if (!selectedPosting) return;
    
    const selectedPostingData = jobPostings.find(posting => posting.id === selectedPosting);
    if (selectedPostingData) {
      // Context에 선택된 공고 정보 저장
      dispatch({ 
        type: 'SET_JOB_POSTING', 
        payload: {
          company: selectedPostingData.company,
          companyCode: selectedPostingData.companyCode,
          position: selectedPostingData.position,
          postingId: selectedPostingData.id
        }
      });
      
      navigate('/interview/resume-selection');
    }
  };

  const selectedPostingData = jobPostings.find(posting => posting.id === selectedPosting);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header 
        title="면접 준비"
        subtitle="지원하고 싶은 공고를 선택해주세요"
      />
      
      <main className="container mx-auto px-6 py-8">
        <StepIndicator currentStep={1} totalSteps={5} steps={steps} />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              어떤 공고에 지원하시나요?
            </h2>
            <p className="text-slate-600">
              관심있는 공고를 선택하면 해당 기업에 맞는 맞춤형 면접을 준비해드립니다.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {jobPostings.map((posting) => (
              <div
                key={posting.id}
                onClick={() => handleSelectPosting(posting.id)}
                className={`bg-white/80 backdrop-blur-sm rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg ${
                  selectedPosting === posting.id
                    ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 transform scale-105'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="border-2 border-gray-300 rounded-2xl p-2">
                    <img 
                      src={posting.logo} 
                      alt={`${posting.company} 로고`}
                      className="w-8 h-8 object-contain"
                    />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{posting.company}</h3>
                    <p className="text-blue-600 font-medium">{posting.position}</p>
                  </div>
                </div>

                <p className="text-sm text-slate-600 mb-4 line-clamp-2">
                  {posting.description}
                </p>

                <div className="space-y-3">
                  <div>
                    <div className="text-xs font-medium text-slate-500 mb-1">기술 스택</div>
                    <div className="flex flex-wrap gap-1">
                      {posting.techStack.slice(0, 3).map((tech, idx) => (
                        <span key={idx} className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded-full">
                          {tech}
                        </span>
                      ))}
                      {posting.techStack.length > 3 && (
                        <span className="px-2 py-1 bg-slate-100 text-slate-500 text-xs rounded-full">
                          +{posting.techStack.length - 3}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex justify-between text-xs text-slate-500">
                    <span>{posting.experience}</span>
                    <span>{posting.location}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 선택된 공고 상세 정보 */}
          {selectedPostingData && (
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 mb-8">
              <h3 className="text-xl font-bold text-slate-900 mb-4">선택된 공고</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-slate-700 mb-2">주요 요구사항</h4>
                  <ul className="space-y-1">
                    {selectedPostingData.requirements.map((req, idx) => (
                      <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                        <span className="text-blue-500 mt-1">•</span>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-slate-700 mb-2">기술 스택</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedPostingData.techStack.map((tech, idx) => (
                      <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onNext={handleNext}
              nextLabel="이력서 선택하기"
              canGoNext={!!selectedPosting}
              showPrevious={false}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default JobPostingSelection;