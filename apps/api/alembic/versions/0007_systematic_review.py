"""systematic_review

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-18 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('articles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('abstract', sa.Text(), nullable=True))

    op.create_table('reviews',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=False),
    sa.Column('pico_population', sa.Text(), nullable=True),
    sa.Column('pico_intervention', sa.Text(), nullable=True),
    sa.Column('pico_comparator', sa.Text(), nullable=True),
    sa.Column('pico_outcome', sa.Text(), nullable=True),
    sa.Column('eligibility_inclusion', sa.Text(), nullable=True),
    sa.Column('eligibility_exclusion', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reviews_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_reviews_project_user', ['project_id', 'user_id'], unique=True)

    op.create_table('search_records',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('review_id', sa.String(length=32), nullable=False),
    sa.Column('database_name', sa.String(length=64), nullable=False),
    sa.Column('query_string', sa.Text(), nullable=False),
    sa.Column('date_searched', sa.DateTime(), nullable=False),
    sa.Column('n_results', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('search_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_search_records_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_search_records_review', ['review_id'], unique=False)

    op.create_table('screening_records',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('review_id', sa.String(length=32), nullable=False),
    sa.Column('article_id', sa.String(length=32), nullable=False),
    sa.Column('stage', sa.String(length=16), nullable=False),
    sa.Column('decision', sa.String(length=16), nullable=False),
    sa.Column('exclusion_category', sa.String(length=32), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('reviewer_id', sa.String(length=64), nullable=True),
    sa.Column('ai_suggestion', sa.JSON(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('screening_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_screening_records_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_screening_review_article_stage', ['review_id', 'article_id', 'stage'], unique=True)
        batch_op.create_index('ix_screening_review_stage', ['review_id', 'stage'], unique=False)

    op.create_table('rob_assessments',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('review_id', sa.String(length=32), nullable=False),
    sa.Column('article_id', sa.String(length=32), nullable=False),
    sa.Column('tool', sa.String(length=16), nullable=False),
    sa.Column('domain_answers', sa.JSON(), nullable=False),
    sa.Column('overall_auto', sa.String(length=16), nullable=False),
    sa.Column('overall_override', sa.String(length=16), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rob_assessments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rob_assessments_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_rob_review_article_tool', ['review_id', 'article_id', 'tool'], unique=True)

    op.create_table('extraction_records',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('review_id', sa.String(length=32), nullable=False),
    sa.Column('article_id', sa.String(length=32), nullable=False),
    sa.Column('fields', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('extraction_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_extraction_records_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_extraction_review_article', ['review_id', 'article_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('extraction_records', schema=None) as batch_op:
        batch_op.drop_index('uq_extraction_review_article')
        batch_op.drop_index(batch_op.f('ix_extraction_records_user_id'))
    op.drop_table('extraction_records')

    with op.batch_alter_table('rob_assessments', schema=None) as batch_op:
        batch_op.drop_index('uq_rob_review_article_tool')
        batch_op.drop_index(batch_op.f('ix_rob_assessments_user_id'))
    op.drop_table('rob_assessments')

    with op.batch_alter_table('screening_records', schema=None) as batch_op:
        batch_op.drop_index('ix_screening_review_stage')
        batch_op.drop_index('uq_screening_review_article_stage')
        batch_op.drop_index(batch_op.f('ix_screening_records_user_id'))
    op.drop_table('screening_records')

    with op.batch_alter_table('search_records', schema=None) as batch_op:
        batch_op.drop_index('ix_search_records_review')
        batch_op.drop_index(batch_op.f('ix_search_records_user_id'))
    op.drop_table('search_records')

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index('uq_reviews_project_user')
        batch_op.drop_index(batch_op.f('ix_reviews_user_id'))
    op.drop_table('reviews')

    with op.batch_alter_table('articles', schema=None) as batch_op:
        batch_op.drop_column('abstract')
