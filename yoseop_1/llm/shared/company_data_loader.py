#!/usr/bin/env python3
"""
회사 데이터 로더
7개 회사 정보를 효율적으로 로드하고 관리하는 클래스
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class CompanyDataLoader:
    """회사 데이터 로딩 및 관리 클래스"""
    
    def __init__(self, data_path: str = None):
        """
        CompanyDataLoader 초기화
        
        Args:
            data_path: companies_data.json 파일 경로 (기본값: llm/shared/data/companies_data.json)
        """
        if not data_path:
            # 현재 파일 기준으로 상대 경로 계산
            current_dir = Path(__file__).parent
            data_path = current_dir / "data" / "companies_data.json"
        
        self.data_path = data_path
        self._companies_data = None
        self._companies_dict = None
        self._load_companies_data()
    
    def _load_companies_data(self) -> None:
        """회사 데이터를 로드합니다"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._companies_data = json.load(f)
            
            # 빠른 검색을 위한 딕셔너리 생성
            self._companies_dict = {
                company["id"]: company 
                for company in self._companies_data["companies"]
            }
            
            print(f"✅ 회사 데이터 로드 완료: {len(self._companies_dict)}개 회사")
            
        except FileNotFoundError:
            print(f"❌ 회사 데이터 파일을 찾을 수 없습니다: {self.data_path}")
            self._companies_data = {"companies": []}
            self._companies_dict = {}
        except json.JSONDecodeError as e:
            print(f"❌ 회사 데이터 파일 파싱 오류: {e}")
            self._companies_data = {"companies": []}
            self._companies_dict = {}
    
    def get_company_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 회사의 데이터를 가져옵니다
        
        Args:
            company_id: 회사 ID (예: 'naver', 'kakao', 'line', 'coupang', 'baemin', 'daangn', 'toss')
            
        Returns:
            회사 데이터 딕셔너리 또는 None
        """
        return self._companies_dict.get(company_id)
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """모든 회사 데이터를 반환합니다"""
        return self._companies_data.get("companies", [])
    
    def get_company_list(self) -> List[Dict[str, str]]:
        """회사 ID와 이름 목록을 반환합니다"""
        return [
            {"id": company["id"], "name": company["name"]} 
            for company in self._companies_data.get("companies", [])
        ]
    
    def get_company_culture(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사의 문화 정보를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("company_culture") if company else None
    
    def get_interviewer_personas(self, company_id: str) -> Optional[Dict[str, Any]]:
        """회사의 면접관 페르소나를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("interviewer_personas") if company else None
    
    def get_tech_focus(self, company_id: str) -> Optional[List[str]]:
        """회사의 기술 포커스 영역을 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("tech_focus") if company else None
    
    def get_interview_keywords(self, company_id: str) -> Optional[List[str]]:
        """회사의 면접 키워드를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("interview_keywords") if company else None
    
    def get_technical_challenges(self, company_id: str) -> Optional[List[str]]:
        """회사의 기술적 도전과제를 가져옵니다"""
        company = self.get_company_data(company_id)
        return company.get("technical_challenges") if company else None
    
    def is_valid_company(self, company_id: str) -> bool:
        """유효한 회사 ID인지 확인합니다"""
        return company_id in self._companies_dict
    
    def get_supported_companies(self) -> List[str]:
        """지원되는 회사 ID 목록을 반환합니다"""
        return list(self._companies_dict.keys())

# 전역 인스턴스 (싱글톤 패턴)
_company_loader_instance = None

def get_company_loader() -> CompanyDataLoader:
    """CompanyDataLoader 싱글톤 인스턴스를 반환합니다"""
    global _company_loader_instance
    if _company_loader_instance is None:
        _company_loader_instance = CompanyDataLoader()
    return _company_loader_instance

# 편의 함수들
def get_company_data(company_id: str) -> Optional[Dict[str, Any]]:
    """회사 데이터를 가져오는 편의 함수"""
    return get_company_loader().get_company_data(company_id)

def get_all_companies() -> List[Dict[str, Any]]:
    """모든 회사 데이터를 가져오는 편의 함수"""
    return get_company_loader().get_all_companies()

def is_valid_company(company_id: str) -> bool:
    """유효한 회사인지 확인하는 편의 함수"""
    return get_company_loader().is_valid_company(company_id)