import json
import os
from datetime import datetime

class AdminConfig:
    """Admin configuration manager"""
    
    CONFIG_FILE = 'data/config/admin_settings.json'
    DEFAULT_PASSWORD = 'Kbfcc!23'  # 기본 비밀번호
    
    DEFAULT_SETTINGS = {
        'cache_type': 'sqlite',  # 'sqlite' or 'redis'
        'redis_config': {
            'host': 'localhost',
            'port': 6379,
            'password': None
        },
        'chunk_strategy': {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'separator': '\n\n'
        },
        'embedding_config': {
            'model': 'text-embedding-3-small',
            'dimension': 1536
        },
        'llm_config': {
            'default_model': 'gpt-4o-mini',
            'temperature': 0.7,
            'max_tokens': 2000
        },
        'cache_config': {
            'ttl_hours': 24,
            'max_entries': 10000,
            'popular_threshold': 5,  # 5회 이상 조회시 RDB 저장
            'validation_enabled': True  # 문서 변경 감지 활성화
        },
        'admin_password_hash': None,  # Will be set on first use
        'last_updated': None
    }
    
    def __init__(self):
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file or create default"""
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Merge with defaults for any missing keys
                    for key, value in self.DEFAULT_SETTINGS.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            except:
                return self.DEFAULT_SETTINGS.copy()
        else:
            # Create default settings file
            self.save_settings(self.DEFAULT_SETTINGS)
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings=None):
        """Save settings to file"""
        if settings is None:
            settings = self.settings
        
        settings['last_updated'] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        self.settings = settings
        return True
    
    def verify_password(self, password):
        """Verify admin password"""
        import hashlib
        
        # If no password is set, use default
        if not self.settings.get('admin_password_hash'):
            return password == self.DEFAULT_PASSWORD
        
        # Hash and compare
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.settings['admin_password_hash']
    
    def set_password(self, new_password):
        """Set new admin password"""
        import hashlib
        
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        self.settings['admin_password_hash'] = password_hash
        self.save_settings()
        return True
    
    def get_cache_type(self):
        """Get current cache type"""
        return self.settings.get('cache_type', 'sqlite')
    
    def set_cache_type(self, cache_type):
        """Set cache type (sqlite or redis)"""
        if cache_type not in ['sqlite', 'redis']:
            raise ValueError("Cache type must be 'sqlite' or 'redis'")
        
        self.settings['cache_type'] = cache_type
        self.save_settings()
        return True
    
    def get_redis_config(self):
        """Get Redis configuration"""
        return self.settings.get('redis_config', {})
    
    def set_redis_config(self, host=None, port=None, password=None):
        """Set Redis configuration"""
        if host:
            self.settings['redis_config']['host'] = host
        if port:
            self.settings['redis_config']['port'] = port
        if password is not None:
            self.settings['redis_config']['password'] = password
        
        self.save_settings()
        return True
    
    def get_chunk_strategy(self):
        """Get chunk strategy settings"""
        return self.settings.get('chunk_strategy', {})
    
    def set_chunk_strategy(self, chunk_size=None, chunk_overlap=None, separator=None):
        """Set chunk strategy"""
        if chunk_size:
            self.settings['chunk_strategy']['chunk_size'] = chunk_size
        if chunk_overlap is not None:
            self.settings['chunk_strategy']['chunk_overlap'] = chunk_overlap
        if separator:
            self.settings['chunk_strategy']['separator'] = separator
        
        self.save_settings()
        return True
    
    def get_all_settings(self):
        """Get all settings"""
        # Remove sensitive data
        settings_copy = self.settings.copy()
        if 'admin_password_hash' in settings_copy:
            settings_copy['admin_password_hash'] = '***'
        if settings_copy.get('redis_config', {}).get('password'):
            settings_copy['redis_config']['password'] = '***'
        
        return settings_copy
    
    def update_settings(self, new_settings):
        """Update multiple settings at once"""
        # Don't allow password change through this method
        if 'admin_password_hash' in new_settings:
            del new_settings['admin_password_hash']
        
        # Update settings
        for key, value in new_settings.items():
            if key in self.settings:
                self.settings[key] = value
        
        self.save_settings()
        return True