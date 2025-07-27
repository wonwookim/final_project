import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import LoadingSpinner from '../components/common/LoadingSpinner';

const SignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    code: '',
    password: '',
    passwordConfirm: '',
    name: ''
  });
  const [error, setError] = useState('');
  const [emailSent, setEmailSent] = useState(false);
  const [codeVerified, setCodeVerified] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [verifyMessage, setVerifyMessage] = useState('');

  // 입력 변경 핸들러
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
    if (name === 'email') setEmailError('');
    if (name === 'code') setVerifyMessage(''); // Remove setCodeError('');
    setInfoMessage('');
    setVerifyMessage('');
  };

  // 인증받기 클릭
  const handleSendCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(formData.email)) {
      setEmailError('올바른 이메일을 입력하세요.');
      setInfoMessage('');
      return;
    }
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setEmailSent(true);
      setInfoMessage('이메일로 인증번호를 전송했습니다. 메일을 확인해주세요!');
    }, 700);
  };

  // 인증확인 클릭
  const handleVerifyCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.code !== '1234') {
      setVerifyMessage('인증번호가 올바르지 않습니다.');
      return;
    }
    setCodeVerified(true);
    setVerifyMessage('인증이 완료되었습니다!');
  };

  // 회원가입 클릭
  const handleSignUp = (e: React.FormEvent) => {
    e.preventDefault();
    if (!codeVerified) return;
    if (formData.password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (formData.password !== formData.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (!formData.name.trim()) {
      setError('이름을 입력하세요.');
      return;
    }
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      navigate('/');
    }, 700);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Header title="회원가입" subtitle="Beta-GO Interview에 오신 것을 환영합니다" />
      <main className="container mx-auto px-6 py-12">
        <div className="max-w-md mx-auto">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-slate-200 shadow-lg">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-slate-900 mb-2">회원가입</h1>
              <p className="text-slate-600">이메일 인증 후 정보를 입력하세요</p>
            </div>
            <form className="space-y-6" onSubmit={handleSignUp}>
              {/* 이메일 + 인증받기 */}
              <div className="flex gap-2">
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="이메일을 입력하세요"
                  required
                  disabled={codeVerified}
                />
                <button
                  type="button"
                  onClick={handleSendCode}
                  disabled={isLoading || codeVerified}
                  className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all disabled:opacity-50"
                >
                  {isLoading && !codeVerified ? <LoadingSpinner size="sm" color="white" /> : '인증받기'}
                </button>
              </div>
              {emailError && <div className="mb-2 text-center text-red-600 font-semibold text-sm">{emailError}</div>}
              {infoMessage && <div className="mb-2 text-center text-blue-600 font-semibold text-sm">{infoMessage}</div>}

              {/* 인증번호 + 인증확인 */}
              <div className="flex gap-2">
                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleInputChange}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                  placeholder="인증번호 입력"
                  required
                  disabled={!emailSent || codeVerified}
                />
                <button
                  type="button"
                  onClick={handleVerifyCode}
                  disabled={!emailSent || codeVerified}
                  className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all disabled:opacity-50"
                >
                  인증확인
                </button>
              </div>
              {verifyMessage && (
                <div className={`mb-2 text-center font-semibold text-sm ${verifyMessage.includes('완료') ? 'text-green-600' : 'text-red-600'}`}>{verifyMessage}</div>
              )}

              {/* PW, PW 확인, 이름 */}
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                placeholder="패스워드 (8자 이상)"
                required
                disabled={!codeVerified}
              />
              <input
                type="password"
                name="passwordConfirm"
                value={formData.passwordConfirm}
                onChange={handleInputChange}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                placeholder="패스워드 확인"
                required
                disabled={!codeVerified}
              />
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                placeholder="이름"
                required
                disabled={!codeVerified}
              />
              {error && <div className="mb-2 text-center text-red-600 font-semibold text-sm">{error}</div>}
              <button
                type="submit"
                disabled={!codeVerified || isLoading}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-xl font-bold text-lg hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <LoadingSpinner size="sm" color="white" /> 회원가입 중...
                  </div>
                ) : (
                  '회원가입'
                )}
              </button>
            </form>
          </div>
          <div className="mt-8 text-center">
            <button
              onClick={() => navigate('/')}
              className="text-slate-600 hover:text-slate-800 text-sm"
            >
              홈으로 돌아가기
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SignUpPage; 