import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.group import Group, GroupMember
from app.models.tutor import Subject

groups_bp = Blueprint("groups", __name__)


def _gen_invite_code() -> str:
    while True:
        code = secrets.token_urlsafe(8)[:8].upper()
        if not Group.query.filter_by(invite_code=code).first():
            return code


@groups_bp.route("/")
@login_required
def index():
    if current_user.is_tutor():
        groups = (
            Group.query
            .filter_by(tutor_id=current_user.id)
            .order_by(Group.created_at.desc())
            .all()
        )
        return render_template("groups/tutor_groups.html", groups=groups)
    else:
        memberships = [m for m in current_user.group_memberships if m.status == "active"]
        return render_template("groups/student_groups.html", memberships=memberships)


@groups_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_tutor():
        flash("Yalnız müəllimlər qrup yarada bilər.", "error")
        return redirect(url_for("groups.index"))

    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        subject_id = request.form.get("subject_id", type=int)
        max_students = request.form.get("max_students", 10, type=int)

        if not name:
            flash("Qrup adı tələb olunur.", "error")
            return render_template("groups/create.html", subjects=subjects)

        group = Group(
            tutor_id=current_user.id,
            name=name,
            description=description,
            subject_id=subject_id or None,
            max_students=max(1, min(max_students, 50)),
            invite_code=_gen_invite_code(),
        )
        db.session.add(group)
        db.session.commit()
        flash(f'"{group.name}" qrupu yaradıldı.', "success")
        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template("groups/create.html", subjects=subjects)


@groups_bp.route("/<int:group_id>")
@login_required
def detail(group_id):
    group = Group.query.get_or_404(group_id)
    # Only tutor or members can view
    is_member = any(m.student_id == current_user.id for m in group.members if m.status == "active")
    if group.tutor_id != current_user.id and not is_member:
        flash("Bu qrupa girişiniz yoxdur.", "error")
        return redirect(url_for("groups.index"))
    return render_template("groups/detail.html", group=group, is_member=is_member)


@groups_bp.route("/join", methods=["GET", "POST"])
@login_required
def join():
    if current_user.is_tutor():
        flash("Müəllimlər qrupa qoşula bilməz.", "error")
        return redirect(url_for("groups.index"))

    code = request.args.get("code", "").strip().upper() or request.form.get("code", "").strip().upper()

    if request.method == "POST":
        group = Group.query.filter_by(invite_code=code, is_active=True).first()
        if not group:
            flash("Dəvət kodu tapılmadı.", "error")
            return render_template("groups/join.html", code=code)
        if group.is_full():
            flash("Bu qrup doludur.", "error")
            return render_template("groups/join.html", code=code)

        existing = GroupMember.query.filter_by(
            group_id=group.id, student_id=current_user.id
        ).first()
        if existing:
            if existing.status == "active":
                flash("Siz artıq bu qrupdansınız.", "info")
            else:
                existing.status = "active"
                db.session.commit()
                flash(f'"{group.name}" qrupuna yenidən qoşuldunuz.', "success")
        else:
            member = GroupMember(group_id=group.id, student_id=current_user.id)
            db.session.add(member)
            db.session.commit()
            flash(f'"{group.name}" qrupuna qoşuldunuz!', "success")

        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template("groups/join.html", code=code)


@groups_bp.route("/<int:group_id>/remove/<int:student_id>", methods=["POST"])
@login_required
def remove_student(group_id, student_id):
    group = Group.query.get_or_404(group_id)
    if group.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("groups.index"))

    member = GroupMember.query.filter_by(group_id=group_id, student_id=student_id).first_or_404()
    member.status = "removed"
    db.session.commit()
    flash("Şagird qrupdan çıxarıldı.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))
