import time
import json
import random
import asyncio
import re
import base64
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

# TTS 동시 요청 제한을 위한 세마포어 추가
_tts_semaphore = asyncio.Semaphore(1)  # 한 번에 하나의 TTS 요청만 허용

@dataclass
class Metadata:
    interview_id: str
    step: int
    task: str
    from_agent: str 
    next_agent: str
    status_code: int

@dataclass
class Content:
    type: str
    content: str

@dataclass
class Metrics:
    total_time: Optional[float] = None
    duration: Optional[float] = None

@dataclass
class AgentMessage:
    metadata: Metadata
    content: Content
    metrics: Metrics = field(default_factory=Metrics)

class Orchestrator:
    def __init__(self, session_id: str, session_state: Dict[str, Any], 
                 question_generator=None, ai_candidate_model=None):
        """
        Orchestrator: 모든 면접 비즈니스 로직 담당
        - 플로우 제어
        - 에이전트 조율
        - 메시지 처리
        - 상태 업데이트
        """
        self.session_id = session_id
        self.session_state = session_state  # InterviewService의 session_state 참조
        self.question_generator = question_generator
        self.ai_candidate_model = ai_candidate_model

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지를 받아서 상태를 업데이트하고 다음 액션을 결정"""
        from_agent = message.get("metadata", {}).get("from_agent", "unknown")
        print(f"[TRACE] {from_agent} -> Orchestrator")
        print(json.dumps(message, indent=2, ensure_ascii=False))

        task = message.get("metadata", {}).get("task")
        content = message.get("content", {}).get("content")

        # 상태 업데이트
        self._update_state_from_message(task, content, from_agent)

        # 다음 메시지 결정
        next_message = self._decide_next_message()
        next_agent = next_message.get("metadata", {}).get("next_agent", "unknown")
        print(f"[TRACE] Orchestrator -> {next_agent}")
        print(json.dumps(next_message, indent=2, ensure_ascii=False))
        return next_message

    def _update_state_from_message(self, task: str, content: str, from_agent: str) -> None:
        """메시지로부터 세션 상태 업데이트"""
        if task == "intro_generated":
            # 인트로 메시지 생성 완료 - 세션에 저장
            self.session_state['intro_message'] = content
            # 답변 없이 바로 턴 증가
            self.session_state['turn_count'] += 1  # 턴 0 완료, 턴 1로 이동
            # current_question은 설정하지 않음 (답변 요청하지 않음)
            
        elif task == "question_generated":
            # 턴 0에서 받은 메시지는 인트로 메시지로 처리
            current_turn = self.session_state.get('turn_count', 0)
            if current_turn == 0:
                self.session_state['intro_message'] = content
                self.session_state['turn_count'] += 1  # 턴 0 완료, 턴 1로 이동
                print(f"[DEBUG] 인트로 메시지 처리 완료: 턴 {current_turn} -> {self.session_state['turn_count']}")
            else:
                # 일반 질문 처리
                self.session_state['current_question'] = content
                print(f"[DEBUG] 일반 질문 처리: 턴 {current_turn}")
            
            # 🆕 질문 타입 추출 로직 제거 - QuestionGenerator에서 결정한 면접관 사용
            # current_interviewer는 QuestionGenerator에서 이미 설정됨
            # 여기서는 질문 내용만 저장하고 면접관 추측하지 않음
            
        elif task == "individual_questions_generated":
            # 🆕 개별 꼬리질문 생성 완료 - content는 dict 형태
            import json
            if isinstance(content, str):
                questions_data = json.loads(content)
            else:
                questions_data = content
                
            self.session_state['current_questions'] = {
                'user_question': questions_data.get('user_question', {}),
                'ai_question': questions_data.get('ai_question', {}),
                'is_individual': questions_data.get('is_individual_questions', True),
                'interviewer_type': questions_data.get('interviewer_type', 'HR')
            }
            
            print(f"[DEBUG] 개별 꼬리질문 상태 저장 완료")
            print(f"[DEBUG] 사용자 질문: {questions_data.get('user_question', {}).get('question', 'N/A')[:30]}...")
            print(f"[DEBUG] AI 질문: {questions_data.get('ai_question', {}).get('question', 'N/A')[:30]}...")
            
        elif task == "individual_answer_generated":
            # 🆕 개별 질문에 대한 답변 처리
            current_questions = self.session_state.get('current_questions', {})
            if current_questions.get('is_individual', False):
                # 개별 질문의 경우 answerer에 따라 해당하는 질문 매핑
                if from_agent == 'user':
                    question_text = current_questions.get('user_question', {}).get('question', '')
                elif from_agent == 'ai':
                    question_text = current_questions.get('ai_question', {}).get('question', '')
                else:
                    question_text = self.session_state.get('current_question', '')
            else:
                question_text = self.session_state.get('current_question', '')
            
            # qa_history에 답변 저장
            qa_entry = {
                "question": question_text,
                "answerer": from_agent,
                "answer": content
            }
            self.session_state['qa_history'].append(qa_entry)
            print(f"[DEBUG] QA 저장: answerer={from_agent}, question='{question_text[:50]}...', answer='{content[:30]}...'")
            
            # 개별 답변 완료 체크 (사용자와 AI 모두 답변했는지)
            if current_questions.get('is_individual', False):
                # 현재 턴의 개별 답변 수 계산
                individual_answers = len([qa for qa in self.session_state['qa_history'] 
                                        if qa['question'] in [
                                            current_questions.get('user_question', {}).get('question', ''),
                                            current_questions.get('ai_question', {}).get('question', '')
                                        ]])
                
                if individual_answers >= 2:
                    self._handle_turn_completion_for_individual_questions()
            else:
                # 기존 로직 유지 (공통 질문인 경우)
                self._handle_turn_completion_for_common_question()
                
        elif task == "answer_generated":
            # 기존 답변 처리 (메인 질문 또는 공통 꼬리질문)
            # AI가 실제로 받은 질문이 사용자 질문과 다를 수 있으므로 보정
            if from_agent == 'ai' and '_ai_actual_question' in self.session_state:
                question_text = self.session_state.pop('_ai_actual_question')
            else:
                question_text = self.session_state['current_question']

            qa_entry = {
                "question": question_text,
                "answerer": from_agent,
                "answer": content
            }
            self.session_state['qa_history'].append(qa_entry)
            print(f"[DEBUG] QA 저장 (async): answerer={from_agent}, question='{question_text[:50]}...', answer='{content[:30]}...'")

            # 두 답변이 모두 완료되면 턴 증가 및 꼬리 질문 상태 업데이트
            # 현재 질문(사용자용)과 AI용 변환 텍스트 둘 다에 대해 답변이 존재하는지 확인
            try:
                user_question = self.session_state['current_question']
                ai_question_variant = self._format_question_for_ai(user_question)
                answers_for_pair = [qa for qa in self.session_state['qa_history']
                                    if qa['question'] in (user_question, ai_question_variant)]
                answerers = {qa['answerer'] for qa in answers_for_pair}
                if {'user', 'ai'}.issubset(answerers):
                    self._handle_turn_completion_for_common_question()
            except Exception:
                # 폴백: 기존 방식으로 현재 질문 텍스트 기준 카운트
                current_answers = len([qa for qa in self.session_state['qa_history']
                                      if qa['question'] == self.session_state['current_question']])
                if current_answers >= 2:
                    self._handle_turn_completion_for_common_question()

    def _handle_turn_completion_for_common_question(self):
        """공통 질문 완료 시 처리"""
        # 🆕 꼬리 질문 카운트 증가 (수정된 로직)
        current_interviewer = self.session_state.get('current_interviewer')
        if current_interviewer and current_interviewer in ['HR', 'TECH', 'COLLABORATION']:
            turn_state = self.session_state.get('interviewer_turn_state', {})
            if current_interviewer in turn_state:
                # 현재 질문이 메인 질문인지 꼬리 질문인지 판단
                current_turn = self.session_state.get('turn_count', 0)
                
                # 턴 1, 2는 고정 질문이므로 카운트하지 않음
                if current_turn > 2:
                    # 메인 질문 완료 표시
                    if not turn_state[current_interviewer]['main_question_asked']:
                        turn_state[current_interviewer]['main_question_asked'] = True
                    else:
                        # 꼬리 질문 카운트 증가
                        turn_state[current_interviewer]['follow_up_count'] += 1
        
        self.session_state['turn_count'] += 1
        self.session_state['current_question'] = None
    
    def _handle_turn_completion_for_individual_questions(self):
        """개별 꼬리질문 완료 시 처리"""
        current_interviewer = self.session_state.get('current_interviewer')
        if current_interviewer and current_interviewer in ['HR', 'TECH', 'COLLABORATION']:
            turn_state = self.session_state.get('interviewer_turn_state', {})
            if current_interviewer in turn_state:
                # 꼬리 질문 카운트 증가
                turn_state[current_interviewer]['follow_up_count'] += 1
        
        self.session_state['turn_count'] += 1
        self.session_state['current_questions'] = None
        print(f"[DEBUG] 개별 꼬리질문 턴 완료, 다음 턴으로 이동")

    def _decide_next_message(self) -> Dict[str, Any]:
        """다음 메시지 결정 - 실제 플로우 제어 로직"""
        current_turn = self.session_state.get('turn_count', 0)
        start_time = self.session_state.get('start_time')
        
        # 턴 0: 인트로 처리
        if current_turn == 0:
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_intro",
                from_agent="orchestrator",
                content_text="인트로 메시지를 생성해주세요.",
                turn_count=current_turn,
                content_type="INTRO",
                start_time=start_time
            )
            message["metadata"]["next_agent"] = "interviewer"
            return message
        
        # 완료 조건 체크 (턴 0: 인트로 제외)
        if current_turn > self.session_state.get('total_question_limit', 15):
            self.session_state['is_completed'] = True
            message = self.create_agent_message(
                session_id=self.session_id,
                task="end_interview",
                from_agent="orchestrator",
                content_text="수고하셨습니다.",
                turn_count=current_turn,
                content_type="OUTTRO",
                start_time=start_time
            )
            message["metadata"]["next_agent"] = "orchestrator"
            return message

        # 🆕 개별 꼬리질문 처리 로직
        current_questions = self.session_state.get('current_questions')
        if current_questions and current_questions.get('is_individual', False):
            return self._handle_individual_questions_flow(current_questions, current_turn, start_time)
        
        # 현재 질문이 없으면 새 질문 생성 (메인 질문 또는 꼬리질문 결정)
        if not self.session_state.get('current_question'):
            # 🆕 꼬리질문 생성 조건 체크
            if self._should_generate_individual_follow_up():
                print(f"[DEBUG] 개별 꼬리질문 생성 조건 만족")
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="generate_individual_follow_up",
                    from_agent="orchestrator",
                    content_text="개별 꼬리질문을 생성해주세요.",
                    turn_count=current_turn,
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = "interviewer_individual"
                return message
            else:
                # 일반 메인 질문 생성
                message = self.create_agent_message(
                    session_id=self.session_id,
                    task="generate_question",
                    from_agent="orchestrator",
                    content_text="다음 질문을 생성해주세요.",
                    turn_count=current_turn,
                    start_time=start_time
                )
                message["metadata"]["next_agent"] = "interviewer"
                return message
        
        # 현재 메인 질문에 대한 답변 수 확인 (AI용 변형 포함)
        user_question = self.session_state['current_question']
        ai_question_variant = self._format_question_for_ai(user_question) if user_question else None
        current_answers = len([qa for qa in self.session_state['qa_history']
                             if qa['question'] == user_question or (ai_question_variant and qa['question'] == ai_question_variant)])
        
        # 첫 번째 답변: 랜덤 선택
        if current_answers == 0:
            selected_agent = 'user' if self._random_select() == -1 else 'ai'
            # 에이전트별로 전달할 질문 텍스트 결정
            if selected_agent == 'ai':
                question_text = self._format_question_for_ai(self.session_state['current_question'])
                # QA 기록을 위해 임시 저장
                self.session_state['_ai_actual_question'] = question_text
            else:
                question_text = self.session_state['current_question']
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 번째 답변: 반대 에이전트
        elif current_answers == 1:
            # 첫 번째 답변자 확인
            first_answerer = self.session_state['qa_history'][-1]['answerer']
            selected_agent = 'ai' if first_answerer == 'user' else 'user'
            # 에이전트별로 전달할 질문 텍스트 결정
            if selected_agent == 'ai':
                question_text = self._format_question_for_ai(self.session_state['current_question'])
                self.session_state['_ai_actual_question'] = question_text
            else:
                question_text = self.session_state['current_question']
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 모든 답변 완료: 다음 질문으로
        else:
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_question",
                from_agent="orchestrator",
                content_text="다음 질문을 생성해주세요.",
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = "interviewer"
            return message

   

    def _random_select(self) -> int:
        """사용자와 AI 중 랜덤으로 선택"""
        return random.choice([-1, 1])

    def _should_generate_individual_follow_up(self) -> bool:
        """개별 꼬리질문을 생성할 조건인지 체크"""
        current_turn = self.session_state.get('turn_count', 0)
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        
        # 턴 3 이후 && 현재 면접관이 설정되어 있고 && 메인 질문이 완료된 상태
        if (current_turn > 2 and 
            current_interviewer and 
            current_interviewer in turn_state):
            
            interviewer_state = turn_state[current_interviewer]
            main_asked = interviewer_state.get('main_question_asked', False)
            follow_up_count = interviewer_state.get('follow_up_count', 0)
            
            # 메인 질문은 완료했고, 꼬리질문이 2개 미만인 경우
            if main_asked and follow_up_count < 2:
                # 최근에 두 답변이 모두 완료되었는지 확인
                qa_history = self.session_state.get('qa_history', [])
                if len(qa_history) >= 2:
                    # 마지막 2개가 같은 질문에 대한 답변인지 확인
                    recent_questions = [qa['question'] for qa in qa_history[-2:]]
                    if len(set(recent_questions)) == 1:  # 같은 질문
                        print(f"[DEBUG] 개별 꼬리질문 조건 만족: {current_interviewer}, follow_up={follow_up_count}/2")
                        return True
        
        return False

    def _handle_individual_questions_flow(self, current_questions: Dict, current_turn: int, start_time: float) -> Dict[str, Any]:
        """개별 꼬리질문 플로우 처리"""
        user_question = current_questions.get('user_question', {}).get('question', '')
        ai_question = current_questions.get('ai_question', {}).get('question', '')
        
        # 개별 질문들에 대한 답변 수 확인
        qa_history = self.session_state.get('qa_history', [])
        individual_answers = len([qa for qa in qa_history 
                                if qa['question'] in [user_question, ai_question]])
        
        print(f"[DEBUG] 개별 질문 플로우: 답변 수 {individual_answers}/2")
        
        # 첫 번째 답변: 랜덤 선택
        if individual_answers == 0:
            selected_agent = 'user' if self._random_select() == -1 else 'ai'
            question_text = user_question if selected_agent == 'user' else ai_question
            
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_individual_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 번째 답변: 반대 에이전트
        elif individual_answers == 1:
            # 첫 번째 답변자 확인
            first_answerer = qa_history[-1]['answerer']
            selected_agent = 'ai' if first_answerer == 'user' else 'user'
            question_text = user_question if selected_agent == 'user' else ai_question
            
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_individual_answer",
                from_agent="orchestrator",
                content_text=question_text,
                turn_count=current_turn,
                start_time=start_time
            )
            message["metadata"]["next_agent"] = selected_agent
            return message
        
        # 두 답변 모두 완료: 다음 단계로 (이 경우는 이미 _update_state_from_message에서 처리됨)
        else:
            return self._decide_next_message()  # 재귀 호출로 다음 단계 결정

    # 에이전트 조율 메서드들 (내부 처리용)
    async def _request_question_from_interviewer(self) -> str:
        """면접관(QuestionGenerator)에게 질문 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            from llm.shared.logging_config import interview_logger
            interview_logger.info(f"📤 면접관에게 질문 생성 요청: {self.session_id}")
            
            # QuestionGenerator에게 상태 객체(state)를 전달하여 질문 생성
            question_data = await asyncio.to_thread(
                self.question_generator.generate_question_with_orchestrator_state,
                self.session_state
            )
            
            # 🆕 턴 전환 처리
            if question_data.get('turn_switch'):
                # 🆕 턴 전환 시 바로 다음 질문을 요청 (재귀 호출)
                print(f"[DEBUG] 턴 전환 감지: {question_data.get('message', '')}")
                # 상태 업데이트 후 다시 질문 요청
                return await self._request_question_from_interviewer()
            
            # 🆕 개별 질문 데이터 체크 - 직접 반환
            if 'user_question' in question_data and 'ai_question' in question_data:
                print(f"[DEBUG] 개별 질문 감지됨 - 개별 질문 데이터 반환")
                return question_data  # Dict 형태로 반환
            
            # 일반 질문 반환
            return question_data.get('question', '다음 질문이 무엇인가요?')
            
        except Exception as e:
            from llm.shared.logging_config import interview_logger
            interview_logger.error(f"면접관 질문 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 질문을 생성하는 데 문제가 발생했습니다."

    async def _request_individual_follow_up_questions(self) -> Dict[str, Any]:
        """면접관에게 개별 꼬리질문 2개 생성 요청"""
        try:
            from llm.shared.logging_config import interview_logger
            interview_logger.info(f"📤 면접관에게 개별 꼬리질문 생성 요청: {self.session_id}")
            
            # qa_history에서 최신 답변들 추출
            qa_history = self.session_state.get('qa_history', [])
            if len(qa_history) < 2:
                raise ValueError("개별 꼬리질문을 생성하려면 최소 2개의 답변이 필요합니다")
            
            # 가장 최근 질문과 답변들 추출 
            latest_qa_pairs = qa_history[-2:]  # 마지막 2개 (사용자 + AI 답변)
            previous_question = latest_qa_pairs[0]['question'] if latest_qa_pairs else ''
            
            # 사용자와 AI 답변 분리
            user_answer = ""
            ai_answer = ""
            for qa in latest_qa_pairs:
                if qa['answerer'] == 'user':
                    user_answer = qa['answer']
                elif qa['answerer'] == 'ai':
                    ai_answer = qa['answer']
            
            if not user_answer or not ai_answer:
                raise ValueError("사용자와 AI 답변이 모두 필요합니다")
            
            # 회사 정보 가져오기
            company_info = self.question_generator.companies_data.get(
                self.session_state.get('company_id'), {}
            )
            
            # 현재 면접관 정보
            current_interviewer = self.session_state.get('current_interviewer', 'HR')
            
            # 사용자 이력서 정보
            user_resume = {
                'name': self.session_state.get('user_name', '지원자'),
                'position': self.session_state.get('position', '개발자')
            }
            
            print(f"[DEBUG] 개별 꼬리질문 생성 - 면접관: {current_interviewer}")
            print(f"[DEBUG] 이전 질문: {previous_question[:50]}...")
            print(f"[DEBUG] 사용자 답변: {user_answer[:50]}...")
            print(f"[DEBUG] AI 답변: {ai_answer[:50]}...")
            
            # 개별 꼬리질문 생성 요청
            follow_up_data = await asyncio.to_thread(
                self.question_generator.generate_follow_up_questions_for_both,
                previous_question=previous_question,
                user_answer=user_answer,
                ai_answer=ai_answer,
                company_info=company_info,
                interviewer_role=current_interviewer,
                user_resume=user_resume
            )
            
            return follow_up_data
            
        except Exception as e:
            from llm.shared.logging_config import interview_logger
            interview_logger.error(f"개별 꼬리질문 요청 오류: {e}", exc_info=True)
            
            # 폴백: 공통 꼬리질문 사용
            try:
                common_question = await self._request_question_from_interviewer()
                return {
                    'user_question': {'question': common_question},
                    'ai_question': {'question': common_question},
                    'interviewer_type': self.session_state.get('current_interviewer', 'HR'),
                    'question_type': 'follow_up',
                    'is_individual_questions': False,
                    'fallback_reason': 'individual_request_failed'
                }
            except Exception as fallback_error:
                interview_logger.error(f"폴백 질문 생성도 실패: {fallback_error}")
                return {
                    'user_question': {'question': '추가로 설명해 주실 수 있나요?'},
                    'ai_question': {'question': '더 자세한 내용을 말씀해 주세요.'},
                    'interviewer_type': 'HR',
                    'question_type': 'follow_up',
                    'is_individual_questions': False,
                    'fallback_reason': 'complete_fallback'
                }

    async def _request_answer_from_ai_candidate(self, question: str) -> str:
        """AI 지원자에게 답변 생성을 요청하고, 텍스트 결과만 반환"""
        try:
            from llm.shared.logging_config import interview_logger
            interview_logger.info(f"📤 AI 지원자에게 답변 요청: {self.session_id}")
            
            ai_persona = self.session_state.get('ai_persona')
            
            # 답변 생성 요청 구성
            from llm.shared.models import AnswerRequest, QuestionType, LLMProvider
            from llm.candidate.quality_controller import QualityLevel
            
            answer_request = AnswerRequest(
                question_content=question,
                question_type=QuestionType.HR, # TODO: 질문 유형을 state에서 가져오도록 개선
                question_intent="면접관의 질문",
                company_id=self.session_state.get('company_id'),
                position=self.session_state.get('position'),
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
            from llm.shared.logging_config import interview_logger
            interview_logger.error(f"AI 지원자 답변 요청 오류: {e}", exc_info=True)
            return "죄송합니다, 답변을 생성하는 데 문제가 발생했습니다."

    async def _generate_tts(self, text: str) -> Optional[str]:
        """텍스트를 TTS로 변환하여 base64 인코딩된 MP3 데이터 반환"""
        async with _tts_semaphore:  # TTS 동시 요청 제한
            try:
                print(f"[🔍 TTS_DEBUG] _generate_tts 함수 시작 (세마포어 획득)")
                print(f"[🔍 TTS_DEBUG] 입력 text: '{text[:100] if text else 'None'}'")
                print(f"[🔍 TTS_DEBUG] text 타입: {type(text)}")
                print(f"[🔍 TTS_DEBUG] text 길이: {len(text) if text else 0}")
                
                if not text or not text.strip():
                    print(f"[🔍 TTS_DEBUG] ❌ text가 비어있음 - 반환 None")
                    return None
                    
                from backend.services.voice_service import elevenlabs_tts_stream
                print(f"[🔍 TTS_DEBUG] voice_service import 성공")
                print(f"[🔍 TTS_DEBUG] TTS 생성 시작: {text[:50]}...")
                print(f"[🔍 TTS_DEBUG] 정제된 text: '{text.strip()[:50]}...'")
                
                # ElevenLabs API 호출
                print(f"[🔍 TTS_DEBUG] elevenlabs_tts_stream 호출 시작")
                audio_bytes = await elevenlabs_tts_stream(
                    text=text.strip(), 
                    voice_id="21m00Tcm4TlvDq8ikWAM"  # Rachel 음성
                )
                print(f"[🔍 TTS_DEBUG] elevenlabs_tts_stream 호출 완료")
                print(f"[🔍 TTS_DEBUG] audio_bytes 타입: {type(audio_bytes)}")
                print(f"[🔍 TTS_DEBUG] audio_bytes 길이: {len(audio_bytes) if audio_bytes else 0}")
                
                if not audio_bytes:
                    print(f"[🔍 TTS_DEBUG] ❌ audio_bytes가 비어있음")
                    return None
                
                # base64 인코딩
                print(f"[🔍 TTS_DEBUG] base64 인코딩 시작")
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                print(f"[🔍 TTS_DEBUG] base64 인코딩 완료")
                print(f"[🔍 TTS_DEBUG] ✅ TTS 생성 완료: {len(audio_base64)} chars (세마포어 해제)")
                
                return audio_base64
                
            except Exception as e:
                print(f"[🔍 TTS_DEBUG] ❌ TTS 생성 실패: {e}")
                import traceback
                print(f"[🔍 TTS_DEBUG] 스택 트레이스: {traceback.format_exc()}")
                return None

    async def _handle_missing_tts_for_first_response(self, result: Dict[str, Any]) -> None:
        """첫 번째 응답에서 누락된 TTS를 추가로 생성"""
        try:
            current_turn = self.session_state.get('turn_count', 0)
            
            print(f"[🔍 TTS_DEBUG] _handle_missing_tts_for_first_response 함수 호출됨")
            print(f"[🔍 TTS_DEBUG] current_turn: {current_turn}")
            print(f"[🔍 TTS_DEBUG] result 키들: {list(result.keys())}")
            
            # 첫 번째 턴(INTRO + 첫 질문)에서만 처리
            if current_turn <= 1:
                print(f"[🔍 TTS_DEBUG] 조건 만족: current_turn({current_turn}) <= 1")
                print(f"[🔍 TTS_DEBUG] 첫 번째 응답 TTS 보완 처리 시작 (턴 {current_turn})")
                
                # INTRO 메시지 TTS 추가 (create_user_waiting_message에서 이미 처리되었을 수 있음)
                intro_message_exists = 'intro_message' in result
                intro_audio_exists = 'intro_audio' in result
                print(f"[🔍 TTS_DEBUG] intro_message 존재: {intro_message_exists}")
                print(f"[🔍 TTS_DEBUG] intro_audio 존재: {intro_audio_exists}")
                
                if intro_message_exists:
                    intro_text = result['intro_message']
                    print(f"[🔍 TTS_DEBUG] intro_text: '{intro_text[:100] if intro_text else 'None'}'")
                    print(f"[🔍 TTS_DEBUG] intro_text.strip() 결과: {bool(intro_text and intro_text.strip())}")
                    
                    if not intro_audio_exists and intro_text and intro_text.strip():
                        print(f"[🔍 TTS_DEBUG] 누락된 INTRO TTS 생성 시작: {intro_text[:50]}...")
                        intro_audio = await self._generate_tts(intro_text)
                        print(f"[🔍 TTS_DEBUG] _generate_tts 결과: {bool(intro_audio)} (길이: {len(intro_audio) if intro_audio else 0})")
                        if intro_audio:
                            result['intro_audio'] = intro_audio
                            print(f"[🔍 TTS_DEBUG] ✅ INTRO TTS 보완 완료")
                        else:
                            print(f"[🔍 TTS_DEBUG] ❌ INTRO TTS 생성 실패")
                    else:
                        if intro_audio_exists:
                            print(f"[🔍 TTS_DEBUG] ⏭️ INTRO audio 이미 존재함")
                        if not intro_text or not intro_text.strip():
                            print(f"[🔍 TTS_DEBUG] ⏭️ INTRO text가 비어있음")
                
                # 첫 질문 TTS 추가 (create_user_waiting_message에서 이미 처리되었을 수 있음)
                question_text = result.get('content', {}).get('content', '')
                question_audio_exists = 'question_audio' in result
                print(f"[🔍 TTS_DEBUG] question_text: '{question_text[:100] if question_text else 'None'}'")
                print(f"[🔍 TTS_DEBUG] question_audio 존재: {question_audio_exists}")
                print(f"[🔍 TTS_DEBUG] question_text.strip() 결과: {bool(question_text and question_text.strip())}")
                
                if question_text and question_text.strip() and not question_audio_exists:
                    print(f"[🔍 TTS_DEBUG] 누락된 첫 질문 TTS 생성 시작: {question_text[:50]}...")
                    question_audio = await self._generate_tts(question_text)
                    print(f"[🔍 TTS_DEBUG] _generate_tts 결과: {bool(question_audio)} (길이: {len(question_audio) if question_audio else 0})")
                    if question_audio:
                        result['question_audio'] = question_audio
                        print(f"[🔍 TTS_DEBUG] ✅ 첫 질문 TTS 보완 완료")
                    else:
                        print(f"[🔍 TTS_DEBUG] ❌ 첫 질문 TTS 생성 실패")
                else:
                    if question_audio_exists:
                        print(f"[🔍 TTS_DEBUG] ⏭️ 질문 audio 이미 존재함")
                    if not question_text or not question_text.strip():
                        print(f"[🔍 TTS_DEBUG] ⏭️ 질문 text가 비어있음")
                        
                print(f"[🔍 TTS_DEBUG] 첫 번째 응답 TTS 보완 처리 완료")
                print(f"[🔍 TTS_DEBUG] 최종 result 키들: {list(result.keys())}")
            else:
                print(f"[🔍 TTS_DEBUG] 조건 불만족: current_turn({current_turn}) > 1, TTS 보완 건너뜀")
            
        except Exception as e:
            print(f"[🔍 TTS_DEBUG] ❌ 첫 번째 응답 TTS 보완 실패: {e}")
            import traceback
            print(f"[🔍 TTS_DEBUG] 스택 트레이스: {traceback.format_exc()}")

    async def _generate_and_play_tts(self, text: str, agent_type: str = "interviewer") -> None:
        """텍스트를 TTS로 변환하고 재생한 후 다음 작업으로 넘어감"""
        try:
            if not text or not text.strip():
                print(f"[🔊 TTS_PLAY] {agent_type} 텍스트가 비어있음 - TTS 건너뜀")
                return
            
            print(f"[🔊 TTS_PLAY] {agent_type} TTS 생성 및 재생 시작: {text[:50]}...")
            
            # TTS 생성
            audio_base64 = await self._generate_tts(text)
            if not audio_base64:
                print(f"[🔊 TTS_PLAY] ❌ {agent_type} TTS 생성 실패")
                return
            
            # TTS 재생 시작
            print(f"[🔊 TTS_PLAY] ✅ {agent_type} TTS 생성 완료, 재생 시작")
            
            # 재생 완료까지 대기
            # 방법 1: 텍스트 길이 기반 대략적 재생 시간 계산 (초당 약 3-4음절)
            estimated_duration = len(text) / 3.5  # 초당 약 3.5음절로 계산
            min_duration = 1.0  # 최소 1초
            max_duration = 10.0  # 최대 10초
            wait_time = max(min_duration, min(estimated_duration, max_duration))
            
            print(f"[🔊 TTS_PLAY] 📊 예상 재생 시간: {wait_time:.1f}초 (텍스트 길이: {len(text)}자)")
            await asyncio.sleep(wait_time)
            
            print(f"[🔊 TTS_PLAY] ✅ {agent_type} TTS 재생 완료, 다음 작업 진행")
            
        except Exception as e:
            print(f"[🔊 TTS_PLAY] ❌ {agent_type} TTS 처리 실패: {e}")
            import traceback
            print(f"[🔊 TTS_PLAY] 스택 트레이스: {traceback.format_exc()}")

    async def _generate_and_play_tts_with_callback(self, text: str, agent_type: str = "interviewer", 
                                                 on_complete: callable = None) -> None:
        """텍스트를 TTS로 변환하고 재생한 후 콜백 함수 실행"""
        try:
            if not text or not text.strip():
                print(f"[🔊 TTS_PLAY] {agent_type} 텍스트가 비어있음 - TTS 건너뜀")
                if on_complete:
                    await on_complete()
                return
            
            print(f"[🔊 TTS_PLAY] {agent_type} TTS 생성 및 재생 시작: {text[:50]}...")
            
            # TTS 생성
            audio_base64 = await self._generate_tts(text)
            if not audio_base64:
                print(f"[🔊 TTS_PLAY] ❌ {agent_type} TTS 생성 실패")
                if on_complete:
                    await on_complete()
                return
            
            # TTS 재생 시작
            print(f"[🔊 TTS_PLAY] ✅ {agent_type} TTS 생성 완료, 재생 시작")
            
            # 재생 완료까지 대기
            estimated_duration = len(text) / 3.5
            min_duration = 1.0
            max_duration = 10.0
            wait_time = max(min_duration, min(estimated_duration, max_duration))
            
            print(f"[🔊 TTS_PLAY] 📊 예상 재생 시간: {wait_time:.1f}초 (텍스트 길이: {len(text)}자)")
            await asyncio.sleep(wait_time)
            
            print(f"[🔊 TTS_PLAY] ✅ {agent_type} TTS 재생 완료")
            
            # 콜백 함수 실행
            if on_complete:
                await on_complete()
            
        except Exception as e:
            print(f"[🔊 TTS_PLAY] ❌ {agent_type} TTS 처리 실패: {e}")
            import traceback
            print(f"[🔊 TTS_PLAY] 스택 트레이스: {traceback.format_exc()}")
            if on_complete:
                await on_complete()

    @staticmethod
    def create_agent_message(session_id: str, task: str, from_agent: str, content_text: str, 
                             turn_count: int, duration: float = 0, content_type: str = "text", 
                             start_time: float = None) -> Dict[str, Any]:
        """외부(Agent)에서 Orchestrator로 보낼 메시지를 생성하는 정적 메서드"""
        # 🆕 total_time 계산
        total_time = None
        if start_time:
            total_time = time.time() - start_time
        
        return {
            "metadata": {
                "interview_id": session_id,
                "step": turn_count,
                "task": task,
                "from_agent": from_agent,
                "next_agent": "orchestrator",
                "status_code": 200
            },
            "content": {
                "type": content_type,
                "content": content_text
            },
            "metrics": {
                "duration": duration,
                "total_time": total_time
            }
        }

    async def process_user_answer(self, user_answer: str, time_spent: float = None) -> Dict[str, Any]:
        """사용자 답변을 처리하고 전체 플로우를 완료하여 최종 결과 반환"""
        print(f"[TRACE] Orchestrator.process_user_answer start: session={self.session_id}")
        
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 1. 사용자 답변 메시지 생성 및 처리
        task = "individual_answer_generated" if is_individual_question else "answer_generated"
        
        user_message = self.create_agent_message(
            session_id=self.session_id,
            task=task,
            from_agent="user",
            content_text=user_answer,
            turn_count=self.session_state.get('turn_count', 0),
            duration=time_spent,
            start_time=self.session_state.get('start_time')
        )
        
        # 2. 사용자 답변으로 상태 업데이트 (handle_message에서 JSON 출력됨)
        self.handle_message(user_message)
        
        # 3. 다음 액션 결정 및 전체 플로우 처리
        return await self._process_complete_flow()
    
    async def _process_complete_flow(self) -> Dict[str, Any]:
        """완전한 플로우를 처리하여 최종 결과 반환"""
        print(f"[TRACE] Orchestrator._process_complete_flow start: session={self.session_id}")
        
        while True:
            print(f"[TRACE] turn={self.session_state.get('turn_count', 0)}")
            
            # 다음 메시지 결정
            next_message = self._decide_next_message()
            next_agent = next_message.get("metadata", {}).get("next_agent")
            task = next_message.get("metadata", {}).get("task")
            
            print(f"[TRACE] decide_next -> next_agent={next_agent}, task={task}")
            
            # 완료 조건 체크
            if task == "end_interview":
                print(f"[TRACE] interview complete")
                result = {
                    "status": "completed",
                    "message": "수고하셨습니다.",
                    "qa_history": self.session_state.get('qa_history', []),
                    "session_id": self.session_id
                }
                # 🆕 프론트 추출용 AI 메타데이터 포함 (resume_id 전달)
                try:
                    ai_resume_id = self.session_state.get('ai_resume_id') or (
                        (self.session_state.get('ai_persona') or {}).get('resume_id') if isinstance(self.session_state.get('ai_persona'), dict) else None
                    )
                except Exception:
                    ai_resume_id = None
                result['turn_info'] = {
                    'ai_metadata': {
                        'resume_id': ai_resume_id
                    }
                }
                print(f"[TRACE] Orchestrator -> Client (complete)")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # 사용자 입력 대기 상태인 경우
            if next_agent == "user":
                print(f"[TRACE] wait for user input")
                result = await self.create_user_waiting_message()
                
                # 🆕 첫 번째 응답에서 누락된 TTS 처리
                await self._handle_missing_tts_for_first_response(result)
                
                print(f"[TRACE] Orchestrator -> Client (wait)")
                # JSON 출력은 create_user_waiting_message에서 이미 처리됨
                return result
            
            # 에이전트 작업 수행 (handle_message에서 JSON 출력됨)
            if next_agent == "interviewer":
                print(f"[TRACE] interviewer task start")
                await self._process_interviewer_task_parallel()
            elif next_agent == "interviewer_individual":
                print(f"[TRACE] interviewer individual follow-up task start")
                await self._process_individual_interviewer_task_parallel()
            elif next_agent == "ai":
                print(f"[TRACE] ai task start")
                await self._process_ai_task_parallel(next_message.get("content", {}).get("content"))
            
            print(f"[TRACE] loop end")
    
    async def _process_interviewer_task(self):
        """면접관 작업 처리"""
        print(f"[TRACE] Orchestrator -> Interviewer (generate_question)")
        
        # 🆕 현재 상태 디버깅 (개선)
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] interviewer_state turn={current_turn}, current_interviewer={current_interviewer}")
        for role, state in turn_state.items():
            main_done = "✓" if state['main_question_asked'] else "✗"
            follow_count = state['follow_up_count']
            print(f"[DEBUG]   {role}: 메인 {main_done}, 꼬리 {follow_count}개")
        
        question_result = await self._request_question_from_interviewer()
        
        # 🆕 반환값 타입에 따른 처리
        if isinstance(question_result, dict) and 'user_question' in question_result and 'ai_question' in question_result:
            print(f"[TRACE] individual questions generated (dict)")
            
            # 개별 질문 메시지 생성
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(question_result),
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            self.handle_message(questions_message)
            
            # 🆕 개별 질문 TTS 생성 및 재생
            user_question = question_result.get('user_question', {}).get('question', '')
            ai_question = question_result.get('ai_question', {}).get('question', '')
            
            if user_question:
                await self._generate_and_play_tts(user_question, "면접관(사용자용)")
            if ai_question:
                await self._generate_and_play_tts(ai_question, "면접관(AI용)")
            
        else:
            # 일반 질문 처리
            question_content = question_result if isinstance(question_result, str) else str(question_result)
            
            # 🆕 content_type 결정
            content_type = "INTRO" if current_turn == 0 else current_interviewer or "HR"
            
            # 현재 턴에 따라 task 결정
            task = "intro_generated" if current_turn == 0 else "question_generated"
            
            question_message = self.create_agent_message(
                session_id=self.session_id,
                task=task,
                from_agent="interviewer",
                content_text=question_content,
                turn_count=current_turn,
                content_type=content_type,
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (question_generated)
            self.handle_message(question_message)
            
            # 🆕 면접관 질문 TTS 생성 및 재생
            if question_content:
                await self._generate_and_play_tts(question_content, "면접관")
    
    async def _process_individual_interviewer_task(self):
        """개별 꼬리질문 생성 작업 처리"""
        print(f"[TRACE] Orchestrator -> Interviewer (generate_individual_follow_up)")
        
        # 현재 상태 디버깅
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] individual follow-up start turn={current_turn}, interviewer={current_interviewer}")
        
        try:
            # 개별 꼬리질문 생성 요청
            individual_questions = await self._request_individual_follow_up_questions()
            
            # 개별 질문 메시지 생성 및 처리
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(individual_questions),  # Dict를 JSON으로 변환
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            self.handle_message(questions_message)
            
            # 🆕 개별 꼬리질문 TTS 생성 및 재생
            user_question = individual_questions.get('user_question', {}).get('question', '')
            ai_question = individual_questions.get('ai_question', {}).get('question', '')
            
            if user_question:
                await self._generate_and_play_tts(user_question, "면접관(개별-사용자용)")
            if ai_question:
                await self._generate_and_play_tts(ai_question, "면접관(개별-AI용)")
            
        except Exception as e:
            print(f"[TRACE][ERROR] individual follow-up generation failed: {e}")
            # 폴백: 일반 질문으로 대체
            await self._process_interviewer_task()

    async def _process_individual_interviewer_task_parallel(self) -> Dict[str, Any]:
        """
        🆕 병렬 처리를 적용한 개별 꼬리질문 생성 작업 처리
        """
        print(f"[TRACE] Orchestrator -> Interviewer (generate_individual_follow_up)")
        
        # 현재 상태 디버깅
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[TRACE] individual follow-up start turn={current_turn}, interviewer={current_interviewer}")
        
        try:
            # 개별 꼬리질문 생성 요청
            individual_questions = await self._request_individual_follow_up_questions()
            
            # 개별 질문 메시지 생성 및 처리
            questions_message = self.create_agent_message(
                session_id=self.session_id,
                task="individual_questions_generated",
                from_agent="interviewer",
                content_text=json.dumps(individual_questions),  # Dict를 JSON으로 변환
                turn_count=current_turn,
                content_type=current_interviewer or "HR",
                start_time=self.session_state.get('start_time')
            )
            
            # TRACE 출력: interviewer -> orchestrator (individual_questions_generated)
            self.handle_message(questions_message)
            
            # 🆕 병렬 TTS 처리 - 재생을 기다리지 않고 즉시 다음 작업 준비
            user_question = individual_questions.get('user_question', {}).get('question', '')
            ai_question = individual_questions.get('ai_question', {}).get('question', '')
            
            print(f"[DEBUG] 개별 질문 TTS 처리: 사용자용='{user_question[:30]}...', AI용='{ai_question[:30]}...'")
            
            if user_question:
                print(f"[DEBUG] 사용자용 질문 TTS 태스크 생성")
                asyncio.create_task(self._generate_and_play_tts_parallel(user_question, "면접관(개별-사용자용)"))
            if ai_question:
                print(f"[DEBUG] AI용 질문 TTS 태스크 생성")
                asyncio.create_task(self._generate_and_play_tts_parallel(ai_question, "면접관(개별-AI용)"))
            
            return questions_message
            
        except Exception as e:
            print(f"[TRACE][ERROR] individual follow-up generation failed: {e}")
            # 폴백: 일반 질문으로 대체
            return await self._process_interviewer_task_parallel()
    
    async def _process_ai_task(self, question: str):
        """AI 지원자 작업 처리"""
        print(f"[TRACE] Orchestrator -> AI (question) : {question[:50]}...")
        
        # AI에게 전달할 질문에서 사용자 이름 호칭을 AI용으로 최소 치환
        ai_question = self._format_question_for_ai(question)
        
        # 🆕 AI 질문을 클라이언트 전달용으로 임시 저장
        self.session_state['latest_ai_question'] = ai_question
        print(f"[DEBUG] AI 질문 임시 저장: {ai_question[:50]}...")
        
        ai_answer = await self._request_answer_from_ai_candidate(ai_question)
        
        # 🆕 AI 답변을 클라이언트 전달용으로 임시 저장  
        self.session_state['latest_ai_answer'] = ai_answer
        print(f"[DEBUG] AI 답변 임시 저장: {ai_answer[:50]}...")
        
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 🆕 content_type 결정 (현재 면접관 기반)
        current_interviewer = self.session_state.get('current_interviewer', 'HR')
        content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
        
        # 개별 질문 여부에 따라 task 결정
        task = "individual_answer_generated" if is_individual_question else "answer_generated"
        
        # AI가 실제로 받은 질문을 상태에 임시 저장 (qa 기록용)
        self.session_state['_ai_actual_question'] = ai_question

        ai_message = self.create_agent_message(
            session_id=self.session_id,
            task=task,
            from_agent="ai",
            content_text=ai_answer,
            turn_count=self.session_state.get('turn_count', 0),
            content_type=content_type,
            start_time=self.session_state.get('start_time')
        )
        
        # handle_message에서 JSON 출력됨
        self.handle_message(ai_message)
        
        # 🆕 AI 답변 TTS 생성 및 재생
        if ai_answer:
            await self._generate_and_play_tts(ai_answer, "AI지원자")

    async def create_user_waiting_message(self) -> Dict[str, Any]:
        """사용자 입력 대기 메시지 생성"""
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 🆕 질문 텍스트 결정
        if is_individual_question:
            question_text = current_questions.get('user_question', {}).get('question', '')
            print(f"[DEBUG] 사용자 개별 질문: {question_text[:50]}...")
        else:
            question_text = self.session_state.get('current_question', '')
        
        # 🆕 content_type 결정 (현재 면접관 기반)
        current_interviewer = self.session_state.get('current_interviewer', 'HR')
        content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
        
        response = self.create_agent_message(
            session_id=self.session_id,
            task="wait_for_user_input",
            from_agent="orchestrator",
            content_text=question_text,
            turn_count=self.session_state.get('turn_count', 0),
            content_type=content_type,
            start_time=self.session_state.get('start_time')
        )
        # next_agent를 'user'로 수정하여 프론트엔드가 올바르게 인식하도록 함
        response['metadata']['next_agent'] = 'user'
        response['status'] = 'waiting_for_user'
        response['message'] = '답변을 입력해주세요.'
        response['session_id'] = self.session_id
        
        # 🆕 INTRO 메시지 포함 (있는 경우) - 한 번만 전달 + TTS 변환
        intro_message = self.session_state.get('intro_message')
        print(f"[🔍 TTS_DEBUG] create_user_waiting_message - intro_message 존재: {bool(intro_message)}")
        if intro_message:
            print(f"[🔍 TTS_DEBUG] intro_message 내용: '{intro_message[:100] if intro_message else 'None'}'")
            response['intro_message'] = intro_message
            print(f"[🔍 TTS_DEBUG] INTRO 메시지 클라이언트 전달: {intro_message[:50]}...")
            
            # TTS 변환
            print(f"[🔍 TTS_DEBUG] INTRO TTS 생성 시작...")
            intro_audio = await self._generate_tts(intro_message)
            print(f"[🔍 TTS_DEBUG] INTRO TTS 생성 결과: {bool(intro_audio)} (길이: {len(intro_audio) if intro_audio else 0})")
            if intro_audio:
                response['intro_audio'] = intro_audio
                print(f"[🔍 TTS_DEBUG] ✅ INTRO TTS 생성 완료")
            else:
                print(f"[🔍 TTS_DEBUG] ❌ INTRO TTS 생성 실패")
            
            # 한 번 전달 후 삭제
            del self.session_state['intro_message']
            print(f"[🔍 TTS_DEBUG] intro_message 세션에서 삭제됨")
        else:
            print(f"[🔍 TTS_DEBUG] intro_message가 세션에 없음")
        
        # 🆕 턴 정보 추가 (개별 질문 정보 포함)
        try:
            ai_resume_id = self.session_state.get('ai_resume_id') or (
                (self.session_state.get('ai_persona') or {}).get('resume_id') if isinstance(self.session_state.get('ai_persona'), dict) else None
            )
        except Exception:
            ai_resume_id = None
        response['turn_info'] = {
            'current_turn': self.session_state.get('turn_count', 0),
            'is_user_turn': True,
            'is_individual_question': is_individual_question,
            'question_type': 'individual_follow_up' if is_individual_question else 'main_question',
            'ai_metadata': {
                'resume_id': ai_resume_id
            }
        }
        
        # 🆕 AI 질문과 답변을 클라이언트로 전달 (TTS용) + TTS 변환
        latest_ai_question = self.session_state.get('latest_ai_question')
        latest_ai_answer = self.session_state.get('latest_ai_answer')
        
        print(f"[DEBUG] AI 데이터 전달 체크:")
        print(f"  - latest_ai_question 존재: {bool(latest_ai_question)}")
        print(f"  - latest_ai_answer 존재: {bool(latest_ai_answer)}")
        
        if latest_ai_question:
            response['ai_question'] = {
                'content': latest_ai_question
            }
            print(f"[DEBUG] AI 질문 클라이언트 전달: {latest_ai_question[:50]}...")
            
            # TTS 변환
            ai_question_audio = await self._generate_tts(latest_ai_question)
            if ai_question_audio:
                response['ai_question_audio'] = ai_question_audio
                print(f"[DEBUG] AI 질문 TTS 생성 완료")
            
            # 한번 전달 후 삭제
            del self.session_state['latest_ai_question']
            
        if latest_ai_answer:
            response['ai_answer'] = {
                'content': latest_ai_answer
            }
            print(f"[DEBUG] AI 답변 클라이언트 전달: {latest_ai_answer[:50]}...")
            
            # TTS 변환
            ai_answer_audio = await self._generate_tts(latest_ai_answer)
            if ai_answer_audio:
                response['ai_answer_audio'] = ai_answer_audio
                print(f"[DEBUG] AI 답변 TTS 생성 완료")
            
            # 한번 전달 후 삭제
            del self.session_state['latest_ai_answer']
        
        # 🆕 사용자 질문 TTS 변환
        print(f"[🔍 TTS_DEBUG] 사용자 질문 TTS 변환 체크:")
        print(f"[🔍 TTS_DEBUG] question_text: '{question_text[:100] if question_text else 'None'}'")
        print(f"[🔍 TTS_DEBUG] question_text.strip() 결과: {bool(question_text and question_text.strip())}")
        if question_text and question_text.strip():
            print(f"[🔍 TTS_DEBUG] 사용자 질문 TTS 생성 시작...")
            question_audio = await self._generate_tts(question_text)
            print(f"[🔍 TTS_DEBUG] 사용자 질문 TTS 생성 결과: {bool(question_audio)} (길이: {len(question_audio) if question_audio else 0})")
            if question_audio:
                response['question_audio'] = question_audio
                print(f"[🔍 TTS_DEBUG] ✅ 사용자 질문 TTS 생성 완료: {question_text[:50]}...")
            else:
                print(f"[🔍 TTS_DEBUG] ❌ 사용자 질문 TTS 생성 실패")
        else:
            print(f"[🔍 TTS_DEBUG] 사용자 질문 text가 비어있음, TTS 건너뜀")
        
        # 🆕 최종 응답 JSON 로그 (디버깅용) - 오디오 데이터 축약
        print(f"[DEBUG] 최종 클라이언트 응답 JSON:")
        response_for_log = response.copy()
        
        # 오디오 필드들을 길이 정보로 대체
        audio_fields = ['intro_audio', 'ai_question_audio', 'ai_answer_audio', 'question_audio']
        for field in audio_fields:
            if field in response_for_log:
                audio_data = response_for_log[field]
                if audio_data:
                    response_for_log[field] = f"[AUDIO_DATA:{len(audio_data)} chars]"
                else:
                    response_for_log[field] = "[AUDIO_DATA:EMPTY]"
        
        print(json.dumps(response_for_log, indent=2, ensure_ascii=False))
        
        # 🆕 TTS 생성 상태 요약
        print(f"[🔍 TTS_SUMMARY] === TTS 생성 결과 요약 ===")
        for field in audio_fields:
            if field in response:
                status = "✅ 성공" if response[field] else "❌ 실패"
                length = len(response[field]) if response[field] else 0
                print(f"[🔍 TTS_SUMMARY] {field}: {status} ({length} chars)")
            else:
                print(f"[🔍 TTS_SUMMARY] {field}: ⏭️ 없음")
        print(f"[🔍 TTS_SUMMARY] ========================")
        
        return response

    def _format_question_for_ai(self, question: str) -> str:
        """AI에게 보낼 때 사용자 이름 호칭을 'AI 지원자님'으로 최소 치환"""
        try:
            if not isinstance(question, str):
                return question

            user_name_raw = self.session_state.get('user_name', '지원자') or '지원자'
            # 공백 제거 및 '님' 제거한 두 가지 버전 준비
            user_name_compact = re.sub(r"\s+", "", user_name_raw)
            name_wo_suffix = user_name_compact[:-1] if user_name_compact.endswith('님') else user_name_compact

            # 패턴들: 맨 앞에 등장하는 이름 호칭 + 선택적 공백/콤마를 AI용으로 치환
            patterns = [
                rf"^\s*{re.escape(name_wo_suffix)}\s*님\s*[,， ]*",
                rf"^\s*{re.escape(user_name_compact)}\s*[,， ]*",
                rf"{re.escape(name_wo_suffix)}\s*님\s*[,， ]*",
                rf"{re.escape(user_name_compact)}\s*[,， ]*",
            ]

            for pat in patterns:
                if re.search(pat, question):
                    question = re.sub(pat, "AI 지원자님, ", question, count=1)
                    break

            # 일반적인 '지원자님' 호칭 치환 (한 번만)
            if re.search(r"지원자님\s*[,， ]*", question):
                question = re.sub(r"지원자님\s*[,， ]*", "AI 지원자님, ", question, count=1)

            # 선두에 중복된 'AI ' 토큰 정리: 'AI AI 지원자님' -> 'AI 지원자님'
            question = re.sub(r"^\s*(AI\s+)+지원자님\s*[,， ]*", "AI 지원자님, ", question)

            # 호칭이 없으면 앞에만 붙임 (중복 방지)
            if not question.strip().startswith("AI 지원자님"):
                question = f"AI 지원자님, {question}"
            return question
        except Exception:
            return question

    async def _generate_and_play_tts_parallel(self, text: str, agent_type: str = "interviewer") -> None:
        """
        🆕 병렬 처리를 통한 효율적인 TTS 생성 및 재생
        TTS 생성과 재생을 별도 태스크로 분리하여 동시에 처리
        """
        try:
            print(f"🎵 [{agent_type}] TTS 병렬 처리 시작: {text[:50]}...")
            print(f"[DEBUG] TTS 함수 호출됨 - agent_type: {agent_type}, text_length: {len(text)}")
            
            # TTS 생성 태스크 (백그라운드에서 실행)
            print(f"🎵 [{agent_type}] TTS 생성 태스크 시작 (세마포어 대기 중...)")
            tts_task = asyncio.create_task(self._generate_tts_async(text))
            
            # TTS 생성이 완료될 때까지 대기
            audio_data = await tts_task
            
            if audio_data:
                # 재생 태스크 시작 (백그라운드에서 실행)
                playback_task = asyncio.create_task(self._play_audio_async(audio_data, text))
                
                # 재생 태스크를 백그라운드에서 실행하고 즉시 반환
                # 이렇게 하면 재생 중에도 다음 작업을 준비할 수 있음
                print(f"🎵 [{agent_type}] TTS 재생 시작 (백그라운드)")
                
                # 재생 완료를 기다리지 않고 즉시 반환
                # 필요시 나중에 playback_task를 await할 수 있음
                
            else:
                print(f"❌ [{agent_type}] TTS 생성 실패")
                
        except Exception as e:
            print(f"❌ [{agent_type}] TTS 병렬 처리 중 오류: {e}")

    async def _generate_tts_async(self, text: str) -> Optional[str]:
        """
        🆕 비동기 TTS 생성
        """
        try:
            print(f"[DEBUG] _generate_tts_async 호출됨 - text_length: {len(text)}")
            # 실제 TTS 서비스 호출을 비동기로 처리
            audio_data = await self._generate_tts(text)
            print(f"[DEBUG] _generate_tts_async 완료 - audio_data: {'있음' if audio_data else '없음'}")
            return audio_data
        except Exception as e:
            print(f"TTS 생성 중 오류: {e}")
            return None

    async def _play_audio_async(self, audio_data: str, text: str) -> None:
        """
        🆕 비동기 오디오 재생 (시뮬레이션)
        """
        try:
            # 재생 시간 계산
            estimated_duration = len(text) * 0.06  # 초 단위
            
            print(f"🔊 오디오 재생 시작 (예상 시간: {estimated_duration:.1f}초)")
            
            # 재생 시간만큼 대기 (실제로는 오디오 재생 API 호출)
            await asyncio.sleep(estimated_duration)
            
            print(f"✅ 오디오 재생 완료")
            
        except Exception as e:
            print(f"오디오 재생 중 오류: {e}")

    async def _process_interviewer_task_parallel(self) -> Dict[str, Any]:
        """
        🆕 병렬 처리를 적용한 면접관 태스크 처리
        """
        try:
            # 질문 요청
            question_content = await self._request_question_from_interviewer()
            
            if question_content:
                # 질문 메시지 생성 및 처리
                question_message = self.create_agent_message(
                        session_id=self.session_id,
                        task="question_generated",
                        content_text=question_content,
                        from_agent="interviewer",
                        turn_count=self.session_state.get('turn_count', 0)
                    )
                
                self.handle_message(question_message)
                
                # 🆕 병렬 TTS 처리 - 재생을 기다리지 않고 즉시 다음 작업 준비
                if question_content:
                    asyncio.create_task(self._generate_and_play_tts_parallel(question_content, "면접관"))
                
                return question_message
            else:
                return self.create_agent_message(
                    session_id=self.session_id,
                    task="error",
                    content_text="질문 생성 실패",
                    from_agent="orchestrator",
                    turn_count=self.session_state.get('turn_count', 0)
                )
                
        except Exception as e:
            print(f"면접관 태스크 처리 중 오류: {e}")
            return self.create_agent_message(
                session_id=self.session_id,
                task="error",
                content_text=f"면접관 태스크 오류: {str(e)}",
                from_agent="orchestrator",
                turn_count=self.session_state.get('turn_count', 0)
            )

    async def _process_ai_task_parallel(self, question: str) -> Dict[str, Any]:
        """
        🆕 병렬 처리를 적용한 AI 태스크 처리
        """
        try:
            print(f"[DEBUG] AI 태스크 시작: {question[:50]}...")
            
            # AI 답변 요청
            ai_answer = await self._request_answer_from_ai_candidate(question)
            
            if ai_answer:
                print(f"[DEBUG] AI 답변 생성 완료: {ai_answer[:50]}...")
                
                # AI 답변 메시지 생성 및 처리
                ai_message = self.create_agent_message(
                        session_id=self.session_id,
                        task="answer_generated",
                        content_text=ai_answer,
                        from_agent="ai",
                        turn_count=self.session_state.get('turn_count', 0)
                    )
                
                self.handle_message(ai_message)
                
                # 🆕 병렬 TTS 처리 - 재생을 기다리지 않고 즉시 다음 작업 준비
                if ai_answer:
                    print(f"[DEBUG] AI TTS 태스크 생성 시작")
                    asyncio.create_task(self._generate_and_play_tts_parallel(ai_answer, "AI지원자"))
                    print(f"[DEBUG] AI TTS 태스크 생성 완료")
                else:
                    print(f"[DEBUG] AI 답변이 비어있어 TTS 건너뜀")
                
                return ai_message
            else:
                return self.create_agent_message(
                    session_id=self.session_id,
                    task="error",
                    content_text="AI 답변 생성 실패",
                    from_agent="orchestrator",
                    turn_count=self.session_state.get('turn_count', 0)
                )
                
        except Exception as e:
            print(f"AI 태스크 처리 중 오류: {e}")
            return self.create_agent_message(
                session_id=self.session_id,
                task="error",
                content_text=f"AI 태스크 오류: {str(e)}",
                from_agent="orchestrator",
                turn_count=self.session_state.get('turn_count', 0)
            )

    
