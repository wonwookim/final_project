import time
import json
import random
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

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
        print(f"[{from_agent}] -> [Orchestrator]")
        print(json.dumps(message, indent=2, ensure_ascii=False))

        task = message.get("metadata", {}).get("task")
        content = message.get("content", {}).get("content")

        # 상태 업데이트
        self._update_state_from_message(task, content, from_agent)

        # 다음 메시지 결정
        next_message = self._decide_next_message()
        next_agent = next_message.get("metadata", {}).get("next_agent", "unknown")
        print(f"[Orchestrator] -> [{next_agent}]")
        print(json.dumps(next_message, indent=2, ensure_ascii=False))
        return next_message

    def _update_state_from_message(self, task: str, content: str, from_agent: str) -> None:
        """메시지로부터 세션 상태 업데이트"""
        if task == "intro_generated":
            # 인트로 메시지 생성 완료 - 답변 없이 바로 턴 증가
            self.session_state['turn_count'] += 1  # 턴 0 완료, 턴 1로 이동
            # current_question은 설정하지 않음 (답변 요청하지 않음)
            
        elif task == "question_generated":
            self.session_state['current_question'] = content
            
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
            self.session_state['qa_history'].append({
                "question": question_text,
                "answerer": from_agent,
                "answer": content
            })
            
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
            self.session_state['qa_history'].append({
                "question": self.session_state['current_question'],
                "answerer": from_agent,
                "answer": content
            })

            # 두 답변이 모두 완료되면 턴 증가 및 꼬리 질문 상태 업데이트
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
        
        # 완료 조건 체크
        if current_turn >= self.session_state.get('total_question_limit', 15):
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
        
        # 현재 메인 질문에 대한 답변 수 확인
        current_answers = len([qa for qa in self.session_state['qa_history'] 
                             if qa['question'] == self.session_state['current_question']])
        
        # 첫 번째 답변: 랜덤 선택
        if current_answers == 0:
            selected_agent = 'user' if self._random_select() == -1 else 'ai'
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=self.session_state['current_question'],
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
            message = self.create_agent_message(
                session_id=self.session_id,
                task="generate_answer",
                from_agent="orchestrator",
                content_text=self.session_state['current_question'],
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
        print(f"[Orchestrator] 🔄 사용자 답변 처리 시작: {self.session_id}")
        
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
        print(f"[Orchestrator] �� _process_complete_flow 시작: {self.session_id}")
        
        while True:
            print(f"[Orchestrator] 🔄 while 루프 시작 - turn_count: {self.session_state.get('turn_count', 0)}")
            
            # 다음 메시지 결정
            next_message = self._decide_next_message()
            next_agent = next_message.get("metadata", {}).get("next_agent")
            task = next_message.get("metadata", {}).get("task")
            
            print(f"[Orchestrator] 🔄 다음 액션 결정: {next_agent} - {task}")
            
            # 완료 조건 체크
            if task == "end_interview":
                print(f"[Orchestrator] ✅ 면접 완료")
                result = {
                    "status": "completed",
                    "message": "수고하셨습니다.",
                    "qa_history": self.session_state.get('qa_history', []),
                    "session_id": self.session_id
                }
                print(f"[Orchestrator] -> [Client]")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # 사용자 입력 대기 상태인 경우
            if next_agent == "user":
                print(f"[Orchestrator] 👤 사용자 입력 대기")
                result = self.create_user_waiting_message()
                print(f"[Orchestrator] -> [Client]")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # 에이전트 작업 수행 (handle_message에서 JSON 출력됨)
            if next_agent == "interviewer":
                print(f"[Orchestrator] 🎤 면접관 작업 시작")
                await self._process_interviewer_task()
            elif next_agent == "interviewer_individual":
                print(f"[Orchestrator] 🎤🎤 면접관 개별 꼬리질문 작업 시작")
                await self._process_individual_interviewer_task()
            elif next_agent == "ai":
                print(f"[Orchestrator] 🤖 AI 지원자 작업 시작")
                await self._process_ai_task(next_message.get("content", {}).get("content"))
            
            print(f"[Orchestrator] 🔄 while 루프 끝")
    
    async def _process_interviewer_task(self):
        """면접관 작업 처리"""
        print(f"[Orchestrator] -> [Interviewer] (질문 생성 요청)")
        
        # 🆕 현재 상태 디버깅 (개선)
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[DEBUG] 턴 {current_turn}: 현재 면접관 = {current_interviewer}")
        for role, state in turn_state.items():
            main_done = "✓" if state['main_question_asked'] else "✗"
            follow_count = state['follow_up_count']
            print(f"[DEBUG]   {role}: 메인 {main_done}, 꼬리 {follow_count}개")
        
        question_result = await self._request_question_from_interviewer()
        
        # 🆕 반환값 타입에 따른 처리
        if isinstance(question_result, dict) and 'user_question' in question_result and 'ai_question' in question_result:
            print(f"[DEBUG] 개별 질문 데이터 처리 시작")
            
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
            
            # handle_message에서 JSON 출력됨
            self.handle_message(questions_message)
            
        else:
            # 일반 질문 처리 (기존 로직)
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
            
            # handle_message에서 JSON 출력됨
            self.handle_message(question_message)
    
    async def _process_individual_interviewer_task(self):
        """개별 꼬리질문 생성 작업 처리"""
        print(f"[Orchestrator] -> [Interviewer] (개별 꼬리질문 생성 요청)")
        
        # 현재 상태 디버깅
        current_interviewer = self.session_state.get('current_interviewer')
        turn_state = self.session_state.get('interviewer_turn_state', {})
        current_turn = self.session_state.get('turn_count', 0)
        
        print(f"[DEBUG] 개별 꼬리질문 생성 - 턴 {current_turn}, 면접관: {current_interviewer}")
        
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
            
            # handle_message에서 JSON 출력됨
            self.handle_message(questions_message)
            
        except Exception as e:
            print(f"[ERROR] 개별 꼬리질문 생성 실패: {e}")
            # 폴백: 일반 질문으로 대체
            await self._process_interviewer_task()
    
    async def _process_ai_task(self, question: str):
        """AI 지원자 작업 처리"""
        print(f"[Orchestrator] -> [AI Candidate] (질문: {question[:50]}...)")
        
        # 예전 로직으로 복원: 원본 질문 그대로 사용
        ai_answer = await self._request_answer_from_ai_candidate(question)
        
        # 🆕 개별 질문 상태 체크
        current_questions = self.session_state.get('current_questions')
        is_individual_question = current_questions and current_questions.get('is_individual', False)
        
        # 🆕 content_type 결정 (현재 면접관 기반)
        current_interviewer = self.session_state.get('current_interviewer', 'HR')
        content_type = current_interviewer if current_interviewer in ['HR', 'TECH', 'COLLABORATION'] else 'HR'
        
        # 개별 질문 여부에 따라 task 결정
        task = "individual_answer_generated" if is_individual_question else "answer_generated"
        
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
    
    def create_user_waiting_message(self) -> Dict[str, Any]:
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
        
        # 🆕 턴 정보 추가 (개별 질문 정보 포함)
        response['turn_info'] = {
            'current_turn': self.session_state.get('turn_count', 0),
            'is_user_turn': True,
            'is_individual_question': is_individual_question,
            'question_type': 'individual_follow_up' if is_individual_question else 'main_question'
        }
        
        return response

    
