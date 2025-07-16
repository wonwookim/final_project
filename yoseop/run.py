#!/usr/bin/env python3
"""
AI 면접 시스템 실행 파일
"""

import os
import sys
import subprocess
import time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import config
from core.logging_config import interview_logger

def print_startup_banner():
    """시작 배너 출력"""
    print("🎯 AI 면접 시스템 v2.0")
    print("=" * 60)
    print("개인화된 AI 면접 시스템을 시작합니다...")
    print(f"📱 브라우저에서 http://localhost:{config.FLASK_PORT} 접속")
    print()
    print("🚀 제공 기능:")
    print("  📄 문서 업로드 기반 개인화 면접")
    print("  📝 문서 없이 표준 면접 진행") 
    print("  🤖 AI 지원자 '춘식이'와 경쟁 면접")
    print("  👀 AI 단독 면접 시연")
    print("  🏢 7개 대기업 맞춤형 질문")
    print("  📊 AI 기반 상세 평가 및 피드백")
    print()
    print("🔧 시스템 설정:")
    config_summary = config.get_config_summary()
    print(f"  • 서버: {config_summary['server']['host']}:{config_summary['server']['port']}")
    print(f"  • 디버그 모드: {config_summary['server']['debug']}")
    print(f"  • AI 모델: {config_summary['ai']['model']}")
    print(f"  • 최대 파일 크기: {config_summary['limits']['max_file_size']}")
    print(f"  • 총 질문 수: {config_summary['limits']['total_questions']}")
    print()
    print("⚠️  서버 종료: Ctrl+C")
    print("=" * 60)

def check_requirements():
    """필수 요구사항 확인"""
    try:
        # OpenAI API 키 확인
        if not config.OPENAI_API_KEY:
            print("❌ OpenAI API 키가 설정되지 않았습니다.")
            print("💡 해결 방법:")
            print("   1. .env 파일에 OPENAI_API_KEY=your-api-key 추가")
            print("   2. 환경변수로 직접 설정")
            return False
        
        # 업로드 폴더 확인
        if not os.path.exists(config.UPLOAD_FOLDER):
            os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
            print(f"📁 업로드 폴더 생성: {config.UPLOAD_FOLDER}")
        
        # 로그 폴더 확인
        if config.LOG_FILE:
            log_dir = os.path.dirname(config.LOG_FILE)
            if not log_dir:
                log_dir = 'logs'
        else:
            log_dir = 'logs'
            
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"📁 로그 폴더 생성: {log_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 환경 확인 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    try:
        # 프로젝트 루트 디렉토리로 이동
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # 시작 배너 출력
        print_startup_banner()
        
        # 요구사항 확인
        if not check_requirements():
            print("\n❌ 시스템 요구사항이 충족되지 않았습니다.")
            print("💡 해결 방법:")
            print("   - .env 파일 확인 및 API 키 설정")
            print("   - pip install -r requirements.txt 실행")
            print("   - Python 3.8+ 버전 확인")
            sys.exit(1)
        
        # 로그 기록
        interview_logger.info("시스템 시작", 
                            port=config.FLASK_PORT, 
                            debug=config.FLASK_DEBUG,
                            config_summary=config.get_config_summary())
        
        print("🚀 웹 서버 시작 중...")
        time.sleep(1)
        
        # 웹 앱 실행
        subprocess.run([sys.executable, "web/app.py"])
        
    except KeyboardInterrupt:
        print("\n\n⏹️  서버가 안전하게 종료되었습니다.")
        interview_logger.info("시스템 종료", reason="사용자 요청")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("💡 해결 방법:")
        print("   - Python 환경 확인 (python --version)")
        print("   - 의존성 설치 (pip install -r requirements.txt)")
        print("   - .env 파일 확인 및 API 키 설정")
        print("   - 포트 충돌 확인 (다른 프로세스가 포트 사용 중)")
        print("   - 로그 파일 확인 (logs/server.log)")
        
        interview_logger.error("시스템 시작 실패", 
                             error=str(e), 
                             config_summary=config.get_config_summary())
        sys.exit(1)

if __name__ == "__main__":
    main()