# Backend Extensions

이 폴더는 백엔드의 미래 확장 기능들을 위해 준비되었습니다.

## 계획된 구조

```
backend/extensions/
├── resume/                 # 이력서 업로드/분석 API
├── persona/                # 페르소나 선택/관리 API
├── video/                  # 화상면접 세션 API
└── agents/                 # 에이전트 관리 API
```

## 확장 인터페이스

현재 backend/main.py는 기본 면접 기능만 제공하며, 추후 이 폴더의 확장 모듈들이 플러그인 방식으로 추가될 예정입니다.