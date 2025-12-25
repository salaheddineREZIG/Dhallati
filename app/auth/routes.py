from flask import redirect, url_for, flash, make_response, request, render_template, current_app
from app import db, oauth
from .models import User
from authlib.integrations.base_client.errors import AuthlibBaseError
import os
from app.decorators import login_required
from . import auth
from .forms import LoginForm
from datetime import datetime
from app.functions import log_action
import requests


@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Note: your original code used form.validate_on_submit() inside GET which is unusual.
    # I'll keep the same behavior but log unexpected conditions.
    try:
        form = LoginForm()
        if request.method == 'GET':
            # If somehow the GET carries form data that validates, we handle it (keeps old logic)
            if form.validate_on_submit():
                if request.cookies.get('id_token'):
                    flash("Already logged in", "info")
                    return redirect(url_for("lost_and_found.lost_and_found_page"))
                try:
                    google = oauth.create_client('google')
                    redirect_uri = url_for('auth.callback', _external=True)
                    return google.authorize_redirect(redirect_uri)
                except requests.exceptions.ConnectionError:
                    current_app.logger.exception("Connection error while trying to authorize redirect to Google")
                    flash("Unable to connect to Google. Please check your internet connection.", "danger")
                    return redirect(url_for('auth.login'))
                except Exception:
                    current_app.logger.exception("Unexpected error during Google authorize redirect (GET/validate_on_submit)")
                    flash("An unexpected error occurred.", "danger")
                    return redirect(url_for('auth.login'))
            return render_template('login.html', form=form)

        # POST branch: start OAuth flow (same as your prior code)
        if request.cookies.get('id_token'):
            flash("Already logged in", "info")
            return redirect(url_for("lost_and_found.lost_and_found_page"))

        try:
            google = oauth.create_client('google')
            redirect_uri = url_for('auth.callback', _external=True)
            return google.authorize_redirect(redirect_uri)
        except requests.exceptions.ConnectionError:
            current_app.logger.exception("Connection error while trying to authorize redirect to Google (POST)")
            flash("Unable to connect to Google. Please check your internet connection.", "danger")
            return redirect(url_for('auth.login'))
        except Exception:
            current_app.logger.exception("Unexpected error during Google authorize redirect (POST)")
            flash("An unexpected error occurred.", "danger")
            return redirect(url_for('auth.login'))

    except Exception:
        current_app.logger.exception("Unhandled exception in auth.login")
        flash("An internal error occurred. Please try again later.", "danger")
        return redirect(url_for('auth.login'))


@auth.route('/callback')
def callback():
    try:
        google = oauth.create_client('google')
        full_token = google.authorize_access_token()

        if not full_token:
            current_app.logger.warning("authorize_access_token returned no token in /callback")
            flash("Failed to retrieve token", "danger")
            return redirect(url_for('auth.login'))

        id_token = full_token.get('id_token')
        profile = full_token.get('userinfo') or full_token.get('userinfo')  # keep existing key

        if not id_token or not profile:
            current_app.logger.warning("Missing id_token or userinfo in token response: %s", full_token)
            flash("Failed to retrieve token/profile", "danger")
            return redirect(url_for('auth.login'))

        # Enforce email domain
        """domain = os.getenv('LAGH_UNI_DOMAIN')
        if not profile.get('email') or not domain:
            current_app.logger.warning("Missing profile email or LAGH_UNI_DOMAIN not set. profile=%s domain=%s", profile, domain)
            flash("Authentication configuration error. Contact admin.", "danger")
            return redirect(url_for('auth.login'))
            

        if not profile['email'].endswith(domain):
            current_app.logger.info("Blocked login attempt from non-university email: %s", profile['email'])
            flash("Only Lagh University emails are allowed", "danger")
            return make_response(redirect(url_for('main.index')))

        """
        # Check if User exists in db
        try:
            user = User.query.filter_by(google_id=profile['sub']).first()
        except Exception:
            current_app.logger.exception("Database error when querying for user by google_id")
            flash("An internal error occurred. Please try again later.", "danger")
            return redirect(url_for('auth.login'))

        try:
            if not user:
                # Create new User
                user = User(
                    google_id=profile['sub'],
                    email=profile.get('email'),
                    name=profile.get('name'),
                    profile_pic=profile.get('picture')
                )
                db.session.add(user)
                db.session.commit()
                # Log user creation in AuditLog
                log_action(user.id, 'users', user.id, 'create', changes=f"User {user.email} created.")
                current_app.logger.info("Created new user: %s", user.email)
            else:
                user.last_login_at = datetime.utcnow()
                db.session.commit()
                # Log user login in AuditLog
                log_action(user.id, 'users', user.id, 'login', changes=f"User {user.email} logged in.")
                current_app.logger.info("Existing user logged in: %s", user.email)
        except Exception:
            current_app.logger.exception("Failed to create or update user during OAuth callback")
            # rollback to keep DB consistent
            try:
                db.session.rollback()
            except Exception:
                current_app.logger.exception("Rollback failed after user create/update error")
            flash("An internal error occurred. Please try again later.", "danger")
            return redirect(url_for('auth.login'))

        # Process User info and create a response
        try:
            response = make_response(redirect(url_for("lost_and_found.lost_and_found_page")))
            # set cookie (httponly+secure may break local dev on http, but preserving your settings)
            response.set_cookie("id_token", id_token, httponly=True, secure=True, samesite="Lax")
            flash("Logged in successfully", "success")
            return response
        except Exception:
            current_app.logger.exception("Failed while setting cookie/creating response in callback")
            flash("An internal error occurred. Please try again later.", "danger")
            return redirect(url_for('auth.login'))

    except AuthlibBaseError as e:
        current_app.logger.exception("AuthlibBaseError during OAuth callback")
        flash("Authentication failed. Please try again.", "danger")
        return redirect(url_for('auth.login'))
    except requests.exceptions.ConnectionError:
        current_app.logger.exception("Connection error during OAuth callback")
        flash("Unable to connect to authentication provider. Please check your connection.", "danger")
        return redirect(url_for('auth.login'))
    except Exception:
        current_app.logger.exception("Unhandled exception in OAuth callback")
        flash("An error occurred. Please try again later.", "danger")
        return redirect(url_for('auth.login'))


@auth.route('/logout')
@login_required
def logout(user):
    try:
        response = make_response(redirect(url_for("main.index")))
        response.set_cookie("id_token", "", expires=0)
        flash("Logged out successfully", "success")
        log_action(user['id'], 'users', user['id'], 'logout', changes=f"User {user['email']} logged out.")
        current_app.logger.info("User %s logged out", user['email'])
        return response
    except Exception:
        current_app.logger.exception("Failed during logout for user id=%s", user.get('id') if user else None)
        flash("An error occurred while logging out.", "danger")
        return redirect(url_for('main.index'))
