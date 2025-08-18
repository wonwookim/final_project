import json
import json
from typing import Dict, Any, List, Optional
import asyncio
import uuid
import time
import boto3
import os
from llm.interviewer.question_generator import QuestionGenerator
from llm.candidate.model import AICandidateModel, CandidatePersona
from llm.shared.models import AnswerRequest, QuestionType, LLMProvider
from llm.candidate.quality_controller import QualityLevel
from llm.shared.logging_config import interview_logger

from backend.services.Orchestrator import Orchestrator
from backend.services.supabase_client import get_supabase_client
from backend.services.existing_tables_service import existing_tables_service
from backend.services.gaze_service import gaze_analyzer
class InterviewService:
    def __init__(self):
        # 세션 상태 관리 (Orchestrator의 state를 여기로 이관)
        self.session_states: Dict[str, Dict[str, Any]] = {}
        self.active_orchestrators: Dict[str, Orchestrator] = {}
        self.question_generator = QuestionGenerator()
        self.ai_candidate_model = AICandidateModel()
        
        # 에이전트 핸들러는 Orchestrator로 이관됨
        
        self.company_name_map = {
            "네이버": "naver", "카카오": "kakao", "라인": "line",
            "라인플러스": "라인플러스", "쿠팡": "coupang", "배달의민족": "baemin",
            "당근마켓": "daangn", "토스": "toss"
        }

    def get_company_id(self, company_name: str) -> str:
        return self.company_name_map.get(company_name, company_name.lower())

    # 세션 관리 메서드들
    def get_active_sessions(self) -> List[str]:
        """현재 활성 세션 ID들을 반환"""
        return list(self.session_states.keys())
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """특정 세션의 상태를 반환"""
        return self.session_states.get(session_id)
    
    def has_active_session(self, session_id: str) -> bool:
        """세션이 활성 상태인지 확인"""
        return session_id in self.session_states
    
    def create_session_state(self, session_id: str, initial_settings: Dict[str, Any]) -> Dict[str, Any]:
        """새로운 세션 상태 생성"""
        session_state = {
            "turn_count": 0,
            "current_question": None,
            "qa_history": [],
            "is_completed": False,
            "start_time": time.perf_counter(),
            # 🆕 꼬리 질문 관리를 위한 필드들 추가
            "interviewer_turn_state": {
                'HR': {'main_question_asked': False, 'follow_up_count': 0},
                'TECH': {'main_question_asked': False, 'follow_up_count': 0},
                'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
            },
            "current_interviewer": None,
            # 🆕 TTS 통합 큐: {'type': '유형', 'content': 'TTS할 텍스트'} 형태의 딕셔너리 저장
            "tts_queue": [],
            # 🆕 중복 제거: qa_history에서 최신 데이터 추출
            **initial_settings
        }
        self.session_states[session_id] = session_state
        interview_logger.info(f"DEBUG: create_session_state - 세션 {session_id}이(가) self.session_states에 추가됨. 현재 self.session_states 키: {self.session_states.keys()}")
        return session_state
    
    def update_session_state(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """세션 상태 업데이트"""
        if session_id not in self.session_states:
            return False
        self.session_states[session_id].update(updates)
        return True
    
    def remove_session(self, session_id: str) -> bool:
        """세션 제거"""
        if session_id in self.session_states:
            del self.session_states[session_id]
        if session_id in self.active_orchestrators:
            del self.active_orchestrators[session_id]
        return True
    
    def get_session_or_error(self, session_id: str) -> tuple[Optional[Dict[str, Any]], Optional[Dict]]:
        """세션 상태를 가져오거나 에러 반환"""
        session_state = self.session_states.get(session_id)
        interview_logger.info(f"DEBUG: get_session_or_error - self.session_states에서 {session_id} 조회 결과: {bool(session_state)}. 현재 self.session_states 키: {self.session_states.keys()}")
        if not session_state:
            interview_logger.error(f"ERROR: get_session_or_error - 세션 {session_id}을(를) 찾을 수 없음.")
            return None, {"error": "유효하지 않은 세션 ID입니다."}
        if session_state.get('is_completed', False):
            return None, {"error": "이미 완료된 면접입니다."}
        return session_state, None

    async def _create_ai_persona(self, ai_candidate_model: AICandidateModel, company_id: str, position: str):
        try:
            persona = await asyncio.to_thread(
                ai_candidate_model.create_persona_for_interview, company_id, position
            )
            return persona if persona else ai_candidate_model._create_default_persona(company_id, position)
        except Exception as e:
            interview_logger.error(
                f"AI 페르소나 생성 실패(안전 폴백 적용): company_id={company_id}, position={position}, error={e}",
                exc_info=True
            )
            # 모델 내부 예외가 발생해도 서비스는 기본 페르소나로 계속 진행
            return ai_candidate_model._create_default_persona(company_id, position)

    async def _resolve_ai_resume_id(self, session_like: Dict[str, Any]) -> Optional[int]:
        """가능한 단서로 AI 이력서 ID를 유추합니다."""
        try:
            # 1) 이미 설정되어 있으면 사용
            if session_like.get('ai_resume_id'):
                return int(session_like['ai_resume_id'])

            client = get_supabase_client()

            # 2) position_id가 있으면 해당 포지션의 ai_resume 중 하나 선택
            position_id = session_like.get('position_id')
            if position_id:
                res = client.table('ai_resume').select('ai_resume_id').eq('position_id', position_id).limit(1).execute()
                if res.data:
                    return int(res.data[0]['ai_resume_id'])

            # 3) posting_id로 position_id를 복원 후 재시도
            posting_id = session_like.get('posting_id')
            if posting_id:
                try:
                    posting = await existing_tables_service.get_posting_by_id(posting_id)
                    if posting and posting.get('position_id'):
                        res = client.table('ai_resume').select('ai_resume_id').eq('position_id', posting['position_id']).limit(1).execute()
                        if res.data:
                            return int(res.data[0]['ai_resume_id'])
                except Exception:
                    pass

            # 4) 최후 수단: 아무 ai_resume 한 개
            res_any = client.table('ai_resume').select('ai_resume_id').limit(1).execute()
            if res_any.data:
                return int(res_any.data[0]['ai_resume_id'])
        except Exception as e:
            interview_logger.warning(f"ai_resume_id 유추 실패: {e}")
        return None

    def _get_orchestrator_or_error(self, session_id: str) -> tuple[Optional[Orchestrator], Optional[Dict]]:
        orchestrator = self.active_orchestrators.get(session_id)
        if not orchestrator:
            return None, {"error": "유효하지 않은 세션 ID입니다."}
        if orchestrator.state.get('is_completed', False):
            return None, {"error": "이미 완료된 면접입니다."}
        return orchestrator, None

    async def submit_user_answer(self, session_id: str, user_answer: str, time_spent: float = None) -> Dict[str, Any]:
        try:
            interview_logger.info(f"DEBUG: submit_user_answer - 호출됨 (session_id: {session_id}). 현재 self.session_states 키: {self.session_states.keys()}")
            session_state, error = self.get_session_or_error(session_id)
            if error: 
                return error

            interview_logger.info(f"👤 사용자 답변 제출: {session_id}")
            
            print(f"[Client] -> [InterviewService]")
            print(json.dumps({
                "session_id": session_id,
                "user_answer": user_answer,
                "time_spent": time_spent
            }, indent=2, ensure_ascii=False))
            
            # Orchestrator가 모든 것을 처리
            orchestrator = self.active_orchestrators.get(session_id)
            if not orchestrator:
                return {"error": "Orchestrator를 찾을 수 없습니다."}
            
            interview_logger.info(f"DEBUG: submit_user_answer - get_session_or_error 호출 직전 (session_id: {session_id})")
            result = await orchestrator.process_user_answer(user_answer, time_spent)

            # 면접이 완료되면 피드백 평가를 백그라운드로 트리거
            try:
                if isinstance(result, dict) and result.get('status') == 'completed':
                    interview_logger.info(f"🏁 완료 상태 수신. 피드백 트리거 실행: session_id={session_id}")
                    asyncio.create_task(self.trigger_feedback_for_session(session_id))
            except Exception as e:
                interview_logger.error(f"❌ 피드백 트리거 실패: session_id={session_id}, error={e}")

            return result

        except Exception as e:
            interview_logger.error(f"사용자 답변 제출 오류: {e}", exc_info=True)
            return {"error": f"답변 제출 중 오류가 발생했습니다: {str(e)}"}

    async def start_ai_competition(self, settings: Dict[str, Any], start_time: float = None) -> Dict[str, Any]:
        try:
            interview_logger.info(f"DEBUG: start_ai_competition - 함수 시작. settings: {settings.get('candidate_name')}")
            session_id = f"comp_{uuid.uuid4().hex[:12]}"
            interview_logger.info(f"DEBUG: start_ai_competition - 생성된 session_id: {session_id}")
            # 회사 식별자 분리: 모델/프롬프트용 문자열 코드 vs. DB용 숫자 ID
            company_code_for_persona = self.get_company_id(settings['company'])  # 예: 'naver', 'kakao'
            company_numeric_id = settings.get('company_id')  # DB의 정수 ID일 수 있음
            ai_persona = await self._create_ai_persona(self.ai_candidate_model, company_code_for_persona, settings['position'])
            ai_resume_id = getattr(ai_persona, 'resume_id', None) if ai_persona else None

            # 보강: persona에서 못 받은 경우 다양한 단서로 유추
            if not ai_resume_id:
                ai_resume_id = await self._resolve_ai_resume_id(settings)
            
            # 세션 상태 생성
            initial_settings = {
                'total_question_limit': 2,  # 디버깅용 - 실제 운영시에는 15로 변경
                'company_id': company_code_for_persona,  # 모델/질문 생성 로직과 호환되는 문자열 코드 유지
                'company_numeric_id': company_numeric_id,  # DB 연동을 위한 숫자 ID 별도 보관
                'position': settings['position'],
                'position_id': settings.get('position_id'),
                'posting_id': settings.get('posting_id'),
                'user_id': settings.get('user_id'),
                'user_name': settings['candidate_name'],
                'ai_persona': ai_persona,
                'ai_resume_id': int(ai_resume_id) if ai_resume_id else None
            }
            # 사용자 이력서 ID를 세션에 저장 (있으면)
            if settings.get('user_resume_id'):
                try:
                    initial_settings['user_resume_id'] = int(settings['user_resume_id'])
                except Exception:
                    initial_settings['user_resume_id'] = None

            # --- ▼▼▼ 바로 이 부분을 추가해주세요! ▼▼▼ ---
            initial_settings['calibration_data'] = settings.get('calibration_data')
            interview_logger.info(f"DEBUG: start_ai_competition - create_session_state 호출 직전 (session_id: {session_id})")
            session_state = self.create_session_state(session_id, initial_settings)
            interview_logger.info(f"DEBUG: start_ai_competition - create_session_state 호출 완료 (session_id: {session_id}, keys: {session_state.keys()})")
            
            # Orchestrator 생성 - 에이전트들도 전달
            orchestrator = Orchestrator(
                session_id=session_id, 
                session_state=session_state,
                question_generator=self.question_generator,
                ai_candidate_model=self.ai_candidate_model
            )
            self.active_orchestrators[session_id] = orchestrator
            interview_logger.info(f"DEBUG: start_ai_competition - Orchestrator 활성화 완료 (session_id: {session_id}). 현재 active_orchestrators 키: {self.active_orchestrators.keys()}")
            
            interview_logger.info(f"AI 경쟁 면접 시작: {session_id}")
            
            print(f"[Client] -> [InterviewService]")
            print(json.dumps(settings, indent=2, ensure_ascii=False))
            
            # ⚡ INTRO만 처리하고 즉시 API 응답 (속도 최적화)
            result = await orchestrator._process_initial_flow()
            # session_id는 이미 _process_initial_flow에서 포함됨

            # 🔍 DEBUG: 최종 API 응답 구조 확인
            print(f"[🔍 API_RESPONSE_DEBUG] === 최종 API 응답 구조 분석 ===")
            print(f"[🔍 API_RESPONSE_DEBUG] result 타입: {type(result)}")
            print(f"[🔍 API_RESPONSE_DEBUG] result 키들: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if isinstance(result, dict):
                for key, value in result.items():
                    if key in ['intro_audio', 'first_question_audio']:
                        print(f"[🔍 API_RESPONSE_DEBUG] {key}: {bool(value)} ({type(value).__name__}) - 길이: {len(str(value)) if value else 0}")
                    else:
                        print(f"[🔍 API_RESPONSE_DEBUG] {key}: {bool(value)} ({type(value).__name__})")
                        if key == 'first_question' and value:
                            print(f"[🔍 API_RESPONSE_DEBUG] first_question 내용: {str(value)[:50]}...")
            
            print(f"[🔍 API_RESPONSE_DEBUG] === FastAPI로 전달될 result ===")
            
            interview_logger.info(f"DEBUG: start_ai_competition - 최종 응답 반환 직전 (session_id: {session_id})")
            return result

        except Exception as e:
            interview_logger.error(f"AI 경쟁 면접 시작 오류: {e}", exc_info=True)
            return {"error": f"면접 시작 중 오류가 발생했습니다: {str(e)}"}

    def get_interview_flow_status(self, session_id: str) -> Dict[str, Any]:
        """현재 면접 진행 상태와 다음 액션을 반환"""
        session_state, error = self.get_session_or_error(session_id)
        if error:
            return error
        
        return session_state

    async def trigger_feedback_for_session(self, session_id: str) -> None:
        """면접 완료 시 세션의 QA 히스토리를 기반으로 피드백 평가/계획을 백그라운드에서 실행"""
        try:
            from llm.feedback.api_models import QuestionAnswerPair
            from llm.feedback.api_service import InterviewEvaluationService
            import os
            import glob
            interview_logger.info(f"피드백 트리거 시작: {session_id}")
            await asyncio.sleep(5)  # CPU 사용 없이 5초 비동기 대기
            interview_logger.info(f"피드백 트리거 종료: {session_id}")
            session_state = self.session_states.get(session_id)
            if not session_state:
                return

            qa_history = session_state.get('qa_history', [])
            if not qa_history:
                return

            user_id = session_state.get('user_id')
            # 평가 서비스는 숫자 company_id를 요구하므로 numeric 우선 사용
            company_id = session_state.get('company_numeric_id') or session_state.get('company_id')
            position_id = session_state.get('position_id')
            posting_id = session_state.get('posting_id')
            ai_resume_id = session_state.get('ai_resume_id') or await self._resolve_ai_resume_id(session_state)
            user_resume_id = session_state.get('user_resume_id')

            # 필수 값(company_id, user_id)이 없으면 실행하지 않음
            interview_logger.info(f"🔍 피드백 실행 조건 체크: company_id={company_id}, user_id={user_id}")
            if not company_id or not user_id:
                interview_logger.warning(f"⚠️ 필수값 누락으로 피드백 실행 중단: company_id={company_id}, user_id={user_id}")
                return

            # 사용자/AI 분리
            user_qas = [qa for qa in qa_history if qa.get('answerer') == 'user']
            ai_qas = [qa for qa in qa_history if qa.get('answerer') == 'ai']
            interview_logger.info(f"📊 QA 히스토리 분석: user_qas={len(user_qas)}개, ai_qas={len(ai_qas)}개")

            # QuestionAnswerPair 목록 생성
            def build_pairs(items: list) -> list:
                pairs: list[QuestionAnswerPair] = []
                for qa in items:
                    pairs.append(QuestionAnswerPair(
                        question=qa.get('question', ''),
                        answer=qa.get('answer', ''),
                        duration=qa.get('duration') or 120,
                        question_level=qa.get('question_level') or 1,
                    ))
                return pairs

            evaluation_service = InterviewEvaluationService()
            shared_interview_id = None

            # 통합 평가 (사용자와 AI 지원자를 하나의 interview 세션에 저장)
            if user_qas or ai_qas:
                interview_logger.info(f"🔄 통합 면접 평가 시작: user={len(user_qas)}개, ai={len(ai_qas)}개 질문")
                
                user_pairs = build_pairs(user_qas) if user_qas else []
                ai_pairs = build_pairs(ai_qas) if ai_qas else []
                
                # 새로운 통합 평가 메서드 호출
                combined_eval = evaluation_service.evaluate_combined_interview(
                    user_id=user_id,
                    user_qas=user_pairs,
                    ai_qas=ai_pairs,
                    ai_resume_id=ai_resume_id,
                    user_resume_id=user_resume_id,
                    posting_id=posting_id,
                    company_id=company_id,
                    position_id=position_id
                )
                
                if combined_eval and combined_eval.get('success'):
                    shared_interview_id = combined_eval['interview_id']
                    interview_logger.info(f"✅ 통합 면접 평가 완료: interview_id={shared_interview_id}")
                    interview_logger.info(f"📊 평가 결과: 사용자 점수={combined_eval.get('user_score', 0):.2f}, AI 점수={combined_eval.get('ai_score', 0):.2f}")
                    
                    # 🆕 임시 시선 추적 파일 처리 (interview_id 생성 후)
                    if shared_interview_id:
                        await self._process_temporary_gaze_file(session_id, shared_interview_id)
                        # 🆕 시선 분석 데이터 지연 처리 (Pre-signed URL 기반)
                        await self._process_gaze_data_after_evaluation(shared_interview_id, session_id, user_id)
                    
                    # 개선 계획 생성
                    try:
                        evaluation_service.generate_interview_plans(shared_interview_id)
                        interview_logger.info(f"✅ 면접 계획 생성 완료: interview_id={shared_interview_id}")
                    except Exception as e:
                        interview_logger.error(f"❌ 면접 계획 생성 실패: {str(e)}", exc_info=True)
                else:
                    interview_logger.error(f"❌ 통합 면접 평가 실패: {combined_eval}")
            else:
                interview_logger.warning(f"⚠️ 사용자/AI QA 모두 없어서 평가를 건너뜀")

        except Exception as e:
            interview_logger.error(f"❌ 피드백 처리 중 예외 발생: {str(e)}", exc_info=True)
            return

    async def _process_temporary_gaze_file(self, session_id: str, interview_id: int) -> None:
        """임시 파일을 Boto3로 S3에 업로드하고, 그 메타데이터를 Supabase DB에 저장한 후, 분석을 트리거"""
        try:
            from datetime import datetime
            import glob

            # 1. 임시 파일 찾기
            temp_folder = "backend/uploads/temp_gaze"
            temp_files = glob.glob(os.path.join(temp_folder, f"{session_id}.*"))

            if not temp_files:
                interview_logger.info(f"🔍 세션 {session_id}에 대한 임시 시선 추적 파일이 없습니다.")
                return

            temp_file_path = temp_files[0]
            interview_logger.info(f"📁 임시 파일 발견: {temp_file_path}")

            # 2. Boto3 S3 클라이언트 생성
            access_key = os.getenv('AWS_ACCESS_KEY_ID')
            secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            region = os.getenv('AWS_REGION', 'ap-northeast-2')
            bucket_name = 'betago-s3'

            if not access_key or not secret_key:
                interview_logger.error("❌ AWS 자격증명이 .env 파일에 설정되지 않았습니다.")
                return

            s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)

            # 3. S3에 업로드할 경로 및 파일명 결정
            file_extension = os.path.splitext(temp_file_path)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"gaze_tracking/{interview_id}/gaze_video_{timestamp}{file_extension}"

            # 4. S3에 파일 업로드
            interview_logger.info(f"📤 S3에 파일 업로드 시작: Bucket={bucket_name}, Key={s3_key}")
            s3_client.upload_file(temp_file_path, bucket_name, s3_key)
            interview_logger.info(f"✅ S3 업로드 성공: {s3_key}")

            # 5. Supabase DB에 메타데이터 저장
            try:
                supabase_db_client = get_supabase_client()

                # 세션에서 user_id 가져오기
                session_state = self.session_states.get(session_id)
                user_id = session_state.get('user_id') if session_state else None
                if not user_id:
                    raise Exception(f"세션({session_id})에서 user_id를 찾을 수 없습니다.")

                # S3 URL 및 파일 크기 계산
                s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
                file_size = os.path.getsize(temp_file_path)

                # DB 스키마에 맞는 데이터 구성
                media_data_to_insert = {
                    'user_id': user_id,
                    'interview_id': interview_id,
                    'file_name': os.path.basename(s3_key),
                    'file_type': 'video',
                    's3_url': s3_url,
                    's3_key': s3_key,
                    'file_size': file_size,
                }

                interview_logger.info(f"💾 DB에 저장할 메타데이터: {media_data_to_insert}")
                insert_result = supabase_db_client.table('media_files').insert(media_data_to_insert).execute()

                if insert_result.data:
                    media_record_id = insert_result.data[0]['media_id']
                    interview_logger.info(f"✅ Supabase DB에 미디어 메타데이터 저장 성공. media_id: {media_record_id}")
                else:
                    raise Exception(f"DB insert 실패: {getattr(insert_result, 'error', 'Unknown error')}")

            except Exception as db_error:
                interview_logger.error(f"❌ 미디어 메타데이터 DB 저장 실패: {db_error}", exc_info=True)
                return

            # 6. 시선 분석 서비스 호출
            try:
                interview_logger.info(f"📊 시선 분석 시작: interview_id={interview_id}, s3_path={s3_key}")
                session_state = self.session_states.get(session_id)

                # 6-1. 세션에서 캘리브레이션 데이터 가져오기
                calibration_data = session_state.get('calibration_data')
                if not calibration_data:
                    raise Exception(f"세션({session_id})에서 캘리브레이션 데이터를 찾을 수 없습니다.")

                calibration_points = calibration_data.get('calibration_points')
                initial_face_size = calibration_data.get('initial_face_size')

                if not calibration_points:
                     raise Exception(f"세션({session_id})의 캘리브레이션 데이터에 points 정보가 없습니다.")

                # 6-2. gaze_analyzer로 분석 실행
                analysis_result = gaze_analyzer.analyze_video_from_s3(
                    bucket=bucket_name,
                    key=s3_key,
                    calibration_points=calibration_points,
                    initial_face_size=initial_face_size
                )

                # 6-3. 분석 결과를 DB에 저장 (객체 속성 접근 방식으로 수정)
                if analysis_result:
                    try:
                        supabase_client = get_supabase_client()

                        # video_metadata JSON 객체 구성
                        video_metadata = {
                            "total_frames": getattr(analysis_result, 'total_frames', 0),
                            "analyzed_frames": getattr(analysis_result, 'analyzed_frames', 0),
                            "in_range_ratio": getattr(analysis_result, 'in_range_ratio', 0),
                            "analysis_duration_sec": getattr(analysis_result, 'analysis_duration', 0),
                            "feedback_summary": getattr(analysis_result, 'feedback', "N/A")
                        }

                        # DB에 저장할 데이터 구성 (사용자 테이블 스키마에 맞춤)
                        data_to_insert = {
                            "interview_id": interview_id,
                            "user_id": user_id,
                            "gaze_score": getattr(analysis_result, 'gaze_score', 0),
                            "jitter_score": getattr(analysis_result, 'jitter_score', 0),
                            "compliance_score": getattr(analysis_result, 'compliance_score', 0),
                            "stability_rating": getattr(analysis_result, 'stability_rating', "Error"),
                            "gaze_points": getattr(analysis_result, 'gaze_points', []),
                            "calibration_points": getattr(analysis_result, 'calibration_points', []),
                            "video_metadata": video_metadata
                        }

                        interview_logger.info(f"💾 시선 분석 결과 DB 저장 시도: interview_id={interview_id}")

                        insert_res = supabase_client.table('gaze_analysis').insert(data_to_insert).execute()

                        if insert_res.data:
                            interview_logger.info(f"✅ 시선 분석 결과 DB 저장 성공. gaze_id: {insert_res.data[0].get('gaze_id')}")
                        else:
                            error_details = getattr(insert_res, 'error', 'Unknown error')
                            raise Exception(f"DB insert 실패: {error_details}")

                    except Exception as db_save_error:
                        interview_logger.error(f"❌ 시선 분석 결과 DB 저장 실패: {db_save_error}", exc_info=True)
                else:
                    interview_logger.error(f"❌ 시선 분석 실패: analysis_result가 없습니다.")

            except Exception as analysis_error:
                interview_logger.error(f"❌ 시선 분석 또는 결과 저장 실패: {analysis_error}", exc_info=True)

        except Exception as e:
            interview_logger.error(f"❌ 임시 시선 추적 파일 처리 실패: session_id={session_id}, error={str(e)}", exc_info=True)
        finally:
            # 7. 임시 파일 정리
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    interview_logger.info(f"🗑️ 임시 파일 삭제 완료: {temp_file_path}")
                except Exception as cleanup_error:
                    interview_logger.error(f"⚠️ 임시 파일 정리 실패: {str(cleanup_error)}")

    async def _process_gaze_data_after_evaluation(self, interview_id: int, session_id: str, user_id: int) -> None:
        """
        면접 평가 완료 후 시선 분석 데이터 지연 처리
        
        Pre-signed URL 기반 업로드 플로우에서 interview_id가 확정된 후:
        1. analysis_tasks에서 해당 세션의 시선 분석 결과 찾기
        2. media_files 테이블에 레코드 삽입
        3. gaze_analysis 테이블에 분석 결과 저장
        """
        try:
            from backend.routers.gaze import analysis_tasks
            import os
            
            interview_logger.info(f"📊 면접 평가 후 시선 데이터 처리 시작: interview_id={interview_id}, session_id={session_id}")

            # 1. analysis_tasks에서 해당 세션의 분석 결과 찾기
            session_task_data = None
            session_task_id = None
            
            for task_id, task_info in analysis_tasks.items():
                if (task_info.get("session_id") == session_id and 
                    task_info.get("user_id") == user_id and 
                    task_info.get("status") == "completed"):
                    session_task_data = task_info
                    session_task_id = task_id
                    break

            if not session_task_data:
                interview_logger.info(f"📝 세션 {session_id}에 대한 완료된 시선 분석 결과를 찾을 수 없습니다. Pre-signed URL 업로드가 없었거나 분석이 완료되지 않았을 수 있습니다.")
                return

            s3_key_found = session_task_data.get("s3_key")
            temp_media_id_found = session_task_data.get("temp_media_id")
            analysis_result = session_task_data.get("analysis_result")  # 원본 분석 결과 객체

            interview_logger.info(f"✅ 시선 분석 결과 발견: task_id={session_task_id}, s3_key={s3_key_found}")

            # 2. media_files 테이블에 레코드 삽입
            try:
                supabase_db_client = get_supabase_client()
                
                # S3 URL 및 파일 정보 생성
                BUCKET_NAME = 'betago-s3'
                AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
                file_name = os.path.basename(s3_key_found)
                s3_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key_found}"

                media_data_to_insert = {
                    'user_id': user_id,
                    'interview_id': interview_id,  # 확정된 interview_id 사용
                    'file_name': file_name,
                    'file_type': 'video',
                    's3_url': s3_url,
                    's3_key': s3_key_found,
                    'media_id': temp_media_id_found,  # 임시 media_id를 최종 media_id로 사용
                    'metadata': {
                        'type': 'gaze_tracking',
                        'purpose': 'gaze_analysis',
                        'delayed_insert': True,
                        'original_session_id': session_id
                    }
                }

                interview_logger.info(f"💾 media_files 테이블 삽입 시도: {media_data_to_insert}")
                insert_result = supabase_db_client.table('media_files').insert(media_data_to_insert).execute()

                if insert_result.data:
                    final_media_id = insert_result.data[0]['media_id']
                    interview_logger.info(f"✅ media_files 레코드 삽입 완료: media_id={final_media_id}")
                else:
                    raise Exception(f"media_files 삽입 실패: {getattr(insert_result, 'error', 'Unknown error')}")

            except Exception as e:
                interview_logger.error(f"❌ media_files 삽입 중 오류 발생: {e}", exc_info=True)
                return

            # 3. gaze_analysis 테이블에 분석 결과 저장 (analysis_result가 있는 경우)
            if analysis_result:
                try:
                    supabase_client = get_supabase_client()

                    # video_metadata JSON 객체 구성
                    video_metadata = {
                        "total_frames": getattr(analysis_result, 'total_frames', 0),
                        "analyzed_frames": getattr(analysis_result, 'analyzed_frames', 0),
                        "in_range_ratio": getattr(analysis_result, 'in_range_ratio', 0),
                        "analysis_duration_sec": getattr(analysis_result, 'analysis_duration', 0),
                        "feedback_summary": getattr(analysis_result, 'feedback', "N/A"),
                        "delayed_processing": True,
                        "source_session_id": session_id
                    }

                    # DB에 저장할 데이터 구성
                    gaze_data_to_insert = {
                        "interview_id": interview_id,
                        "user_id": user_id,
                        "gaze_score": getattr(analysis_result, 'gaze_score', 0),
                        "jitter_score": getattr(analysis_result, 'jitter_score', 0),
                        "compliance_score": getattr(analysis_result, 'compliance_score', 0),
                        "stability_rating": getattr(analysis_result, 'stability_rating', "Unknown"),
                        "gaze_points": getattr(analysis_result, 'gaze_points', []),
                        "calibration_points": getattr(analysis_result, 'calibration_points', []),
                        "video_metadata": video_metadata
                    }

                    interview_logger.info(f"💾 gaze_analysis 테이블 삽입 시도: interview_id={interview_id}")
                    gaze_insert_result = supabase_client.table('gaze_analysis').insert(gaze_data_to_insert).execute()

                    if gaze_insert_result.data:
                        gaze_id = gaze_insert_result.data[0].get('gaze_id')
                        interview_logger.info(f"✅ gaze_analysis 레코드 삽입 완료: gaze_id={gaze_id}")
                    else:
                        error_details = getattr(gaze_insert_result, 'error', 'Unknown error')
                        raise Exception(f"gaze_analysis 삽입 실패: {error_details}")

                except Exception as e:
                    interview_logger.error(f"❌ gaze_analysis 삽입 중 오류 발생: {e}", exc_info=True)

            # 4. analysis_tasks에서 처리된 task 정리 (선택적)
            try:
                if session_task_id in analysis_tasks:
                    analysis_tasks[session_task_id]['processed'] = True
                    analysis_tasks[session_task_id]['linked_interview_id'] = interview_id
                    interview_logger.info(f"🧹 analysis_task {session_task_id} 처리 완료 표시")
            except Exception as cleanup_error:
                interview_logger.warning(f"⚠️ analysis_task 정리 중 오류: {cleanup_error}")

            interview_logger.info(f"✅ 시선 분석 데이터 지연 처리 완료: interview_id={interview_id}, session_id={session_id}")

        except Exception as e:
            interview_logger.error(f"❌ 시선 분석 데이터 지연 처리 실패: session_id={session_id}, interview_id={interview_id}, error={str(e)}", exc_info=True)

