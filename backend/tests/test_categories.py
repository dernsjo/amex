from spending_core import DEFAULT_CATEGORIES

from tests.test_api import add, user_id


def names(client, household_id=None):
    params = {"household_id": household_id} if household_id else {}
    return [c["name"] for c in client.get("/categories", params=params).json()]


def category_id(client, name, household_id=None):
    params = {"household_id": household_id} if household_id else {}
    return next(c["id"] for c in client.get("/categories", params=params).json() if c["name"] == name)


def solo_account(client):
    return client.post("/accounts", json={"name": "Debit"}).json()["id"]


# Categories


def test_each_scope_starts_with_the_defaults(couple, axel, ebba):
    household_id, _ = couple
    assert names(axel) == DEFAULT_CATEGORIES
    assert names(axel, household_id) == DEFAULT_CATEGORIES
    assert names(ebba, household_id) == DEFAULT_CATEGORIES
    fallback = [c for c in axel.get("/categories").json() if c["is_fallback"]]
    assert [c["name"] for c in fallback] == ["Other"]


def test_scopes_are_separate(couple, axel, ebba):
    household_id, _ = couple
    assert axel.post("/categories", json={"name": "Golf"}).status_code == 201
    assert ebba.post("/categories", params={"household_id": household_id}, json={"name": "Kids"}).status_code == 201
    assert "Golf" in names(axel) and "Golf" not in names(axel, household_id)
    assert "Kids" in names(axel, household_id) and "Kids" not in names(axel) and "Kids" not in names(ebba)


def test_duplicate_names_conflict_case_insensitively(axel):
    names(axel)
    assert axel.post("/categories", json={"name": "groceries"}).status_code == 409
    other = category_id(axel, "Other")
    assert axel.patch(f"/categories/{other}", json={"name": "TRAVEL"}).status_code == 409


def test_rename_carries_transactions_rules_and_budgets(axel):
    account_id = solo_account(axel)
    t = add(axel, account_id, 100, "HEMKOP")
    axel.post("/category-rules", json={"pattern": "willys", "category": "Groceries"})
    axel.put("/budgets", json={"category": "Groceries", "amount_minor": 500000})

    groceries = category_id(axel, "Groceries")
    assert axel.patch(f"/categories/{groceries}", json={"name": "Food"}).json()["name"] == "Food"

    assert axel.get("/transactions").json()[0]["category"] == "Food"
    assert [r["category"] for r in axel.get("/category-rules").json()] == ["Food"]
    line = next(x for x in axel.get("/budgets", params={"month": t["booked_on"][:7]}).json()["lines"] if x["category"] == "Food")
    assert (line["target_minor"], line["spent_minor"]) == (500000, 10000)
    # The default keywords still find the renamed category.
    assert add(axel, account_id, 1, "ICA NARA")["category"] == "Food"


def test_delete_recategorizes_and_fallback_stays(axel):
    account_id = solo_account(axel)
    add(axel, account_id, 100, "PIZZERIA NAPOLI")
    eating_out = category_id(axel, "Eating out")
    assert axel.delete(f"/categories/{eating_out}").status_code == 204
    assert axel.get("/transactions").json()[0]["category"] == "Other"
    assert add(axel, account_id, 1, "SUSHI BAR")["category"] == "Other"
    assert axel.delete(f"/categories/{category_id(axel, 'Other')}").status_code == 409


# Rules


def test_rule_applies_to_new_and_existing_but_not_manual_choices(axel):
    account_id = solo_account(axel)
    auto = add(axel, account_id, 100, "SYSTEMBOLAGET 123")
    manual = add(axel, account_id, 100, "SYSTEMBOLAGET 456", category="Shopping")
    assert auto["category"] == "Other"

    r = axel.post("/category-rules", json={"pattern": "  systembolaget ", "category": "eating out"})
    assert r.status_code == 201, r.text
    assert r.json()["rule"] == {"id": r.json()["rule"]["id"], "pattern": "systembolaget", "category": "Eating out"}
    assert r.json()["recategorized"] == 1

    by_id = {t["id"]: t["category"] for t in axel.get("/transactions").json()}
    assert by_id == {auto["id"]: "Eating out", manual["id"]: "Shopping"}
    assert add(axel, account_id, 1, "Systembolaget Odenplan")["category"] == "Eating out"
    preview = axel.post(
        f"/accounts/{account_id}/imports/preview",
        files={"file": ("a.csv", b"Datum,Beskrivning,Belopp\n2025-07-01,SYSTEMBOLAGET,\"1,00\"\n", "text/csv")},
    )
    assert preview.json()["transactions"][0]["category"] == "Eating out"


def test_same_pattern_updates_the_rule_and_deleting_reverts(axel):
    account_id = solo_account(axel)
    add(axel, account_id, 100, "SYSTEMBOLAGET")
    axel.post("/category-rules", json={"pattern": "systembolaget", "category": "Shopping"})
    rule = axel.post("/category-rules", json={"pattern": "SYSTEMBOLAGET", "category": "Eating out"}).json()["rule"]
    assert len(axel.get("/category-rules").json()) == 1
    assert axel.delete(f"/category-rules/{rule['id']}").status_code == 204
    assert axel.get("/transactions").json()[0]["category"] == "Other"


def test_rule_needs_an_existing_category(axel):
    assert axel.post("/category-rules", json={"pattern": "foo", "category": "Nope"}).status_code == 422


def test_correcting_a_category_marks_it_manual(couple, axel, ebba):
    household_id, account_id = couple
    t = add(axel, account_id, 100, "SYSTEMBOLAGET")
    ebba.patch("/transactions", json=[{"id": t["id"], "category": "Shopping"}])
    ebba.post("/category-rules", params={"household_id": household_id}, json={"pattern": "systembolaget", "category": "Eating out"})
    assert axel.get("/transactions").json()[0]["category"] == "Shopping"


def test_shared_accounts_use_household_categories(couple, axel, ebba):
    household_id, account_id = couple
    ebba.post("/categories", params={"household_id": household_id}, json={"name": "Kids"})
    assert add(axel, account_id, 1, "x", category="Kids")["category"] == "Kids"
    # Axel's own categories don't apply to the shared account, and vice versa.
    axel.post("/categories", json={"name": "Golf"})
    assert axel.post(
        f"/accounts/{account_id}/transactions", json={"description": "x", "amount": 1, "category": "Golf"}
    ).status_code == 422
    assert add(axel, solo_account(axel), 1, "x", category="Golf")["category"] == "Golf"


def test_sharing_an_account_switches_its_rules(couple, axel):
    household_id, _ = couple
    account_id = solo_account(axel)
    axel.post("/category-rules", json={"pattern": "systembolaget", "category": "Eating out"})
    t = add(axel, account_id, 100, "SYSTEMBOLAGET")
    assert t["category"] == "Eating out"
    axel.patch(f"/accounts/{account_id}", json={"household_id": household_id})
    assert axel.get("/transactions", params={"account_id": account_id}).json()[0]["category"] == "Other"


# Budgets


def test_budget_targets_and_overrides(axel):
    account_id = solo_account(axel)
    add(axel, account_id, 300, "ICA", booked_on="2025-07-10")
    add(axel, account_id, 50, "ICA", booked_on="2025-08-01")
    add(axel, account_id, 999, "Excluded ICA", booked_on="2025-07-11", allocation="excluded")
    assert axel.put("/budgets", json={"category": "Groceries", "amount_minor": 400000}).status_code == 204
    assert axel.put("/budgets", json={"category": "groceries", "month": "2025-07", "amount_minor": 600000}).status_code == 204

    july = axel.get("/budgets", params={"month": "2025-07"}).json()
    groceries = july["lines"][0]
    assert groceries == {
        "category": "Groceries",
        "recurring_minor": 400000,
        "override_minor": 600000,
        "target_minor": 600000,
        "spent_minor": 30000,
    }
    assert (july["target_minor"], july["spent_minor"]) == (600000, 30000)
    assert [x["category"] for x in july["lines"]] == DEFAULT_CATEGORIES

    august = axel.get("/budgets", params={"month": "2025-08"}).json()["lines"][0]
    assert (august["target_minor"], august["spent_minor"]) == (400000, 5000)

    axel.put("/budgets", json={"category": "Groceries", "month": "2025-07", "amount_minor": None})
    assert axel.get("/budgets", params={"month": "2025-07"}).json()["lines"][0]["target_minor"] == 400000


def test_budget_validation(axel):
    assert axel.put("/budgets", json={"category": "Nope", "amount_minor": 1}).status_code == 422
    assert axel.put("/budgets", json={"category": "Groceries", "amount_minor": -1}).status_code == 422
    assert axel.put("/budgets", json={"category": "Groceries", "month": "2025-13", "amount_minor": 1}).status_code == 422
    assert axel.get("/budgets", params={"month": "July"}).status_code == 422


def test_household_budget_counts_shared_and_mine_counts_my_share(couple, axel, ebba):
    household_id, account_id = couple
    axel_id, ebba_id = user_id(axel), user_id(ebba)
    axel.patch(f"/households/{household_id}/members/{axel_id}", json={"split_weight": 3})
    axel.patch(f"/households/{household_id}/members/{ebba_id}", json={"split_weight": 1})
    day = "2025-07-15"
    add(axel, account_id, 1000, "ICA", booked_on=day)  # shared
    add(axel, account_id, 200, "ICA", booked_on=day, member_id=ebba_id)  # Ebba's own
    add(axel, account_id, 100, "ICA", booked_on=day, allocation="outlay")
    add(axel, solo_account(axel), 40, "ICA", booked_on=day)  # Axel's unshared card

    def spent(client, household=None):
        params = {"month": "2025-07"} | ({"household_id": household} if household else {})
        return client.get("/budgets", params=params).json()["lines"][0]["spent_minor"]

    assert spent(axel, household_id) == spent(ebba, household_id) == 100000
    assert spent(axel) == 75000 + 4000
    assert spent(ebba) == 25000 + 20000


# Isolation


def test_outsider_cannot_touch_household_categories(couple, axel, login):
    household_id, _ = couple
    mallory = login("mallory")
    hh = {"household_id": household_id}
    groceries = category_id(axel, "Groceries", household_id)
    assert mallory.get("/categories", params=hh).status_code == 404
    assert mallory.post("/categories", params=hh, json={"name": "x"}).status_code == 404
    assert mallory.get("/category-rules", params=hh).status_code == 404
    assert mallory.get("/budgets", params=hh | {"month": "2025-07"}).status_code == 404
    assert mallory.put("/budgets", params=hh, json={"category": "Groceries", "amount_minor": 1}).status_code == 404
    # Ids from someone else's scope aren't found in your own.
    assert mallory.patch(f"/categories/{groceries}", json={"name": "Mine"}).status_code == 404
    assert mallory.delete(f"/categories/{groceries}").status_code == 404
    rule = axel.post("/category-rules", params=hh, json={"pattern": "ica", "category": "Groceries"}).json()["rule"]
    assert mallory.delete(f"/category-rules/{rule['id']}").status_code == 404
    assert names(axel, household_id) == DEFAULT_CATEGORIES


def test_own_categories_are_private(couple, axel, ebba):
    axel.post("/categories", json={"name": "Golf"})
    golf = category_id(axel, "Golf")
    assert "Golf" not in names(ebba)
    assert ebba.delete(f"/categories/{golf}").status_code == 404
