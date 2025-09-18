"""
BAIS Authentication Module
==========================
Hybrid authentication using PostgreSQL users + streamlit-authenticator cookies.
Simple, secure session management with 2-hour timeout.

Usage:
    from utils.auth import Authenticator
    auth = Authenticator()
    authenticator = auth.get_authenticator()
    name, authentication_status, username = authenticator.login()
"""

import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .config import get_config
from .database import get_database
from .app_logger import get_logger, log_auth_event


class Authenticator:
    """
    Hybrid authentication manager for BAIS application.
    Combines PostgreSQL user storage with cookie-based sessions.
    """
    
    def __init__(self):
        """Initialize authentication manager."""
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)
        
        # Get auth configuration
        self.auth_config = self.config.get_auth_config()
        
        # Database connection for user management (read-only by default)
        self.db = get_database('ro', 'live')
        
        self.logger.info("Authentication manager initialized")
    
    def load_users_from_db(self) -> Dict[str, Dict]:
        """
        Load active users from PostgreSQL live.auth_users table.
        
        Returns:
            Dictionary of users in format expected by streamlit-authenticator
        """
        try:
            # Query active users from live schema
            query = """
                SELECT 
                    u.email,
                    u.password_hash,
                    u.user_id,
                    r.role_name,
                    u.is_active
                FROM live.auth_users u
                JOIN live.auth_user_roles r ON u.role_id = r.role_id
                WHERE u.is_active = true
            """
            
            users = self.db.fetch_all(query)
            
            # Convert to streamlit-authenticator format
            credentials = {}
            for user in users:
                # Use email as username
                username = user['email']
                credentials[username] = {
                    'email': user['email'],
                    'name': user['email'].split('@')[0],  # Extract name from email
                    'password': user['password_hash'],  # Already hashed
                    'role': user['role_name'],
                    'user_id': user['user_id']
                }
            
            self.logger.info(f"Loaded {len(credentials)} active users from database")
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to load users from database: {e}")
            return {}
    
    def get_authenticator(self) -> stauth.Authenticate:
        """
        Create and configure streamlit-authenticator instance.
        
        Returns:
            Configured Authenticate object with 2-hour cookie expiry
        """
        # Load users from database
        users = self.load_users_from_db()
        
        if not users:
            self.logger.warning("No users loaded from database")
            # Return authenticator with empty credentials
            users = {'dummy': {'email': '', 'name': '', 'password': ''}}
        
        # Prepare credentials dictionary
        credentials = {
            'usernames': users
        }
        
        # Get cookie configuration
        cookie_name = self.auth_config.get('cookie_name', 'bais_auth')
        cookie_key = self.auth_config.get('cookie_key')
        expiry_hours = self.auth_config.get('expiry_hours', 2)
        
        # Validate cookie key
        if not cookie_key:
            self.logger.error("Cookie key not found in configuration!")
            # Generate a temporary key (not secure for production!)
            import secrets
            cookie_key = secrets.token_hex(32)
            self.logger.warning("Using temporary cookie key - set AUTH_COOKIE_KEY in .env!")
        
        # Convert hours to days for streamlit-authenticator
        expiry_days = expiry_hours / 24.0
        
        # Create authenticator with cookie persistence
        authenticator = stauth.Authenticate(
            credentials,
            cookie_name,
            cookie_key,
            expiry_days,
            preauthorized=None  # No pre-authorized emails
        )
        
        self.logger.debug(f"Created authenticator with {expiry_hours}-hour cookie expiry")
        
        return authenticator
    
    def update_last_login(self, email: str) -> bool:
        """
        Update user's last_login timestamp after successful authentication.
        
        Args:
            email: User's email address
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Need write access for this operation
            db_rw = get_database('rw', 'live')
            
            query = """
                UPDATE live.auth_users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE email = %s AND is_active = true
            """
            
            affected = db_rw.execute(query, (email,))
            
            if affected > 0:
                log_auth_event("login", email, True)
                self.logger.info(f"Updated last_login for user: {email}")
                return True
            else:
                self.logger.warning(f"No active user found to update: {email}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update last_login: {e}")
            log_auth_event("login", email, False)
            return False
    
    def get_user_role(self, email: str) -> Optional[str]:
        """
        Get user's role from database.
        
        Args:
            email: User's email address
            
        Returns:
            Role name or None if user not found
        """
        query = """
            SELECT r.role_name
            FROM live.auth_users u
            JOIN live.auth_user_roles r ON u.role_id = r.role_id
            WHERE u.email = %s AND u.is_active = true
        """
        
        result = self.db.fetch_one(query, (email,))
        return result['role_name'] if result else None
    
    def is_admin(self, email: str) -> bool:
        """
        Check if user has admin role.
        
        Args:
            email: User's email address
            
        Returns:
            True if user is admin, False otherwise
        """
        role = self.get_user_role(email)
        return role == 'admin'
    
    def is_readonly(self, email: str) -> bool:
        """
        Check if user has readonly role.
        
        Args:
            email: User's email address
            
        Returns:
            True if user is readonly, False otherwise
        """
        role = self.get_user_role(email)
        return role == 'readonly'
    
    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)


def require_auth(func):
    """
    Simple decorator to require authentication for a function.
    Use this to protect sensitive operations.
    
    Usage:
        @require_auth
        def admin_function():
            # This will only run if user is authenticated
            pass
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'authentication_status' not in st.session_state:
            st.error("Authentication required")
            st.stop()
        
        if not st.session_state.get('authentication_status'):
            st.error("Please login to continue")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def require_role(role: str):
    """
    Decorator to require specific role for a function.
    
    Args:
        role: Required role name ('admin', 'editor', etc.)
        
    Usage:
        @require_role('admin')
        def admin_only_function():
            # This will only run if user has admin role
            pass
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check authentication first
            if 'authentication_status' not in st.session_state:
                st.error("Authentication required")
                st.stop()
            
            if not st.session_state.get('authentication_status'):
                st.error("Please login to continue")
                st.stop()
            
            # Check role
            username = st.session_state.get('username')
            if not username:
                st.error("User session invalid")
                st.stop()
            
            auth = Authenticator()
            user_role = auth.get_user_role(username)
            
            if user_role != role:
                st.error(f"This function requires {role} role. Your role: {user_role}")
                st.stop()
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_current_user() -> Optional[Dict]:
    """
    Get current authenticated user information from session.
    
    Returns:
        Dictionary with user info or None if not authenticated
    """
    if not st.session_state.get('authentication_status'):
        return None
    
    username = st.session_state.get('username')
    name = st.session_state.get('name')
    
    if username:
        auth = Authenticator()
        role = auth.get_user_role(username)
        
        return {
            'username': username,
            'name': name,
            'role': role,
            'authenticated': True
        }
    
    return None


def handle_authentication(location: str = 'main') -> Tuple[Optional[str], Optional[bool], Optional[str]]:
    """
    Handle the authentication flow with proper error handling.
    
    Args:
        location: Where to display login ('main' or 'sidebar')
        
    Returns:
        Tuple of (name, authentication_status, username)
    """
    try:
        auth = Authenticator()
        authenticator = auth.get_authenticator()
        
        # Perform login
        name, authentication_status, username = authenticator.login('Login', location)
        
        # Update last login on successful authentication
        if authentication_status and username:
            auth.update_last_login(username)
        
        return name, authentication_status, username
        
    except Exception as e:
        logger = get_logger('BAIS.Auth')
        logger.error(f"Authentication error: {e}")
        st.error("Authentication system error. Please contact administrator.")
        return None, False, None


# Convenience function for simple authentication check
def is_authenticated() -> bool:
    """
    Check if user is currently authenticated.
    
    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get('authentication_status', False)