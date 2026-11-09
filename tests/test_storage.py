"""Unit tests — storage layer only, no MCP involved."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from database.db import TaskRepository
from database.doc_search import DocumentIndex
from database.models import NoteCreate, TaskCreate, TaskUpdate
from database.notes_store import NotesStore


@pytest.fixture
def repo(tmp_path):
    return TaskRepository(tmp_path / "t.db")


def test_create_and_list(repo):
    t = repo.create(TaskCreate(title="  Learn MCP ", priority="high", due_date=date.today()))
    assert t.id == 1 and t.title == "Learn MCP" and t.status == "todo"
    assert [x.title for x in repo.list()] == ["Learn MCP"]


def test_validation_rejects_bad_input():
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")
    with pytest.raises(ValidationError):
        TaskCreate(title="x", priority="urgent")


def test_complete_sets_timestamp_and_stats(repo):
    a = repo.create(TaskCreate(title="a", project="P", due_date=date.today()))
    repo.create(TaskCreate(title="b", project="P", due_date=date.today() - timedelta(days=2)))
    done = repo.complete(a.id)
    assert done.status == "done" and done.completed_at
    s = repo.stats()
    assert s["completed"] == 1 and s["overdue"] == 1 and s["projects"]["P"]["pct"] == 50
    reopened = repo.update(a.id, TaskUpdate(status="todo"))
    assert reopened.completed_at is None


def test_update_missing_and_delete(repo):
    with pytest.raises(ValueError):
        repo.update(99, TaskUpdate(title="x"))
    t = repo.create(TaskCreate(title="gone"))
    assert repo.delete(t.id) and not repo.delete(t.id)
    assert any("Deleted" in a["message"] for a in repo.recent_activity())


def test_notes_crud_and_search(tmp_path):
    store = NotesStore(tmp_path)
    n = store.create(NoteCreate(title="RAG ideas", content="chunk overlap", tags=["rag"], important=True))
    store.create(NoteCreate(title="RAG ideas", content="dup title"))
    assert {x["id"] for x in store.list()} == {"rag-ideas", "rag-ideas-2"}
    assert store.search("overlap")[0]["id"] == n["id"]
    assert len(store.search("rag", important_only=True)) == 1
    updated = store.update(n["id"], content="more", append=True)
    assert updated["content"].endswith("more") and updated["important"]


def test_notes_path_traversal_blocked(tmp_path):
    with pytest.raises(ValueError):
        NotesStore(tmp_path).get("../secrets")


def test_document_search(tmp_path):
    (tmp_path / "a.md").write_text("# Arch\n\nThe MCP client routes tool calls.\n\nUnrelated text.")
    (tmp_path / "b.txt").write_text("Cooking recipes and pasta.")
    idx = DocumentIndex(tmp_path)
    assert len(idx.list()) == 2
    hits = idx.search("tool calls routing")
    assert hits and hits[0]["document"] == "a.md"
    with pytest.raises(ValueError):
        idx.read("../../etc/passwd")
