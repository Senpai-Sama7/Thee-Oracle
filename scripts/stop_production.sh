#!/bin/bash

# Oracle Agent Production Stop Script
# Gracefully shuts down all components

set -e

echo "🛑 Stopping Oracle Agent Production System..."

# Stop Oracle Agent if running
if [ -f ".oracle_agent.pid" ]; then
    echo "📋 Reading PID file..."
    PIDS=$(cat .oracle_agent.pid)
    
    for PID in $PIDS; do
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping process $PID..."
            kill "$PID"
            
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$PID" 2>/dev/null; then
                    echo "✅ Process $PID stopped gracefully"
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                echo "⚡ Force killing process $PID..."
                kill -9 "$PID"
            fi
        else
            echo "⚠️  Process $PID not found"
        fi
    done
    
    rm -f .oracle_agent.pid
else
    echo "ℹ️  No PID file found, checking for running processes..."
    # Kill any remaining oracle processes
    pkill -f "python3 main.py" || true
fi

# Stop infrastructure services
echo "📦 Stopping infrastructure services..."
docker-compose -f infrastructure/docker-compose.yml down

# Clean up logs if older than 7 days
echo "🧹 Cleaning up old logs..."
find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true

echo "✅ Oracle Agent Production System Stopped"
echo "📊 Logs preserved in logs/ directory"
