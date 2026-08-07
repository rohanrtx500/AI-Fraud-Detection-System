import os

import httpx


class FraudAPIClient:
    """
    HTTP client wrapper for the AI Fraud Detection FastAPI Backend.
    Encapsulates REST calls to keep dashboard components separated from direct API routes.
    Includes API key authentication headers for securing requests.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
        self.api_key = os.getenv("API_KEY", "fraud_dev_sec_key")
        self.headers = {"X-API-KEY": self.api_key}

    def get_summary_metrics(self) -> dict:
        """
        Fetches system performance and risk distributions.
        Calls GET /analytics/summary
        """
        try:
            r = httpx.get(f"{self.base_url}/analytics/summary", headers=self.headers, timeout=5.0)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def get_daily_trends(self, days: int = 7) -> list[dict]:
        """
        Fetches time-series trends.
        Calls GET /analytics/daily-trends
        """
        try:
            r = httpx.get(
                f"{self.base_url}/analytics/daily-trends",
                params={"days": days},
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def score_transaction(self, transaction_payload: dict) -> dict:
        """
        Scores a live transaction.
        Calls POST /transactions/score
        """
        try:
            r = httpx.post(
                f"{self.base_url}/transactions/score",
                json=transaction_payload,
                headers=self.headers,
                timeout=8.0,
            )
            if r.status_code == 200:
                return r.json()
            return {"error": f"API error status {r.status_code}: {r.text}"}
        except Exception as e:
            return {"error": f"Failed to connect to API: {e}"}

    def get_active_model_info(self) -> dict:
        """
        Retrieves active model properties.
        Calls GET /models/active
        """
        try:
            r = httpx.get(f"{self.base_url}/models/active", headers=self.headers, timeout=5.0)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def get_cases(
        self,
        status: str | None = None,
        priority: str | None = None,
        analyst: str | None = None,
        search_query: str | None = None,
    ) -> list[dict]:
        try:
            params = {}
            if status:
                params["status"] = status
            if priority:
                params["priority"] = priority
            if analyst:
                params["analyst"] = analyst
            if search_query:
                params["search_query"] = search_query
            r = httpx.get(
                f"{self.base_url}/cases", params=params, headers=self.headers, timeout=5.0
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def get_case_details(self, case_id: str) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/cases/{case_id}", headers=self.headers, timeout=5.0)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def escalate_alert(
        self, alert_id: str, priority: str = "MEDIUM", analyst: str | None = None
    ) -> dict:
        try:
            params = {"alert_id": alert_id, "priority": priority}
            if analyst:
                params["analyst"] = analyst
            r = httpx.post(
                f"{self.base_url}/cases", params=params, headers=self.headers, timeout=5.0
            )
            return r.json() if r.status_code in [200, 201] else {}
        except Exception:
            return {}

    def update_case(
        self,
        case_id: str,
        status: str | None = None,
        priority: str | None = None,
        analyst: str | None = None,
        actor: str = "system",
    ) -> dict:
        try:
            payload = {}
            if status:
                payload["status"] = status
            if priority:
                payload["priority"] = priority
            if analyst is not None:
                payload["analyst"] = analyst
            r = httpx.patch(
                f"{self.base_url}/cases/{case_id}",
                json=payload,
                params={"actor": actor},
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def add_case_note(self, case_id: str, category: str, content: str, author: str) -> dict:
        try:
            payload = {"category": category, "content": content, "author": author}
            r = httpx.post(
                f"{self.base_url}/cases/{case_id}/notes",
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code in [200, 201] else {}
        except Exception:
            return {}

    def update_case_note(self, note_id: str, content: str) -> dict:
        try:
            payload = {"content": content}
            r = httpx.put(
                f"{self.base_url}/cases/notes/{note_id}",
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def upload_evidence(
        self, case_id: str, filename: str, file_bytes: bytes, mime_type: str, uploaded_by: str
    ) -> dict:
        try:
            files = {"file": (filename, file_bytes, mime_type)}
            r = httpx.post(
                f"{self.base_url}/cases/{case_id}/evidence",
                files=files,
                params={"uploaded_by": uploaded_by},
                headers=self.headers,
                timeout=10.0,
            )
            return r.json() if r.status_code in [200, 201] else {}
        except Exception:
            return {}

    def get_cases_metrics(self) -> dict:
        try:
            r = httpx.get(
                f"{self.base_url}/cases/dashboard/metrics", headers=self.headers, timeout=5.0
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def search_workspace(self, query: str) -> dict:
        try:
            r = httpx.get(
                f"{self.base_url}/cases/search",
                params={"query": query},
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code == 200 else {"cases": [], "transactions": []}
        except Exception:
            return {"cases": [], "transactions": []}

    def get_monitoring_report(self) -> dict:
        """
        Fetches the active model monitoring and drift report.
        Calls GET /monitoring/report
        """
        try:
            r = httpx.get(f"{self.base_url}/monitoring/report", headers=self.headers, timeout=10.0)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def run_monitoring_check(self) -> dict:
        """
        Manually triggers a new model monitoring and drift check.
        Calls POST /monitoring/run
        """
        try:
            r = httpx.post(f"{self.base_url}/monitoring/run", headers=self.headers, timeout=15.0)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def get_reports_summary(self, window: str = "weekly") -> dict:
        """
        Fetches executive summary metrics for reports.
        Calls GET /reports/summary
        """
        try:
            r = httpx.get(
                f"{self.base_url}/reports/summary",
                params={"window": window},
                headers=self.headers,
                timeout=10.0,
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def get_reports_export_raw(self, window: str = "weekly", format: str = "pdf") -> bytes | None:
        """
        Fetches the exported report binary file.
        Calls GET /reports/export
        """
        try:
            r = httpx.get(
                f"{self.base_url}/reports/export",
                params={"window": window, "format": format},
                headers=self.headers,
                timeout=15.0,
            )
            return r.content if r.status_code == 200 else None
        except Exception:
            return None

    def get_audit_logs(self, limit: int = 100) -> list[dict]:
        """
        Fetches system override audit logs.
        Calls GET /cases/audit/logs
        """
        try:
            r = httpx.get(
                f"{self.base_url}/cases/audit/logs",
                params={"limit": limit},
                headers=self.headers,
                timeout=5.0,
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def get_threats(self, indicator_type: str | None = None) -> list[dict]:
        """
        Fetches blacklisted threat indicators.
        Calls GET /threats
        """
        try:
            params = {}
            if indicator_type:
                params["indicator_type"] = indicator_type
            r = httpx.get(
                f"{self.base_url}/threats", params=params, headers=self.headers, timeout=5.0
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def add_threat(
        self,
        indicator_type: str,
        value: str,
        risk_multiplier: float = 2.0,
        source: str = "manual_entry",
    ) -> dict:
        """
        Registers a new blacklisted threat indicator.
        Calls POST /threats
        """
        try:
            params = {
                "indicator_type": indicator_type,
                "value": value,
                "risk_multiplier": risk_multiplier,
                "source": source,
            }
            r = httpx.post(
                f"{self.base_url}/threats", params=params, headers=self.headers, timeout=5.0
            )
            return r.json() if r.status_code in [200, 201] else {}
        except Exception:
            return {}

    def delete_threat(self, indicator_id: str) -> bool:
        """
        Deletes a blacklisted threat indicator by ID.
        Calls DELETE /threats/{indicator_id}
        """
        try:
            r = httpx.delete(
                f"{self.base_url}/threats/{indicator_id}", headers=self.headers, timeout=5.0
            )
            return r.status_code == 200
        except Exception:
            return False

    def set_token(self, token: str | None) -> None:
        """
        Sets or clears the Authorization Bearer header for JWT requests.
        """
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]

    def register_user(self, username: str, password: str, role: str) -> dict:
        """
        Registers a new compliance dashboard user.
        Calls POST /auth/register
        """
        try:
            r = httpx.post(
                f"{self.base_url}/auth/register",
                json={"username": username, "password": password, "role": role},
                headers=self.headers,
                timeout=5.0,
            )
            if r.status_code == 201:
                return r.json()
            else:
                detail = r.json().get("detail", "Registration failed")
                return {"error": detail}
        except Exception as e:
            return {"error": str(e)}

    def login_user(self, role_id: str, password: str) -> dict:
        """
        Obtains a JWT access token for a user.
        Calls POST /auth/token
        """
        try:
            r = httpx.post(
                f"{self.base_url}/auth/token",
                data={"username": role_id, "password": password},
                headers=self.headers,
                timeout=5.0,
            )
            if r.status_code == 200:
                return r.json()
            else:
                detail = r.json().get("detail", "Login failed")
                return {"error": detail}
        except Exception as e:
            return {"error": str(e)}

