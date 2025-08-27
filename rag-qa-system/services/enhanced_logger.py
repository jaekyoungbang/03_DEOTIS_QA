"""
향상된 로깅 시스템
- Redis/MySQL 작업 로그를 직관적으로 표시
- 색상 코딩 및 아이콘 사용
- 구조화된 로그 포맷
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json

class ColorFormatter(logging.Formatter):
    """색상이 적용된 로그 포맷터"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',     # 청록색
        'INFO': '\033[32m',      # 초록색
        'WARNING': '\033[33m',   # 노란색
        'ERROR': '\033[31m',     # 빨간색
        'CRITICAL': '\033[35m',  # 보라색
        'RESET': '\033[0m'       # 리셋
    }
    
    # 레벨별 아이콘
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        # 색상 및 아이콘 적용
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        icon = self.ICONS.get(record.levelname, '📝')
        reset = self.COLORS['RESET']
        
        # 시간 포맷
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # 로그 메시지 포맷
        log_message = f"{color}{icon} [{timestamp}] {record.levelname}{reset} - {record.getMessage()}"
        
        return log_message

class EnhancedLogger:
    """향상된 로거 클래스"""
    
    def __init__(self, name: str = "RAG_QA_SYSTEM"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColorFormatter())
        
        self.logger.addHandler(console_handler)
        self.logger.propagate = False
    
    def redis_operation(self, operation: str, query: str, result: Any = None, 
                       error: Optional[str] = None, duration: Optional[float] = None):
        """Redis 작업 로그"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        if error:
            self.logger.error(f"🔴 REDIS [{operation}] FAILED")
            self.logger.error(f"   📝 Query: \"{query_preview}\"")
            self.logger.error(f"   ❌ Error: {error}")
        else:
            status_icon = "🎯" if operation == "HIT" else "💾" if operation == "SET" else "📊" if operation == "STATS" else "🔢" if operation == "COUNT" else "📋"
            self.logger.info(f"{status_icon} REDIS [{operation}] SUCCESS")
            self.logger.info(f"   📝 Query: \"{query_preview}\"")
            
            if duration:
                self.logger.info(f"   ⏱️  Duration: {duration:.3f}s")
            
            if operation == "HIT" and result:
                cached_time = result.get('cached_at', 'Unknown')
                access_count = result.get('access_count', 1)
                self.logger.info(f"   🕐 Cached at: {cached_time}")
                self.logger.info(f"   👥 Access count: {access_count} times")
                
            elif operation == "SET" and result:
                similarity = result.get('similarity_score', 0)
                ttl = result.get('ttl', '1 hour')
                self.logger.info(f"   📈 Similarity: {similarity:.1%}")
                self.logger.info(f"   ⏰ TTL: {ttl}")
                self.logger.info(f"   ✅ 🔥 CACHED for fast future access!")
                
            elif operation == "COUNT" and result:
                count = result.get('current_count', 0)
                ttl = result.get('ttl', '1 hour')
                self.logger.info(f"   🔢 Search count: {count} times")
                self.logger.info(f"   ⏰ TTL: {ttl}")
                
                if count >= 5:
                    self.logger.info(f"   🎯 ⭐ POPULAR THRESHOLD REACHED! (5+ searches)")
                elif count >= 3:
                    self.logger.info(f"   📈 Getting popular... ({count}/5)")
                
            elif operation == "STATS" and result:
                self.logger.info(f"   📊 Cached queries: {result.get('cached_queries', 0)}")
                self.logger.info(f"   🔢 Total searches: {result.get('total_searches', 0)}")
                self.logger.info(f"   ⭐ Popular queries: {result.get('popular_queries', 0)}")
    
    def mysql_operation(self, operation: str, query: str = "", result: Any = None, 
                       error: Optional[str] = None, count: Optional[int] = None):
        """MySQL 작업 로그"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        if error:
            self.logger.error(f"🔴 MYSQL [{operation}] FAILED")
            if query:
                self.logger.error(f"   📝 Query: \"{query_preview}\"")
            self.logger.error(f"   ❌ Error: {error}")
        else:
            status_icon = "💫" if operation == "INSERT" else "📋" if operation == "SELECT" else "🗑️" if operation == "DELETE" else "🔧"
            self.logger.info(f"{status_icon} MYSQL [{operation}] SUCCESS")
            
            if query:
                self.logger.info(f"   📝 Query: \"{query_preview}\"")
            
            if operation == "INSERT" and count:
                search_count = count
                category = result.get('category', 'unknown') if result else 'unknown'
                similarity = result.get('similarity', 0.0) if result else 0.0
                
                self.logger.info(f"   🔢 Search count: {search_count} times")
                self.logger.info(f"   📂 Category: {category}")
                self.logger.info(f"   📈 Similarity: {similarity:.1%}")
                self.logger.info(f"   ✅ 🎯 SAVED TO POPULAR QUESTIONS DATABASE!")
                
                # 인기도에 따른 추가 메시지
                if search_count >= 10:
                    self.logger.info(f"   🔥 🌟 SUPER POPULAR QUESTION! ({search_count} searches)")
                elif search_count >= 7:
                    self.logger.info(f"   🔥 Very popular question ({search_count} searches)")
                else:
                    self.logger.info(f"   📈 Popular question ({search_count} searches)")
                
            elif operation == "SELECT" and result:
                if isinstance(result, list):
                    self.logger.info(f"   📋 Found: {len(result)} popular questions")
                    if result:
                        self.logger.info(f"   🏆 Top question: \"{result[0].get('query', '')[:40]}...\"")
                elif isinstance(result, dict):
                    total_q = result.get('total_questions', 0)
                    total_s = result.get('total_searches', 0)
                    avg_sim = result.get('avg_similarity', 0.0)
                    self.logger.info(f"   📊 Total questions: {total_q}")
                    self.logger.info(f"   🔢 Total searches: {total_s}")
                    self.logger.info(f"   📈 Average similarity: {avg_sim:.1%}")
                    
            elif operation == "DELETE" and count is not None:
                self.logger.info(f"   🗑️  Deleted records: {count}")
                if count > 0:
                    self.logger.info(f"   ✅ Database cleared successfully!")
    
    def system_operation(self, operation: str, component: str, status: str, 
                        details: Optional[Dict] = None, error: Optional[str] = None):
        """시스템 작업 로그"""
        if error or status == "FAILED":
            self.logger.error(f"🚨 SYSTEM [{component}] {operation} FAILED")
            if error:
                self.logger.error(f"   ❌ Error: {error}")
        else:
            status_icon = "🚀" if operation == "INIT" else "🔄" if operation == "UPDATE" else "🛑" if operation == "SHUTDOWN" else "⚙️"
            self.logger.info(f"{status_icon} SYSTEM [{component}] {operation} {status}")
            
            if details:
                for key, value in details.items():
                    icon = "📊" if "count" in key.lower() or "stat" in key.lower() else "🔗" if "connect" in key.lower() else "📝"
                    self.logger.info(f"   {icon} {key.title()}: {value}")
    
    def search_operation(self, query: str, similarity: float, source: str, 
                        cached: bool = False, duration: Optional[float] = None):
        """검색 작업 로그"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        cache_icon = "🎯" if cached else "🔍"
        similarity_icon = "🟢" if similarity >= 0.8 else "🟡" if similarity >= 0.6 else "🔴"
        
        self.logger.info(f"{cache_icon} SEARCH {'[CACHED]' if cached else '[VECTOR]'}")
        self.logger.info(f"   📝 Query: \"{query_preview}\"")
        self.logger.info(f"   {similarity_icon} Similarity: {similarity:.1%}")
        self.logger.info(f"   📂 Source: {source}")
        
        if duration:
            self.logger.info(f"   ⏱️  Duration: {duration:.3f}s")
    
    def question_flow(self, query: str, flow_type: str, details: Dict):
        """질문 처리 플로우 로그"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        if flow_type == "START":
            request_count = details.get('request_count', 0)
            self.logger.info(f"🎬 QUESTION PROCESSING START")
            self.logger.info(f"   📝 Query: \"{query_preview}\"")
            if request_count > 0:
                self.logger.info(f"   🔢 Request #{request_count} for this query")
            
        elif flow_type == "CACHE_CHECK":
            hit = details.get('hit', False)
            if hit:
                self.logger.info(f"🎯 CACHE HIT - Returning cached result")
            else:
                self.logger.info(f"❌ CACHE MISS - Proceeding to vector search")
                
        elif flow_type == "VECTOR_SEARCH":
            similarity = details.get('similarity', 0)
            self.logger.info(f"🔍 VECTOR SEARCH COMPLETED")
            self.logger.info(f"   📈 Max similarity: {similarity:.1%}")
            
        elif flow_type == "LLM_REQUEST":
            self.logger.info(f"🤖 REQUESTING LLM GENERATION")
            self.logger.info(f"   📝 Query: \"{query_preview}\"")
            self.logger.info(f"   🔄 Generating response with AI model...")
            
        elif flow_type == "LLM_RESPONSE":
            response_length = details.get('response_length', 0)
            duration = details.get('duration', 0)
            self.logger.info(f"🤖 LLM RESPONSE RECEIVED")
            self.logger.info(f"   📝 Response length: {response_length} characters")
            if duration > 0:
                self.logger.info(f"   ⏱️  Generation time: {duration:.3f}s")
            
        elif flow_type == "RESPONSE_TYPE":
            response_type = details.get('type', 'unknown')
            threshold_met = details.get('threshold_met', False)
            
            if response_type == "normal":
                self.logger.info(f"✅ NORMAL RESPONSE - High similarity")
            elif response_type == "low_similarity":
                show_buttons = details.get('show_popular_buttons', False)
                if show_buttons:
                    self.logger.info(f"🔘 LOW SIMILARITY - Showing popular question buttons")
                else:
                    self.logger.info(f"💡 LOW SIMILARITY - Showing suggested questions")
            elif response_type == "cached":
                self.logger.info(f"⚡ CACHED RESPONSE - Lightning fast!")
            else:
                self.logger.info(f"📋 {response_type.upper()} RESPONSE")
                
        elif flow_type == "END":
            cached = details.get('cached', False)
            popular_saved = details.get('popular_saved', False)
            total_requests = details.get('total_requests', 0)
            
            self.logger.info(f"🏁 QUESTION PROCESSING END")
            if cached:
                self.logger.info(f"   💾 ✅ RESULT CACHED for future speed boost!")
            if popular_saved:
                self.logger.info(f"   ⭐ ✅ ADDED TO POPULAR QUESTIONS DATABASE!")
            if total_requests > 0:
                self.logger.info(f"   📊 Total requests for this query: {total_requests}")
    
    def performance_metrics(self, operation: str, metrics: Dict):
        """성능 메트릭 로그"""
        self.logger.info(f"📊 PERFORMANCE [{operation}]")
        
        for key, value in metrics.items():
            if 'time' in key.lower() or 'duration' in key.lower():
                icon = "⏱️"
                if isinstance(value, float):
                    value_str = f"{value:.3f}s"
                else:
                    value_str = str(value)
            elif 'count' in key.lower():
                icon = "🔢"
                value_str = str(value)
            elif 'size' in key.lower():
                icon = "📦"
                value_str = str(value)
            else:
                icon = "📝"
                value_str = str(value)
                
            self.logger.info(f"   {icon} {key.replace('_', ' ').title()}: {value_str}")
    
    def separator(self, title: str = ""):
        """구분선 출력"""
        if title:
            line = "=" * 20 + f" {title} " + "=" * 20
        else:
            line = "=" * 60
        self.logger.info(line)
    
    def structured_log_box(self, title: str, data: Dict, box_type: str = "INFO"):
        """정형화된 박스 형태 로그"""
        # 박스 너비 계산
        max_width = max(len(title), max(len(f"{k}: {v}") for k, v in data.items()) if data else 0) + 4
        box_width = max(max_width, 50)
        
        # 박스 아이콘 선택
        box_icons = {
            "REDIS": "💾",
            "MYSQL": "🗄️", 
            "SYSTEM": "⚙️",
            "SEARCH": "🔍",
            "INFO": "📋",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        icon = box_icons.get(box_type, "📋")
        
        # 박스 그리기
        horizontal_line = "─" * (box_width - 2)
        self.logger.info(f"┌{horizontal_line}┐")
        
        # 제목
        title_padded = f"{icon} {title}".center(box_width - 2)
        self.logger.info(f"│{title_padded}│")
        
        if data:
            self.logger.info(f"├{horizontal_line}┤")
            
            # 데이터 출력
            for key, value in data.items():
                content = f" {key}: {value}"
                padding = " " * (box_width - len(content) - 1)
                self.logger.info(f"│{content}{padding}│")
        
        self.logger.info(f"└{horizontal_line}┘")
    
    def redis_data_box(self, operation: str, query: str, data: Dict):
        """Redis 데이터 정형화 박스"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        box_data = {
            "Operation": operation,
            "Query": f'"{query_preview}"',
            "Similarity": f"{data.get('similarity_score', 0):.1%}" if data.get('similarity_score') else "N/A",
            "Search Count": f"{data.get('current_count', 0)} times",
            "TTL": data.get('ttl', '1 hour'),
            "Cached At": data.get('cached_at', 'N/A'),
            "Duration": f"{data.get('duration', 0):.3f}s" if data.get('duration') else "N/A"
        }
        
        # 불필요한 N/A 제거
        filtered_data = {k: v for k, v in box_data.items() if v != "N/A"}
        
        self.structured_log_box(f"REDIS - {operation}", filtered_data, "REDIS")
    
    def mysql_data_box(self, operation: str, query: str, data: Dict):
        """MySQL 데이터 정형화 박스"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        box_data = {
            "Operation": operation,
            "Query": f'"{query_preview}"' if query else "N/A",
            "Search Count": f"{data.get('search_count', 0)} times",
            "Category": data.get('category', 'N/A'),
            "Similarity": f"{data.get('similarity', 0):.1%}" if data.get('similarity') else "N/A",
            "Total Questions": data.get('total_questions', 'N/A'),
            "Total Searches": data.get('total_searches', 'N/A'),
            "Deleted Records": data.get('deleted_count', 'N/A')
        }
        
        # 불필요한 N/A 제거
        filtered_data = {k: v for k, v in box_data.items() if v != "N/A"}
        
        self.structured_log_box(f"MYSQL - {operation}", filtered_data, "MYSQL")
    
    def system_summary_box(self, query: str, summary_data: Dict):
        """시스템 처리 요약 박스"""
        query_preview = query[:30] + "..." if len(query) > 30 else query
        
        box_data = {
            "Query": f'"{query_preview}"',
            "Request Count": f"#{summary_data.get('request_count', 1)}",
            "Max Similarity": f"{summary_data.get('max_similarity', 0):.1%}",
            "Response Type": summary_data.get('response_type', 'Unknown'),
            "Cached": "✅ Yes" if summary_data.get('cached') else "❌ No",
            "Popular Saved": "✅ Yes" if summary_data.get('popular_saved') else "❌ No",
            "Total Duration": f"{summary_data.get('total_duration', 0):.3f}s",
            "LLM Duration": f"{summary_data.get('llm_duration', 0):.3f}s" if summary_data.get('llm_duration') else "N/A"
        }
        
        # 불필요한 N/A 제거
        filtered_data = {k: v for k, v in box_data.items() if v != "N/A"}
        
        self.structured_log_box("PROCESSING SUMMARY", filtered_data, "SUCCESS")

# 전역 로거 인스턴스
_enhanced_logger = None

def get_enhanced_logger() -> EnhancedLogger:
    """전역 향상된 로거 인스턴스 반환"""
    global _enhanced_logger
    if _enhanced_logger is None:
        _enhanced_logger = EnhancedLogger()
    return _enhanced_logger