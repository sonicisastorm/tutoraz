from datetime import datetime
from app import db


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    max_students = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    invite_code = db.Column(db.String(12), unique=True)  # generated for sharing

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tutor = db.relationship("User", back_populates="created_groups", foreign_keys=[tutor_id])
    subject = db.relationship("Subject")
    members = db.relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")

    @property
    def member_count(self) -> int:
        return len([m for m in self.members if m.status == "active"])

    def is_full(self) -> bool:
        return self.member_count >= self.max_students

    def __repr__(self):
        return f"<Group '{self.name}'>"


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="active")  # active | removed | left
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("group_id", "student_id"),)

    # Relationships
    group = db.relationship("Group", back_populates="members")
    student = db.relationship("User", back_populates="group_memberships")
