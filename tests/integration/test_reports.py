from fastapi.testclient import TestClient

from src.api.main import app

DEV_API_KEY = "fraud_dev_sec_key"
HEADERS = {"X-API-KEY": DEV_API_KEY}


def test_reports_summary_unauthorized():
    """
    Accessing the reports/summary endpoint without credentials should fail with 403.
    """
    with TestClient(app) as client:
        response = client.get("/api/v1/reports/summary")
        assert response.status_code == 403


def test_reports_export_unauthorized():
    """
    Accessing the reports/export endpoint without credentials should fail with 403.
    """
    with TestClient(app) as client:
        response = client.get("/api/v1/reports/export", params={"format": "pdf"})
        assert response.status_code == 403


def test_reports_summary_authorized():
    """
    Accessing summary returns correct structure and values under different windows.
    """
    with TestClient(app) as client:
        for w in ["daily", "weekly", "monthly"]:
            res = client.get("/api/v1/reports/summary", params={"window": w}, headers=HEADERS)
            assert res.status_code == 200
            data = res.json()

            assert "title" in data
            assert data["window"] == w
            assert "summary" in data
            assert "top_threats" in data
            assert "analyst_performance" in data
            assert "risk_trends" in data

            # Sub keys
            summary = data["summary"]
            assert "fraud_rate" in summary
            assert "money_at_risk" in summary
            assert "total_transactions" in summary


def test_reports_export_csv():
    """
    Exports to CSV stream correct headers and structured trend values.
    """
    with TestClient(app) as client:
        res = client.get(
            "/api/v1/reports/export", params={"window": "weekly", "format": "csv"}, headers=HEADERS
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in res.headers
        assert "executive_fraud_report_weekly.csv" in res.headers["Content-Disposition"]

        # Verify headers of the CSV
        content = res.text
        assert "Date,Total Transactions Volume,Total Amount Scored ($)" in content


def test_reports_export_excel():
    """
    Exports to Excel compile spreadsheet binaries (openpyxl zip files).
    """
    with TestClient(app) as client:
        res = client.get(
            "/api/v1/reports/export",
            params={"window": "monthly", "format": "excel"},
            headers=HEADERS,
        )
        assert res.status_code == 200
        assert (
            res.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "Content-Disposition" in res.headers
        assert "executive_fraud_report_monthly.xlsx" in res.headers["Content-Disposition"]

        # Verify Excel/Zip file signature (starts with PK)
        assert res.content.startswith(b"PK")


def test_reports_export_pdf():
    """
    Exports to PDF compile structured documents starting with standard %PDF.
    """
    with TestClient(app) as client:
        res = client.get(
            "/api/v1/reports/export", params={"window": "daily", "format": "pdf"}, headers=HEADERS
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in res.headers
        assert "executive_fraud_report_daily.pdf" in res.headers["Content-Disposition"]

        # Verify PDF signature
        assert res.content.startswith(b"%PDF")


def test_reports_invalid_parameters():
    """
    Validation checks reject invalid windows or formats with 422.
    """
    with TestClient(app) as client:
        # Invalid window
        res = client.get("/api/v1/reports/summary", params={"window": "yearly"}, headers=HEADERS)
        assert res.status_code == 422

        # Invalid format
        res = client.get("/api/v1/reports/export", params={"format": "word"}, headers=HEADERS)
        assert res.status_code == 422
