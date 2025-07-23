#!/usr/bin/env python3
"""
AI 면접 시스템 실행 파일
"""

import os
import sys
import subprocess

def main():
    print("AI 면접 시스템 v2.0")
    print("=" * 50)
    
    # 프로젝트 루트 디렉토리로 이동
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("개인화된 면접 시스템을 시작합니다...")
    print("브라우저에서 http://localhost:9001 접속")
    print()
    print("제공 기능:")
    print("  •  문서 업로드 기반 개인화 면접")
    print("  •  문서 없이 표준 면접 진행")
    print("  •  7개 기업별 맞춤형 질문")
    print("  •  AI 기반 상세 평가 및 피드백")
    print()
    print("서버 종료: Ctrl+C")
    print("=" * 50)
    
    try:
        # 웹 앱 실행
        subprocess.run([sys.executable, "web/app.py"])
    except KeyboardInterrupt:
        print("\n서버가 종료되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("해결 방법:")
        print("  - Python 환경 확인")
        print("  - pip install -r requirements.txt")
        print("  - OpenAI API 키 확인")

if __name__ == "__main__":
    main()
    