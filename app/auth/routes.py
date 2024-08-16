from flask import redirect, url_for, flash, make_response, request, render_template
from app import db, oauth
from ..models import User
from authlib.integrations.base_client.errors import AuthlibBaseError
import os
from app.functions import login_required
from . import auth


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        if request.cookies.get('id_token'):
            flash("Already logged in", "info")
            return redirect(url_for("main.home"))

        google = oauth.create_client('google')
        redirect_uri = url_for('auth.callback', _external=True)
        return google.authorize_redirect(redirect_uri)

@auth.route('/callback')
def callback():
    try:
        google = oauth.create_client('google')
        full_token = google.authorize_access_token()

        if not full_token:
            flash("Failed to retrieve token", "danger")
            return redirect(url_for('auth.login'))

        id_token = full_token['id_token']
        profile = full_token['userinfo']

        if profile['hd'] != os.getenv('LAGH_UNI_DOMAIN'):
            flash("Only Lagh University emails are allowed", "danger")
            return make_response(redirect(url_for('main.index')))

        # Check if User exists in db
        user = User.query.filter_by(google_id=profile['sub']).first()

        if not user:
            # Create new User
            user = User(
                google_id=profile['sub'],
                email=profile['email'],
                name=profile['name'],
                picture=profile['picture']
            )
            db.session.add(user)
            db.session.commit()

        # Process User info and create a response
        response = make_response(redirect(url_for("main.home")))
        response.set_cookie("id_token", id_token, httponly=True, secure=True, samesite="Lax")
        flash("Logged in successfully", "success")
        return response

    except AuthlibBaseError as e:
        flash("Authentication failed. Please try again.", "danger")
        return redirect(url_for('auth.login'))
    except Exception as e:
        flash("An error occurred. Please try again later.", "danger")
        return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout(user):
    response = make_response(redirect(url_for("main.index")))
    response.set_cookie("id_token", "", expires=0)
    flash("Logged out successfully", "success")
    return response