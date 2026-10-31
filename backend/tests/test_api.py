AMEX_CSV = (
    "Datum,Beskrivning,Belopp\n"
    '07/01/2025,HEMKOP SABIS STOCKHO 09   STOCKHOLM,"262,71"\n'
    '06/28/2025,RETUR ZARA,"−100,00"\n'
).encode("utf-8")


def add(client, amount, paid_by="Split", description="Test"):
    r = client.post("/expenses", json={"description": description, "amount": amount, "paid_by": paid_by})
    assert r.status_code == 201, r.text
    return r.json()


def test_empty_expense_list_is_not_404(client):
    r = client.get("/expenses")
    assert r.status_code == 200
    assert r.json() == []


def test_more_than_100_expenses_are_returned(household):
    for _ in range(101):
        add(household, 1)
    assert len(household.get("/expenses").json()) == 101


def test_upload_parses_amex_and_categorizes(household):
    r = household.post("/expenses/upload", files={"file": ("activity.csv", AMEX_CSV, "text/csv")})
    assert r.status_code == 201, r.text
    rows = sorted(r.json(), key=lambda e: e["date"])
    assert [(e["date"], e["amount"], e["category"]) for e in rows] == [
        ("2025-06-28", -100.0, "Shopping"),  # Unicode minus used to become 0.0
        ("2025-07-01", 262.71, "Groceries"),
    ]


def test_upload_rejects_non_amex_file(client):
    r = client.post("/expenses/upload", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert r.status_code == 400
    assert "missing column" in r.json()["detail"]


def test_settlement_matches_poc(household):
    add(household, 1000)
    add(household, 200, "Axel")
    add(household, 50, "Ebba")
    add(household, 300, "Outlay")
    add(household, 999, "Exclude")
    r = household.get("/expenses/settlement")
    assert r.status_code == 200
    assert r.json() == {"per_member": {"Axel": 700.0, "Ebba": 550.0}, "outlay": 300.0, "shared": 1000.0, "total": 1550.0}


def test_settlement_requires_users(client):
    add(client, 100)
    assert client.get("/expenses/settlement").status_code == 409


def test_patch_paid_by_validates(household):
    e = add(household, 100)
    assert household.patch("/expenses", json=[{"id": e["id"], "paid_by": "Nobody"}]).status_code == 422
    assert household.patch("/expenses", json=[{"id": 999, "paid_by": "Axel"}]).status_code == 404
    r = household.patch("/expenses", json=[{"id": e["id"], "paid_by": "Axel"}])
    assert r.status_code == 200
    assert r.json()[0]["paid_by"] == "Axel"


def test_patch_category(client):
    e = add(client, 100, description="ICA NARA")
    assert e["category"] == "Groceries"
    r = client.patch("/expenses", json=[{"id": e["id"], "category": "Eating out"}])
    assert r.status_code == 200
    assert (r.json()[0]["category"], r.json()[0]["paid_by"]) == ("Eating out", "Split")  # paid_by untouched
    assert client.patch("/expenses", json=[{"id": e["id"], "category": "Nope"}]).status_code == 422
    assert client.patch("/expenses", json=[{"id": e["id"]}]).status_code == 422  # nothing to update


def test_category_options_and_explicit_category_on_create(client):
    categories = client.get("/expenses/categories").json()
    assert "Groceries" in categories and "Other" in categories
    r = client.post("/expenses", json={"description": "ICA", "amount": 1, "category": "Other"})
    assert r.json()["category"] == "Other"
    r = client.post("/expenses", json={"description": "ICA", "amount": 1, "category": "Nope"})
    assert r.status_code == 422


def test_delete_expense(client):
    e = add(client, 100)
    assert client.delete(f"/expenses/{e['id']}").status_code == 204
    assert client.delete(f"/expenses/{e['id']}").status_code == 404


def test_amount_rounding_and_default_category(client):
    e = add(client, 12.345, description="ICA NARA")
    assert e["amount"] == 12.35
    assert e["category"] == "Groceries"


def test_users(client):
    assert client.post("/users", json={"name": "Axel"}).status_code == 201
    assert client.post("/users", json={"name": "Axel"}).status_code == 409
    assert client.post("/users", json={"name": "split"}).status_code == 422
    assert "Axel" in client.get("/expenses/paid-by-options").json()


def test_cannot_delete_user_with_personal_expenses(household):
    axel = next(u for u in household.get("/users").json() if u["name"] == "Axel")
    add(household, 100, "Axel")
    assert household.delete(f"/users/{axel['id']}").status_code == 409


def test_deleted_user_can_be_recreated(household):
    ebba = next(u for u in household.get("/users").json() if u["name"] == "Ebba")
    assert household.delete(f"/users/{ebba['id']}").status_code == 204
    assert [u["name"] for u in household.get("/users").json()] == ["Axel"]
    assert household.post("/users", json={"name": "Ebba"}).status_code == 201
