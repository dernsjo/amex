from app import models

AMEX_CSV = (
    "Datum,Beskrivning,Belopp\n"
    '07/01/2025,HEMKOP SABIS STOCKHO 09   STOCKHOLM,"262,71"\n'
    '06/28/2025,RETUR ZARA,"−100,00"\n'
).encode("utf-8")


def upload(client, account_id, content=AMEX_CSV, name="activity.csv"):
    return client.post(f"/accounts/{account_id}/imports", files={"file": (name, content, "text/csv")})


def add(client, account_id, amount, description="Test", **fields):
    r = client.post(
        f"/accounts/{account_id}/transactions", json={"description": description, "amount": amount, **fields}
    )
    assert r.status_code == 201, r.text
    return r.json()


def user_id(client):
    return client.get("/me").json()["id"]


# A user on their own: no household needed


def test_solo_user_flow(axel):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    assert account["owner"]["display_name"] == "axel"
    assert account["household_id"] is None
    assert [m["display_name"] for m in account["members"]] == ["axel"]

    t = add(axel, account["id"], 12.345, "ICA NARA")
    assert (t["amount_minor"], t["category"]) == (1235, "Groceries")
    # Unshared spending is the owner's own.
    assert (t["allocation"], t["member_id"]) == ("personal", user_id(axel))


def test_empty_lists_are_not_404(axel):
    assert axel.get("/accounts").json() == []
    assert axel.get("/transactions").json() == []


def test_more_than_100_transactions_are_returned(axel):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    for _ in range(101):
        add(axel, account["id"], 1)
    assert len(axel.get("/transactions").json()) == 101


# Imports


def test_upload_parses_amex_and_categorizes(axel):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    r = upload(axel, account["id"])
    assert r.status_code == 201, r.text
    assert (r.json()["transaction_count"], r.json()["duplicate_count"]) == (2, 0)

    rows = sorted(axel.get("/transactions").json(), key=lambda t: t["booked_on"])
    assert [(t["booked_on"], t["amount_minor"], t["category"]) for t in rows] == [
        ("2025-06-28", -10000, "Shopping"),  # Unicode minus used to become 0.0
        ("2025-07-01", 26271, "Groceries"),
    ]
    assert rows[1]["description"] == "HEMKOP SABIS STOCKHO 09 STOCKHOLM"
    assert {t["import_id"] for t in rows} == {r.json()["id"]}


def test_uploading_the_same_file_twice_adds_nothing(axel):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    upload(axel, account["id"])
    r = upload(axel, account["id"])
    assert (r.json()["transaction_count"], r.json()["duplicate_count"]) == (0, 2)
    assert len(axel.get("/transactions").json()) == 2


def test_upload_rejects_non_amex_file(axel):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    r = upload(axel, account["id"], b"a,b\n1,2\n", "x.csv")
    assert r.status_code == 400
    assert "missing column" in r.json()["detail"]


def test_upload_into_shared_account_defaults_to_shared(couple, axel):
    _, account_id = couple
    upload(axel, account_id)
    assert {(t["allocation"], t["member_id"]) for t in axel.get("/transactions").json()} == {("shared", None)}


# Households


def test_both_members_see_the_same_household(couple, axel, ebba):
    household_id, account_id = couple
    assert axel.get(f"/households/{household_id}").json() == ebba.get(f"/households/{household_id}").json()
    assert [h["role"] for h in axel.get("/me").json()["households"]] == ["owner"]
    assert [h["role"] for h in ebba.get("/me").json()["households"]] == ["member"]

    add(axel, account_id, 100, "ICA")
    assert axel.get(f"/transactions?household_id={household_id}").json() == ebba.get(
        f"/transactions?household_id={household_id}"
    ).json()


def test_add_member_requires_a_signed_in_user(axel):
    hh = axel.post("/households", json={"name": "Home"}).json()
    r = axel.post(f"/households/{hh['id']}/members", json={"email": "nobody@example.com"})
    assert r.status_code == 404
    assert "sign in" in r.json()["detail"]


def test_add_member_twice_conflicts(couple, axel):
    household_id, _ = couple
    r = axel.post(f"/households/{household_id}/members", json={"email": "EBBA@example.com"})
    assert r.status_code == 409


def test_only_owners_manage_the_household(couple, ebba, axel):
    household_id, _ = couple
    axel_id = user_id(axel)
    assert ebba.patch(f"/households/{household_id}", json={"name": "Ebba's"}).status_code == 403
    assert ebba.patch(f"/households/{household_id}/members/{axel_id}", json={"split_weight": 0}).status_code == 403
    assert ebba.delete(f"/households/{household_id}/members/{axel_id}").status_code == 403


def test_last_owner_cannot_leave_others_behind(couple, axel, ebba):
    household_id, _ = couple
    axel_id, ebba_id = user_id(axel), user_id(ebba)
    assert axel.delete(f"/households/{household_id}/members/{axel_id}").status_code == 409
    assert axel.patch(f"/households/{household_id}/members/{axel_id}", json={"role": "member"}).status_code == 409

    assert axel.patch(f"/households/{household_id}/members/{ebba_id}", json={"role": "owner"}).status_code == 200
    assert axel.delete(f"/households/{household_id}/members/{axel_id}").status_code == 204
    assert [m["display_name"] for m in ebba.get(f"/households/{household_id}").json()["members"]] == ["ebba"]


def test_last_member_leaving_deletes_household(axel):
    hh = axel.post("/households", json={"name": "Solo"}).json()
    account = axel.post("/accounts", json={"name": "Amex", "household_id": hh["id"]}).json()
    assert axel.delete(f"/households/{hh['id']}/members/{user_id(axel)}").status_code == 204
    assert axel.get("/me").json()["households"] == []
    assert axel.get("/accounts").json()[0]["id"] == account["id"]  # the account survives, unshared


# Editing transactions


def test_patch_allocation_member_and_category(couple, axel, ebba):
    _, account_id = couple
    t = add(axel, account_id, 100, "ICA NARA")
    ebba_id = user_id(ebba)

    # Ebba marks an exception on Axel's card: it was her personal purchase.
    r = ebba.patch("/transactions", json=[{"id": t["id"], "member_id": ebba_id}])
    assert r.status_code == 200
    assert (r.json()[0]["allocation"], r.json()[0]["member_id"]) == ("personal", ebba_id)

    r = ebba.patch("/transactions", json=[{"id": t["id"], "allocation": "shared", "category": "Eating out"}])
    assert (r.json()[0]["allocation"], r.json()[0]["member_id"], r.json()[0]["category"]) == (
        "shared",
        None,
        "Eating out",
    )


def test_patch_personal_without_member_defaults_to_owner(couple, axel):
    _, account_id = couple
    t = add(axel, account_id, 100)
    r = axel.patch("/transactions", json=[{"id": t["id"], "allocation": "personal"}])
    assert r.json()[0]["member_id"] == user_id(axel)


def test_patch_validates_and_is_all_or_nothing(couple, axel):
    _, account_id = couple
    a, b = add(axel, account_id, 100), add(axel, account_id, 200)
    assert axel.patch("/transactions", json=[{"id": a["id"], "category": "Nope"}]).status_code == 422
    assert axel.patch("/transactions", json=[{"id": a["id"], "allocation": "nope"}]).status_code == 422
    assert axel.patch("/transactions", json=[{"id": a["id"]}]).status_code == 422
    assert axel.patch("/transactions", json=[{"id": 999, "category": "Other"}]).status_code == 404

    r = axel.patch(
        "/transactions",
        json=[{"id": a["id"], "allocation": "excluded"}, {"id": b["id"], "category": "Nope"}],
    )
    assert r.status_code == 422
    assert {t["allocation"] for t in axel.get("/transactions").json()} == {"shared"}


def test_create_validates_category_and_member(couple, axel, login):
    _, account_id = couple
    r = axel.post(f"/accounts/{account_id}/transactions", json={"description": "x", "amount": 1, "category": "Nope"})
    assert r.status_code == 422
    stranger = user_id(login("stranger"))
    r = axel.post(f"/accounts/{account_id}/transactions", json={"description": "x", "amount": 1, "member_id": stranger})
    assert r.status_code == 422


def test_delete_transaction(couple, axel, ebba):
    _, account_id = couple
    t = add(axel, account_id, 100)
    assert ebba.delete(f"/transactions/{t['id']}").status_code == 403
    assert axel.delete(f"/transactions/{t['id']}").status_code == 204
    assert axel.delete(f"/transactions/{t['id']}").status_code == 404


def test_category_options(axel):
    categories = axel.get("/categories").json()
    assert "Groceries" in categories and "Other" in categories


# Settlement


def test_settlement_matches_poc(couple, axel, ebba):
    household_id, account_id = couple
    axel_id, ebba_id = user_id(axel), user_id(ebba)
    add(axel, account_id, 1000)
    add(axel, account_id, 200, member_id=axel_id)
    add(axel, account_id, 50, member_id=ebba_id)
    add(axel, account_id, 300, allocation="outlay")
    add(axel, account_id, 999, allocation="excluded")
    axel.post("/accounts", json={"name": "Private"})  # unshared accounts don't count

    r = ebba.get(f"/households/{household_id}/settlement")
    assert r.status_code == 200
    assert r.json() == {
        "household_id": household_id,
        "per_member": [
            {"user_id": axel_id, "display_name": "axel", "amount_minor": 70000},
            {"user_id": ebba_id, "display_name": "ebba", "amount_minor": 55000},
        ],
        "outlay_minor": 30000,
        "shared_minor": 100000,
        "total_minor": 155000,
    }


def test_settlement_uses_split_weights(couple, axel, ebba):
    household_id, account_id = couple
    axel.patch(f"/households/{household_id}/members/{user_id(axel)}", json={"split_weight": 3})
    axel.patch(f"/households/{household_id}/members/{user_id(ebba)}", json={"split_weight": 2})
    add(axel, account_id, 1000)
    shares = [m["amount_minor"] for m in axel.get(f"/households/{household_id}/settlement").json()["per_member"]]
    assert shares == [60000, 40000]


def test_settlement_flags_personal_spending_of_former_member(couple, axel, ebba):
    household_id, account_id = couple
    ebba_id = user_id(ebba)
    add(axel, account_id, 50, member_id=ebba_id)
    ebba.delete(f"/households/{household_id}/members/{ebba_id}")
    r = axel.get(f"/households/{household_id}/settlement")
    assert r.status_code == 409
    assert "isn't a member" in r.json()["detail"]


def test_deleting_account_deletes_its_transactions_and_imports(axel, db_session):
    account = axel.post("/accounts", json={"name": "Amex"}).json()
    upload(axel, account["id"])
    assert axel.delete(f"/accounts/{account['id']}").status_code == 204
    with db_session() as db:
        assert db.query(models.Transaction).count() == 0
        assert db.query(models.Import).count() == 0
