# Chaos-Engineered Self-Healing GitOps Platform 🚀

[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-ef7b4d?style=for-the-badge&logo=argo&logoColor=white)](https://argo-cd.readthedocs.io/)
[![Chaos Mesh](https://img.shields.io/badge/Chaos_Mesh-24292e?style=for-the-badge&logo=linux&logoColor=white)](https://chaos-mesh.org/)
[![Grafana](https://img.shields.io/badge/grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

A portfolio-grade, zero-cloud-cost Kubernetes platform built on Minikube. This project demonstrates modern SRE and DevOps practices including **GitOps-driven Continuous Delivery**, **Observability**, and **Chaos Engineering**.

---

## 🏗️ Architecture

```mermaid
graph TD
    subgraph GitOps Loop
        Git[GitHub Repository] -->|Polls every 3m| ArgoCD
        ArgoCD -->|Syncs State| K8s[Minikube Cluster]
    end

    subgraph "Minikube Cluster (2 Nodes)"
        direction TB
        Ingress[NGINX Ingress] -->|NodePort:30080| Frontend[Frontend: NGINX]
        Frontend -->|ClusterIP:8000| Backend[Backend: FastAPI]
        Backend -->|ClusterIP:5432| DB[(PostgreSQL StatefulSet)]
        
        Prometheus[Prometheus] -.->|Scrapes Metrics| Frontend
        Prometheus -.->|Scrapes Metrics| Backend
        Grafana[Grafana] -->|Queries| Prometheus
        
        Chaos[Chaos Mesh] -.->|Injects Faults| Backend
    end
```

## 🛠️ Tech Stack & Key Concepts
- **Infrastructure:** Minikube (2-node cluster), Docker Desktop (WSL2).
- **Application:** 3-Tier architecture (NGINX Frontend, Python/FastAPI Backend, PostgreSQL StatefulSet).
- **GitOps:** ArgoCD (Automated syncing, pruning, and self-healing from Git).
- **Resilience (K8s Native):** 
  - `HorizontalPodAutoscaler` (HPA) for CPU-based scaling.
  - `PodDisruptionBudget` (PDB) to guarantee minimum availability during disruptions.
  - `Liveness` & `Readiness` probes gating traffic.
- **Observability:** `kube-prometheus-stack` (Prometheus + Grafana).
- **Chaos Engineering:** Chaos Mesh (Injecting automated pod kills to prove MTTR).

---

## 📸 Platform Highlights

### 1. GitOps Automated Delivery (ArgoCD)
The entire platform is declaratively managed by ArgoCD. No `kubectl apply` is used in production.
![ArgoCD Sync Status](assets/screenshots/argocd-sync.png)

### 2. Full Observability (Grafana)
CPU, Memory, and Pod health are scraped by Prometheus and visualized in real-time.
![Grafana Dashboard](assets/screenshots/grafana-dashboard.png)

### 3. Self-Healing Resilience (HPA, PDB, & Chaos Mesh)
When Chaos Mesh assassinates a pod, the ReplicaSet instantly replaces it. The PodDisruptionBudget ensures zero downtime.
![Chaos Recovery and Autoscaling](assets/screenshots/hpa-pdb.png)
*(Above: Proof of pod replacement (4m vs 29m age) alongside active HPA and PDB configurations).*

### 4. Live 3-Tier Application
![Application Frontend](assets/screenshots/app-frontend.png)

### 5. AI-Assisted CI Debugging 🤖
To reduce Mean Time To Recovery (MTTR) during development, this repository features an automated, GenAI-powered CI Debugger.
- **Zero Cost:** Uses GitHub Actions free tier and Groq's free API (`llama-3.1-8b-instant`).
- **Security & Air-Gapping:** A Python script sanitizes and redacts all logs (stripping tokens, passwords, and API keys) *before* sending them to the LLM. 
- **Design Boundary:** The AI is strictly **suggestion-only**. It posts root-cause analysis as a PR comment but is mathematically prevented from auto-committing fixes or merging code.

![AI Debugger PR Comment](assets/screenshots/ai-debugger.png)

---

## 🚀 How to Run Locally

### 1. Prerequisites
- Docker Desktop (WSL2) with at least 6GB RAM allocated.
- Minikube (`minikube start --nodes 2 --cpus 2 --memory 6144`)
- Helm & Kubectl

### 2. Bootstrap GitOps
```bash
# 1. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Apply the Application Manifest
kubectl apply -f argocd/application.yaml
```
ArgoCD will automatically read this repository and deploy the Helm chart found in `helm/gitops-platform/`.

### 3. Observability & Chaos
```bash
# Install Prometheus Stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring-values.yaml

# Install Chaos Mesh
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace --set chaosDaemon.runtime=containerd --set chaosDaemon.socketPath=/run/containerd/containerd.sock --version 2.7.0

# Trigger a Chaos Experiment
kubectl apply -f chaos/pod-kill.yaml
```
