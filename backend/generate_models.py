import os

models_dir = 'c:/PJT/backend/app/models'
os.makedirs(models_dir, exist_ok=True)

files = {
    'base.py': '''from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
''',
    'users.py': '''import uuid
from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(CITEXT, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='invited')
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
''',
    'organizations.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
from .base import Base, TimestampMixin

class Organization(Base, TimestampMixin):
    __tablename__ = 'organizations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(CITEXT, unique=True, nullable=False)
    plan_tier = Column(Text, nullable=False, default='free')
    settings = Column(JSONB, nullable=False, server_default='{}')
    deleted_at = Column(DateTime(timezone=True))

class OrganizationMember(Base, TimestampMixin):
    __tablename__ = 'organization_members'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(Text, nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )
''',
    'projects.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin

class Project(Base, TimestampMixin):
    __tablename__ = 'projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    status = Column(Text, nullable=False, default='active')
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_project_org_name'),
    )
''',
    'meetings.py': '''import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin

class Meeting(Base, TimestampMixin):
    __tablename__ = 'meetings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    status = Column(Text, nullable=False, default='scheduled')
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    deleted_at = Column(DateTime(timezone=True))
''',
    'media.py': '''import uuid
from sqlalchemy import Column, Text, BigInteger, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin

class MediaAsset(Base, TimestampMixin):
    __tablename__ = 'media_assets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    asset_type = Column(Text, nullable=False)
    storage_bucket = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    storage_provider = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    size_bytes = Column(BigInteger)
    duration_seconds = Column(Numeric(10, 3))
    checksum_sha256 = Column(Text)
    resolution = Column(Text)
    codec = Column(Text)
    upload_status = Column(Text, nullable=False, default='pending')
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('storage_bucket', 'storage_key', name='uq_media_asset_storage'),
    )
''',
    'models_registry.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, TimestampMixin

class ModelVersion(Base, TimestampMixin):
    __tablename__ = 'model_versions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_family = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    artifact_uri = Column(Text)
    training_dataset_id = Column(UUID(as_uuid=True)) # no FK initially to avoid circular dependency
    hyperparameters = Column(JSONB)
    metrics = Column(JSONB)
    status = Column(Text, nullable=False, default='staging')
    released_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('model_family', 'name', 'version', name='uq_model_version_family_name_ver'),
    )
''',
    'jobs.py': '''import uuid
from sqlalchemy import Column, Text, SmallInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, TimestampMixin

class ProcessingJob(Base, TimestampMixin):
    __tablename__ = 'processing_jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='SET NULL'))
    job_type = Column(Text, nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'))
    status = Column(Text, nullable=False, default='queued')
    priority = Column(SmallInteger, nullable=False, default=0)
    queue_name = Column(Text, nullable=False, default='default')
    attempt_count = Column(SmallInteger, nullable=False, default=0)
    max_attempts = Column(SmallInteger, nullable=False, default=3)
    progress_pct = Column(SmallInteger)
    error_message = Column(Text)
    error_detail = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

class ProcessingJobEvent(Base):
    __tablename__ = 'processing_job_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, server_default='{}')
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'participants.py': '''import uuid
from sqlalchemy import Column, Text, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from .base import Base, TimestampMixin

class Participant(Base, TimestampMixin):
    __tablename__ = 'participants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    display_name = Column(Text, nullable=False)
    external_reference = Column(Text)
    deleted_at = Column(DateTime(timezone=True))

class MeetingParticipant(Base, TimestampMixin):
    __tablename__ = 'meeting_participants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    display_name = Column(Text, nullable=False)
    email = Column(CITEXT)
    role_in_meeting = Column(Text)
    external_platform_id = Column(Text)
    joined_at = Column(DateTime(timezone=True))
    left_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('uq_meeting_participants_platform', 'meeting_id', 'external_platform_id', unique=True, postgresql_where=__import__('sqlalchemy.sql').text('external_platform_id IS NOT NULL')),
    )

class ParticipantTrack(Base, TimestampMixin):
    __tablename__ = 'participant_tracks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='CASCADE'), nullable=False)
    meeting_participant_id = Column(UUID(as_uuid=True), ForeignKey('meeting_participants.id', ondelete='SET NULL'))
    participant_id = Column(UUID(as_uuid=True), ForeignKey('participants.id', ondelete='SET NULL'))
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    track_label = Column(Text, nullable=False)
    first_seen_at_ms = Column(Integer, nullable=False)
    last_seen_at_ms = Column(Integer, nullable=False)
    detection_frame_count = Column(Integer)
    avg_detection_confidence = Column(Numeric(5, 4))
''',
    'features.py': '''import uuid
from sqlalchemy import Column, Text, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base

class FeatureExtraction(Base):
    __tablename__ = 'feature_extractions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='CASCADE'), nullable=False)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    extraction_pipeline_version = Column(Text, nullable=False)
    feature_type = Column(Text, nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    frame_index = Column(Integer)
    confidence = Column(Numeric(5, 4))
    values = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

class FeatureWindow(Base):
    __tablename__ = 'feature_windows'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    feature_type = Column(Text, nullable=False)
    window_start_ms = Column(Integer, nullable=False)
    window_end_ms = Column(Integer, nullable=False)
    aggregation = Column(JSONB, nullable=False)
    source_extraction_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('participant_track_id', 'feature_type', 'window_start_ms', 'window_end_ms', name='uq_feature_windows_track_feature_time'),
    )
''',
    'metrics.py': '''import uuid
from sqlalchemy import Column, Text, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class BehavioralMetric(Base):
    __tablename__ = 'behavioral_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    metric_key = Column(Text, nullable=False)
    metric_category = Column(Text, nullable=False)
    window_start_ms = Column(Integer)
    window_end_ms = Column(Integer)
    value = Column(Numeric(12, 6), nullable=False)
    unit = Column(Text)
    computed_by_pipeline_version = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'scores.py': '''import uuid
from sqlalchemy import Column, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from .base import Base

class NtsScore(Base):
    __tablename__ = 'nts_scores'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'))
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    nts_score = Column(Numeric(6, 3), nullable=False)
    confidence_interval_low = Column(Numeric(6, 3))
    confidence_interval_high = Column(Numeric(6, 3))
    component_scores = Column(JSONB, nullable=False)
    input_metric_ids = Column(ARRAY(UUID(as_uuid=True)))
    computed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

class ModelPrediction(Base):
    __tablename__ = 'model_predictions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    nts_score_id = Column(UUID(as_uuid=True), ForeignKey('nts_scores.id', ondelete='CASCADE'))
    subject_type = Column(Text, nullable=False)
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    prediction_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'archetypes.py': '''import uuid
from sqlalchemy import Column, Text, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin

class Archetype(Base, TimestampMixin):
    __tablename__ = 'archetypes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    description = Column(Text)

class ParticipantArchetype(Base):
    __tablename__ = 'participant_archetypes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    archetype_id = Column(UUID(as_uuid=True), ForeignKey('archetypes.id', ondelete='RESTRICT'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    confidence = Column(Numeric(5, 4))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('participant_track_id', 'model_version_id', name='uq_participant_archetype_track_model'),
    )
''',
    'reports.py': '''import uuid
from sqlalchemy import Column, Text, SmallInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin

class Report(Base, TimestampMixin):
    __tablename__ = 'reports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='SET NULL'))
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    export_format = Column(Text)
    storage_bucket = Column(Text)
    storage_key = Column(Text)
    deleted_at = Column(DateTime(timezone=True))

class ReportSection(Base, TimestampMixin):
    __tablename__ = 'report_sections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'), nullable=False)
    section_key = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    order_index = Column(SmallInteger, nullable=False)
    content_markdown = Column(Text)
    content_source = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('report_id', 'section_key', name='uq_report_sections_report_key'),
    )
''',
    'llm.py': '''import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base

class LlmGeneration(Base):
    __tablename__ = 'llm_generations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    report_section_id = Column(UUID(as_uuid=True), ForeignKey('report_sections.id', ondelete='SET NULL'))
    nts_score_id = Column(UUID(as_uuid=True), ForeignKey('nts_scores.id', ondelete='SET NULL'))
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    prompt_template_key = Column(Text, nullable=False)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    input_context = Column(JSONB)
    output_text = Column(Text, nullable=False)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'datasets.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, TimestampMixin

class Dataset(Base, TimestampMixin):
    __tablename__ = 'datasets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    name = Column(Text, nullable=False)
    purpose = Column(Text, nullable=False)
    description = Column(Text)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

class DatasetSample(Base):
    __tablename__ = 'dataset_samples'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='SET NULL'))
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'))
    label = Column(JSONB)
    split = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'experiments.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, TimestampMixin

class Experiment(Base, TimestampMixin):
    __tablename__ = 'experiments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='RESTRICT'), nullable=False)
    resulting_model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='SET NULL'))
    name = Column(Text, nullable=False)
    config = Column(JSONB)
    status = Column(Text, nullable=False)
    metrics = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
''',
    'audit.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from .base import Base

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    action = Column(Text, nullable=False)
    resource_type = Column(Text, nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    ip_address = Column(INET)
    user_agent = Column(Text)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default='{}')
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    'auth.py': '''import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
''',
    '__init__.py': '''from .base import Base
from .users import User
from .organizations import Organization, OrganizationMember
from .projects import Project
from .meetings import Meeting
from .media import MediaAsset
from .jobs import ProcessingJob, ProcessingJobEvent
from .participants import Participant, MeetingParticipant, ParticipantTrack
from .features import FeatureExtraction, FeatureWindow
from .metrics import BehavioralMetric
from .scores import NtsScore, ModelPrediction
from .models_registry import ModelVersion
from .archetypes import Archetype, ParticipantArchetype
from .reports import Report, ReportSection
from .llm import LlmGeneration
from .datasets import Dataset, DatasetSample
from .experiments import Experiment
from .audit import AuditLog
from .auth import RefreshToken

__all__ = [
    "Base", "User", "Organization", "OrganizationMember", "Project", "Meeting",
    "MediaAsset", "ProcessingJob", "ProcessingJobEvent", "Participant",
    "MeetingParticipant", "ParticipantTrack", "FeatureExtraction", "FeatureWindow",
    "BehavioralMetric", "NtsScore", "ModelPrediction", "ModelVersion",
    "Archetype", "ParticipantArchetype", "Report", "ReportSection",
    "LlmGeneration", "Dataset", "DatasetSample", "Experiment", "AuditLog", "RefreshToken"
]
'''
}

for filename, content in files.items():
    path = os.path.join(models_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Created {len(files)} model files successfully.")
