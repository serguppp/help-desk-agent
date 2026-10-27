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


def test_search_matches_tokens_independently_of_word_order(monkeypatch):
    document = {
        "source": "example.md",
        "text": "# Example\n## Booking fee\nThe online charge is two euros.\n",
    }
    monkeypatch.setattr(policies, "load_policies", lambda: [document])

    results = policies.search_policies("booking fee")

    assert results
    assert results == policies.search_policies("fee booking")


def test_load_policies_rejects_directory_without_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(policies, "POLICIES_PATH", tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="No CityWheels policy documents found",
    ):
        policies.load_policies()


def test_tokenize_ignores_case_punctuation_and_stop_words():
    assert policies.tokenize("  OPEN, March! 24-hour THE ") == {
        "open",
        "march",
        "24",
        "hour",
    }


def test_search_finds_opening_hours_for_multiword_query():
    results = policies.search_policies("open hours march")

    assert results
    assert results[0]["source"] == "faq.md"
    assert results[0]["heading"] == "When are you open?"


def test_search_matches_whole_words_instead_of_substrings():
    results = policies.search_policies("age")

    assert [section["heading"] for section in results] == ["Are there age limits?"]


def test_search_returns_no_results_for_only_stop_words():
    assert policies.search_policies("can I") == []


def test_search_limits_results_and_preserves_order_for_equal_scores(monkeypatch):
    document = {
        "source": "example.md",
        "text": (
            "# Example\n"
            "## First\nVoucher information.\n"
            "## Second\nVoucher information.\n"
            "## Third\nVoucher information.\n"
            "## Fourth\nVoucher information.\n"
        ),
    }
    monkeypatch.setattr(policies, "load_policies", lambda: [document])

    results = policies.search_policies("voucher")

    assert [section["heading"] for section in results] == [
        "First",
        "Second",
        "Third",
    ]


def test_search_ranks_more_matching_tokens_higher(monkeypatch):
    document = {
        "source": "example.md",
        "text": (
            "# Example\n"
            "## First\nVoucher information.\n"
            "## Second\nVoucher and card information.\n"
        ),
    }
    monkeypatch.setattr(policies, "load_policies", lambda: [document])

    results = policies.search_policies("voucher card")

    assert [section["heading"] for section in results] == ["Second", "First"]


def test_search_does_not_increase_weight_for_repeated_query_words():
    assert policies.search_policies("voucher voucher") == policies.search_policies(
        "voucher"
    )


@pytest.mark.parametrize("query", ["buy a bike purchase sales", "purchase bikes"])
def test_search_finds_explicit_sales_policy(query):
    results = policies.search_policies(query)

    assert results[0]["heading"] == "Do you sell bikes?"
    assert results[0]["source"] == "faq.md"
    assert "only rent" in results[0]["text"]


@pytest.mark.parametrize("query", ["payment methods", "accepted payment", "pay"])
def test_search_finds_rental_and_deposit_payment_rules(query):
    results = policies.search_policies(query)

    payment = next(s for s in results if s["heading"] == "How can I pay?")

    assert "cash" in payment["text"]
    assert "not the deposit" in payment["text"]


@pytest.mark.parametrize("file_name", ["faq.md", "prices.md", "cancellations.md"])
def test_read_policy_document_returns_complete_document(file_name):
    result = policies.read_policy_document(file_name)

    assert result["source"] == file_name
    assert result["text"] == (policies.POLICIES_PATH / file_name).read_text(
        encoding="utf-8"
    )
    assert result["text"].strip()


def test_read_policy_document_reads_configured_directory_as_utf8(tmp_path, monkeypatch):
    text = "# FAQ\nZażółć gęślą jaźń.\n"
    (tmp_path / "faq.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(policies, "POLICIES_PATH", tmp_path)

    assert policies.read_policy_document("faq.md") == {
        "source": "faq.md",
        "text": text,
    }


@pytest.mark.parametrize(
    "file_name",
    [
        "",
        "../faq.md",
        r"..\faq.md",
        ".env",
        "FAQ.md",
        "C:/secret.md",
        None,
        123,
        [],
    ],
)
def test_read_policy_document_rejects_unknown_names(file_name):
    with pytest.raises(ValueError, match="file_name"):
        policies.read_policy_document(file_name)


def test_read_policy_document_does_not_hide_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(policies, "POLICIES_PATH", tmp_path)

    with pytest.raises(FileNotFoundError):
        policies.read_policy_document("faq.md")
