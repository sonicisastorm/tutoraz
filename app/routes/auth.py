from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.tutor import TutorProfile

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        errors = []
        if not full_name or len(full_name) < 2:
            errors.append("Ad ən azı 2 simvol olmalıdır.")
        if not email or "@" not in email:
            errors.append("Düzgün e-poçt daxil edin.")
        if len(password) < 8:
            errors.append("Şifrə ən azı 8 simvol olmalıdır.")
        if role not in ("tutor", "student"):
            errors.append("Rol seçin.")
        if User.query.filter_by(email=email).first():
            errors.append("Bu e-poçt artıq istifadə olunur.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", form_data=request.form)

        user = User(full_name=full_name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)

        if role == "tutor":
            profile = TutorProfile(user=user)
            db.session.add(profile)

        db.session.commit()
        login_user(user)
        flash("Xoş gəlmisiniz!", "success")

        if role == "tutor":
            return redirect(url_for("tutor.edit_profile"))
        return redirect(url_for("student.search"))

    return render_template("auth/register.html", form_data={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("E-poçt və ya şifrə yanlışdır.", "error")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth_bp.route("/account/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        password = request.form.get("password", "")
        if not current_user.check_password(password):
            flash("Şifrə yanlışdır.", "error")
            return render_template("auth/delete_account.html")

        user = User.query.get(current_user.id)
        logout_user()
        db.session.delete(user)  # cascades to tutor_profile, courses, groups, purchases, memberships
        db.session.commit()
        flash("Hesabınız silindi.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/delete_account.html")