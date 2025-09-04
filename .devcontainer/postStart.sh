
#!/usr/bin/env bash
set -euo pipefail

cd "/workspaces/workspace" || exit 1

echo "🔄 Post-start setup..."

# Ensure Poetry is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Activate the virtual environment for the terminal session
if [ -f .venv/bin/activate ]; then
    echo "🐍 Virtual environment found, activating..."
    source .venv/bin/activate
    
    # Verify Python version and key packages
    echo "📊 Environment info:"
    echo "  Python: $(python --version)"
    echo "  Poetry: $(poetry --version)"
    echo "  Working directory: $(pwd)"
    
    # Show available make targets
    echo ""
    echo "🛠️  Available commands:"
    make help 2>/dev/null || echo "  Run 'make help' to see available commands"
else
    echo "⚠️  Virtual environment not found. Run 'poetry install' to set it up."
fi

echo "✅ Ready for development!"
