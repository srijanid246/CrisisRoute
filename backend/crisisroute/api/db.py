from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioRecord(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seed = Column(Integer, nullable=False)
    preset = Column(String, nullable=True)
    data = Column(JSON, nullable=False)
    hidden_events = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    plans = relationship("PlanRecord", back_populates="scenario", cascade="all, delete-orphan")
    events = relationship("EventRecord", back_populates="scenario", cascade="all, delete-orphan")


class PlanRecord(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("scenario_id", "version", name="uq_plan_scenario_version"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    version = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    scenario = relationship("ScenarioRecord", back_populates="plans")


class EventRecord(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    resulting_plan_version = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    diff = Column(JSON, nullable=False)
    static_outcome = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    scenario = relationship("ScenarioRecord", back_populates="events")


def build_engine(database_url: str):
    connect_args = {}
    engine_kwargs = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool
    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


def build_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
