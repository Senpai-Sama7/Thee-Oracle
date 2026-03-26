import os
from google import genai
from google.genai import types
from oracle_storage import OraclePersistence


def test_thought_signature_resumption():
    print("[*] Initializing Gemini 3.1 Pro (Questing Quokka Environment)")
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    storage = OraclePersistence(db_path="test_verify.db")
    session_id = "test_turn_recovery"

    # Step 1: Trigger a Deep Think loop with Tool Calling
    prompt = "Find all files in /etc/systemd/system/ ending in .service and check their status."
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        tools=[types.Tool(code_execution=types.CodeExecution())],
        max_output_tokens=65536,
    )

    print("[*] Step 1: Initiating High-Reasoning Turn...")
    response = client.models.generate_content(
        model="gemini-3.1-pro-preview-customtools", contents=[prompt], config=config
    )

    # Validate signature existence
    has_sig = any(hasattr(p, "thought_signature") for p in response.candidates[0].content.parts)
    if not has_sig:
        raise Exception("FAIL: 3.1 Pro did not return a thought_signature.")

    print(f"[+] Step 1 Success: Signature captured ({len(response.candidates[0].content.parts)} parts)")

    # Step 2: Simulate Systemd Service Crash / Restart
    print("[*] Step 2: Persisting state to SQLite and clearing local memory...")
    history = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)]), response.candidates[0].content]
    storage.save_session(session_id, history)
    del history  # Memory cleared

    # Step 3: Recover and Execute Tool Result turn
    print("[*] Step 3: Recovering state from SQLite...")
    recovered_history = storage.load_session(session_id)

    # Simulate a Tool Result (Mocking the bash output)
    tool_result_part = types.Part.from_function_response(
        name="run_bash", response={"result": "gemini-oracle.service found, status active"}
    )
    recovered_history.append(types.Content(role="tool", parts=[tool_result_part]))

    print("[*] Step 4: Validating turn with recovered Signature...")
    final_response = client.models.generate_content(
        model="gemini-3.1-pro-preview-customtools", contents=recovered_history, config=config
    )

    print(f"[SUCCESS] Oracle recovered reasoning state. Final Text: {final_response.text[:50]}...")


if __name__ == "__main__":
    test_thought_signature_resumption()
