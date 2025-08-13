import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../contexts/InterviewContext';
import { sessionApi, interviewApi, tokenManager } from '../services/api';
import apiClient, { handleApiError } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SpeechIndicator from '../components/voice/SpeechIndicator';
import { getInterviewState, markApiCallCompleted, debugInterviewState, setApiCallInProgress, isApiCallInProgress } from '../utils/interviewStateManager';
import { GazeAnalysisResult, VideoAnalysisResponse, AnalysisStatusResponse } from '../components/test/types';

// API 응답 타입 정의
interface UploadResponse {
  play_url: string;
  file_name?: string;
  file_type?: string;
  media_id?: string;
}

interface FeedbackEvaluationRequest {
  user_id: number;
  user_resume_id: number | null;
  ai_resume_id: number | null;
  posting_id: number | null;
  company_id: number | null;
  position_id: number | null;
  qa_pairs: {
    question: string;
    answer: string;
    duration: number;
    question_level: number;
  }[];
}

interface FeedbackEvaluationResponse {
  success: boolean;
  results?: {
    interview_id: number;
    evaluation_id: number;
  }[];
  message?: string;
}

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

  // 🎥 카메라 스트림 검증 및 연결
  useEffect(() => {
    const validateAndConnectStream = async () => {
      console.log('🔍 카메라 스트림 검증 시작:', !!state.cameraStream);
      
      // 1. 스트림 객체가 존재하는지 확인
      if (!state.cameraStream) {
        console.log('❌ 카메라 스트림이 없습니다.');
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 2. 스트림이 활성화 상태인지 확인
      if (!state.cameraStream.active) {
        console.log('❌ 카메라 스트림이 비활성화 상태입니다.');
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 3. 비디오 트랙이 존재하고 live 상태인지 확인
      const videoTracks = state.cameraStream.getVideoTracks();
      if (videoTracks.length === 0 || videoTracks[0].readyState !== 'live') {
        console.log('❌ 카메라 비디오 트랙이 유효하지 않습니다:', videoTracks.length, videoTracks[0]?.readyState);
        alert('카메라 연결에 문제가 발생했습니다. 환경 체크 페이지로 다시 이동합니다.');
        navigate('/interview/environment-check');
        return;
      }
      
      // 4. 모든 검증을 통과했다면 비디오 엘리먼트에 스트림 연결
      if (videoRef.current) {
        console.log('✅ 카메라 스트림 검증 완료 - 비디오 엘리먼트에 연결');
        videoRef.current.srcObject = state.cameraStream;
        
        try {
          await videoRef.current.play();
          console.log('✅ 카메라 비디오 재생 시작');
        } catch (playError) {
          console.warn('⚠️ 비디오 자동 재생 실패 (권한 문제일 수 있음):', playError);
        }
      }
    };

    // cameraStream이 존재할 때 검증 실행
    if (state.cameraStream) {
      validateAndConnectStream();
    }
  }, [state.cameraStream, navigate]);

  // 🧹 컴포넌트 언마운트 시 비디오 스트림 정리 (메모리 누수 방지)
  useEffect(() => {
    const currentVideoRef = videoRef.current;
    return () => {
      if (currentVideoRef) {
        console.log('🧹 비디오 엘리먼트 스트림 연결 해제');
        currentVideoRef.srcObject = null;
      }
    };
  }, []);

  

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
  
  // 🆕 INTRO 메시지 관련 상태
  const [introMessage, setIntroMessage] = useState<string>('');
  const [hasIntroMessage, setHasIntroMessage] = useState(false);
  const [showIntroMessage, setShowIntroMessage] = useState(false);
  
  // 🆕 TTS 관련 상태
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  
  // 🔊 TTS 확인용 주석입니다 - TTS 실행 이력 추적
  const [ttsList, setTtsList] = useState<{type: string, text: string, timestamp: string}[]>([]);
  
  // 🔊 TTS 확인용 주석입니다 - TTS 큐 시스템
  const [ttsQueue, setTtsQueue] = useState<string[]>([]);
  
  // 🆕 AI 질문/답변 관련 상태
  const [currentAIQuestion, setCurrentAIQuestion] = useState<string>('');
  const [currentAIAnswer, setCurrentAIAnswer] = useState<string>('');
  
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
  const [recordingTime, setRecordingTime] = useState(0);
  const [hasAudioPermission, setHasAudioPermission] = useState<boolean | null>(null);

  // 👁️ 시선 추적 관련 상태
  const [isGazeRecording, setIsGazeRecording] = useState(false);
  const [gazeBlob, setGazeBlob] = useState<Blob | null>(null);
  const [gazeError, setGazeError] = useState<string | null>(null);
  const [gazeAnalysisResult, setGazeAnalysisResult] = useState<GazeAnalysisResult | null>(null);
  
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  // 🆕 API 호출 중복 방지를 위한 useRef
  const apiCallCancelRef = useRef<AbortController | null>(null);
  const isApiCallInProgressRef = useRef(false);

  // 👁️ 시선 추적용 refs
  const gazeVideoRef = useRef<HTMLVideoElement>(null);
  const gazeMediaRecorderRef = useRef<MediaRecorder | null>(null);
  const gazeChunksRef = useRef<Blob[]>([]);

  // 👁️ 시선 분석 폴링 관련 상태
  const [analysisTaskId, setAnalysisTaskId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [pollingError, setPollingError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingMainTimeoutRef = useRef<NodeJS.Timeout | null>(null); // 5분 타임아웃용

  // 📊 백그라운드 피드백 처리 상태
  const [isFeedbackProcessing, setIsFeedbackProcessing] = useState(false);
  const [feedbackProcessingError, setFeedbackProcessingError] = useState<string | null>(null);

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

  // 🆕 백엔드에서 생성된 base64 오디오 재생 함수
  const playBase64Audio = async (base64Data: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      try {
        console.log('🔊 Base64 오디오 재생 시작');
        setIsTTSPlaying(true);
        
        // 이전 오디오가 있으면 정지
        if (currentAudio) {
          currentAudio.pause();
          currentAudio.currentTime = 0;
        }
        
        // base64 → blob → Audio 객체 생성
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const audioBlob = new Blob([bytes], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        setCurrentAudio(audio);
        
        // 재생 완료 이벤트
        audio.onended = () => {
          console.log('✅ Base64 오디오 재생 완료');
          setIsTTSPlaying(false);
          setCurrentAudio(null);
          URL.revokeObjectURL(audioUrl); // 메모리 정리
          resolve();
        };
        
        // 재생 에러 이벤트
        audio.onerror = () => {
          console.error('❌ Base64 오디오 재생 실패');
          setIsTTSPlaying(false);
          setCurrentAudio(null);
          URL.revokeObjectURL(audioUrl); // 메모리 정리
          reject(new Error('Base64 오디오 재생 실패'));
        };
        
        // 오디오 재생 시작
        audio.play();
        
      } catch (error) {
        console.error('❌ TTS 호출 실패:', error);
        setIsTTSPlaying(false);
        setCurrentAudio(null);
        reject(error);
      }
    });
  };

  const stopTTS = () => {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
    }
    setIsTTSPlaying(false);
  };

  // 🆕 백엔드에서 받은 오디오들을 순차적으로 재생하는 함수
  const playSequentialAudio = async (response: any) => {
    try {
      console.log('🎵 순차 오디오 재생 시작');
      
      // 1. INTRO 오디오 재생
      if (response.intro_audio) {
        console.log('🎤 INTRO 오디오 재생');
        await playBase64Audio(response.intro_audio);
      }
      
      // 2. AI 질문 오디오 재생
      if (response.ai_question_audio) {
        console.log('🤖 AI 질문 오디오 재생');
        await playBase64Audio(response.ai_question_audio);
      }
      
      // 3. AI 답변 오디오 재생
      if (response.ai_answer_audio) {
        console.log('🤖 AI 답변 오디오 재생');
        await playBase64Audio(response.ai_answer_audio);
      }
      
      // 4. 사용자 질문 오디오 재생
      if (response.question_audio) {
        console.log('👤 사용자 질문 오디오 재생');
        await playBase64Audio(response.question_audio);
      }
      
      console.log('✅ 모든 오디오 재생 완료');
      
    } catch (error) {
      console.error('❌ 순차 오디오 재생 실패:', error);
      // TTS 실패해도 정상 진행
    }
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

  // AI 응답에서 resume_id 추출 및 Context 업데이트 함수
  const extractAndSaveAIResumeId = (response: any) => {
    try {
      console.log('🔍 AI resume_id 추출 시도 시작...');
      
      // 다양한 경로에서 AI 메타데이터 찾기
      const sources = [
        { name: 'ai_answer.metadata', data: response?.ai_answer?.metadata },
        { name: 'metadata', data: response?.metadata },
        { name: 'content.metadata', data: response?.content?.metadata },
        { name: 'turn_info.ai_metadata', data: response?.turn_info?.ai_metadata },
        { name: 'ai_response.metadata', data: response?.ai_response?.metadata },
        { name: 'content.ai_answer.metadata', data: response?.content?.ai_answer?.metadata }
      ];

      console.log('🔍 검색할 메타데이터 경로들:');
      sources.forEach((source, index) => {
        console.log(`  ${index + 1}. ${source.name}:`, source.data);
      });

      for (const source of sources) {
        if (source.data?.resume_id && typeof source.data.resume_id === 'number') {
          console.log(`✅ AI resume_id 추출 성공 (${source.name}):`, source.data.resume_id);
          dispatch({ type: 'SET_EXTRACTED_AI_RESUME_ID', payload: source.data.resume_id });
          return; // 첫 번째로 찾은 유효한 ID 사용
        }
      }

      console.log('⚠️ AI resume_id를 찾을 수 없습니다.');
    } catch (error) {
      console.warn('❌ AI resume_id 추출 중 오류:', error);
    }
  };

  // 🆕 텍스트를 TTS로 변환하여 재생하는 함수
  const generateAndPlayTTS = async (text: string, label: string = ""): Promise<void> => {
    if (!text || !text.trim()) {
      console.log(`[🔊 TTS] ${label} 텍스트가 비어있음 - TTS 건너뜀`);
      return;
    }

    // 🔊 TTS 확인용 주석입니다 - 실행된 TTS를 리스트에 추가
    const ttsEntry = {
      type: label,
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString()
    };
    setTtsList(prev => [...prev, ttsEntry]);

    try {
      console.log(`[🔊 TTS] ${label} TTS 생성 시작: ${text.slice(0, 50)}...`);
      
      // 백엔드 TTS API 호출
      const response = await fetch('http://localhost:8000/interview/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text.trim(),
          voice_id: "21m00Tcm4TlvDq8ikWAM" // Rachel 음성
        })
      });

      if (!response.ok) {
        throw new Error(`TTS API 오류: ${response.status}`);
      }

      const audioData = await response.arrayBuffer();
      console.log(`[🔊 TTS] ${label} TTS 생성 완료, 재생 시작`);

      // 오디오 재생
      const audioBlob = new Blob([audioData], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      // 재생 완료 대기
      await new Promise<void>((resolve, reject) => {
        audio.onended = () => {
          console.log(`[🔊 TTS] ${label} TTS 재생 완료`);
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.onerror = () => {
          console.error(`[🔊 TTS] ${label} TTS 재생 실패`);
          URL.revokeObjectURL(audioUrl);
          reject(new Error('TTS 재생 실패'));
        };
        audio.play().catch(reject);
      });

    } catch (error) {
      console.error(`[🔊 TTS] ${label} TTS 처리 실패:`, error);
    }
  };

  // 🔊 TTS 확인용 주석입니다 - 큐에 텍스트 추가 함수 (더 이상 사용하지 않음 - 동기적 수집 방식으로 변경)
  // const addToTTSQueue = (text: string, label: string = "") => {
  //   if (text && text.trim()) {
  //     setTtsQueue(prev => [...prev, text.trim()]);
  //     console.log(`🔊 [큐 추가] ${label}: ${text.substring(0, 50)}...`);
  //   }
  // };

  // 🔊 TTS 확인용 주석입니다 - 전달받은 항목들을 순차 처리
  const processTTSQueue = async (ttsItems: string[] = []) => {
    console.log(`🔊 [큐 처리] 함수 호출됨 - 처리할 항목 수: ${ttsItems.length}`);
    console.log(`🔊 [큐 처리] 처리 항목들:`, ttsItems.map(item => item.substring(0, 50) + '...'));
    
    if (ttsItems.length === 0) {
      console.log('🔊 [큐 처리] 처리할 TTS 없음 - 종료');
      return;
    }
    
    console.log(`🔊 [큐 처리] ${ttsItems.length}개 항목 순차 처리 시작`);
    
    for (let i = 0; i < ttsItems.length; i++) {
      const text = ttsItems[i];
      console.log(`🔊 [큐 처리] ${i + 1}/${ttsItems.length} 처리 중: ${text.substring(0, 50)}...`);
      
      try {
        await generateAndPlayTTS(text, `큐 처리 ${i + 1}`);
        console.log(`🔊 [큐 처리] ${i + 1}/${ttsItems.length} 완료`);
      } catch (error) {
        console.error(`🔊 [큐 처리] ${i + 1}/${ttsItems.length} 실패:`, error);
      }
    }
    
    console.log('🔊 [큐 처리] 모든 TTS 처리 완료');
  };

  // 🆕 백엔드 응답에서 TTS 처리 (동기적 수집 방식)
  const handleTTSFromResponse = async (response: any, task?: string, status?: string): Promise<string[]> => {
    try {
      console.log('[🔊 TTS] 응답에서 TTS 처리 시작');
      
      // 즉시 TTS: 인트로 메시지
      if (response.intro_message) {
        await generateAndPlayTTS(response.intro_message, "INTRO");
      }

      // 첫 질문은 즉시 TTS (사용자가 들어야 하니까)
      const isFirstQuestion = !state.questions || state.questions.length === 0;
      if (isFirstQuestion && response.content?.content) {
        await generateAndPlayTTS(response.content.content, "첫 질문");
        return []; // 첫 질문은 즉시 처리했으므로 빈 배열 반환
      } else {
        // 🔊 TTS 처리를 위한 항목들을 동기적으로 수집
        const ttsItems: string[] = [];
        
        // 🔊 백엔드에서 제공한 순서대로 수집
        if (response.tts_queue && Array.isArray(response.tts_queue)) {
          console.log(`🔊 [백엔드 큐] ${response.tts_queue.length}개 항목을 순서대로 수집`);
          response.tts_queue.forEach((item: any, index: number) => {
            if (item.content) {
              console.log(`🔊 [백엔드 큐] ${index + 1}. ${item.type}: ${item.content.substring(0, 50)}...`);
              ttsItems.push(item.content);
            }
          });
        } else {
          // 🔊 기존 방식 fallback - 생성 순서대로 수집
          console.log('🔊 [백엔드 큐] tts_queue 없음 - 기존 방식으로 수집');
          
          if (response.ai_question?.content) {
            console.log(`🔊 [수집] AI 질문: ${response.ai_question.content.substring(0, 50)}...`);
            ttsItems.push(response.ai_question.content);
          }
          if (response.ai_answer?.content) {
            console.log(`🔊 [수집] AI 답변: ${response.ai_answer.content.substring(0, 50)}...`);
            ttsItems.push(response.ai_answer.content);
          }
          if (response.content?.content || response.content?.question) {
            const questionText = response.content.content || response.content.question;
            console.log(`🔊 [수집] 사용자 질문: ${questionText.substring(0, 50)}...`);
            ttsItems.push(questionText);
          }
          
          // 🔊 면접 종료 시 종료 메시지 처리 (백엔드 message 필드 사용)
          if (response.message && (task === 'end_interview' || status === 'completed')) {
            console.log(`🔊 [수집] 면접 종료 메시지: ${response.message.substring(0, 50)}...`);
            ttsItems.push(response.message);
          }
        }
        
        console.log(`[🔊 TTS] 응답 TTS 처리 완료 - ${ttsItems.length}개 항목 수집됨`);
        return ttsItems;
      }
      
    } catch (error) {
      console.error('[🔊 TTS] 응답 TTS 처리 중 오류:', error);
      return [];
    }
  };

  // 🔊 TTS 확인용 주석입니다 - TTS 이력 출력 함수
  const showTTSHistory = () => {
    console.log('🔊 === TTS 실행 이력 전체 목록 ===');
    ttsList.forEach((entry, index) => {
      console.log(`${index + 1}. [${entry.timestamp}] ${entry.type}: ${entry.text.substring(0, 50)}${entry.text.length > 50 ? '...' : ''}`);
    });
    console.log(`🔊 총 ${ttsList.length}개의 TTS가 실행되었습니다.`);
    console.log('🔊 === TTS 이력 종료 ===');
  };


  // 🆕 백엔드 응답에 따른 currentPhase 업데이트 함수 + TTS 처리
  const updatePhaseFromResponse = async (response: any): Promise<{ ttsItems: string[], isEndInterview: boolean }> => {
    console.log('🔄 === 전체 응답 구조 분석 START ===');
    console.log('📋 응답 객체 전체:', JSON.stringify(response, null, 2));
    console.log('🔍 메타데이터 분석:');
    console.log('  - response.metadata:', response?.metadata);
    console.log('  - response.ai_answer:', response?.ai_answer);
    console.log('  - response.ai_answer?.metadata:', response?.ai_answer?.metadata);
    console.log('  - response.content:', response?.content);
    console.log('  - response.turn_info:', response?.turn_info);
    console.log('🔄 === 전체 응답 구조 분석 END ===');
    
    // AI 응답에서 resume_id 추출 및 Context 업데이트
    extractAndSaveAIResumeId(response);
    
    // 변수들을 먼저 추출
    const nextAgent = response?.metadata?.next_agent;
    const task = response?.metadata?.task;
    const status = response?.status;
    
    // 🆕 TTS 처리 - 하이브리드 방식 (즉시 + 수집)
    const collectedTTSItems = await handleTTSFromResponse(response, task, status);
    const turnInfo = response?.turn_info;

    console.log('🔍 Phase 판단:', { nextAgent, task, status, turnInfo });

    if (task === 'end_interview' || status === 'completed') {
        // 🔊 end_interview 시에는 TTS 처리 후 면접 완료 처리를 submitAnswer에서 수행
        console.log('🔍 면접 종료 응답 감지 - TTS 처리 후 완료 처리 예정');
        // 임시로 사용자 턴으로 설정 (TTS 처리 후 변경될 예정)
        setCurrentPhase('user_turn');
        setCurrentTurn('user');
        setIsTimerActive(false);
        setCanSubmit(false);
        console.log('✅ 면접 완료로 설정됨');

        // 👁️ 시선 추적 녹화만 중지 (분석은 면접 완전 완료 후 실행)
        if (isGazeRecording) {
          console.log('👁️ 면접 완료 - 시선 추적 녹화 중지');
          stopGazeRecording();
        }
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

    // AI 질문, 답변 및 사용자 질문 TTS 처리
    const aiQuestion = response?.ai_question?.content;
    const aiAnswer = response?.ai_answer?.content || response?.ai_response?.content;
    const question = response?.content?.content;
    
    if (question) {
        setCurrentQuestion(question);
        console.log('📝 질문 업데이트:', question);
    }
    
    // AI 질문 상태 업데이트
    if (aiQuestion && aiQuestion.trim()) {
        setCurrentAIQuestion(aiQuestion);
        console.log('🤖 AI 질문 상태 업데이트:', aiQuestion);
    }
    
    // AI 답변 상태 업데이트
    if (aiAnswer && aiAnswer.trim()) {
        setCurrentAIAnswer(aiAnswer);
        console.log('🤖 AI 답변 상태 업데이트:', aiAnswer);
    }

    // 🆕 백엔드에서 전달된 텍스트 데이터들을 확인하고 순차 TTS 재생
    console.log('🔍 백엔드 텍스트 데이터 분석:');
    console.log('  - INTRO 메시지 존재:', !!response.intro_message, response.intro_message ? `(${response.intro_message.length}자)` : '');
    console.log('  - AI 질문 텍스트 존재:', !!response.ai_question?.content, response.ai_question?.content ? `(${response.ai_question.content.length}자)` : '');
    console.log('  - AI 답변 텍스트 존재:', !!response.ai_answer?.content, response.ai_answer?.content ? `(${response.ai_answer.content.length}자)` : '');
    console.log('  - 사용자 질문 텍스트 존재:', !!response.content?.content, response.content?.content ? `(${response.content.content.length}자)` : '');
    
    // 🔊 TTS 확인용 주석입니다 - 큐 시스템으로 대체됨 (중복 방지)
    
    // 🎤 녹음 권한 및 상태 업데이트
    updateVoicePermissions();
    
    // 🔊 수집된 TTS 항목들 반환 (end_interview 플래그 포함)
    const isEndInterview = task === 'end_interview' || status === 'completed';
    return { ttsItems: collectedTTSItems, isEndInterview };
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

  // 🆕 사용자 턴 상태 설정 헬퍼 함수
  const setUserTurnState = (question: string, source: string) => {
    console.log(`✅ 사용자 턴 설정 (${source}):`, question);
    setCurrentPhase('user_turn');
    setCurrentTurn('user');
    setIsTimerActive(true);
    setTimeLeft(120);
    setCanSubmit(true);
    setCanRecord(true);
    setCurrentQuestion(question);
  };

  // 🆕 초기 턴 상태 설정 (세션 로드 완료 후)
  useEffect(() => {
    if (!isRestoring && state.sessionId) {
      console.log('🚀 초기 턴 상태 설정');
      
      // 면접 시작 시 받은 응답에서 턴 정보 확인
      const checkInitialTurnStatus = async () => {
        try {
          // 1. 먼저 localStorage에서 면접 시작 응답 확인 (유틸리티 함수 사용)
          debugInterviewState(); // 디버그 정보 출력
          const parsedState = getInterviewState();
          if (parsedState) {
            console.log('📦 localStorage에서 면접 상태 확인:', parsedState);
            
            // 🆕 API 호출이 필요한 경우 (환경 체크에서 온 경우) + 중복 방지 강화
            if (parsedState.needsApiCall && !parsedState.apiCallCompleted) {
              console.log('🎯 API 호출 조건 충족: needsApiCall=true, apiCallCompleted=false');
              
              // 🚦 메모리 기반 중복 호출 체크 (React Strict Mode 대응)
              if (isApiCallInProgress(parsedState.sessionId) || isApiCallInProgressRef.current) {
                console.log('⚠️ API 이미 진행 중 - 중복 호출 방지 (메모리 기반)');
                return;
              }
              
              console.log('🚀 환경 체크에서 온 새로운 면접 - 첫 질문 로딩 시작');
              setCurrentQuestion("첫 번째 질문을 준비하고 있습니다...");
              setCurrentPhase('waiting');
              setCurrentTurn('waiting');
              setIsLoading(true);
              
              // 🚦 호출 진행 상태 설정 (메모리 + 전역)
              isApiCallInProgressRef.current = true;
              setApiCallInProgress(parsedState.sessionId, true);
              
              try {
                // 🆕 AbortController 설정 (cleanup을 위한)
                const abortController = new AbortController();
                apiCallCancelRef.current = abortController;
                
                let response: any;
                const finalSettings = parsedState.settings;
                
                if (finalSettings.mode === 'ai_competition') {
                  console.log('🤖 AI 경쟁 모드 - API 호출 시작');
                  response = await interviewApi.startAICompetition(finalSettings);
                } else {
                  console.log('👤 일반 모드 - API 호출 시작');
                  response = await interviewApi.startInterview(finalSettings);
                }
                
                // AbortController 확인 (호출이 취소되었으면 중단)
                if (abortController.signal.aborted) {
                  console.log('⚠️ API 호출이 취소됨 - 처리 중단');
                  return;
                }
                
                console.log('✅ 첫 질문 로딩 완료:', response);
                
                // 🔧 백엔드에서 받은 실제 세션 ID로 업데이트
                if (response.session_id) {
                  console.log('🔄 세션 ID 업데이트:', parsedState.sessionId, '->', response.session_id);
                  
                  // Context 업데이트
                  dispatch({ type: 'SET_SESSION_ID', payload: response.session_id });
                  
                  // localStorage도 즉시 업데이트 (나중에 다시 업데이트하지만 일관성을 위해)
                  parsedState.sessionId = response.session_id;
                }
                
                // 질문 처리 함수 (response를 파라미터로 받음)
                const processQuestion = (apiResponse: any) => {
                  const responseContent = apiResponse?.content;
                  const contentText = responseContent?.content;
                  const contentType = responseContent?.type;
                  
                  if (apiResponse && contentText) {
                    try {
                      console.log('📝 컨텐츠 추출 성공:', contentText, '타입:', contentType);
                      
                      // 일반 질문 처리 (HR, TECH, COLLABORATION 등)
                      const questionData = {
                        id: `q_${Date.now()}`,
                        question: contentText,
                        category: contentType || 'HR',
                        time_limit: 120,
                        keywords: []
                      };
                        
                      dispatch({ 
                        type: 'ADD_QUESTION', 
                        payload: questionData
                      });
                      
                      setCurrentQuestion(questionData.question);
                      console.log('✅ 질문 설정 완료:', questionData.question);
                      
                      // 면접 시작
                      setUserTurnState(questionData.question, "API 로딩");
                      
                      return questionData; // questionData 반환
                      
                    } catch (error) {
                      console.error('❌ 컨텐츠 처리 실패:', error);
                      setCurrentQuestion("컨텐츠를 처리하는 중 오류가 발생했습니다.");
                    }
                  } else {
                    console.warn('⚠️ API 응답에 컨텐츠가 없습니다:', apiResponse);
                    setCurrentQuestion("컨텐츠를 받지 못했습니다. 새로고침해주세요.");
                  }
                  return null;
                };

                // 🆕 질문 데이터 먼저 처리 (INTRO 여부와 관계없이)
                console.log('📝 질문 데이터 처리 시작');
                const questionData = processQuestion(response);
                
                // 🆕 INTRO 메시지 처리 (텍스트 표시용)
                const introMessageFromResponse = (response as any)?.intro_message;
                if (introMessageFromResponse) {
                  console.log('📢 응답에서 INTRO 메시지 감지:', introMessageFromResponse);
                  setIntroMessage(introMessageFromResponse);
                  setHasIntroMessage(true);
                  setShowIntroMessage(true);
                  
                  // INTRO 표시 후 잠시 후 숨기기 (TTS는 백엔드에서 자동 처리됨)
                  setTimeout(() => {
                    setShowIntroMessage(false);
                    setHasIntroMessage(false);
                  }, 3000); // 3초 후 숨김
                  
                  console.log('📢 INTRO 메시지 표시 - TTS는 백엔드에서 자동 처리');
                } else {
                  console.log('📝 INTRO 메시지 없음 - 바로 질문 진행');
                }
                
                // 🆕 첫 번째 응답에서도 TTS 재생 처리
                console.log('🎵 첫 번째 응답 TTS 재생 처리 시작');
                const { ttsItems: firstResponseTTSItems, isEndInterview: firstEndInterview } = await updatePhaseFromResponse(response);
                await processTTSQueue(firstResponseTTSItems);
                
                // 첫 응답에서는 일반적으로 end_interview가 아니지만 혹시 모르니 처리
                if (firstEndInterview) {
                  showTTSHistory();
                  setCurrentPhase('interview_completed');
                  setCurrentTurn('waiting');
                  setIsTimerActive(false);
                  setCanSubmit(false);
                }
                
                setIsLoading(false);
                
                // 🆕 즉시 API 호출 완료 상태로 업데이트 (재호출 방지)
                markApiCallCompleted(response);
                
                // 🚦 로컬 호출 상태 리셋
                isApiCallInProgressRef.current = false;
                apiCallCancelRef.current = null;
                
                console.log('💾 localStorage 즉시 업데이트 완료 - 재호출 방지');
                console.log('✅ 첫 질문 로딩 및 면접 시작 완료');
                return;
                
              } catch (error) {
                console.error('❌ 첫 질문 로딩 실패:', error);
                
                // AbortError인 경우 (cleanup에 의한 취소) 별도 처리
                if (error instanceof Error && error.name === 'AbortError') {
                  console.log('⚠️ API 호출이 cleanup에 의해 취소됨');
                  return;
                }
                
                setCurrentQuestion("질문 로딩에 실패했습니다. 새로고침해주세요.");
                setIsLoading(false);
                setCurrentPhase('unknown');
                setCurrentTurn('waiting');
                
                // 🆕 에러 상황에서도 재호출 방지 플래그 설정 (유틸리티 사용)
                const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
                markApiCallCompleted(undefined, errorMessage);
                
                // 🚦 로컬 호출 상태 리셋
                isApiCallInProgressRef.current = false;
                apiCallCancelRef.current = null;
                
                console.log('💾 API 에러 상태로 localStorage 업데이트 (재호출 방지)');
                
                alert(`면접 시작에 실패했습니다: ${errorMessage}\n\n다시 시도해주세요.`);
                return;
              }
            }
            
            // 🆕 API 호출이 이미 완료된 경우 (중복 호출 방지)
            if (parsedState.needsApiCall && parsedState.apiCallCompleted) {
              console.log('⚠️ API 이미 호출 완료됨 - 재호출 건너뛰기');
              console.log('📄 저장된 응답 사용:', parsedState.interviewStartResponse);
              
              // 저장된 응답이 있으면 그것을 사용
              if (parsedState.interviewStartResponse) {
                const { ttsItems: savedResponseTTSItems, isEndInterview: savedEndInterview } = await updatePhaseFromResponse(parsedState.interviewStartResponse);
                await processTTSQueue(savedResponseTTSItems);
                
                // 저장된 응답이 end_interview인 경우 처리
                if (savedEndInterview) {
                  showTTSHistory();
                  setCurrentPhase('interview_completed');
                  setCurrentTurn('waiting');
                  setIsTimerActive(false);
                  setCanSubmit(false);
                  return;
                }
                const question = parsedState.interviewStartResponse.content?.content || "질문을 불러오는 중...";
                setUserTurnState(question, "저장된 응답");
                return;
              }
            }
            
            // 면접 시작 응답에서 턴 정보 확인 (기존 로직)
            if (parsedState.interviewStartResponse && parsedState.interviewStartResponse.status === 'waiting_for_user') {
              const question = parsedState.interviewStartResponse.content?.content || "질문을 불러오는 중...";
              setUserTurnState(question, "localStorage");
              return;
            }
          }
          
          // 2. localStorage에 없으면 현재 면접 상태만 확인 (API 재호출 없이)
          console.log('🔄 현재 면접 상태 확인');
          const currentSettings = state.settings;
          if (currentSettings) {
            console.log('✅ AI 경쟁 면접 기본값으로 사용자 턴 설정');
            setUserTurnState("면접을 시작합니다. 첫 번째 질문을 기다려주세요.", "기본값");
            return;
          }
          
          // 3. 세션 상태 확인 (fallback)
          const sessionState = await sessionApi.getSessionState(state.sessionId!);
          console.log('📋 초기 세션 상태:', sessionState);
          
          // 세션 상태에서 턴 정보 확인
          if (sessionState && sessionState.state?.status) {
            const status = sessionState.state.status;
            console.log('🔍 초기 세션에서 턴 상태 발견:', status);
            
            if (status === 'waiting_for_user') {
              const question = sessionState.state?.current_question || "질문을 불러오는 중...";
              setUserTurnState(question, "세션 상태");
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
    
    // 🧹 Cleanup 함수 - 컴포넌트 언마운트 또는 의존성 변경 시 API 호출 취소
    return () => {
      if (apiCallCancelRef.current) {
        console.log('🧹 useEffect cleanup - API 호출 취소');
        apiCallCancelRef.current.abort();
        apiCallCancelRef.current = null;
      }
      // 로컬 호출 상태 리셋
      isApiCallInProgressRef.current = false;
    };
  }, [isRestoring, state.sessionId, dispatch]);

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
      
      // 백엔드 응답에 따른 턴 상태 업데이트 + TTS 수집
      const { ttsItems, isEndInterview } = await updatePhaseFromResponse(result);
      
      // 🔊 TTS 확인용 주석입니다 - 수집된 TTS 항목들을 순차 처리
      await processTTSQueue(ttsItems);
      
      // 🔊 면접 종료 시 완료 처리
      if (isEndInterview) {
        console.log('🔊 면접 종료 TTS 처리 완료 - 면접 완료 상태로 변경');
        
        // TTS 이력 출력
        showTTSHistory();
        
        // 면접 완료 상태로 변경
        setCurrentPhase('interview_completed');
        setCurrentTurn('waiting');
        setIsTimerActive(false);
        setCanSubmit(false);
        console.log('✅ 면접 완료로 설정됨');

        // 🆕 면접 완전 완료 후 분석 작업 시작
        console.log('🔍 면접 완료 - 분석 작업 준비 중...');
        console.log('📊 gazeBlob 상태:', !!gazeBlob, gazeBlob?.size);
        console.log('👁️ calibrationSessionId:', state.gazeTracking?.calibrationSessionId);

        // 👁️ 시선 분석 시작
        if (gazeBlob && state.gazeTracking?.calibrationSessionId) {
          console.log('👁️ 면접 완료 - 시선 분석 시작');
          setTimeout(() => {
            uploadAndAnalyzeGaze();
          }, 1000); // blob 안정화를 위한 1초 대기
        } else {
          console.log('⚠️ 시선 분석 조건 미충족:', {
            hasGazeBlob: !!gazeBlob,
            hasCalibrationSessionId: !!state.gazeTracking?.calibrationSessionId
          });
        }

        // 📊 면접 피드백 처리 시작
        console.log('📊 면접 완료 - 백그라운드 피드백 처리 시작');
        setIsFeedbackProcessing(true);
        setFeedbackProcessingError(null);
        
        try {
          triggerBackgroundFeedback([]);
        } catch (error) {
          console.error('❌ 백그라운드 피드백 처리 시작 실패:', error);
          setFeedbackProcessingError('피드백 처리를 시작할 수 없습니다.');
          setIsFeedbackProcessing(false);
        }
      }
      
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

  // 👁️ 시선 추적 녹화 시작
  const startGazeRecording = async () => {
    // 캘리브레이션 세션 ID 확인
    const calibrationSessionId = state.gazeTracking?.calibrationSessionId;
    if (!calibrationSessionId) {
      console.log('⚠️ 캘리브레이션 정보가 없어 시선 추적을 건너뜁니다.');
      return;
    }

    try {
      // 화면 + 웹캠 스트림 가져오기
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: false // 음성은 별도로 녹음
      });

      if (gazeVideoRef.current) {
        gazeVideoRef.current.srcObject = stream;
      }

      // MediaRecorder 설정
      let mimeType = 'video/webm;codecs=vp8';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm';
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      gazeMediaRecorderRef.current = mediaRecorder;
      gazeChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          gazeChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(gazeChunksRef.current, { type: mimeType });
        setGazeBlob(blob);
        console.log('👁️ 시선 추적 녹화 완료, 크기:', blob.size);

        // 스트림 정리
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        console.error('❌ 시선 추적 녹화 오류:', event);
        setGazeError('시선 추적 녹화 중 오류가 발생했습니다.');
      };

      mediaRecorder.start();
      setIsGazeRecording(true);
      console.log('👁️ 시선 추적 녹화 시작');

    } catch (error) {
      console.error('❌ 시선 추적 녹화 시작 실패:', error);
      setGazeError('시선 추적을 시작할 수 없습니다.');
    }
  };

  // 👁️ 시선 추적 녹화 중지
  const stopGazeRecording = () => {
    if (gazeMediaRecorderRef.current && isGazeRecording) {
      gazeMediaRecorderRef.current.stop();
      setIsGazeRecording(false);
      console.log('👁️ 시선 추적 녹화 중지');
    }
  };

  // 👁️ 시선 추적 비디오 업로드 및 분석
  const uploadAndAnalyzeGaze = async () => {
    if (!gazeBlob || !state.sessionId) {
      console.log('⚠️ 시선 비디오 또는 세션 ID가 없어 분석을 건너뜁니다.');
      return;
    }

    const calibrationSessionId = state.gazeTracking?.calibrationSessionId;
    if (!calibrationSessionId) {
      console.log('⚠️ 캘리브레이션 세션 ID가 없어 분석을 건너뜁니다.');
      return;
    }

    try {
      console.log('👁️ 시선 비디오 업로드 시작...');

      // 1. 비디오 업로드
      const formData = new FormData();
      formData.append('file', gazeBlob, 'gaze-recording.webm');
      formData.append('file_type', 'video');
      formData.append('interview_id', state.sessionId);

      const uploadResponse = await apiClient.post<UploadResponse>('/test/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const videoUrl = uploadResponse.data.play_url;
      console.log('✅ 시선 비디오 업로드 완료:', videoUrl);

      // 2. 시선 분석 요청
      console.log('👁️ 시선 분석 시작...');
      const analysisResponse = await apiClient.post<VideoAnalysisResponse>('/test/gaze/analyze', {
        video_url: videoUrl,
        session_id: calibrationSessionId
      });

      const taskId = analysisResponse.data.task_id;
      console.log('✅ 시선 분석 작업 시작:', taskId);

      // 3. taskId를 상태에 설정하여 useEffect 폴링 트리거
      setAnalysisTaskId(taskId);
      setIsPolling(true);
      setPollingError(null);

    } catch (error) {
      console.error('❌ 시선 분석 프로세스 실패:', error);
      setGazeError('시선 분석을 완료할 수 없습니다.');
    }
  };

  // 👁️ 분석 결과를 Supabase에 저장
  const saveGazeAnalysisToDatabase = async (result: GazeAnalysisResult) => {
    try {
      const user = tokenManager.getUser();
      const userId = user?.user_id;
      const calibrationSessionId = state.gazeTracking?.calibrationSessionId;

      if (!userId || !state.sessionId || !calibrationSessionId) {
        console.error('❌ 필수 정보 누락:', { userId, sessionId: state.sessionId, calibrationSessionId });
        return;
      }

      // Supabase gaze_analysis 테이블에 저장
      const saveResponse = await apiClient.post('/gaze/analysis/save', {
        interview_id: parseInt(state.sessionId),
        user_id: userId,
        calibration_session_id: calibrationSessionId,
        gaze_score: result.gaze_score,
        jitter_score: result.jitter_score,
        compliance_score: result.compliance_score,
        stability_rating: result.stability_rating
      });

      console.log('✅ 시선 분석 결과 DB 저장 완료:', saveResponse.data);

    } catch (error) {
      console.error('❌ 시선 분석 결과 DB 저장 실패:', error);
      // DB 저장 실패해도 면접 진행에는 영향 없도록 처리
    }
  };

  // 🆕 필요한 데이터 추출 함수들
  const getCurrentUserId = (): number => {
    // 실제 로그인된 사용자 ID 가져오기
    const user = tokenManager.getUser();
    if (user && user.user_id) {
      return user.user_id;
    }
    
    // 로그인되지 않은 경우 에러 로그
    console.error('❌ 로그인된 사용자를 찾을 수 없습니다.');
    throw new Error('로그인된 사용자 정보가 없습니다.');
  };

  const getUserResumeId = (): number | null => {
    console.log('🔍 getUserResumeId 호출 시작...');
    
    // 1순위: Context에 저장된 이력서 데이터에서 추출
    if (state.resume?.id) {
      const resumeId = parseInt(state.resume.id);
      console.log('📋 Context에서 찾은 resume ID:', state.resume.id, '-> 파싱 결과:', resumeId);
      
      if (!isNaN(resumeId)) {
        // 추가 검증: 로그인된 사용자와 이력서 사용자 정보 매칭 확인
        const currentUser = tokenManager.getUser();
        console.log('🔍 이메일 매칭 확인:', {
          resumeEmail: state.resume.email,
          currentUserEmail: currentUser?.email,
          isMatch: state.resume.email === currentUser?.email
        });
        
        if (currentUser && state.resume.email === currentUser.email) {
          console.log('✅ Context에서 유효한 user_resume_id 반환:', resumeId);
          return resumeId;
        } else {
          console.warn('⚠️ 이력서 소유자와 로그인 사용자가 다릅니다.');
        }
      } else {
        console.warn('⚠️ resume.id 파싱 실패:', state.resume.id);
      }
    } else {
      console.warn('⚠️ Context에 resume 데이터가 없습니다.');
    }
    
    // 2순위: 로그인된 사용자 정보로 추정
    const currentUser = tokenManager.getUser();
    if (currentUser?.user_id) {
      console.log('🔍 로그인된 사용자 정보로 user_resume 추정 시도:', currentUser.user_id);
      // TODO: API 호출로 user_id에 해당하는 user_resume_id 조회
      // 지금은 Context 데이터가 없으면 null 반환
    }
    
    console.log('❌ user_resume_id를 찾을 수 없어 null 반환');
    return null;
  };

  const getAIResumeId = (): number | null => {
    // 1순위: AI 응답에서 추출된 resume_id 사용 (가장 정확함)
    if (state.textCompetitionData?.extracted_ai_resume_id) {
      console.log('✅ 추출된 AI resume_id 사용:', state.textCompetitionData.extracted_ai_resume_id);
      return state.textCompetitionData.extracted_ai_resume_id;
    }
    
    // 2순위: 기존 aiPersona에서 resume_id 찾기
    if (state.textCompetitionData?.aiPersona?.resume_id) {
      console.log('⚠️ aiPersona에서 resume_id 사용:', state.textCompetitionData.aiPersona.resume_id);
      return state.textCompetitionData.aiPersona.resume_id;
    }
    
    // 3순위: settings에서 ai_resume_id가 있다면 사용 (create_persona_for_interview에서 전달될 수 있음)
    if (state.settings && 'ai_resume_id' in state.settings) {
      const aiResumeId = (state.settings as any).ai_resume_id;
      if (aiResumeId && aiResumeId !== 0) {
        console.log('⚠️ settings에서 resume_id 사용:', aiResumeId);
        return aiResumeId;
      }
    }
    
    // DB 제약조건 위반 방지를 위해 null 반환 (ai_resume_id=0은 존재하지 않음)
    console.log('❌ AI resume_id를 찾을 수 없어 null 반환');
    return null;
  };

  const getPostingId = (): number | null => {
    // TODO: 채용공고 ID를 가져오는 로직 구현 필요
    return state.settings?.posting_id || null;
  };

  const getCompanyId = (): number | null => {
    // 1순위: jobPosting에서 company_id 추출 (create_persona_for_interview에서 사용하는 방식)
    if (state.jobPosting?.company_id) {
      return state.jobPosting.company_id;
    }
    
    // 2순위: settings에서 posting_id를 통해 company_id 추출하려면 추가 API 호출이 필요
    // 현재는 posting_id만 있으므로 null 반환
    return null;
  };

  const getPositionId = (): number | null => {
    // 1순위: jobPosting에서 position_id 추출 (create_persona_for_interview에서 사용하는 방식)
    if (state.jobPosting?.position_id) {
      return state.jobPosting.position_id;
    }
    
    // 2순위: settings에서 posting_id를 통해 position_id 추출하려면 추가 API 호출이 필요
    // 현재는 posting_id만 있으므로 null 반환
    return null;
  };

  // 🆕 피드백 처리 함수들
  const triggerBackgroundFeedback = async (qaHistory: any[]) => {
    try {
      // 🔊 TTS 확인용 주석입니다 - 전체 TTS 실행 이력 출력
      console.log('🔊 === TTS 실행 이력 전체 목록 ===');
      ttsList.forEach((entry, index) => {
        console.log(`${index + 1}. [${entry.timestamp}] ${entry.type}: ${entry.text.substring(0, 50)}${entry.text.length > 50 ? '...' : ''}`);
      });
      console.log(`🔊 총 ${ttsList.length}개의 TTS가 실행되었습니다.`);
      console.log('🔊 === TTS 이력 종료 ===');
      
      console.log('🔄 백그라운드 피드백 처리 시작...');
      
      // qa_history를 사용자와 AI로 분리
      const userQAHistory = qaHistory.filter(qa => qa.answerer === "user");
      const aiQAHistory = qaHistory.filter(qa => qa.answerer === "ai");
      
      console.log(`📊 분리된 QA - 사용자: ${userQAHistory.length}개, AI: ${aiQAHistory.length}개`);
      
      // 현재 Context 상태 전체 로깅
      console.log('🔍 === Context 상태 분석 START ===');
      console.log('state.resume:', state.resume);
      console.log('state.textCompetitionData:', state.textCompetitionData);
      console.log('state.settings:', state.settings);
      console.log('state.jobPosting:', state.jobPosting);
      const currentUser = tokenManager.getUser();
      console.log('currentUser:', currentUser);
      console.log('🔍 === Context 상태 분석 END ===');
      
      // 필수 데이터 검증
      let userId: number;
      try {
        userId = getCurrentUserId();
        console.log(`✅ 사용자 ID 확인: ${userId}`);
      } catch (error) {
        console.error('❌ 사용자 ID를 가져올 수 없습니다:', error);
        throw new Error('로그인이 필요합니다.');
      }
      
      const userResumeId = getUserResumeId();
      const aiResumeId = getAIResumeId();
      const postingId = getPostingId();
      const companyId = getCompanyId();
      const positionId = getPositionId();
      
      console.log('📋 데이터 검증 결과:', {
        userId,
        userResumeId,
        aiResumeId,
        postingId,
        companyId,
        positionId
      });
      
      // 2개의 평가 요청 생성
      const evaluationRequests = [
        // 사용자 평가 요청
        {
          user_id: userId,
          user_resume_id: userResumeId,
          ai_resume_id: null,
          posting_id: postingId,
          company_id: companyId,
          position_id: positionId,
          qa_pairs: userQAHistory.map(qa => ({
            question: qa.question,
            answer: qa.answer,
            duration: qa.duration || 120,
            question_level: qa.question_level || 1
          }))
        },
        // AI 지원자 평가 요청
        {
          user_id: userId,
          user_resume_id: null,
          ai_resume_id: aiResumeId,
          posting_id: postingId,
          company_id: companyId,
          position_id: positionId,
          qa_pairs: aiQAHistory.map(qa => ({
            question: qa.question,
            answer: qa.answer,
            duration: qa.duration || 120,
            question_level: qa.question_level || 1
          }))
        }
      ];

      console.log('📤 피드백 평가 API 호출 중...');
      
      // 피드백 평가 API 호출
      const response = await apiClient.post<FeedbackEvaluationResponse>('/interview/feedback/evaluate', evaluationRequests);
      const result = response.data;
      console.log('✅ 피드백 평가 완료:', result);

      // 계획 생성 API 호출 (옵션)
      if (result.success && result.results) {
        for (const evalResult of result.results) {
          if (evalResult.interview_id) {
            try {
              const planResponse = await apiClient.post('/interview/feedback/plans', { 
                interview_id: evalResult.interview_id 
              });
              
              console.log(`✅ 면접 계획 생성 완료 (ID: ${evalResult.interview_id}):`, planResponse.data);
            } catch (planError) {
              console.error(`❌ 면접 계획 생성 실패 (ID: ${evalResult.interview_id}):`, planError);
            }
          }
        }
      }

      console.log('🎉 모든 백그라운드 피드백 처리 완료');
      setIsFeedbackProcessing(false);
      setFeedbackProcessingError(null);

    } catch (error) {
      console.error('❌ 백그라운드 피드백 처리 실패:', error);
      setFeedbackProcessingError('피드백 처리 중 오류가 발생했습니다.');
      setIsFeedbackProcessing(false);
    }
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
      // 👁️ 시선 추적 정리
      if (gazeMediaRecorderRef.current && isGazeRecording) {
        stopGazeRecording();
      }
    };
  }, []);

  // 👁️ 면접 시작 시 자동으로 시선 추적 시작
  useEffect(() => {
    const startAutoGazeTracking = async () => {
      // 캘리브레이션 세션 ID가 있고, 아직 녹화 중이 아닐 때만 시작
      const calibrationSessionId = state.gazeTracking?.calibrationSessionId;
      if (calibrationSessionId && !isGazeRecording && !isRestoring) {
        console.log('👁️ 면접 페이지 진입 - 시선 추적 자동 시작');
        await startGazeRecording();
      }
    };

    startAutoGazeTracking();
  }, [state.gazeTracking?.calibrationSessionId, isRestoring, isGazeRecording, startGazeRecording]);

  // 👁️ 시선 분석 상태 폴링 useEffect
  useEffect(() => {
    if (!analysisTaskId || !isPolling) {
      return;
    }

    console.log('🔄 시선 분석 폴링 시작:', analysisTaskId);

    const stopPolling = () => {
      // 모든 타이머 정리
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      if (pollingMainTimeoutRef.current) {
        clearTimeout(pollingMainTimeoutRef.current);
        pollingMainTimeoutRef.current = null;
      }
    };

    const pollAnalysisStatus = async () => {
      try {
        const statusResponse = await apiClient.get<AnalysisStatusResponse>(`/test/gaze/analyze/status/${analysisTaskId}`);
        const statusData = statusResponse.data;

        if (statusData.status === 'completed' && statusData.result) {
          // 분석 완료
          console.log('🎉 시선 분석 완료:', statusData.result);
          setGazeAnalysisResult(statusData.result);
          setIsPolling(false);
          setPollingError(null);
          stopPolling(); // 모든 타이머 정리
          
          // DB에 결과 저장
          try {
            await saveGazeAnalysisToDatabase(statusData.result);
          } catch (saveError) {
            console.error('❌ DB 저장 실패:', saveError);
            // DB 저장 실패해도 분석 결과는 유지
          }

        } else if (statusData.status === 'failed') {
          // 분석 실패
          console.error('❌ 시선 분석 실패:', statusData.error);
          setGazeError('시선 분석에 실패했습니다.');
          setIsPolling(false);
          setPollingError('시선 분석에 실패했습니다.');
          stopPolling(); // 모든 타이머 정리
        }
        // 진행 중인 경우는 계속 폴링
      } catch (error) {
        console.error('❌ 분석 상태 체크 실패:', error);
        setPollingError('시선 분석 상태를 확인할 수 없습니다.');
        // 에러가 발생해도 폴링은 계속 진행 (네트워크 일시 오류일 수 있음)
      }
    };

    // 첫 번째 상태 체크 (5초 후)
    pollingTimeoutRef.current = setTimeout(() => {
      pollAnalysisStatus();
      
      // 그 이후 5초마다 반복
      pollingIntervalRef.current = setInterval(pollAnalysisStatus, 5000);
    }, 5000);

    // 5분 후 타임아웃 처리
    pollingMainTimeoutRef.current = setTimeout(() => {
      console.warn('⏰ 시선 분석 타임아웃 (5분)');
      setIsPolling(false);
      setPollingError('시선 분석이 시간 초과되었습니다.');
      setGazeError('시선 분석이 시간 초과되었습니다.');
      
      // 피드백 처리도 함께 정리 (장시간 실행된 경우)
      if (isFeedbackProcessing) {
        setIsFeedbackProcessing(false);
        setFeedbackProcessingError('분석이 시간 초과되어 중단되었습니다.');
      }
      
      stopPolling(); // 타임아웃 시에도 모든 타이머 정리
    }, 5 * 60 * 1000); // 5분

    // Cleanup function - 컴포넌트 언마운트나 의존성 변경 시
    return stopPolling;
  }, [analysisTaskId, isPolling, saveGazeAnalysisToDatabase]);

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

            {/* 👁️ 시선 추적용 숨겨진 비디오 */}
            <video
              ref={gazeVideoRef}
              autoPlay
              muted
              playsInline
              className="hidden"
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
                
                {/* TTS 상태 표시 */}
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium ${
                  isTTSPlaying ? 'bg-green-500 text-white animate-pulse' :
                  'bg-green-600 text-white'
                }`}>
                  <span className="text-lg">
                    {isTTSPlaying ? '🔊' : '🎵'}
                  </span>
                  <span className="text-xs">
                    {isTTSPlaying ? '음성 재생 중...' : '자동 음성 재생'}
                  </span>
                </div>
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
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col overflow-hidden">
            {/* 스크롤 가능한 컨텐츠 영역 */}
            <div className="flex-1 overflow-y-auto">
              {/* 🆕 현재 턴 상태 표시 */}
              <div className="text-center mb-4">
              <div className={`text-sm font-bold mb-2 ${
                isTTSPlaying ? 'text-purple-400' :
                currentPhase === 'user_turn' ? 'text-yellow-400' : 
                currentPhase === 'ai_processing' ? 'text-green-400' : 
                currentPhase === 'interview_completed' ? 'text-blue-400' :
                'text-gray-400'
              }`}>
                {isTTSPlaying ? '🔊 음성 재생 중...' :
                 currentPhase === 'user_turn' ? '🎯 사용자 답변 차례' :
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

              {/* 👁️ 시선 추적 상태 표시 */}
              {state.gazeTracking?.calibrationSessionId && (
                <div className="text-center mb-2">
                  {isGazeRecording ? (
                    <div className="text-green-400 text-xs flex items-center justify-center">
                      <div className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></div>
                      👁️ 면접 전체 시선 추적 중
                    </div>
                  ) : currentPhase === 'interview_completed' ? (
                    <div className="text-blue-400 text-xs space-y-1">
                      <div className="flex items-center justify-center">
                        {isPolling ? (
                          <div className="w-2 h-2 bg-blue-400 rounded-full mr-1 animate-pulse"></div>
                        ) : null}
                        👁️ 시선 분석 {isPolling ? '진행 중' : '완료'}
                      </div>
                      <div className="flex items-center justify-center">
                        {isFeedbackProcessing ? (
                          <div className="w-2 h-2 bg-purple-400 rounded-full mr-1 animate-pulse"></div>
                        ) : null}
                        📊 면접 피드백 {isFeedbackProcessing ? '처리 중' : '완료'}
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-400 text-xs">
                      👁️ 시선 추적 준비 중
                    </div>
                  )}
                </div>
              )}

              {/* 👁️ 시선 분석 상태 표시 */}
              {gazeAnalysisResult && (
                <div className="text-center mb-2">
                  <div className="text-blue-400 text-xs">
                    🎉 시선 분석 완료 (점수: {gazeAnalysisResult.gaze_score}/100)
                  </div>
                </div>
              )}

              {/* 👁️ 시선 추적 에러 표시 */}
              {gazeError && (
                <div className="text-red-400 text-xs mb-2 text-center">
                  ⚠️ {gazeError}
                </div>
              )}
            </div>

            {/* INTRO 메시지 및 현재 질문 표시 */}
            <div className="text-center mb-6">
              {showIntroMessage && hasIntroMessage ? (
                // INTRO 메시지 표시
                <div className="intro-message">
                  <div className="text-blue-400 text-sm mb-2">🎤 면접관 인사</div>
                  <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-blue-900/20 rounded-lg p-4 border border-blue-500/30 max-h-32 overflow-y-auto">
                    {introMessage}
                  </div>
                  <div className="text-gray-400 text-xs">잠시 후 면접이 시작됩니다...</div>
                </div>
              ) : (
                // 일반 질문 표시
                <div>
                  <div className="text-gray-400 text-sm mb-2">현재 질문</div>
                  <div className="text-white text-base leading-relaxed mb-3 max-h-16 overflow-y-auto">
                    {isLoading ? (
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-blue-400">첫 번째 질문을 준비하고 있습니다...</span>
                      </div>
                    ) : (
                      currentQuestion || "질문을 불러오는 중..."
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* AI 지원자 질문 표시 */}
            {currentAIQuestion && (
              <div className="text-center mb-6">
                <div className="text-orange-400 text-sm mb-2">🎯 AI 지원자용 질문</div>
                <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-orange-900/20 rounded-lg p-4 border border-orange-500/30 max-h-32 overflow-y-auto">
                  {currentAIQuestion}
                </div>
                <div className="text-orange-300 text-xs">
                  🔊 음성은 자동으로 재생됩니다
                </div>
              </div>
            )}

            {/* AI 지원자 답변 표시 */}
            {currentAIAnswer && (
              <div className="text-center mb-6">
                <div className="text-purple-400 text-sm mb-2">🤖 AI 지원자 답변 (춘식이)</div>
                <div className="text-white text-base leading-relaxed whitespace-pre-line mb-3 bg-purple-900/20 rounded-lg p-4 border border-purple-500/30 max-h-40 overflow-y-auto">
                  {currentAIAnswer}
                </div>
                <div className="text-purple-300 text-xs">
                  🔊 음성은 자동으로 재생됩니다
                </div>
              </div>
            )}
            </div>

            {/* 컨트롤 버튼 */}
             <div className="space-y-3">
               {currentPhase === 'interview_completed' ? (
                 // 면접 완료 시 나가기 버튼 표시
                 <div className="space-y-2">
                   {(isPolling || isFeedbackProcessing) && !pollingError && !feedbackProcessingError ? (
                     <div className="text-center text-sm text-yellow-400 mb-2">
                       💫 분석이 완료될 때까지 잠시만 기다려주세요
                     </div>
                   ) : null}
                   
                   {(pollingError || feedbackProcessingError) && (
                     <div className="text-center text-sm text-red-400 mb-2">
                       ⚠️ 분석 중 문제가 발생했지만, 면접을 나가실 수 있습니다
                     </div>
                   )}
                   
                   <button 
                     onClick={() => navigate('/mypage')}
                     className={`w-full py-3 text-white rounded-lg font-semibold transition-colors ${
                       (isPolling || isFeedbackProcessing) && !pollingError && !feedbackProcessingError
                         ? 'bg-gray-600 hover:bg-gray-500' 
                         : 'bg-blue-600 hover:bg-blue-500'
                     }`}
                   >
                     {(isPolling || isFeedbackProcessing) && !pollingError && !feedbackProcessingError
                       ? '🔄 분석 중... (나가기 가능)'
                       : '🏠 면접 나가기'
                     }
                   </button>
                 </div>
               ) : (
                 // 면접 진행 중일 때 답변 제출 버튼 표시
                 (() => {
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
                 })()
               )}
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
