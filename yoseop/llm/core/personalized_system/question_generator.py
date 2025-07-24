#!/usr/bin/env python3
"""
개인화된 질문 생성기
사용자 프로필과 컨텍스트를 바탕으로 맞춤형 질문을 생성
"""

import re
from typing import Dict, Any, Tuple
import openai
from ..interview_system import QuestionType
from ..constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from ..utils import parse_career_years, get_difficulty_level, extract_question_and_intent
from .session import PersonalizedInterviewSession

class QuestionGenerator:
    """개인화된 질문 생성기"""
    
    def __init__(self, client: openai.OpenAI):
        self.client = client
    
    def generate_personalized_question(self, session: PersonalizedInterviewSession, 
                                     company_data: Dict[str, Any], question_plan: Dict[str, Any],
                                     get_fixed_question_func, build_previous_answers_context_func) -> Tuple[str, str]:
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
            
            fixed_question = get_fixed_question_func(section, difficulty_level)
            if fixed_question:
                return (
                    fixed_question["content"],
                    fixed_question["intent"]
                )
        
        # 개인화된 질문 생성
        print(f"🎯 개인화 질문 생성 시작 - {question_type.value}, focus: {focus}")
        context = self._build_personalized_context(session, company_data)
        
        # 고정 질문 답변 참고를 위한 컨텍스트 추가
        previous_answers_context = build_previous_answers_context_func(session)
        if previous_answers_context:
            context += f"\n\n이전 답변 참고사항:\n{previous_answers_context}"
        
        prompt = self._create_personalized_prompt(question_type, focus, context, session.candidate_name)
        print(f"📝 LLM 프롬프트 생성 완료 - 길이: {len(prompt)} 글자")
        
        try:
            print(f"🤖 OpenAI API 호출 중...")
            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": f"당신은 {company_data['name']}의 면접관입니다. 전문적이고 예의바른 질문을 생성하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ OpenAI 응답 받음: {result[:100]}...")
            
            # 제어 문자와 특수 문자 정리
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
        """개인화된 컨텍스트 구성"""
        
        profile = session.user_profile
        
        # UserProfile 객체인지 확인하고 안전하게 처리
        if hasattr(profile, 'background'):
            # 정상적인 UserProfile 객체
            context = f"""
=== 지원자 프로필 ===
이름: {profile.name}
경력: {profile.background.get('career_years', '0')}년
현재 직책: {profile.background.get('current_position', '신입')}
주요 기술: {', '.join(profile.technical_skills[:5]) if profile.technical_skills else '없음'}

=== 주요 프로젝트 ===
"""
            for i, project in enumerate(profile.projects[:3], 1):
                context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
                context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            
            context += f"""
=== 강점 및 특징 ===
주요 강점: {', '.join(profile.strengths[:3]) if profile.strengths else '없음'}
차별화 포인트: {', '.join(profile.unique_points[:2]) if profile.unique_points else '없음'}
커리어 목표: {profile.career_goal}
"""
        else:
            # dict 형태 또는 기타 형태인 경우
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
=== 지원자 프로필 ===
이름: {profile_dict.get('name', '지원자')}
경력: {profile_dict.get('background', {}).get('career_years', '0')}년
현재 직책: {profile_dict.get('background', {}).get('current_position', '신입')}
주요 기술: {', '.join(profile_dict.get('technical_skills', [])[:5]) if profile_dict.get('technical_skills') else '없음'}

=== 주요 프로젝트 ===
"""
            projects = profile_dict.get('projects', [])
            for i, project in enumerate(projects[:3], 1):
                context += f"{i}. {project.get('name', '프로젝트')}: {project.get('description', '')}\n"
                context += f"   기술스택: {', '.join(project.get('tech_stack', []))}\n"
            
            context += f"""
=== 강점 및 특징 ===
주요 강점: {', '.join(profile_dict.get('strengths', [])[:3]) if profile_dict.get('strengths') else '없음'}
차별화 포인트: {', '.join(profile_dict.get('unique_points', [])[:2]) if profile_dict.get('unique_points') else '없음'}
커리어 목표: {profile_dict.get('career_goal', '성장')}
"""
        
        context += f"""
=== 기업 요구사항 ===
인재상: {company_data.get('talent_profile', '우수한 개발자')}
핵심 역량: {', '.join(company_data.get('core_competencies', ['기술 역량', '협업 능력']))}
기술 중점: {', '.join(company_data.get('tech_focus', ['백엔드', '시스템 설계']))}

=== 이전 대화 내용 ===
"""
        
        if session.conversation_history:
            for i, qa in enumerate(session.conversation_history[-2:], 1):  # 최근 2개만
                context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
                context += f"   답변: {qa.answer_content[:100]}...\n\n"
        else:
            context += "아직 대화 내용이 없습니다.\n"
        
        return context
    
    def _create_personalized_prompt(self, question_type: QuestionType, focus: str, context: str, candidate_name: str) -> str:
        """개인화된 프롬프트 생성"""
        
        focus_descriptions = {
            # HR 관련 포커스
            "growth_mindset": "성장 마인드셋과 학습 의지를 평가하는 질문",
            "leadership_style": "리더십 스타일과 팀 관리 능력을 평가하는 질문", 
            "growth": "성장 가능성과 발전 의지를 평가하는 질문",
            "adaptability": "적응력과 변화 대응 능력을 평가하는 질문",
            "potential": "잠재력과 발전 가능성을 평가하는 질문",
            "enthusiasm": "열정과 의지를 평가하는 질문",
            
            # 기술 관련 포커스
            "problem_solving": "문제 해결 능력과 논리적 사고를 평가하는 질문",
            "innovation": "혁신적 사고와 창의성을 평가하는 질문",
            "learning": "학습 능력과 기술 습득 방법을 평가하는 질문",
            "technical_depth": "기술적 깊이와 전문성을 평가하는 질문", 
            "learning_ability": "새로운 기술 학습 능력을 평가하는 질문",
            "project_experience": "프로젝트 경험과 실무 능력을 평가하는 질문",
            "passion": "기술에 대한 열정과 관심을 평가하는 질문",
            
            # 협업 관련 포커스  
            "communication": "의사소통 능력과 표현력을 평가하는 질문",
            "conflict_resolution": "갈등 해결과 문제 조정 능력을 평가하는 질문",
            "team_contribution": "팀 기여도와 협업 방식을 평가하는 질문",
            "peer_learning": "동료와의 학습과 지식 공유를 평가하는 질문",
            "willingness_to_learn": "학습 의지와 성장 태도를 평가하는 질문",
            
            # 심화 질문 포커스
            "career": "커리어 방향성과 전략을 평가하는 질문", 
            "future_goals": "미래 목표와 비전을 평가하는 질문",
            "company_contribution": "회사 기여 방안과 가치 창출을 평가하는 질문",
            "career_growth": "커리어 성장 계획과 방향성을 평가하는 질문",
            "growth_mindset": "성장 마인드셋과 도전 정신을 평가하는 질문"
        }
        
        focus_description = focus_descriptions.get(focus, f"{focus} 관련 역량을 평가하는 질문")
        
        return f"""
다음 정보를 바탕으로 {candidate_name}님에게 적합한 개인화된 면접 질문을 생성해주세요.

{context}

=== 질문 생성 요구사항 ===
• 질문 유형: {question_type.value}
• 평가 포커스: {focus_description}
• 지원자의 프로필과 경험을 고려한 맞춤형 질문
• 구체적이고 실질적인 경험을 물어보는 질문
• 지원자의 성장 가능성을 평가할 수 있는 질문

=== 질문 형식 ===
질문: [구체적이고 개인화된 질문 내용]

의도: [질문의 평가 의도와 목적]

주의사항:
- 지원자의 실제 경험과 배경을 고려해주세요
- 너무 일반적이지 않고 구체적인 상황을 가정한 질문을 만들어주세요  
- 지원자가 답변하기 어려운 과도한 기술적 질문은 피해주세요
- 예의바르고 존중하는 어조로 질문해주세요
"""
    
    def _get_fallback_personalized_question(self, question_type: QuestionType, focus: str, candidate_name: str) -> Tuple[str, str]:
        """개인화 질문 생성 실패 시 대체 질문"""
        
        fallback_questions = {
            QuestionType.HR: {
                "growth_mindset": (f"{candidate_name}님은 어떤 상황에서 가장 많이 성장한다고 생각하시나요?", "성장 마인드셋 평가"),
                "leadership_style": (f"{candidate_name}님이 생각하는 좋은 리더의 조건은 무엇인가요?", "리더십 관점 평가"),
                "growth": (f"{candidate_name}님의 성장을 위해 가장 중요하다고 생각하는 것은 무엇인가요?", "성장 의지 평가"),
                "adaptability": (f"새로운 환경에 적응할 때 {candidate_name}님만의 방법이 있나요?", "적응력 평가"),
                "potential": (f"{candidate_name}님의 잠재력을 가장 잘 보여주는 경험이 있다면 말씀해 주세요.", "잠재력 평가"),
                "enthusiasm": (f"개발 일에 대한 {candidate_name}님의 열정을 보여주는 사례가 있나요?", "열정 평가")
            },
            QuestionType.TECH: {
                "problem_solving": (f"기술적 문제를 해결할 때 {candidate_name}님만의 접근 방식이 있나요?", "문제 해결 능력 평가"),
                "innovation": (f"기존과 다른 창의적인 방법으로 문제를 해결한 경험이 있나요?", "혁신적 사고 평가"),
                "learning": (f"새로운 기술을 학습할 때 {candidate_name}님만의 방법이 있나요?", "학습 능력 평가"),
                "technical_depth": (f"가장 깊이 있게 다뤄본 기술 분야에 대해 설명해 주세요.", "기술적 깊이 평가"),
                "learning_ability": (f"가장 최근에 새롭게 배운 기술과 그 과정을 말씀해 주세요.", "학습 능력 평가"),
                "project_experience": (f"가장 기억에 남는 프로젝트 경험을 공유해 주세요.", "프로젝트 경험 평가"),
                "passion": (f"개발에 대한 {candidate_name}님의 열정을 보여주는 활동이 있나요?", "기술 열정 평가")
            },
            QuestionType.COLLABORATION: {
                "communication": (f"팀원들과 소통할 때 {candidate_name}님이 중요하게 생각하는 것은 무엇인가요?", "의사소통 능력 평가"),
                "conflict_resolution": (f"팀 내 의견 차이가 있을 때 어떻게 해결하시나요?", "갈등 해결 능력 평가"),
                "team_contribution": (f"팀에 {candidate_name}님만의 기여 방식이 있다면 무엇인가요?", "팀 기여도 평가"),
                "peer_learning": (f"동료들과 지식을 공유하고 함께 성장한 경험이 있나요?", "동료 학습 평가"),
                "willingness_to_learn": (f"모르는 것이 있을 때 어떻게 학습하고 해결하시나요?", "학습 의지 평가")
            },
            QuestionType.FOLLOWUP: {
                "career": (f"{candidate_name}님의 커리어 방향과 목표에 대해 말씀해 주세요.", "커리어 계획 평가"),
                "future_goals": (f"앞으로 3-5년 후 {candidate_name}님의 모습을 어떻게 그리고 계시나요?", "미래 비전 평가"),
                "company_contribution": (f"저희 회사에서 {candidate_name}님이 가장 기여할 수 있는 부분은 무엇이라고 생각하시나요?", "회사 기여도 평가"),
                "career_growth": (f"커리어 성장을 위해 가장 중요하다고 생각하는 것은 무엇인가요?", "성장 계획 평가"),
                "growth_mindset": (f"도전적인 상황을 어떻게 성장의 기회로 만드시나요?", "성장 마인드셋 평가")
            }
        }
        
        question_data = fallback_questions.get(question_type, {}).get(focus)
        if question_data:
            return question_data
        
        # 최종 대체 질문
        return (
            f"{candidate_name}님의 {question_type.value} 관련 경험을 공유해 주세요.",
            f"{question_type.value} 역량 평가"
        )