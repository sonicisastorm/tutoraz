from flask import Blueprint, render_template, request
from app.models.tutor import TutorProfile, Subject
from app import db

student_bp = Blueprint("student", __name__)


@student_bp.route("/")
def search():
    q = request.args.get("q", "").strip()
    subject_id = request.args.get("subject", type=int)
    mode = request.args.get("mode", "")   # online | inperson | ''
    city = request.args.get("city", "").strip()

    query = (
        TutorProfile.query
        .filter_by(is_published=True)
        .join(TutorProfile.user)
    )

    if q:
        like = f"%{q}%"
        from app.models.user import User
        query = query.filter(
            db.or_(
                TutorProfile.headline.ilike(like),
                TutorProfile.bio.ilike(like),
                User.full_name.ilike(like),
            )
        )

    if subject_id:
        query = query.filter(
            TutorProfile.subjects.any(Subject.id == subject_id)
        )

    if mode == "online":
        query = query.filter_by(teaches_online=True)
    elif mode == "inperson":
        query = query.filter_by(teaches_inperson=True)

    if city:
        query = query.filter(TutorProfile.city.ilike(f"%{city}%"))

    tutors = query.order_by(TutorProfile.is_featured.desc(), TutorProfile.updated_at.desc()).all()
    subjects = Subject.query.order_by(Subject.name).all()

    return render_template(
        "student/search.html",
        tutors=tutors,
        subjects=subjects,
        q=q,
        subject_id=subject_id,
        mode=mode,
        city=city,
        total=len(tutors),
    )
