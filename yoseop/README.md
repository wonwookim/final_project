# 🎯 AI 면접 시스템 (AI Interview System)

한국 주요 IT 기업 맞춤형 AI 면접 시스템으로, **사용자 vs AI 후보자 "춘식이"와의 실시간 경쟁 면접**을 제공합니다.

> **🎉 최신 업데이트 (v2.1)**: Supabase 데이터베이스 통합 완료! 프로덕션 레벨 데이터 관리와 확장성이 크게 향상되었습니다.

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

### 🎯 지원 직군 (7개)
- 백엔드 개발자
- 프론트엔드 개발자
- 풀스택 개발자
- 데이터 엔지니어
- AI/ML 엔지니어
- DevOps 엔지니어
- 모바일 개발자

### ✨ 새로 추가된 기능 (v2.1)
- **🗄️ Supabase 데이터베이스 통합**: 프로덕션 레벨 데이터 관리
- **📊 데이터 마이그레이션 시스템**: 로컬 JSON → 클라우드 DB 완전 이전
- **🔌 데이터베이스 API**: RESTful API로 데이터 관리
- **📈 실시간 데이터 동기화**: 면접 세션 데이터 실시간 저장

## 🛠️ 기술 스택

### **프로덕션 레벨 아키텍처 (v2.1)**

#### Frontend
- **React 19.1.0 + TypeScript** - 최신 React with 타입 안정성
- **Tailwind CSS 3.4.17** - 유틸리티 우선 CSS
- **React Router 7.7.0** - 라우팅
- **Axios 1.10.0** - API 통신

#### Backend  
- **FastAPI** - 고성능 비동기 웹 프레임워크
- **Python 3.8+** - 메인 언어
- **Uvicorn** - ASGI 서버
- **Supabase Python Client 2.17.0** - 데이터베이스 연결

#### Database
- **Supabase (PostgreSQL)** - 클라우드 데이터베이스
- **Row Level Security (RLS)** - 보안 관리
- **Real-time subscriptions** - 실시간 데이터 동기화

#### LLM/AI
- **OpenAI GPT-4o-mini** - 메인 AI 모델
- **GPT-4 & GPT-3.5** - 추가 모델 옵션
- **Custom LLM Manager** - 멀티 모델 지원 아키텍처

## 🏗️ 프로젝트 구조 (v2.1)

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
│   └── extensions/         # 확장 기능들
│       ├── database_integration.py    # 데이터베이스 API
│       └── migration_api.py          # 마이그레이션 API
│
├── 🗄️ database/             # 데이터베이스 레이어 (NEW!)
│   ├── supabase_client.py   # Supabase 클라이언트
│   ├── models.py           # 데이터 모델 (Pydantic)
│   └── services/           # 데이터 서비스
│       ├── existing_tables_service.py  # 기존 테이블 관리
│       └── data_migration_service.py   # 마이그레이션 서비스
│
├── 🧠 llm/                  # AI/LLM 로직
│   ├── core/               # 핵심 AI 로직
│   │   ├── personalized_system.py    # 개인화 면접 시스템
│   │   ├── ai_candidate_model.py     # AI 후보자 "춘식이" 모델
│   │   ├── interview_system.py       # 면접 시스템 코어
│   │   └── llm_manager.py           # LLM 관리자
│   ├── data/               # AI 데이터 (마이그레이션 완료)
│   │   ├── companies_data.json      # 기업 정보 → DB 이전 완료
│   │   ├── candidate_personas.json  # AI 후보자 페르소나 → DB 이전 중
│   │   └── fixed_questions.json     # 고정 질문 세트 → DB 이전 완료
│   └── config/            # AI 설정 파일
│
├── 🔄 scripts/              # 실행 및 마이그레이션 스크립트 (NEW!)
│   ├── migrate_data.py     # 데이터 마이그레이션 도구
│   ├── check_table_schema.py    # 스키마 검사
│   └── test_migration.py   # 마이그레이션 테스트
│
├── 🤖 agents/               # 미래 MCP/Agent2Agent 확장
├── 📁 media/                # 미래 이력서/화상면접 파일 저장
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

# Python 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일이 이미 생성되어 있습니다 (API 키 포함)
# 필요시 수정: vim .env

# 포함된 설정:
# - OPENAI_API_KEY (설정 완료)
# - SUPABASE_URL (설정 완료)  
# - SUPABASE_ANON_KEY (설정 완료)
# - 기타 서버/AI 설정들
```

### 3. 데이터베이스 상태 확인
```bash
# 현재 데이터베이스 상태 확인
python scripts/migrate_data.py --task validate

# 결과: 
# - 회사 데이터: 7개 (마이그레이션 완료)
# - 포지션 데이터: 7개 (마이그레이션 완료)  
# - 고정 질문: 26개 (마이그레이션 완료)
# - AI 후보자: 진행 중 (서버 안정화 대기)
```

### 4. 백엔드 서버 실행
```bash
# 방법 1: 스크립트 사용
python scripts/start_backend.py

# 방법 2: 직접 실행
python backend/main.py

# 방법 3: uvicorn 사용
cd backend && python -m uvicorn main:app --reload

# 출력 예시:
# ✅ 데이터베이스 확장 로드 성공
# ✅ 마이그레이션 API 로드 성공  
# ✅ 데이터베이스 API 라우터 등록 완료
```

### 5. 프론트엔드 실행
```bash
# 의존성 설치
cd frontend
npm install

# 개발 서버 시작
npm start
```

### 6. 브라우저 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs
- **데이터베이스 관리**: http://127.0.0.1:8000/api/database/...

## 🎮 사용 가이드

### 🏆 AI 경쟁 면접 (메인 기능)

1. **면접 설정**
   - 회사 선택 (네이버, 카카오, 토스 등) - DB에서 실시간 로드
   - 직군 선택 (백엔드, 프론트엔드, 풀스택 등) - DB에서 실시간 로드
   - 이름 입력

2. **면접 진행**
   - 영상통화 스타일 UI에서 진행
   - 상단: 3명의 면접관 (인사/협업/기술)
   - 하단: 사용자와 춘식이 영역
   - 질문 유형에 따라 해당 면접관 자동 하이라이트

3. **턴제 시스템**
   - 사용자 턴 → 춘식이 턴 순서로 진행
   - 각각 독립적인 세션에서 질문 받고 답변
   - 모든 데이터 실시간 Supabase 저장
   - 실시간 타임라인에서 전체 진행 상황 확인

4. **최종 결과**
   - 사용자 vs 춘식이 성과 비교
   - 카테고리별 상세 분석
   - 개선 포인트 제안

## 🔧 개발자 가이드

### 🧪 테스트 실행
```bash
# 데이터베이스 연결 테스트
python scripts/test_simple_migration.py

# 스키마 검사
python scripts/inspect_schemas.py

# 서버 테스트  
python scripts/test_server.py
```

### 🗄️ 데이터베이스 관리

#### 마이그레이션 도구
```bash
# 전체 데이터 마이그레이션
python scripts/migrate_data.py --task all

# 특정 데이터만 마이그레이션
python scripts/migrate_data.py --task companies
python scripts/migrate_data.py --task questions  
python scripts/migrate_data.py --task candidates

# 드라이 런 (실제 실행하지 않고 미리보기)
python scripts/migrate_data.py --task all --dry-run
```

#### API를 통한 데이터 관리
```bash
# 마이그레이션 상태 확인
curl http://127.0.0.1:8000/api/migration/status

# 데이터 검증
curl http://127.0.0.1:8000/api/migration/validate

# 마이그레이션 실행 (웹 인터페이스)
curl -X POST http://127.0.0.1:8000/api/migration/run \
  -H "Content-Type: application/json" \
  -d '{"task": "all", "dry_run": false}'
```

### 📊 API 엔드포인트 (v2.1)

#### 핵심 면접 API
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/health` | GET | 서버 상태 확인 |
| `/api/interview/start` | POST | 면접 시작 |
| `/api/interview/question` | GET | 다음 질문 가져오기 |
| `/api/interview/answer` | POST | 답변 제출 |
| `/api/interview/ai/start` | POST | AI 경쟁 면접 시작 |
| `/api/interview/comparison/user-turn` | POST | 사용자 턴 제출 |
| `/api/interview/comparison/ai-turn` | POST | AI 턴 처리 |

#### 새로운 데이터베이스 API (v2.1)
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/database/companies` | GET | 회사 목록 조회 |
| `/api/database/positions` | GET | 직군 목록 조회 |
| `/api/database/questions` | GET | 질문 목록 조회 |
| `/api/migration/status` | GET | 마이그레이션 상태 |
| `/api/migration/run` | POST | 마이그레이션 실행 |
| `/api/migration/validate` | GET | 데이터 검증 |

## 🗄️ 데이터베이스 현황 (v2.1)

### ✅ 마이그레이션 완료
- **Company 테이블**: 7개 회사 데이터 (네이버, 카카오, 라인플러스, 쿠팡, 배달의민족, 당근마켓, 토스)
- **Position 테이블**: 7개 직군 (백엔드, 프론트엔드, 풀스택, 데이터, AI/ML, DevOps, 모바일)
- **Fix_Question 테이블**: 26개 기술 분야별 고정 질문

### 🔄 진행 중
- **AI_Resume 테이블**: AI 후보자 페르소나 (서버 안정화 대기)

### 📊 테이블 구조
```sql
-- Company 테이블
company_id (int, PK)
name (string, NOT NULL)  
talent_profile, core_competencies, tech_focus,
interview_keywords, question_direction,
company_culture, technical_challenges

-- Position 테이블  
position_id (int, PK)
position_name (string, NOT NULL)

-- Fix_Question 테이블
question_id (int, PK)
question_index (int)
question_content (string, NOT NULL)
question_intent, question_level

-- Interview 테이블 (기존)
interview_id, user_id, ai_resume_id, 
user_resume_id, posting_id, company_id,
position_id, total_feedback, date
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
- Supabase 인증 키 보안 관리
- Row Level Security (RLS) 적용

### 💰 비용 관리
- GPT-4o-mini 사용으로 비용 최적화
- Supabase 무료 티어 한도 모니터링
- 토큰 사용량 모니터링 권장

### 🎯 성능
- FastAPI의 비동기 처리로 동시 사용자 지원 향상
- Supabase 실시간 구독으로 데이터 동기화 최적화
- React의 가상 DOM으로 UI 성능 최적화

## 📚 추가 문서

- [데이터베이스 마이그레이션 가이드](docs/DATABASE_MIGRATION.md) - Supabase 통합 상세 내용
- [API 문서](docs/API_REFERENCE.md) - 상세한 API 스펙  
- [개발자 가이드](docs/DEVELOPER_GUIDE.md) - 개발 환경 설정 및 기여 방법

---

**개발팀**: AI Interview System Team  
**버전**: 2.1.0 (Supabase 통합 완료)  
**최종 업데이트**: 2025-01-23  
**데이터베이스**: Supabase (PostgreSQL)  
**백업 리포지토리**: https://github.com/1203choi/final_demo.git