from datetime import date

from spending_core import ParsedTransaction, dedupe_hashes

COFFEE = ParsedTransaction(date(2025, 7, 1), "Espresso House", 4500)
LUNCH = ParsedTransaction(date(2025, 7, 1), "Max Hamburgare", 12900)


def test_same_file_gives_same_hashes():
    assert dedupe_hashes(1, [COFFEE, LUNCH]) == dedupe_hashes(1, [COFFEE, LUNCH])


def test_identical_rows_in_one_file_are_kept_apart():
    first, second = dedupe_hashes(1, [COFFEE, COFFEE])
    assert first != second


def test_overlapping_export_lines_up():
    # The second export repeats the first coffee and adds a new one.
    old = set(dedupe_hashes(1, [COFFEE, LUNCH]))
    new = dedupe_hashes(1, [LUNCH, COFFEE, COFFEE])
    assert [h in old for h in new] == [True, True, False]


def test_description_whitespace_and_case_are_ignored():
    messy = ParsedTransaction(COFFEE.booked_on, "  ESPRESSO   house ", COFFEE.amount_minor)
    assert dedupe_hashes(1, [messy]) == dedupe_hashes(1, [COFFEE])


def test_accounts_do_not_collide():
    assert dedupe_hashes(1, [COFFEE]) != dedupe_hashes(2, [COFFEE])
