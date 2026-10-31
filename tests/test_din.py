from din import parse_din_id


def test_branch_name():
    assert parse_din_id("DIN-202/repo-bootstrap") == "DIN-202"


def test_commit_message():
    assert parse_din_id("Fix thing\n\nDIN-7 follow-up") == "DIN-7"


def test_no_id():
    assert parse_din_id("feature/no-id") is None
    assert parse_din_id(None) is None
