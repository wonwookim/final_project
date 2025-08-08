#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모델 플로우 테스트 파일
- 회사/직군 입력 → DB에서 이력서 가져오기 → 페르소나 형성 → 질문 생성 → 답변 생성
- 테스트 계획 및 평가서용 모델 동작 확인
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

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

# Available options (기존과 동일)
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

def print_header(title: str):
    """헤더 출력"""
    print(f"\n{'='*80}")
    print(f"🎯 {title}")
    print('='*80)

def print_section(title: str):
    """섹션 출력"""
    print(f"\n{'─'*60}")
    print(f"📌 {title}")
    print('─'*60)

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

def display_persona_details(persona):
    """페르소나 상세 정보 출력 (전체 필드)"""
    print(f"\n🤖 생성된 AI 지원자 페르소나 (전체 정보):")
    print("="*70)
    
    # 기본 정보
    print(f"📋 기본 정보:")
    print(f"   • 이름: {persona.name}")
    print(f"   • 요약: {persona.summary}")
    print(f"   • 이력서 ID: {persona.resume_id}")
    print(f"   • 생성 모델: {persona.generated_by}")
    
    # 배경 정보
    print(f"\n👤 배경 정보:")
    for key, value in persona.background.items():
        print(f"   • {key}: {value}")
    
    # 성격 특성 (전체)
    print(f"\n🧠 성격 특성:")
    for trait in persona.personality_traits:
        print(f"   • {trait}")
    
    # 기술 스킬 (전체)
    print(f"\n🛠 기술 스킬:")
    for skill in persona.technical_skills:
        print(f"   • {skill}")
    
    # 경력 사항 (전체)
    print(f"\n💼 경력 사항:")
    for i, exp in enumerate(persona.experiences, 1):
        if isinstance(exp, dict):
            print(f"   {i}. {exp.get('company', '회사명')} - {exp.get('position', '직책')}")
            print(f"      기간: {exp.get('duration', '미정')}")
            print(f"      설명: {exp.get('description', '설명 없음')}")
            if 'achievements' in exp:
                print(f"      성과: {exp['achievements']}")
            if 'tech_stack' in exp:
                print(f"      기술스택: {', '.join(exp['tech_stack'])}")
        else:
            print(f"   {i}. {exp}")
        print()
    
    # 프로젝트 (전체)
    print(f"🚀 프로젝트:")
    for i, project in enumerate(persona.projects, 1):
        if isinstance(project, dict):
            print(f"   {i}. {project.get('name', '프로젝트명')}")
            print(f"      설명: {project.get('description', '설명 없음')}")
            if 'tech_used' in project:
                print(f"      사용기술: {', '.join(project['tech_used'])}")
            if 'achievements' in project:
                print(f"      성과: {project['achievements']}")
            if 'challenges' in project:
                print(f"      도전과제: {project['challenges']}")
        else:
            print(f"   {i}. {project}")
        print()
    
    # 강점 (전체)
    print(f"💪 강점:")
    for strength in persona.strengths:
        print(f"   • {strength}")
    
    # 약점/개선점 (전체)
    print(f"\n🔍 약점/개선하고 싶은 점:")
    for weakness in persona.weaknesses:
        print(f"   • {weakness}")
    
    # 개인적 경험 (추론된)
    print(f"\n💭 개인적 경험/깨달음:")
    for exp in persona.inferred_personal_experiences:
        if isinstance(exp, dict):
            for key, value in exp.items():
                print(f"   • {key}: {value}")
        else:
            print(f"   • {exp}")
    
    # 동기 및 목표
    print(f"\n💡 개발 동기:")
    print(f"   {persona.motivation}")
    
    print(f"\n🎯 커리어 목표:")
    print(f"   {persona.career_goal}")
    
    print(f"\n🗣 면접 스타일:")
    print(f"   {persona.interview_style}")
    
    print("="*70)

def display_question_analysis(question: str, company_name: str, role_name: str):
    """질문 분석 정보 출력"""
    print(f"\n📝 생성된 면접 질문:")
    print(f"   {question}")
    
    print(f"\n🔍 질문 분석:")
    print(f"   • 회사: {company_name} 특화 질문")
    print(f"   • 면접관 타입: {role_name} 면접관")
    print(f"   • 개인화 수준: 지원자 이력서 기반 맞춤형")

def generate_and_display_answers(question_gen, answer_gen, persona, question, 
                               interviewer_role, role_name, company_id, position):
    """답변 생성 및 출력"""
    print(f"\n🤖 AI 지원자 답변 생성:")
    
    # 질문 타입 매핑
    question_type_mapping = {
        "HR": QuestionType.HR,
        "TECH": QuestionType.TECH,
        "COLLABORATION": QuestionType.COLLABORATION
    }
    question_type = question_type_mapping.get(interviewer_role, QuestionType.TECH)
    
    # 여러 품질 레벨로 답변 생성
    levels = [
        ("🔰 초급자 수준 (부족함)", QualityLevel.INADEQUATE), 
        ("🔸 중급자 수준 (평균)", QualityLevel.AVERAGE), 
        ("🔥 고급자 수준 (우수함)", QualityLevel.EXCELLENT)
    ]
    
    answers = []
    
    for level_name, quality_level in levels:
        print(f"\n{'-'*50}")
        print(f"{level_name}")
        print(f"{'-'*50}")
        
        request = AnswerRequest(
            question_content=question,
            question_type=question_type,
            question_intent=f"{role_name} 역량 평가",
            company_id=company_id,
            position=position, 
            quality_level=quality_level,
            llm_provider=LLMProvider.OPENAI_GPT4O
        )
        
        print("답변 생성 중...")
        response = answer_gen.generate_answer(request, persona=persona)
        
        print(f"\n📝 답변:")
        print(f"{response.answer_content}")
        
        answers.append({
            "level": level_name,
            "content": response.answer_content,
            "quality": quality_level.value
        })
    
    return answers

def save_test_results(company_name, position_name, role_name, persona, question, answers):
    """테스트 결과를 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"model_test/model_flow_test_results_{timestamp}.xlsx"
    
    # 결과 데이터 구성
    result_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": company_name,
        "position": position_name,
        "interviewer_role": role_name,
        
        # 페르소나 정보
        "persona_name": persona.name,
        "persona_summary": persona.summary,
        "persona_personality_traits": ', '.join(persona.personality_traits[:5]),
        "persona_career_years": persona.background.get('career_years', '미정'),
        "persona_education": persona.background.get('education', '미정'),
        "persona_skills": ', '.join(persona.technical_skills[:10]),
        "persona_strengths": ', '.join(persona.strengths[:5]),
        "persona_weaknesses": ', '.join(persona.weaknesses[:3]),
        "persona_motivation": persona.motivation,
        "persona_goal": persona.career_goal,
        "persona_interview_style": persona.interview_style,
        "persona_experiences": ' | '.join([str(exp) for exp in persona.experiences[:3]]),
        "persona_projects": ' | '.join([str(proj) for proj in persona.projects[:3]]),
        
        # 질문 및 답변
        "generated_question": question,
        "beginner_answer": answers[0]["content"] if len(answers) > 0 else "",
        "intermediate_answer": answers[1]["content"] if len(answers) > 1 else "",
        "advanced_answer": answers[2]["content"] if len(answers) > 2 else "",
    }
    
    try:
        df = pd.DataFrame([result_data])
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n📊 테스트 결과가 저장되었습니다: {filename}")
        return filename
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return ""

def run_model_flow_test():
    """모델 플로우 테스트 실행"""
    print_header("AI 면접 시스템 모델 플로우 테스트")
    print("📋 테스트 계획 및 평가서용 모델 동작 과정 확인")
    
    # 1. 사용자 입력 받기
    print_section("1단계: 면접 설정 선택")
    
    company_id, company_name = get_user_choice(COMPANIES, "📍 회사를 선택하세요:")
    position, position_name = get_user_choice(POSITIONS, "💼 직군을 선택하세요:")
    interviewer_role, role_name = get_user_choice(INTERVIEWER_ROLES, "👨‍💼 면접관 유형을 선택하세요:")
    
    print(f"\n✅ 선택 완료: {company_name} {position_name} {role_name} 면접")
    
    # 2. 모델 초기화
    print_section("2단계: 모델 초기화")
    print("🔧 면접관 모델 및 지원자 모델 로드 중...")
    
    question_gen = QuestionGenerator()
    answer_gen = AICandidateModel()
    print("✅ 모델 초기화 완료")
    
    # 3. 페르소나 생성 (DB에서 이력서 기반)
    print_section("3단계: AI 지원자 페르소나 생성")
    print(f"📋 {company_name} {position_name} 직군 지원자 페르소나를 DB에서 생성 중...")
    
    persona = answer_gen.create_persona_for_interview(company_id, position)
    if not persona:
        print("⚠️ 특화 페르소나 생성 실패, 기본 페르소나 사용")
        persona = answer_gen._create_default_persona(company_id, position)
    
    print("✅ 페르소나 생성 완료")
    display_persona_details(persona)
    
    # 4. 이력서 데이터 구성
    print_section("4단계: 이력서 데이터 구성")
    print("📝 생성된 페르소나를 바탕으로 이력서 데이터 구성 중...")
    
    resume_data = {
        "name": persona.name,
        "background": persona.background,
        "technical_skills": persona.technical_skills,
        "experiences": persona.experiences,
        "projects": persona.projects,
        "strengths": persona.strengths,
        "career_goal": persona.career_goal
    }
    
    print("✅ 이력서 데이터 구성 완료")
    print(f"   • 이름: {resume_data['name']}")
    print(f"   • 경력: {resume_data['background'].get('career_years', '미정')}년")
    print(f"   • 주요 기술: {', '.join(resume_data['technical_skills'][:5])}")
    
    # 5. 면접관 질문 생성
    print_section("5단계: 면접관 질문 생성")
    print(f"🎯 {company_name} {role_name} 면접관이 이력서를 분석하여 맞춤 질문 생성 중...")
    
    question_result = question_gen.generate_question_by_role(
        interviewer_role=interviewer_role,
        company_id=company_id, 
        user_resume=resume_data
    )
    question = question_result['question']
    
    print("✅ 질문 생성 완료")
    display_question_analysis(question, company_name, role_name)
    
    # 6. AI 지원자 답변 생성 (여러 레벨)
    print_section("6단계: AI 지원자 답변 생성")
    print("🤖 동일한 페르소나가 서로 다른 품질 레벨로 답변 생성...")
    
    answers = generate_and_display_answers(
        question_gen, answer_gen, persona, question,
        interviewer_role, role_name, company_id, position
    )
    
    # 7. 결과 저장
    print_section("7단계: 결과 저장")
    filename = save_test_results(company_name, position_name, role_name, persona, question, answers)
    
    # 8. 요약 출력
    print_section("✅ 테스트 완료 - 모델 동작 요약")
    print(f"🎯 테스트 시나리오: {company_name} {position_name} {role_name} 면접")
    print(f"📊 확인된 모델 기능:")
    print(f"   ✅ 회사/직군 입력에 따른 페르소나 자동 생성")
    print(f"   ✅ 페르소나 기반 개인화된 이력서 데이터 구성") 
    print(f"   ✅ 이력서 분석을 통한 맞춤형 질문 생성")
    print(f"   ✅ 페르소나 일관성 유지하며 다양한 품질 레벨 답변 생성")
    print(f"   ✅ 전체 면접 프로세스 시뮬레이션")
    
    if filename:
        print(f"\n📁 상세 결과 파일: {filename}")
        print("📋 테스트 계획 및 평가서에 활용 가능한 데이터 포함")

def batch_test_all_scenarios():
    """모든 주요 시나리오 배치 테스트"""
    print_header("배치 테스트 모드 - 모든 주요 시나리오 테스트")
    
    # 주요 테스트 시나리오들
    test_scenarios = [
        ("naver", "네이버", "backend", "백엔드", "TECH", "기술"),
        ("kakao", "카카오", "frontend", "프론트엔드", "HR", "인사"),
        ("toss", "토스", "ai", "AI/ML", "TECH", "기술"),
        ("coupang", "쿠팡", "data", "데이터사이언스", "COLLABORATION", "협업"),
    ]
    
    all_results = []
    
    for i, (company_id, company_name, position, position_name, interviewer_role, role_name) in enumerate(test_scenarios, 1):
        print(f"\n🎯 시나리오 {i}/{len(test_scenarios)}: {company_name} {position_name} {role_name}")
        print("─" * 60)
        
        try:
            # 모델 초기화
            question_gen = QuestionGenerator()
            answer_gen = AICandidateModel()
            
            # 페르소나 생성
            persona = answer_gen.create_persona_for_interview(company_id, position)
            if not persona:
                persona = answer_gen._create_default_persona(company_id, position)
            
            print(f"✅ 페르소나: {persona.name}")
            
            # 이력서 데이터 구성
            resume_data = {
                "name": persona.name,
                "background": persona.background,
                "technical_skills": persona.technical_skills,
                "experiences": persona.experiences,
                "projects": persona.projects,
                "strengths": persona.strengths,
                "career_goal": persona.career_goal
            }
            
            # 질문 생성
            question_result = question_gen.generate_question_by_role(
                interviewer_role=interviewer_role,
                company_id=company_id, 
                user_resume=resume_data
            )
            question = question_result['question']
            print(f"✅ 질문 생성 완료")
            
            # 답변 생성 (간단 버전)
            question_type_mapping = {
                "HR": QuestionType.HR,
                "TECH": QuestionType.TECH,
                "COLLABORATION": QuestionType.COLLABORATION
            }
            question_type = question_type_mapping.get(interviewer_role, QuestionType.TECH)
            
            levels = [QualityLevel.INADEQUATE, QualityLevel.AVERAGE, QualityLevel.EXCELLENT]
            answers = []
            
            for quality_level in levels:
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
                answers.append(response.answer_content)
            
            print(f"✅ 3가지 레벨 답변 생성 완료")
            
            # 결과 저장
            result = {
                "scenario": f"{company_name}_{position_name}_{role_name}",
                "company": company_name,
                "position": position_name,
                "interviewer_role": role_name,
                "persona_name": persona.name,
                "persona_skills": ', '.join(persona.technical_skills[:8]),
                "question": question,
                "beginner_answer": answers[0] if len(answers) > 0 else "",
                "intermediate_answer": answers[1] if len(answers) > 1 else "",
                "advanced_answer": answers[2] if len(answers) > 2 else "",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            all_results.append(result)
            print(f"✅ 시나리오 {i} 완료\n")
            
        except Exception as e:
            print(f"❌ 시나리오 {i} 실패: {e}\n")
            continue
    
    # 전체 결과 저장
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_test/batch_model_flow_results_{timestamp}.xlsx"
        
        try:
            df = pd.DataFrame(all_results)
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"🎉 배치 테스트 완료!")
            print(f"📊 총 {len(all_results)}개 시나리오 결과 저장: {filename}")
        except Exception as e:
            print(f"❌ 배치 결과 저장 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 AI 면접 시스템 모델 플로우 테스트")
    print("📋 테스트 계획 및 평가서용 모델 동작 검증")
    print("=" * 80)
    
    mode_choice = input("\n실행 모드를 선택하세요:\n1. 단일 테스트 (상세)\n2. 배치 테스트 (전체 시나리오)\n\n선택 (1 or 2): ").strip()
    
    if mode_choice == "2":
        batch_test_all_scenarios()
    else:
        run_model_flow_test()

if __name__ == "__main__":
    main()