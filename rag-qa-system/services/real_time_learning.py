#!/usr/bin/env python3
"""
실시간 학습 및 피드백 시스템 - 사용자 피드백을 통한 지속적인 성능 개선
"""

import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import sqlite3
import threading
from pathlib import Path
import numpy as np
import hashlib

@dataclass
class UserFeedback:
    """사용자 피드백 데이터"""
    feedback_id: str
    query: str
    response: str
    rating: int  # 1-5 점
    feedback_type: str  # "rating", "correction", "suggestion"
    feedback_text: Optional[str]
    user_session: str
    timestamp: datetime
    context_info: Dict[str, Any]
    source_documents: List[str]

@dataclass
class QueryPattern:
    """쿼리 패턴 분석 결과"""
    pattern_id: str
    pattern_type: str
    keywords: List[str]
    frequency: int
    success_rate: float
    average_rating: float
    last_updated: datetime
    improvement_suggestions: List[str]

@dataclass
class LearningEvent:
    """학습 이벤트"""
    event_id: str
    event_type: str  # "feedback", "pattern_update", "model_adjustment"
    description: str
    impact_score: float
    timestamp: datetime
    metadata: Dict[str, Any]

class FeedbackDatabase:
    """피드백 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "data/feedback.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 피드백 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                rating INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                feedback_text TEXT,
                user_session TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context_info TEXT,
                source_documents TEXT
            )
        ''')
        
        # 쿼리 패턴 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                keywords TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                average_rating REAL NOT NULL,
                last_updated TEXT NOT NULL,
                improvement_suggestions TEXT
            )
        ''')
        
        # 학습 이벤트 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                impact_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_feedback(self, feedback: UserFeedback):
        """피드백 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback.feedback_id,
            feedback.query,
            feedback.response,
            feedback.rating,
            feedback.feedback_type,
            feedback.feedback_text,
            feedback.user_session,
            feedback.timestamp.isoformat(),
            json.dumps(feedback.context_info),
            json.dumps(feedback.source_documents)
        ))
        
        conn.commit()
        conn.close()
    
    def save_pattern(self, pattern: QueryPattern):
        """쿼리 패턴 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO query_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.pattern_type,
            json.dumps(pattern.keywords),
            pattern.frequency,
            pattern.success_rate,
            pattern.average_rating,
            pattern.last_updated.isoformat(),
            json.dumps(pattern.improvement_suggestions)
        ))
        
        conn.commit()
        conn.close()
    
    def get_feedback_by_timerange(self, start_time: datetime, end_time: datetime) -> List[UserFeedback]:
        """시간 범위별 피드백 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM feedback 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        ''', (start_time.isoformat(), end_time.isoformat()))
        
        results = []
        for row in cursor.fetchall():
            feedback = UserFeedback(
                feedback_id=row[0],
                query=row[1],
                response=row[2],
                rating=row[3],
                feedback_type=row[4],
                feedback_text=row[5],
                user_session=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                context_info=json.loads(row[8]) if row[8] else {},
                source_documents=json.loads(row[9]) if row[9] else []
            )
            results.append(feedback)
        
        conn.close()
        return results
    
    def get_patterns(self) -> List[QueryPattern]:
        """모든 쿼리 패턴 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM query_patterns ORDER BY frequency DESC')
        
        results = []
        for row in cursor.fetchall():
            pattern = QueryPattern(
                pattern_id=row[0],
                pattern_type=row[1],
                keywords=json.loads(row[2]),
                frequency=row[3],
                success_rate=row[4],
                average_rating=row[5],
                last_updated=datetime.fromisoformat(row[6]),
                improvement_suggestions=json.loads(row[7]) if row[7] else []
            )
            results.append(pattern)
        
        conn.close()
        return results

class PatternAnalyzer:
    """쿼리 패턴 분석기"""
    
    def __init__(self):
        self.pattern_types = {
            "card_issuance": ["카드", "발급", "신청", "개설"],
            "customer_service": ["고객센터", "문의", "상담", "연락처"],
            "procedures": ["절차", "방법", "과정", "단계"],
            "personal_inquiry": ["김명정", "고객", "개인", "맞춤"],
            "card_benefits": ["혜택", "포인트", "할인", "적립"],
            "technical_issue": ["오류", "문제", "안됨", "실패"]
        }
        
        self.improvement_templates = {
            "low_rating": [
                "더 구체적인 정보 제공 필요",
                "사용자 친화적인 설명 개선",
                "단계별 가이드 강화"
            ],
            "high_frequency": [
                "자주 묻는 질문으로 등록",
                "미리 준비된 답변 최적화",
                "관련 문서 보강"
            ],
            "confusion_pattern": [
                "용어 설명 추가",
                "예시 제공 강화",
                "다양한 표현 방식 적용"
            ]
        }
    
    def analyze_query_patterns(self, feedbacks: List[UserFeedback]) -> List[QueryPattern]:
        """피드백에서 쿼리 패턴 분석"""
        pattern_data = defaultdict(lambda: {
            'queries': [],
            'ratings': [],
            'frequencies': 0,
            'keywords': set()
        })
        
        # 패턴별 데이터 수집
        for feedback in feedbacks:
            detected_patterns = self._detect_patterns(feedback.query)
            
            for pattern_type in detected_patterns:
                pattern_data[pattern_type]['queries'].append(feedback.query)
                pattern_data[pattern_type]['ratings'].append(feedback.rating)
                pattern_data[pattern_type]['frequencies'] += 1
                pattern_data[pattern_type]['keywords'].update(self._extract_keywords(feedback.query))
        
        # QueryPattern 객체 생성
        patterns = []
        for pattern_type, data in pattern_data.items():
            if data['frequencies'] < 2:  # 최소 2회 이상 등장한 패턴만
                continue
            
            avg_rating = np.mean(data['ratings'])
            success_rate = sum(1 for r in data['ratings'] if r >= 4) / len(data['ratings'])
            
            # 개선 제안 생성
            improvement_suggestions = self._generate_improvement_suggestions(
                pattern_type, avg_rating, success_rate, data['frequencies']
            )
            
            pattern_id = hashlib.md5(f"{pattern_type}_{datetime.now().date()}".encode()).hexdigest()[:8]
            
            pattern = QueryPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                keywords=list(data['keywords'])[:10],  # 상위 10개 키워드
                frequency=data['frequencies'],
                success_rate=success_rate,
                average_rating=avg_rating,
                last_updated=datetime.now(),
                improvement_suggestions=improvement_suggestions
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _detect_patterns(self, query: str) -> List[str]:
        """쿼리에서 패턴 감지"""
        detected = []
        query_lower = query.lower()
        
        for pattern_type, keywords in self.pattern_types.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append(pattern_type)
        
        return detected
    
    def _extract_keywords(self, query: str) -> set:
        """쿼리에서 키워드 추출"""
        import re
        
        # 한글 단어 추출 (2글자 이상)
        keywords = re.findall(r'[가-힣]{2,}', query)
        
        # 불용어 제거
        stop_words = {'하고', '있는', '으로', '에서', '에게', '에는', '과는', '까지'}
        keywords = [kw for kw in keywords if kw not in stop_words]
        
        return set(keywords)
    
    def _generate_improvement_suggestions(self, pattern_type: str, avg_rating: float, 
                                        success_rate: float, frequency: int) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        # 낮은 평점
        if avg_rating < 3.0:
            suggestions.extend(self.improvement_templates["low_rating"])
        
        # 높은 빈도
        if frequency > 10:
            suggestions.extend(self.improvement_templates["high_frequency"])
        
        # 낮은 성공률
        if success_rate < 0.6:
            suggestions.extend(self.improvement_templates["confusion_pattern"])
        
        # 패턴별 특화 제안
        if pattern_type == "personal_inquiry":
            suggestions.append("개인화 정보 처리 알고리즘 개선")
        elif pattern_type == "technical_issue":
            suggestions.append("기술적 문제 해결 가이드 강화")
        
        return list(set(suggestions))  # 중복 제거

class AdaptiveLearningEngine:
    """적응형 학습 엔진"""
    
    def __init__(self):
        self.learning_rules = {
            "response_improvement": {
                "trigger": lambda feedback: feedback.rating <= 2,
                "action": self._improve_response_quality,
                "weight": 1.0
            },
            "pattern_recognition": {
                "trigger": lambda feedback: feedback.feedback_type == "suggestion",
                "action": self._update_pattern_recognition,
                "weight": 0.8
            },
            "personalization": {
                "trigger": lambda feedback: "김명정" in feedback.query and feedback.rating >= 4,
                "action": self._enhance_personalization,
                "weight": 1.2
            }
        }
        
        self.improvement_memory = deque(maxlen=100)  # 최근 100개 개선사항 기억
        self.logger = logging.getLogger(__name__)
    
    def process_feedback(self, feedback: UserFeedback) -> List[LearningEvent]:
        """피드백 처리 및 학습 이벤트 생성"""
        events = []
        
        for rule_name, rule in self.learning_rules.items():
            if rule["trigger"](feedback):
                try:
                    event = rule["action"](feedback, rule["weight"])
                    if event:
                        events.append(event)
                        self.improvement_memory.append(event)
                        self.logger.info(f"Learning rule '{rule_name}' applied: {event.description}")
                except Exception as e:
                    self.logger.error(f"Error applying learning rule '{rule_name}': {e}")
        
        return events
    
    def _improve_response_quality(self, feedback: UserFeedback, weight: float) -> Optional[LearningEvent]:
        """응답 품질 개선"""
        # 낮은 평점의 응답 패턴 분석
        problematic_phrases = self._identify_problematic_phrases(feedback.response)
        
        if problematic_phrases:
            event_id = hashlib.md5(f"quality_{feedback.feedback_id}".encode()).hexdigest()[:8]
            
            return LearningEvent(
                event_id=event_id,
                event_type="response_improvement",
                description=f"품질 개선 필요: {', '.join(problematic_phrases[:3])}",
                impact_score=weight * (5 - feedback.rating) / 4,  # 평점이 낮을수록 높은 임팩트
                timestamp=datetime.now(),
                metadata={
                    "original_query": feedback.query,
                    "problematic_response": feedback.response[:200],
                    "user_rating": feedback.rating,
                    "improvement_areas": problematic_phrases
                }
            )
        
        return None
    
    def _update_pattern_recognition(self, feedback: UserFeedback, weight: float) -> Optional[LearningEvent]:
        """패턴 인식 업데이트"""
        if feedback.feedback_text:
            # 사용자 제안에서 새로운 패턴 학습
            suggested_keywords = self._extract_suggestion_keywords(feedback.feedback_text)
            
            if suggested_keywords:
                event_id = hashlib.md5(f"pattern_{feedback.feedback_id}".encode()).hexdigest()[:8]
                
                return LearningEvent(
                    event_id=event_id,
                    event_type="pattern_update",
                    description=f"새로운 패턴 학습: {', '.join(suggested_keywords)}",
                    impact_score=weight * 0.8,
                    timestamp=datetime.now(),
                    metadata={
                        "new_keywords": suggested_keywords,
                        "user_suggestion": feedback.feedback_text,
                        "context_query": feedback.query
                    }
                )
        
        return None
    
    def _enhance_personalization(self, feedback: UserFeedback, weight: float) -> Optional[LearningEvent]:
        """개인화 강화"""
        # 고평점 개인화 응답에서 성공 패턴 학습
        success_patterns = self._extract_success_patterns(feedback.query, feedback.response)
        
        if success_patterns:
            event_id = hashlib.md5(f"personal_{feedback.feedback_id}".encode()).hexdigest()[:8]
            
            return LearningEvent(
                event_id=event_id,
                event_type="personalization_enhancement",
                description=f"개인화 성공 패턴: {', '.join(success_patterns)}",
                impact_score=weight * feedback.rating / 5,
                timestamp=datetime.now(),
                metadata={
                    "success_patterns": success_patterns,
                    "user_rating": feedback.rating,
                    "personalized_query": feedback.query
                }
            )
        
        return None
    
    def _identify_problematic_phrases(self, response: str) -> List[str]:
        """문제가 있는 표현 식별"""
        problematic_patterns = [
            "죄송합니다", "모르겠습니다", "확인이 어렵습니다",
            "정보가 없습니다", "답변드리기 어렵습니다"
        ]
        
        found_issues = []
        for pattern in problematic_patterns:
            if pattern in response:
                found_issues.append(pattern)
        
        return found_issues
    
    def _extract_suggestion_keywords(self, suggestion_text: str) -> List[str]:
        """제안 텍스트에서 키워드 추출"""
        import re
        
        # 한글 키워드 추출
        keywords = re.findall(r'[가-힣]{2,}', suggestion_text)
        
        # 빈도순 정렬
        from collections import Counter
        keyword_counts = Counter(keywords)
        
        return [kw for kw, count in keyword_counts.most_common(5)]
    
    def _extract_success_patterns(self, query: str, response: str) -> List[str]:
        """성공 패턴 추출"""
        patterns = []
        
        # 개인화 성공 지표
        if "김명정" in query and "님" in response:
            patterns.append("개인화_호칭")
        
        if "보유카드" in query and "현재" in response:
            patterns.append("현재상태_반영")
        
        if "추천" in query and ("적합" in response or "맞춤" in response):
            patterns.append("맞춤형_추천")
        
        return patterns

class RealTimeLearningSystem:
    """실시간 학습 시스템 메인 클래스"""
    
    def __init__(self, db_path: str = "data/feedback.db"):
        self.db = FeedbackDatabase(db_path)
        self.pattern_analyzer = PatternAnalyzer()
        self.learning_engine = AdaptiveLearningEngine()
        
        # 학습 통계
        self.learning_stats = {
            "total_feedback": 0,
            "processed_patterns": 0,
            "learning_events": 0,
            "improvement_score": 0.0
        }
        
        # 백그라운드 학습 스레드
        self.learning_thread = None
        self.is_learning = False
        
        self.logger = logging.getLogger(__name__)
    
    def submit_feedback(self, query: str, response: str, rating: int,
                       feedback_type: str = "rating", feedback_text: str = None,
                       user_session: str = "default", context_info: Dict = None,
                       source_documents: List[str] = None) -> str:
        """피드백 제출"""
        feedback_id = hashlib.md5(f"{query}_{response}_{time.time()}".encode()).hexdigest()[:12]
        
        feedback = UserFeedback(
            feedback_id=feedback_id,
            query=query,
            response=response,
            rating=rating,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            user_session=user_session,
            timestamp=datetime.now(),
            context_info=context_info or {},
            source_documents=source_documents or []
        )
        
        # 데이터베이스 저장
        self.db.save_feedback(feedback)
        
        # 실시간 학습 처리
        learning_events = self.learning_engine.process_feedback(feedback)
        
        # 통계 업데이트
        self.learning_stats["total_feedback"] += 1
        self.learning_stats["learning_events"] += len(learning_events)
        
        self.logger.info(f"피드백 처리 완료: {feedback_id}, 평점: {rating}, 학습 이벤트: {len(learning_events)}개")
        
        return feedback_id
    
    def analyze_patterns(self, days: int = 7) -> List[QueryPattern]:
        """최근 N일간 패턴 분석"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        feedbacks = self.db.get_feedback_by_timerange(start_time, end_time)
        patterns = self.pattern_analyzer.analyze_query_patterns(feedbacks)
        
        # 패턴 저장
        for pattern in patterns:
            self.db.save_pattern(pattern)
        
        self.learning_stats["processed_patterns"] = len(patterns)
        self.logger.info(f"{days}일간 패턴 분석 완료: {len(patterns)}개 패턴 발견")
        
        return patterns
    
    def get_improvement_recommendations(self) -> Dict[str, Any]:
        """개선 권고사항 생성"""
        patterns = self.db.get_patterns()
        
        # 우선순위 기준
        priority_patterns = sorted(patterns, key=lambda p: p.frequency * (5 - p.average_rating), reverse=True)
        
        recommendations = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "summary": {
                "total_patterns": len(patterns),
                "needs_immediate_attention": 0,
                "average_success_rate": np.mean([p.success_rate for p in patterns]) if patterns else 0.0
            }
        }
        
        for pattern in priority_patterns[:20]:  # 상위 20개만
            priority_score = pattern.frequency * (5 - pattern.average_rating)
            
            rec = {
                "pattern_type": pattern.pattern_type,
                "frequency": pattern.frequency,
                "average_rating": pattern.average_rating,
                "success_rate": pattern.success_rate,
                "priority_score": priority_score,
                "suggestions": pattern.improvement_suggestions
            }
            
            if priority_score > 10:
                recommendations["high_priority"].append(rec)
                recommendations["summary"]["needs_immediate_attention"] += 1
            elif priority_score > 5:
                recommendations["medium_priority"].append(rec)
            else:
                recommendations["low_priority"].append(rec)
        
        return recommendations
    
    def start_continuous_learning(self, interval_hours: int = 24):
        """연속 학습 시작"""
        if self.is_learning:
            self.logger.warning("연속 학습이 이미 실행 중입니다")
            return
        
        self.is_learning = True
        
        def learning_loop():
            while self.is_learning:
                try:
                    # 패턴 분석 실행
                    patterns = self.analyze_patterns(days=1)
                    
                    # 개선사항 계산
                    if patterns:
                        improvement_score = np.mean([p.success_rate for p in patterns])
                        self.learning_stats["improvement_score"] = improvement_score
                    
                    self.logger.info(f"연속 학습 실행: {len(patterns)}개 패턴 처리")
                    
                    # 대기
                    time.sleep(interval_hours * 3600)
                    
                except Exception as e:
                    self.logger.error(f"연속 학습 오류: {e}")
                    time.sleep(300)  # 5분 후 재시도
        
        self.learning_thread = threading.Thread(target=learning_loop, daemon=True)
        self.learning_thread.start()
        
        self.logger.info(f"연속 학습 시작: {interval_hours}시간 간격")
    
    def stop_continuous_learning(self):
        """연속 학습 중지"""
        self.is_learning = False
        if self.learning_thread:
            self.learning_thread.join(timeout=5)
        
        self.logger.info("연속 학습 중지")
    
    def get_learning_status(self) -> Dict[str, Any]:
        """학습 시스템 상태 조회"""
        return {
            "learning_stats": self.learning_stats,
            "is_continuous_learning": self.is_learning,
            "memory_size": len(self.learning_engine.improvement_memory),
            "recent_improvements": [
                {
                    "event_type": event.event_type,
                    "description": event.description,
                    "impact_score": event.impact_score,
                    "timestamp": event.timestamp.isoformat()
                }
                for event in list(self.learning_engine.improvement_memory)[-5:]  # 최근 5개
            ]
        }

# 전역 학습 시스템 인스턴스
learning_system = RealTimeLearningSystem()

def submit_user_feedback(query: str, response: str, rating: int, **kwargs) -> str:
    """사용자 피드백 제출 (편의 함수)"""
    return learning_system.submit_feedback(query, response, rating, **kwargs)

def get_system_improvements() -> Dict[str, Any]:
    """시스템 개선사항 조회 (편의 함수)"""
    return learning_system.get_improvement_recommendations()

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 샘플 피드백 제출
    feedback_id = submit_user_feedback(
        query="김명정 고객의 BC카드 발급 안내",
        response="김명정님을 위한 맞춤형 카드 발급 안내를 제공드립니다...",
        rating=5,
        feedback_type="rating",
        user_session="test_session"
    )
    
    print(f"피드백 제출 완료: {feedback_id}")
    
    # 패턴 분석
    patterns = learning_system.analyze_patterns(days=1)
    print(f"분석된 패턴: {len(patterns)}개")
    
    # 개선사항 조회
    improvements = get_system_improvements()
    print(f"개선 권고사항: {len(improvements['high_priority'])}개 고우선순위")
    
    # 학습 상태 조회
    status = learning_system.get_learning_status()
    print(f"학습 통계: {status['learning_stats']}")