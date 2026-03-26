#!/bin/bash

# Omni-Agent Enterprise Oracle Startup Script
# This script starts all components for a fully operational system

echo "🚀 Starting Omni-Agent Enterprise Oracle System..."

# 1. Start Infrastructure (Docker)
echo "📦 Starting Docker infrastructure..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 10

# 2. Start Knowledge Worker (Background)
echo "🧠 Starting Knowledge Worker..."
cd /home/donovan/Projects/replit
python3 knowledge_worker.py &
KNOWLEDGE_PID=$!
echo "Knowledge Worker started with PID: $KNOWLEDGE_PID"

# 3. Start the Main Agent (Foreground)
echo "🎯 Starting Oracle Agent..."
echo "System is ready! You can now interact with the Oracle."
echo ""
echo "💡 Usage Examples:"
echo "  python3 agent_system.py"
echo "  Then enter prompts like:"
echo "  'Search for latest Ubuntu security updates'"
echo "  'Check system status and report to memory'"
echo "  'Analyze the logs in /var/log/syslog'"
echo ""
echo "Press Ctrl+C to stop all services."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down system..."
    if [ ! -z "$KNOWLEDGE_PID" ]; then
        kill $KNOWLEDGE_PID 2>/dev/null
        echo "✅ Knowledge Worker stopped"
    fi
    echo "📦 Stopping Docker containers..."
    docker-compose down
    echo "✅ System shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Keep script running
wait
