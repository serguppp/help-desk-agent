import pytest

from helpdesk import policies


def test_search_finds_dog_policy():
    results = policies.search_policies("dog")

    assert any(
        section["source"] == "faq.md"
        and section["heading"] == "Can I take my dog?"
        and "Dogs are not allowed" in section["text"]
        for section in results
    )


def test_search_ignores_case_and_surrounding_spaces():
    assert policies.search_policies(" OPEN ") == policies.search_policies("open")
    assert policies.search_policies("open")


def test_search_finds_booking_fee_policy():
    results = policies.search_policies(" booking fee ")

    assert any(
        section["source"] == "prices.md" and section["heading"] == "Booking fee"
        for section in results
    )


def test_search_finds_voucher_refund_policy():
    results = policies.search_policies("voucher")

    assert any(
        section["source"] == "cancellations.md"
        and section["heading"] == "How the money comes back"
        and "new voucher" in section["text"]
        for section in results
    )


def test_search_returns_empty_list_without_matches():
    assert policies.search_policies("capital Australia") == []


@pytest.mark.parametrize("query", ["", "   ", None, 123, [], {}])
def test_search_rejects_invalid_query(query):
    with pytest.raises(ValueError, match="query"):
        policies.search_policies(query)


def test_search_prioritizes_headings_and_avoids_duplicates(monkeypatch):
    document = {
        "source": "example.md",
        "text": (
            "# Example\n"
            "## Other information\n"
            "Ask the staff about a voucher.\n"
            "## Voucher\n"
            "A voucher can be used for payment.\n"
        ),
    }
    monkeypatch.setattr(
        policies,
        "load_policies",
        lambda: [document],
    )

    results = policies.search_policies("voucher")

    assert [section["heading"] for section in results] == [
        "Voucher",
        "Other information",
    ]


def test_search_matches_a_contiguous_phrase(monkeypatch):
    document = {
        "source": "example.md",
        "text": ("# Example\n## Booking fee\nThe online charge is two euros.\n"),
    }
    monkeypatch.setattr(
        policies,
        "load_policies",
        lambda: [document],
    )

    assert policies.search_policies("booking fee")
    assert policies.search_policies("fee booking") == []


def test_load_policies_rejects_directory_without_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(policies, "POLICIES_PATH", tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="No CityWheels policy documents found",
    ):
        policies.load_policies()
