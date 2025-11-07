# Runbook — Inventory Management System

This document summarizes the actions we've performed in this workspace, the exact commands used, the files changed, and how to reproduce or continue work. It's intended as a chronological and actionable record.

Date: 2025-11-07
Workspace: d:\inventory-management-system-master

---

## 1) Goal

Get the Inventory Management Flask app running locally using Docker Compose, add a minimal HTML UI, enable edit/delete for products, and deploy the stack to a local Kubernetes cluster (Docker Desktop kubeadm). Document commands and changes.

---

## 2) Environment notes
- Host OS: Windows
- Shell used: PowerShell
- Docker Desktop (with Kubernetes enabled)
- kubectl configured to talk to Docker Desktop Kubernetes

---

## 3) High-level steps performed
1. Inspected repository files: `app.py`, `requirements.txt`, `README.md`, templates, and existing Docker/Kubernetes manifests.
2. Attempted to create a Python virtualenv locally but the local `python`/`py` executable was not available in the shell used by this automation.
3. Used Docker Compose to bring up MySQL + Flask app containers.
4. Verified the Flask API endpoints via PowerShell (`Invoke-RestMethod`) and validated adding products and placing orders.
5. Enhanced `app.py` to render templates and added simple UI routes (`/ui/report`, `/ui/add_product`).
6. Rebuilt the app image and restarted the `app` container.
7. Implemented product edit/delete UI: added routes, created `edit_product.html`, and updated `report.html`.
8. Deployed the application to local Kubernetes (Docker Desktop kubeadm) using the repo's YAML manifests.
9. Resolved an `ImagePullBackOff` by setting `imagePullPolicy: IfNotPresent` and ensuring the local image `inventory-app:latest` existed.

---

## 4) Exact commands run (chronological, PowerShell where applicable)

### A — Initial reads (no commands recorded, files opened):
- Read `app.py`, `requirements.txt`, `README.md`, and templates in `templates/`.

### B — Docker Compose (start stack)

```powershell
# From repo root
docker-compose -f docker-compose.yaml up --build -d
```

This built the `app` image and started two containers: `mysql` and `app`. The MySQL container initializes the database and the app waits for DB readiness.

### C — Check running containers and logs

```powershell
docker ps --filter "name=inventory-management-system-master" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker-compose -f docker-compose.yaml logs --tail=200
```

Expected/observed output: `app` and `mysql` containers running. App logs included `MySQL is ready!` and `Database tables created/verified successfully!`.

### D — Exercise API endpoints (PowerShell)

```powershell
Invoke-WebRequest -Uri http://localhost:5000 -UseBasicParsing

# Add a product (JSON API)
Invoke-RestMethod -Uri http://localhost:5000/add_product -Method Post `
  -Body (ConvertTo-Json @{ name='Widget'; description='Test product'; price=9.99; stock_quantity=10 }) `
  -ContentType 'application/json'

# Get report
(Invoke-RestMethod -Uri http://localhost:5000/report -Method Get) | ConvertTo-Json

# Place an order
Invoke-RestMethod -Uri http://localhost:5000/place_order -Method Post `
  -Body (ConvertTo-Json @{ customer_id=1; items=@( @{ product_id=1; quantity=2 } ) }) `
  -ContentType 'application/json'
```

Observed: product added successfully (product_id returned), order placed, stock decreased.

### E — Rebuild app after code changes

After editing `app.py` and templates, rebuild/restart app service only:

```powershell
docker-compose -f docker-compose.yaml up --build -d app
```

### F — Kubernetes deployment

Assuming Docker Desktop Kubernetes is enabled (kubeadm), the following commands were used to apply the repository manifests:

```powershell
kubectl apply -f mysql-deployment.yaml
kubectl apply -f inventory-app-deployment.yaml
kubectl get pods -w
```

Observed: `mysql` pod became Running. `inventory-app` pods initially reported ErrImagePull / ImagePullBackOff because the cluster attempted to pull `inventory-app:latest` from a registry and it wasn't present there.

### G — Fix for image pulling (use local image)
- Confirm local images:

```powershell
docker images --format "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}"
```

- Ensure the local image tag matches the Deployment's `image:` (`inventory-app:latest`). If not, tag the local image:

```powershell
# Example: tag the earlier built image
docker tag inventory-management-system-master-app:latest inventory-app:latest
```

- Update the deployment manifest to prefer local images:
  - Set `imagePullPolicy: IfNotPresent` in `inventory-app-deployment.yaml` under the container spec (this repository change was made and reapplied).

- Re-apply the manifest and restart rollout:

```powershell
kubectl apply -f inventory-app-deployment.yaml
kubectl rollout restart deployment inventory-app-deployment
kubectl rollout status deployment inventory-app-deployment --watch=true
kubectl get pods -w
```

After this, pods should use the local `inventory-app:latest` image and transition to `Running`.

### H — Useful kubectl checks

```powershell
kubectl get pods -o wide
kubectl get svc
kubectl describe pod <pod-name>
kubectl logs -l app=inventory-app --tail=200
kubectl logs -l app=mysql --tail=200
kubectl port-forward svc/inventory-app-service 5000:80
```

Use `kubectl port-forward` to access the app in the browser at `http://localhost:5000`.

---

## 5) Files changed in this session

- Modified: `app.py`
  - Added template rendering for `/`.
  - Added HTML UI routes: `/ui`, `/ui/add_product` (GET/POST), `/ui/report`.
  - Added `/ui/edit_product/<id>` (GET/POST) and `/ui/delete_product/<id>` (POST).
  - Added `app.config['SECRET_KEY']` for flash messages.
  - Added Decimal import and conversion for price in edit route.

- Modified: `templates/report.html`
  - Added Actions column with Edit and Delete controls.

- Added: `templates/edit_product.html`
  - Form to edit product details.

- Modified: `inventory-app-deployment.yaml`
  - Added `imagePullPolicy: IfNotPresent` under the container spec to prefer local images.

- Created: `RUNBOOK.md` (this file)

(Other repository files were read but not modified: `requirements.txt`, `README.md`, `docker-compose.yaml`, `mysql-deployment.yaml`.)

---

## 6) Current status summary (what is running now)
- Docker Compose stack: `app` and `mysql` containers ran earlier under Compose. The app was tested using the API and UI.
- Kubernetes: `mysql-deployment` and `inventory-app-deployment` were applied. Resolve image pull issues by ensuring the local image `inventory-app:latest` exists and `imagePullPolicy` is `IfNotPresent` (already applied).
- UI: `/ui/report` and `/ui/add_product` and edit/delete product UI are available in the app.

---

## 7) Important notes & recommendations

- MySQL persistence in Kubernetes: the current `mysql-deployment.yaml` uses `emptyDir` (ephemeral). If you want persistent storage across Pod restarts or node reboots, replace `emptyDir` with a PVC and StorageClass. I can add a PVC manifest if you want.

- Development workflow suggestions:
  - For rapid iteration on the app while using Kubernetes, either:
    - Use `docker-compose` for dev (fast rebuilds), or
    - Use a bind-mount in `docker-compose.yaml` for the app service to avoid rebuilding the image on every change (useful for local Compose only), or
    - Use `kubectl` + `kubectl rollout restart` after tagging/loading the local image into the cluster.

- Backups: before running destructive commands (`docker-compose down -v`, `docker volume rm`, `kubectl delete pvc`), create a SQL dump:

```powershell
# Backup example (docker-compose service name may differ)
docker-compose exec mysql sh -c 'exec mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > .\db_backup.sql
```

- Production: do not use the Flask development server for production. Use Gunicorn or uWSGI behind a proper Ingress/LoadBalancer.

---

## 8) Next suggested steps (pick any)
- I can add a PersistentVolumeClaim + patch `mysql-deployment.yaml` so MySQL data persists.
- I can add a `Place Order` browser UI page and a small client-side flow.
- I can add a `test_api.ps1` script to automate the endpoint tests (add product, place order, verify report).
- I can add healthchecks and adjust readiness/liveness probe timing if pods fail probes on slow starts.
- I can add a `helm` chart or a basic CI workflow that builds the image and applies manifests.

Tell me which next step you'd like; I can implement it and update this runbook accordingly.
