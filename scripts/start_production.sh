#!/bin/bash

# Oracle Agent Production Startup Script
# This script starts all components with production configuration

set -e

echo "🚀 Starting Oracle Agent Production System..."

# Check environment configuration
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "📋 Copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID not configured"
    exit 1
fi

# Check GCP authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    echo "❌ Error: No active GCP authentication found"
    echo "🔧 Run: gcloud auth application-default login"
    exit 1
fi

echo "✅ Environment validation passed"

# Start infrastructure services
echo "📦 Starting infrastructure services..."
docker-compose -f infrastructure/docker-compose.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if ! docker-compose -f infrastructure/docker-compose.yml ps | grep -q "Up"; then
    echo "❌ Error: Some services failed to start"
    docker-compose -f infrastructure/docker-compose.yml ps
    exit 1
fi

# Start Oracle Agent with production configuration
echo "🎯 Starting Oracle Agent..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Start in background for production
nohup python3 main.py > logs/oracle.log 2>&1 &
ORACLE_PID=$!

echo "📝 Oracle Agent started with PID: $ORACLE_PID"
echo "📊 Logs available at: logs/oracle.log"

# Wait for agent to initialize
sleep 5

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✅ Oracle Agent is healthy and ready"
else
    echo "⚠️  Health check failed, but agent may still be starting"
fi

# Start monitoring if enabled
if [ "$METRICS_ENABLED" = "true" ]; then
    echo "📈 Starting monitoring services..."
    # Start Prometheus if configured
    if command -v prometheus >/dev/null 2>&1; then
        prometheus --config.file=infrastructure/prometheus.yml &
        PROMETHEUS_PID=$!
        echo "📊 Prometheus started with PID: $PROMETHEUS_PID"
    fi
fi

echo ""
echo "🎉 Oracle Agent Production System Started Successfully!"
echo "📋 System Components:"
echo "  • Oracle Agent: PID $ORACLE_PID"
echo "  • Infrastructure: Docker Compose services"
echo "  • Logs: logs/oracle.log"
echo "  • Health Check: http://localhost:8080/health"
echo "  • Metrics: http://localhost:9090 (if enabled)"
echo ""
echo "🛑 To stop: ./scripts/stop_production.sh"
echo "📊 To monitor: tail -f logs/oracle.log"

# Save PIDs for cleanup
echo $ORACLE_PID > .oracle_agent.pid
if [ ! -z "$PROMETHEUS_PID" ]; then
    echo $PROMETHEUS_PID >> .oracle_agent.pid
fi

exit 0
