#!/usr/bin/env python3
"""
면접 서비스
모든 면접 관련 비즈니스 로직을 담당하는 서비스 계층
"""

import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import time

# 통합 세션 관리 모듈 (FinalInterviewSystem 대체)
from llm.session import SessionManager, InterviewSession, ComparisonSession
# 새로운 턴제 면접관 시스템
from llm.interviewer.service import InterviewerService

# 문서 처리 및 AI 모델
from llm.interviewer.document_processor import DocumentProcessor, UserProfile
from llm.candidate.model import AICandidateModel
from llm.feedback.service import FeedbackService
from llm.shared.models import QuestionAnswer, QuestionType
from llm.shared.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE
from llm.shared.logging_config import interview_logger, performance_logger

class InterviewService:
    """면접 서비스 - 모든 면접 관련 로직을 담당"""
    
    def __init__(self):
        """서비스 초기화"""
        # 🆕 통합 세션 관리자 (FinalInterviewSystem + PersonalizedInterviewSystem 통합)
        self.session_manager = SessionManager()
        
        # 🚀 새로운 턴제 면접관 시스템
        self.interviewer_service = InterviewerService()
        
        # 보조 서비스들
        self.document_processor = DocumentProcessor()
        self.ai_candidate_model = AICandidateModel()
        self.feedback_service = FeedbackService()
        
        # 🔄 더 이상 필요 없음 - SessionManager가 모든 세션을 관리
        # self.comparison_sessions = {}
        
        # 회사 이름 매핑
        self.company_name_map = {
            "네이버": "naver",
            "카카오": "kakao", 
            "라인": "line",
            "쿠팡": "coupang",
            "배달의민족": "baemin",
            "당근마켓": "daangn", 
            "토스": "toss"
        }
    
    def get_company_id(self, company_name: str) -> str:
        """회사 이름을 ID로 변환"""
        return self.company_name_map.get(company_name, company_name.lower())
    
    async def start_interview(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """일반 면접 시작 (SessionManager 사용)"""
        try:
            company_id = self.get_company_id(settings['company'])
            
            # 🆕 SessionManager를 통한 표준 면접 시작 (FinalInterviewSystem 기능 통합)
            session_id = self.session_manager.start_interview(
                company_id=company_id,
                position=settings['position'],
                candidate_name=settings['candidate_name']
            )
            
            interview_logger.info(f"면접 시작 - 세션 ID: {session_id}")
            
            return {
                "session_id": session_id,
                "message": "면접이 시작되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"면접 시작 오류: {str(e)}")
            raise Exception(f"면접 시작 중 오류가 발생했습니다: {str(e)}")
    
    async def upload_document(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """문서 업로드 및 분석"""
        try:
            # 파일 검증
            filename = file_data['filename']
            content = file_data['content']
            
            if not filename.lower().endswith(tuple(ALLOWED_FILE_EXTENSIONS)):
                raise ValueError("지원하지 않는 파일 형식입니다.")
            
            # 파일 저장
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_path = upload_dir / f"{uuid.uuid4()}_{filename}"
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # 문서 분석
            analyzed_content = await self._analyze_document_async(file_path)
            
            return {
                "file_id": str(file_path),
                "analyzed_content": analyzed_content,
                "message": "문서 업로드 및 분석이 완료되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"문서 업로드 오류: {str(e)}")
            raise Exception(f"문서 업로드 중 오류가 발생했습니다: {str(e)}")
    
    async def get_next_question(self, session_id: str) -> Dict[str, Any]:
        """다음 질문 가져오기 (SessionManager 사용)"""
        try:
            # 🆕 SessionManager를 통한 질문 가져오기
            question_data = self.session_manager.get_next_question(session_id)
            
            if not question_data:
                return {"completed": True, "message": "모든 질문이 완료되었습니다."}
            
            # 진행률 정보 계산
            session = self.session_manager.get_session(session_id)
            if session:
                current_index = session.current_question_count
                total_questions = len(session.question_plan)
                progress = (current_index / total_questions) * 100 if total_questions > 0 else 0
            else:
                current_index = 0
                total_questions = 20
                progress = 0
            
            return {
                "question": {
                    "id": question_data["question_id"],
                    "question": question_data["question_content"],
                    "category": question_data["question_type"],
                    "time_limit": question_data.get("time_limit", 120),
                    "keywords": question_data.get("keywords", [])
                },
                "question_index": current_index,
                "total_questions": total_questions,
                "progress": progress
            }
            
        except Exception as e:
            interview_logger.error(f"질문 가져오기 오류: {str(e)}")
            raise Exception(f"질문을 가져오는 중 오류가 발생했습니다: {str(e)}")
    
    async def submit_answer(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """답변 제출 (SessionManager 사용)"""
        try:
            session_id = answer_data['session_id']
            answer = answer_data['answer']
            
            # 🆕 SessionManager를 통한 답변 제출
            result = self.session_manager.submit_answer(session_id, answer)
            
            if "error" in result:
                raise Exception(result["error"])
            
            return {
                "status": result.get("status", "success"),
                "message": result.get("message", "답변이 성공적으로 제출되었습니다."),
                "question": result.get("question"),
                "answered_count": result.get("answered_count", 0),
                "total_questions": result.get("total_questions", 0)
            }
            
        except Exception as e:
            interview_logger.error(f"답변 제출 오류: {str(e)}")
            raise Exception(f"답변 제출 중 오류가 발생했습니다: {str(e)}")
    
    async def get_interview_results(self, session_id: str) -> Dict[str, Any]:
        """면접 결과 조회 (SessionManager 사용)"""
        try:
            # 🆕 SessionManager를 통한 면접 평가
            results = self.session_manager.evaluate_interview(session_id)
            
            if "error" in results:
                raise ValueError(results["error"])
            
            # 🧹 면접 완료 시 페르소나 캐시 정리 (비교 면접인 경우)
            if session_id.startswith("comp_"):
                try:
                    self.session_manager.comparison_session_manager.clear_session_persona(session_id)
                    interview_logger.info(f"🧹 [CLEANUP] 면접 완료 - 페르소나 캐시 정리: {session_id}")
                except Exception as cleanup_error:
                    interview_logger.warning(f"⚠️ [CLEANUP] 페르소나 캐시 정리 실패: {cleanup_error}")
            
            # 결과가 이미 완전한 형태로 반환됨
            return results
            
        except Exception as e:
            interview_logger.error(f"결과 조회 오류: {str(e)}")
            raise Exception(f"결과를 조회하는 중 오류가 발생했습니다: {str(e)}")
    
    async def start_ai_competition(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """AI 지원자와의 경쟁 면접 시작 (SessionManager 사용)"""
        try:
            interview_logger.info("AI 비교 면접 시작")
            
            # 🆕 DB 기반 정보가 있으면 사용, 없으면 기존 방식
            if settings.get('company_id') and settings.get('position_id'):
                company_id = settings['company_id']
                interview_logger.info(f"📋 DB 기반 정보 사용: company_id={company_id}, position_id={settings.get('position_id')}")
            else:
                # 기존 방식: 회사명으로 company_id 찾기
                company_id = self.get_company_id(settings['company'])
            
            # 🆕 SessionManager를 통한 비교 면접 시작 (새로운 20개 질문 시스템)
            comparison_session_id = await self.session_manager.start_comparison_interview(
                company_id=company_id,
                position=settings['position'],
                user_name=settings['candidate_name'],
                ai_name="춘식이",
                posting_id=settings.get('posting_id'),  # 🆕 posting_id 전달
                position_id=settings.get('position_id')  # 🆕 position_id 전달
            )
            
            # AI 이름 가져오기
            from llm.core.llm_manager import LLMProvider
            ai_name = self.ai_candidate_model.get_ai_name(LLMProvider.OPENAI_GPT4O_MINI)
            
            # 랜덤으로 시작자 결정
            import random
            starts_with_user = random.choice([True, False])
            
            if starts_with_user:
                # 사용자부터 시작 - 첫 질문 가져오기
                first_question = self.session_manager.get_comparison_next_question(comparison_session_id)
                
                return {
                    "session_id": comparison_session_id,
                    "comparison_session_id": comparison_session_id,
                    "user_session_id": comparison_session_id + "_user",
                    "ai_session_id": comparison_session_id + "_ai",
                    "question": first_question,
                    "current_phase": "user_turn",
                    "current_respondent": settings['candidate_name'],
                    "question_index": 1,
                    "total_questions": 20,
                    "ai_name": ai_name,
                    "starts_with_user": True,
                    "message": f"{settings['candidate_name']}님부터 시작합니다"
                }
            else:
                # AI부터 시작 - 첫 질문도 함께 제공
                first_question = self.session_manager.get_comparison_next_question(comparison_session_id)
                
                return {
                    "session_id": comparison_session_id,
                    "comparison_session_id": comparison_session_id,
                    "user_session_id": comparison_session_id + "_user",
                    "ai_session_id": comparison_session_id + "_ai",
                    "question": first_question,
                    "current_phase": "ai_turn",
                    "current_respondent": ai_name,
                    "question_index": 1,
                    "total_questions": 20,
                    "ai_name": ai_name,
                    "user_name": settings['candidate_name'],
                    "starts_with_user": False,
                    "message": f"{ai_name}부터 시작합니다"
                }
            
        except Exception as e:
            interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}")
            raise Exception(f"AI 경쟁 면접 시작 중 오류가 발생했습니다: {str(e)}")
    
    async def get_ai_answer(self, session_id: str, question_id: str) -> Dict[str, Any]:
        """AI 지원자의 답변 생성"""
        try:
            # URL 디코딩
            import urllib.parse
            decoded_session_id = urllib.parse.unquote(session_id)
            
            # 세션 ID에서 회사와 포지션 파싱
            session_parts = decoded_session_id.split('_')
            company_id = session_parts[0] if len(session_parts) > 0 else "naver"
            position = "_".join(session_parts[1:-1]) if len(session_parts) > 2 else "백엔드 개발"
            
            # AI 세션 시작하고 질문 가져오기
            ai_session_id = self.ai_candidate_model.start_ai_interview(company_id, position)
            ai_question_data = self.ai_candidate_model.get_ai_next_question(ai_session_id)
            
            if ai_question_data:
                question_content = ai_question_data["question_content"]
                question_intent = ai_question_data["question_intent"]
                question_type = ai_question_data["question_type"]
            else:
                # 폴백 질문
                if question_id == "q_1":
                    question_content = "춘식이, 자기소개를 부탁드립니다."
                    question_intent = "지원자의 기본 정보와 성격, 역량을 파악"
                    question_type = "INTRO"
                elif question_id == "q_2":
                    question_content = f"춘식이께서 네이버에 지원하게 된 동기는 무엇인가요?"
                    question_intent = "회사에 대한 관심도와 지원 동기 파악"
                    question_type = "MOTIVATION"
                else:
                    question_content = "춘식이에 대해 더 알려주세요."
                    question_intent = "일반적인 평가"
                    question_type = "HR"
            
            # AI 답변 생성
            from llm.candidate.model import AnswerRequest
            from llm.shared.models import QuestionType
            from llm.candidate.quality_controller import QualityLevel
            from llm.core.llm_manager import LLMProvider
            
            # QuestionType 매핑
            question_type_map = {
                "INTRO": QuestionType.INTRO,
                "MOTIVATION": QuestionType.MOTIVATION,
                "HR": QuestionType.HR,
                "TECH": QuestionType.TECH,
                "COLLABORATION": QuestionType.COLLABORATION
            }
            
            answer_request = AnswerRequest(
                question_content=question_content,
                question_type=question_type_map.get(question_type, QuestionType.HR),
                question_intent=question_intent,
                company_id=company_id,
                position=position,
                quality_level=QualityLevel.GOOD,
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            # 🔄 단독 AI 답변 생성 (세션 없음 - 매번 새로운 페르소나)
            interview_logger.info(f"🎭 [STANDALONE AI] 단독 AI 답변 생성 (세션 무관): {company_id} - {position}")
            ai_answer = self.ai_candidate_model.generate_answer(answer_request, persona=None)
            
            if not ai_answer:
                raise Exception("AI 답변 생성에 실패했습니다.")
            
            return {
                "question": question_content,
                "questionType": question_type,
                "questionIntent": question_intent,
                "answer": ai_answer.answer_content,
                "time_spent": 60,
                "score": 85,
                "quality_level": ai_answer.quality_level.value,
                "persona_name": ai_answer.persona_name
            }
            
        except Exception as e:
            interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
            raise Exception(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")
    
    async def submit_comparison_user_turn(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """비교 면접 사용자 턴 답변 제출 (SessionManager 사용)"""
        try:
            comparison_session_id = answer_data['comparison_session_id']
            answer = answer_data['answer']
            
            # 🆕 SessionManager를 통한 비교 세션 답변 제출 (턴 관리는 내부에서 처리됨)
            result = self.session_manager.submit_comparison_answer(
                comparison_session_id, answer, "human"
            )
            
            # 세션 상태 확인
            session = self.session_manager.get_comparison_session(comparison_session_id)
            interview_logger.info(f"🔍 사용자 답변 제출 후 세션 상태: current_question_index={session.current_question_index}, total_questions={session.total_questions}, is_complete={session.is_complete()}")
            
            # 🆕 면접 완료 확인 (세션의 is_complete 메서드 사용)
            if session and session.is_complete():
                interview_logger.info(f"✅ 사용자 턴에서 면접 완료 확인: {session.current_question_index}/{session.total_questions}")
                return {
                    "status": "success",
                    "message": "비교 면접이 완료되었습니다",
                    "next_phase": "completed",
                    "interview_status": "completed",
                    "progress": {
                        "current": session.current_question_index,
                        "total": session.total_questions,
                        "percentage": 100
                    }
                }
            
            return {
                "status": "success", 
                "message": "사용자 답변이 제출되었습니다",
                "next_phase": session.current_phase,  # 세션에서 관리되는 현재 페이즈
                "submission_result": result,
                "next_question": result.get("next_question"),  # 둘 다 답변했을 때의 다음 질문
                "progress": {
                    "current": session.current_question_index + 1,  # 현재 진행 중인 질문 번호
                    "total": session.total_questions,
                    "percentage": ((session.current_question_index + 1) / session.total_questions) * 100
                }
            }
            
        except Exception as e:
            interview_logger.error(f"사용자 턴 제출 오류: {str(e)}")
            raise Exception(f"답변 제출 중 오류가 발생했습니다: {str(e)}")
    
    async def process_comparison_ai_turn(self, ai_turn_data: Dict[str, Any]) -> Dict[str, Any]:
        """비교 면접 AI 턴 처리 (SessionManager 사용)"""
        try:
            comparison_session_id = ai_turn_data['comparison_session_id']
            step = ai_turn_data.get('step', 'question')
            
            if step == 'question':
                # 🆕 SessionManager를 통한 AI 질문 생성
                ai_question = self.session_manager.get_comparison_next_question(comparison_session_id)
                
                if not ai_question:
                    raise Exception("AI 질문을 생성할 수 없습니다")
                
                return {
                    "status": "success",
                    "step": "question_generated",
                    "ai_question": ai_question,
                    "message": "AI 질문이 생성되었습니다. 2-3초 후 답변이 생성됩니다."
                }
                
            elif step == 'answer':
                # AI 답변 생성 및 제출
                session = self.session_manager.get_comparison_session(comparison_session_id)
                if not session:
                    raise ValueError("비교 세션을 찾을 수 없습니다")
                
                # AI 답변 생성 로직 (기존과 동일)
                from llm.candidate.model import AnswerRequest
                from llm.shared.models import QuestionType
                from llm.candidate.quality_controller import QualityLevel
                from llm.core.llm_manager import LLMProvider
                
                # 현재 질문 가져오기 (SessionManager에서 다음 질문 조회를 통해 현재 질문 확인)
                current_question = self.session_manager.get_comparison_next_question(comparison_session_id)
                ai_question_content = current_question.get("question_content", "자기소개를 해주세요.") if current_question else "자기소개를 해주세요."
                
                answer_request = AnswerRequest(
                    question_content=ai_question_content,
                    question_type=QuestionType.HR,
                    question_intent="AI 지원자 역량 평가",
                    company_id=session.company_id,
                    position=getattr(session, 'position', '백엔드 개발자'),  # 세션에서 position 가져오기
                    quality_level=QualityLevel.GOOD,
                    llm_provider=LLMProvider.OPENAI_GPT4O_MINI
                )
                
                # 디버깅을 위한 로깅
                interview_logger.info(f"🎯 AI 답변 생성 요청: {session.company_id} - {getattr(session, 'position', '백엔드 개발자')}")
                interview_logger.info(f"📝 질문 내용: {ai_question_content}")
                
                # 🆕 세션별 페르소나 조회 및 생성
                session_persona = self.session_manager.comparison_session_manager.get_session_persona(comparison_session_id)
                
                if not session_persona:
                    # 페르소나가 없으면 생성하고 캐시에 저장
                    interview_logger.info(f"🎭 [PERSONA] 세션 페르소나 생성 중: {comparison_session_id}")
                    session_persona = self.ai_candidate_model.create_persona_for_interview(
                        session.company_id, 
                        getattr(session, 'position', '백엔드 개발자')
                    )
                    
                    if session_persona:
                        # 생성된 페르소나를 세션에 저장
                        self.session_manager.comparison_session_manager.set_session_persona(comparison_session_id, session_persona)
                        interview_logger.info(f"✅ [PERSONA] 페르소나 생성 및 저장 완료: {session_persona.name}")
                    else:
                        interview_logger.error(f"❌ [PERSONA] 페르소나 생성 실패: {comparison_session_id}")
                else:
                    interview_logger.info(f"✅ [PERSONA] 기존 세션 페르소나 재사용: {session_persona.name}")
                
                # 페르소나와 함께 답변 생성
                ai_answer_response = self.ai_candidate_model.generate_answer(answer_request, persona=session_persona)
                
                interview_logger.info(f"✅ AI 답변 생성 완료: 페르소나={ai_answer_response.persona_name}")
                
                if ai_answer_response.error:
                    interview_logger.error(f"❌ AI 답변 생성 실패: {ai_answer_response.error}")
                    raise Exception(f"AI 답변 생성 실패: {ai_answer_response.error}")
                
                # 🆕 SessionManager를 통한 AI 답변 제출 (턴 관리는 내부에서 처리됨)
                ai_submit_result = self.session_manager.submit_comparison_answer(
                    comparison_session_id, ai_answer_response.answer_content, "ai"
                )
                
                # 🆕 세션 완료 확인 (세션의 is_complete 메서드 사용)
                updated_session = self.session_manager.get_comparison_session(comparison_session_id)
                interview_logger.info(f"🔍 AI 답변 제출 후 세션 상태: current_question_index={updated_session.current_question_index}, total_questions={updated_session.total_questions}, is_complete={updated_session.is_complete()}")
                
                # 세션 완료 여부 확인
                if updated_session and updated_session.is_complete():
                    interview_logger.info(f"✅ 비교 면접 완료: {updated_session.current_question_index}/{updated_session.total_questions}")
                    return {
                        "status": "success",
                        "step": "answer_generated",
                        "interview_status": "completed",
                        "ai_answer": {
                            "content": ai_answer_response.answer_content,
                            "persona_name": ai_answer_response.persona_name,
                            "confidence": ai_answer_response.confidence_score
                        },
                        "message": f"비교 면접이 완료되었습니다 ({updated_session.current_question_index}/{updated_session.total_questions} 질문 완료)"
                    }
                else:
                    interview_logger.info(f"🔄 면접 계속: {updated_session.current_question_index + 1}/{updated_session.total_questions} 질문 진행 중")
                    return {
                        "status": "success",
                        "step": "answer_generated", 
                        "interview_status": "continue",
                        "ai_answer": {
                            "content": ai_answer_response.answer_content,
                            "persona_name": ai_answer_response.persona_name,
                            "confidence": ai_answer_response.confidence_score
                        },
                        "next_question": ai_submit_result.get("next_question"),  # 세션에서 반환된 다음 질문
                        "next_user_question": ai_submit_result.get("next_question"),  # 프론트엔드 호환성을 위한 중복 필드
                        "next_phase": updated_session.current_phase,  # 세션에서 관리되는 현재 페이즈
                        "progress": {
                            "current": updated_session.current_question_index + 1,  # 현재 진행 중인 질문 번호
                            "total": updated_session.total_questions,
                            "percentage": ((updated_session.current_question_index + 1) / updated_session.total_questions) * 100
                        }
                    }
            else:
                raise ValueError("유효하지 않은 step 값입니다")
                
        except Exception as e:
            interview_logger.error(f"AI 턴 처리 오류: {str(e)}")
            raise Exception(f"AI 턴 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def get_interview_history(self, user_id: str = None) -> Dict[str, Any]:
        """면접 기록 조회 (SessionManager 사용)"""
        try:
            completed_sessions = []
            
            # 🆕 SessionManager의 모든 세션 가져오기
            all_sessions = self.session_manager.get_all_sessions()
            
            for session_info in all_sessions:
                if session_info.get("state") == "completed":
                    completed_sessions.append({
                        "session_id": session_info["session_id"],
                        "settings": {
                            "company": session_info.get("company_id", "unknown"),
                            "position": session_info.get("position", "unknown"),
                            "user_name": session_info.get("candidate_name", session_info.get("user_name", "unknown"))
                        },
                        "completed_at": session_info.get("created_at", ""),
                        "total_score": 85,  # 기본값
                        "type": session_info.get("type", "standard")
                    })
            
            return {
                "total_interviews": len(completed_sessions),
                "interviews": completed_sessions
            }
            
        except Exception as e:
            interview_logger.error(f"기록 조회 오류: {str(e)}")
            raise Exception(f"기록을 조회하는 중 오류가 발생했습니다: {str(e)}")
    
    # 🚀 새로운 턴제 면접 시스템 메서드들
    
    async def start_turn_based_interview(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """턴제 면접 시작 - 새로운 InterviewerService 사용"""
        try:
            company_id = self.get_company_id(settings['company'])
            
            # 세션 ID 생성
            session_id = f"turn_{company_id}_{settings['position']}_{uuid.uuid4().hex[:8]}"
            
            # 사용자 이력서 정보 (임시)
            user_resume = {
                'name': settings['candidate_name'],
                'career_years': '3',
                'technical_skills': ['Python', 'Django', 'PostgreSQL', 'AWS']
            }
            
            # AI 지원자 페르소나 생성
            from llm.candidate.model import CandidatePersona
            ai_persona = CandidatePersona(
                name='춘식이', summary='3년차 Python 백엔드 개발자',
                background={'career_years': '3', 'current_position': '백엔드 개발자'},
                technical_skills=['Python', 'Django', 'PostgreSQL', 'AWS'],
                projects=[{'name': '이커머스 플랫폼', 'description': '대용량 트래픽 처리'}],
                experiences=[{'company': '스타트업', 'position': '개발자', 'period': '3년'}],
                strengths=['문제 해결', '학습 능력'], weaknesses=['완벽주의'],
                motivation='좋은 서비스를 만들고 싶어서',
                inferred_personal_experiences=[{'experience': '성장', 'lesson': '끊임없는 학습'}],
                career_goal='시니어 개발자로 성장', personality_traits=['친근함', '전문성'],
                interview_style='상호작용적', resume_id=1
            )
            
            # 세션 상태 저장 (간단한 메모리 저장)
            if not hasattr(self, 'turn_based_sessions'):
                self.turn_based_sessions = {}
            
            self.turn_based_sessions[session_id] = {
                'user_resume': user_resume,
                'ai_persona': ai_persona,
                'company_id': company_id,
                'qa_history': [],
                'user_answers': [],
                'ai_answers': [],
                'created_at': time.time()
            }
            
            # 첫 질문 생성
            first_question = self.interviewer_service.generate_next_question(
                user_resume, ai_persona, company_id
            )
            
            interview_logger.info(f"턴제 면접 시작 - 세션 ID: {session_id}")
            
            return {
                "session_id": session_id,
                "question": first_question,
                "total_question_limit": self.interviewer_service.total_question_limit,
                "current_interviewer": self.interviewer_service._get_current_interviewer(),
                "questions_asked": self.interviewer_service.questions_asked_count,
                "message": "턴제 면접이 시작되었습니다."
            }
            
        except Exception as e:
            interview_logger.error(f"턴제 면접 시작 오류: {str(e)}")
            raise Exception(f"턴제 면접 시작 중 오류가 발생했습니다: {str(e)}")
    
    async def get_turn_based_question(self, session_id: str, user_answer: str = None) -> Dict[str, Any]:
        """턴제 면접 다음 질문 가져오기"""
        try:
            if not hasattr(self, 'turn_based_sessions') or session_id not in self.turn_based_sessions:
                raise ValueError("세션을 찾을 수 없습니다")
            
            session_data = self.turn_based_sessions[session_id]
            
            # 사용자 답변 저장
            if user_answer:
                session_data['user_answers'].append(user_answer)
                
                # AI 답변 생성 (간단한 구현)
                ai_answer = "저는 기술적 완성도를 중시하며, 코드 리뷰와 테스트를 통해 안정적인 서비스를 만들려고 노력합니다."
                session_data['ai_answers'].append(ai_answer)
            
            # 다음 질문 생성
            next_question = self.interviewer_service.generate_next_question(
                session_data['user_resume'],
                session_data['ai_persona'], 
                session_data['company_id'],
                session_data['qa_history'],
                user_answer,
                session_data['ai_answers'][-1] if session_data['ai_answers'] else None
            )
            
            # 면접 종료 확인
            if next_question.get('is_final'):
                return {
                    "completed": True,
                    "message": next_question['question'],
                    "final_stats": {
                        "total_questions": self.interviewer_service.questions_asked_count,
                        "interviewer_stats": self.interviewer_service.interviewer_turn_state
                    }
                }
            
            # 턴 전환 확인
            if next_question.get('force_turn_switch'):
                # 다시 질문 생성 시도
                next_question = self.interviewer_service.generate_next_question(
                    session_data['user_resume'],
                    session_data['ai_persona'], 
                    session_data['company_id'],
                    session_data['qa_history']
                )
            
            # QA 히스토리 업데이트
            session_data['qa_history'].append({
                'question': next_question['question'],
                'interviewer_type': next_question['interviewer_type']
            })
            
            return {
                "question": next_question,
                "session_stats": {
                    "questions_asked": self.interviewer_service.questions_asked_count,
                    "remaining_questions": self.interviewer_service.total_question_limit - self.interviewer_service.questions_asked_count,
                    "current_interviewer": self.interviewer_service._get_current_interviewer(),
                    "turn_states": self.interviewer_service.interviewer_turn_state
                }
            }
            
        except Exception as e:
            interview_logger.error(f"턴제 질문 가져오기 오류: {str(e)}")
            raise Exception(f"질문을 가져오는 중 오류가 발생했습니다: {str(e)}")
    
    # 헬퍼 메소드들
    
    async def _generate_personalized_profile(self, documents: List[str]) -> UserProfile:
        """문서 기반 사용자 프로필 생성 (필요시 사용)"""
        try:
            profile = None
            
            for doc_path in documents:
                if os.path.exists(doc_path):
                    profile = await asyncio.to_thread(
                        self.document_processor.process_document, 
                        doc_path
                    )
                    break
            
            if not profile:
                # 기본 프로필 생성
                profile = UserProfile(
                    name="지원자",
                    background={"career_years": "3", "education": "대학교 졸업"},
                    technical_skills=["Java", "Spring", "MySQL"],
                    projects=[{"name": "웹 서비스 개발", "description": "백엔드 API 개발"}],
                    experiences=[{"company": "이전 회사", "role": "백엔드 개발자", "duration": "2년"}],
                    strengths=["문제해결능력", "커뮤니케이션"],
                    keywords=["개발", "협업", "성장"],
                    career_goal="시니어 개발자로 성장",
                    unique_points=["빠른 학습 능력"]
                )
            
            return profile
            
        except Exception as e:
            interview_logger.error(f"프로필 생성 오류: {str(e)}")
            return None
    
    async def _analyze_document_async(self, file_path: Path) -> Dict:
        """문서 분석 (비동기)"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.document_processor.process_document,
                str(file_path)
            )
            return result
        except Exception as e:
            interview_logger.error(f"문서 분석 오류: {str(e)}")
            return {}