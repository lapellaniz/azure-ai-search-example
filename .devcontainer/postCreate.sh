
#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Setting up Azure AI Prompt Retrieval development environment..."

cd "/workspaces/workspace" || exit 1

# Ensure Poetry is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found in PATH. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "📦 Installing dependencies with Poetry..."
poetry config virtualenvs.in-project true
poetry install --with=dev,test

echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install || echo "⚠️  Pre-commit not available, skipping..."

echo "🧪 Running initial tests to verify setup..."
poetry run pytest tests/ -v || echo "⚠️  Some tests failed, but setup continues..."

echo "📋 Creating example .env file if it doesn't exist..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Azure Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_API_VERSION=2023-11-01
SEARCH_INDEX_NAME_QUESTIONS=questions
SEARCH_SIMILARITY_THRESHOLD=0.75

# Azure OpenAI Configuration (optional for dynamic prompts)
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL_NAME=gpt-4

# Application Insights (optional for telemetry)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=your-key;IngestionEndpoint=...
EOF
    echo "📝 Created .env file with example configuration"
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Quick start commands:"
echo "  make test      - Run tests"
echo "  make lint      - Run linting"
echo "  make fmt       - Format code"
echo "  poetry shell   - Activate virtual environment"
echo ""
echo "📚 See README.md for more information."
