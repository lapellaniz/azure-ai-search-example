
# syntax=docker/dockerfile:1
ARG VARIANT="3.12-bookworm"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

# Install system dependencies
USER root
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        git \
        make \
        zip \
        curl \
        jq \
        vim \
        tree \
        httpie \
        # Development tools
        build-essential \
        # For potential C extensions in Python packages
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
USER vscode
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Set working directory
WORKDIR /workspaces

# Configure Poetry to create virtual environments in project directory
ENV POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_NO_INTERACTION=1
