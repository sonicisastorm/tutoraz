from datetime import datetime
from app import db

tutor_subjects = db.Table(
    "tutor_subjects",
    db.Column("tutor_profile_id", db.Integer, db.ForeignKey("tutor_profiles.id"), primary_key=True),
    db.Column("subject_id",       db.Integer, db.ForeignKey("subjects.id"),        primary_key=True),
)


class Subject(db.Model):
    __tablename__ = "subjects"
    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(80), unique=True, nullable=False)
    name_az = db.Column(db.String(80))


class TutorProfile(db.Model):
    __tablename__ = "tutor_profiles"

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    bio              = db.Column(db.Text)
    headline         = db.Column(db.String(160))
    years_experience = db.Column(db.Integer, default=0)
    education        = db.Column(db.String(255))

    city           = db.Column(db.String(80), default="Bakı")
    district       = db.Column(db.String(80))
    phone          = db.Column(db.String(30))      # ← NEW
    teaches_online   = db.Column(db.Boolean, default=True)
    teaches_inperson = db.Column(db.Boolean, default=True)

    hourly_rate_min = db.Column(db.Numeric(6, 2))
    hourly_rate_max = db.Column(db.Numeric(6, 2))

    avatar_url   = db.Column(db.String(512))       # stores /static/avatars/<filename>
    is_published = db.Column(db.Boolean, default=False)
    is_featured  = db.Column(db.Boolean, default=False)

    # Stripe Connect (Express) — only set once tutor opts into course creation
    stripe_account_id           = db.Column(db.String(255))   # acct_...
    stripe_onboarding_complete   = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user     = db.relationship("User", back_populates="tutor_profile")
    subjects = db.relationship("Subject", secondary=tutor_subjects, lazy="subquery")

    def display_rate(self):
        if self.hourly_rate_min and self.hourly_rate_max:
            return f"{int(self.hourly_rate_min)}–{int(self.hourly_rate_max)} AZN/saat"
        if self.hourly_rate_min:
            return f"{int(self.hourly_rate_min)}+ AZN/saat"
        return "Razılaşma ilə"

    def avatar(self):
        return self.avatar_url or None

    def can_sell_courses(self):
        return bool(self.stripe_onboarding_complete)
