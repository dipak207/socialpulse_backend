"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-06-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'analyzed_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('platform_user_id', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('followers', sa.BigInteger(), nullable=False),
        sa.Column('following', sa.BigInteger(), nullable=True),
        sa.Column('posts_count', sa.Integer(), nullable=False),
        sa.Column('avg_engagement_rate', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('posting_frequency', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('last_analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_analyzed_profiles_platform_username', 'analyzed_profiles', ['platform', 'username'], unique=False)

    op.create_table(
        'analyzed_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('platform_post_id', sa.String(), nullable=True),
        sa.Column('post_type', sa.String(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('author_followers', sa.BigInteger(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('views', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('likes', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('comments', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('shares', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('engagement_rate', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('virality_score', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('trend_score', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('hashtags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    op.create_table(
        'analytics_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analyzed_profiles.id'), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('followers', sa.BigInteger(), nullable=False),
        sa.Column('views', sa.BigInteger(), nullable=False),
        sa.Column('likes', sa.BigInteger(), nullable=False),
        sa.Column('comments', sa.BigInteger(), nullable=False),
        sa.Column('shares', sa.BigInteger(), nullable=False),
        sa.Column('engagement_rate', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('posts_published', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )
    op.create_unique_constraint('uq_snapshots_profile_date', 'analytics_snapshots', ['profile_id', 'snapshot_date'])

    op.create_table(
        'hashtag_trends',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hashtag', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('avg_engagement_rate', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )
    op.create_unique_constraint('uq_hashtag_platform', 'hashtag_trends', ['hashtag', 'platform'])

    op.create_table(
        'cached_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cache_key', sa.String(), nullable=False, unique=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )

    op.create_table(
        'generated_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False),
        sa.Column('subject_urls', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('timeframe', sa.String(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('generated_reports')
    op.drop_table('cached_metrics')
    op.drop_table('hashtag_trends')
    op.drop_table('analytics_snapshots')
    op.drop_table('analyzed_posts')
    op.drop_table('analyzed_profiles')
