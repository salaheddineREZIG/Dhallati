from flask import request, redirect, url_for, flash
from .auth.models import User
from functools import wraps
import requests
import time
import os
import requests

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('id_token')

        if not token:
            flash("Please login first", "danger")
            return redirect(url_for('auth.login'))

        try:
            # Verify the token using Google's public keys
            token_info = requests.get(os.getenv("GOOGLE_TOKEN_INFO")+token)

            if token_info.status_code != 200:
                flash("Invalid token. Please log in again.", "danger")
                return redirect(url_for('auth.login'))

            token_data = token_info.json()

            # Check if token has expired
            if int(token_data.get('exp')) < time.time():
                flash("Token has expired. Please log in again.", "danger")
                return redirect(url_for('auth.login'))

            # Retrieve User using Google ID from token_data
            user = User.query.filter_by(google_id=token_data['sub']).first()

            if not user:
                flash("Invalid token. Please log in again.", "danger")
                return redirect(url_for('auth.login'))

            return f(user, *args, **kwargs)

        except Exception as e:
            flash("An error occurred. Please log in again.", "danger")
            return redirect(url_for('auth.login'))

    return decorated_function
