"""Adding someone to a household before they've signed in."""

from datetime import date

import pytest

from tests.conftest import make_token


@pytest.fixture
def household(axel):
    hh = axel.post("/households", json={"name": "Home"}).json()
    r = axel.post(f"/households/{hh['id']}/members", json={"email": "ebba@example.com", "display_name": "Ebba"})
    assert r.status_code == 201, r.text
    return r.json()


def sign_in(anon, email, sub="sub-ebba", **claims):
    return anon.get("/me", headers={"Authorization": f"Bearer {make_token(sub, email, **claims)}"})


def test_pending_member_is_listed(household):
    ebba = household["members"][1]
    assert (ebba["display_name"], ebba["email"], ebba["pending"], ebba["role"]) == (
        "Ebba",
        "ebba@example.com",
        True,
        "member",
    )
    assert household["members"][0]["pending"] is False


def test_pending_member_can_be_split_with(household, axel):
    ebba_id = household["members"][1]["user_id"]
    account = axel.post("/accounts", json={"name": "Amex", "household_id": household["id"]}).json()
    assert {m["display_name"] for m in account["members"]} == {"axel", "Ebba"}
    axel.post(f"/accounts/{account['id']}/transactions", json={"description": "Rent", "amount": 1000})
    axel.post(f"/accounts/{account['id']}/transactions", json={"description": "Shoes", "amount": 100, "member_id": ebba_id})
    month = date.today().strftime("%Y-%m")
    shares = axel.get(f"/households/{household['id']}/settlement", params={"month": month}).json()["per_member"]
    assert [(m["display_name"], m["amount_minor"]) for m in shares] == [("axel", 50000), ("Ebba", 60000)]


def test_first_sign_in_takes_over_the_placeholder(household, anon):
    ebba_id = household["members"][1]["user_id"]
    me = sign_in(anon, "Ebba@Example.com").json()
    assert me["id"] == ebba_id
    assert me["display_name"] == "Ebba"  # the name Axel gave her stays until she changes it
    assert [h["name"] for h in me["households"]] == ["Home"]


def test_unverified_email_does_not_take_over(household, anon):
    me = sign_in(anon, "ebba@example.com", user_metadata={"email_verified": False}).json()
    assert me["id"] != household["members"][1]["user_id"]
    assert me["households"] == []


def test_adding_the_same_email_twice_conflicts(household, axel):
    r = axel.post(f"/households/{household['id']}/members", json={"email": "EBBA@example.com"})
    assert r.status_code == 409


def test_placeholder_is_reused_across_households(household, login):
    other = login("carl")
    hh = other.post("/households", json={"name": "Office"}).json()
    r = other.post(f"/households/{hh['id']}/members", json={"email": "ebba@example.com"}).json()
    assert r["members"][1]["user_id"] == household["members"][1]["user_id"]


def test_display_name_defaults_to_email_name(axel):
    hh = axel.post("/households", json={"name": "Home"}).json()
    r = axel.post(f"/households/{hh['id']}/members", json={"email": "sam@example.com"}).json()
    assert r["members"][1]["display_name"] == "sam"


def test_invalid_email_is_422(axel):
    hh = axel.post("/households", json={"name": "Home"}).json()
    assert axel.post(f"/households/{hh['id']}/members", json={"email": "not an email"}).status_code == 422


def test_pending_member_can_be_removed(household, axel):
    ebba_id = household["members"][1]["user_id"]
    assert axel.delete(f"/households/{household['id']}/members/{ebba_id}").status_code == 204
    assert len(axel.get(f"/households/{household['id']}").json()["members"]) == 1
