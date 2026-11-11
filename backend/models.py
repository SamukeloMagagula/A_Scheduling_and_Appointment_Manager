"""SQLAlchemy models — mirror of schema.sql.

The database is still the source of truth; create it with schema.sql.
These models exist so the Python code gets types, joins and relationship
helpers without hand-writing SQL for the common reads.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, String, Time,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

ENTRY_TYPES = ("work", "customer", "standby", "break", "leave")
USER_ROLES  = ("user", "manager", "admin")


class Department(Base):
    __tablename__ = "departments"
    id:   Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    teams: Mapped[list["Team"]] = relationship(back_populates="department")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("department_id", "name", name="uq_team_dept_name"),)

    id:            Mapped[int] = mapped_column(primary_key=True)
    name:          Mapped[str] = mapped_column(String(120), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    department: Mapped[Department] = relationship(back_populates="teams")
    members:    Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]  = mapped_column(primary_key=True)
    email:      Mapped[str]  = mapped_column(String(190), unique=True, nullable=False)
    name:       Mapped[str]  = mapped_column(String(120), nullable=False)
    role:       Mapped[str]  = mapped_column(Enum(*USER_ROLES, name="user_role"),
                                             nullable=False, default="user")
    team_id:    Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    team:    Mapped[Optional[Team]] = relationship(back_populates="members")
    entries: Mapped[list["TimeEntry"]] = relationship(back_populates="user",
                                                      cascade="all, delete-orphan")


class Customer(Base):
    __tablename__ = "customers"

    id:         Mapped[int] = mapped_column(primary_key=True)
    name:       Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    active:     Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id:         Mapped[int] = mapped_column(primary_key=True)
    name:       Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    active:     Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)


class TimeEntry(Base):
    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_entry_times"),
        Index("ix_entry_user_date", "user_id", "entry_date"),
    )

    id:          Mapped[int]  = mapped_column(primary_key=True)
    user_id:     Mapped[int]  = mapped_column(ForeignKey("users.id"), nullable=False)
    entry_date:  Mapped[date] = mapped_column(Date, nullable=False)
    start_time:  Mapped[time] = mapped_column(Time, nullable=False)
    end_time:    Mapped[time] = mapped_column(Time, nullable=False)
    entry_type:  Mapped[str]  = mapped_column(Enum(*ENTRY_TYPES, name="entry_type"), nullable=False)
    project_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"),  nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    notes:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(),
                                                  onupdate=func.current_timestamp())

    user:     Mapped[User]                 = relationship(back_populates="entries")
    project:  Mapped[Optional[Project]]    = relationship()
    customer: Mapped[Optional[Customer]]   = relationship()


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id:          Mapped[int] = mapped_column(primary_key=True)
    user_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action:      Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entity_id:   Mapped[Optional[int]] = mapped_column(nullable=True)
    detail:      Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
