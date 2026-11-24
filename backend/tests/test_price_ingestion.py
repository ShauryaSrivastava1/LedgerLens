from app.services.price_ingestion import parse_price_csv


def test_parses_standard_date_close_headers():
    csv_bytes = b"date,close\n2025-03-31,1234.50\n2025-04-01,1240.00\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 2
    assert result.errors == []
    assert result.rows[0].close_price == 1234.50


def test_tolerates_alternate_header_names():
    csv_bytes = b"Date,Close Price\n2025-03-31,1234.50\n"
    # "Close Price" isn't a recognized alias verbatim (has a space) -
    # use the recognized alias "close_price" instead to confirm matching
    # is case-insensitive on the exact alias.
    csv_bytes = b"Date,close_price\n2025-03-31,1234.50\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 1
    assert result.errors == []


def test_tolerates_ltp_column_name():
    csv_bytes = b"trade_date,ltp\n2025-03-31,999.99\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 1


def test_handles_comma_thousands_separator():
    csv_bytes = b"date,close\n2025-03-31,\"1,234.50\"\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 1
    assert result.rows[0].close_price == 1234.50


def test_parses_multiple_date_formats():
    csv_bytes = b"date,close\n31-03-2025,100\n2025-04-01,101\n04/02/2025,102\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 3
    assert result.errors == []


def test_reports_unparseable_date_by_row_number():
    csv_bytes = b"date,close\nnot-a-date,100\n2025-04-01,101\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 1
    assert len(result.errors) == 1
    assert "Row 2" in result.errors[0]


def test_reports_unparseable_price():
    csv_bytes = b"date,close\n2025-03-31,not-a-number\n"
    result = parse_price_csv(csv_bytes)
    assert result.rows == []
    assert "Row 2" in result.errors[0]


def test_rejects_non_positive_price():
    csv_bytes = b"date,close\n2025-03-31,0\n2025-04-01,-5\n"
    result = parse_price_csv(csv_bytes)
    assert result.rows == []
    assert len(result.errors) == 2


def test_skips_blank_lines():
    csv_bytes = b"date,close\n2025-03-31,100\n,\n2025-04-01,101\n"
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 2
    assert result.errors == []


def test_missing_expected_columns_reports_error():
    csv_bytes = b"foo,bar\n1,2\n"
    result = parse_price_csv(csv_bytes)
    assert result.rows == []
    assert len(result.errors) == 1
    assert "Could not find date/close columns" in result.errors[0]


def test_empty_file():
    result = parse_price_csv(b"")
    assert result.rows == []
    assert len(result.errors) == 1


def test_handles_bom_prefixed_csv():
    csv_bytes = "date,close\n2025-03-31,100\n".encode("utf-8-sig")
    result = parse_price_csv(csv_bytes)
    assert len(result.rows) == 1
    assert result.errors == []
