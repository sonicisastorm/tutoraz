from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from app.models.tutor import TutorProfile, Subject
from app.models.group import Group
from app import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    featured = (TutorProfile.query
                .filter_by(is_published=True)
                .join(TutorProfile.user)
                .order_by(TutorProfile.created_at.desc())
                .limit(6).all())
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template("main/index.html", featured=featured, subjects=subjects)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_tutor():
        profile = current_user.tutor_profile
        groups  = (Group.query
                   .filter_by(tutor_id=current_user.id, is_active=True)
                   .order_by(Group.created_at.desc()).all())
        return render_template("main/dashboard_tutor.html", profile=profile, groups=groups)
    else:
        memberships  = current_user.group_memberships
        active_groups= [m.group for m in memberships if m.status == "active" and m.group.is_active]
        return render_template("main/dashboard_student.html", groups=active_groups)
