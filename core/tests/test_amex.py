from datetime import date

import pytest

from spending_core import ImportFileError, ParsedTransaction, parse_amex_csv

# Synthetic data in the raw Amex export shape (comma decimals, Unicode minus).
RAW = (
    "Datum,Beskrivning,Belopp\n"
    '07/01/2025,"HEMKOP SABIS STOCKHO 09   STOCKHOLM","262,71"\n'
    '06/30/2025,7133 AUTOGRILL PALERMO  CINISI,"272,6"\n'
    '06/28/2025,BETALNING MOTTAGEN,"−1500,00"\n'
    ",,\n"
)


def test_parses_raw_export():
    assert parse_amex_csv(RAW) == [
        ParsedTransaction(date(2025, 7, 1), "HEMKOP SABIS STOCKHO 09 STOCKHOLM", 26271),
        ParsedTransaction(date(2025, 6, 30), "7133 AUTOGRILL PALERMO CINISI", 27260),
        ParsedTransaction(date(2025, 6, 28), "BETALNING MOTTAGEN", -150000),
    ]


def test_accepts_bytes_with_bom_and_iso_dates():
    content = "﻿Datum,Beskrivning,Belopp\n2025-07-02,ÅRSAVGIFT,500.0\n".encode("utf-8")
    assert parse_amex_csv(content) == [ParsedTransaction(date(2025, 7, 2), "ÅRSAVGIFT", 50000)]


def test_extra_columns_are_ignored():
    content = "Datum,Beskrivning,Kortmedlem,Belopp\n2025-07-02,X,AXEL,\"1,00\"\n"
    assert parse_amex_csv(content)[0].amount_minor == 100


def test_missing_columns():
    with pytest.raises(ImportFileError, match="missing column.*Belopp"):
        parse_amex_csv("Datum,Beskrivning\n2025-07-02,X\n")


def test_bad_row_reports_line_number():
    with pytest.raises(ImportFileError, match="Line 3"):
        parse_amex_csv("Datum,Beskrivning,Belopp\n2025-07-02,A,1\n2025-07-02,B,oops\n")


def test_bad_date():
    with pytest.raises(ImportFileError, match="Unrecognized date"):
        parse_amex_csv("Datum,Beskrivning,Belopp\nyesterday,A,1\n")


def test_windows_1252_is_read():
    content = "Datum,Beskrivning,Belopp\n2025-07-02,HEMKÖP,1\n".encode("cp1252")
    assert parse_amex_csv(content)[0].description == "HEMKÖP"
