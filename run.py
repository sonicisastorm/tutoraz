from app import create_app, db
from app.models import (
    User, TutorProfile, Subject, Group, GroupMember, GroupSchedule,
    Course, CourseSection, Lesson, Homework, Purchase,
)

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, TutorProfile=TutorProfile,
                Subject=Subject, Group=Group, GroupMember=GroupMember,
                GroupSchedule=GroupSchedule, Course=Course, CourseSection=CourseSection,
                Lesson=Lesson, Homework=Homework, Purchase=Purchase)


if __name__ == "__main__":
    app.run(debug=True)
