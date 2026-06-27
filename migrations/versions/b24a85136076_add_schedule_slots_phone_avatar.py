"""add schedule slots, phone, avatar

Revision ID: b24a85136076
Revises: d43ac59f042f
Create Date: 2026-06-27 06:21:17.381549

"""
from alembic import op
import sqlalchemy as sa

revision = 'b24a85136076'
down_revision = 'd43ac59f042f'
branch_labels = None
depends_on = None


def upgrade():
    # Add phone column to tutor_profiles
    with op.batch_alter_table('tutor_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=30), nullable=True))

    # Create group_schedules table (new)
    op.create_table(
        'group_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.String(length=5), nullable=False),
        sa.Column('end_time', sa.String(length=5), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('group_schedules')
    with op.batch_alter_table('tutor_profiles', schema=None) as batch_op:
        batch_op.drop_column('phone')
