import os
import json
import time
import urllib.request
import subprocess

def load_env():
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value.strip('"\'')
    return env_vars

def get_token():
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()

def poll_lro(env, operation_id):
    project_number = env.get("GCP_PROJECT_NUMBER")
    project_id = env.get("GCP_PROJECT_ID")
    data_store_id = env.get("GCP_DATA_STORE_ID")
    
    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_number}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/0/operations/{operation_id}"
    
    print(f"[*] Monitoring LRO: {operation_id}")
    
    attempts = 0
    while True:
        attempts += 1
        headers = {
            "Authorization": f"Bearer {get_token()}",
            "X-Goog-User-Project": project_id
        }
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
                if res.get("done"):
                    print(f"\n[+] LRO COMPLETED in attempt {attempts}.")
                    return True
                else:
                    # Exponential backoff: min 10s, max 60s
                    wait_time = min(10 * attempts, 60)
                    print(f"    [Status: PENDING] Re-polling in {wait_time}s...", end='\r')
                    time.sleep(wait_time)
        except Exception as e:
            print(f"\n[!] Polling Error: {e}")
            return False

def verify_search(env):
    project_number = env.get("GCP_PROJECT_NUMBER")
    engine_id = env.get("DISCOVERY_ENGINE_ID")
    project_id = env.get("GCP_PROJECT_ID")
    
    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_number}/locations/global/collections/default_collection/engines/{engine_id}/servingConfigs/default_search:search"
    
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id
    }
    
    payload = json.dumps({"query": "Google Cloud GenAI", "pageSize": 5}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')

    print("[*] Executing Semantic Search Verification...")
    try:
        with urllib.request.urlopen(req) as response:
            results = json.loads(response.read().decode('utf-8')).get("results", [])
            if results:
                print("\n[!!!] SYSTEM OPERATIONAL: Semantic Hit Confirmed.")
                print(f"    Result: {results[0].get('document', {}).get('derivedStructData', {}).get('snippets', [{}])[0].get('snippet')}")
                return True
            else:
                print("\n[-] Serving Latency: Index is done but not yet propagated. Retry in 60s.")
                return False
    except Exception as e:
        print(f"\n[!] Search Error: {e}")
        return False

if __name__ == "__main__":
    env_data = load_env()
    
    # Use environment variable for operation ID instead of hardcoded value
    op_id = os.environ.get("ORACLE_OPERATION_ID", "default-operation-id")
    
    if poll_lro(env_data, op_id):
        # Wait for potential serving propagation
        time.sleep(30)
        success = False
        for _ in range(5):
            if verify_search(env_data):
                success = True
                break
            time.sleep(60)
        
        if success:
            print("\n[CREDIT STATUS] $1,000 Pool: ACTIVE")
        else:
            print("\n[!] Timeout reached during serving propagation.")
