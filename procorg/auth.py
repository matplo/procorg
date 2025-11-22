"""Authentication module for ProcOrg multi-user support."""

import os
import pwd
from functools import wraps
from typing import Optional, Dict
from flask import session, request, jsonify


class User:
    """Represents an authenticated user."""

    def __init__(self, username: str, uid: int):
        self.username = username
        self.uid = uid
        self.is_root = (uid == 0)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'username': self.username,
            'uid': self.uid,
            'is_root': self.is_root
        }


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user against system PAM.

    Args:
        username: System username
        password: User password

    Returns:
        User object if authentication succeeds, None otherwise
    """
    try:
        import pam
        p = pam.pam()

        if p.authenticate(username, password):
            # Get user info
            try:
                user_info = pwd.getpwnam(username)
                return User(username=username, uid=user_info.pw_uid)
            except KeyError:
                return None
        else:
            return None

    except ImportError:
        # PAM not available - fall back to development mode
        # WARNING: This is insecure and should only be used for development!
        print("WARNING: python-pam not installed, using development authentication")
        print("         This is INSECURE and should not be used in production!")

        try:
            user_info = pwd.getpwnam(username)
            # In dev mode, accept any password for testing
            # TODO: Remove this in production
            return User(username=username, uid=user_info.pw_uid)
        except KeyError:
            return None


def get_user_uid(username: str) -> Optional[int]:
    """Get the UID for a username.

    Args:
        username: System username

    Returns:
        UID if user exists, None otherwise
    """
    try:
        return pwd.getpwnam(username).pw_uid
    except KeyError:
        return None


def get_current_user() -> Optional[User]:
    """Get the currently authenticated user from session.

    Returns:
        User object if authenticated, None otherwise
    """
    if 'user' not in session:
        return None

    user_data = session['user']
    return User(
        username=user_data['username'],
        uid=user_data['uid']
    )


def require_auth(f):
    """Decorator to require authentication for a route.

    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = get_current_user()
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_root(f):
    """Decorator to require root access for a route.

    Usage:
        @app.route('/api/admin')
        @require_root
        def admin_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_root:
            return jsonify({'error': 'Root access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def init_session(user: User) -> None:
    """Initialize session for authenticated user.

    Args:
        user: Authenticated user
    """
    session['user'] = user.to_dict()
    session.permanent = True  # Session persists across browser closes


def clear_session() -> None:
    """Clear the current session (logout)."""
    session.clear()
