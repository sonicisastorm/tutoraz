import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.group import Group, GroupMember, GroupSchedule, DAYS
from app.models.tutor import Subject

groups_bp = Blueprint("groups", __name__)


def _gen_invite_code():
    while True:
        code = secrets.token_urlsafe(8)[:8].upper()
        if not Group.query.filter_by(invite_code=code).first():
            return code


def _save_schedules(group, form):
    """Parse schedule rows from POST form and save to DB."""
    # Delete old slots first
    GroupSchedule.query.filter_by(group_id=group.id).delete()
    days_list   = form.getlist("sched_day")
    starts_list = form.getlist("sched_start")
    ends_list   = form.getlist("sched_end")
    for day, start, end in zip(days_list, starts_list, ends_list):
        if day and start and end:
            try:
                day_int = int(day)
                slot = GroupSchedule(
                    group_id=group.id,
                    day_of_week=day_int,
                    start_time=start,
                    end_time=end,
                )
                db.session.add(slot)
            except ValueError:
                pass


@groups_bp.route("/")
@login_required
def index():
    if current_user.is_tutor():
        groups = (Group.query
                  .filter_by(tutor_id=current_user.id)
                  .order_by(Group.created_at.desc()).all())
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
        if not name:
            flash("Qrup adı tələb olunur.", "error")
            return render_template("groups/create.html", subjects=subjects, days=DAYS)

        group = Group(
            tutor_id=current_user.id,
            name=name,
            description=request.form.get("description", "").strip(),
            subject_id=request.form.get("subject_id", type=int) or None,
            max_students=max(1, min(request.form.get("max_students", 10, type=int), 50)),
            invite_code=_gen_invite_code(),
        )
        db.session.add(group)
        db.session.flush()   # get group.id before schedules
        _save_schedules(group, request.form)
        db.session.commit()
        flash(f'"{group.name}" qrupu yaradıldı.', "success")
        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template("groups/create.html", subjects=subjects, days=DAYS)


@groups_bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
@login_required
def edit(group_id):
    group = Group.query.get_or_404(group_id)
    if group.tutor_id != current_user.id:
        flash("İcazəniz yoxdur.", "error")
        return redirect(url_for("groups.index"))

    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        group.name        = request.form.get("name", "").strip() or group.name
        group.description = request.form.get("description", "").strip()
        group.subject_id  = request.form.get("subject_id", type=int) or None
        group.max_students= max(1, min(request.form.get("max_students", 10, type=int), 50))
        _save_schedules(group, request.form)
        db.session.commit()
        flash("Qrup yeniləndi.", "success")
        return redirect(url_for("groups.detail", group_id=group.id))

    return render_template("groups/create.html", subjects=subjects, days=DAYS, group=group)


@groups_bp.route("/<int:group_id>")
@login_required
def detail(group_id):
    group = Group.query.get_or_404(group_id)
    is_member = any(
        m.student_id == current_user.id
        for m in group.members if m.status == "active"
    )
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

    code = (request.args.get("code", "") or request.form.get("code", "")).strip().upper()

    if request.method == "POST":
        group = Group.query.filter_by(invite_code=code, is_active=True).first()
        if not group:
            flash("Dəvət kodu tapılmadı.", "error")
            return render_template("groups/join.html", code=code)
        if group.is_full():
            flash("Bu qrup doludur.", "error")
            return render_template("groups/join.html", code=code)

        existing = GroupMember.query.filter_by(
            group_id=group.id, student_id=current_user.id).first()
        if existing:
            if existing.status == "active":
                flash("Siz artıq bu qrupdansınız.", "info")
            else:
                existing.status = "active"
                db.session.commit()
                flash(f'"{group.name}" qrupuna yenidən qoşuldunuz.', "success")
        else:
            db.session.add(GroupMember(group_id=group.id, student_id=current_user.id))
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
    member = GroupMember.query.filter_by(
        group_id=group_id, student_id=student_id).first_or_404()
    member.status = "removed"
    db.session.commit()
    flash("Şagird qrupdan çıxarıldı.", "success")
    return redirect(url_for("groups.detail", group_id=group_id))


# ── Schedule view ─────────────────────────────────────────────────────────────
@groups_bp.route("/schedule")
@login_required
def schedule():
    """Weekly timetable for current user (tutor or student)."""
    if current_user.is_tutor():
        groups = Group.query.filter_by(tutor_id=current_user.id, is_active=True).all()
    else:
        memberships = [m for m in current_user.group_memberships if m.status == "active"]
        groups = [m.group for m in memberships if m.group.is_active]

    # Build day_map: {0: [slot_dicts], 1: [...], ...}
    from app.models.group import DAYS
    day_map = {d[0]: [] for d in DAYS}
    COLORS = ["#2D5BE3","#18794E","#9E5200","#7C3AED","#CE2C31","#0369A1","#B45309"]

    for i, group in enumerate(groups):
        color = COLORS[i % len(COLORS)]
        for slot in group.schedules:
            day_map[slot.day_of_week].append({
                "group":      group,
                "start":      slot.start_time,
                "end":        slot.end_time,
                "color":      color,
            })

    # Sort each day by start time
    for day in day_map:
        day_map[day].sort(key=lambda x: x["start"])

    return render_template("groups/schedule.html", day_map=day_map, days=DAYS, groups=groups)
