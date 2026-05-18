"""statistics

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-18 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('datasets',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=False),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('file_ref', sa.JSON(), nullable=False),
    sa.Column('file_type', sa.String(length=64), nullable=False),
    sa.Column('n_rows', sa.Integer(), nullable=False),
    sa.Column('n_columns', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_datasets_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_datasets_user_project', ['user_id', 'project_id'], unique=False)

    op.create_table('dataset_variables',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('dataset_id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('inferred_type', sa.String(length=32), nullable=False),
    sa.Column('user_type', sa.String(length=32), nullable=True),
    sa.Column('n_missing', sa.Integer(), nullable=False),
    sa.Column('sample_values', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('dataset_variables', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_dataset_variables_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_dataset_variable_dataset_name', ['dataset_id', 'name'], unique=True)

    op.create_table('analyses',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=False),
    sa.Column('dataset_id', sa.String(length=32), nullable=False),
    sa.Column('question_type', sa.String(length=32), nullable=False),
    sa.Column('chosen_test', sa.String(length=64), nullable=False),
    sa.Column('recommendation_rationale', sa.Text(), nullable=False),
    sa.Column('variables', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analyses_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_analyses_user_project', ['user_id', 'project_id'], unique=False)

    op.create_table('analysis_results',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('analysis_id', sa.String(length=32), nullable=False),
    sa.Column('summary', sa.JSON(), nullable=False),
    sa.Column('assumptions', sa.JSON(), nullable=False),
    sa.Column('chart', sa.JSON(), nullable=True),
    sa.Column('ai_interpretation', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('analysis_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analysis_results_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_analysis_results_analysis', ['analysis_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('analysis_results', schema=None) as batch_op:
        batch_op.drop_index('uq_analysis_results_analysis')
        batch_op.drop_index(batch_op.f('ix_analysis_results_user_id'))
    op.drop_table('analysis_results')

    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.drop_index('ix_analyses_user_project')
        batch_op.drop_index(batch_op.f('ix_analyses_user_id'))
    op.drop_table('analyses')

    with op.batch_alter_table('dataset_variables', schema=None) as batch_op:
        batch_op.drop_index('uq_dataset_variable_dataset_name')
        batch_op.drop_index(batch_op.f('ix_dataset_variables_user_id'))
    op.drop_table('dataset_variables')

    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.drop_index('ix_datasets_user_project')
        batch_op.drop_index(batch_op.f('ix_datasets_user_id'))
    op.drop_table('datasets')
