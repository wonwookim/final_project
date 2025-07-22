# 🎯 AI 면접 시스템 (AI Interview System)

한국 주요 IT 기업 맞춤형 AI 면접 시스템으로, **사용자 vs AI 후보자 "춘식이"와의 실시간 경쟁 면접**을 제공합니다.

> **🎉 최신 업데이트**: 프로젝트가 깔끔한 3파트 아키텍처로 리팩터링되어 확장성과 유지보수성이 크게 향상되었습니다!

## 🚀 주요 기능

### 🏆 **AI 경쟁 면접 (메인 기능)**
- **실시간 경쟁**: 사용자와 AI 후보자 "춘식이"가 턴제로 면접 진행
- **영상통화 스타일 UI**: 3명의 면접관(인사/협업/기술)과 함께하는 몰입감 있는 인터페이스
- **동적 면접관 하이라이트**: 질문 유형에 따라 해당 면접관이 강조
- **세션 완전 분리**: 사용자와 AI가 각각 독립적인 세션에서 면접 진행
- **실시간 타임라인**: 모든 질문과 답변이 시간순으로 표시

### 🏢 지원 기업 (7개)
| 기업 | 특화 분야 | 핵심 기술 |
|------|-----------|-----------|
| 네이버 | 검색, AI, 클라우드 | 하이퍼클로바X, NCP |
| 카카오 | 플랫폼, 메시징 | MSA, 대용량 처리 |
| 라인플러스 | 글로벌 메시징 | 실시간 통신, 품질 |
| 쿠팡 | 이커머스, 물류 | 스케일링, 자동화 |
| 배달의민족 | 플랫폼, 매칭 | 실시간 시스템 |
| 당근마켓 | 로컬 커뮤니티 | 위치 기반 서비스 |
| 토스 | 핀테크, 결제 | 보안, 사용자 경험 |

### ✨ 다음 버전 예정 기능
- **이력서 기반 춘식이 페르소나**: 고정된 춘식이 캐릭터 중 선택
- **사용자 이력서 맞춤 질문**: 개인 이력서 업로드 기반 맞춤형 질문 생성
- **화상면접 기능**: WebRTC 기반 실시간 비디오 면접
- **MCP/Agent2Agent**: 면접관들 간 실시간 상호작용

## 🛠️ 기술 스택

### **리팩터링된 새로운 아키텍처**

#### Frontend
- **React 19.1.0 + TypeScript** - 최신 React with 타입 안정성
- **Tailwind CSS 3.4.17** - 유틸리티 우선 CSS
- **React Router 7.7.0** - 라우팅
- **Axios 1.10.0** - API 통신

#### Backend  
- **FastAPI** - 고성능 비동기 웹 프레임워크
- **Python 3.8+** - 메인 언어
- **Uvicorn** - ASGI 서버

#### LLM/AI
- **OpenAI GPT-4o-mini** - 메인 AI 모델
- **GPT-4 & GPT-3.5** - 추가 모델 옵션
- **Custom LLM Manager** - 멀티 모델 지원 아키텍처

## 🏗️ 새로운 프로젝트 구조

```
final_Q_test/
├── 📱 frontend/              # React TypeScript 앱
│   ├── src/
│   │   ├── components/       # 재사용 가능 컴포넌트
│   │   ├── pages/           # 페이지 컴포넌트 (면접 진행, 설정 등)
│   │   ├── contexts/        # React Context (면접 상태 관리)
│   │   └── services/        # API 호출 서비스
│   └── package.json
│
├── 🖥️ backend/               # FastAPI 서버
│   ├── main.py             # FastAPI 메인 애플리케이션
│   └── extensions/         # 미래 확장 기능들
│
├── 🧠 llm/                  # AI/LLM 로직
│   ├── core/               # 핵심 AI 로직
│   │   ├── personalized_system.py    # 개인화 면접 시스템
│   │   ├── ai_candidate_model.py     # AI 후보자 "춘식이" 모델
│   │   ├── interview_system.py       # 면접 시스템 코어
│   │   └── llm_manager.py           # LLM 관리자
│   ├── data/               # AI 데이터
│   │   ├── companies_data.json      # 기업 정보
│   │   ├── candidate_personas.json  # AI 후보자 페르소나
│   │   └── fixed_questions.json     # 고정 질문 세트
│   └── config/            # AI 설정 파일
│
├── 🤖 agents/               # 미래 MCP/Agent2Agent 확장
├── 📁 media/                # 미래 이력서/화상면접 파일 저장
├── 🔧 scripts/              # 실행 및 테스트 스크립트
├── 📄 shared/               # 공통 유틸리티
└── 📚 docs/                 # 프로젝트 문서
```

## 📦 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd final_Q_test

# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. API 키 설정
```bash
# .env 파일 생성 (프로젝트 루트에)
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 3. 백엔드 서버 실행
```bash
# 방법 1: 스크립트 사용
python scripts/start_backend.py

# 방법 2: 직접 실행
python backend/main.py

# 방법 3: uvicorn 사용
cd backend && python -m uvicorn main:app --reload
```

### 4. 프론트엔드 실행
```bash
# 의존성 설치
cd frontend
npm install

# 개발 서버 시작
npm start
```

### 5. 브라우저 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs

## 🎮 사용 가이드

### 🏆 AI 경쟁 면접 (메인 기능)

1. **면접 설정**
   - 회사 선택 (네이버, 카카오, 토스 등)
   - 직군 선택 (백엔드, 프론트엔드, 풀스택 등)
   - 이름 입력

2. **면접 진행**
   - 영상통화 스타일 UI에서 진행
   - 상단: 3명의 면접관 (인사/협업/기술)
   - 하단: 사용자와 춘식이 영역
   - 질문 유형에 따라 해당 면접관 자동 하이라이트

3. **턴제 시스템**
   - 사용자 턴 → 춘식이 턴 순서로 진행
   - 각각 독립적인 세션에서 질문 받고 답변
   - 실시간 타임라인에서 전체 진행 상황 확인

4. **최종 결과**
   - 사용자 vs 춘식이 성과 비교
   - 카테고리별 상세 분석
   - 개선 포인트 제안

## 🔧 개발자 가이드

### 🧪 테스트 실행
```bash
# 리팩터링 테스트
python scripts/test_refactor.py

# 서버 테스트  
python scripts/test_server.py
```

### 🚀 새로운 기능 추가

#### 1. 백엔드 API 확장
```bash
# backend/extensions/ 에 새로운 모듈 추가
mkdir backend/extensions/new_feature
# API 엔드포인트 추가 후 main.py에서 임포트
```

#### 2. 프론트엔드 컴포넌트 추가
```bash
# frontend/src/components/ 에 새 컴포넌트 추가
# React + TypeScript + Tailwind CSS 사용
```

#### 3. AI 로직 확장
```bash
# llm/core/ 에 새로운 AI 모듈 추가
# 기존 LLM Manager 패턴 활용
```

### 📊 API 엔드포인트

#### 주요 API (v2.0)
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/health` | GET | 서버 상태 확인 |
| `/api/interview/start` | POST | 면접 시작 |
| `/api/interview/question` | GET | 다음 질문 가져오기 |
| `/api/interview/answer` | POST | 답변 제출 |
| `/api/interview/ai/start` | POST | AI 경쟁 면접 시작 |
| `/api/interview/comparison/user-turn` | POST | 사용자 턴 제출 |
| `/api/interview/comparison/ai-turn` | POST | AI 턴 처리 |

#### 요청/응답 예시
```javascript
// AI 경쟁 면접 시작
POST /api/interview/ai/start
{
  "company": "네이버",
  "position": "백엔드 개발자",
  "mode": "ai_competition",
  "difficulty": "medium",
  "candidate_name": "김개발"
}

// 응답
{
  "session_id": "comp_abc123",
  "comparison_session_id": "comp_session_xyz",
  "user_session_id": "user_abc",
  "ai_session_id": "ai_def",
  "question": { ... },
  "current_phase": "user_turn",
  "ai_name": "춘식이"
}
```

## 🔮 미래 확장 계획

### 📋 이력서 기반 기능
- **춘식이 페르소나 선택**: 신입/3년차/시니어 등 고정 페르소나
- **사용자 맞춤 질문**: 이력서 업로드 기반 개인화된 질문 생성
- **구현 위치**: `media/resumes/`, `backend/extensions/resume/`

### 📹 화상면접 기능
- **WebRTC 실시간 통신**: 실제 화상면접 환경
- **음성 인식**: 답변 자동 텍스트 변환
- **표정 분석**: 추가적인 면접 피드백
- **구현 위치**: `frontend/src/components/video/`, `backend/extensions/video/`

### 🤝 MCP/Agent2Agent
- **면접관 협업**: 3명 면접관 AI들의 실시간 상호작용
- **그룹 면접**: 여러 AI 후보자들과의 동시 면접
- **구현 위치**: `agents/protocols/`, `agents/coordination/`

## 🚨 주의사항

### 🔐 보안
- OpenAI API 키를 `.env` 파일에서 관리 (Git에 커밋하지 않음)
- 환경변수로 민감한 설정 관리

### 💰 비용 관리
- GPT-4o-mini 사용으로 비용 최적화
- 토큰 사용량 모니터링 권장
- 대량 사용 시 요청 제한 고려

### 🎯 성능
- FastAPI의 비동기 처리로 동시 사용자 지원 향상
- React의 가상 DOM으로 UI 성능 최적화
- 컴포넌트 기반 구조로 재사용성 극대화

## 📚 추가 문서

- [리팩터링 보고서](REFACTORING_SUMMARY.md) - 새로운 구조로의 마이그레이션 상세 내용
- [API 문서](docs/API_REFERENCE.md) - 상세한 API 스펙
- [개발자 가이드](docs/DEVELOPER_GUIDE.md) - 개발 환경 설정 및 기여 방법

---

**개발팀**: AI Interview System Team  
**버전**: 2.0.0 (리팩터링 완료)  
**최종 업데이트**: 2025-01-22  
**백업 리포지토리**: https://github.com/1203choi/final_demo.git