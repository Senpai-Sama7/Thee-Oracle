#!/usr/bin/env python3
"""
Grafana Dashboard Generator for Gemini 3.1 Pro Oracle
Creates comprehensive monitoring dashboard JSON for enterprise observability
"""

import json
from typing import Dict, Any

def create_grafana_dashboard() -> Dict[str, Any]:
    """
    Generate Grafana dashboard JSON for Gemini 3.1 Pro Oracle monitoring.
    Returns complete dashboard configuration with 11 panels.
    """

    dashboard = {
        "dashboard": {
            "title": "Gemini 3.1 Pro Oracle Monitor",
            "tags": ["oracle", "gemini", "ai", "monitoring"],
            "timezone": "UTC",
            "panels": [],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "timepicker": {},
            "templating": {
                "list": []
            },
            "annotations": {
                "list": []
            },
            "refresh": "30s",
            "schemaVersion": 27,
            "version": 0,
            "links": []
        }
    }

    panels = []

    # Panel 1: Deep Think Mini Latency Distribution
    panels.append({
        "id": 1,
        "title": "Deep Think Mini Latency Distribution",
        "type": "histogram",
        "targets": [{
            "expr": "rate(oracle_thinking_duration_seconds_sum[5m]) / rate(oracle_thinking_duration_seconds_count[5m])",
            "legendFormat": "Avg Thinking Latency",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
    })

    # Panel 2: Token Consumption Breakdown
    panels.append({
        "id": 2,
        "title": "Token Consumption Mix (Input / Output / Thinking)",
        "type": "barchart",
        "targets": [
            {
                "expr": "sum(rate(oracle_tokens_input_total[5m]))",
                "legendFormat": "Input Tokens",
                "refId": "A"
            },
            {
                "expr": "sum(rate(oracle_tokens_output_total[5m]))",
                "legendFormat": "Output Tokens",
                "refId": "B"
            },
            {
                "expr": "sum(rate(oracle_tokens_thinking_total[5m]))",
                "legendFormat": "Thinking Tokens",
                "refId": "C"
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "none",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
    })

    # Panel 3: API Cost Estimate
    panels.append({
        "id": 3,
        "title": "API Cost Estimate (2026 Pricing)",
        "type": "timeseries",
        "targets": [{
            "expr": "rate(oracle_cost_estimate_dollars[5m])",
            "legendFormat": "Cost per Minute (USD)",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "currencyUSD",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 10},
                        {"color": "red", "value": 25}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
    })

    # Panel 4: Thinking vs Output Ratio
    panels.append({
        "id": 4,
        "title": "Thinking vs Output Efficiency Ratio",
        "type": "gauge",
        "targets": [{
            "expr": "sum(oracle_tokens_thinking_total) / sum(oracle_tokens_output_total)",
            "legendFormat": "Thinking/Output Ratio",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit",
                "min": 0,
                "max": 3,
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 2}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
    })

    # Panel 5: API Request Rate
    panels.append({
        "id": 5,
        "title": "API Request Rate by Status",
        "type": "timeseries",
        "targets": [
            {
                "expr": "rate(oracle_api_requests_total{status=\"success\"}[5m])",
                "legendFormat": "Success",
                "refId": "A"
            },
            {
                "expr": "rate(oracle_api_requests_total{status=\"error\"}[5m])",
                "legendFormat": "Error",
                "refId": "B"
            },
            {
                "expr": "rate(oracle_api_requests_total{status=\"timeout\"}[5m])",
                "legendFormat": "Timeout",
                "refId": "C"
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "reqps",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
    })

    # Panel 6: Session Duration Distribution
    panels.append({
        "id": 6,
        "title": "Session Duration Distribution",
        "type": "histogram",
        "targets": [{
            "expr": "oracle_session_duration_seconds",
            "legendFormat": "Session Duration",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
    })

    # Panel 7: Database Size Monitoring
    panels.append({
        "id": 7,
        "title": "Oracle Database Size",
        "type": "timeseries",
        "targets": [{
            "expr": "oracle_database_size_bytes",
            "legendFormat": "Database Size",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "bytes",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 104857600},  # 100MB
                        {"color": "red", "value": 524288000}     # 500MB
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
    })

    # Panel 8: Active Sessions
    panels.append({
        "id": 8,
        "title": "Active Sessions Count",
        "type": "stat",
        "targets": [{
            "expr": "oracle_active_sessions",
            "legendFormat": "Active Sessions",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 5},
                        {"color": "red", "value": 10}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
    })

    # Panel 9: Service Uptime
    panels.append({
        "id": 9,
        "title": "Oracle Service Uptime",
        "type": "stat",
        "targets": [{
            "expr": "oracle_service_uptime_seconds",
            "legendFormat": "Uptime",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 300},   # 5 minutes
                        {"color": "red", "value": 60}       # 1 minute
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 32}
    })

    # Panel 10: Memory Usage
    panels.append({
        "id": 10,
        "title": "Oracle Memory Usage",
        "type": "timeseries",
        "targets": [{
            "expr": "oracle_memory_usage_bytes",
            "legendFormat": "Memory Usage",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "bytes",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 536870912},  # 512MB
                        {"color": "red", "value": 1073741824}    # 1GB
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 32}
    })

    # Panel 11: Thinking Level Distribution
    panels.append({
        "id": 11,
        "title": "Thinking Level Distribution",
        "type": "piechart",
        "targets": [{
            "expr": "sum(oracle_tokens_thinking_total) by (thinking_level)",
            "legendFormat": "{{thinking_level}}",
            "refId": "A"
        }],
        "fieldConfig": {
            "defaults": {
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 40}
    })

    dashboard["dashboard"]["panels"] = panels

    return dashboard

def main():
    """Generate and save the Grafana dashboard JSON."""
    dashboard = create_grafana_dashboard()

    output_file = "oracle_grafana_dashboard.json"
    with open(output_file, 'w') as f:
        json.dump(dashboard, f, indent=2)

    print(f"[+] Grafana dashboard JSON generated: {output_file}")
    print("[+] Import this file into Grafana to create the Oracle monitoring dashboard")
    print("[+] Dashboard includes 11 panels for comprehensive Gemini 3.1 Pro observability")

if __name__ == "__main__":
    main()
