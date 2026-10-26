from tests.conftest import login

PAYLOAD = {
    "employee_code": "emp-101",
    "first_name": "Rahul",
    "last_name": "Kumar",
    "designation": "Senior Software Developer",
    "department": "Engineering",
    "email": "Rahul@Example.com",
    "phone": "+91 98765 43210",
    "website": "example.com",
    "linkedin_url": "https://linkedin.com/in/rahul",
}


def test_create_employee(client, admin_headers):
    r = client.post("/api/employees", json=PAYLOAD, headers=admin_headers)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["employee_code"] == "EMP-101"
    assert data["email"] == "rahul@example.com"
    assert data["website"] == "https://example.com"
    assert data["full_name"] == "Rahul Kumar"
    assert data["has_login"] is False
    assert data["twitter_url"] is None


def test_create_employee_with_login(client, admin_headers):
    r = client.post("/api/employees", json={**PAYLOAD, "password": "Welcome#2026"}, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["data"]["has_login"] is True
    headers = login(client, "rahul@example.com", "Welcome#2026")
    assert client.get("/api/employees/me", headers=headers).json()["data"]["first_name"] == "Rahul"


def test_duplicate_code_and_email_rejected(client, admin_headers):
    client.post("/api/employees", json=PAYLOAD, headers=admin_headers)
    r = client.post("/api/employees", json={**PAYLOAD, "email": "other@example.com"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_EMPLOYEE_CODE"
    r = client.post("/api/employees", json={**PAYLOAD, "employee_code": "EMP-999"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_EMAIL"


def test_employee_validation(client, admin_headers):
    cases = [
        {"first_name": ""},
        {"email": "not-an-email"},
        {"phone": "call me"},
        {"linkedin_url": "javascript:alert(1)"},
        {"employee_code": "bad code!"},
        {"profile_photo_url": "file:///C:/secret.png"},
        {"password": "short"},
    ]
    for override in cases:
        r = client.post("/api/employees", json={**PAYLOAD, **override}, headers=admin_headers)
        assert r.status_code == 422, override
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_search_and_filter(client, admin_headers, john, priya):
    data = client.get("/api/employees", headers=admin_headers).json()["data"]
    assert data["total"] == 2
    data = client.get("/api/employees?q=priya", headers=admin_headers).json()["data"]
    assert [e["first_name"] for e in data["items"]] == ["Priya"]
    data = client.get("/api/employees?department=Engineering", headers=admin_headers).json()["data"]
    assert [e["first_name"] for e in data["items"]] == ["John"]
    assert client.get("/api/employees/departments", headers=admin_headers).json()["data"] == [
        "Engineering", "Human Resources"
    ]


def test_update_employee(client, admin_headers, john):
    payload = {
        "employee_code": john.employee_code, "first_name": "Johnny", "last_name": "Smith",
        "designation": "Lead Developer", "email": "johnny@company.com", "department": "Engineering",
    }
    r = client.put(f"/api/employees/{john.id}", json=payload, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["designation"] == "Lead Developer"
    # The linked login follows the new email address.
    from tests.conftest import EMPLOYEE_PASSWORD
    assert client.post("/api/auth/login", json={"email": "johnny@company.com", "password": EMPLOYEE_PASSWORD}).status_code == 200


def test_deactivate_blocks_login_and_reactivate(client, admin_headers, john):
    from tests.conftest import EMPLOYEE_PASSWORD
    r = client.patch(f"/api/employees/{john.id}/status", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["is_active"] is False
    assert client.post("/api/auth/login", json={"email": john.email, "password": EMPLOYEE_PASSWORD}).status_code == 403
    client.patch(f"/api/employees/{john.id}/status", json={"is_active": True}, headers=admin_headers)
    assert client.post("/api/auth/login", json={"email": john.email, "password": EMPLOYEE_PASSWORD}).status_code == 200


def test_get_and_delete_employee(client, admin_headers, john):
    assert client.get(f"/api/employees/{john.id}", headers=admin_headers).json()["data"]["email"] == john.email
    assert client.delete(f"/api/employees/{john.id}", headers=admin_headers).status_code == 200
    r = client.get(f"/api/employees/{john.id}", headers=admin_headers)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
