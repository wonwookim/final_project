import os
import json
from .process_single_qa import SingleQAProcessor
from .final_eval import run_final_evaluation_from_realtime
from .supabase_client import SupabaseManager
from .plan_eval import generate_interview_plan
from typing import Tuple, Optional
import re

class InterviewEvaluationService:
    # 클래스 변수로 모델 인스턴스 저장 (싱글톤 패턴)
    _shared_processor = None
    
    def __init__(self):
        """면접 평가 서비스 초기화"""
        self.processor = None
        self.db_manager = None
        self._initialize_processor()
        self._initialize_db()
    
    def _initialize_processor(self):
        """프로세서 초기화 (모델만 미리 로드)"""
        try:
            if InterviewEvaluationService._shared_processor is None:
                print("ML 모델과 임베딩 모델을 최초 로드 중...")
                # 모델 로딩만 미리 수행
                from .num_eval import load_model, load_encoder, MODEL_PATH, ENCODER_NAME
                ml_model = load_model(MODEL_PATH)
                encoder = load_encoder(ENCODER_NAME)
                InterviewEvaluationService._shared_processor = {
                    'ml_model': ml_model,
                    'encoder': encoder
                }
                print("모델 로드 완료! (이후 요청에서 재사용됨)")
            else:
                print("기존 로드된 모델 재사용")
            
            self.processor = InterviewEvaluationService._shared_processor
            
        except Exception as e:
            print(f"WARNING: 모델 로드 실패: {str(e)}")
            print(f"상세 에러: {type(e).__name__}: {str(e)}")
            self.processor = None
    
    def _initialize_db(self):
        """Supabase 데이터베이스 초기화"""
        try:
            self.db_manager = SupabaseManager()
            print("SUCCESS: 데이터베이스 연결 성공")
        except Exception as e:
            print(f"WARNING: 데이터베이스 연결 실패: {str(e)}")
            self.db_manager = None
    
    
    def _create_interview_session(self, user_id: int, ai_resume_id: Optional[int] = None, 
                                 user_resume_id: Optional[int] = None, posting_id: Optional[int] = None,
                                 company_id: Optional[int] = None, position_id: Optional[int] = None) -> Optional[int]:
        """새로운 면접 세션 생성"""
        if self.db_manager:
            try:
                interview_id = self.db_manager.save_interview_session(
                    user_id=user_id,
                    ai_resume_id=ai_resume_id,
                    user_resume_id=user_resume_id,
                    posting_id=posting_id,
                    company_id=company_id,
                    position_id=position_id
                )
                return interview_id
            except Exception as e:
                print(f"WARNING: 면접 세션 생성 실패: {str(e)}")
        return None
    
    def _evaluate_single_question(self, qa_pair, company_info, question_index, position_info=None, posting_info=None, resume_info=None):
        """단일 질문 평가 (공유 모델 사용)"""
        try:
            print(f"\n--- Q{question_index} 평가 중 ---")
            
            # 동적으로 SingleQAProcessor 생성 (미리 로드된 모델 사용)
            if not self.processor:
                raise ValueError("ML 모델이 로드되지 않았습니다.")
            
            from .num_eval import evaluate_single_qa as num_evaluate_single_qa
            from .text_eval import evaluate_single_qa_with_intent_extraction
            
            # ML 점수 계산 (미리 로드된 모델 사용)
            ml_score = num_evaluate_single_qa(
                qa_pair.question, qa_pair.answer, 
                self.processor['ml_model'], self.processor['encoder']
            )
            
            # LLM 평가 수행
            llm_result = evaluate_single_qa_with_intent_extraction(
                qa_pair.question, qa_pair.answer, company_info, 
                position_info, posting_info, resume_info
            )
            
            result = {
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "intent": llm_result["extracted_intent"],
                "ml_score": ml_score,
                "llm_evaluation": llm_result["evaluation"]
            }
            
            return {
                "question_index": question_index,
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "ml_score": result.get("ml_score", 0.0),
                "llm_evaluation": result.get("llm_evaluation", ""),
                "intent": result.get("intent", ""),
                "question_level": qa_pair.question_level if qa_pair.question_level else "unknown",
                "duration": qa_pair.duration
            }
        except Exception as e:
            print(f"ERROR: Q{question_index} 평가 실패: {str(e)}")
            return {
                "question_index": question_index,
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "ml_score": 0.0,
                "llm_evaluation": f"평가 중 오류 발생: {str(e)}",
                "intent": "",
                "question_level": "unknown",
                "duration": qa_pair.duration
            }
    
    def evaluate_multiple_questions(self, user_id: int, qa_pairs: list, 
                                   ai_resume_id: Optional[int] = None, user_resume_id: Optional[int] = None,
                                   posting_id: Optional[int] = None, company_id: Optional[int] = None,
                                   position_id: Optional[int] = None) -> dict:
        """
        여러 질문-답변 일괄 평가 후 자동으로 최종 평가 수행
        
        Args:
            user_id: 사용자 ID
            qa_pairs: 질문-답변 쌍 리스트
            기타 외래키 ID들
            
        Returns:
            dict: 전체 평가 결과 (개별 평가 + 최종 평가 + 계획)
        """
        try:
            if not self.processor:
                return {
                    "success": False,
                    "message": "ML 모델이 로드되지 않았습니다.",
                    "interview_id": None,
                    "total_questions": 0
                }
            
            # 1. 새 면접 세션 생성
            interview_id = self._create_interview_session(
                user_id=user_id,
                ai_resume_id=ai_resume_id,
                user_resume_id=user_resume_id,
                posting_id=posting_id,
                company_id=company_id,
                position_id=position_id
            )
            
            if not interview_id:
                print("WARNING: 면접 세션 생성 실패, 필수 필드만으로 재시도")
                try:
                    interview_id = self._create_interview_session(user_id=user_id)
                    print(f"재시도 결과: interview_id = {interview_id}")
                except Exception as e:
                    print(f"재시도 중 오류: {str(e)}")
            
            if not interview_id:
                error_msg = f"면접 세션 생성 실패 - user_id: {user_id}"
                print(f"CRITICAL ERROR: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "interview_id": None,
                    "total_questions": 0
                }
            
            # 2. 추가 정보 조회 (회사, 직군, 공고, 이력서)
            # 모든 정보 조회는 필수이며, 하나라도 실패하면 오류를 발생시킵니다.
            if not self.db_manager:
                raise RuntimeError("데이터베이스 연결이 설정되지 않았습니다.")

            # 회사 정보 조회 (필수)
            if not company_id:
                raise ValueError("company_id는 필수 파라미터입니다.")
            company_info = self.db_manager.get_company_info(company_id)
            if not company_info:
                raise ValueError(f"Company ID {company_id}에 해당하는 회사 정보를 찾을 수 없습니다.")
            print(f"SUCCESS: Company 정보 조회 완료 - {company_info.get('name')}")

            # 직군 정보 조회 (선택적이지만 없으면 경고)
            position_info = None
            if position_id:
                position_info = self.db_manager.get_position_info(position_id)
                if position_info:
                    print(f"SUCCESS: Position 정보 조회 완료 - {position_info.get('position_name')}")
                else:
                    print(f"WARNING: Position ID {position_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")

            # 공고 정보 조회 (선택적이지만 없으면 경고)
            posting_info = None
            if posting_id:
                posting_info = self.db_manager.get_posting_info(posting_id)
                if posting_info:
                    print(f"SUCCESS: Posting 정보 조회 완료")
                else:
                    print(f"WARNING: Posting ID {posting_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")

            # 이력서 정보 조회 (선택적이지만 없으면 경고)
            resume_info = None
            if ai_resume_id:
                resume_info = self.db_manager.get_ai_resume_info(ai_resume_id)
                if resume_info:
                    print(f"SUCCESS: AI Resume 정보 조회 완료")
                else:
                    print(f"WARNING: AI Resume ID {ai_resume_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")
            elif user_resume_id:
                resume_info = self.db_manager.get_user_resume_info(user_resume_id)
                if resume_info:
                    print(f"SUCCESS: User Resume 정보 조회 완료")
                else:
                    print(f"WARNING: User Resume ID {user_resume_id} 정보를 찾을 수 없습니다. 일반 평가로 진행됩니다.")
            
            # 3. 모든 필수 정보 조회 완료. 평가를 시작합니다.
            
            # 4. 각 질문-답변 쌍을 순차적으로 평가 (모델 재사용으로 빠른 처리)
            print(f"총 {len(qa_pairs)}개 질문 순차 평가 시작 (모델 재사용)...")
            
            per_question_results = []
            for i, qa_pair in enumerate(qa_pairs, 1):
                result = self._evaluate_single_question(qa_pair, company_info, i, position_info, posting_info, resume_info)
                per_question_results.append(result)
            
            print(f"SUCCESS: {len(per_question_results)}개 질문 평가 완료")
            
            # 5. 메모리 데이터 기반 최종 평가 수행
            print(f"\n--- 최종 평가 시작 ---")
            final_result = self.run_final_evaluation_from_memory(interview_id, per_question_results, company_info, position_info, posting_info, resume_info)
            
            # 최종 평가 결과를 API 응답 형식에 맞게 재구성
            # final_result가 실패했더라도 해당 내용을 담아서 반환
            response = {
                "success": final_result.get("success", False),
                "interview_id": interview_id,
                "message": final_result.get("message", f"전체 면접 평가 완료 ({len(qa_pairs)}개 질문)"),
                "total_questions": len(qa_pairs),
                "overall_score": final_result.get("overall_score"),
                "overall_feedback": final_result.get("overall_feedback"),
                "per_question_results": final_result.get("per_question", []), # 'per_question'을 'per_question_results'로 매핑
                "interview_plan": None # 계획 생성은 별도 API 호출
            }
            
            return response
            
        except ValueError as e:
            # 잘못된 파라미터나 데이터 문제
            print(f"PARAMETER ERROR: {str(e)}")
            return {
                "success": False,
                "message": f"파라미터 오류: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
        except RuntimeError as e:
            # 시스템 리소스 문제
            print(f"SYSTEM ERROR: {str(e)}")
            return {
                "success": False,
                "message": f"시스템 오류: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"UNEXPECTED ERROR: {error_details}")
            return {
                "success": False,
                "message": f"예상치 못한 오류 발생: {str(e)}",
                "interview_id": None,
                "total_questions": 0
            }
    

    def run_final_evaluation_from_memory(self, interview_id: int, per_question_results: list, company_info: dict, position_info=None, posting_info=None, resume_info=None) -> dict:
        """
        메모리 데이터를 기반으로 최종 평가 실행 후 DB에 저장
        
        Args:
            interview_id: 면접 세션 ID
            per_question_results: 개별 질문 평가 결과 리스트
            company_info: 회사 정보
            position_info: 직군 정보
            posting_info: 공고 정보
            resume_info: 이력서 정보
            
        Returns:
            dict: 최종 평가 결과
        """
        try:
            if not self.db_manager:
                return {
                    "success": False,
                    "message": "데이터베이스 연결이 없습니다.",
                    "overall_score": None,
                    "overall_feedback": None
                }
            
            # 1. realtime_data 형태로 변환
            realtime_data = []
            for item in per_question_results:
                realtime_data.append({
                    "question": item["question"],
                    "answer": item["answer"],
                    "intent": item["intent"],
                    "ml_score": item["ml_score"],
                    "llm_evaluation": item["llm_evaluation"]
                })
            
            # 2. 최종 평가 로직 실행 (메모리에서 처리)
            print("DEBUG: Calling final_eval.run_final_evaluation_from_realtime...")
            try:
                final_results = run_final_evaluation_from_realtime(
                    realtime_data=realtime_data, 
                    company_info=company_info,
                    position_info=position_info,
                    posting_info=posting_info,
                    resume_info=resume_info,
                    output_file=None  # 파일 저장 하지 않음
                )
            except Exception as e:
                import traceback
                print(f"CRITICAL_ERROR: Failed to run or import from final_eval.py: {traceback.format_exc()}")
                final_results = {"success": False, "message": str(e), "per_question": [], "overall_score": None, "overall_feedback": None}
            
            if not final_results:
                return {
                    "success": False,
                    "message": "최종 평가 실행 실패",
                    "overall_score": None,
                    "overall_feedback": None
                }
            
            # 3. 각 질문별 최종 평가 결과를 history_detail에 저장
            per_question_data = final_results.get("per_question", [])
            if per_question_data:
                print("개별 질문 최종 평가 결과를 DB에 저장 중...")
                for i, question_eval in enumerate(per_question_data, 1):
                    try:
                        # 원본 데이터에서 추가 정보 가져오기
                        original_data = per_question_results[i-1]
                        
                        qa_data = {
                            "question_index": i,
                            "question_id": i,
                            "question": question_eval.get("question", ""),
                            "answer": question_eval.get("answer", ""),
                            "intent": question_eval.get("intent", ""),
                            "question_level": original_data.get("question_level", "unknown"),
                            "who": "interviewer",
                            "sequence": i,
                            "duration": original_data.get("duration")
                        }
                        
                        # 최종 정제된 피드백 저장
                        final_feedback = {
                            "final_score": question_eval.get("final_score"),
                            "evaluation": question_eval.get("evaluation"),
                            "improvement": question_eval.get("improvement")
                        }
                        
                        detail_id = self.db_manager.save_qa_detail(
                            interview_id, 
                            qa_data, 
                            json.dumps(final_feedback, ensure_ascii=False)
                        )
                        print(f"SUCCESS: Q{i} 최종 평가 DB 저장 완료 (Detail ID: {detail_id})")
                        
                    except Exception as e:
                        print(f"WARNING: Q{i} 최종 평가 저장 실패: {str(e)}")
            
            # 4. 전체 평가 결과를 interview 테이블에 저장
            try:
                overall_data = {
                    "overall_score": final_results.get("overall_score"),
                    "overall_feedback": final_results.get("overall_feedback"),
                    "summary": final_results.get("summary")
                }
                self.db_manager.update_total_feedback(interview_id, overall_data)
                print("SUCCESS: 전체 평가 결과 DB 저장 완료")
                
            except Exception as e:
                print(f"WARNING: 전체 평가 결과 저장 실패: {str(e)}")
            
            return {
                "success": True,
                "overall_score": final_results.get("overall_score"),
                "overall_feedback": final_results.get("overall_feedback"),
                "summary": final_results.get("summary"),
                "per_question": final_results.get("per_question"),
                "message": "최종 평가 완료",
                "interview_id": interview_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"최종 평가 중 오류 발생: {str(e)}",
                "overall_score": None,
                "overall_feedback": None
            }

    def generate_interview_plans(self, interview_id: int) -> dict:
        """
        면접 준비 계획 생성 (DB 기반)
        
        Args:
            interview_id: 면접 세션 ID
            
        Returns:
            dict: 면접 준비 계획 결과
        """
        try:
            if not self.db_manager:
                return {
                    "success": False,
                    "message": "데이터베이스 연결이 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 1. 면접 데이터 조회 (총평 포함)
            interview_details = self.db_manager.get_interview_details(interview_id)
            
            if not interview_details or not interview_details['interview']:
                return {
                    "success": False,
                    "message": "면접 데이터를 찾을 수 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 2. total_feedback에서 전체 평가 결과 추출 및 유효성 검사
            total_feedback = interview_details['interview'].get('total_feedback')
            if not total_feedback:
                return {
                    "success": False,
                    "message": f"Interview ID {interview_id}에 대한 최종 평가 결과(total_feedback)가 없습니다.",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            if isinstance(total_feedback, str):
                try:
                    total_feedback = json.loads(total_feedback)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "message": "total_feedback 필드의 JSON 형식이 잘못되었습니다.",
                        "interview_plan": None,
                        "plan_id": None,
                        "interview_id": interview_id
                    }
            
            # 3. 면접 준비 계획 생성
            from .plan_eval import generate_interview_plan
            plan_data = generate_interview_plan(total_feedback)
            
            if not plan_data["success"]:
                return {
                    "success": False,
                    "message": f"면접 계획 생성 실패: {plan_data.get('error', 'Unknown error')}",
                    "interview_plan": None,
                    "plan_id": None,
                    "interview_id": interview_id
                }
            
            # 4. plans 테이블에 저장
            plan_id = self.db_manager.save_interview_plan(
                interview_id=interview_id,
                shortly_plan=plan_data["shortly_plan"],
                long_plan=plan_data["long_plan"]
            )
            
            plan_result = {
                "shortly_plan": plan_data["shortly_plan"],
                "long_plan": plan_data["long_plan"],
                "plan_id": plan_id
            }
            
            return {
                "success": True,
                "interview_plan": plan_result,
                "plan_id": plan_id,
                "message": "면접 준비 계획 생성 완료",
                "interview_id": interview_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"면접 계획 생성 중 오류 발생: {str(e)}",
                "interview_plan": None,
                "plan_id": None,
                "interview_id": interview_id
            }

