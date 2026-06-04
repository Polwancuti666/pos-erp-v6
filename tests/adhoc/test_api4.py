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

# Get POS auth (like KSR001 does)
pos_login = api("POST", "/pos/auth", {"staff_id": "KSR001", "pin": "1234"})
print("POS Login:", json.dumps(pos_login, indent=2)[:300])

# Get available staff
staff = api("GET", "/master/user", token=token)
print("\nStaff:", json.dumps(staff, indent=2)[:500])

# Get available staff via POS
beds = api("GET", "/pos/beds", token=pos_login.get("token", ""))
print("\nBeds:", json.dumps(beds, indent=2)[:300])

# Create transaction via POS API (this is what the POS frontend uses)
tx = api("POST", "/api/transaction", {"branch_code": "HQ", "device_id": "POS-01", "cashier_id": "KSR001"}, token)
print("\nCreate TX:", json.dumps(tx, indent=2)[:300])
tx_id = tx.get("transaction_id", "")

if tx_id:
    # Try with different staff (KSR002)
    add = api("POST", "/api/transaction/" + tx_id + "/add-item", {
        "service_id": "4946e9aa-f43d-46fa-b92e-d89b28191d7b",
        "staff_id": "KSR002",
        "quantity": 1
    }, token)
    print("\nAdd Item (KSR002):", json.dumps(add, indent=2)[:400])
