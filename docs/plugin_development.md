# 🔌 Oracle Agent Plugin Development Guide

## 📋 Overview

This guide provides comprehensive information for developing plugins for Oracle Agent v5.0-hardened. Plugins extend the platform's capabilities by adding custom tools, integrations, and functionality while maintaining security and performance standards.

---

## 🏗️ Plugin Architecture

### Plugin Types
- **Tool Plugins**: Custom tools and utilities
- **Skill Plugins**: Specialized AI capabilities
- **Integration Plugins**: External service connections
- **Middleware Plugins**: Request/response processing
- **UI Component Plugins**: Custom GUI components

### Plugin Lifecycle
1. **Discovery**: Plugin is discovered by the plugin manager
2. **Loading**: Plugin code is loaded into memory
3. **Initialization**: Plugin is initialized with configuration
4. **Registration**: Plugin capabilities are registered
5. **Execution**: Plugin functions are called as needed
6. **Cleanup**: Plugin resources are cleaned up on unload

### Security Model
- **Sandboxing**: Plugins run in isolated environments
- **Permission System**: Plugins request specific permissions
- **Resource Limits**: CPU, memory, and network limits enforced
- **API Validation**: All plugin APIs are validated

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Understanding of Oracle Agent architecture
- Basic knowledge of async/await patterns

### Development Environment
```bash
# Clone Oracle Agent
git clone https://github.com/oracle-agent/oracle-agent.git
cd oracle-agent

# Create plugin development environment
python3 -m venv plugin-dev
source plugin-dev/bin/activate
pip install -r requirements.txt

# Create plugins directory
mkdir plugins
cd plugins
```

### Basic Plugin Structure
```
my_plugin/
├── __init__.py
├── plugin.py
├── requirements.txt
├── config.json
├── README.md
├── tests/
│   ├── __init__.py
│   └── test_plugin.py
└── docs/
    └── usage.md
```

---

## 📝 Plugin Development

### Basic Plugin Template

```python
# plugins/my_plugin/plugin.py
from typing import Dict, List, Any, Optional
from src.oracle.plugin_system import Plugin, PluginType

class MyPlugin:
    """Plugin metadata"""
    name = "My Custom Plugin"
    version = "1.0.0"
    description = "A custom plugin for specialized processing"
    type = PluginType.TOOL
    author = "Your Name"
    homepage = "https://github.com/yourname/my-plugin"
    repository = "https://github.com/yourname/my-plugin.git"
    license = "MIT"
    dependencies = ["requests>=2.25.0", "pandas>=1.3.0"]
    min_oracle_version = "5.0.0"
    permissions = ["network", "file_read"]
    
    def __init__(self):
        """Initialize plugin"""
        self.initialized = False
        self.config = {}
        self.plugin_id = None
        self.plugin_manager = None
        
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """Initialize plugin with configuration"""
        try:
            self.config = config or {}
            self._validate_config()
            self._setup_resources()
            self.initialized = True
            return True
        except Exception as e:
            print(f"Plugin initialization failed: {e}")
            return False
    
    def _validate_config(self):
        """Validate plugin configuration"""
        required_keys = ["api_endpoint"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Required config key missing: {key}")
    
    def _setup_resources(self):
        """Setup plugin resources"""
        # Initialize connections, caches, etc.
        pass
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools provided by this plugin"""
        return [
            {
                "name": "custom_process",
                "description": "Custom data processing tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "Data to process"
                        },
                        "options": {
                            "type": "object",
                            "description": "Processing options",
                            "properties": {
                                "format": {"type": "string", "enum": ["json", "csv", "xml"]},
                                "timeout": {"type": "integer", "minimum": 1, "maximum": 300}
                            }
                        }
                    },
                    "required": ["data"]
                },
                "function": self.custom_process
            },
            {
                "name": "custom_analyze",
                "description": "Custom data analysis tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset": {"type": "string", "description": "Dataset path or URL"},
                        "analysis_type": {"type": "string", "enum": ["statistical", "ml", "visualization"]}
                    },
                    "required": ["dataset"]
                },
                "function": self.custom_analyze
            }
        ]
    
    async def custom_process(self, data: List[Any], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Custom processing implementation"""
        try:
            # Validate inputs
            if not data:
                return {"success": False, "error": "No data provided"}
            
            # Process data
            processed_count = len(data)
            format_type = options.get("format", "json") if options else "json"
            
            # Apply processing logic
            result = {
                "processed_items": processed_count,
                "format": format_type,
                "processed_at": str(datetime.now()),
                "plugin_version": self.version
            }
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "plugin": self.name,
                    "version": self.version,
                    "execution_time": 0.5
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "processing_error"
            }
    
    async def custom_analyze(self, dataset: str, analysis_type: str = "statistical") -> Dict[str, Any]:
        """Custom analysis implementation"""
        try:
            # Load dataset
            data = self._load_dataset(dataset)
            
            # Perform analysis
            if analysis_type == "statistical":
                result = self._statistical_analysis(data)
            elif analysis_type == "ml":
                result = self._ml_analysis(data)
            elif analysis_type == "visualization":
                result = self._visualization_analysis(data)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            return {
                "success": True,
                "result": result,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "analysis_error"
            }
    
    def _load_dataset(self, dataset: str) -> Any:
        """Load dataset from file or URL"""
        if dataset.startswith("http"):
            # Load from URL
            import requests
            response = requests.get(dataset)
            response.raise_for_status()
            return response.json()
        else:
            # Load from file
            import json
            with open(dataset, 'r') as f:
                return json.load(f)
    
    def _statistical_analysis(self, data: Any) -> Dict[str, Any]:
        """Perform statistical analysis"""
        import statistics
        
        if isinstance(data, list) and data:
            numeric_data = [x for x in data if isinstance(x, (int, float))]
            return {
                "count": len(data),
                "mean": statistics.mean(numeric_data) if numeric_data else None,
                "median": statistics.median(numeric_data) if numeric_data else None,
                "std_dev": statistics.stdev(numeric_data) if len(numeric_data) > 1 else None
            }
        return {"error": "Invalid data for statistical analysis"}
    
    def _ml_analysis(self, data: Any) -> Dict[str, Any]:
        """Perform machine learning analysis"""
        # Placeholder for ML analysis
        return {
            "model_type": "classification",
            "accuracy": 0.85,
            "features": len(data) if isinstance(data, list) else 0
        }
    
    def _visualization_analysis(self, data: Any) -> Dict[str, Any]:
        """Perform visualization analysis"""
        # Placeholder for visualization analysis
        return {
            "chart_type": "histogram",
            "data_points": len(data) if isinstance(data, list) else 0,
            "recommendations": ["Use bar chart for categorical data", "Consider scatter plot for correlations"]
        }
    
    def get_api_endpoints(self) -> List[Dict[str, Any]]:
        """Return API endpoints provided by this plugin"""
        return [
            {
                "path": "/api/my-plugin/process",
                "method": "POST",
                "handler": self.api_process,
                "description": "Process data via API",
                "parameters": {
                    "data": {"type": "array", "required": True},
                    "options": {"type": "object", "required": False}
                }
            },
            {
                "path": "/api/my-plugin/analyze",
                "method": "POST",
                "handler": self.api_analyze,
                "description": "Analyze data via API",
                "parameters": {
                    "dataset": {"type": "string", "required": True},
                    "analysis_type": {"type": "string", "required": False}
                }
            }
        ]
    
    async def api_process(self, request) -> Dict[str, Any]:
        """Handle API requests for processing"""
        data = request.json
        return await self.custom_process(data.get("data"), data.get("options"))
    
    async def api_analyze(self, request) -> Dict[str, Any]:
        """Handle API requests for analysis"""
        data = request.json
        return await self.custom_analyze(
            data.get("dataset"), 
            data.get("analysis_type", "statistical")
        )
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Return webhook handlers"""
        return [
            {
                "event": "data_processed",
                "handler": self.handle_data_processed,
                "description": "Handle data processing completion events"
            }
        ]
    
    async def handle_data_processed(self, event_data: Dict[str, Any]):
        """Handle data processing events"""
        print(f"Data processed: {event_data}")
        # Send notification, update dashboard, etc.
    
    def get_middleware(self) -> callable:
        """Return middleware function"""
        async def middleware(request, response, next_handler):
            # Pre-processing
            start_time = time.time()
            
            # Call next handler
            result = await next_handler(request, response)
            
            # Post-processing
            execution_time = time.time() - start_time
            response.headers["X-Plugin-Execution-Time"] = str(execution_time)
            
            return result
        
        return middleware
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Return UI components"""
        return [
            {
                "name": "CustomProcessor",
                "type": "tool",
                "component": "CustomProcessor.vue",
                "description": "Custom data processing interface",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "input_format": {"type": "string", "enum": ["json", "csv", "xml"]},
                        "processing_options": {"type": "object"}
                    }
                }
            }
        ]
    
    def cleanup(self):
        """Cleanup plugin resources"""
        try:
            # Close connections, cleanup caches, etc.
            self.initialized = False
            print(f"Plugin {self.name} cleaned up successfully")
        except Exception as e:
            print(f"Plugin cleanup error: {e}")

# Plugin class for auto-discovery
Plugin = MyPlugin
```

### Plugin Configuration

#### config.json
```json
{
  "name": "My Custom Plugin",
  "version": "1.0.0",
  "description": "A custom plugin for specialized processing",
  "type": "tool",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/yourname/my-plugin",
  "repository": "https://github.com/yourname/my-plugin.git",
  "dependencies": ["requests>=2.25.0", "pandas>=1.3.0"],
  "min_oracle_version": "5.0.0",
  "permissions": ["network", "file_read"],
  "config_schema": {
    "type": "object",
    "properties": {
      "api_endpoint": {
        "type": "string",
        "description": "API endpoint URL",
        "required": true
      },
      "timeout": {
        "type": "integer",
        "description": "Request timeout in seconds",
        "default": 30,
        "minimum": 1,
        "maximum": 300
      }
    }
  },
  "entry_point": "plugin.py",
  "icon": "icon.png",
  "screenshots": ["screenshot1.png", "screenshot2.png"]
}
```

#### requirements.txt
```
requests>=2.25.0
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.5.0
```

---

## 🧪 Testing

### Unit Tests
```python
# plugins/my_plugin/tests/test_plugin.py
import unittest
import asyncio
from plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin()
        self.config = {
            "api_endpoint": "https://api.example.com"
        }
    
    def test_initialization(self):
        """Test plugin initialization"""
        result = self.plugin.initialize(self.config)
        self.assertTrue(result)
        self.assertTrue(self.plugin.initialized)
    
    def test_custom_process(self):
        """Test custom processing"""
        asyncio.run(self.plugin.initialize(self.config))
        
        test_data = [1, 2, 3, 4, 5]
        result = asyncio.run(self.plugin.custom_process(test_data))
        
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["processed_items"], 5)
    
    def test_custom_analyze(self):
        """Test custom analysis"""
        asyncio.run(self.plugin.initialize(self.config))
        
        result = asyncio.run(self.plugin.custom_analyze("test_data.json", "statistical"))
        
        self.assertTrue(result["success"])
        self.assertIn("count", result["result"])
    
    def test_error_handling(self):
        """Test error handling"""
        asyncio.run(self.plugin.initialize(self.config))
        
        result = asyncio.run(self.plugin.custom_process([]))
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def tearDown(self):
        """Cleanup after tests"""
        self.plugin.cleanup()

if __name__ == "__main__":
    unittest.main()
```

### Integration Tests
```python
# plugins/my_plugin/tests/test_integration.py
import unittest
import asyncio
from src.oracle.plugin_system import PluginManager

class TestPluginIntegration(unittest.TestCase):
    def setUp(self):
        self.plugin_manager = PluginManager()
    
    def test_plugin_loading(self):
        """Test plugin loading"""
        result = self.plugin_manager.load_plugin("my_plugin")
        self.assertTrue(result)
        
        plugin = self.plugin_manager.get_plugin("my_plugin")
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.metadata["name"], "My Custom Plugin")
    
    def test_tool_execution(self):
        """Test tool execution through plugin manager"""
        self.plugin_manager.load_plugin("my_plugin")
        
        # Execute tool
        result = self.plugin_manager.execute_tool("custom_process", {
            "data": [1, 2, 3],
            "options": {"format": "json"}
        })
        
        self.assertTrue(result["success"])
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        self.plugin_manager.load_plugin("my_plugin")
        
        plugin = self.plugin_manager.get_plugin("my_plugin")
        endpoints = plugin.instance.get_api_endpoints()
        
        self.assertEqual(len(endpoints), 2)
        self.assertEqual(endpoints[0]["path"], "/api/my-plugin/process")

if __name__ == "__main__":
    unittest.main()
```

### Running Tests
```bash
# Run unit tests
cd plugins/my_plugin
python -m pytest tests/ -v

# Run integration tests
cd ../../
python -m pytest plugins/my_plugin/tests/test_integration.py -v

# Run all tests with coverage
python -m pytest plugins/my_plugin/tests/ --cov=plugin --cov-report=html
```

---

## 📦 Publishing

### Plugin Package Structure
```
my-plugin-1.0.0/
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   ├── config.json
│   └── requirements.txt
├── README.md
├── LICENSE
├── setup.py
└── MANIFEST.in
```

### setup.py
```python
from setuptools import setup, find_packages

setup(
    name="oracle-agent-my-plugin",
    version="1.0.0",
    description="A custom plugin for Oracle Agent",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourname/my-plugin",
    packages=find_packages(),
    install_requires=[
        "oracle-agent>=5.0.0",
        "requests>=2.25.0",
        "pandas>=1.3.0"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    entry_points={
        "oracle_agent.plugins": [
            "my_plugin = my_plugin.plugin:Plugin"
        ]
    }
)
```

### Publishing to Plugin Registry
```bash
# Build package
python setup.py sdist bdist_wheel

# Publish to registry
twine upload dist/*

# Or publish to Oracle Agent registry
oracle-agent publish dist/
```

---

## 🔧 Best Practices

### Code Quality
1. **Type Hints**: Use strict typing throughout
2. **Error Handling**: Comprehensive error handling and logging
3. **Documentation**: Document all public methods
4. **Testing**: High test coverage (>90%)
5. **Performance**: Optimize for enterprise workloads

### Security
1. **Input Validation**: Validate all inputs
2. **Sanitization**: Sanitize user inputs
3. **Permissions**: Request minimal permissions
4. **Dependencies**: Use secure, updated dependencies
5. **Secrets**: Never hardcode secrets

### Performance
1. **Async Operations**: Use async/await for I/O
2. **Caching**: Cache expensive operations
3. **Resource Management**: Proper resource cleanup
4. **Memory**: Monitor memory usage
5. **Concurrency**: Handle concurrent requests

### Usability
1. **Clear Names**: Use descriptive names
2. **Consistent API**: Follow Oracle Agent patterns
3. **Error Messages**: Provide helpful error messages
4. **Documentation**: Comprehensive documentation
5. **Examples**: Include usage examples

---

## 📚 Examples

### Tool Plugin Example
```python
class DataValidationPlugin:
    name = "Data Validation"
    version = "1.0.0"
    description = "Validate data against schemas and rules"
    type = PluginType.TOOL
    
    def get_tools(self):
        return [
            {
                "name": "validate_json",
                "description": "Validate JSON data against schema",
                "function": self.validate_json
            },
            {
                "name": "validate_csv",
                "description": "Validate CSV data structure",
                "function": self.validate_csv
            }
        ]
    
    async def validate_json(self, data: Dict, schema: Dict) -> Dict:
        """Validate JSON against schema"""
        import jsonschema
        
        try:
            jsonschema.validate(data, schema)
            return {"success": True, "valid": True}
        except jsonschema.ValidationError as e:
            return {"success": False, "error": str(e), "valid": False}
```

### Integration Plugin Example
```python
class SalesforcePlugin:
    name = "Salesforce Integration"
    version = "1.0.0"
    description = "Integrate with Salesforce CRM"
    type = PluginType.INTEGRATION
    
    def get_tools(self):
        return [
            {
                "name": "create_lead",
                "description": "Create lead in Salesforce",
                "function": self.create_lead
            },
            {
                "name": "update_opportunity",
                "description": "Update opportunity in Salesforce",
                "function": self.update_opportunity
            }
        ]
    
    async def create_lead(self, lead_data: Dict) -> Dict:
        """Create lead in Salesforce"""
        # Salesforce API integration logic
        return {"success": True, "lead_id": "001xx000003DHbo"}
```

### UI Component Plugin Example
```python
class DashboardPlugin:
    name = "Custom Dashboard"
    version = "1.0.0"
    description = "Custom dashboard components"
    type = PluginType.UI_COMPONENT
    
    def get_ui_components(self):
        return [
            {
                "name": "CustomChart",
                "type": "visualization",
                "component": "CustomChart.vue",
                "props": {
                    "data": {"type": "array", "required": True},
                    "chart_type": {"type": "string", "default": "line"}
                }
            },
            {
                "name": "CustomTable",
                "type": "data_display",
                "component": "CustomTable.vue",
                "props": {
                    "columns": {"type": "array", "required": True},
                    "data": {"type": "array", "required": True}
                }
            }
        ]
```

---

## 🐛 Troubleshooting

### Common Issues

#### Plugin Not Loading
```bash
# Check plugin structure
ls -la plugins/my_plugin/

# Check syntax
python -m py_compile plugins/my_plugin/plugin.py

# Check dependencies
pip install -r plugins/my_plugin/requirements.txt

# Check configuration
python -c "import json; json.load(open('plugins/my_plugin/config.json'))"
```

#### Permission Errors
```bash
# Check required permissions
grep -r "permissions" plugins/my_plugin/config.json

# Test permission request
python -c "
from plugin_system import SecurityManager
sm = SecurityManager()
print(sm.check_permission('my_plugin', 'network', 'execute'))
"
```

#### Performance Issues
```bash
# Profile plugin
python -m cProfile -o profile.stats plugins/my_plugin/plugin.py

# Check memory usage
python -m memory_profiler plugins/my_plugin/plugin.py

# Monitor execution time
time python plugins/my_plugin/tests/test_plugin.py
```

### Debug Mode
```bash
# Enable debug logging
export ORACLE_LOG_LEVEL=DEBUG
export ORACLE_PLUGIN_DEBUG=true

# Run with verbose output
python3 main.py --verbose --debug-plugins
```

---

## 📞 Support

### Getting Help
- **Documentation**: [Oracle Agent Plugin Docs](https://oracle-agent.com/docs/plugins)
- **Community**: [GitHub Discussions](https://github.com/oracle-agent/oracle-agent/discussions)
- **Issues**: [GitHub Issues](https://github.com/oracle-agent/oracle-agent/issues)
- **Plugin Support**: [plugins@oracle-agent.com](mailto:plugins@oracle-agent.com)

### Resources
- **Plugin Templates**: [GitHub Templates](https://github.com/oracle-agent/plugin-templates)
- **Examples**: [Plugin Examples](https://github.com/oracle-agent/plugin-examples)
- **Best Practices**: [Development Guide](https://oracle-agent.com/docs/plugin-best-practices)

---

## 📈 Roadmap

### Upcoming Features
- **Plugin Marketplace**: Centralized plugin distribution
- **Visual Plugin Builder**: No-code plugin creation
- **Advanced Testing**: Automated testing framework
- **Performance Monitoring**: Built-in performance metrics
- **Security Scanning**: Automated security validation

### API Changes
- **v5.1**: Enhanced plugin permissions
- **v5.2**: Plugin dependency management
- **v5.3**: Advanced UI component framework

---

**🔌 Oracle Agent Plugin Development Guide - Build Powerful Extensions for the Enterprise AI Platform**
