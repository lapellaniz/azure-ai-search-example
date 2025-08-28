
# syntax=docker/dockerfile:1
ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

USER root
RUN apt-get update         && export DEBIAN_FRONTEND=noninteractive         && apt-get install -y --no-install-recommends            git make zip         && rm -rf /var/lib/apt/lists/*

USER vscode
WORKDIR /workspaces
