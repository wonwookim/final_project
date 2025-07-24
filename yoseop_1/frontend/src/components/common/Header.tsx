import React from 'react';
import { useNavigate } from 'react-router-dom';

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

  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showBackButton && (
              <button
                onClick={() => navigate(-1)}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                <svg fill="currentColor" height="20px" viewBox="0 0 256 256" width="20px">
                  <path d="M224,128a8,8,0,0,1-8,8H59.31l58.35,58.34a8,8,0,0,1-11.32,11.32l-72-72a8,8,0,0,1,0-11.32l72-72a8,8,0,0,1,11.32,11.32L59.31,120H216A8,8,0,0,1,224,128Z"/>
                </svg>
              </button>
            )}
            
            <div className="h-8 w-8 bg-primary text-white rounded flex items-center justify-center font-bold">
              B
            </div>
            
            <div>
              <h1 className="text-xl font-bold text-slate-900">{title}</h1>
              {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {actionButton}
            {actions}
            
            <nav className="hidden md:flex items-center gap-8">
              <button 
                onClick={() => navigate('/')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                홈
              </button>
              <button 
                onClick={() => navigate('/interview')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                면접 시작
              </button>
              <button 
                onClick={() => navigate('/history')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                내 기록
              </button>
              <button 
                onClick={() => navigate('/profile')}
                className="text-sm font-medium text-slate-600 hover:text-primary transition-colors"
              >
                마이페이지
              </button>
            </nav>
            
            <button className="flex items-center justify-center rounded-full h-10 w-10 bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">
              <svg fill="currentColor" height="20px" viewBox="0 0 256 256" width="20px">
                <path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z"/>
              </svg>
            </button>
            
            <div className="w-10 h-10 rounded-full bg-gray-300"></div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;