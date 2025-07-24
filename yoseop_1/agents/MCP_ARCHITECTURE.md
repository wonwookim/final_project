# MCP (Model Context Protocol) 아키텍처 설계

## 🎯 목표
현재 독립적인 면접관 AI들과 춘식이를 **협업하는 에이전트 시스템**으로 전환

## 🏗️ 시스템 아키텍처

```
agents/
├── protocols/
│   ├── mcp_protocol.py          # MCP 프로토콜 구현
│   ├── agent_interface.py       # 공통 에이전트 인터페이스
│   └── message_types.py         # 메시지 타입 정의
│
├── core/
│   ├── agent_manager.py         # 에이전트 생명주기 관리
│   ├── context_store.py         # 공유 컨텍스트 저장소
│   ├── message_broker.py        # 에이전트 간 메시지 중개
│   └── decision_engine.py       # 협업 의사결정 엔진
│
├── interviewer_agents/
│   ├── hr_agent.py             # 인사 면접관 에이전트
│   ├── collaboration_agent.py  # 협업 면접관 에이전트
│   ├── technical_agent.py      # 기술 면접관 에이전트
│   └── coordinator_agent.py    # 면접 진행 조정자
│
├── candidate_agents/
│   ├── chunsik_agent.py        # 춘식이 에이전트
│   ├── candidate_base.py       # AI 후보자 기본 클래스
│   └── multi_candidate.py      # 다중 후보자 관리
│
└── scenarios/
    ├── collaborative_interview.py  # 협업 면접 시나리오
    ├── group_interview.py          # 그룹 면접 시나리오
    └── adaptive_interview.py       # 적응형 면접 시나리오
```

## 🔄 MCP 워크플로우

### 1단계: 에이전트 등록 및 초기화
```python
# 면접 시작 시 모든 에이전트 등록
agents = [
    HRAgent("김인사", personality="warm_supportive"),
    CollaborationAgent("박협업", personality="analytical_systematic"), 
    TechnicalAgent("이기술", personality="direct_technical"),
    ChunsikAgent("춘식이", persona="selected_persona")
]

# 공유 컨텍스트 초기화
context = SharedContext(
    interview_type="ai_competition",
    company="네이버",
    position="백엔드 개발자",
    participants=agents
)
```

### 2단계: 면접관 협업 - 질문 생성
```python
# 면접관들이 협업하여 다음 질문 결정
hr_agent.propose_question("인성 측면에서 이런 질문은 어떨까요?")
tech_agent.respond("기술적 깊이가 부족한 것 같습니다")
collab_agent.analyze("이전 답변을 보면 협업 경험을 더 파야할 것 같습니다")

# 최종 질문 합의
coordinator.finalize_question(consensus_question)
```

### 3단계: 실시간 반응 및 피드백
```python
# 사용자 답변 후 면접관들의 실시간 반응
user_answer = "저는 React와 Node.js를 주로 사용합니다"

hr_agent.internal_thought("기본적인 답변이네요")
tech_agent.internal_thought("구체적인 경험이 부족합니다")
collab_agent.suggest_followup("프로젝트 협업 경험을 물어보죠")
```

### 4단계: 춘식이 vs 다른 AI 후보자들
```python
# 멀티 에이전트 경쟁
chunsik_agent.generate_answer(question, context)
other_ai_agent.generate_answer(question, context)

# 에이전트들 간 상호작용
chunsik_agent.react_to_other("그 답변은 너무 이론적인 것 같은데요?")
other_ai_agent.counter_react("실무 경험으로 답변드리겠습니다")
```

## 📡 MCP 프로토콜 구현

### 메시지 타입
```python
class MCPMessageType(Enum):
    QUESTION_PROPOSAL = "question_proposal"
    AGENT_REACTION = "agent_reaction" 
    CONTEXT_SHARE = "context_share"
    CONSENSUS_REQUEST = "consensus_request"
    FOLLOWUP_SUGGESTION = "followup_suggestion"
    CANDIDATE_INTERACTION = "candidate_interaction"
```

### 에이전트 간 통신
```python
class MCPMessage:
    sender: str              # 송신 에이전트
    recipients: List[str]    # 수신 에이전트들
    message_type: MCPMessageType
    content: Dict[str, Any]  # 메시지 내용
    context_id: str         # 공유 컨텍스트 ID
    timestamp: datetime
    requires_response: bool  # 응답 필요 여부
```

## 🎬 실제 면접 진행 시나리오

### 시나리오 1: 협업 면접관
```
👤 사용자: "저는 팀 프로젝트에서 백엔드를 담당했습니다"

🧠 내부 에이전트 대화:
HR: "팀워크 능력을 더 파봅시다"
기술: "구체적인 기술 스택을 물어봐야겠네요"
협업: "의사소통 방식에 대해 질문하겠습니다"

👔 협업 면접관 (화면): "팀 프로젝트에서 의견 충돌이 있을 때 어떻게 해결하셨나요?"
```

### 시나리오 2: AI 후보자들 상호작용
```
👔 기술 면접관: "어려웠던 기술적 문제와 해결 방안을 설명해주세요"

👤 사용자: "데이터베이스 최적화 문제가 있었는데..."

🤖 춘식이: "저도 비슷한 경험이 있어서 말씀드리면, 인덱싱 전략을 바꿔서 해결했습니다"

🤖 다른 AI: "제가 보기에는 캐싱 전략이 더 효과적일 것 같은데요"
```

## 🔧 기술적 구현 방안

### 1. 기존 시스템과의 통합
- **현재**: `llm/core/` 의 개별 AI 모델들
- **MCP 후**: 각 모델을 에이전트로 래핑
- **백엔드 API**: `/api/mcp/` 엔드포인트 추가

### 2. 프론트엔드 변경사항
- **에이전트 상태 표시**: 어떤 에이전트가 "생각 중"인지 표시
- **실시간 상호작용**: 에이전트들의 내부 대화 선택적 노출
- **멀티 후보자 UI**: 여러 AI 후보자들 동시 표시

### 3. 성능 고려사항
- **병렬 처리**: 에이전트들의 동시 사고/반응
- **컨텍스트 최적화**: 공유 메모리 효율적 관리
- **응답 시간**: 실시간 상호작용을 위한 응답 속도 보장

## 🚀 단계적 구현 계획

### Phase 1: 기본 MCP 프레임워크
- [ ] 에이전트 인터페이스 정의
- [ ] 메시지 브로커 구현
- [ ] 공유 컨텍스트 시스템

### Phase 2: 면접관 협업
- [ ] 3명 면접관을 에이전트로 전환
- [ ] 질문 생성 시 협업 로직
- [ ] 실시간 반응 시스템

### Phase 3: 멀티 AI 후보자
- [ ] 춘식이 에이전트화
- [ ] 추가 AI 후보자들 추가
- [ ] 상호작용 UI 개발

### Phase 4: 고급 시나리오
- [ ] 적응형 면접 (답변에 따른 동적 조정)
- [ ] 그룹 면접 모드
- [ ] 면접관-후보자 직접 상호작용

## 💡 혁신적인 기능 아이디어

### 1. "면접관 회의" 모드
```
면접 중간에 면접관들이 잠깐 회의:
"이 후보자 어떻게 보세요?"
"기술력은 괜찮은데 소통 능력을 더 봐야겠네요"
"다음 질문은 협업 관련으로 하죠"
```

### 2. "AI 후보자 경쟁" 모드  
```
여러 AI가 동시에 면접:
춘식이: "이 문제는 제가 실제로 해결해본 적이 있습니다"
김AI: "저는 다른 접근법을 써봤는데 더 효율적이었어요"
박AI: "둘 다 좋은 방법이지만 확장성 측면에서는..."
```

### 3. "실시간 피드백" 모드
```
사용자가 답변하는 동안 면접관들의 실시간 반응:
😊 HR: "좋은 답변이네요"
🤔 기술: "구체적인 예시가 더 필요할 것 같은데"
✍️ 협업: "팀워크 부분을 더 강조해보세요"
```

이 MCP 시스템으로 단순한 질의응답을 넘어서 **진짜 면접장 같은 역동적인 상호작용**을 만들 수 있을 것 같습니다!