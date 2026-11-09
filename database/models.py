"""Pydantic models = the validation layer.

Every value that comes from the LLM (through an MCP tool call) is checked
here before it touches the database. If Claude sends priority="urgent" or an
empty title, Pydantic raises a clear error instead of corrupting data.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Priority = Literal["low", "medium", "high"]
Status = Literal["todo", "in_progress", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    priority: Priority = "medium"
    due_date: Optional[date] = None
    project: str = Field(default="General", max_length=60)

    @field_validator("title", "project")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    due_date: Optional[date] = None
    project: Optional[str] = Field(default=None, max_length=60)


class Task(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: Status
    due_date: Optional[date]
    project: str
    created_at: str
    completed_at: Optional[str]


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    content: str = Field(default="", max_length=50_000)
    tags: list[str] = Field(default_factory=list)
    important: bool = False
