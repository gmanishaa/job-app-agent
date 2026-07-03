import time

from fetch_source import normalize_json_listings, normalize_rows


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
