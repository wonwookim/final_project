"""
LLM 모델 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.llm_manager import LLMManager, LLMProvider

class BaseLLMModel(ABC):
    """LLM 모델 기본 클래스"""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI_GPT4O_MINI):
        self.llm_manager = LLMManager()
        self.provider = provider
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """응답 생성 (하위 클래스에서 구현)"""
        pass
    
    async def _call_llm(self, prompt: str, system_message: str = "", **kwargs) -> str:
        """LLM 호출 공통 메서드"""
        try:
            # LLMManager의 동기 메서드 사용
            full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt
            response = self.llm_manager.generate_response(
                prompt=full_prompt,
                provider=self.provider,
                **kwargs
            )
            return response.content.strip() if response else ""
        except Exception as e:
            print(f"LLM 호출 오류: {str(e)}")
            return ""