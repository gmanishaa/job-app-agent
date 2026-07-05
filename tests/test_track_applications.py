import io
import json

import yaml

import track_applications


def run_cmd(monkeypatch, tmp_path, argv: list[str], stdin_payload) -> str:
    monkeypatch.setenv("JOB_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["track_applications.py"] + argv)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(stdin_payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    track_applications.main()
    return out.getvalue()


def read_tracker(tmp_path) -> list[dict]:
    return yaml.safe_load((tmp_path / "applications.yaml").read_text())


def posting(**overrides) -> dict:
    base = {
        "company": "Acme",
        "role": "SWE Intern",
        "location": "NYC",
        "link": "https://a.co/1",
        "source": "simplify-internships",
    }
    base.update(overrides)
    return base


def test_upsert_adds_new_postings_as_seen(monkeypatch, tmp_path):
    out = run_cmd(monkeypatch, tmp_path, ["upsert"], [posting()])
    echoed = json.loads(out)
    assert echoed[0]["status"] == "seen"
    assert echoed[0]["already_seen"] is False

    entries = read_tracker(tmp_path)
    assert len(entries) == 1
    assert entries[0]["status"] == "seen"
    assert entries[0]["first_seen"] == entries[0]["last_updated"]


def test_upsert_marks_repeats_with_current_status(monkeypatch, tmp_path):
    run_cmd(monkeypatch, tmp_path, ["upsert"], [posting()])
    run_cmd(monkeypatch, tmp_path, ["set-status", "tailored"], posting())

    out = run_cmd(monkeypatch, tmp_path, ["upsert"],
                  [posting(), posting(company="Globex", link="https://g.co/1")])
    echoed = json.loads(out)
    assert echoed[0]["already_seen"] is True
    assert echoed[0]["status"] == "tailored"
    assert echoed[1]["already_seen"] is False
    assert len(read_tracker(tmp_path)) == 2


def test_upsert_key_ignores_link_changes(monkeypatch, tmp_path):
    run_cmd(monkeypatch, tmp_path, ["upsert"], [posting()])
    out = run_cmd(monkeypatch, tmp_path, ["upsert"],
                  [posting(link="https://a.co/1?utm=changed")])
    assert json.loads(out)[0]["already_seen"] is True
    assert len(read_tracker(tmp_path)) == 1


def test_set_status_records_tailored_file(monkeypatch, tmp_path):
    run_cmd(monkeypatch, tmp_path, ["upsert"], [posting()])
    run_cmd(monkeypatch, tmp_path,
            ["set-status", "tailored", "--file", "tailored/acme-2026-07-05.md"],
            posting())
    entry = read_tracker(tmp_path)[0]
    assert entry["status"] == "tailored"
    assert entry["tailored_file"] == "tailored/acme-2026-07-05.md"


def test_set_status_untracked_posting_added_with_warning(monkeypatch, tmp_path, capsys):
    run_cmd(monkeypatch, tmp_path, ["set-status", "tailored"], posting())
    entries = read_tracker(tmp_path)
    assert len(entries) == 1
    assert entries[0]["status"] == "tailored"
    assert "was not in the tracker" in capsys.readouterr().err


def test_set_status_rejects_unknown_status(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        run_cmd(monkeypatch, tmp_path, ["set-status", "ghosted"], posting())
