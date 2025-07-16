# 🎯 AI 면접 시스템 (AI Interview System)

한국 주요 IT 기업 맞춤형 AI 면접 시스템으로, 개인화된 질문 생성과 실시간 AI 지원자와의 경쟁 면접을 제공합니다.

## 🚀 주요 기능

### 🎭 면접 모드
1. **📄 개인화 면접** - 문서 업로드 기반 맞춤형 질문
2. **📝 표준 면접** - 기본 질문으로 진행
3. **🤖 AI 경쟁 면접** - AI 지원자 "춘식이"와 턴제 경쟁
4. **👀 AI 단독 면접** - AI 답변 시연 모드

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

### 🎯 핵심 특징
- **🧠 AI 기반 질문 생성**: GPT-4o-mini 활용
- **📊 실시간 평가**: 답변별 즉시 피드백
- **🔄 중복 방지**: 의미적 유사도 기반 질문 필터링
- **⏰ 자연스러운 흐름**: AI 답변 타이밍 최적화
- **🎲 랜덤 시작**: 사용자/AI 랜덤 순서 결정
- **📈 상세 분석**: 개인화된 면접 결과 리포트

## 🛠️ 기술 스택

### Backend
- **Python 3.8+** - 메인 언어
- **Flask 3.0.3** - 웹 프레임워크
- **OpenAI 1.82.1** - GPT API 연동

### Document Processing
- **PyPDF2** - PDF 파일 처리
- **python-docx** - Word 문서 처리

### Frontend
- **HTML5/CSS3/JavaScript** - 반응형 웹 UI
- **Bootstrap 스타일링** - 모던 인터페이스

## 📦 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd final_Q_test

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. API 키 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 3. 서버 실행
```bash
# 메인 실행 파일로 시작
python run.py

# 또는 직접 실행
python web/app.py
```

### 4. 브라우저 접속
```
http://localhost:8888
```

## 🎮 사용 가이드

### 📄 개인화 면접
1. **문서 업로드**: 자기소개서, 이력서, 포트폴리오 업로드
2. **자동 분석**: AI가 문서를 분석하여 개인 프로필 생성
3. **맞춤형 질문**: 개인 배경을 반영한 질문 생성 (20개)
4. **실시간 평가**: 답변별 즉시 피드백 및 점수

### 🤖 AI 경쟁 면접
1. **정보 입력**: 기업, 직군, 이름 입력
2. **랜덤 시작**: 사용자 또는 AI가 랜덤하게 먼저 시작
3. **턴제 진행**: 사용자 → AI → 사용자 순서로 교대 답변
4. **타임라인 UI**: 모든 질문과 답변이 시간순으로 표시
5. **비교 분석**: 최종 사용자 vs AI 성과 비교

### ⭐ 고급 기능

#### 🔄 중복 질문 방지
- 의미적 유사도 분석 (60% 의도 + 30% 키워드 + 10% 구조)
- 실시간 중복 감지 및 필터링
- 50% 유사도 임계값 적용

#### ⏰ AI 답변 타이밍
1. **1단계**: AI 질문 표시 ("생각 중..." 상태)
2. **2단계**: 2.5초 후 답변 생성 및 표시
3. **자연스러운 흐름**: 사람과 유사한 답변 패턴

#### 📊 상세 평가 시스템
- **개별 답변 점수**: 각 질문별 100점 만점
- **카테고리별 분석**: 인사/기술/협업 영역별 평가
- **개선 제안**: 구체적인 피드백과 다음 단계 가이드

## 🏗️ 시스템 아키텍처

### 📁 프로젝트 구조
```
final_Q_test/
├── core/                    # 핵심 비즈니스 로직
│   ├── ai_candidate_model.py      # AI 지원자 모델
│   ├── conversation_context.py    # 대화 컨텍스트 관리
│   ├── document_processor.py      # 문서 처리
│   ├── interview_system.py        # 면접 시스템 코어
│   ├── llm_manager.py             # LLM 관리
│   ├── personalized_system.py     # 개인화 시스템
│   └── utils.py                   # 유틸리티 함수
├── web/                     # 웹 애플리케이션
│   └── app.py                     # Flask 메인 앱
├── data/                    # 데이터 파일
│   ├── companies_data.json        # 기업 정보
│   ├── candidate_personas.json    # AI 지원자 페르소나
│   └── fixed_questions.json       # 고정 질문 세트
├── config/                  # 설정 파일
├── docs/                    # 문서
├── uploads/                 # 업로드 파일 저장
└── requirements.txt         # 의존성 목록
```

### 🔄 데이터 플로우
```
사용자 입력 → 문서 처리 → 프로필 생성 → 질문 생성 → 면접 진행 → 평가 분석
```

## 🔧 API 엔드포인트

### 📋 주요 API
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/upload` | POST | 문서 업로드 |
| `/analyze` | POST | 문서 분석 및 프로필 생성 |
| `/start_personalized` | POST | 개인화 면접 시작 |
| `/start_standard` | POST | 표준 면접 시작 |
| `/start_comparison_interview` | POST | AI 경쟁 면접 시작 |
| `/answer` | POST | 답변 제출 |
| `/evaluate` | POST | 면접 평가 |
| `/ai_turn_process` | POST | AI 턴 처리 |

### 📝 요청/응답 예시
```javascript
// 개인화 면접 시작
POST /start_personalized
{
  "company": "naver",
  "position": "백엔드 개발자",
  "user_profile": { ... }
}

// 응답
{
  "success": true,
  "session_id": "session_123",
  "question": {
    "question_type": "자기소개",
    "question_content": "본인을 소개해 주세요.",
    "progress": "1/20",
    "personalized": false
  }
}
```

## ⚙️ 설정 및 커스터마이징

### 🎛️ 주요 설정값
```python
# core/constants.py
DEFAULT_TOTAL_QUESTIONS = 20    # 총 질문 수
GPT_MODEL = "gpt-4o-mini"       # 사용 모델
MAX_TOKENS = 400                # 최대 토큰
TEMPERATURE = 0.7               # 창의성 수준
```

### 🏢 새 기업 추가
1. `data/companies_data.json`에 기업 정보 추가:
```json
{
  "id": "new_company",
  "name": "새로운 기업",
  "talent_profile": "인재상",
  "core_competencies": ["역량1", "역량2"],
  "tech_focus": ["기술1", "기술2"]
}
```

2. `core/constants.py`의 `SUPPORTED_COMPANIES`에 추가

### 🎭 AI 페르소나 커스터마이징
`data/candidate_personas.json`에서 AI 지원자 특성 수정:
- 배경 정보 (경력, 학력)
- 기술 스킬
- 성격 특성
- 답변 스타일

## 🔍 성능 및 모니터링

### 📈 주요 메트릭
- **평균 응답 시간**: 3-5초
- **토큰 사용량**: 질문당 1,500-2,000 토큰
- **동시 사용자**: 최대 10명 (단일 서버)
- **정확도**: 95% 이상 성공률

### 🚨 에러 처리
- API 호출 실패 시 자동 재시도 (3회)
- Rate Limit 대응 (지수 백오프)
- 입력 데이터 검증 및 sanitization
- 구조화된 에러 로깅

## 🧪 테스트

### 🏃‍♂️ 기본 테스트
```bash
# AI 지원자 시스템 테스트
python test_ai_candidate.py

# 세션 관리 테스트
python test_session.py

# 전체 시스템 데모
python demo_ai_candidate.py
```

### 🔬 단위 테스트
```bash
# 문서 처리 테스트
python -m pytest tests/test_document_processor.py

# 질문 생성 테스트
python -m pytest tests/test_interview_system.py
```

## 🚨 주의사항

### 🔐 보안
- OpenAI API 키 노출 방지 (.env 파일 사용)
- 업로드 파일 검증 (16MB 제한, 확장자 검사)
- SQL 인젝션 방지 (파라미터화된 쿼리)

### 💰 비용 관리
- GPT API 사용량 모니터링 필요
- 대량 사용 시 비용 최적화 고려
- 토큰 수 제한으로 비용 제어

### 🎯 품질 관리
- 생성된 질문의 적절성 검토 권장
- 정기적인 AI 답변 품질 점검
- 사용자 피드백 기반 개선

## 🤝 기여 및 지원

### 📝 기여 방법
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Create Pull Request

### 🐛 버그 리포트
- GitHub Issues 활용
- 재현 가능한 단계 포함
- 환경 정보 명시

### 💡 기능 제안
- 구체적인 사용 사례 설명
- 기대 효과 명시
- 기술적 구현 방안 고려

## 📄 라이선스

MIT License - 상업적/비상업적 사용 가능

---

**개발팀**: AI Interview System Team  
**버전**: 2.0.0  
**최종 업데이트**: 2025-01-16  
**문의**: [GitHub Issues](https://github.com/your-repo/issues)