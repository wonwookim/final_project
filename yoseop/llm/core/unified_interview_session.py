#!/usr/bin/env python3
"""
통합 면접 세션 관리자
기존 PersonalizedInterviewSystem과 AICandidateModel을 통합하여 세션 관리 단순화
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from .personalized_system import PersonalizedInterviewSystem
from .ai_candidate_model import AICandidateModel
from .document_processor import UserProfile


@dataclass
class QuestionData:
    """질문 데이터 클래스"""
    id: str
    content: str
    category: str
    intent: str
    time_limit: int = 120
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class AnswerData:
    """답변 데이터 클래스"""
    question_id: str
    content: str
    time_spent: int
    timestamp: datetime
    answer_type: str  # "human" or "ai"
    score: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UnifiedInterviewSession:
    """통합 면접 세션 - Human과 AI를 하나의 세션으로 관리"""
    
    def __init__(self, company: str, position: str, user_name: str, user_profile: UserProfile):
        self.session_id = str(uuid.uuid4())
        self.company = company
        self.position = position
        self.user_name = user_name
        self.user_profile = user_profile
        
        # 세션 상태
        self.status = "active"
        self.created_at = datetime.now()
        self.completed_at = None
        self.total_score = None
        self.current_question_index = 0
        self.total_questions = 20
        
        # 질문과 답변 저장
        self.questions: List[QuestionData] = []
        self.human_answers: List[AnswerData] = []
        self.ai_answers: List[AnswerData] = []
        
        # 기존 시스템들 초기화
        self.personalized_system = PersonalizedInterviewSystem()
        self.ai_candidate_model = AICandidateModel()
        
        # PersonalizedInterviewSystem 세션 시작
        self.personalized_session_id = None
        self._init_personalized_system()
        
        # AI 세션 시작
        self.ai_session_id = None
        self._init_ai_session()
        
        # 기본 고정 질문 2개 추가
        self._add_initial_questions()
    
    def _init_personalized_system(self):
        """PersonalizedInterviewSystem 초기화"""
        try:
            company_id = self._get_company_id(self.company)
            self.personalized_session_id = self.personalized_system.start_personalized_interview(
                company_id, self.position, self.user_name, self.user_profile
            )
            print(f"✅ PersonalizedInterviewSystem 초기화 완료: {self.personalized_session_id}")
        except Exception as e:
            print(f"❌ PersonalizedInterviewSystem 초기화 실패: {e}")
            self.personalized_session_id = None
    
    def _init_ai_session(self):
        """AI 세션 초기화"""
        try:
            company_id = self._get_company_id(self.company)
            self.ai_session_id = self.ai_candidate_model.start_ai_interview(
                company_id, self.position
            )
            print(f"✅ AI 세션 초기화 완료: {self.ai_session_id}")
        except Exception as e:
            print(f"❌ AI 세션 초기화 실패: {e}")
            self.ai_session_id = None
    
    def _get_company_id(self, company_name: str) -> str:
        """회사 이름을 ID로 변환"""
        company_map = {
            "네이버": "naver", "카카오": "kakao", "라인": "line",
            "쿠팡": "coupang", "배달의민족": "baemin", "당근마켓": "daangn", "토스": "toss"
        }
        return company_map.get(company_name, company_name.lower())
    
    def _add_initial_questions(self):
        """기본 고정 질문 2개 추가"""
        # 1. 자기소개
        intro_question = QuestionData(
            id="q_1",
            content=f"{self.user_name}님, 안녕하세요. 간단한 자기소개 부탁드립니다.",
            category="자기소개",
            intent="지원자의 기본 배경, 경력, 성격을 파악하여 면접 분위기를 조성"
        )
        self.questions.append(intro_question)
        
        # 2. 지원동기
        motivation_question = QuestionData(
            id="q_2",
            content=f"{self.user_name}님께서 {self.company}에 지원하게 된 동기는 무엇인가요?",
            category="지원동기", 
            intent="회사에 대한 관심도, 지원 의지, 회사 이해도를 평가"
        )
        self.questions.append(motivation_question)
        
        print(f"✅ 기본 질문 2개 추가 완료")
    
    def get_current_question(self) -> Optional[QuestionData]:
        """현재 질문 가져오기"""
        # 현재 인덱스가 질문 수보다 크거나 같으면 새 질문 생성
        if self.current_question_index >= len(self.questions):
            # 새 질문 생성 필요
            if self._generate_next_question():
                return self.questions[self.current_question_index]
            else:
                return None
        
        # 현재 인덱스에 해당하는 질문 반환
        current_question = self.questions[self.current_question_index]
        print(f"🔍 현재 질문 반환: index={self.current_question_index}, question={current_question.content[:30]}...")
        return current_question
    
    def _generate_next_question(self) -> bool:
        """다음 질문 생성"""
        if not self.personalized_session_id:
            return False
        
        if self.current_question_index >= self.total_questions:
            return False
        
        try:
            # PersonalizedInterviewSystem에서 질문 생성
            question_data = self.personalized_system.get_next_question(self.personalized_session_id)
            
            if question_data:
                # 중복 질문 필터링 (자기소개, 지원동기 제외)
                question_type = question_data["question_type"]
                question_content = question_data["question_content"]
                
                # 자기소개나 지원동기 관련 질문 스킵
                if (any(keyword in question_content for keyword in ["자기소개", "지원하게", "지원 동기", "지원동기"]) or
                    any(keyword in question_type for keyword in ["자기소개", "지원동기"])):
                    print(f"⚠️ 중복 질문 스킵 (내용/카테고리): {question_content[:50]}...")
                    # 다시 질문 생성 시도
                    return self._generate_next_question()
                
                new_question = QuestionData(
                    id=question_data["question_id"],
                    content=question_data["question_content"],
                    category=question_data["question_type"],
                    intent=question_data.get("question_intent", "")
                )
                self.questions.append(new_question)
                print(f"✅ 새 질문 생성: {new_question.content[:50]}...")
                return True
                
        except Exception as e:
            print(f"❌ 질문 생성 실패: {e}")
        
        return False
    
    def submit_human_answer(self, question_id: str, answer: str, time_spent: int) -> bool:
        """사용자 답변 제출"""
        try:
            # 답변 저장
            human_answer = AnswerData(
                question_id=question_id,
                content=answer,
                time_spent=time_spent,
                timestamp=datetime.now(),
                answer_type="human"
            )
            self.human_answers.append(human_answer)
            
            # PersonalizedInterviewSystem에 답변 제출
            if self.personalized_session_id:
                self.personalized_system.submit_answer(
                    self.personalized_session_id,
                    answer
                )
            
            # 다음 질문으로 이동
            self.current_question_index += 1
            
            print(f"✅ 사용자 답변 제출 완료: {question_id}")
            return True
            
        except Exception as e:
            print(f"❌ 사용자 답변 제출 실패: {e}")
            return False
    
    def generate_ai_answer(self, question_id: str) -> Optional[Dict[str, Any]]:
        """AI 답변 생성"""
        try:
            # 질문 찾기
            question = None
            for q in self.questions:
                if q.id == question_id:
                    question = q
                    break
            
            if not question:
                print(f"❌ 질문을 찾을 수 없음: {question_id}")
                return None
            
            # AI 세션 확인
            if not self.ai_session_id:
                print(f"❌ AI 세션이 초기화되지 않음")
                return None
            
            # 질문 데이터 구성
            question_data = {
                "question_id": question_id,
                "question_content": question.content,
                "question_type": question.category,
                "question_intent": question.intent
            }
            
            # AI 답변 생성
            ai_response = self.ai_candidate_model.generate_ai_answer_for_question(
                self.ai_session_id,
                question_data
            )
            
            if ai_response and not ai_response.error:
                # AI 답변 저장
                ai_answer = AnswerData(
                    question_id=question_id,
                    content=ai_response.answer_content,
                    time_spent=int(ai_response.response_time * 30),
                    timestamp=datetime.now(),
                    answer_type="ai",
                    score=int(ai_response.confidence_score * 100),
                    metadata={
                        "quality_level": ai_response.quality_level.value,
                        "persona_name": ai_response.persona_name,
                        "llm_provider": ai_response.llm_provider.value
                    }
                )
                self.ai_answers.append(ai_answer)
                
                print(f"✅ AI 답변 생성 완료: {question_id}")
                
                return {
                    "answer": ai_response.answer_content,
                    "time_spent": ai_answer.time_spent,
                    "score": ai_answer.score,
                    "quality_level": ai_response.quality_level.value,
                    "persona_name": ai_response.persona_name
                }
            else:
                print(f"❌ AI 답변 생성 실패: {ai_response.error if ai_response else 'Unknown error'}")
                return None
                
        except Exception as e:
            print(f"❌ AI 답변 생성 중 오류: {e}")
            return None
    
    def is_completed(self) -> bool:
        """면접 완료 여부 확인"""
        return self.current_question_index >= self.total_questions
    
    def get_progress(self) -> Dict[str, Any]:
        """면접 진행 상황"""
        return {
            "current_index": self.current_question_index,
            "total_questions": self.total_questions,
            "progress_percentage": (self.current_question_index / self.total_questions) * 100,
            "questions_answered": len(self.human_answers),
            "ai_answers_generated": len(self.ai_answers),
            "status": self.status
        }
    
    @property
    def answers(self) -> List[Dict[str, Any]]:
        """results API와 호환되는 답변 형식으로 반환"""
        return [
            {
                "answer": a.content,
                "time_spent": a.time_spent,
                "evaluation": {}  # 기본 빈 평가 객체
            } for a in self.human_answers
        ]

    def get_results(self) -> Dict[str, Any]:
        """면접 결과 반환"""
        return {
            "session_id": self.session_id,
            "company": self.company,
            "position": self.position,
            "user_name": self.user_name,
            "status": self.status,
            "progress": self.get_progress(),
            "questions": [
                {
                    "id": q.id,
                    "content": q.content,
                    "category": q.category,
                    "intent": q.intent
                } for q in self.questions[:self.current_question_index]
            ],
            "human_answers": [
                {
                    "question_id": a.question_id,
                    "content": a.content,
                    "time_spent": a.time_spent,
                    "timestamp": a.timestamp.isoformat()
                } for a in self.human_answers
            ],
            "ai_answers": [
                {
                    "question_id": a.question_id,
                    "content": a.content,
                    "time_spent": a.time_spent,
                    "score": a.score,
                    "metadata": a.metadata
                } for a in self.ai_answers
            ]
        }