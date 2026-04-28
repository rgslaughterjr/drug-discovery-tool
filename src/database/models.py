"""SQLAlchemy table definitions for persistent research sessions."""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, MetaData, String, Table, Text, create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

research_sessions = Table(
    "research_sessions", metadata,
    Column("id", String(36), primary_key=True),
    Column("auth_session_id", String(36), nullable=False, index=True),
    Column("name", String(200), nullable=True),
    Column("organism", String(200), nullable=True),
    Column("target_protein", String(200), nullable=True),
    Column("uniprot_id", String(20), nullable=True),
    Column("pdb_id", String(10), nullable=True),
    Column("chembl_target_id", String(20), nullable=True),
    # "evaluate" | "controls" | "screening" | "hits"
    Column("pipeline_stage", String(50), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("last_active_at", DateTime, default=datetime.utcnow),
    Column("provider", String(50), nullable=False),
    Column("model", String(100), nullable=False),
)

conversation_turns = Table(
    "conversation_turns", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("research_session_id", String(36),
           ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("turn_index", Integer, nullable=False),
    Column("role", String(20), nullable=False),   # "user" | "assistant"
    # Full Anthropic content block list serialized as JSON
    Column("content_json", Text, nullable=False),
    Column("is_compressed", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

workflow_results = Table(
    "workflow_results", metadata,
    Column("id", String(36), primary_key=True),
    Column("research_session_id", String(36),
           ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
    # "evaluate_target" | "get_controls" | "prep_screening" | "analyze_hits"
    Column("workflow_type", String(50), nullable=False),
    Column("result_json", Text, nullable=False),
    # Audit log: all tool calls + responses for this workflow run
    Column("tool_calls_json", Text, nullable=True),
    Column("model_used", String(100), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("is_verified", Boolean, default=False),
)

verified_compounds = Table(
    "verified_compounds", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workflow_result_id", String(36),
           ForeignKey("workflow_results.id", ondelete="CASCADE"), nullable=False),
    Column("research_session_id", String(36),
           ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
    # "positive_control" | "negative_control" | "hit"
    Column("compound_type", String(20), nullable=False),
    Column("name", String(300), nullable=True),
    Column("pubchem_cid", Integer, nullable=True),
    Column("chembl_id", String(20), nullable=True),
    Column("smiles", Text, nullable=False),
    Column("canonical_smiles", Text, nullable=True),
    Column("mw", Float, nullable=True),
    Column("logp", Float, nullable=True),
    Column("tpsa", Float, nullable=True),
    Column("hbd", Integer, nullable=True),
    Column("hba", Integer, nullable=True),
    Column("activity_value_nm", Float, nullable=True),
    Column("activity_type", String(10), nullable=True),  # "IC50" | "Ki" | "Kd"
    Column("is_pains", Boolean, nullable=True),
    Column("pains_alerts", Text, nullable=True),         # comma-separated alert names
    Column("docking_score", Float, nullable=True),
    Column("rank", Integer, nullable=True),
    Column("notes", Text, nullable=True),
)


def create_engine_from_path(db_path: str) -> Engine:
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)
