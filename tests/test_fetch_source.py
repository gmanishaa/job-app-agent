import datetime
import time

from fetch_source import normalize_json_listings, normalize_rows, prune_old_snapshots


class TestPruneOldSnapshots:
    def _make(self, tmp_path, days_ago: int, raw: bool = False):
        date = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
        name = f"raw.{date}.md" if raw else f"{date}.json"
        (tmp_path / name).write_text("x")
        return name

    def test_old_files_pruned_within_kind_windows(self, tmp_path):
        kept_records = {self._make(tmp_path, d) for d in (0, 1, 5, 14)}
        pruned_records = {self._make(tmp_path, d) for d in (15, 40)}
        kept_raw = {self._make(tmp_path, d, raw=True) for d in (0, 1, 3)}
        pruned_raw = {self._make(tmp_path, d, raw=True) for d in (4, 40)}

        prune_old_snapshots(tmp_path, {})

        remaining = {f.name for f in tmp_path.iterdir()}
        assert remaining == kept_records | kept_raw
        assert not (pruned_records | pruned_raw) & remaining

    def test_newest_two_kept_even_when_ancient(self, tmp_path):
        # A long gap between runs must not delete the diff baseline.
        names = {self._make(tmp_path, d) for d in (100, 200)}
        prune_old_snapshots(tmp_path, {})
        assert {f.name for f in tmp_path.iterdir()} == names

    def test_third_ancient_file_is_pruned(self, tmp_path):
        oldest = self._make(tmp_path, 300)
        self._make(tmp_path, 200)
        self._make(tmp_path, 100)
        prune_old_snapshots(tmp_path, {})
        assert oldest not in {f.name for f in tmp_path.iterdir()}

    def test_retention_configurable(self, tmp_path):
        name = self._make(tmp_path, 20)
        self._make(tmp_path, 0)
        self._make(tmp_path, 1)
        prune_old_snapshots(tmp_path, {"retention": {"records_days": 30}})
        assert name in {f.name for f in tmp_path.iterdir()}


class TestNormalizeRows:
    def test_continuation_arrow_carries_company_forward(self):
        rows = [
            {"Company": "[Acme](https://acme.com)", "Role": "SWE Intern",
             "Location": "NYC", "Link": "[Apply](https://a.co/1)", "Age": "0d"},
            {"Company": "↳", "Role": "Backend Intern",
             "Location": "SF", "Link": "[Apply](https://a.co/2)", "Age": "2d"},
        ]
        recs = normalize_rows(rows)
        assert recs[0]["company"] == "Acme"
        assert recs[1]["company"] == "Acme"
        assert recs[0]["age_days"] == 0
        assert recs[1]["age_days"] == 2

    def test_link_falls_back_to_role_link(self):
        rows = [{"Company": "Acme", "Role": "[SWE](https://a.co/role)", "Location": "NYC"}]
        assert normalize_rows(rows)[0]["link"] == "https://a.co/role"

    def test_alternate_headers(self):
        rows = [{"Company Name": "Acme", "Position": "SWE", "Location": "NYC",
                 "Apply": "[link](https://a.co/1)", "Date Posted": "1d"}]
        rec = normalize_rows(rows)[0]
        assert rec["company"] == "Acme"
        assert rec["role"] == "SWE"
        assert rec["link"] == "https://a.co/1"
        assert rec["age_days"] == 1

    def test_jobright_style_row(self):
        rows = [{"Company": "**[SAP](https://www.sap.com)**",
                 "Job Title": "**[Software Engineer](https://jobright.ai/jobs/info/123)**",
                 "Location": "Alpharetta, GA", "Work Model": "Hybrid",
                 "Date Posted": "Jul 05"}]
        rec = normalize_rows(rows)[0]
        assert rec["company"] == "SAP"
        assert rec["role"] == "Software Engineer"
        assert rec["link"] == "https://jobright.ai/jobs/info/123"
        assert rec["age_days"] is not None

    def test_speedyapply_style_row(self):
        rows = [{"Company": '<a href="https://www.nvidia.com"><strong>NVIDIA</strong></a>',
                 "Position": "SWE - New College Grad", "Location": "US, CA, Santa Clara",
                 "Salary": "$172k/yr",
                 "Posting": '<a href="https://nvidia.wd5.example/job/1"><img src="a.png"/></a>',
                 "Age": "19d"}]
        rec = normalize_rows(rows)[0]
        assert rec["company"] == "NVIDIA"
        assert rec["role"] == "SWE - New College Grad"
        assert rec["link"] == "https://nvidia.wd5.example/job/1"
        assert rec["age_days"] == 19


class TestNormalizeJsonListings:
    def _listing(self, **overrides):
        base = {
            "company_name": "Acme",
            "title": "SWE Intern",
            "locations": ["NYC", "SF"],
            "url": "https://a.co/1",
            "active": True,
            "date_posted": int(time.time()),
            "category": "Software",
        }
        base.update(overrides)
        return base

    def test_maps_fields(self):
        rec = normalize_json_listings([self._listing()])[0]
        assert rec["company"] == "Acme"
        assert rec["role"] == "SWE Intern"
        assert rec["location"] == "NYC; SF"
        assert rec["link"] == "https://a.co/1"
        assert rec["category"] == "Software"
        assert rec["age_days"] == 0

    def test_inactive_listings_are_skipped(self):
        assert normalize_json_listings([self._listing(active=False)]) == []

    def test_age_days_from_date_posted(self):
        two_days_ago = int(time.time()) - 2 * 86400 - 60
        rec = normalize_json_listings([self._listing(date_posted=two_days_ago)])[0]
        assert rec["age_days"] == 2

    def test_missing_date_posted_gives_none(self):
        rec = normalize_json_listings([self._listing(date_posted=None)])[0]
        assert rec["age_days"] is None
