"""Схемы API интеграции Jira."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class JiraSearchHit(BaseModel):
    issue_key: str
    summary: str
    status_name: str = ""


class JiraFieldRead(BaseModel):
    id: str
    label: str
    group: str
    value: str | None
    kind: str = "text"


class JiraFieldGroupRead(BaseModel):
    key: str
    label: str
    fields: list[JiraFieldRead]


class SpecialistJiraRead(BaseModel):
    specialist_sub: str
    jira_issue_key: str | None
    jira_browse_url: str | None
    jira_synced_at: datetime | None
    groups: list[JiraFieldGroupRead] = Field(default_factory=list)


class JiraLinkRequest(BaseModel):
    issue_key: str = Field(min_length=3, max_length=32)
