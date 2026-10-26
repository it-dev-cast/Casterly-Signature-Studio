"""End-to-end acceptance scenario against a RUNNING backend (real HTTP, real database).

    python scripts/acceptance.py --base-url http://localhost:8000

Uses the development admin created by `python -m app.seed` unless overridden with
--email / --password. Safe to re-run: existing employees are reused.
"""
import argparse
import io
import sys

import httpx
from PIL import Image, ImageDraw

STEPS: list[str] = []


def step(msg: str) -> None:
    STEPS.append(msg)
    print(f"  [ok] {msg}")


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  [FAIL] {msg}")
        sys.exit(1)


def data(r: httpx.Response):
    body = r.json()
    check(body.get("success") is True, f"{r.request.method} {r.request.url.path} -> {r.status_code} {body}")
    return body["data"]


def banner_image(text: str, bg: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (1200, 240), bg)
    ImageDraw.Draw(img).text((60, 90), text, fill=(255, 255, 255), font_size=56)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ensure_employee(c: httpx.Client, payload: dict) -> dict:
    found = data(c.get("/api/employees", params={"q": payload["email"]}))["items"]
    if found:
        return found[0]
    return data(c.post("/api/employees", json=payload))


def signature(c: httpx.Client, emp_id: int) -> dict:
    return data(c.get(f"/api/signatures/{emp_id}"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--email", default="admin@example.com")
    p.add_argument("--password", default="Admin@12345")
    args = p.parse_args()

    c = httpx.Client(base_url=args.base_url, timeout=15)
    print("Signature Studio acceptance scenario")

    # 1-3 backend up + login
    check(c.get("/api/health").status_code == 200, "backend is not reachable")
    login = data(c.post("/api/auth/login", json={"email": args.email, "password": args.password}))
    c.headers["Authorization"] = f"Bearer {login['access_token']}"
    step("Logged in as admin")

    # 4-5 overview + employees
    data(c.get("/api/overview"))
    step("Opened Overview")
    data(c.get("/api/employees"))
    step("Opened Employees")

    # 6-7 add employees
    rahul = ensure_employee(c, {
        "employee_code": "EMP-101", "first_name": "Rahul", "last_name": "Kumar",
        "designation": "Senior Software Developer", "department": "Engineering", "email": "rahul@example.com",
    })
    priya = ensure_employee(c, {
        "employee_code": "EMP-102", "first_name": "Priya", "last_name": "Sharma",
        "designation": "HR Manager", "department": "Human Resources", "email": "priya@example.com",
    })
    step(f"Employees present: {rahul['full_name']} (#{rahul['id']}), {priya['full_name']} (#{priya['id']})")

    # 8-13 create Company Anniversary as draft
    data(c.get("/api/banners"))
    upload = data(c.post("/api/uploads", data={"kind": "banner"},
                         files={"file": ("anniversary.png", banner_image("Celebrating 10 Years", (30, 58, 138)), "image/png")}))
    step(f"Uploaded banner image -> {upload['url']}")
    anniversary_in = {
        "name": "Company Anniversary", "title": "Celebrating 10 Years",
        "description": "Thank you for being part of our journey.",
        "image_url": upload["path"], "target_url": "https://www.example.com/10-years",
    }
    preview = data(c.post("/api/banners/preview", json=anniversary_in))
    check(upload["path"] in preview["html"], "preview does not contain the uploaded image")
    step("Previewed banner")
    anniversary = data(c.post("/api/banners", json=anniversary_in))
    check(anniversary["status"] == "DRAFT", "new banner should be DRAFT")
    step(f"Saved draft 'Company Anniversary' (#{anniversary['id']}) -> DRAFT")

    # 14-17 publish
    pub = data(c.post(f"/api/banners/{anniversary['id']}/publish"))
    check(pub["status"] == "PUBLISHED", "banner should be PUBLISHED")
    step("Published 'Company Anniversary' -> PUBLISHED")
    ov = data(c.get("/api/overview"))
    check(ov["current_banner"] and ov["current_banner"]["id"] == anniversary["id"], "overview current banner mismatch")
    step("Overview shows 'Company Anniversary' as current banner")

    # 18-21 signatures contain their own info + anniversary banner
    for emp, name, title in ((rahul, "Rahul Kumar", "Senior Software Developer"), (priya, "Priya Sharma", "HR Manager")):
        s = signature(c, emp["id"])
        check(name in s["html"] and title in s["html"] and emp["email"] in s["html"], f"{name} details missing")
        check(s["banner"]["name"] == "Company Anniversary" and upload["path"] in s["html"], f"{name} banner wrong")
        step(f"{name}'s signature = {name} info + Company Anniversary banner")

    # 22-24 New Year Campaign
    ny_upload = data(c.post("/api/uploads", data={"kind": "banner"},
                            files={"file": ("new-year.png", banner_image("Happy New Year 2027", (127, 29, 29)), "image/png")}))
    new_year = data(c.post("/api/banners", json={
        "name": "New Year Campaign", "title": "Happy New Year 2027",
        "description": "Wishing you a successful year ahead.", "image_url": ny_upload["path"],
        "target_url": "https://www.example.com/new-year",
    }))
    data(c.post(f"/api/banners/{new_year['id']}/publish"))
    step("Created and published 'New Year Campaign'")
    current = data(c.get("/api/banners/current"))["banner"]
    check(current["id"] == new_year["id"], "current banner should be New Year Campaign")
    old = data(c.get(f"/api/banners/{anniversary['id']}"))
    check(old["status"] == "DRAFT" and not old["is_current"], "Company Anniversary should no longer be current")
    step("'Company Anniversary' is no longer current (back to DRAFT)")

    # 25-28 signatures now show New Year Campaign
    for emp, name in ((rahul, "Rahul Kumar"), (priya, "Priya Sharma")):
        s = signature(c, emp["id"])
        check(s["banner"]["name"] == "New Year Campaign" and ny_upload["path"] in s["html"], f"{name} should show New Year")
        check(upload["path"] not in s["html"], f"{name} still shows anniversary")
        step(f"{name}'s signature now shows New Year Campaign")

    # 29-30 unpublish -> no banner anywhere
    data(c.post(f"/api/banners/{new_year['id']}/unpublish"))
    check(data(c.get("/api/banners/current"))["banner"] is None, "no banner should be current")
    for emp, name in ((rahul, "Rahul Kumar"), (priya, "Priya Sharma")):
        s = signature(c, emp["id"])
        check(s["banner"] is None and "/uploads/banners/" not in s["html"], f"{name} should have no banner")
    step("Unpublished 'New Year Campaign' -> neither employee has a banner")

    # 31 audit
    actions = [i["action"] for i in data(c.get("/api/audit-logs", params={"page_size": 50}))["items"]]
    for expected in ("BANNER_PUBLISHED", "BANNER_UNPUBLISHED", "BANNER_CREATED", "LOGIN"):
        check(expected in actions, f"audit log missing {expected}")
    step(f"Audit log contains {', '.join(sorted(set(actions)))}")

    print(f"\nPASSED - {len(STEPS)} checks")


if __name__ == "__main__":
    main()
