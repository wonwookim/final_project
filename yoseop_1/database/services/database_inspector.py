"""
Supabase 데이터베이스 구조 확인 도구
"""

from database.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def inspect_database():
    """현재 데이터베이스 구조 확인"""
    try:
        client = get_supabase_client()
        
        print("🔍 Supabase 데이터베이스 구조 확인 중...")
        
        # 현재 존재하는 테이블 목록 조회
        tables_query = """
        SELECT table_name, table_schema
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        
        result = client.rpc('sql_query', {'query': tables_query}).execute()
        
        if result.data:
            print("\n📋 현재 존재하는 테이블들:")
            for table in result.data:
                print(f"  - {table['table_name']}")
        else:
            print("\n📋 현재 public 스키마에 테이블이 없습니다.")
            
        return result.data
        
    except Exception as e:
        print(f"❌ 데이터베이스 구조 확인 실패: {str(e)}")
        return None

if __name__ == "__main__":
    inspect_database()