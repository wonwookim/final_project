#!/usr/bin/env python3
"""
지능형 턴제 면접관 패널 시스템

핵심 특징:
- 3명의 면접관(HR, TECH, COLLABORATION)이 턴제로 질문 진행
- 각 면접관은 메인 질문 1개 + 동적 꼬리 질문 1~2개로 주제 심층 탐구
- 15개 주제 풀에서 다양한 메인 질문 선택
- 지원자 답변을 실시간 분석하여 맞춤형 꼬리 질문 생성
- DB 기반 참조질문과 LLM 기반 생성질문의 전략적 혼합
"""

import json
import random
import os
import sys
from typing import Dict, List, Any, Optional
import openai
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.supabase_client import get_supabase_client
from llm.shared.constants import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from llm.candidate.model import CandidatePersona

class InterviewerService:
    """지능형 턴제 기반 면접관 패널 시스템"""
    
    def __init__(self, total_question_limit: int = 15):
        # Supabase 클라이언트 초기화
        self.client = get_supabase_client()
        
        # OpenAI 클라이언트 초기화
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        self.openai_client = openai.OpenAI(api_key=api_key)
        
        # DB 데이터 로딩 및 캐싱
        self.companies_data = self._load_companies_data()
        self.fixed_questions = self._load_fixed_questions()
        
        # 면접관 역할 정의
        self.interviewer_roles = ['HR', 'TECH', 'COLLABORATION']
        self.question_type_mapping = {
            'HR': 1,
            'TECH': 2, 
            'COLLABORATION': 3
        }
        
        # 턴제 시스템 관리 변수
        self.total_question_limit = total_question_limit
        self.questions_asked_count = 0
        self.current_interviewer_index = 0
        self.interviewer_turn_state = {
            'HR': {'main_question_asked': False, 'follow_up_count': 0},
            'TECH': {'main_question_asked': False, 'follow_up_count': 0}, 
            'COLLABORATION': {'main_question_asked': False, 'follow_up_count': 0}
        }
        
        # 면접관별 주제 풀 정의
        self.topic_pools = {
            'HR': ['인성_가치관', '성장_동기', '갈등_해결', '스트레스_관리', '팀워크_리더십'],
            'TECH': ['기술_역량', '문제_해결', '성능_최적화', '코드_품질', '새로운_기술_학습'],
            'COLLABORATION': ['소통_능력', '프로젝트_협업', '의견_조율', '크로스_팀_협업', '조직_문화_적응']
        }
    
    def _load_companies_data(self) -> Dict[str, Any]:
        """회사 데이터 로딩 및 캐싱 (CompanyDataLoader와 동일한 매핑 방식 사용)"""
        try:
            result = self.client.table('company').select('*').execute()
            companies_dict = {}
            
            # CompanyDataLoader와 동일한 매핑 테이블 사용
            company_id_mapping = {
                '네이버': 'naver',
                '카카오': 'kakao', 
                '라인': 'line',
                '라인플러스': '라인플러스',  # Supabase DB 호환성
                '쿠팡': 'coupang',
                '배달의민족': 'baemin',
                '당근마켓': 'daangn',
                '토스': 'toss'
            }
            
            if result.data:
                for company in result.data:
                    # 한글 이름을 영문 ID로 매핑
                    company_name = company.get('name', '')
                    english_id = company_id_mapping.get(company_name, company_name.lower())
                    companies_dict[english_id] = company
                    
            print(f"✅ 회사 데이터 로딩 완료: {len(companies_dict)}개, 키: {list(companies_dict.keys())}")
            return companies_dict
        except Exception as e:
            print(f"❌ 회사 데이터 로딩 실패: {e}")
            return {}
    
    def _load_fixed_questions(self) -> List[Dict[str, Any]]:
        """고정 질문 데이터 로딩 및 캐싱"""
        try:
            result = self.client.table('fix_question').select('*').execute()
            questions = result.data if result.data else []
            print(f"✅ 고정 질문 데이터 로딩 완료: {len(questions)}개")
            return questions
        except Exception as e:
            print(f"❌ 고정 질문 데이터 로딩 실패: {e}")
            return []
    
    def generate_next_question(self, user_resume: Dict, chun_sik_persona: CandidatePersona, 
                              company_id: str, previous_qa_pairs: List[Dict] = None,
                              user_answer: str = None, chun_sik_answer: str = None) -> Dict:
        """턴제 기반 면접 컨트롤 타워 - 질문 수 한도 관리 및 면접관 턴 제어"""
        
        print(f"🎯 [InterviewerService] generate_next_question 호출: questions_asked_count={self.questions_asked_count}, total_limit={self.total_question_limit}")
        
        # 질문 수 한도 확인
        if self.questions_asked_count >= self.total_question_limit:
            print(f"🏁 [InterviewerService] 질문 한도 도달, 면접 종료: {self.questions_asked_count}/{self.total_question_limit}")
            return {
                'question': '면접이 종료되었습니다. 수고하셨습니다.',
                'intent': '면접 종료',
                'interviewer_type': 'SYSTEM',
                'is_final': True
            }
        
        # 첫 2개 질문은 고정 (기존 로직 유지)
        if self.questions_asked_count == 0:
            self.questions_asked_count += 1
            print(f"📝 [InterviewerService] 1번째 질문 생성: 자기소개")
            # 자기소개는 이름을 모르는 상황이므로 이름 호명 없이 진행
            return {
                'question': '자기소개를 부탁드립니다.',
                'intent': '지원자의 기본 정보와 성격, 역량을 파악',
                'interviewer_type': 'HR'
            }
        
        elif self.questions_asked_count == 1:
            company_info = self.companies_data.get(company_id, {})
            company_name = company_info.get('name', '저희 회사')
            self.questions_asked_count += 1
            print(f"📝 [InterviewerService] 2번째 질문 생성: 지원동기 ({company_name})")
            
            # 지원동기 질문에 이름 호명 추가 (자기소개 후이므로 이름을 알고 있음)
            base_question = f'저희 {company_name}에 지원하신 동기를 말씀해 주세요.'
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            question_with_name = self._add_candidate_name_to_question(base_question, candidate_name)
            
            return {
                'question': question_with_name,
                'intent': '회사에 대한 관심도와 지원 동기 파악',
                'interviewer_type': 'HR'
            }
        
        # 턴제 시스템 시작 (question_index >= 2)
        else:
            print(f"🎭 [InterviewerService] {self.questions_asked_count + 1}번째 질문 생성 (턴제 시스템)")
            company_info = self.companies_data.get(company_id, {})
            if not company_info:
                raise ValueError(f"회사 정보를 찾을 수 없습니다: {company_id}")
            
            # 현재 면접관 결정
            current_interviewer = self._get_current_interviewer()
            print(f"👔 [InterviewerService] 현재 면접관: {current_interviewer}")
            
            # 면접관의 턴 수행
            question_result = self._conduct_interview_turn(
                user_resume, chun_sik_persona, company_info, current_interviewer,
                user_answer, chun_sik_answer, previous_qa_pairs
            )
            
            # 질문 수 증가
            self.questions_asked_count += 1
            print(f"📈 [InterviewerService] 질문 수 증가: {self.questions_asked_count}/{self.total_question_limit}")
            
            # 면접관 턴 상태 업데이트
            self._update_turn_state(current_interviewer, question_result)
            
            return question_result
    
    def _get_current_interviewer(self) -> str:
        """현재 턴을 진행할 면접관 결정"""
        return self.interviewer_roles[self.current_interviewer_index]
    
    def _update_turn_state(self, interviewer_role: str, question_result: Dict):
        """면접관 턴 상태 업데이트 및 다음 면접관으로 전환 여부 결정"""
        turn_state = self.interviewer_turn_state[interviewer_role]
        
        # 강제 턴 전환인 경우 (빈 질문) 상태 업데이트 없이 바로 전환
        if question_result.get('force_turn_switch', False):
            self._switch_to_next_interviewer()
            return
        
        # 메인 질문이었는지 꼬리 질문이었는지 확인
        if question_result.get('question_type') == 'follow_up':
            turn_state['follow_up_count'] += 1
        else:
            # 메인 질문인 경우
            turn_state['main_question_asked'] = True
        
        # 턴 전환 조건 확인 (메인 질문 + 최대 2개 꼬리 질문 또는 남은 질문 수 부족)
        remaining_questions = self.total_question_limit - self.questions_asked_count
        should_switch_turn = (
            turn_state['follow_up_count'] >= 2 or  # 최대 꼬리 질문 수 도달
            remaining_questions <= 3  # 남은 질문이 적어 다른 면접관에게 기회 제공
        )
        
        if should_switch_turn:
            self._switch_to_next_interviewer()
    
    def _switch_to_next_interviewer(self):
        """다음 면접관으로 턴 전환"""
        # 현재 면접관의 턴 상태 초기화
        current_interviewer = self.interviewer_roles[self.current_interviewer_index]
        self.interviewer_turn_state[current_interviewer] = {
            'main_question_asked': False, 
            'follow_up_count': 0
        }
        
        # 다음 면접관으로 전환
        self.current_interviewer_index = (self.current_interviewer_index + 1) % 3
    
    def _conduct_interview_turn(self, user_resume: Dict, chun_sik_persona: CandidatePersona,
                               company_info: Dict, interviewer_role: str, 
                               user_answer: str = None, chun_sik_answer: str = None,
                               previous_qa_pairs: List[Dict] = None) -> Dict:
        """면접관의 턴 수행 - 메인 질문 또는 꼬리 질문 생성"""
        
        turn_state = self.interviewer_turn_state[interviewer_role]
        remaining_budget = self.total_question_limit - self.questions_asked_count
        
        # 메인 질문이 아직 안 나왔다면 메인 질문 생성
        if not turn_state['main_question_asked']:
            return self._generate_main_question(
                user_resume, chun_sik_persona, company_info, interviewer_role
            )
        
        # 메인 질문이 나왔다면 꼬리 질문 생성 조건 확인
        else:
            # 꼬리 질문 생성 조건 체크
            should_generate_follow_up = self._should_generate_follow_up_question(
                turn_state, remaining_budget, user_answer, chun_sik_answer
            )
            
            if should_generate_follow_up and user_answer and chun_sik_answer:
                # 이전 질문 정보 가져오기
                previous_question = self._get_last_question_from_history(previous_qa_pairs)
                
                return self._generate_follow_up_question(
                    previous_question, user_answer, chun_sik_answer, 
                    company_info, interviewer_role, user_resume
                )
            else:
                # 꼬리 질문을 생성하지 않고 턴 종료, 다음 면접관으로 넘김
                return {
                    'question': '',
                    'intent': '',
                    'interviewer_type': interviewer_role,
                    'force_turn_switch': True
                }
    
    def _should_generate_follow_up_question(self, turn_state: Dict, remaining_budget: int,
                                          user_answer: str, chun_sik_answer: str) -> bool:
        """꼬리 질문 생성 여부 결정"""
        
        # 기본 조건 체크
        if turn_state['follow_up_count'] >= 2:  # 최대 꼬리 질문 수 도달
            return False
        
        if remaining_budget <= 3:  # 남은 질문 수가 적어 다른 면접관에게 기회 제공
            return False
        
        if not user_answer or not chun_sik_answer:  # 이전 답변이 없으면 꼬리 질문 불가
            return False
        
        # 동적 결정 (답변 길이 기반)
        answer_quality_score = len(user_answer.split()) + len(chun_sik_answer.split())
        
        # 답변이 충분히 길거나 내용이 있으면 꼬리 질문 생성
        return answer_quality_score >= 20
    
    def _get_last_question_from_history(self, previous_qa_pairs: List[Dict]) -> str:
        """이전 질문 기록에서 마지막 질문 추출"""
        if not previous_qa_pairs:
            return "이전 질문 정보를 찾을 수 없습니다."
        
        last_qa = previous_qa_pairs[-1] if previous_qa_pairs else {}
        return last_qa.get('question', '이전 질문 정보를 찾을 수 없습니다.')
    
    def _generate_main_question(self, user_resume: Dict, chun_sik_persona: CandidatePersona,
                               company_info: Dict, interviewer_role: str) -> Dict:
        """메인 질문 생성 - 다양한 주제 풀에서 선택하여 참조/생성 혼합 (폴백 방지)"""
        
        # 면접관 역할에 맞는 주제 목록 선택
        topic_pool = self.topic_pools.get(interviewer_role, [])
        if not topic_pool:
            print(f"⚠️ [InterviewerService] {interviewer_role} 주제 풀이 비어있음. 일반 주제로 시도")
            topic_pool = ['일반']
        
        # 랜덤하게 주제 선택
        selected_topic = random.choice(topic_pool)
        
        # 50% 확률로 DB 템플릿 또는 LLM 생성 방식 선택
        use_db_first = random.choice([True, False])
        
        question_result = None
        
        if use_db_first:
            print(f"🎯 [InterviewerService] DB 템플릿 우선 시도: {selected_topic}")
            # 1차: DB 템플릿 기반 생성 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            print(f"❌ [InterviewerService] DB 템플릿 실패. LLM 생성으로 전환")
            # 2차: DB 실패 시 LLM 생성 시도 
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
                
        else:
            print(f"🤖 [InterviewerService] LLM 생성 우선 시도: {selected_topic}")
            # 1차: LLM 기반 생성 시도
            question_result = self._try_generate_from_llm(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
            
            print(f"❌ [InterviewerService] LLM 생성 실패. DB 템플릿으로 전환")
            # 2차: LLM 실패 시 DB 템플릿 시도
            question_result = self._try_generate_from_db_template(
                user_resume, company_info, interviewer_role, selected_topic
            )
            
            if question_result:
                return question_result
        
        # 최종 폴백: 둘 다 실패 시 일반적인 질문 (장점/단점 아님)
        print(f"🚨 [InterviewerService] 모든 질문 생성 실패. 일반 질문으로 폴백")
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        return self._get_generic_question(interviewer_role, selected_topic, candidate_name)
    
    def _try_generate_from_db_template(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Optional[Dict]:
        """DB 템플릿 기반 질문 생성 시도 (실패 시 None 반환)"""
        try:
            return self._generate_from_db_template_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"❌ [InterviewerService] DB 템플릿 생성 중 예외: {e}")
            return None
    
    def _try_generate_from_llm(self, user_resume: Dict, company_info: Dict, 
                             interviewer_role: str, topic: str) -> Optional[Dict]:
        """LLM 기반 질문 생성 시도 (실패 시 None 반환)"""
        try:
            return self._generate_from_llm_with_topic(
                user_resume, company_info, interviewer_role, topic
            )
        except Exception as e:
            print(f"❌ [InterviewerService] LLM 생성 중 예외: {e}")
            return None
    
    def _get_generic_question(self, interviewer_role: str, topic: str, candidate_name: str = None) -> Dict:
        """최종 폴백: 일반적인 질문 (장점/단점 아님)"""
        generic_questions = {
            'HR': {
                'question': f'{topic} 관련해서 본인의 경험을 자유롭게 말씀해 주세요.',
                'intent': '지원자의 경험과 역량 파악'
            },
            'TECH': {
                'question': f'{topic} 분야에서 본인이 해결한 문제나 경험을 설명해 주세요.',
                'intent': '기술적 문제 해결 능력 평가'
            },
            'COLLABORATION': {
                'question': f'{topic}과 관련된 팀 협업 경험을 말씀해 주세요.',
                'intent': '협업 능력과 소통 역량 평가'
            }
        }
        
        fallback = generic_questions.get(interviewer_role, generic_questions['HR'])
        
        # 이름 호명 추가
        question_with_name = self._add_candidate_name_to_question(
            fallback['question'], candidate_name
        )
        
        return {
            'question': question_with_name,
            'intent': fallback['intent'],
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'generic_fallback'
        }
    
    def _generate_from_db_template_with_topic(self, user_resume: Dict, company_info: Dict, 
                                            interviewer_role: str, topic: str) -> Dict:
        """주제 특화 DB 템플릿 기반 질문 생성"""
        
        # 면접관 역할에 해당하는 question_type ID 가져오기
        question_type_id = self.question_type_mapping.get(interviewer_role, 1)
        
        # 해당 타입의 질문 템플릿 필터링
        filtered_questions = [
            q for q in self.fixed_questions 
            if q.get('question_type') == question_type_id
        ]
        
        if not filtered_questions:
            raise ValueError(f"DB에 {interviewer_role} 역할(question_type={question_type_id})의 질문이 없습니다.")
        
        # 랜덤 템플릿 선택
        selected_template = random.choice(filtered_questions)
        
        # 템플릿에 데이터 주입
        question_content = self._inject_data_to_template(
            selected_template.get('question_content', ''),
            user_resume, 
            company_info
        )
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        question_with_name = self._add_candidate_name_to_question(question_content, candidate_name)
        
        return {
            'question': question_with_name,
            'intent': f"{topic} 관련 {selected_template.get('question_intent', f'{interviewer_role} 역량 평가')}",
            'interviewer_type': interviewer_role,
            'topic': topic,
            'question_source': 'db_template'
        }
    
    def _generate_from_llm_with_topic(self, user_resume: Dict, company_info: Dict, 
                                     interviewer_role: str, topic: str) -> Dict:
        """주제 특화 LLM 기반 질문 생성"""
        
        # 주제별 프롬프트 빌더 호출
        prompt = self._build_topic_specific_prompt(
            user_resume, company_info, interviewer_role, topic
        )
        
        # LLM 호출
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": """당신은 전문 면접관입니다. 

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "프로젝트에서 가장 어려웠던 기술적 도전은 무엇이었나요?", "intent": "문제 해결 능력과 기술적 역량 평가"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            # JSON 파싱
            result_text = response.choices[0].message.content.strip()
            
            if not result_text:
                raise ValueError("LLM이 빈 응답을 반환했습니다")
            
            result = json.loads(result_text)
            
            # 결과 검증 및 보정
            if not result.get('question'):
                raise ValueError("question 필드가 비어있습니다")
            
            # 이름 호명 추가
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            result['question'] = self._add_candidate_name_to_question(result['question'], candidate_name)
            
            result['interviewer_type'] = interviewer_role
            result['topic'] = topic
            result['question_source'] = 'llm_generated'
            return result
            
        except Exception as e:
            print(f"❌ LLM 메인 질문 생성 실패: {e}")
            raise  # 예외를 다시 발생시켜 상위 함수에서 처리하도록 함
    
    def _build_topic_specific_prompt(self, user_resume: Dict, company_info: Dict, 
                                   interviewer_role: str, topic: str) -> str:
        """전사적 DNA 매트릭스 프롬프트 빌더 - 회사의 모든 특성과 직무 전문성을 융합한 맞춤형 질문 생성"""
        
        # 1. [회사 DNA] 정보 체계적 추출
        company_name = company_info.get('name', '회사')
        talent_profile = company_info.get('talent_profile', '정의되지 않음')
        core_competencies = ', '.join(company_info.get('core_competencies', ['정의되지 않음']))
        tech_focus = ', '.join(company_info.get('tech_focus', ['정의되지 않음']))
        question_direction = company_info.get('question_direction', '정의되지 않음')
        
        # 기업문화 정보 추출
        company_culture = company_info.get('company_culture', {})
        core_values = []
        work_style = ''
        if isinstance(company_culture, dict):
            core_values = company_culture.get('core_values', [])
            work_style = company_culture.get('work_style', '')
        
        # 2. [지원자 직무 컨텍스트] 정의
        position = user_resume.get('position', '개발자')
        position_contexts = {
            "백엔드": "대용량 트래픽 처리, 데이터베이스 설계, MSA 아키텍처, API 성능 최적화, 시스템 안정성, 분산 트랜잭션",
            "프론트엔드": "웹 성능 최적화(로딩 속도), 상태 관리, UI/UX 개선, 크로스 브라우징, 웹 접근성, Critical Rendering Path",
            "AI": "모델 성능 및 정확도, 데이터 전처리, 과적합 방지, 최신 논문 구현, MLOps, Transformer 아키텍처",
            "데이터사이언스": "A/B 테스트 설계, 통계적 가설 검증, Feature Engineering, 데이터 시각화, 예측 모델링, 불균형 데이터 처리",
            "기획": "사용자 요구사항 분석, 제품 로드맵 설정, KPI 정의, 시장 조사, 기능 우선순위 결정, RICE/ICE 프레임워크"
        }
        
        # 직군 매칭 (부분 문자열 포함 검사)
        position_context = "소프트웨어 개발 일반"
        for key, context in position_contexts.items():
            if key in position or key.lower() in position.lower():
                position_context = context
                break
        
        # 주제별 기본 가이드라인
        topic_guidelines = {
            '인성_가치관': '지원자의 핵심 가치관과 인생 철학을 파악할 수 있는 질문',
            '성장_동기': '학습 의지와 자기계발에 대한 태도를 확인하는 질문',
            '갈등_해결': '대인관계나 업무상 갈등 상황에서의 해결 능력을 평가하는 질문',
            '스트레스_관리': '압박 상황에서의 대처 능력과 회복력을 측정하는 질문',
            '팀워크_리더십': '팀 내에서의 역할과 리더십 역량을 확인하는 질문',
            '기술_역량': '전문 기술 지식과 실무 적용 능력을 검증하는 질문',
            '문제_해결': '복잡한 기술적 문제에 대한 접근 방식과 해결 과정을 평가하는 질문',
            '성능_최적화': '시스템 성능 개선과 최적화 경험을 확인하는 질문',
            '코드_품질': '코드 리뷰, 테스트, 문서화 등 품질 관리 능력을 평가하는 질문',
            '새로운_기술_학습': '기술 트렌드 파악과 새로운 기술 습득 능력을 확인하는 질문',
            '소통_능력': '의사소통과 정보 전달 능력을 평가하는 질문',
            '프로젝트_협업': '다양한 역할의 팀원들과의 협업 경험을 확인하는 질문',
            '의견_조율': '서로 다른 의견을 조율하고 합의점을 찾는 능력을 평가하는 질문',
            '크로스_팀_협업': '부서간 협업과 이해관계자 관리 능력을 확인하는 질문',
            '조직_문화_적응': '새로운 환경에 대한 적응력과 조직 문화 이해도를 평가하는 질문'
        }
        
        # 3. 안전장치: 필수 DNA 정보 부족 시 기존 방식 사용
        critical_dna_missing = (
            talent_profile == '정의되지 않음' and 
            core_competencies == '정의되지 않음' and 
            tech_focus == '정의되지 않음' and 
            question_direction == '정의되지 않음'
        )
        
        if critical_dna_missing:
            # 기존 프롬프트 구조로 폴백
            guideline = topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')
            return f"""
당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

면접 직군: {position}
면접 주제: {topic}
질문 가이드라인: {guideline}

위 주제에 대해 두 지원자를 동시에 평가할 수 있는 메인 질문을 하나만 생성해주세요.

응답 형식:
{{"question": "질문 내용", "intent": "질문 의도"}}
"""
        
        # 4. [전사적 DNA 매트릭스 프롬프트] 구성
        prompt = f"""
### 당신의 미션 ###
당신은 '{company_name}'의 채용 철학을 완벽하게 이해한 최고 수준의 {interviewer_role} 면접관입니다.
아래에 주어진 [회사 DNA]와 [지원자 컨텍스트]를 '모두' 유기적으로 결합하여, 지원자의 역량을 다각도로 검증할 수 있는 매우 날카롭고 구체적인 질문을 '단 하나만' 생성하세요.

### [회사 DNA 분석] ###
- **인재상 (WHO):** 우리는 '{talent_profile}'인 사람을 원합니다.
- **핵심 역량 (WHAT):** 우리는 '{core_competencies}' 역량을 중요하게 생각합니다.
- **기술 중점 분야 (WHERE):** 우리의 기술은 '{tech_focus}' 분야에 집중되어 있습니다.
- **평가 방향 (HOW):** 우리는 '{question_direction}' 방식으로 지원자를 평가합니다.
{f"- **핵심가치:** {', '.join(core_values[:3])}" if core_values else ""}
{f"- **업무문화:** {work_style}" if work_style else ""}

### [지원자 컨텍스트] ###
- **직군:** {position}
- **주요 업무 영역:** {position_context}
- **면접 주제:** {topic_guidelines.get(topic, f'{topic} 관련 전문성을 평가하는 질문')}

### [질문 생성 사고 프로세스] (반드시 이 순서대로 생각하고 질문을 만드세요) ###
1. **DNA 융합:** 우리 회사의 **인재상(WHO)**과 **핵심 역량(WHAT)**을 고려했을 때, {position} 직무에서는 어떤 행동이나 기술적 결정이 가장 중요할지 정의하세요.

2. **상황 설정:** 위에서 정의한 행동/결정이 필요한 구체적인 문제 상황을 우리 회사의 **기술 중점 분야(WHERE)** 내에서 매우 현실적으로 설정하세요.

3. **질문 공식화:** 설정된 상황 속에서, 지원자가 어떻게 문제를 해결했는지 그 경험을 묻는 최종 질문을 만드세요. 이 질문은 반드시 우리 회사의 **평가 방향(HOW)**에 부합해야 하며, 지원자의 기술적 깊이와 우리 회사와의 문화적 적합성을 동시에 파악할 수 있어야 합니다.

### [질문 생성의 예시] ###
**만약 회사가 '네이버', 인재상이 '기술로 모든 것을 연결하는 플랫폼 빌더', 기술 중점이 'AI', 직군이 '백엔드'라면:**
- **사고 과정:** '기술로 모든 것을 연결'하는 '백엔드' 개발자는 기존 시스템의 한계를 넘어서는 것을 두려워하지 않아야 한다. 네이버의 'AI' 기술 중점 분야에서, 대규모 AI 모델의 데이터 서빙 파이프라인은 항상 도전적인 과제이다.
- **좋은 질문:** "네이버의 핵심 가치 중 하나는 '기술로 모든 것을 연결'하는 것입니다. 과거 대규모 AI 모델에 실시간으로 데이터를 공급하는 파이프라인에서 병목 현상을 겪고, 이를 해결하기 위해 기존 시스템의 구조에 '도전'하여 새롭게 개선했던 경험이 있다면 말씀해주세요. 어떤 기술적 근거로 새로운 아키텍처를 제안했고, 그 결과는 어땠나요?"

### [최종 출력] ###
다른 어떤 설명도 없이, 아래 JSON 형식에 맞춰서만 응답하세요.
{{
  "question": "생성된 최종 질문 내용",
  "intent": "이 질문을 통해 평가하려는 역량 (예: 데이터베이스 최적화 능력과 고객 중심 사고의 결합)",
  "related_dna": ["평가와 관련된 회사 DNA 키워드 (예: '고객 중심', '최고의 기술력')"]
}}
"""
        return prompt
    
    def _generate_follow_up_question(self, previous_question: str, user_answer: str, 
                                   chun_sik_answer: str, company_info: Dict, 
                                   interviewer_role: str, user_resume: Dict = None) -> Dict:
        """동적 꼬리 질문 생성 - 답변 기반 실시간 심층 탐구"""
        
        company_name = company_info.get('name', '회사')
        
        # 꼬리 질문 생성 프롬프트
        prompt = f"""
당신은 {company_name}의 {interviewer_role} 담당 면접관입니다.

이전 질문: {previous_question}

사용자 답변: {user_answer}

춘식이 답변: {chun_sik_answer}

위 상황을 분석하여, 다음 중 하나의 목표를 달성할 수 있는 날카로운 꼬리 질문을 즉석에서 단 하나만 생성하세요:

목표 1 (심층 검증): 한 지원자의 답변에서 더 깊게 파고들 만한 부분을 찾아 구체적인 추가 설명을 요구하세요.
목표 2 (비교 분석): 두 답변의 차이점을 정확히 짚어내고, 각자의 선택에 대한 이유나 생각을 토론하도록 유도하세요.  
목표 3 (수준 조절): 한 지원자가 답변을 잘 못했다면, 그 상황을 고려하여 더 쉬운 개념 질문으로 전환하세요.

꼬리 질문 생성 가이드라인:
- 이전 답변의 구체적인 내용을 언급하며 질문하세요
- "방금 말씀하신 ~에 대해", "~라고 하셨는데" 등의 표현 활용
- 단순한 Yes/No 질문보다는 구체적인 설명을 요구하는 열린 질문
- 두 지원자 모두에게 공정하게 답변 기회 제공
- 면접관의 전문성이 드러나는 날카로운 관점

응답 형식:
{{"question": "질문 내용", "intent": "질문 의도"}}
"""
        
        # LLM 호출
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": """당신은 경험 많은 전문 면접관입니다. 지원자들의 답변을 분석하여 핵심을 파고드는 날카로운 꼬리 질문을 생성합니다.

🚨 **절대 준수 사항** 🚨
- 오직 아래 JSON 형식으로만 응답하세요
- 다른 어떤 텍스트, 설명, 주석도 절대 포함하지 마세요
- JSON 앞뒤에 ```json이나 기타 텍스트 금지

**필수 응답 형식:**
{"question": "질문 내용", "intent": "질문 의도"}

**예시:**
{"question": "방금 말씀하신 성능 최적화 방법에서 가장 효과적이었던 부분은 무엇인가요?", "intent": "구체적인 기술적 성과와 판단 근거 확인"}

위 형식만 사용하세요. 다른 형태의 응답은 시스템 오류를 발생시킵니다."""},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7  # 창의적인 꼬리 질문을 위해 조금 높임
            )
            
            # JSON 파싱 개선 (꼬리 질문용)
            result_text = response.choices[0].message.content.strip()
            
            if not result_text:
                raise ValueError("LLM이 빈 응답을 반환했습니다")
            
            # JSON 블록 추출 (```json 블록 또는 { } 블록)
            if '```json' in result_text:
                json_start = result_text.find('```json') + 7
                json_end = result_text.find('```', json_start)
                result_text = result_text[json_start:json_end].strip()
            elif '{' in result_text and '}' in result_text:
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                result_text = result_text[json_start:json_end]
            
            result = json.loads(result_text)
            
            # 결과 검증 및 보정
            if not result.get('question'):
                raise ValueError("question 필드가 비어있습니다")
            
            # 이름 호명 추가
            candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
            result['question'] = self._add_candidate_name_to_question(result['question'], candidate_name)
            
            result['interviewer_type'] = interviewer_role
            result['question_type'] = 'follow_up'
            result['question_source'] = 'llm_follow_up'
            return result
            
        except Exception as e:
            print(f"❌ 꼬리 질문 생성 실패: {e}")
            # 폴백 꼬리 질문
            return self._get_fallback_follow_up_question(interviewer_role, previous_question, user_resume)
    
    def _get_fallback_follow_up_question(self, interviewer_role: str, previous_question: str, user_resume: Dict = None) -> Dict:
        """꼬리 질문 생성 실패 시 폴백 질문"""
        
        fallback_follow_ups = {
            'HR': {
                'question': '방금 말씀해주신 내용에서 가장 어려웠던 점은 무엇이었나요?',
                'intent': '어려움 극복 과정과 성장 경험 확인'
            },
            'TECH': {
                'question': '해당 기술이나 방법을 선택한 구체적인 이유가 있다면 설명해주세요.',
                'intent': '기술적 판단 근거와 의사결정 과정 평가'
            },
            'COLLABORATION': {
                'question': '그 상황에서 다른 팀원들의 반응은 어땠나요?',
                'intent': '팀 동료와의 상호작용과 영향력 평가'
            }
        }
        
        fallback = fallback_follow_ups.get(interviewer_role, fallback_follow_ups['HR'])
        
        # 이름 호명 추가
        candidate_name = user_resume.get('name', '지원자') if user_resume else '지원자'
        fallback['question'] = self._add_candidate_name_to_question(fallback['question'], candidate_name)
        
        fallback['interviewer_type'] = interviewer_role
        fallback['question_type'] = 'follow_up'
        fallback['question_source'] = 'fallback'
        
        return fallback
    
    def _add_candidate_name_to_question(self, question: str, candidate_name: str, is_intro_question: bool = False) -> str:
        """질문에 지원자 이름 호명 추가"""
        if not candidate_name or candidate_name == '지원자':
            return question
        
        # 자기소개 질문인 경우 특별 처리 (이미 이름을 모르는 상황)
        if is_intro_question:
            return question
        
        # 이름 호명 패턴들 (자연스러운 다양성 확보)
        name_patterns = [
            f"{candidate_name}님, {question}",
            f"{candidate_name}님께서는 {question}",
            f"{candidate_name}님, {question}",
            f"그렇다면 {candidate_name}님, {question}",
            f"{candidate_name}님의 경우 {question}"
        ]
        
        # 랜덤하게 패턴 선택 (80% 확률로 이름 호명)
        if random.random() < 0.8:
            selected_pattern = random.choice(name_patterns[:3])  # 기본 패턴 우선 사용
            return selected_pattern
        else:
            return question  # 20%는 이름 없이 (자연스러운 다양성)
    
    def _inject_data_to_template(self, template: str, user_resume: Dict, company_info: Dict) -> str:
        """템플릿에 실제 데이터 동적 주입"""
        result = template
        
        # 회사 정보 치환
        result = result.replace('{company_name}', company_info.get('name', '회사'))
        result = result.replace('{talent_profile}', company_info.get('talent_profile', ''))
        result = result.replace('{tech_focus}', ', '.join(company_info.get('tech_focus', [])))
        
        # 지원자 정보 치환 
        if user_resume:
            result = result.replace('{candidate_name}', user_resume.get('name', '지원자'))
            result = result.replace('{experience_years}', str(user_resume.get('career_years', '0')))
            result = result.replace('{main_skills}', ', '.join(user_resume.get('technical_skills', [])[:3]))
        
        # AI 지원자 이름 통일
        result = result.replace('{persona_name}', '춘식이')
        
        return result
    

def main():
    """턴제 면접 시스템 테스트"""
    print("🎯 지능형 턴제 면접관 패널 시스템 테스트")
    
    try:
        # 서비스 초기화
        service = InterviewerService(total_question_limit=10)
        
        # 샘플 데이터
        user_resume = {
            'name': '김개발',
            'position': '백엔드 개발자',  # 직군 정보 추가
            'career_years': '3',
            'technical_skills': ['Python', 'Django', 'PostgreSQL', 'AWS']
        }
        
        persona = CandidatePersona(
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
        
        qa_history = []
        total_topics = sum(len(topics) for topics in service.topic_pools.values())
        
        print(f"💼 질문 한도: {service.total_question_limit}개")
        print(f"👥 면접관: {', '.join(service.interviewer_roles)}")
        print(f"🎲 주제 풀: {total_topics}개")
        
        # 면접 시뮬레이션
        while service.questions_asked_count < service.total_question_limit:
            question = service.generate_next_question(
                user_resume, persona, '1', qa_history,
                user_answer="API 응답 시간을 50% 개선한 경험이 있습니다." if qa_history else None,
                chun_sik_answer="코드 리뷰와 테스트 코드 작성을 중시합니다." if qa_history else None
            )
            
            if question.get('is_final'):
                print(f"\n✅ {question['question']}")
                break
                
            if question.get('force_turn_switch'):
                print(f"🔄 {question['interviewer_type']} 면접관 턴 종료")
                continue
            
            # 질문 출력
            num = service.questions_asked_count
            interviewer = service._get_current_interviewer()
            state = service.interviewer_turn_state[interviewer]
            
            print(f"\n📝 질문 {num}번 - {question['interviewer_type']}")
            if question.get('topic'):
                print(f"🎯 주제: {question['topic']}")
            print(f"❓ {question['question']}")
            print(f"📈 턴 상태: 메인 {'✓' if state['main_question_asked'] else '✗'}, 꼬리 {state['follow_up_count']}개")
            
            qa_history.append({'question': question['question'], 'interviewer_type': question['interviewer_type']})
            
            if num >= 8:  # 테스트 제한
                break
        
        # 최종 통계
        print(f"\n📊 총 질문 수: {service.questions_asked_count}개")
        for role in service.interviewer_roles:
            state = service.interviewer_turn_state[role]
            print(f"   {role}: 메인 {'✓' if state['main_question_asked'] else '✗'}, 꼬리 {state['follow_up_count']}개")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()