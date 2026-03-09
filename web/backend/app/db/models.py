"""Database models for the Web UI."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    aep_configs: Mapped[list["AEPConfig"]] = relationship("AEPConfig", back_populates="user", cascade="all, delete-orphan")
    schemas: Mapped[list["Schema"]] = relationship("Schema", back_populates="user", cascade="all, delete-orphan")
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="user", cascade="all, delete-orphan")


class AEPConfig(Base):
    """Adobe Experience Platform configuration per user."""
    
    __tablename__ = "aep_configs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    sandbox_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_client_secret: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted
    org_id: Mapped[str] = mapped_column(String(255), nullable=False)
    technical_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="aep_configs")


class Schema(Base):
    """XDM Schema metadata."""
    
    __tablename__ = "schemas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    aep_schema_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    class_id: Mapped[str] = mapped_column(String(255), nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="schemas")
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="schema")


class Dataset(Base):
    """Dataset metadata."""
    
    __tablename__ = "datasets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    schema_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("schemas.id"), nullable=True)
    aep_dataset_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    identity_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="datasets")
    schema: Mapped[Optional["Schema"]] = relationship("Schema", back_populates="datasets")
    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="dataset", cascade="all, delete-orphan")


class Batch(Base):
    """Ingestion batch metadata."""
    
    __tablename__ = "batches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False)
    aep_batch_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="loading", nullable=False)
    files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="batches")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="batches")


class OnboardingProgress(Base):
    """User onboarding tutorial progress."""
    
    __tablename__ = "onboarding_progress"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    scenario: Mapped[str] = mapped_column(String(100), default="basic", nullable=False)
    completed_steps: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array
    milestones_achieved: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array
    created_resources: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON object
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
