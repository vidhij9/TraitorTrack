"""
Fast Authentication Module - Optimized for high concurrency
Uses bcrypt with reduced rounds for faster password verification
"""

import bcrypt
import hashlib
import time
from functools import lru_cache

class FastAuth:
    """Fast authentication with optimized password hashing"""
    
    # Use 6 rounds for bcrypt (milliseconds instead of seconds)
    # Note: In production, use at least 10 rounds
    BCRYPT_ROUNDS = 6
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using fast bcrypt settings"""
        # Use bcrypt with reduced rounds for speed
        salt = bcrypt.gensalt(rounds=FastAuth.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash - optimized for speed"""
        try:
            # Handle both bcrypt and werkzeug hashes
            if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
                # Bcrypt hash
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            else:
                # Fallback to werkzeug for existing hashes
                from werkzeug.security import check_password_hash
                return check_password_hash(password_hash, password)
        except Exception:
            return False
    
    @staticmethod
    @lru_cache(maxsize=128)
    def quick_hash(value: str) -> str:
        """Quick hash for caching keys"""
        return hashlib.md5(value.encode()).hexdigest()[:16]
    
    @staticmethod
    def migrate_password_hash(user, password: str) -> bool:
        """Migrate old slow hash to fast bcrypt hash"""
        try:
            # Generate new fast hash
            new_hash = FastAuth.hash_password(password)
            
            # Update user's password hash
            user.password_hash = new_hash
            
            from app_clean import db
            db.session.commit()
            
            return True
        except Exception:
            return False

# Pre-compile bcrypt for faster first use
def warmup():
    """Warmup bcrypt to avoid cold start delays"""
    try:
        test_password = "warmup_test"
        test_hash = FastAuth.hash_password(test_password)
        FastAuth.verify_password(test_password, test_hash)
    except:
        pass

# Run warmup on import
warmup()