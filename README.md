# AutoPilot Ops

A self-healing CI/CD platform that automatically deploys applications to
Kubernetes **and** detects + fixes common production incidents (crash
loops, memory pressure, failed rollouts) without human intervention.

Built to run entirely on **AWS Free Tier** using a single `t2.micro`
instance running `k3s` (lightweight Kubernetes) - so it costs $0 to run
and demo.

📄 See [`docs/architecture.md`](docs/architecture.md) for the full
architecture diagram and design rationale.

## What it does

| Layer | Tool |
|---|---|
| CI/CD | GitHub Actions |
| Container runtime | Docker |
| Orchestration | k3s (lightweight Kubernetes) |
| Infra as Code | Terraform |
| Security scanning | Trivy |
| Monitoring | Prometheus + Grafana |
| Alerting | Alertmanager |
| **Auto-remediation** | Custom Python webhook bot (the unique piece) |

## Repo structure

```
autopilot-ops/
├── app/                  # Demo Flask microservice
├── terraform/             # AWS infra provisioning (EC2 + security group)
├── k8s/                   # Kubernetes manifests (deployment, service, HPA, RBAC)
├── .github/workflows/      # CI/CD pipeline
├── monitoring/            # Prometheus/Grafana/Alertmanager config
├── remediation/            # The self-healing bot
└── docs/                  # Architecture diagram & notes
```

## Setup (step by step)

### 1. Provision infrastructure
```bash
cd terraform
terraform init
terraform apply -var="key_pair_name=<your-aws-keypair-name>"
```
This spins up a free-tier EC2 instance with k3s pre-installed.

### 2. Set GitHub Secrets
In your repo settings, add:
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `EC2_HOST` (public IP from terraform output)
- `EC2_SSH_KEY` (private key content)

### 3. Deploy base manifests
```bash
scp -i <key>.pem -r k8s ubuntu@<EC2_IP>:~/
ssh -i <key>.pem ubuntu@<EC2_IP>
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/remediation-bot.yaml
```

### 4. Install monitoring stack
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  -f monitoring/prometheus-values.yaml -n monitoring --create-namespace
kubectl apply -f monitoring/alertmanager-config.yaml
```

### 5. Push code to trigger CI/CD
Push to `main` and watch GitHub Actions build, scan, and deploy automatically.

### 6. Trigger self-healing (demo)
```bash
curl http://<EC2_IP>:30080/simulate-crash
# watch the pod crash-loop, then get auto-restarted by the bot
kubectl get pods -n autopilot-ops -w
```

## Resume bullet points (use these)

- Designed and deployed a self-healing DevOps platform on AWS using
  Terraform, k3s, and GitHub Actions, implementing a GitOps-style
  CI/CD pipeline with automated security scanning (Trivy) gating every
  deployment.
- Built a custom Python remediation service that consumes Prometheus/
  Alertmanager webhooks to automatically restart crash-looping pods,
  roll back degraded deployments, and recycle high-memory pods -
  reducing manual incident response.
- Implemented least-privilege RBAC, resource-scoped autoscaling (HPA),
  and cooldown-based guardrails to prevent remediation loops.
- Optimized infrastructure cost by choosing k3s over managed Kubernetes
  (EKS), running the entire stack within AWS Free Tier limits.

## Likely interview questions you should be ready for

- "Why k3s instead of EKS/managed Kubernetes?" → cost + it's still real
  upstream Kubernetes, just lighter control plane.
- "How do you prevent the bot from restart-looping forever?" → the
  cooldown guardrail (`COOLDOWN_SECONDS` in `webhook_server.py`).
- "What if the remediation bot itself crashes?" → it's just another
  Deployment with a liveness probe like any other workload; you could
  extend by making it self-monitor too (good honest answer if asked to
  extend the project further).
- "How is this different from just using Kubernetes' built-in
  restartPolicy?" → K8s restarts crashed containers automatically, but
  it does NOT roll back bad deployments, recycle memory-leaking pods
  before OOMKill, or notify a team - that's the gap this project fills.

## Suggested next steps to make it even stronger

- Replace SSH-based deploy with ArgoCD for true GitOps
- Add a `/metrics` endpoint to the remediation bot itself (meta-monitoring)
- Write a couple of Grafana dashboard JSON files and commit them to `monitoring/`
