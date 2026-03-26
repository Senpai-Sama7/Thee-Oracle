# 🤝 Contributing to Oracle Agent

## 📋 Overview

We welcome contributions to Oracle Agent! This guide provides comprehensive information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git
- GitHub account
- Development environment setup

### Development Setup
```bash
# Fork and clone repository
git clone https://github.com/your-username/oracle-agent.git
cd oracle-agent

# Add upstream remote
git remote add upstream https://github.com/oracle-agent/oracle-agent.git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest
```

## 🏗️ Development Workflow

### 1. Create Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow code style guidelines
- Write tests for new features
- Update documentation
- Ensure all tests pass

### 3. Test Changes
```bash
# Run unit tests
python -m pytest tests/

# Run type checking
mypy src/oracle/

# Run linting
ruff check .

# Run security audit
python3 security_audit.py
```

### 4. Submit Pull Request
- Push to your fork
- Create pull request
- Fill out PR template
- Wait for review

## 📝 Code Standards

### Style Guidelines
- Use `ruff` for code formatting
- Follow PEP 8 style guide
- Use type hints everywhere
- Write clear docstrings

### Example Code
```python
from typing import Dict, List, Any, Optional

class ExampleClass:
    """Example class following Oracle Agent standards."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.initialized = False
    
    async def process_data(self, data: List[Any]) -> Dict[str, Any]:
        """Process data asynchronously.
        
        Args:
            data: List of data items to process
            
        Returns:
            Dictionary containing processed results
            
        Raises:
            ValueError: If data is invalid
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Processing logic here
        return {"processed": len(data)}
```

## 🧪 Testing

### Test Structure
```
tests/
├── unit/
│   ├── test_agent_system.py
│   ├── test_workflow_engine.py
│   └── test_plugin_system.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_workflows.py
└── security/
    ├── test_authentication.py
    └── test_input_validation.py
```

### Writing Tests
```python
import pytest
from unittest.mock import Mock, patch
from src.oracle.workflow_engine import WorkflowEngine

class TestWorkflowEngine:
    def setup_method(self):
        """Setup test environment."""
        self.engine = WorkflowEngine()
    
    def test_create_workflow(self):
        """Test workflow creation."""
        steps = [{"type": "shell", "command": "echo test"}]
        workflow_id = self.engine.create_workflow("Test Workflow", steps)
        
        assert workflow_id is not None
        assert workflow_id in self.engine.workflows
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test workflow execution."""
        workflow_id = self.engine.create_workflow("Test", [])
        result = await self.engine.execute_workflow(workflow_id)
        
        assert result["status"] == "completed"
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            self.engine.execute_workflow("invalid-id")
```

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/unit/test_workflow_engine.py

# Run with coverage
python -m pytest --cov=src/oracle --cov-report=html

# Run integration tests
python -m pytest tests/integration/

# Run security tests
python -m pytest tests/security/
```

## 📚 Documentation

### Documentation Types
- **Code Documentation**: Docstrings and type hints
- **API Documentation**: API reference docs
- **User Documentation**: Guides and tutorials
- **Developer Documentation**: Architecture and contribution guides

### Writing Documentation
```python
def complex_function(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """Complex function with comprehensive documentation.
    
    This function demonstrates proper documentation format including:
    - Detailed description
    - Parameter documentation
    - Return value documentation
    - Exception documentation
    - Usage examples
    
    Args:
        param1: First parameter, must be a valid string
        param2: Optional integer parameter, defaults to None
        
    Returns:
        Dictionary containing:
        - 'success': Boolean indicating success
        - 'data': Processed data
        - 'timestamp': ISO timestamp of processing
        
    Raises:
        ValueError: If param1 is empty or invalid
        TypeError: If param2 is not an integer when provided
        
    Examples:
        >>> result = complex_function("test", 42)
        >>> print(result['success'])
        True
        
        >>> result = complex_function("test")
        >>> print(result['data'])
        {'param1': 'test', 'param2': None}
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    
    if param2 is not None and not isinstance(param2, int):
        raise TypeError("param2 must be an integer")
    
    return {
        "success": True,
        "data": {"param1": param1, "param2": param2},
        "timestamp": datetime.now().isoformat()
    }
```

## 🔌 Plugin Development

### Creating Plugins
See [Plugin Development Guide](docs/plugin_development.md) for comprehensive plugin development instructions.

### Plugin Guidelines
- Follow security best practices
- Use proper error handling
- Include comprehensive tests
- Document all public APIs
- Follow Oracle Agent patterns

## 🐛 Bug Reports

### Reporting Bugs
1. Check existing issues
2. Create new issue with bug template
3. Provide detailed information
4. Include reproduction steps
5. Add logs and screenshots

### Bug Report Template
```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Go to...
2. Click on...
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11.0]
- Oracle Agent version: [e.g. 5.0.0-hardened]

## Logs
[Attach relevant logs]

## Screenshots
[Add screenshots if applicable]
```

## ✨ Feature Requests

### Requesting Features
1. Check existing issues and discussions
2. Create feature request with template
3. Describe use case and benefits
4. Provide implementation suggestions
5. Consider contributing the feature

### Feature Request Template
```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this feature needed?

## Benefits
What benefits would this provide?

## Implementation Ideas
Any suggestions for implementation?

## Alternatives
Any alternative solutions considered?
```

## 🔍 Code Review

### Review Process
1. Automated checks pass
2. Code review by maintainers
3. Security review for sensitive changes
4. Documentation review
5. Merge to main branch

### Review Guidelines
- Focus on logic and security
- Check for performance issues
- Verify test coverage
- Ensure documentation is updated
- Be constructive and respectful

## 🏷️ Release Process

### Version Management
- Follow semantic versioning
- Update CHANGELOG.md
- Tag releases properly
- Update documentation

### Release Checklist
- [ ] All tests pass
- [ ] Security audit passes
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Tagged and released

## 📞 Getting Help

### Communication Channels
- **GitHub Discussions**: General questions and discussions
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time chat (invite link in README)
- **Email**: dev@oracle-agent.com

### Resources
- [Documentation](https://oracle-agent.com/docs)
- [API Reference](https://oracle-agent.com/api)
- [Examples](https://github.com/oracle-agent/examples)
- [Tutorials](https://oracle-agent.com/tutorials)

## 🏆 Recognition

### Contributor Recognition
- Contributors listed in README
- Top contributors featured
- Annual contributor awards
- Contribution statistics

### Ways to Contribute
- Code contributions
- Bug reports and fixes
- Documentation improvements
- Feature suggestions
- Community support
- Security research
- Translation help

## 📋 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards
- Use welcoming and inclusive language
- Be respectful of different viewpoints
- Accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Enforcement
Instances of abusive behavior will be reported to the project maintainers for review.

---

## 🤝 Thank You for Contributing!

We appreciate all contributions to Oracle Agent. Your help makes this project better for everyone!

**🚀 Together, we're building the future of enterprise AI agents!**
