"""
Oracle Agent Integration Framework
"""

from __future__ import annotations

from enum import Enum
from typing import Any, cast

import requests

from .network_guard import HTTP_REDIRECT_BLOCKED_ERROR, validate_outbound_http_url


class IntegrationType(Enum):
    API = "api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    WEBHOOK = "webhook"


class Integration:
    def __init__(
        self,
        integration_id: str,
        integration_type: IntegrationType,
        config: dict[str, Any],
    ) -> None:
        self.id = integration_id
        self.type = integration_type
        self.config = config
        self.status = "inactive"

    def connect(self) -> bool:
        """Connect to integration."""
        try:
            if self.type == IntegrationType.API:
                return self._connect_api()
            if self.type == IntegrationType.DATABASE:
                return self._connect_database()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def _connect_api(self) -> bool:
        """Connect to API integration."""
        url = self.config.get("url")
        if not isinstance(url, str) or not self._is_allowed_url(url):
            return False
        response = requests.get(url, timeout=10, allow_redirects=False)
        if 300 <= response.status_code < 400:
            return False
        return response.status_code == 200

    def _connect_database(self) -> bool:
        """Connect to database integration."""
        return True

    def execute(self, operation: str, data: dict[str, Any]) -> Any:
        """Execute integration operation."""
        if self.type == IntegrationType.API:
            return self._execute_api(operation, data)
        if self.type == IntegrationType.DATABASE:
            return self._execute_database(operation, data)
        return {"result": f"Executed {operation}"}

    def _execute_api(self, operation: str, data: dict[str, Any]) -> dict[str, Any]:
        """Execute API operation."""
        del operation
        url_value = self.config.get("url")
        if not isinstance(url_value, str):
            raise ValueError("API integration missing URL")
        error = validate_outbound_http_url(url_value)
        if error:
            raise ValueError(error)

        method = str(data.get("method", "GET"))
        headers = data.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}

        response = requests.request(
            method,
            url_value,
            headers=headers,
            json=data.get("body"),
            timeout=10,
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            raise ValueError(HTTP_REDIRECT_BLOCKED_ERROR)
        return {
            "status_code": response.status_code,
            "data": response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text,
        }

    @staticmethod
    def _is_allowed_url(url: str) -> bool:
        return validate_outbound_http_url(url) is None

    def _execute_database(self, operation: str, data: dict[str, Any]) -> dict[str, Any]:
        """Execute database operation."""
        return {"result": f"Executed {operation} on database", "data": data}


class IntegrationManager:
    def __init__(self) -> None:
        self.integrations: dict[str, Integration] = {}
        self.config_file = "integrations.json"

    def add_integration(
        self,
        integration_id: str,
        integration_type: IntegrationType,
        config: dict[str, Any],
    ) -> bool:
        """Add integration."""
        integration = Integration(integration_id, integration_type, config)

        if integration.connect():
            self.integrations[integration_id] = integration
            return True
        return False

    def remove_integration(self, integration_id: str) -> bool:
        """Remove integration."""
        if integration_id in self.integrations:
            del self.integrations[integration_id]
            return True
        return False

    def get_integration(self, integration_id: str) -> Integration | None:
        """Get integration by ID."""
        return self.integrations.get(integration_id)

    def list_integrations(self) -> list[dict[str, Any]]:
        """List all integrations."""
        return [
            {
                "id": integration.id,
                "type": integration.type.value,
                "status": integration.status,
                "config": {
                    key: value for key, value in integration.config.items() if key not in ["password", "token", "key"]
                },
            }
            for integration in self.integrations.values()
        ]

    def execute_integration(self, integration_id: str, operation: str, data: dict[str, Any]) -> Any:
        """Execute integration operation."""
        integration = self.get_integration(integration_id)
        if integration:
            return integration.execute(operation, data)
        raise ValueError(f"Integration {integration_id} not found")


class SlackIntegration(Integration):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__("slack", IntegrationType.API, config)

    def send_message(self, channel: str, message: str) -> dict[str, Any]:
        """Send message to Slack."""
        data = {"channel": channel, "text": message}
        result = self.execute("send_message", {"method": "POST", "body": data})
        return cast(dict[str, Any], result)


class GitHubIntegration(Integration):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__("github", IntegrationType.API, config)

    def create_repository(self, name: str, description: str) -> dict[str, Any]:
        """Create GitHub repository."""
        data = {"name": name, "description": description}
        headers = {"Authorization": f"token {self.config.get('token')}"}
        result = self.execute("create_repo", {"method": "POST", "headers": headers, "body": data})
        return cast(dict[str, Any], result)


class AWSIntegration(Integration):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__("aws", IntegrationType.API, config)

    def create_s3_bucket(self, bucket_name: str) -> dict[str, Any]:
        """Create S3 bucket."""
        return {"result": f"Created S3 bucket: {bucket_name}"}
