from datetime import date, datetime, timedelta

from ui import components as C


def test_due_label():
    t = date.today()
    assert C.due_label(t.isoformat()) == "Today"
    assert C.due_label((t + timedelta(days=1)).isoformat()) == "Tomorrow"
    assert C.due_label((t - timedelta(days=3)).isoformat()) == "3d overdue"
    assert C.due_label(None) == "No date"


def test_greeting():
    assert C.greeting(datetime(2026, 1, 1, 9)) == "Good Morning"
    assert C.greeting(datetime(2026, 1, 1, 20)) == "Good Evening"


def test_html_is_escaped():
    html = C.task_card({"id": 1, "title": "<script>x</script>", "priority": "low", "status": "todo",
                        "project": "P", "due_date": None})
    assert "<script>" not in html and "&lt;script&gt;" in html
