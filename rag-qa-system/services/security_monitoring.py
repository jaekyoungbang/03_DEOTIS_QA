#!/usr/bin/env python3
"""
보안 및 성능 모니터링 시스템 - 상업화 QA 시스템의 보안과 성능을 실시간 모니터링
"""

import time
import json
import logging
import hashlib
import threading
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import psutil
import socket
from pathlib import Path
from collections import defaultdict, deque
import re
import ipaddress
import jwt

class ThreatLevel(Enum):
    """위협 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEventType(Enum):
    """보안 이벤트 타입"""
    SUSPICIOUS_REQUEST = "suspicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    AUTHENTICATION_FAILURE = "auth_failure"
    MALICIOUS_INPUT = "malicious_input"
    DATA_LEAK_ATTEMPT = "data_leak_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    INJECTION_ATTEMPT = "injection_attempt"

@dataclass
class SecurityEvent:
    """보안 이벤트"""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    source_ip: str
    user_agent: str
    request_path: str
    request_data: Dict[str, Any]
    description: str
    timestamp: datetime
    is_blocked: bool
    metadata: Dict[str, Any]

@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    response_times: List[float]
    error_rate: float
    concurrent_users: int
    cache_hit_rate: float

class SecurityAnalyzer:
    """보안 분석기"""
    
    def __init__(self):
        # 악성 패턴 정의
        self.malicious_patterns = {
            "sql_injection": [
                r"(union|select|insert|update|delete|drop)\s+.*\s+(from|into|where)",
                r"['\"];?\s*(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",
                r"(exec|execute|sp_|xp_)\s*\(",
                r"'.*or.*'.*='.*'",
                r"--\s*$",
                r"/\*.*\*/"
            ],
            "xss_injection": [
                r"<script[^>]*>.*</script>",
                r"javascript:",
                r"on\w+\s*=\s*['\"][^'\"]*['\"]",
                r"<iframe[^>]*>",
                r"eval\s*\(",
                r"document\.(write|cookie)"
            ],
            "command_injection": [
                r";.*\|",
                r"\$\(.*\)",
                r"`.*`",
                r"&&\s*(rm|del|format|cat|type)",
                r"\|\s*(curl|wget|nc|netcat)"
            ],
            "path_traversal": [
                r"\.\.\/",
                r"\.\.\\",
                r"%2e%2e%2f",
                r"%2e%2e%5c"
            ]
        }
        
        # IP 화이트리스트 (관리자 IP 등)
        self.whitelisted_ips = {
            "127.0.0.1",
            "::1",
            "192.168.0.0/16",
            "10.0.0.0/8"
        }
        
        # 속도 제한 설정
        self.rate_limits = {
            "default": {"requests": 100, "window": 3600},  # 시간당 100 요청
            "premium": {"requests": 1000, "window": 3600}, # 시간당 1000 요청
            "burst": {"requests": 10, "window": 60}        # 분당 10 요청 (버스트)
        }
        
        # 요청 히스토리 (IP별)
        self.request_history = defaultdict(deque)
        
        self.logger = logging.getLogger(__name__)
    
    def analyze_request(self, ip: str, user_agent: str, path: str, 
                       request_data: Dict, user_tier: str = "default") -> Optional[SecurityEvent]:
        """요청 보안 분석"""
        # 1. 속도 제한 확인
        if self._check_rate_limit(ip, user_tier):
            return self._create_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                ThreatLevel.MEDIUM,
                ip, user_agent, path, request_data,
                f"속도 제한 초과: {user_tier} 등급"
            )
        
        # 2. 악성 패턴 탐지
        malicious_event = self._detect_malicious_patterns(
            ip, user_agent, path, request_data
        )
        if malicious_event:
            return malicious_event
        
        # 3. 의심스러운 행위 패턴 분석
        suspicious_event = self._analyze_behavioral_patterns(
            ip, user_agent, path, request_data
        )
        if suspicious_event:
            return suspicious_event
        
        # 4. 데이터 유출 시도 탐지
        leak_event = self._detect_data_leak_attempts(
            ip, user_agent, path, request_data
        )
        if leak_event:
            return leak_event
        
        return None
    
    def _check_rate_limit(self, ip: str, user_tier: str) -> bool:
        """속도 제한 확인"""
        if self._is_whitelisted_ip(ip):
            return False
        
        current_time = time.time()
        rate_config = self.rate_limits.get(user_tier, self.rate_limits["default"])
        window_size = rate_config["window"]
        max_requests = rate_config["requests"]
        
        # 현재 윈도우 내의 요청만 유지
        request_times = self.request_history[ip]
        while request_times and current_time - request_times[0] > window_size:
            request_times.popleft()
        
        # 요청 추가
        request_times.append(current_time)
        
        # 제한 확인
        if len(request_times) > max_requests:
            return True
        
        # 버스트 제한 확인
        burst_config = self.rate_limits["burst"]
        recent_requests = [t for t in request_times if current_time - t <= burst_config["window"]]
        
        return len(recent_requests) > burst_config["requests"]
    
    def _detect_malicious_patterns(self, ip: str, user_agent: str, path: str,
                                  request_data: Dict) -> Optional[SecurityEvent]:
        """악성 패턴 탐지"""
        all_text = f"{path} {json.dumps(request_data)} {user_agent}"
        
        for category, patterns in self.malicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, all_text, re.IGNORECASE):
                    threat_level = ThreatLevel.HIGH if category in ["sql_injection", "command_injection"] else ThreatLevel.MEDIUM
                    
                    return self._create_security_event(
                        SecurityEventType.MALICIOUS_INPUT,
                        threat_level,
                        ip, user_agent, path, request_data,
                        f"{category} 패턴 탐지: {pattern[:50]}..."
                    )
        
        return None
    
    def _analyze_behavioral_patterns(self, ip: str, user_agent: str, path: str,
                                   request_data: Dict) -> Optional[SecurityEvent]:
        """행위 패턴 분석"""
        # 1. 봇/자동화 도구 탐지
        bot_indicators = [
            "bot", "crawler", "spider", "scraper", "curl", "wget", 
            "python-requests", "automation", "headless"
        ]
        
        if any(indicator in user_agent.lower() for indicator in bot_indicators):
            if not self._is_whitelisted_ip(ip):
                return self._create_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    ThreatLevel.LOW,
                    ip, user_agent, path, request_data,
                    f"자동화 도구 감지: {user_agent}"
                )
        
        # 2. 비정상적인 경로 접근
        sensitive_paths = ["/admin", "/config", "/backup", "/.env", "/debug"]
        if any(sensitive in path.lower() for sensitive in sensitive_paths):
            return self._create_security_event(
                SecurityEventType.UNAUTHORIZED_ACCESS,
                ThreatLevel.HIGH,
                ip, user_agent, path, request_data,
                f"민감한 경로 접근 시도: {path}"
            )
        
        # 3. 과도한 데이터 요청
        if isinstance(request_data, dict):
            data_str = json.dumps(request_data)
            if len(data_str) > 100000:  # 100KB 초과
                return self._create_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    ThreatLevel.MEDIUM,
                    ip, user_agent, path, request_data,
                    f"과도한 데이터 크기: {len(data_str)} bytes"
                )
        
        return None
    
    def _detect_data_leak_attempts(self, ip: str, user_agent: str, path: str,
                                 request_data: Dict) -> Optional[SecurityEvent]:
        """데이터 유출 시도 탐지"""
        # 시스템 정보 요청 패턴
        system_info_patterns = [
            r"version", r"config", r"env", r"debug", r"status",
            r"admin", r"root", r"password", r"secret", r"key"
        ]
        
        all_text = f"{path} {json.dumps(request_data)}".lower()
        
        if any(re.search(pattern, all_text) for pattern in system_info_patterns):
            return self._create_security_event(
                SecurityEventType.DATA_LEAK_ATTEMPT,
                ThreatLevel.HIGH,
                ip, user_agent, path, request_data,
                "시스템 정보 유출 시도"
            )
        
        return None
    
    def _is_whitelisted_ip(self, ip: str) -> bool:
        """IP 화이트리스트 확인"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for whitelist_entry in self.whitelisted_ips:
                if "/" in whitelist_entry:
                    network = ipaddress.ip_network(whitelist_entry, strict=False)
                    if ip_obj in network:
                        return True
                elif ip == whitelist_entry:
                    return True
            return False
        except ValueError:
            return False
    
    def _create_security_event(self, event_type: SecurityEventType, threat_level: ThreatLevel,
                             ip: str, user_agent: str, path: str, request_data: Dict,
                             description: str) -> SecurityEvent:
        """보안 이벤트 생성"""
        event_id = hashlib.md5(f"{ip}_{path}_{time.time()}".encode()).hexdigest()[:12]
        
        return SecurityEvent(
            event_id=event_id,
            event_type=event_type,
            threat_level=threat_level,
            source_ip=ip,
            user_agent=user_agent,
            request_path=path,
            request_data=request_data,
            description=description,
            timestamp=datetime.now(),
            is_blocked=threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            metadata={}
        )

class PerformanceMonitor:
    """성능 모니터"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)  # 최근 1000개 메트릭 유지
        self.response_times = deque(maxlen=10000)  # 응답 시간 히스토리
        self.error_count = defaultdict(int)
        
        # 성능 임계값
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "response_time": 5.0,  # seconds
            "error_rate": 5.0      # percentage
        }
        
        self.logger = logging.getLogger(__name__)
    
    def collect_metrics(self) -> PerformanceMetrics:
        """성능 메트릭 수집"""
        # CPU 사용률
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        # 네트워크 I/O
        network = psutil.net_io_counters()
        network_io = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv
        }
        
        # 응답 시간 통계
        recent_response_times = list(self.response_times)[-100:]  # 최근 100개
        
        # 에러율 계산
        total_requests = sum(self.error_count.values()) if self.error_count else 1
        error_requests = self.error_count.get('error', 0)
        error_rate = (error_requests / total_requests) * 100
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_io=network_io,
            response_times=recent_response_times,
            error_rate=error_rate,
            concurrent_users=self._get_concurrent_users(),
            cache_hit_rate=self._get_cache_hit_rate()
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def record_response_time(self, response_time: float):
        """응답 시간 기록"""
        self.response_times.append(response_time)
    
    def record_error(self, error_type: str = 'error'):
        """에러 기록"""
        self.error_count[error_type] += 1
        self.error_count['total'] = self.error_count.get('total', 0) + 1
    
    def check_performance_alerts(self, metrics: PerformanceMetrics) -> List[str]:
        """성능 알림 확인"""
        alerts = []
        
        if metrics.cpu_usage > self.thresholds["cpu_usage"]:
            alerts.append(f"CPU 사용률 높음: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self.thresholds["memory_usage"]:
            alerts.append(f"메모리 사용률 높음: {metrics.memory_usage:.1f}%")
        
        if metrics.disk_usage > self.thresholds["disk_usage"]:
            alerts.append(f"디스크 사용률 높음: {metrics.disk_usage:.1f}%")
        
        if metrics.response_times:
            avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
            if avg_response_time > self.thresholds["response_time"]:
                alerts.append(f"응답 시간 초과: {avg_response_time:.2f}초")
        
        if metrics.error_rate > self.thresholds["error_rate"]:
            alerts.append(f"에러율 높음: {metrics.error_rate:.1f}%")
        
        return alerts
    
    def _get_concurrent_users(self) -> int:
        """현재 동시 사용자 수 (실제 구현에서는 세션 관리자에서 조회)"""
        # 네트워크 연결 수로 추정
        connections = psutil.net_connections(kind='inet')
        return len([conn for conn in connections if conn.status == 'ESTABLISHED'])
    
    def _get_cache_hit_rate(self) -> float:
        """캐시 적중률 (실제 구현에서는 Redis 등에서 조회)"""
        # 임시 구현
        return 85.0

class SecurityDatabase:
    """보안 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "data/security.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 보안 이벤트 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                threat_level TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                user_agent TEXT,
                request_path TEXT,
                request_data TEXT,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_blocked BOOLEAN NOT NULL,
                metadata TEXT
            )
        ''')
        
        # 성능 메트릭 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_usage REAL NOT NULL,
                memory_usage REAL NOT NULL,
                disk_usage REAL NOT NULL,
                network_io TEXT,
                response_times TEXT,
                error_rate REAL NOT NULL,
                concurrent_users INTEGER NOT NULL,
                cache_hit_rate REAL NOT NULL
            )
        ''')
        
        # 차단된 IP 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_ips (
                ip TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                blocked_at TEXT NOT NULL,
                expires_at TEXT,
                is_permanent BOOLEAN NOT NULL
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_ip ON security_events(source_ip)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)')
        
        conn.commit()
        conn.close()
    
    def save_security_event(self, event: SecurityEvent):
        """보안 이벤트 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO security_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id,
            event.event_type.value,
            event.threat_level.value,
            event.source_ip,
            event.user_agent,
            event.request_path,
            json.dumps(event.request_data),
            event.description,
            event.timestamp.isoformat(),
            event.is_blocked,
            json.dumps(event.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def save_performance_metrics(self, metrics: PerformanceMetrics):
        """성능 메트릭 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics 
            (timestamp, cpu_usage, memory_usage, disk_usage, network_io, 
             response_times, error_rate, concurrent_users, cache_hit_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.timestamp.isoformat(),
            metrics.cpu_usage,
            metrics.memory_usage,
            metrics.disk_usage,
            json.dumps(metrics.network_io),
            json.dumps(metrics.response_times),
            metrics.error_rate,
            metrics.concurrent_users,
            metrics.cache_hit_rate
        ))
        
        conn.commit()
        conn.close()
    
    def get_security_events(self, hours: int = 24, threat_level: ThreatLevel = None) -> List[SecurityEvent]:
        """보안 이벤트 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        if threat_level:
            cursor.execute('''
                SELECT * FROM security_events 
                WHERE timestamp >= ? AND threat_level = ?
                ORDER BY timestamp DESC
            ''', (start_time.isoformat(), threat_level.value))
        else:
            cursor.execute('''
                SELECT * FROM security_events 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (start_time.isoformat(),))
        
        events = []
        for row in cursor.fetchall():
            event = SecurityEvent(
                event_id=row[0],
                event_type=SecurityEventType(row[1]),
                threat_level=ThreatLevel(row[2]),
                source_ip=row[3],
                user_agent=row[4],
                request_path=row[5],
                request_data=json.loads(row[6]) if row[6] else {},
                description=row[7],
                timestamp=datetime.fromisoformat(row[8]),
                is_blocked=bool(row[9]),
                metadata=json.loads(row[10]) if row[10] else {}
            )
            events.append(event)
        
        conn.close()
        return events
    
    def block_ip(self, ip: str, reason: str, duration_hours: int = None):
        """IP 차단"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        blocked_at = datetime.now()
        expires_at = blocked_at + timedelta(hours=duration_hours) if duration_hours else None
        is_permanent = duration_hours is None
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_ips VALUES (?, ?, ?, ?, ?)
        ''', (
            ip,
            reason,
            blocked_at.isoformat(),
            expires_at.isoformat() if expires_at else None,
            is_permanent
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.warning(f"IP 차단: {ip}, 사유: {reason}, 기간: {'영구' if is_permanent else f'{duration_hours}시간'}")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """IP 차단 상태 확인"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now()
        
        cursor.execute('''
            SELECT expires_at, is_permanent FROM blocked_ips 
            WHERE ip = ?
        ''', (ip,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        expires_at, is_permanent = result
        
        # 영구 차단
        if is_permanent:
            return True
        
        # 임시 차단 - 만료 시간 확인
        if expires_at:
            expiry_time = datetime.fromisoformat(expires_at)
            return current_time < expiry_time
        
        return False

class MonitoringSystem:
    """모니터링 시스템 메인 클래스"""
    
    def __init__(self, db_path: str = "data/security.db"):
        self.security_analyzer = SecurityAnalyzer()
        self.performance_monitor = PerformanceMonitor()
        self.db = SecurityDatabase(db_path)
        
        # 모니터링 스레드
        self.monitoring_thread = None
        self.is_monitoring = False
        
        # 알림 설정
        self.alert_handlers = []
        
        self.logger = logging.getLogger(__name__)
    
    def analyze_request_security(self, ip: str, user_agent: str, path: str, 
                               request_data: Dict, user_tier: str = "default") -> Tuple[bool, Optional[str]]:
        """요청 보안 분석 및 차단 결정"""
        # 1. IP 차단 상태 확인
        if self.db.is_ip_blocked(ip):
            return False, "차단된 IP에서의 요청"
        
        # 2. 보안 분석 수행
        security_event = self.security_analyzer.analyze_request(
            ip, user_agent, path, request_data, user_tier
        )
        
        if security_event:
            # 보안 이벤트 저장
            self.db.save_security_event(security_event)
            
            # 심각한 위협인 경우 IP 차단
            if security_event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                duration = 24 if security_event.threat_level == ThreatLevel.HIGH else None  # CRITICAL은 영구차단
                self.db.block_ip(ip, security_event.description, duration)
            
            # 알림 발송
            self._send_security_alert(security_event)
            
            return not security_event.is_blocked, security_event.description
        
        return True, None
    
    def record_request_metrics(self, response_time: float, is_error: bool = False):
        """요청 메트릭 기록"""
        self.performance_monitor.record_response_time(response_time)
        
        if is_error:
            self.performance_monitor.record_error()
    
    def start_continuous_monitoring(self, interval_seconds: int = 60):
        """연속 모니터링 시작"""
        if self.is_monitoring:
            self.logger.warning("모니터링이 이미 실행 중입니다")
            return
        
        self.is_monitoring = True
        
        def monitoring_loop():
            while self.is_monitoring:
                try:
                    # 성능 메트릭 수집
                    metrics = self.performance_monitor.collect_metrics()
                    self.db.save_performance_metrics(metrics)
                    
                    # 성능 알림 확인
                    alerts = self.performance_monitor.check_performance_alerts(metrics)
                    for alert in alerts:
                        self._send_performance_alert(alert)
                    
                    # 보안 이벤트 분석
                    self._analyze_security_trends()
                    
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    self.logger.error(f"모니터링 오류: {e}")
                    time.sleep(30)  # 오류 발생 시 30초 후 재시도
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info(f"연속 모니터링 시작: {interval_seconds}초 간격")
    
    def stop_continuous_monitoring(self):
        """연속 모니터링 중지"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("연속 모니터링 중지")
    
    def get_security_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """보안 대시보드 데이터"""
        events = self.db.get_security_events(hours)
        
        # 이벤트 통계
        event_stats = defaultdict(int)
        threat_stats = defaultdict(int)
        ip_stats = defaultdict(int)
        
        for event in events:
            event_stats[event.event_type.value] += 1
            threat_stats[event.threat_level.value] += 1
            ip_stats[event.source_ip] += 1
        
        # 상위 공격자 IP
        top_attackers = sorted(ip_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period_hours": hours,
            "total_events": len(events),
            "event_breakdown": dict(event_stats),
            "threat_level_breakdown": dict(threat_stats),
            "top_attacker_ips": top_attackers,
            "recent_high_threats": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "type": event.event_type.value,
                    "threat_level": event.threat_level.value,
                    "source_ip": event.source_ip,
                    "description": event.description
                }
                for event in events[:10] if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            ]
        }
    
    def get_performance_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """성능 대시보드 데이터"""
        recent_metrics = list(self.performance_monitor.metrics_history)[-100:]
        
        if not recent_metrics:
            return {"message": "성능 데이터가 없습니다"}
        
        # 평균 계산
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)
        
        # 응답 시간 통계
        all_response_times = []
        for m in recent_metrics:
            all_response_times.extend(m.response_times)
        
        response_stats = {}
        if all_response_times:
            response_stats = {
                "average": sum(all_response_times) / len(all_response_times),
                "p95": sorted(all_response_times)[int(len(all_response_times) * 0.95)],
                "p99": sorted(all_response_times)[int(len(all_response_times) * 0.99)]
            }
        
        return {
            "period_hours": hours,
            "resource_usage": {
                "cpu_average": avg_cpu,
                "memory_average": avg_memory,
                "disk_average": avg_disk
            },
            "response_time_stats": response_stats,
            "current_metrics": {
                "cpu_usage": recent_metrics[-1].cpu_usage,
                "memory_usage": recent_metrics[-1].memory_usage,
                "concurrent_users": recent_metrics[-1].concurrent_users,
                "cache_hit_rate": recent_metrics[-1].cache_hit_rate,
                "error_rate": recent_metrics[-1].error_rate
            } if recent_metrics else {}
        }
    
    def _analyze_security_trends(self):
        """보안 트렌드 분석"""
        # 최근 1시간 동안의 이벤트 분석
        events = self.db.get_security_events(hours=1)
        
        # IP별 이벤트 빈도 분석
        ip_event_count = defaultdict(int)
        for event in events:
            ip_event_count[event.source_ip] += 1
        
        # 의심스러운 IP 자동 차단 (1시간에 10회 이상 보안 이벤트)
        for ip, count in ip_event_count.items():
            if count >= 10 and not self.db.is_ip_blocked(ip):
                self.db.block_ip(ip, f"자동 차단: 1시간 내 {count}회 보안 이벤트", 24)
    
    def _send_security_alert(self, event: SecurityEvent):
        """보안 알림 발송"""
        alert_message = f"보안 이벤트 발생: {event.description} (IP: {event.source_ip})"
        
        for handler in self.alert_handlers:
            try:
                handler("security", alert_message, event)
            except Exception as e:
                self.logger.error(f"알림 발송 실패: {e}")
        
        self.logger.warning(alert_message)
    
    def _send_performance_alert(self, alert_message: str):
        """성능 알림 발송"""
        for handler in self.alert_handlers:
            try:
                handler("performance", alert_message, None)
            except Exception as e:
                self.logger.error(f"성능 알림 발송 실패: {e}")
        
        self.logger.warning(f"성능 알림: {alert_message}")
    
    def add_alert_handler(self, handler):
        """알림 핸들러 추가"""
        self.alert_handlers.append(handler)

# 전역 모니터링 시스템 인스턴스
monitoring_system = MonitoringSystem()

def check_request_security(ip: str, user_agent: str, path: str, 
                         request_data: Dict, user_tier: str = "default") -> Tuple[bool, Optional[str]]:
    """요청 보안 확인 (편의 함수)"""
    return monitoring_system.analyze_request_security(ip, user_agent, path, request_data, user_tier)

def record_request_performance(response_time: float, is_error: bool = False):
    """요청 성능 기록 (편의 함수)"""
    monitoring_system.record_request_metrics(response_time, is_error)

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 보안 분석 테스트
    is_allowed, reason = check_request_security(
        "192.168.1.100",
        "Mozilla/5.0",
        "/api/query",
        {"question": "BC카드 안내"},
        "basic"
    )
    print(f"요청 허용: {is_allowed}, 사유: {reason}")
    
    # 악성 요청 테스트
    is_allowed, reason = check_request_security(
        "10.0.0.1", 
        "sqlmap",
        "/api/query", 
        {"question": "'; DROP TABLE users; --"}, 
        "free"
    )
    print(f"악성 요청 허용: {is_allowed}, 사유: {reason}")
    
    # 연속 모니터링 시작
    monitoring_system.start_continuous_monitoring(10)  # 10초 간격
    
    # 성능 메트릭 기록
    record_request_performance(1.2, False)
    record_request_performance(5.5, True)
    
    # 대시보드 데이터
    security_dashboard = monitoring_system.get_security_dashboard(1)
    performance_dashboard = monitoring_system.get_performance_dashboard(1)
    
    print(f"보안 이벤트: {security_dashboard['total_events']}개")
    print(f"현재 CPU 사용률: {performance_dashboard.get('current_metrics', {}).get('cpu_usage', 'N/A')}%")
    
    time.sleep(3)
    monitoring_system.stop_continuous_monitoring()