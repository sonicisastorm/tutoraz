import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.tutor import TutorProfile, Subject

tutor_bp = Blueprint("tutor", __name__)

ALLOWED_SUBJECTS = [
    "Riyaziyyat", "Fizika", "Kimya", "Biologiya", "Coğrafiya",
    "Tarix", "İngilis dili", "Rus dili", "Azərbaycan dili", "Ədəbiyyat",
    "İnformatika", "DİM hazırlığı",
]


def _seed_subjects():
    """Ensure subjects exist (idempotent)."""
    for name in ALLOWED_SUBJECTS:
        if not Subject.query.filter_by(name=name).first():
            db.session.add(Subject(name=name))
    db.session.commit()


@tutor_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if not current_user.is_tutor():
        flash("Bu səhifə yalnız müəllimlər üçündür.", "error")
        return redirect(url_for("main.dashboard"))

    _seed_subjects()
    profile = current_user.tutor_profile
    all_subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        profile.headline = request.form.get("headline", "").strip()[:160]
        profile.bio = request.form.get("bio", "").strip()
        profile.education = request.form.get("education", "").strip()[:255]
        profile.city = request.form.get("city", "Baku").strip()
        profile.district = request.form.get("district", "").strip()
        profile.teaches_online = bool(request.form.get("teaches_online"))
        profile.teaches_inperson = bool(request.form.get("teaches_inperson"))
        profile.years_experience = int(request.form.get("years_experience") or 0)

        try:
            rate_min = request.form.get("hourly_rate_min")
            rate_max = request.form.get("hourly_rate_max")
            profile.hourly_rate_min = float(rate_min) if rate_min else None
            profile.hourly_rate_max = float(rate_max) if rate_max else None
        except ValueError:
            pass

        # Subjects
        selected_ids = request.form.getlist("subjects")
        selected_subjects = Subject.query.filter(Subject.id.in_(selected_ids)).all()
        profile.subjects = selected_subjects

        # Publish toggle
        if request.form.get("action") == "publish":
            if not profile.headline:
                flash("Profili yayımlamaq üçün başlıq əlavə edin.", "error")
            else:
                profile.is_published = True
                flash("Profiliniz yayımlandı!", "success")
        else:
            flash("Dəyişikliklər yadda saxlanıldı.", "success")

        db.session.commit()
        return redirect(url_for("tutor.edit_profile"))

    return render_template(
        "tutor/edit_profile.html",
        profile=profile,
        all_subjects=all_subjects,
    )


@tutor_bp.route("/<int:tutor_id>")
def public_profile(tutor_id):
    profile = TutorProfile.query.filter_by(id=tutor_id, is_published=True).first_or_404()
    return render_template("tutor/public_profile.html", profile=profile)
