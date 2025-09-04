# Development Container Setup

This project includes a comprehensive development container configuration for Azure AI Prompt Retrieval development.

## Features

### 🐍 **Python 3.12 Environment**
- Latest Python 3.12 with Poetry package management
- Pre-configured virtual environment in project directory
- Automatic dependency installation

### 🛠️ **Development Tools**
- **Black & Ruff**: Code formatting and linting
- **Pytest**: Testing framework with auto-discovery
- **Pre-commit**: Git hooks for code quality
- **Azure CLI**: Azure resource management
- **Docker**: Container development support

### 🔧 **VS Code Extensions**
- **Python Development**: Full Python IntelliSense, debugging, and testing
- **Azure Tools**: Complete Azure development suite
- **Testing**: Integrated test discovery and execution
- **Git**: Enhanced version control with GitLens
- **Utilities**: REST client, Markdown support, and more

### ☁️ **Azure Integration**
- Pre-configured environment variables for Azure services
- Azure CLI with Bicep support
- Application Insights telemetry setup
- Azure Search and OpenAI service configuration

## Quick Start

1. **Open in Container**: Use VS Code's "Reopen in Container" command
2. **Wait for Setup**: The container will automatically install dependencies
3. **Configure Azure**: Update the `.env` file with your Azure service details
4. **Start Developing**: Run `make test` to verify everything works

## Available Commands

```bash
# Development commands
make install    # Install dependencies
make test       # Run tests
make lint       # Run linting
make fmt        # Format code
make ci         # Full CI pipeline

# Poetry commands
poetry shell    # Activate virtual environment
poetry add pkg  # Add new dependency
poetry show     # List installed packages

# Azure CLI commands
az login        # Authenticate with Azure
az account list # List subscriptions
```

## Environment Configuration

The container automatically creates a `.env` file with placeholders for:

- **Azure Search**: Endpoint, API key, index configuration
- **Azure OpenAI**: Endpoint, API key, model settings
- **Application Insights**: Connection string for telemetry

Update these values with your actual Azure service details.

## Port Forwarding

The container automatically forwards these ports:
- `8000`: Development server
- `8080`: Alternative web server
- `3000`: React/Node.js development
- `5000`: Flask/Python web apps

## Persistent Volumes

- **Source Code**: Mounted with cached consistency for performance
- **Poetry Cache**: Persistent cache for faster dependency installation
- **Docker Socket**: Access to host Docker daemon

## Troubleshooting

### Poetry Issues
```bash
# Reset Poetry environment
rm -rf .venv
poetry install

# Update Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### VS Code Python Issues
```bash
# Reset Python interpreter
# Use Command Palette: "Python: Select Interpreter"
# Choose: /workspaces/workspace/.venv/bin/python
```

### Azure CLI Issues
```bash
# Re-authenticate
az logout
az login
```

## Performance Tips

1. **Use .devcontainer volume**: Dependencies are cached between rebuilds
2. **Exclude large directories**: `.venv`, `node_modules` are excluded from search
3. **Cached volume mount**: Source code uses cached consistency for better performance

## Extensions Included

- **Python**: Complete Python development suite
- **Azure**: Full Azure development tools
- **Testing**: Integrated test runners and coverage
- **Git**: Enhanced version control
- **Markdown**: Documentation editing
- **REST**: API testing tools
- **Utilities**: Path intellisense, better comments, etc.
