"""Summaries, trends, and settling a household's month."""

from tests.test_api import add, settlement, user_id

MAY, JUNE, JULY, AUGUST = "2025-05", "2025-06", "2025-07", "2025-08"


def on(month, day=15):
    return f"{month}-{day:02d}"


def summary(client, month, household_id=None):
    params = {"month": month} | ({"household_id": household_id} if household_id else {})
    r = client.get("/summary", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def trends(client, first, last, household_id=None):
    params = {"from": first, "to": last} | ({"household_id": household_id} if household_id else {})
    return client.get("/trends", params=params)


# Summary and trends


def test_household_summary_counts_shared_spending(couple, axel, ebba):
    household_id, account_id = couple
    add(axel, account_id, 1000, "ICA MAXI", booked_on=on(JULY))
    add(axel, account_id, 300, "SL", booked_on=on(JULY))
    add(axel, account_id, 99, "Shoes", booked_on=on(JULY), member_id=user_id(ebba))  # not shared
    add(axel, account_id, 500, "ICA MAXI", booked_on=on(JUNE))
    ebba.put("/budgets", params={"household_id": household_id}, json={"category": "Groceries", "amount_minor": 150000})

    result = summary(ebba, JULY, household_id)
    groceries = next(line for line in result["lines"] if line["category"] == "Groceries")
    assert (groceries["target_minor"], groceries["spent_minor"]) == (150000, 100000)
    assert result["spent_minor"] == 130000
    assert result["previous_spent_minor"] == 50000
    assert [t["description"] for t in result["largest"]] == ["ICA MAXI", "SL"]


def test_my_summary_counts_my_share(couple, axel, ebba):
    _, account_id = couple
    private = axel.post("/accounts", json={"name": "Debit"}).json()["id"]
    add(axel, account_id, 1000, "ICA MAXI", booked_on=on(JULY))  # half is Ebba's
    add(axel, account_id, 80, "Shoes", booked_on=on(JULY), member_id=user_id(ebba))
    add(axel, private, 200, "Golf", booked_on=on(JULY))

    mine = summary(axel, JULY)
    assert mine["spent_minor"] == 50000 + 20000
    assert [t["description"] for t in mine["largest"]] == ["ICA MAXI", "Golf"]  # not Ebba's shoes
    hers = summary(ebba, JULY)
    assert hers["spent_minor"] == 50000 + 8000
    assert [t["description"] for t in hers["largest"]] == ["ICA MAXI", "Shoes"]  # not Axel's private golf


def test_trends_cover_every_month(couple, axel):
    household_id, account_id = couple
    add(axel, account_id, 1000, "ICA MAXI", booked_on=on(MAY))
    add(axel, account_id, 300, "SL", booked_on=on(JULY, 1), category="Transportation")
    add(axel, account_id, 200, "ICA MAXI", booked_on=on(JULY, 31))
    add(axel, account_id, 999, "ICA MAXI", booked_on=on(AUGUST, 1))  # after the range

    r = trends(axel, MAY, JULY, household_id)
    assert r.status_code == 200
    assert r.json()["months"] == [
        {"month": MAY, "spent_minor": 100000, "by_category": {"Groceries": 100000}},
        {"month": JUNE, "spent_minor": 0, "by_category": {}},
        {"month": JULY, "spent_minor": 50000, "by_category": {"Groceries": 20000, "Transportation": 30000}},
    ]


def test_trend_range_is_validated(axel):
    assert trends(axel, JULY, JUNE).status_code == 422
    assert trends(axel, "2020-01", JULY).status_code == 422  # more than 36 months
    assert trends(axel, "2025-13", JULY).status_code == 422
    assert trends(axel, "2025-01", "2025-12").status_code == 200


# Settlement


def test_settlement_is_per_month(couple, axel, ebba):
    household_id, account_id = couple
    add(axel, account_id, 1000, booked_on=on(JULY))
    add(axel, account_id, 400, booked_on=on(AUGUST))
    july = settlement(ebba, household_id, JULY).json()
    assert (july["month"], july["shared_minor"]) == (JULY, 100000)
    assert settlement(ebba, household_id, AUGUST).json()["shared_minor"] == 40000
    assert settlement(ebba, household_id, "2025-09").json()["transfers"] == []
    assert settlement(ebba, household_id, "July").status_code == 422


def test_who_paid_comes_from_the_account_owner(couple, axel, ebba):
    household_id, axel_account = couple
    ebba_account = ebba.post("/accounts", json={"name": "Visa", "household_id": household_id}).json()["id"]
    add(axel, axel_account, 1000, booked_on=on(JULY))
    add(ebba, ebba_account, 600, booked_on=on(JULY))
    add(ebba, ebba_account, 100, booked_on=on(JULY), member_id=user_id(ebba))

    result = settlement(axel, household_id, JULY).json()
    assert [(m["paid_minor"], m["amount_minor"], m["balance_minor"]) for m in result["per_member"]] == [
        (100000, 80000, 20000),
        (70000, 90000, -20000),
    ]
    [transfer] = result["transfers"]
    assert (transfer["debtor"]["display_name"], transfer["creditor"]["display_name"]) == ("ebba", "axel")
    assert transfer["amount_minor"] == 20000


def test_closing_a_month_keeps_its_settlement(couple, axel, ebba):
    household_id, account_id = couple
    t = add(axel, account_id, 1000, booked_on=on(JULY))
    r = ebba.post(f"/households/{household_id}/settlements", json={"month": JULY})
    assert r.status_code == 201, r.text
    closed = r.json()
    assert closed["closed_at"] is not None
    assert closed["shared_minor"] == 100000

    # Later edits don't change the closed month...
    add(axel, account_id, 500, booked_on=on(JULY, 20))
    axel.patch("/transactions", json=[{"id": t["id"], "allocation": "excluded"}])
    axel.patch(f"/households/{household_id}/members/{user_id(axel)}", json={"split_weight": 3})
    axel.patch("/me", json={"display_name": "Axel D"})
    assert settlement(ebba, household_id, JULY).json() == closed
    assert ebba.post(f"/households/{household_id}/settlements", json={"month": JULY}).status_code == 409
    assert axel.get(f"/households/{household_id}/settlements").json() == [closed]

    # ...until an owner reopens it.
    assert ebba.delete(f"/households/{household_id}/settlements/{JULY}").status_code == 403
    assert axel.delete(f"/households/{household_id}/settlements/{JULY}").status_code == 204
    reopened = settlement(ebba, household_id, JULY).json()
    assert (reopened["closed_at"], reopened["shared_minor"]) == (None, 50000)
    assert axel.get(f"/households/{household_id}/settlements").json() == []
    assert axel.delete(f"/households/{household_id}/settlements/{JULY}").status_code == 404


def test_closed_months_are_listed_newest_first(couple, axel):
    household_id, _ = couple
    for month in (JULY, MAY, AUGUST):
        assert axel.post(f"/households/{household_id}/settlements", json={"month": month}).status_code == 201
    listed = axel.get(f"/households/{household_id}/settlements").json()
    assert [s["month"] for s in listed] == [AUGUST, JULY, MAY]


def test_cannot_close_a_month_that_does_not_add_up(couple, axel, ebba):
    household_id, account_id = couple
    ebba_id = user_id(ebba)
    add(axel, account_id, 50, booked_on=on(JULY), member_id=ebba_id)
    ebba.delete(f"/households/{household_id}/members/{ebba_id}")
    assert axel.post(f"/households/{household_id}/settlements", json={"month": JULY}).status_code == 409
    assert axel.get(f"/households/{household_id}/settlements").json() == []
