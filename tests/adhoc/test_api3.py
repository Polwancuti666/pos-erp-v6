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

# Get available staff
users = api("GET", "/master/user", token=token)
print("Users:", json.dumps(users, indent=2)[:500])

# Get all transactions to see lock status
txns = api("GET", "/pos/transactions", token=token)
print("\nTransactions:", json.dumps(txns, indent=2)[:500])
