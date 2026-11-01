import json

import pytest

from tests.test_api import AMEX_CSV, upload

BANK_CSV = (
    "Kontoutdrag;;;\n"
    "Bokföringsdag;Text;Belopp;Saldo\n"
    "2025-07-02;ICA NARA;-262,71;9 737,29\n"
    "2025-07-03;LÖN;25 000,00;34 737,29\n"
).encode("cp1252")

BANK_CONFIG = {
    "importer": "csv",
    "mapping": {"date_column": "Bokföringsdag", "description_column": "Text", "amount_column": "Belopp"},
}


@pytest.fixture
def account(axel):
    return axel.post("/accounts", json={"name": "Bank"}).json()["id"]


def preview(client, account_id, content, config=None, name="export.csv"):
    data = {"config": json.dumps(config)} if config else {}
    return client.post(
        f"/accounts/{account_id}/imports/preview", files={"file": (name, content, "text/csv")}, data=data
    )


def confirm(client, account_id, content, config=None, name="export.csv"):
    data = {"config": json.dumps(config)} if config else {}
    return client.post(f"/accounts/{account_id}/imports", files={"file": (name, content, "text/csv")}, data=data)


def test_preview_detects_amex_and_stores_nothing(axel, account):
    r = preview(axel, account, AMEX_CSV)
    assert r.status_code == 200, r.text
    p = r.json()
    assert (p["source"], p["config"], p["error"]) == ("detected", {"importer": "amex_se", "mapping": None}, None)
    assert [(t["amount_minor"], t["category"], t["duplicate"]) for t in p["transactions"]] == [
        (26271, "Groceries", False),
        (-10000, "Shopping", False),
    ]
    assert (p["new_count"], p["duplicate_count"]) == (2, 0)
    assert axel.get("/transactions").json() == []
    assert axel.get(f"/accounts/{account}/imports").json() == []


def test_preview_guesses_mapping_for_unknown_bank(axel, account):
    p = preview(axel, account, BANK_CSV).json()
    assert p["source"] == "guessed"
    assert p["columns"] == ["Bokföringsdag", "Text", "Belopp", "Saldo"]
    assert p["sample_rows"][0] == ["2025-07-02", "ICA NARA", "-262,71", "9 737,29"]
    assert p["config"]["mapping"]["amount_column"] == "Belopp"
    assert [t["amount_minor"] for t in p["transactions"]] == [26271, -2500000]


def test_preview_reports_unusable_config_instead_of_failing(axel, account):
    bad = {"importer": "csv", "mapping": {**BANK_CONFIG["mapping"], "amount_column": "Saldo", "date_column": "Text"}}
    p = preview(axel, account, BANK_CSV, bad).json()
    assert p["error"].startswith("Line 3: Unrecognized date")
    assert p["transactions"] == []
    assert p["suggested_mapping"]["date_column"] == "Bokföringsdag"  # to help fix it


def test_preview_without_any_usable_columns(axel, account):
    p = preview(axel, account, b"x;y\nfoo;bar\n").json()
    assert (p["source"], p["config"]) == ("none", None)
    assert "choose them" in p["error"]
    r = confirm(axel, account, b"x;y\nfoo;bar\n")
    assert r.status_code == 400


def test_confirm_saves_config_so_next_upload_is_automatic(axel, account):
    mapping = {**BANK_CONFIG["mapping"], "spending_is_negative": False}  # an odd bank
    r = confirm(axel, account, BANK_CSV, {"importer": "csv", "mapping": mapping})
    assert r.status_code == 201, r.text
    assert (r.json()["importer"], r.json()["transaction_count"]) == ("csv", 2)
    assert axel.get("/accounts").json()[0]["import_config"]["mapping"]["spending_is_negative"] is False

    # Next month's file: no config sent, the saved one is used.
    p = preview(axel, account, BANK_CSV.replace(b"2025-07", b"2025-08")).json()
    assert p["source"] == "saved"
    assert [t["amount_minor"] for t in p["transactions"]] == [-26271, 2500000]


def test_preview_marks_duplicates_and_previous_upload(axel, account):
    confirm(axel, account, AMEX_CSV)
    p = preview(axel, account, AMEX_CSV).json()
    assert [t["duplicate"] for t in p["transactions"]] == [True, True]
    assert (p["new_count"], p["duplicate_count"]) == (0, 2)
    assert p["already_imported_at"] is not None

    overlapping = AMEX_CSV + b'07/02/2025,NEW ROW,"1,00"\n'
    p = preview(axel, account, overlapping).json()
    assert [t["duplicate"] for t in p["transactions"]] == [True, True, False]
    assert p["already_imported_at"] is None  # a different file


def test_invalid_config_json_is_422(axel, account):
    r = axel.post(
        f"/accounts/{account}/imports/preview",
        files={"file": ("x.csv", AMEX_CSV, "text/csv")},
        data={"config": '{"importer": "csv", "mapping": {"decimal_separator": ";"}}'},
    )
    assert r.status_code == 422


def test_unknown_importer_is_reported(axel, account):
    p = preview(axel, account, AMEX_CSV, {"importer": "nordea_pdf"}).json()
    assert "Unknown importer" in p["error"]


def test_empty_file_is_400(axel, account):
    assert preview(axel, account, b"").status_code == 400


def test_history_and_undo(axel, account):
    first = confirm(axel, account, AMEX_CSV, name="june.csv").json()
    axel.post(f"/accounts/{account}/transactions", json={"description": "Manual", "amount": 5})
    history = axel.get(f"/accounts/{account}/imports").json()
    assert [(h["filename"], h["period_start"], h["period_end"]) for h in history] == [
        ("june.csv", "2025-06-28", "2025-07-01")
    ]

    assert axel.delete(f"/accounts/{account}/imports/{first['id']}").status_code == 204
    assert [t["description"] for t in axel.get("/transactions").json()] == ["Manual"]
    assert axel.get(f"/accounts/{account}/imports").json() == []
    assert axel.delete(f"/accounts/{account}/imports/{first['id']}").status_code == 404
    # Undone rows are no longer duplicates.
    assert confirm(axel, account, AMEX_CSV).json()["transaction_count"] == 2


def test_import_routes_are_owner_only(couple, axel, ebba, login):
    _, account_id = couple
    imp = confirm(axel, account_id, AMEX_CSV).json()
    # A household member sees the history but can't import or undo.
    assert len(ebba.get(f"/accounts/{account_id}/imports").json()) == 1
    assert preview(ebba, account_id, AMEX_CSV).status_code == 403
    assert confirm(ebba, account_id, AMEX_CSV).status_code == 403
    assert ebba.delete(f"/accounts/{account_id}/imports/{imp['id']}").status_code == 403
    # An outsider sees nothing.
    mallory = login("mallory")
    assert mallory.get(f"/accounts/{account_id}/imports").status_code == 404
    assert preview(mallory, account_id, AMEX_CSV).status_code == 404
    assert mallory.delete(f"/accounts/{account_id}/imports/{imp['id']}").status_code == 404


def test_cannot_undo_another_accounts_import_through_own_account(axel, account):
    other = axel.post("/accounts", json={"name": "Other"}).json()["id"]
    imp = confirm(axel, other, AMEX_CSV).json()
    assert axel.delete(f"/accounts/{account}/imports/{imp['id']}").status_code == 404
