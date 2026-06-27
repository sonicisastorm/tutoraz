from app import create_app, db
from app.models import User, TutorProfile, Subject, Group, GroupMember, GroupSchedule

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, TutorProfile=TutorProfile,
                Subject=Subject, Group=Group, GroupMember=GroupMember,
                GroupSchedule=GroupSchedule)


if __name__ == "__main__":
    app.run(debug=True)
