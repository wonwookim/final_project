import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/common/Header';
import StepIndicator from '../../components/interview/StepIndicator';
import NavigationButtons from '../../components/interview/NavigationButtons';
import { useInterview } from '../../contexts/InterviewContext';
import { postingAPI, JobPosting, Company, Position } from '../../services/api';

const JobPostingSelection: React.FC = () => {
  const navigate = useNavigate();
  const { dispatch } = useInterview();
  
  // 🆕 2단계 선택 상태 관리
  const [currentStep, setCurrentStep] = useState<'company' | 'position' | 'posting'>('company');
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [matchedPosting, setMatchedPosting] = useState<JobPosting | null>(null);
  
  // 데이터 상태
  const [companies, setCompanies] = useState<Company[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasInitialized = useRef(false);

  // 회사 로고 매핑 함수
  const getCompanyLogo = (companyName: string): string => {
    const logoMap: Record<string, string> = {
      '네이버': '/img/naver.png',
      '카카오': '/img/kakao.svg',
      '라인플러스': '/img/line.svg',
      '쿠팡': '/img/coupang.svg',
      '배달의민족': '/img/baemin.svg',
      '배민': '/img/baemin.svg',
      '당근': '/img/daangn.png',
      '당근마켓': '/img/daangn.png',
      '토스': '/img/toss.png'
    };
    
    return logoMap[companyName] || '/img/default-company.png'; // fallback 이미지
  };

  // 🆕 회사 및 직군 데이터 로딩 (React Strict Mode 중복 방지)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    
    const loadInitialData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // 회사와 직군 데이터를 병렬로 로드
        const [companiesData, positionsData] = await Promise.all([
          postingAPI.getAllCompanies(),
          postingAPI.getAllPositions()
        ]);
        
        console.log('📋 회사 데이터 로드 완료:', companiesData.length, '개');
        console.log('📋 직군 데이터 로드 완료:', positionsData.length, '개');
        
        if (companiesData.length === 0 || positionsData.length === 0) {
          console.warn('⚠️ DB에서 회사/직군 데이터를 찾을 수 없음 - fallback 데이터 사용');
          // fallback: 더미 데이터 사용
          const { companies: fallbackCompanies, positions: fallbackPositions } = getFallbackData();
          setCompanies(fallbackCompanies);
          setPositions(fallbackPositions);
        } else {
          setCompanies(companiesData);
          setPositions(positionsData);
        }
        
      } catch (error) {
        console.error('❌ 회사/직군 데이터 로딩 실패:', error);
        setError('회사 및 직군 정보를 불러오는데 실패했습니다.');
        // fallback: 더미 데이터 사용
        const { companies: fallbackCompanies, positions: fallbackPositions } = getFallbackData();
        setCompanies(fallbackCompanies);
        setPositions(fallbackPositions);
      } finally {
        setIsLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // fallback 더미 데이터 (DB 연결 실패 시 사용)
  const getFallbackData = () => {
    const companies: Company[] = [
      { company_id: 1, name: '네이버' },
      { company_id: 2, name: '카카오' },
      { company_id: 3, name: '라인플러스' },
      { company_id: 4, name: '쿠팡' },
      { company_id: 5, name: '배달의민족' },
      { company_id: 6, name: '당근마켓' },
      { company_id: 7, name: '토스' }
    ];
    
    const positions: Position[] = [
      { position_id: 1, position_name: '프론트엔드 개발자' },
      { position_id: 2, position_name: '백엔드 개발자' },
      { position_id: 3, position_name: '기획' },
      { position_id: 4, position_name: 'AI' },
      { position_id: 5, position_name: '데이터 사이언스' }
    ];
    
    return { companies, positions };
  };

  const steps = ['공고 선택', '이력서 선택', '면접 모드 선택', 'AI 설정', '환경 체크'];

  // 🆕 회사 선택 핸들러
  const handleSelectCompany = (company: Company) => {
    setSelectedCompany(company);
    setCurrentStep('position');
  };

  // 🆕 직군 선택 핸들러 - 자동으로 공고 매칭
  const handleSelectPosition = async (position: Position) => {
    if (!selectedCompany) return;
    
    setSelectedPosition(position);
    setIsLoading(true);
    
    try {
      // 선택된 회사와 직군으로 공고를 자동 조회
      const posting = await postingAPI.getPostingByCompanyAndPosition(
        selectedCompany.company_id, 
        position.position_id
      );
      
      if (posting) {
        setMatchedPosting(posting);
        setCurrentStep('posting');
        console.log('✅ 자동 매칭된 공고:', posting);
      } else {
        // 매칭되는 공고가 없는 경우 fallback 생성
        const fallbackPosting: JobPosting = {
          posting_id: Date.now(), // 임시 ID
          company_id: selectedCompany.company_id,
          position_id: position.position_id,
          company: selectedCompany.name,
          position: position.position_name,
          content: `${selectedCompany.name}에서 ${position.position_name} 포지션에 대한 채용을 진행중입니다. 해당 포지션에 맞는 맞춤형 면접을 준비해드립니다.`
        };
        setMatchedPosting(fallbackPosting);
        setCurrentStep('posting');
        console.log('⚠️ 매칭 공고 없음 - fallback 생성:', fallbackPosting);
      }
    } catch (error) {
      console.error('❌ 공고 매칭 실패:', error);
      setError('공고 매칭에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // 🆕 뒤로가기 핸들러
  const handleGoBack = () => {
    if (currentStep === 'position') {
      setCurrentStep('company');
      setSelectedCompany(null);
    } else if (currentStep === 'posting') {
      setCurrentStep('position');
      setSelectedPosition(null);
      setMatchedPosting(null);
    }
  };

  const handleNext = () => {
    if (!matchedPosting) return;
    
    // Context에 선택된 공고 정보 저장
    dispatch({ 
      type: 'SET_JOB_POSTING', 
      payload: {
        posting_id: matchedPosting.posting_id,
        company_id: matchedPosting.company_id,
        position_id: matchedPosting.position_id,
        company: matchedPosting.company,
        position: matchedPosting.position,
        content: matchedPosting.content
      }
    });
    
    navigate('/interview/resume-selection');
  };

  // 현재 단계별 데이터 및 UI 상태 가져오기
  const getCurrentStepData = () => {
    switch (currentStep) {
      case 'company':
        return {
          title: '회사를 선택해주세요',
          subtitle: '대표적인 IT 기업을 선택해주세요.',
          data: companies,
          canGoNext: false,
          showPrevious: false
        };
      case 'position':
        return {
          title: '직군을 선택해주세요',
          subtitle: `${selectedCompany?.name}에 지원할 직군을 선택해주세요.`,
          data: positions,
          canGoNext: false,
          showPrevious: true
        };
      case 'posting':
        return {
          title: '공고가 자동 매칭되었습니다!',
          subtitle: '선택한 회사와 직군에 맞는 공고입니다.',
          data: null,
          canGoNext: !!matchedPosting,
          showPrevious: true
        };
      default:
        return { title: '', subtitle: '', data: null, canGoNext: false, showPrevious: false };
    }
  };
  
  const stepData = getCurrentStepData();

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
              {stepData.title}
            </h2>
            <p className="text-slate-600">
              {stepData.subtitle}
            </p>
            
            {/* 현재 단계 표시 */}
            <div className="flex justify-center items-center mt-6 space-x-4">
              <div className={`flex items-center space-x-2 ${
                currentStep === 'company' ? 'text-blue-600 font-semibold' : 'text-slate-400'
              }`}>
                <div className={`w-3 h-3 rounded-full ${
                  currentStep === 'company' ? 'bg-blue-500' : selectedCompany ? 'bg-green-500' : 'bg-slate-300'
                }`}></div>
                <span>1. 회사 선택</span>
              </div>
              
              <div className="w-8 h-px bg-slate-300"></div>
              
              <div className={`flex items-center space-x-2 ${
                currentStep === 'position' ? 'text-blue-600 font-semibold' : 'text-slate-400'
              }`}>
                <div className={`w-3 h-3 rounded-full ${
                  currentStep === 'position' ? 'bg-blue-500' : selectedPosition ? 'bg-green-500' : 'bg-slate-300'
                }`}></div>
                <span>2. 직군 선택</span>
              </div>
              
              <div className="w-8 h-px bg-slate-300"></div>
              
              <div className={`flex items-center space-x-2 ${
                currentStep === 'posting' ? 'text-blue-600 font-semibold' : 'text-slate-400'
              }`}>
                <div className={`w-3 h-3 rounded-full ${
                  currentStep === 'posting' ? 'bg-blue-500' : matchedPosting ? 'bg-green-500' : 'bg-slate-300'
                }`}></div>
                <span>3. 공고 확인</span>
              </div>
            </div>
          </div>

          {/* 로딩 상태 */}
          {isLoading && (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-slate-600">채용공고를 불러오는 중...</span>
            </div>
          )}

          {/* 에러 상태 */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-red-600">{error}</p>
              <p className="text-red-500 text-sm mt-1">fallback 데이터를 사용합니다.</p>
            </div>
          )}

          {/* 회사 선택 단계 */}
          {currentStep === 'company' && !isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {companies.map((company) => (
                <div
                  key={company.company_id}
                  onClick={() => handleSelectCompany(company)}
                  className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg hover:border-slate-300 border-slate-200"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="border-2 border-gray-300 rounded-2xl p-2">
                      <img 
                        src={getCompanyLogo(company.name)} 
                        alt={company.name}
                        className="w-8 h-8 rounded-lg object-contain"
                        onError={(e) => {
                          const img = e.currentTarget;
                          const fallbackDiv = img.nextElementSibling as HTMLElement;
                          if (fallbackDiv) {
                            img.style.display = 'none';
                            fallbackDiv.style.display = 'flex';
                          }
                        }}
                      />
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center" style={{display: 'none'}}>
                        <span className="text-white font-bold text-sm">
                          {company.name?.charAt(0) || 'C'}
                        </span>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">{company.name}</h3>
                      <p className="text-slate-500 text-sm">{company.name}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* 직군 선택 단계 */}
          {currentStep === 'position' && !isLoading && (
            <div>
              {/* 선택된 회사 표시 */}
              {selectedCompany && (
                <div className="bg-blue-50 rounded-xl p-4 mb-6">
                  <div className="flex items-center gap-3">
                    <img 
                      src={getCompanyLogo(selectedCompany.name)} 
                      alt={selectedCompany.name}
                      className="w-10 h-10 rounded-lg object-contain"
                      onError={(e) => {
                        const img = e.currentTarget;
                        img.src = '/img/default-company.png';
                      }}
                    />
                    <div>
                      <p className="text-blue-800 font-semibold">선택된 회사: {selectedCompany.name}</p>
                      <p className="text-blue-600 text-sm">직군을 선택해주세요</p>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {positions.map((position) => (
                  <div
                    key={position.position_id}
                    onClick={() => handleSelectPosition(position)}
                    className="bg-white/80 backdrop-blur-sm rounded-xl p-4 border-2 cursor-pointer transition-all duration-300 hover:shadow-lg hover:border-slate-300 border-slate-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                        <span className="text-white font-bold text-sm">💼</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-slate-900">{position.position_name}</h3>
                        <p className="text-slate-500 text-sm">{position.position_name}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* 공고 확인 단계 */}
          {currentStep === 'posting' && !isLoading && matchedPosting && (
            <div className="mb-8">
              {/* 선택 요약 */}
              <div className="bg-green-50 rounded-xl p-4 mb-6">
                <h3 className="text-green-800 font-semibold mb-2">✅ 매칭 완료</h3>
                <div className="flex items-center gap-4">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                    {selectedCompany?.name}
                  </span>
                  <span className="text-slate-400">×</span>
                  <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                    {selectedPosition?.position_name}
                  </span>
                </div>
              </div>
              
              {/* 매칭된 공고 상세 */}
              <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
                <div className="flex items-center gap-3 mb-4">
                  <img 
                    src={getCompanyLogo(matchedPosting.company)} 
                    alt={matchedPosting.company}
                    className="w-12 h-12 rounded-xl object-contain"
                    onError={(e) => {
                      const img = e.currentTarget;
                      img.src = '/img/default-company.png';
                    }}
                  />
                  <div>
                    <h4 className="text-lg font-bold text-slate-900">{matchedPosting.company}</h4>
                    <p className="text-blue-600 font-medium">{matchedPosting.position}</p>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-slate-700 mb-2">채용공고 내용</h4>
                  <p className="text-sm text-slate-600 leading-relaxed">{matchedPosting.content}</p>
                </div>
              </div>
            </div>
          )}


          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-slate-200">
            <NavigationButtons
              onNext={currentStep === 'posting' ? handleNext : undefined}
              onPrevious={stepData.showPrevious ? handleGoBack : undefined}
              nextLabel={currentStep === 'posting' ? '이력서 선택하기' : undefined}
              canGoNext={stepData.canGoNext}
              showPrevious={stepData.showPrevious}
            />
          </div>
        </div>
      </main>
    </div>
  )
  ;
};

export default JobPostingSelection;