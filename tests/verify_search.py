import os
import json
import urllib.request
import subprocess


def load_env():
    """Parses the local .env file without external dependencies."""
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value.strip("\"'")
    return env_vars


def verify_engine():
    env = load_env()
    project_number = env.get("GCP_PROJECT_NUMBER")
    engine_id = env.get("DISCOVERY_ENGINE_ID")
    location = env.get("GCP_LOCATION", "global")
    project_id = env.get("GCP_PROJECT_ID")

    print(f"[*] Verifying Engine: {engine_id} in Project: {project_number}")

    # Retrieve active OAuth token via subprocess
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    except subprocess.CalledProcessError:
        print("[!] Error: gcloud auth failed. Run 'gcloud auth login'.")
        return

    # Construct the Discovery Engine Search API endpoint
    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_number}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_search:search"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    # Query matching the synthetic document uploaded earlier
    payload = json.dumps({"query": "Google Cloud GenAI", "pageSize": 5}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            results = res_data.get("results", [])

            if results:
                print("\n[+] SUCCESS: Indexing Complete. Results Found:")
                for idx, result in enumerate(results, 1):
                    doc = result.get("document", {}).get("derivedStructData", {})
                    snippet = doc.get("snippets", [{}])[0].get("snippet", "No snippet")
                    print(f"    {idx}. {snippet}")
            else:
                print(
                    "\n[-] PENDING: No results found. The Long Running Operation "
                    "(LRO) is still indexing. Wait 5 minutes and retry."
                )

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"\n[!] HTTP Error {e.code}: {error_msg}")


if __name__ == "__main__":
    verify_engine()
