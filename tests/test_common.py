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

    def test_month_day_dates(self):
        import datetime
        today = datetime.date.today()
        assert parse_age_days(today.strftime("%b %d")) == 0
        yesterday = today - datetime.timedelta(days=1)
        assert parse_age_days(yesterday.strftime("%b %d")) == 1
        # A future month/day is read as last year's date, never negative.
        tomorrow = today + datetime.timedelta(days=1)
        assert parse_age_days(tomorrow.strftime("%b %d")) >= 300

    def test_unparseable_returns_none(self):
        assert parse_age_days("") is None
        assert parse_age_days("yesterday") is None
        assert parse_age_days("Octember 05") is None


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

    def test_bold_wrapped_link(self):  # jobright style
        assert strip_markdown_link("**[SAP](https://www.sap.com)**") == \
            ("SAP", "https://www.sap.com")

    def test_html_anchor(self):  # speedyapply company cell
        cell = '<a href="https://www.nvidia.com"><strong>NVIDIA</strong></a>'
        assert strip_markdown_link(cell) == ("NVIDIA", "https://www.nvidia.com")

    def test_html_anchor_with_image_body(self):  # speedyapply posting cell
        cell = '<a href="https://jobs.example/1"><img src="x.png" alt="Apply" width="70"/></a>'
        assert strip_markdown_link(cell) == ("", "https://jobs.example/1")

    def test_plain_cell_with_html_noise(self):
        assert strip_markdown_link("<strong>Acme</strong>") == ("Acme", None)


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

    def test_table_split_by_multiline_cell_continues_current_table(self):
        # A newline inside a cell breaks the pipe-block in two; the second
        # block must reuse the current header, not misread a data row as one.
        md = "\n".join([
            "| Company | Role | Location |",
            "| --- | --- | --- |",
            "| Acme | SWE Intern | NYC |",
            "| Globex | Broken role that",
            "wraps to a second line | SF |",
            "| Initech | QA Intern | Austin |",
            "| Umbrella | Platform Intern | Boston |",
        ])
        rows = parse_markdown_table(md)
        companies = [r["Company"] for r in rows]
        # The broken row (wrong cell count) is skipped; everything after it
        # is still parsed under the original header.
        assert companies == ["Acme", "Initech", "Umbrella"]

    def test_pipe_lines_before_any_table_are_ignored(self):
        md = "\n".join([
            "| just a decorative pipe line, no separator after |",
            "",
            "| Company | Role |",
            "| --- | --- |",
            "| Acme | SWE Intern |",
        ])
        rows = parse_markdown_table(md)
        assert rows == [{"Company": "Acme", "Role": "SWE Intern"}]

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
