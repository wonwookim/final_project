#!/usr/bin/env python3
"""
개인화된 면접 시스템
사용자 프로필을 기반으로 맞춤형 질문을 생성하는 시스템
코드 정리 및 구조 개선 버전
"""

import json
import random
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import openai
from datetime import datetime
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

from ..shared.models import QuestionType, QuestionAnswer
from ..session.models import InterviewSession
from .document_processor import DocumentProcessor, UserProfile
from ..shared.constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE, QUESTION_SECTIONS
from ..shared.utils import parse_career_years, get_difficulty_level, safe_json_load, extract_question_and_intent
from .prompt_templates import InterviewPromptTemplates
from .conversation_context import ConversationContext
# 🔄 FinalInterviewSystem 대신 SessionManager 사용
from ..session import SessionManager

class PersonalizedInterviewSession(InterviewSession):
    """개인화된 면접 세션"""
    
    def __init__(self, company_id: str, position: str, candidate_name: str, user_profile: UserProfile):
        super().__init__(company_id, position, candidate_name)
        self.user_profile = user_profile
        
        # 대화 컨텍스트 관리자 초기화
        self.conversation_context = ConversationContext(
            company_id=company_id,
            position=position,
            persona_name=candidate_name
        )
        
        # 개인화된 질문 계획 (사용자 배경에 따라 동적 조정)
        self.question_plan = self._create_personalized_plan()
    
    def add_qa_pair(self, qa_pair: QuestionAnswer):
        """질문-답변 쌍 추가 (컨텍스트 추적 포함)"""
        super().add_qa_pair(qa_pair)
        
        # 대화 컨텍스트에 질문-답변 추가
        if hasattr(self, 'conversation_context'):
            self.conversation_context.add_question_answer(
                qa_pair.question_content,
                qa_pair.answer_content,
                qa_pair.question_type
            )
    
    def _create_personalized_plan(self) -> List[Dict[str, Any]]:
        """사용자 프로필에 따른 개인화된 질문 계획"""
        
        # 기본 질문 (모든 면접자 공통)
        base_plan = [
            {"type": QuestionType.INTRO, "focus": "self_introduction", "personalized": False, "fixed": True},
            {"type": QuestionType.MOTIVATION, "focus": "application_reason", "personalized": False, "fixed": True}
        ]
        
        # 경력 년수 파싱 (유틸리티 함수 사용)
        career_years_str = self.user_profile.background.get("career_years", "0")
        career_years = parse_career_years(career_years_str)
        
        # 기술 스킬과 프로젝트 수 계산
        tech_skills_count = len(self.user_profile.technical_skills)
        projects_count = len(self.user_profile.projects)
        
        if career_years >= 3:  # 경력자 (총 18개 질문)
            additional_questions = [
                # 인사 영역 (2개 고정 + 2개 생성) - 순수 인성 중심
                {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "growth_mindset", "personalized": True, "fixed": False},
                {"type": QuestionType.HR, "focus": "leadership_style", "personalized": True, "fixed": False},
                
                # 기술 영역 (2개 고정 + 3개 생성) - 순수 기술 중심
                {"type": QuestionType.TECH, "focus": "expertise", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "architecture", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "problem_solving", "personalized": True, "fixed": False},
                {"type": QuestionType.TECH, "focus": "innovation", "personalized": True, "fixed": False},
                {"type": QuestionType.TECH, "focus": "learning", "personalized": True, "fixed": False},
                
                # 협업 영역 (1개 고정 + 2개 생성) - 순수 협업 중심
                {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
                {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": True, "fixed": False},
                {"type": QuestionType.COLLABORATION, "focus": "conflict_resolution", "personalized": True, "fixed": False},
                
                # 심화 질문 (3개 생성)
                {"type": QuestionType.FOLLOWUP, "focus": "career", "personalized": True, "fixed": False},
                {"type": QuestionType.FOLLOWUP, "focus": "future_goals", "personalized": True, "fixed": False},
                {"type": QuestionType.FOLLOWUP, "focus": "company_contribution", "personalized": True, "fixed": False}
            ]
        elif career_years >= 1:  # 주니어 (총 16개 질문)
            additional_questions = [
                # 인사 영역 (2개 고정 + 2개 생성) - 순수 인성 중심
                {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "growth", "personalized": True, "fixed": False},
                {"type": QuestionType.HR, "focus": "adaptability", "personalized": True, "fixed": False},
                
                # 기술 영역 (2개 고정 + 3개 생성) - 순수 기술 중심
                {"type": QuestionType.TECH, "focus": "skills", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "recent_learning", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "problem_solving", "personalized": True, "fixed": False},
                {"type": QuestionType.TECH, "focus": "technical_depth", "personalized": True, "fixed": False},
                {"type": QuestionType.TECH, "focus": "learning_ability", "personalized": True, "fixed": False},
                
                # 협업 영역 (2개 고정 + 2개 생성) - 순수 협업 중심
                {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
                {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": False, "fixed": True, "section": "collaboration"},
                {"type": QuestionType.COLLABORATION, "focus": "team_contribution", "personalized": True, "fixed": False},
                {"type": QuestionType.COLLABORATION, "focus": "peer_learning", "personalized": True, "fixed": False},
                
                # 심화 질문 (1개 생성)
                {"type": QuestionType.FOLLOWUP, "focus": "career_growth", "personalized": True, "fixed": False}
            ]
        else:  # 신입 (총 13개 질문)
            additional_questions = [
                # 인사 영역 (2개 고정 + 2개 생성) - 순수 인성 중심
                {"type": QuestionType.HR, "focus": "personality", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "values", "personalized": False, "fixed": True, "section": "hr"},
                {"type": QuestionType.HR, "focus": "potential", "personalized": True, "fixed": False},
                {"type": QuestionType.HR, "focus": "enthusiasm", "personalized": True, "fixed": False},
                
                # 기술 영역 (2개 고정 + 2개 생성) - 순수 기술 중심
                {"type": QuestionType.TECH, "focus": "fundamentals", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "learning", "personalized": False, "fixed": True, "section": "technical"},
                {"type": QuestionType.TECH, "focus": "project_experience", "personalized": True, "fixed": False},
                {"type": QuestionType.TECH, "focus": "passion", "personalized": True, "fixed": False},
                
                # 협업 영역 (1개 고정 + 2개 생성) - 순수 협업 중심
                {"type": QuestionType.COLLABORATION, "focus": "teamwork", "personalized": False, "fixed": True, "section": "collaboration"},
                {"type": QuestionType.COLLABORATION, "focus": "communication", "personalized": True, "fixed": False},
                {"type": QuestionType.COLLABORATION, "focus": "willingness_to_learn", "personalized": True, "fixed": False},
                
                # 심화 질문 (1개 생성)
                {"type": QuestionType.FOLLOWUP, "focus": "growth_mindset", "personalized": True, "fixed": False}
            ]
        
        return base_plan + additional_questions

class PersonalizedInterviewSystem(SessionManager):
    """개인화된 면접 시스템"""
    
    def __init__(self, api_key: str = None, companies_data_path: str = "llm/shared/data/companies_data.json"):
        super().__init__(api_key, companies_data_path)
        self.document_processor = DocumentProcessor(api_key or os.getenv('OPENAI_API_KEY'))
        self.fixed_questions = self._load_fixed_questions()
        self.question_cache = {}  # 질문 캐시 추가
        
        # 새로운 회사 데이터 로더 사용
        from ..shared.company_data_loader import get_company_loader
        self.company_loader = get_company_loader()
    
    def _load_fixed_questions(self) -> Dict[str, List[Dict]]:
        """고정 질문 데이터 로드"""
        default_structure = {
            "hr_questions": [], 
            "technical_questions": [], 
            "collaboration_questions": []
        }
        return safe_json_load("llm/interviewer/data/fixed_questions.json", default_structure)
    
    def _get_fixed_question(self, section: str, difficulty_level: int = None) -> Optional[Dict]:
        """섹션별 고정 질문 캐시된 선택"""
        cache_key = f"{section}_{difficulty_level or 'all'}"
        
        # 캐시에서 먼저 확인
        if cache_key in self.question_cache:
            return self.question_cache[cache_key]
            
        questions = self.fixed_questions.get(QUESTION_SECTIONS.get(section, ""), [])
        if not questions:
            return None
            
        # 난이도별 필터링 (선택사항)
        if difficulty_level:
            filtered_questions = [q for q in questions if q.get("level", 1) == difficulty_level]
            questions = filtered_questions if filtered_questions else questions
        
        selected_question = random.choice(questions) if questions else None
        
        # 캐시에 저장 (간단한 캐싱)
        if selected_question:
            self.question_cache[cache_key] = selected_question
            
        return selected_question
    
    def _build_previous_answers_context(self, session: PersonalizedInterviewSession) -> str:
        """이전 답변에서 참고할 만한 내용 추출"""
        if not session.conversation_history:
            return ""
        
        context_parts = []
        for i, qa in enumerate(session.conversation_history[-3:]):  # 최근 3개 답변만
            if qa.answer_content and len(qa.answer_content.strip()) > 20:  # 의미있는 답변만
                context_parts.append(f"- {qa.question_content[:50]}... → {qa.answer_content[:100]}...")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def start_personalized_interview(self, company_id: str, position: str, candidate_name: str, 
                                   user_profile: UserProfile) -> str:
        """개인화된 면접 시작"""
        
        company_data = self.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        session = PersonalizedInterviewSession(company_id, position, candidate_name, user_profile)
        self.sessions[session.session_id] = session
        
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[PersonalizedInterviewSession]:
        """세션 가져오기"""
        return self.sessions.get(session_id)
    
    def get_current_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """현재 질문 가져오기"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # 현재 질문이 있으면 반환
        if session.conversation_history:
            last_qa = session.conversation_history[-1]
            return {
                "question_id": f"q_{len(session.conversation_history)}",
                "question_type": "current",
                "question_content": last_qa.question_content,
                "question_intent": last_qa.question_intent or "현재 질문",
                "progress": f"{len(session.conversation_history)}/{len(session.question_plan)}",
                "personalized": True
            }
        
        # 현재 질문이 없으면 첫 번째 질문 생성
        return self.get_next_question(session_id)
    
    def _generate_personalized_question(self, session: PersonalizedInterviewSession, 
                                      company_data: Dict[str, Any], question_plan: Dict[str, Any]) -> Tuple[str, str]:
        """개인화된 질문 생성"""
        
        question_type = question_plan["type"]
        focus = question_plan.get("focus", "general")
        is_fixed = question_plan.get("fixed", False)
        section = question_plan.get("section", "")
        
        # 기본 질문 처리 (INTRO, MOTIVATION)
        if question_type == QuestionType.INTRO:
            return (
                f"{session.candidate_name}님, 자기소개를 부탁드립니다.",
                "지원자의 기본 정보와 성격, 역량을 파악"
            )
        elif question_type == QuestionType.MOTIVATION:
            return (
                f"저희 {company_data['name']}에 지원하신 동기를 말씀해 주세요.",
                "회사에 대한 관심도와 지원 동기 파악"
            )
        
        # 고정 질문 데이터에서 선택
        if is_fixed and section:
            career_years_str = session.user_profile.background.get("career_years", "0")
            career_years = parse_career_years(career_years_str)
            difficulty_level = get_difficulty_level(career_years)
            
            fixed_question = self._get_fixed_question(section, difficulty_level)
            if fixed_question:
                return (
                    fixed_question["content"],
                    fixed_question["intent"]
                )
        
        # 개인화된 질문 생성
        print(f"🎯 개인화 질문 생성 시작 - {question_type.value}, focus: {focus}")
        context = self._build_personalized_context(session, company_data)
        
        # 고정 질문 답변 참고를 위한 컨텍스트 추가
        previous_answers_context = self._build_previous_answers_context(session)
        if previous_answers_context:
            context += f"\n\n이전 답변 참고사항:\n{previous_answers_context}"
        
        prompt = self._create_personalized_prompt(question_type, focus, context, session.candidate_name)
        print(f"📝 LLM 프롬프트 생성 완료 - 길이: {len(prompt)} 글자")
        
        try:
            print(f"🤖 OpenAI API 호출 중...")
            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": InterviewPromptTemplates.get_system_prompt(company_data['name'])},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ OpenAI 응답 받음: {result[:100]}...")
            
            # 제어 문자와 특수 문자 정리
            import re
            result = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', result)  # 제어 문자 제거
            result = re.sub(r'\*\*', '', result)  # 마크다운 제거
            result = re.sub(r'^\d+\.\s*', '', result)  # 번호 제거
            result = re.sub(r'\n+', ' ', result)  # 개행 문자를 공백으로 변환
            
            final_result = extract_question_and_intent(result)
            print(f"🎯 최종 질문: {final_result[0]}")
            return final_result
            
        except Exception as e:
            print(f"개인화 질문 생성 중 오류: {e}")
            return self._get_fallback_personalized_question(question_type, focus, session.candidate_name)
    
    def _build_personalized_context(self, session: PersonalizedInterviewSession, company_data: Dict[str, Any]) -> str:
        """개인화된 컨텍스트 구성 - 7개 회사 상세 정보 활용"""
        
        profile = session.user_profile
        
        # 회사별 상세 정보 추출
        company_name = company_data.get('name', '회사')
        company_id = company_data.get('id', 'unknown')
        talent_profile = company_data.get('talent_profile', '')
        core_competencies = company_data.get('core_competencies', [])
        tech_focus = company_data.get('tech_focus', [])
        interview_keywords = company_data.get('interview_keywords', [])
        company_culture = company_data.get('company_culture', {})
        technical_challenges = company_data.get('technical_challenges', [])
        interviewer_personas = company_data.get('interviewer_personas', {})
        
        # UserProfile 객체인지 확인하고 안전하게 처리
        if hasattr(profile, 'background'):
            # 정상적인 UserProfile 객체
            context = f"""
=== 🏢 {company_name} 채용 컨텍스트 ===
• 인재상: {talent_profile}
• 핵심 역량: {', '.join(core_competencies[:3])}
• 기술 포커스: {', '.join(tech_focus[:4])}
• 면접 키워드: {', '.join(interview_keywords[:5])}

=== 🎯 회사 문화 및 가치관 ===
• 업무 스타일: {company_culture.get('work_style', '협업 중심')}
• 의사결정 방식: {company_culture.get('decision_making', '데이터 기반')}
• 핵심 가치: {', '.join(company_culture.get('core_values', [])[:3])}

=== 🔧 기술적 도전과제 ===
"""
            for i, challenge in enumerate(technical_challenges[:3], 1):
                context += f"{i}. {challenge}\n"
            
            context += f"""
=== 👤 지원자 프로필 ===
이름: {profile.name}
경력: {profile.background.get('career_years', '0')}년
현재 직책: {profile.background.get('current_position', '신입')}
주요 기술: {', '.join(profile.technical_skills[:5]) if profile.technical_skills else '없음'}

=== 📋 주요 프로젝트 ===
"""
            for i, project in enumerate(profile.projects[:3], 1):
                context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
                context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            
            context += f"""
=== ⭐ 강점 및 특징 ===
주요 강점: {', '.join(profile.strengths[:3]) if profile.strengths else '없음'}
차별화 포인트: {', '.join(profile.unique_points[:2]) if profile.unique_points else '없음'}
커리어 목표: {profile.career_goal}

=== 🎤 면접관 페르소나 정보 ===
"""
            for persona_type, persona_info in list(interviewer_personas.items())[:2]:
                context += f"• {persona_info.get('name', persona_type)}: {persona_info.get('role', '')}\n"
                context += f"  특징: {persona_info.get('personality', '')}\n"
        else:
            # dict 형태 또는 기타 형태인 경우 - 회사 정보 우선 활용
            print(f"⚠️ profile이 UserProfile 객체가 아닙니다: {type(profile)}")
            profile_dict = profile if isinstance(profile, dict) else {
                'name': '지원자',
                'background': {'career_years': '0', 'current_position': '신입'},
                'technical_skills': [],
                'projects': [],
                'strengths': [],
                'unique_points': [],
                'career_goal': '성장'
            }
            
            context = f"""
=== 🏢 {company_name} 채용 컨텍스트 ===
• 인재상: {talent_profile}
• 핵심 역량: {', '.join(core_competencies[:3])}
• 기술 포커스: {', '.join(tech_focus[:4])}
• 면접 키워드: {', '.join(interview_keywords[:5])}

=== 🎯 회사 문화 및 가치관 ===
• 업무 스타일: {company_culture.get('work_style', '협업 중심')}
• 의사결정 방식: {company_culture.get('decision_making', '데이터 기반')}
• 핵심 가치: {', '.join(company_culture.get('core_values', [])[:3])}

=== 👤 지원자 프로필 ===
이름: {profile_dict.get('name', '지원자')}
경력: {profile_dict.get('background', {}).get('career_years', '0')}년
현재 직책: {profile_dict.get('background', {}).get('current_position', '신입')}
주요 기술: {', '.join(profile_dict.get('technical_skills', [])[:5]) if profile_dict.get('technical_skills') else '없음'}

=== 📋 주요 프로젝트 ===
"""
            projects = profile_dict.get('projects', [])
            for i, project in enumerate(projects[:3], 1):
                context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
                context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            
            context += f"""
=== ⭐ 강점 및 특징 ===
주요 강점: {', '.join(profile_dict.get('strengths', [])[:3]) if profile_dict.get('strengths') else '없음'}
차별화 포인트: {', '.join(profile_dict.get('unique_points', [])[:2]) if profile_dict.get('unique_points') else '없음'}
커리어 목표: {profile_dict.get('career_goal', '성장')}
"""
        
        # 이전 대화 요약 추가
        if session.conversation_history:
            context += f"""

=== 💬 이전 대화 요약 ===
"""
            for i, qa in enumerate(session.conversation_history[-3:], 1):  # 최근 3개만
                context += f"{i}. [{qa.question_type.value}] {qa.question_content[:50]}...\n"
                context += f"   답변: {qa.answer_content[:100]}...\n"
        
        return context
    
    def _create_personalized_prompt(self, question_type: QuestionType, focus: str, context: str, candidate_name: str) -> str:
        """개인화된 프롬프트 생성"""
        
        prompts = {
            QuestionType.MOTIVATION: f"""
{context}

위 지원자의 배경과 {candidate_name}님의 커리어 목표를 고려하여, 
{candidate_name}님이 이 회사에 지원한 구체적인 동기를 묻는 맞춤형 질문을 만들어주세요.

지원자의 경험과 목표가 회사의 비전과 어떻게 연결되는지 탐색할 수 있는 질문이어야 합니다.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
""",
            
            QuestionType.HR: f"""
{context}

위 지원자의 배경을 고려하여 **인성 영역({focus})**을 평가하는 맞춤형 질문을 만들어주세요.

**인성 질문 기준:**
- 성격, 가치관, 인생관, 태도
- 스트레스 대처 방식, 갈등 해결 방식  
- 개인적 성장, 자기계발, 목표 설정
- 도덕적 판단, 책임감, 성실성

**협업이나 기술과 관련된 내용은 제외**하고 순수하게 지원자의 인성을 알아볼 수 있는 질문을 만드세요.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
""",
            
            QuestionType.TECH: f"""
{context}

위 지원자의 기술 스택과 프로젝트 경험을 고려하여 **기술 영역({focus})**을 평가하는 맞춤형 질문을 만들어주세요.

**기술 질문 기준:**
- 프로그래밍 언어, 프레임워크, 도구 사용 경험
- 프로젝트 구현, 아키텍처 설계, 성능 최적화
- 기술적 문제 해결, 디버깅, 트러블슈팅
- 새로운 기술 학습, 기술 트렌드 이해

**인성이나 협업과 관련된 내용은 제외**하고 순수하게 기술적 역량을 평가할 수 있는 질문을 만드세요.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
""",
            
            QuestionType.COLLABORATION: f"""
{context}

위 지원자의 경력과 프로젝트 경험을 고려하여 **협업 영역({focus})**을 평가하는 맞춤형 질문을 만들어주세요.

**협업 질문 기준:**
- 팀워크, 팀 내 역할 수행, 팀원과의 소통
- 갈등 상황 해결, 의견 조율, 합의 도출
- 리더십, 팔로워십, 멘토링
- 크로스 팀 협업, 이해관계자 소통

**개인적 인성이나 순수 기술과 관련된 내용은 제외**하고 순수하게 협업 능력을 평가할 수 있는 질문을 만드세요.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
""",
            
            QuestionType.FOLLOWUP: f"""
{context}

위 지원자의 답변과 배경을 바탕으로 {focus} 관련 심화 질문을 만들어주세요.

지원자의 가장 인상적인 경험이나 강점을 더 깊이 탐구할 수 있는 질문이어야 합니다.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""
        }
        
        return prompts.get(question_type, f"""
{context}

위 지원자의 배경을 고려하여 {question_type.value} 영역을 평가하는 맞춤형 질문을 만들어주세요.

간결하고 자연스러운 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
""")
    
    def _get_fallback_personalized_question(self, question_type: QuestionType, focus: str, candidate_name: str) -> Tuple[str, str]:
        """개인화 실패 시 대체 질문"""
        
        fallback_questions = {
            (QuestionType.HR, "growth"): (
                f"{candidate_name}님의 성장 과정에서 가장 큰 변화나 깨달음이 있었던 경험을 말씀해 주세요.",
                "개인적 성장과 학습 능력 평가"
            ),
            (QuestionType.TECH, "problem_solving"): (
                f"{candidate_name}님이 기술적으로 가장 어려웠던 문제를 어떻게 해결하셨나요?",
                "문제 해결 능력과 기술적 사고력 평가"
            ),
            (QuestionType.COLLABORATION, "teamwork"): (
                f"{candidate_name}님의 팀 프로젝트에서 갈등이 있었을 때 어떻게 해결하셨나요?",
                "협업 능력과 갈등 해결 능력 평가"
            )
        }
        
        key = (question_type, focus)
        if key in fallback_questions:
            return fallback_questions[key]
        
        return (
            f"{candidate_name}님의 경험에 대해 더 자세히 말씀해 주세요.",
            f"{question_type.value} 영역 기본 평가"
        )
    
    def _generate_personalized_question_with_duplicate_check(self, session: PersonalizedInterviewSession, 
                                                           company_data: Dict[str, Any], 
                                                           question_plan: Dict[str, Any]) -> Tuple[str, str]:
        """중복 방지가 강화된 개인화 질문 생성"""
        
        # 기존 질문 생성 로직 사용
        question_content, question_intent = self._generate_personalized_question(
            session, company_data, question_plan
        )
        
        # 컨텍스트 기반 추가 다양성 적용
        if hasattr(session, 'conversation_context'):
            # 덜 탐색된 주제 우선 활용
            underexplored_topics = session.conversation_context.get_underexplored_topics()
            focus_suggestions = session.conversation_context.suggest_next_question_focus()
            
            if underexplored_topics and focus_suggestions.get('suggested_new_angles'):
                # 새로운 각도로 질문 재생성
                additional_context = f"새로운 접근 방향: {', '.join(focus_suggestions['suggested_new_angles'][:2])}"
                question_content = self._enhance_question_with_context(
                    question_content, additional_context, session
                )
        
        return question_content, question_intent
    
    def _generate_alternative_question(self, session: PersonalizedInterviewSession, 
                                     question_plan: Dict[str, Any]) -> Tuple[str, str]:
        """대안 질문 생성 (중복 발생 시)"""
        
        if not hasattr(session, 'conversation_context'):
            return self._generate_fallback_question(session, question_plan)
        
        # 컨텍스트 기반 대안 질문 생성
        focus_suggestions = session.conversation_context.suggest_next_question_focus()
        underexplored_topics = session.conversation_context.get_underexplored_topics()
        
        if underexplored_topics:
            # 덜 탐색된 주제로 대안 질문 생성
            topic = underexplored_topics[0]
            question_content = self._create_topic_specific_question(topic, session, question_plan)
            question_intent = f"{topic.value} 영역 심화 탐색"
        else:
            # 기존 정보를 바탕으로 심화 질문 생성
            question_content = self._create_deepdive_question(session, question_plan)
            question_intent = f"{question_plan['type'].value} 영역 심화 질문"
        
        return question_content, question_intent
    
    def _enhance_question_with_context(self, base_question: str, additional_context: str, 
                                     session: PersonalizedInterviewSession) -> str:
        """컨텍스트를 활용한 질문 향상"""
        
        try:
            prompt = f"""
기본 질문: {base_question}
추가 컨텍스트: {additional_context}
지원자 배경: {session.user_profile.background}

위 정보를 바탕으로 기본 질문을 더 구체적이고 차별화된 질문으로 개선해주세요.
기존 질문의 의도는 유지하되, 새로운 관점이나 구체적인 상황을 추가하여 더 풍부한 답변을 이끌어낼 수 있도록 해주세요.

개선된 질문:"""

            # 환경변수에서 API 키 가져오기
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("⚠️ OpenAI API 키가 설정되지 않았습니다.")
                return base_question
                
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.8
            )
            
            enhanced_question = response.choices[0].message.content.strip()
            return enhanced_question if enhanced_question else base_question
            
        except Exception as e:
            print(f"⚠️ 질문 향상 중 오류: {e}")
            return base_question
    
    def _create_topic_specific_question(self, topic, session: PersonalizedInterviewSession, 
                                      question_plan: Dict[str, Any]) -> str:
        """특정 주제에 대한 질문 생성 (HR vs 협업 명확히 구분)"""
        
        # HR 전용 질문 (개인 인성, 가치관, 성장)
        hr_questions = {
            "개인 배경": [
                "본인을 한 문장으로 표현한다면 어떻게 말씀하시겠어요?",
                "인생에서 가장 소중하게 생각하는 가치관이 무엇인가요?",
                "지금의 본인을 만든 가장 중요한 경험이나 사건이 있다면 무엇인가요?",
                "어려운 상황에서 본인을 지탱해주는 힘은 무엇인가요?"
            ],
            "학습 능력": [
                "새로운 것을 배울 때 본인만의 방식이나 습관이 있나요?",
                "실패나 좌절을 경험했을 때 어떻게 극복하시나요?",
                "최근에 개인적으로 도전해본 새로운 일이 있다면 무엇인가요?",
                "본인의 성장에 가장 큰 영향을 준 사람이나 경험은 무엇인가요?"
            ],
            "커리어 목표": [
                "5년 후 본인의 모습을 어떻게 그리고 계신가요?",
                "본인이 추구하는 이상적인 일의 의미는 무엇인가요?",
                "개인적인 성취감을 느끼는 순간은 언제인가요?",
                "본인의 롤모델이나 존경하는 인물이 있다면 그 이유는 무엇인가요?"
            ]
        }
        
        # 협업 전용 질문 (팀워크, 소통, 리더십)
        collaboration_questions = {
            "팀 협업": [
                "팀에서 의견 충돌이 있을 때 어떻게 해결하시나요?",
                "팀 프로젝트에서 본인이 주로 맡게 되는 역할은 무엇인가요?",
                "어려운 팀원과 함께 일해야 할 때 어떤 방식으로 접근하시나요?",
                "팀의 분위기나 효율성을 높이기 위해 어떤 노력을 하시나요?"
            ],
            "소통 능력": [
                "복잡한 기술적 내용을 비전문가에게 설명할 때 어떤 방식을 사용하시나요?",
                "다른 사람과 의견이 다를 때 어떻게 소통하시나요?",
                "팀 회의에서 본인의 의견을 어떻게 표현하고 전달하시나요?",
                "상대방의 이야기를 듣고 이해하는 본인만의 방법이 있나요?"
            ],
            "리더십": [
                "팀을 이끌어본 경험이 있다면 어떤 리더십 스타일을 추구하시나요?",
                "후배나 동료에게 도움을 줄 때 어떤 방식으로 접근하시나요?",
                "갈등 상황에서 중재자 역할을 해본 경험이 있나요?",
                "팀의 목표를 달성하기 위해 어떻게 동기부여를 하시나요?"
            ]
        }
        
        # 기타 주제
        other_questions = {
            "기술 역량": [
                "최근에 새로 학습한 기술이나 도구가 있다면 어떤 계기로 시작하게 되었나요?",
                "기술적으로 가장 도전적이었던 문제를 어떻게 해결하셨나요?",
                "현재 업계 트렌드 중에서 가장 주목하고 있는 기술은 무엇인가요?"
            ],
            "프로젝트 경험": [
                "프로젝트 진행 중 예상치 못한 변수가 생겼을 때 어떻게 대처하셨나요?",
                "가장 기억에 남는 프로젝트와 그 이유를 말씀해주세요.",
                "실패했던 프로젝트가 있다면, 그 경험에서 얻은 교훈은 무엇인가요?"
            ]
        }
        
        # 질문 타입에 따라 적절한 질문 풀 선택
        question_type = question_plan.get("type", QuestionType.GENERAL)
        
        if question_type == QuestionType.HR:
            questions = hr_questions.get(topic.value, hr_questions.get("개인 배경", []))
        elif question_type == QuestionType.COLLABORATION:
            questions = collaboration_questions.get(topic.value, collaboration_questions.get("팀 협업", []))
        else:
            questions = other_questions.get(topic.value, ["본인의 경험에 대해 자세히 말씀해주세요."])
        
        if not questions:
            questions = ["본인의 경험에 대해 자세히 말씀해주세요."]
        
        return random.choice(questions)
    
    def _create_deepdive_question(self, session: PersonalizedInterviewSession, 
                                question_plan: Dict[str, Any]) -> str:
        """기존 정보 기반 심화 질문 생성"""
        
        # 기존 답변에서 언급된 키워드 활용
        if hasattr(session, 'conversation_context'):
            memory = session.conversation_context.memory
            
            if memory.mentioned_projects:
                project = list(memory.mentioned_projects)[0]
                return f"{project}에서 가장 기억에 남는 기술적 도전과 해결 과정을 구체적으로 설명해주세요."
            
            if memory.mentioned_technologies:
                tech = list(memory.mentioned_technologies)[0]
                return f"{tech} 기술을 선택한 이유와 실제 사용 경험에서의 장단점을 말씀해주세요."
        
        # 기본 심화 질문
        return "지금까지 말씀해주신 경험 중에서 가장 자랑스러운 성과와 그 과정을 자세히 설명해주세요."
    
    def _generate_fallback_question(self, session: PersonalizedInterviewSession, 
                                  question_plan: Dict[str, Any]) -> Tuple[str, str]:
        """기본 대체 질문 (컨텍스트 없을 때)"""
        
        fallback_questions = {
            QuestionType.HR: ("본인의 강점 중 하나를 구체적인 사례와 함께 설명해주세요.", "HR 역량 평가"),
            QuestionType.TECH: ("가장 자신 있는 기술 스택과 그 이유를 말씀해주세요.", "기술 역량 평가"),
            QuestionType.COLLABORATION: ("팀워크에서 중요하다고 생각하는 요소는 무엇인가요?", "협업 능력 평가"),
            QuestionType.FOLLOWUP: ("지금까지의 답변 중 더 자세히 설명하고 싶은 부분이 있나요?", "심화 질문")
        }
        
        return fallback_questions.get(
            question_plan["type"], 
            ("본인에 대해 더 자세히 말씀해주세요.", "일반 질문")
        )
    
    def generate_organic_followup(self, session: PersonalizedInterviewSession, 
                                last_answer: str) -> Optional[Dict[str, Any]]:
        """유기적 후속 질문 생성 (자연스러운 대화 흐름)"""
        
        if not hasattr(session, 'conversation_context'):
            return None
        
        context = session.conversation_context
        memory = context.memory
        
        # 마지막 답변에서 흥미로운 포인트 추출
        interesting_points = self._extract_interesting_points(last_answer)
        
        if not interesting_points:
            return None
        
        # 가장 유기적인 후속 질문 생성
        followup_question = self._create_organic_followup(
            interesting_points, session, context
        )
        
        return {
            "question_id": f"followup_{session.current_question_count + 1}",
            "question_type": "유기적 후속",
            "question_content": followup_question,
            "question_intent": "자연스러운 대화 심화",
            "is_organic": True,
            "based_on": interesting_points[:2]  # 기반이 된 포인트들
        }
    
    def _extract_interesting_points(self, answer: str) -> List[str]:
        """답변에서 흥미로운 포인트 추출"""
        
        interesting_points = []
        answer_lower = answer.lower()
        
        # 구체적인 수치나 성과 언급
        import re
        numbers = re.findall(r'(\d+(?:[%배개명건초분년월]|시간|명|개|배|프로젝트))', answer)
        for num in numbers:
            interesting_points.append(f"구체적 성과: {num}")
        
        # 기술이나 도구 언급
        tech_keywords = ["python", "java", "react", "spring", "docker", "aws", "mysql", "redis"]
        mentioned_tech = [tech for tech in tech_keywords if tech in answer_lower]
        for tech in mentioned_tech:
            interesting_points.append(f"기술 언급: {tech}")
        
        # 감정이나 느낌 표현
        emotion_keywords = ["어려웠", "힘들었", "흥미로웠", "재미있었", "보람", "성취감", "아쉬웠"]
        mentioned_emotions = [emotion for emotion in emotion_keywords if emotion in answer]
        for emotion in mentioned_emotions:
            interesting_points.append(f"감정 표현: {emotion}")
        
        # 프로젝트나 경험 언급
        if "프로젝트" in answer or "경험" in answer:
            interesting_points.append("프로젝트/경험 언급")
        
        # 문제나 해결 언급
        if any(word in answer for word in ["문제", "해결", "개선", "최적화"]):
            interesting_points.append("문제해결 언급")
        
        return interesting_points[:3]  # 최대 3개
    
    def _create_organic_followup(self, interesting_points: List[str], 
                               session: PersonalizedInterviewSession,
                               context) -> str:
        """유기적인 후속 질문 생성"""
        
        # 가장 흥미로운 포인트 선택
        primary_point = interesting_points[0] if interesting_points else None
        
        if not primary_point:
            return "그 경험에 대해 조금 더 자세히 들려주시겠어요?"
        
        # 포인트 유형별 후속 질문 패턴
        if "구체적 성과" in primary_point:
            return f"방금 말씀하신 {primary_point.split(': ')[1]}이라는 성과가 인상적이네요. 그 성과를 달성하기까지 어떤 과정이 있었는지 더 자세히 설명해주시겠어요?"
        
        elif "기술 언급" in primary_point:
            tech_name = primary_point.split(': ')[1]
            return f"{tech_name}를 언급해주셨는데, 실제로 사용해보시면서 어떤 점이 가장 인상적이었나요?"
        
        elif "감정 표현" in primary_point:
            emotion = primary_point.split(': ')[1]
            if emotion in ["어려웠", "힘들었"]:
                return "그런 어려움을 어떻게 극복하셨는지 궁금하네요. 당시 상황을 좀 더 구체적으로 설명해주실 수 있나요?"
            elif emotion in ["흥미로웠", "재미있었", "보람"]:
                return f"그 {emotion}다고 하신 부분에 대해 더 들어보고 싶어요. 어떤 점이 특히 그랬나요?"
        
        elif "프로젝트/경험 언급" in primary_point:
            return "그 프로젝트에서 본인이 맡으신 역할과 기여한 부분을 좀 더 구체적으로 설명해주시겠어요?"
        
        elif "문제해결 언급" in primary_point:
            return "문제 해결 과정이 흥미롭네요. 그때 어떤 접근 방식을 사용하셨고, 다른 대안도 고려해보셨나요?"
        
        # 기본 후속 질문
        return "그 부분에 대해 좀 더 자세한 이야기를 들려주실 수 있나요?"
    
    def enhance_conversation_naturalness(self, session: PersonalizedInterviewSession) -> Dict[str, Any]:
        """대화의 자연스러움 향상을 위한 메타 정보 제공"""
        
        if not hasattr(session, 'conversation_context'):
            return {}
        
        context = session.conversation_context
        summary = context.get_conversation_summary()
        
        return {
            "conversation_depth": len(context.question_history),
            "topic_coverage": summary['topic_coverage'],
            "natural_transition_points": self._identify_transition_points(context),
            "conversation_rhythm": self._analyze_conversation_rhythm(context),
            "suggested_tone": self._suggest_conversation_tone(context)
        }
    
    def _identify_transition_points(self, context) -> List[str]:
        """대화 전환점 식별"""
        
        transition_points = []
        
        # 주제 전환이 필요한 시점 식별
        for topic, tracker in context.topic_trackers.items():
            if tracker.coverage_score > 0.7:  # 충분히 다뤄진 주제
                transition_points.append(f"{topic.value} 주제에서 전환 가능")
        
        # 답변 길이 패턴 분석
        if len(context.answer_history) >= 3:
            recent_lengths = [len(answer) for answer in context.answer_history[-3:]]
            avg_length = sum(recent_lengths) / len(recent_lengths)
            
            if avg_length < 100:
                transition_points.append("답변이 짧아짐 - 주제 변경 고려")
            elif avg_length > 500:
                transition_points.append("답변이 길어짐 - 요약 질문 고려")
        
        return transition_points
    
    def _analyze_conversation_rhythm(self, context) -> Dict[str, Any]:
        """대화 리듬 분석"""
        
        rhythm = {
            "pace": "normal",
            "depth_level": "medium",
            "engagement": "medium"
        }
        
        if len(context.question_history) > 0:
            # 질문 간 시간 간격 (구현 시 추가)
            # 답변 길이 변화 패턴
            if len(context.answer_history) >= 2:
                length_trend = len(context.answer_history[-1]) - len(context.answer_history[-2])
                if length_trend > 100:
                    rhythm["engagement"] = "increasing"
                elif length_trend < -100:
                    rhythm["engagement"] = "decreasing"
        
        return rhythm
    
    def _suggest_conversation_tone(self, context) -> str:
        """대화 톤 제안"""
        
        # 추출된 정보를 바탕으로 톤 결정
        if len(context.memory.achievements) > 2:
            return "achievement_focused"  # 성취 중심
        elif len(context.memory.mentioned_technologies) > 3:
            return "technical_deep_dive"  # 기술 심화
        elif len(context.used_keywords) > 15:
            return "comprehensive"  # 포괄적
        else:
            return "exploratory"  # 탐색적
    
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """다음 질문 가져오기 (개인화 지원 + 중복 방지)"""
        
        session = self.sessions.get(session_id)
        if not session or session.is_complete():
            return None
        
        company_data = self.get_company_data(session.company_id)
        question_plan = session.get_next_question_plan()
        
        if not question_plan:
            return None
        
        # 빠른 시작을 위해 중복 검사 최적화
        # 첫 번째 질문이거나 고정 질문인 경우 중복 검사 건너뛰기
        skip_duplicate_check = (session.current_question_count == 0 or question_plan.get("fixed", False))
        
        max_attempts = 1 if skip_duplicate_check else 3
        for attempt in range(max_attempts):
            # 개인화된 질문 생성
            if isinstance(session, PersonalizedInterviewSession) and question_plan.get("personalized", False):
                question_content, question_intent = self._generate_personalized_question_with_duplicate_check(
                    session, company_data, question_plan
                )
            else:
                # PersonalizedInterviewSession에 맞는 질문 생성
                question_content, question_intent = self._generate_personalized_question(
                    session, company_data, question_plan
                )
            
            # 중복 검사 (PersonalizedInterviewSession만, 첫 질문 제외)
            if isinstance(session, PersonalizedInterviewSession) and not skip_duplicate_check:
                is_duplicate, similar_question, similarity = session.conversation_context.check_question_duplicate(question_content)
                
                if not is_duplicate:
                    break  # 중복이 아니면 사용
                else:
                    print(f"⚠️ 중복 질문 감지 (유사도: {similarity:.2f}): {similar_question[:50]}...")
                    if attempt == max_attempts - 1:
                        print("🔄 대안 질문 생성 중...")
                        # 마지막 시도에서는 컨텍스트 기반 대안 질문 생성
                        question_content, question_intent = self._generate_alternative_question(session, question_plan)
            else:
                break  # 중복 검사 건너뛰기 또는 일반 세션
        
        return {
            "question_id": f"q_{session.current_question_count + 1}",
            "question_type": question_plan["type"].value,
            "question_content": question_content,
            "question_intent": question_intent,
            "progress": f"{session.current_question_count + 1}/{len(session.question_plan)}",
            "personalized": question_plan.get("personalized", False),
            "fixed": question_plan.get("fixed", False),
            "focus": question_plan.get("focus", "general")
        }

if __name__ == "__main__":
    print("🎯 개인화된 면접 시스템 테스트")
    
    # 샘플 사용자 프로필 생성
    sample_profile = UserProfile(
        name="김개발",
        background={
            "career_years": "3",
            "current_position": "백엔드 개발자",
            "education": ["컴퓨터공학과 졸업"]
        },
        technical_skills=["Python", "Django", "PostgreSQL", "AWS", "Docker"],
        projects=[
            {
                "name": "이커머스 플랫폼",
                "description": "대용량 트래픽 처리를 위한 마이크로서비스 아키텍처 구축",
                "tech_stack": ["Python", "Django", "Redis", "PostgreSQL"],
                "role": "백엔드 리드",
                "period": "6개월"
            }
        ],
        experiences=[
            {
                "company": "스타트업 A",
                "position": "백엔드 개발자",
                "period": "2021-2024",
                "achievements": ["API 성능 30% 개선", "신규 서비스 런칭"]
            }
        ],
        strengths=["문제 해결 능력", "빠른 학습력", "팀워크"],
        keywords=["마이크로서비스", "성능 최적화", "팀 리더십"],
        career_goal="기술 리더로 성장하여 서비스 아키텍처를 설계하고 싶습니다.",
        unique_points=["대용량 트래픽 경험", "팀 리딩 경험"]
    )
    
    # 개인화된 면접 시스템 테스트 (자동으로 .env에서 API 키 로드)
    system = PersonalizedInterviewSystem()
    
    try:
        session_id = system.start_personalized_interview("naver", "백엔드 개발자", "김개발", sample_profile)
        print(f"\n✅ 개인화된 면접 세션 시작: {session_id}")
        
        # 첫 번째 질문 생성
        question = system.get_next_question(session_id)
        print(f"\n📝 첫 번째 질문:")
        print(f"유형: {question['question_type']}")
        print(f"개인화: {question['personalized']}")
        print(f"질문: {question['question_content']}")
        print(f"의도: {question['question_intent']}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")