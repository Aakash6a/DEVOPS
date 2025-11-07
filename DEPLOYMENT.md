# Deployment Guide

This guide provides step-by-step instructions for deploying the Inventory Management System.

## Prerequisites

- Docker and Docker Compose installed
- Kubernetes cluster (for Kubernetes deployment) - Optional
- kubectl configured (for Kubernetes deployment) - Optional

## Quick Start with Docker Compose

### 1. Build and Start Services

```bash
docker-compose up --build
```

Or use the deployment script:
```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. Verify Deployment

- Application: http://localhost:5000
- API Endpoints:
  - GET http://localhost:5000/ - Health check
  - GET http://localhost:5000/report - Inventory report
  - POST http://localhost:5000/add_product - Add product
  - POST http://localhost:5000/place_order - Place order

### 3. Test the API

Add a product:
```bash
curl -X POST http://localhost:5000/add_product \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "Gaming Laptop",
    "price": 999.99,
    "stock_quantity": 10
  }'
```

Get report:
```bash
curl http://localhost:5000/report
```

## Kubernetes Deployment

### 1. Build Docker Image

```bash
docker build -t inventory-app:latest .
```

### 2. Deploy MySQL

```bash
kubectl apply -f mysql-deployment.yaml
```

Wait for MySQL to be ready:
```bash
kubectl wait --for=condition=ready pod -l app=mysql --timeout=120s
```

### 3. Deploy Application

```bash
kubectl apply -f inventory-app-deployment.yaml
```

### 4. Verify Deployment

```bash
kubectl get pods
kubectl get svc
```

### 5. Access Application

For local Kubernetes (Docker Desktop/Minicube):
```bash
kubectl port-forward svc/inventory-app-service 5000:80
```

Then access at: http://localhost:5000

For cloud Kubernetes, use the LoadBalancer external IP:
```bash
kubectl get svc inventory-app-service
```

## Troubleshooting

### Docker Compose Issues

- **MySQL connection errors**: Wait a few seconds for MySQL to initialize
- **Build errors**: Check Dockerfile and requirements.txt
- **Port conflicts**: Change ports in docker-compose.yaml

### Kubernetes Issues

- **Pod not starting**: Check logs with `kubectl logs <pod-name>`
- **Service not accessible**: Verify service selector matches pod labels
- **Database connection**: Ensure MySQL service is running and accessible

### View Logs

Docker Compose:
```bash
docker-compose logs -f app
docker-compose logs -f mysql
```

Kubernetes:
```bash
kubectl logs -l app=inventory-app
kubectl logs -l app=mysql
```

## Clean Up

### Docker Compose
```bash
docker-compose down
docker-compose down -v  # Also remove volumes
```

### Kubernetes
```bash
kubectl delete -f inventory-app-deployment.yaml
kubectl delete -f mysql-deployment.yaml
```

