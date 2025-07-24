"""
AI 지원자 기본 모델 - 기존 성능 유지하며 간소화
"""
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..base_model import BaseLLMModel
from ...core.interview_system import QuestionType
from ...core.answer_quality_controller import QualityLevel, AnswerQualityController
from ...core.llm_manager import LLMProvider

@dataclass
class CandidatePersona:
    """지원자 페르소나 데이터 클래스 - 기존과 동일"""
    company_id: str
    name: str
    background: Dict[str, Any]
    technical_skills: list[str]
    projects: list[Dict[str, Any]]
    experiences: list[Dict[str, Any]]
    strengths: list[str]
    achievements: list[str]
    career_goal: str
    personality_traits: list[str]
    interview_style: str
    success_factors: list[str]

@dataclass
class AnswerResponse:
    """답변 응답 데이터 - 기존과 동일"""
    answer_content: str
    quality_level: QualityLevel
    llm_provider: LLMProvider
    persona_name: str
    confidence_score: float
    response_time: float = 0.0
    reasoning: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class BaseCandidate(BaseLLMModel):
    """AI 지원자 기본 클래스 - 기존 성능 유지"""
    
    def __init__(self, company_id: str = "naver", **kwargs):
        super().__init__(**kwargs)
        self.company_id = company_id
        self.quality_controller = AnswerQualityController()
        self.personas = self._load_default_personas()
        self.persona = self.personas.get(company_id, self._get_default_persona())
        self.name = self.persona.name
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """BaseLLMModel 추상 메서드 구현"""
        system_message = self._create_persona_system_message()
        return await self._call_llm(prompt, system_message, **kwargs)
    
    async def generate_answer(self, 
                            question: str,
                            question_type: QuestionType,
                            company_id: str,
                            position: str,
                            quality_level: QualityLevel = QualityLevel.GOOD) -> AnswerResponse:
        """답변 생성 - 기존 성능 유지"""
        import time
        start_time = time.time()
        
        try:
            # 품질 컨트롤러를 통한 정교한 프롬프트 생성
            prompt = self._create_enhanced_answer_prompt(question, question_type, company_id, position, quality_level)
            system_message = self._create_persona_system_message()
            
            # LLM 호출
            answer = await self._call_llm(prompt, system_message, max_tokens=800, temperature=0.7)
            
            # 답변 후처리 및 품질 검증
            processed_answer = self._post_process_answer(answer, question_type)
            confidence = self._calculate_confidence(processed_answer, question_type)
            
            response_time = time.time() - start_time
            
            return AnswerResponse(
                answer_content=processed_answer,
                quality_level=quality_level,
                llm_provider=self.provider,
                persona_name=self.name,
                confidence_score=confidence,
                response_time=response_time,
                reasoning=f"Based on {self.persona.interview_style} approach"
            )
            
        except Exception as e:
            return AnswerResponse(
                answer_content="죄송합니다. 답변을 준비하는 중에 문제가 발생했습니다. 다시 한번 질문해 주시면 더 나은 답변을 드리겠습니다.",
                quality_level=QualityLevel.POOR,
                llm_provider=self.provider,
                persona_name=self.name,
                confidence_score=0.0,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def _create_enhanced_answer_prompt(self, question: str, question_type: QuestionType, 
                                     company_id: str, position: str, quality_level: QualityLevel) -> str:
        """정교한 답변 프롬프트 생성 - 기존 로직 재현"""
        persona_context = self._get_persona_context()
        quality_guidance = self.quality_controller.get_quality_guidance(quality_level)
        
        return f"""
{persona_context}

=== 면접 상황 ===
면접 회사: {company_id.upper()}
지원 직군: {position}
질문 유형: {question_type.value}

=== 면접관 질문 ===
{question}

=== 답변 가이드라인 ===
{quality_guidance}

=== 답변 스타일 ===
- 페르소나 특성: {self.persona.interview_style}
- 강조할 요소: {', '.join(self.persona.success_factors)}
- 성격 반영: {', '.join(self.persona.personality_traits[:2])}

위 페르소나로서 자연스럽고 설득력 있는 답변을 해주세요.
구체적인 경험과 성과를 포함하여 2-3분 길이로 답변하세요.
"""
    
    def _create_persona_system_message(self) -> str:
        """페르소나 기반 시스템 메시지"""
        return f"""당신은 {self.name}입니다. 

기본 정보:
- 경력: {self.persona.background.get('career_years', '3')}년차 {self.persona.background.get('current_position', '개발자')}
- 전문분야: {', '.join(self.persona.technical_skills[:3])}
- 커리어 목표: {self.persona.career_goal}

면접에서는 자신감 있고 전문적으로 답변하되, {self.persona.interview_style} 스타일을 유지하세요.
실제 경험을 바탕으로 구체적이고 설득력 있게 답변하세요."""
    
    def _get_persona_context(self) -> str:
        """페르소나 컨텍스트 구성 - 기존 로직"""
        return f"""
=== AI 지원자 페르소나 정보 ===
이름: {self.persona.name}
경력: {self.persona.background.get('career_years', '0')}년
현재 직책: {self.persona.background.get('current_position', '지원자')}
주요 기술: {', '.join(self.persona.technical_skills[:5])}
강점: {', '.join(self.persona.strengths[:3])}
커리어 목표: {self.persona.career_goal}
성격 특성: {', '.join(self.persona.personality_traits)}

=== 주요 프로젝트 경험 ===
{self._format_projects()}

=== 주요 성과 ===
{self._format_achievements()}
"""
    
    def _format_projects(self) -> str:
        """프로젝트 정보 포맷팅"""
        if not self.persona.projects:
            return "다양한 개발 프로젝트 경험"
        
        formatted = []
        for project in self.persona.projects[:2]:  # 상위 2개만
            formatted.append(f"- {project.get('name', '프로젝트')}: {project.get('description', '상세 내용')}")
        return '\n'.join(formatted)
    
    def _format_achievements(self) -> str:
        """성과 정보 포맷팅"""
        return '\n'.join([f"- {achievement}" for achievement in self.persona.achievements[:3]])
    
    def _post_process_answer(self, answer: str, question_type: QuestionType) -> str:
        """답변 후처리"""
        # 기본 정제
        answer = answer.strip()
        
        # 질문 유형별 후처리
        if question_type == QuestionType.INTRO and not answer.startswith(("안녕하세요", "반갑습니다")):
            answer = f"안녕하세요, {answer}"
        
        return answer
    
    def _calculate_confidence(self, answer: str, question_type: QuestionType) -> float:
        """신뢰도 계산"""
        base_confidence = 0.75
        
        # 길이 기반 조정
        if len(answer) > 200:
            base_confidence += 0.1
        elif len(answer) < 50:
            base_confidence -= 0.2
        
        # 질문 유형별 조정
        if question_type in [QuestionType.INTRO, QuestionType.MOTIVATION]:
            base_confidence += 0.05
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _load_default_personas(self) -> Dict[str, CandidatePersona]:
        """기본 페르소나 로드 - 기존 데이터 사용"""
        return {
            "naver": CandidatePersona(
                company_id="naver",
                name="춘식이",
                background={"career_years": "3", "current_position": "백엔드 개발자", "education": ["컴퓨터공학과 졸업"]},
                technical_skills=["Java", "Spring Boot", "MySQL", "Redis", "Docker"],
                projects=[{"name": "검색 엔진 최적화", "description": "대용량 검색 시스템 성능 개선"}],
                experiences=[{"company": "IT 스타트업", "position": "백엔드 개발자", "period": "2021-2024"}],
                strengths=["대용량 처리", "시스템 최적화", "문제 해결"],
                achievements=["검색 응답시간 30% 개선", "시스템 안정성 99.9% 달성"],
                career_goal="검색 및 AI 분야의 시니어 개발자",
                personality_traits=["분석적", "완벽주의", "협업 중시"],
                interview_style="논리적이고 데이터 중심적",
                success_factors=["기술적 깊이", "대규모 시스템 경험", "성능 최적화 능력"]
            ),
            "kakao": CandidatePersona(
                company_id="kakao",
                name="춘식이",
                background={"career_years": "4", "current_position": "플랫폼 개발자"},
                technical_skills=["Node.js", "React", "MongoDB", "Docker", "Kubernetes"],
                projects=[{"name": "메시징 플랫폼 MSA 전환", "description": "모놀리식에서 마이크로서비스로 전환"}],
                experiences=[{"company": "IT 스타트업", "position": "풀스택 개발자", "period": "2020-2024"}],
                strengths=["플랫폼 설계", "MSA 아키텍처", "사회적 가치 추구"],
                achievements=["사내 해커톤 우승", "오픈소스 기여"],
                career_goal="사회적 가치를 창출하는 플랫폼 아키텍트",
                personality_traits=["개방적", "창의적", "사회적 가치 중시"],
                interview_style="협력적이고 가치 중심적",
                success_factors=["플랫폼 경험", "협업 능력", "사회적 가치 인식"]
            )
        }
    
    def _get_default_persona(self) -> CandidatePersona:
        """기본 페르소나"""
        return CandidatePersona(
            company_id="default",
            name="춘식이",
            background={"career_years": "3", "current_position": "개발자"},
            technical_skills=["Python", "JavaScript", "SQL"],
            projects=[{"name": "웹 서비스 개발", "description": "풀스택 웹 애플리케이션 개발"}],
            experiences=[{"company": "IT 회사", "position": "개발자", "period": "2021-2024"}],
            strengths=["문제 해결", "빠른 학습", "협업"],
            achievements=["프로젝트 성공적 완료"],
            career_goal="전문 개발자로 성장",
            personality_traits=["성실함", "적극적"],
            interview_style="진솔하고 전문적",
            success_factors=["기술 역량", "학습 능력", "협업 능력"]
        )