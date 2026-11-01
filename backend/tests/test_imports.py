import json

import pytest

from tests.test_api import AMEX_CSV, add, upload, user_id

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


# Statement periods: an upload counts toward the month it ends in

STATEMENT_CSV = (
    "Bokföringsdag;Text;Belopp;Saldo\n"
    "2025-09-27;ICA NARA;-100,00;0\n"
    "2025-10-10;SL;-200,00;0\n"
    "2025-10-27;COOP;-400,00;0\n"
).encode("cp1252")


def test_an_upload_counts_toward_the_month_it_ends_in(couple, axel, ebba):
    household_id, account_id = couple
    assert preview(axel, account_id, STATEMENT_CSV, BANK_CONFIG).json()["period"] == "2025-10"
    imp = confirm(axel, account_id, STATEMENT_CSV, BANK_CONFIG).json()
    assert imp["period"] == "2025-10"
    september = {"month": "2025-09"}
    october = {"month": "2025-10"}

    # 27 September is on October's statement, so it counts toward October.
    assert ebba.get(f"/households/{household_id}/settlement", params=september).json()["shared_minor"] == 0
    assert ebba.get(f"/households/{household_id}/settlement", params=october).json()["shared_minor"] == 70000
    summary = ebba.get("/summary", params=october | {"household_id": household_id}).json()
    assert summary["spent_minor"] == 70000

    # A transaction added by hand counts toward the month it was booked in.
    add(axel, account_id, 50, "Cash", booked_on="2025-09-28")
    assert ebba.get(f"/households/{household_id}/settlement", params=september).json()["shared_minor"] == 5000


def test_an_upload_can_move_to_another_month(couple, axel, ebba):
    household_id, account_id = couple
    imp = confirm(axel, account_id, STATEMENT_CSV, BANK_CONFIG).json()
    url = f"/accounts/{account_id}/imports/{imp['id']}"

    r = axel.patch(url, json={"period": "2025-11"})
    assert r.status_code == 200 and r.json()["period"] == "2025-11"
    settlement = ebba.get(f"/households/{household_id}/settlement", params={"month": "2025-11"}).json()
    assert settlement["shared_minor"] == 70000

    assert axel.patch(url, json={"period": "2025-13"}).status_code == 422
    assert ebba.patch(url, json={"period": "2025-10"}).status_code in (403, 404)  # not her account


# Going through a statement


def test_reviewing_a_statement(couple, axel, ebba):
    household_id, account_id = couple
    axel.patch(f"/accounts/{account_id}", json={"kind": "credit"})
    imp = confirm(axel, account_id, STATEMENT_CSV, BANK_CONFIG).json()
    review_url = f"/accounts/{account_id}/imports/{imp['id']}/review"

    review = ebba.get(review_url).json()  # a household member can go through it too
    assert (review["total_count"], review["checked_count"], review["account_kind"]) == (3, 0, "credit")
    assert {s["display_name"]: s["amount_minor"] for s in review["split"]["shares"]} == {"axel": 35000, "ebba": 35000}

    rows = ebba.get("/transactions", params={"import_id": imp["id"]}).json()
    assert len(rows) == 3 and not any(t["reviewed"] for t in rows)
    shoes, *rest = sorted(rows, key=lambda t: t["amount_minor"])  # the 100 kr line
    # Saying whose it is checks it; confirming one as it is checks it too.
    r = ebba.patch("/transactions", json=[{"id": shoes["id"], "member_id": user_id(ebba)}, {"id": rest[0]["id"], "reviewed": True}])
    assert [t["reviewed"] for t in r.json()] == [True, True]
    # A category alone doesn't.
    ebba.patch("/transactions", json=[{"id": rest[1]["id"], "category": "Travel"}])

    review = ebba.get(review_url).json()
    assert review["checked_count"] == 2
    assert {s["display_name"]: s["amount_minor"] for s in review["split"]["shares"]} == {"axel": 30000, "ebba": 40000}

    settlement = ebba.get(f"/households/{household_id}/settlement", params={"month": "2025-10"}).json()
    assert [(u["account_name"], u["import_id"], u["period"], u["count"]) for u in settlement["unchecked"]] == [
        ("Amex", imp["id"], "2025-10", 1)
    ]


def test_added_by_hand_is_already_checked(couple, axel):
    _, account_id = couple
    assert add(axel, account_id, 10)["reviewed"] is True
