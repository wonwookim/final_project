import json
import json
from typing import Dict, Any, List, Optional
import asyncio
import uuid
import time
from llm.interviewer.question_generator import QuestionGenerator
from llm.candidate.model import AICandidateModel, CandidatePersona
from llm.shared.models import AnswerRequest, QuestionType, LLMProvider
from llm.candidate.quality_controller import QualityLevel
from llm.shared.logging_config import interview_logger

from backend.services.Orchestrator import Orchestrator

class InterviewService:
    def __init__(self):
        self.active_orchestrators: Dict[str, Orchestrator] = {}
        self.question_generator = QuestionGenerator()
        self.ai_candidate_model = AICandidateModel()
        
        # 에이전트 핸들러 등록
        self.agent_handlers = {
            "interviewer": self._handle_interviewer_message,
            "ai": self._handle_ai_candidate_message,
            "user": self._handle_user_message
        }
        
        self.company_name_map = {
            "네이버": "naver", "카카오": "kakao", "라인": "line",
            "라인플러스": "라인플러스", "쿠팡": "coupang", "배달의민족": "baemin",
            "당근마켓": "daangn", "토스": "toss"
        }

    def get_company_id(self, company_name: str) -> str:
        return self.company_name_map.get(company_name, company_name.lower())

    def get_active_sessions(self) -> List[str]:
        """현재 활성 세션 ID들을 반환"""
        return list(self.active_orchestrators.keys())
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """특정 세션의 상태를 반환"""
        orchestrator = self.active_orchestrators.get(session_id)
        return orchestrator.get_current_state() if orchestrator else None
    
    def has_active_session(self, session_id: str) -> bool:
        """세션이 활성 상태인지 확인"""
        return session_id in self.active_orchestrators

    async def _create_ai_persona(self, ai_candidate_model: AICandidateModel, company_id: str, position: str):
        persona = await asyncio.to_thread(
            ai_candidate_model.create_persona_for_interview, company_id, position
        )
        return persona if persona else ai_candidate_model._create_default_persona(company_id, position)

    def _get_orchestrator_or_error(self, session_id: str) -> tuple[Optional[Orchestrator], Optional[Dict]]:
        orchestrator = self.active_orchestrators.get(session_id)
        if not orchestrator:
            return None, {"error": "유효하지 않은 세션 ID입니다."}
        if orchestrator.state.get('is_completed', False):
            return None, {"error": "이미 완료된 면접입니다."}
        return orchestrator, None

    async def start_ai_competition(self, settings: Dict[str, Any], start_time: float = None) -> Dict[str, Any]:
        try:
            session_id = f"comp_{uuid.uuid4().hex[:12]}"
            company_id = self.get_company_id(settings['company'])
            ai_persona = await self._create_ai_persona(self.ai_candidate_model, company_id, settings['position'])
            
            orchestrator_settings = {
                'total_question_limit': 15,
                'company_id': company_id,
                'position': settings['position'],
                'user_name': settings['candidate_name'],
                'ai_persona': ai_persona
            }
            
            orchestrator = Orchestrator(session_id, orchestrator_settings)
            self.active_orchestrators[session_id] = orchestrator
            
            interview_logger.info(f"AI 경쟁 면접 시작: {session_id}")
            
            # Orchestrator에게 첫 행동을 요청하는 메시지를 받음
            initial_message = orchestrator._decide_next_message()
            print(f"[InterviewService] ➡️ [Orchestrator]")
            print(json.dumps(initial_message, indent=2, ensure_ascii=False))
            
            # 해당 메시지를 처리하여 면접의 첫 단계를 시작
            result = await self._process_orchestrator_message(session_id, initial_message)

            # 최종 결과에 session_id 추가
            if isinstance(result, dict) and 'session_id' not in result:
                result['session_id'] = session_id

            print(f"[InterviewService] ➡️ [Client]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

        except Exception as e:
            interview_logger.error(f"AI 경쟁 면접 시작 오류: {e}", exc_info=True)
            return {"error": f"면접 시작 중 오류가 발생했습니다: {str(e)}"}

    async def submit_user_answer(self, session_id: str, user_answer: str, time_spent: float = None) -> Dict[str, Any]:
        try:
            orchestrator, error = self._get_orchestrator_or_error(session_id)
            if error: 
                return error

            interview_logger.info(f"👤 사용자 답변 제출: {session_id}")
            
            # 사용자 답변을 Orchestrator가 처리할 수 있는 표준 메시지로 변환
            user_message_to_orchestrator = Orchestrator.create_agent_message(
                session_id=session_id,
                task="answer_generated",
                from_agent="user",
                content_text=user_answer,
                turn_count=orchestrator.state.get('turn_count', 0),
                duration=time_spent
            )
            print(f"[InterviewService] ➡️ [Orchestrator]")
            print(json.dumps(user_message_to_orchestrator, indent=2, ensure_ascii=False))
            
            # Orchestrator는 이 메시지를 받아 상태를 업데이트하고, 다음 행동 메시지를 반환
            next_message_from_orchestrator = orchestrator.handle_message(user_message_to_orchestrator)
            
            # Orchestrator가 결정한 다음 행동을 처리
            result = await self._process_orchestrator_message(session_id, next_message_from_orchestrator)
            
            # 최종 결과에 session_id 추가
            if isinstance(result, dict) and 'session_id' not in result:
                result['session_id'] = session_id

            print(f"[InterviewService] ➡️ [Client]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

        except Exception as e:
            interview_logger.error(f"사용자 답변 제출 오류: {e}", exc_info=True)
            return {"error": f"답변 제출 중 오류가 발생했습니다: {str(e)}"}

    async def _process_orchestrator_message(self, session_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrator의 메시지를 받아 실제 작업을 수행하고, 그 결과를 다시 Orchestrator에게 전달"""
        
        orchestrator, error = self._get_orchestrator_or_error(session_id)
        if error:
            return error

        task = message.get("metadata", {}).get("task")
        next_agent = message.get("metadata", {}).get("next_agent")

        print(f"[InterviewService] ⬅️ [Orchestrator]")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        interview_logger.info(f"🔄 Processing task: {task} for agent: {next_agent}")

        if task == "end_interview":
            return {
                "status": "completed",
                "message": "면접이 종료되었습니다.",
                "qa_history": orchestrator.state.get('qa_history', [])
            }

        # 에이전트 핸들러를 통해 다음 작업 처리
        handler = self.agent_handlers.get(next_agent)
        if not handler:
            return {"error": f"알 수 없는 next_agent: {next_agent}"}
        
        # 핸들러는 항상 Orchestrator에게 보낼 메시지를 반환해야 함
        response_message_to_orchestrator = await handler(orchestrator, message)
        
        print(f"[InterviewService] ➡️ [Orchestrator]")
        print(json.dumps(response_message_to_orchestrator, indent=2, ensure_ascii=False))

        # 사용자에게 응답을 기다리라는 메시지가 아닌 경우에만 Orchestrator의 handle_message를 호출
        if response_message_to_orchestrator.get("metadata", {}).get("task") == "wait_for_user_input":
            return response_message_to_orchestrator

        next_message_from_orchestrator = orchestrator.handle_message(response_message_to_orchestrator)
        
        # Orchestrator가 결정한 다음 행동을 재귀적으로 처리
        return await self._process_orchestrator_message(session_id, next_message_from_orchestrator)

    async def _handle_interviewer_message(self, orchestrator: Orchestrator, message: Dict[str, Any]) -> Dict[str, Any]:
        """면접관 에이전트의 메시지를 처리"""
        question_content = await self._request_question_from_interviewer(orchestrator)
        
        return Orchestrator.create_agent_message(
            session_id=orchestrator.state['session_id'],
            task="question_generated",
            from_agent="interviewer",
            content_text=question_content,
            turn_count=orchestrator.state.get('turn_count', 0)
        )

    async def _handle_ai_candidate_message(self, orchestrator: Orchestrator, message: Dict[str, Any]) -> Dict[str, Any]:
        """AI 지원자 에이전트의 메시지를 처리"""
        question = message.get("content", {}).get("content")
        ai_answer = await self._request_answer_from_ai_candidate(orchestrator, question)
        
        return Orchestrator.create_agent_message(
            session_id=orchestrator.state['session_id'],
            task="answer_generated",
            from_agent="ai",
            content_text=ai_answer,
            turn_count=orchestrator.state.get('turn_count', 0)
        )

    async def _handle_user_message(self, orchestrator: Orchestrator, message: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 입력을 기다리는 상태를 클라이언트에게 반환"""
        # 사용자에게 전달할 메시지는 Orchestrator의 표준 메시지 형식을 따르되,
        # 재귀 호출을 멈추기 위해 특별한 task명을 사용하고, 바로 클라이언트에게 반환됩니다.
        response_to_client = orchestrator.create_message(
            content_text=orchestrator.state.get('current_question'),
            task="wait_for_user_input", # 클라이언트가 이 task를 보고 사용자 입력을 활성화
            next_agent="user"
        )
        # 추가적으로 클라이언트가 UI를 구성하는 데 필요한 정보를 덧붙여줍니다.
        response_to_client['status'] = 'waiting_for_user'
        response_to_client['message'] = '답변을 입력해주세요.'
        return response_to_client
                

    async def _request_question_from_interviewer(self, orchestrator: Orchestrator) -> str:
        """면접관(QuestionGenerator)에게 질문 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            interview_logger.info(f"📤 면접관에게 질문 생성 요청: {orchestrator.state['session_id']}")
            
            # QuestionGenerator에게 상태 객체(state)를 전달하여 질문 생성
            question_data = await asyncio.to_thread(
                self.question_generator.generate_question_with_orchestrator_state,
                orchestrator.get_current_state()
            )
            return question_data.get('question', '다음 질문이 무엇인가요?')
            
        except Exception as e:
            interview_logger.error(f"면접관 질문 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 질문을 생성하는 데 문제가 발생했습니다."

    async def _request_answer_from_ai_candidate(self, orchestrator: Orchestrator, question: str) -> str:
        """AI 지원자에게 답변 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            interview_logger.info(f"📤 AI 지원자에게 답변 요청: {orchestrator.state['session_id']}")
            
            state = orchestrator.get_current_state()
            ai_persona = state.get('ai_persona')
            
            # 답변 생성 요청 구성
            answer_request = AnswerRequest(
                question_content=question,
                question_type=QuestionType.HR, # TODO: 질문 유형을 state에서 가져오도록 개선
                question_intent="면접관의 질문",
                company_id=state.get('company_id'),
                position=state.get('position'),
                quality_level=QualityLevel.AVERAGE,
                llm_provider=LLMProvider.OPENAI_GPT4O
            )
            
            response = await asyncio.to_thread(
                self.ai_candidate_model.generate_answer,
                request=answer_request,
                persona=ai_persona
            )
            return response.answer_content
            
        except Exception as e:
            interview_logger.error(f"AI 지원자 답변 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 답변을 생성하는 데 문제가 발생했습니다."

    def get_interview_flow_status(self, session_id: str) -> Dict[str, Any]:
        """현재 면접 진행 상태와 다음 액션을 반환"""
        orchestrator, error = self._get_orchestrator_or_error(session_id)
        if error:
            return error
        
        return orchestrator.get_current_state()

