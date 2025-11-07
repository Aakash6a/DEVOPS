#!/bin/bash

# Deployment script for Inventory Management System
# This script helps deploy the application using Docker Compose or Kubernetes

set -e

echo "=== Inventory Management System Deployment ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "1. Building Docker image..."
docker build -t inventory-app:latest .

echo ""
echo "2. Starting services with Docker Compose..."
docker-compose up -d --build

echo ""
echo "3. Waiting for services to be ready..."
sleep 10

echo ""
echo "4. Checking service status..."
docker-compose ps

echo ""
echo "=== Deployment Complete ==="
echo "Application should be available at: http://localhost:5000"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
echo ""
echo "For Kubernetes deployment:"
echo "  kubectl apply -f mysql-deployment.yaml"
echo "  kubectl apply -f inventory-app-deployment.yaml"

