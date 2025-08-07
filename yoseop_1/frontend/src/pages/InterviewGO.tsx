import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../contexts/InterviewContext';
import { sessionApi, interviewApi } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SpeechIndicator from '../components/voice/SpeechIndicator';

const InterviewGO: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useInterview();

  // sessionId를 InterviewService 상태에서 가져오기
  React.useEffect(() => {
    const loadSessionFromService = async () => {
      try {
        // 1. 이미 Context에 sessionId가 있으면 OK
        if (state.sessionId) {
          console.log('✅ Context에 sessionId 존재:', state.sessionId);
          setIsRestoring(false);
          return;
        }

        // 2. InterviewService의 활성 세션에서 sessionId 가져오기
        console.log('🔍 InterviewService에서 활성 세션 조회 중...');
        const latestSessionId = await sessionApi.getLatestSessionId();
        
        if (latestSessionId) {
          console.log('✅ InterviewService에서 sessionId 발견:', latestSessionId);
          
          // 세션 상태도 함께 가져오기
          const sessionState = await sessionApi.getSessionState(latestSessionId);
          console.log('📋 세션 상태:', sessionState);
          
          // Context에 sessionId 설정
          dispatch({ type: 'SET_SESSION_ID', payload: latestSessionId });
          setIsRestoring(false);
          return;
        }

        // 3. localStorage에서 sessionId 복원 시도 (fallback)
        const saved = localStorage.getItem('interview_state');
        if (saved) {
          const parsedState = JSON.parse(saved);
          console.log('📦 localStorage에서 상태 복원 시도:', parsedState.sessionId);
          
          if (parsedState.sessionId) {
            dispatch({ type: 'SET_SESSION_ID', payload: parsedState.sessionId });
            console.log('✅ localStorage에서 sessionId 복원 완료:', parsedState.sessionId);
            setIsRestoring(false);
            return;
          }
        }

        // 4. sessionId가 없으면 환경 체크로 이동
        console.log('❌ sessionId를 찾을 수 없습니다. 환경 체크 페이지로 이동합니다.');
        navigate('/interview/environment-check');
        
      } catch (error) {
        console.error('❌ sessionId 로드 실패:', error);
        navigate('/interview/environment-check');
      } finally {
        setIsRestoring(false);
      }
    };

    loadSessionFromService();
  }, [state.sessionId, dispatch, navigate]);

  // 난이도별 AI 지원자 이미지 매핑 함수
  const getAICandidateImage = (level: number): string => {
    if (level <= 3) return '/img/candidate_1.png'; // 초급자
    if (level <= 7) return '/img/candidate_2.png'; // 중급자
    return '/img/candidate_3.png'; // 고급자
  };

  // 난이도별 AI 지원자 이름 매핑 함수
  const getAICandidateName = (level: number): string => {
    if (level <= 3) return '춘식이 (초급)';
    if (level <= 7) return '춘식이 (중급)';
    return '춘식이 (고급)';
  };
  
  // 🆕 새로운 상태들 추가
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true); // 복원 상태 추가
  
  // 🆕 턴 관리 상태
  const [currentTurn, setCurrentTurn] = useState<'user' | 'ai' | 'waiting'>('waiting');
  const [timeLeft, setTimeLeft] = useState(120); // 2분 타이머
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [canSubmit, setCanSubmit] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  
  // 🆕 currentPhase 상태 추가
  const [currentPhase, setCurrentPhase] = useState<'user_turn' | 'ai_processing' | 'interview_completed' | 'waiting' | 'unknown'>('waiting');
  
  // 🎤 음성 관련 상태
  const [isRecording, setIsRecording] = useState(false);
  const [canRecord, setCanRecord] = useState(false);
  const [sttResult, setSttResult] = useState('');
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [hasAudioPermission, setHasAudioPermission] = useState<boolean | null>(null);
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // 🆕 타이머 관리
  useEffect(() => {
    // 사용자 턴이고 타이머가 활성화되어 있을 때만 타이머 실행
    if (currentTurn === 'user' && isTimerActive && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            handleTimeUp();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      // 타이머 정지
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [currentTurn, isTimerActive, timeLeft]);

  // 🆕 시간 만료 핸들러
  const handleTimeUp = () => {
    console.log('⏰ 시간 만료!');
    setIsTimerActive(false);
    setCanSubmit(false);
    alert('시간이 만료되었습니다!');
    // 자동으로 답변 제출
    submitAnswer();
  };

  // 🆕 타이머 포맷 함수
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // 🆕 타이머 색상 함수
  const getTimerColor = (): string => {
    if (timeLeft > 60) return 'text-green-600';
    if (timeLeft > 30) return 'text-yellow-600';
    return 'text-red-600';
  };

  // 🆕 백엔드 응답에 따른 currentPhase 업데이트 함수
  const updatePhaseFromResponse = (response: any) => {
    console.log('🔄 currentPhase 업데이트 (단순화된 로직):', response);
    
    const nextAgent = response?.metadata?.next_agent;
    const task = response?.metadata?.task;
    const status = response?.status;
    const turnInfo = response?.turn_info;

    console.log('🔍 Phase 판단:', { nextAgent, task, status, turnInfo });

    if (task === 'end_interview') {
        setCurrentPhase('interview_completed');
        setCurrentTurn('waiting');
        setIsTimerActive(false);
        setCanSubmit(false);
        console.log('✅ 면접 완료로 설정됨');
    } else if (nextAgent === 'user' || status === 'waiting_for_user' || turnInfo?.is_user_turn) {
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(true);
        setTimeLeft(120);
        setCanSubmit(true);
        setCanRecord(true);  // 🎤 녹음 활성화
        console.log('✅ 사용자 턴으로 설정됨 (턴 정보:', turnInfo, ')');
    } else if (nextAgent === 'ai' || nextAgent === 'interviewer') {
        setCurrentPhase('ai_processing');
        setCurrentTurn('ai');
        setIsTimerActive(false);
        setCanSubmit(false);
        setCanRecord(false); // 🎤 녹음 비활성화
        // 진행 중인 녹음이 있으면 자동 중지
        if (isRecording) {
            stopRecording();
        }
        console.log('✅ AI/면접관 처리 중으로 설정됨');
    } else {
        // 기본적으로 사용자 턴으로 설정 (대기 상태 방지)
        console.log('⚠️ 명확한 턴 정보가 없어서 사용자 턴으로 기본 설정');
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(true);
        setTimeLeft(120);
        setCanSubmit(true);
        setCanRecord(true);  // 🎤 녹음 활성화
    }

    // 현재 질문 업데이트 (content.content 사용)
    const question = response?.content?.content;
    if (question) {
        setCurrentQuestion(question);
        console.log('📝 질문 업데이트:', question);
        
        // 🆕 질문이 업데이트되면 TTS 자동 재생
        if (question && question.trim()) {
            playQuestionTTS(question);
        }
    }
    
    // 🎤 녹음 권한 및 상태 업데이트
    updateVoicePermissions();
  };

  // 🆕 턴 상태 업데이트 함수 (JSON 응답 기반) - 기존 함수 유지
  const updateTurnFromResponse = (response: any) => {
    console.log('🔄 턴 상태 업데이트:', response);
    
    // JSON 응답에서 턴 정보 추출 (실제 응답 구조에 맞게 수정)
    const status = response?.status || '';
    const isUserTurn = status === 'waiting_for_user' || 
                      status === 'waiting_for_user_answer' || 
                      status === 'user_turn' || 
                      status === 'user';
    
    const isAITurn = status === 'ai_answering' || 
                     status === 'ai_turn' || 
                     status === 'ai' ||
                     status === 'waiting_for_ai';
    
    console.log('🔍 턴 판단:', {
      status,
      isUserTurn,
      isAITurn,
      responseKeys: Object.keys(response || {})
    });
    
    if (isUserTurn) {
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120); // 2분으로 재설정
      setCanSubmit(true);
      console.log('✅ 사용자 턴으로 설정됨');
    } else if (isAITurn) {
      setCurrentTurn('ai');
      setIsTimerActive(false);
      setCanSubmit(false);
      console.log('✅ AI 턴으로 설정됨');
    } else {
      // 기본적으로 사용자 턴으로 설정 (대기 상태 방지)
      console.log('⚠️ 명확한 턴 정보가 없어서 사용자 턴으로 기본 설정');
      setCurrentTurn('user');
      setIsTimerActive(true);
      setTimeLeft(120);
      setCanSubmit(true);
    }

    // 현재 질문 업데이트
    if (response?.question) {
      setCurrentQuestion(response.question);
      console.log('📝 질문 업데이트:', response.question);
    }
  };

  // 🆕 초기 턴 상태 설정 (세션 로드 완료 후)
  useEffect(() => {
    if (!isRestoring && state.sessionId) {
      console.log('🚀 초기 턴 상태 설정');
      
      // 면접 시작 시 받은 응답에서 턴 정보 확인
      const checkInitialTurnStatus = async () => {
        try {
          // 1. 먼저 localStorage에서 면접 시작 응답 확인
          const savedState = localStorage.getItem('interview_state');
          if (savedState) {
            const parsedState = JSON.parse(savedState);
            console.log('📦 localStorage에서 면접 상태 확인:', parsedState);
            
            // 면접 시작 응답에서 턴 정보 확인
            if (parsedState.interviewStartResponse && parsedState.interviewStartResponse.status === 'waiting_for_user') {
              console.log('✅ localStorage에서 사용자 턴 정보 발견');
              setCurrentPhase('user_turn');
              setCurrentTurn('user');
              setIsTimerActive(true);
              setTimeLeft(120);
              setCanSubmit(true);
              setCanRecord(true);  // 🎤 녹음 활성화
              setCurrentQuestion(parsedState.interviewStartResponse.content?.content || "질문을 불러오는 중...");
              console.log('✅ 초기 사용자 턴 설정 완료 (localStorage)');
              return;
            }
          }
          
          // 2. localStorage에 없으면 현재 면접 상태만 확인 (API 재호출 없이)
          console.log('🔄 현재 면접 상태 확인');
          if (state.settings) {
            try {
              // 면접 시작 API를 재호출하지 않고, 현재 상태만 확인
              // AI 경쟁 면접은 보통 사용자 턴으로 시작하므로 기본값 설정
              console.log('✅ AI 경쟁 면접 기본값으로 사용자 턴 설정');
              setCurrentPhase('user_turn');
              setCurrentTurn('user');
              setIsTimerActive(true);
              setTimeLeft(120);
              setCanSubmit(true);
              setCanRecord(true);  // 🎤 녹음 활성화
              setCurrentQuestion("면접을 시작합니다. 첫 번째 질문을 기다려주세요.");
              console.log('✅ 초기 사용자 턴 설정 완료 (기본값)');
              return;
            } catch (apiError) {
              console.log('⚠️ 기본값 설정 실패, 세션 상태로 fallback:', apiError);
            }
          }
          
          // 3. 세션 상태 확인 (fallback)
          const sessionState = await sessionApi.getSessionState(state.sessionId!);
          console.log('📋 초기 세션 상태:', sessionState);
          
          // 세션 상태에서 턴 정보 확인
          if (sessionState && sessionState.state?.status) {
            const status = sessionState.state.status;
            console.log('🔍 초기 세션에서 턴 상태 발견:', status);
            
            if (status === 'waiting_for_user') {
              setCurrentPhase('user_turn');
              setCurrentTurn('user');
              setIsTimerActive(true);
              setTimeLeft(120);
              setCanSubmit(true);
              setCanRecord(true);  // 🎤 녹음 활성화
              setCurrentQuestion(sessionState.state?.current_question || "질문을 불러오는 중...");
              console.log('✅ 초기 사용자 턴 설정 완료 (세션 상태)');
              return;
            }
          }
          
          // 4. 턴 정보가 없으면 unknown 상태로 시작
          setCurrentPhase('unknown');
          setCurrentTurn('waiting');
          setIsTimerActive(false);
          setCanSubmit(false);
          setCurrentQuestion("답변을 제출하여 턴을 시작하세요.");
          
        } catch (error) {
          console.error('❌ 초기 턴 상태 확인 실패:', error);
          setCurrentPhase('unknown');
          setCurrentTurn('waiting');
          setIsTimerActive(false);
          setCanSubmit(false);
          setCurrentQuestion("턴 정보를 확인하는 중...");
        }
      };
      
      checkInitialTurnStatus();
    }
  }, [isRestoring, state.sessionId, state.settings]);

  // 🆕 주기적 턴 상태 확인 제거 - 턴 정보는 답변 제출 후 응답에서만 받아옴

  // 답변 제출 실패 시에도 unknown 상태로 복구
  const submitAnswer = async () => {
    if (!currentAnswer.trim()) {
      console.log('❌ 답변이 입력되지 않았습니다.');
      return;
    }

    if (isLoading) {
      console.log('❌ 이미 제출 중입니다.');
      return;
    }

    // 사용자 턴이 아니면 제출 불가
    if (currentPhase !== 'user_turn') {
      console.log('❌ 사용자 턴이 아닙니다.');
      return;
    }

    let sessionId = state.sessionId;
    if (!sessionId) {
      try {
        sessionId = await sessionApi.getLatestSessionId();
        if (sessionId) {
          dispatch({ type: 'SET_SESSION_ID', payload: sessionId });
        }
      } catch (error) {
        console.error('❌ sessionId 조회 실패:', error);
      }
    }

    if (!sessionId) {
      alert('세션이 만료되었습니다. 면접을 다시 시작해주세요.');
      navigate('/interview/environment-check');
      return;
    }

    try {
      setIsLoading(true);
      setIsTimerActive(false); // 타이머 정지
      setCanSubmit(false); // 제출 버튼 비활성화
      setCanRecord(false); // 🎤 녹음 비활성화
      // 진행 중인 녹음이 있으면 자동 중지
      if (isRecording) {
          stopRecording();
      }
      
      console.log('🚀 답변 제출 시작:', {
        sessionId: sessionId,
        answer: currentAnswer,
        answerLength: currentAnswer.length,
        timeSpent: 120 - timeLeft
      });

      const result = await interviewApi.submitUserAnswer(
        sessionId,
        currentAnswer.trim(),
        120 - timeLeft
      );

      console.log('✅ 답변 제출 성공:', result);
      setCurrentAnswer(''); // 답변 초기화
      
      // 백엔드 응답에 따른 턴 상태 업데이트
      updatePhaseFromResponse(result);
      
    } catch (error: any) {
      console.error('❌ 답변 제출 오류:', error);
      // 에러 발생 시 unknown 상태로 복구
      setCurrentPhase('unknown');
      setCurrentTurn('waiting');
      setIsTimerActive(false);
      setCanSubmit(false);
      let errorMessage = '알 수 없는 오류';
      if (error.response) {
        errorMessage = `HTTP ${error.response.status}: ${error.response.data?.detail || error.response.statusText}`;
      } else if (error.request) {
        errorMessage = '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
      } else {
        errorMessage = error.message;
      }
      alert(`답변 제출 실패: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 🎤 음성 권한 확인 및 업데이트
  const updateVoicePermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setHasAudioPermission(true);
      // 사용 후 스트림 정리
      stream.getTracks().forEach(track => track.stop());
    } catch (error) {
      console.error('🎤 마이크 권한 없음:', error);
      setHasAudioPermission(false);
    }
  };

  // 🎤 녹음 시작
  const startRecording = async () => {
    // 이중 체크: 사용자 턴인지 확인
    if (currentTurn !== 'user' || currentPhase !== 'user_turn' || !canRecord) {
      alert('지금은 녹음할 수 없습니다. 사용자 차례를 기다려주세요.');
      return;
    }

    if (isRecording) {
      console.log('이미 녹음 중입니다.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 44100,  // 더 높은 품질
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true  // 자동 볼륨 조절 활성화
        }
      });

      // 브라우저 호환성을 위한 MIME 타입 선택
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/mp4';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = ''; // 브라우저 기본값 사용
      }
      
      console.log('🎤 사용할 MIME 타입:', mimeType);
      
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('🎤 녹음 완료, STT 처리 시작:', audioBlob.size, 'bytes');
        
        // STT 처리
        await processSTT(audioBlob);
        
        // 스트림 정리
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // 녹음 시간 카운터
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      console.log('🎤 녹음 시작');

    } catch (error) {
      console.error('🎤 녹음 시작 실패:', error);
      alert('마이크 접근 실패. 브라우저에서 마이크 권한을 허용해주세요.');
    }
  };

  // 🎤 녹음 중지
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      console.log('🎤 녹음 중지');
    }
  };

  // 🗣️ STT 처리 (OpenAI Whisper API)
  const processSTT = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      
      console.log('🗣️ STT 요청 전송 중...');
      
      const response = await fetch('http://localhost:8000/interview/stt', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('🔥 STT API 에러 응답:', response.status, errorData);
        throw new Error(`STT API 오류: ${response.status} - ${errorData.detail || response.statusText}`);
      }
      
      const result = await response.json();
      const transcribedText = result.text || '';
      
      console.log('✅ STT 처리 성공:', transcribedText);
      setSttResult(transcribedText);
      
      // 인식된 텍스트를 답변란에 자동 입력
      if (transcribedText.trim()) {
        setCurrentAnswer(prev => {
          const newAnswer = prev + (prev ? ' ' : '') + transcribedText;
          return newAnswer;
        });
      }
      
    } catch (error) {
      console.error('❌ STT 처리 실패:', error);
      alert(`음성 인식 실패: ${error}`);
    }
  };

  // 🔊 TTS 기능 (질문 읽어주기)
  const playQuestionTTS = async (text: string, voiceId: string = 'default') => {
    if (!text.trim() || isTTSPlaying) return;
    
    try {
      setIsTTSPlaying(true);
      console.log('🔊 TTS 재생 시작:', text.substring(0, 50));
      
      const response = await fetch('http://localhost:8000/interview/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text,
          voice_id: voiceId
        })
      });
      
      if (!response.ok) {
        throw new Error(`TTS API 오류: ${response.status}`);
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsTTSPlaying(false);
        URL.revokeObjectURL(audioUrl);
        console.log('✅ TTS 재생 완료');
      };
      
      audio.onerror = () => {
        setIsTTSPlaying(false);
        URL.revokeObjectURL(audioUrl);
        console.error('❌ TTS 재생 오류');
      };
      
      await audio.play();
      
    } catch (error) {
      console.error('❌ TTS 실패:', error);
      setIsTTSPlaying(false);
    }
  };

  // 🔇 TTS 중지
  const stopTTS = () => {
    setIsTTSPlaying(false);
    // 현재 재생 중인 TTS를 중지하는 로직은 여기에 추가 가능
  };

  // 🎤 음성 답변 제출 (녹음 후 자동 제출)
  const submitVoiceAnswer = async () => {
    if (isRecording) {
      // 녹음 중지 후 STT 처리가 완료되면 자동으로 submitAnswer 호출
      stopRecording();
      // STT 처리 완료 후 제출은 processSTT에서 처리
    } else if (currentAnswer.trim()) {
      // 이미 텍스트가 있으면 바로 제출
      submitAnswer();
    } else {
      alert('답변을 녹음하시거나 입력해주세요.');
    }
  };

  // 🎤 useEffect: 사용자 턴 변경 시 녹음 상태 업데이트
  useEffect(() => {
    if (currentTurn === 'user' && currentPhase === 'user_turn') {
      setCanRecord(true);
      console.log('✅ 사용자 턴 시작 - 녹음 가능');
    } else {
      setCanRecord(false);
      // 진행 중인 녹음이 있으면 자동 중지
      if (isRecording) {
        console.log('❌ 사용자 턴 종료 - 녹음 자동 중지');
        stopRecording();
      }
    }
  }, [currentTurn, currentPhase]);

  // 🎤 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        stopRecording();
      }
    };
  }, []);

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">
      {/* 메인 인터페이스 */}
      <div className="flex-1 flex flex-col">
        {/* 상단 면접관 영역 */}
        <div className="grid grid-cols-3 gap-4 p-4" style={{ height: '40vh' }}>
          {/* 인사 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              👔 인사 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_1.jpg"
                alt="인사 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 협업 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              🤝 협업 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_2.jpg"
                alt="협업 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* 기술 면접관 */}
          <div className="bg-gray-900 rounded-lg overflow-hidden relative border-2 border-gray-700">
            <div className="absolute top-4 left-4 font-semibold text-white">
              💻 기술 면접관
            </div>
            <div className="h-full flex items-center justify-center relative">
              <img 
                src="/img/interviewer_3.jpg"
                alt="기술 면접관"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>

        {/* 하단 영역 */}
        <div className="grid gap-4 p-4" style={{ height: '60vh', gridTemplateColumns: '2fr 1fr 2fr' }}>
          {/* 사용자 영역 */}
          <div className={`bg-gray-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // 사용자 턴일 때
            currentPhase === 'user_turn'
              ? 'border-yellow-500 shadow-lg shadow-yellow-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-yellow-400 font-semibold z-10">
              사용자: {state.settings?.candidate_name || 'You'}
            </div>
            
            {/* 🆕 턴 상태 표시 */}
            {currentPhase === 'user_turn' && (
              <div className="absolute top-4 right-4 bg-yellow-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🎯 답변 차례
              </div>
            )}
            
            {/* 실제 사용자 비디오 - 항상 렌더링 */}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }}
            />
            
            {/* 📹 카메라 연결 상태 오버레이 */}
            {!state.cameraStream && (
              <div className="absolute inset-0 h-full flex items-center justify-center bg-gray-800">
                <div className="text-white text-lg opacity-50">
                  카메라 대기 중...
                </div>
              </div>
            )}
            
            {/* 라이브 표시 */}
            <div className="absolute top-4 right-4 bg-red-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
              LIVE
            </div>

            {/* 답변 입력 오버레이 */}
            <div className="absolute bottom-0 left-0 right-0 bg-black/80 p-4">
              <textarea
                ref={answerRef}
                value={currentAnswer}
                onChange={(e) => setCurrentAnswer(e.target.value)}
                disabled={currentPhase !== 'user_turn'}
                className={`w-full h-20 p-2 bg-gray-800 text-white border border-gray-600 rounded-lg resize-none text-sm ${
                  currentPhase !== 'user_turn' ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                placeholder={currentPhase === 'user_turn' ? "답변을 입력해주세요..." : "대기 중..."}
              />
              
              {/* 🎤 음성 제어 버튼들 */}
              <div className="flex items-center justify-between mt-3 gap-3">
                {/* 음성 인식 결과 표시 */}
                {sttResult && (
                  <div className="text-xs text-blue-400 bg-blue-900/30 px-2 py-1 rounded">
                    🇢 인식: {sttResult.substring(0, 30)}{sttResult.length > 30 ? '...' : ''}
                  </div>
                )}
                
                {/* 녹음 버튼 */}
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={!canRecord || isLoading}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                    !canRecord ? 'bg-gray-600 text-gray-400 cursor-not-allowed' :
                    isRecording ? 'bg-red-500 text-white animate-pulse' :
                    'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                  title={!canRecord ? '사용자 차례가 아닙니다' : isRecording ? '녹음 중지' : '녹음 시작'}
                >
                  <span className="text-lg">
                    {!canRecord ? '🔒' : isRecording ? '🔴' : '🎤'}
                  </span>
                  <span className="text-sm">
                    {!canRecord ? '대기중' : isRecording ? `녹음중 (${recordingTime}s)` : '녹음하기'}
                  </span>
                </button>
                
                {/* TTS 버튼 */}
                <button
                  onClick={() => currentQuestion ? playQuestionTTS(currentQuestion) : null}
                  disabled={!currentQuestion || isTTSPlaying}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium transition-all ${
                    !currentQuestion ? 'bg-gray-600 text-gray-400 cursor-not-allowed' :
                    isTTSPlaying ? 'bg-orange-500 text-white animate-pulse' :
                    'bg-green-500 text-white hover:bg-green-600'
                  }`}
                  title="질문 다시 듣기"
                >
                  <span className="text-lg">
                    {isTTSPlaying ? '🔇' : '🔊'}
                  </span>
                  <span className="text-xs">
                    {isTTSPlaying ? '재생중' : '다시듣기'}
                  </span>
                </button>
              </div>
              
              <div className="flex items-center justify-between mt-2">
                <div className="text-gray-400 text-xs">{currentAnswer.length}자</div>
                {/* 🆕 타이머 표시 */}
                {currentPhase === 'user_turn' && isTimerActive && (
                  <div className={`text-lg font-bold ${getTimerColor()}`}>
                    {formatTime(timeLeft)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 중앙 컨트롤 */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col justify-center">
            {/* 🆕 현재 턴 상태 표시 */}
            <div className="text-center mb-4">
              <div className={`text-sm font-bold mb-2 ${
                currentPhase === 'user_turn' ? 'text-yellow-400' : 
                currentPhase === 'ai_processing' ? 'text-green-400' : 
                currentPhase === 'interview_completed' ? 'text-blue-400' :
                'text-gray-400'
              }`}>
                {currentPhase === 'user_turn' ? '🎯 사용자 답변 차례' :
                 currentPhase === 'ai_processing' ? '🤖 AI 답변 중' :
                 currentPhase === 'interview_completed' ? '✅ 면접 완료' :
                 '⏳ 대기 중'}
              </div>
              
              {/* 🆕 타이머 표시 */}
              {currentPhase === 'user_turn' && isTimerActive && (
                <div className={`text-2xl font-bold ${getTimerColor()} mb-2`}>
                  {formatTime(timeLeft)}
                </div>
              )}
              
              {/* 🎤 음성 상태 표시 */}
              {isRecording && (
                <SpeechIndicator 
                  isListening={true}
                  isSpeaking={false}
                  className="justify-center mb-2"
                />
              )}
              
              {/* 🎤 마이크 권한 상태 */}
              {hasAudioPermission === false && (
                <div className="text-red-400 text-xs mb-2">
                  🚫 마이크 권한이 필요합니다
                </div>
              )}
            </div>

            {/* 현재 질문 표시 */}
            <div className="text-center mb-6">
              <div className="text-gray-400 text-sm mb-2">현재 질문</div>
              <div className="text-white text-base leading-relaxed line-clamp-2 mb-3">
                {currentQuestion || "질문을 불러오는 중..."}
              </div>
            </div>

                         {/* 컨트롤 버튼 */}
             <div className="space-y-3">
               {(() => {
                 const hasAnswer = !!currentAnswer.trim();
                 const hasSessionId = !!state.sessionId || !isRestoring;
                 const isUserTurn = currentPhase === 'user_turn';
                 const isButtonDisabled = !hasAnswer || isLoading || isRestoring || !isUserTurn || !canSubmit;
                 
                 return (
                   <button 
                     className={`w-full py-3 text-white rounded-lg font-semibold transition-colors ${
                       isButtonDisabled 
                         ? 'bg-gray-600 cursor-not-allowed' 
                         : 'bg-green-600 hover:bg-green-500'
                     }`}
                     onClick={submitAnswer}
                     disabled={isButtonDisabled}
                   >
                     {isLoading 
                       ? '제출 중...' 
                       : isRestoring
                       ? '세션 로드 중...'
                       : !hasSessionId 
                       ? '세션 없음' 
                       : !isUserTurn
                       ? '대기 중...'
                       : !canSubmit
                       ? '준비 중...'
                       : !hasAnswer
                       ? '답변을 입력해주세요'
                       : '🚀 답변 제출'
                     }
                   </button>
                 );
               })()}
             </div>

            {/* 🆕 진행 상황 표시 */}
            <div className="mt-4 text-center">
              <div className="text-white text-sm mb-2">
                상태: {currentPhase === 'user_turn' ? '사용자 턴' : 
                       currentPhase === 'ai_processing' ? 'AI 처리 중' : 
                       currentPhase === 'interview_completed' ? '면접 완료' : 
                       '대기'}
              </div>
              
              {/* 🆕 디버깅 정보 */}
              <div className="text-gray-400 text-xs space-y-1">
                <div>세션: {state.sessionId ? '✅' : '❌'}</div>
                <div>복원: {isRestoring ? '🔄' : '✅'}</div>
                <div>타이머: {isTimerActive ? '⏰' : '⏸️'}</div>
                <div>제출: {canSubmit ? '✅' : '❌'}</div>
              </div>
              
              {/* 🆕 테스트 버튼들 */}
              <div className="mt-2 space-y-1">
                <button
                  onClick={() => {
                    setCurrentPhase('user_turn');
                    setCurrentTurn('user');
                    setIsTimerActive(true);
                    setTimeLeft(120);
                    setCanSubmit(true);
                    console.log('🧪 수동으로 사용자 턴 설정');
                  }}
                  className="w-full py-1 px-2 bg-yellow-600 hover:bg-yellow-500 text-white text-xs rounded"
                >
                  🧪 사용자 턴 테스트
                </button>
                <button
                  onClick={() => {
                    setCurrentPhase('ai_processing');
                    setCurrentTurn('ai');
                    setIsTimerActive(false);
                    setCanSubmit(false);
                    console.log('🧪 수동으로 AI 턴 설정');
                  }}
                  className="w-full py-1 px-2 bg-green-600 hover:bg-green-500 text-white text-xs rounded"
                >
                  🧪 AI 턴 테스트
                </button>
                <button
                  onClick={() => {
                    setCurrentPhase('interview_completed');
                    setCurrentTurn('waiting');
                    setIsTimerActive(false);
                    setCanSubmit(false);
                    console.log('🧪 수동으로 면접 완료 설정');
                  }}
                  className="w-full py-1 px-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded"
                >
                  🧪 면접 완료 테스트
                </button>
              </div>
            </div>
          </div>

          {/* AI 지원자 춘식이 */}
          <div className={`bg-blue-900 rounded-lg overflow-hidden relative border-2 transition-all duration-300 ${
            // AI 턴일 때
            currentPhase === 'ai_processing'
              ? 'border-green-500 shadow-lg shadow-green-500/50 animate-pulse'
            // 대기 상태
            : 'border-gray-600'
          }`}>
            <div className="absolute top-4 left-4 text-green-400 font-semibold z-10">
              AI 지원자 {getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
            </div>
            
            {/* 🆕 AI 턴 상태 표시 */}
            {currentPhase === 'ai_processing' && (
              <div className="absolute top-4 right-4 bg-green-500 text-black px-3 py-1 rounded-full text-xs font-bold z-10">
                🤖 답변 중
              </div>
            )}
            
            {/* AI 지원자 전체 이미지 */}
            <div className="h-full flex items-center justify-center relative">
              <img 
                src={getAICandidateImage(state.aiSettings?.aiQualityLevel || 6)}
                alt={getAICandidateName(state.aiSettings?.aiQualityLevel || 6)}
                className="w-full h-full object-cover"
              />
              
              {/* 상태 표시 오버레이 */}
              {currentPhase === 'ai_processing' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-green-400 text-sm font-semibold mb-2">답변 중...</div>
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                </div>
              ) : currentPhase === 'interview_completed' ? (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center bg-black/70 rounded-lg p-4">
                  <div className="text-blue-400 text-sm font-semibold mb-2">면접 완료</div>
                  <div className="text-blue-300 text-xs">수고하셨습니다!</div>
                </div>
              ) : (
                <div className="absolute bottom-4 right-4 bg-black/70 rounded-lg p-2">
                  <div className="text-blue-300 text-sm">대기 중</div>
                </div>
              )}
              
              {/* 라이브 표시 */}
              <div className="absolute top-4 right-4 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium z-10">
                AI
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewGO;
