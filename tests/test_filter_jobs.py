import io
import json

import yaml

import filter_jobs


def run_filter(monkeypatch, tmp_path, config: dict, postings: list[dict]) -> dict:
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump(config))
    monkeypatch.setenv("JOB_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(postings)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    filter_jobs.main()
    return json.loads(out.getvalue())


BASE_CONFIG = {
    "repos": [],
    "filters": {
        "locations_exclude": ["Bangalore"],
        "seniority_exclude": ["Senior"],
        "keywords_exclude": ["Clearance", "Quant"],
        "keywords_include": ["Software Engineer"],
    },
    "max_age_days": 1,
}


def posting(**overrides) -> dict:
    base = {
        "company": "Acme",
        "role": "Software Engineer Intern",
        "location": "NYC",
        "link": "https://a.co/1",
        "age_days": 0,
        "category": "Software",
    }
    base.update(overrides)
    return base


def test_keyword_match_vs_review_split(monkeypatch, tmp_path):
    result = run_filter(monkeypatch, tmp_path, BASE_CONFIG, [
        posting(),
        posting(company="Globex", role="Platform Intern", link="https://a.co/2"),
    ])
    assert [p["company"] for p in result["keyword_match"]] == ["Acme"]
    assert [p["company"] for p in result["review"]] == ["Globex"]


def test_stale_postings_dropped_unknown_age_kept(monkeypatch, tmp_path):
    result = run_filter(monkeypatch, tmp_path, BASE_CONFIG, [
        posting(age_days=2),
        posting(company="Globex", age_days=None, link="https://a.co/2"),
    ])
    all_kept = result["keyword_match"] + result["review"]
    assert [p["company"] for p in all_kept] == ["Globex"]


def test_max_age_days_configurable(monkeypatch, tmp_path):
    config = {**BASE_CONFIG, "max_age_days": 3}
    result = run_filter(monkeypatch, tmp_path, config, [posting(age_days=3)])
    assert len(result["keyword_match"]) == 1


def test_exact_duplicates_dropped(monkeypatch, tmp_path):
    result = run_filter(monkeypatch, tmp_path, BASE_CONFIG, [
        posting(),
        posting(link="https://a.co/other"),  # same company/role/location
    ])
    assert len(result["keyword_match"]) == 1


def test_hard_excludes(monkeypatch, tmp_path):
    result = run_filter(monkeypatch, tmp_path, BASE_CONFIG, [
        posting(location="Bangalore, India"),
        posting(role="Senior Software Engineer"),
        posting(role="Software Engineer - Clearance Required"),
        posting(role="Trading Intern", category="Quant"),  # excluded via category
    ])
    assert result["keyword_match"] == []
    assert result["review"] == []
