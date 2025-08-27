"""
MySQL 기반 인기 질문 관리자
- 5회 이상 검색된 질문을 MySQL에 저장
- 인기 질문 통계 및 관리
"""

import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os
import time
from .enhanced_logger import get_enhanced_logger

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger()

class PopularQuestionManager:
    """인기 질문 관리자"""
    
    def __init__(self):
        """MySQL 연결 설정"""
        self.connection = None
        self.connect_to_database()
        self.create_tables()
    
    def connect_to_database(self):
        """MySQL 데이터베이스 연결"""
        try:
            start_time = time.time()
            host = os.getenv('MYSQL_HOST', 'localhost')
            port = os.getenv('MYSQL_PORT', 3306)
            database = os.getenv('MYSQL_DB', 'rag_qa_system')
            user = os.getenv('MYSQL_USER', 'root')
            
            # 환경변수나 기본값으로 DB 설정
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=os.getenv('MYSQL_PASSWORD', ''),
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                autocommit=True
            )
            
            if self.connection.is_connected():
                duration = time.time() - start_time
                enhanced_logger.system_operation(
                    "INIT", "MYSQL", "SUCCESS",
                    details={
                        "host": f"{host}:{port}",
                        "database": database,
                        "user": user,
                        "connection_time": f"{duration:.3f}s"
                    }
                )
            
        except Error as e:
            enhanced_logger.system_operation(
                "INIT", "MYSQL", "FAILED", error=str(e)
            )
            self.connection = None
    
    def is_connected(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        try:
            return self.connection and self.connection.is_connected()
        except:
            return False
    
    def create_tables(self):
        """필요한 테이블 생성"""
        if not self.is_connected():
            enhanced_logger.system_operation(
                "CREATE_TABLES", "MYSQL", "SKIPPED",
                error="MySQL not connected"
            )
            return
        
        try:
            start_time = time.time()
            cursor = self.connection.cursor()
            
            # 인기 질문 테이블 생성
            create_popular_questions_table = """
            CREATE TABLE IF NOT EXISTS popular_questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                query TEXT NOT NULL,
                query_hash VARCHAR(32) NOT NULL UNIQUE,
                search_count INT DEFAULT 1,
                first_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                similarity_score FLOAT DEFAULT 0.0,
                category VARCHAR(50) DEFAULT 'general',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_query_hash (query_hash),
                INDEX idx_search_count (search_count),
                INDEX idx_category (category),
                INDEX idx_last_searched (last_searched_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_popular_questions_table)
            
            # 질문 카테고리 테이블 생성
            create_question_categories_table = """
            CREATE TABLE IF NOT EXISTS question_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_question_categories_table)
            
            # 기본 카테고리 데이터 삽입
            insert_default_categories = """
            INSERT IGNORE INTO question_categories (name, display_name, description) VALUES
            ('card', '카드 관련', 'BC카드 발급, 이용, 해지 관련 질문'),
            ('personal', '개인화', '특정 고객 개인정보 관련 질문'),
            ('general', '일반', '기타 일반적인 질문'),
            ('complaint', '민원', '민원 접수 및 고객 불만 관련'),
            ('service', '서비스', '부가서비스 및 혜택 관련')
            """
            
            cursor.execute(insert_default_categories)
            
            cursor.close()
            duration = time.time() - start_time
            
            enhanced_logger.system_operation(
                "CREATE_TABLES", "MYSQL", "SUCCESS",
                details={
                    "tables_created": "popular_questions, question_categories",
                    "default_categories": 5,
                    "duration": f"{duration:.3f}s"
                }
            )
            
        except Error as e:
            enhanced_logger.system_operation(
                "CREATE_TABLES", "MYSQL", "FAILED", error=str(e)
            )
    
    def add_popular_question(self, query: str, search_count: int, 
                           similarity_score: float = 0.0, 
                           category: str = 'general') -> bool:
        """인기 질문 추가/업데이트 (5회 이상)"""
        if not self.is_connected():
            return False
            
        if search_count < 5:
            enhanced_logger.mysql_operation(
                "SKIP_INSERT", query, 
                result={'reason': 'Low search count', 'count': search_count}
            )
            return False
        
        try:
            start_time = time.time()
            cursor = self.connection.cursor()
            
            # 쿼리 해시 생성 (Redis와 동일한 방식)
            import hashlib
            normalized_query = query.strip().lower().replace(" ", "")
            query_hash = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
            
            # 카테고리 자동 분류
            detected_category = self._classify_question(query)
            if detected_category:
                category = detected_category
            
            # UPSERT 쿼리 (중복시 업데이트)
            upsert_query = """
            INSERT INTO popular_questions 
            (query, query_hash, search_count, similarity_score, category, last_searched_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            search_count = VALUES(search_count),
            similarity_score = GREATEST(similarity_score, VALUES(similarity_score)),
            category = VALUES(category),
            last_searched_at = NOW(),
            updated_at = NOW()
            """
            
            cursor.execute(upsert_query, (query, query_hash, search_count, similarity_score, category))
            
            cursor.close()
            duration = time.time() - start_time
            
            enhanced_logger.mysql_operation(
                "INSERT", query,
                result={'category': category, 'similarity': similarity_score},
                count=search_count
            )
            
            # 정형화된 박스 로그 추가
            enhanced_logger.mysql_data_box("INSERT POPULAR", query, {
                'search_count': search_count,
                'category': category,
                'similarity': similarity_score,
                'status': 'Added to Popular Questions Database'
            })
            
            return True
            
        except Error as e:
            enhanced_logger.mysql_operation(
                "INSERT", query, error=str(e)
            )
            return False
    
    def _classify_question(self, query: str) -> str:
        """질문 카테고리 자동 분류"""
        query_lower = query.lower()
        
        # 개인화 질문
        if any(name in query for name in ["김명정", "김철수", "박영희"]):
            return "personal"
        
        # 민원 관련
        if any(keyword in query_lower for keyword in ["민원", "불만", "문제", "신고", "접수"]):
            return "complaint"
        
        # 카드 관련
        if any(keyword in query_lower for keyword in ["카드", "발급", "신청", "bc카드", "연회비"]):
            return "card"
        
        # 서비스 관련
        if any(keyword in query_lower for keyword in ["서비스", "혜택", "포인트", "할인"]):
            return "service"
        
        return "general"
    
    def get_popular_questions(self, limit: int = 10, category: str = None) -> List[Dict]:
        """인기 질문 목록 조회"""
        if not self.is_connected():
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            base_query = """
            SELECT 
                pq.id,
                pq.query,
                pq.search_count,
                pq.similarity_score,
                pq.category,
                pq.last_searched_at,
                qc.display_name as category_display
            FROM popular_questions pq
            LEFT JOIN question_categories qc ON pq.category = qc.name
            WHERE pq.is_active = TRUE AND pq.search_count >= 5
            """
            
            params = []
            if category:
                base_query += " AND pq.category = %s"
                params.append(category)
            
            base_query += " ORDER BY pq.search_count DESC, pq.last_searched_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            cursor.close()
            return results
            
        except Error as e:
            logger.error(f"인기질문 조회 오류: {e}")
            return []
    
    def get_top_3_popular_questions(self) -> List[str]:
        """상위 3개 인기질문 (50% 미만 답변시 표시용)"""
        popular = self.get_popular_questions(limit=3)
        return [q['query'] for q in popular]
    
    def get_question_stats(self) -> Dict:
        """질문 통계 정보"""
        if not self.is_connected():
            return {'connected': False}
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # 전체 통계
            cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                SUM(search_count) as total_searches,
                AVG(similarity_score) as avg_similarity,
                MAX(search_count) as max_searches
            FROM popular_questions 
            WHERE is_active = TRUE
            """)
            
            stats = cursor.fetchone()
            
            # 카테고리별 통계
            cursor.execute("""
            SELECT 
                pq.category,
                qc.display_name,
                COUNT(*) as question_count,
                SUM(pq.search_count) as total_searches
            FROM popular_questions pq
            LEFT JOIN question_categories qc ON pq.category = qc.name
            WHERE pq.is_active = TRUE
            GROUP BY pq.category, qc.display_name
            ORDER BY total_searches DESC
            """)
            
            categories = cursor.fetchall()
            
            cursor.close()
            
            return {
                'connected': True,
                'total_questions': stats['total_questions'],
                'total_searches': stats['total_searches'],
                'avg_similarity': float(stats['avg_similarity']) if stats['avg_similarity'] else 0.0,
                'max_searches': stats['max_searches'],
                'categories': categories
            }
            
        except Error as e:
            logger.error(f"통계 조회 오류: {e}")
            return {'connected': False, 'error': str(e)}
    
    def clear_popular_questions(self) -> bool:
        """인기 질문 데이터 초기화"""
        if not self.is_connected():
            logger.warning("MySQL 연결되지 않음 - 인기질문 초기화 생략")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # 인기질문 데이터 삭제
            cursor.execute("DELETE FROM popular_questions")
            deleted_count = cursor.rowcount
            
            cursor.close()
            
            logger.info(f"🗑️ MySQL 인기질문 초기화: {deleted_count}개 레코드 삭제")
            return True
            
        except Error as e:
            logger.error(f"인기질문 초기화 오류: {e}")
            return False
    
    def close_connection(self):
        """데이터베이스 연결 종료"""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                logger.info("MySQL 연결 종료")
        except Error as e:
            logger.error(f"연결 종료 오류: {e}")