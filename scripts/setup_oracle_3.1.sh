#!/bin/bash
# 2026 OMNI-AGENT SETUP FOR UBUNTU 25.10 (Questing Quokka)
# Prepares the environment for Gemini 3.1 Pro Preview with Deep Think Mini

set -e

echo "[*] Updating Google GenAI SDK to v1.2.0 (March 2026)..."
pip install --upgrade google-genai pika Pillow psutil

echo "[*] Configuring Google Cloud Auth for Questing Quokka..."
# Ensures the 3.1 Pro Preview endpoint is accessible
gcloud auth application-default login --no-launch-browser

echo "[*] Setting Enterprise Oracle Environment Variables..."
# Use the specialized customtools endpoint for better shell/bash stability
export GEMINI_MODEL_ID="gemini-3.1-pro-preview-customtools"
export GOOGLE_GENAI_USE_THOUGHT_SIGNATURES=true

echo "[+] System Ready. 3.1 Pro (Deep Think Mini) is now the primary driver."
echo "[+] Environment configured for Ubuntu 25.10 (Kernel 6.17.0-6-generic)"
echo "[+] Gemini 3.1 Pro Preview endpoint: $GEMINI_MODEL_ID"
