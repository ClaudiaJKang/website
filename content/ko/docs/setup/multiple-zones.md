---
title: 여러 영역에서 구동
weight: 90
content_template: templates/concept
---

{{% capture overview %}}

이 페이지는 여러 영역에서 어떻게 클러스터를 구동하는지 설명한다. 

{{% /capture %}}

{{% capture body %}}

## 소개

쿠버네티스 1.2는 여러 실패 영역의 단일 클러스터 동작을 위한 지원을 추가했다.
(여기서 이를 "영역"이라고 하며, GCE는 단순히 "영역"이라고 하고, AWS는 "가용 영역"이라고 부른다.)
이것은 보다 광범위한 클러스터 연합의 경량화 버전이다. 
(이전에는 별칭 ["Ubernetes"](https://github.com/kubernetes/community/blob/{{< param "githubbranch" >}}/contributors/design-proposals/multicluster/federation.md)로 불렸었다.)
전체 클러스터 연합은 다른 지역이나 
클라우드 공급자 (또는 온-프레미스 데이터 센터)에서 실행되는 
쿠버네티스 클러스터를 결합 할 수 있다.
그러나, 많은 사용자는 단일 클라우드 제공 업체의 여러 영역에서 
보다 많은 쿠버네티스 클러스터를 실행하기를 원한다.
이는 결국 1.2의 여러 영역 지원을 허용하는 것이다.(이전에는 별칭 "Ubernetes Lite"라는 별칭으로 사용되었다).

여러영역 지원은 의도적으로 제한된다. 
하나의 단일 쿠버네티스 클러스터는 여러 영역에서 실행할 수 있지만, 동일한 지역(및 클라우드 공급자) 내에서만 가능하다.
오직 GCE와 AWS는 현재 자동적으로 지원한다. 
(간단하게 노드 및 추가할 적절한 레이블을 정렬함으로써, 
다른 클라우드 또는 베어메탈에 쉽게 유사한 지원을 추가할 수 있다.)

## 기능

노드가 시작될 때, kubelet은 자동적으로 
영역 정보와 함께 레이블을 추가한다.

쿠버네티스는 단일 영역 클러스터의 노드를 통해 자동으로 레플리케이션 컨트롤러나 
서비스를 파드로 분산한다. (실패의 영향을 줄이기 위함.)
다중 영역의 클러스터에서 이 분산하는 행동은 
여러 영역으로 확장한다. (실패의 영향을 줄이기 위함.)
(이것은 `SelectorSpreadPriority`로 이루어진다.).  
이것은 최선의 배치이므로, 클러스터의 영역이 이기종일 경우,
(예를 들면 다른 수의 노드, 다른 유형의 노드 또는 다른 파드의 리소스 요구 사항), 
영역을 가로질러 파드로 완벽하게 분산되지 않을 수 있다.
원한다면, 균등 영역(같은 수의 노드와 같은 유형의 노드)을 사용하여 
불균등하게 퍼질 확률을 줄일 수 있다.

퍼시스턴트 볼륨을 생성할 때, 
`PersistentVolumeLabel` 어드미션 컨트롤러는 자동적으로 영역 레이블을 추가한다. 
The scheduler (`VolumeZonePredicate`를 통해) will then ensure that pods that claim a
given volume are only placed into the same zone as that volume, as volumes
cannot be attached across zones.

## 제한 사항

There are some important limitations of the multizone support:

* We assume that the different zones are located close to each other in the
network, so we don't perform any zone-aware routing.  In particular, traffic
that goes via services might cross zones (even if some pods backing that service
exist in the same zone as the client), and this may incur additional latency and cost.

* Volume zone-affinity will only work with a `PersistentVolume`, and will not
work if you directly specify an EBS volume in the pod spec (for example).

* Clusters cannot span clouds or regions (this functionality will require full
federation support).

* Although your nodes are in multiple zones, kube-up currently builds
a single master node by default.  While services are highly
available and can tolerate the loss of a zone, the control plane is
located in a single zone.  Users that want a highly available control
plane should follow the [high availability](/docs/admin/high-availability) instructions.

### Volume limitations
The following limitations are addressed with [topology-aware volume binding](/docs/concepts/storage/storage-classes/#volume-binding-mode).

* StatefulSet volume zone spreading when using dynamic provisioning is currently not compatible with
  pod affinity or anti-affinity policies.

* If the name of the StatefulSet contains dashes ("-"), volume zone spreading
  may not provide a uniform distribution of storage across zones.

* When specifying multiple PVCs in a Deployment or Pod spec, the StorageClass
  needs to be configured for a specific single zone, or the PVs need to be
  statically provisioned in a specific zone. Another workaround is to use a
  StatefulSet, which will ensure that all the volumes for a replica are
  provisioned in the same zone.

## 연습

We're now going to walk through setting up and using a multi-zone
cluster on both GCE & AWS.  To do so, you bring up a full cluster
(specifying `MULTIZONE=true`), and then you add nodes in additional zones
by running `kube-up` again (specifying `KUBE_USE_EXISTING_MASTER=true`).

### 클러스터 가져오기

Create the cluster as normal, but pass MULTIZONE to tell the cluster to manage multiple zones; creating nodes in us-central1-a.

GCE:

```shell
curl -sS https://get.k8s.io | MULTIZONE=true KUBERNETES_PROVIDER=gce KUBE_GCE_ZONE=us-central1-a NUM_NODES=3 bash
```

AWS:

```shell
curl -sS https://get.k8s.io | MULTIZONE=true KUBERNETES_PROVIDER=aws KUBE_AWS_ZONE=us-west-2a NUM_NODES=3 bash
```

This step brings up a cluster as normal, still running in a single zone
(but `MULTIZONE=true` has enabled multi-zone capabilities).

### 라벨이 지정된 노드 확인

View the nodes; you can see that they are labeled with zone information.
They are all in `us-central1-a` (GCE) or `us-west-2a` (AWS) so far.  The
labels are `failure-domain.beta.kubernetes.io/region` for the region,
and `failure-domain.beta.kubernetes.io/zone` for the zone:

```shell
kubectl get nodes --show-labels
```

The output is similar to this:

```shell
NAME                     STATUS                     ROLES    AGE   VERSION          LABELS
kubernetes-master        Ready,SchedulingDisabled   <none>   6m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-1,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-master
kubernetes-minion-87j9   Ready                      <none>   6m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-87j9
kubernetes-minion-9vlv   Ready                      <none>   6m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-9vlv
kubernetes-minion-a12q   Ready                      <none>   6m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-a12q
```

### 두번째 영역에 더 많은 노드 추가하기

Let's add another set of nodes to the existing cluster, reusing the
existing master, running in a different zone (us-central1-b or us-west-2b).
We run kube-up again, but by specifying `KUBE_USE_EXISTING_MASTER=true`
kube-up will not create a new master, but will reuse one that was previously
created instead.

GCE:

```shell
KUBE_USE_EXISTING_MASTER=true MULTIZONE=true KUBERNETES_PROVIDER=gce KUBE_GCE_ZONE=us-central1-b NUM_NODES=3 kubernetes/cluster/kube-up.sh
```

On AWS we also need to specify the network CIDR for the additional
subnet, along with the master internal IP address:

```shell
KUBE_USE_EXISTING_MASTER=true MULTIZONE=true KUBERNETES_PROVIDER=aws KUBE_AWS_ZONE=us-west-2b NUM_NODES=3 KUBE_SUBNET_CIDR=172.20.1.0/24 MASTER_INTERNAL_IP=172.20.0.9 kubernetes/cluster/kube-up.sh
```


View the nodes again; 3 more nodes should have launched and be tagged
in us-central1-b:

```shell
kubectl get nodes --show-labels
```

The output is similar to this:

```shell
NAME                     STATUS                     ROLES    AGE   VERSION           LABELS
kubernetes-master        Ready,SchedulingDisabled   <none>   16m   v1.13.0           beta.kubernetes.io/instance-type=n1-standard-1,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-master
kubernetes-minion-281d   Ready                      <none>   2m    v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-b,kubernetes.io/hostname=kubernetes-minion-281d
kubernetes-minion-87j9   Ready                      <none>   16m   v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-87j9
kubernetes-minion-9vlv   Ready                      <none>   16m   v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-9vlv
kubernetes-minion-a12q   Ready                      <none>   17m   v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-a12q
kubernetes-minion-pp2f   Ready                      <none>   2m    v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-b,kubernetes.io/hostname=kubernetes-minion-pp2f
kubernetes-minion-wf8i   Ready                      <none>   2m    v1.13.0           beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-b,kubernetes.io/hostname=kubernetes-minion-wf8i
```

### 볼륨 어피니티

Create a volume using the dynamic volume creation (only PersistentVolumes are supported for zone affinity):

```json
kubectl create -f - <<EOF
{
  "kind": "PersistentVolumeClaim",
  "apiVersion": "v1",
  "metadata": {
    "name": "claim1",
    "annotations": {
        "volume.alpha.kubernetes.io/storage-class": "foo"
    }
  },
  "spec": {
    "accessModes": [
      "ReadWriteOnce"
    ],
    "resources": {
      "requests": {
        "storage": "5Gi"
      }
    }
  }
}
EOF
```

{{< note >}}
For version 1.3+ Kubernetes will distribute dynamic PV claims across
the configured zones. For version 1.2, dynamic persistent volumes were
always created in the zone of the cluster master
(here us-central1-a / us-west-2a); that issue
([#23330](https://github.com/kubernetes/kubernetes/issues/23330))
was addressed in 1.3+.
{{< /note >}}

Now let's validate that Kubernetes automatically labeled the zone & region the PV was created in.

```shell
kubectl get pv --show-labels
```

The output is similar to this:

```shell
NAME           CAPACITY   ACCESSMODES   RECLAIM POLICY   STATUS    CLAIM            STORAGECLASS    REASON    AGE       LABELS
pv-gce-mj4gm   5Gi        RWO           Retain           Bound     default/claim1   manual                    46s       failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a
```

So now we will create a pod that uses the persistent volume claim.
Because GCE PDs / AWS EBS volumes cannot be attached across zones,
this means that this pod can only be created in the same zone as the volume:

```yaml
kubectl create -f - <<EOF
kind: Pod
apiVersion: v1
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: claim1
EOF
```

Note that the pod was automatically created in the same zone as the volume, as
cross-zone attachments are not generally permitted by cloud providers:

```shell
kubectl describe pod mypod | grep Node
```

```shell
Node:        kubernetes-minion-9vlv/10.240.0.5
```

And check node labels:

```shell
kubectl get node kubernetes-minion-9vlv --show-labels
```

```shell
NAME                     STATUS    AGE    VERSION          LABELS
kubernetes-minion-9vlv   Ready     22m    v1.6.0+fff5156   beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-9vlv
```

### 여러 영역에 파드 분배하기

Pods in a replication controller or service are automatically spread
across zones.  First, let's launch more nodes in a third zone:

GCE:

```shell
KUBE_USE_EXISTING_MASTER=true MULTIZONE=true KUBERNETES_PROVIDER=gce KUBE_GCE_ZONE=us-central1-f NUM_NODES=3 kubernetes/cluster/kube-up.sh
```

AWS:

```shell
KUBE_USE_EXISTING_MASTER=true MULTIZONE=true KUBERNETES_PROVIDER=aws KUBE_AWS_ZONE=us-west-2c NUM_NODES=3 KUBE_SUBNET_CIDR=172.20.2.0/24 MASTER_INTERNAL_IP=172.20.0.9 kubernetes/cluster/kube-up.sh
```

Verify that you now have nodes in 3 zones:

```shell
kubectl get nodes --show-labels
```

Create the guestbook-go example, which includes an RC of size 3, running a simple web app:

```shell
find kubernetes/examples/guestbook-go/ -name '*.json' | xargs -I {} kubectl create -f {}
```

The pods should be spread across all 3 zones:

```shell
kubectl describe pod -l app=guestbook | grep Node
```

```shell
Node:        kubernetes-minion-9vlv/10.240.0.5
Node:        kubernetes-minion-281d/10.240.0.8
Node:        kubernetes-minion-olsh/10.240.0.11
```

```shell
kubectl get node kubernetes-minion-9vlv kubernetes-minion-281d kubernetes-minion-olsh --show-labels
```

```shell
NAME                     STATUS    ROLES    AGE    VERSION          LABELS
kubernetes-minion-9vlv   Ready     <none>   34m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-a,kubernetes.io/hostname=kubernetes-minion-9vlv
kubernetes-minion-281d   Ready     <none>   20m    v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-b,kubernetes.io/hostname=kubernetes-minion-281d
kubernetes-minion-olsh   Ready     <none>   3m     v1.13.0          beta.kubernetes.io/instance-type=n1-standard-2,failure-domain.beta.kubernetes.io/region=us-central1,failure-domain.beta.kubernetes.io/zone=us-central1-f,kubernetes.io/hostname=kubernetes-minion-olsh
```


Load-balancers span all zones in a cluster; the guestbook-go example
includes an example load-balanced service:

```shell
kubectl describe service guestbook | grep LoadBalancer.Ingress
```

The output is similar to this:

```shell
LoadBalancer Ingress:   130.211.126.21
```

Set the above IP:

```shell
export IP=130.211.126.21
```

Explore with curl via IP:

```shell
curl -s http://${IP}:3000/env | grep HOSTNAME
```

The output is similar to this:

```shell
  "HOSTNAME": "guestbook-44sep",
```

Again, explore multiple times:

```shell
(for i in `seq 20`; do curl -s http://${IP}:3000/env | grep HOSTNAME; done)  | sort | uniq
```

The output is similar to this:

```shell
  "HOSTNAME": "guestbook-44sep",
  "HOSTNAME": "guestbook-hum5n",
  "HOSTNAME": "guestbook-ppm40",
```

The load balancer correctly targets all the pods, even though they are in multiple zones.

### 클러스터 강제 종료

When you're done, clean up:

GCE:

```shell
KUBERNETES_PROVIDER=gce KUBE_USE_EXISTING_MASTER=true KUBE_GCE_ZONE=us-central1-f kubernetes/cluster/kube-down.sh
KUBERNETES_PROVIDER=gce KUBE_USE_EXISTING_MASTER=true KUBE_GCE_ZONE=us-central1-b kubernetes/cluster/kube-down.sh
KUBERNETES_PROVIDER=gce KUBE_GCE_ZONE=us-central1-a kubernetes/cluster/kube-down.sh
```

AWS:

```shell
KUBERNETES_PROVIDER=aws KUBE_USE_EXISTING_MASTER=true KUBE_AWS_ZONE=us-west-2c kubernetes/cluster/kube-down.sh
KUBERNETES_PROVIDER=aws KUBE_USE_EXISTING_MASTER=true KUBE_AWS_ZONE=us-west-2b kubernetes/cluster/kube-down.sh
KUBERNETES_PROVIDER=aws KUBE_AWS_ZONE=us-west-2a kubernetes/cluster/kube-down.sh
```

{{% /capture %}}
