#!/usr/bin/env python3
"""
상업화 기능 - 사용자 관리, 과금, 분석 시스템
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import threading
from pathlib import Path
import jwt
import uuid
from collections import defaultdict

class UserTier(Enum):
    """사용자 등급"""
    FREE = "free"           # 무료 사용자
    BASIC = "basic"         # 기본 사용자  
    PREMIUM = "premium"     # 프리미엄 사용자
    ENTERPRISE = "enterprise"  # 기업 사용자

class UsageType(Enum):
    """사용량 타입"""
    QUERY = "query"         # 쿼리 요청
    TOKEN = "token"         # 토큰 사용량
    STORAGE = "storage"     # 저장 공간
    API_CALL = "api_call"   # API 호출

@dataclass
class UserAccount:
    """사용자 계정 정보"""
    user_id: str
    username: str
    email: str
    tier: UserTier
    created_at: datetime
    last_login: datetime
    is_active: bool
    subscription_expires: Optional[datetime]
    api_key: str
    usage_limits: Dict[str, int]
    current_usage: Dict[str, int]
    metadata: Dict[str, Any]

@dataclass
class UsageRecord:
    """사용량 기록"""
    record_id: str
    user_id: str
    usage_type: UsageType
    amount: int
    cost: float
    timestamp: datetime
    request_metadata: Dict[str, Any]
    billing_cycle: str  # "2024-01" format

@dataclass
class BillingRecord:
    """청구 기록"""
    billing_id: str
    user_id: str
    billing_cycle: str
    total_usage: Dict[str, int]
    total_cost: float
    payment_status: str
    generated_at: datetime
    paid_at: Optional[datetime]
    invoice_data: Dict[str, Any]

class PricingManager:
    """가격 정책 관리자"""
    
    def __init__(self):
        self.pricing_tiers = {
            UserTier.FREE: {
                "monthly_limits": {
                    "query": 100,
                    "token": 10000,
                    "storage": 100,  # MB
                    "api_call": 50
                },
                "costs": {
                    "query": 0.0,
                    "token": 0.0,
                    "storage": 0.0,
                    "api_call": 0.0
                },
                "monthly_fee": 0.0
            },
            UserTier.BASIC: {
                "monthly_limits": {
                    "query": 1000,
                    "token": 100000,
                    "storage": 1000,  # MB
                    "api_call": 500
                },
                "costs": {
                    "query": 0.01,    # $0.01 per query
                    "token": 0.0001,  # $0.0001 per token
                    "storage": 0.001, # $0.001 per MB
                    "api_call": 0.005 # $0.005 per API call
                },
                "monthly_fee": 9.99
            },
            UserTier.PREMIUM: {
                "monthly_limits": {
                    "query": 10000,
                    "token": 1000000,
                    "storage": 10000,  # MB
                    "api_call": 5000
                },
                "costs": {
                    "query": 0.008,
                    "token": 0.00008,
                    "storage": 0.0008,
                    "api_call": 0.004
                },
                "monthly_fee": 49.99
            },
            UserTier.ENTERPRISE: {
                "monthly_limits": {
                    "query": 100000,
                    "token": 10000000,
                    "storage": 100000,  # MB
                    "api_call": 50000
                },
                "costs": {
                    "query": 0.005,
                    "token": 0.00005,
                    "storage": 0.0005,
                    "api_call": 0.002
                },
                "monthly_fee": 199.99
            }
        }
    
    def calculate_usage_cost(self, user_tier: UserTier, usage_type: UsageType, amount: int) -> float:
        """사용량 기반 비용 계산"""
        tier_pricing = self.pricing_tiers[user_tier]
        unit_cost = tier_pricing["costs"][usage_type.value]
        return amount * unit_cost
    
    def get_usage_limits(self, user_tier: UserTier) -> Dict[str, int]:
        """사용량 제한 조회"""
        return self.pricing_tiers[user_tier]["monthly_limits"].copy()
    
    def get_monthly_fee(self, user_tier: UserTier) -> float:
        """월 구독료 조회"""
        return self.pricing_tiers[user_tier]["monthly_fee"]

class UserDatabase:
    """사용자 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 계정 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                tier TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT NOT NULL,
                is_active BOOLEAN NOT NULL,
                subscription_expires TEXT,
                api_key TEXT UNIQUE NOT NULL,
                usage_limits TEXT NOT NULL,
                current_usage TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # 사용량 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_records (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                cost REAL NOT NULL,
                timestamp TEXT NOT NULL,
                request_metadata TEXT,
                billing_cycle TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # 청구 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billing_records (
                billing_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                billing_cycle TEXT NOT NULL,
                total_usage TEXT NOT NULL,
                total_cost REAL NOT NULL,
                payment_status TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                paid_at TEXT,
                invoice_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_user_cycle ON usage_records(user_id, billing_cycle)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_billing_user_cycle ON billing_records(user_id, billing_cycle)')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username: str, email: str, tier: UserTier = UserTier.FREE,
                   subscription_expires: Optional[datetime] = None) -> UserAccount:
        """사용자 계정 생성"""
        user_id = str(uuid.uuid4())
        api_key = self._generate_api_key(user_id)
        
        pricing_manager = PricingManager()
        usage_limits = pricing_manager.get_usage_limits(tier)
        current_usage = {key: 0 for key in usage_limits.keys()}
        
        user = UserAccount(
            user_id=user_id,
            username=username,
            email=email,
            tier=tier,
            created_at=datetime.now(),
            last_login=datetime.now(),
            is_active=True,
            subscription_expires=subscription_expires,
            api_key=api_key,
            usage_limits=usage_limits,
            current_usage=current_usage,
            metadata={}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.user_id,
            user.username,
            user.email,
            user.tier.value,
            user.created_at.isoformat(),
            user.last_login.isoformat(),
            user.is_active,
            user.subscription_expires.isoformat() if user.subscription_expires else None,
            user.api_key,
            json.dumps(user.usage_limits),
            json.dumps(user.current_usage),
            json.dumps(user.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"사용자 계정 생성: {username} ({tier.value})")
        return user
    
    def get_user_by_api_key(self, api_key: str) -> Optional[UserAccount]:
        """API 키로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE api_key = ? AND is_active = ?', (api_key, True))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_user(row)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserAccount]:
        """사용자 ID로 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_user(row)
        return None
    
    def update_user_usage(self, user_id: str, usage_type: str, amount: int):
        """사용량 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 현재 사용량 조회
        cursor.execute('SELECT current_usage FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            current_usage = json.loads(row[0])
            current_usage[usage_type] = current_usage.get(usage_type, 0) + amount
            
            cursor.execute(
                'UPDATE users SET current_usage = ? WHERE user_id = ?',
                (json.dumps(current_usage), user_id)
            )
        
        conn.commit()
        conn.close()
    
    def _generate_api_key(self, user_id: str) -> str:
        """API 키 생성"""
        payload = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        }
        # 실제 운영환경에서는 안전한 시크릿 키 사용
        secret_key = "your-secret-key-here"
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def _row_to_user(self, row) -> UserAccount:
        """DB 행을 UserAccount 객체로 변환"""
        return UserAccount(
            user_id=row[0],
            username=row[1],
            email=row[2],
            tier=UserTier(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            last_login=datetime.fromisoformat(row[5]),
            is_active=bool(row[6]),
            subscription_expires=datetime.fromisoformat(row[7]) if row[7] else None,
            api_key=row[8],
            usage_limits=json.loads(row[9]),
            current_usage=json.loads(row[10]),
            metadata=json.loads(row[11]) if row[11] else {}
        )

class UsageTracker:
    """사용량 추적 시스템"""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self.pricing_manager = PricingManager()
        self.user_db = UserDatabase(db_path)
        self.logger = logging.getLogger(__name__)
    
    def record_usage(self, user_id: str, usage_type: UsageType, amount: int,
                    request_metadata: Dict = None) -> bool:
        """사용량 기록"""
        user = self.user_db.get_user_by_id(user_id)
        if not user:
            self.logger.error(f"사용자를 찾을 수 없음: {user_id}")
            return False
        
        # 사용량 제한 확인
        current_usage = user.current_usage.get(usage_type.value, 0)
        usage_limit = user.usage_limits.get(usage_type.value, 0)
        
        if current_usage + amount > usage_limit and user.tier != UserTier.ENTERPRISE:
            self.logger.warning(f"사용량 제한 초과: {user.username}, {usage_type.value}")
            return False
        
        # 비용 계산
        cost = self.pricing_manager.calculate_usage_cost(user.tier, usage_type, amount)
        
        # 사용량 기록 저장
        record_id = str(uuid.uuid4())
        billing_cycle = datetime.now().strftime("%Y-%m")
        
        usage_record = UsageRecord(
            record_id=record_id,
            user_id=user_id,
            usage_type=usage_type,
            amount=amount,
            cost=cost,
            timestamp=datetime.now(),
            request_metadata=request_metadata or {},
            billing_cycle=billing_cycle
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usage_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            usage_record.record_id,
            usage_record.user_id,
            usage_record.usage_type.value,
            usage_record.amount,
            usage_record.cost,
            usage_record.timestamp.isoformat(),
            json.dumps(usage_record.request_metadata),
            usage_record.billing_cycle
        ))
        
        conn.commit()
        conn.close()
        
        # 사용자 사용량 업데이트
        self.user_db.update_user_usage(user_id, usage_type.value, amount)
        
        self.logger.info(f"사용량 기록: {user.username}, {usage_type.value}={amount}, 비용=${cost:.4f}")
        return True
    
    def get_user_usage(self, user_id: str, billing_cycle: str = None) -> Dict[str, Any]:
        """사용자 사용량 조회"""
        if billing_cycle is None:
            billing_cycle = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT usage_type, SUM(amount), SUM(cost) 
            FROM usage_records 
            WHERE user_id = ? AND billing_cycle = ? 
            GROUP BY usage_type
        ''', (user_id, billing_cycle))
        
        results = cursor.fetchall()
        conn.close()
        
        usage_summary = {
            "user_id": user_id,
            "billing_cycle": billing_cycle,
            "usage_breakdown": {},
            "total_cost": 0.0
        }
        
        for usage_type, total_amount, total_cost in results:
            usage_summary["usage_breakdown"][usage_type] = {
                "amount": total_amount,
                "cost": total_cost
            }
            usage_summary["total_cost"] += total_cost
        
        return usage_summary

class AnalyticsEngine:
    """분석 엔진"""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def generate_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """사용자 분석 리포트 생성"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 일별 사용량 통계
        cursor.execute('''
            SELECT DATE(timestamp) as date, usage_type, SUM(amount), SUM(cost)
            FROM usage_records 
            WHERE user_id = ? AND timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp), usage_type
            ORDER BY date
        ''', (user_id, start_date.isoformat(), end_date.isoformat()))
        
        daily_usage = defaultdict(lambda: defaultdict(lambda: {"amount": 0, "cost": 0.0}))
        
        for date, usage_type, amount, cost in cursor.fetchall():
            daily_usage[date][usage_type]["amount"] = amount
            daily_usage[date][usage_type]["cost"] = cost
        
        # 월별 트렌드
        cursor.execute('''
            SELECT strftime('%Y-%m', timestamp) as month, usage_type, SUM(amount), SUM(cost)
            FROM usage_records 
            WHERE user_id = ? AND timestamp BETWEEN ? AND ?
            GROUP BY month, usage_type
            ORDER BY month
        ''', (user_id, start_date.isoformat(), end_date.isoformat()))
        
        monthly_trends = defaultdict(lambda: defaultdict(lambda: {"amount": 0, "cost": 0.0}))
        
        for month, usage_type, amount, cost in cursor.fetchall():
            monthly_trends[month][usage_type]["amount"] = amount
            monthly_trends[month][usage_type]["cost"] = cost
        
        # 피크 사용 시간대
        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as request_count
            FROM usage_records 
            WHERE user_id = ? AND timestamp BETWEEN ? AND ?
            GROUP BY hour
            ORDER BY request_count DESC
        ''', (user_id, start_date.isoformat(), end_date.isoformat()))
        
        peak_hours = cursor.fetchall()
        
        conn.close()
        
        return {
            "user_id": user_id,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "daily_usage": dict(daily_usage),
            "monthly_trends": dict(monthly_trends),
            "peak_usage_hours": [
                {"hour": f"{hour}:00", "request_count": count}
                for hour, count in peak_hours[:5]
            ],
            "insights": self._generate_usage_insights(daily_usage, monthly_trends)
        }
    
    def generate_system_analytics(self) -> Dict[str, Any]:
        """전체 시스템 분석"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 통계
        cursor.execute('''
            SELECT tier, COUNT(*), 
                   COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users
            FROM users 
            GROUP BY tier
        ''')
        
        user_stats = {}
        total_users = 0
        active_users = 0
        
        for tier, count, active in cursor.fetchall():
            user_stats[tier] = {"total": count, "active": active}
            total_users += count
            active_users += active
        
        # 수익 통계
        cursor.execute('''
            SELECT billing_cycle, SUM(total_cost)
            FROM billing_records
            WHERE payment_status = 'paid'
            GROUP BY billing_cycle
            ORDER BY billing_cycle DESC
            LIMIT 12
        ''')
        
        revenue_trends = [
            {"month": cycle, "revenue": revenue}
            for cycle, revenue in cursor.fetchall()
        ]
        
        # 사용량 통계
        cursor.execute('''
            SELECT usage_type, SUM(amount), SUM(cost)
            FROM usage_records
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY usage_type
        ''')
        
        usage_stats = {}
        total_cost = 0.0
        
        for usage_type, total_amount, cost in cursor.fetchall():
            usage_stats[usage_type] = {
                "total_amount": total_amount,
                "total_cost": cost
            }
            total_cost += cost
        
        conn.close()
        
        return {
            "system_overview": {
                "total_users": total_users,
                "active_users": active_users,
                "user_tiers": user_stats,
                "monthly_revenue": total_cost
            },
            "revenue_trends": revenue_trends,
            "usage_statistics": usage_stats,
            "performance_metrics": self._calculate_performance_metrics()
        }
    
    def _generate_usage_insights(self, daily_usage, monthly_trends) -> List[str]:
        """사용량 인사이트 생성"""
        insights = []
        
        # 사용량 증가 트렌드 분석
        if len(monthly_trends) >= 2:
            months = sorted(monthly_trends.keys())
            if len(months) >= 2:
                latest_month = months[-1]
                prev_month = months[-2]
                
                latest_total = sum(
                    data["amount"] for data in monthly_trends[latest_month].values()
                )
                prev_total = sum(
                    data["amount"] for data in monthly_trends[prev_month].values()
                )
                
                if prev_total > 0:
                    growth_rate = ((latest_total - prev_total) / prev_total) * 100
                    if growth_rate > 20:
                        insights.append(f"사용량이 전월 대비 {growth_rate:.1f}% 증가했습니다")
                    elif growth_rate < -20:
                        insights.append(f"사용량이 전월 대비 {abs(growth_rate):.1f}% 감소했습니다")
        
        # 비용 효율성 분석
        total_cost = sum(
            sum(month_data[usage_type]["cost"] for usage_type in month_data)
            for month_data in monthly_trends.values()
        )
        
        if total_cost > 0:
            insights.append(f"총 사용 비용: ${total_cost:.2f}")
        
        return insights
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 계산"""
        # 실제 구현에서는 Redis나 다른 메트릭 저장소에서 데이터 조회
        return {
            "average_response_time": 1.2,  # seconds
            "success_rate": 99.5,  # percentage
            "uptime": 99.9,  # percentage
            "cache_hit_rate": 85.3  # percentage
        }

class CommercialSystem:
    """상업화 시스템 메인 클래스"""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.user_db = UserDatabase(db_path)
        self.usage_tracker = UsageTracker(db_path)
        self.analytics = AnalyticsEngine(db_path)
        self.pricing_manager = PricingManager()
        
        self.logger = logging.getLogger(__name__)
    
    def authenticate_request(self, api_key: str) -> Optional[UserAccount]:
        """요청 인증"""
        user = self.user_db.get_user_by_api_key(api_key)
        
        if user and user.is_active:
            # 구독 만료 확인
            if user.subscription_expires and user.subscription_expires < datetime.now():
                self.logger.warning(f"구독 만료된 사용자: {user.username}")
                return None
            
            return user
        
        return None
    
    def check_usage_limits(self, user: UserAccount, usage_type: UsageType, 
                          requested_amount: int) -> Tuple[bool, str]:
        """사용량 제한 확인"""
        current_usage = user.current_usage.get(usage_type.value, 0)
        usage_limit = user.usage_limits.get(usage_type.value, 0)
        
        if current_usage + requested_amount > usage_limit:
            remaining = usage_limit - current_usage
            return False, f"사용량 제한 초과. 남은 할당량: {remaining}"
        
        return True, "사용 가능"
    
    def process_request(self, api_key: str, usage_type: UsageType, amount: int,
                       request_metadata: Dict = None) -> Tuple[bool, str, Optional[UserAccount]]:
        """요청 처리 (인증 + 사용량 체크 + 기록)"""
        # 1. 인증
        user = self.authenticate_request(api_key)
        if not user:
            return False, "인증 실패", None
        
        # 2. 사용량 제한 확인
        can_proceed, message = self.check_usage_limits(user, usage_type, amount)
        if not can_proceed:
            return False, message, user
        
        # 3. 사용량 기록
        success = self.usage_tracker.record_usage(
            user.user_id, usage_type, amount, request_metadata
        )
        
        if success:
            return True, "요청 처리 완료", user
        else:
            return False, "사용량 기록 실패", user
    
    def generate_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """사용자 대시보드 데이터 생성"""
        user = self.user_db.get_user_by_id(user_id)
        if not user:
            return {"error": "사용자를 찾을 수 없습니다"}
        
        # 현재 월 사용량
        current_usage = self.usage_tracker.get_user_usage(user_id)
        
        # 분석 데이터
        analytics = self.analytics.generate_user_analytics(user_id, days=30)
        
        # 요금 정보
        monthly_fee = self.pricing_manager.get_monthly_fee(user.tier)
        
        return {
            "user_info": {
                "username": user.username,
                "email": user.email,
                "tier": user.tier.value,
                "subscription_expires": user.subscription_expires.isoformat() if user.subscription_expires else None,
                "is_active": user.is_active
            },
            "usage_summary": current_usage,
            "usage_limits": user.usage_limits,
            "analytics": analytics,
            "billing_info": {
                "monthly_fee": monthly_fee,
                "estimated_usage_cost": current_usage["total_cost"],
                "total_estimated": monthly_fee + current_usage["total_cost"]
            }
        }
    
    def generate_admin_dashboard(self) -> Dict[str, Any]:
        """관리자 대시보드 데이터 생성"""
        system_analytics = self.analytics.generate_system_analytics()
        
        return {
            "system_analytics": system_analytics,
            "timestamp": datetime.now().isoformat()
        }

# 전역 상업화 시스템 인스턴스
commercial_system = CommercialSystem()

def create_user_account(username: str, email: str, tier: str = "free") -> UserAccount:
    """사용자 계정 생성 (편의 함수)"""
    user_tier = UserTier(tier)
    return commercial_system.user_db.create_user(username, email, user_tier)

def authenticate_api_request(api_key: str) -> Optional[UserAccount]:
    """API 요청 인증 (편의 함수)"""
    return commercial_system.authenticate_request(api_key)

def track_api_usage(api_key: str, usage_type: str, amount: int = 1) -> bool:
    """API 사용량 추적 (편의 함수)"""
    usage_enum = UsageType(usage_type)
    success, message, user = commercial_system.process_request(
        api_key, usage_enum, amount
    )
    return success

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 사용자 계정 생성
    user = create_user_account("testuser", "test@example.com", "basic")
    print(f"생성된 사용자: {user.username}, API 키: {user.api_key}")
    
    # API 사용량 추적
    success = track_api_usage(user.api_key, "query", 1)
    print(f"사용량 추적: {success}")
    
    # 대시보드 데이터
    dashboard = commercial_system.generate_user_dashboard(user.user_id)
    print(f"대시보드: {dashboard['usage_summary']}")
    
    # 관리자 대시보드
    admin_dashboard = commercial_system.generate_admin_dashboard()
    print(f"전체 사용자: {admin_dashboard['system_analytics']['system_overview']['total_users']}명")