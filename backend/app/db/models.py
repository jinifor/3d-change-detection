from datetime import datetime, timezone
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    crs_epsg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    registration_rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tiles: Mapped[list["Tile"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    registration_matrix: Mapped[list[list[float]] | None] = mapped_column(JSON, nullable=True)
    registration_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    project: Mapped[Project] = relationship(back_populates="jobs")


class Tile(Base):
    __tablename__ = "tile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"), nullable=False, index=True)
    tile_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    bbox: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    project: Mapped[Project] = relationship(back_populates="tiles")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="tile")


class Candidate(Base):
    __tablename__ = "candidate"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"), nullable=False, index=True)
    tile_id: Mapped[str | None] = mapped_column(ForeignKey("tile.id"), nullable=True, index=True)
    geometry = mapped_column(Geometry(geometry_type="POLYGON"), nullable=False)
    centroid = mapped_column(Geometry(geometry_type="POINT"), nullable=False)
    bbox: Mapped[dict] = mapped_column(JSON, nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=False)
    point_count: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_mean: Mapped[float] = mapped_column(Float, nullable=False)
    distance_max: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[Project] = relationship(back_populates="candidates")
    tile: Mapped[Tile | None] = relationship(back_populates="candidates")
