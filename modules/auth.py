from functools import wraps
from flask import session, redirect, url_for

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("staff_id"):
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                return redirect(url_for("home"))
            return view(*args, **kwargs)

        return wrapped

    return decorator

def current_staff():
    if not session.get("staff_id"):
        return None
    return {
        "staff_id": session.get("staff_id"),
        "username": session.get("username"),
        "first_name": session.get("first_name"),
        "last_name": session.get("last_name"),
        "role": session.get("role"),
    }
