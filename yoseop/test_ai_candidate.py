#\!/usr/bin/env python3
"""
AI 지원자 시스템 테스트
"""

import os
import sys
sys.path.append('.')

from core.ai_candidate_model import AICandidateModel
from core.llm_manager import LLMProvider

def test_ai_candidate():
    """AI 지원자 시스템 테스트"""
    print("🧪 AI 지원자 시스템 테스트 시작")
    
    try:
        # 1. 모델 초기화
        ai_candidate = AICandidateModel()
        print("✅ AI 지원자 모델 초기화 성공")
        
        # 2. AI 이름 테스트
        ai_name = ai_candidate.get_ai_name(LLMProvider.OPENAI_GPT35)
        print(f"✅ AI 이름: {ai_name}")
        
        # 3. 페르소나 리스트 확인
        available_personas = list(ai_candidate.candidate_personas.keys())
        print(f"✅ 사용 가능한 페르소나: {available_personas}")
        
        # 4. AI 면접 시작 테스트
        ai_session_id = ai_candidate.start_ai_interview("naver", "백엔드 개발자")
        print(f"✅ AI 면접 세션 시작: {ai_session_id}")
        
        # 5. 첫 번째 질문 생성 테스트
        first_question = ai_candidate.get_ai_next_question(ai_session_id)
        if first_question:
            print(f"✅ 첫 번째 질문 생성 성공")
            print(f"   - 타입: {first_question['question_type']}")
            print(f"   - 내용: {first_question['question_content'][:50]}...")
            print(f"   - 진행률: {first_question['progress']}")
        else:
            print("❌ 첫 번째 질문 생성 실패")
            
        print("🎉 모든 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_candidate()