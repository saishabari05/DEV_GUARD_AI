import time
import json
import urllib.request
import urllib.error
import subprocess
import os

def request_api(method, url, data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode('utf-8')
        
    return status, body

def run_tests():
    print("Starting Flask...")
    flask_env = os.environ.copy()
    flask_env["FLASK_APP"] = "app:create_app()"
    
    process = subprocess.Popen(
        [r"venv\Scripts\flask.exe", "run", "-p", "5001"],
        env=flask_env,
        cwd=r"d:\AI-project\devguard-ai\backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(3)
    
    try:
        base_url = "http://127.0.0.1:5001/api"
        
        print("\n--- GET /api/health ---")
        status, body = request_api("GET", f"{base_url}/health")
        print(f"Status: {status}\n{body}")
        
        print("\n--- POST /api/investigate ---")
        status, body = request_api("POST", f"{base_url}/investigate", {
            "repository": "auth_bug",
            "bug_report": "Users cannot log in when their valid email address contains uppercase characters."
        })
        print(f"Status: {status}\n{body}")
        
        print("\n--- POST /api/tools/search ---")
        status, body = request_api("POST", f"{base_url}/tools/search", {
            "repository": "auth_bug",
            "query": "authenticate_user"
        })
        print(f"Status: {status}\n{body[:300]}" + ("..." if len(body) > 300 else ""))
        
        print("\n--- POST /api/tools/test ---")
        status, body = request_api("POST", f"{base_url}/tools/test", {
            "repository": "auth_bug"
        })
        print(f"Status: {status}\n{body[:500]}" + ("..." if len(body) > 500 else ""))
        
    finally:
        print("\nStopping Flask...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    run_tests()
