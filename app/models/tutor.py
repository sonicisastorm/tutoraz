from datetime import datetime
from app import db

# Many-to-many: TutorProfile ↔ Subject
tutor_subjects = db.Table(
    "tutor_subjects",
    db.Column("tutor_profile_id", db.Integer, db.ForeignKey("tutor_profiles.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subjects.id"), primary_key=True),
)


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    name_az = db.Column(db.String(80))  # Azerbaijani name

    def __repr__(self):
        return f"<Subject {self.name}>"


class TutorProfile(db.Model):
    __tablename__ = "tutor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Bio
    bio = db.Column(db.Text)
    headline = db.Column(db.String(160))          # e.g. "Chemistry tutor · 8 years exp"
    years_experience = db.Column(db.Integer, default=0)
    education = db.Column(db.String(255))         # e.g. "BSc Chemistry, BDU"

    # Location / contact
    city = db.Column(db.String(80), default="Baku")
    district = db.Column(db.String(80))           # e.g. "Yasamal"
    teaches_online = db.Column(db.Boolean, default=True)
    teaches_inperson = db.Column(db.Boolean, default=True)

    # Pricing (AZN / hour)
    hourly_rate_min = db.Column(db.Numeric(6, 2))
    hourly_rate_max = db.Column(db.Numeric(6, 2))

    # Photo
    avatar_url = db.Column(db.String(512))

    # Visibility
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)   # future premium flag

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="tutor_profile")
    subjects = db.relationship("Subject", secondary=tutor_subjects, lazy="subquery")

    def display_rate(self) -> str:
        if self.hourly_rate_min and self.hourly_rate_max:
            return f"{int(self.hourly_rate_min)}–{int(self.hourly_rate_max)} AZN/saat"
        if self.hourly_rate_min:
            return f"{int(self.hourly_rate_min)}+ AZN/saat"
        return "Qiymət razılaşma ilə"

    def subject_names(self) -> list[str]:
        return [s.name for s in self.subjects]

    def __repr__(self):
        return f"<TutorProfile user_id={self.user_id}>"
