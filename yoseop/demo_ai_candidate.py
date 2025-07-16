#!/usr/bin/env python3
"""
AI 지원자 모델 데모 스크립트
다양한 기능을 테스트하고 시연할 수 있는 통합 데모
"""

import os
import sys
import time
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# .env 파일에서 환경변수 로드
load_dotenv()

from core.ai_candidate_model import AICandidateModel, AnswerRequest, AnswerResponse
from core.llm_manager import LLMProvider
from core.answer_quality_controller import QualityLevel
from core.interview_system import QuestionType
from core.ai_candidate_config import get_config

class AICandidateDemo:
    """AI 지원자 데모 클래스"""
    
    def __init__(self):
        self.ai_candidate = None
        self.config = get_config()
        
    def setup(self) -> bool:
        """데모 초기 설정"""
        print("🤖 AI 지원자 모델 데모 시스템")
        print("=" * 60)
        
        # .env 파일에서 API 키 자동 로드
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("⚠️ .env 파일에서 OPENAI_API_KEY를 찾을 수 없습니다.")
            api_key = input("🔑 OpenAI API 키를 직접 입력하세요: ").strip()
            if not api_key:
                print("❌ API 키가 필요합니다.")
                return False
        else:
            print(f"✅ .env 파일에서 API 키 로드 완료 (끝 4자리: ...{api_key[-4:]})")
        
        # AI 지원자 모델 초기화
        try:
            self.ai_candidate = AICandidateModel(api_key)
            print("✅ AI 지원자 모델 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
            return False
    
    def show_main_menu(self):
        """메인 메뉴 표시"""
        print("\n" + "=" * 60)
        print("🎯 AI 지원자 데모 메뉴")
        print("=" * 60)
        print("1. 기본 답변 생성 테스트")
        print("2. 품질 레벨별 답변 비교")
        print("3. 다중 LLM 모델 비교")
        print("4. 회사별 페르소나 비교")
        print("5. 전체 면접 시뮬레이션")
        print("6. 설정 관리")
        print("7. 페르소나 정보 조회")
        print("0. 종료")
        print("=" * 60)
    
    def run_basic_answer_test(self):
        """기본 답변 생성 테스트"""
        print("\n📝 기본 답변 생성 테스트")
        print("-" * 40)
        
        # 회사 선택
        companies = self.ai_candidate.get_available_companies()
        print(f"사용 가능한 회사: {', '.join(companies)}")
        
        company_id = input("회사를 선택하세요: ").strip()
        if company_id not in companies:
            print("❌ 잘못된 회사 선택")
            return
        
        # 질문 입력
        questions = [
            "간단한 자기소개를 해주세요.",
            "우리 회사에 지원한 동기는 무엇인가요?",
            "가장 자신 있는 기술 스택은 무엇인가요?",
            "팀 프로젝트에서 어려웠던 경험이 있나요?",
            "직접 입력"
        ]
        
        print("\n질문을 선택하거나 직접 입력하세요:")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")
        
        choice = input("선택 (1-5): ").strip()
        
        if choice == "5":
            question_content = input("질문을 입력하세요: ").strip()
            question_type = QuestionType.HR
        else:
            try:
                idx = int(choice) - 1
                question_content = questions[idx]
                question_types = [QuestionType.INTRO, QuestionType.MOTIVATION, 
                                QuestionType.TECH, QuestionType.COLLABORATION]
                question_type = question_types[idx] if idx < 4 else QuestionType.HR
            except (ValueError, IndexError):
                print("❌ 잘못된 선택")
                return
        
        # 답변 생성
        request = AnswerRequest(
            question_content=question_content,
            question_type=question_type,
            question_intent="지원자 역량 평가",
            company_id=company_id,
            position="백엔드 개발자",
            quality_level=QualityLevel.GOOD,
            llm_provider=LLMProvider.OPENAI_GPT4O_MINI
        )
        
        print(f"\n🔄 답변 생성 중...")
        start_time = time.time()
        
        response = self.ai_candidate.generate_answer(request)
        
        generation_time = time.time() - start_time
        
        # 결과 출력
        print(f"\n✅ 답변 생성 완료 (총 {generation_time:.2f}초)")
        print("=" * 60)
        print(f"🏢 회사: {company_id}")
        print(f"👤 페르소나: {response.persona_name}")
        print(f"📊 품질 레벨: {response.quality_level.value}점")
        print(f"🎯 신뢰도: {response.confidence_score}")
        print(f"⏱️ 응답 시간: {response.response_time:.2f}초")
        print("=" * 60)
        print(f"❓ 질문: {question_content}")
        print(f"💬 답변:\n{response.answer_content}")
        print("=" * 60)
        
        if response.error:
            print(f"❌ 오류: {response.error}")
    
    def run_quality_comparison(self):
        """품질 레벨별 답변 비교"""
        print("\n📊 품질 레벨별 답변 비교")
        print("-" * 40)
        
        # 기본 설정
        companies = self.ai_candidate.get_available_companies()
        if not companies:
            print("❌ 사용 가능한 회사가 없습니다.")
            return
        
        company_id = companies[0]  # 첫 번째 회사 사용
        question_content = "가장 자신있는 기술 스택과 관련 프로젝트 경험을 설명해주세요."
        
        # 비교할 품질 레벨
        quality_levels = [QualityLevel.EXCELLENT, QualityLevel.GOOD, QualityLevel.AVERAGE, QualityLevel.POOR]
        
        print(f"회사: {company_id}")
        print(f"질문: {question_content}")
        print(f"비교 품질 레벨: {[f'{q.value}점' for q in quality_levels]}")
        
        input("\n계속하려면 Enter를 누르세요...")
        
        # 각 품질 레벨별 답변 생성
        results = {}
        for level in quality_levels:
            print(f"\n🔄 {level.value}점 수준 답변 생성 중...")
            
            request = AnswerRequest(
                question_content=question_content,
                question_type=QuestionType.TECH,
                question_intent="기술적 역량 및 프로젝트 경험 평가",
                company_id=company_id,
                position="백엔드 개발자",
                quality_level=level,
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            response = self.ai_candidate.generate_answer(request)
            results[level] = response
        
        # 결과 비교 출력
        print("\n" + "=" * 80)
        print("📊 품질 레벨별 답변 비교 결과")
        print("=" * 80)
        
        for level, response in results.items():
            print(f"\n🎯 {level.value}점 수준 ({level.name})")
            print(f"신뢰도: {response.confidence_score} | 응답시간: {response.response_time:.2f}초 | 길이: {len(response.answer_content)}자")
            print(f"답변: {response.answer_content[:200]}...")
            print("-" * 80)
    
    def run_llm_comparison(self):
        """다중 LLM 모델 비교"""
        print("\n🔧 다중 LLM 모델 비교")
        print("-" * 40)
        
        # 활성화된 모델 확인
        enabled_models = self.config.get_enabled_models()
        available_models = [m for m in enabled_models if m in [LLMProvider.OPENAI_GPT4O_MINI, LLMProvider.OPENAI_GPT35]]
        
        if len(available_models) < 2:
            print("❌ 비교할 수 있는 모델이 부족합니다. (최소 2개 필요)")
            print(f"현재 사용 가능: {[m.value for m in available_models]}")
            return
        
        # 기본 설정
        companies = self.ai_candidate.get_available_companies()
        company_id = companies[0] if companies else "naver"
        question_content = "팀에서 갈등이 있었을 때 어떻게 해결했나요?"
        
        print(f"회사: {company_id}")
        print(f"질문: {question_content}")
        print(f"비교 모델: {[m.value for m in available_models]}")
        
        input("\n계속하려면 Enter를 누르세요...")
        
        # 각 모델별 답변 생성
        results = {}
        for model in available_models:
            print(f"\n🔄 {model.value} 모델 답변 생성 중...")
            
            request = AnswerRequest(
                question_content=question_content,
                question_type=QuestionType.COLLABORATION,
                question_intent="협업 및 갈등 해결 능력 평가",
                company_id=company_id,
                position="백엔드 개발자",
                quality_level=QualityLevel.GOOD,
                llm_provider=model
            )
            
            response = self.ai_candidate.generate_answer(request)
            results[model] = response
        
        # 결과 비교 출력
        print("\n" + "=" * 80)
        print("🔧 LLM 모델별 답변 비교 결과")
        print("=" * 80)
        
        for model, response in results.items():
            print(f"\n🤖 {model.value}")
            print(f"신뢰도: {response.confidence_score} | 응답시간: {response.response_time:.2f}초 | 길이: {len(response.answer_content)}자")
            print(f"답변: {response.answer_content[:300]}...")
            print("-" * 80)
    
    def run_persona_comparison(self):
        """회사별 페르소나 비교"""
        print("\n🏢 회사별 페르소나 비교")
        print("-" * 40)
        
        companies = self.ai_candidate.get_available_companies()
        if len(companies) < 2:
            print("❌ 비교할 회사가 부족합니다.")
            return
        
        question_content = "우리 회사에 지원한 동기는 무엇인가요?"
        
        print(f"질문: {question_content}")
        print(f"비교 회사: {companies}")
        
        input("\n계속하려면 Enter를 누르세요...")
        
        # 각 회사별 답변 생성
        results = {}
        for company in companies[:3]:  # 최대 3개 회사
            print(f"\n🔄 {company} 페르소나 답변 생성 중...")
            
            request = AnswerRequest(
                question_content=question_content,
                question_type=QuestionType.MOTIVATION,
                question_intent="지원 동기 및 회사 이해도 평가",
                company_id=company,
                position="백엔드 개발자",
                quality_level=QualityLevel.GOOD,
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            response = self.ai_candidate.generate_answer(request)
            results[company] = response
        
        # 결과 비교 출력
        print("\n" + "=" * 80)
        print("🏢 회사별 페르소나 답변 비교 결과")
        print("=" * 80)
        
        for company, response in results.items():
            print(f"\n🏢 {company} - {response.persona_name}")
            print(f"신뢰도: {response.confidence_score} | 응답시간: {response.response_time:.2f}초")
            print(f"답변: {response.answer_content}")
            print("-" * 80)
    
    def run_full_interview_simulation(self):
        """전체 면접 시뮬레이션"""
        print("\n🎭 전체 면접 시뮬레이션")
        print("-" * 40)
        
        # 회사 선택
        companies = self.ai_candidate.get_available_companies()
        print(f"사용 가능한 회사: {', '.join(companies)}")
        
        company_id = input("회사를 선택하세요: ").strip()
        if company_id not in companies:
            print("❌ 잘못된 회사 선택")
            return
        
        # 면접 질문 세트
        interview_questions = [
            ("간단한 자기소개를 해주세요.", QuestionType.INTRO),
            (f"우리 회사에 지원한 동기는 무엇인가요?", QuestionType.MOTIVATION),
            ("가장 자신 있는 기술 스택과 프로젝트 경험을 설명해주세요.", QuestionType.TECH),
            ("팀 프로젝트에서 갈등을 해결한 경험이 있나요?", QuestionType.COLLABORATION),
            ("개발자로서 가장 어려웠던 문제를 어떻게 해결했나요?", QuestionType.TECH)
        ]
        
        print(f"\n🎯 {company_id} 면접 시뮬레이션 시작")
        print(f"총 {len(interview_questions)}개 질문")
        
        input("계속하려면 Enter를 누르세요...")
        
        responses = []
        total_time = 0
        
        for i, (question, q_type) in enumerate(interview_questions, 1):
            print(f"\n{'='*60}")
            print(f"질문 {i}/{len(interview_questions)}")
            print(f"{'='*60}")
            print(f"❓ {question}")
            
            # 답변 생성
            request = AnswerRequest(
                question_content=question,
                question_type=q_type,
                question_intent=f"{q_type.value} 역량 평가",
                company_id=company_id,
                position="백엔드 개발자",
                quality_level=QualityLevel.GOOD,
                llm_provider=LLMProvider.OPENAI_GPT4O_MINI
            )
            
            print("🔄 답변 생성 중...")
            response = self.ai_candidate.generate_answer(request)
            responses.append(response)
            total_time += response.response_time
            
            print(f"💬 {response.persona_name}:")
            print(f"{response.answer_content}")
            print(f"\n📊 평가: 신뢰도 {response.confidence_score}, 응답시간 {response.response_time:.2f}초")
            
            if i < len(interview_questions):
                input("\n다음 질문으로 계속하려면 Enter를 누르세요...")
        
        # 면접 결과 요약
        print(f"\n{'='*80}")
        print("🎭 면접 시뮬레이션 결과 요약")
        print(f"{'='*80}")
        print(f"🏢 회사: {company_id}")
        print(f"👤 페르소나: {responses[0].persona_name}")
        print(f"📊 평균 신뢰도: {sum(r.confidence_score for r in responses) / len(responses):.2f}")
        print(f"⏱️ 총 응답 시간: {total_time:.2f}초")
        print(f"📝 답변 수: {len(responses)}개")
        print(f"💬 평균 답변 길이: {sum(len(r.answer_content) for r in responses) // len(responses)}자")
    
    def show_persona_info(self):
        """페르소나 정보 조회"""
        print("\n👤 페르소나 정보 조회")
        print("-" * 40)
        
        companies = self.ai_candidate.get_available_companies()
        
        for company in companies:
            summary = self.ai_candidate.get_persona_summary(company)
            if summary:
                print(f"\n🏢 {company.upper()}")
                print(f"이름: {summary.get('name', 'N/A')}")
                print(f"경력: {summary.get('career_years', 'N/A')}년")
                print(f"직책: {summary.get('position', 'N/A')}")
                print(f"주요 기술: {', '.join(summary.get('main_skills', [])[:3])}")
                print(f"핵심 강점: {', '.join(summary.get('key_strengths', [])[:2])}")
                print(f"면접 스타일: {summary.get('interview_style', 'N/A')}")
                print("-" * 50)
    
    def manage_settings(self):
        """설정 관리"""
        print("\n⚙️ 설정 관리")
        print("-" * 40)
        
        # 현재 설정 요약
        summary = self.config.get_config_summary()
        print("📊 현재 설정:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # 설정 유효성 검증
        warnings = self.config.validate_config()
        if warnings:
            print("\n⚠️ 설정 경고:")
            for warning in warnings:
                print(f"  - {warning}")
        
        print("\n설정 옵션:")
        print("1. 모델 활성화/비활성화")
        print("2. 품질 설정 변경")
        print("3. 설정 저장")
        print("4. 기본 설정으로 초기화")
        print("0. 돌아가기")
        
        choice = input("선택: ").strip()
        
        if choice == "1":
            self._manage_model_settings()
        elif choice == "2":
            self._manage_quality_settings()
        elif choice == "3":
            self.config.save_config()
            print("✅ 설정이 저장되었습니다.")
        elif choice == "4":
            confirm = input("정말 기본 설정으로 초기화하시겠습니까? (y/N): ")
            if confirm.lower() == 'y':
                self.config.reset_to_defaults()
    
    def _manage_model_settings(self):
        """모델 설정 관리"""
        print("\n🤖 모델 설정 관리")
        
        for provider in LLMProvider:
            setting = self.config.get_model_setting(provider)
            if setting:
                status = "✅ 활성화" if setting.enabled else "❌ 비활성화"
                print(f"{provider.value}: {status}")
        
        provider_name = input("\n변경할 모델 (예: openai_gpt4o_mini): ").strip()
        try:
            provider = LLMProvider(provider_name)
            action = input("활성화(e)/비활성화(d): ").strip().lower()
            
            if action == 'e':
                self.config.enable_model(provider)
            elif action == 'd':
                self.config.disable_model(provider)
        except ValueError:
            print("❌ 잘못된 모델명입니다.")
    
    def _manage_quality_settings(self):
        """품질 설정 관리"""
        print("\n📊 품질 설정 관리")
        print(f"현재 기본 품질 레벨: {self.config.quality_settings.default_level.value}")
        
        try:
            new_level = int(input("새 기본 품질 레벨 (1-10): "))
            if 1 <= new_level <= 10:
                self.config.update_quality_setting(default_level=new_level)
            else:
                print("❌ 1-10 범위의 값을 입력하세요.")
        except ValueError:
            print("❌ 숫자를 입력하세요.")
    
    def run(self):
        """데모 실행"""
        if not self.setup():
            return
        
        while True:
            try:
                self.show_main_menu()
                choice = input("\n선택하세요: ").strip()
                
                if choice == "0":
                    print("👋 데모를 종료합니다.")
                    break
                elif choice == "1":
                    self.run_basic_answer_test()
                elif choice == "2":
                    self.run_quality_comparison()
                elif choice == "3":
                    self.run_llm_comparison()
                elif choice == "4":
                    self.run_persona_comparison()
                elif choice == "5":
                    self.run_full_interview_simulation()
                elif choice == "6":
                    self.manage_settings()
                elif choice == "7":
                    self.show_persona_info()
                else:
                    print("❌ 잘못된 선택입니다.")
                
                input("\n메인 메뉴로 돌아가려면 Enter를 누르세요...")
                
            except KeyboardInterrupt:
                print("\n\n👋 데모를 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                input("계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    demo = AICandidateDemo()
    demo.run()