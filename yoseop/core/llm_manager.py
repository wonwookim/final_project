#!/usr/bin/env python3
"""
LLM 모델 관리자
다양한 LLM 모델을 통합 관리하고 모델별 특성에 맞게 최적화
"""

import openai
import json
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class LLMProvider(Enum):
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    GOOGLE_GEMINI_PRO = "google_gemini_pro"
    GOOGLE_GEMINI_FLASH = "google_gemini_flash"
    KT_BELIEF = "kt_belief"

@dataclass
class LLMConfig:
    """LLM 모델별 설정"""
    provider: LLMProvider
    model_name: str
    max_tokens: int
    temperature: float
    api_key: Optional[str] = None
    additional_params: Dict[str, Any] = None

@dataclass
class LLMResponse:
    """LLM 응답 표준화"""
    content: str
    provider: LLMProvider
    model_name: str
    token_count: Optional[int] = None
    response_time: Optional[float] = None
    error: Optional[str] = None

class BaseLLMClient(ABC):
    """LLM 클라이언트 기본 클래스"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """응답 생성"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """모델 사용 가능 여부 확인"""
        pass

class RateLimiter:
    """API 호출 속도 제한"""
    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def acquire(self):
        """요청 허용 여부 확인 및 대기"""
        with self.lock:
            now = time.time()
            
            # 시간 윈도우 밖의 요청 기록 제거
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()
            
            # 요청 한도 초과 시 대기
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0]) + 0.1
                print(f"⏳ Rate limit 도달. {sleep_time:.1f}초 대기...")
                time.sleep(sleep_time)
                return self.acquire()  # 재귀 호출
            
            # 요청 기록 추가
            self.requests.append(now)
            return True

class OpenAIClient(BaseLLMClient):
    """OpenAI 클라이언트"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if config.api_key:
            self.client = openai.OpenAI(api_key=config.api_key)
        else:
            self.client = openai.OpenAI()
        
        # Rate limiter 초기화 (분당 20회 제한)
        self.rate_limiter = RateLimiter(max_requests=20, time_window=60.0)
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """OpenAI API를 통한 응답 생성 (재시도 로직 포함)"""
        import time
        start_time = time.time()
        
        # Rate limiting 적용
        self.rate_limiter.acquire()
        
        max_retries = 5  # 재시도 횟수 증가
        base_delay = 2.0  # 기본 대기 시간 증가
        
        for attempt in range(max_retries):
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # 요청 파라미터 최적화 (안정성 향상)
                request_params = {
                    "model": self.config.model_name,
                    "messages": messages,
                    "max_tokens": min(self.config.max_tokens, 400),  # 토큰 제한 강화
                    "temperature": self.config.temperature,
                    "timeout": 60.0  # 타임아웃 설정
                }
                
                # 추가 파라미터가 있으면 병합
                if self.config.additional_params:
                    request_params.update(self.config.additional_params)
                
                response = self.client.chat.completions.create(**request_params)
                
                response_time = time.time() - start_time
                
                return LLMResponse(
                    content=response.choices[0].message.content.strip(),
                    provider=self.config.provider,
                    model_name=self.config.model_name,
                    token_count=response.usage.total_tokens if response.usage else None,
                    response_time=response_time
                )
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ API 호출 실패 (시도 {attempt + 1}/{max_retries}): {error_msg}")
                
                # 오버로드 에러, rate limit, 또는 서버 에러인 경우 재시도
                if any(keyword in error_msg.lower() for keyword in ["overloaded", "rate limit", "429", "503", "502", "500", "timeout"]):
                    if attempt < max_retries - 1:
                        # 지수 백오프 + 지터 적용
                        wait_time = base_delay * (2 ** attempt) + (attempt * 0.5)  # 지터 추가
                        print(f"🔄 {wait_time:.1f}초 후 재시도... (백오프 적용)")
                        time.sleep(wait_time)
                        continue
                
                # 최종 실패 또는 재시도하지 않는 에러
                return LLMResponse(
                    content="",
                    provider=self.config.provider,
                    model_name=self.config.model_name,
                    error=f"API 호출 실패 ({attempt + 1}회 시도): {error_msg}"
                )
        
        # 모든 재시도 실패
        return LLMResponse(
            content="",
            provider=self.config.provider,
            model_name=self.config.model_name,
            error=f"최대 재시도 횟수 초과: {max_retries}회"
        )
    
    def is_available(self) -> bool:
        """OpenAI API 사용 가능 여부 확인"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except:
            return False

class GoogleGeminiClient(BaseLLMClient):
    """Google Gemini 클라이언트 (향후 구현)"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Google AI API 클라이언트 초기화 (향후 구현)
        print(f"Google Gemini {config.model_name} 클라이언트 준비 중...")
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Gemini API를 통한 응답 생성 (향후 구현)"""
        return LLMResponse(
            content=f"[Gemini {self.config.model_name} 응답 준비 중...]",
            provider=self.config.provider,
            model_name=self.config.model_name,
            error="API 미구현"
        )
    
    def is_available(self) -> bool:
        return False

class KTBeliefClient(BaseLLMClient):
    """KT 믿음 모델 클라이언트 (향후 구현)"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        print(f"KT 믿음 모델 클라이언트 준비 중...")
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """KT 믿음 API를 통한 응답 생성 (향후 구현)"""
        return LLMResponse(
            content="[KT 믿음 모델 응답 준비 중...]",
            provider=self.config.provider,
            model_name=self.config.model_name,
            error="API 미구현"
        )
    
    def is_available(self) -> bool:
        return False

class LLMManager:
    """LLM 모델 통합 관리자"""
    
    def __init__(self):
        self.clients: Dict[LLMProvider, BaseLLMClient] = {}
        self.default_configs = self._get_default_configs()
        
    def _get_default_configs(self) -> Dict[LLMProvider, LLMConfig]:
        """기본 모델 설정"""
        return {
            LLMProvider.OPENAI_GPT4: LLMConfig(
                provider=LLMProvider.OPENAI_GPT4,
                model_name="gpt-4",
                max_tokens=400,  # 토큰 제한 강화
                temperature=0.6  # 안정성 향상
            ),
            LLMProvider.OPENAI_GPT35: LLMConfig(
                provider=LLMProvider.OPENAI_GPT35,
                model_name="gpt-3.5-turbo",
                max_tokens=350,  # 더 안정적인 모델 우선 사용
                temperature=0.6
            ),
            LLMProvider.OPENAI_GPT4O_MINI: LLMConfig(
                provider=LLMProvider.OPENAI_GPT4O_MINI,
                model_name="gpt-4o-mini",
                max_tokens=350,  # 토큰 제한 강화
                temperature=0.6
            ),
            LLMProvider.GOOGLE_GEMINI_PRO: LLMConfig(
                provider=LLMProvider.GOOGLE_GEMINI_PRO,
                model_name="gemini-pro",
                max_tokens=800,
                temperature=0.7
            ),
            LLMProvider.GOOGLE_GEMINI_FLASH: LLMConfig(
                provider=LLMProvider.GOOGLE_GEMINI_FLASH,
                model_name="gemini-flash",
                max_tokens=600,
                temperature=0.7
            ),
            LLMProvider.KT_BELIEF: LLMConfig(
                provider=LLMProvider.KT_BELIEF,
                model_name="kt-belief-1.0",
                max_tokens=600,
                temperature=0.7
            )
        }
    
    def register_model(self, provider: LLMProvider, config: LLMConfig = None, api_key: str = None):
        """모델 등록"""
        if config is None:
            config = self.default_configs[provider]
        
        if api_key:
            config.api_key = api_key
        
        # 클라이언트 생성
        if provider in [LLMProvider.OPENAI_GPT4, LLMProvider.OPENAI_GPT35, LLMProvider.OPENAI_GPT4O_MINI]:
            self.clients[provider] = OpenAIClient(config)
        elif provider in [LLMProvider.GOOGLE_GEMINI_PRO, LLMProvider.GOOGLE_GEMINI_FLASH]:
            self.clients[provider] = GoogleGeminiClient(config)
        elif provider == LLMProvider.KT_BELIEF:
            self.clients[provider] = KTBeliefClient(config)
        
        print(f"✅ {provider.value} 모델 등록 완료")
    
    def generate_response(self, provider: LLMProvider, prompt: str, system_prompt: str = "") -> LLMResponse:
        """지정된 모델로 응답 생성"""
        if provider not in self.clients:
            return LLMResponse(
                content="",
                provider=provider,
                model_name="",
                error=f"모델 {provider.value}이 등록되지 않았습니다."
            )
        
        return self.clients[provider].generate_response(prompt, system_prompt)
    
    def generate_multi_responses(self, providers: List[LLMProvider], prompt: str, system_prompt: str = "") -> Dict[LLMProvider, LLMResponse]:
        """여러 모델로 동시 응답 생성"""
        responses = {}
        for provider in providers:
            responses[provider] = self.generate_response(provider, prompt, system_prompt)
        return responses
    
    def get_available_models(self) -> List[LLMProvider]:
        """사용 가능한 모델 목록"""
        available = []
        for provider, client in self.clients.items():
            if client.is_available():
                available.append(provider)
        return available
    
    def get_model_info(self, provider: LLMProvider) -> Dict[str, Any]:
        """모델 정보 조회"""
        if provider not in self.clients:
            return {"error": "모델이 등록되지 않았습니다."}
        
        config = self.clients[provider].config
        return {
            "provider": provider.value,
            "model_name": config.model_name,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "is_available": self.clients[provider].is_available()
        }
    
    def update_model_config(self, provider: LLMProvider, **kwargs):
        """모델 설정 업데이트"""
        if provider not in self.clients:
            print(f"⚠️ 모델 {provider.value}이 등록되지 않았습니다.")
            return
        
        config = self.clients[provider].config
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
                print(f"✅ {provider.value} {key} 설정을 {value}로 변경")

if __name__ == "__main__":
    # LLM Manager 테스트
    print("🔧 LLM Manager 테스트")
    
    manager = LLMManager()
    
    # OpenAI 모델 등록 테스트
    api_key = input("OpenAI API 키를 입력하세요 (테스트용): ")
    if api_key:
        manager.register_model(LLMProvider.OPENAI_GPT4O_MINI, api_key=api_key)
        
        # 간단한 응답 생성 테스트
        response = manager.generate_response(
            LLMProvider.OPENAI_GPT4O_MINI,
            "안녕하세요. 간단한 자기소개를 해주세요.",
            "당신은 신입 개발자 지원자입니다."
        )
        
        print(f"\n📝 응답 테스트:")
        print(f"모델: {response.model_name}")
        print(f"응답: {response.content}")
        if response.error:
            print(f"오류: {response.error}")
    
    # 사용 가능한 모델 확인
    available_models = manager.get_available_models()
    print(f"\n✅ 사용 가능한 모델: {[m.value for m in available_models]}")