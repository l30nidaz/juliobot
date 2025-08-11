#!/usr/bin/env bash
set -o errexit

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing build dependencies..."
python -m pip install setuptools>=68.0.0 wheel pip-tools

echo "Installing project dependencies..."
python -m pip install -r requirements.txt

echo "Build completed successfully!"