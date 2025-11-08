#!/bin/bash

# Myla Development Startup Script
# This script helps you easily start your Slack bot in Docker with live code reloading

set -e

echo "🚀 Starting Myla Slack Bot Development Environment"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "📝 Created .env file from env.example"
        echo "🔧 Please edit .env file with your actual API keys and tokens"
        echo ""
    else
        echo "❌ No env.example file found. Please create a .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "🔨 Building Docker image..."
docker-compose build

echo "📦 Starting development container with live reload..."
echo "💡 Your code changes will automatically sync to the container"
echo "🔄 To restart the bot after code changes, use: docker-compose restart myla-bot"
echo ""
echo "🛑 To stop the bot, press Ctrl+C or run: docker-compose down"
echo ""

# Start the development environment
docker-compose up myla-bot
