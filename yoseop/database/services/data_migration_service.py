"""
로컬 JSON 데이터를 Supabase 데이터베이스로 마이그레이션하는 서비스
기존 테이블 구조를 최대한 활용하면서 데이터 이전
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from database.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class DataMigrationService:
    """데이터 마이그레이션 서비스"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_path = os.path.join(self.project_root, 'llm', 'data')
    
    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """JSON 파일 로드"""
        file_path = os.path.join(self.data_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 파일 로드 실패 ({filename}): {str(e)}")
            return {}
    
    # ===================
    # 회사 데이터 마이그레이션
    # ===================
    
    async def migrate_companies(self) -> bool:
        """회사 데이터 마이그레이션"""
        try:
            print("🏢 회사 데이터 마이그레이션 시작...")
            
            # 로컬 회사 데이터 로드
            companies_data = self.load_json_file('companies_data.json')
            if not companies_data.get('companies'):
                print("❌ 회사 데이터를 찾을 수 없습니다.")
                return False
            
            # 기존 회사 데이터 확인
            existing_companies = self.client.table('company').select('company_id, name').execute()
            existing_names = {comp['name'] for comp in existing_companies.data} if existing_companies.data else set()
            
            migrated_count = 0
            for company in companies_data['companies']:
                company_name = company['name']
                
                # 이미 존재하는 회사는 스킵
                if company_name in existing_names:
                    print(f"⏭️  {company_name} - 이미 존재함, 스킵")
                    continue
                
                # 새 회사 데이터 준비
                company_data = {
                    'name': company_name,
                    'talent_profile': company.get('talent_profile', ''),
                    'core_competencies': json.dumps(company.get('core_competencies', []), ensure_ascii=False),
                    'tech_focus': json.dumps(company.get('tech_focus', []), ensure_ascii=False),
                    'interview_keywords': json.dumps(company.get('interview_keywords', []), ensure_ascii=False),
                    'question_direction': company.get('question_direction', ''),
                    'company_culture': json.dumps(company.get('company_culture', {}), ensure_ascii=False),
                    'technical_challenges': json.dumps(company.get('technical_challenges', []), ensure_ascii=False)
                }
                
                # 회사 데이터 삽입
                result = self.client.table('company').insert(company_data).execute()
                
                if result.data:
                    print(f"✅ {company_name} - 마이그레이션 완료")
                    migrated_count += 1
                    
                    # 포지션 데이터도 함께 생성 (기본 포지션들)
                    await self._create_default_positions(result.data[0]['company_id'], company_name)
                else:
                    print(f"❌ {company_name} - 마이그레이션 실패")
            
            print(f"🎉 회사 데이터 마이그레이션 완료: {migrated_count}개 회사")
            return True
            
        except Exception as e:
            logger.error(f"회사 데이터 마이그레이션 실패: {str(e)}")
            print(f"❌ 회사 데이터 마이그레이션 실패: {str(e)}")
            return False
    
    async def _create_default_positions(self, company_id: int, company_name: str):
        """기본 포지션 생성 (position 테이블은 company_id 없이 독립적으로 관리)"""
        default_positions = [
            "백엔드 개발자",
            "프론트엔드 개발자", 
            "풀스택 개발자",
            "데이터 엔지니어",
            "AI/ML 엔지니어",
            "DevOps 엔지니어",
            "모바일 개발자"
        ]
        
        try:
            for position_name in default_positions:
                # position 테이블은 company_id 없이 position_name만 저장
                position_data = {
                    'position_name': position_name
                }
                
                # 이미 존재하는 포지션인지 확인 (position_name으로만)
                existing = self.client.table('position').select('position_id').eq('position_name', position_name).execute()
                
                if not existing.data:
                    result = self.client.table('position').insert(position_data).execute()
                    if result.data:
                        print(f"  ✅ 포지션 생성: {position_name}")
                else:
                    print(f"  ⏭️  포지션 이미 존재: {position_name}")
                    
        except Exception as e:
            logger.error(f"기본 포지션 생성 실패 ({company_name}): {str(e)}")
            print(f"❌ 포지션 생성 실패: {str(e)}")
    
    # ===================
    # 고정 질문 마이그레이션
    # ===================
    
    async def migrate_fixed_questions(self) -> bool:
        """고정 질문 데이터 마이그레이션"""
        try:
            print("❓ 고정 질문 데이터 마이그레이션 시작...")
            
            # 로컬 질문 데이터 로드
            questions_data = self.load_json_file('fixed_questions.json')
            if not questions_data:
                print("❌ 고정 질문 데이터를 찾을 수 없습니다.")
                return False
            
            # 기존 질문 확인
            existing_questions = self.client.table('fix_question').select('question_id').execute()
            existing_ids = {q['question_id'] for q in existing_questions.data} if existing_questions.data else set()
            
            migrated_count = 0
            
            # 각 섹션별로 질문 마이그레이션
            for section_name, questions in questions_data.items():
                if not isinstance(questions, list):
                    continue
                    
                print(f"📝 {section_name} 섹션 처리 중...")
                
                for question in questions:
                    question_id = question.get('question_id')
                    
                    # 이미 존재하는 질문은 스킵
                    if question_id in existing_ids:
                        continue
                    
                    # 질문 데이터 준비
                    question_data = {
                        'question_index': question.get('question_id', 0),
                        'question_content': question.get('content', ''),
                        'question_intent': question.get('intent', ''),
                        'question_level': str(question.get('level', 1))
                    }
                    
                    # 질문 삽입
                    result = self.client.table('fix_question').insert(question_data).execute()
                    
                    if result.data:
                        migrated_count += 1
            
            print(f"🎉 고정 질문 마이그레이션 완료: {migrated_count}개 질문")
            return True
            
        except Exception as e:
            logger.error(f"고정 질문 마이그레이션 실패: {str(e)}")
            print(f"❌ 고정 질문 마이그레이션 실패: {str(e)}")
            return False
    
    # ===================
    # AI 후보자 데이터 마이그레이션
    # ===================
    
    async def migrate_ai_candidates(self) -> bool:
        """AI 후보자 데이터 마이그레이션"""
        try:
            print("🤖 AI 후보자 데이터 마이그레이션 시작...")
            
            # 로컬 페르소나 데이터 로드
            personas_data = self.load_json_file('candidate_personas.json')
            if not personas_data.get('personas'):
                print("❌ AI 후보자 데이터를 찾을 수 없습니다.")
                return False
            
            migrated_count = 0
            
            for company_key, persona in personas_data['personas'].items():
                try:
                    # 회사 ID 찾기
                    company_result = self.client.table('company').select('company_id').ilike('name', f'%{company_key}%').execute()
                    
                    if not company_result.data:
                        print(f"⚠️  {company_key} 회사를 찾을 수 없습니다.")
                        continue
                    
                    company_id = company_result.data[0]['company_id']
                    
                    # 기본 포지션 ID 찾기 (백엔드 개발자) - position 테이블은 company와 독립적
                    position_result = self.client.table('position').select('position_id').eq('position_name', '백엔드 개발자').execute()
                    
                    if not position_result.data:
                        print(f"⚠️  백엔드 개발자 포지션을 찾을 수 없습니다. 먼저 포지션을 생성합니다.")
                        # 포지션이 없으면 생성
                        create_result = self.client.table('position').insert({'position_name': '백엔드 개발자'}).execute()
                        if create_result.data:
                            position_id = create_result.data[0]['position_id']
                            print(f"✅ 백엔드 개발자 포지션 생성 완료 (ID: {position_id})")
                        else:
                            print(f"❌ 백엔드 개발자 포지션 생성 실패")
                            continue
                    else:
                        position_id = position_result.data[0]['position_id']
                    
                    # AI 이력서 데이터 준비
                    ai_resume_data = {
                        'title': f"{persona['name']} - {company_key} 경력 5년차",
                        'content': self._format_persona_content(persona),
                        'position_id': position_id
                    }
                    
                    # 중복 체크
                    existing = self.client.table('ai_resume').select('ai_resume_id').eq('position_id', position_id).eq('title', ai_resume_data['title']).execute()
                    
                    if not existing.data:
                        result = self.client.table('ai_resume').insert(ai_resume_data).execute()
                        
                        if result.data:
                            print(f"✅ {persona['name']} ({company_key}) - AI 이력서 생성 완료")
                            migrated_count += 1
                        else:
                            print(f"❌ {persona['name']} ({company_key}) - AI 이력서 생성 실패")
                    else:
                        print(f"⏭️  {persona['name']} ({company_key}) - 이미 존재함, 스킵")
                
                except Exception as e:
                    logger.error(f"AI 후보자 마이그레이션 실패 ({company_key}): {str(e)}")
            
            print(f"🎉 AI 후보자 마이그레이션 완료: {migrated_count}개 이력서")
            return True
            
        except Exception as e:
            logger.error(f"AI 후보자 마이그레이션 실패: {str(e)}")
            print(f"❌ AI 후보자 마이그레이션 실패: {str(e)}")
            return False
    
    def _format_persona_content(self, persona: Dict[str, Any]) -> str:
        """페르소나 데이터를 이력서 형태로 포맷팅"""
        content = f"""
# {persona.get('name', 'AI 후보자')} 이력서

## 기본 정보
- 경력: {persona.get('background', {}).get('total_experience', '5년')}
- 현재 직책: {persona.get('background', {}).get('current_position', '시니어 개발자')}
- 학력: {', '.join(persona.get('background', {}).get('education', []))}

## 기술 스택
{', '.join(persona.get('technical_skills', []))}

## 주요 프로젝트
"""
        
        projects = persona.get('projects', [])
        for i, project in enumerate(projects[:3], 1):  # 상위 3개 프로젝트만
            content += f"""
### {i}. {project.get('name', '프로젝트')}
- **기간**: {project.get('period', '')}
- **역할**: {project.get('role', '')}
- **팀 규모**: {project.get('team_size', '')}
- **기술 스택**: {', '.join(project.get('tech_stack', []))}
- **주요 성과**: 
  {chr(10).join(f'  - {achievement}' for achievement in project.get('achievements', [])[:3])}
"""
        
        return content.strip()
    
    # ===================
    # 전체 마이그레이션 실행
    # ===================
    
    async def run_full_migration(self) -> Dict[str, bool]:
        """전체 데이터 마이그레이션 실행"""
        print("🚀 데이터 마이그레이션 시작...")
        print("=" * 50)
        
        results = {}
        
        # 1. 회사 데이터 마이그레이션
        results['companies'] = await self.migrate_companies()
        
        # 2. 고정 질문 마이그레이션  
        results['fixed_questions'] = await self.migrate_fixed_questions()
        
        # 3. AI 후보자 마이그레이션
        results['ai_candidates'] = await self.migrate_ai_candidates()
        
        print("=" * 50)
        print("🎯 마이그레이션 결과:")
        for task, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"  {task}: {status}")
        
        return results
    
    # ===================
    # 데이터 검증
    # ===================
    
    async def validate_migration(self) -> Dict[str, int]:
        """마이그레이션된 데이터 검증"""
        try:
            print("🔍 데이터 검증 중...")
            
            results = {}
            
            # 회사 수 확인
            companies = self.client.table('company').select('company_id').execute()
            results['companies'] = len(companies.data) if companies.data else 0
            
            # 포지션 수 확인
            positions = self.client.table('position').select('position_id').execute()
            results['positions'] = len(positions.data) if positions.data else 0
            
            # 고정 질문 수 확인
            questions = self.client.table('fix_question').select('question_id').execute()
            results['fixed_questions'] = len(questions.data) if questions.data else 0
            
            # AI 이력서 수 확인
            ai_resumes = self.client.table('ai_resume').select('ai_resume_id').execute()
            results['ai_resumes'] = len(ai_resumes.data) if ai_resumes.data else 0
            
            print("📊 현재 데이터베이스 상태:")
            for table, count in results.items():
                print(f"  {table}: {count}개")
            
            return results
            
        except Exception as e:
            logger.error(f"데이터 검증 실패: {str(e)}")
            return {}

# 전역 서비스 인스턴스
migration_service = DataMigrationService()