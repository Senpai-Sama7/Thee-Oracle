# 📚 Oracle Agent API Reference

## 📋 Overview

This document provides comprehensive API reference for Oracle Agent v5.0-hardened, including all enterprise features, workflow engine, agent collaboration, code generation, plugin system, and integration framework.

---

## 🔗 Core API Endpoints

### Base URL
```
Production: https://your-domain.com/api
Development: http://localhost:8080/api
```

### Authentication
All API endpoints require authentication using API key:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8080/api/status
```

### Response Format
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2026-03-25T12:00:00Z"
}
```

---

## 🏠 System Management

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "5.0.0-hardened",
  "uptime": 86400,
  "timestamp": "2026-03-25T12:00:00Z"
}
```

### System Status
```http
GET /status
```

**Response:**
```json
{
  "agent": {
    "initialized": true,
    "model_id": "gemini-2.0-flash-exp",
    "gcp_project": "your-project"
  },
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 23.1
  },
  "security": {
    "api_key_valid": true,
    "rate_limit_status": "active"
  }
}
```

### System Metrics
```http
GET /metrics
```

**Response:**
```json
{
  "performance": {
    "avg_response_time": 1.2,
    "requests_per_second": 45.6,
    "error_rate": 0.02
  },
  "workflows": {
    "total": 156,
    "running": 3,
    "completed": 148,
    "failed": 5
  },
  "agents": {
    "total": 12,
    "active": 8,
    "idle": 4
  }
}
```

---

## 🔄 Workflow Engine API

### Create Workflow
```http
POST /workflows
```

**Request Body:**
```json
{
  "name": "Data Processing Pipeline",
  "description": "Process customer data and generate reports",
  "steps": [
    {
      "type": "shell",
      "command": "echo 'Starting workflow'",
      "name": "Initialize",
      "timeout": 30
    },
    {
      "type": "api",
      "url": "https://api.example.com/data",
      "method": "GET",
      "name": "Fetch Data",
      "headers": {
        "Authorization": "Bearer $API_TOKEN"
      }
    },
    {
      "type": "decision",
      "condition": "status_code == 200",
      "true_path": "process_data",
      "false_path": "handle_error",
      "name": "Validate Response"
    }
  ],
  "variables": {
    "environment": "production",
    "retry_count": 3
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow_id": "wf_123456789",
    "name": "Data Processing Pipeline",
    "status": "created",
    "created_at": "2026-03-25T12:00:00Z"
  }
}
```

### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
```

**Request Body:**
```json
{
  "context": {
    "input_file": "data.csv",
    "output_format": "json"
  },
  "async": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec_123456789",
    "workflow_id": "wf_123456789",
    "status": "running",
    "started_at": "2026-03-25T12:00:00Z"
  }
}
```

### Get Workflow Status
```http
GET /workflows/{workflow_id}/executions/{execution_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec_123456789",
    "workflow_id": "wf_123456789",
    "status": "completed",
    "started_at": "2026-03-25T12:00:00Z",
    "completed_at": "2026-03-25T12:05:30Z",
    "results": [
      {
        "step": "Initialize",
        "status": "completed",
        "output": "Starting workflow"
      },
      {
        "step": "Fetch Data",
        "status": "completed",
        "output": {"status_code": 200, "data": [...]}
      }
    ],
    "context": {
      "processed_records": 1250,
      "output_file": "processed_data.json"
    }
  }
}
```

### List Workflows
```http
GET /workflows
```

**Query Parameters:**
- `status` (optional): Filter by status (created, running, completed, failed)
- `limit` (optional): Number of workflows to return (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "data": {
    "workflows": [
      {
        "workflow_id": "wf_123456789",
        "name": "Data Processing Pipeline",
        "status": "completed",
        "created_at": "2026-03-25T12:00:00Z",
        "last_execution": "2026-03-25T12:05:30Z"
      }
    ],
    "total": 156,
    "limit": 50,
    "offset": 0
  }
}
```

---

## 🤝 Agent Collaboration API

### Register Agent
```http
POST /agents
```

**Request Body:**
```json
{
  "name": "Data Processor",
  "role": "worker",
  "capabilities": [
    {
      "name": "data_processing",
      "description": "Process structured data",
      "performance_score": 0.85
    },
    {
      "name": "file_operations",
      "description": "File system operations",
      "performance_score": 0.90
    }
  ],
  "config": {
    "max_concurrent_tasks": 5,
    "timeout": 300
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_id": "agent_123456789",
    "name": "Data Processor",
    "role": "worker",
    "status": "registered",
    "created_at": "2026-03-25T12:00:00Z"
  }
}
```

### Execute Collaborative Task
```http
POST /agents/collaborate
```

**Request Body:**
```json
{
  "task_name": "Enterprise Data Analysis",
  "description": "Analyze customer data and generate insights",
  "subtasks": [
    {
      "name": "Data Collection",
      "type": "data_processing",
      "required_capabilities": ["api_access", "data_parsing"],
      "priority": "high"
    },
    {
      "name": "Statistical Analysis",
      "type": "data_analysis",
      "required_capabilities": ["statistical_analysis", "ml_models"],
      "priority": "medium"
    },
    {
      "name": "Report Generation",
      "type": "reporting",
      "required_capabilities": ["document_generation", "visualization"],
      "priority": "low"
    }
  ],
  "coordination_config": {
    "max_parallel_agents": 3,
    "timeout": 1800,
    "retry_failed_tasks": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456789",
    "task_name": "Enterprise Data Analysis",
    "status": "running",
    "assigned_agents": [
      {
        "agent_id": "agent_123456789",
        "name": "Data Processor",
        "role": "worker",
        "assigned_subtasks": ["Data Collection"]
      }
    ],
    "started_at": "2026-03-25T12:00:00Z"
  }
}
```

### Get Agent Status
```http
GET /agents/{agent_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_id": "agent_123456789",
    "name": "Data Processor",
    "role": "worker",
    "status": "idle",
    "capabilities": [
      {
        "name": "data_processing",
        "performance_score": 0.85
      }
    ],
    "current_tasks": [],
    "performance_metrics": {
      "tasks_completed": 45,
      "success_rate": 0.96,
      "avg_execution_time": 120.5
    }
  }
}
```

### List Agents
```http
GET /agents
```

**Query Parameters:**
- `status` (optional): Filter by status (idle, working, error)
- `role` (optional): Filter by role (coordinator, worker, specialist)

**Response:**
```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "agent_id": "agent_123456789",
        "name": "Data Processor",
        "role": "worker",
        "status": "idle",
        "capabilities_count": 2
      }
    ],
    "total": 12
  }
}
```

---

## 💻 Code Generation API

### Generate Code
```http
POST /code/generate
```

**Request Body:**
```json
{
  "description": "Create a Python function that processes user data from API and returns structured results with error handling",
  "language": "python",
  "code_type": "function",
  "options": {
    "include_tests": true,
    "include_documentation": true,
    "style_preferences": {
      "max_line_length": 88,
      "use_type_hints": true,
      "error_handling": "comprehensive"
    }
  },
  "context": {
    "framework": "fastapi",
    "database": "postgresql"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "code": "def process_user_data(api_url: str) -> Dict[str, Any]:\n    \"\"\"\n    Process user data from API and return structured results\n    \n    Args:\n        api_url: URL of the API endpoint\n    \n    Returns:\n        Dictionary containing processed user data\n    \"\"\"\n    try:\n        response = requests.get(api_url)\n        response.raise_for_status()\n        \n        data = response.json()\n        processed_data = {\n            'users': data.get('users', []),\n            'count': len(data.get('users', [])),\n            'processed_at': datetime.now().isoformat()\n        }\n        \n        return processed_data\n    except requests.RequestException as e:\n        return {'error': str(e), 'status': 'failed'}\n    except Exception as e:\n        return {'error': f'Unexpected error: {str(e)}', 'status': 'failed'}",
    "language": "python",
    "code_type": "function",
    "quality_score": 0.92,
    "dependencies": ["requests", "typing"],
    "usage_examples": [
      "# Example usage:\nresult = process_user_data('https://api.example.com/users')\nprint(result)"
    ],
    "explanation": "Generated Python function with comprehensive error handling, type hints, and documentation. The function makes API requests, processes the response, and returns structured data with proper error handling.",
    "test_code": "def test_process_user_data():\n    # Test cases would go here\n    pass"
  }
}
```

### Get Code Templates
```http
GET /code/templates
```

**Query Parameters:**
- `language` (optional): Filter by language
- `code_type` (optional): Filter by code type

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "name": "Python Function",
        "language": "python",
        "code_type": "function",
        "description": "Basic Python function template with type hints",
        "parameters": ["function_name", "parameters", "return_type"]
      }
    ]
  }
}
```

---

## 🔌 Plugin System API

### List Plugins
```http
GET /plugins
```

**Response:**
```json
{
  "success": true,
  "data": {
    "plugins": [
      {
        "id": "slack_integration",
        "name": "Slack Integration",
        "version": "1.2.0",
        "description": "Integrate with Slack for notifications and messaging",
        "type": "integration",
        "status": "active",
        "author": "Oracle Agent Team",
        "dependencies": ["slack-sdk"],
        "created_at": "2026-03-20T12:00:00Z"
      }
    ],
    "total": 8
  }
}
```

### Install Plugin
```http
POST /plugins/install
```

**Request Body:**
```json
{
  "source": "registry",
  "plugin_id": "slack_integration",
  "version": "latest",
  "config": {
    "slack_token": "xoxb-your-slack-token",
    "default_channel": "#oracle-agent"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "plugin_id": "slack_integration",
    "status": "installed",
    "version": "1.2.0",
    "installed_at": "2026-03-25T12:00:00Z"
  }
}
```

### Enable/Disable Plugin
```http
POST /plugins/{plugin_id}/toggle
```

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "plugin_id": "slack_integration",
    "status": "active",
    "message": "Plugin enabled successfully"
  }
}
```

### Configure Plugin
```http
PUT /plugins/{plugin_id}/config
```

**Request Body:**
```json
{
  "config": {
    "slack_token": "xoxb-new-token",
    "default_channel": "#general",
    "notification_level": "info"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "plugin_id": "slack_integration",
    "config_updated": true,
    "updated_at": "2026-03-25T12:00:00Z"
  }
}
```

---

## 🔗 Integration Framework API

### List Integrations
```http
GET /integrations
```

**Response:**
```json
{
  "success": true,
  "data": {
    "integrations": [
      {
        "id": "slack",
        "name": "Slack",
        "type": "communication",
        "status": "connected",
        "features": ["messaging", "notifications", "file_sharing"],
        "last_activity": "2026-03-25T11:30:00Z"
      }
    ]
  }
}
```

### Add Integration
```http
POST /integrations
```

**Request Body:**
```json
{
  "type": "api",
  "name": "Custom CRM",
  "config": {
    "endpoint": "https://crm.example.com/api/v1",
    "api_key": "your-api-key",
    "timeout": 30,
    "retry_count": 3
  },
  "features": ["customer_management", "sales_tracking"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "integration_id": "crm_123456789",
    "name": "Custom CRM",
    "type": "api",
    "status": "connected",
    "created_at": "2026-03-25T12:00:00Z"
  }
}
```

### Execute Integration
```http
POST /integrations/{integration_id}/execute
```

**Request Body:**
```json
{
  "operation": "get_customers",
  "parameters": {
    "limit": 100,
    "status": "active",
    "include_contacts": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "integration_id": "crm_123456789",
    "operation": "get_customers",
    "result": {
      "customers": [...],
      "total": 85,
      "execution_time": 1.2
    },
    "executed_at": "2026-03-25T12:00:00Z"
  }
}
```

---

## 📊 Analytics API

### Get Usage Analytics
```http
GET /analytics/usage
```

**Query Parameters:**
- `start_date` (optional): Start date for analytics period
- `end_date` (optional): End date for analytics period
- `granularity` (optional): Data granularity (hour, day, week, month)

**Response:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2026-03-01T00:00:00Z",
      "end_date": "2026-03-25T12:00:00Z",
      "granularity": "day"
    },
    "metrics": {
      "total_requests": 15420,
      "unique_users": 234,
      "avg_response_time": 1.2,
      "success_rate": 0.987
    },
    "breakdown": [
      {
        "date": "2026-03-25",
        "requests": 1250,
        "users": 45,
        "avg_response_time": 1.1
      }
    ]
  }
}
```

### Get Performance Analytics
```http
GET /analytics/performance
```

**Response:**
```json
{
  "success": true,
  "data": {
    "system_performance": {
      "cpu_usage": 45.2,
      "memory_usage": 67.8,
      "disk_usage": 23.1,
      "network_io": {
        "bytes_sent": 1048576,
        "bytes_received": 2097152
      }
    },
    "application_performance": {
      "workflow_success_rate": 0.95,
      "agent_utilization": 0.78,
      "plugin_performance": {
        "slack_integration": 0.99,
        "github_integration": 0.97
      }
    }
  }
}
```

---

## 🔒 Security API

### Get Security Status
```http
GET /security/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "security_score": 91,
    "last_audit": "2026-03-24T12:00:00Z",
    "vulnerabilities": {
      "critical": 0,
      "high": 0,
      "medium": 1,
      "low": 3
    },
    "compliance": {
      "gdpr": true,
      "soc2": true,
      "iso27001": true
    },
    "active_threats": 0
  }
}
```

### Rotate API Key
```http
POST /security/rotate-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "new_api_key": "new-secure-api-key-12345",
    "expires_at": "2026-06-25T12:00:00Z",
    "message": "API key rotated successfully. Update your applications."
  }
}
```

---

## 📝 Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "workflow_name",
      "issue": "Required field missing"
    }
  },
  "timestamp": "2026-03-25T12:00:00Z"
}
```

### Common Error Codes

| Error Code | HTTP Status | Description |
|-------------|--------------|-------------|
| VALIDATION_ERROR | 400 | Request validation failed |
| UNAUTHORIZED | 401 | Invalid or missing API key |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Internal server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

---

## 🔄 Rate Limiting

### Rate Limits
- **Standard**: 1000 requests per hour
- **Premium**: 10000 requests per hour
- **Enterprise**: Unlimited

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 947
X-RateLimit-Reset: 1648233600
```

### Rate Limit Response
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Try again later.",
    "retry_after": 3600
  }
}
```

---

## 🧪 Testing

### Test Environment
- **Base URL**: `https://test-api.oracle-agent.com`
- **API Key**: `test-api-key-12345`
- **Features**: All production features available

### Test Endpoints
```bash
# Test health check
curl https://test-api.oracle-agent.com/health

# Test workflow creation
curl -X POST \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workflow"}' \
  https://test-api.oracle-agent.com/workflows
```

---

## 📞 Support

### API Documentation
- **Interactive Docs**: [https://oracle-agent.com/api/docs](https://oracle-agent.com/api/docs)
- **OpenAPI Spec**: [https://oracle-agent.com/api/openapi.json](https://oracle-agent.com/api/openapi.json)

### Getting Help
- **API Issues**: [GitHub Issues](https://github.com/oracle-agent/oracle-agent/issues)
- **API Support**: [api-support@oracle-agent.com](mailto:api-support@oracle-agent.com)
- **Status Page**: [https://status.oracle-agent.com](https://status.oracle-agent.com)

---

## 📈 Changelog

### v5.0.0-hardened (2026-03-25)
- Added Workflow Engine API
- Added Agent Collaboration API
- Added Code Generation API
- Added Plugin System API
- Added Integration Framework API
- Enhanced security with rate limiting
- Added comprehensive analytics endpoints

### v4.2.0 (2026-02-15)
- Enhanced authentication system
- Added performance monitoring
- Improved error handling
- Updated security headers

---

**📚 Oracle Agent API Reference - Complete API Documentation for Enterprise Integration**
