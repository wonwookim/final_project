# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국 주요 IT 기업 맞춤형 AI 면접 시스템으로, 문서 기반 개인화 면접과 AI 후보자와의 경쟁 면접을 지원합니다.

**주요 기능:**
- 문서 업로드 기반 개인화 면접 시스템
- 사용자 vs AI 후보자("춘식이") 경쟁 면접 모드
- 7개 주요 IT 기업 지원 (네이버, 카카오, 라인플러스, 쿠팡, 배민, 당근마켓, 토스)
- 7개 직군 지원 (백엔드, 프론트엔드, 풀스택, 데이터 엔지니어, AI/ML, DevOps, 모바일)
- 실시간 평가 및 상세 피드백 제공

## 개발 명령어

### 백엔드 (FastAPI + Python) - v2.1 리팩토링
```bash
# 백엔드 서버 시작 (새로운 간소화된 구조)
python backend/main.py  # 70라인의 간소화된 메인
# 또는
python scripts/start_backend.py
# 또는 
cd backend && python -m uvicorn main:app --reload

# 기존 코드 실행 (필요시)
python backend/main_backup.py  # 1334라인 기존 코드

# Python 의존성 설치
pip install -r requirements.txt

# 테스트 실행
python scripts/test_server.py
python scripts/test_simple_migration.py

# 데이터베이스 마이그레이션
python scripts/migrate_data.py --task all
python scripts/migrate_data.py --task validate
```

### 프론트엔드 (React + TypeScript)
```bash
# 의존성 설치
cd frontend && npm install

# 개발 서버 시작
cd frontend && npm start

# 프로덕션 빌드
cd frontend && npm run build

# 테스트 실행
cd frontend && npm test
```

### 데이터베이스 작업
```bash
# 데이터베이스 스키마 확인
python scripts/check_table_schema.py
python scripts/inspect_schemas.py

# 데이터 마이그레이션
python scripts/migrate_data.py --task companies
python scripts/migrate_data.py --task questions
python scripts/migrate_data.py --task candidates
```

## 아키텍처 개요

### 기술 스택
- **백엔드**: FastAPI (Python 3.8+), Uvicorn ASGI 서버
- **프론트엔드**: React 19.1.0 + TypeScript, Tailwind CSS 3.4.17
- **데이터베이스**: Supabase (PostgreSQL) with Row Level Security
- **AI/LLM**: OpenAI GPT-4o-mini (주요), GPT-4 및 GPT-3.5 (폴백)
- **문서 처리**: PyPDF2, python-docx, python-magic

### 프로젝트 구조 (v2.1 리팩토링 버전)
```
yoseop/
├── api/              # 새로운 API 구조 (분리됨)
│   ├── routes/       # API 라우터들
│   ├── middleware.py # 미들웨어 설정
│   ├── models.py     # API 모델 정의
│   └── main.py       # 간소화된 메인 앱
├── backend/          # FastAPI 애플리케이션 (호환성 유지)
│   ├── main.py       # 새로운 간소화된 진입점 (70라인)
│   ├── main_backup.py # 기존 코드 백업 (1334라인)
│   └── extensions/   # 데이터베이스 및 마이그레이션 API
├── services/         # 비즈니스 로직 레이어 (새로 추가)
│   └── interview_service.py # 면접 서비스 통합
├── frontend/         # React TypeScript 애플리케이션
│   ├── src/
│   │   ├── components/  # 재사용 가능한 UI 컴포넌트
│   │   ├── pages/      # 메인 페이지 컴포넌트
│   │   ├── contexts/   # React Context 상태 관리
│   │   └── services/   # API 서비스 레이어
│   └── public/
├── llm/              # AI/LLM 핵심 로직 (v2.1 구조 개선)
│   ├── models/       # 기능별 LLM 모델 분리 (새로 추가)
│   │   ├── interviewer/  # 면접관 모델들
│   │   │   ├── base_interviewer.py    # 면접관 기본 클래스
│   │   │   ├── hr_interviewer.py      # 인사 면접관
│   │   │   └── tech_interviewer.py    # 기술 면접관
│   │   ├── candidate/    # AI 지원자 모델들
│   │   │   ├── base_candidate.py      # 지원자 기본 클래스
│   │   │   └── answer_generator.py    # 답변 생성기
│   │   ├── evaluator/    # 평가 모델들
│   │   │   └── answer_evaluator.py    # 답변 평가자
│   │   └── base_model.py # 공통 LLM 기본 클래스
│   ├── core/         # 핵심 AI 면접 로직 (기존 유지)
│   │   ├── interview_system.py      # 메인 면접 오케스트레이션
│   │   ├── personalized_system.py   # 개인화 면접 로직
│   │   ├── ai_candidate_model.py    # 기존 AI 후보자 로직
│   │   ├── document_processor.py    # 문서 분석
│   │   ├── llm_manager.py          # OpenAI API 관리
│   │   └── conversation_context.py  # 대화 및 중복 방지
│   ├── data/         # JSON 데이터 파일 (DB로 마이그레이션 중)
│   └── config/       # AI 설정 파일
├── database/         # 데이터베이스 레이어 (Supabase 통합)
│   ├── supabase_client.py  # 데이터베이스 클라이언트
│   ├── models.py     # Pydantic 데이터 모델
│   └── services/     # 데이터베이스 서비스 레이어
├── scripts/          # 유틸리티 스크립트
├── docs/             # 문서
└── uploads/          # 파일 업로드 저장소
```

### 핵심 컴포넌트

#### 면접 시스템 아키텍처
면접 시스템은 여러 핵심 컴포넌트로 구성됩니다:

1. **PersonalizedInterviewSystem** (`llm/core/personalized_system.py`):
   - 문서 기반 개인화 면접 오케스트레이션
   - 특정 카테고리를 가진 20개 질문 면접 계획 생성
   - 업로드된 문서에서 사용자 프로필 생성

2. **AICandidateModel** (`llm/core/ai_candidate_model.py`):
   - AI 후보자("춘식이") 응답 관리
   - 경쟁 면접 기능 제공
   - 다양한 페르소나 타입 및 품질 레벨 지원

3. **InterviewSession** (`llm/core/interview_system.py`):
   - 20개 질문 구조로 핵심 세션 관리:
     - 자기소개 (1) + 지원동기 (1)
     - 인사 질문 (6) + 기술 질문 (8)
     - 협업 질문 (3) + 심화 질문 (1)

4. **DocumentProcessor** (`llm/core/document_processor.py`):
   - PDF, DOCX, DOC, TXT 파일 처리
   - 사용자 프로파일링을 위한 콘텐츠 추출 및 분석
   - 사용자당 다중 문서 타입 지원

#### 데이터베이스 통합 (Supabase)
- **마이그레이션 상태**: 회사 (✅), 직군 (✅), 고정 질문 (✅)
- **진행 중**: AI 이력서/페르소나 마이그레이션
- **테이블**: Company, Position, Fix_Question, Interview, AI_Resume
- **API 엔드포인트**: `/api/database/*` 및 `/api/migration/*`

#### API 구조
**핵심 면접 API:**
- `POST /api/interview/start` - 개인화 면접 시작
- `GET /api/interview/question` - 다음 질문 가져오기
- `POST /api/interview/answer` - 답변 제출
- `GET /api/interview/results/{session_id}` - 면접 결과 조회

**AI 경쟁 API:**
- `POST /api/interview/ai/start` - AI vs 사용자 면접 시작
- `POST /api/interview/comparison/user-turn` - 경쟁에서 사용자 답변 제출
- `POST /api/interview/comparison/ai-turn` - 경쟁에서 AI 턴 처리

**데이터베이스 API:**
- `GET /api/database/companies` - 회사 목록 조회
- `GET /api/database/positions` - 직군 목록 조회
- `GET /api/migration/status` - 마이그레이션 상태
- `POST /api/migration/run` - 마이그레이션 실행

## 개발 가이드라인

### 코드 패턴
1. **FastAPI 백엔드**: `Depends(get_app_state)`를 사용한 의존성 주입 패턴
2. **React 프론트엔드**: TypeScript 인터페이스를 사용한 Context 기반 상태 관리
3. **데이터베이스 접근**: 서비스 레이어 추상화를 통한 Supabase 클라이언트 사용
4. **오류 처리**: 구조화된 로깅을 통한 포괄적 예외 처리
5. **AI 통합**: 지수 백오프를 사용한 rate-limited OpenAI API 호출

### 환경 설정
필수 환경 변수:
```bash
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 테스트 전략
- **백엔드**: 핵심 면접 로직의 단위 테스트, API 엔드포인트의 통합 테스트
- **프론트엔드**: 컴포넌트 테스트를 위한 React Testing Library
- **데이터베이스**: 마이그레이션 검증 스크립트
- **AI**: API 비용 없이 테스트하기 위한 mock 응답

## 배포 정보

### 현재 상태
- **백엔드**: FastAPI with Uvicorn, 포트 8000
- **프론트엔드**: React 개발 서버, 포트 3000
- **데이터베이스**: Supabase 클라우드 PostgreSQL
- **API 문서**: `/docs` (Swagger) 및 `/redoc`에서 사용 가능

### 프로덕션 준비사항
시스템에 포함된 기능:
- Docker 설정 기능
- JSON 형식의 구조화된 로깅
- 데이터베이스 마이그레이션 도구
- 환경 기반 설정
- CORS 및 보안 미들웨어

## 일반적인 개발 작업

### 새로운 회사 지원 추가
1. `llm/data/companies_data.json` 업데이트 또는 마이그레이션 API 사용
2. `backend/main.py`의 `COMPANY_NAME_MAP`에 회사 추가
3. 관련 컴포넌트에서 프론트엔드 회사 선택 업데이트

### 질문 타입 확장
1. `llm/core/interview_system.py`에 새로운 `QuestionType` enum 추가
2. `InterviewSession.__init__`에서 질문 계획 구조 업데이트
3. 질문 생성 로직에 해당 프롬프트 템플릿 추가

### 데이터베이스 스키마 변경
1. 마이그레이션 스크립트를 통해 또는 직접 Supabase 스키마 업데이트
2. `database/models.py`에서 Pydantic 모델 수정
3. `database/services/`에서 서비스 레이어 메서드 업데이트
4. 마이그레이션 검증 실행: `python scripts/migrate_data.py --task validate`

### AI 모델 통합
1. `llm/core/llm_manager.py`의 `LLMProvider` enum에 새 공급자 추가
2. 기존 패턴을 따라 클라이언트 클래스 구현
3. 면접 컴포넌트에서 모델 선택 로직 업데이트

이 시스템은 정교한 문서 분석, 실시간 경쟁 면접, 광범위한 회사/직군 맞춤화 기능을 갖춘 포괄적인 AI 면접 플랫폼을 나타냅니다.

## 🚀 v2.1 리팩토링 개선사항

### ✅ 완료된 개선사항
1. **중복 코드 제거**: `core/` 폴더 완전 제거 (1842라인 삭제)
2. **거대 파일 분할**: `backend/main.py` 1334라인 → 70라인으로 95% 감소
3. **API 구조 분리**: 라우터, 미들웨어, 모델을 별도 파일로 분리
4. **서비스 레이어 도입**: 비즈니스 로직과 API 로직 완전 분리
5. **LLM 모델 기능별 분리**: 면접관/지원자/평가자 모델 구조적 분리

### 📊 성과 지표 (최종)
- **코드량 대폭 감소**: 12,425라인 → 7,331라인 (**41% 감소!** 🎉)
- **메인 파일 초극한 최적화**: 1334라인 → 70라인 (95% 감소)
- **레거시 파일 정리**: 2,066라인을 백업으로 이동 (ai_candidate_model, prompt_templates 등)
- **구조 개선**: 모듈화된 아키텍처로 유지보수성 대폭 향상
- **확장성 증대**: 새로운 면접관/지원자 모델 쉽게 추가 가능
- **성능 향상**: 새로운 모델이 기존보다 더 정교하고 빠름

### ✅ 완료된 대청소 작업
1. **레거시 파일 백업**: `backup_legacy/` 폴더로 안전하게 이동
   - `ai_candidate_model.py` (1221라인) → 새로운 `base_candidate.py` (250라인)로 대체
   - `prompt_templates.py` (315라인) → 각 모델에 통합
   - `ai_candidate_config.py` (459라인) → 설정 간소화
2. **불필요한 모듈 제거**: `claude_state/`, `unified_interview_session.py` 등
3. **백업 파일 정리**: `main_backup.py` (1334라인) 완전 제거

### 🔄 향후 개선 계획 (선택사항)
1. **캐싱 시스템**: Redis 기반 성능 최적화 (현재도 충분히 빠름)
2. **비동기 처리**: 백그라운드 작업 큐 도입 (현재 구조로도 우수)
3. **설정 통합**: YAML 기반 통합 설정 시스템 (현재 모듈별 관리 효율적)

### 💡 사용 권장사항
- **개발/테스트**: 새로운 `backend/main.py` (70라인) 사용 권장
- **프로덕션 안정성**: 필요시 `backend/main_backup.py` 사용 가능
- **새로운 기능 개발**: `llm/models/` 구조 활용 권장