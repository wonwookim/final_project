import json
import openai
import os
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class QuestionType(Enum):
    INTRO = "자기소개"
    MOTIVATION = "지원동기"
    MOTIVE = "동기"
    HR = "인사"
    TECH = "기술"
    COLLABORATION = "협업"
    FOLLOWUP = "심화"
    GENERAL = "일반"
    BASIC = "기본"
    FUTURE = "미래"

@dataclass
class QuestionAnswer:
    question_id: str
    question_type: QuestionType
    question_content: str
    answer_content: str
    timestamp: datetime
    question_intent: str = ""
    individual_score: int = 0
    individual_feedback: str = ""

class InterviewSession:
    def __init__(self, company_id: str, position: str, candidate_name: str):
        self.company_id = company_id
        self.position = position
        self.candidate_name = candidate_name
        self.conversation_history: List[QuestionAnswer] = []
        self.current_question_count = 0
        self.session_id = f"{company_id}_{position.replace(' ', '_')}_{int(time.time())}"
        self.created_at = datetime.now()
        
        # 고정된 질문 순서 (총 20개 질문)
        self.question_plan = [
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
        
    def add_qa_pair(self, qa_pair: QuestionAnswer):
        self.conversation_history.append(qa_pair)
        self.current_question_count += 1
        
    def get_next_question_plan(self) -> Optional[Dict]:
        if self.current_question_count < len(self.question_plan):
            return self.question_plan[self.current_question_count]
        return None
        
    def is_complete(self) -> bool:
        return self.current_question_count >= len(self.question_plan)
        
    def get_conversation_context(self) -> str:
        context = f"면접 진행 상황: {self.current_question_count}/{len(self.question_plan)}\n"
        context += f"지원자: {self.candidate_name}님\n"
        context += f"지원 직군: {self.position}\n\n"
        
        if self.conversation_history:
            context += "이전 대화 내용:\n"
            for i, qa in enumerate(self.conversation_history, 1):
                context += f"{i}. [{qa.question_type.value}] {qa.question_content}\n"
                context += f"   답변: {qa.answer_content}\n\n"
        
        return context

class FinalInterviewSystem:
    def __init__(self, api_key: str = None, companies_data_path: str = "llm/shared/data/companies_data.json"):
        # API 키 자동 로드
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다. .env 파일에 OPENAI_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.companies_data = self._load_companies_data(companies_data_path)
        self.sessions: Dict[str, InterviewSession] = {}
        
    def _load_companies_data(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"기업 데이터 파일을 찾을 수 없습니다: {path}")
            return {"companies": []}
    
    def get_company_data(self, company_id: str) -> Dict[str, Any]:
        for company in self.companies_data["companies"]:
            if company["id"] == company_id:
                return company
        return None
    
    def list_companies(self) -> List[Dict[str, str]]:
        return [{"id": company["id"], "name": company["name"]} 
                for company in self.companies_data["companies"]]
    
    def start_interview(self, company_id: str, position: str, candidate_name: str) -> str:
        company_data = self.get_company_data(company_id)
        if not company_data:
            raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
        
        session = InterviewSession(company_id, position, candidate_name)
        self.sessions[session.session_id] = session
        
        return session.session_id
    
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
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
    
    def submit_answer(self, session_id: str, answer_content: str, current_question_data: Dict[str, str] = None) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "세션을 찾을 수 없습니다"}
        
        print(f"DEBUG: submit_answer 호출 - 세션: {session_id}, 현재 질문 수: {session.current_question_count}, 전체 질문 수: {len(session.question_plan)}")
        
        # 현재 질문 계획 가져오기 (질문을 다시 생성하지 않고)
        current_question_plan = session.get_next_question_plan()
        if not current_question_plan:
            print(f"DEBUG: 현재 질문 계획이 없음 - 면접 완료")
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
        
        # 현재 질문 정보 가져오기 - 실제 질문을 다시 생성하여 저장
        company_data = self.get_company_data(session.company_id)
        question_content, question_intent = self._generate_next_question(
            session, company_data, current_question_plan["type"], current_question_plan.get("fixed", False)
        )
        
        question_id = f"q_{session.current_question_count + 1}"
        question_type = current_question_plan["type"]
        
        # 질문-답변 쌍 생성 (실제 내용으로)
        qa_pair = QuestionAnswer(
            question_id=question_id,
            question_type=question_type,
            question_content=question_content,
            answer_content=answer_content,
            timestamp=datetime.now(),
            question_intent=question_intent
        )
        
        # 세션에 추가 (이 과정에서 current_question_count가 증가)
        session.add_qa_pair(qa_pair)
        
        print(f"DEBUG: 답변 추가 완료 - 새로운 현재 질문 수: {session.current_question_count}")
        
        # 면접 완료 여부 확인
        if session.is_complete():
            print(f"DEBUG: 면접 완료 - {session.current_question_count}/{len(session.question_plan)}")
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
        
        # 다음 질문 생성
        print(f"DEBUG: 다음 질문 생성 시도...")
        next_question = self.get_next_question(session_id)
        if next_question:
            print(f"DEBUG: 다음 질문 생성 성공: {next_question.get('question_content', '')[:50]}...")
            return {
                "status": "next_question",
                "question": next_question,
                "answered_count": session.current_question_count
            }
        else:
            print(f"DEBUG: 다음 질문 생성 실패 - 면접 완료")
            return {
                "status": "interview_complete",
                "message": "면접이 완료되었습니다. 평가를 진행합니다.",
                "total_questions": session.current_question_count
            }
    
    def evaluate_interview(self, session_id: str) -> Dict[str, Any]:
        """면접 전체 평가 (배치 처리로 최적화)"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "세션을 찾을 수 없습니다"}
        
        company_data = self.get_company_data(session.company_id)
        
        # 1. 배치 평가로 모든 답변을 한 번에 평가
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
                # 폴백: 기본 평가
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
                "personalized": False  # 표준 면접 시스템은 개인화되지 않음
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
        
        # 2. 배치 평가에서 종합 평가 추출
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
    
    def _evaluate_single_answer(self, qa: QuestionAnswer, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """개별 답변 평가 (매우 엄격한 기준)"""
        
        answer = qa.answer_content.strip()
        
        # 매우 엄격한 검증
        if len(answer) < 5:
            return {
                "score": 10,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: 답변이 너무 짧습니다. 최소한의 설명도 없습니다.\n\n🔧 개선 방법: 구체적인 경험이나 생각을 3-4문장으로 설명해 주세요."
            }
        
        # 숫자나 단순 답변 검증
        if answer.isdigit() or answer in [".", "없음", "모름", "pass", "1", "2", "3", "4", "5"]:
            return {
                "score": 5,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: 숫자나 단순 답변은 면접에 적절하지 않습니다.\n\n🔧 개선 방법: 질문의 의도를 파악하고 구체적인 경험과 생각을 공유해 주세요."
            }
        
        # 너무 짧은 답변
        if len(answer) < 20:
            return {
                "score": 20,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: 답변이 너무 간단합니다. 더 구체적인 설명이 필요합니다.\n\n🔧 개선 방법: 경험 사례, 구체적인 예시, 본인의 생각을 포함해서 답변해 주세요."
            }
        
        prompt = f"""
다음 면접 질문과 답변을 매우 엄격하게 평가해주세요.

=== 질문 정보 ===
질문 유형: {qa.question_type.value}
질문: {qa.question_content}
질문 의도: {qa.question_intent}

=== 지원자 답변 ===
{answer}

=== 평가 기준 (매우 엄격) ===
- 0점: 답변 거부, 무의미한 답변, 숫자만 입력
- 20-35점: 너무 짧거나 성의없는 답변
- 35-50점: 기본적이지만 표면적이고 구체성 부족
- 50-65점: 적절하지만 평범하고 깊이 부족
- 65-75점: 구체적이고 좋은 답변
- 75-85점: 매우 구체적이고 인상적인 답변
- 85-95점: 탁월하고 깊이 있는 답변
- 95-100점: 완벽하고 감동적인 답변

평가 요소:
1. 질문 의도 이해도 - 답변이 질문의 핵심을 정확히 파악했는가?
2. 구체성 - 실제 경험과 사례가 포함되어 있는가?
3. 깊이 - 표면적이지 않고 깊이 있는 사고가 드러나는가?
4. 논리성 - 답변이 논리적으로 구성되어 있는가?
5. 성찰 - 개인적 학습이나 성장이 포함되어 있는가?

피드백 작성 시:
- 질문 의도를 명확히 설명
- 답변의 좋은 점과 부족한 점을 구체적으로 지적
- 개선 방법을 실질적으로 제안

JSON 형식으로 응답:
{{
  "score": 점수,
  "feedback": "📝 질문 의도: {qa.question_intent}\\n\\n💬 평가: 구체적인 평가 내용 (좋은 점, 부족한 점 포함)\\n\\n🔧 개선 방법: 실질적이고 구체적인 개선 제안"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 매우 엄격한 면접 평가자입니다. 높은 기준으로 정확하게 평가하고, 구체적이고 건설적인 피드백을 제공하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                evaluation = json.loads(json_str)
                
                # 점수가 너무 높으면 강제로 조정
                if evaluation["score"] > 80 and len(answer) < 100:
                    evaluation["score"] = min(evaluation["score"], 60)
                
                return evaluation
            else:
                raise ValueError("JSON 형식을 찾을 수 없습니다")
                
        except Exception as e:
            print(f"개별 평가 중 오류: {str(e)}")
            # 기본 엄격한 평가
            if len(answer) < 30:
                score = 25
            elif len(answer) < 100:
                score = 45
            else:
                score = 55
            
            return {
                "score": score,
                "feedback": f"📝 질문 의도: {qa.question_intent}\n\n💬 평가: 시스템 오류로 기본 평가를 적용했습니다.\n\n🔧 개선 방법: 더 구체적이고 상세한 답변을 제공해 주세요."
            }
    
    def _generate_overall_evaluation(self, session: InterviewSession, company_data: Dict[str, Any], overall_score: int) -> Dict[str, Any]:
        """종합 평가 생성"""
        
        conversation_summary = ""
        for qa in session.conversation_history:
            conversation_summary += f"[{qa.question_type.value}] {qa.question_content}\n답변: {qa.answer_content}\n개별 점수: {qa.individual_score}점\n\n"
        
        prompt = f"""
{company_data['name']} {session.position} 면접 종합 평가를 수행해주세요.

=== 지원자 정보 ===
- 이름: {session.candidate_name}님
- 지원 직군: {session.position}
- 전체 평균 점수: {overall_score}점

=== 면접 내용 ===
{conversation_summary}

=== 기업 요구사항 ===
- 인재상: {company_data['talent_profile']}
- 핵심 역량: {', '.join(company_data['core_competencies'])}

다음 형식으로 JSON 응답:
{{
  "strengths": ["구체적인 강점1", "구체적인 강점2", "구체적인 강점3"],
  "improvements": ["구체적인 개선점1", "구체적인 개선점2", "구체적인 개선점3"],
  "recommendation": "채용 추천 여부와 구체적인 이유",
  "next_steps": "다음 단계 제안",
  "overall_assessment": "전체적인 평가 요약"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"{company_data['name']} 면접 평가 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            
        except Exception as e:
            print(f"종합 평가 중 오류: {str(e)}")
        
        # 점수에 따른 기본 평가
        if overall_score >= 70:
            recommendation = "다음 단계 진행 고려"
            next_steps = "실무진 면접 진행"
        elif overall_score >= 50:
            recommendation = "보완 후 재검토"
            next_steps = "경험 보완 후 재지원"
        else:
            recommendation = "현재 기준 미달"
            next_steps = "충분한 준비 후 재지원"
        
        return {
            "strengths": ["면접 참여", "기본 소통", "성실함"],
            "improvements": ["구체적 사례 제시", "답변 깊이", "전문성 향상"],
            "recommendation": recommendation,
            "next_steps": next_steps,
            "overall_assessment": f"전체 {overall_score}점 수준의 면접 결과입니다."
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
        
        # 배치 평가 프롬프트 (간소화)
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

if __name__ == "__main__":
    print("🎯 최종 면접 시스템")
    print("=" * 50)
    
    # 자동으로 .env에서 API 키 로드
    system = FinalInterviewSystem()
    
    companies = system.list_companies()
    print("\n📋 선택 가능한 회사:")
    for i, company in enumerate(companies, 1):
        print(f"{i}. {company['name']}")
    
    while True:
        try:
            choice = int(input("\n회사를 선택하세요 (번호): ")) - 1
            if 0 <= choice < len(companies):
                selected_company = companies[choice]
                break
            else:
                print("올바른 번호를 입력하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    position = input("직군을 입력하세요: ")
    candidate_name = input("이름을 입력하세요: ")
    
    print(f"\n🚀 {selected_company['name']} {position} 면접을 시작합니다!")
    print(f"👋 {candidate_name}님, 환영합니다.")
    
    try:
        session_id = system.start_interview(selected_company['id'], position, candidate_name)
        
        current_question = system.get_next_question(session_id)
        
        while current_question:
            print(f"\n{'='*70}")
            print(f"📝 [{current_question['question_type']}] 질문 {current_question['progress']}")
            print(f"🎯 질문 의도: {current_question['question_intent']}")
            print("-" * 70)
            print(f"❓ {current_question['question_content']}")
            print("="*70)
            
            answer = input("\n💬 답변을 입력하세요: ")
            
            result = system.submit_answer(session_id, answer)
            
            if result['status'] == 'interview_complete':
                print(f"\n✅ {result['message']}")
                break
            elif result['status'] == 'next_question':
                current_question = result['question']
            else:
                print("❌ 오류가 발생했습니다.")
                break
        
        print("\n🔄 최종 평가를 진행합니다...")
        evaluation = system.evaluate_interview(session_id)
        
        print(f"\n{'='*70}")
        print(f"📊 {evaluation['company']} 면접 결과")
        print("="*70)
        
        eval_data = evaluation['evaluation']
        print(f"🎯 전체 점수: {eval_data['overall_score']}/100")
        
        print("\n📈 카테고리별 점수:")
        for category, score in eval_data['category_scores'].items():
            print(f"  • {category}: {score}/100")
        
        print("\n📝 개별 답변 평가:")
        for feedback in evaluation['individual_feedbacks']:
            print(f"\n{feedback['question_number']}. [{feedback['question_type']}] 점수: {feedback['score']}/100")
            print(f"   질문: {feedback['question']}")
            print(f"   답변: {feedback['answer']}")
            print(f"   평가: {feedback['feedback']}")
        
        print(f"\n💪 주요 강점:")
        for strength in eval_data['strengths']:
            print(f"  ✅ {strength}")
        
        print(f"\n🔧 개선 필요 사항:")
        for improvement in eval_data['improvements']:
            print(f"  🔨 {improvement}")
        
        print(f"\n🎯 최종 추천: {eval_data['recommendation']}")
        print(f"🚀 다음 단계: {eval_data['next_steps']}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")