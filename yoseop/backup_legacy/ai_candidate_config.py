#!/usr/bin/env python3
"""
AI 지원자 설정 관리 모듈
LLM 모델 설정, 답변 품질 조절, 페르소나 설정 등을 중앙 관리
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .llm_manager import LLMProvider
from .answer_quality_controller import QualityLevel

@dataclass
class ModelSettings:
    """LLM 모델별 설정"""
    provider: LLMProvider
    enabled: bool = True
    api_key: Optional[str] = None
    max_tokens: int = 600
    temperature: float = 0.7
    timeout: float = 30.0
    custom_params: Dict[str, Any] = None

@dataclass
class QualitySettings:
    """품질 설정"""
    default_level: QualityLevel = QualityLevel.GOOD
    min_answer_length: int = 50
    max_answer_length: int = 500
    enable_post_processing: bool = True
    quality_check_enabled: bool = True

@dataclass
class PersonaSettings:
    """페르소나 설정"""
    use_real_personas: bool = True
    fallback_to_default: bool = True
    persona_data_path: str = "llm/data/candidate_personas.json"
    enable_persona_validation: bool = True

@dataclass
class AnswerSettings:
    """답변 생성 설정"""
    include_confidence_score: bool = True
    enable_answer_comparison: bool = True
    max_retries: int = 3
    enable_fallback_answers: bool = True
    answer_cache_enabled: bool = True
    cache_duration_minutes: int = 60

@dataclass
class LoggingSettings:
    """로깅 설정"""
    log_level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = True
    log_performance: bool = True
    log_file_path: str = "logs/ai_candidate.log"

class AICandidateConfig:
    """AI 지원자 설정 관리자"""
    
    def __init__(self, config_file: str = "config/ai_candidate_config.json"):
        self.config_file = config_file
        self.model_settings: Dict[LLMProvider, ModelSettings] = {}
        self.quality_settings = QualitySettings()
        self.persona_settings = PersonaSettings()
        self.answer_settings = AnswerSettings()
        self.logging_settings = LoggingSettings()
        
        # 기본 설정 초기화
        self._initialize_default_settings()
        
        # 설정 파일에서 로드
        self.load_config()
    
    def _initialize_default_settings(self):
        """기본 설정 초기화"""
        
        # 기본 모델 설정
        default_models = {
            LLMProvider.OPENAI_GPT4O_MINI: ModelSettings(
                provider=LLMProvider.OPENAI_GPT4O_MINI,
                enabled=True,
                max_tokens=600,
                temperature=0.7,
                timeout=30.0
            ),
            LLMProvider.OPENAI_GPT4: ModelSettings(
                provider=LLMProvider.OPENAI_GPT4,
                enabled=False,  # 기본적으로 비활성화 (비용 때문)
                max_tokens=800,
                temperature=0.6,
                timeout=45.0
            ),
            LLMProvider.OPENAI_GPT35: ModelSettings(
                provider=LLMProvider.OPENAI_GPT35,
                enabled=True,
                max_tokens=500,
                temperature=0.8,
                timeout=25.0
            ),
            LLMProvider.GOOGLE_GEMINI_PRO: ModelSettings(
                provider=LLMProvider.GOOGLE_GEMINI_PRO,
                enabled=False,  # API 미구현
                max_tokens=700,
                temperature=0.7,
                timeout=35.0
            ),
            LLMProvider.KT_BELIEF: ModelSettings(
                provider=LLMProvider.KT_BELIEF,
                enabled=False,  # API 미구현
                max_tokens=600,
                temperature=0.7,
                timeout=40.0
            )
        }
        
        self.model_settings = default_models
    
    def load_config(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
            if not os.path.exists(self.config_file):
                self.save_config()  # 기본 설정으로 파일 생성
                return True
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 모델 설정 로드
            if 'model_settings' in config_data:
                for provider_name, settings in config_data['model_settings'].items():
                    try:
                        provider = LLMProvider(provider_name)
                        self.model_settings[provider] = ModelSettings(
                            provider=provider,
                            enabled=settings.get('enabled', True),
                            api_key=settings.get('api_key'),
                            max_tokens=settings.get('max_tokens', 600),
                            temperature=settings.get('temperature', 0.7),
                            timeout=settings.get('timeout', 30.0),
                            custom_params=settings.get('custom_params')
                        )
                    except ValueError:
                        print(f"⚠️ 알 수 없는 LLM Provider: {provider_name}")
            
            # 품질 설정 로드
            if 'quality_settings' in config_data:
                qs = config_data['quality_settings']
                self.quality_settings = QualitySettings(
                    default_level=QualityLevel(qs.get('default_level', 8)),
                    min_answer_length=qs.get('min_answer_length', 50),
                    max_answer_length=qs.get('max_answer_length', 500),
                    enable_post_processing=qs.get('enable_post_processing', True),
                    quality_check_enabled=qs.get('quality_check_enabled', True)
                )
            
            # 페르소나 설정 로드
            if 'persona_settings' in config_data:
                ps = config_data['persona_settings']
                self.persona_settings = PersonaSettings(
                    use_real_personas=ps.get('use_real_personas', True),
                    fallback_to_default=ps.get('fallback_to_default', True),
                    persona_data_path=ps.get('persona_data_path', "llm/data/candidate_personas.json"),
                    enable_persona_validation=ps.get('enable_persona_validation', True)
                )
            
            # 답변 설정 로드
            if 'answer_settings' in config_data:
                ans = config_data['answer_settings']
                self.answer_settings = AnswerSettings(
                    include_confidence_score=ans.get('include_confidence_score', True),
                    enable_answer_comparison=ans.get('enable_answer_comparison', True),
                    max_retries=ans.get('max_retries', 3),
                    enable_fallback_answers=ans.get('enable_fallback_answers', True),
                    answer_cache_enabled=ans.get('answer_cache_enabled', True),
                    cache_duration_minutes=ans.get('cache_duration_minutes', 60)
                )
            
            # 로깅 설정 로드
            if 'logging_settings' in config_data:
                ls = config_data['logging_settings']
                self.logging_settings = LoggingSettings(
                    log_level=ls.get('log_level', "INFO"),
                    log_requests=ls.get('log_requests', True),
                    log_responses=ls.get('log_responses', True),
                    log_performance=ls.get('log_performance', True),
                    log_file_path=ls.get('log_file_path', "logs/ai_candidate.log")
                )
            
            print(f"✅ 설정 파일에서 로드 완료: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            return False
    
    def save_config(self) -> bool:
        """현재 설정을 파일에 저장"""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {
                "model_settings": {
                    provider.value: {
                        "enabled": settings.enabled,
                        "api_key": settings.api_key,
                        "max_tokens": settings.max_tokens,
                        "temperature": settings.temperature,
                        "timeout": settings.timeout,
                        "custom_params": settings.custom_params
                    }
                    for provider, settings in self.model_settings.items()
                },
                "quality_settings": {
                    "default_level": self.quality_settings.default_level.value,
                    "min_answer_length": self.quality_settings.min_answer_length,
                    "max_answer_length": self.quality_settings.max_answer_length,
                    "enable_post_processing": self.quality_settings.enable_post_processing,
                    "quality_check_enabled": self.quality_settings.quality_check_enabled
                },
                "persona_settings": {
                    "use_real_personas": self.persona_settings.use_real_personas,
                    "fallback_to_default": self.persona_settings.fallback_to_default,
                    "persona_data_path": self.persona_settings.persona_data_path,
                    "enable_persona_validation": self.persona_settings.enable_persona_validation
                },
                "answer_settings": {
                    "include_confidence_score": self.answer_settings.include_confidence_score,
                    "enable_answer_comparison": self.answer_settings.enable_answer_comparison,
                    "max_retries": self.answer_settings.max_retries,
                    "enable_fallback_answers": self.answer_settings.enable_fallback_answers,
                    "answer_cache_enabled": self.answer_settings.answer_cache_enabled,
                    "cache_duration_minutes": self.answer_settings.cache_duration_minutes
                },
                "logging_settings": {
                    "log_level": self.logging_settings.log_level,
                    "log_requests": self.logging_settings.log_requests,
                    "log_responses": self.logging_settings.log_responses,
                    "log_performance": self.logging_settings.log_performance,
                    "log_file_path": self.logging_settings.log_file_path
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 설정 파일 저장 완료: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            return False
    
    def update_model_setting(self, provider: LLMProvider, **kwargs) -> bool:
        """모델 설정 업데이트"""
        try:
            if provider not in self.model_settings:
                print(f"⚠️ 모델 {provider.value}이 등록되지 않았습니다.")
                return False
            
            settings = self.model_settings[provider]
            
            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
                    print(f"✅ {provider.value} {key} 설정을 {value}로 변경")
                else:
                    print(f"⚠️ 알 수 없는 설정 항목: {key}")
            
            return True
            
        except Exception as e:
            print(f"❌ 모델 설정 업데이트 실패: {e}")
            return False
    
    def set_api_key(self, provider: LLMProvider, api_key: str) -> bool:
        """API 키 설정"""
        return self.update_model_setting(provider, api_key=api_key)
    
    def enable_model(self, provider: LLMProvider) -> bool:
        """모델 활성화"""
        return self.update_model_setting(provider, enabled=True)
    
    def disable_model(self, provider: LLMProvider) -> bool:
        """모델 비활성화"""
        return self.update_model_setting(provider, enabled=False)
    
    def get_enabled_models(self) -> List[LLMProvider]:
        """활성화된 모델 목록"""
        return [provider for provider, settings in self.model_settings.items() 
                if settings.enabled]
    
    def get_model_setting(self, provider: LLMProvider) -> Optional[ModelSettings]:
        """모델 설정 조회"""
        return self.model_settings.get(provider)
    
    def update_quality_setting(self, **kwargs) -> bool:
        """품질 설정 업데이트"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.quality_settings, key):
                    if key == 'default_level' and isinstance(value, int):
                        value = QualityLevel(value)
                    setattr(self.quality_settings, key, value)
                    print(f"✅ 품질 설정 {key}를 {value}로 변경")
                else:
                    print(f"⚠️ 알 수 없는 품질 설정 항목: {key}")
            return True
        except Exception as e:
            print(f"❌ 품질 설정 업데이트 실패: {e}")
            return False
    
    def update_persona_setting(self, **kwargs) -> bool:
        """페르소나 설정 업데이트"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.persona_settings, key):
                    setattr(self.persona_settings, key, value)
                    print(f"✅ 페르소나 설정 {key}를 {value}로 변경")
                else:
                    print(f"⚠️ 알 수 없는 페르소나 설정 항목: {key}")
            return True
        except Exception as e:
            print(f"❌ 페르소나 설정 업데이트 실패: {e}")
            return False
    
    def update_answer_setting(self, **kwargs) -> bool:
        """답변 설정 업데이트"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.answer_settings, key):
                    setattr(self.answer_settings, key, value)
                    print(f"✅ 답변 설정 {key}를 {value}로 변경")
                else:
                    print(f"⚠️ 알 수 없는 답변 설정 항목: {key}")
            return True
        except Exception as e:
            print(f"❌ 답변 설정 업데이트 실패: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보"""
        enabled_models = self.get_enabled_models()
        
        return {
            "enabled_models": [model.value for model in enabled_models],
            "default_quality_level": self.quality_settings.default_level.value,
            "persona_data_path": self.persona_settings.persona_data_path,
            "answer_cache_enabled": self.answer_settings.answer_cache_enabled,
            "logging_enabled": self.logging_settings.log_requests,
            "config_file": self.config_file
        }
    
    def validate_config(self) -> List[str]:
        """설정 유효성 검증"""
        warnings = []
        
        # 활성화된 모델이 있는지 확인
        enabled_models = self.get_enabled_models()
        if not enabled_models:
            warnings.append("활성화된 LLM 모델이 없습니다.")
        
        # API 키 확인
        for provider in enabled_models:
            settings = self.model_settings[provider]
            if not settings.api_key and provider.value.startswith('openai'):
                warnings.append(f"{provider.value} 모델의 API 키가 설정되지 않았습니다.")
        
        # 페르소나 파일 확인
        if self.persona_settings.use_real_personas:
            if not os.path.exists(self.persona_settings.persona_data_path):
                warnings.append(f"페르소나 데이터 파일을 찾을 수 없습니다: {self.persona_settings.persona_data_path}")
        
        # 로그 디렉토리 확인
        log_dir = os.path.dirname(self.logging_settings.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            warnings.append(f"로그 디렉토리가 존재하지 않습니다: {log_dir}")
        
        return warnings
    
    def reset_to_defaults(self):
        """기본 설정으로 초기화"""
        self._initialize_default_settings()
        self.quality_settings = QualitySettings()
        self.persona_settings = PersonaSettings()
        self.answer_settings = AnswerSettings()
        self.logging_settings = LoggingSettings()
        print("✅ 모든 설정이 기본값으로 초기화되었습니다.")

# 전역 설정 인스턴스
_global_config = None

def get_config() -> AICandidateConfig:
    """전역 설정 인스턴스 반환"""
    global _global_config
    if _global_config is None:
        _global_config = AICandidateConfig()
    return _global_config

def reload_config():
    """설정 재로드"""
    global _global_config
    _global_config = None
    return get_config()

if __name__ == "__main__":
    # AI 지원자 설정 관리 테스트
    print("⚙️ AI 지원자 설정 관리 테스트")
    
    # 설정 생성 및 로드
    config = AICandidateConfig("config/test_ai_candidate_config.json")
    
    # 현재 설정 확인
    print(f"\n📊 현재 설정 요약:")
    summary = config.get_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 설정 유효성 검증
    warnings = config.validate_config()
    if warnings:
        print(f"\n⚠️ 설정 경고사항:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print(f"\n✅ 설정이 유효합니다.")
    
    # 모델 설정 업데이트 테스트
    print(f"\n🔧 설정 업데이트 테스트:")
    
    # API 키 설정 (실제로는 입력받아야 함)
    # config.set_api_key(LLMProvider.OPENAI_GPT4O_MINI, "test-api-key")
    
    # 품질 설정 변경
    config.update_quality_setting(default_level=9, max_answer_length=600)
    
    # 답변 설정 변경
    config.update_answer_setting(max_retries=5, cache_duration_minutes=120)
    
    # 변경된 설정 저장
    config.save_config()
    
    print(f"\n💾 설정이 저장되었습니다.")
    
    # 전역 설정 테스트
    print(f"\n🌐 전역 설정 테스트:")
    global_config = get_config()
    print(f"전역 설정 활성화된 모델: {global_config.get_enabled_models()}")
    
    # 설정 파일 정리 (테스트용)
    import os
    if os.path.exists("config/test_ai_candidate_config.json"):
        os.remove("config/test_ai_candidate_config.json")
        print("🗑️ 테스트 설정 파일 삭제 완료")