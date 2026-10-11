"""decision tracking (V4 phase 4)

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('decision_tracking',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rec_key', sa.String(length=160), nullable=False),
    sa.Column('feedback_id', sa.Integer(), nullable=True),
    sa.Column('action_item_id', sa.Integer(), nullable=True),
    sa.Column('plan_name', sa.String(length=40), nullable=True),
    sa.Column('engine', sa.String(length=40), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('product_id', sa.String(length=20), nullable=True),
    sa.Column('location_id', sa.String(length=20), nullable=True),
    sa.Column('department', sa.String(length=40), nullable=False),
    sa.Column('approved_by', sa.String(length=255), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=False),
    sa.Column('data_as_of', sa.String(length=20), nullable=True),
    sa.Column('expected_value_egp', sa.Float(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('baseline', sa.JSON(), nullable=True),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.Column('measure_days', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('measured_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'))
    with op.batch_alter_table('decision_tracking', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_decision_tracking_rec_key'), ['rec_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_decision_tracking_product_id'), ['product_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_decision_tracking_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('decision_tracking', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_decision_tracking_status'))
        batch_op.drop_index(batch_op.f('ix_decision_tracking_product_id'))
        batch_op.drop_index(batch_op.f('ix_decision_tracking_rec_key'))
    op.drop_table('decision_tracking')
