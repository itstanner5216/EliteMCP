# Configuration Guide

This guide documents the configuration options for the Directory Intelligence Tool and FastMCP Server.

## Configuration Sources

Configuration can be provided from multiple sources with the following precedence:

1. **Environment Variables** (highest priority)
2. **Config File** (`config/config.json`)
3. **Default Values** (lowest priority)

## Server Configuration

### Config File Structure

Location: `config/config.json`

```json
{
  "server_name": "directory-intelligence-server",
  "host": "127.0.0.1",
  "port": 8000,
  "log_level": "INFO",
  "enable_directory_tool": true,
  "tools": {
    "directory_tool": {
      "enabled": true,
      "max_file_count": 50,
      "expand_large": false
    }
  }
}
```

### Configuration Fields

#### Server Settings

**server_name** (string)
- Name of the FastMCP server
- Used for identification and logging
- Default: `"directory-intelligence-server"`

**host** (string)
- IP address to bind the server to
- Default: `"127.0.0.1"`
- Set to `"0.0.0.0"` to listen on all interfaces

**port** (integer)
- Port number for the server
- Range: 1-65535
- Default: `8000`

**log_level** (string)
- Logging level for the server
- Valid values: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- Default: `"INFO"`

**enable_directory_tool** (boolean)
- Whether to enable the directory intelligence tool
- Default: `true`

#### Tool-Specific Settings

**tools.directory_tool.enabled** (boolean)
- Enable/disable directory tool registration
- Default: `true`

**tools.directory_tool.max_file_count** (integer)
- Threshold for directory summarization
- Directories with more files than this value will show `<summary count="N"/>` instead of listing all files
- Default: `50`

**tools.directory_tool.expand_large** (boolean)
- Default value for expand_large parameter
- When `true`, always expand directories regardless of file count
- Default: `false`

**IMPORTANT:** Tool-specific configuration (max_file_count, expand_large) is loaded by the MCP server but is NOT automatically propagated to the DirectoryIntelligenceTool instance. These values serve as documentation and defaults in the config file, but the tool uses its own internal configuration unless explicitly coded to read from the server config. This is intentional behavior to maintain separation between server configuration and tool implementation.

### Environment Variables

Override config file values:

**DIRECTORY_TOOL_MAX_FILES**
- Override max_file_count for directory tool
- Example: `export DIRECTORY_TOOL_MAX_FILES=100`

**DIRECTORY_TOOL_EXPAND_LARGE**
- Override expand_large default
- Valid values: `true`, `1`, `yes` (case-insensitive)
- Example: `export DIRECTORY_TOOL_EXPAND_LARGE=true`

## Docker Configuration

### Docker Socket

The server requires access to Docker socket for the sandbox execution engine:

**Environment Variable:**
- `DOCKER_HOST`: Path to Docker socket
- Default: `unix:///var/run/docker.sock`

**Mount:**
- Docker socket must be mounted into the container
- In devcontainer: `source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind`

### Docker Permissions

- Container must run with appropriate privileges
- In devcontainer: `--privileged` flag is used
- For production, consider more restrictive permissions

## Daytona Configuration

### API Key

**Environment Variable:**
- `DAYTONA_API_KEY`: Daytona API key for authentication
- Must be set before using Daytona backend
- In devcontainer: `${localEnv:DAYTONA_API_KEY}` passes through local value

### Daytona SDK

**Installation:**
```bash
pip install daytona_sdk
```

## Development Environment

### DevContainer Configuration

Location: `.devcontainer/devcontainer.json`

#### Python Environment

**Image:** `mcr.microsoft.com/devcontainers/python:3.11`
- Python 3.11 with common development tools pre-installed

**PYTHONPATH:** `/workspace/src`
- Ensures src/ modules can be imported

#### Ports

**Forwarded Ports:**
- `8000`: FastMCP Server

#### Dependencies

**postCreateCommand:**
```bash
pip install --upgrade pip && pip install -r requirements.txt && pip install -e /workspace
```
- Upgrades pip
- Installs all dependencies from requirements.txt
- Installs project in editable mode

#### Features

- `docker-in-docker:2`: Docker support
- `git:1`: Git version control
- `common-utils:2`: Common utilities and shell setup

#### Extensions

Installed VS Code extensions:
- ms-python.python
- ms-python.vscode-pylance
- ms-python.black-formatter
- ms-python.flake8
- ms-python.pytest
- ms-vscode.test-adapter-converter
- redhat.vscode-xml
- ms-vscode.vscode-json

## Error Conditions

### Config File Errors

#### File Not Found
```
Config:not_found: /path/to/config.json
```
**Solution:** Create config file or rely on defaults

#### Invalid JSON
```
Config:invalid_json: <error_message>
```
**Solution:** Fix JSON syntax in config file

#### Permission Denied
```
Config:permission_denied: <error_message>
```
**Solution:** Check file permissions

#### Missing Required Fields
```
Config:invalid: <field> must be <type>
```
**Solution:** Add required fields to config

### Validation Errors

#### Invalid Port
```
Config:invalid: port must be between 1 and 65535
```
**Solution:** Use valid port number

#### Invalid Log Level
```
Config:invalid: log_level must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
```
**Solution:** Use valid log level

#### Invalid Host
```
Config:invalid: host must be a non-empty string
```
**Solution:** Provide non-empty host string

### Startup Sequence

1. **Load Configuration**
   - Try to load from config file
   - Apply defaults for missing fields
   - Override with environment variables

2. **Validate Configuration**
   - Check all required fields
   - Validate field types and ranges
   - Log validation results at DEBUG level

3. **Initialize FastMCP**
   - Create FastMCP instance with server name
   - Log initialization at DEBUG level

4. **Register Tools**
   - Check if directory tool is enabled
   - Import tool from directory_tool module
   - Register with FastMCP
   - Log registration at DEBUG level

5. **Start Server**
   - Bind to host and port
   - Log startup information
   - Begin accepting connections

## Examples

### Minimal Config File

```json
{
  "port": 8000
}
```

All other fields will use default values.

### Production Config

```json
{
  "server_name": "production-server",
  "host": "0.0.0.0",
  "port": 8000,
  "log_level": "WARNING",
  "enable_directory_tool": true,
  "tools": {
    "directory_tool": {
      "enabled": true,
      "max_file_count": 100,
      "expand_large": false
    }
  }
}
```

### Development Config

```json
{
  "server_name": "dev-server",
  "host": "127.0.0.1",
  "port": 8000,
  "log_level": "DEBUG",
  "enable_directory_tool": true,
  "tools": {
    "directory_tool": {
      "enabled": true,
      "max_file_count": 50,
      "expand_large": true
    }
  }
}
```

### Disable Directory Tool

```json
{
  "enable_directory_tool": false
}
```

### Environment Variable Override

```bash
export DIRECTORY_TOOL_MAX_FILES=100
export DIRECTORY_TOOL_EXPAND_LARGE=true
python src/mcp_server.py
```

## Best Practices

1. **Use Environment Variables for Secrets**
   - Store API keys in environment variables
   - Don't commit secrets to config files

2. **Separate Dev and Prod Configs**
   - Use different config files for different environments
   - Or use environment variables to override

3. **Set Appropriate Log Levels**
   - Use DEBUG in development
   - Use WARNING or ERROR in production

4. **Use Default Port When Possible**
   - Port 8000 is conventional for FastMCP servers
   - Avoid conflicts with other services

5. **Validate Config on Startup**
   - Server validates config before starting
   - Check logs for validation errors

## Troubleshooting

### Server Won't Start

**Check config file:**
```bash
python -m json.tool config/config.json
```

**Verify environment variables:**
```bash
echo $DIRECTORY_TOOL_MAX_FILES
```

**Check logs:**
- Server logs configuration at DEBUG level
- Look for Config:validation messages

### Config Not Applied

**Verify precedence:**
1. Environment variables override config file
2. Config file overrides defaults

**Check file location:**
- Config must be at `config/config.json` (relative to project root)

### Invalid Configuration

**Common errors:**
- Missing commas in JSON
- Invalid port numbers
- Wrong log level values
- Non-string host values

**Solution:** Validate JSON syntax and field values

## Requirements

- Python 3.11+
- Config file in JSON format
- Appropriate file permissions for config directory

## License

This configuration guide is part of the Directory Intelligence Tool project.
