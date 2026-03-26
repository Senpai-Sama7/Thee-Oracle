#!/bin/bash
# Gemini 3.1 Pro Usage Monitoring & Thinking Level Management
# Monitors API token usage and switches thinking_level to "MEDIUM" if 80% budget exhausted

# Configuration
DAILY_BUDGET=250  # 3.1 Pro Preview daily request limit (Tier 1)
THRESHOLD_PERCENT=80  # Switch to MEDIUM thinking at 80% usage
LOG_FILE="/var/log/oracle/api_usage.log"

# Environment variables (set these in your environment)
# GOOGLE_API_KEY - Your Google API key
# GEMINI_MODEL_ID - Current model (gemini-3.1-pro-preview-customtools)
# THINKING_LEVEL - Current thinking level (HIGH/MEDIUM)

# Function to check current API usage
check_api_usage() {
    local today=$(date +%Y-%m-%d)
    local requests_today=0
    
    # Count requests from log file for today
    if [ -f "$LOG_FILE" ]; then
        requests_today=$(grep "$today" "$LOG_FILE" | wc -l)
    fi
    
    echo "$requests_today"
}

# Function to calculate usage percentage
calculate_percentage() {
    local used=$1
    local budget=$2
    local percentage=$(( (used * 100) / budget ))
    echo "$percentage"
}

# Function to switch thinking level
switch_thinking_level() {
    local new_level=$1
    local current_level=${THINKING_LEVEL:-HIGH}
    
    if [ "$new_level" != "$current_level" ]; then
        echo "[*] Switching thinking level from $current_level to $new_level"
        export THINKING_LEVEL="$new_level"
        
        # Update systemd service environment if running
        if systemctl is-active --quiet gemini-oracle.service; then
            sudo systemctl set-environment THINKING_LEVEL="$new_level"
            sudo systemctl restart gemini-oracle.service
            echo "[+] Updated systemd service thinking level to $new_level"
        fi
        
        # Log the change
        echo "$(date): Thinking level switched to $new_level (usage: $used/$budget requests)" >> "$LOG_FILE"
    fi
}

# Main monitoring function
monitor_and_adjust() {
    local used=$(check_api_usage)
    local percentage=$(calculate_percentage "$used" "$DAILY_BUDGET")
    
    echo "📊 API Usage Monitor (Gemini 3.1 Pro)"
    echo "======================================"
    echo "Requests Today: $used / $DAILY_BUDGET"
    echo "Usage Percentage: $percentage%"
    
    # Check if we need to switch to MEDIUM thinking
    if [ "$percentage" -ge "$THRESHOLD_PERCENT" ]; then
        echo "⚠️  Usage above $THRESHOLD_PERCENT% threshold"
        switch_thinking_level "MEDIUM"
        echo "✅ Switched to MEDIUM thinking to conserve API budget"
    else
        echo "✅ Usage within safe limits - maintaining HIGH thinking"
    fi
    
    echo "Current Thinking Level: ${THINKING_LEVEL:-HIGH}"
    echo "======================================"
}

# Function to log API request (call this after each API call)
log_api_request() {
    local endpoint="$1"
    local tokens_used="$2"
    echo "$(date): API call to $endpoint, tokens: $tokens_used" >> "$LOG_FILE"
}

# Function to check if we should make an API call
should_make_call() {
    local used=$(check_api_usage)
    local percentage=$(calculate_percentage "$used" "$DAILY_BUDGET")
    
    if [ "$percentage" -ge 95 ]; then
        echo "❌ API budget nearly exhausted ($percentage%). Blocking API calls."
        return 1
    fi
    
    return 0
}

# Run monitoring
case "$1" in
    "monitor")
        monitor_and_adjust
        ;;
    "log")
        log_api_request "$2" "$3"
        ;;
    "check")
        should_make_call
        ;;
    "status")
        echo "API Usage Status:"
        check_api_usage
        echo "Budget: $DAILY_BUDGET"
        echo "Threshold: $THRESHOLD_PERCENT%"
        echo "Current Level: ${THINKING_LEVEL:-HIGH}"
        ;;
    *)
        echo "Usage: $0 {monitor|log|check|status}"
        echo "  monitor - Check usage and adjust thinking level"
        echo "  log <endpoint> <tokens> - Log API usage"
        echo "  check - Check if API call should be made"
        echo "  status - Show current status"
        ;;
esac
