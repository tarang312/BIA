import random
from datetime import datetime, date, timedelta
import bcrypt
import streamlit as st
from typing import Optional, List, Dict, Any
from bia_core.schemas import UserProfile, WasteLog

@st.cache_resource
def get_auth_store():
    """Get thread-safe authentication store"""
    return {
        'users': {},
        'waste_logs': []
    }

class AuthStore:
    """Thread-safe authentication and data store"""
    
    def __init__(self):
        self.store = get_auth_store()
        self._init_demo_user()
    
    def _init_demo_user(self):
        """Initialize demo user if not exists"""
        if 'demo' not in self.store['users']:
            # Hash the demo password
            password_hash = bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt())
            
            demo_profile = UserProfile(
                username='demo',
                password_hash=password_hash.decode('utf-8'),
                entity_name='Demo Bio-energy Corp',
                city='Mumbai',
                waste_type='organic'
            )
            
            self.store['users']['demo'] = demo_profile
            # Pre-populate 100 dummy rows for demo user
            self.generate_dummy_logs(username='demo', count=100)
        elif not self.get_user_logs('demo'):
            self.generate_dummy_logs(username='demo', count=100)
    
    def generate_dummy_logs(self, username: str, count: int = 100, base_waste: float = 45.0) -> List[WasteLog]:
        """Generate N realistic dummy waste log entries over past N days"""
        today = date.today()
        # Remove existing logs for user to avoid duplicates if re-generating
        self.store['waste_logs'] = [l for l in self.store['waste_logs'] if l.username != username]
        
        # Deterministic pseudo-random seed based on username
        rng = random.Random(hash(username) & 0xffffffff)
        
        new_logs = []
        for i in range(count - 1, -1, -1):
            log_date = today - timedelta(days=i)
            # Add day-of-week variation and random noise
            day_mult = 1.15 if log_date.weekday() < 5 else 0.85
            trend = 1.0 + (count - i) * 0.0015
            noise = rng.uniform(-8.0, 8.0)
            waste_val = round(max(5.0, base_waste * day_mult * trend + noise), 2)
            
            log = WasteLog(
                username=username,
                date=log_date,
                waste_tons=waste_val
            )
            new_logs.append(log)
            self.store['waste_logs'].append(log)
            
        return new_logs
    
    def add_user(self, username: str, password: str, entity_name: str, 
                 city: str, waste_type: str) -> bool:
        """Add new user with hashed password"""
        if username in self.store['users']:
            return False
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_profile = UserProfile(
            username=username,
            password_hash=password_hash.decode('utf-8'),
            entity_name=entity_name,
            city=city,
            waste_type=waste_type
        )
        
        self.store['users'][username] = user_profile
        # Auto generate 100 dummy rows for new user so they immediately have data
        self.generate_dummy_logs(username=username, count=100)
        return True
    
    def validate_user(self, username: str, password: str) -> Optional[UserProfile]:
        """Validate user credentials"""
        if username not in self.store['users']:
            return None
        
        user_profile = self.store['users'][username]
        
        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), user_profile.password_hash.encode('utf-8')):
            return user_profile
        
        return None
    
    def add_waste_log(self, waste_log: WasteLog):
        """Add waste log entry"""
        self.store['waste_logs'].append(waste_log)
    
    def get_user_logs(self, username: str) -> List[WasteLog]:
        """Get all waste logs for a user sorted by date ascending"""
        user_logs = [log for log in self.store['waste_logs'] if log.username == username]
        return sorted(user_logs, key=lambda x: x.date)

# Global auth store instance
auth_store = AuthStore()

def add_user(username: str, password: str, entity_name: str, 
             city: str, waste_type: str) -> bool:
    """Add new user"""
    return auth_store.add_user(username, password, entity_name, city, waste_type)

def validate_user(username: str, password: str) -> Optional[UserProfile]:
    """Validate user credentials"""
    return auth_store.validate_user(username, password)

def add_waste_log(waste_log: WasteLog):
    """Add waste log"""
    auth_store.add_waste_log(waste_log)

def get_user_logs(username: str) -> List[WasteLog]:
    """Get user's waste logs"""
    return auth_store.get_user_logs(username)

def generate_dummy_logs(username: str, count: int = 100) -> List[WasteLog]:
    """Generate N dummy logs for user"""
    return auth_store.generate_dummy_logs(username, count)

