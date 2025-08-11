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
import random
from datetime import datetime
from typing import Dict, List
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, answer_correctness
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    "1": ("backend", "백엔드"),                    # POSITION_MAPPING: "backend": 2
    "2": ("frontend", "프론트엔드"),                # POSITION_MAPPING: "frontend": 1  
    "3": ("ai", "AI/ML"),                         # POSITION_MAPPING: "ai": 4
    "4": ("데이터사이언스", "데이터사이언스"),        # POSITION_MAPPING: "데이터사이언스": 5 
    "5": ("기획", "기획")                         # POSITION_MAPPING: "기획": 3
}

INTERVIEWER_ROLES = {
    "1": ("HR", "인사"),
    "2": ("TECH", "기술"),
    "3": ("COLLABORATION", "협업")
}

def generate_ground_truth_answer(question: str, company_id: str, position: str, interviewer_role: str, persona_resume: Dict) -> str:
    """면접관 관점에서 페르소나 기반 모범답안 생성"""
    # API 키 확인
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return "모범답안 생성에 실패했습니다. (API Key 없음)"
    
    client = openai.OpenAI(api_key=openai_api_key)
    
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
    """RAGAS 라이브러리로 답변 평가 - ragas_rerun.py 방식 완전 적용"""
    try:
        from langchain_openai import ChatOpenAI
        
        # OpenAI API 키 확인
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return {"error": "OPENAI_API_KEY가 설정되지 않았습니다."}
        
        # OpenAI LLM 설정 (ragas_rerun.py와 동일)
        llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
        
        # 3개 답변 수집 (ragas_rerun.py와 동일한 유효성 검사)
        valid_answers = []
        for ans in candidate_answers:
            content = ans["content"]
            if content and str(content).strip() and not str(content).startswith("답변 생성에 실패"):
                valid_answers.append(str(content).strip())
            else:
                valid_answers.append("답변을 생성할 수 없습니다.")
        
        # RAGAS Dataset 생성 (ragas_rerun.py와 동일)
        data = {
            "question": [question] * 3,
            "contexts": [["면접 상황"]] * 3,
            "answer": valid_answers,
            "ground_truth": [ground_truth] * 3
        }
        
        dataset = Dataset.from_dict(data)
        
        # RAGAS 평가 실행 (ragas_rerun.py와 동일)
        result = evaluate(
            dataset,
            metrics=[answer_relevancy, answer_correctness],
            llm=llm
        )
        
        # 점수 추출 - ragas_rerun.py의 evaluate_single_row_with_ragas 함수와 동일한 로직
        scores = None
        
        # 방법 1: scores 속성 접근
        if hasattr(result, 'scores'):
            scores = result.scores
        # 방법 2: dict 변환 시도  
        elif hasattr(result, '__getitem__'):
            try:
                scores = dict(result)
            except:
                pass
        # 방법 3: 직접 할당
        else:
            scores = result
        
        # RAGAS 결과가 list 형태인 경우 처리 (ragas_rerun.py에서 추가된 로직)
        if scores is not None and isinstance(scores, list) and len(scores) >= 3:
            # 각 답변별 점수 추출
            beginner_scores = scores[0]
            intermediate_scores = scores[1] 
            advanced_scores = scores[2]
            
            # 점수 값 추출
            beginner_rel = beginner_scores.get('answer_relevancy', 0)
            beginner_cor = beginner_scores.get('answer_correctness', 0)
            intermediate_rel = intermediate_scores.get('answer_relevancy', 0)
            intermediate_cor = intermediate_scores.get('answer_correctness', 0)
            advanced_rel = advanced_scores.get('answer_relevancy', 0)
            advanced_cor = advanced_scores.get('answer_correctness', 0)
            
            return {
                'answer_relevancy': [beginner_rel, intermediate_rel, advanced_rel],
                'answer_correctness': [beginner_cor, intermediate_cor, advanced_cor],
                'success': True
            }
        
        # scores가 dictionary인 경우 (ragas_rerun.py 기존 방식)
        elif scores is not None and hasattr(scores, 'keys') and 'answer_relevancy' in scores and 'answer_correctness' in scores:
            relevancy_list = scores['answer_relevancy'] 
            correctness_list = scores['answer_correctness']
            
            # 리스트가 아닌 경우 처리
            if not isinstance(relevancy_list, list):
                relevancy_list = [relevancy_list] if relevancy_list is not None else [0, 0, 0]
            if not isinstance(correctness_list, list):
                correctness_list = [correctness_list] if correctness_list is not None else [0, 0, 0]
            
            # 길이가 3이 아닌 경우 처리
            while len(relevancy_list) < 3:
                relevancy_list.append(0)
            while len(correctness_list) < 3:
                correctness_list.append(0)
            
            return {
                'answer_relevancy': relevancy_list[:3],
                'answer_correctness': correctness_list[:3],
                'success': True
            }
        else:
            # 디버깅 정보 제공 (ragas_rerun.py와 동일)
            if scores is not None:
                if hasattr(scores, 'keys'):
                    available_keys = list(scores.keys())
                    error_msg = f"Missing expected keys. Available keys: {available_keys}"
                else:
                    error_msg = f"Scores is not dict-like. Type: {type(scores)}, Content: {scores}"
            else:
                error_msg = "Scores is None"
            
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

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
    
    # API 키 확인
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에서 OPENAI_API_KEY를 설정해주세요.")
        return
    
    # Initialize models
    print("\n🔧 모델 초기화 중...")
    try:
        question_gen = QuestionGenerator()
        answer_gen = AICandidateModel()
        print("✅ 모델 초기화 완료")
        
        # 실제 DB에서 로딩된 회사 목록 확인 및 출력
        print(f"\n🔍 실제 로딩된 회사 목록: {list(question_gen.companies_data.keys())}")
        
        # 사용 가능한 첫 번째 회사로 강제 변경
        if question_gen.companies_data:
            available_company_id = list(question_gen.companies_data.keys())[0]
            if company_id not in question_gen.companies_data:
                print(f"⚠️  회사를 {company_id}에서 {available_company_id}로 변경합니다.")
                company_id = available_company_id
                company_name = question_gen.companies_data[company_id].get('name', company_id)
        else:
            print("❌ DB에서 회사 데이터를 로딩하지 못했습니다.")
            return
            
    except Exception as e:
        print(f"❌ 모델 초기화 실패: {e}")
        return
    
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
    try:
        question_result = question_gen.generate_question_by_role(
            interviewer_role=interviewer_role,
            company_id=company_id, 
            user_resume=resume_data  # Use actual persona data instead of placeholder
        )
        question = question_result['question']
        question_source = question_result.get('question_source', 'unknown')
        
        print(f"\n📝 Generated Question (Source: {question_source}):")
        print(f"{question}")
        
        # 질문이 제대로 생성되었는지 확인
        if not question or len(question.strip()) < 10:
            raise ValueError("질문이 너무 짧거나 비어있습니다.")
            
    except Exception as e:
        print(f"❌ 질문 생성 실패: {e}")
        # 기본 질문으로 대체
        question = f"{company_name} {position_name} 직군에 지원한 이유와 본인의 강점을 설명해주세요."
        print(f"📝 기본 질문 사용: {question}")
    
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
    
    # RAGAS 결과 처리 - 개선된 버전
    try:
        if isinstance(ragas_result, dict) and "error" in ragas_result:
            print(f"\n❌ RAGAS 평가 오류: {ragas_result['error']}")
        elif ragas_result.get('success', True):  # success 키가 있으면 체크, 없으면 True로 간주
            print(f"\n📊 RAGAS 평가 결과:")
            print("=" * 50)
            
            # RAGAS 결과에서 점수 추출
            try:
                relevancy_scores = ragas_result['answer_relevancy']
                correctness_scores = ragas_result['answer_correctness']
                
                # Display results for each answer
                level_names = ["🔰 초급", "🔸 중급", "🔥 고급"]
                for i, (ans, level_name) in enumerate(zip(candidate_answers, level_names)):
                    if i < len(relevancy_scores) and i < len(correctness_scores):
                        relevancy = relevancy_scores[i]
                        correctness = correctness_scores[i]
                        combined = (relevancy + correctness) / 2
                        
                        print(f"\n{level_name} 평가:")
                        print(f"  • Answer Relevancy: {relevancy:.3f}")
                        print(f"  • Answer Correctness: {correctness:.3f}")  
                        print(f"  • 종합 점수: {combined:.3f}")
                    
                # 평균 점수 계산
                if relevancy_scores and correctness_scores:
                    avg_relevancy = sum(relevancy_scores) / len(relevancy_scores)
                    avg_correctness = sum(correctness_scores) / len(correctness_scores)
                    overall_avg = (avg_relevancy + avg_correctness) / 2
                    
                    print(f"\n📈 평균 점수:")
                    print(f"  • Answer Relevancy: {avg_relevancy:.3f}")
                    print(f"  • Answer Correctness: {avg_correctness:.3f}")
                    print(f"  • 전체 평균: {overall_avg:.3f}")
                
            except Exception as score_error:
                print(f"\n❌ 점수 추출 오류: {score_error}")
                print(f"  📊 RAGAS 점수 (원본 결과):")
                print(f"     결과 타입: {type(ragas_result)}")
                print(f"     결과 내용: {ragas_result}")
        else:
            print(f"\n❌ RAGAS 평가 실패: {ragas_result.get('error', 'Unknown error')}")
                
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
    
    # Add RAGAS scores if available - 개선된 버전
    try:
        if isinstance(ragas_result, dict) and "error" in ragas_result:
            print(f"⚠️ RAGAS 평가 실패로 기본 점수 사용")
            # 기본값 추가
            test_data.update({
                "beginner_relevancy": 0, "beginner_correctness": 0,
                "intermediate_relevancy": 0, "intermediate_correctness": 0, 
                "advanced_relevancy": 0, "advanced_correctness": 0,
                "avg_relevancy": 0, "avg_correctness": 0,
                "ragas_error": ragas_result["error"]
            })
        elif ragas_result.get('success', True):
            print(f"🔍 RAGAS 점수 Excel 저장 중...")
            
            # 점수 추출
            relevancy_list = ragas_result.get('answer_relevancy', [0, 0, 0])
            correctness_list = ragas_result.get('answer_correctness', [0, 0, 0])
            
            # 안전한 인덱스 접근
            beginner_rel = relevancy_list[0] if len(relevancy_list) > 0 else 0
            beginner_cor = correctness_list[0] if len(correctness_list) > 0 else 0
            intermediate_rel = relevancy_list[1] if len(relevancy_list) > 1 else 0
            intermediate_cor = correctness_list[1] if len(correctness_list) > 1 else 0
            advanced_rel = relevancy_list[2] if len(relevancy_list) > 2 else 0
            advanced_cor = correctness_list[2] if len(correctness_list) > 2 else 0
            
            test_data.update({
                "beginner_relevancy": beginner_rel,
                "beginner_correctness": beginner_cor,
                "intermediate_relevancy": intermediate_rel,
                "intermediate_correctness": intermediate_cor,
                "advanced_relevancy": advanced_rel,
                "advanced_correctness": advanced_cor,
                "avg_relevancy": sum(relevancy_list) / len(relevancy_list) if relevancy_list else 0,
                "avg_correctness": sum(correctness_list) / len(correctness_list) if correctness_list else 0,
            })
            print(f"✅ RAGAS 점수 추가 완료")
        else:
            print(f"⚠️ RAGAS 평가 실패 - 기본값 사용")
            # 기본값 추가
            test_data.update({
                "beginner_relevancy": 0, "beginner_correctness": 0,
                "intermediate_relevancy": 0, "intermediate_correctness": 0, 
                "advanced_relevancy": 0, "advanced_correctness": 0,
                "avg_relevancy": 0, "avg_correctness": 0,
                "ragas_error": ragas_result.get('error', 'Unknown RAGAS error')
            })
            
    except Exception as score_error:
        print(f"⚠️ 점수 추가 중 오류: {score_error}")
        # 오류 발생 시 기본값 추가
        test_data.update({
            "beginner_relevancy": 0, "beginner_correctness": 0,
            "intermediate_relevancy": 0, "intermediate_correctness": 0,
            "advanced_relevancy": 0, "advanced_correctness": 0, 
            "avg_relevancy": 0, "avg_correctness": 0,
            "score_extraction_error": str(score_error)
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
    
    # Test scenarios - 5개 직군만 사용, 영문 company_id 사용
    scenarios = [
        ("naver", "네이버", "backend", "백엔드", "TECH", "기술"),
        ("kakao", "카카오", "frontend", "프론트엔드", "HR", "인사"),
        ("toss", "토스", "ai", "AI/ML", "TECH", "기술"),
        ("coupang", "쿠팡", "데이터사이언스", "데이터사이언스", "COLLABORATION", "협업"),
        ("baemin", "배달의민족", "기획", "기획", "HR", "인사"),
    ]
    
    all_results = []
    
    for i, (company_id, company_name, position, position_name, interviewer_role, role_name) in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] 테스트 중: {company_name} {position_name} {role_name} 면접")
        print("-" * 50)
        
        try:
            # API 키 확인
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
                continue
            
            # Initialize models
            try:
                question_gen = QuestionGenerator()
                answer_gen = AICandidateModel()
                
                # 실제 DB에서 로딩된 회사 목록 확인 및 강제 변경
                if question_gen.companies_data:
                    available_company_id = list(question_gen.companies_data.keys())[0]
                    if company_id not in question_gen.companies_data:
                        print(f"⚠️  회사를 {company_id}에서 {available_company_id}로 변경")
                        company_id = available_company_id
                        company_name = question_gen.companies_data[company_id].get('name', company_id)
                else:
                    print("❌ DB에서 회사 데이터 로딩 실패")
                    continue
                    
            except Exception as init_error:
                print(f"❌ 모델 초기화 실패: {init_error}")
                continue
            
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
            try:
                question_result = question_gen.generate_question_by_role(
                    interviewer_role=interviewer_role,
                    company_id=company_id, 
                    user_resume=resume_data
                )
                question = question_result['question']
                question_source = question_result.get('question_source', 'unknown')
                
                # 질문 검증
                if not question or len(question.strip()) < 10:
                    raise ValueError("질문이 너무 짧거나 비어있습니다.")
                    
                print(f"📝 질문 생성 완료 (Source: {question_source})")
            except Exception as question_error:
                print(f"❌ 질문 생성 실패: {question_error}")
                # 기본 질문으로 대체
                question = f"{company_name} {position_name} 직군에 지원한 이유와 본인의 강점을 설명해주세요."
                print(f"📝 기본 질문 사용")
            
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
            
            # Add RAGAS scores - 개선된 버전
            try:
                if isinstance(ragas_result, dict) and "error" in ragas_result:
                    # 기본값 추가
                    result_data.update({
                        "beginner_relevancy": 0, "beginner_correctness": 0,
                        "intermediate_relevancy": 0, "intermediate_correctness": 0,
                        "advanced_relevancy": 0, "advanced_correctness": 0,
                        "avg_relevancy": 0, "avg_correctness": 0,
                        "ragas_error": ragas_result["error"]
                    })
                elif ragas_result.get('success', True):
                    # 점수 추출
                    relevancy_list = ragas_result.get('answer_relevancy', [0, 0, 0])
                    correctness_list = ragas_result.get('answer_correctness', [0, 0, 0])
                    
                    # 안전한 인덱스 접근
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
                        "ragas_error": ragas_result.get('error', 'Unknown RAGAS error')
                    })
            except Exception as e:
                # 오류 발생 시 기본값 추가
                result_data.update({
                    "beginner_relevancy": 0, "beginner_correctness": 0,
                    "intermediate_relevancy": 0, "intermediate_correctness": 0,
                    "advanced_relevancy": 0, "advanced_correctness": 0,
                    "avg_relevancy": 0, "avg_correctness": 0,
                    "score_extraction_error": str(e)
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

def random_batch_test(num_tests: int = 100):
    """무작위 회사와 직군으로 N번 테스트하여 평균 점수 계산"""
    print(f"🎲 무작위 배치 테스트 모드 - {num_tests}번 실행")
    print("=" * 60)
    
    # 회사와 직군 리스트
    companies = list(COMPANIES.values())
    positions = list(POSITIONS.values()) 
    interviewer_roles = list(INTERVIEWER_ROLES.values())
    
    all_results = []  # 개별 테스트 결과 저장용
    all_scores = {
        'relevancy_beginner': [],
        'relevancy_intermediate': [],
        'relevancy_advanced': [],
        'correctness_beginner': [],
        'correctness_intermediate': [],
        'correctness_advanced': [],
        'overall_scores': []
    }
    
    successful_tests = 0
    failed_tests = 0
    
    # 베스트 케이스 저장용
    best_case = {
        'score': -1,
        'test_num': 0,
        'company_name': '',
        'position_name': '', 
        'role_name': '',
        'question': '',
        'ground_truth': '',
        'candidate_answers': [],
        'scores': {}
    }
    
    # tqdm 진행률 표시
    progress_bar = tqdm(range(1, num_tests + 1), desc="테스트 진행", unit="test")
    
    for test_num in progress_bar:
        # 무작위 선택 - 한글 회사명 사용
        company_id, company_name = random.choice(companies)
        position, position_name = random.choice(positions)
        interviewer_role, role_name = random.choice(interviewer_roles)
        
        # tqdm에 현재 상태 업데이트
        progress_bar.set_postfix({
            '현재': f"{company_name} {position_name} {role_name}",
            '성공': successful_tests,
            '실패': failed_tests
        })
        
        try:
            # API 키 확인
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                progress_bar.write(f"[ERROR] OPENAI_API_KEY가 설정되지 않았습니다.")
                failed_tests += 1
                continue
            
            # Initialize models
            try:
                question_gen = QuestionGenerator()
                answer_gen = AICandidateModel()
                progress_bar.write(f"[DEBUG] 모델 초기화 완료")
                
                # 실제 DB에서 로딩된 회사 목록 확인 및 강제 변경
                if question_gen.companies_data:
                    available_company_id = list(question_gen.companies_data.keys())[0]
                    if company_id not in question_gen.companies_data:
                        progress_bar.write(f"[DEBUG] 회사 변경: {company_id} -> {available_company_id}")
                        company_id = available_company_id
                        company_name = question_gen.companies_data[company_id].get('name', company_id)
                else:
                    progress_bar.write(f"[ERROR] DB 회사 데이터 없음")
                    failed_tests += 1
                    continue
                    
            except Exception as init_error:
                progress_bar.write(f"[ERROR] 모델 초기화 실패: {init_error}")
                failed_tests += 1
                continue
            
            # Create persona
            try:
                # 디버깅: 정확한 매핑 확인
                progress_bar.write(f"[DEBUG] 페르소나 생성 시도: company_id='{company_id}', position='{position}'")
                
                persona = answer_gen.create_persona_for_interview(company_id, position)
                if not persona:
                    progress_bar.write(f"[WARNING] 페르소나 생성 실패, 기본 페르소나 생성 중...")
                    persona = answer_gen._create_default_persona(company_id, position)
                progress_bar.write(f"[DEBUG] 페르소나 생성 완료: {persona.name}")
            except Exception as persona_error:
                progress_bar.write(f"[ERROR] 페르소나 생성 실패: {persona_error}")
                # 완전한 기본 페르소나 생성
                persona = answer_gen._create_default_persona(company_id, position)
            
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
            try:
                progress_bar.write(f"[DEBUG] 질문 생성 시도: role='{interviewer_role}', company='{company_id}'")
                question_result = question_gen.generate_question_by_role(
                    interviewer_role=interviewer_role,
                    company_id=company_id, 
                    user_resume=resume_data
                )
                question = question_result['question']
                question_source = question_result.get('question_source', 'unknown')
                progress_bar.write(f"[DEBUG] 질문 생성 완료: source='{question_source}'")
                progress_bar.write(f"[DEBUG] 질문 내용: {question[:100]}...")
            except Exception as question_error:
                progress_bar.write(f"[ERROR] 질문 생성 실패: {question_error}")
                raise
            
            # Generate ground truth
            ground_truth = generate_ground_truth_answer(question, company_id, position, interviewer_role, persona_resume=resume_data)
            
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
            
            # RAGAS evaluation
            try:
                ragas_result = evaluate_with_ragas(question, ground_truth, candidate_answers)
                progress_bar.write(f"[DEBUG] RAGAS 결과 타입: {type(ragas_result)}")
                progress_bar.write(f"[DEBUG] RAGAS 결과: {ragas_result}")
            except Exception as ragas_error:
                progress_bar.write(f"[ERROR] RAGAS 평가 실패: {ragas_error}")
                ragas_result = {"error": str(ragas_error)}
            
            # Extract scores - 개선된 버전
            scores_extracted = False
            if isinstance(ragas_result, dict) and "error" in ragas_result:
                progress_bar.write(f"[DEBUG] RAGAS 평가 실패: {ragas_result['error']}")
                scores_extracted = False
            elif ragas_result.get('success', True):
                # 점수 추출
                relevancy_list = ragas_result.get('answer_relevancy', [0, 0, 0])
                correctness_list = ragas_result.get('answer_correctness', [0, 0, 0])
                
                progress_bar.write(f"[DEBUG] 점수 추출: relevancy={relevancy_list}, correctness={correctness_list}")
                
                if len(relevancy_list) >= 3 and len(correctness_list) >= 3:
                    # 개별 레벨별 점수 저장
                    all_scores['relevancy_beginner'].append(relevancy_list[0])
                    all_scores['relevancy_intermediate'].append(relevancy_list[1])
                    all_scores['relevancy_advanced'].append(relevancy_list[2])
                    all_scores['correctness_beginner'].append(correctness_list[0])
                    all_scores['correctness_intermediate'].append(correctness_list[1])
                    all_scores['correctness_advanced'].append(correctness_list[2])
                    
                    # 전체 평균 점수 계산
                    overall_avg = (sum(relevancy_list) + sum(correctness_list)) / (2 * len(relevancy_list))
                    all_scores['overall_scores'].append(overall_avg)
                    
                    # 레벨별 종합 점수 계산 (relevancy + correctness)
                    beginner_score = (relevancy_list[0] + correctness_list[0]) / 2
                    intermediate_score = (relevancy_list[1] + correctness_list[1]) / 2 
                    advanced_score = (relevancy_list[2] + correctness_list[2]) / 2
                    
                    # 개별 테스트 결과 저장
                    test_result = {
                        'test_num': test_num,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'company': company_name,
                        'position': position_name,
                        'interviewer_role': role_name,
                        'question': question,
                        'ground_truth': ground_truth,
                        'beginner_answer': candidate_answers[0]['content'],
                        'intermediate_answer': candidate_answers[1]['content'],
                        'advanced_answer': candidate_answers[2]['content'],
                        'beginner_relevancy': relevancy_list[0],
                        'beginner_correctness': correctness_list[0],
                        'intermediate_relevancy': relevancy_list[1],
                        'intermediate_correctness': correctness_list[1],
                        'advanced_relevancy': relevancy_list[2],
                        'advanced_correctness': correctness_list[2],
                        'avg_relevancy': sum(relevancy_list) / len(relevancy_list),
                        'avg_correctness': sum(correctness_list) / len(correctness_list)
                    }
                    all_results.append(test_result)
                    
                    # 베스트 케이스 판별 (평균 점수가 높고, 초급 < 중급 < 고급 순서인 경우)
                    is_progressive = beginner_score < intermediate_score < advanced_score
                    if overall_avg > best_case['score'] and is_progressive:
                        best_case.update({
                            'score': overall_avg,
                            'test_num': test_num,
                            'company_name': company_name,
                            'position_name': position_name,
                            'role_name': role_name,
                            'question': question,
                            'ground_truth': ground_truth,
                            'candidate_answers': candidate_answers.copy(),
                            'scores': {
                                'beginner': beginner_score,
                                'intermediate': intermediate_score, 
                                'advanced': advanced_score,
                                'relevancy': relevancy_list.copy(),
                                'correctness': correctness_list.copy()
                            }
                        })
                        
                    scores_extracted = True
                else:
                    progress_bar.write(f"[DEBUG] 점수 배열 길이 부족: relevancy={len(relevancy_list)}, correctness={len(correctness_list)}")
            else:
                progress_bar.write(f"[DEBUG] RAGAS 평가 실패: {ragas_result.get('error', 'Unknown error')}")
            
            if scores_extracted:
                successful_tests += 1
            else:
                failed_tests += 1
                
        except Exception as e:
            failed_tests += 1
            continue
        
        # tqdm 상태 업데이트
        progress_bar.set_postfix({
            '현재': f"{company_name} {position_name} {role_name}",
            '성공': successful_tests,
            '실패': failed_tests
        })
    
    # 결과 계산 및 출력
    print(f"\n📊 무작위 배치 테스트 결과")
    print("=" * 60)
    print(f"총 테스트: {num_tests}개")
    print(f"성공: {successful_tests}개")
    print(f"실패: {failed_tests}개")
    print(f"성공률: {(successful_tests/num_tests*100):.1f}%")
    
    if successful_tests > 0:
        print(f"\n📈 평균 점수 (성공한 {successful_tests}개 테스트 기준):")
        print("-" * 40)
        
        # 레벨별 평균 점수
        avg_relevancy_beginner = sum(all_scores['relevancy_beginner']) / len(all_scores['relevancy_beginner'])
        avg_relevancy_intermediate = sum(all_scores['relevancy_intermediate']) / len(all_scores['relevancy_intermediate'])
        avg_relevancy_advanced = sum(all_scores['relevancy_advanced']) / len(all_scores['relevancy_advanced'])
        
        avg_correctness_beginner = sum(all_scores['correctness_beginner']) / len(all_scores['correctness_beginner'])
        avg_correctness_intermediate = sum(all_scores['correctness_intermediate']) / len(all_scores['correctness_intermediate'])
        avg_correctness_advanced = sum(all_scores['correctness_advanced']) / len(all_scores['correctness_advanced'])
        
        print("🔰 초급 레벨:")
        print(f"  • Answer Relevancy: {avg_relevancy_beginner:.3f}")
        print(f"  • Answer Correctness: {avg_correctness_beginner:.3f}")
        print(f"  • 레벨 평균: {(avg_relevancy_beginner + avg_correctness_beginner) / 2:.3f}")
        
        print("\n🔸 중급 레벨:")
        print(f"  • Answer Relevancy: {avg_relevancy_intermediate:.3f}")
        print(f"  • Answer Correctness: {avg_correctness_intermediate:.3f}")
        print(f"  • 레벨 평균: {(avg_relevancy_intermediate + avg_correctness_intermediate) / 2:.3f}")
        
        print("\n🔥 고급 레벨:")
        print(f"  • Answer Relevancy: {avg_relevancy_advanced:.3f}")
        print(f"  • Answer Correctness: {avg_correctness_advanced:.3f}")
        print(f"  • 레벨 평균: {(avg_relevancy_advanced + avg_correctness_advanced) / 2:.3f}")
        
        # 전체 평균
        overall_relevancy = (avg_relevancy_beginner + avg_relevancy_intermediate + avg_relevancy_advanced) / 3
        overall_correctness = (avg_correctness_beginner + avg_correctness_intermediate + avg_correctness_advanced) / 3
        overall_average = sum(all_scores['overall_scores']) / len(all_scores['overall_scores'])
        
        print(f"\n🎯 전체 평균:")
        print(f"  • Answer Relevancy: {overall_relevancy:.3f}")
        print(f"  • Answer Correctness: {overall_correctness:.3f}")
        print(f"  • 최종 평균 점수: {overall_average:.3f}")
        
        # 결과를 Excel에 저장 (baseline과 동일한 형태)
        summary_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_tests': num_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': successful_tests/num_tests*100,
            # baseline 형태로 컬럼명 변경
            'beginner_relevancy': avg_relevancy_beginner,
            'beginner_correctness': avg_correctness_beginner,
            'intermediate_relevancy': avg_relevancy_intermediate,
            'intermediate_correctness': avg_correctness_intermediate,
            'advanced_relevancy': avg_relevancy_advanced,
            'advanced_correctness': avg_correctness_advanced,
            'avg_relevancy': overall_relevancy,
            'avg_correctness': overall_correctness,
            'final_average_score': overall_average
        }
        
        # 베스트 케이스 출력
        if best_case['score'] > -1:
            print(f"\n{'='*80}")
            print(f"🏆 베스트 케이스 예시 (#{best_case['test_num']}: {best_case['company_name']} {best_case['position_name']} {best_case['role_name']} 면접)")
            print(f"   전체 평균 점수: {best_case['score']:.3f}")
            print(f"{'='*80}")
            
            print(f"❓ 질문:")
            print(f"{best_case['question']}")
            
            print(f"\n🎯 모범답안:")
            print(f"{best_case['ground_truth']}")
            
            print(f"\n🤖 AI 답변 및 점수:")
            print("-" * 80)
            
            level_names = ["🔰 초급", "🔸 중급", "🔥 고급"]
            level_keys = ["beginner", "intermediate", "advanced"]
            
            for i, (level_name, level_key) in enumerate(zip(level_names, level_keys)):
                answer = best_case['candidate_answers'][i]['content']
                score = best_case['scores'][level_key]
                relevancy = best_case['scores']['relevancy'][i]
                correctness = best_case['scores']['correctness'][i]
                
                print(f"{level_name} (종합: {score:.3f}):")
                print(f"  📊 Answer Relevancy: {relevancy:.3f} | Answer Correctness: {correctness:.3f}")
                print(f"  💬 답변: {answer}")
                
                if i < len(level_names) - 1:
                    print("-" * 60)
            
            print(f"{'='*80}")
        else:
            print(f"\n⚠️  베스트 케이스를 찾을 수 없었습니다. (초급 < 중급 < 고급 순서의 케이스 없음)")

        # Excel 파일 저장 (baseline과 동일한 형태로 모든 개별 테스트 결과)
        if all_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"model_test/new_model_ragas_results_{timestamp}.xlsx"
            
            try:
                # 모든 개별 테스트 결과를 DataFrame으로 변환
                results_df = pd.DataFrame(all_results)
                results_df.to_excel(filename, index=False, engine='openpyxl')
                print(f"\n💾 상세 결과 저장: {filename}")
                print(f"   📊 {len(all_results)}개 개별 테스트 결과 저장 완료")
                
                # 요약 통계도 별도로 출력
                print(f"\n📈 저장된 데이터 요약:")
                print(f"   - 성공한 테스트: {len(all_results)}개")
                print(f"   - 평균 Relevancy: {results_df['avg_relevancy'].mean():.3f}")
                print(f"   - 평균 Correctness: {results_df['avg_correctness'].mean():.3f}")
                
            except Exception as e:
                print(f"❌ 결과 저장 실패: {e}")
        else:
            print(f"\n⚠️ 저장할 유효한 결과가 없습니다.")
    
    else:
        print("\n❌ 성공한 테스트가 없어 평균을 계산할 수 없습니다.")
    
    return successful_tests, failed_tests, all_scores if successful_tests > 0 else None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--batch":
            batch_test_scenarios()
        elif sys.argv[1] == "--random":
            # 기본 100번, 원하는 수를 지정할 수 있음
            num_tests = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            random_batch_test(num_tests)
        else:
            print("사용법:")
            print("  python candidate_model_test.py              # 단일 테스트")
            print("  python candidate_model_test.py --batch      # 5개 시나리오 배치 테스트")
            print("  python candidate_model_test.py --random     # 100번 무작위 테스트")
            print("  python candidate_model_test.py --random 50  # 50번 무작위 테스트")
    else:
        main()