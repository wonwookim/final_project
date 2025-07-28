#!/usr/bin/env python3
"""
통합 세션 관리자
모든 세션 타입을 관리하는 중앙화된 매니저
FinalInterviewSystem의 모든 기능을 포함하여 완전한 세션 관리 제공
"""

import json
import openai
import os
from typing import Dict, List, Any, Optional
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv

from .models import InterviewSession, ComparisonSession, SessionState, AnswerData
from .base_session import BaseInterviewSession
from .comparison_session import ComparisonSessionManager
from ..shared.models import QuestionAnswer, QuestionType
from ..shared.company_data_loader import get_company_loader

# .env 파일에서 환경변수 로드
load_dotenv()


class SessionManager:
    """
    중앙화된 세션 관리자
    FinalInterviewSystem + BaseInterviewSession + ComparisonSession을 통합 관리
    모든 면접 관련 기능을 하나의 인터페이스로 제공
    """
    
    def __init__(self, api_key: str = None):
        # OpenAI API 클라이언트 초기화
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다. .env 파일에 OPENAI_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.client = openai.OpenAI(api_key=api_key)
        
        # 기존 관리자들
        self.base_session_manager = BaseInterviewSession()
        self.comparison_session_manager = ComparisonSessionManager()
        
        # 회사 데이터 로더
        self.company_loader = get_company_loader()
        
        # 통합 세션 추적
        self.all_sessions: Dict[str, Any] = {}  # 모든 세션 추적
        self.standard_sessions: Dict[str, InterviewSession] = {}  # FinalInterviewSystem 호환 세션들
        
    # 개별 세션 관리 (기존 기능 위임)
    def start_individual_interview(self, company_id: str, position: str, candidate_name: str) -> str:
        """개별 면접 시작"""
        session_id = self.base_session_manager.start_interview(company_id, position, candidate_name)
        self.all_sessions[session_id] = {
            "type": "individual",
            "session_id": session_id,
            "created_at": datetime.now()
        }
        return session_id
    
    def get_individual_session(self, session_id: str) -> Optional[InterviewSession]:
        """개별 세션 조회"""
        return self.base_session_manager.get_session(session_id)
    
    def submit_individual_answer(self, session_id: str, answer_content: str) -> Dict[str, Any]:
        """개별 세션 답변 제출"""
        return self.base_session_manager.submit_answer(session_id, answer_content)
    
    def get_individual_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """개별 세션 다음 질문"""
        return self.base_session_manager.get_next_question(session_id)
    
    # 비교 세션 관리 (새로운 기능)
    async def start_comparison_interview(self, company_id: str, position: str, user_name: str, ai_name: str = "춘식이", posting_id: int = None, position_id: int = None) -> str:
        """AI 비교 면접 시작 (새로운 질문 생성 시스템 사용)"""
        comparison_id = await self.comparison_session_manager.start_comparison_session(
            company_id, position, user_name, ai_name, posting_id, position_id
        )
        self.all_sessions[comparison_id] = {
            "type": "comparison",
            "session_id": comparison_id,
            "created_at": datetime.now()
        }
        return comparison_id
    
    def get_comparison_session(self, comparison_id: str) -> Optional[ComparisonSession]:
        """비교 세션 조회"""
        return self.comparison_session_manager.get_session(comparison_id)
    
    def submit_comparison_answer(self, comparison_id: str, answer_content: str, answer_type: str) -> Dict[str, Any]:
        """비교 세션 답변 제출"""
        return self.comparison_session_manager.submit_answer(comparison_id, answer_content, answer_type)
    
    def get_comparison_next_question(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """비교 세션 다음 질문 (동적 질문 생성 포함)"""
        question_data = self.comparison_session_manager.get_next_question(comparison_id)
        
        if not question_data:
            return None
        
        # 동적 질문이고 내용이 비어있으면 LLM으로 생성
        if (not question_data.get("is_fixed", True) and 
            (not question_data.get("question_content") or 
             question_data.get("question_content", "").startswith("["))):
            
            try:
                session = self.get_comparison_session(comparison_id)
                if session:
                    # LLM으로 실시간 질문 생성
                    generated_content = self._generate_dynamic_question_for_comparison(
                        session, question_data
                    )
                    if generated_content:
                        question_data["question_content"] = generated_content
                        question_data["question_intent"] = f"{question_data['question_type']} 역량 평가"
            except Exception as e:
                print(f"동적 질문 생성 실패: {str(e)}")
                # 폴백: 기본 질문 사용
                question_data["question_content"] = self._get_fallback_dynamic_question(
                    question_data.get("question_type", "HR")
                )
        
        return question_data
    
    def switch_comparison_turn(self, comparison_id: str) -> Dict[str, Any]:
        """비교 세션 턴 전환"""
        return self.comparison_session_manager.switch_turn(comparison_id)
    
    # 통합 관리 기능
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """모든 세션 목록"""
        result = []
        for session_id, session_info in self.all_sessions.items():
            if session_info["type"] == "individual":
                session = self.get_individual_session(session_id)
                if session:
                    result.append({
                        "session_id": session_id,
                        "type": "individual",
                        "company_id": session.company_id,
                        "position": session.position,
                        "candidate_name": session.candidate_name,
                        "state": session.state.value,
                        "created_at": session.created_at.isoformat()
                    })
            elif session_info["type"] == "comparison":
                session = self.get_comparison_session(session_id)
                if session:
                    result.append({
                        "session_id": session_id,
                        "type": "comparison",
                        "company_id": session.company_id,
                        "position": session.position,
                        "user_name": session.user_name,
                        "ai_name": session.ai_name,
                        "state": session.state.value,
                        "created_at": session.created_at.isoformat()
                    })
        return result
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 ID로 세션 조회 (타입 무관)"""
        session_info = self.all_sessions.get(session_id)
        if not session_info:
            return None
        
        if session_info["type"] == "individual":
            session = self.get_individual_session(session_id)
            return {
                "type": "individual",
                "session": session,
                "summary": self.base_session_manager.get_session_summary(session_id)
            }
        elif session_info["type"] == "comparison":
            session = self.get_comparison_session(session_id)
            return {
                "type": "comparison", 
                "session": session,
                "summary": self.comparison_session_manager.get_session_summary(session_id)
            }
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        session_info = self.all_sessions.get(session_id)
        if not session_info:
            return False
        
        if session_info["type"] == "individual":
            self.base_session_manager.sessions.pop(session_id, None)
        elif session_info["type"] == "comparison":
            self.comparison_session_manager.sessions.pop(session_id, None)
        
        self.all_sessions.pop(session_id, None)
        return True
    
    # === FinalInterviewSystem 호환 메서드들 ===
    
    def get_company_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사 데이터 조회 (FinalInterviewSystem 호환)"""
        return self.company_loader.get_company_data(company_id)
    
    def list_companies(self) -> List[Dict[str, str]]:
        """지원 가능한 회사 목록 (FinalInterviewSystem 호환)"""
        return self.company_loader.get_company_list()
    
    def start_interview(self, company_id: str, position: str, candidate_name: str) -> str:
        """표준 면접 시작 (FinalInterviewSystem 호환)"""
        company_data = self.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        # 기존 FinalInterviewSystem과 호환되는 세션 생성
        session = InterviewSession(company_id, position, candidate_name)
        session.start_session()
        
        # 고정된 질문 순서 (총 20개 질문) - FinalInterviewSystem과 동일
        session.question_plan = [
            # 기본 질문 (2개)
            {"type": QuestionType.INTRO, "fixed": True},
            {"type": QuestionType.MOTIVATION, "fixed": True},
            
            # 인사 영역 (6개)
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            {"type": QuestionType.HR, "fixed": False},
            
            # 기술 영역 (8개)
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            {"type": QuestionType.TECH, "fixed": False},
            
            # 협업 영역 (3개)
            {"type": QuestionType.COLLABORATION, "fixed": False},
            {"type": QuestionType.COLLABORATION, "fixed": False},
            {"type": QuestionType.COLLABORATION, "fixed": False},
            
            # 심화 질문 (1개)
            {"type": QuestionType.FOLLOWUP, "fixed": False}
        ]
        
        self.standard_sessions[session.session_id] = session
        self.all_sessions[session.session_id] = {
            "type": "standard",
            "session_id": session.session_id,
            "created_at": datetime.now()
        }
        
        return session.session_id
    
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """다음 질문 가져오기 (FinalInterviewSystem 호환)"""
        session = self.standard_sessions.get(session_id)
        if not session or session.is_complete():
            return None
        
        company_data = self.get_company_data(session.company_id)
        question_plan = session.get_next_question_plan()
        
        if not question_plan:
            return None
        
        # 질문 생성
        question_content, question_intent = self._generate_next_question(
            session, company_data, question_plan["type"], question_plan["fixed"]
        )
        
        return {
            "question_id": f"q_{session.current_question_count + 1}",
            "question_type": question_plan["type"].value,
            "question_content": question_content,
            "question_intent": question_intent,
            "progress": f"{session.current_question_count + 1}/{len(session.question_plan)}",
            "personalized": False  # 표준 면접 시스템은 개인화되지 않음
        }
    
    def _generate_next_question(self, session: InterviewSession, company_data: Dict[str, Any], 
                               question_type: QuestionType, is_fixed: bool) -> tuple[str, str]:
        """다음 질문 생성 (FinalInterviewSystem과 동일한 로직)"""
        
        # 첫 두 질문은 완전히 고정
        if question_type == QuestionType.INTRO:
            return (
                f"{session.candidate_name}님, 안녕하세요. 간단한 자기소개 부탁드립니다.",
                "지원자의 기본 배경, 경력, 성격을 파악하여 면접 분위기를 조성"
            )
        elif question_type == QuestionType.MOTIVATION:
            return (
                f"{session.candidate_name}님께서 {company_data['name']}에 지원하게 된 동기는 무엇인가요?",
                "회사에 대한 관심도, 지원 의지, 회사 이해도를 평가"
            )
        
        # 나머지 질문들은 동적 생성
        context = session.get_conversation_context()
        
        if question_type == QuestionType.HR:
            prompt = self._create_hr_question_prompt(company_data, context, session.candidate_name)
        elif question_type == QuestionType.TECH:
            prompt = self._create_tech_question_prompt(company_data, context, session.position, session.candidate_name)
        elif question_type == QuestionType.COLLABORATION:
            prompt = self._create_collaboration_question_prompt(company_data, context, session.candidate_name)
        elif question_type == QuestionType.FOLLOWUP:
            prompt = self._create_followup_question_prompt(company_data, context, session.candidate_name)
        else:
            return f"{session.candidate_name}님에 대해 더 알고 싶습니다.", "일반적인 질문"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"당신은 {company_data['name']}의 면접관입니다. 지원자를 존중하며 ~님으로 호칭하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            
            if "의도:" in result:
                parts = result.split("의도:")
                question_content = parts[0].strip()
                question_intent = parts[1].strip() if len(parts) > 1 else ""
            else:
                question_content = result
                question_intent = f"{question_type.value} 역량 평가"
            
            return question_content, question_intent
            
        except Exception as e:
            print(f"질문 생성 중 오류 발생: {str(e)}")
            return self._get_fallback_question(question_type, session.candidate_name), f"{question_type.value} 기본 질문"
    
    def _create_hr_question_prompt(self, company_data: Dict[str, Any], context: str, candidate_name: str) -> str:
        return f"""
{context}

{candidate_name}님의 인사 영역(개인적 특성, 성격, 가치관, 성장 의지)을 평가하는 질문을 만들어주세요.

=== 기업 정보 ===
- 인재상: {company_data['talent_profile']}
- 핵심 역량: {', '.join(company_data['core_competencies'])}

협업과 구분되는 개인적 측면에 집중하세요.
간결한 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""
    
    def _create_tech_question_prompt(self, company_data: Dict[str, Any], context: str, position: str, candidate_name: str) -> str:
        return f"""
{context}

{candidate_name}님의 기술 역량을 평가하는 질문을 만들어주세요.

=== 기술 정보 ===
- 직군: {position}
- 기술 중점: {', '.join(company_data['tech_focus'])}

구체적이고 실무 중심의 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""
    
    def _create_collaboration_question_prompt(self, company_data: Dict[str, Any], context: str, candidate_name: str) -> str:
        return f"""
{context}

{candidate_name}님의 협업 능력(팀워크, 소통, 갈등 해결, 협업 프로세스)을 평가하는 질문을 만들어주세요.

인사 질문과 구분되는 실제 협업 경험에 집중하세요.
간결한 질문 하나만 생성하세요.

형식:
질문 내용
의도: 이 질문의 평가 목적
"""
    
    def _create_followup_question_prompt(self, company_data: Dict[str, Any], context: str, candidate_name: str) -> str:
        return f"""
{context}

{candidate_name}님의 이전 답변을 바탕으로 가장 흥미로운 부분을 깊이 파고드는 심화 질문을 만들어주세요.

- 구체적인 사례나 경험의 디테일 요구
- 사고 과정이나 의사결정 배경 탐구
- 결과와 학습한 점 확인

형식:
질문 내용
의도: 이 질문의 평가 목적
"""
    
    def _get_fallback_question(self, question_type: QuestionType, candidate_name: str) -> str:
        fallback_questions = {
            QuestionType.INTRO: f"{candidate_name}님, 간단한 자기소개 부탁드립니다.",
            QuestionType.MOTIVATION: f"{candidate_name}님이 저희 회사에 지원하게 된 동기가 궁금합니다.",
            QuestionType.HR: f"{candidate_name}님의 장점과 성장하고 싶은 부분은 무엇인가요?",
            QuestionType.TECH: f"{candidate_name}님의 기술적 경험에 대해 말씀해 주세요.",
            QuestionType.COLLABORATION: f"{candidate_name}님의 팀 협업 경험을 공유해 주세요.",
            QuestionType.FOLLOWUP: f"{candidate_name}님이 가장 자신 있는 경험을 더 자세히 설명해 주세요."
        }
        return fallback_questions.get(question_type, f"{candidate_name}님, 본인에 대해 말씀해 주세요.")
    
    def _generate_dynamic_question_for_comparison(self, session: ComparisonSession, question_data: Dict[str, Any]) -> Optional[str]:
        """비교 면접용 동적 질문 생성"""
        try:
            company_data = self.get_company_data(session.company_id)
            if not company_data:
                return None
            
            question_type_str = question_data.get("question_type", "HR")
            
            # 질문 타입에 따른 프롬프트 생성
            if question_type_str == "HR":
                prompt = self._create_hr_question_prompt(company_data, "", session.user_name)
            elif question_type_str == "TECH":
                prompt = self._create_tech_question_prompt(company_data, "", session.position, session.user_name)
            elif question_type_str == "COLLABORATION":
                prompt = self._create_collaboration_question_prompt(company_data, "", session.user_name)
            else:
                return None
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"당신은 {company_data['name']}의 면접관입니다. AI 지원자와 인간 지원자가 경쟁하는 면접에서 공정한 질문을 만드세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            
            # "의도:" 부분 제거하고 질문만 추출
            if "의도:" in result:
                question_content = result.split("의도:")[0].strip()
            else:
                question_content = result
            
            return question_content
            
        except Exception as e:
            print(f"LLM 동적 질문 생성 오류: {str(e)}")
            return None
    
    def _get_fallback_dynamic_question(self, question_type: str) -> str:
        """동적 질문 생성 실패 시 폴백 질문"""
        fallback_questions = {
            "HR": "본인의 강점과 약점에 대해 말씀해 주세요.",
            "TECH": "최근에 사용해본 기술 중 가장 인상 깊었던 것은 무엇인가요?",
            "COLLABORATION": "팀 프로젝트에서 발생한 어려움을 어떻게 해결하셨나요?",
        }
        return fallback_questions.get(question_type, "본인에 대해 더 자세히 말씀해 주세요.")
    
    def submit_answer(self, session_id: str, answer_content: str, current_question_data: Dict[str, str] = None) -> Dict[str, Any]:
        """답변 제출 (FinalInterviewSystem 호환)"""
        session = self.standard_sessions.get(session_id)
        if not session:
            return {"error": "세션을 찾을 수 없습니다"}
        
        # 현재 질문 계획 가져오기
        current_question_plan = session.get_next_question_plan()
        if not current_question_plan:
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
        
        # 현재 질문 정보 가져오기
        company_data = self.get_company_data(session.company_id)
        question_content, question_intent = self._generate_next_question(
            session, company_data, current_question_plan["type"], current_question_plan.get("fixed", False)
        )
        
        question_id = f"q_{session.current_question_count + 1}"
        question_type = current_question_plan["type"]
        
        # 질문-답변 쌍 생성
        qa_pair = QuestionAnswer(
            question_id=question_id,
            question_type=question_type,
            question_content=question_content,
            answer_content=answer_content,
            timestamp=datetime.now(),
            question_intent=question_intent
        )
        
        # 세션에 추가
        session.add_qa_pair(qa_pair)
        
        # 면접 완료 여부 확인
        if session.is_complete():
            session.complete_session()
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
        
        # 다음 질문 생성
        next_question = self.get_next_question(session_id)
        if next_question:
            return {
                "status": "next_question",
                "question": next_question,
                "answered_count": session.current_question_count
            }
        else:
            session.complete_session()
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
    
    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """세션 조회 (FinalInterviewSystem 호환)"""
        return self.standard_sessions.get(session_id)
    
    def evaluate_interview(self, session_id: str) -> Dict[str, Any]:
        """면접 전체 평가 (FinalInterviewSystem 호환)"""
        session = self.standard_sessions.get(session_id)
        if not session:
            return {"error": "세션을 찾을 수 없습니다"}
        
        company_data = self.get_company_data(session.company_id)
        
        # 배치 평가로 모든 답변을 한 번에 평가
        batch_evaluation = self._evaluate_batch_answers(session, company_data)
        
        individual_feedbacks = []
        total_score = 0
        category_scores = {}
        
        for i, qa in enumerate(session.conversation_history):
            # 배치 평가 결과에서 개별 평가 추출
            if i < len(batch_evaluation.get('individual_scores', [])):
                individual_eval = batch_evaluation['individual_scores'][i]
                qa.individual_score = individual_eval.get('score', 50)
                qa.individual_feedback = individual_eval.get('feedback', '평가를 생성할 수 없습니다.')
            else:
                qa.individual_score = 50
                qa.individual_feedback = "기본 평가가 적용되었습니다."
            
            individual_feedbacks.append({
                "question_number": len(individual_feedbacks) + 1,
                "question_type": qa.question_type.value,
                "question": qa.question_content,
                "question_intent": qa.question_intent,
                "answer": qa.answer_content,
                "score": qa.individual_score,
                "feedback": qa.individual_feedback,
                "personalized": False
            })
            
            total_score += qa.individual_score
            
            # 카테고리별 점수 계산
            category = qa.question_type.value
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(qa.individual_score)
        
        # 전체 평균 계산
        overall_score = int(total_score / len(session.conversation_history))
        
        # 카테고리별 평균
        for category in category_scores:
            category_scores[category] = int(sum(category_scores[category]) / len(category_scores[category]))
        
        # 종합 평가
        overall_evaluation = batch_evaluation.get('overall_evaluation', {
            "strengths": ["기본 강점"],
            "improvements": ["기본 개선사항"],
            "recommendation": "보완 후 재검토",
            "next_steps": "추가 면접 진행",
            "overall_assessment": f"전체 {overall_score}점 수준의 면접 결과입니다."
        })
        
        return {
            "session_id": session_id,
            "company": company_data["name"],
            "position": session.position,
            "candidate": session.candidate_name,
            "individual_feedbacks": individual_feedbacks,
            "evaluation": {
                "overall_score": overall_score,
                "category_scores": category_scores,
                **overall_evaluation
            },
            "completed_at": datetime.now().isoformat()
        }
    
    def _evaluate_batch_answers(self, session: InterviewSession, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """배치 처리로 모든 답변을 한 번에 평가 (속도 최적화)"""
        
        # 모든 질문과 답변을 하나의 텍스트로 구성
        qa_summary = ""
        for i, qa in enumerate(session.conversation_history, 1):
            qa_summary += f"""
질문 {i}: [{qa.question_type.value}] {qa.question_content}
의도: {qa.question_intent}
답변: {qa.answer_content}
---
"""
        
        # 배치 평가 프롬프트
        batch_prompt = f"""
다음은 {company_data['name']} {session.position} 면접의 전체 질문과 답변입니다.

=== 면접 내용 ===
{qa_summary}

=== 평가 요구사항 ===
각 답변을 0-100점으로 평가하고 간단한 피드백을 제공하세요.
전체 종합 평가도 함께 제공하세요.

JSON 형식으로 응답:
{{
  "individual_scores": [
    {{"score": 점수, "feedback": "간단한 피드백"}},
    ...
  ],
  "overall_evaluation": {{
    "strengths": ["강점1", "강점2", "강점3"],
    "improvements": ["개선점1", "개선점2", "개선점3"],
    "recommendation": "최종 추천",
    "next_steps": "다음 단계",
    "overall_assessment": "전체 평가 요약"
  }}
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"당신은 {company_data['name']}의 면접 평가 전문가입니다. 빠르고 정확하게 평가하세요."},
                    {"role": "user", "content": batch_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("JSON 형식을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"배치 평가 중 오류: {str(e)}")
            # 폴백: 기본 평가 생성
            return {
                "individual_scores": [{"score": 50, "feedback": "기본 평가가 적용되었습니다."} for _ in session.conversation_history],
                "overall_evaluation": {
                    "strengths": ["면접 참여", "기본 소통"],
                    "improvements": ["구체적 사례 제시", "답변 깊이"],
                    "recommendation": "보완 후 재검토",
                    "next_steps": "추가 면접 진행",
                    "overall_assessment": "시스템 오류로 기본 평가가 적용되었습니다."
                }
            }