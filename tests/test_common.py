from common import (
    get_max_age_days,
    parse_age_days,
    parse_markdown_table,
    strip_markdown_link,
)


class TestParseAgeDays:
    def test_units(self):
        assert parse_age_days("0d") == 0
        assert parse_age_days("5d") == 5
        assert parse_age_days("12h") == 0
        assert parse_age_days("2w") == 14
        assert parse_age_days("1mo") == 30

    def test_whitespace_and_case(self):
        assert parse_age_days(" 3 D ") == 3

    def test_unparseable_returns_none(self):
        assert parse_age_days("Oct 05") is None
        assert parse_age_days("") is None
        assert parse_age_days("yesterday") is None


class TestGetMaxAgeDays:
    def test_default_is_one(self):
        assert get_max_age_days({}) == 1

    def test_valid_value_passes_through(self):
        assert get_max_age_days({"max_age_days": 2}) == 2
        assert get_max_age_days({"max_age_days": 3}) == 3

    def test_clamped_to_cap(self):
        assert get_max_age_days({"max_age_days": 7}) == 3

    def test_raised_to_one(self):
        assert get_max_age_days({"max_age_days": 0}) == 1

    def test_non_numeric_falls_back_to_one(self):
        assert get_max_age_days({"max_age_days": "tomorrow"}) == 1


class TestStripMarkdownLink:
    def test_link_cell(self):
        assert strip_markdown_link("[Acme](https://acme.com)") == ("Acme", "https://acme.com")

    def test_plain_cell(self):
        assert strip_markdown_link("Acme") == ("Acme", None)


class TestParseMarkdownTable:
    def test_basic_table(self):
        md = "\n".join([
            "# Jobs",
            "",
            "| Company | Role | Location |",
            "| --- | --- | --- |",
            "| Acme | SWE Intern | NYC |",
            "| Globex | Backend Intern | SF |",
        ])
        rows = parse_markdown_table(md)
        assert rows == [
            {"Company": "Acme", "Role": "SWE Intern", "Location": "NYC"},
            {"Company": "Globex", "Role": "Backend Intern", "Location": "SF"},
        ]

    def test_rows_with_wrong_column_count_are_skipped(self):
        md = "\n".join([
            "| Company | Role |",
            "| --- | --- |",
            "| Acme | SWE Intern |",
            "| broken row with | too | many | cells |",
        ])
        assert len(parse_markdown_table(md)) == 1

    def test_no_table_returns_empty(self):
        assert parse_markdown_table("just some prose") == []

    def test_multiple_tables_all_parsed(self):
        md = "\n".join([
            "## Software",
            "| Company | Role | Location |",
            "| --- | --- | --- |",
            "| Acme | SWE Intern | NYC |",
            "",
            "## Hardware (different column count)",
            "| Company | Role |",
            "| --- | --- |",
            "| Globex | HW Intern |",
        ])
        rows = parse_markdown_table(md)
        assert len(rows) == 2
        assert rows[0]["Company"] == "Acme"
        assert rows[1] == {"Company": "Globex", "Role": "HW Intern"}

    def test_second_table_header_and_separator_not_treated_as_rows(self):
        md = "\n".join([
            "| Company | Role |",
            "| --- | --- |",
            "| Acme | SWE Intern |",
            "",
            "| Company | Role |",
            "| :--- | ---: |",
            "| Globex | HW Intern |",
        ])
        rows = parse_markdown_table(md)
        companies = [r["Company"] for r in rows]
        assert companies == ["Acme", "Globex"]  # no '---' or 'Company' junk rows
