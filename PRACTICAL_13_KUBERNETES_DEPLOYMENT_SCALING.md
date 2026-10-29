# PRACTICAL - 13: Deploy and Scale the Telecom Churn Prediction Application Using Kubernetes

**Course**: MLOps Practical Series | Telecom Churn Prediction  
**Continuation from**: Practical-12: Monitor the Deployed API Using Prometheus and Grafana  
**Running Project**: Telecom Churn Prediction  
**Container Image**: `ghcr.io/231fa04f21/telecom-churn-prediction:latest`  
**Manifest Directory**: `Practical_13_Kubernetes/`  
**Kubernetes Service**: `telecom-churn-prediction-service` (NodePort)  

---

## 1. Aim & Practical Focus

- **Aim**: To deploy the tested Dockerized Telecom Churn Prediction API from GitHub Container Registry (GHCR) on a local Kubernetes cluster, expose it through a Kubernetes NodePort Service, verify health, docs, prediction, and metric endpoints, scale the application to multiple replicas, observe automated self-healing, execute a zero-downtime rolling update, and demonstrate rollback.
- **MLOps Core Concept**: Deploying a single container instance on a cloud VM or PaaS (like Render in Practical 10) leaves the application vulnerable to instance failure and unable to dynamically scale with load spikes. **Kubernetes** acts as the industry-standard container orchestrator, managing desired replica states, load balancing traffic, executing zero-downtime rolling updates, and self-healing failed containers automatically.

```
GitHub Container Registry (ghcr.io/231fa04f21/telecom-churn-prediction:latest)
                                │
                                ▼  (Image Pull)
+───────────────────────────────────────────────────────────────────────────────+
|                           Kubernetes Cluster (Minikube)                      |
|                                                                               |
|   Deployment: telecom-churn-prediction                                        |
|     ├── ReplicaSet                                                            |
|     │     ├── Pod 1 (telecom-churn-api container, port 5000)                  |
|     │     ├── Pod 2 (telecom-churn-api container, port 5000)                  |
|     │     └── Pod 3 (telecom-churn-api container, port 5000)                  |
|     │                                                                         |
|     └── Health Probes: Readiness (/health:5000) & Liveness (/health:5000)     |
|                                                                               |
|   Service: telecom-churn-prediction-service (NodePort)                        |
|     └── Routes port 80 (external) -> port 5000 (targetPort across ready Pods)|
+───────────────────────────────────────┬───────────────────────────────────────+
                                        │
                                        ▼
             Endpoints: /health | /docs | /predict | /metrics
```

---

## 2. Kubernetes vs. Apache Airflow

| Aspect | Apache Airflow | Kubernetes |
|:---|:---|:---|
| **Primary Role** | Workflow and pipeline task orchestrator | Container and deployment runtime orchestrator |
| **Core Question** | Which ML job should run first, next, or on failure? | How many container instances should run and how to route traffic? |
| **Typical Tasks** | Data extraction $\rightarrow$ preprocessing $\rightarrow$ training $\rightarrow$ evaluation | Running Flask/FastAPI servers $\rightarrow$ replicas $\rightarrow$ rolling updates |
| **Key Primitives** | DAGs, Tasks, Operators, Sensors | Deployments, Pods, Services, ReplicaSets |
| **Execution Model** | Scheduled or triggered batch execution | Always-on, long-running resilient network services |

---

## 3. Kubernetes Objects Used

| Object | Name in this Practical | Purpose |
|:---|:---|:---|
| **Deployment** | `telecom-churn-prediction` | Declares desired state, manages ReplicaSets and rolling updates |
| **ReplicaSet** | Automatically managed | Guarantees exact number of Pod replicas (e.g. 1 or 3) are running |
| **Pod** | `telecom-churn-prediction-xxxx-yyyy` | Smallest deployable unit running the Dockerized prediction container |
| **Service** | `telecom-churn-prediction-service` | Stable network abstraction and internal load balancer (NodePort) |
| **Readiness Probe** | HTTP GET `/health:5000` | Checks if Pod is ready to accept incoming traffic |
| **Liveness Probe** | HTTP GET `/health:5000` | Checks if container is alive; restarts container if unresponsive |

---

## 4. Manifest Definitions

### `Practical_13_Kubernetes/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telecom-churn-prediction
  labels:
    app: telecom-churn-prediction
spec:
  replicas: 1
  selector:
    matchLabels:
      app: telecom-churn-prediction
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: telecom-churn-prediction
    spec:
      containers:
        - name: telecom-churn-api
          image: ghcr.io/231fa04f21/telecom-churn-prediction:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 5000
          readinessProbe:
            httpGet:
              path: /health
              port: 5000
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health
              port: 5000
            initialDelaySeconds: 30
            periodSeconds: 20
            timeoutSeconds: 3
            failureThreshold: 3
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
```

### `Practical_13_Kubernetes/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: telecom-churn-prediction-service
  labels:
    app: telecom-churn-prediction
spec:
  type: NodePort
  selector:
    app: telecom-churn-prediction
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 5000
```

---

## 5. Step-by-Step Execution Guide

### Step 1 - Verify Tools
Open PowerShell and verify Docker, Minikube, and kubectl:
```powershell
docker --version
minikube version
kubectl version --client
```

---

### Step 2 - Start Local Kubernetes Cluster
```powershell
minikube start --driver=docker
```
*(Wait until Minikube reports `Done! kubectl is now configured to use "minikube" cluster`)*.

---

### Step 3 - Verify the Cluster
```powershell
kubectl cluster-info
kubectl get nodes
```
> **Expected Output**: Node `minikube` listed with `Status: Ready`.

---

### Step 4 - Apply Kubernetes Manifests
Navigate to your project directory and apply the deployment and service manifests:
```powershell
cd C:\Users\Nutha\Downloads\MLOPS-tell\MLOPS-ASS-1
kubectl apply -f Practical_13_Kubernetes/deployment.yaml
kubectl apply -f Practical_13_Kubernetes/service.yaml
```

---

### Step 5 - Wait for Deployment & Verify Pod Status
```powershell
kubectl rollout status deployment/telecom-churn-prediction
kubectl get deployments
kubectl get pods -o wide
kubectl get services
```
> **Expected Output**: `deployment.apps/telecom-churn-prediction successfully rolled out`. Pod status is `Running (1/1)`.

---

### Step 6 - Access the Service URL
Ask Minikube to provide the accessible URL for the NodePort Service:
```powershell
minikube service telecom-churn-prediction-service --url
```
*(Copy the URL displayed, e.g. `http://127.0.0.1:xxxxx`)*.

---

### Step 7 - Test API Endpoints
Using the service URL returned by Minikube, test all endpoints:

#### Test Health (`/health`):
```powershell
Invoke-RestMethod -Uri "<SERVICE_URL>/health" -Method Get
```

#### Test Swagger UI (`/docs`):
Open `<SERVICE_URL>/docs` in your browser.

#### Test Live Prediction (`/predict`):
```powershell
Invoke-RestMethod -Uri "<SERVICE_URL>/predict" -Method Post -ContentType "application/json" -Body '{"age": 70, "num_dependents": 0, "estimated_salary": 30000, "calls_made": 5, "sms_sent": 2, "data_used": 100}'
```
> **Output:** `prediction: CHURN, prediction_code: 1`

#### Test Prometheus Metrics (`/metrics`):
```powershell
Invoke-RestMethod -Uri "<SERVICE_URL>/metrics" -Method Get
```

---

### Step 8 - Inspect Pod Logs
```powershell
$pod = (kubectl get pods -l app=telecom-churn-prediction -o jsonpath='{.items[0].metadata.name}')
kubectl logs $pod
```
Confirm `event=model_loaded` and structured `event=http_request` logs are displayed.

---

### Step 9 - Scale Deployment to 3 Replicas
```powershell
kubectl scale deployment telecom-churn-prediction --replicas=3
kubectl rollout status deployment/telecom-churn-prediction
kubectl get pods -o wide
```
> **Expected Output**: 3 Pods reach `Running (1/1)` state.

Inspect the load-balancer backend endpoints:
```powershell
kubectl get endpointslice -l kubernetes.io/service-name=telecom-churn-prediction-service -o wide
```
Confirm 3 backend IP addresses are registered under the Service.

---

### Step 10 - Demonstrate Automated Self-Healing
Record a Pod name and delete it intentionally:
```powershell
$podToDelete = (kubectl get pods -l app=telecom-churn-prediction -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $podToDelete
```
Immediately observe the Pods recovering:
```powershell
kubectl get pods
```
> **Expected Observation**: The deleted Pod terminates, and Kubernetes instantly spins up a brand-new replacement Pod to maintain the desired count of 3.

---

### Step 11 - Perform a Zero-Downtime Rolling Update
Update the container image to `:v1` (or a specific commit SHA):
```powershell
kubectl set image deployment/telecom-churn-prediction telecom-churn-api=ghcr.io/231fa04f21/telecom-churn-prediction:v1
kubectl rollout status deployment/telecom-churn-prediction
```
View rollout revision history:
```powershell
kubectl rollout history deployment/telecom-churn-prediction
```

---

### Step 12 - Demonstrate Rollback
Roll the Deployment back to revision 1:
```powershell
kubectl rollout undo deployment/telecom-churn-prediction
kubectl rollout status deployment/telecom-churn-prediction
kubectl rollout history deployment/telecom-churn-prediction
```
Verify the active image:
```powershell
kubectl get deployment telecom-churn-prediction -o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

### Step 13 - Scale Back to 1 Replica
```powershell
kubectl scale deployment telecom-churn-prediction --replicas=1
kubectl get pods
```

---

## 6. Observation Table

| Activity | Expected Evidence | Student Record | Result |
|:---|:---|:---|:---:|
| **Cluster startup** | Node name and Ready status | Node `minikube` in `Ready` state | PASS |
| **Initial deployment** | Deployment READY `1/1` and Pod Running | Single Pod running with readiness probe passing | PASS |
| **Service access** | NodePort URL allows endpoint requests | `/health`, `/docs`, `/predict`, `/metrics` all 200 OK | PASS |
| **Application logs** | Structured logs via `kubectl logs` | `event=model_loaded` and request IDs logged | PASS |
| **Scale to 3** | Number of ready Pods after scaling | 3 Pods running concurrently | PASS |
| **Service backends** | EndpointSlice contains 3 ready IPs | Traffic load-balanced across 3 backend Pods | PASS |
| **Self-healing** | Deleted Pod replaced automatically | Replacement Pod created within seconds | PASS |
| **Rolling update** | Zero-downtime rolling update succeeds | `rollout status` succeeds with `maxUnavailable: 0` | PASS |
| **Rollback** | Revision restored to previous image | `rollout undo` restores revision 1 seamlessly | PASS |
| **Final scale-down** | Replica count returns to 1 | 2 Pods terminated, 1 Pod remains healthy | PASS |

---

## 7. Practical Deliverables & Screenshots Checklist

- [ ] 1. Minikube node in `Ready` state (`kubectl get nodes`).
- [ ] 2. Deployment and NodePort Service applied successfully.
- [ ] 3. Initial Pod running (`kubectl get pods -o wide`).
- [ ] 4. Terminal testing `/health` and `/predict` via the NodePort service URL.
- [ ] 5. Application logs via `kubectl logs <pod-name>`.
- [ ] 6. Three ready Pod replicas after scaling (`kubectl scale --replicas=3`).
- [ ] 7. EndpointSlice showing multiple ready backend IPs.
- [ ] 8. Self-healing demonstration showing deleted Pod replaced.
- [ ] 9. Rolling update execution and `rollout history`.
- [ ] 10. Successful rollback via `kubectl rollout undo`.
- [ ] 11. Scale-down to 1 replica.
- [ ] 12. Completed observation table.

---

## 8. Viva / Discussion Questions & Answers

1. **What is Kubernetes?**  
   An open-source container orchestration system that automates the deployment, scaling, management, networking, and availability of containerized applications.

2. **How is Kubernetes different from Docker?**  
   Docker is a containerization runtime that builds and runs individual containers on a single host. Kubernetes is an orchestrator that coordinates hundreds of containers across multiple host machines (clusters).

3. **How is Kubernetes different from Apache Airflow?**  
   Airflow orchestrates batch workflow task dependencies as Directed Acyclic Graphs (DAGs). Kubernetes orchestrates long-running containerized service runtimes, networking, and compute resources.

4. **What is container orchestration?**  
   The automated coordination of container lifecycles, including provisioning, scheduling, replica management, self-healing, networking, and rolling updates.

5. **What is a Kubernetes Pod?**  
   The smallest atomic deployable unit in Kubernetes, encapsulating one or more tightly coupled containers sharing network namespaces, storage volumes, and an IP address.

6. **What is a Deployment?**  
   A declarative Kubernetes controller that defines the desired application state, manages ReplicaSets, and orchestrates rolling updates and rollbacks.

7. **What is the role of a ReplicaSet?**  
   To guarantee that a specified number of identical Pod replicas are actively running at any given time.

8. **Why is a Kubernetes Service required?**  
   Pods are ephemeral; when a Pod crashes or is rescheduled, its IP address changes. A Service provides a permanent, stable IP/DNS entry and balances traffic across all matching ready Pods.

9. **What is the difference between a Pod IP and a Service endpoint?**  
   A Pod IP is temporary and tied to a single container instance. A Service endpoint is persistent and distributes incoming requests across multiple backend Pods.

10. **What is a NodePort Service?**  
    A Service type that exposes an application on a static port (between 30000–32767) on each cluster node's IP, allowing external clients to reach the service from outside the cluster.

11. **What is a readiness probe?**  
    A health probe that checks whether a container is ready to accept incoming user traffic. If the probe fails, the Pod is removed from the Service's active endpoints.

12. **What is a liveness probe?**  
    A health probe that determines whether a running container is still functional. If it fails consecutively, Kubernetes automatically kills and restarts the container.

13. **Why is `/health` reused for Kubernetes probes?**  
    Because `/health` verifies that the Python interpreter is running, dependencies are loaded, and the ML model is resident in memory, providing a definitive signal of application health.

14. **What happens when one Pod is manually deleted?**  
    The ReplicaSet immediately detects that the current count (2) is less than the desired count (3) and immediately launches a new Pod to restore the desired state (Self-healing).

15. **What does scaling a Deployment mean?**  
    Adjusting the desired number of Pod replicas (e.g. from 1 to 3) to handle higher concurrent user request throughput without hardware modifications.

16. **How does the Service work when three replicas are running?**  
    Incoming HTTP requests sent to the Service are distributed via round-robin or random load balancing across all three ready Pod backends.

17. **What is ImagePullBackOff?**  
    A Kubernetes Pod error indicating that the container runtime failed to pull the specified container image from the registry due to invalid image name, tag, network issue, or missing authentication secret.

18. **Why are registry tokens never written directly into YAML files?**  
    YAML files are tracked in source control. Storing tokens directly compromises credentials. Kubernetes Secrets decouple sensitive credentials from deployment definitions.

19. **What is a rolling update?**  
    A deployment release strategy where new Pod versions are gradually spun up and verified while old Pods are decommissioned, ensuring zero application downtime during updates.

20. **Why are immutable/versioned Docker image tags useful?**  
    They guarantee reproducibility and traceability. Using `latest` is ambiguous, whereas using commit SHAs or version numbers ensures exact environment reproduction and predictable rollbacks.

21. **What does `kubectl rollout status` show?**  
    The real-time progress and completion state of a deployment or image rollout.

22. **What does `kubectl rollout history` show?**  
    A chronological audit log of deployment revisions and their associated pod template configurations.

23. **When would a rollback be required?**  
    When a newly deployed application version introduces runtime exceptions, memory leaks, high latency, or model accuracy degradations.

---

## 9. Result

The tested Telecom Churn Prediction API was deployed to a local Kubernetes cluster using Minikube. The application was exposed through a NodePort Service, validated across all endpoints, scaled to 3 replicas with load balancing across EndpointSlices, demonstrated automated self-healing upon Pod deletion, and executed zero-downtime rolling updates and rollbacks.
