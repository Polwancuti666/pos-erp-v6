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
    except Exception as e:
        return {"error": str(e)}

# Login
login = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
token = login.get("access_token", "")
print("Login: OK, token length=" + str(len(token)))

# Create transaction
tx = api("POST", "/api/transaction", {"branch_code": "HQ", "device_id": "POS-01", "cashier_id": "KSR001"}, token)
print("Create TX:", json.dumps(tx, indent=2)[:300])

tx_id = tx.get("transaction_id", "")
if tx_id:
    # Add item
    add = api("POST", "/api/transaction/" + tx_id + "/add-item", {
        "service_id": "4946e9aa-f43d-46fa-b92e-d89b28191d7b",
        "staff_id": "KSR001",
        "quantity": 1
    }, token)
    print("Add Item:", json.dumps(add, indent=2)[:300])
