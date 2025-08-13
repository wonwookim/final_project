from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional
import logging
from typing import List, Union
from backend.services.supabase_client import supabase_client
from backend.schemas.user import UserResponse
from schemas.interview import InterviewHistoryResponse, InterviewSettings, AnswerSubmission, AICompetitionAnswerSubmission, CompetitionTurnSubmission, InterviewResponse, TTSRequest, STTResponse, MemoUpdateRequest
from services.interview_service import InterviewService
from services.interview_service_temp import InterviewServiceTemp
from backend.services.auth_service import AuthService
from backend.services.voice_service import elevenlabs_tts_stream
from fastapi.responses import HTMLResponse
import io
import time
import os
import tempfile
import aiohttp
from dotenv import load_dotenv



# 서비스 계층 사용
interview_service = InterviewService()
interview_service_temp = InterviewServiceTemp()

# AuthService 인스턴스 생성
auth_service = AuthService()

# 의존성 주입
def get_interview_service():
    return interview_service

def get_temp_interview_service():
    return interview_service_temp

# 로거 설정
interview_logger = logging.getLogger("interview_logger")

# APIRouter 인스턴스 생성
interview_router = APIRouter(
    prefix="/interview",
    tags=["Interview"],
)

# @interview_router.post("/start")
# async def start_interview(
#     settings: InterviewSettings,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """면접 시작 - 서비스 계층 사용"""
#     try:
#         settings_dict = {
#             "company": settings.company,
#             "position": settings.position,
#             "candidate_name": settings.candidate_name,
#             "documents": settings.documents
#         }
# =================================================================
# 🚀 TTS 테스트용 임시 코드 START (나중에 이 부분을 삭제하세요)
# =================================================================


@interview_router.get("/tts-test", response_class=HTMLResponse, summary="[테스트용] TTS 웹 페이지")
async def get_tts_test_page():
    """
    TTS API를 테스트하기 위한 간단한 HTML 페이지를 반환합니다.
    이 엔드포인트는 개발 및 디버깅 목적으로만 사용됩니다.
    """
    try:
        with open("temp_test.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="테스트 파일을 찾을 수 없습니다: temp_test.html")
# =================================================================
# 🚀 TTS 테스트용 임시 코드 END
# =================================================================
        
#         result = await service.start_interview(settings_dict)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"면접 시작 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
    
# @interview_router.post("/upload")
# async def upload_document(
#     file: UploadFile = File(...),
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """문서 업로드 및 분석"""
#     try:
#         content = await file.read()
#         file_data = {
#             "filename": file.filename,
#             "content": content
#         }
        
#         result = await service.upload_document(file_data)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"문서 업로드 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @interview_router.get("/question")
# async def get_next_question(
#     session_id: str,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """다음 질문 가져오기 - 서비스 계층 사용"""
#     try:
#         result = await service.get_next_question(session_id)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"질문 가져오기 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/question")
async def get_next_question_ai_competition(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 경쟁 면접에서 다음 질문/답변 턴 진행"""
    try:
        result = await service.advance_interview_turn(session_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"면접 턴 진행 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @interview_router.post("/answer")
# async def submit_answer(
#     answer_data: AnswerSubmission,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """답변 제출 - 서비스 계층 사용"""
#     try:
#         answer_dict = {
#             "session_id": answer_data.session_id,
#             "answer": answer_data.answer,
#             "time_spent": answer_data.time_spent
#         }
        
#         result = await service.submit_answer(answer_dict)
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"답변 제출 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @interview_router.post("/answer")
# async def submit_user_answer(
#     answer_data: AnswerSubmission,
#     service: InterviewService = Depends(get_interview_service)
# ):
#     """사용자 답변 제출 - Orchestrator 기반"""
#     try:
#         result = await service.submit_user_answer(
#             session_id=answer_data.session_id,
#             user_answer=answer_data.answer,
#             time_spent=answer_data.time_spent
#         )
#         return result
        
#     except Exception as e:
#         interview_logger.error(f"사용자 답변 제출 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# AI 경쟁 모드 엔드포인트

@interview_router.post("/ai/start")
async def start_ai_competition(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """AI 지원자와의 경쟁 면접 시작"""
    start_time = time.perf_counter()  # 시간 측정 시작
    try:
        # 🐛 디버깅: FastAPI에서 받은 설정값 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 받은 settings = {settings.dict()}")
        interview_logger.info(f"🐛 FastAPI DEBUG: use_interviewer_service = {settings.use_interviewer_service}")
        
        # 🆕 user_resume_id가 없으면 DB에서 자동으로 조회
        if not settings.user_resume_id:
            try:
                from backend.services.existing_tables_service import existing_tables_service
                user_resumes = await existing_tables_service.get_user_resumes(current_user.user_id)
                if user_resumes:
                    settings.user_resume_id = user_resumes[0].get('user_resume_id')  # 첫 번째 이력서 사용
                    interview_logger.info(f"✅ 자동 조회된 user_resume_id: {settings.user_resume_id}")
                else:
                    interview_logger.warning(f"⚠️ 사용자 이력서를 찾을 수 없음: user_id={current_user.user_id}")
            except Exception as e:
                interview_logger.error(f"❌ user_resume_id 자동 조회 실패: {e}")
        
        # 🆕 posting_id가 있으면 DB에서 실제 채용공고 정보를 가져와서 사용
        if settings.posting_id:
            from backend.services.existing_tables_service import existing_tables_service
            posting_info = await existing_tables_service.get_posting_by_id(settings.posting_id)
            
            if posting_info:
                interview_logger.info(f"📋 실제 채용공고 사용: posting_id={settings.posting_id}")
                interview_logger.info(f"   회사: {posting_info.get('company', {}).get('name', 'Unknown')}")
                interview_logger.info(f"   직무: {posting_info.get('position', {}).get('position_name', 'Unknown')}")
                
                settings_dict = {
                    "company": posting_info.get('company', {}).get('name', settings.company),
                    "position": posting_info.get('position', {}).get('position_name', settings.position),
                    "candidate_name": settings.candidate_name,
                    "posting_id": settings.posting_id,
                    "company_id": posting_info.get('company_id'),
                    "position_id": posting_info.get('position_id'),
                    "difficulty": settings.difficulty,  # 난이도 값 추가 (첫 번째 파일에서)
                    "use_interviewer_service": settings.use_interviewer_service,
                    "user_id": current_user.user_id,
                    "user_resume_id": settings.user_resume_id
                }
            else:
                interview_logger.warning(f"⚠️ 채용공고를 찾을 수 없음: posting_id={settings.posting_id}, fallback to original")
                settings_dict = {
                    "company": settings.company,
                    "position": settings.position,
                    "candidate_name": settings.candidate_name,
                    "difficulty": settings.difficulty,  # 난이도 값 추가 (첫 번째 파일에서)
                    "use_interviewer_service": settings.use_interviewer_service,
                    "user_id": current_user.user_id,
                    "user_resume_id": settings.user_resume_id
                }
        else:
            # 기존 방식: company/position 문자열 사용
            settings_dict = {
                "company": settings.company,
                "position": settings.position,
                "candidate_name": settings.candidate_name,
                "difficulty": settings.difficulty,  # 난이도 값 추가 (첫 번째 파일에서)
                "use_interviewer_service": settings.use_interviewer_service,
                "user_id": current_user.user_id,
                "user_resume_id": settings.user_resume_id
            }
        
        # 🐛 디버깅: 서비스에 전달할 settings_dict 로깅
        interview_logger.info(f"🐛 FastAPI DEBUG: 서비스에 전달할 settings_dict = {settings_dict}")
        
        result = await service.start_ai_competition(settings_dict, start_time=start_time)
        
        # 전체 소요 시간 로깅 (첫 번째 파일에서)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        interview_logger.info(f"✅ AI 경쟁 면접 시작 성공. 총 처리 시간: {elapsed_time:.4f}초")
        
        # 🔍 DEBUG: FastAPI 라우터에서 최종 HTTP 응답 전 result 구조 확인
        print(f"[🔍 FASTAPI_ROUTER_DEBUG] === HTTP 응답 직전 result 구조 ===")
        print(f"[🔍 FASTAPI_ROUTER_DEBUG] result 타입: {type(result)}")
        if isinstance(result, dict):
            print(f"[🔍 FASTAPI_ROUTER_DEBUG] result 키들: {list(result.keys())}")
            for key, value in result.items():
                if key in ['intro_audio', 'first_question_audio']:
                    print(f"[🔍 FASTAPI_ROUTER_DEBUG] {key}: {bool(value)} ({len(str(value)) if value else 0}자)")
                else:
                    print(f"[🔍 FASTAPI_ROUTER_DEBUG] {key}: {bool(value)}")
                    if key == 'first_question' and value:
                        print(f"[🔍 FASTAPI_ROUTER_DEBUG] first_question 내용: {str(value)[:50]}...")
        print(f"[🔍 FASTAPI_ROUTER_DEBUG] === FastAPI가 HTTP 응답으로 직렬화할 데이터 ===")
        
        return result
        
    except Exception as e:
        # 에러 발생 시에도 소요 시간 로깅 (첫 번째 파일에서)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        interview_logger.error(f"AI 경쟁 면접 시작 오류: {str(e)}. 처리 시간: {elapsed_time:.4f}초")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.post("/answer")
async def submit_user_answer(
    submission: AICompetitionAnswerSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """사용자 답변 제출 - AI 경쟁 면접용"""
    try:
        interview_logger.info(f"👤 사용자 답변 제출 요청: {submission.session_id}")
        
        result = await service.submit_user_answer(
            session_id=submission.session_id,
            user_answer=submission.answer,
            time_spent=submission.time_spent
        )
        
        interview_logger.info(f"✅ 사용자 답변 제출 완료: {submission.session_id}")
        return result
        
    except Exception as e:
        interview_logger.error(f"사용자 답변 제출 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/session/active")
async def get_active_sessions(
    service: InterviewService = Depends(get_interview_service)
):
    """현재 활성 세션들 조회"""
    try:
        active_sessions = service.get_active_sessions()
        return {
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }
    except Exception as e:
        interview_logger.error(f"활성 세션 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/session/{session_id}/state")
async def get_session_state(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """특정 세션의 상태 조회"""
    try:
        state = service.get_session_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {
            "session_id": session_id,
            "state": state,
            "is_active": True
        }
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"세션 상태 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/ai-answer/{session_id}/{question_id}")
async def get_ai_answer(
    session_id: str,
    question_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """AI 지원자의 답변 생성"""
    try:
        result = await service.get_ai_answer(session_id, question_id)
        return result
        
    except Exception as e:
        interview_logger.error(f"AI 답변 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.post("/comparison/turn")
async def process_competition_turn(
    submission: CompetitionTurnSubmission,
    service: InterviewService = Depends(get_interview_service)
):
    """경쟁 면접 통합 턴 처리"""
    try:
        result = await service.process_competition_turn(
            submission.comparison_session_id,
            submission.answer
        )
        return result
    except Exception as e:
        interview_logger.error(f"경쟁 면접 턴 처리 API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🚀 새로운 턴제 면접 엔드포인트
@interview_router.post("/turn-based/start")
async def start_turn_based_interview(
    settings: InterviewSettings,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 시작 - 새로운 InterviewerService 사용"""
    try:
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name
        }
        
        result = await service.start_turn_based_interview(settings_dict)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 면접 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@interview_router.get("/turn-based/question/{session_id}")
async def get_turn_based_question(
    session_id: str,
    user_answer: Optional[str] = None,
    service: InterviewService = Depends(get_interview_service)
):
    """턴제 면접 다음 질문 가져오기"""
    try:
        result = await service.get_turn_based_question(session_id, user_answer)
        return result
        
    except Exception as e:
        interview_logger.error(f"턴제 질문 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🟢 GET /interview/history – 내 면접 기록 조회
@interview_router.get("/history", response_model=List[InterviewResponse])
async def get_interview_history(current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 면접 기록을 Supabase에서 조회합니다."""
    print(f"🔍 DEBUG: 면접 히스토리 조회 - 사용자 ID: {current_user.user_id} (타입: {type(current_user.user_id)}), 이메일: {current_user.email}")
    
    # 전체 interview 테이블 데이터 확인
    all_interviews = supabase_client.client.from_("interview").select("interview_id, user_id").execute()
    print(f"🔍 DEBUG: 전체 interview 테이블 레코드 수: {len(all_interviews.data) if all_interviews.data else 0}")
    if all_interviews.data:
        user_ids_with_types = [(item['user_id'], type(item['user_id'])) for item in all_interviews.data[:5]]
        print(f"🔍 DEBUG: 전체 interview 사용자 ID들과 타입: {user_ids_with_types}")
        
        # 현재 사용자 ID와 일치하는지 직접 확인
        matching_interviews = [item for item in all_interviews.data if str(item['user_id']) == str(current_user.user_id)]
        print(f"🔍 DEBUG: 문자열 변환 후 일치하는 면접 수: {len(matching_interviews)}")
    
    # 첫 번째 파일의 더 상세한 쿼리 사용 (company, position join 포함)
    # 타입 불일치 방지를 위해 문자열로 변환하여 조회
    res = supabase_client.client.from_("interview").select(
        "*, company(name), position(position_name)"
    ).eq("user_id", str(current_user.user_id)).execute()
    
    print(f"🔍 DEBUG: 사용자별 면접 기록 조회 결과: {len(res.data) if res.data else 0}개")
    if res.data:
        print(f"🔍 DEBUG: 첫 번째 면접 기록: {res.data[0]}")
    
    if not res.data:
        return []  # 빈 배열 반환 (404 에러 대신)
    # ai_resume_id/user_resume_id가 None인 경우에도 스키마 검증을 통과하도록 보정
    data = res.data
    for row in data:
        if 'ai_resume_id' in row and row['ai_resume_id'] is None:
            row['ai_resume_id'] = None
        if 'user_resume_id' in row and row['user_resume_id'] is None:
            row['user_resume_id'] = None
        # total_feedback이 None인 경우 빈 문자열로 변환
        if 'total_feedback' in row and row['total_feedback'] is None:
            row['total_feedback'] = ""
    return data


@interview_router.get("/history/{interview_id}")
async def get_interview_results(
    interview_id: int,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """현재 로그인한 유저의 특정 면접 기록 조회 (상세 데이터 + 전체 피드백)"""
    
    # 1. history_detail 테이블에서 질문별 상세 데이터 가져오기
    detail_res = supabase_client.client.from_("history_detail") \
        .select("*") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 2. interview 테이블에서 전체 피드백 가져오기
    interview_res = supabase_client.client.from_("interview") \
        .select("total_feedback") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 3. plans 테이블에서 개선 계획 가져오기
    plans_res = supabase_client.client.from_("plans") \
        .select("shortly_plan, long_plan") \
        .eq("interview_id", interview_id) \
        .execute()
    
    # 데이터 통합
    result = {
        "details": detail_res.data or [],
        "total_feedback": interview_res.data[0]["total_feedback"] if interview_res.data else None,
        "plans": plans_res.data[0] if plans_res.data else None
    }
    
    return result

@interview_router.post("/memo")
async def update_memo(memo_update: MemoUpdateRequest):
    """
    Updates the memo field in the history_detail table.
    """
    try:
        response = supabase_client.client.from_("history_detail").update(
            {"memo": memo_update.memo}
        ).eq("interview_id", memo_update.interview_id).eq(
            "question_index", memo_update.question_index
        ).eq(
            "who", memo_update.who
        ).execute()

        if response.data:
            interview_logger.info(f"메모 업데이트 성공: interview_id={memo_update.interview_id}, question_index={memo_update.question_index}, who={memo_update.who}")
            return {"message": "메모가 성공적으로 업데이트되었습니다."}
        else:
            interview_logger.warning(f"메모 업데이트 실패: 해당 항목을 찾을 수 없음. interview_id={memo_update.interview_id}, question_index={memo_update.question_index}, who={memo_update.who}")
            raise HTTPException(status_code=404, detail="해당 면접 기록을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"메모 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메모 업데이트 중 오류 발생: {str(e)}")

# 🟢 POST /interview/tts
@interview_router.post("/tts")
async def text_to_speech_elevenlabs(req: TTSRequest):
    # 로그 추가
    interview_logger.info(f"TTS 요청 수신: voice_id='{req.voice_id}', text='{req.text[:50]}...'")

    # 빈 텍스트 유효성 검사
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="TTS를 위한 텍스트 내용이 비어있습니다.")

    try:
        audio_bytes = await elevenlabs_tts_stream(req.text, req.voice_id)
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except HTTPException as e:
        # voice_service에서 발생한 HTTPException을 그대로 전달
        interview_logger.error(f"TTS API 오류 발생: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        # 그 외 예기치 않은 오류 처리
        interview_logger.error(f"TTS 처리 중 예기치 않은 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="TTS 처리 중 서버 오류가 발생했습니다.")

# 🟢 POST /interview/stt
@interview_router.post("/stt", response_model=STTResponse)
async def speech_to_text(file: UploadFile = File(...)):
    """음성 파일을 OpenAI Whisper로 텍스트 변환 후 파일 삭제"""
    # 파일 유효성 검사
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="음성 파일이 필요합니다.")
    
    # 지원하는 오디오 형식 확인
    allowed_extensions = ['.wav', '.mp3', '.m4a', '.webm', '.ogg', '.flac']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
        )
    
    # OpenAI API 키 확인
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    temp_file_path = None
    try:
        # 임시 파일로 음성 데이터 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        interview_logger.info(f"🎙️ STT 처리 시작: {file.filename} ({len(content)} bytes)")
        interview_logger.info(f"📄 파일 정보: content_type={file.content_type}, filename={file.filename}")
        
        # OpenAI Whisper API 호출
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # 파일을 한 번에 읽어서 메모리에 저장
        with open(temp_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            
        interview_logger.info(f"📊 오디오 데이터 크기: {len(audio_data)} bytes")
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', audio_data, filename=file.filename, content_type=file.content_type or 'audio/webm')
        form_data.add_field('model', 'whisper-1')
        form_data.add_field('response_format', 'json')
        # 언어를 자동 감지로 변경 (더 정확할 수 있음)
        # form_data.add_field('language', 'ko')  # 한국어 강제 설정 제거
        form_data.add_field('temperature', '0')  # 일관성 있는 결과를 위해 temperature 0 설정
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=form_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    interview_logger.error(f"❌ Whisper API 오류: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"STT API 오류: {error_text}"
                    )
                
                result = await response.json()
                transcribed_text = result.get('text', '').strip()
                
                # 전체 Whisper API 응답 로깅
                interview_logger.info(f"🤖 Whisper API 전체 응답: {result}")
                interview_logger.info(f"📝 추출된 텍스트: '{transcribed_text}'")
        
        return STTResponse(
            text=transcribed_text,
            confidence=1.0,  # Whisper는 confidence score를 제공하지 않으므로 기본값
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ STT 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")
    finally:
        # 임시 파일 삭제
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                interview_logger.info(f"🗑️ 임시 음성 파일 삭제 완료: {temp_file_path}")
            except Exception as cleanup_error:
                interview_logger.warning(f"⚠️ 임시 파일 삭제 실패: {cleanup_error}")


# ============================================================================
# 🚀 텍스트 기반 AI 경쟁 면접 엔드포인트들 (InterviewServiceTemp 사용)
# ============================================================================

@interview_router.post("/text-competition/start")
async def start_text_competition(
    settings: InterviewSettings,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 AI 경쟁 면접 시작"""
    try:
        interview_logger.info(f"🎯 텍스트 경쟁 면접 시작 요청: {settings.company} - {settings.position}")
        
        # 🔍 디버깅: 받은 설정 데이터 확인 (첫 번째 파일에서)
        interview_logger.info(f"📋 받은 설정 데이터: company={settings.company}, position={settings.position}, candidate_name={settings.candidate_name}")
        interview_logger.info(f"📄 이력서 데이터 확인: {settings.resume is not None}")
        if settings.resume:
            interview_logger.info(f"📝 이력서 내용: name={settings.resume.get('name', 'N/A')}, tech={str(settings.resume.get('tech', 'N/A'))[:50]}...")
        
        settings_dict = {
            "company": settings.company,
            "position": settings.position,
            "candidate_name": settings.candidate_name,
            "documents": settings.documents or [],
            "resume": settings.resume,  # 🆕 이력서 데이터 추가 (첫 번째 파일에서)
            "difficulty": settings.difficulty  # 🆕 난이도 추가 (첫 번째 파일에서)
        }
        
        result = await temp_service.start_text_interview(settings_dict)
        
        interview_logger.info(f"✅ 텍스트 경쟁 면접 시작 성공: {result.get('session_id')}")
        return result
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 경쟁 면접 시작 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.post("/text-competition/submit-answer")
async def submit_text_answer(
    answer_data: dict,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 답변 제출 및 AI 답변 + 다음 질문 받기"""
    try:
        session_id = answer_data.get("session_id")
        answer = answer_data.get("answer")
        
        if not session_id or not answer:
            raise HTTPException(status_code=400, detail="session_id와 answer가 필요합니다")
        
        interview_logger.info(f"📝 텍스트 답변 제출: {session_id}")
        
        result = await temp_service.submit_answer_and_get_next(session_id, answer)
        
        interview_logger.info(f"✅ 텍스트 답변 처리 완료: {session_id} - {result.get('status')}")
        return result
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 답변 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/session/{session_id}")
async def get_text_session_info(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 세션 정보 조회"""
    try:
        interview_logger.info(f"🔍 텍스트 세션 정보 조회: {session_id}")
        
        result = await temp_service.get_session_info(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 세션 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/results/{session_id}")
async def get_text_interview_results(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 결과 조회"""
    try:
        interview_logger.info(f"📊 텍스트 면접 결과 조회: {session_id}")
        
        result = await temp_service.get_interview_results(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 면접 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.delete("/text-competition/session/{session_id}")
async def cleanup_text_session(
    session_id: str,
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 세션 정리"""
    try:
        interview_logger.info(f"🧹 텍스트 세션 정리 요청: {session_id}")
        
        success = temp_service.cleanup_session(session_id)
        
        if success:
            return {"message": "세션이 성공적으로 정리되었습니다.", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 세션 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/text-competition/stats")
async def get_text_interview_stats(
    temp_service: InterviewServiceTemp = Depends(get_temp_interview_service)
):
    """텍스트 기반 면접 시스템 통계"""
    try:
        active_sessions = temp_service.get_active_sessions_count()
        
        return {
            "active_sessions": active_sessions,
            "service_type": "text_based_competition",
            "system_status": "operational"
        }
        
    except Exception as e:
        interview_logger.error(f"❌ 텍스트 면접 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# 🎯 Feedback 관련 엔드포인트 추가 (두 번째 파일에서)
# ========================================

# Feedback 모델 임포트
try:
    from llm.feedback.api_models import QuestionRequest, QuestionResponse, PlansRequest, PlansResponse
    from llm.feedback.api_service import InterviewEvaluationService
    
    # 전역 평가 서비스 인스턴스 (싱글톤)
    evaluation_service = InterviewEvaluationService()
    
    @interview_router.post("/feedback/evaluate")
    async def evaluate_interview(request: Union[QuestionRequest, List[QuestionRequest]]):
        """면접 질문-답변 평가 (단일 또는 배치)"""
        try:
            # 단일 요청인지 리스트인지 체크
            if isinstance(request, list):
                # 리스트인 경우 - 배치 처리
                results = []
                for i, req in enumerate(request):
                    interview_logger.info(f"배치 평가 {i+1}/{len(request)}: user_id={req.user_id}, questions={len(req.qa_pairs)}")
                    
                    result = evaluation_service.evaluate_multiple_questions(
                        user_id=req.user_id,
                        qa_pairs=req.qa_pairs,
                        ai_resume_id=req.ai_resume_id,
                        user_resume_id=req.user_resume_id,
                        posting_id=req.posting_id,
                        company_id=req.company_id,
                        position_id=req.position_id
                    )
                    results.append(result)
                
                return {
                    "success": True,
                    "message": f"{len(results)}개 평가 완료",
                    "results": results
                }
            else:
                # 기존 단일 처리 로직 유지
                interview_logger.info(f"면접 평가 요청: user_id={request.user_id}, questions={len(request.qa_pairs)}")
                
                result = evaluation_service.evaluate_multiple_questions(
                    user_id=request.user_id,
                    qa_pairs=request.qa_pairs,
                    ai_resume_id=request.ai_resume_id,
                    user_resume_id=request.user_resume_id,
                    posting_id=request.posting_id,
                    company_id=request.company_id,
                    position_id=request.position_id
                )
                
                return QuestionResponse(**result)
            
        except Exception as e:
            interview_logger.error(f"면접 평가 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"면접 평가 중 오류 발생: {str(e)}")

    @interview_router.post("/feedback/plans", response_model=PlansResponse)
    async def generate_interview_plans(request: PlansRequest):
        """면접 준비 계획 생성"""
        try:
            interview_logger.info(f"면접 계획 생성 요청: interview_id={request.interview_id}")
            
            result = evaluation_service.generate_interview_plans(request.interview_id)
            
            return PlansResponse(**result)
            
        except Exception as e:
            interview_logger.error(f"면접 계획 생성 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"면접 계획 생성 중 오류 발생: {str(e)}")

except ImportError as e:
    interview_logger.warning(f"Feedback 모듈 로드 실패: {e}")
    
    @interview_router.post("/feedback/evaluate")
    async def evaluate_interview_fallback():
        raise HTTPException(status_code=503, detail="면접 평가 서비스를 사용할 수 없습니다.")
    
    @interview_router.post("/feedback/plans")
    async def generate_interview_plans_fallback():
        raise HTTPException(status_code=503, detail="면접 계획 서비스를 사용할 수 없습니다.")

# 🟢 POST /interview/complete – 면접 완료 처리 (비동기)
@interview_router.post("/complete")
async def complete_interview_async(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    """면접 완료 시 즉시 응답하고 백그라운드에서 피드백 처리"""
    try:
        interview_logger.info(f"🏁 면접 완료 요청: session_id={session_id}, user={current_user.user_id}")
        
        # 백그라운드에서 피드백 처리 스케줄링
        if FEEDBACK_ENABLED:
            background_tasks.add_task(process_feedback_async, session_id, current_user.user_id)
        
        # 즉시 응답 반환
        return {
            "status": "completed",
            "message": "면접이 완료되었습니다. 피드백 처리가 백그라운드에서 진행됩니다.",
            "session_id": session_id,
            "feedback_processing": FEEDBACK_ENABLED
        }
        
    except Exception as e:
        interview_logger.error(f"❌ 면접 완료 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_feedback_async(session_id: str, user_id: int):
    """백그라운드에서 실행되는 피드백 처리"""
    try:
        interview_logger.info(f"🔄 백그라운드 피드백 처리 시작: session_id={session_id}")
        
        if FEEDBACK_ENABLED:
            # 기존 피드백 평가 로직 실행
            request = EvaluationRequest(session_id=session_id)
            evaluation_service.evaluate_interview(request)
            
            interview_logger.info(f"✅ 백그라운드 피드백 처리 완료: session_id={session_id}")
        else:
            interview_logger.warning(f"⚠️ 피드백 서비스 비활성화: session_id={session_id}")
            
    except Exception as e:
        interview_logger.error(f"❌ 백그라운드 피드백 처리 실패: session_id={session_id}, error={str(e)}")