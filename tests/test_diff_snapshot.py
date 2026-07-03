from diff_snapshot import record_key


def test_link_changes_do_not_make_a_posting_new():
    a = {"company": "Acme", "role": "SWE Intern", "location": "NYC",
         "link": "https://a.co/1?utm=x"}
    b = {**a, "link": "https://a.co/1?utm=y"}
    assert record_key(a) == record_key(b)


def test_key_is_case_insensitive():
    a = {"company": "Acme", "role": "SWE Intern", "location": "NYC", "link": ""}
    b = {**a, "company": "ACME"}
    assert record_key(a) == record_key(b)


def test_new_location_counts_as_new():
    a = {"company": "Acme", "role": "SWE Intern", "location": "NYC", "link": ""}
    b = {**a, "location": "SF"}
    assert record_key(a) != record_key(b)
