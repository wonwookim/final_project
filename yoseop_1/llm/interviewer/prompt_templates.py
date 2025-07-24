#!/usr/bin/env python3
"""
면접 질문 생성을 위한 프롬프트 템플릿 모음
중앙화된 프롬프트 관리로 일관성 확보
"""

from typing import Dict, Any
from ..shared.constants import GPT_MODEL


class InterviewPromptTemplates:
    """면접 질문 생성 프롬프트 템플릿 클래스"""
    
    @staticmethod
    def get_system_prompt(company_name: str) -> str:
        """시스템 프롬프트 반환"""
        return f"""당신은 {company_name}의 경험 많은 면접관입니다. 
실무진 면접관의 관점에서 실제 면접에서 사용할 수 있는 고품질 질문을 생성해주세요.

핵심 원칙:
- 질문은 구체적이고 실무 중심이어야 합니다
- 지원자의 경력 수준에 맞는 적절한 난이도로 조정해주세요
- 기업의 핵심 가치와 기술 스택을 반영해주세요
- 실제 면접 상황에서 바로 사용할 수 있는 수준으로 작성해주세요
- 한국어로 자연스럽게 작성해주세요"""
    
    @staticmethod
    def get_basic_interview_prompt(company_data: dict, position: str, 
                                 experience_years: int, num_questions: int) -> str:
        """기본 면접 질문 생성 프롬프트"""
        interviewer = company_data["interviewer_persona"]
        
        return f"""
당신은 {company_data['name']}의 {interviewer['name']}입니다.
- 역할: {interviewer['role']}
- 경험: {interviewer['experience']}
- 성격: {interviewer['personality']}
- 말하는 스타일: {interviewer['speaking_style']}

현재 {position} {experience_years}년차 개발자를 면접하고 있습니다.

=== 기업 정보 ===
- 인재상: {company_data['talent_profile']}
- 핵심 역량: {', '.join(company_data['core_competencies'])}
- 기술 중점 분야: {', '.join(company_data['tech_focus'])}
- 면접 키워드: {', '.join(company_data['interview_keywords'])}
- 평가 방향: {company_data['question_direction']}

=== 질문 생성 요구사항 ===
다음 4가지 카테고리별로 각각 질문을 생성해주세요:

1. **기술 역량 평가 질문** (2문제)
   - {experience_years}년차에 적합한 기술적 깊이
   - 실제 업무 상황 기반 시나리오
   - {company_data['name']}의 기술 스택과 연관성

2. **문화 적합성 질문** (1문제)
   - {company_data['name']}의 핵심 가치와 연결
   - 실제 협업 경험 확인

3. **문제 해결 능력 질문** (1문제)
   - 실무에서 발생할 수 있는 상황
   - 사고 과정과 해결 접근법 확인

4. **성장 의지 및 동기 질문** (1문제)
   - {company_data['name']}에 대한 이해도
   - 장기적 커리어 계획

=== 출력 형식 ===
각 질문은 다음 형식으로 작성해주세요:
**[카테고리] 질문 번호**
질문 내용

면접관의 의도: (이 질문으로 무엇을 평가하고자 하는지)
기대하는 답변 방향: (좋은 답변의 핵심 포인트 2-3개)

---

총 {num_questions}개의 질문을 생성해주세요.
"""
    
    @staticmethod
    def get_technical_deep_dive_prompt(company_data: dict, position: str, 
                                     experience_years: int, tech_area: str) -> str:
        """기술 심화 질문 생성 프롬프트"""
        interviewer = company_data["interviewer_persona"]
        
        return f"""
당신은 {company_data['name']}의 {interviewer['name']}입니다.
{experience_years}년차 {position} 지원자와 {tech_area} 기술에 대한 심화 면접을 진행합니다.

=== 기술 심화 면접 요구사항 ===
{tech_area} 분야에서 다음 난이도별로 질문을 생성해주세요:

1. **기초 개념 확인** (1문제)
   - 기본적인 이해도 확인
   - 실무 적용 경험 확인

2. **설계 및 아키텍처** (2문제)
   - 시스템 설계 능력
   - 트레이드오프 이해

3. **실무 경험 기반** (1문제)
   - 실제 문제 해결 경험
   - 성능 최적화 경험

4. **미래 기술 트렌드** (1문제)
   - 기술 발전 방향 이해
   - 학습 의지 확인

각 질문은 {company_data['name']}의 실제 업무 환경과 연관지어 작성해주세요.
"""
    
    @staticmethod
    def get_cultural_fit_prompt(company_data: dict, position: str, experience_years: int) -> str:
        """문화 적합성 중심 질문 생성 프롬프트"""
        interviewer = company_data["interviewer_persona"]
        
        return f"""
당신은 {company_data['name']}의 {interviewer['name']}입니다.
{experience_years}년차 {position} 지원자의 문화 적합성을 평가하는 면접을 진행합니다.

=== 문화 적합성 평가 요구사항 ===
{company_data['name']}의 핵심 가치를 중심으로 질문을 생성해주세요:

핵심 가치: {', '.join(company_data['core_competencies'])}
인재상: {company_data['talent_profile']}

1. **가치 일치도 확인** (2문제)
   - 기업 가치에 대한 이해
   - 개인 가치와의 일치성

2. **협업 및 소통** (2문제)
   - 팀워크 경험
   - 갈등 해결 능력

3. **성장 마인드셋** (1문제)
   - 학습 의지
   - 도전 정신

실제 업무 상황을 가정한 시나리오 기반으로 질문을 작성해주세요.
"""
    
    @staticmethod
    def get_problem_solving_prompt(company_data: dict, position: str, 
                                 experience_years: int, domain: str) -> str:
        """문제 해결 능력 중심 질문 생성 프롬프트"""
        interviewer = company_data["interviewer_persona"]
        
        return f"""
당신은 {company_data['name']}의 {interviewer['name']}입니다.
{experience_years}년차 {position} 지원자의 문제 해결 능력을 평가합니다.

=== 문제 해결 능력 평가 요구사항 ===
{domain} 도메인에서 발생할 수 있는 실제 문제 상황을 기반으로 질문을 생성해주세요.

1. **문제 분석 능력** (1문제)
   - 복잡한 문제의 원인 파악
   - 체계적 접근 방법

2. **해결 방안 도출** (2문제)
   - 창의적 해결책 제시
   - 여러 대안 비교 분석

3. **실행 및 검증** (1문제)
   - 솔루션 구현 과정
   - 결과 측정 및 개선

4. **학습 및 적용** (1문제)
   - 문제 해결 과정에서의 학습
   - 유사 문제 예방책

각 질문은 {company_data['name']}의 실제 비즈니스 상황과 연관지어 작성해주세요.
"""
    
    @staticmethod
    def get_scenario_based_prompt(company_data: dict, position: str, 
                                experience_years: int, scenario_type: str) -> str:
        """시나리오 기반 질문 생성 프롬프트"""
        interviewer = company_data["interviewer_persona"]
        
        scenarios = {
            "긴급상황": "서비스 장애나 긴급한 버그 수정이 필요한 상황",
            "성능최적화": "시스템 성능 문제 해결이 필요한 상황", 
            "팀협업": "다른 팀과의 협업이나 의견 충돌 상황",
            "기술선택": "새로운 기술 도입이나 기술 스택 변경 상황",
            "사용자피드백": "사용자 불만이나 요구사항 변경 상황"
        }
        
        scenario_desc = scenarios.get(scenario_type, "일반적인 업무 상황")
        
        return f"""
당신은 {company_data['name']}의 {interviewer['name']}입니다.
{experience_years}년차 {position} 지원자에게 {scenario_desc}에 대한 시나리오 기반 질문을 합니다.

=== 시나리오 기반 질문 요구사항 ===
다음 상황을 가정하여 질문을 생성해주세요:

상황 설정: {scenario_desc}
기업 컨텍스트: {company_data['name']}의 {', '.join(company_data['tech_focus'])} 분야

1. **상황 인식** (1문제)
   - 문제 상황 파악 능력
   - 우선순위 판단

2. **대응 방안** (2문제)
   - 즉각적 대응 방법
   - 장기적 해결 전략

3. **의사소통** (1문제)
   - 이해관계자 소통 방법
   - 상황 공유 및 보고

4. **결과 검토** (1문제)
   - 해결 과정 회고
   - 개선 방안 도출

실제 {company_data['name']}에서 발생할 수 있는 구체적인 상황으로 설정해주세요.
"""

# 프롬프트 템플릿 사용 예시
class PromptManager:
    """프롬프트 관리자 클래스"""
    
    def __init__(self):
        self.templates = InterviewPromptTemplates()
    
    def get_prompt(self, prompt_type: str, company_data: dict, **kwargs) -> str:
        """프롬프트 타입에 따라 적절한 프롬프트 반환"""
        
        if prompt_type == "basic":
            return self.templates.get_basic_interview_prompt(
                company_data, 
                kwargs.get('position', '백엔드 개발자'),
                kwargs.get('experience_years', 3),
                kwargs.get('num_questions', 5)
            )
        elif prompt_type == "technical":
            return self.templates.get_technical_deep_dive_prompt(
                company_data,
                kwargs.get('position', '백엔드 개발자'),
                kwargs.get('experience_years', 3),
                kwargs.get('tech_area', '백엔드 시스템')
            )
        elif prompt_type == "cultural":
            return self.templates.get_cultural_fit_prompt(
                company_data,
                kwargs.get('position', '백엔드 개발자'),
                kwargs.get('experience_years', 3)
            )
        elif prompt_type == "problem_solving":
            return self.templates.get_problem_solving_prompt(
                company_data,
                kwargs.get('position', '백엔드 개발자'),
                kwargs.get('experience_years', 3),
                kwargs.get('domain', '웹 서비스')
            )
        elif prompt_type == "scenario":
            return self.templates.get_scenario_based_prompt(
                company_data,
                kwargs.get('position', '백엔드 개발자'),
                kwargs.get('experience_years', 3),
                kwargs.get('scenario_type', '긴급상황')
            )
        else:
            raise ValueError(f"지원하지 않는 프롬프트 타입: {prompt_type}")
    
    def list_prompt_types(self) -> list:
        """사용 가능한 프롬프트 타입 목록 반환"""
        return ["basic", "technical", "cultural", "problem_solving", "scenario"]
    
    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return self.templates.get_system_prompt()

# 사용 예시
if __name__ == "__main__":
    import json
    
    # 기업 데이터 로드 (예시)
    with open("companies_data.json", "r", encoding="utf-8") as f:
        companies_data = json.load(f)
    
    naver_data = companies_data["companies"][0]  # 네이버 데이터
    
    # 프롬프트 매니저 생성
    prompt_manager = PromptManager()
    
    # 기본 면접 질문 프롬프트
    basic_prompt = prompt_manager.get_prompt(
        "basic", 
        naver_data, 
        position="백엔드 개발자",
        experience_years=5,
        num_questions=5
    )
    
    print("=== 기본 면접 질문 프롬프트 ===")
    print(basic_prompt)
    print()
    
    # 기술 심화 프롬프트
    technical_prompt = prompt_manager.get_prompt(
        "technical", 
        naver_data, 
        position="백엔드 개발자",
        experience_years=5,
        tech_area="검색 엔진"
    )
    
    print("=== 기술 심화 면접 프롬프트 ===")
    print(technical_prompt)
    print()
    
    # 사용 가능한 프롬프트 타입 확인
    print("사용 가능한 프롬프트 타입:", prompt_manager.list_prompt_types())