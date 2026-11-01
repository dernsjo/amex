from datetime import date

import pytest

from spending_core import (
    CsvMapping,
    ImportConfig,
    ImportFileError,
    ParsedTransaction,
    importer_for,
    read_table,
    resolve,
)
from spending_core.importers import guess_mapping

# Synthetic exports in shapes Swedish banks use. Not copies of any real bank's format.
SEMICOLON_CP1252 = (
    "Kontoutdrag Privatkonto 1234-5 678 901;;;;\r\n"
    "Exporterad 2025-07-31;;;;\r\n"
    "\r\n"
    "Bokföringsdag;Transaktionsdag;Text;Belopp;Saldo\r\n"
    "2025-07-02;2025-07-01;ICA NÄRA   ÅRSTA;-262,71;9 737,29\r\n"
    "2025-07-03;2025-07-03;LÖN;25 000,00;34 737,29\r\n"
    "2025-07-04;2025-07-04;Swish återbetalning;-1 250,50;33 486,79\r\n"
    ";;Summa;23 486,79;\r\n"
).encode("cp1252")

ENGLISH = (
    "Date,Description,Amount,Currency\n"
    '15/07/2025,"Coffee, large",-4.50,SEK\n'
    '16/07/2025,Rent,"-12,000.00",SEK\n'
)

AMEX = "Datum,Beskrivning,Belopp\n07/01/2025,HEMKOP,\"262,71\"\n"


# Reading tables


def test_read_table_skips_preamble_and_detects_dialect():
    table = read_table(SEMICOLON_CP1252)
    assert table.header == ["Bokföringsdag", "Transaktionsdag", "Text", "Belopp", "Saldo"]
    assert table.rows[0].cells[2] == "ICA NÄRA   ÅRSTA"
    assert table.rows[0].line == 5
    assert len(table.rows) == 4  # including the footer, which the importer skips


def test_read_table_pads_short_rows():
    table = read_table("a,b,c\n1,2\n")
    assert table.rows[0].cells == ["1", "2", ""]


def test_read_table_rejects_empty_file():
    with pytest.raises(ImportFileError, match="empty"):
        read_table(b"  \n")


def test_missing_column_names_the_columns():
    with pytest.raises(ImportFileError, match="Column 'Nope' not found"):
        read_table(ENGLISH).column("Nope")


# Generic CSV mapping


SEMICOLON_MAPPING = CsvMapping(date_column="Bokföringsdag", description_column="Text", amount_column="Belopp")


def test_mapping_parses_bank_export_with_spending_negative():
    parsed = importer_for(ImportConfig("csv", SEMICOLON_MAPPING)).parse(read_table(SEMICOLON_CP1252))
    assert parsed == [
        ParsedTransaction(date(2025, 7, 2), "ICA NÄRA ÅRSTA", 26271),  # money out = spending = positive
        ParsedTransaction(date(2025, 7, 3), "LÖN", -2500000),  # income is negative
        ParsedTransaction(date(2025, 7, 4), "Swish återbetalning", 125050),
    ]


def test_mapping_with_dot_decimals_and_day_first_dates():
    mapping = CsvMapping("Date", "Description", "Amount", decimal_separator=".", date_format="%d/%m/%Y")
    parsed = importer_for(ImportConfig("csv", mapping)).parse(read_table(ENGLISH))
    assert parsed == [
        ParsedTransaction(date(2025, 7, 15), "Coffee, large", 450),
        ParsedTransaction(date(2025, 7, 16), "Rent", 1200000),
    ]


def test_mapping_spending_positive():
    mapping = CsvMapping("Datum", "Beskrivning", "Belopp", spending_is_negative=False)
    parsed = importer_for(ImportConfig("csv", mapping)).parse(read_table("Datum;Beskrivning;Belopp\n2025-07-01;X;100,00\n"))
    assert parsed[0].amount_minor == 10000


def test_mapping_bad_value_names_the_line():
    mapping = CsvMapping("Date", "Description", "Amount", decimal_separator=".")
    with pytest.raises(ImportFileError, match="Line 3"):
        importer_for(ImportConfig("csv", mapping)).parse(read_table("Date,Description,Amount\n2025-07-01,A,1\n2025-07-02,B,x\n"))


def test_mapping_wrong_date_format():
    mapping = CsvMapping("Date", "Description", "Amount", decimal_separator=".", date_format="%Y-%m-%d")
    with pytest.raises(ImportFileError, match="Unrecognized date '15/07/2025'"):
        importer_for(ImportConfig("csv", mapping)).parse(read_table(ENGLISH))


def test_config_round_trips_through_dict():
    config = ImportConfig("csv", SEMICOLON_MAPPING)
    assert ImportConfig.from_dict(config.to_dict()) == config
    assert ImportConfig.from_dict({"importer": "amex_se"}) == ImportConfig("amex_se")


def test_csv_config_without_mapping_or_unknown_importer():
    with pytest.raises(ImportFileError, match="Choose which columns"):
        importer_for(ImportConfig("csv"))
    with pytest.raises(ImportFileError, match="Unknown importer"):
        importer_for(ImportConfig("nordea_xlsx"))


# Guessing a mapping


def test_guess_mapping_from_swedish_names():
    guess = guess_mapping(read_table(SEMICOLON_CP1252))
    assert guess == {
        "date_column": "Bokföringsdag",
        "description_column": "Text",
        "amount_column": "Belopp",
        "decimal_separator": ",",
        "spending_is_negative": True,
        "date_format": "%Y-%m-%d",
    }


def test_guess_mapping_from_english_names():
    guess = guess_mapping(read_table(ENGLISH))
    assert (guess["date_column"], guess["description_column"], guess["amount_column"]) == ("Date", "Description", "Amount")
    assert (guess["decimal_separator"], guess["date_format"]) == (".", "%d/%m/%Y")


def test_guess_mapping_from_content_when_names_are_unknown():
    table = read_table("A;B;C\n2025-07-01;Pressbyrån Centralen;-45,00\n2025-07-02;SL;-39,00\n")
    guess = guess_mapping(table)
    assert (guess["date_column"], guess["description_column"], guess["amount_column"]) == ("A", "B", "C")


def test_guess_mapping_leaves_unknowns_empty():
    guess = guess_mapping(read_table("x;y\nfoo;bar\n"))
    assert guess["date_column"] is None and guess["amount_column"] is None


# Choosing an importer


def test_resolve_detects_amex():
    r = resolve(read_table(AMEX))
    assert (r.source, r.config) == ("detected", ImportConfig("amex_se"))


def test_resolve_guesses_mapping_for_unknown_bank():
    r = resolve(read_table(SEMICOLON_CP1252))
    assert r.source == "guessed"
    assert r.config == ImportConfig("csv", CsvMapping("Bokföringsdag", "Text", "Belopp", date_format="%Y-%m-%d"))


def test_resolve_prefers_saved_config_that_still_fits():
    saved = ImportConfig("csv", CsvMapping("Datum", "Beskrivning", "Belopp", spending_is_negative=False))
    assert resolve(read_table(AMEX), saved=saved).source == "saved"
    # A different file from another bank doesn't fit the saved columns.
    assert resolve(read_table(SEMICOLON_CP1252), saved=saved).source == "guessed"


def test_resolve_requested_wins():
    requested = ImportConfig("csv", SEMICOLON_MAPPING)
    assert resolve(read_table(AMEX), requested=requested, saved=ImportConfig("amex_se")).config == requested


def test_resolve_gives_up_without_columns():
    r = resolve(read_table("x;y\nfoo;bar\n"))
    assert (r.source, r.config) == ("none", None)
