from datetime import datetime
from app import db

DAYS = [
    (0, "Bazar ertəsi"),
    (1, "Çərşənbə axşamı"),
    (2, "Çərşənbə"),
    (3, "Cümə axşamı"),
    (4, "Cümə"),
    (5, "Şənbə"),
    (6, "Bazar"),
]
DAY_NAMES = {d[0]: d[1] for d in DAYS}
DAY_SHORT  = {0:"B.e", 1:"Ç.a", 2:"Çər", 3:"C.a", 4:"Cüm", 5:"Şnb", 6:"Bzr"}


class GroupSchedule(db.Model):
    """One recurring weekly slot for a group — e.g. Mon 10:00–11:30."""
    __tablename__ = "group_schedules"

    id         = db.Column(db.Integer, primary_key=True)
    group_id   = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    day_of_week= db.Column(db.Integer, nullable=False)   # 0=Mon … 6=Sun
    start_time = db.Column(db.String(5), nullable=False) # "HH:MM"
    end_time   = db.Column(db.String(5), nullable=False) # "HH:MM"

    group = db.relationship("Group", back_populates="schedules")

    @property
    def day_name(self):
        return DAY_NAMES.get(self.day_of_week, "")

    @property
    def day_short(self):
        return DAY_SHORT.get(self.day_of_week, "")

    def __repr__(self):
        return f"<Slot day={self.day_of_week} {self.start_time}-{self.end_time}>"


class Group(db.Model):
    __tablename__ = "groups"

    id          = db.Column(db.Integer, primary_key=True)
    tutor_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    subject_id  = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    max_students= db.Column(db.Integer, default=10)
    is_active   = db.Column(db.Boolean, default=True)
    invite_code = db.Column(db.String(12), unique=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    tutor    = db.relationship("User", back_populates="created_groups", foreign_keys=[tutor_id])
    subject  = db.relationship("Subject")
    members  = db.relationship("GroupMember",  back_populates="group", cascade="all, delete-orphan")
    schedules= db.relationship("GroupSchedule", back_populates="group", cascade="all, delete-orphan",
                               order_by="GroupSchedule.day_of_week, GroupSchedule.start_time")

    @property
    def member_count(self):
        return len([m for m in self.members if m.status == "active"])

    def is_full(self):
        return self.member_count >= self.max_students

    def schedule_summary(self):
        if not self.schedules:
            return "Cədvəl yoxdur"
        parts = []
        for s in self.schedules:
            parts.append(f"{s.day_short} {s.start_time}–{s.end_time}")
        return " · ".join(parts)


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id         = db.Column(db.Integer, primary_key=True)
    group_id   = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status     = db.Column(db.String(20), default="active")
    joined_at  = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("group_id", "student_id"),)

    group   = db.relationship("Group", back_populates="members")
    student = db.relationship("User",  back_populates="group_memberships")
