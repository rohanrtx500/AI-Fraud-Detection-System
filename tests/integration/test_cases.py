import io

from fastapi.testclient import TestClient

from src.api.main import app

DEV_API_KEY = "fraud_dev_sec_key"
HEADERS = {"X-API-KEY": DEV_API_KEY}


def test_cases_complete_lifecycle(mock_transaction_payload):
    """
    Tests the complete lifecycle of a fraud investigation case:
    1. Score transaction to create a RiskAssessment.
    2. Escalate the RiskAssessment alert to a Case.
    3. Retrieve the Case list and filter by status.
    4. Retrieve Case details and verify timeline events.
    5. Update Case priority, status, and analyst.
    6. Add an analyst note.
    7. Update the analyst note content.
    8. Upload a PDF evidence attachment.
    9. Download the evidence file binary.
    10. Fetch dashboard case metrics.
    11. Query unified workspace search.
    """
    with TestClient(app) as client:
        # Step 1: Score transaction to generate DB RiskAssessment
        score_res = client.post(
            "/api/v1/transactions/score",
            json=mock_transaction_payload,
            headers=HEADERS,
        )
        assert score_res.status_code == 200
        score_data = score_res.json()
        alert_id = score_data.get("assessment_id")
        assert alert_id is not None

        # Step 2: Escalate alert to a Case
        esc_res = client.post(
            "/api/v1/cases",
            params={"alert_id": alert_id, "priority": "HIGH", "analyst": "analyst_rohan"},
            headers=HEADERS,
        )
        assert esc_res.status_code == 201
        case_data = esc_res.json()
        case_id = case_data.get("case_id")
        assert case_id is not None
        assert case_data["status"] == "OPEN"
        assert case_data["priority"] == "HIGH"

        # Step 3: Get Case list with status filters
        list_res = client.get("/api/v1/cases", params={"status": "OPEN"}, headers=HEADERS)
        assert list_res.status_code == 200
        cases_list = list_res.json()
        assert len(cases_list) >= 1
        assert any(c["case_id"] == case_id for c in cases_list)

        # Step 4: Get detailed Case view
        detail_res = client.get(f"/api/v1/cases/{case_id}", headers=HEADERS)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["case_id"] == case_id
        assert detail_data["assessment"]["assessment_id"] == alert_id
        assert len(detail_data["timeline_events"]) >= 1
        assert detail_data["timeline_events"][0]["event_type"] == "CASE_CREATED"

        # Step 5: Update Case status, priority, and analyst
        patch_res = client.patch(
            f"/api/v1/cases/{case_id}",
            json={"status": "INVESTIGATING", "priority": "CRITICAL", "analyst": "analyst_clara"},
            params={"actor": "analyst_clara"},
            headers=HEADERS,
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["status"] == "INVESTIGATING"
        assert patch_data["priority"] == "CRITICAL"
        assert patch_data["analyst"] == "analyst_clara"

        # Step 6: Add an analyst note
        note_res = client.post(
            f"/api/v1/cases/{case_id}/notes",
            json={
                "category": "BEHAVIORAL",
                "content": "Initial anomaly note",
                "author": "analyst_clara",
            },
            headers=HEADERS,
        )
        assert note_res.status_code == 201
        note_data = note_res.json()
        note_id = note_data["note_id"]
        assert note_data["category"] == "BEHAVIORAL"
        assert note_data["content"] == "Initial anomaly note"

        # Step 7: Update the analyst note
        update_note_res = client.put(
            f"/api/v1/cases/notes/{note_id}",
            json={"content": "Updated anomaly note text"},
            headers=HEADERS,
        )
        assert update_note_res.status_code == 200
        updated_note_data = update_note_res.json()
        assert updated_note_data["content"] == "Updated anomaly note text"
        assert updated_note_data["updated_at"] is not None

        # Step 8: Upload evidence attachment
        file_content = b"Mock PDF Evidence Data"
        upload_res = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            files={"file": ("evidence.pdf", io.BytesIO(file_content), "application/pdf")},
            params={"uploaded_by": "analyst_clara"},
            headers=HEADERS,
        )
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        evidence_id = upload_data["evidence_id"]
        assert upload_data["filename"] == "evidence.pdf"
        assert upload_data["file_type"] == "application/pdf"

        # Step 9: Download evidence attachment
        download_res = client.get(f"/api/v1/cases/evidence/{evidence_id}/file", headers=HEADERS)
        assert download_res.status_code == 200
        assert download_res.content == file_content
        assert download_res.headers["content-type"] == "application/pdf"

        # Step 10: Fetch dashboard metrics
        metrics_res = client.get("/api/v1/cases/dashboard/metrics", headers=HEADERS)
        assert metrics_res.status_code == 200
        metrics_data = metrics_res.json()
        assert "status_distribution" in metrics_data
        assert "priority_distribution" in metrics_data
        assert "analyst_workload" in metrics_data
        assert metrics_data["status_distribution"]["INVESTIGATING"] >= 1
        assert metrics_data["priority_distribution"]["CRITICAL"] >= 1

        # Step 11: Unified search query
        search_res = client.get(
            "/api/v1/cases/search", params={"query": case_id[:8]}, headers=HEADERS
        )
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["cases"]) >= 1
        assert search_data["cases"][0]["case_id"] == case_id
