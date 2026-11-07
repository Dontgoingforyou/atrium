"""Схемы internal API для Hocuspocus document-collab."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCollabAuthenticateRequest(BaseModel):
    ticket: str = Field(..., min_length=8)


class DocumentCollabAuthenticateRead(BaseModel):
    document_id: UUID
    user_sub: str
    display_name: str
    version: int = Field(..., ge=1)
    body: str | None = None


class DocumentCollabDocumentRead(BaseModel):
    document_id: UUID
    version: int = Field(..., ge=1)
    body: str | None = None


class DocumentCollabSnapshotRequest(BaseModel):
    body: str | None = None
    expected_version: int = Field(..., ge=1)
    actor_sub: str = Field(..., min_length=1, max_length=255)
    actor_display_name: str | None = Field(default=None, max_length=512)


class DocumentCollabSnapshotRead(BaseModel):
    document_id: UUID
    version: int = Field(..., ge=1)
