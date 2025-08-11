#!/usr/bin/env python3
"""
면접관 프롬프트 빌더
service.py에서 분리된 모든 프롬프트 관련 로직을 담당
"""

from typing import Dict, List, Any
from ..shared.constants import GPT_MODEL


class InterviewerPromptBuilder:
    """면접관 프롬프트 생성을 담당하는 클래스"""
    
    def __init__(self):
        # 면접관별 확장된 주제 풀 구축
        self.expanded_topic_pools = self._build_expanded_topic_pools()
        # 면접관별 페르소나 정의
        self.interviewer_personas = self._build_interviewer_personas()
    
    def _build_expanded_topic_pools(self) -> Dict[str, List[str]]:
        """면접관별 확장된 주제 풀 (기존 5개 → 15개)"""
        return {
            'HR': [
                '가치관_신념체계', '성장_학습동기', '갈등_해결경험', '스트레스_압박대처',
                '팀워크_상호존중', '실패_극복과정', '의사소통_공감능력', '변화_적응력',
                '윤리_도덕적판단', '장기_커리어비전', '자기성찰_피드백수용', '챕임감_주인의식',
                '다양성_포용성', '목표설정_달성의지', '인간관계_신뢰구축'
            ],
            'TECH': [
                '핵심기술_전문성', '아키텍처_설계경험', '성능최적화_튜닝', '코드품질_랑팩토링',
                '문제해결_디버깅', '신기술_학습적용', '데이터베이스_설계', '보안_취약점대응',
                '테스트_자동화', '배포_운영경험', '모니터링_장애대응', '협업도구_프로세스',
                '기술선택_의사결정', '레거시_마이그레이션', '오픈소스_기여'
            ],
            'COLLABORATION': [
                '팀내_소통방식', '갈등_중재해결', '크로스팀_협업', '프로젝트_역할분담',
                '의견조율_합의', '지식공유_멘토링', '회의_퍼실리테이션', '피드백_주고받기',
                '문화차이_극복', '원격_협업경험', '이해관계자_관리', '팀빌딩_관계형성',
                '리더십_발휘', '팔로워십_지원', '다양성_포용'
            ]
        }
    
    def _build_interviewer_personas(self) -> Dict[str, str]:
        """면접관별 전문성 및 관점을 정의한 페르소나"""
        return {
            "HR": """
### 당신의 전문성 ###
당신은 인사 전문가(HR 면접관)입니다.  
**당신의 유일한 임무는 지원자의 인간적 측면(가치관, 인성, 스트레스 내성, 문화 적합성)을 평가하는 것입니다.**
[중요 제약 조건]
- **기술 스택, 프로젝트 세부 기술, 코드, 알고리즘, 문제 해결 과정에 대해 절대 묻지 마십시오.**  
- **오직 지원자의 가치관, 태도, 장기 근무 가능성, 회사 문화 적합성을 탐구하는 질문만 하십시오.**  
- **기술적, 협업적 평가 요소가 포함된 질문은 금지됩니다.**
- **핵심 초점**: 이 사람이 회사에서 모나지 않게 오랫동안 일할 수 있을까?
- **평가 관점**: 문화 적합성, 장기 근무 가능성, 인성, 스트레스 내성
- **질문 스타일**: 사람에 대한 깊이 있는 이해, 가치관과 인성 탐구
- **중요 사항**: 기술적 세부사항보다는 인간적 측면에 집중
### [출력 전 자기 검증] ###
1. 이 질문은 인간적 측면만 평가하는가?  
2. 기술/협업 관련 요소가 섞여 있지 않은가?  
→ 위반 시 질문을 다시 생성하십시오.
""",
            
            "TECH": """
### 당신의 전문성 ###
당신은 기술 전문가(TECH 면접관)입니다.  
**당신의 유일한 임무는 지원자의 기술 역량(회사 기술 환경 적합성, 실무 경험 깊이, 문제 해결 능력)을 평가하는 것입니다.**
[중요 제약 조건]
- **인성, 가치관, 문화 적합성, 협업 태도에 대한 질문은 절대 하지 마십시오.**  
- **오직 기술 환경 적합성과 실무 적용 경험, 문제 해결 능력을 검증하는 질문만 하십시오.**  
- **비기술적 요소가 섞인 질문은 금지됩니다.**
- **핵심 초점**: 이 회사가 원하는 기술스택으로 실제 업무를 수행할 수 있을까?
- **평가 관점**: 회사 기술 환경 적합성, 실무 경험 깊이, 문제 해결 능력
- **질문 스타일**: 실무 중심, 구체적 경험 요구, 기술적 논리와 판단력 평가
- **중요 사항**: 이론적 지식도 중요하지만 실제 적용 경험과 성과가 더 중요시됨
### [출력 전 자기 검증] ###
1. 이 질문은 기술 역량만 평가하는가?  
2. 인성/협업 관련 요소가 섞여 있지 않은가?  
→ 위반 시 질문을 다시 생성하십시오.
""",
            
            "COLLABORATION": """
### 당신의 전문성 ###
당신은 협업 전문가(COLLABORATION 면접관)입니다.  
**당신의 유일한 임무는 지원자의 협업 능력(팀워크, 커뮤니케이션, 갈등 해결 능력)을 평가하는 것입니다.**
[중요 제약 조건]
- **기술적 문제 해결 능력, 개인의 가치관/인성 전체를 평가하는 질문은 절대 하지 마십시오.**  
- **오직 협업, 소통, 갈등 조율, 팀워크 경험만을 탐구하십시오.**  
- **기술적 세부 내용이나 HR적 질문은 금지됩니다.**
- **핵심 초점**: 이 사람과 소통과 협업을 잘할 수 있을까? 협동심과 팀워크는?
- **평가 관점**: 팀워크, 커뮤니케이션, 갈등 해결, 협업 경험
- **질문 스타일**: 상황 기반 협업 경험 탐구, 갈등 조율 능력 평가
- **중요 사항**: 개인 역량보다는 팀 전체의 성과와 협력에 집중
### [출력 전 자기 검증] ###
1. 이 질문은 협업 능력만 평가하는가?  
2. 기술/인성 관련 평가 요소가 섞여 있지 않은가?  
→ 위반 시 질문을 다시 생성하십시오.
"""
        }
    
    def build_system_prompt_for_question_generation(self) -> str:
        """질문 생성용 시스템 프롬프트"""
        return """당신은 전문 면접관입니다. 

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "프로젝트에서 가장 어려웠던 기술적 도전은 무엇이었나요?", "intent": "문제 해결 능력과 기술적 역량 평가"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""
    
    def build_main_question_prompt(self, user_resume: Dict, company_info: Dict, 
                                 interviewer_role: str, topic: str) -> str:
        """전사적 DNA 매트릭스 프롬프트 빌더 - 회사의 모든 특성과 직무 전문성을 융합한 맞춤형 질문 생성"""
        
        # 1. [회사 DNA] 정보 체계적 추출
        company_name = company_info.get('name', '회사')
        talent_profile = company_info.get('talent_profile', '정의되지 않음')
        core_competencies = ', '.join(company_info.get('core_competencies', ['정의되지 않음']))
        tech_focus = ', '.join(company_info.get('tech_focus', ['정의되지 않음']))
        question_direction = company_info.get('question_direction', '정의되지 않음')
        
        # 기업문화 정보 추출
        company_culture = company_info.get('company_culture', {})
        core_values = []
        work_style = ''
        if isinstance(company_culture, dict):
            core_values = company_culture.get('core_values', [])
            work_style = company_culture.get('work_style', '')
        
        # 2. [지원자 직무 컨텍스트] 정의
        position = user_resume.get('position', '개발자')
        position_contexts = {
            "백엔드": "대용량 트래픽 처리, 데이터베이스 설계, MSA 아키텍처, API 성능 최적화, 시스템 안정성, 분산 트랜잭션",
            "프론트엔드": "웹 성능 최적화(로딩 속도), 상태 관리, UI/UX 개선, 크로스 브라우징, 웹 접근성, Critical Rendering Path",
            "AI": "llm 모델 설계, 모델 성능 및 정확도, 데이터 전처리, 과적합 방지, 최신 논문 구현, MLOps, Transformer 아키텍처",
            "데이터사이언스": "A/B 테스트 설계, 통계적 가설 검증, Feature Engineering, 데이터 시각화, 예측 모델링, 불균형 데이터 처리",
            "기획": "사용자 요구사항 분석, 제품 로드맵 설정, KPI 정의, 시장 조사, 기능 우선순위 결정, RICE/ICE 프레임워크"
        }
        
        # 직군 매칭 (부분 문자열 포함 검사)
        position_context = "소프트웨어 개발 일반"
        for key, context in position_contexts.items():
            if key in position or key.lower() in position.lower():
                position_context = context
                break
        
        # 면접관별 주제 풀 확장
        interviewer_topics = self.expanded_topic_pools.get(interviewer_role, [])
        
        # 면접관별 특화된 주제별 가이드라인 
        topic_guidelines = self._get_specialized_topic_guidelines(interviewer_role)
        
        # 3. 안전장치: 필수 DNA 정보 부족 시 기존 방식 사용
        critical_dna_missing = (
            talent_profile == '정의되지 않음' and 
            core_competencies == '정의되지 않음' and 
            tech_focus == '정의되지 않음' and 
            question_direction == '정의되지 않음'
        )
        
        if critical_dna_missing:
            # 기존 프롬프트 구조로 폴백
            guideline = topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')
            return f"""
당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

면접 직군: {position}
면접 주제: {topic}
질문 가이드라인: {guideline}

위 주제에 대해 두 지원자를 동시에 평가할 수 있는 메인 질문을 하나만 생성해주세요.

응답 형식:
{{"question": "질문 내용", "intent": "질문 의도"}}
"""
        
        # 4. 면접관별 전문화된 DNA 매트릭스 프롬프트 구성
        interviewer_persona = self.interviewer_personas.get(interviewer_role, "")
        specialized_prompt = self._build_specialized_dna_matrix_prompt(
            interviewer_role, company_name, talent_profile, core_competencies, 
            tech_focus, question_direction, core_values, work_style,
            position, position_context, topic, topic_guidelines, interviewer_persona
        )
        
        return specialized_prompt
    
    def _get_specialized_topic_guidelines(self, interviewer_role: str) -> Dict[str, str]:
        """면접관별 특화된 주제별 가이드라인"""
        
        if interviewer_role == 'HR':
            return {
                '가치관_신념체계': '지원자의 핵심 가치관이 회사 문화와 얼마나 부합하는지 평가',
                '성장_학습동기': '지속적 학습 의지와 장기 근무 가능성 평가',
                '갈등_해결경험': '대인관계 갈등 상황에서의 성숙한 대처 능력 평가',
                '스트레스_압박대처': '업무 압박과 스트레스 상황에서의 회복력과 적응력 평가',
                '팀워크_상호존중': '팀 내에서의 배려와 협조 정신, 상호 존중 태도 평가',
                '실패_극복과정': '실패와 좌절을 통한 성장과 교훈 습득 능력 평가',
                '의사소통_공감능력': '타인과의 원활한 소통과 공감 능력 평가',
                '변화_적응력': '조직 변화와 새로운 환경에 대한 적응 능력 평가',
                '윤리_도덕적판단': '업무상 윤리적 딜레마 상황에서의 올바른 판단 능력 평가',
                '장기_커리어비전': '개인의 성장 목표와 회사에서의 장기적 기여 의지 평가',
                '자기성찰_피드백수용': '자기 인식과 타인의 피드백을 수용하는 자세 평가',
                '책임감_주인의식': '업무에 대한 책임감과 주인의식, 헌신도 평가',
                '다양성_포용성': '다양한 배경의 동료들과 조화롭게 일하는 능력 평가',
                '목표설정_달성의지': '목표 설정과 달성을 위한 의지와 실행력 평가',
                '인간관계_신뢰구축': '동료들과 신뢰 관계를 구축하고 유지하는 능력 평가'
            }
        
        elif interviewer_role == 'TECH':
            return {
                '핵심기술_전문성': '회사에서 사용하는 핵심 기술 스택에 대한 실무 경험과 전문성 평가',
                '아키텍처_설계경험': '시스템 아키텍처 설계와 기술적 의사결정 경험 평가',
                '성능최적화_튜닝': '시스템 성능 문제 진단과 최적화 경험 평가',
                '코드품질_리팩토링': '코드 품질 관리와 리팩토링, 기술 부채 해결 경험 평가',
                '문제해결_디버깅': '복잡한 기술적 문제의 원인 분석과 해결 과정 평가',
                '신기술_학습적용': '새로운 기술 습득과 프로젝트 적용 능력 평가',
                '데이터베이스_설계': '데이터베이스 설계와 쿼리 최적화 경험 평가',
                '보안_취약점대응': '보안 취약점 식별과 대응, 보안 설계 경험 평가',
                '테스트_자동화': '테스트 코드 작성과 CI/CD 파이프라인 구축 경험 평가',
                '배포_운영경험': '서비스 배포와 운영, 모니터링 경험 평가',
                '모니터링_장애대응': '시스템 모니터링과 장애 상황 대응 경험 평가',
                '협업도구_프로세스': '개발 협업 도구와 프로세스 개선 경험 평가',
                '기술선택_의사결정': '기술 스택 선택과 아키텍처 결정의 근거와 결과 평가',
                '레거시_마이그레이션': '레거시 시스템 개선과 마이그레이션 경험 평가',
                '오픈소스_기여': '오픈소스 프로젝트 기여와 커뮤니티 활동 경험 평가'
            }
        
        elif interviewer_role == 'COLLABORATION':
            return {
                '팀내_소통방식': '팀원들과의 효과적인 의사소통 방식과 협업 스타일 평가',
                '갈등_중재해결': '팀 내 갈등 상황에서의 중재와 해결 능력 평가',
                '크로스팀_협업': '다른 부서나 팀과의 협업 경험과 조율 능력 평가',  
                '프로젝트_역할분담': '프로젝트에서의 역할 분담과 책임 수행 능력 평가',
                '의견조율_합의': '서로 다른 의견을 조율하여 합의점을 도출하는 능력 평가',
                '지식공유_멘토링': '지식 공유와 후배 멘토링, 팀 성장 기여도 평가',
                '회의_퍼실리테이션': '회의 진행과 의사결정 프로세스 개선 능력 평가',
                '피드백_주고받기': '건설적인 피드백을 주고받는 소통 능력 평가',
                '문화차이_극복': '다양한 문화적 배경의 팀원들과의 협업 경험 평가',
                '원격_협업경험': '원격 근무 환경에서의 협업 능력과 적응력 평가',
                '이해관계자_관리': '다양한 이해관계자들과의 소통과 관계 관리 능력 평가',
                '팀빌딩_관계형성': '팀 내 긍정적 분위기 조성과 관계 형성 능력 평가',
                '리더십_발휘': '상황에 따른 리더십 발휘와 팀 이끌기 경험 평가',
                '팔로워십_지원': '팀장이나 리더를 지원하는 팔로워십과 협력 자세 평가',
                '다양성_포용': '다양한 관점과 아이디어를 수용하고 활용하는 능력 평가'
            }
        
        else:
            # 기본 가이드라인 (폴백)
            return {
                '인성_가치관': '지원자의 핵심 가치관과 인생 철학을 파악할 수 있는 질문',
                '성장_동기': '학습 의지와 자기계발에 대한 태도를 확인하는 질문',
                '갈등_해결': '대인관계나 업무상 갈등 상황에서의 해결 능력을 평가하는 질문'
            }
    
    def _build_specialized_dna_matrix_prompt(self, interviewer_role: str, company_name: str, 
                                           talent_profile: str, core_competencies: str, 
                                           tech_focus: str, question_direction: str,
                                           core_values: List, work_style: str,
                                           position: str, position_context: str, 
                                           topic: str, topic_guidelines: Dict,
                                           interviewer_persona: str) -> str:
        """면접관별로 특화된 전사적 DNA 매트릭스 프롬프트 생성"""
        
        # 면접관별 특화된 관점과 접근 방식
        role_specific_guidance = {
            'HR': f"""
### 🎯 당신의 HR 전문가 관점 ###
{interviewer_persona}

### 핵심 평가 목표 ###
이 지원자가 {company_name}에서 {position}직무로 장기간 성공적으로 일할 수 있는 사람인지 종합적으로 평가하세요:
1. **문화적 적합성**: 회사 가치관과 개인 가치관의 일치도
2. **장기 근무 가능성**: 회사에서 지속적으로 성장하고 기여할 의지
3. **팀 조화**: 기존 팀원들과 원만한 관계를 형성할 수 있는 성격과 태도
4. **스트레스 내성**: 업무 압박 상황에서의 건전한 대처 능력""",
            
            'TECH': f"""
### 🎯 당신의 기술 전문가 관점 ###
{interviewer_persona}

### 핵심 평가 목표 ###
이 지원자가 {company_name}의 {position}직무로 기술 환경에서 실제로 성과를 낼 수 있는지 기술적 역량을 평가하세요:
1. **기술 스택 적합성**: 회사에서 사용하는 핵심 기술들의 실무 경험 수준
2. **문제 해결 능력**: 복잡한 기술적 문제를 체계적으로 분석하고 해결하는 능력  
3. **기술적 성장성**: 새로운 기술을 빠르게 학습하고 적용할 수 있는 능력
4. **실무 적용 경험**: 이론이 아닌 실제 프로젝트에서의 기술 활용 경험""",
            
            'COLLABORATION': f"""
### 🎯 당신의 협업 전문가 관점 ###
{interviewer_persona}

### 핵심 평가 목표 ###
이 지원자가 {company_name}의 {position}직무가 협업하는 여러 팀의 다양한 팀원들과 효과적으로 협업할 수 있는지 협업 역량을 평가하세요:
1. **소통 능력**: 복잡한 내용을 명확하게 전달하고 이해시키는 능력
2. **갈등 해결**: 의견 충돌이나 갈등 상황을 건설적으로 해결하는 능력
3. **팀 기여도**: 개인 성과뿐만 아니라 팀 전체의 성공을 위해 기여하는 자세
4. **협업 경험**: 다양한 역할과 부서의 사람들과 함께 일한 실제 경험"""
        }
        
        specific_guidance = role_specific_guidance.get(interviewer_role, "")
        
        prompt = f"""
{specific_guidance}

### [회사 DNA 분석] ###
- **인재상 (WHO):** 우리는 '{talent_profile}'인 사람을 원합니다.
- **핵심 역량 (WHAT):** 우리는 '{core_competencies}' 역량을 중요하게 생각합니다.
- **기술 중점 분야 (WHERE):** 우리의 기술은 '{tech_focus}' 분야에 집중되어 있습니다.
- **평가 방향 (HOW):** 우리는 '{question_direction}' 방식으로 지원자를 평가합니다.
{f"- **핵심가치:** {', '.join(core_values[:3])}" if core_values else ""}
{f"- **업무문화:** {work_style}" if work_style else ""}

### [지원자 컨텍스트] ###
- **직군:** {position}
- **주요 업무 영역:** {position_context}
- **면접 주제:** {topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')}

### [면접관별 특화된 질문 생성 전략] ###
**{interviewer_role} 면접관으로서, 위의 회사 DNA와 지원자 정보를 종합하여:**

1. **DNA 융합**: 회사의 인재상과 핵심 역량을 {interviewer_role} 관점에서 해석하고, {position} 직무에서 가장 중요한 요소를 정의하세요.

2. **{interviewer_role} 특화 상황**: 당신의 전문 영역({interviewer_role})에서 발생할 수 있는 구체적이고 현실적인 상황을 회사의 기술 중점 분야와 연결하여 설정하세요.

3. **차별화된 질문**: 다른 면접관(HR/TECH/COLLABORATION)과는 완전히 다른 관점에서, 당신만의 전문성을 활용한 날카로운 질문을 만드세요.

### [최종 출력] ###
다른 어떤 설명도 없이, 아래 JSON 형식에 맞춰서만 응답하세요.
{{
  "question": "생성된 최종 질문 내용",
  "intent": "이 질문을 통해 평가하려는 역량",
  "related_dna": ["평가와 관련된 회사 DNA 키워드"]
}}
"""
        return prompt
    
    def build_system_prompt_for_follow_up(self) -> str:
        """꼬리 질문 생성용 시스템 프롬프트"""
        return """당신은 경험 많은 전문 면접관입니다. 지원자들의 답변을 분석하여 핵심을 파고드는 날카로운 꼬리 질문을 생성합니다.

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "방금 말씀하신 성능 최적화 방법에서 가장 효과적이었던 부분은 무엇인가요?", "intent": "구체적인 기술적 성과와 판단 근거 확인"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""
    def build_system_prompt_for_follow_up(self) -> str:
                """고도화된 꼬리 질문 생성용 시스템 프롬프트 - 직무별 전문성 반영"""
                return """당신은 각 직무별 전문성을 깊이 이해하는 경험 많은 면접관입니다. 
        지원자들의 답변을 정밀 분석하여 직무 전문가만이 답할 수 있는 날카로운 꼬리 질문을 생성합니다.

        🎯 **핵심 원칙** 🎯
        - 각 직무(프론트엔드/백엔드/기획/AI/데이터)의 고유한 전문성 반영
        - 답변 품질을 분석하여 적절한 깊이의 질문 생성
        - 실무에서 정말 중요한 판단력과 경험을 검증하는 질문
        - 부적절한 타 직무 질문 철저히 배제

        🚨 **절대 준수 사항** 🚨  
        - 오직 아래 JSON 형식으로만 응답하세요
        - 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
        - JSON 앞뒤에 ```json이나 기타 텍스트 금지

        **필수 응답 형식:**
        {"question": "질문 내용", "intent": "질문 의도"}

        **직무별 전문성 예시:**
        프론트엔드: {"question": "말씀하신 렌더링 최적화에서 Virtual DOM 업데이트 과정 중 가장 성능 개선 효과가 컸던 부분은?", "intent": "프론트엔드 성능 최적화 전문성 검증"}
        백엔드: {"question": "대용량 트래픽 상황에서 DB 커넥션 풀 관리는 어떤 전략으로 하셨나요?", "intent": "백엔드 확장성 설계 경험 검증"}

        위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""
            
    def build_follow_up_question_prompt(self, previous_question: str, user_answer: str, 
                                        chun_sik_answer: str, company_info: Dict, 
                                        interviewer_role: str, position: str) -> str:
            """고도화된 동적 꼬리 질문 생성 - 직무별 전문성 반영"""
            
            company_name = company_info.get('name', '회사')
            
            # 1. 직무별 전문성 컨텍스트 동적 생성
            position_context = self._build_position_context(position, interviewer_role)
            
            # 2. 답변 분석 및 질문 전략 결정
            answer_analysis = self._analyze_answers_for_follow_up(user_answer, chun_sik_answer, position)
            
            # 3. 직무별 금지 키워드 및 권장 방향 설정
            guidelines = self._get_position_specific_guidelines(position, interviewer_role)
            
            # 4. 통합 프롬프트 생성
            prompt = f"""
    당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

    {position_context}

    ### 📊 이전 질문과 답변 분석 ###
    이전 질문: {previous_question}
    사용자 답변: {user_answer}
    춘식이 답변: {chun_sik_answer}

    {answer_analysis}

    ### 🎯 {position} 특화 꼬리질문 생성 전략 ###
    {guidelines}

    ### 📝 질문 생성 가이드라인 ###
    - **직무 전문성**: {position} 관점에서만 질문 (다른 직무 영역 금지)
    - **답변 연결**: 위 답변의 구체적 내용을 반드시 인용
    - **전문가 관점**: {interviewer_role} 면접관다운 날카로운 시각
    - **실무 중심**: 실제 업무에서 중요한 판단력 평가

    응답 형식:
    {{"question": "질문 내용", "intent": "질문 의도"}}
    """
            return prompt.strip()
        
    def _build_position_context(self, position: str, interviewer_role: str) -> str:
            """직무별 전문성 컨텍스트 동적 생성"""
            
            # 직무명 정규화 (다양한 표기법 대응)
            position_normalized = self._normalize_position_name(position)
            
            position_map = {
                "프론트엔드": {
                    "core_focus": "사용자 경험, 웹 성능, UI/UX 최적화, 접근성, 반응형 디자인",
                    "tech_keywords": "React, Vue, JavaScript, TypeScript, CSS, 웹팩, 번들링, 렌더링",  
                    "business_impact": "사용자 만족도, 전환율, 페이지 로딩 속도, 이탈률 감소",
                    "daily_challenges": "크로스 브라우징, 성능 최적화, 상태 관리, 컴포넌트 설계"
                },
                "백엔드": {
                    "core_focus": "시스템 안정성, 확장성, API 설계, 데이터 처리, 보안",
                    "tech_keywords": "Spring, Node.js, 데이터베이스, 아키텍처, 분산처리, 캐싱",
                    "business_impact": "서비스 안정성, 처리 용량, 응답 시간, 동시 접속자 처리",
                    "daily_challenges": "대용량 트래픽, 데이터베이스 최적화, 장애 대응, 모니터링"
                },
                "기획": {
                    "core_focus": "사용자 니즈 파악, 비즈니스 가치 창출, 우선순위 결정, 이해관계자 관리",
                    "tech_keywords": "데이터 분석, A/B테스트, 사용자 리서치, KPI, 로드맵, 와이어프레임",
                    "business_impact": "제품 목표 달성, ROI 향상, 사용자 만족도, 매출 기여",
                    "daily_challenges": "요구사항 분석, 우선순위 조율, 일정 관리, 의사소통"
                },
                "AI": {
                    "core_focus": "모델 성능 향상, 데이터 품질 관리, 알고리즘 최적화, 윤리적 AI 개발",
                    "tech_keywords": "머신러닝, 딥러닝, 데이터 전처리, 모델 평가, MLOps, 피처 엔지니어링",
                    "business_impact": "예측 정확도 향상, 업무 자동화, 비용 절감, 의사결정 지원",
                    "daily_challenges": "모델 성능 개선, 편향성 제거, 데이터 수집, 모델 배포"
                },
                "데이터사이언스": {
                    "core_focus": "데이터 인사이트 발굴, 통계적 검증, 비즈니스 문제 해결, 의사결정 지원",
                    "tech_keywords": "통계 분석, 데이터 시각화, SQL, Python, R, 파이프라인, 지표 설계",
                    "business_impact": "데이터 기반 의사결정, 매출 기여도 분석, ROI 측정, 트렌드 예측",
                    "daily_challenges": "데이터 품질 관리, 인사이트 도출, 가설 검증, 리포팅"
                }
            }
            
            context = position_map.get(position_normalized, position_map["백엔드"])  # fallback
            
            return f"""
    ### 🎯 {position} 전문 면접관으로서 당신의 관점 ###
    - **핵심 관심사**: {context['core_focus']}
    - **기술적 키워드**: {context['tech_keywords']}  
    - **비즈니스 임팩트**: {context['business_impact']}
    - **일상적 도전과제**: {context['daily_challenges']}
    - **면접관 역할**: {interviewer_role} 관점에서 {position} 전문성과 실무 역량 평가
    """

    def _analyze_answers_for_follow_up(self, user_answer: str, ai_answer: str, position: str) -> str:
            """답변 분석 및 질문 전략 결정"""
            
            # 답변 길이 및 구체성 분석
            user_length = len(user_answer.strip())
            ai_length = len(ai_answer.strip())
            
            # 직무별 핵심 키워드 추출
            position_keywords = self._get_position_keywords(position)
            user_keywords = [kw for kw in position_keywords if kw.lower() in user_answer.lower()]
            ai_keywords = [kw for kw in position_keywords if kw.lower() in ai_answer.lower()]
            
            # 분석 결과 기반 전략 결정
            analysis_parts = []
            
            # 답변 품질 격차 분석
            if abs(user_length - ai_length) > 200:
                longer_answer = "사용자" if user_length > ai_length else "AI"
                analysis_parts.append(f"📏 **답변 길이 차이**: {longer_answer} 답변이 더 상세함")
            
            # 전문 키워드 사용 분석
            if len(user_keywords) > len(ai_keywords):
                analysis_parts.append(f"🔑 **기술적 키워드**: 사용자 답변에서 더 많은 {position} 전문 용어 사용")
            elif len(ai_keywords) > len(user_keywords):
                analysis_parts.append(f"🔑 **기술적 키워드**: AI 답변에서 더 많은 {position} 전문 용어 사용")
            
            # 구체적 수치나 사례 언급 분석
            has_numbers_user = any(char.isdigit() for char in user_answer)
            has_numbers_ai = any(char.isdigit() for char in ai_answer)
            
            if has_numbers_user and not has_numbers_ai:
                analysis_parts.append("📊 **구체성**: 사용자 답변에 구체적 수치/데이터 포함")
            elif has_numbers_ai and not has_numbers_user:
                analysis_parts.append("📊 **구체성**: AI 답변에 구체적 수치/데이터 포함")
            
            # 전략 제안
            strategy_parts = []
            
            if user_length < 100:
                strategy_parts.append("🎯 **전략**: 사용자 답변이 간략함 → 구체적 경험 탐구 필요")
            elif user_length > 300:
                strategy_parts.append("🎯 **전략**: 사용자 답변이 상세함 → 핵심 포인트 심화 탐구")
            
            if len(user_keywords) < 2:
                strategy_parts.append(f"🎯 **전략**: {position} 전문성 확인 필요 → 기술적 깊이 검증")
            
            return "\n".join(analysis_parts + strategy_parts) if analysis_parts or strategy_parts else f"📋 **분석**: 두 답변 모두 {position} 관점에서 균형있게 구성됨"

    def _get_position_specific_guidelines(self, position: str, interviewer_role: str) -> str:
            """직무별 특화 가이드라인"""
            
            position_normalized = self._normalize_position_name(position)
            
            forbidden_areas = {
                "프론트엔드": "백엔드 서버 구조, 데이터베이스 설계, 인프라 운영, 서버 배포",
                "백엔드": "프론트엔드 UI/UX, React/Vue 구현 세부사항, CSS 디자인, 사용자 인터페이스",
                "기획": "코딩 구현 세부사항, 알고리즘 복잡도, 데이터베이스 쿼리 최적화, 서버 아키텍처",
                "AI": "웹 개발, 서버 운영, 일반적인 백엔드/프론트엔드 개발, UI/UX 디자인",
                "데이터사이언스": "UI 개발, 서버 아키텍처 설계, 프론트엔드 프레임워크, 백엔드 API 구현"
            }
            
            recommended_areas = {
                "프론트엔드": "사용자 경험 개선, 웹 성능 최적화, 접근성, 브라우저 호환성, 반응형 디자인",
                "백엔드": "시스템 확장성, API 설계, 데이터 처리 최적화, 보안, 장애 대응",
                "기획": "사용자 니즈 분석, 비즈니스 가치 창출, 우선순위 결정, 이해관계자 조율",
                "AI": "모델 성능 개선, 데이터 품질 관리, 편향성 제거, 모델 해석, 윤리적 고려",
                "데이터사이언스": "데이터 인사이트 발굴, 통계적 검증, 비즈니스 문제 해결, A/B 테스트"
            }
            
            interviewer_focus = {
                "HR": f"{position} 개발자로서의 가치관, 팀워크, 성장 마인드, 문제 해결 태도",
                "TECH": f"{position} 기술 전문성, 실무 경험 깊이, 문제 해결 능력, 기술적 판단력",
                "COLLABORATION": f"{position} 업무에서의 협업 경험, 소통 방식, 갈등 해결, 팀 기여도"
            }
            
            return f"""
    **✅ {position} 관점에서 탐구해야 할 핵심 영역**
    - {recommended_areas.get(position_normalized, "전문 업무 역량")}
    - {interviewer_focus.get(interviewer_role, "전문성 평가")}

    **❌ 절대 금지 영역**  
    - {forbidden_areas.get(position_normalized, "관련 없는 기술 분야")}
    - {position}와 직접적 관련이 없는 타 직무의 전문 기술

    **🎯 질문 방향성**
    - 실제 {position} 업무에서 마주하는 현실적 문제 상황
    - {position} 전문가만이 답할 수 있는 깊이 있는 내용
    - {interviewer_role} 면접관 관점에서의 날카로운 검증 포인트
    """

    def _normalize_position_name(self, position: str) -> str:
            """다양한 직무명 표기를 표준화"""
            
            position_lower = position.lower().replace(" ", "").replace("-", "")
            
            if any(keyword in position_lower for keyword in ["프론트", "frontend", "fe", "front"]):
                return "프론트엔드"
            elif any(keyword in position_lower for keyword in ["백엔드", "backend", "be", "back"]):
                return "백엔드"
            elif any(keyword in position_lower for keyword in ["기획", "pm", "product", "planning"]):
                return "기획"
            elif any(keyword in position_lower for keyword in ["ai", "머신러닝", "ml", "딥러닝", "인공지능"]):
                return "AI"
            elif any(keyword in position_lower for keyword in ["데이터", "data", "ds", "분석"]):
                return "데이터사이언스"
            else:
                return position  # 원본 반환

    def _get_position_keywords(self, position: str) -> List[str]:
            """직무별 핵심 키워드 리스트"""
            
            position_normalized = self._normalize_position_name(position)
            
            keywords_map = {
                "프론트엔드": ["React", "Vue", "JavaScript", "TypeScript", "CSS", "HTML", "웹팩", "번들", "렌더링", "DOM", "성능", "최적화", "사용자", "UI", "UX", "반응형", "브라우저"],
                "백엔드": ["API", "서버", "데이터베이스", "MySQL", "PostgreSQL", "Spring", "Node.js", "아키텍처", "확장성", "분산", "캐시", "보안", "인증", "성능", "최적화"],
                "기획": ["사용자", "요구사항", "기획", "분석", "KPI", "지표", "A/B테스트", "우선순위", "로드맵", "이해관계자", "비즈니스", "ROI", "데이터"],
                "AI": ["모델", "학습", "데이터", "알고리즘", "정확도", "예측", "분류", "회귀", "딥러닝", "머신러닝", "신경망", "편향", "과적합", "검증"],
                "데이터사이언스": ["데이터", "분석", "통계", "시각화", "SQL", "Python", "R", "인사이트", "패턴", "트렌드", "지표", "대시보드", "리포트", "가설"]
            }
            
            return keywords_map.get(position_normalized, [])

    def build_db_template_enhancement_prompt(self, db_template: str, user_resume: Dict, 
                                           company_info: Dict, interviewer_role: str) -> str:
        """DB 참조질문을 LLM으로 튜닝/개선하기 위한 고도화된 프롬프트"""
        
        company_name = company_info.get('name', '회사')
        talent_profile = company_info.get('talent_profile', '정의되지 않음')
        core_competencies = ', '.join(company_info.get('core_competencies', ['정의되지 않음']))
        tech_focus = ', '.join(company_info.get('tech_focus', ['정의되지 않음']))
        question_direction = company_info.get('question_direction', '정의되지 않음')
        
        # 기업문화 정보 추출
        company_culture = company_info.get('company_culture', {})
        core_values = []
        work_style = ''
        if isinstance(company_culture, dict):
            core_values = company_culture.get('core_values', [])
            work_style = company_culture.get('work_style', '')
        
        # 지원자 정보
        position = user_resume.get('position', '개발자')
        candidate_name = user_resume.get('name', '지원자')
        
        # 면접관별 페르소나 및 관점
        interviewer_persona = self.interviewer_personas.get(interviewer_role, "")
        
        prompt = f"""
{interviewer_persona}

### [회사 DNA 분석] ###
- **인재상 (WHO):** 우리는 '{talent_profile}'인 사람을 원합니다.
- **핵심 역량 (WHAT):** 우리는 '{core_competencies}' 역량을 중요하게 생각합니다.
- **기술 중점 분야 (WHERE):** 우리의 기술은 '{tech_focus}' 분야에 집중되어 있습니다.
- **평가 방향 (HOW):** 우리는 '{question_direction}' 방식으로 지원자를 평가합니다.
{f"- **핵심가치:** {', '.join(core_values[:3])}" if core_values else ""}
{f"- **업무문화:** {work_style}" if work_style else ""}

### [지원자 컨텍스트] ###
- **지원자명:** {candidate_name}
- **지원 직군:** {position}

### [원본 DB 참조질문] ###
{db_template}

### [질문 개선 임무] ###
당신은 {interviewer_role} 면접관으로서, 위의 DB 참조질문을 다음과 같이 개선해야 합니다:

1. **회사 DNA 융합**: 회사의 인재상, 핵심 역량, 기술 중점 분야를 반영하여 질문을 개선
2. **개인화**: 지원자의 이름과 직군에 맞게 질문을 자연스럽게 조정
3. **면접관 관점**: {interviewer_role} 면접관만의 전문성과 관점을 반영
4. **자연스러운 표현**: 딱딱한 DB 템플릿을 대화하듯 자연스러운 면접 질문으로 개선
5. **원본 의도 유지**: 원본 질문의 평가 목적과 핵심 의도는 반드시 보존

### [개선 원칙] ###
- 질문의 핵심 평가 요소는 그대로 유지
- 회사와 지원자에 맞는 구체적인 상황으로 맥락화
- {interviewer_role} 면접관다운 전문적이고 날카로운 시각 반영
- 면접 상황에서 자연스럽게 물어볼 수 있는 형태로 개선

### [절대 준수사항] ###
🚨 오직 아래 JSON 형식으로만 응답하세요. 다른 텍스트, 설명, 주석 절대 금지 🚨

{{"question": "개선된 질문 내용", "intent": "질문을 통해 평가하려는 역량"}}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다.
"""
        return prompt.strip()
