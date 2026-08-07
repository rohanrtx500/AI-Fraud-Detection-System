from fastapi.testclient import TestClient

from src.api.main import app

DEV_API_KEY = "fraud_dev_sec_key"
HEADERS = {"X-API-KEY": DEV_API_KEY}


def test_auth_and_rbac_flow():
    """
    Integration test verifying:
    1. Registering new users with different roles.
    2. Enforcing password strength constraints.
    3. Generating system-managed usernames: {RolePrefix}_{CapitalizedName}_{RoleId}.
    4. Generating unique role IDs (CO-xxxx, AN-xxxx, AU-xxxx).
    5. Testing endpoint authorization gates.
    """
    with TestClient(app) as client:
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        officer_name = f"officer_name_{unique_suffix}"
        analyst_name = f"analyst_name_{unique_suffix}"
        auditor_name = f"auditor_name_{unique_suffix}"
        password_strong = "SecurePass123!"
        password_weak = "weakpw"

        # 1. Test Password Strength Validation
        reg_fail_pw = client.post(
            "/api/v1/auth/register",
            json={
                "username": officer_name,
                "password": password_weak,
                "role": "Compliance Officer",
            },
        )
        assert reg_fail_pw.status_code == 400
        assert "Password must be at least 8 characters long." in reg_fail_pw.json()["detail"]

        reg_fail_pw2 = client.post(
            "/api/v1/auth/register",
            json={
                "username": officer_name,
                "password": "weakpasswordnoformat",
                "role": "Compliance Officer",
            },
        )
        assert reg_fail_pw2.status_code == 400

        # 2. Registration & Username Generation Checks
        # Officer Registration
        reg_res = client.post(
            "/api/v1/auth/register",
            json={
                "username": officer_name,
                "password": password_strong,
                "role": "Compliance Officer",
            },
        )
        assert reg_res.status_code == 201
        data_officer = reg_res.json()
        role_id_officer = data_officer["role_id"]
        username_officer = data_officer["username"]
        assert role_id_officer.startswith("CO-")
        assert username_officer == officer_name

        # Analyst Registration
        reg_res2 = client.post(
            "/api/v1/auth/register",
            json={"username": analyst_name, "password": password_strong, "role": "Analyst"},
        )
        assert reg_res2.status_code == 201
        data_analyst = reg_res2.json()
        role_id_analyst = data_analyst["role_id"]
        username_analyst = data_analyst["username"]
        assert role_id_analyst.startswith("AN-")
        assert username_analyst == analyst_name

        # Auditor Registration
        reg_res3 = client.post(
            "/api/v1/auth/register",
            json={"username": auditor_name, "password": password_strong, "role": "Auditor"},
        )
        assert reg_res3.status_code == 201
        data_auditor = reg_res3.json()
        role_id_auditor = data_auditor["role_id"]
        username_auditor = data_auditor["username"]
        assert role_id_auditor.startswith("AU-")
        assert username_auditor == auditor_name

        # Duplicate name registration succeeds and issues a distinct role ID
        reg_res_dup_name = client.post(
            "/api/v1/auth/register",
            json={"username": analyst_name, "password": password_strong, "role": "Analyst"},
        )
        assert reg_res_dup_name.status_code == 201
        data_dup = reg_res_dup_name.json()
        assert data_dup["username"] == analyst_name
        assert data_dup["role_id"] != role_id_analyst

        # 3. Log In and Token Retrieval
        # Fail with wrong password
        login_fail = client.post(
            "/api/v1/auth/token",
            data={"username": role_id_officer, "password": "WrongPassword!"},
        )
        assert login_fail.status_code == 401

        # Success Logins
        tok_officer = client.post(
            "/api/v1/auth/token",
            data={"username": role_id_officer, "password": password_strong},
        ).json()["access_token"]

        tok_analyst = client.post(
            "/api/v1/auth/token",
            data={"username": role_id_analyst, "password": password_strong},
        ).json()["access_token"]

        tok_auditor = client.post(
            "/api/v1/auth/token",
            data={"username": role_id_auditor, "password": password_strong},
        ).json()["access_token"]

        # 4. RBAC gates testing
        headers_officer = {"X-API-KEY": DEV_API_KEY, "Authorization": f"Bearer {tok_officer}"}
        headers_analyst = {"X-API-KEY": DEV_API_KEY, "Authorization": f"Bearer {tok_analyst}"}
        headers_auditor = {"X-API-KEY": DEV_API_KEY, "Authorization": f"Bearer {tok_auditor}"}

        # /reports/summary (Officer, Auditor allow; Analyst deny)
        assert client.get("/api/v1/reports/summary", headers=headers_officer).status_code == 200
        assert client.get("/api/v1/reports/summary", headers=headers_auditor).status_code == 200
        assert client.get("/api/v1/reports/summary", headers=headers_analyst).status_code == 403

        # /threats POST (Officer allow; Analyst, Auditor deny)
        threat_payload = {
            "indicator_type": "IP",
            "value": f"198.51.100.222_{unique_suffix}",
            "risk_multiplier": 3.0,
            "source": "test",
        }
        assert (
            client.post(
                "/api/v1/threats", params=threat_payload, headers=headers_officer
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/threats", params=threat_payload, headers=headers_analyst
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/threats", params=threat_payload, headers=headers_auditor
            ).status_code
            == 403
        )

        # /me profile validation
        profile_res = client.get("/api/v1/auth/me", headers=headers_analyst)
        assert profile_res.status_code == 200
        assert profile_res.json()["username"] == username_analyst
        assert profile_res.json()["role_id"] == role_id_analyst
