"""meta_analysis

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-18 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'meta_analyses',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('review_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('effect_metric', sa.String(length=8), nullable=False),
        sa.Column('model', sa.String(length=8), nullable=False),
        sa.Column('subgroup_variable', sa.String(length=64), nullable=True),
        sa.Column('pooled_estimate', sa.Float(), nullable=True),
        sa.Column('pooled_se', sa.Float(), nullable=True),
        sa.Column('ci_low', sa.Float(), nullable=True),
        sa.Column('ci_high', sa.Float(), nullable=True),
        sa.Column('z_value', sa.Float(), nullable=True),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('q_value', sa.Float(), nullable=True),
        sa.Column('q_df', sa.Integer(), nullable=True),
        sa.Column('q_p', sa.Float(), nullable=True),
        sa.Column('i2', sa.Float(), nullable=True),
        sa.Column('tau2', sa.Float(), nullable=True),
        sa.Column('subgroup_summary', sa.JSON(), nullable=True),
        sa.Column('ai_interpretation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('meta_analyses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_meta_analyses_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_meta_analyses_review', ['review_id'], unique=False)

    op.create_table(
        'meta_inputs',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('meta_id', sa.String(length=32), nullable=False),
        sa.Column('article_id', sa.String(length=32), nullable=False),
        sa.Column('study_label', sa.String(length=120), nullable=True),
        sa.Column('subgroup', sa.String(length=120), nullable=True),
        sa.Column('mean_a', sa.Float(), nullable=True),
        sa.Column('sd_a', sa.Float(), nullable=True),
        sa.Column('n_a', sa.Integer(), nullable=True),
        sa.Column('mean_b', sa.Float(), nullable=True),
        sa.Column('sd_b', sa.Float(), nullable=True),
        sa.Column('n_b', sa.Integer(), nullable=True),
        sa.Column('events_a', sa.Integer(), nullable=True),
        sa.Column('n_a_total', sa.Integer(), nullable=True),
        sa.Column('events_b', sa.Integer(), nullable=True),
        sa.Column('n_b_total', sa.Integer(), nullable=True),
        sa.Column('log_hr', sa.Float(), nullable=True),
        sa.Column('se_log_hr', sa.Float(), nullable=True),
        sa.Column('hr', sa.Float(), nullable=True),
        sa.Column('hr_ci_low', sa.Float(), nullable=True),
        sa.Column('hr_ci_high', sa.Float(), nullable=True),
        sa.Column('r', sa.Float(), nullable=True),
        sa.Column('n_r', sa.Integer(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['meta_id'], ['meta_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('meta_inputs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_meta_inputs_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_meta_inputs_meta', ['meta_id'], unique=False)
        batch_op.create_index('uq_meta_inputs_meta_article', ['meta_id', 'article_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('meta_inputs', schema=None) as batch_op:
        batch_op.drop_index('uq_meta_inputs_meta_article')
        batch_op.drop_index('ix_meta_inputs_meta')
        batch_op.drop_index(batch_op.f('ix_meta_inputs_user_id'))
    op.drop_table('meta_inputs')

    with op.batch_alter_table('meta_analyses', schema=None) as batch_op:
        batch_op.drop_index('ix_meta_analyses_review')
        batch_op.drop_index(batch_op.f('ix_meta_analyses_user_id'))
    op.drop_table('meta_analyses')
