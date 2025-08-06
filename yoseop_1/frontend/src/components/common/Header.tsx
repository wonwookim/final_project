import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  showBackButton?: boolean;
  actions?: React.ReactNode;
  actionButton?: React.ReactNode;
}

const Header: React.FC<HeaderProps> = ({ 
  title = "Beta-GO Interview", 
  subtitle,
  showBackButton = false,
  actions,
  actionButton
}) => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout, isLoading } = useAuth();

  // 로그아웃 핸들러
  const handleLogout = async () => {
    const result = await logout();
    if (!result.success) {
      console.error('로그아웃 실패:', result.error);
      // 에러가 있어도 로그인 페이지로 이동 (이미 logout 함수에서 처리됨)
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <div className="container mx-auto px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex-between">
          <div className="flex items-center gap-2 sm:gap-3">
            {showBackButton && (
              <button
                onClick={() => navigate(-1)}
                className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                <svg fill="currentColor" height="16px" width="16px" className="sm:h-5 sm:w-5" viewBox="0 0 256 256">
                  <path d="M224,128a8,8,0,0,1-8,8H59.31l58.35,58.34a8,8,0,0,1-11.32,11.32l-72-72a8,8,0,0,1,0-11.32l72-72a8,8,0,0,1,11.32,11.32L59.31,120H216A8,8,0,0,1,224,128Z"/>
                </svg>
              </button>
            )}
            
            <div className="h-6 w-6 sm:h-8 sm:w-8 bg-primary text-white rounded flex-center font-bold text-sm sm:text-base">
              B
            </div>
            
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-slate-900">{title}</h1>
              {subtitle && <p className="text-xs sm:text-sm text-slate-600">{subtitle}</p>}
            </div>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-4">
            {actionButton}
            {actions}
            
            <nav className="hidden md:flex items-center gap-6 lg:gap-8">
              <button 
                onClick={() => navigate('/')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                홈
              </button>
              <button 
                onClick={() => navigate('/interview/job-posting')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                면접 시작
              </button>
              
              {isAuthenticated ? (
                <>
                  {user && (
                    <span className="text-sm font-medium text-slate-700">
                      {user.name}님
                    </span>
                  )}
                  <button 
                    onClick={handleLogout}
                    disabled={isLoading}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors disabled:opacity-50"
                  >
                    {isLoading ? '로그아웃 중...' : '로그아웃'}
                  </button>
                  <button 
                    onClick={() => navigate('/profile')}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                  >
                    마이페이지
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => navigate('/login')}
                    className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                  >
                    로그인
                  </button>
                  <button 
                    onClick={() => navigate('/signup')}
                    className="btn btn-primary text-sm px-3 py-1.5"
                  >
                    회원가입
                  </button>
                </>
              )}
            </nav>
            
            {/* 모바일 메뉴 버튼 */}
            <button className="md:hidden flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">
              <svg fill="currentColor" height="20px" width="20px" viewBox="0 0 256 256">
                <path d="M224,120H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm0-64H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm0,128H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;