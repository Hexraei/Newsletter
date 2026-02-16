"""Initial migration - create all tables.

Revision ID: 001
Revises: 
Create Date: 2026-02-03 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("year_of_study", sa.Integer(), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("college_name", sa.String(255), nullable=True),
        sa.Column("interests", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("content_preferences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("notification_settings", postgresql.JSONB(), 
                  server_default='{"email_digest": true, "breaking_news": true, "weekly_summary": true}',
                  nullable=False),
        sa.Column("streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_reads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_badges", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("weekly_goal", sa.Integer(), server_default="7", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email")
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    
    # Create sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("scrape_config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("schedule_cron", sa.String(50), nullable=True),
        sa.Column("rate_limit", sa.Integer(), server_default="60", nullable=False),
        sa.Column("proxy_tier", sa.String(20), server_default="standard", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_rate", sa.Numeric(5, 2), server_default="100.0", nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("default_categories", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("default_tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Create raw_content table
    op.create_table(
        "raw_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=True),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("original_author", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("processing_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"])
    )
    op.create_index("ix_raw_content_content_hash", "raw_content", ["content_hash"], unique=True)
    op.create_index("ix_raw_content_status", "raw_content", ["status"])
    
    # Create processed_content table
    op.create_table(
        "processed_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_content_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_blocks", postgresql.JSONB(), nullable=True),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("department_tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("difficulty_level", sa.String(20), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("relevance_score", sa.Integer(), nullable=True),
        sa.Column("priority_score", sa.Integer(), nullable=True),
        sa.Column("attractiveness_score", sa.Integer(), nullable=True),
        sa.Column("is_breaking", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("breaking_score", sa.Integer(), nullable=True),
        sa.Column("breaking_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured_image_url", sa.Text(), nullable=True),
        sa.Column("visualizations", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("view_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("read_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("save_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("share_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("weekly_bucket", sa.String(10), nullable=True),
        sa.Column("content_type", sa.String(20), server_default="news", nullable=False),
        sa.Column("opportunity_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opportunity_pay", sa.String(100), nullable=True),
        sa.Column("opportunity_source_platform", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["raw_content_id"], ["raw_content.id"])
    )
    op.create_index("ix_processed_content_status", "processed_content", ["status"])
    op.create_index("ix_processed_content_published", "processed_content", ["published_at"])
    op.create_index("ix_processed_content_category", "processed_content", ["category"])
    op.create_index("ix_processed_content_breaking", "processed_content", ["is_breaking", "breaking_score"])
    
    # Create vector_embeddings table
    op.create_table(
        "vector_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"])
    )
    
    # Create hookline_queue table
    op.create_table(
        "hookline_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_title", sa.String(500), nullable=False),
        sa.Column("generated_hook", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"])
    )
    
    # Create breaking_alerts table
    op.create_table(
        "breaking_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_level", sa.String(20), nullable=False),
        sa.Column("alert_score", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("action_required", sa.Text(), nullable=True),
        sa.Column("platforms_detected", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("detection_confidence", sa.Numeric(3, 2), server_default="0.0", nullable=False),
        sa.Column("notifications_sent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notifications_opened", sa.Integer(), server_default="0", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"])
    )
    
    # Create velocity_metrics table
    op.create_table(
        "velocity_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("hour_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("engagement_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("velocity_score", sa.Numeric(5, 2), server_default="0.0", nullable=False),
        sa.Column("is_breaking_candidate", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"])
    )
    
    # Create user_reads table
    op.create_table(
        "user_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("completion_percentage", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"]),
        sa.UniqueConstraint("user_id", "content_id")
    )
    
    # Create user_saves table
    op.create_table(
        "user_saves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_name", sa.String(100), server_default="default", nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"]),
        sa.UniqueConstraint("user_id", "content_id")
    )
    
    # Create user_feedback table
    op.create_table(
        "user_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_type", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reported_issue", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["processed_content.id"])
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("user_feedback")
    op.drop_table("user_saves")
    op.drop_table("user_reads")
    op.drop_table("velocity_metrics")
    op.drop_table("breaking_alerts")
    op.drop_table("hookline_queue")
    op.drop_table("vector_embeddings")
    op.drop_table("processed_content")
    op.drop_table("raw_content")
    op.drop_table("sources")
    op.drop_table("users")
