#!/usr/bin/env python3
"""
리팩터링 후 기능 테스트 스크립트
현재 동작하는 모든 기능이 새로운 구조에서도 정상 동작하는지 확인
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import_structure():
    """새로운 import 구조 테스트"""
    print("🔍 Import 구조 테스트 시작...")
    
    try:
        # LLM 시스템 임포트 테스트
        from llm.interviewer.service import InterviewerService
        from llm.candidate.model import AICandidateModel
        from llm.session.interviewer_session import InterviewerSession
        print("✅ LLM 모듈 import 성공")
        
        # 기본 객체 생성 테스트
        interviewer_service = InterviewerService()
        ai_candidate = AICandidateModel()
        interviewer_session = InterviewerSession("naver", "백엔드 개발자", "테스트유저")
        print("✅ 객체 생성 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ Import 오류: {e}")
        return False

def test_backend_server():
    """백엔드 서버 구동 테스트"""
    print("\n🔍 백엔드 서버 테스트 시작...")
    
    try:
        # 백엔드 main.py import 테스트
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backend_main", 
            "/Users/choiyoseop/Desktop/final_project/final_Q_test/backend/main.py"
        )
        backend_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_main)
        
        print("✅ 백엔드 서버 모듈 로드 성공")
        return True
        
    except Exception as e:
        print(f"❌ 백엔드 서버 오류: {e}")
        return False

if __name__ == "__main__":
    print("🚀 리팩터링 기능 테스트 시작\n")
    
    success_count = 0
    total_tests = 2
    
    # 테스트 실행
    if test_import_structure():
        success_count += 1
    
    if test_backend_server():
        success_count += 1
    
    # 결과 출력
    print(f"\n📊 테스트 결과: {success_count}/{total_tests} 성공")
    
    if success_count == total_tests:
        print("🎉 모든 테스트 통과! 리팩터링이 성공적으로 완료되었습니다.")
    else:
        print("⚠️  일부 테스트 실패. 문제를 해결해야 합니다.")