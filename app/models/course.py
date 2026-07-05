import uuid
from datetime import datetime
from app import db


def _uid():
    return uuid.uuid4().hex


class Course(db.Model):
    __tablename__ = "courses"

    id          = db.Column(db.Integer, primary_key=True)
    tutor_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_id  = db.Column(db.Integer, db.ForeignKey("subjects.id"))

    title       = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(512))

    price_azn   = db.Column(db.Numeric(7, 2), nullable=False, default=0)   # AZN
    is_published= db.Column(db.Boolean, default=False)

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tutor    = db.relationship("User", back_populates="courses", foreign_keys=[tutor_id])
    subject  = db.relationship("Subject")
    sections = db.relationship(
        "CourseSection", back_populates="course",
        cascade="all, delete-orphan", order_by="CourseSection.position"
    )
    purchases = db.relationship("Purchase", back_populates="course", cascade="all, delete-orphan")

    @property
    def lesson_count(self):
        return sum(len(s.lessons) for s in self.sections)

    @property
    def total_duration_label(self):
        # Placeholder — could sum lesson durations if we track them
        return f"{self.lesson_count} dərs"

    def is_purchased_by(self, user_id):
        return any(p.student_id == user_id and p.status == "completed" for p in self.purchases)

    @property
    def is_free(self):
        return not self.price_azn or float(self.price_azn) == 0

    def price_display(self):
        if not self.price_azn or float(self.price_azn) == 0:
            return "Pulsuz"
        return f"{float(self.price_azn):.0f} AZN"


class CourseSection(db.Model):
    """A named chapter within a course, e.g. 'Optika', 'Elektromaqnetizm'."""
    __tablename__ = "course_sections"

    id        = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title     = db.Column(db.String(160), nullable=False)
    position  = db.Column(db.Integer, default=0)   # for ordering

    course  = db.relationship("Course", back_populates="sections")
    lessons = db.relationship(
        "Lesson", back_populates="section",
        cascade="all, delete-orphan", order_by="Lesson.position"
    )


class Lesson(db.Model):
    """A single video lesson within a section, with optional homework."""
    __tablename__ = "lessons"

    id         = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("course_sections.id"), nullable=False)

    title      = db.Column(db.String(160), nullable=False)
    video_url  = db.Column(db.String(512))     # S3/CloudFront URL in production
    position   = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    section  = db.relationship("CourseSection", back_populates="lessons")
    homework = db.relationship(
        "Homework", back_populates="lesson", uselist=False, cascade="all, delete-orphan"
    )


class Homework(db.Model):
    """Optional homework sheet + optional answer key, attached 1:1 to a lesson."""
    __tablename__ = "homeworks"

    id        = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False, unique=True)

    sheet_url  = db.Column(db.String(512))    # homework PDF/doc
    answer_url = db.Column(db.String(512))    # optional answer key

    lesson = db.relationship("Lesson", back_populates="homework")


class Purchase(db.Model):
    """A student's purchase of a course — one row per successful transaction."""
    __tablename__ = "purchases"

    id         = db.Column(db.Integer, primary_key=True)
    course_id  = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    amount_azn = db.Column(db.Numeric(7, 2), nullable=False)
    platform_fee_azn = db.Column(db.Numeric(7, 2))   # 10% cut, recorded for bookkeeping

    stripe_checkout_session_id = db.Column(db.String(255), unique=True)
    stripe_payment_intent_id   = db.Column(db.String(255))

    status     = db.Column(db.String(20), default="pending")  # pending | completed | failed | refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("course_id", "student_id", name="uq_course_student"),)

    course  = db.relationship("Course", back_populates="purchases")
    student = db.relationship("User", back_populates="purchases", foreign_keys=[student_id])