#!/usr/bin/env python3
"""
AI 지원자 모델 - LLM 기반 실시간 페르소나 생성
실제 이력서 데이터를 기반으로 LLM이 인간미 넘치는 페르소나를 실시간 생성
"""

import os
import json
import sys
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel

# .env 파일에서 환경변수 로드
load_dotenv()

# 상위 디렉토리의 database 모듈 접근을 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from database.supabase_client import get_supabase_client
except ImportError:
    print("⚠️ Supabase 클라이언트를 가져올 수 없습니다. 파일 기반 fallback만 사용됩니다.")
    get_supabase_client = None

from ..core.llm_manager import LLMManager, LLMProvider, LLMResponse
from .quality_controller import AnswerQualityController, QualityLevel
from ..shared.models import QuestionType, QuestionAnswer, AnswerRequest, AnswerResponse
from ..session.models import InterviewSession
from ..shared.utils import safe_json_load, get_fixed_questions

# 직군 매핑 (position_name -> position_id)
POSITION_MAPPING = {
    "프론트엔드": 1,
    "프론트": 1,
    "frontend": 1,
    "백엔드": 2,
    "백엔드개발자": 2,
    "backend": 2,
    "기획": 3,
    "기획자": 3,
    "pm": 3,
    "product manager": 3,
    "AI": 4,
    "ai": 4,
    "인공지능": 4,
    "머신러닝": 4,
    "ml": 4,
    "데이터사이언스": 5,
    "데이터": 5,
    "data science": 5,
    "data scientist": 5,
    "ds": 5
}

# 새로운 CandidatePersona 모델 (LLM 생성용)
class CandidatePersona(BaseModel):
    """LLM이 생성하는 인간미 넘치는 페르소나 모델"""
    # --- LLM 생성 정보 ---
    name: str
    summary: str  # 예: "5년차 Java 백엔드 개발자로, 대용량 트래픽 처리와 MSA 설계에 강점이 있습니다."
    background: Dict[str, Any]
    technical_skills: List[str]
    projects: List[Dict[str, Any]]  # 각 프로젝트에 'achievements'와 'challenges' 포함
    experiences: List[Dict[str, Any]]
    strengths: List[str]
    weaknesses: List[str]  # 개선하고 싶은 점
    motivation: str  # 개발자/기술에 대한 개인적 동기나 스토리
    inferred_personal_experiences: List[Dict[str, str]]  # 이력서 기반으로 추론된 개인적 교훈
    career_goal: str
    personality_traits: List[str]
    interview_style: str
    
    # --- 메타데이터 ---
    generated_by: str = "gpt-4o-mini"
    resume_id: int  # 원본 이력서 ID

# 모델별 AI 지원자 이름 매핑 (호환성을 위해 유지)
AI_CANDIDATE_NAMES = {
    LLMProvider.OPENAI_GPT4: "춘식이",
    LLMProvider.OPENAI_GPT35: "춘식이", 
    LLMProvider.OPENAI_GPT4O_MINI: "춘식이",
    LLMProvider.GOOGLE_GEMINI_PRO: "제미니",
    LLMProvider.GOOGLE_GEMINI_FLASH: "제미니",
    LLMProvider.KT_BELIEF: "믿음이"
}

class AICandidateSession(InterviewSession):
    """AI 지원자 전용 면접 세션 - 면접자와 동일한 플로우"""
    
    def __init__(self, company_id: str, position: str, persona: CandidatePersona):
        super().__init__(company_id, position, persona.name)
        self.persona = persona
        self.ai_answers: List[QuestionAnswer] = []
        
        # 면접자와 동일한 20개 질문 계획 사용
        # 이미 부모 클래스에서 self.question_plan이 20개로 설정됨
        
    def add_ai_answer(self, qa_pair: QuestionAnswer):
        """AI 답변 추가"""
        self.ai_answers.append(qa_pair)
        # 부모 클래스의 add_qa_pair 메서드를 사용하여 일관성 유지
        super().add_qa_pair(qa_pair)
    
    @property
    def question_answers(self) -> List[QuestionAnswer]:
        """FeedbackService 호환성을 위한 question_answers property - conversation_history 반환"""
        return super().question_answers
        
    def get_persona_context(self) -> str:
        """페르소나 컨텍스트 구성"""
        context = f"""
=== AI 지원자 페르소나 정보 ===
이름: {self.persona.name}
경력: {self.persona.background.get('career_years', '0')}년
현재 직책: {self.persona.background.get('current_position', '지원자')}
주요 기술: {', '.join(self.persona.technical_skills[:5])}
강점: {', '.join(self.persona.strengths[:3])}
커리어 목표: {self.persona.career_goal}
성격 특성: {', '.join(self.persona.personality_traits)}
면접 스타일: {self.persona.interview_style}

=== 주요 프로젝트 ===
"""
        for i, project in enumerate(self.persona.projects[:2], 1):
            context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
            context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            if project.get('achievements'):
                context += f"   성과: {', '.join(project['achievements'])}\n"
        
        context += f"""
=== 업무 경험 ===
"""
        for exp in self.persona.experiences[:2]:
            context += f"- {exp.get('company', '회사')}: {exp.get('position', '개발자')} ({exp.get('period', '기간')})\n"
            if exp.get('achievements'):
                context += f"  성과: {', '.join(exp['achievements'])}\n"
        
        return context
    
    def get_previous_answers_context(self) -> str:
        """이전 답변 컨텍스트 (일관성 유지용)"""
        if not self.ai_answers:
            return ""
        
        context = "\n=== 이전 답변 내역 (일관성 유지) ===\n"
        for i, qa in enumerate(self.ai_answers[-3:], 1):  # 최근 3개만
            context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
            context += f"   답변: {qa.answer_content[:100]}...\n\n"
        
        return context

class AICandidateModel:
    """AI 지원자 모델 메인 클래스"""
    
    def __init__(self, api_key: str = None):
        self.llm_manager = LLMManager()
        self.quality_controller = AnswerQualityController()
        self.companies_data = self._load_companies_data()
        
        # AI 지원자 세션 관리
        self.ai_sessions: Dict[str, 'AICandidateSession'] = {}
        self.fixed_questions = self._load_fixed_questions()
        
        # 새로운 LLM 기반 시스템에서는 페르소나를 동적으로 생성하므로 빈 딕셔너리로 초기화
        self.candidate_personas: Dict[str, CandidatePersona] = {}
        self.personas_data = {"personas": {}}
        
        # API 키 자동 로드 (.env 파일에서)
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        # 기본 OpenAI 모델 등록
        if api_key:
            self.llm_manager.register_model(LLMProvider.OPENAI_GPT4O_MINI, api_key=api_key)
            self.llm_manager.register_model(LLMProvider.OPENAI_GPT4, api_key=api_key)
            self.llm_manager.register_model(LLMProvider.OPENAI_GPT35, api_key=api_key)
        else:
            print("⚠️ OpenAI API 키가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가하거나 직접 전달하세요.")
    
    def create_persona_for_interview(self, company_name: str, position_name: str) -> Optional[CandidatePersona]:
        """
        주어진 회사와 직군에 맞는 AI 지원자 페르소나를 LLM으로 실시간 생성
        
        Args:
            company_name: 회사명 (예: "네이버", "카카오")
            position_name: 직군명 (예: "백엔드", "프론트엔드")
            
        Returns:
            생성된 CandidatePersona 객체 또는 None (실패 시)
        """
        try:
            print(f"🎯 {company_name} {position_name} 직군 페르소나 생성 시작...")
            
            # 1단계: 직군 ID 매핑
            position_id = self._get_position_id(position_name)
            if not position_id:
                print(f"❌ 지원하지 않는 직군: {position_name}")
                return None
            
            print(f"📊 직군 매핑: {position_name} -> {position_id}")
            
            # 2단계: 데이터베이스에서 이력서 조회
            resume_data = self._get_random_resume_from_db(position_id)
            if not resume_data:
                print(f"❌ position_id {position_id}에 해당하는 이력서가 없습니다")
                return None
            
            print(f"📋 이력서 로드 성공: ID {resume_data.get('ai_resume_id', 'unknown')}")
            
            # 3단계: 회사 정보 가져오기
            company_info = self._get_company_info(company_name)
            
            # 4단계: LLM 프롬프트 생성
            prompt = self._build_persona_generation_prompt(resume_data, company_name, position_name, company_info)
            
            # 5단계: LLM 호출로 페르소나 생성 (max_tokens 늘림)
            print(f"🤖 LLM으로 페르소나 생성 중...")
            llm_response = self._generate_persona_with_extended_tokens(
                prompt,
                self._build_system_prompt_for_persona_generation()
            )
            
            if llm_response.error:
                print(f"❌ LLM 응답 오류: {llm_response.error}")
                return None
            
            # 6단계: JSON 응답을 CandidatePersona 객체로 변환
            persona = self._parse_llm_response_to_persona(llm_response.content, resume_data.get('ai_resume_id', 0))
            
            if persona:
                print(f"✅ 페르소나 생성 완료: {persona.name} ({company_name} {position_name})")
                return persona
            else:
                print(f"❌ 페르소나 파싱 실패")
                return None
                
        except Exception as e:
            print(f"❌ 페르소나 생성 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_position_id(self, position_name: str) -> Optional[int]:
        """직군명을 position_id로 변환"""
        position_lower = position_name.lower().replace(" ", "")
        return POSITION_MAPPING.get(position_lower)
    
    def _get_random_resume_from_db(self, position_id: int) -> Optional[Dict[str, Any]]:
        """데이터베이스에서 해당 직군의 이력서를 무작위로 선택"""
        if get_supabase_client is None:
            print("⚠️ Supabase 클라이언트를 사용할 수 없습니다")
            return None
        
        try:
            supabase = get_supabase_client()
            
            # 해당 position_id의 이력서들 조회
            response = supabase.table('ai_resume').select('*').eq('position_id', position_id).execute()
            
            if not response.data:
                print(f"📄 position_id {position_id}에 해당하는 이력서가 없습니다")
                return None
            
            # 무작위로 하나 선택
            selected_resume = random.choice(response.data)
            print(f"🎲 {len(response.data)}개 이력서 중 ID {selected_resume.get('ai_resume_id', 'unknown')} 선택")
            
            return selected_resume
            
        except Exception as e:
            print(f"❌ 이력서 조회 오류: {str(e)}")
            return None
    
    def _get_company_info(self, company_name: str) -> Dict[str, Any]:
        """회사 정보 가져오기"""
        # companies_data.json에서 회사 정보 찾기
        for company in self.companies_data.get("companies", []):
            if company.get("name", "").lower() == company_name.lower() or company.get("id", "").lower() == company_name.lower():
                return company
        
        # 찾지 못한 경우 기본값 반환
        return {
            "name": company_name,
            "core_competencies": [],
            "tech_focus": [],
            "talent_profile": ""
        }
    
    def _build_persona_generation_prompt(self, resume_data: Dict[str, Any], company_name: str, position_name: str, company_info: Dict[str, Any]) -> str:
        """데이터베이스 이력서를 기반으로 LLM 페르소나 생성 프롬프트 구성"""
        
        # 이력서 데이터 정리
        career = resume_data.get('career', '')
        academic = resume_data.get('academic_record', '')
        tech_skills = resume_data.get('tech', '')
        activities = resume_data.get('activities', '')
        certificates = resume_data.get('certificate', '')
        awards = resume_data.get('awards', '')
        resume_id = resume_data.get('ai_resume_id', 0)
        
        # 회사 정보 정리
        company_profile = company_info.get('talent_profile', '')
        core_competencies = ', '.join(company_info.get('core_competencies', []))
        tech_focus = ', '.join(company_info.get('tech_focus', []))
        
        prompt = f"""
다음 이력서 데이터를 분석하여 {company_name} {position_name} 직군에 지원하는 인간미 넘치는 AI 지원자 페르소나를 생성하세요.

=== 이력서 데이터 ===
- 경력: {career}
- 학력: {academic}
- 기술 스탉: {tech_skills}
- 활동: {activities}
- 자격증: {certificates}
- 수상: {awards}

=== {company_name} 회사 정보 ===
- 인재상: {company_profile}
- 핵심 역량: {core_competencies}
- 기술 중점: {tech_focus}

=== 인간미 또는 생성 지시사항 ===
1. **이름 생성**: 한국 이름으로 자연스럽게 생성하세요.

2. **인간적 약점 포함**: 이력서의 강점과 함께 개선이 필요한 약점을 한 가지 포함시켜라. (예: "너무 완벽주의적인 성향", "대인관계에서 소극적인 모습")

3. **프로젝트 성과와 어려움**: 각 프로젝트에는 성공적인 성과(achievements)와 함께 겪었던 어려움(challenges)을 포함시켜라.

4. **개인적 동기**: 이 지원자가 왜 이 직업을 선택했는지에 대한 개인적인 동기(motivation)를 이력서 데이터를 바탕으로 추론해라.

5. **개인적 교훈**: 이력서의 활동(블로그, 오픈소스, 프로젝트 등)을 바탕으로 개인적인 교훈(inferred_personal_experiences)을 추론해라. **절대 없는 사실을 지어내지 마라.**

6. **JSON 스키마 준수**: 반드시 아래 지정된 JSON 스키마에 맞춰서 응답해야 한다.

=== 출력 JSON 스키마 ===
{{
  "name": "춘식이",
  "summary": "예: 5년차 Java 백엔드 개발자로, 대용량 트래픽 처리와 MSA 설계에 강점이 있습니다.",
  "background": {{
    "career_years": "예: 5",
    "current_position": "예: 시니어 백엔드 개발자",
    "education": ["예: OO대학교 컴퓨터공학과 졸업"]
  }},
  "technical_skills": ["예: Java", "예: Spring Boot"],
  "projects": [
    {{
      "name": "예: 대용량 결제 시스템 개발",
      "description": "예: 일일 100만건 결제 처리를 위한 고가용성 시스템 구축",
      "tech_stack": ["예: Java", "예: Redis"],
      "role": "예: 백엔드 리드 개발자",
      "achievements": ["예: 처리 속도 40% 향상", "예: 시스템 안정성 99.9% 달성"],
      "challenges": ["예: 대량 트래픽 발생 시 데이터베이스 병목 현상", "예: 레거시 시스템과의 호환성 문제"]
    }}
  ],
  "experiences": [
    {{
      "company": "예: ABC 테크",
      "position": "예: 시니어 개발자",
      "period": "예: 2020.03 - 2024.12",
      "achievements": ["예: 결제 시스템 성능 최적화", "예: 신입 개발자 3명 멘토링"]
    }}
  ],
  "strengths": ["예: 대용량 시스템 설계", "예: 성능 최적화"],
  "weaknesses": ["예: 완벽주의적 성향으로 때로 일정 지연"],
  "motivation": "예: 대학 시절 처음 코딩을 배웠을 때의 성취감과 문제 해결의 즉시에 매력을 느껴 개발자의 길을 선택하게 되었습니다.",
  "inferred_personal_experiences": [
    {{
      "category": "예: 학습경험",
      "experience": "예: 개발 블로그를 운영하며 지식을 정리하고 공유하는 활동을 지속해옴",
      "lesson": "예: 지식을 남과 공유할 때 더 깊이 이해하게 되고, 다른 사람들의 피드백으로 성장할 수 있다는 것을 배웠습니다."
    }}
  ],
  "career_goal": "예: {company_name}의 고가용성 시스템을 책임지는 기술 리더로 성장하여, 전 세계 사용자들에게 안정적이고 빠른 서비스를 제공하고 싶습니다.",
  "personality_traits": ["예: 분석적", "예: 추진력 있는"],
  "interview_style": "예: 구체적인 경험과 수치를 바탕으로 체계적으로 설명하는 스타일",
  "generated_by": "gpt-4o-mini",
  "resume_id": {resume_id}
}}

**중요**: 
1. 이름은 반드시 "춘식이"로 설정하세요.
2. 오직 JSON 형식으로만 응답하고, 다른 설명이나 주석은 절대 추가하지 마세요.
"""
        return prompt.strip()
    
    def _build_system_prompt_for_persona_generation(self) -> str:
        """페르소나 생성용 시스템 프롬프트"""
        return """당신은 전문적인 AI 페르소나 생성 에이전트입니다.
이력서 데이터를 바탕으로 인간적이고 현실적인 AI 지원자 페르소나를 생성하는 전문가입니다.

핀수 지시사항:
1. 이력서에 있는 사실만 기반으로 추론하고, 없는 사실은 절대 지어내지 마세요.
2. 인간적인 매력과 약점을 모두 포함하여 현실적인 인물로 만드세요.
3. 회사와 직군의 특성에 맞는 페르소나를 생성하세요.
4. 반드시 지정된 JSON 스키마에 맞춰 응답하세요.
5. JSON 외의 다른 내용은 절대 출력하지 마세요."""
    
    def _generate_persona_with_extended_tokens(self, prompt: str, system_prompt: str) -> LLMResponse:
        """페르소나 생성용 확장된 토큰으로 LLM 호출"""
        import openai
        import os
        import time
        
        try:
            # OpenAI 클라이언트 직접 생성
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return LLMResponse(
                    content="",
                    provider=LLMProvider.OPENAI_GPT4O_MINI,
                    model_name="gpt-4o-mini",
                    error="OpenAI API 키가 설정되지 않았습니다."
                )
            
            client = openai.OpenAI(api_key=api_key)
            start_time = time.time()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 페르소나 생성용 확장 파라미터
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,  # 페르소나 생성을 위해 충분한 토큰 할당
                temperature=0.7,
                timeout=60.0
            )
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=response.choices[0].message.content.strip(),
                provider=LLMProvider.OPENAI_GPT4O_MINI,
                model_name="gpt-4o-mini",
                token_count=response.usage.total_tokens if response.usage else None,
                response_time=response_time
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                provider=LLMProvider.OPENAI_GPT4O_MINI,
                model_name="gpt-4o-mini",
                error=f"페르소나 생성 LLM 호출 실패: {str(e)}"
            )
    
    def _parse_llm_response_to_persona(self, llm_response: str, resume_id: int) -> Optional[CandidatePersona]:
        """LLM JSON 응답을 CandidatePersona 객체로 파싱"""
        try:
            # JSON 영역만 추출 (전후 설명 제거)
            response_clean = llm_response.strip()
            
            # JSON 블록 찾기
            if response_clean.startswith('```json'):
                response_clean = response_clean.replace('```json', '').replace('```', '').strip()
            elif response_clean.startswith('```'):
                response_clean = response_clean.replace('```', '').strip()
            
            # JSON 파싱
            persona_data = json.loads(response_clean)
            
            # 필수 필드 검증
            required_fields = ['name', 'summary', 'background', 'technical_skills', 'projects', 'experiences', 
                              'strengths', 'weaknesses', 'motivation', 'inferred_personal_experiences', 
                              'career_goal', 'personality_traits', 'interview_style']
            
            for field in required_fields:
                if field not in persona_data:
                    print(f"❌ 필수 필드 누락: {field}")
                    return None
            
            # CandidatePersona 객체 생성
            persona = CandidatePersona(
                name=persona_data['name'],
                summary=persona_data['summary'],
                background=persona_data['background'],
                technical_skills=persona_data['technical_skills'],
                projects=persona_data['projects'],
                experiences=persona_data['experiences'],
                strengths=persona_data['strengths'],
                weaknesses=persona_data['weaknesses'],
                motivation=persona_data['motivation'],
                inferred_personal_experiences=persona_data['inferred_personal_experiences'],
                career_goal=persona_data['career_goal'],
                personality_traits=persona_data['personality_traits'],
                interview_style=persona_data['interview_style'],
                generated_by=persona_data.get('generated_by', 'gpt-4o-mini'),
                resume_id=resume_id
            )
            
            return persona
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {str(e)}")
            print(f"LLM 응답 길이: {len(llm_response)} 문자")
            print(f"응답 마지막 100자: ...{llm_response[-100:]}")
            return None
        except Exception as e:
            print(f"❌ 페르소나 객체 생성 오류: {str(e)}")
            return None
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로드"""
        return safe_json_load("llm/data/companies_data.json", {"companies": []})
    
    def _load_fixed_questions(self) -> Dict[str, List[Dict]]:
        """고정 질문 데이터 로드"""
        return get_fixed_questions()
    
    def start_ai_interview(self, company_id: str, position: str) -> str:
        """AI 지원자 면접 시작 (면접자와 동일한 플로우)"""
        persona = self.get_persona(company_id)
        if not persona:
            raise ValueError(f"회사 {company_id}의 AI 지원자 페르소나를 찾을 수 없습니다.")
        
        # AI 세션 생성
        ai_session = AICandidateSession(company_id, position, persona)
        self.ai_sessions[ai_session.session_id] = ai_session
        
        return ai_session.session_id
    
    def get_ai_next_question(self, ai_session_id: str) -> Optional[Dict[str, Any]]:
        """AI 지원자 다음 질문 가져오기 (면접자와 동일한 구조)"""
        ai_session = self.ai_sessions.get(ai_session_id)
        if not ai_session or ai_session.is_complete():
            return None
        
        # 현재 질문 계획 가져오기
        question_plan = ai_session.get_next_question_plan()
        if not question_plan:
            return None
        
        # 면접자와 동일한 질문 생성 로직
        question_content, question_intent = self._generate_ai_question(
            ai_session, question_plan
        )
        
        return {
            "question_id": f"ai_q_{ai_session.current_question_count + 1}",
            "question_type": question_plan["type"].value,
            "question_content": question_content,
            "question_intent": question_intent,
            "progress": f"{ai_session.current_question_count + 1}/{len(ai_session.question_plan)}",
            "personalized": False  # AI는 표준 질문 사용
        }
    
    def _generate_ai_question(self, ai_session: AICandidateSession, question_plan: Dict) -> tuple[str, str]:
        """AI 지원자용 질문 생성 (면접자와 동일한 로직)"""
        question_type = question_plan["type"]
        
        # AI 이름 가져오기 (춘식이)
        ai_name = self.get_ai_name(LLMProvider.OPENAI_GPT35)
        
        # 첫 두 질문은 완전히 고정 (AI 전용 - honorific 포함)
        if question_type == QuestionType.INTRO:
            return (
                f"{ai_name}님, 자기소개를 부탁드립니다.",
                "지원자의 기본 배경, 경력, 성격을 파악하여 면접 분위기를 조성"
            )
        elif question_type == QuestionType.MOTIVATION:
            company_data = self._get_company_data(ai_session.company_id)
            return (
                f"{ai_name}님께서 {company_data.get('name', '저희 회사')}에 지원하게 된 동기는 무엇인가요?",
                "회사에 대한 관심도, 지원 의지, 회사 이해도를 평가"
            )
        
        # 고정 질문 풀에서 선택
        if question_type == QuestionType.HR:
            questions = self.fixed_questions.get("hr_questions", [])
        elif question_type == QuestionType.TECH:
            questions = self.fixed_questions.get("technical_questions", [])
        elif question_type == QuestionType.COLLABORATION:
            questions = self.fixed_questions.get("collaboration_questions", [])
        else:
            # FOLLOWUP이나 기타 질문은 동적 생성
            return self._generate_dynamic_question(ai_session, question_type)
        
        # 이미 사용된 질문 제외
        used_questions = set()
        for qa in ai_session.ai_answers:
            used_questions.add(qa.question_content)
        
        # 사용 가능한 질문 필터링
        available_questions = [q for q in questions if q["content"] not in used_questions]
        
        if available_questions:
            # 레벨에 따라 정렬된 질문 선택
            current_question_index = ai_session.current_question_count
            if current_question_index < len(available_questions):
                selected_question = available_questions[current_question_index % len(available_questions)]
            else:
                selected_question = available_questions[0]
            
            # 질문에 AI 이름 호칭 추가
            ai_name = self.get_ai_name(LLMProvider.OPENAI_GPT35)
            question_content = self._add_honorific_to_question(selected_question["content"], ai_name)
            return question_content, selected_question["intent"]
        
        # 폴백 질문
        ai_name = self.get_ai_name(LLMProvider.OPENAI_GPT35)
        return self._get_fallback_question(question_type, ai_name)
    
    def _generate_dynamic_question(self, ai_session: AICandidateSession, question_type: QuestionType) -> tuple[str, str]:
        """동적 질문 생성 (심화 질문 등)"""
        context = ai_session.get_previous_answers_context()
        company_data = self._get_company_data(ai_session.company_id)
        
        if question_type == QuestionType.FOLLOWUP:
            # 이전 답변을 바탕으로 한 심화 질문
            if ai_session.ai_answers:
                last_answer = ai_session.ai_answers[-1]
                return (
                    f"방금 말씀하신 {last_answer.question_content[:30]}... 부분에 대해 좀 더 자세히 설명해 주실 수 있나요?",
                    "이전 답변의 구체적인 사례나 경험의 디테일 탐구"
                )
        
        ai_name = self.get_ai_name(LLMProvider.OPENAI_GPT35)
        return f"{ai_name}님에 대해 더 알고 싶습니다.", "일반적인 질문"
    
    def _get_fallback_question(self, question_type: QuestionType, persona_name: str) -> tuple[str, str]:
        """폴백 질문 (면접자와 동일)"""
        fallback_questions = {
            QuestionType.INTRO: (f"{persona_name}님, 간단한 자기소개 부탁드립니다.", "기본 배경 파악"),
            QuestionType.MOTIVATION: (f"{persona_name}님이 저희 회사에 지원하게 된 동기가 궁금합니다.", "지원 동기 파악"),
            QuestionType.HR: (f"{persona_name}님의 장점과 성장하고 싶은 부분은 무엇인가요?", "개인적 특성 평가"),
            QuestionType.TECH: (f"{persona_name}님의 기술적 경험에 대해 말씀해 주세요.", "기술 역량 평가"),
            QuestionType.COLLABORATION: (f"{persona_name}님의 팀 협업 경험을 공유해 주세요.", "협업 능력 평가"),
            QuestionType.FOLLOWUP: (f"{persona_name}님이 가장 자신 있는 경험을 더 자세히 설명해 주세요.", "심화 탐구")
        }
        return fallback_questions.get(question_type, (f"{persona_name}님, 본인에 대해 말씀해 주세요.", "일반적인 질문"))
    
    def _add_honorific_to_question(self, question_content: str, ai_name: str) -> str:
        """질문에 AI 이름 호칭 추가"""
        # 이미 호칭이 포함된 경우 그대로 반환
        if "님" in question_content or ai_name in question_content:
            return question_content
        
        # 질문 앞에 호칭 추가
        return f"{ai_name}님, {question_content}"

    def generate_ai_answer_for_question(self, ai_session_id: str, question_data: Dict[str, Any]) -> AnswerResponse:
        """특정 질문에 대한 AI 답변 생성 (일관성 유지)"""
        ai_session = self.ai_sessions.get(ai_session_id)
        if not ai_session:
            return AnswerResponse(
                answer_content="",
                quality_level=QualityLevel(8),
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI,
                persona_name="Unknown",
                confidence_score=0.0,
                response_time=0.0,
                reasoning="AI 세션을 찾을 수 없음",
                error=f"AI 세션을 찾을 수 없습니다: {ai_session_id}"
            )
        
        # 일관성 있는 답변 생성을 위한 요청 구성
        request = AnswerRequest(
            question_content=question_data["question_content"],
            question_type=QuestionType(question_data["question_type"]),
            question_intent=question_data["question_intent"],
            company_id=ai_session.company_id,
            position=ai_session.position,
            quality_level=QualityLevel(8),  # 고품질 답변
            llm_provider=LLMProvider.OPENAI_GPT4O_MINI,
            additional_context=ai_session.get_previous_answers_context()
        )
        
        # 답변 생성
        answer_response = self.generate_answer(request)
        
        # AI 세션에 답변 저장
        if not answer_response.error:
            qa_pair = QuestionAnswer(
                question_id=question_data["question_id"],
                question_type=QuestionType(question_data["question_type"]),
                question_content=question_data["question_content"],
                answer_content=answer_response.answer_content,
                timestamp=datetime.now(),
                question_intent=question_data["question_intent"]
            )
            ai_session.add_ai_answer(qa_pair)
        
        return answer_response
    
    def _parse_personas_data(self, personas_data: Dict) -> Dict[str, CandidatePersona]:
        """페르소나 데이터 파싱"""
        personas = {}
        for company_id, data in personas_data.items():
            personas[company_id] = CandidatePersona(
                company_id=company_id,
                name=data.get("name", f"지원자_{company_id}"),
                background=data.get("background", {}),
                technical_skills=data.get("technical_skills", []),
                projects=data.get("projects", []),
                experiences=data.get("experiences", []),
                strengths=data.get("strengths", []),
                achievements=data.get("achievements", []),
                career_goal=data.get("career_goal", ""),
                personality_traits=data.get("personality_traits", []),
                interview_style=data.get("interview_style", ""),
                success_factors=data.get("success_factors", [])
            )
        return personas
    
    def get_persona(self, company_id: str) -> Optional[CandidatePersona]:
        """회사별 페르소나 조회 (동적 생성 시스템에서는 deprecated)"""
        print(f"⚠️ get_persona() 메서드는 deprecated입니다. create_persona_for_interview()를 사용하세요.")
        print(f"🔍 페르소나 조회 요청: {company_id}")
        print(f"🔍 캐시된 페르소나: {list(self.candidate_personas.keys())}")
        persona = self.candidate_personas.get(company_id)
        if persona:
            print(f"✅ 캐시된 페르소나 찾음: {persona.name}")
        else:
            print(f"❌ 캐시된 페르소나 없음: {company_id}")
        return persona
    
    def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        """질문에 대한 AI 지원자 답변 생성"""
        start_time = datetime.now()
        
        # 페르소나 조회
        persona = self.get_persona(request.company_id)
        if not persona:
            return AnswerResponse(
                answer_content="",
                quality_level=request.quality_level,
                llm_provider=request.llm_provider,
                persona_name="Unknown",
                confidence_score=0.0,
                response_time=0.0,
                reasoning="페르소나를 찾을 수 없음",
                error=f"회사 {request.company_id}의 페르소나를 찾을 수 없습니다."
            )
        
        # 회사 데이터 조회
        company_data = self._get_company_data(request.company_id)
        
        # 답변 생성 프롬프트 구성
        prompt = self._build_answer_prompt(request, persona, company_data)
        system_prompt = self._build_system_prompt(persona, company_data, request.question_type, request.llm_provider)
        
        # 품질 레벨에 맞는 프롬프트 조정
        quality_prompt = self.quality_controller.generate_quality_prompt(
            prompt, 
            request.quality_level,
            request.question_type.value
        )
        
        # LLM 응답 생성
        llm_response = self.llm_manager.generate_response(
            request.llm_provider,
            quality_prompt,
            system_prompt
        )
        
        # 응답 시간 계산
        response_time = (datetime.now() - start_time).total_seconds()
        
        # 신뢰도 점수 계산
        confidence_score = self._calculate_confidence_score(llm_response, request.quality_level)
        
        # 답변 후처리
        processed_answer = self._post_process_answer(llm_response.content, request.quality_level)
        
        # 모델에 따른 AI 이름 결정
        ai_name = self.get_ai_name(request.llm_provider)
        
        return AnswerResponse(
            answer_content=processed_answer,
            quality_level=request.quality_level,
            llm_provider=request.llm_provider,
            persona_name=ai_name,  # 모델별 고정 이름 사용
            confidence_score=confidence_score,
            response_time=response_time,
            reasoning=f"{ai_name}의 {request.company_id} 면접 답변 (품질 레벨: {request.quality_level.value})",
            error=llm_response.error,
            metadata={
                "token_count": llm_response.token_count,
                "company_id": request.company_id,
                "question_type": request.question_type.value,
                "original_prompt_length": len(prompt)
            }
        )
    
    def _get_relevant_personal_experiences(self, persona: CandidatePersona, question_content: str) -> str:
        """질문과 관련된 개인적 경험 선별"""
        
        # 페르소나에서 개인 경험 추출
        personal_experiences = self._get_persona_attribute(persona, 'personal_experiences', [])
        if not personal_experiences:
            return "개인적 경험: 성실하고 꾸준히 노력하는 성격으로, 어려운 상황에서도 포기하지 않고 끝까지 최선을 다하는 것을 중요하게 생각합니다."
        
        # 질문 내용에 따라 관련 경험 선별
        question_lower = question_content.lower()
        relevant_experiences = []
        
        # 키워드 매핑
        keyword_category_map = {
            "가치관": ["가치관형성", "개인도전"],
            "성격": ["인간관계", "개인도전"],
            "강점": ["학창시절", "개인도전", "실패극복"],
            "약점": ["실패극복", "인간관계"],
            "성장": ["개인도전", "실패극복", "학창시절"],
            "목표": ["가치관형성", "개인도전"],
            "도전": ["개인도전", "실패극복"],
            "협업": ["인간관계", "학창시절"],
            "소통": ["인간관계", "학창시절"],
            "리더십": ["학창시절", "인간관계"],
            "실패": ["실패극복"],
            "어려움": ["실패극복", "가치관형성"]
        }
        
        # 질문과 관련된 카테고리 찾기
        matched_categories = set()
        for keyword, categories in keyword_category_map.items():
            if keyword in question_lower:
                matched_categories.update(categories)
        
        # 관련 경험 선별
        for exp in personal_experiences:
            if not matched_categories or exp.get('category') in matched_categories:
                relevant_experiences.append(exp)
        
        # 최대 3개까지만 선별
        if not relevant_experiences:
            relevant_experiences = personal_experiences[:3]
        else:
            relevant_experiences = relevant_experiences[:3]
        
        # 경험들을 문자열로 포맷팅
        experience_text = ""
        for i, exp in enumerate(relevant_experiences, 1):
            experience_text += f"""
{i}. [{exp.get('category', '개인경험')}] {exp.get('experience', '')}
   배운 점: {exp.get('lesson', '')}
   감정: {exp.get('emotion', '')}
"""
        
        return experience_text.strip()
    
    def _get_persona_attribute(self, persona: CandidatePersona, attr_name: str, default_value):
        """페르소나 속성 안전하게 가져오기"""
        try:
            # 페르소나 객체에서 직접 속성 접근
            if hasattr(persona, attr_name):
                return getattr(persona, attr_name)
            
            # 사전 형태로 접근 (페르소나가 dict인 경우)
            if hasattr(persona, '__dict__') and attr_name in persona.__dict__:
                return persona.__dict__[attr_name]
            
            # JSON 데이터에서 직접 로드한 경우 - _raw_data 속성 확인
            if hasattr(persona, '_raw_data') and attr_name in persona._raw_data:
                return persona._raw_data[attr_name]
            
            # 페르소나 딕셔너리에서 직접 접근 시도
            persona_dict = self._get_persona_dict(persona.company_id, persona.name)
            if persona_dict and attr_name in persona_dict:
                return persona_dict[attr_name]
                
            return default_value
        except:
            return default_value
    
    def _get_persona_dict(self, company_id: str, persona_name: str) -> Dict[str, Any]:
        """페르소나 딕셔너리 직접 조회"""
        try:
            personas = self.personas_data.get("personas", {})
            if company_id in personas:
                return personas[company_id]
            return {}
        except:
            return {}
    
    def _get_company_data(self, company_id: str) -> Dict[str, Any]:
        """회사 데이터 조회"""
        for company in self.companies_data.get("companies", []):
            if company["id"] == company_id:
                return company
        return {}
    
    def get_ai_name(self, llm_provider: LLMProvider) -> str:
        """모델에 따른 AI 지원자 이름 반환"""
        return AI_CANDIDATE_NAMES.get(llm_provider, "춘식이")  # 기본값: 춘식이
    
    def _build_system_prompt(self, persona: CandidatePersona, company_data: Dict, question_type: QuestionType, llm_provider: LLMProvider = LLMProvider.OPENAI_GPT35) -> str:
        """질문 타입별 시스템 프롬프트 구성"""
        
        # AI 이름 결정 (모델에 따라 동적으로 설정)
        ai_name = self.get_ai_name(llm_provider)
        
        base_info = f"""당신은 {company_data.get('name', '회사')} 면접에 참여한 우수한 지원자입니다.

=== 중요: 당신의 이름은 "{ai_name}"입니다 ===
- **자기소개 질문(INTRO)에서만** "{ai_name}"라고 이름을 언급하세요
- **다른 모든 질문에서는 절대 이름을 언급하지 마세요**
- "안녕하세요" 같은 인사말도 자기소개가 아닌 경우 사용하지 마세요
- 다른 이름(김네이버, 박카카오 등)을 절대 사용하지 마세요

예시:
- 자기소개: "안녕하세요, 저는 {ai_name}라고 합니다. 5년의 백엔드 개발 경험을..."
- 지원동기: "제가 네이버에 지원하게 된 이유는..." (이름/인사 없이 바로 시작)
- 기술질문: "그 부분에 대해서는 제 경험을 말씀드리면..." (이름/인사 없이)
- 기타질문: "제 생각에는..." 또는 "저의 경험으로는..." (이름/인사 없이)

=== 당신의 배경 ===
- 경력: {persona.background.get('career_years', '0')}년
- 현재 직책: {persona.background.get('current_position', '지원자')}
- 성격 특성: {', '.join(persona.personality_traits)}
- 면접 스타일: {persona.interview_style}

=== 당신의 강점 ===
{', '.join(persona.strengths)}

=== 당신의 목표 ===
{persona.career_goal}"""

        if question_type == QuestionType.INTRO:
            return f"""{base_info}

=== 자기소개 질문 답변 스타일 ===
- **반드시 "{ai_name}"라고 이름을 먼저 소개하세요**
- 간단하고 명확하게 자신을 소개하세요
- 주요 경력과 강점을 간략히 언급하세요
- 면접에 대한 감사 인사를 포함하세요
- 예: "안녕하세요, 저는 {ai_name}라고 합니다. 5년의 백엔드 개발 경험을 가지고 있으며..."

**중요**: 자기소개 질문에서만 이름을 언급하세요. 다른 모든 질문에서는 이름을 절대 언급하지 마세요."""
        
        elif question_type == QuestionType.HR:
            return f"""{base_info}

=== 인성 질문 답변 스타일 ===
- **절대 이름을 언급하지 마세요** (이미 자기소개에서 했음)
- **"안녕하세요" 같은 인사말 사용 금지**
- 바로 답변 내용으로 시작하세요
- **개인적이고 진정성 있게** 답변하세요
- 기술적/프로젝트 경험보다는 **개인적 경험과 감정**을 중심으로 답변
- 당신의 **가치관, 성격, 인생 철학**을 드러내세요
- "제 경험을 말씀드리면..." "저는 개인적으로..." 같은 표현 사용
- **솔직하고 인간적인** 면모를 보여주세요
- 구체적인 개인 경험과 그때의 **감정, 생각의 변화**를 포함하세요"""
        
        elif question_type == QuestionType.TECH:
            return f"""{base_info}

=== 기술 질문 답변 스타일 ===
- **이름을 언급하지 마세요** (이미 자기소개에서 했음)
- 기술적 전문성과 경험을 중심으로 답변하세요
- 구체적인 프로젝트 사례와 기술 스택을 언급하세요
- 문제 해결 과정과 기술적 선택의 이유를 설명하세요
- 전문적이면서도 자신감 있는 톤을 유지하세요"""
        
        elif question_type == QuestionType.COLLABORATION:
            return f"""{base_info}

=== 협업 질문 답변 스타일 ===
- **이름을 언급하지 마세요** (이미 자기소개에서 했음)
- 팀워크와 협업 경험을 중심으로 답변하세요
- 구체적인 협업 상황과 해결 과정을 설명하세요
- 다른 팀원들과의 소통 방식과 갈등 해결 경험을 포함하세요
- 협력적이고 배려심 있는 면모를 보여주세요"""
        
        else:  # MOTIVATION, FOLLOWUP 등
            return f"""{base_info}

=== 면접 태도 ===
- **절대 이름을 언급하지 마세요** (자기소개가 아닌 경우)
- **"안녕하세요" 같은 인사말 사용 금지**
- 바로 답변 내용으로 시작하세요
- 자신감 있고 성실하게 답변하세요
- 구체적인 경험을 바탕으로 답변하세요
- {company_data.get('name', '회사')}에 대한 진정성 있는 관심을 보여주세요
- 전문적이면서도 자연스러운 톤을 유지하세요

답변 시작 예시:
- 지원동기: "제가 네이버에 지원하게 된 이유는..."
- 일반질문: "그 부분에 대해서는..." "제 경험으로는..." "저는 항상..."
- 기술질문: "해당 기술에 대한 제 경험을 말씀드리면..."
- 협업질문: "팀워크 관련해서는 제가 겪었던 사례가..."
"""
    
    def _build_answer_prompt(self, request: AnswerRequest, persona: CandidatePersona, company_data: Dict) -> str:
        """답변 생성 프롬프트 구성"""
        
        # 페르소나의 기술 스킬 및 프로젝트 정보
        tech_info = f"주요 기술: {', '.join(persona.technical_skills[:5])}"
        
        projects_info = ""
        for i, project in enumerate(persona.projects[:2], 1):
            projects_info += f"\n{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}"
            if project.get('achievements'):
                projects_info += f" (성과: {', '.join(project['achievements'])})"
        
        experiences_info = ""
        for exp in persona.experiences[:2]:
            experiences_info += f"\n- {exp.get('company', '회사')}: {exp.get('position', '개발자')} ({exp.get('period', '기간')})"
            if exp.get('achievements'):
                experiences_info += f" - {', '.join(exp['achievements'])}"
        
        # 회사별 맞춤 정보
        company_focus = ""
        if company_data:
            company_focus = f"""
=== {company_data['name']} 관련 정보 ===
- 인재상: {company_data.get('talent_profile', '')}
- 기술 중점: {', '.join(company_data.get('tech_focus', []))}
- 핵심 역량: {', '.join(company_data.get('core_competencies', []))}"""
        
        # 질문 타입별 프롬프트 구성
        if request.question_type == QuestionType.HR:
            # 개인적 경험 선별 (질문과 관련된 경험 우선)
            personal_experiences = self._get_relevant_personal_experiences(persona, request.question_content)
            life_philosophy = self._get_persona_attribute(persona, 'life_philosophy', '지속적인 학습과 성장을 추구합니다.')
            core_values = self._get_persona_attribute(persona, 'core_values', ['성장', '협업', '도전'])
            
            prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (인성 질문)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 개인적 특성 ===
- 성격 특성: {', '.join(persona.personality_traits)}
- 인생 철학: {life_philosophy}
- 핵심 가치: {', '.join(core_values)}
- 면접 스타일: {persona.interview_style}

=== 활용할 수 있는 개인 경험들 ===
{personal_experiences}

=== 답변 방식 (매우 중요) ===
이 질문은 당신의 **인성과 가치관**을 평가하는 질문입니다.

**반드시 지켜야 할 원칙:**
- ❌ 프로젝트 경험 중심 답변 금지
- ✅ 개인적 경험과 감정을 중심으로 답변
- ✅ 위의 개인 경험들을 적극 활용하세요
- ✅ 학창시절, 일상생활, 인간관계, 개인적 도전 등의 경험 포함
- ✅ "개인적으로 저는...", "제가 중요하게 생각하는 것은..." 표현 사용
- ✅ 감정과 생각의 변화 과정을 구체적으로 표현
- ✅ 실패와 극복 경험, 가치관 형성 과정 포함

**답변 구조:**
1. 개인적 관점/가치관 표현
2. 구체적인 개인 경험 사례 (업무 외 경험 우선)
3. 그 경험에서 느낀 감정과 배운 점
4. 현재 삶/업무에 어떻게 적용하고 있는지

위 지침을 바탕으로 진정성 있고 인간적인 답변을 해주세요.
"""
        elif request.question_type == QuestionType.COLLABORATION:
            # 협업 질문: 개인적 소통/관계 경험 포함
            personal_experiences = self._get_relevant_personal_experiences(persona, request.question_content)
            core_values = self._get_persona_attribute(persona, 'core_values', ['협업', '소통', '성장'])
            
            prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value} (협업 능력 평가)
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 개인적 특성 ===
- 성격 특성: {', '.join(persona.personality_traits)}
- 핵심 가치: {', '.join(core_values)}
- 면접 스타일: {persona.interview_style}

=== 참고할 개인 경험들 ===
{personal_experiences}

=== 당신의 배경 정보 ===
{tech_info}

=== 주요 프로젝트 경험 ==={projects_info}

=== 답변 방식 ===
이 질문은 당신의 **협업 능력과 소통 스타일**을 평가하는 질문입니다.

**답변 비율 가이드:**
- 업무/프로젝트 경험: 60%
- 개인적 경험 (학창시절, 일상 관계): 40%

**포함해야 할 요소:**
- 구체적인 협업/소통 경험 (업무+개인)
- 그 상황에서의 감정과 생각
- 갈등 해결이나 관계 개선 사례
- 개인적 소통 철학이나 방식
- 팀에서의 자신의 역할과 기여

위의 개인 경험들도 적절히 활용하여 인간적이고 진정성 있는 답변을 해주세요.
"""
        else:
            # 기술 질문 등 기타 질문
            life_philosophy = self._get_persona_attribute(persona, 'life_philosophy', '지속적인 학습과 성장을 추구합니다.')
            
            prompt = f"""
=== 면접 상황 ===
회사: {company_data.get('name', request.company_id)}
직군: {request.position}
질문 유형: {request.question_type.value}
질문: {request.question_content}
질문 의도: {request.question_intent}

=== 당신의 특성 ===
- 성격 특성: {', '.join(persona.personality_traits)}
- 인생 철학: {life_philosophy}
- 면접 스타일: {persona.interview_style}

=== 당신의 배경 정보 ===
{tech_info}

=== 주요 프로젝트 경험 ==={projects_info}

=== 업무 경험 ==={experiences_info}

=== 주요 성취 ===
{', '.join(getattr(persona, 'achievements', persona.strengths))}
{company_focus}

=== 답변 방식 ===
**답변 구성 비율:**
- 기술적/전문적 내용: 70%
- 개인적 학습/성장 관점: 30%

**포함 요소:**
- 구체적인 기술 경험과 성과
- 개인적 학습 동기와 과정
- 기술에 대한 본인만의 철학이나 관점
- 실패와 극복 경험
- 지속적 성장을 위한 노력

위 정보를 바탕으로 기술적 전문성과 개인적 성장 스토리를 균형있게 포함하여 답변하세요.
"""
        
        if request.additional_context:
            prompt += f"\n\n=== 추가 컨텍스트 ===\n{request.additional_context}"
        
        return prompt
    
    def _calculate_confidence_score(self, llm_response: LLMResponse, quality_level: QualityLevel) -> float:
        """답변 신뢰도 점수 계산"""
        if llm_response.error:
            return 0.0
        
        base_score = 0.7
        
        # 품질 레벨에 따른 가산점
        quality_bonus = (quality_level.value - 5) * 0.05
        
        # 답변 길이에 따른 가산점
        length_bonus = min(len(llm_response.content) / 1000, 0.2)
        
        # 응답 시간에 따른 가산점 (빠를수록 좋음)
        time_bonus = 0.1 if llm_response.response_time and llm_response.response_time < 3.0 else 0.0
        
        confidence = min(base_score + quality_bonus + length_bonus + time_bonus, 1.0)
        return round(confidence, 2)
    
    def _post_process_answer(self, answer: str, quality_level: QualityLevel) -> str:
        """답변 후처리"""
        if not answer:
            return ""
        
        # 기본 정리
        processed = answer.strip()
        
        # 품질 레벨에 따른 추가 처리
        config = self.quality_controller.get_quality_config(quality_level)
        
        # 길이 조정
        if len(processed) > config.answer_length_max:
            # 문장 단위로 자르기
            sentences = processed.split('. ')
            total_length = 0
            result_sentences = []
            
            for sentence in sentences:
                if total_length + len(sentence) <= config.answer_length_max:
                    result_sentences.append(sentence)
                    total_length += len(sentence) + 2
                else:
                    break
            
            processed = '. '.join(result_sentences)
            if not processed.endswith('.'):
                processed += '.'
        
        return processed
    
    def compare_answers(self, request: AnswerRequest, quality_levels: List[QualityLevel]) -> Dict[QualityLevel, AnswerResponse]:
        """여러 품질 레벨로 답변 생성 및 비교"""
        results = {}
        
        for level in quality_levels:
            request.quality_level = level
            results[level] = self.generate_answer(request)
        
        return results
    
    def compare_llm_models(self, request: AnswerRequest, llm_providers: List[LLMProvider]) -> Dict[LLMProvider, AnswerResponse]:
        """여러 LLM 모델로 답변 생성 및 비교"""
        results = {}
        
        for provider in llm_providers:
            request.llm_provider = provider
            results[provider] = self.generate_answer(request)
        
        return results
    
    def get_available_companies(self) -> List[str]:
        """사용 가능한 회사 목록 (companies_data.json 기반)"""
        companies = []
        for company in self.companies_data.get("companies", []):
            companies.append(company.get("id", ""))
        return [c for c in companies if c]  # 빈 문자열 제거
    

    def get_persona_summary(self, company_id: str) -> Dict[str, Any]:
        """페르소나 요약 정보 (동적 생성 시스템용)"""
        persona = self.get_persona(company_id)
        if not persona:
            # 동적 생성 시스템에서는 회사 정보만 반환
            company_info = self._get_company_info(company_id)
            return {
                "company": company_id,
                "company_name": company_info.get("name", company_id),
                "available_positions": ["프론트엔드", "백엔드", "기획", "AI", "데이터사이언스"],
                "note": "실시간 LLM 생성 페르소나 사용"
            }
        
        return {
            "name": persona.name,
            "company": company_id,
            "career_years": persona.background.get("career_years", "0"),
            "current_position": persona.background.get("current_position", "지원자"),
            "position": persona.background.get("current_position", "지원자"),  # 호환성을 위해 둘 다 제공
            "main_skills": persona.technical_skills[:5],
            "key_strengths": persona.strengths[:3],
            "interview_style": persona.interview_style,
            "success_factors": getattr(persona, 'success_factors', [])
        }

if __name__ == "__main__":
    # AI 지원자 모델 테스트
    print("🤖 AI 지원자 모델 테스트 - LLM 기반 실시간 페르소나 생성")
    
    # 모델 초기화 (자동으로 .env에서 API 키 로드)
    ai_candidate = AICandidateModel()
    
    # 사용 가능한 회사 확인
    companies = ai_candidate.get_available_companies()
    print(f"\n🏢 사용 가능한 회사: {companies}")
    
    # === 새로운 LLM 기반 페르소나 생성 테스트 ===
    print("\n" + "="*60)
    print("🎯 LLM 기반 실시간 페르소나 생성 테스트")
    print("="*60)
    
    if companies:
        # 네이버 백엔드 개발자 페르소나 생성 테스트
        print("\n🔥 네이버 백엔드 개발자 페르소나 생성 테스트")
        naver_persona = ai_candidate.create_persona_for_interview("네이버", "백엔드")
        
        if naver_persona:
            print(f"\n" + "="*80)
            print(f"🎯 생성된 페르소나 전체 정보")
            print(f"="*80)
            print(f"📛 이름: {naver_persona.name}")
            print(f"📝 요약: {naver_persona.summary}")
            print(f"🏢 이력서 ID: {naver_persona.resume_id}")
            print(f"🤖 생성 모델: {naver_persona.generated_by}")
            
            print(f"\n📋 배경 정보:")
            print(f"  • 경력: {naver_persona.background.get('career_years', '0')}년")
            print(f"  • 현재 직책: {naver_persona.background.get('current_position', '지원자')}")
            print(f"  • 학력: {', '.join(naver_persona.background.get('education', ['정보 없음']))}")
            
            print(f"\n💻 기술 스킬:")
            for i, skill in enumerate(naver_persona.technical_skills, 1):
                print(f"  {i}. {skill}")
            
            print(f"\n🚀 프로젝트 경험:")
            for i, project in enumerate(naver_persona.projects, 1):
                print(f"  {i}. {project.get('name', '프로젝트')}")
                print(f"     설명: {project.get('description', '')}")
                print(f"     기술: {', '.join(project.get('tech_stack', []))}")
                print(f"     역할: {project.get('role', '')}")
                if project.get('achievements'):
                    print(f"     성과: {', '.join(project['achievements'])}")
                if project.get('challenges'):
                    print(f"     어려움: {', '.join(project['challenges'])}")
                print()
            
            print(f"💼 업무 경험:")
            for i, exp in enumerate(naver_persona.experiences, 1):
                print(f"  {i}. {exp.get('company', '회사')}")
                print(f"     직책: {exp.get('position', '개발자')}")
                print(f"     기간: {exp.get('period', '기간')}")
                if exp.get('achievements'):
                    print(f"     성과: {', '.join(exp['achievements'])}")
                print()
            
            print(f"💪 강점:")
            for i, strength in enumerate(naver_persona.strengths, 1):
                print(f"  {i}. {strength}")
            
            print(f"\n🤔 약점 (개선점):")
            for i, weakness in enumerate(naver_persona.weaknesses, 1):
                print(f"  {i}. {weakness}")
            
            print(f"\n❤️ 개인적 동기:")
            print(f"  {naver_persona.motivation}")
            
            print(f"\n🎯 커리어 목표:")
            print(f"  {naver_persona.career_goal}")
            
            print(f"\n🧠 개인적 교훈/경험:")
            for i, exp in enumerate(naver_persona.inferred_personal_experiences, 1):
                print(f"  {i}. [{exp.get('category', '경험')}] {exp.get('experience', '')}")
                print(f"     교훈: {exp.get('lesson', '')}")
                print()
            
            print(f"🎭 성격 특성:")
            print(f"  {', '.join(naver_persona.personality_traits)}")
            
            print(f"\n🗣️ 면접 스타일:")
            print(f"  {naver_persona.interview_style}")
            
            print(f"="*80)
            
            # 임시로 페르소나를 캐시에 저장 (기존 코드 호환성을 위해)
            ai_candidate.candidate_personas["naver"] = naver_persona
            
            # 생성된 페르소나로 답변 생성 테스트
            print(f"\n📝 생성된 페르소나로 답변 생성 테스트:")
            test_request = AnswerRequest(
                question_content="간단한 자기소개를 해주세요.",
                question_type=QuestionType.INTRO,
                question_intent="지원자의 기본 배경과 역량 파악",
                company_id="naver",
                position="백엔드 개발자",
                quality_level=QualityLevel(8),
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            response = ai_candidate.generate_answer(test_request)
            
            print(f"페르소나: {response.persona_name}")
            print(f"품질 레벨: {response.quality_level.value}점")
            print(f"신뢰도: {response.confidence_score}")
            print(f"응답 시간: {response.response_time:.2f}초")
            print(f"답변: {response.answer_content[:300]}...")
            
            if response.error:
                print(f"오류: {response.error}")
        else:
            print("❌ 페르소나 생성 실패")
    
    # 페르소나 요약 정보 확인 (동적 생성 시스템)
    print(f"\n📊 회사별 정보 확인:")
    for company in companies[:3]:
        summary = ai_candidate.get_persona_summary(company)
        print(f"\n👤 {company}:")
        if summary.get('note'):
            print(f"  타입: {summary.get('note')}")
            print(f"  회사명: {summary.get('company_name')}")
            print(f"  지원 가능 직군: {', '.join(summary.get('available_positions', []))}")
        else:
            print(f"  이름: {summary.get('name', 'N/A')}")
            print(f"  경력: {summary.get('career_years', 'N/A')}년")
    
    print("\n🎉 테스트 완료! LLM 기반 페르소나 생성 시스템이 성공적으로 구현되었습니다.")