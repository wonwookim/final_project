#!/usr/bin/env python3
"""
End-to-End 면접 시뮬레이션 테스트
목표: 실제 면접과 동일한 전체 시퀀스를 시뮬레이션하며, 각 단계별 모델 성능을 종합적으로 평가

면접 순서:
1. 아이스브레이킹 (2턴)
2. HR 면접관 (2턴) 
3. 기술(TECH) 면접관 (2턴)
4. 협업(COLLABORATION) 면접관 (2턴)
총 8턴의 완전한 면접 사이클
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # 핵심 서비스 임포트
    print("🔄 E2E 테스트 모듈 임포트 중...")
    
    from llm.shared.models import QuestionType, AnswerRequest
    from llm.candidate.model import CandidatePersona, AICandidateModel, POSITION_MAPPING
    from llm.interviewer.service import InterviewerService
    from llm.candidate.quality_controller import QualityLevel
    from llm.core.llm_manager import LLMProvider
    from llm.shared.company_data_loader import get_company_loader
    
    print("✅ 모든 모듈 임포트 완료")
    
except ImportError as e:
    print(f"❌ 필수 모듈 임포트 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


class EndToEndInterviewSimulator:
    """실제 면접과 동일한 E2E 시뮬레이션 및 성능 평가"""
    
    def __init__(self):
        """시뮬레이터 초기화"""
        self.company_id = "naver"  # 네이버로 고정
        self.position = "백엔드"
        self.total_turns = 8  # 총 8턴
        
        # 면접관 순서 정의 (2턴씩)
        self.interview_sequence = [
            {"turns": [1, 2], "type": "ICEBREAKING", "interviewer": "아이스브레이킹"},
            {"turns": [3, 4], "type": QuestionType.HR, "interviewer": "HR 면접관"},  
            {"turns": [5, 6], "type": QuestionType.TECH, "interviewer": "기술 면접관"},
            {"turns": [7, 8], "type": QuestionType.COLLABORATION, "interviewer": "협업 면접관"}
        ]
        
        # 결과 저장
        self.simulation_results = {
            "timestamp": datetime.now().isoformat(),
            "test_scenario": "E2E 전체 면접 시뮬레이션 (8턴)",
            "company": "네이버",
            "position": "백엔드",
            "total_turns": self.total_turns,
            "turns": [],
            "performance_summary": {},
            "conversation_flow": []
        }
        
        # 서비스 초기화
        self.ai_candidate = AICandidateModel()
        self.interviewer_service = InterviewerService()
        self.company_loader = get_company_loader()
        
        # 페르소나 저장
        self.persona = None
        
        print(f"✅ E2E 시뮬레이터 초기화 완료 (총 {self.total_turns}턴)")
    
    def get_current_interview_context(self, turn_number: int) -> Dict[str, Any]:
        """현재 턴의 면접 맥락 정보 반환"""
        for sequence in self.interview_sequence:
            if turn_number in sequence["turns"]:
                return {
                    "turn_number": turn_number,
                    "question_type": sequence["type"],
                    "interviewer_name": sequence["interviewer"],
                    "is_first_turn_of_interviewer": turn_number == sequence["turns"][0],
                    "is_followup": turn_number == sequence["turns"][1]
                }
        return {}
    
    def generate_persona_once(self) -> bool:
        """페르소나 최초 1회 생성"""
        print("\n" + "="*80)
        print("🎭 1단계: 페르소나 생성")
        print("="*80)
        
        try:
            # 실제 AICandidateModel 호출
            self.persona = self.ai_candidate.create_persona_for_interview("네이버", "백엔드")
            
            if not self.persona:
                print("❌ 페르소나 생성 실패")
                return False
            
            print(f"✅ 페르소나 생성 성공: {self.persona.name}")
            print(f"   배경: {self.persona.background.get('current_position', '신입')} ({self.persona.background.get('career_years', '0')}년)")
            print(f"   기술 스택: {', '.join(self.persona.technical_skills[:5])}")
            
            # 결과에 페르소나 정보 저장
            self.simulation_results["persona"] = {
                "name": self.persona.name,
                "background": self.persona.background,
                "technical_skills": self.persona.technical_skills,
                "projects": self.persona.projects,
                "strengths": self.persona.strengths
            }
            
            return True
            
        except Exception as e:
            print(f"❌ 페르소나 생성 중 오류: {str(e)}")
            return False
    
    def generate_question_for_turn(self, turn_number: int) -> Optional[Dict[str, Any]]:
        """특정 턴의 질문 생성"""
        context = self.get_current_interview_context(turn_number)
        
        print(f"\n🎯 Turn {turn_number}: {context['interviewer_name']} 질문 생성")
        
        try:
            # 이전 대화 기록 준비
            previous_qa_pairs = []
            for turn_data in self.simulation_results["turns"]:
                if "question" in turn_data and "answer" in turn_data:
                    previous_qa_pairs.append({
                        "question": turn_data["question"]["content"],
                        "user_answer": turn_data["answer"]["content"],
                        "chun_sik_answer": turn_data["answer"]["content"]  # E2E 테스트에서는 동일
                    })
            
            # InterviewerService의 실제 API 사용
            if context["question_type"] == "ICEBREAKING":
                # 아이스브레이킹은 특별 처리
                if turn_number == 1:
                    question_result = {
                        "question": "안녕하세요! 먼저 간단한 자기소개를 부탁드립니다.",
                        "intent": "지원자의 기본 정보와 성격을 파악하여 면접 분위기를 조성",
                        "question_type": "INTRO",
                        "interviewer_role": "아이스브레이킹"
                    }
                else:
                    # 2턴째는 간단한 꼬리 질문
                    question_result = {
                        "question": "자기소개에서 언급하신 경험에 대해 좀 더 자세히 말씀해 주세요.",
                        "intent": "자기소개 내용 심화 탐구",
                        "question_type": "FOLLOW_UP",
                        "interviewer_role": "아이스브레이킹"
                    }
            else:
                # 더미 사용자 이력서 생성 (E2E 테스트용)
                user_resume = {
                    "name": "테스트 사용자",
                    "position": self.position,
                    "experience": "신입",
                    "skills": ["Python", "JavaScript"],
                    "projects": ["개인 프로젝트"]
                }
                
                # InterviewerService.generate_next_question 호출
                question_result = self.interviewer_service.generate_next_question(
                    user_resume=user_resume,
                    chun_sik_persona=self.persona,
                    company_id=self.company_id,
                    previous_qa_pairs=previous_qa_pairs,
                    user_answer=previous_qa_pairs[-1]["user_answer"] if previous_qa_pairs else None,
                    chun_sik_answer=previous_qa_pairs[-1]["chun_sik_answer"] if previous_qa_pairs else None
                )
            
            if question_result and "question" in question_result:
                print(f"✅ 질문 생성 성공: {question_result['question'][:50]}...")
                return {
                    "content": question_result["question"],
                    "intent": question_result.get("intent", ""),
                    "question_type": question_result.get("question_type", str(context["question_type"])),
                    "interviewer": question_result.get("interviewer_role", context["interviewer_name"])
                }
            else:
                print("❌ 질문 생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ 질문 생성 중 오류: {str(e)}")
            return None
    
    def generate_answer_for_question(self, question: str, turn_number: int) -> Optional[Dict[str, Any]]:
        """질문에 대한 답변 생성"""
        print(f"💬 Turn {turn_number}: 답변 생성 중...")
        
        try:
            # AnswerRequest 생성  
            answer_request = AnswerRequest(
                question_content=question,
                question_type=QuestionType.GENERAL,
                question_intent="일반 질문",
                company_id=self.company_id,
                position=self.position,
                quality_level=QualityLevel.VERY_GOOD,
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            # AICandidateModel.generate_answer 호출 (페르소나 전달)
            answer_result = self.ai_candidate.generate_answer(answer_request, persona=self.persona)
            
            if answer_result and hasattr(answer_result, 'answer_content') and answer_result.answer_content:
                answer_content = answer_result.answer_content
                print(f"✅ 답변 생성 성공: {answer_content[:50]}...")
                
                return {
                    "content": answer_content,
                    "quality_level": str(answer_result.quality_level) if hasattr(answer_result, 'quality_level') else "VERY_GOOD",
                    "length": len(answer_content.split())
                }
            else:
                print("❌ 답변 생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ 답변 생성 중 오류: {str(e)}")
            return None
    
    def evaluate_turn_performance(self, turn_number: int, question: Dict[str, Any], answer: Dict[str, Any]) -> Dict[str, Any]:
        """턴별 성능 평가"""
        print(f"📊 Turn {turn_number}: 성능 평가 중...")
        
        evaluation = {
            "turn_number": turn_number,
            "question_evaluation": {},
            "answer_evaluation": {},
            "overall_score": 0,
            "feedback": []
        }
        
        # 질문 품질 평가
        question_content = question["content"]
        persona_keywords = self.persona.technical_skills + [self.persona.name]
        
        # 페르소나 연관성 체크
        persona_relevance = sum(1 for keyword in persona_keywords if keyword.lower() in question_content.lower())
        
        evaluation["question_evaluation"] = {
            "persona_relevance_score": min(persona_relevance * 10, 50),  # 최대 50점
            "question_length": len(question_content.split()),
            "has_specific_context": len(question_content.split()) > 10,
            "interviewer_type": question["interviewer"]
        }
        
        # 답변 품질 평가  
        answer_content = answer["content"]
        
        # 페르소나 일관성 체크
        persona_consistency = sum(1 for skill in self.persona.technical_skills[:3] if skill.lower() in answer_content.lower())
        
        # 구체적 사례 포함 여부
        has_examples = any(word in answer_content.lower() for word in ["프로젝트", "경험", "구현", "개발", "사용"])
        
        evaluation["answer_evaluation"] = {
            "persona_consistency_score": min(persona_consistency * 15, 45),  # 최대 45점
            "has_specific_examples": has_examples,
            "answer_length": answer["length"],
            "quality_level": answer["quality_level"]
        }
        
        # 전체 점수 계산 (0-100)
        question_score = evaluation["question_evaluation"]["persona_relevance_score"]
        answer_score = evaluation["answer_evaluation"]["persona_consistency_score"]
        length_bonus = min(answer["length"] // 10, 15)  # 길이 보너스 최대 15점
        
        evaluation["overall_score"] = min(question_score + answer_score + length_bonus, 100)
        
        # 피드백 생성
        feedback = []
        
        if persona_relevance > 0:
            feedback.append(f"✅ [질문 품질] 페르소나의 {persona_relevance}개 키워드와 연관된 좋은 질문입니다.")
        else:
            feedback.append("⚠️  [질문 품질] 페르소나와 연관성이 부족합니다.")
        
        if has_examples:
            feedback.append("✅ [답변 품질] 구체적인 경험과 사례를 포함한 좋은 답변입니다.")
        else:
            feedback.append("⚠️  [답변 품질] 더 구체적인 사례가 필요합니다.")
        
        if evaluation["overall_score"] >= 70:
            feedback.append(f"🎯 [전체 평가] {evaluation['overall_score']}점 - 우수한 질의응답입니다.")
        elif evaluation["overall_score"] >= 50:
            feedback.append(f"📈 [전체 평가] {evaluation['overall_score']}점 - 보통 수준의 질의응답입니다.")
        else:
            feedback.append(f"📉 [전체 평가] {evaluation['overall_score']}점 - 개선이 필요합니다.")
        
        evaluation["feedback"] = feedback
        
        # 실시간 피드백 출력
        print("\n📊 실시간 성능 평가:")
        for fb in feedback:
            print(f"   {fb}")
        print(f"   턴 점수: {evaluation['overall_score']}/100")
        
        return evaluation
    
    def run_complete_simulation(self) -> bool:
        """전체 E2E 시뮬레이션 실행"""
        print("\n" + "🚀" + "="*78 + "🚀")
        print("🎬 E2E 전체 면접 시뮬레이션 시작")
        print("🚀" + "="*78 + "🚀")
        
        start_time = time.time()
        
        # 1. 페르소나 생성
        if not self.generate_persona_once():
            return False
        
        # 2. 8턴 면접 진행
        total_score = 0
        successful_turns = 0
        
        for turn in range(1, self.total_turns + 1):
            print(f"\n{'='*20} TURN {turn}/{self.total_turns} {'='*20}")
            
            # 질문 생성
            question = self.generate_question_for_turn(turn)
            if not question:
                print(f"❌ Turn {turn} 질문 생성 실패")
                continue
            
            # 답변 생성  
            answer = self.generate_answer_for_question(question["content"], turn)
            if not answer:
                print(f"❌ Turn {turn} 답변 생성 실패")
                continue
            
            # 성능 평가
            evaluation = self.evaluate_turn_performance(turn, question, answer)
            
            # 결과 저장
            turn_result = {
                "turn_number": turn,
                "question": question,
                "answer": answer,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }
            
            self.simulation_results["turns"].append(turn_result)
            self.simulation_results["conversation_flow"].append({
                "turn": turn,
                "interviewer": question["interviewer"], 
                "question": question["content"],
                "answer": answer["content"]
            })
            
            total_score += evaluation["overall_score"]
            successful_turns += 1
            
            print(f"✅ Turn {turn} 완료 (점수: {evaluation['overall_score']}/100)")
        
        # 3. 최종 성능 요약
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.simulation_results["performance_summary"] = {
            "total_turns_completed": successful_turns,
            "success_rate": (successful_turns / self.total_turns) * 100,
            "average_score": total_score / successful_turns if successful_turns > 0 else 0,
            "total_score": total_score,
            "execution_time_seconds": execution_time,
            "performance_grade": self._get_performance_grade(total_score / successful_turns if successful_turns > 0 else 0)
        }
        
        print(f"\n🏁 E2E 시뮬레이션 완료!")
        print(f"   완료 턴 수: {successful_turns}/{self.total_turns}")
        print(f"   평균 점수: {self.simulation_results['performance_summary']['average_score']:.1f}/100")
        print(f"   실행 시간: {execution_time:.1f}초")
        
        return successful_turns > 0
    
    def _get_performance_grade(self, avg_score: float) -> str:
        """평균 점수를 기반으로 성능 등급 반환"""
        if avg_score >= 90:
            return "A급 (최우수)"
        elif avg_score >= 80:
            return "B급 (우수)"
        elif avg_score >= 70:
            return "C급 (보통)"
        elif avg_score >= 60:
            return "D급 (개선필요)"
        else:
            return "F급 (부족)"
    
    def save_results(self) -> str:
        """결과를 JSON 파일로 저장"""
        # test_results 디렉토리 생성
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_results")
        os.makedirs(results_dir, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"e2e_interview_result_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # JSON 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.simulation_results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 결과 저장 완료: {filepath}")
        return filepath


def main():
    """메인 실행 함수"""
    print("🎭 E2E 전체 면접 시뮬레이션 테스트")
    print("=" * 80)
    
    simulator = EndToEndInterviewSimulator()
    
    # 시뮬레이션 실행
    success = simulator.run_complete_simulation()
    
    if success:
        # 결과 저장
        result_file = simulator.save_results()
        
        print("\n" + "🎉" + "="*78 + "🎉")
        print("✅ E2E 면접 시뮬레이션 테스트 완료!")
        print("🎉" + "="*78 + "🎉")
        print(f"📊 성능 요약:")
        summary = simulator.simulation_results["performance_summary"]
        print(f"   • 완료율: {summary['success_rate']:.1f}%")
        print(f"   • 평균 점수: {summary['average_score']:.1f}/100")
        print(f"   • 성능 등급: {summary['performance_grade']}")
        print(f"   • 실행 시간: {summary['execution_time_seconds']:.1f}초")
        print(f"📄 상세 결과: {result_file}")
    else:
        print("\n❌ E2E 시뮬레이션이 실패하였습니다.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)