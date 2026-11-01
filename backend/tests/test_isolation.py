"""The most important tests in the codebase: nobody sees data they shouldn't.

Mallory is a signed-in user with no relation to Axel or Ebba.
"""

import pytest

AMEX_CSV = b'Datum,Beskrivning,Belopp\n07/01/2025,ICA NARA,"100,00"\n'


@pytest.fixture
def mallory(login):
    return login("mallory")


@pytest.fixture
def private_account(axel):
    """An account Axel has not shared, with one transaction."""
    account = axel.post("/accounts", json={"name": "Private"}).json()
    t = axel.post(f"/accounts/{account['id']}/transactions", json={"description": "Gift", "amount": 500}).json()
    return account["id"], t["id"]


def test_outsider_sees_nothing(couple, private_account, mallory):
    assert mallory.get("/accounts").json() == []
    assert mallory.get("/transactions").json() == []
    assert mallory.get("/me").json()["households"] == []


def test_outsider_gets_404_for_every_household_and_account_route(couple, axel, mallory):
    household_id, account_id = couple
    t = axel.post(f"/accounts/{account_id}/transactions", json={"description": "ICA", "amount": 100}).json()

    for method, url, kwargs in [
        ("get", f"/households/{household_id}", {}),
        ("patch", f"/households/{household_id}", {"json": {"name": "Mine now"}}),
        ("post", f"/households/{household_id}/members", {"json": {"email": "mallory@example.com"}}),
        ("patch", f"/households/{household_id}/members/1", {"json": {"split_weight": 0}}),
        ("delete", f"/households/{household_id}/members/1", {}),
        ("get", f"/households/{household_id}/settlement", {}),
        ("get", f"/transactions?household_id={household_id}", {}),
        ("get", f"/transactions?account_id={account_id}", {}),
        ("patch", f"/accounts/{account_id}", {"json": {"name": "Mine now"}}),
        ("delete", f"/accounts/{account_id}", {}),
        ("post", f"/accounts/{account_id}/transactions", {"json": {"description": "x", "amount": 1}}),
        ("post", f"/accounts/{account_id}/imports", {"files": {"file": ("a.csv", AMEX_CSV, "text/csv")}}),
        ("patch", "/transactions", {"json": [{"id": t["id"], "allocation": "excluded"}]}),
        ("delete", f"/transactions/{t['id']}", {}),
    ]:
        r = getattr(mallory, method)(url, **kwargs)
        assert r.status_code == 404, f"{method.upper()} {url} -> {r.status_code}"

    # And nothing changed.
    assert axel.get(f"/households/{household_id}").json()["name"] == "Axel & Ebba"
    assert axel.get("/transactions").json()[0]["allocation"] == "shared"


def test_outsider_cannot_share_own_account_into_foreign_household(couple, mallory):
    household_id, _ = couple
    r = mallory.post("/accounts", json={"name": "Trojan", "household_id": household_id})
    assert r.status_code == 404
    account = mallory.post("/accounts", json={"name": "Trojan"}).json()
    assert mallory.patch(f"/accounts/{account['id']}", json={"household_id": household_id}).status_code == 404


def test_household_member_does_not_see_unshared_accounts(couple, private_account, ebba):
    _, shared_id = couple
    private_id, private_tx = private_account
    assert [a["id"] for a in ebba.get("/accounts").json()] == [shared_id]
    assert ebba.get(f"/transactions?account_id={private_id}").status_code == 404
    assert ebba.patch("/transactions", json=[{"id": private_tx, "category": "Other"}]).status_code == 404


def test_member_sees_shared_account_but_cannot_manage_it(couple, ebba):
    _, account_id = couple
    assert ebba.patch(f"/accounts/{account_id}", json={"household_id": None}).status_code == 403
    assert ebba.delete(f"/accounts/{account_id}").status_code == 403
    assert ebba.post(f"/accounts/{account_id}/transactions", json={"description": "x", "amount": 1}).status_code == 403


def test_unsharing_revokes_access(couple, axel, ebba):
    _, account_id = couple
    axel.post(f"/accounts/{account_id}/transactions", json={"description": "ICA", "amount": 100})
    assert len(ebba.get("/transactions").json()) == 1
    assert axel.patch(f"/accounts/{account_id}", json={"household_id": None}).status_code == 200
    assert ebba.get("/transactions").json() == []
    assert ebba.get("/accounts").json() == []


def test_leaving_household_revokes_access_both_ways(couple, axel, ebba):
    household_id, _ = couple
    ebba.post("/accounts", json={"name": "Ebba card", "household_id": household_id})
    assert len(axel.get("/accounts").json()) == 2

    ebba_id = ebba.get("/me").json()["id"]
    assert ebba.delete(f"/households/{household_id}/members/{ebba_id}").status_code == 204
    assert ebba.get(f"/households/{household_id}").status_code == 404
    assert [a["name"] for a in ebba.get("/accounts").json()] == ["Ebba card"]
    # Ebba's card is no longer shared, so Axel lost access to it.
    assert [a["name"] for a in axel.get("/accounts").json()] == ["Amex"]
    assert ebba.get("/accounts").json()[0]["household_id"] is None


def test_member_cannot_assign_transaction_to_outsider(couple, axel, mallory):
    _, account_id = couple
    t = axel.post(f"/accounts/{account_id}/transactions", json={"description": "ICA", "amount": 100}).json()
    mallory_id = mallory.get("/me").json()["id"]
    r = axel.patch("/transactions", json=[{"id": t["id"], "member_id": mallory_id}])
    assert r.status_code == 422


def test_member_lookup_by_email_is_exact(axel, login):
    a_b = login("a_b").get("/me").json()["id"]  # a_b@example.com
    hh = axel.post("/households", json={"name": "Home"}).json()
    # With LIKE semantics "_" would match any character and add a_b instead.
    r = axel.post(f"/households/{hh['id']}/members", json={"email": "axb@example.com"}).json()
    assert r["members"][1]["user_id"] != a_b
    r = axel.post(f"/households/{hh['id']}/members", json={"email": "A_B@example.com"}).json()
    assert r["members"][2]["user_id"] == a_b
