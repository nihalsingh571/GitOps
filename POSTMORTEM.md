# Incident Postmortem: Backend Pod Assassination (Chaos Experiment) 🚨

**Date:** August 6, 2026  
**Authors:** Nihal Kumar  
**Status:** Resolved (Self-Healed)  
**Incident Type:** Simulated Chaos Engineering (Pod Kill)

---

## 📄 Summary
At approximately 11:57 UTC, a deliberate chaos engineering experiment (`backend-pod-kill`) was executed against the `gitops-app` namespace via **Chaos Mesh**. The experiment abruptly terminated a random `backend` pod serving live traffic. 

Thanks to the platform's declarative resilience patterns (ReplicaSet auto-healing, Liveness/Readiness probes, and a PodDisruptionBudget), the system experienced **zero downtime**. The Mean Time To Recovery (MTTR) for full capacity restoration was ~15 seconds.

## 🕒 Timeline (UTC)
- **11:56:45** - `podchaos.chaos-mesh.org/backend-pod-kill` applied to the cluster.
- **11:57:24** - Chaos controller intercepts the backend API and violently kills pod `backend-7f6d584c79-2mfbb`.
- **11:57:25** - Kubernetes ReplicaSet detects the actual state (1 pod) no longer matches the desired state (2 pods) defined in Git.
- **11:57:26** - ReplicaSet schedules replacement pod `backend-7f6d584c79-ttd5m`.
- **11:57:36** - New pod starts. Backend `init_db()` successfully connects to PostgreSQL.
- **11:57:40** - Readiness probe (`/ready`) returns `200 OK`. Pod is added to the Service endpoint pool. 
- **11:57:41** - System is fully restored to 100% capacity. 

## 💥 Impact
- **End-User Impact:** **None.** Frontend NGINX successfully routed all traffic to the surviving backend pod while the dead pod was replaced.
- **Data Loss:** **None.** Backend pods are stateless. PostgreSQL StatefulSet was unaffected.

## 🔎 Root Cause (Simulated)
The incident was a planned fault injection using the CNCF Chaos Mesh project to validate the disaster recovery mechanisms of the GitOps platform.

## 🛡️ Defenses That Worked
1. **ReplicaSet Controllers:** Instantly noticed the missing pod and requested a new one.
2. **PodDisruptionBudget (PDB):** Our PDB is configured with `minAvailable: 1`. This prevented Chaos Mesh from killing the *second* pod while the system was recovering the first one.
3. **Readiness Probes:** The NGINX frontend did not route traffic to the recovering pod until its `/ready` probe confirmed a live DB connection, preventing 503 errors.
4. **GitOps (ArgoCD):** If the deployment had been deleted entirely, ArgoCD's `selfHeal: true` flag would have restored it in under 3 minutes.

## 🎓 Lessons Learned
- The `nodeSelector` fix applied to the PostgreSQL StatefulSet during Phase 2 was critical. Without it, the backend recovery would have hung indefinitely trying to connect to an unschedulable database.
- Relying on a boolean `_db_ready` startup flag in the application code was an anti-pattern. Moving the database connection check directly into the Kubernetes Readiness Probe ensured accurate real-time routing.

## 📎 References
- [View Chaos Recovery Proof](assets/screenshots/hpa-pdb.png)
- [View ArgoCD State](assets/screenshots/argocd-sync.png)
