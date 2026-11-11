#!/bin/bash
# CrossLayer - Cluster Inspection Script
# Run on k8s-master-1 to collect complete cluster inventory

set -e

OUTPUT_FILE="${1:-crosslayer_cluster_inspection.txt}"

echo "CrossLayer Cluster Inspection - $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee "$OUTPUT_FILE"
echo "================================================================" | tee -a "$OUTPUT_FILE"

echo -e "\n=== 1. MICROK8S STATUS ===" | tee -a "$OUTPUT_FILE"
microk8s status 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 2. NODES (WIDE) ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get nodes -o wide 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 3. NODE RESOURCE SUMMARY ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
CPU_CORES:.status.capacity.cpu,\
CPU_ALLOC:.status.allocatable.cpu,\
MEMORY:.status.capacity.memory,\
MEM_ALLOC:.status.allocatable.memory,\
OS:.status.nodeInfo.osImage,\
KUBELET:.status.nodeInfo.kubeletVersion 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 4. NODE LABELS AND TAINTS ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl describe nodes | grep -E "^Name:|Taints:|Roles:|Labels:" 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 5. KUBE-SYSTEM PODS ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get pods -n kube-system -o wide 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 6. OBSERVABILITY PODS ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get pods -n observability -o wide 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 7. ALL NAMESPACES ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get namespaces 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 8. CROSSLAYER WORKLOADS ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get pods -n crosslayer-workloads -o wide 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 9. ALL SERVICES ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get svc -A 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 10. STORAGE CLASSES ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl get storageclass 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 11. CLUSTER-INFO ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl cluster-info 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 12. TOP NODES (RESOURCE USAGE) ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl top nodes 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n=== 13. TOP PODS (CROSSLAYER) ===" | tee -a "$OUTPUT_FILE"
microk8s kubectl top pods -n crosslayer-workloads 2>&1 | tee -a "$OUTPUT_FILE"

echo -e "\n================================================================" | tee -a "$OUTPUT_FILE"
echo "Inspection complete. Output saved to: $OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
