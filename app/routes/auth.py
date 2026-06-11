import re
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app.extensions import db
from app.models import AdminUser, is_valid_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def is_valid_username(username: str) -> bool:
    if not username:
        return False
    pattern = r"^[A-Za-z0-9_.]{4,30}$"
    return re.match(pattern, username) is not None


def is_strong_password(password: str) -> bool:
    if not password or len(password) < 6:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_letter and has_digit


@auth_bp.route("/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not full_name or not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.admin_register"))

        if len(full_name) < 3:
            flash("Full name must be at least 3 characters long.", "danger")
            return redirect(url_for("auth.admin_register"))

        if not is_valid_username(username):
            flash("Username must be 4-30 characters and contain only letters, numbers, underscore, or dot.", "danger")
            return redirect(url_for("auth.admin_register"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("auth.admin_register"))

        if not is_strong_password(password):
            flash("Password must be at least 6 characters long and include both letters and numbers.", "danger")
            return redirect(url_for("auth.admin_register"))

        existing = AdminUser.query.filter(
            (AdminUser.username == username) | (AdminUser.email == email)
        ).first()

        if existing:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("auth.admin_register"))

        try:
            admin = AdminUser(
                full_name=full_name,
                username=username,
                email=email
            )
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()

            flash("Admin registered successfully.", "success")
            return redirect(url_for("auth.admin_login"))

        except Exception:
            db.session.rollback()
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("auth.admin_register"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("auth.admin_login"))

        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for("auth.admin_login"))

        admin = AdminUser.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin)
            flash("Login successful.", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.admin_login"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def admin_logout():
    logout_user()
    flash("Logout successful.", "success")
    return redirect(url_for("public.home"))