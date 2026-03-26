# Oracle Agent GUI

A modern web-based interface for the Oracle Agent Platform providing an intuitive chat experience with real-time tool execution visualization.

## Features

- **💬 Interactive Chat Interface**: Real-time conversation with Oracle Agent
- **🔧 Tool Execution Panel**: Direct access to shell, file, HTTP, and vision tools
- **📊 Live Status Monitoring**: Agent health, configuration, and GCS backup status
- **🌙 Dark Theme**: Modern, eye-friendly interface with syntax highlighting
- **⚡ Real-time Updates**: WebSocket-powered live message streaming
- **💾 Session Management**: Persistent conversation history with clear/backup options
- **🔗 Health Check Links**: Quick access to monitoring endpoints

## Quick Start

### 1. Install Dependencies

```bash
cd /home/donovan/Projects/replit/gui
pip install -r requirements.txt
```

### 2. Launch the GUI

```bash
# Make sure you're in the project root
python3 gui/launch.py
```

Or manually:

```bash
python3 gui/app.py
```

### 3. Access the Interface

Open your browser to: **http://localhost:5000**

## Architecture

The GUI consists of three layers:

1. **Backend (Flask + SocketIO)**: `app.py`
   - Wraps OracleAgent with HTTP/WebSocket API
   - Handles tool execution and session management
   - Serves static files and templates

2. **Frontend (HTML/CSS/JS)**: `templates/` and `static/`
   - Modern responsive design with dark theme
   - Real-time chat with markdown rendering
   - Interactive tool execution panel

3. **Integration Layer**
   - Connects to existing OracleAgent instance
   - Reuses configuration from `.env` file
   - Supports both sync and async agent methods

## Directory Structure

```
gui/
├── app.py                 # Flask backend
├── launch.py             # Launch script with dependency checking
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── templates/
│   └── index.html       # Main GUI template
└── static/
    ├── css/
    │   └── style.css    # GUI styles
    └── js/
        └── app.js       # Frontend JavaScript
```

## Configuration

The GUI automatically loads configuration from your existing `.env` file:

- `ORACLE_MODEL_ID` - AI model to use
- `GCP_PROJECT_ID` - Google Cloud project (optional)
- `ORACLE_MAX_TURNS` - Maximum conversation turns
- `ORACLE_SHELL_TIMEOUT` - Shell command timeout
- `ORACLE_HTTP_TIMEOUT` - HTTP request timeout

## API Endpoints

- `GET /` - Main GUI interface
- `GET /api/status` - Agent status and configuration
- `GET /api/config` - Get/set configuration
- `WebSocket /` - Real-time communication

## WebSocket Events

### Client → Server
- `send_message` - Send chat message
- `execute_tool` - Execute specific tool
- `backup_to_gcs` - Trigger cloud backup
- `clear_history` - Clear session history

### Server → Client
- `message` - Assistant response
- `thinking` - Agent processing indicator
- `tool_result` - Tool execution result
- `backup_result` - Backup completion status
- `error` - Error messages

## Tool Execution

The sidebar provides direct access to Oracle Agent's tools:

1. **Shell**: Execute bash commands with safety sandboxing
2. **Files**: Read, write, list, and delete files
3. **HTTP**: Make API requests to external services
4. **Vision**: Capture screenshots (when available)

Click any tool to open the execution panel with a form for the tool's parameters.

## Session Management

- **Session ID**: Displayed in chat header (default: "default")
- **Clear History**: Removes all messages from current session
- **Backup to GCS**: Triggers cloud backup (if configured)
- **Persistent Storage**: Conversations saved to `data/oracle_core.db`

## Troubleshooting

### Agent Not Initialized
- Check that `.env` file exists with valid configuration
- Verify `GCP_PROJECT_ID` is set for full AI mode
- Run `demo.py` first to test without credentials

### Connection Issues
- Ensure port 5000 is not in use by another application
- Check that Flask-SocketIO dependencies are installed
- Verify no firewall blocking WebSocket connections

### Tool Execution Failures
- Verify `ORACLE_PROJECT_ROOT` is set correctly
- Check tool timeouts in configuration
- Review agent logs for detailed error messages

## Development

### Adding New Tools
1. Add tool button to sidebar in `templates/index.html`
2. Create tool form configuration in `static/js/app.js`
3. Implement tool handler in `app.py` if needed

### Customizing Theme
- Modify CSS variables in `static/css/style.css`
- Primary color: `--primary: #6366f1`
- Background: `--bg-dark: #0f172a`
- Text: `--text-primary: #f8fafc`

### Extending API
Add new Flask routes in `app.py`:

```python
@app.route("/api/custom")
def custom_endpoint():
    return jsonify({"data": "custom"})
```

## Integration with Main System

The GUI is designed to work alongside the existing Oracle Agent infrastructure:

- Shares the same `.env` configuration
- Uses the same SQLite database for history
- Integrates with existing health check server
- Supports both production and demo modes

## Security Considerations

- All file operations are sandboxed to `ORACLE_PROJECT_ROOT`
- Shell commands use explicit list form (no shell injection)
- No credentials exposed in frontend
- Configuration changes require server restart

## License

Part of Oracle Agent Platform v5.0
