from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'tutor' | 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    tutor_profile = db.relationship(
        "TutorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    created_groups = db.relationship(
        "Group", back_populates="tutor", foreign_keys="Group.tutor_id", cascade="all, delete-orphan"
    )
    group_memberships = db.relationship(
        "GroupMember", back_populates="student", cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_tutor(self) -> bool:
        return self.role == "tutor"

    def is_student(self) -> bool:
        return self.role == "student"

    def __repr__(self):
        return f"<User {self.email}>"
