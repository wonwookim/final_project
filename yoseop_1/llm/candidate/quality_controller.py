#!/usr/bin/env python3
"""
답변 품질 제어 시스템
사용자 설정에 따라 AI 지원자의 답변 품질을 조절
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

class QualityLevel(Enum):
    """답변 품질 레벨 - 프론트엔드 3단계에 맞춤"""
    EXCELLENT = 3    # 고급 - 탁월한 수준 (85-100점)
    AVERAGE = 2      # 중급 - 평균 수준 (55-84점)
    INADEQUATE = 1   # 초급 - 부적절한 수준 (5-54점)    # 부적절한 수준 (5-14점)

@dataclass
class QualityConfig:
    """품질 레벨별 설정"""
    level: QualityLevel
    description: str
    answer_length_min: int
    answer_length_max: int
    detail_level: str  # 'high', 'medium', 'low'
    specificity: str   # 'very_specific', 'specific', 'general', 'vague'
    professional_tone: bool
    include_examples: bool
    include_metrics: bool
    include_challenges: bool
    temperature: float
    additional_instructions: List[str]
    model_name: str

class AnswerQualityController:
    """답변 품질 제어 컨트롤러"""
    
    def __init__(self):
        self.quality_configs = self._initialize_quality_configs()
        
    def _initialize_quality_configs(self) -> Dict[QualityLevel, QualityConfig]:
        """품질 레벨별 설정 초기화 - prompt.py 기반 완전 고도화"""
        return {
            QualityLevel.EXCELLENT: QualityConfig(
                level=QualityLevel.EXCELLENT,
                description="🌟 EXCELLENT - H.U.M.A.N 프레임워크 완전 활용, 면접관에게 강한 인상을 남기는 탁월한 답변",
                
                # prompt.py 기반 정확한 길이 (초 → 자 변환: 1초당 6-7자 기준)
                answer_length_min=300,  # 50초 * 6자 = 300자
                answer_length_max=455,  # 65초 * 7자 = 455자
                
                detail_level="maximum_depth",
                specificity="highly_specific_with_metrics",
                professional_tone=True,
                include_examples=True,
                include_metrics=True,
                include_challenges=True,
                temperature=0.6,  # 창의성과 일관성의 균형
                
                # H.U.M.A.N 프레임워크 기반 고도화된 지침
                additional_instructions=[
                    "💝 Honesty: 기술나열이 아닌 진솔한 개인적 동기와 경험을 중심으로 답변하세요",
                    "🌟 Uniqueness: 다른 지원자와 차별화되는 나만의 특별한 경험과 관점을 강조하세요",
                    "⚡ Moment: 구체적이고 생생한 감정, 깨달음의 순간을 스토리로 전달하세요",
                    "❤️ Affection: 개발과 성장에 대한 진정한 열정과 애정을 자연스럽게 표현하세요",
                    "📖 Narrative: 과거→현재→미래로 이어지는 연결된 성장 스토리를 구성하세요",
                    "📊 구체적 수치와 성과를 반드시 포함하되, 맥락과 함께 설명하세요",
                    "🔍 문제-분석-해결-결과-교훈의 완전한 스토리텔링 구조를 활용하세요",
                    "🏢 회사의 가치관과 문화에 자연스럽게 연결지어 답변하세요",
                    "🎯 질문의 의도를 정확히 파악하고 그에 맞는 깊이와 관점으로 답변하세요"
                ],
                model_name="gpt-4o"  # 최고 품질 모델 사용
            ),
            
            QualityLevel.AVERAGE: QualityConfig(
                level=QualityLevel.AVERAGE,
                description="📝 AVERAGE - 기본 H.U.M.A.N 요소 활용, 성실하고 체계적인 중급 수준 답변",
                
                # 중급 레벨 길이 (35-50초 기준)
                answer_length_min=210,  # 35초 * 6자 = 210자
                answer_length_max=350,  # 50초 * 7자 = 350자
                
                detail_level="moderate_depth",
                specificity="general_with_examples",
                professional_tone=True,
                include_examples=True,  # 예시는 포함하되 간단하게
                include_metrics=False,  # 수치보다는 정성적 설명
                include_challenges=False,  # 성공 위주로
                temperature=0.7,  # 적절한 창의성
                
                # 기본 H.U.M.A.N 활용 지침
                additional_instructions=[
                    "💝 Honesty: 솔직하고 진실한 개인 경험을 바탕으로 답변하세요",
                    "📖 Narrative: 과거 경험 → 현재 상황 → 미래 계획 순서로 체계적으로 구성하세요",
                    "🎯 관련된 경험이나 사례를 1-2개 포함하여 구체성을 높이세요",
                    "🤝 성실하고 진지한 태도로 면접관과 소통하는 자세를 보여주세요",
                    "📚 기본적인 전문성을 드러내되 과도하지 않게 균형을 맞추세요",
                    "🔄 질문에 직접적으로 답변한 후 간단한 부연 설명을 추가하세요"
                ],
                model_name="gpt-4o-mini"  # 효율적인 모델 사용
            ),
            
            QualityLevel.INADEQUATE: QualityConfig(
                level=QualityLevel.INADEQUATE,
                description="🌱 INADEQUATE - 기본 구조만 유지, 준비 부족하지만 성장 의지가 느껴지는 초급 답변",
                
                # 초급 레벨 길이 (20-35초 기준)
                answer_length_min=120,  # 20초 * 6자 = 120자
                answer_length_max=245,  # 35초 * 7자 = 245자
                
                detail_level="surface_level",
                specificity="vague_general",
                professional_tone=False,  # 자연스럽고 솔직한 톤
                include_examples=False,   # 구체적 예시 부족
                include_metrics=False,    # 수치 데이터 없음
                include_challenges=False, # 어려움 언급 회피
                temperature=0.9,  # 높은 변동성으로 어색함 표현
                
                # 초보자 수준 지침
                additional_instructions=[
                    "😅 약간의 긴장감과 준비 부족한 느낌을 자연스럽게 표현하세요",
                    "🗣️ '~것 같습니다', '~하고 싶습니다' 등 불확실한 표현을 적절히 사용하세요",
                    "📝 기본적인 정보 전달에 집중하되 깊이 있는 분석은 피하세요",
                    "💭 구체적인 사례보다는 일반적이고 추상적인 내용으로 답변하세요",
                    "🌱 '더 배우고 싶다', '노력하겠다' 등 성장 의지는 분명히 표현하세요",
                    "🤔 질문에 대해 완전히 확신하지 못하는 듯한 뉘앙스를 포함하세요"
                ],
                model_name="gpt-4o-mini"  # 기본 모델 사용
            )
        }
    
    def get_quality_config(self, level: QualityLevel) -> QualityConfig:
        """품질 레벨에 따른 설정 반환"""
        return self.quality_configs.get(level, self.quality_configs[QualityLevel.AVERAGE])
    
    def generate_quality_prompt(self, base_prompt: str, level: QualityLevel, question_type: str = "") -> str:
        """품질 레벨에 맞는 프롬프트 생성 - 고도화된 가이드라인 적용"""
        config = self.get_quality_config(level)
        
        # 레벨별 기본 품질 지침
        quality_instructions = f"""

=== 🎯 답변 품질 목표 ({level.name}) ===
{config.description}

=== 📏 기본 답변 가이드라인 ===
• 답변 길이: {config.answer_length_min}-{config.answer_length_max}자 정도
• 세부 정도: {config.detail_level}
• 구체성 수준: {config.specificity}
• 전문적 톤: {'필수 사용' if config.professional_tone else '자연스럽게'}
• 구체적 예시: {'반드시 포함' if config.include_examples else '선택적 포함'}
• 수치/성과: {'구체적 수치 포함' if config.include_metrics else '정성적 설명'}
• 도전/어려움: {'실패 경험도 포함' if config.include_challenges else '성공 위주'}

=== 🚀 품질 향상 지침 ==="""
        
        for instruction in config.additional_instructions:
            quality_instructions += f"• {instruction}"
        
        # 자기소개 반복 방지 강력 지침
        if question_type != "자기소개":
            quality_instructions += f"""
            
=== 🚫 중요한 답변 규칙 ===
• **절대 금지**: "안녕하세요", "저는 춘식이라고 합니다" 같은 인사나 자기소개 반복
• **바로 시작**: 질문에 대한 답변으로 바로 시작하세요
• **자연스러운 연결**: 이전 대화가 이어지는 것처럼 자연스럽게 답변
• **예시**: "{question_type}" 질문이라면 "그 부분에 대해서는...", "제 경험으로는...", "저는 생각하기에..." 등으로 시작"""
        
        # 질문 유형별 고도화된 가이드 추가
        if question_type:
            quality_instructions += f"\n\n=== 🎭 {question_type} 질문 특화 전략 ===\n"
            type_guide = self._get_question_type_guide(question_type, level)
            quality_instructions += type_guide
        
        # 레벨별 마무리 당부
        level_reminders = {
            QualityLevel.EXCELLENT: "\n\n⭐ **EXCELLENT 레벨**: 면접관에게 강한 인상을 남길 수 있는 깊이와 진정성을 보여주세요!",
            QualityLevel.AVERAGE: "\n\n📝 **AVERAGE 레벨**: 성실하고 체계적인 답변으로 기본기를 탄탄히 보여주세요.",
            QualityLevel.INADEQUATE: "\n\n🌱 **INADEQUATE 레벨**: 간단하더라도 솔직하고 성장 의지가 느껴지는 답변을 해주세요."
        }
        
        quality_instructions += level_reminders.get(level, "")
        
        return f"{base_prompt}\n{quality_instructions}"
    
    def _get_question_type_guide(self, question_type: str, level: QualityLevel) -> str:
        """질문 유형별 품질 가이드 - prompt.py 기반 고도화된 가이드라인"""
        
        guides = {
            "자기소개": {
                QualityLevel.EXCELLENT: """
=== H.U.M.A.N 프레임워크 완전 활용 ===
**💝 Honesty**: 기술나열 말고 진짜 개인적 동기 → 진솔한 개발 시작 이유
**🌟 Uniqueness**: 나만의 특별한 경험 → 다른 사람과 차별화되는 독특한 배경
**⚡ Moment**: 구체적이고 생생한 감정과 깨달음 → 인생을 바꾼 결정적 순간
**❤️ Affection**: 진짜 열정과 따뜻함 → 개발과 성장에 대한 진심어린 애정
**📖 Narrative**: 과거 → 현재 → 미래로 자연스럽게 연결된 스토리

**답변 구조**: 따뜻한 인사 → 개인적 동기 → 생생한 경험 → 진솔한 미래 비전
**답변 길이**: 50-65초 분량 (300-400자)
**답변 톤**: 진정성 있고 따뜻한 사람의 목소리로
**핵심**: 직무별 정체성 DNA와 개인 경험을 유기적으로 연결""",

                QualityLevel.AVERAGE: """
=== 기본 H.U.M.A.N 요소 활용 ===
**💝 Honesty**: 솔직한 지원 동기
**📖 Narrative**: 과거 경험 → 현재 상황 → 미래 계획 순서로 구성

**답변 구조**: 간단한 인사 → 주요 경험 → 지원 이유 → 포부
**답변 길이**: 35-50초 분량 (200-300자)  
**답변 톤**: 자연스럽고 성실한 태도
**핵심**: 기본적인 개인 정보와 경험을 체계적으로 정리""",

                QualityLevel.INADEQUATE: """
=== 기본 구조만 유지 ===
**답변 구조**: 이름 → 간단한 배경 → 지원 이유
**답변 길이**: 20-35초 분량 (100-200자)
**답변 톤**: 약간 긴장되고 준비 부족한 느낌
**핵심**: 기본적인 정보 전달에만 집중, 깊이 있는 내용 부족"""
            },
            
            "기술": {
                QualityLevel.EXCELLENT: """
=== 기술 특화 H.U.M.A.N 프레임워크 ===
**💝 Honesty**: 기술 과시가 아닌 진솔한 학습 여정 → 어려웠던 점과 한계 인정
**🌟 Uniqueness**: 남들과 다른 나만의 기술적 접근 → 창의적 해결책이나 독특한 관점
**⚡ Moment**: 기술적 성장의 결정적 순간들 → 브레이크스루, 실패와 극복, 성취감
**❤️ Affection**: 기술과 문제 해결에 대한 진심 → 지속적 관심과 적용 의지
**📖 Narrative**: 기술 학습과 성장의 연결된 이야기 → 과거-현재-미래 발전 계획

**3가지 답변 스타일 중 선택**:
1. 깊이 우선: 특정 기술 심층 분석 + 전문적 인사이트
2. 폭넓은 접근: 다양한 기술 조합 + 시너지 효과
3. 실무 중심: 프로젝트 성과 + 구체적 문제 해결

**답변 길이**: 45-70초 분량 (250-350자)
**필수 포함**: 구체적 수치, 문제-해결-결과 구조, 기술적 판단 근거""",

                QualityLevel.AVERAGE: """
=== 기본 기술 경험 중심 ===
**핵심 요소**: 사용 기술 → 관련 프로젝트 → 배운 점 → 향후 계획
**답변 길이**: 30-50초 분량 (180-280자)
**포함 내용**: 주요 기술 스택, 간단한 프로젝트 예시, 학습 과정
**톤**: 기술에 대한 관심과 성장 의지 표현""",

                QualityLevel.INADEQUATE: """
=== 기본 기술 나열 수준 ===
**구조**: 알고 있는 기술 → 간단한 사용 경험
**답변 길이**: 20-40초 분량 (120-200자)  
**특징**: 구체적 경험 부족, 일반적인 기술 설명 위주
**톤**: 약간의 불확실함, "공부해보겠습니다" 식 마무리"""
            },
            
            "지원동기": {
                QualityLevel.EXCELLENT: """
=== 동기 특화 H.U.M.A.N 접근 ===
**💝 Honesty**: 진짜 개인적 동기, 단순한 취업이 아닌 진심어린 이유
**🌟 Uniqueness**: 회사에 관심을 갖게 된 구체적 순간과 특별한 계기
**⚡ Moment**: 회사와의 연결점을 발견한 구체적 순간과 감정
**❤️ Affection**: 회사 가치관과 문화에 대한 진정한 공감과 애정
**📖 Narrative**: 개인 목표 → 회사 발견 → 구체적 기여 방안 → 장기 비전

**답변 구조**: 개인적 계기 → 회사 분석 → 가치 공감 → 기여 방안 → 성장 비전
**답변 길이**: 55-70초 분량 (320-400자)
**핵심**: 회사 리서치 기반 구체적 연결점과 진정성 있는 미래 계획""",

                QualityLevel.AVERAGE: """
=== 기본 동기 설명 ===
**구조**: 회사 관심 이유 → 개인 목표와의 연결 → 기여하고 싶은 점
**답변 길이**: 40-55초 분량 (240-320자)
**포함**: 회사에 대한 기본 이해, 개인적 목표, 간단한 기여 방안
**톤**: 성실하고 진지한 태도""",

                QualityLevel.INADEQUATE: """
=== 일반적인 지원 이유 ===
**구조**: 회사가 좋아 보여서 → 성장하고 싶어서 → 열심히 하겠다
**답변 길이**: 25-40초 분량 (150-240자)
**특징**: 구체성 부족, 일반적인 답변, 준비 부족한 느낌
**톤**: "~것 같습니다", "~하고 싶습니다" 등 불확실한 표현"""
            },
            
            "인성": {
                QualityLevel.EXCELLENT: """
=== 인성 특화 H.U.M.A.N 심층 분석 ===
**💝 Honesty**: 완벽한 사람 연기가 아닌 진솔한 자기 인식과 성장 과정
- 약점 인정: 개선하고 싶은 부분을 솔직하게 인정하고 노력 과정 공유
- 실패 경험: 어려웠던 상황에서의 진실한 감정과 배움
- 진짜 가치관: 개발자로서, 사람으로서의 진심어린 신념

**🌟 Uniqueness**: 남들과 다른 나만의 관점과 성장 방식
- 독특한 시각: 문제를 바라보는 나만의 특별한 관점
- 개인적 배경: 나만이 가진 특별한 경험이나 환경
- 차별화된 해결법: 나만의 독특한 문제 해결 방식

**⚡ Moment**: 인생이나 가치관을 바꾼 구체적이고 결정적인 순간들
- 전환점 순간: 생각이나 행동이 바뀐 결정적 계기
- 깨달음의 순간: 중요한 것을 깨닫게 된 구체적 상황
- 감정적 순간: 그때 느꼈던 생생한 감정과 반응

**❤️ Affection**: 성장과 사람들에 대한 진심어린 애정과 관심
- 자기 개선에 대한 열정: 더 나은 사람이 되고 싶은 진심
- 사람에 대한 관심: 함께 일하는 사람들에 대한 진심어린 마음
- 긍정적 영향: 주변에 좋은 영향을 주고 싶은 마음

**📖 Narrative**: 과거 경험 → 현재 성장 → 미래 비전의 일관된 성장 스토리
- 과거: 어려움이나 실패를 겪었던 시점과 그때의 모습
- 현재: 그 경험들을 통해 성장하고 변화한 현재 모습
- 미래: 앞으로 더 발전하고 싶은 구체적 방향과 노력

**3가지 답변 스타일 중 성격에 맞게 선택**:
1. 감정 중심: 내면의 감정과 성찰에 집중한 진솔한 이야기
2. 논리 중심: 체계적 분석과 개선 계획 중심의 구조적 접근
3. 경험 중심: 구체적 사례와 생생한 스토리텔링 활용

**답변 길이**: 40-60초 분량 (220-320자)
**답변 톤**: 진정성 있고 성찰적이면서도 성장 의지가 느껴지는 모습
**핵심**: 약점을 성장 기회로 바꾸는 건설적 사고와 구체적 개선 노력""",

                QualityLevel.AVERAGE: """
=== 기본 인성 질문 답변 구조 ===
**핵심 요소**: 솔직한 자기 인식 → 관련 경험 → 배운 점 → 개선 노력
**답변 길이**: 30-45초 분량 (170-260자)
**포함 내용**: 개인적 특성, 간단한 경험 사례, 성장하려는 의지
**톤**: 성실하고 진솔한 태도로 자연스럽게 표현
**구조**: 질문에 대한 직접 답변 → 관련 경험 → 현재 개선 노력 → 미래 계획""",

                QualityLevel.INADEQUATE: """
=== 일반적인 인성 답변 수준 ===
**구조**: 질문에 대한 간단한 답변 → 일반적인 설명
**답변 길이**: 20-35초 분량 (110-200자)
**특징**: 구체적 경험 부족, 일반론적 답변 위주
**톤**: 약간 준비 부족한 느낌, "노력하겠습니다" 식 마무리
**내용**: 추상적 설명이 많고 개인적 경험이나 구체적 사례 부족"""
            },
            
            "협업": {
                QualityLevel.EXCELLENT: """
=== 협업 특화 H.U.M.A.N 스토리 ===
**💝 Honesty**: 협업에서의 실제 어려움과 갈등 상황 솔직하게 인정
**🌟 Uniqueness**: 나만의 독특한 협업 방식이나 커뮤니케이션 스타일
**⚡ Moment**: 팀워크로 위기를 극복하거나 큰 성과를 낸 구체적 순간
**❤️ Affection**: 팀원들과 함께 성장하는 것에 대한 진심어린 기쁨
**📖 Narrative**: 협업 능력의 성장 과정과 앞으로의 발전 방향

**답변 구조**: 협업 철학 → 구체적 사례 → 갈등 해결 → 팀 성과 → 배운 점
**답변 길이**: 40-60초 분량 (220-320자)
**핵심**: 구체적 협업 도구, 갈등 해결 경험, 팀 성과 기여도""",

                QualityLevel.AVERAGE: """
=== 기본 협업 경험 ===
**구조**: 협업 스타일 → 팀 프로젝트 경험 → 역할과 기여
**답변 길이**: 30-45초 분량 (180-270자)
**포함**: 기본적인 협업 방식, 간단한 팀 경험, 소통 방법
**톤**: 협조적이고 긍정적인 태도""",

                QualityLevel.INADEQUATE: """
=== 일반적인 협업 언급 ===
**구조**: 팀워크 중요하다고 생각 → 잘 맞춰서 일함 → 소통 잘함
**답변 길이**: 20-35초 분량 (120-210자)
**특징**: 구체적 사례 부족, 일반론적 답변
**톤**: "잘할 수 있을 것 같다", "노력하겠다" 등 모호한 표현"""
            }
        }
        
        question_guides = guides.get(question_type, {})
        return question_guides.get(level, "질문에 성실히 답변하세요.")
    
    
    
    
    
    def process_complete_answer(self, raw_answer: str, quality_level: QualityLevel, question_type: str = "") -> str:
        """답변에 대한 완전한 품질 처리 (model.py에서 이동한 로직)"""
        if not raw_answer or not raw_answer.strip():
            return "죄송합니다, 답변을 생성할 수 없었습니다."
        
        # 기본 정리
        processed = raw_answer.strip()
        
        # 품질 레벨에 따른 설정 가져오기
        config = self.get_quality_config(quality_level)
        
        # 길이 조정
        if len(processed) > config.answer_length_max:
            # 문장 단위로 자르기
            sentences = processed.split('. ')
            total_length = 0
            result_sentences = []
            
            for sentence in sentences:
                if total_length + len(sentence) <= config.answer_length_max:
                    result_sentences.append(sentence)
                    total_length += len(sentence) + 2  # '. ' 포함
                else:
                    break
            
            processed = '. '.join(result_sentences)
            if not processed.endswith('.'):
                processed += '.'
        
        # 최소 길이 확보
        elif len(processed) < config.answer_length_min:
            # 품질 레벨에 따른 추가 내용 생성 가이드
            if config.include_examples:
                processed += " 구체적인 예시를 통해 더 자세히 설명드리겠습니다."
            elif config.include_challenges:
                processed += " 이 과정에서 겪었던 도전과 그 해결 방법도 중요한 경험이었습니다."
        
        # 전문적 톤 조정
        if config.professional_tone:
            # 존댓말과 전문적 표현 강화
            processed = self._enhance_professional_tone(processed)
        
        # 품질 레벨별 마무리 조정
        processed = self._apply_quality_finishing(processed, quality_level)
        
        return processed
    
    def _enhance_professional_tone(self, text: str) -> str:
        """전문적 톤으로 조정"""
        # 기본적인 톤 조정 (간단한 규칙 기반)
        replacements = {
            '그냥': '단순히',
            '되게': '매우',
            '진짜': '정말로',
            '좀': '조금',
            '엄청': '매우'
        }
        
        result = text
        for informal, formal in replacements.items():
            result = result.replace(informal, formal)
        
        return result
    
    def _apply_quality_finishing(self, text: str, quality_level: QualityLevel) -> str:
        """품질 레벨별 마무리 조정 - 3단계 시스템"""
        if quality_level == QualityLevel.EXCELLENT:
            # 높은 품질: 명확하고 자신감 있는 마무리
            if not text.endswith(('.', '습니다', '입니다')):
                text += '.'
        elif quality_level == QualityLevel.INADEQUATE:
            # 낮은 품질: 약간의 불확실성 표현
            uncertain_endings = ['요.', '것 같습니다.', '생각합니다.']
            if not any(text.endswith(ending) for ending in uncertain_endings):
                if not text.endswith('.'):
                    text += '.'
        else:  # AVERAGE
            # 중간 품질: 자연스러운 마무리
            if not text.endswith('.'):
                text += '.'
        
        return text
    
    

if __name__ == "__main__":
    # 답변 품질 제어 시스템 테스트
    print("🎯 답변 품질 제어 시스템 테스트")
    
    controller = AnswerQualityController()
    
    # 품질 레벨별 설정 확인
    print("\n📊 품질 레벨별 설정:")
    for level in [QualityLevel.EXCELLENT, QualityLevel.AVERAGE, QualityLevel.INADEQUATE]:
        config = controller.get_quality_config(level)
        print(f"\n{level.value}점 ({level.name}):")
        print(f"  설명: {config.description}")
        print(f"  답변 길이: {config.answer_length_min}-{config.answer_length_max}자")
        print(f"  온도: {config.temperature}")
        print(f"  설명: {config.description}")
    
    # 프롬프트 생성 테스트
    base_prompt = "네이버 백엔드 개발자 지원 면접에서 '간단한 자기소개를 해주세요'라는 질문에 답변하세요."
    
    print(f"\n📝 품질별 프롬프트 예시 (자기소개 질문):")
    for level in [QualityLevel.EXCELLENT, QualityLevel.AVERAGE, QualityLevel.INADEQUATE]:
        quality_prompt = controller.generate_quality_prompt(base_prompt, level, "자기소개")
        print(f"\n{level.value}점 수준 프롬프트:")
        print("=" * 50)
        print(quality_prompt[:200] + "..." if len(quality_prompt) > 200 else quality_prompt)