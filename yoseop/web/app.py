#!/usr/bin/env python3
"""
개인화된 웹 기반 면접 시스템
사용자 문서 업로드 및 맞춤형 질문 생성 지원
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import sys
from werkzeug.utils import secure_filename
from datetime import datetime
import time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 설정 및 로깅 시스템 임포트
from core.config import config
from core.logging_config import interview_logger, performance_logger, log_api_performance
from core.exceptions import *

# 핵심 모듈 임포트
from core.personalized_system import PersonalizedInterviewSystem
from core.document_processor import DocumentProcessor
from core.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_FOLDER, DEFAULT_TOTAL_QUESTIONS
from core.ai_candidate_model import AICandidateModel, AnswerRequest
from core.answer_quality_controller import QualityLevel
from core.interview_system import QuestionType, QuestionAnswer
from core.llm_manager import LLMProvider

# Flask 앱 초기화
app = Flask(__name__)
CORS(app)  # CORS 활성화

# 설정 적용
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['SECRET_KEY'] = config.SECRET_KEY

# 설정 검증
if not config.validate_config():
    interview_logger.warning("설정 검증 실패", config_summary=config.get_config_summary())
else:
    interview_logger.info("AI 면접 시스템 시작", config_summary=config.get_config_summary())

# 전역 상태 관리
class ApplicationState:
    """애플리케이션 상태 관리 클래스"""
    def __init__(self):
        self.interview_system = None
        self.document_processor = None
        self.ai_candidate = None
        self.current_sessions = {}    # 사용자 세션
        self.user_profiles = {}
        self.ai_sessions = {}         # AI 전용 세션
        self.session_orders = {}      # 답변 순서 정보 (session_id -> "user_first" | "ai_first")
        self.comparison_sessions = {} # 비교 면접 세션

app_state = ApplicationState()

def get_system():
    if app_state.interview_system is None:
        app_state.interview_system = PersonalizedInterviewSystem(config.OPENAI_API_KEY)
    return app_state.interview_system

def get_document_processor():
    if app_state.document_processor is None:
        app_state.document_processor = DocumentProcessor(config.OPENAI_API_KEY)
    return app_state.document_processor

def get_ai_candidate():
    if app_state.ai_candidate is None:
        app_state.ai_candidate = AICandidateModel(config.OPENAI_API_KEY)
    return app_state.ai_candidate

# 업로드 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 개인화된 AI 면접 시스템</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
        .container { background: white; padding: 30px; border-radius: 15px; margin: 20px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #1a202c; margin-bottom: 30px; }
        .step { margin: 20px 0; padding: 20px; border: 2px solid #e2e8f0; border-radius: 10px; }
        .step.active { border-color: #3182ce; background: #ebf8ff; }
        .step.completed { border-color: #38a169; background: #f0fff4; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        button { background: #3182ce; color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; }
        button:hover { background: #2b77cb; }
        button:disabled { background: #a0aec0; cursor: not-allowed; }
        .hidden { display: none; }
        .error { background: #fed7d7; color: #c53030; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #e53e3e; }
        .success { background: #c6f6d5; color: #2d7d43; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #38a169; }
        .question { background: #ebf8ff; padding: 20px; border-left: 4px solid #3182ce; margin: 15px 0; border-radius: 8px; }
        .result { background: #f0fff4; padding: 20px; border-left: 4px solid #48bb78; margin: 15px 0; border-radius: 8px; }
        .file-upload { border: 2px dashed #cbd5e0; padding: 20px; text-align: center; border-radius: 8px; margin: 10px 0; }
        .file-upload.dragover { border-color: #3182ce; background: #ebf8ff; }
        .profile-summary { background: #edf2f7; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .progress-bar { width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #3182ce, #63b3ed); transition: width 0.3s ease; }
        .document-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f7fafc; margin: 5px 0; border-radius: 6px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .badge-success { background: #c6f6d5; color: #2d7d43; }
        .badge-info { background: #bee3f8; color: #2b6cb0; }
        .badge-warning { background: #fef5e7; color: #c05621; }
        .document-upload-section { border: 2px solid #e2e8f0; border-radius: 10px; padding: 15px; background: #f8f9fa; }
        .document-upload-section h4 { margin-top: 0; color: #2d3748; text-align: center; }
        .document-drop-area { min-height: 80px; margin: 10px 0; }
        .uploaded-file { min-height: 40px; margin: 10px 0; padding: 10px; background: #e6fffa; border-radius: 6px; font-size: 14px; }
        .direct-input { margin: 10px 0; }
        .add-text-btn { width: 100%; margin-top: 5px; background: #38a169; }
        
        /* 타임라인 스타일 */
        .timeline-turn { 
            margin: 15px 0; 
            padding: 20px; 
            border-radius: 10px; 
            border-left: 4px solid; 
            position: relative;
            animation: fadeIn 0.5s ease-in;
        }
        .timeline-turn.user-turn { 
            background: #ebf8ff; 
            border-left-color: #3182ce; 
        }
        .timeline-turn.ai-turn { 
            background: #f0fff4; 
            border-left-color: #10b981; 
        }
        .turn-header { 
            font-weight: bold; 
            margin-bottom: 10px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
        }
        .turn-question { 
            background: rgba(255,255,255,0.7); 
            padding: 15px; 
            border-radius: 8px; 
            margin: 10px 0; 
            font-weight: 500;
        }
        .turn-answer { 
            background: rgba(255,255,255,0.5); 
            padding: 15px; 
            border-radius: 8px; 
            margin: 10px 0; 
            line-height: 1.6;
        }
        .turn-badge { 
            font-size: 12px; 
            padding: 4px 8px; 
            border-radius: 12px; 
            background: rgba(0,0,0,0.1);
        }
        .turn-badge.thinking {
            background: #fbbf24;
            color: white;
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <h1>🎯 개인화된 AI 면접 시스템</h1>
    
    <!-- Step 1: 문서 업로드 -->
    <div id="upload-section" class="container">
        <div class="step active">
            <h2>📄 1단계: 지원 문서 업로드</h2>
            <p>자기소개서, 이력서, 포트폴리오를 업로드하면 맞춤형 질문을 생성합니다.</p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0;">
                <!-- 자기소개서 업로드 -->
                <div class="document-upload-section">
                    <h4>📝 자기소개서</h4>
                    <div class="file-upload document-drop-area" data-doc-type="자기소개서">
                        <p>자기소개서를 업로드하세요</p>
                        <p><small>PDF, DOCX, DOC, TXT</small></p>
                        <input type="file" class="file-input" accept=".pdf,.docx,.doc,.txt" style="display: none;">
                        <button onclick="this.previousElementSibling.click()">파일 선택</button>
                    </div>
                    <div class="uploaded-file" id="cover-letter-file"></div>
                    <textarea class="direct-input" placeholder="또는 자기소개서 내용을 직접 입력..." rows="3"></textarea>
                    <button onclick="addDirectTextByType('자기소개서', this.previousElementSibling.value, this.previousElementSibling)" class="add-text-btn">텍스트 추가</button>
                </div>
                
                <!-- 이력서 업로드 -->
                <div class="document-upload-section">
                    <h4>📄 이력서</h4>
                    <div class="file-upload document-drop-area" data-doc-type="이력서">
                        <p>이력서를 업로드하세요</p>
                        <p><small>PDF, DOCX, DOC, TXT</small></p>
                        <input type="file" class="file-input" accept=".pdf,.docx,.doc,.txt" style="display: none;">
                        <button onclick="this.previousElementSibling.click()">파일 선택</button>
                    </div>
                    <div class="uploaded-file" id="resume-file"></div>
                    <textarea class="direct-input" placeholder="또는 이력서 내용을 직접 입력..." rows="3"></textarea>
                    <button onclick="addDirectTextByType('이력서', this.previousElementSibling.value, this.previousElementSibling)" class="add-text-btn">텍스트 추가</button>
                </div>
                
                <!-- 포트폴리오 업로드 -->
                <div class="document-upload-section">
                    <h4>💼 포트폴리오</h4>
                    <div class="file-upload document-drop-area" data-doc-type="포트폴리오">
                        <p>포트폴리오를 업로드하세요</p>
                        <p><small>PDF, DOCX, DOC, TXT</small></p>
                        <input type="file" class="file-input" accept=".pdf,.docx,.doc,.txt" style="display: none;">
                        <button onclick="this.previousElementSibling.click()">파일 선택</button>
                    </div>
                    <div class="uploaded-file" id="portfolio-file"></div>
                    <textarea class="direct-input" placeholder="또는 포트폴리오 내용을 직접 입력..." rows="3"></textarea>
                    <button onclick="addDirectTextByType('포트폴리오', this.previousElementSibling.value, this.previousElementSibling)" class="add-text-btn">텍스트 추가</button>
                </div>
            </div>
            
            <div id="upload-status" style="margin: 20px 0;"></div>
            
            <button id="analyze-btn" onclick="analyzeDocuments()">📊 문서 분석하기</button>
            <p id="analyze-status" style="text-align: center; color: #666; margin-top: 10px;">
                최소 1개 이상의 문서를 업로드하거나 입력하세요
            </p>
            <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 2px dashed #cbd5e0;">
                <p><strong>또는 바로 면접 시작</strong></p>
                
                <!-- 공통 면접 정보 입력 -->
                <div style="max-width: 400px; margin: 0 auto; text-align: left;">
                    <select id="company" style="margin-bottom: 10px;">
                        <option value="">회사 선택...</option>
                        <option value="naver">네이버</option>
                        <option value="kakao">카카오</option>
                        <option value="line">라인플러스</option>
                        <option value="coupang">쿠팡</option>
                        <option value="baemin">배달의민족</option>
                        <option value="danggeun">당근마켓</option>
                        <option value="toss">토스</option>
                    </select>
                    <input type="text" id="position" placeholder="지원 직군 (예: 백엔드 개발자)" style="margin-bottom: 10px;">
                    <input type="text" id="candidate-name" placeholder="이름" style="margin-bottom: 15px;">
                </div>
                
                <div style="text-align: center;">
                    <button onclick="skipToStandardInterview()" style="background: #718096;">📝 문서 없이 표준 면접 진행</button>
                    <button onclick="startAICandidateMode()" style="background: #9f7aea;">🤖 AI 지원자와 면접 비교</button>
                    <button onclick="startAIStandaloneMode()" style="background: #2b77cb;">🤖 AI 지원자 단독 면접</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Step 2: 프로필 확인 -->
    <div id="profile-section" class="container hidden">
        <div class="step">
            <h2>👤 2단계: 프로필 확인</h2>
            <div id="profile-summary" class="profile-summary"></div>
            <button onclick="editProfile()">✏️ 프로필 수정</button>
            <button onclick="proceedToInterview()">➡️ 면접 진행</button>
        </div>
    </div>
    
    <!-- Step 3: 면접 시작 -->
    <div id="start-section" class="container hidden">
        <div class="step">
            <h2>🚀 3단계: 면접 시작</h2>
            <select id="company">
                <option value="">회사 선택...</option>
                <option value="naver">네이버</option>
                <option value="kakao">카카오</option>
                <option value="line">라인플러스</option>
                <option value="coupang">쿠팡</option>
                <option value="baemin">배달의민족</option>
                <option value="danggeun">당근마켓</option>
                <option value="toss">토스</option>
            </select>
            <input type="text" id="position" placeholder="지원 직군 (예: 백엔드 개발자)">
            <input type="text" id="candidate-name" placeholder="이름">
            <div id="interview-type-selection">
                <button onclick="startPersonalizedInterview()" id="personalized-btn">🎯 개인화된 면접 시작</button>
                <button onclick="startStandardInterview()" id="standard-btn">📝 표준 면접 시작</button>
                <button onclick="startAICandidateMode()" id="ai-candidate-btn" style="background: #e53e3e;">🤖 AI 지원자와 경쟁</button>
            </div>
        </div>
    </div>
    
    <!-- Step 3-2: 표준 면접 시작 (문서 없이) -->
    <div id="standard-start-section" class="container hidden">
        <div class="step">
            <h2>📝 표준 면접 시작</h2>
            <div style="background: #e6fffa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p><strong>표준 면접 모드:</strong> 회사별 기본 질문으로 진행됩니다.</p>
                <ul>
                    <li>🎯 첫 번째 질문: 자기소개 (고정)</li>
                    <li>💼 두 번째 질문: 지원동기 (고정)</li>
                    <li>🏢 회사별 맞춤형 질문 (LLM 기반)</li>
                    <li>📊 표준 평가 및 피드백</li>
                </ul>
            </div>
            <div style="background: #fef5e7; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p><strong>🤖 AI 지원자 경쟁 모드:</strong> AI 지원자와 함께 면접을 진행합니다.</p>
                <ul>
                    <li>🤖 회사별 합격 수준의 AI 지원자와 경쟁</li>
                    <li>⚡ 실시간 답변 비교 및 분석</li>
                    <li>📈 AI 답변 대비 본인 강점/약점 파악</li>
                    <li>🎯 객관적인 실력 평가 및 벤치마킹</li>
                </ul>
            </div>
            <select id="standard-company">
                <option value="">회사 선택...</option>
                <option value="naver">네이버</option>
                <option value="kakao">카카오</option>
                <option value="line">라인플러스</option>
                <option value="coupang">쿠팡</option>
                <option value="baemin">배달의민족</option>
                <option value="danggeun">당근마켓</option>
                <option value="toss">토스</option>
            </select>
            <input type="text" id="standard-position" placeholder="지원 직군 (예: 백엔드 개발자)">
            <input type="text" id="standard-name" placeholder="이름">
            <div style="margin-top: 15px;">
                <button onclick="startStandardInterviewDirect()">📝 표준 면접 시작</button>
                <button onclick="startAICandidateModeDirect()" style="background: #e53e3e; margin-left: 10px;">🤖 AI 지원자와 경쟁</button>
            </div>
        </div>
    </div>
    
    <!-- Step 4: 면접 진행 -->
    <div id="interview-section" class="container hidden">
        <div class="progress-bar">
            <div class="progress-fill" id="progress-fill"></div>
        </div>
        <div id="progress-text">질문 0/0</div>
        
        <div id="question-area" class="question">
            <div id="question-meta" style="color: #666; font-size: 14px; margin-bottom: 10px;"></div>
            <div id="question-content"></div>
        </div>
        
        <textarea id="answer" placeholder="구체적이고 상세한 답변을 입력하세요..." rows="5"></textarea>
        <button onclick="submitAnswer()">답변 제출</button>
        <div id="status" style="margin-top: 10px;"></div>
    </div>
    
    <!-- Step 4-2: AI 지원자 모드 면접 진행 (통합 타임라인) -->
    <div id="ai-interview-section" class="container hidden">
        <div class="progress-bar">
            <div class="progress-fill" id="ai-progress-fill"></div>
        </div>
        <div id="ai-progress-text">질문 0/0</div>
        
        <!-- 통합된 면접 진행 타임라인 -->
        <div id="interview-timeline" style="margin: 20px 0;">
            <!-- 각 턴이 여기에 순서대로 추가됩니다 -->
        </div>
        
        <!-- 현재 활성 입력 영역 -->
        <div id="current-turn-input" class="hidden" style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; border: 2px solid #3182ce;">
            <div id="current-turn-header" style="font-weight: bold; margin-bottom: 15px; color: #2563eb;"></div>
            <div id="current-question-content" style="background: #ebf8ff; padding: 15px; border-radius: 8px; margin-bottom: 15px;"></div>
            <textarea id="user-answer" placeholder="구체적이고 상세한 답변을 입력하세요..." rows="4" style="width: 100%; margin-bottom: 15px;"></textarea>
            <button id="submit-comparison-btn" onclick="submitUserTurnAnswer()" style="background: #3182ce; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer;">답변 제출</button>
        </div>
        
        <div id="ai-status" style="margin-top: 10px; text-align: center;"></div>
    </div>
    
    <!-- Step 4-3: AI 지원자 단독 면접 모드 -->
    <div id="ai-standalone-section" class="container hidden">
        <div class="step">
            <h2>🤖 AI 지원자 단독 면접 모드</h2>
            <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p><strong>AI 지원자 단독 면접:</strong> AI 지원자가 독립적으로 면접을 진행합니다.</p>
                <ul>
                    <li>🎯 개인화된 맞춤형 질문 생성</li>
                    <li>🤖 AI 지원자 자동 답변</li>
                    <li>📊 면접 완료 후 종합 평가</li>
                    <li>🔄 완전한 면접 과정 시뮬레이션</li>
                </ul>
            </div>
            
            <div style="margin-bottom: 20px;">
                <h4>회사 및 지원자 정보</h4>
                <select id="ai-standalone-company">
                    <option value="">회사 선택...</option>
                    <option value="naver">네이버</option>
                    <option value="kakao">카카오</option>
                    <option value="line">라인플러스</option>
                    <option value="coupang">쿠팡</option>
                    <option value="baemin">배달의민족</option>
                    <option value="danggeun">당근마켓</option>
                    <option value="toss">토스</option>
                </select>
                <input type="text" id="ai-standalone-position" placeholder="지원 직군 (예: 백엔드 개발자)">
                
                <h4 style="margin-top: 20px;">AI 지원자 설정</h4>
                <label for="ai-quality-level">답변 품질 레벨:</label>
                <select id="ai-quality-level" style="margin-bottom: 10px;">
                    <option value="10">10점 - 탁월한 수준 (매우 구체적, 수치 포함, 전문적)</option>
                    <option value="9">9점 - 우수한 수준 (구체적 예시, 체계적 구성)</option>
                    <option value="8" selected>8점 - 양호한 수준 (적절한 내용, 무난한 답변)</option>
                    <option value="7">7점 - 보통 수준 (기본적 내용)</option>
                    <option value="6">6점 - 평균 이하 (간단한 구성)</option>
                    <option value="5">5점 - 부족한 수준 (짧고 표면적)</option>
                </select>
                
                <label for="ai-answer-style">답변 스타일:</label>
                <select id="ai-answer-style" style="margin-bottom: 10px;">
                    <option value="detailed" selected>상세형 - 구체적이고 자세한 설명</option>
                    <option value="concise">간결형 - 핵심만 간단명료하게</option>
                    <option value="storytelling">스토리텔링형 - 경험 중심의 서술</option>
                    <option value="technical">기술중심형 - 기술적 전문성 강조</option>
                </select>
            </div>
            
            <button onclick="startAIStandaloneInterview()" style="background: #2b77cb;">🚀 AI 지원자 면접 시작</button>
        </div>
    </div>
    
    <!-- Step 4-4: AI 지원자 단독 면접 진행 -->
    <div id="ai-standalone-interview-section" class="container hidden">
        <div class="progress-bar">
            <div class="progress-fill" id="ai-standalone-progress-fill"></div>
        </div>
        <div id="ai-standalone-progress-text">질문 0/0</div>
        
        <div id="ai-standalone-persona-info" style="background: #e6f3ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h4>👤 AI 지원자 페르소나 정보</h4>
            <div id="ai-standalone-persona-details"></div>
        </div>
        
        <div id="ai-standalone-question-area" class="question">
            <div id="ai-standalone-question-meta" style="color: #666; font-size: 14px; margin-bottom: 10px;"></div>
            <div id="ai-standalone-question-content"></div>
        </div>
        
        <div style="margin: 20px 0;">
            <h4>🤖 AI 지원자 답변</h4>
            <div id="ai-standalone-answer-content" style="background: #f8f9fa; padding: 15px; border-radius: 8px; min-height: 100px; border: 1px solid #e2e8f0;">
                AI 답변을 생성하는 중...
            </div>
        </div>
        
        
        <div style="margin-top: 20px; text-align: center;">
            <button onclick="continueAIStandaloneInterview()" id="ai-standalone-continue-btn">다음 질문 진행</button>
            <button onclick="finishAIStandaloneInterview()" id="ai-standalone-finish-btn" style="background: #38a169;" class="hidden">면접 완료</button>
        </div>
        
        <div id="ai-standalone-status" style="margin-top: 10px; text-align: center;"></div>
    </div>
    
    <!-- Step 5: 결과 -->
    <div id="result-section" class="container hidden">
        <h2>📊 개인화된 면접 결과</h2>
        <div id="overall-result" class="result"></div>
        <div id="individual-results"></div>
        <button onclick="location.reload()">새로운 면접 시작</button>
    </div>
    
    <div id="message" class="hidden"></div>

    <script>
        let uploadedDocuments = {};
        let userProfile = null;
        let sessionId = null;
        let aiSessionId = null;
        let currentQuestionNumber = 0;
        let totalQuestions = 0;
        let aiCandidateMode = false;
        let currentAIAnswer = null;
        
        // 파일 업로드 관련
        document.addEventListener('DOMContentLoaded', function() {
            // 모든 파일 입력에 이벤트 리스너 추가
            document.querySelectorAll('.file-input').forEach(input => {
                input.addEventListener('change', function(e) {
                    const docType = e.target.closest('.document-drop-area').dataset.docType;
                    handleFilesByType(e, docType);
                });
            });
            
            // 드래그 앤 드롭 이벤트
            document.querySelectorAll('.document-drop-area').forEach(area => {
                area.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    area.classList.add('dragover');
                });
                
                area.addEventListener('dragleave', () => {
                    area.classList.remove('dragover');
                });
                
                area.addEventListener('drop', (e) => {
                    e.preventDefault();
                    area.classList.remove('dragover');
                    const docType = area.dataset.docType;
                    handleFilesByType({ target: { files: e.dataTransfer.files } }, docType);
                });
            });
            
            updateAnalyzeButton();
        });
        
        function handleFilesByType(event, docType) {
            const files = event.target.files;
            for (let file of files) {
                if (file.size > 16 * 1024 * 1024) {
                    showMessage('파일 크기가 16MB를 초과합니다: ' + file.name, 'error');
                    continue;
                }
                uploadFileByType(file, docType);
            }
        }
        
        function uploadFileByType(file, docType) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('document_type', docType);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addUploadedFileByType(file.name, docType, data.text_preview);
                    uploadedDocuments[docType] = data.text;
                    updateAnalyzeButton();
                } else {
                    showMessage('파일 업로드 실패: ' + data.error, 'error');
                }
            })
            .catch(error => showMessage('업로드 오류: ' + error, 'error'));
        }
        
        function addUploadedFileByType(filename, docType, preview) {
            let containerId;
            switch(docType) {
                case '자기소개서': containerId = 'cover-letter-file'; break;
                case '이력서': containerId = 'resume-file'; break;
                case '포트폴리오': containerId = 'portfolio-file'; break;
                default: return;
            }
            
            const container = document.getElementById(containerId);
            container.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${filename}</strong>
                        <div style="font-size: 12px; color: #666; margin-top: 5px;">${preview}</div>
                    </div>
                    <button onclick="removeFileByType('${docType}')" style="background: #e53e3e; padding: 5px 10px; color: white; border: none; border-radius: 4px;">삭제</button>
                </div>
            `;
        }
        
        function addDirectTextByType(docType, text, textareaElement) {
            if (!text.trim()) {
                showMessage('텍스트를 입력하세요', 'error');
                return;
            }
            
            uploadedDocuments[docType] = text.trim();
            addUploadedFileByType('직접 입력된 텍스트', docType, text.substring(0, 100) + '...');
            textareaElement.value = '';
            updateAnalyzeButton();
            showMessage(`${docType} 텍스트가 추가되었습니다`, 'success');
        }
        
        function removeFileByType(docType) {
            delete uploadedDocuments[docType];
            
            let containerId;
            switch(docType) {
                case '자기소개서': containerId = 'cover-letter-file'; break;
                case '이력서': containerId = 'resume-file'; break;
                case '포트폴리오': containerId = 'portfolio-file'; break;
                default: return;
            }
            
            document.getElementById(containerId).innerHTML = '';
            updateAnalyzeButton();
            showMessage(`${docType}가 삭제되었습니다`, 'info');
        }
        
        function updateAnalyzeButton() {
            const analyzeBtn = document.getElementById('analyze-btn');
            const analyzeStatus = document.getElementById('analyze-status');
            const docCount = Object.keys(uploadedDocuments).length;
            
            if (docCount === 0) {
                analyzeBtn.disabled = true;
                analyzeBtn.style.background = '#a0aec0';
                analyzeStatus.innerHTML = '최소 1개 이상의 문서를 업로드하거나 입력하세요';
                analyzeStatus.style.color = '#e53e3e';
            } else {
                analyzeBtn.disabled = false;
                analyzeBtn.style.background = '#3182ce';
                analyzeStatus.innerHTML = `${docCount}개 문서 준비됨 - 분석 가능`;
                analyzeStatus.style.color = '#38a169';
            }
        }
        
        function analyzeDocuments() {
            if (Object.keys(uploadedDocuments).length === 0) {
                showMessage('업로드된 문서가 없습니다', 'error');
                return;
            }
            
            showMessage('문서 분석 중...');
            
            fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({documents: uploadedDocuments})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    userProfile = data.profile;
                    showProfileSummary(userProfile);
                    document.getElementById('upload-section').style.display = 'none';
                    document.getElementById('profile-section').classList.remove('hidden');
                } else {
                    showMessage('문서 분석 실패: ' + data.error, 'error');
                }
            })
            .catch(error => showMessage('분석 오류: ' + error, 'error'));
        }
        
        function showProfileSummary(profile) {
            const summary = document.getElementById('profile-summary');
            summary.innerHTML = `
                <h3>📋 분석된 프로필</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4>기본 정보</h4>
                        <p><strong>이름:</strong> ${profile.name}</p>
                        <p><strong>경력:</strong> ${profile.background.career_years}년</p>
                        <p><strong>현재 직책:</strong> ${profile.background.current_position}</p>
                    </div>
                    <div>
                        <h4>주요 기술</h4>
                        <p>${profile.technical_skills.slice(0, 5).join(', ')}</p>
                        <h4>강점</h4>
                        <p>${profile.strengths.slice(0, 3).join(', ')}</p>
                    </div>
                </div>
                <div>
                    <h4>커리어 목표</h4>
                    <p>${profile.career_goal}</p>
                </div>
                <div>
                    <h4>주요 프로젝트 (${profile.projects.length}개)</h4>
                    ${profile.projects.slice(0, 2).map(p => 
                        `<p><strong>${p.name}:</strong> ${p.description}</p>`
                    ).join('')}
                </div>
            `;
        }
        
        function editProfile() {
            // 프로필 수정 기능 (향후 구현)
            showMessage('프로필 수정 기능은 향후 추가될 예정입니다', 'info');
        }
        
        function proceedToInterview() {
            document.getElementById('profile-section').style.display = 'none';
            document.getElementById('start-section').classList.remove('hidden');
        }
        
        function skipToStandardInterview() {
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('standard-start-section').classList.remove('hidden');
        }
        
        function startStandardInterview() {
            document.getElementById('start-section').style.display = 'none';
            document.getElementById('standard-start-section').classList.remove('hidden');
        }
        
        function startAICandidateMode() {
            const company = document.getElementById('company').value;
            const position = document.getElementById('position').value;
            const candidateName = document.getElementById('candidate-name').value;
            
            if (!company || !position || !candidateName) {
                showMessage('회사, 직군, 이름을 모두 입력하세요', 'error');
                return;
            }
            
            aiCandidateMode = true;
            showMessage('AI 지원자와의 경쟁 면접을 시작합니다...');
            
            // 새로운 턴제 비교 면접 시작
            fetch('/start_comparison_interview', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: company,
                    position: position,
                    name: candidateName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 전역 변수 설정
                    window.comparisonSessionId = data.comparison_session_id;
                    window.userSessionId = data.user_session_id;
                    window.aiSessionId = data.ai_session_id;
                    window.currentPhase = data.current_phase;
                    window.aiName = data.ai_name;
                    window.userName = candidateName;
                    currentQuestionNumber = data.question_index;
                    totalQuestions = data.total_questions;
                    
                    // UI 전환
                    document.getElementById('start-section').style.display = 'none';
                    document.getElementById('ai-interview-section').classList.remove('hidden');
                    
                    // 타임라인 초기화
                    document.getElementById('interview-timeline').innerHTML = '';
                    
                    // 시작자에 따라 다른 처리
                    if (data.starts_with_user) {
                        // 사용자부터 시작
                        showTurnQuestion(data.question, data.current_phase, data.current_respondent);
                        updateTurnProgress();
                        showMessage(data.message, 'info');
                    } else {
                        // AI부터 시작
                        showMessage(data.message, 'info');
                        setTimeout(() => processAITurn(), 1000);
                    }
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('면접 시작 오류: ' + error, 'error'));
        }
        
        function startAICandidateModeDirect() {
            const company = document.getElementById('standard-company').value;
            const position = document.getElementById('standard-position').value;
            const candidateName = document.getElementById('standard-name').value;
            
            if (!company || !position || !candidateName) {
                showMessage('회사, 직군, 이름을 모두 입력하세요', 'error');
                return;
            }
            
            aiCandidateMode = true;
            showMessage('AI 지원자와의 경쟁 면접을 시작합니다...');
            
            // AI 면접 시작
            fetch('/start_ai_interview', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: company,
                    position: position,
                    name: candidateName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    sessionId = data.user_session_id;
                    aiSessionId = data.ai_session_id;
                    currentQuestionNumber = 1;
                    
                    // 답변 순서 및 AI 이름 정보 저장
                    window.answerOrder = data.answer_order;
                    window.aiName = data.ai_name;
                    
                    // 진행률에서 총 질문 수 추출
                    if (data.question && data.question.progress) {
                        const progressParts = data.question.progress.split('/');
                        totalQuestions = parseInt(progressParts[1]) || 20;
                    }
                    
                    document.getElementById('standard-start-section').style.display = 'none';
                    document.getElementById('ai-interview-section').classList.remove('hidden');
                    
                    // 답변 순서 메시지 표시
                    showMessage(data.order_message, 'info');
                    
                    showAIQuestion(data.question);
                    updateAIProgress();
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('면접 시작 오류: ' + error, 'error'));
        }
        
        function startAIStandaloneMode() {
            const company = document.getElementById('company').value;
            const position = document.getElementById('position').value;
            
            if (!company || !position) {
                showMessage('회사와 직군을 모두 입력하세요', 'error');
                return;
            }
            
            // AI 지원자 단독 면접 섹션으로 이동
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('ai-standalone-section').classList.remove('hidden');
            
            // 입력값 복사
            document.getElementById('ai-standalone-company').value = company;
            document.getElementById('ai-standalone-position').value = position;
        }
        
        function startAIStandaloneInterview() {
            const company = document.getElementById('ai-standalone-company').value;
            const position = document.getElementById('ai-standalone-position').value;
            const qualityLevel = document.getElementById('ai-quality-level').value;
            const answerStyle = document.getElementById('ai-answer-style').value;
            
            if (!company || !position) {
                showMessage('회사와 직군을 모두 입력하세요', 'error');
                return;
            }
            
            showMessage('AI 지원자 단독 면접을 시작합니다...');
            
            // AI 지원자 단독 면접 시작
            fetch('/start_ai_standalone', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: company,
                    position: position,
                    quality_level: parseInt(qualityLevel),
                    answer_style: answerStyle
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    aiSessionId = data.ai_session_id;
                    currentQuestionNumber = 1;
                    totalQuestions = data.total_questions || 20;
                    
                    // 페르소나 정보 표시
                    document.getElementById('ai-standalone-persona-details').innerHTML = `
                        <strong>이름:</strong> ${data.persona.name}<br>
                        <strong>경력:</strong> ${data.persona.career_years}년<br>
                        <strong>직책:</strong> ${data.persona.current_position}<br>
                        <strong>주요 기술:</strong> ${data.persona.main_skills.join(', ')}
                    `;
                    
                    document.getElementById('ai-standalone-section').style.display = 'none';
                    document.getElementById('ai-standalone-interview-section').classList.remove('hidden');
                    
                    showAIStandaloneQuestion(data.question);
                    updateAIStandaloneProgress();
                    generateAIStandaloneAnswer();
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('면접 시작 오류: ' + error, 'error'));
        }
        
        function showAIStandaloneQuestion(question) {
            const personalizationBadge = question.personalized ? 
                '<span class="badge badge-success">개인화됨</span>' : 
                '<span class="badge badge-info">표준</span>';
                
            document.getElementById('ai-standalone-question-meta').innerHTML = 
                `<strong>[${question.question_type}]</strong> ${personalizationBadge} • ${question.progress}`;
            
            document.getElementById('ai-standalone-question-content').innerHTML = 
                `<div><strong>❓ 질문:</strong> ${question.question_content}</div>`;
        }
        
        function updateAIStandaloneProgress() {
            const progress = (currentQuestionNumber / totalQuestions) * 100;
            document.getElementById('ai-standalone-progress-fill').style.width = progress + '%';
            document.getElementById('ai-standalone-progress-text').textContent = `질문 ${currentQuestionNumber}/${totalQuestions}`;
        }
        
        function generateAIStandaloneAnswer() {
            document.getElementById('ai-standalone-answer-content').innerHTML = 'AI 답변을 생성하는 중...';
            document.getElementById('ai-standalone-status').innerHTML = '🤖 AI 지원자가 답변을 생성하고 있습니다...';
            
            fetch('/ai_standalone_answer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    ai_session_id: aiSessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // AI 답변 표시
                    document.getElementById('ai-standalone-answer-content').innerHTML = 
                        `<div><strong>${data.answer.persona_name}</strong></div>
                         <div style="margin-top: 10px;">${data.answer.content}</div>
                         <div style="margin-top: 10px; font-size: 12px; color: #666;">
                             품질 레벨: ${data.answer.quality_level}점 | 신뢰도: ${Math.round(data.answer.confidence * 100)}%
                         </div>`;
                    
                    // 실시간 피드백 제거 - 최종 면접 완료 후에만 피드백 제공
                    
                    // 버튼 상태 업데이트
                    if (data.is_complete) {
                        document.getElementById('ai-standalone-continue-btn').classList.add('hidden');
                        document.getElementById('ai-standalone-finish-btn').classList.remove('hidden');
                    } else {
                        document.getElementById('ai-standalone-continue-btn').classList.remove('hidden');
                        document.getElementById('ai-standalone-finish-btn').classList.add('hidden');
                    }
                    
                    document.getElementById('ai-standalone-status').innerHTML = '✅ AI 답변 생성 완료';
                } else {
                    document.getElementById('ai-standalone-answer-content').innerHTML = 
                        `<span style="color: #e53e3e;">AI 답변 생성 실패: ${data.error}</span>`;
                    document.getElementById('ai-standalone-status').innerHTML = '❌ 답변 생성 실패';
                }
            })
            .catch(error => {
                document.getElementById('ai-standalone-answer-content').innerHTML = 
                    `<span style="color: #e53e3e;">오류: ${error}</span>`;
                document.getElementById('ai-standalone-status').innerHTML = '❌ 시스템 오류';
            });
        }
        
        function continueAIStandaloneInterview() {
            document.getElementById('ai-standalone-status').innerHTML = '다음 질문을 생성하고 있습니다...';
            
            fetch('/ai_standalone_next', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    ai_session_id: aiSessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentQuestionNumber++;
                    showAIStandaloneQuestion(data.question);
                    updateAIStandaloneProgress();
                    
                    // 다음 답변 생성
                    generateAIStandaloneAnswer();
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('오류: ' + error, 'error'));
        }
        
        function finishAIStandaloneInterview() {
            document.getElementById('ai-standalone-status').innerHTML = '최종 평가를 생성하고 있습니다...';
            
            fetch('/ai_standalone_evaluate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    ai_session_id: aiSessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('ai-standalone-interview-section').style.display = 'none';
                    document.getElementById('result-section').classList.remove('hidden');
                    showAIStandaloneResults(data.evaluation);
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('평가 오류: ' + error, 'error'));
        }
        
        function showAIStandaloneResults(evaluation) {
            const evalData = evaluation.evaluation;
            const overallScoreClass = getScoreClass(evalData.overall_score);
            
            let resultHtml = `
                <div style="text-align: center; margin-bottom: 30px;">
                    <h3>🤖 AI 지원자 면접 결과</h3>
                    <div style="background: #e6f3ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <strong>페르소나:</strong> ${evaluation.candidate} (${evaluation.company})<br>
                        <strong>직군:</strong> ${evaluation.position}
                    </div>
                    <h4>전체 점수 <span class="score-badge ${overallScoreClass}">${evalData.overall_score}/100</span></h4>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                    <div style="background: #f0fff4; padding: 15px; border-radius: 8px;">
                        <h4>💪 주요 강점</h4>
                        <ul>${evalData.strengths.map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                    <div style="background: #fef5e7; padding: 15px; border-radius: 8px;">
                        <h4>🔧 개선 영역</h4>
                        <ul>${evalData.improvements.map(i => `<li>${i}</li>`).join('')}</ul>
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h4>🎯 최종 추천</h4>
                    <p>${evalData.recommendation}</p>
                    <h4>🚀 다음 단계</h4>
                    <p>${evalData.next_steps}</p>
                </div>
            `;
            
            document.getElementById('overall-result').innerHTML = resultHtml;
            
            // 개별 답변 결과
            let individualHtml = '<h3>📝 개별 답변별 상세 피드백</h3>';
            evaluation.individual_feedbacks.forEach((feedback, index) => {
                const scoreClass = getScoreClass(feedback.score);
                const personalizationBadge = feedback.personalized ? 
                    '<span class="badge badge-success">개인화됨</span>' : 
                    '<span class="badge badge-info">표준</span>';
                    
                individualHtml += `
                    <div style="margin-bottom: 25px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <strong>${index + 1}. [${feedback.question_type}] ${personalizationBadge}</strong>
                            <span class="score-badge ${scoreClass}">${feedback.score}/100</span>
                        </div>
                        <div style="margin-bottom: 10px; padding: 10px; background: #ebf8ff; border-radius: 6px;">
                            <strong>❓ 질문:</strong> ${feedback.question}
                            ${feedback.question_intent ? `<br><span style="font-size: 0.9em; color: #666; font-style: italic;">🎯 의도: ${feedback.question_intent}</span>` : ''}
                        </div>
                        <div style="margin-bottom: 10px; padding: 10px; background: #e6fffa; border-radius: 6px;">
                            <strong>🤖 AI 답변:</strong> ${feedback.answer}
                        </div>
                        <div style="padding: 10px; background: #fef5e7; border-radius: 6px; white-space: pre-line;">
                            <strong>📝 상세 피드백:</strong><br>${feedback.feedback}
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('individual-results').innerHTML = individualHtml;
        }
        
        function startPersonalizedInterview() {
            const company = document.getElementById('company').value;
            const position = document.getElementById('position').value;
            const candidateName = document.getElementById('candidate-name').value;
            
            if (!company || !position || !candidateName) {
                showMessage('회사, 직군, 이름을 모두 입력하세요', 'error');
                return;
            }
            
            if (!userProfile) {
                showMessage('사용자 프로필이 없습니다. 문서를 업로드하고 분석하세요.', 'error');
                return;
            }
            
            showMessage('개인화된 면접을 시작합니다...');
            
            fetch('/start_personalized', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: company,
                    position: position,
                    user_profile: userProfile
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    sessionId = data.session_id;
                    currentQuestionNumber = 1;
                    // 진행률에서 총 질문 수 추출
                    if (data.question && data.question.progress) {
                        const progressParts = data.question.progress.split('/');
                        totalQuestions = parseInt(progressParts[1]) || 20;
                    }
                    document.getElementById('start-section').style.display = 'none';
                    document.getElementById('interview-section').classList.remove('hidden');
                    showQuestion(data.question);
                    updateProgress();
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('면접 시작 오류: ' + error, 'error'));
        }
        
        function startStandardInterviewDirect() {
            const company = document.getElementById('standard-company').value;
            const position = document.getElementById('standard-position').value;
            const candidateName = document.getElementById('standard-name').value;
            
            if (!company || !position || !candidateName) {
                showMessage('회사, 직군, 이름을 모두 입력하세요', 'error');
                return;
            }
            
            showMessage('표준 면접을 시작합니다...');
            
            fetch('/start_standard', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    company: company,
                    position: position,
                    name: candidateName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    sessionId = data.session_id;
                    currentQuestionNumber = 1;
                    // 진행률에서 총 질문 수 추출
                    if (data.question && data.question.progress) {
                        const progressParts = data.question.progress.split('/');
                        totalQuestions = parseInt(progressParts[1]) || 20;
                    }
                    document.getElementById('standard-start-section').style.display = 'none';
                    document.getElementById('interview-section').classList.remove('hidden');
                    showQuestion(data.question);
                    updateProgress();
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('면접 시작 오류: ' + error, 'error'));
        }
        
        function showQuestion(question) {
            const personalizationBadge = question.personalized ? 
                '<span class="badge badge-success">개인화됨</span>' : 
                '<span class="badge badge-info">표준</span>';
                
            document.getElementById('question-meta').innerHTML = 
                `<strong>[${question.question_type}]</strong> ${personalizationBadge} • ${question.progress}`;
            
            document.getElementById('question-content').innerHTML = 
                `<div><strong>❓ 질문:</strong> ${question.question_content}</div>`;
            
            document.getElementById('answer').value = '';
            document.getElementById('status').innerHTML = '';
        }
        
        function updateProgress() {
            const progress = (currentQuestionNumber / totalQuestions) * 100;
            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('progress-text').textContent = `질문 ${currentQuestionNumber}/${totalQuestions}`;
        }
        
        function submitAnswer() {
            const answer = document.getElementById('answer').value;
            if (!answer.trim()) {
                showMessage('답변을 입력하세요', 'error');
                return;
            }
            
            document.getElementById('status').innerHTML = '답변 저장 중...';
            
            fetch('/answer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: sessionId, answer: answer})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.result.status === 'interview_complete') {
                        evaluateInterview();
                    } else {
                        currentQuestionNumber++;
                        updateProgress();
                        showQuestion(data.result.question);
                    }
                } else {
                    showMessage(data.error, 'error');
                }
                document.getElementById('status').innerHTML = '';
            })
            .catch(error => {
                showMessage('오류: ' + error, 'error');
                document.getElementById('status').innerHTML = '';
            });
        }
        
        function evaluateInterview() {
            document.getElementById('status').innerHTML = '📊 개인화된 평가 생성 중...';
            
            fetch('/evaluate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: sessionId})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('interview-section').style.display = 'none';
                    document.getElementById('result-section').classList.remove('hidden');
                    showResults(data.evaluation);
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('평가 오류: ' + error, 'error'));
        }
        
        function evaluateAIInterview() {
            document.getElementById('ai-status').innerHTML = '📊 AI 면접 평가 생성 중...';
            
            fetch('/ai_evaluate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_session_id: sessionId,
                    ai_session_id: aiSessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('ai-interview-section').style.display = 'none';
                    document.getElementById('result-section').classList.remove('hidden');
                    showAIResults(data.user_evaluation, data.ai_evaluation);
                } else {
                    showMessage(data.error, 'error');
                }
            })
            .catch(error => showMessage('평가 오류: ' + error, 'error'));
        }
        
        function showResults(evaluation) {
            // 결과 표시 로직 (기존과 동일)
            const evalData = evaluation.evaluation;
            const overallScoreClass = getScoreClass(evalData.overall_score);
            
            let overallHtml = `
                <div style="text-align: center; margin-bottom: 30px;">
                    <h3>개인화된 면접 점수 <span class="score-badge ${overallScoreClass}">${evalData.overall_score}/100</span></h3>
                </div>
                <h4>💪 주요 강점:</h4>
                <ul>${evalData.strengths.map(s => `<li>${s}</li>`).join('')}</ul>
                <h4>🔧 개선 필요 사항:</h4>
                <ul>${evalData.improvements.map(i => `<li>${i}</li>`).join('')}</ul>
                <h4>🎯 최종 추천:</h4>
                <p>${evalData.recommendation}</p>
            `;
            
            document.getElementById('overall-result').innerHTML = overallHtml;
            
            // 개별 답변 결과
            let individualHtml = '<h3>📝 개별 답변별 상세 피드백</h3>';
            evaluation.individual_feedbacks.forEach((feedback, index) => {
                const scoreClass = getScoreClass(feedback.score);
                const personalizationBadge = feedback.personalized ? 
                    '<span class="badge badge-success">개인화됨</span>' : 
                    '<span class="badge badge-info">표준</span>';
                    
                individualHtml += `
                    <div style="margin-bottom: 25px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <strong>${index + 1}. [${feedback.question_type}] ${personalizationBadge}</strong>
                            <span class="score-badge ${scoreClass}">${feedback.score}/100</span>
                        </div>
                        <div style="margin-bottom: 10px; padding: 10px; background: #ebf8ff; border-radius: 6px;">
                            <strong>❓ 질문:</strong> ${feedback.question}
                            ${feedback.question_intent ? `<br><span style="font-size: 0.9em; color: #666; font-style: italic;">🎯 의도: ${feedback.question_intent}</span>` : ''}
                        </div>
                        <div style="margin-bottom: 10px; padding: 10px; background: #e6fffa; border-radius: 6px;">
                            <strong>💬 답변:</strong> ${feedback.answer}
                        </div>
                        <div style="padding: 10px; background: #fef5e7; border-radius: 6px; white-space: pre-line;">
                            <strong>📝 상세 피드백:</strong><br>${feedback.feedback}
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('individual-results').innerHTML = individualHtml;
        }
        
        function getScoreClass(score) {
            if (score >= 70) return 'badge-success';
            if (score >= 50) return 'badge-warning';
            return 'badge-error';
        }
        
        function showTurnQuestion(question, phase, respondent) {
            if (phase === 'user_turn') {
                // 사용자 턴: 현재 입력 영역에 표시
                showUserTurnInput(question, respondent);
            } else {
                // AI 턴: 자동으로 AI 답변 처리 (더 이상 여기서 호출되지 않음)
                console.log('AI 턴은 processAITurn()으로 직접 호출됩니다');
            }
        }
        
        function showUserTurnInput(question, respondent) {
            const personalizationBadge = question.personalized ? 
                '<span class="badge badge-success">개인화됨</span>' : 
                '<span class="badge badge-info">표준</span>';
            
            // 현재 입력 영역 표시
            const currentInput = document.getElementById('current-turn-input');
            const header = document.getElementById('current-turn-header');
            const content = document.getElementById('current-question-content');
            const answerInput = document.getElementById('user-answer');
            
            header.innerHTML = `👨‍💻 ${respondent}님의 차례 • [${question.question_type}] ${personalizationBadge} • ${question.progress}`;
            content.innerHTML = `<strong>❓ 질문:</strong> ${question.question_content}`;
            
            answerInput.value = '';
            answerInput.disabled = false;
            currentInput.classList.remove('hidden');
            
            document.getElementById('ai-status').innerHTML = '';
        }
        
        function addUserTurnToTimeline() {
            const currentInput = document.getElementById('current-turn-input');
            const header = document.getElementById('current-turn-header').innerHTML;
            const questionContent = document.getElementById('current-question-content').innerHTML;
            const userAnswer = document.getElementById('user-answer').value;
            
            const timeline = document.getElementById('interview-timeline');
            const turnDiv = document.createElement('div');
            turnDiv.className = 'timeline-turn user-turn';
            
            turnDiv.innerHTML = `
                <div class="turn-header">
                    ${header}
                    <span class="turn-badge">완료</span>
                </div>
                <div class="turn-question">${questionContent}</div>
                <div class="turn-answer">
                    <strong>💬 답변:</strong> ${userAnswer}
                </div>
            `;
            
            timeline.appendChild(turnDiv);
            
            // 타임라인 하단으로 스크롤
            turnDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        
        function addAIQuestionToTimeline(aiQuestion) {
            const personalizationBadge = aiQuestion.personalized ? 
                '<span class="badge badge-success">개인화됨</span>' : 
                '<span class="badge badge-info">표준</span>';
            
            const timeline = document.getElementById('interview-timeline');
            const turnDiv = document.createElement('div');
            turnDiv.className = 'timeline-turn ai-turn';
            turnDiv.id = 'current-ai-turn';  // ID 추가로 나중에 답변 업데이트 가능
            
            turnDiv.innerHTML = `
                <div class="turn-header">
                    🤖 ${window.aiName}의 차례 • [${aiQuestion.question_type}] ${personalizationBadge} • ${aiQuestion.progress}
                    <span class="turn-badge thinking">생각 중...</span>
                </div>
                <div class="turn-question">
                    <strong>❓ 질문:</strong> ${aiQuestion.question_content}
                </div>
                <div class="turn-answer" id="pending-ai-answer">
                    <strong>🤖 답변:</strong> <span style="color: #666; font-style: italic;">답변을 생성하고 있습니다...</span>
                </div>
            `;
            
            timeline.appendChild(turnDiv);
            
            // 타임라인 하단으로 스크롤
            turnDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        
        function updateAIQuestionWithAnswer(aiAnswer) {
            const currentAITurn = document.getElementById('current-ai-turn');
            if (currentAITurn) {
                // 상태 배지 업데이트
                const badge = currentAITurn.querySelector('.turn-badge');
                badge.textContent = '완료';
                badge.className = 'turn-badge';
                
                // 답변 업데이트
                const answerDiv = currentAITurn.querySelector('#pending-ai-answer');
                answerDiv.innerHTML = `
                    <strong>🤖 답변:</strong> ${aiAnswer.content}
                    <div style="font-size: 12px; color: #666; margin-top: 10px;">
                        신뢰도: ${Math.round(aiAnswer.confidence * 100)}%
                    </div>
                `;
                answerDiv.id = '';  // ID 제거
                
                // ID 제거
                currentAITurn.id = '';
                
                // 타임라인 하단으로 스크롤
                currentAITurn.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        }
        
        function addAITurnToTimeline(aiData) {
            // 기존 함수는 호환성을 위해 유지 (한번에 질문+답변)
            const personalizationBadge = aiData.ai_question.personalized ? 
                '<span class="badge badge-success">개인화됨</span>' : 
                '<span class="badge badge-info">표준</span>';
            
            const timeline = document.getElementById('interview-timeline');
            const turnDiv = document.createElement('div');
            turnDiv.className = 'timeline-turn ai-turn';
            
            turnDiv.innerHTML = `
                <div class="turn-header">
                    🤖 ${aiData.ai_answer.persona_name}의 차례 • [${aiData.ai_question.question_type}] ${personalizationBadge} • ${aiData.ai_question.progress}
                    <span class="turn-badge">완료</span>
                </div>
                <div class="turn-question">
                    <strong>❓ 질문:</strong> ${aiData.ai_question.question_content}
                </div>
                <div class="turn-answer">
                    <strong>🤖 답변:</strong> ${aiData.ai_answer.content}
                    <div style="font-size: 12px; color: #666; margin-top: 10px;">
                        신뢰도: ${Math.round(aiData.ai_answer.confidence * 100)}%
                    </div>
                </div>
            `;
            
            timeline.appendChild(turnDiv);
            
            // 타임라인 하단으로 스크롤
            turnDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        
        function generateAIAnswer(question) {
            const company = document.getElementById('company').value;
            const position = document.getElementById('position').value;
            
            document.getElementById('ai-answer-content').innerHTML = '🤖 AI 답변 생성 중...';
            
            fetch('/api/ai-candidate/answer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question_content: question.question_content,
                    question_type: question.question_type,
                    question_intent: question.question_intent || '',
                    company_id: company,
                    position: position,
                    quality_level: 8
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentAIAnswer = data.answer;
                    document.getElementById('ai-answer-content').innerHTML = 
                        `<div><strong>${data.answer.persona_name}</strong></div>
                         <div style="margin-top: 10px;">${data.answer.content}</div>
                         <div style="margin-top: 10px; font-size: 12px; color: #666;">
                             신뢰도: ${Math.round(data.answer.confidence * 100)}%
                         </div>`;
                } else {
                    document.getElementById('ai-answer-content').innerHTML = 
                        `<span style="color: #e53e3e;">AI 답변 생성 실패: ${data.error}</span>`;
                }
            })
            .catch(error => {
                document.getElementById('ai-answer-content').innerHTML = 
                    `<span style="color: #e53e3e;">오류: ${error}</span>`;
            });
        }
        
        function updateTurnProgress() {
            const progress = (currentQuestionNumber / totalQuestions) * 100;
            document.getElementById('ai-progress-fill').style.width = progress + '%';
            document.getElementById('ai-progress-text').textContent = `질문 ${currentQuestionNumber}/${totalQuestions}`;
        }
        
        function updateAIProgress() {
            updateTurnProgress();
        }
        
        function submitUserTurnAnswer() {
            const userAnswer = document.getElementById('user-answer').value;
            if (!userAnswer.trim()) {
                showMessage('답변을 입력하세요', 'error');
                return;
            }
            
            if (window.currentPhase !== 'user_turn') {
                showMessage('현재 사용자 턴이 아닙니다', 'error');
                return;
            }
            
            document.getElementById('ai-status').innerHTML = '답변 제출 중...';
            
            // 사용자 턴 답변 제출
            fetch('/user_turn_submit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    comparison_session_id: window.comparisonSessionId,
                    answer: userAnswer
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 사용자 답변을 타임라인에 추가
                    addUserTurnToTimeline();
                    
                    showMessage(`${window.userName}님의 답변이 제출되었습니다`, 'success');
                    window.currentPhase = data.next_phase;
                    
                    // 입력 영역 숨기기
                    document.getElementById('current-turn-input').classList.add('hidden');
                    
                    // AI 턴으로 전환 - AI 답변 자동 처리
                    setTimeout(() => processAITurn(), 1000);
                } else {
                    showMessage(data.error, 'error');
                }
                document.getElementById('ai-status').innerHTML = '';
            })
            .catch(error => {
                showMessage('오류: ' + error, 'error');
                document.getElementById('ai-status').innerHTML = '';
            });
        }
        
        function processAITurn() {
            if (window.currentPhase !== 'ai_turn') {
                console.warn('현재 AI 턴이 아님');
                return;
            }
            
            // 1단계: AI 질문 생성
            document.getElementById('ai-status').innerHTML = '🤖 AI가 질문을 받고 있습니다...';
            
            fetch('/ai_turn_process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    comparison_session_id: window.comparisonSessionId,
                    step: 'question'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.step === 'question_generated') {
                    // AI 질문만 먼저 타임라인에 추가 (답변 없이)
                    addAIQuestionToTimeline(data.ai_question);
                    
                    document.getElementById('ai-status').innerHTML = '🤖 AI가 답변을 생각하고 있습니다...';
                    
                    // 2-3초 후 AI 답변 생성
                    setTimeout(() => {
                        generateAIAnswer();
                    }, 2500);  // 2.5초 딜레이
                } else {
                    showMessage(data.error || 'AI 질문 생성 실패', 'error');
                }
            })
            .catch(error => {
                showMessage('AI 질문 생성 오류: ' + error, 'error');
                document.getElementById('ai-status').innerHTML = '';
            });
        }
        
        function generateAIAnswer() {
            // 2단계: AI 답변 생성
            document.getElementById('ai-status').innerHTML = '🤖 AI가 답변을 생성하고 있습니다...';
            
            fetch('/ai_turn_process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    comparison_session_id: window.comparisonSessionId,
                    step: 'answer'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.step === 'answer_generated') {
                    // AI 답변을 기존 질문에 추가
                    updateAIQuestionWithAnswer(data.ai_answer);
                    
                    if (data.status === 'completed') {
                        // 면접 완료
                        showMessage('비교 면접이 완료되었습니다!', 'success');
                        setTimeout(() => evaluateComparisonInterview(), 2000);
                    } else if (data.status === 'continue') {
                        // 다음 사용자 턴 데이터 저장 (버튼 클릭 시 사용)
                        window.nextUserQuestion = data.next_user_question;
                        window.currentPhase = data.next_phase;
                        currentQuestionNumber = data.question_index;
                        
                        // "다음으로" 버튼 표시
                        showNextTurnButton();
                    }
                } else {
                    showMessage(data.error || 'AI 답변 생성 실패', 'error');
                }
            })
            .catch(error => {
                showMessage('AI 답변 생성 오류: ' + error, 'error');
                document.getElementById('ai-status').innerHTML = '';
            });
        }
        
        function displayAITurnResult(data) {
            // AI 질문과 답변을 표시하는 결과 화면
            const resultDiv = document.getElementById('comparison-result');
            const contentDiv = document.getElementById('comparison-content');
            
            contentDiv.innerHTML = `
                <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <h5>🤖 ${data.ai_answer.persona_name}의 차례</h5>
                    <div style="background: #ebf8ff; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <strong>❓ 질문:</strong> ${data.ai_question.question_content}
                    </div>
                    <div style="background: #e6fffa; padding: 10px; border-radius: 5px;">
                        <strong>🤖 답변:</strong> ${data.ai_answer.content}
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 10px;">
                        신뢰도: ${Math.round(data.ai_answer.confidence * 100)}%
                    </div>
                </div>
            `;
            
            resultDiv.classList.remove('hidden');
            document.getElementById('ai-status').innerHTML = '✅ AI 답변 완료';
        }
        
        function showNextTurnButton() {
            // "다음으로" 버튼 표시
            const statusDiv = document.getElementById('ai-status');
            statusDiv.innerHTML = `
                <div style="text-align: center; margin-top: 15px;">
                    <button onclick="proceedToNextTurn()" style="background: #10b981; color: white; padding: 10px 20px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;">
                        다음 턴으로 진행 →
                    </button>
                </div>
            `;
        }
        
        function proceedToNextTurn() {
            // 사용자가 버튼 클릭 시 다음 턴 진행
            if (window.nextUserQuestion && window.currentPhase === 'user_turn') {
                showTurnQuestion(window.nextUserQuestion, 'user_turn', window.userName);
                updateTurnProgress();
                
                showMessage(`${window.userName}님의 차례입니다`, 'info');
            }
        }
        
        function evaluateComparisonInterview() {
            document.getElementById('ai-status').innerHTML = '📊 비교 면접 평가 중...';
            
            fetch('/evaluate_comparison_interview', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    comparison_session_id: window.comparisonSessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('ai-interview-section').style.display = 'none';
                    document.getElementById('result-section').classList.remove('hidden');
                    showComparisonResults(data.evaluation);
                } else {
                    showMessage('평가 오류: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('평가 중 오류: ' + error, 'error');
            });
        }
        
        function showComparisonResult(comparison) {
            const resultDiv = document.getElementById('comparison-result');
            const contentDiv = document.getElementById('comparison-content');
            
            contentDiv.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <div>
                        <h5>👨‍💻 당신의 답변</h5>
                        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            ${comparison.user_answer || '답변 없음'}
                        </div>
                    </div>
                    <div>
                        <h5>🤖 ${comparison.ai_persona || 'AI 지원자'} 답변</h5>
                        <div style="background: #ebf8ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            ${comparison.ai_answer || 'AI 답변 없음'}
                        </div>
                        <div style="font-size: 12px; color: #666;">
                            신뢰도: ${Math.round((comparison.ai_confidence || 0) * 100)}%
                        </div>
                    </div>
                </div>
                <div style="margin-top: 15px; padding: 15px; background: #f0f9ff; border-radius: 8px;">
                    <h5>📊 비교 분석</h5>
                    <p>AI 지원자와 답변 스타일을 비교해보세요. 다음 질문에서 더 나은 답변을 해보세요!</p>
                </div>
            `;
            
            resultDiv.classList.remove('hidden');
        }
        
        function showAIResults(userEvaluation, aiEvaluation) {
            const userEval = userEvaluation.evaluation;
            const aiEval = aiEvaluation.evaluation;
            
            let resultHtml = `
                <div style="text-align: center; margin-bottom: 30px;">
                    <h3>🤖 AI 지원자와의 면접 비교 결과</h3>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px;">
                    <div>
                        <h4>👨‍💻 당신의 결과</h4>
                        <div class="score-badge ${getScoreClass(userEval.overall_score)}">${userEval.overall_score}/100</div>
                        <div style="margin-top: 15px;">
                            <h5>강점</h5>
                            <ul>
                                ${userEval.strengths.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    <div>
                        <h4>🤖 ${window.aiName || '춘식이'} 결과</h4>
                        <div class="score-badge ${getScoreClass(aiEval.overall_score)}">${aiEval.overall_score}/100</div>
                        <div style="margin-top: 15px;">
                            <h5>${window.aiName || '춘식이'} 강점</h5>
                            <ul>
                                ${aiEval.strengths.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h4>🔧 개선 제안</h4>
                    <ul>
                        ${userEval.improvements.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                    
                    <h4>🎯 추천 사항</h4>
                    <p>${userEval.recommendation}</p>
                </div>
            `;
            
            document.getElementById('overall-result').innerHTML = resultHtml;
        }
        
        function showMessage(text, type = 'info') {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = type === 'error' ? 'error' : 'success';
            msg.classList.remove('hidden');
            setTimeout(() => msg.classList.add('hidden'), 4000);
        }
    </script>
</body>
</html>
"""

@app.route('/test')
def test():
    """간단한 테스트 엔드포인트"""
    return {
        "status": "ok",
        "message": "Flask 앱이 정상적으로 작동 중입니다",
        "port": 8888,
        "debug": True
    }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/debug')
def debug():
    return {"status": "success", "message": "Flask 서버가 정상 작동합니다!"}

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '파일이 없습니다'})
        
        file = request.files['file']
        document_type = request.form.get('document_type', '기타문서')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다'})
        
        if file and allowed_file(file.filename):
            file_content = file.read()
            file_type = file.filename.rsplit('.', 1)[1].lower()
            
            processor = get_document_processor()
            text = processor.extract_text_from_file(file_content, file_type)
            
            if not text.strip():
                return jsonify({'success': False, 'error': '텍스트를 추출할 수 없습니다'})
            
            text_preview = text[:200] + '...' if len(text) > 200 else text
            
            return jsonify({
                'success': True,
                'document_type': document_type,
                'text': text,
                'text_preview': text_preview
            })
        else:
            return jsonify({'success': False, 'error': '지원하지 않는 파일 형식입니다'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    try:
        data = request.json
        documents = data.get('documents', {})
        
        if not documents:
            return jsonify({'success': False, 'error': '분석할 문서가 없습니다'})
        
        processor = get_document_processor()
        user_profile = processor.create_user_profile(documents)
        
        # 프로필을 딕셔너리로 변환하여 JSON 직렬화 가능하게 만듦
        profile_dict = {
            'name': user_profile.name,
            'background': user_profile.background,
            'technical_skills': user_profile.technical_skills,
            'projects': user_profile.projects,
            'experiences': user_profile.experiences,
            'strengths': user_profile.strengths,
            'keywords': user_profile.keywords,
            'career_goal': user_profile.career_goal,
            'unique_points': user_profile.unique_points
        }
        
        return jsonify({
            'success': True,
            'profile': profile_dict
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_personalized', methods=['POST'])
def start_personalized_interview():
    try:
        data = request.json
        company = data.get('company')
        position = data.get('position')
        profile_dict = data.get('user_profile')
        
        # 딕셔너리를 UserProfile 객체로 변환
        from core.document_processor import UserProfile
        user_profile = UserProfile(
            name=profile_dict['name'],
            background=profile_dict['background'],
            technical_skills=profile_dict['technical_skills'],
            projects=profile_dict['projects'],
            experiences=profile_dict['experiences'],
            strengths=profile_dict['strengths'],
            keywords=profile_dict['keywords'],
            career_goal=profile_dict['career_goal'],
            unique_points=profile_dict['unique_points']
        )
        
        system = get_system()
        session_id = system.start_personalized_interview(company, position, user_profile.name, user_profile)
        app_state.current_sessions[session_id] = True
        app_state.user_profiles[session_id] = user_profile
        
        question = system.get_next_question(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'question': question
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_standard', methods=['POST'])
def start_standard_interview():
    try:
        data = request.json
        company = data.get('company')
        position = data.get('position')
        name = data.get('name')
        
        system = get_system()
        # 표준 면접은 기존 start_interview 메서드 사용
        session_id = system.start_interview(company, position, name)
        app_state.current_sessions[session_id] = True
        
        question = system.get_next_question(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'question': question
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_ai_interview', methods=['POST'])
def start_ai_interview():
    """AI 지원자와 턴제 비교 면접 시작 (순서대로 질문)"""
    try:
        import random
        
        data = request.json
        company = data.get('company')
        position = data.get('position')
        name = data.get('name')
        
        # 사용자 면접 시작
        system = get_system()
        user_session_id = system.start_interview(company, position, name)
        app_state.current_sessions[user_session_id] = True
        
        # AI 지원자 면접 시작
        ai_candidate = get_ai_candidate()
        ai_session_id = ai_candidate.start_ai_interview(company, position)
        app_state.ai_sessions[ai_session_id] = True
        
        # 턴제 시스템 초기화
        # 누가 먼저 시작할지 랜덤 결정
        first_turn = "user" if random.random() < 0.5 else "ai"
        
        # 턴제 상태 저장
        comparison_session_id = f"comp_{user_session_id}"
        app_state.comparison_sessions = getattr(app_state, 'comparison_sessions', {})
        app_state.comparison_sessions[comparison_session_id] = {
            'user_session_id': user_session_id,
            'ai_session_id': ai_session_id,
            'current_turn': first_turn,
            'turn_count': 0,
            'max_turns': 20,  # 총 10개 질문씩 (사용자 10개, AI 10개)
            'user_name': name
        }
        
        # AI 이름 가져오기
        from core.llm_manager import LLMProvider
        ai_name = ai_candidate.get_ai_name(LLMProvider.OPENAI_GPT35)
        
        # 첫 번째 턴의 질문 생성
        if first_turn == "user":
            question = system.get_next_question(user_session_id)
            current_respondent = name
        else:
            question = ai_candidate.get_ai_next_question(ai_session_id)
            current_respondent = ai_name
        
        if question:
            return jsonify({
                'success': True,
                'comparison_session_id': comparison_session_id,
                'user_session_id': user_session_id,
                'ai_session_id': ai_session_id,
                'question': question,
                'current_turn': first_turn,
                'current_respondent': current_respondent,
                'turn_count': 0,
                'ai_name': ai_name,
                'order_message': f"첫 번째는 {current_respondent}님이 답변합니다"
            })
        else:
            return jsonify({'success': False, 'error': '질문을 생성할 수 없습니다'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== 새로운 턴제 비교 면접 API ====================

@app.route('/start_comparison_interview', methods=['POST'])
def start_comparison_interview():
    """턴제 비교 면접 시작 (랜덤 순서로 시작자 결정)"""
    try:
        data = request.json
        company = data.get('company')
        position = data.get('position')
        name = data.get('name')
        
        if not all([company, position, name]):
            return jsonify({'success': False, 'error': '모든 필드가 필요합니다'})
        
        # 사용자 세션 시작
        system = get_system()
        user_session_id = system.start_interview(company, position, name)
        app_state.current_sessions[user_session_id] = True
        
        # AI 세션 시작  
        ai_candidate = get_ai_candidate()
        ai_session_id = ai_candidate.start_ai_interview(company, position)
        app_state.ai_sessions[ai_session_id] = True
        
        # AI 이름 가져오기
        from core.llm_manager import LLMProvider
        ai_name = ai_candidate.get_ai_name(LLMProvider.OPENAI_GPT35)
        
        # 랜덤으로 시작자 결정 (50% 확률)
        import random
        starts_with_user = random.choice([True, False])
        initial_phase = 'user_turn' if starts_with_user else 'ai_turn'
        
        # 비교 세션 생성
        comparison_session_id = f"comp_{user_session_id}"
        app_state.comparison_sessions[comparison_session_id] = {
            'user_session_id': user_session_id,
            'ai_session_id': ai_session_id,
            'current_question_index': 1,
            'current_phase': initial_phase,
            'total_questions': 20,
            'user_name': name,
            'ai_name': ai_name,
            'user_answers': [],
            'ai_answers': [],
            'starts_with_user': starts_with_user
        }
        
        if starts_with_user:
            # 사용자부터 시작
            user_question = system.get_next_question(user_session_id)
            
            if user_question:
                return jsonify({
                    'success': True,
                    'comparison_session_id': comparison_session_id,
                    'user_session_id': user_session_id,
                    'ai_session_id': ai_session_id,
                    'question': user_question,
                    'current_phase': 'user_turn',
                    'current_respondent': name,
                    'question_index': 1,
                    'total_questions': 20,
                    'ai_name': ai_name,
                    'starts_with_user': True,
                    'message': f"{name}님부터 시작합니다"
                })
            else:
                return jsonify({'success': False, 'error': '질문을 생성할 수 없습니다'})
        else:
            # AI부터 시작
            return jsonify({
                'success': True,
                'comparison_session_id': comparison_session_id,
                'user_session_id': user_session_id,
                'ai_session_id': ai_session_id,
                'current_phase': 'ai_turn',
                'current_respondent': ai_name,
                'question_index': 1,
                'total_questions': 20,
                'ai_name': ai_name,
                'user_name': name,
                'starts_with_user': False,
                'message': f"{ai_name}부터 시작합니다"
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/user_turn_submit', methods=['POST'])
def user_turn_submit():
    """사용자 턴 답변 제출"""
    try:
        data = request.json
        comparison_session_id = data.get('comparison_session_id')
        answer = data.get('answer')
        
        if not all([comparison_session_id, answer]):
            return jsonify({'success': False, 'error': '모든 필드가 필요합니다'})
        
        # 비교 세션 확인
        comp_session = app_state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            return jsonify({'success': False, 'error': '비교 세션을 찾을 수 없습니다'})
        
        if comp_session['current_phase'] != 'user_turn':
            return jsonify({'success': False, 'error': '현재 사용자 턴이 아닙니다'})
        
        # 사용자 답변 제출
        system = get_system()
        user_session_id = comp_session['user_session_id']
        user_result = system.submit_answer(user_session_id, answer)
        
        # 답변 저장
        comp_session['user_answers'].append({
            'question_index': comp_session['current_question_index'],
            'question': user_result.get('current_question', ''),
            'answer': answer
        })
        
        # AI 턴으로 전환
        comp_session['current_phase'] = 'ai_turn'
        
        return jsonify({
            'success': True,
            'message': '답변이 제출되었습니다',
            'next_phase': 'ai_turn',
            'ai_name': comp_session['ai_name']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_turn_process', methods=['POST'])
def ai_turn_process():
    """AI 턴 처리 - 질문만 먼저 생성하여 반환"""
    try:
        data = request.json
        comparison_session_id = data.get('comparison_session_id')
        step = data.get('step', 'question')  # 'question' 또는 'answer'
        
        if not comparison_session_id:
            return jsonify({'success': False, 'error': '비교 세션 ID가 필요합니다'})
        
        # 비교 세션 확인
        comp_session = app_state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            return jsonify({'success': False, 'error': '비교 세션을 찾을 수 없습니다'})
        
        if comp_session['current_phase'] != 'ai_turn':
            return jsonify({'success': False, 'error': '현재 AI 턴이 아닙니다'})
        
        ai_candidate = get_ai_candidate()
        ai_session_id = comp_session['ai_session_id']
        
        if step == 'question':
            # 1단계: AI 질문만 생성
            ai_question = ai_candidate.get_ai_next_question(ai_session_id)
            
            if not ai_question:
                return jsonify({'success': False, 'error': 'AI 질문을 생성할 수 없습니다'})
            
            # 질문을 세션에 임시 저장
            comp_session['temp_ai_question'] = ai_question
            
            return jsonify({
                'success': True,
                'step': 'question_generated',
                'ai_question': ai_question,
                'message': 'AI 질문이 생성되었습니다. 2-3초 후 답변이 생성됩니다.'
            })
            
        elif step == 'answer':
            # 2단계: AI 답변 생성 (임시 저장된 질문 사용)
            ai_question = comp_session.get('temp_ai_question')
            if not ai_question:
                return jsonify({'success': False, 'error': '저장된 AI 질문이 없습니다'})
            
            # AI 답변 생성
            ai_answer_response = ai_candidate.generate_ai_answer_for_question(ai_session_id, ai_question)
            
            if ai_answer_response.error:
                return jsonify({'success': False, 'error': f'AI 답변 생성 실패: {ai_answer_response.error}'})
            
            # 답변 저장
            comp_session['ai_answers'].append({
                'question_index': comp_session['current_question_index'],
                'question': ai_question['question_content'],
                'answer': ai_answer_response.answer_content
            })
            
            # 임시 질문 삭제
            if 'temp_ai_question' in comp_session:
                del comp_session['temp_ai_question']
            
            # 다음 질문으로 진행
            comp_session['current_question_index'] += 1
            
            # 면접 완료 확인
            if comp_session['current_question_index'] > comp_session['total_questions']:
                comp_session['current_phase'] = 'completed'
                return jsonify({
                    'success': True,
                    'step': 'answer_generated',
                    'status': 'completed',
                    'ai_question': ai_question,
                    'ai_answer': {
                        'content': ai_answer_response.answer_content,
                        'persona_name': ai_answer_response.persona_name,
                        'confidence': ai_answer_response.confidence_score
                    },
                    'message': '비교 면접이 완료되었습니다'
                })
            else:
                # 다음 사용자 턴 준비
                comp_session['current_phase'] = 'user_turn'
                
                # 다음 사용자 질문 가져오기
                system = get_system()
                next_user_question = system.get_next_question(comp_session['user_session_id'])
                
                return jsonify({
                    'success': True,
                    'step': 'answer_generated', 
                    'status': 'continue',
                    'ai_question': ai_question,
                    'ai_answer': {
                        'content': ai_answer_response.answer_content,
                        'persona_name': ai_answer_response.persona_name,
                        'confidence': ai_answer_response.confidence_score
                    },
                    'next_user_question': next_user_question,
                    'next_phase': 'user_turn',
                    'question_index': comp_session['current_question_index'],
                    'user_name': comp_session['user_name']
                })
        
        else:
            return jsonify({'success': False, 'error': '유효하지 않은 단계입니다'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_comparison_state', methods=['POST'])  
def get_comparison_state():
    """비교 면접 현재 상태 조회"""
    try:
        data = request.json
        comparison_session_id = data.get('comparison_session_id')
        
        comp_session = app_state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            return jsonify({'success': False, 'error': '비교 세션을 찾을 수 없습니다'})
        
        return jsonify({
            'success': True,
            'current_phase': comp_session['current_phase'],
            'question_index': comp_session['current_question_index'],
            'total_questions': comp_session['total_questions'],
            'user_name': comp_session['user_name'],
            'ai_name': comp_session['ai_name']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/evaluate_comparison_interview', methods=['POST'])
def evaluate_comparison_interview():
    """비교 면접 평가"""
    try:
        data = request.json
        comparison_session_id = data.get('comparison_session_id')
        
        comp_session = app_state.comparison_sessions.get(comparison_session_id)
        if not comp_session:
            return jsonify({'success': False, 'error': '비교 세션을 찾을 수 없습니다'})
        
        # 간단한 비교 평가 (실제로는 더 정교한 평가 시스템 필요)
        user_answers = comp_session.get('user_answers', [])
        ai_answers = comp_session.get('ai_answers', [])
        
        evaluation = {
            'user_name': comp_session['user_name'],
            'ai_name': comp_session['ai_name'],
            'total_questions': len(user_answers) + len(ai_answers),
            'user_questions': len(user_answers),
            'ai_questions': len(ai_answers),
            'comparison_summary': f"{comp_session['user_name']}님과 {comp_session['ai_name']}의 비교 면접이 완료되었습니다.",
            'user_answers': user_answers,
            'ai_answers': ai_answers
        }
        
        # 세션 정리
        if comparison_session_id in app_state.comparison_sessions:
            del app_state.comparison_sessions[comparison_session_id]
        
        return jsonify({
            'success': True,
            'evaluation': evaluation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/answer', methods=['POST'])
def submit_answer():
    try:
        data = request.json
        session_id = data.get('session_id')
        answer = data.get('answer')
        
        if session_id not in app_state.current_sessions:
            return jsonify({'success': False, 'error': '세션이 만료되었습니다'})
        
        system = get_system()
        result = system.submit_answer(session_id, answer)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/evaluate', methods=['POST'])
def evaluate():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if session_id not in app_state.current_sessions:
            return jsonify({'success': False, 'error': '세션이 만료되었습니다'})
        
        system = get_system()
        evaluation = system.evaluate_interview(session_id)
        
        # 세션 정리
        if session_id in app_state.current_sessions:
            del app_state.current_sessions[session_id]
        if session_id in app_state.user_profiles:
            del app_state.user_profiles[session_id]
        
        return jsonify({
            'success': True,
            'evaluation': evaluation
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== AI 지원자 모드 API ====================

@app.route('/api/ai-candidate/personas', methods=['GET'])
def get_ai_candidate_personas():
    """사용 가능한 AI 지원자 페르소나 목록 반환"""
    try:
        personas = []
        
        # 7개 기업별 페르소나 정보 반환
        supported_companies = ['naver', 'kakao', 'line', 'coupang', 'baemin', 'danggeun', 'toss']
        for company in supported_companies:
            personas.append({
                'company_id': company,
                'name': f"{company.upper()} AI 지원자",
                'description': f"{company} 합격 수준의 AI 지원자"
            })
        
        return jsonify({
            'success': True,
            'personas': personas
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai-candidate/answer', methods=['POST'])
def get_ai_candidate_answer():
    """AI 지원자 답변 생성"""
    try:
        data = request.json
        question_content = data.get('question_content')
        question_type = data.get('question_type', 'GENERAL')
        question_intent = data.get('question_intent', '')
        company_id = data.get('company_id', 'naver')
        position = data.get('position', '백엔드 개발자')
        quality_level = data.get('quality_level', 8)
        
        if not question_content:
            return jsonify({'success': False, 'error': '질문 내용이 필요합니다'})
        
        ai_candidate = get_ai_candidate()
        
        # AnswerRequest 객체 생성
        answer_request = AnswerRequest(
            question_content=question_content,
            question_type=QuestionType(question_type) if hasattr(QuestionType, question_type) else QuestionType.GENERAL,
            question_intent=question_intent,
            company_id=company_id,
            position=position,
            quality_level=QualityLevel(quality_level),
            llm_provider=LLMProvider.OPENAI_GPT35
        )
        
        # AI 답변 생성
        answer_response = ai_candidate.generate_answer(answer_request)
        
        return jsonify({
            'success': True,
            'answer': {
                'content': answer_response.answer_content,
                'confidence': answer_response.confidence_score,
                'reasoning': answer_response.reasoning,
                'company_id': company_id,
                'persona_name': f"{company_id.upper()} AI 지원자"
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai-candidate/compare', methods=['POST'])
def compare_answers():
    """사용자 답변과 AI 답변 비교"""
    try:
        data = request.json
        user_answer = data.get('user_answer')
        ai_answer = data.get('ai_answer')
        question_content = data.get('question_content')
        
        if not all([user_answer, ai_answer, question_content]):
            return jsonify({'success': False, 'error': '모든 필드가 필요합니다'})
        
        # 간단한 비교 분석 (추후 고도화 가능)
        comparison = {
            'user_length': len(user_answer),
            'ai_length': len(ai_answer),
            'similarity_score': 0.7,  # 임시 값
            'user_strengths': ['구체적인 경험 언급', '열정적인 태도'],
            'ai_strengths': ['체계적인 구성', '전문적인 표현'],
            'improvement_suggestions': ['더 구체적인 사례 필요', '논리적 구성 개선']
        }
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== AI 지원자 테스트 페이지 ====================

@app.route('/ai-test')
def ai_test_page():
    """AI 지원자 단독 테스트 페이지"""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI 지원자 테스트</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 10px; margin: 10px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #1a202c; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        select, input, textarea { width: 100%; padding: 10px; border: 2px solid #e2e8f0; border-radius: 5px; }
        button { background: #3182ce; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #2b77cb; }
        .result { background: #f0fff4; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #38a169; }
        .persona-info { background: #ebf8ff; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .loading { text-align: center; color: #666; }
    </style>
</head>
<body>
    <h1>🤖 AI 지원자 테스트 페이지</h1>
    
    <div class="container">
        <h2>테스트 설정</h2>
        <div class="form-group">
            <label>회사 선택:</label>
            <select id="company">
                <option value="naver">네이버</option>
                <option value="kakao">카카오</option>
                <option value="line">라인플러스</option>
                <option value="coupang">쿠팡</option>
                <option value="baemin">배달의민족</option>
                <option value="danggeun">당근마켓</option>
                <option value="toss">토스</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>직군:</label>
            <input type="text" id="position" value="백엔드 개발자">
        </div>
        
        <div class="form-group">
            <label>질문 내용:</label>
            <textarea id="question" rows="3" placeholder="질문을 입력하세요...">간단한 자기소개를 해주세요.</textarea>
        </div>
        
        <div class="form-group">
            <label>질문 유형:</label>
            <select id="question-type">
                <option value="INTRO">자기소개</option>
                <option value="MOTIVATION">지원동기</option>
                <option value="HR">인성</option>
                <option value="TECH">기술</option>
                <option value="COLLABORATION">협업</option>
                <option value="FOLLOWUP">심화</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>품질 레벨 (1-10):</label>
            <input type="range" id="quality" min="1" max="10" value="8">
            <span id="quality-value">8</span>
        </div>
        
        <button onclick="generateAIAnswer()">AI 답변 생성</button>
        <button onclick="loadPersonaInfo()">페르소나 정보 확인</button>
    </div>
    
    <div id="persona-info" class="container" style="display: none;">
        <h2>🤖 AI 페르소나 정보</h2>
        <div id="persona-content"></div>
    </div>
    
    <div id="result" class="container" style="display: none;">
        <h2>🎯 AI 답변 결과</h2>
        <div id="answer-content"></div>
    </div>

    <script>
        document.getElementById('quality').addEventListener('input', function() {
            document.getElementById('quality-value').textContent = this.value;
        });
        
        function loadPersonaInfo() {
            const company = document.getElementById('company').value;
            
            fetch(`/api/ai-candidate/personas`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const selectedPersona = data.personas.find(p => p.company_id === company);
                    if (selectedPersona) {
                        document.getElementById('persona-content').innerHTML = `
                            <h3>${selectedPersona.name}</h3>
                            <p><strong>회사:</strong> ${selectedPersona.company_id}</p>
                            <p><strong>설명:</strong> ${selectedPersona.description}</p>
                        `;
                        document.getElementById('persona-info').style.display = 'block';
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        }
        
        function generateAIAnswer() {
            const company = document.getElementById('company').value;
            const position = document.getElementById('position').value;
            const question = document.getElementById('question').value;
            const questionType = document.getElementById('question-type').value;
            const quality = document.getElementById('quality').value;
            
            if (!question.trim()) {
                alert('질문을 입력하세요');
                return;
            }
            
            document.getElementById('answer-content').innerHTML = '<div class="loading">AI 답변 생성 중...</div>';
            document.getElementById('result').style.display = 'block';
            
            fetch('/api/ai-candidate/answer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question_content: question,
                    question_type: questionType,
                    question_intent: '테스트 질문',
                    company_id: company,
                    position: position,
                    quality_level: parseInt(quality)
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('answer-content').innerHTML = `
                        <div><strong>페르소나:</strong> ${data.answer.persona_name}</div>
                        <div><strong>품질 레벨:</strong> ${quality}점</div>
                        <div><strong>신뢰도:</strong> ${Math.round(data.answer.confidence * 100)}%</div>
                        <div style="margin-top: 15px;"><strong>답변:</strong></div>
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px;">
                            ${data.answer.content}
                        </div>
                    `;
                } else {
                    document.getElementById('answer-content').innerHTML = `
                        <div style="color: red;">오류: ${data.error}</div>
                    `;
                }
            })
            .catch(error => {
                document.getElementById('answer-content').innerHTML = `
                    <div style="color: red;">네트워크 오류: ${error}</div>
                `;
            });
        }
    </script>
</body>
</html>
    """)

# ==================== AI 지원자 단독 면접 모드 API ====================

@app.route('/start_ai_standalone', methods=['POST'])
def start_ai_standalone_interview():
    """AI 지원자 단독 면접 시작"""
    try:
        data = request.json
        company = data.get('company')
        position = data.get('position', '백엔드 개발자')
        quality_level = data.get('quality_level', 8)
        answer_style = data.get('answer_style', 'detailed')
        
        if not company:
            return jsonify({'success': False, 'error': '회사를 선택해주세요'})
        
        # AI 지원자 모델 초기화
        ai_candidate = get_ai_candidate()
        
        # AI 이름 가져오기
        from core.llm_manager import LLMProvider
        ai_name = ai_candidate.get_ai_name(LLMProvider.OPENAI_GPT35)
        
        # 페르소나 정보 가져오기
        persona_summary = ai_candidate.get_persona_summary(company)
        if not persona_summary:
            return jsonify({'success': False, 'error': f'{company} 페르소나 정보를 찾을 수 없습니다'})
        
        # PersonalizedInterviewSystem 사용하여 AI 지원자 전용 세션 시작
        system = get_system()
        
        # AI 지원자용 가상 프로필 생성 (AI 이름 사용)
        from core.document_processor import UserProfile
        
        ai_user_profile = UserProfile(
            name=ai_name,  # AI 이름 사용
            background={
                'career_years': str(persona_summary.get('career_years', '3')),
                'current_position': persona_summary.get('position', position),
                'education': []
            },
            technical_skills=persona_summary.get('main_skills', []),
            projects=[],
            experiences=[],
            strengths=persona_summary.get('key_strengths', []),
            keywords=[],
            career_goal=f"{company} {position}로서 성장하고 싶습니다.",
            unique_points=[]
        )
        
        # 개인화된 면접 세션 시작 (AI 이름 사용)
        ai_session_id = system.start_personalized_interview(company, position, ai_name, ai_user_profile)
        
        # 세션 정보 저장 (난이도 설정 포함)
        app_state.current_sessions[ai_session_id] = {
            'type': 'ai_standalone',
            'quality_level': quality_level,
            'answer_style': answer_style,
            'company': company,
            'position': position
        }
        app_state.user_profiles[ai_session_id] = ai_user_profile
        
        # 첫 번째 질문 생성
        first_question = system.get_next_question(ai_session_id)
        
        if first_question:
            return jsonify({
                'success': True,
                'ai_session_id': ai_session_id,
                'total_questions': len(system.sessions[ai_session_id].question_plan),
                'persona': {
                    'name': ai_name,  # AI 이름 사용
                    'career_years': persona_summary.get('career_years'),
                    'current_position': persona_summary.get('position'),
                    'main_skills': persona_summary.get('main_skills', [])
                },
                'question': first_question
            })
        else:
            return jsonify({'success': False, 'error': '첫 번째 질문을 생성할 수 없습니다'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_standalone_answer', methods=['POST'])
def generate_ai_standalone_answer():
    """AI 지원자 단독 면접 답변 생성"""
    try:
        data = request.json
        ai_session_id = data.get('ai_session_id')
        
        if not ai_session_id or ai_session_id not in app_state.current_sessions:
            return jsonify({'success': False, 'error': '유효하지 않은 세션입니다'})
        
        # 세션 설정 가져오기
        session_config = app_state.current_sessions[ai_session_id]
        if isinstance(session_config, dict):
            quality_level = session_config.get('quality_level', 8)
            answer_style = session_config.get('answer_style', 'detailed')
        else:
            quality_level = 8
            answer_style = 'detailed'
        
        system = get_system()
        ai_candidate = get_ai_candidate()
        
        # 현재 진행 중인 질문 정보 가져오기
        session = system.sessions.get(ai_session_id)
        if not session:
            return jsonify({'success': False, 'error': '세션을 찾을 수 없습니다'})
        
        # 현재 질문 계획 가져오기
        current_question_plan = session.get_next_question_plan()
        if not current_question_plan:
            return jsonify({'success': False, 'error': '진행할 질문이 없습니다'})
        
        # 현재 질문 생성 (실제 질문 내용)
        company_data = system.get_company_data(session.company_id)
        question_content, question_intent = system._generate_next_question(
            session, company_data, current_question_plan["type"], current_question_plan.get("fixed", False)
        )
        
        # AI 답변 생성 요청 구성 (난이도 설정 반영)
        answer_request = AnswerRequest(
            question_content=question_content,
            question_type=current_question_plan["type"],
            question_intent=question_intent,
            company_id=session.company_id,
            position=session.position,
            quality_level=QualityLevel(quality_level),
            llm_provider=LLMProvider.OPENAI_GPT35,
            additional_context=f"답변 스타일: {answer_style}"
        )
        
        # AI 답변 생성
        answer_response = ai_candidate.generate_answer(answer_request)
        
        # 답변을 세션에 추가
        qa_pair = QuestionAnswer(
            question_id=f"q_{session.current_question_count + 1}",
            question_type=current_question_plan["type"],
            question_content=question_content,
            answer_content=answer_response.answer_content,
            timestamp=datetime.now(),
            question_intent=question_intent
        )
        
        session.add_qa_pair(qa_pair)
        
        # 면접 완료 여부 확인
        is_complete = session.is_complete()
        
        return jsonify({
            'success': True,
            'answer': {
                'content': answer_response.answer_content,
                'persona_name': answer_response.persona_name,
                'quality_level': answer_response.quality_level.value,
                'confidence': answer_response.confidence_score,
                'response_time': answer_response.response_time
            },
            'is_complete': is_complete
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_standalone_next', methods=['POST'])
def get_ai_standalone_next_question():
    """AI 지원자 단독 면접 다음 질문"""
    try:
        data = request.json
        ai_session_id = data.get('ai_session_id')
        
        if not ai_session_id or ai_session_id not in app_state.current_sessions:
            return jsonify({'success': False, 'error': '유효하지 않은 세션입니다'})
        
        system = get_system()
        
        # 다음 질문 가져오기
        next_question = system.get_next_question(ai_session_id)
        
        if next_question:
            return jsonify({
                'success': True,
                'question': next_question
            })
        else:
            return jsonify({'success': False, 'error': '더 이상 질문이 없습니다'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_standalone_evaluate', methods=['POST'])
def evaluate_ai_standalone_interview():
    """AI 지원자 단독 면접 최종 평가"""
    try:
        data = request.json
        ai_session_id = data.get('ai_session_id')
        
        if not ai_session_id or ai_session_id not in app_state.current_sessions:
            return jsonify({'success': False, 'error': '유효하지 않은 세션입니다'})
        
        system = get_system()
        
        # 면접 평가 수행
        evaluation = system.evaluate_interview(ai_session_id)
        
        # 세션 정리 (AI 세션 관리 포함)
        if ai_session_id in app_state.current_sessions:
            del app_state.current_sessions[ai_session_id]
        if ai_session_id in app_state.ai_sessions:
            del app_state.ai_sessions[ai_session_id]
        if ai_session_id in app_state.user_profiles:
            del app_state.user_profiles[ai_session_id]
        
        return jsonify({
            'success': True,
            'evaluation': evaluation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🎯 고도화된 AI 면접 시스템 시작!")
    print("📱 브라우저에서 http://localhost:8888 접속")
    print("\n✨ 새로운 기능:")
    print("  • 📄 자소서/이력서/포트폴리오 업로드")
    print("  • 🔍 자동 문서 분석 및 프로필 생성")
    print("  • 🎯 개인 배경 기반 맞춤형 질문")
    print("  • 📊 개인화된 평가 및 피드백")
    print("  • 🏷️ 질문별 개인화 여부 표시")
    print("\n🚀 고도화 기능:")
    print("  • 📝 면접관별 고정 질문 + 생성 질문 조합")
    print("  • 👥 3명 면접관 (인사/실무/협업) 역할 구분")
    print("  • 🔧 고정 질문 관리 API (추가/삭제/수정)")
    print("  • 📈 질문 통계 및 분석 기능")
    print("\n📚 API 엔드포인트:")
    print("  • /enhanced/start - 고도화된 면접 시작")
    print("  • /api/questions/stats - 질문 통계")
    print("  • /api/questions/{type} - 면접관별 질문 조회")
    
    try:
        print("🔧 서버 설정:")
        print(f"   - Host: 0.0.0.0 (모든 인터페이스)")
        print(f"   - Port: 8888")
        print(f"   - Debug: True")
        print(f"   - Threaded: True")
        print()
        
        app.run(host='0.0.0.0', port=8888, debug=True, threaded=True, use_reloader=False)
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
        import traceback
        traceback.print_exc()

# ==================== AI 면접 관련 새로운 엔드포인트 ====================

@app.route('/ai_answer', methods=['POST'])
def submit_ai_answer():
    """AI 모드에서 답변 제출 (사용자 답변 + AI 답변 생성)"""
    try:
        data = request.json
        user_session_id = data.get('user_session_id')
        ai_session_id = data.get('ai_session_id')
        answer = data.get('answer')
        
        if not all([user_session_id, ai_session_id, answer]):
            return jsonify({'success': False, 'error': '모든 필드가 필요합니다'})
        
        # 사용자 답변 제출
        system = get_system()
        user_result = system.submit_answer(user_session_id, answer)
        
        # AI 답변 생성
        ai_candidate = get_ai_candidate()
        ai_question = ai_candidate.get_ai_next_question(ai_session_id)
        ai_answer_response = None
        
        if ai_question:
            ai_answer_response = ai_candidate.generate_ai_answer_for_question(ai_session_id, ai_question)
        
        # 응답 구성
        response_data = {
            'success': True,
            'status': user_result['status'],
            'answered_count': user_result.get('answered_count', 0),
            'ai_answer': {
                'content': ai_answer_response.answer_content if ai_answer_response else "",
                'confidence': ai_answer_response.confidence_score if ai_answer_response else 0,
                'persona_name': ai_answer_response.persona_name if ai_answer_response else "AI"
            }
        }
        
        if user_result['status'] == 'interview_complete':
            response_data['message'] = user_result['message']
        else:
            response_data['question'] = user_result['question']
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ai_evaluate', methods=['POST'])
def evaluate_ai_interview():
    """AI 모드 면접 평가"""
    try:
        data = request.json
        user_session_id = data.get('user_session_id')
        ai_session_id = data.get('ai_session_id')
        
        if not all([user_session_id, ai_session_id]):
            return jsonify({'success': False, 'error': '모든 세션 ID가 필요합니다'})
        
        # 사용자 면접 평가
        system = get_system()
        user_evaluation = system.evaluate_interview(user_session_id)
        
        # AI 지원자 면접 평가
        ai_candidate = get_ai_candidate()
        ai_evaluation = ai_candidate.evaluate_ai_interview(ai_session_id)
        
        return jsonify({
            'success': True,
            'user_evaluation': user_evaluation,
            'ai_evaluation': ai_evaluation
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})