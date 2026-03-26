# Define and create the Systemd Service Unit
sudo tee /etc/systemd/system/gemini-oracle.service <<EOF
[Unit]
Description=Gemini 3.1 Pro Enterprise Oracle Orchestrator
After=network.target rabbitmq-server.service postgresql.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)

# 2026 Frontier Environment Variables
Environment=PYTHONUNBUFFERED=1
Environment=GOOGLE_API_KEY=$(echo $GOOGLE_API_KEY)
Environment=GEMINI_MODEL_ID=gemini-3.1-pro-preview-customtools
Environment=THINKING_LEVEL=HIGH

# Execution Command
ExecStart=$(which python3) agent_system.py

# Crash Recovery Logic
Restart=on-failure
RestartSec=10

# Allow for Deep Think latency (up to 2 mins per turn)
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

# Reload and Enable
sudo systemctl daemon-reload
sudo systemctl enable gemini-oracle.service
sudo systemctl start gemini-oracle.service

echo "[+] Gemini 3.1 Pro Oracle is now a background daemon on Questing Quokka."
echo "[+] Service configured with thought signature persistence and Deep Think Mini support."
