from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.course import Course, CourseSection, Lesson, Homework
from app.models.tutor import Subject
from app.storage import save_file, delete_file, ALLOWED_VIDEO_EXT, ALLOWED_IMAGE_EXT, ALLOWED_DOC_EXT

courses_bp = Blueprint("courses", __name__)


# ── Discovery (public) ────────────────────────────────────────────────────────
@courses_bp.route("/")
def browse():
    q = request.args.get("q", "").strip()
    subject_id = request.args.get("subject", type=int)

    query = Course.query.filter_by(is_published=True)
    if q:
        query = query.filter(Course.title.ilike(f"%{q}%"))
    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    courses = query.order_by(Course.created_at.desc()).all()
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template("courses/browse.html", courses=courses, subjects=subjects,
                            q=q, subject_id=subject_id, total=len(courses))


@courses_bp.route("/<int:course_id>")
def detail(course_id):
    course = Course.query.get_or_404(course_id)
    if not course.is_published and (
        not current_user.is_authenticated or current_user.id != course.tutor_id
    ):
        flash("Bu kurs mövcud deyil.", "error")
        return redirect(url_for("courses.browse"))

    purchased = (
        current_user.is_authenticated and course.is_purchased_by(current_user.id)
    )
    is_owner = current_user.is_authenticated and current_user.id == course.tutor_id
    return render_template("courses/detail.html", course=course, purchased=purchased, is_owner=is_owner)


# ── Tutor: manage own courses ──────────────────────────────────────────────────
@courses_bp.route("/mine")
@login_required
def my_courses():
    if not current_user.is_tutor():
        flash("Yalnız müəllimlər üçündür.", "error")
        return redirect(url_for("main.dashboard"))
    courses = Course.query.filter_by(tutor_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template("courses/my_courses.html", courses=courses)


@courses_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_tutor():
        flash("Yalnız müəllimlər kurs yarada bilər.", "error")
        return redirect(url_for("main.dashboard"))

    profile = current_user.tutor_profile
    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Kurs adı tələb olunur.", "error")
            return render_template("courses/create.html", subjects=subjects)

        price = request.form.get("price_azn", 0, type=float) or 0
        if price > 0 and not profile.can_sell_courses():
            flash("Ödənişli kurs yaratmaq üçün əvvəlcə ödəniş hesabınızı qoşun.", "error")
            return redirect(url_for("payments.connect_onboarding"))

        course = Course(
            tutor_id=current_user.id,
            title=title,
            description=request.form.get("description", "").strip(),
            subject_id=request.form.get("subject_id", type=int) or None,
            price_azn=price,
        )
        thumb = save_file(request.files.get("thumbnail"), "thumbnails", ALLOWED_IMAGE_EXT)
        if thumb:
            course.thumbnail_url = thumb

        db.session.add(course)
        db.session.commit()
        flash("Kurs yaradıldı. İndi bölmələr əlavə edin.", "success")
        return redirect(url_for("courses.edit", course_id=course.id))

    return render_template("courses/create.html", subjects=subjects)


@courses_bp.route("/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
def edit(course_id):
    course = Course.query.get_or_404(course_id)
    if course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        course.title       = request.form.get("title", "").strip() or course.title
        course.description = request.form.get("description", "").strip()
        course.subject_id  = request.form.get("subject_id", type=int) or None

        new_price = request.form.get("price_azn", 0, type=float) or 0
        profile = current_user.tutor_profile
        if new_price > 0 and not profile.can_sell_courses():
            flash("Ödənişli kurs üçün əvvəlcə ödəniş hesabınızı qoşun.", "error")
            return redirect(url_for("payments.connect_onboarding"))
        course.price_azn = new_price

        thumb = save_file(request.files.get("thumbnail"), "thumbnails", ALLOWED_IMAGE_EXT)
        if thumb:
            if course.thumbnail_url:
                delete_file(course.thumbnail_url, "thumbnails")
            course.thumbnail_url = thumb

        db.session.commit()
        flash("Kurs yeniləndi.", "success")
        return redirect(url_for("courses.edit", course_id=course.id))

    return render_template("courses/edit.html", course=course, subjects=subjects)


@courses_bp.route("/<int:course_id>/publish", methods=["POST"])
@login_required
def publish(course_id):
    course = Course.query.get_or_404(course_id)
    if course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    if not course.sections or not any(s.lessons for s in course.sections):
        flash("Yayımlamaq üçün ən azı bir bölmə və bir dərs əlavə edin.", "error")
        return redirect(url_for("courses.edit", course_id=course.id))

    course.is_published = True
    db.session.commit()
    flash("Kurs yayımlandı!", "success")
    return redirect(url_for("courses.edit", course_id=course.id))


@courses_bp.route("/<int:course_id>/delete", methods=["POST"])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    if course.thumbnail_url:
        delete_file(course.thumbnail_url, "thumbnails")
    for section in course.sections:
        for lesson in section.lessons:
            if lesson.video_url:
                delete_file(lesson.video_url, "videos")
            if lesson.homework:
                if lesson.homework.sheet_url:
                    delete_file(lesson.homework.sheet_url, "homework")
                if lesson.homework.answer_url:
                    delete_file(lesson.homework.answer_url, "homework")

    db.session.delete(course)
    db.session.commit()
    flash("Kurs silindi.", "success")
    return redirect(url_for("courses.my_courses"))


# ── Sections ───────────────────────────────────────────────────────────────────
@courses_bp.route("/<int:course_id>/sections/add", methods=["POST"])
@login_required
def add_section(course_id):
    course = Course.query.get_or_404(course_id)
    if course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    title = request.form.get("title", "").strip()
    if not title:
        flash("Bölmə adı tələb olunur.", "error")
        return redirect(url_for("courses.edit", course_id=course.id))

    position = len(course.sections)
    db.session.add(CourseSection(course_id=course.id, title=title, position=position))
    db.session.commit()
    flash("Bölmə əlavə edildi.", "success")
    return redirect(url_for("courses.edit", course_id=course.id))


@courses_bp.route("/sections/<int:section_id>/rename", methods=["POST"])
@login_required
def rename_section(section_id):
    section = CourseSection.query.get_or_404(section_id)
    if section.course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    title = request.form.get("title", "").strip()
    if title:
        section.title = title
        db.session.commit()
    return redirect(url_for("courses.edit", course_id=section.course_id))


@courses_bp.route("/sections/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    section = CourseSection.query.get_or_404(section_id)
    course_id = section.course_id
    if section.course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    for lesson in section.lessons:
        if lesson.video_url:
            delete_file(lesson.video_url, "videos")
        if lesson.homework:
            if lesson.homework.sheet_url:
                delete_file(lesson.homework.sheet_url, "homework")
            if lesson.homework.answer_url:
                delete_file(lesson.homework.answer_url, "homework")

    db.session.delete(section)
    db.session.commit()
    flash("Bölmə silindi.", "success")
    return redirect(url_for("courses.edit", course_id=course_id))


# ── Lessons ────────────────────────────────────────────────────────────────────
@courses_bp.route("/sections/<int:section_id>/lessons/add", methods=["POST"])
@login_required
def add_lesson(section_id):
    section = CourseSection.query.get_or_404(section_id)
    if section.course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    title = request.form.get("title", "").strip()
    if not title:
        flash("Dərs adı tələb olunur.", "error")
        return redirect(url_for("courses.edit", course_id=section.course_id))

    video_url = save_file(request.files.get("video"), "videos", ALLOWED_VIDEO_EXT)
    position = len(section.lessons)

    lesson = Lesson(section_id=section.id, title=title, video_url=video_url, position=position)
    db.session.add(lesson)
    db.session.flush()

    sheet_url  = save_file(request.files.get("homework_sheet"), "homework", ALLOWED_DOC_EXT)
    answer_url = save_file(request.files.get("homework_answer"), "homework", ALLOWED_DOC_EXT)
    if sheet_url or answer_url:
        db.session.add(Homework(lesson_id=lesson.id, sheet_url=sheet_url, answer_url=answer_url))

    db.session.commit()
    flash("Dərs əlavə edildi.", "success")
    return redirect(url_for("courses.edit", course_id=section.course_id))


@courses_bp.route("/lessons/<int:lesson_id>/delete", methods=["POST"])
@login_required
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.section.course_id
    if lesson.section.course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    if lesson.video_url:
        delete_file(lesson.video_url, "videos")
    if lesson.homework:
        if lesson.homework.sheet_url:
            delete_file(lesson.homework.sheet_url, "homework")
        if lesson.homework.answer_url:
            delete_file(lesson.homework.answer_url, "homework")

    db.session.delete(lesson)
    db.session.commit()
    flash("Dərs silindi.", "success")
    return redirect(url_for("courses.edit", course_id=course_id))


@courses_bp.route("/lessons/<int:lesson_id>/rename", methods=["POST"])
@login_required
def rename_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.section.course_id
    if lesson.section.course.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("courses.my_courses"))

    title = request.form.get("title", "").strip()
    if title:
        lesson.title = title
        db.session.commit()
    return redirect(url_for("courses.edit", course_id=course_id))


# ── Student: view purchased lesson ────────────────────────────────────────────
@courses_bp.route("/lessons/<int:lesson_id>/watch")
@login_required
def watch_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.section.course

    is_owner = current_user.id == course.tutor_id
    purchased = course.is_purchased_by(current_user.id)

    if not is_owner and not purchased:
        flash("Bu dərsi izləmək üçün kursu satın alın.", "error")
        return redirect(url_for("courses.detail", course_id=course.id))

    return render_template("courses/watch.html", lesson=lesson, course=course)
