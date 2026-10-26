import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    stage = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    params = Column(JSONB, nullable=False)
    params_hash = Column(Text, nullable=False)
    code_version = Column(Text, nullable=False)
    model_versions = Column(JSONB, nullable=False)
    input_run_ids = Column(JSONB, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    error = Column(Text)


class VadSegment(Base):
    __tablename__ = 'vad_segments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    mean_prob = Column(Float, nullable=False)
    method = Column(Text, nullable=False)


class SpeechSegment(Base):
    __tablename__ = 'speech_segments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    language = Column(Text)
    asr_avg_logprob = Column(Float)
    no_speech_prob = Column(Float)
    diar_cluster_id = Column(Text)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'), nullable=True)
    attribution_confidence = Column(Float)
    attribution_method = Column(Text)
    alt_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'), nullable=True)
    alt_confidence = Column(Float)
    is_overlap = Column(Boolean, default=False)
    words_per_min = Column(Float)
    derivation = Column(Text, nullable=False)
    evidence = Column(JSONB)


class SpeechWord(Base):
    __tablename__ = 'speech_words'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), ForeignKey('speech_segments.id', ondelete='CASCADE'), nullable=False)
    idx = Column(Integer, nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    word = Column(Text, nullable=False)
    prob = Column(Float)


class DiarizationTurn(Base):
    __tablename__ = 'diarization_turns'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    cluster_id = Column(Text, nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    method = Column(Text, nullable=False)


class MouthActivity(Base):
    __tablename__ = 'mouth_activity'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    t_ms = Column(Integer, nullable=False)
    mar = Column(Float)
    mar_delta = Column(Float)
    lip_activity = Column(Float)
    visible = Column(Boolean, nullable=False)
    face_px = Column(Integer)


class AttributionEvidence(Base):
    __tablename__ = 'attribution_evidence'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(UUID(as_uuid=True), ForeignKey('speech_segments.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    lip_corr = Column(Float)
    lag_ms = Column(Integer)
    visible_frac = Column(Float)
    vad_overlap = Column(Float)
    cluster_prior = Column(Float)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    details = Column(JSONB)


class TrackSpeechActivity(Base):
    __tablename__ = 'track_speech_activity'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    t_ms = Column(Integer, nullable=False)
    activity = Column(Float)
    lip_activity = Column(Float)
    vad_prob = Column(Float)


class ProsodyWindow(Base):
    __tablename__ = 'prosody_windows'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    t_ms = Column(Integer, nullable=False)
    f0_hz = Column(Float)
    voiced = Column(Boolean)
    rms_db = Column(Float)


class ListenerState(Base):
    __tablename__ = 'listener_states'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    state = Column(Text, nullable=False)
    target_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'), nullable=True)
    confidence = Column(Float)
    gaze_on_target_pct = Column(Float)
    derivation = Column(Text, nullable=False)
    evidence = Column(JSONB)


class InteractionEvent(Base):
    __tablename__ = 'interaction_events'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    type = Column(Text, nullable=False)
    from_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'), nullable=True)
    to_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'), nullable=True)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    latency_ms = Column(Integer)
    derivation = Column(Text, nullable=False)
    evidence = Column(JSONB)


class SpeechMetric(Base):
    __tablename__ = 'speech_metrics'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=True)
    metric_key = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(Text)
    window_start_ms = Column(Integer)
    window_end_ms = Column(Integer)
    derivation = Column(Text, nullable=False)
    method = Column(Text)
    evidence = Column(JSONB)


class SpeechReport(Base):
    __tablename__ = 'speech_reports'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    kind = Column(Text, nullable=False)
    input_hash = Column(Text, nullable=False)
    report_json = Column(JSONB, nullable=False)
    pdf_key = Column(Text)
    created_at = Column(DateTime(timezone=True))
