#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Model Test
- Question Generation -> Answer Generation -> RAGAS Evaluation
"""

import os
import sys
import logging
import openai
import pandas as pd
from datetime import datetime
from typing import Dict, List
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, answer_correctness

# Suppress all logs except CRITICAL
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("backend.services.existing_tables_service").setLevel(logging.CRITICAL)
logging.getLogger("llm.shared.utils").setLevel(logging.CRITICAL)

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import existing models
from llm.interviewer.question_generator import QuestionGenerator  
from llm.candidate.model import AICandidateModel
from llm.candidate.quality_controller import QualityLevel
from llm.shared.models import AnswerRequest, QuestionType, LLMProvider

# Available options
COMPANIES = {
    "1": ("naver", "네이버"),
    "2": ("kakao", "카카오"),
    "3": ("toss", "토스"),
    "4": ("coupang", "쿠팡"),
    "5": ("baemin", "배달의민족"),
    "6": ("daangn", "당근마켓"),
    "7": ("line", "라인")
}

POSITIONS = {
    "1": ("backend", "백엔드"),
    "2": ("frontend", "프론트엔드"),
    "3": ("data", "데이터사이언스"),
    "4": ("ai", "AI/ML"),
    "5": ("planning", "기획")
}

INTERVIEWER_ROLES = {
    "1": ("HR", "인사"),
    "2": ("TECH", "기술"),
    "3": ("COLLABORATION", "협업")
}

def generate_ground_truth_answer(question: str, company_id: str, position: str, interviewer_role: str, persona_resume: Dict) -> str:
    """면접관 관점에서 페르소나 기반 모범답안 생성"""
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Convert resume dict to a readable string for the prompt
    resume_summary = f"""지원자 정보:
- 이름: {persona_resume.get('name', 'Unknown')}
- 경력: {persona_resume.get('background', {}).get('career_years', 'N/A')}년
- 주요 기술: {', '.join(persona_resume.get('technical_skills', [])[:5])}
- 강점: {', '.join(persona_resume.get('strengths', [])[:3])}
- 목표: {persona_resume.get('career_goal', 'N/A')}"""
    
    system_prompt = f"""당신은 {company_id} 회사의 경험 많은 {interviewer_role} 면접관입니다.
{position} 직군 지원자에게 한 질문에 대해, 아래 제공된 지원자의 이력서 내용을 바탕으로 이상적인 모범답안을 작성해주세요.

{resume_summary}

모범답안 작성 가이드:
- 제공된 지원자의 이력과 경험에 기반한 답변
- 지원자의 기술 스택과 강점을 활용한 구체적인 예시 포함
- 논리적이고 체계적인 구조
- 적절한 길이 (150-250단어)
- 지원자의 목표와 연결된 답변"""

    user_prompt = f"""질문: {question}

위 질문에 대해 제공된 지원자 정보를 바탕으로 모범답안을 작성해주세요. 
지원자의 실제 경험과 기술을 활용한 현실적이고 설득력 있는 답변이어야 합니다."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ 모범답안 생성 실패: {e}")
        return "모범답안 생성에 실패했습니다."

def evaluate_with_ragas(question: str, ground_truth: str, candidate_answers: List[Dict]) -> Dict:
    """RAGAS 라이브러리로 답변 평가"""
    try:
        # RAGAS Dataset 생성
        data = {
            "question": [question] * len(candidate_answers),
            "contexts": [["면접 상황"]] * len(candidate_answers),  # RAGAS에서 contexts 필수
            "answer": [ans["content"] for ans in candidate_answers],
            "ground_truth": [ground_truth] * len(candidate_answers)
        }
        
        dataset = Dataset.from_dict(data)
        
        # RAGAS 평가 실행
        result = evaluate(
            dataset,
            metrics=[answer_relevancy, answer_correctness]
        )
        
        return result
        
    except Exception as e:
        print(f"❌ RAGAS 평가 실패: {e}")
        return {"error": str(e)}

def save_results_to_excel(test_data: Dict, filename: str = None) -> str:
    """테스트 결과를 Excel 파일로 저장"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_test/ragas_evaluation_results_{timestamp}.xlsx"
    
    try:
        # Create DataFrame
        df = pd.DataFrame([test_data])
        
        # Save to Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"📊 결과가 Excel 파일로 저장되었습니다: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Excel 저장 실패: {e}")
        return ""

def get_user_choice(options_dict, prompt_text):
    """사용자에게 선택지를 보여주고 선택을 받는 함수"""
    print(f"\n{prompt_text}")
    print("-" * 30)
    for key, (value, korean) in options_dict.items():
        print(f"{key}. {korean} ({value})")
    
    while True:
        try:
            choice = input("\n선택하세요 (번호 입력): ").strip()
            if choice in options_dict:
                return options_dict[choice]
            print("❌ 올바른 번호를 입력해주세요.")
        except EOFError:
            # 비대화형 환경에서는 기본값 사용
            print("\n[비대화형 모드] 기본값 사용: 네이버 백엔드 기술면접")
            if "1" in options_dict:
                return options_dict["1"]
            return list(options_dict.values())[0]

def main():
    print("🎯 AI Model Test")
    print("=" * 50)
    
    # User selections
    print("설정을 선택해주세요:")
    
    # 1. Company selection
    company_id, company_name = get_user_choice(COMPANIES, "📍 회사를 선택하세요:")
    
    # 2. Position selection  
    position, position_name = get_user_choice(POSITIONS, "💼 직군을 선택하세요:")
    
    # 3. Interviewer role selection
    interviewer_role, role_name = get_user_choice(INTERVIEWER_ROLES, "👨‍💼 면접관 유형을 선택하세요:")
    
    print(f"\n✅ 선택완료: {company_name} {position_name} {role_name} 면접")
    
    # Initialize models
    print("\n🔧 모델 초기화 중...")
    question_gen = QuestionGenerator()
    answer_gen = AICandidateModel()
    
    # 1. Create single persona for consistency (MOVED TO FIRST)
    print(f"\n👤 페르소나 생성 중...")
    persona = answer_gen.create_persona_for_interview(company_id, position)
    if not persona:
        persona = answer_gen._create_default_persona(company_id, position)
    
    print(f"✅ 페르소나: {persona.name}")
    print(f"   경력: {persona.background.get('career_years', '미정')}년")
    print(f"   주요기술: {', '.join(persona.technical_skills[:3])}")
    
    # 2. Create a resume dictionary from the persona object
    resume_data = {
        "name": persona.name,
        "background": persona.background,
        "technical_skills": persona.technical_skills,
        "experiences": persona.experiences,
        "projects": persona.projects,
        "strengths": persona.strengths,
        "career_goal": persona.career_goal
    }
    
    # 3. Generate context-aware question
    print("\n📝 질문 생성 중...")
    question_result = question_gen.generate_question_by_role(
        interviewer_role=interviewer_role,
        company_id=company_id, 
        user_resume=resume_data  # Use actual persona data instead of placeholder
    )
    question = question_result['question']
    
    print(f"\n📝 Generated Question:")
    print(f"{question}")
    
    # 4. Generate context-aware ground truth answer
    print(f"\n🎯 모범답안 생성 중...")
    ground_truth = generate_ground_truth_answer(question, company_id, position, interviewer_role, persona_resume=resume_data)
    print(f"\n📖 모범답안:")
    print(f"{ground_truth}")
    print("-" * 50)
    
    # Map interviewer role to question type
    question_type_mapping = {
        "HR": QuestionType.HR,
        "TECH": QuestionType.TECH,
        "COLLABORATION": QuestionType.COLLABORATION
    }
    question_type = question_type_mapping.get(interviewer_role, QuestionType.TECH)
    
    # 2. Generate answers by level with same persona
    print(f"\n🤖 AI 답변 생성 중...")
    print("\n🤖 AI Answers:")
    print("-" * 50)
    
    levels = [
        ("🔰 초급", QualityLevel.INADEQUATE), 
        ("🔸 중급", QualityLevel.AVERAGE), 
        ("🔥 고급", QualityLevel.EXCELLENT)
    ]
    
    candidate_answers = []
    
    for level_name, quality_level in levels:
        request = AnswerRequest(
            question_content=question,
            question_type=question_type,
            question_intent=f"{role_name} 역량 평가",
            company_id=company_id,
            position=position, 
            quality_level=quality_level,
            llm_provider=LLMProvider.OPENAI_GPT4O
        )
        
        print(f"\n{level_name} 답변 생성 중...")
        response = answer_gen.generate_answer(request, persona=persona)  # 같은 페르소나 사용
        print(f"\n{level_name}:")
        print(f"{response.answer_content}")
        print("-" * 30)
        
        # Store for RAGAS evaluation
        candidate_answers.append({
            "level": level_name,
            "content": response.answer_content
        })
    
    # 3. RAGAS Evaluation
    print(f"\n🔍 RAGAS 평가 실행 중...")
    ragas_result = evaluate_with_ragas(question, ground_truth, candidate_answers)
    
    # RAGAS 결과 처리
    try:
        if isinstance(ragas_result, dict) and "error" in ragas_result:
            print(f"\n❌ RAGAS 평가 오류: {ragas_result['error']}")
        else:
            print(f"\n📊 RAGAS 평가 결과:")
            print("=" * 50)
            
            # RAGAS 결과에서 점수 추출
            try:
                # RAGAS 0.3.x 버전에서는 직접 접근
                scores = ragas_result
                
                # Display results for each answer
                for i, ans in enumerate(candidate_answers):
                    print(f"\n{ans['level']} 평가:")
                    print(f"  • Answer Relevancy: {scores['answer_relevancy'][i]:.3f}")
                    print(f"  • Answer Correctness: {scores['answer_correctness'][i]:.3f}")  
                    print(f"  • 종합 점수: {(scores['answer_relevancy'][i] + scores['answer_correctness'][i]) / 2:.3f}")
                    
                print(f"\n📈 평균 점수:")
                print(f"  • Answer Relevancy: {sum(scores['answer_relevancy']) / len(scores['answer_relevancy']):.3f}")
                print(f"  • Answer Correctness: {sum(scores['answer_correctness']) / len(scores['answer_correctness']):.3f}")
                print(f"  • 전체 평균: {(sum(scores['answer_relevancy']) + sum(scores['answer_correctness'])) / (2 * len(scores['answer_relevancy'])):.3f}")
                
            except Exception as score_error:
                print(f"\n  📊 RAGAS 점수 (원본 결과):")
                print(f"     결과 타입: {type(ragas_result)}")
                print(f"     결과 내용: {ragas_result}")
                
    except Exception as e:
        print(f"\n❌ RAGAS 결과 처리 오류: {e}")
        print(f"   결과 타입: {type(ragas_result)}")
        print(f"   결과: {ragas_result}")
    
    # 5. Save results to Excel
    print(f"\n💾 결과 저장 중...")
    
    # Prepare test data for Excel
    test_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": company_name,
        "position": position_name,
        "interviewer_role": role_name,
        "persona_name": persona.name,
        "persona_experience": persona.background.get('career_years', '미정'),
        "persona_skills": ', '.join(persona.technical_skills[:5]),
        "question": question,
        "ground_truth": ground_truth,
        "beginner_answer": candidate_answers[0]["content"] if len(candidate_answers) > 0 else "",
        "intermediate_answer": candidate_answers[1]["content"] if len(candidate_answers) > 1 else "",
        "advanced_answer": candidate_answers[2]["content"] if len(candidate_answers) > 2 else "",
    }
    
    # Add RAGAS scores if available
    try:
        if not isinstance(ragas_result, dict) or "error" not in ragas_result:
            # RAGAS 결과 구조 확인 및 점수 추출
            print(f"🔍 RAGAS 결과 타입: {type(ragas_result)}")
            
            # 여러 가지 방법으로 점수 접근 시도
            scores = None
            if hasattr(ragas_result, 'scores'):
                scores = ragas_result.scores
                print(f"🔍 scores 속성 접근 성공")
            elif hasattr(ragas_result, '__getitem__'):
                try:
                    scores = dict(ragas_result)
                    print(f"🔍 dict 변환 성공")
                except:
                    pass
            elif isinstance(ragas_result, dict):
                scores = ragas_result
                print(f"🔍 dict 직접 사용")
            
            if scores and 'answer_relevancy' in scores and 'answer_correctness' in scores:
                relevancy_list = scores['answer_relevancy']
                correctness_list = scores['answer_correctness']
                
                test_data.update({
                    "beginner_relevancy": relevancy_list[0] if len(relevancy_list) > 0 else 0,
                    "beginner_correctness": correctness_list[0] if len(correctness_list) > 0 else 0,
                    "intermediate_relevancy": relevancy_list[1] if len(relevancy_list) > 1 else 0,
                    "intermediate_correctness": correctness_list[1] if len(correctness_list) > 1 else 0,
                    "advanced_relevancy": relevancy_list[2] if len(relevancy_list) > 2 else 0,
                    "advanced_correctness": correctness_list[2] if len(correctness_list) > 2 else 0,
                    "avg_relevancy": sum(relevancy_list) / len(relevancy_list) if relevancy_list else 0,
                    "avg_correctness": sum(correctness_list) / len(correctness_list) if correctness_list else 0,
                })
                print(f"✅ RAGAS 점수 추가 완료")
            else:
                print(f"❌ RAGAS 점수 구조 인식 실패: {scores}")
                # 기본값 추가
                test_data.update({
                    "beginner_relevancy": 0, "beginner_correctness": 0,
                    "intermediate_relevancy": 0, "intermediate_correctness": 0, 
                    "advanced_relevancy": 0, "advanced_correctness": 0,
                    "avg_relevancy": 0, "avg_correctness": 0,
                })
    except Exception as score_error:
        print(f"⚠️ 점수 추가 중 오류: {score_error}")
        # 오류 발생 시 기본값 추가
        test_data.update({
            "beginner_relevancy": 0, "beginner_correctness": 0,
            "intermediate_relevancy": 0, "intermediate_correctness": 0,
            "advanced_relevancy": 0, "advanced_correctness": 0, 
            "avg_relevancy": 0, "avg_correctness": 0,
        })
        
    # Save to Excel
    excel_file = save_results_to_excel(test_data)
    
    print(f"\n✅ 테스트 완료!")
    if excel_file:
        print(f"📁 결과 파일: {excel_file}")

def batch_test_scenarios():
    """여러 시나리오 자동 테스트 - 발표용 데이터 생성"""
    print("🚀 배치 테스트 모드 - 여러 시나리오 자동 실행")
    print("=" * 60)
    
    # Test scenarios
    scenarios = [
        ("naver", "네이버", "backend", "백엔드", "TECH", "기술"),
        ("kakao", "카카오", "frontend", "프론트엔드", "HR", "인사"),
        ("toss", "토스", "ai", "AI/ML", "TECH", "기술"),
        ("coupang", "쿠팡", "data", "데이터사이언스", "COLLABORATION", "협업"),
        ("baemin", "배달의민족", "planning", "기획", "HR", "인사"),
    ]
    
    all_results = []
    
    for i, (company_id, company_name, position, position_name, interviewer_role, role_name) in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] 테스트 중: {company_name} {position_name} {role_name} 면접")
        print("-" * 50)
        
        try:
            # Initialize models
            question_gen = QuestionGenerator()
            answer_gen = AICandidateModel()
            
            # Create persona
            persona = answer_gen.create_persona_for_interview(company_id, position)
            if not persona:
                persona = answer_gen._create_default_persona(company_id, position)
            
            print(f"✅ 페르소나: {persona.name} ({persona.background.get('career_years', '미정')}년)")
            
            # Create resume data
            resume_data = {
                "name": persona.name,
                "background": persona.background,
                "technical_skills": persona.technical_skills,
                "experiences": persona.experiences,
                "projects": persona.projects,
                "strengths": persona.strengths,
                "career_goal": persona.career_goal
            }
            
            # Generate question
            question_result = question_gen.generate_question_by_role(
                interviewer_role=interviewer_role,
                company_id=company_id, 
                user_resume=resume_data
            )
            question = question_result['question']
            print(f"📝 질문 생성 완료")
            
            # Generate ground truth
            ground_truth = generate_ground_truth_answer(question, company_id, position, interviewer_role, persona_resume=resume_data)
            print(f"🎯 모범답안 생성 완료")
            
            # Generate answers by level
            question_type_mapping = {
                "HR": QuestionType.HR,
                "TECH": QuestionType.TECH,
                "COLLABORATION": QuestionType.COLLABORATION
            }
            question_type = question_type_mapping.get(interviewer_role, QuestionType.TECH)
            
            levels = [
                ("초급", QualityLevel.INADEQUATE), 
                ("중급", QualityLevel.AVERAGE), 
                ("고급", QualityLevel.EXCELLENT)
            ]
            
            candidate_answers = []
            for level_name, quality_level in levels:
                request = AnswerRequest(
                    question_content=question,
                    question_type=question_type,
                    question_intent=f"{role_name} 역량 평가",
                    company_id=company_id,
                    position=position, 
                    quality_level=quality_level,
                    llm_provider=LLMProvider.OPENAI_GPT4O
                )
                
                response = answer_gen.generate_answer(request, persona=persona)
                candidate_answers.append({
                    "level": level_name,
                    "content": response.answer_content
                })
            print(f"🤖 3가지 레벨 답변 생성 완료")
            
            # RAGAS evaluation
            ragas_result = evaluate_with_ragas(question, ground_truth, candidate_answers)
            print(f"🔍 RAGAS 평가 완료")
            
            # Prepare result data
            result_data = {
                "scenario": f"{company_name}_{position_name}_{role_name}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "company": company_name,
                "position": position_name,
                "interviewer_role": role_name,
                "persona_name": persona.name,
                "persona_experience": persona.background.get('career_years', '미정'),
                "persona_skills": ', '.join(persona.technical_skills[:5]),
                "question": question,
                "ground_truth": ground_truth,
                "beginner_answer": candidate_answers[0]["content"] if len(candidate_answers) > 0 else "",
                "intermediate_answer": candidate_answers[1]["content"] if len(candidate_answers) > 1 else "",
                "advanced_answer": candidate_answers[2]["content"] if len(candidate_answers) > 2 else "",
            }
            
            # Add RAGAS scores
            try:
                if not isinstance(ragas_result, dict) or "error" not in ragas_result:
                    # RAGAS 결과 구조 확인 및 점수 추출
                    scores = None
                    if hasattr(ragas_result, 'scores'):
                        scores = ragas_result.scores
                    elif hasattr(ragas_result, '__getitem__'):
                        try:
                            scores = dict(ragas_result)
                        except:
                            pass
                    elif isinstance(ragas_result, dict):
                        scores = ragas_result
                    
                    if scores and 'answer_relevancy' in scores and 'answer_correctness' in scores:
                        relevancy_list = scores['answer_relevancy']
                        correctness_list = scores['answer_correctness']
                        
                        result_data.update({
                            "beginner_relevancy": relevancy_list[0] if len(relevancy_list) > 0 else 0,
                            "beginner_correctness": correctness_list[0] if len(correctness_list) > 0 else 0,
                            "intermediate_relevancy": relevancy_list[1] if len(relevancy_list) > 1 else 0,
                            "intermediate_correctness": correctness_list[1] if len(correctness_list) > 1 else 0,
                            "advanced_relevancy": relevancy_list[2] if len(relevancy_list) > 2 else 0,
                            "advanced_correctness": correctness_list[2] if len(correctness_list) > 2 else 0,
                            "avg_relevancy": sum(relevancy_list) / len(relevancy_list) if relevancy_list else 0,
                            "avg_correctness": sum(correctness_list) / len(correctness_list) if correctness_list else 0,
                        })
                    else:
                        # 기본값 추가
                        result_data.update({
                            "beginner_relevancy": 0, "beginner_correctness": 0,
                            "intermediate_relevancy": 0, "intermediate_correctness": 0,
                            "advanced_relevancy": 0, "advanced_correctness": 0,
                            "avg_relevancy": 0, "avg_correctness": 0,
                        })
            except Exception as e:
                # 오류 발생 시 기본값 추가
                result_data.update({
                    "beginner_relevancy": 0, "beginner_correctness": 0,
                    "intermediate_relevancy": 0, "intermediate_correctness": 0,
                    "advanced_relevancy": 0, "advanced_correctness": 0,
                    "avg_relevancy": 0, "avg_correctness": 0,
                })
                
            all_results.append(result_data)
            print(f"✅ 시나리오 {i} 완료\n")
            
        except Exception as e:
            print(f"❌ 시나리오 {i} 실패: {e}\n")
            continue
    
    # Save all results to Excel
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_test/batch_test_results_{timestamp}.xlsx"
        
        try:
            df = pd.DataFrame(all_results)
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"🎉 배치 테스트 완료!")
            print(f"📊 총 {len(all_results)}개 시나리오 결과가 저장되었습니다: {filename}")
            return filename
        except Exception as e:
            print(f"❌ 배치 결과 저장 실패: {e}")
    
    return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        batch_test_scenarios()
    else:
        main()