import json
import urllib.request

BASE = "http://localhost:8000"

def api(method, path, data=None, token=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "body": e.read().decode()[:500]}
    except Exception as e:
        return {"error": str(e)}

# Login
login = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
token = login.get("access_token", "")
print("Login: OK")

# Create transaction
tx = api("POST", "/api/transaction", {"branch_code": "HQ", "device_id": "POS-01", "cashier_id": "KSR001"}, token)
tx_id = tx.get("transaction_id", "")
print("TX ID:", tx_id)

# Try different add-item formats
for attempt, payload in enumerate([
    {"service_id": "4946e9aa-f43d-46fa-b92e-d89b28191d7b", "staff_id": "KSR001", "quantity": 1},
    {"treatment_id": "4946e9aa-f43d-46fa-b92e-d89b28191d7b", "staff_id": "KSR001"},
    {"service_id": "4946e9aa-f43d-46fa-b92e-d89b28191d7b"},
], 1):
    result = api("POST", "/api/transaction/" + tx_id + "/add-item", payload, token)
    print("Attempt", attempt, "payload:", json.dumps(payload)[:80])
    print("Result:", json.dumps(result, indent=2)[:400])
    print()
