---
title: 쿠버네티스 스케줄러
content_template: templates/concept
weight: 60
---

{{% capture overview %}}

쿠버네티스에서, _스케줄링_ 은 {{< glossary_tooltip text="파드" term_id="pod" >}} 와 
{{< glossary_tooltip text="노드" term_id="node" >}} 가 일치하도록 하여 
{{< glossary_tooltip term_id="kubelet" >}}이 그것을 실행할 수 있도록 하는 것을 나타낸다.

{{% /capture %}}

{{% capture body %}}

## 스케줄링 개요 {#scheduling}

스케줄러는 노드가 할당되지 않은 새로 생성된 파드를 감시한다.
스케줄러가 발견한 모든 파드에 대해,
스케줄러는 해당 파드를 실행하기 위한 최적의 노드를 찾는 책임이 있다.
스케줄러는 아래에 설명된 스케줄링 원칙을 고려하여
이 배치 결정에 도달한다.

파드가 특정 노드에 배치되는 이유를 알고 싶거나,
또는 사용자 맞춤 스케줄러를 직접 구현하려는 경우
이 페이지는 스케줄링에 대해 배우는 데 도움이 될 것이다.

## kube-scheduler

[kube-scheduler](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler/)는
쿠버네티스의 기본 스케줄러이고,
{{< glossary_tooltip text="컨트롤 플레인" term_id="control-plane" >}} 의 일부로 실행한다.
kube-scheduler는 원하고 필요에 따라 자체 스케줄링 컴포넌트를 작성하여 
대신 사용할 수 있도록 설계되었다.

새롭게 생성된 파드 또는 다른 스케줄되지 않은 파드들을 대해,
kube-scheduler는 그것을 실행할 최적의 노드를 선택한다. 
그러나, 파드 내의 모든 컨테이너는 리소스에 대한 요구 사항이 다르며, 또한, 모든 파드에도 요구 사항이 다르다.
따라서, 특정한 스케줄링 요구 사항에 따라 
기존 노드를 필터링해야 한다.

클러스터에서, 한 파드의 스케줄링 요구사항을 만족시키는 노드는 _실행 가능한_ 노드라고 한다.
적합한 노드가 없다면, 
스케줄러가 배치할 수 있을 때까지 파드는 스케줄링되지 않은 상태로 유지된다.

스케줄러는 한 파드를 위한 실행 가능한 노드를 찾은 다음,
실행 가능한 노드를 점수를 매기기 위해 함수의 집합을 실행하고, 
실행 가능한 노드 중에서 가장 높은 점수를 가진 노드를 선택하여 파드를 실행한다.
그런 다음 스케줄러는 _binding_ 이라는 단계에서 이 결정에 대해 API 서버에 알린다.

스케줄링 결정을 위한 기술을 검토가 필요한 팩터에는
개별적이고 집합적인 자원 요구사항, 하드웨어 / 소프트웨어 / 정책 제약,
어피니티와 안티-어피니티 명세, 데이터 장소,
내부 워크로드 간섭 등이 포함된다.

## kube-scheduler 스케줄링 {#kube-scheduler-implementation}

kube-scheduler 2가지 단계에서 파드를 위한 노드를 선택한다.

1. 필터링

2. 득점(Scoring)


_필터링_ 단계에서는 파드를 스케줄하기 위한 실행 가능한 노드의 집합을 찾는다.
예를 들어, PodFitsResources 필터는 후보 노드가 
파드의 특정한 리소스 요청을 만족시키는 
충분히 이용 가능한 자원을 가지고 있는지를 확인한다.
이 단계 이후에는, 노드 리스트는 모든 적합한 노드를 포함한다. 종종, 1개보다 더 많을 수도 있다.
만약 이 리스트가 비어있다면, 파드는 여전히 스케줄되지 않는다.

_득점(scoring)_ 단계에서는, 스케줄러는 가장 적합한 파드 장소를 선택하기 위해 남아있는 노드를
순서대로 놓는다. 
스케줄러는 유효한 점수 규칙을 기준으로 필터링되어 살아남은 각 노드에 점수를 지정한다.

마침내, kube-schedular는 가장 높은 등수의 누드에 파드를 배정한다.
만약 동일한 점수의 노드가 1개 이상 존재한다면,
kube-schedular는 그 중에서 1개를 랜덤으로 선택한다.


### 기본 정책 {#default-policies}

kube-scheduler는 스케줄링 정책의 기본 집합을 가진다.

### 필터링

- `PodFitsHostPorts`: 노드에 파드가 요청하고 있는 파드 포트에 대한
  사용 가능한 포트(네트워크 프로토콜 종류)가 있는지 확인한다.

- `PodFitsHost`: 파드가 호스트네임에 따라 노드를 명시하고 있는지 확인한다.

- `PodFitsResources`: 노드가 파드의 요구사항을 만족시킬 수 있는 사용 가능한 자원(예. CPU와 메모리)을
  가지고 있는지 확인한다. 

- `PodMatchNodeSelector`: 파드의 노드 ({{< glossary_tooltip term_id="selector" >}} )가
   노드의 ({{< glossary_tooltip text="label(s)" term_id="label" >}} )과 일치하는지 확인한다.

- `NoVolumeZoneConflict`: Evaluate if the {{< glossary_tooltip text="Volumes" term_id="volume" >}}
  that a Pod requests are available on the Node, given the failure zone restrictions for
  that storage.

- `NoDiskConflict`: Evaluates if a Pod can fit on a Node due to the volumes it requests,
   and those that are already mounted.

- `MaxCSIVolumeCount`: Decides how many {{< glossary_tooltip text="CSI" term_id="csi" >}}
  volumes should be attached, and whether that's over a configured limit.

- `CheckNodeMemoryPressure`: If a Node is reporting memory pressure, and there's no
  configured exception, the Pod won't be scheduled there.

- `CheckNodePIDPressure`: If a Node is reporting that process IDs are scarce, and
  there's no configured exception, the Pod won't be scheduled there.

- `CheckNodeDiskPressure`: If a Node is reporting storage pressure (a filesystem that
   is full or nearly full), and there's no configured exception, the Pod won't be
   scheduled there.

- `CheckNodeCondition`: Nodes can report that they have a completely full filesystem,
  that networking isn't available or that kubelet is otherwise not ready to run Pods.
  If such a condition is set for a Node, and there's no configured exception, the Pod
  won't be scheduled there.

- `PodToleratesNodeTaints`: checks if a Pod's {{< glossary_tooltip text="tolerations" term_id="toleration" >}}
  can tolerate the Node's {{< glossary_tooltip text="taints" term_id="taint" >}}.

- `CheckVolumeBinding`: Evaluates if a Pod can fit due to the volumes it requests.
  This applies for both bound and unbound
  {{< glossary_tooltip text="PVCs" term_id="persistent-volume-claim" >}}.

### 득점(Scoring)

- `SelectorSpreadPriority`: Spreads Pods across hosts, considering Pods that
   belong to the same {{< glossary_tooltip text="Service" term_id="service" >}},
   {{< glossary_tooltip term_id="statefulset" >}} or
   {{< glossary_tooltip term_id="replica-set" >}}.

- `InterPodAffinityPriority`: Computes a sum by iterating through the elements
  of weightedPodAffinityTerm and adding “weight” to the sum if the corresponding
  PodAffinityTerm is satisfied for that node; the node(s) with the highest sum
  are the most preferred.

- `LeastRequestedPriority`: Favors nodes with fewer requested resources. In other
  words, the more Pods that are placed on a Node, and the more resources those
  Pods use, the lower the ranking this policy will give.

- `MostRequestedPriority`: Favors nodes with most requested resources. This policy
  will fit the scheduled Pods onto the smallest number of Nodes needed to run your
  overall set of workloads.

- `RequestedToCapacityRatioPriority`: Creates a requestedToCapacity based ResourceAllocationPriority using default resource scoring function shape.

- `BalancedResourceAllocation`: Favors nodes with balanced resource usage.

- `NodePreferAvoidPodsPriority`: Prioritizes nodes according to the node annotation
  `scheduler.alpha.kubernetes.io/preferAvoidPods`. You can use this to hint that
  two different Pods shouldn't run on the same Node.

- `NodeAffinityPriority`: Prioritizes nodes according to node affinity scheduling
   preferences indicated in PreferredDuringSchedulingIgnoredDuringExecution.
   You can read more about this in [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/configuration/assign-pod-node/).

- `TaintTolerationPriority`: Prepares the priority list for all the nodes, based on
  the number of intolerable taints on the node. This policy adjusts a node's rank
  taking that list into account.

- `ImageLocalityPriority`: Favors nodes that already have the
  {{< glossary_tooltip text="container images" term_id="image" >}} for that
  Pod cached locally.

- `ServiceSpreadingPriority`: For a given Service, this policy aims to make sure that
  the Pods for the Service run on different nodes. It favours scheduling onto nodes
  that don't have Pods for the service already assigned there. The overall outcome is
  that the Service becomes more resilient to a single Node failure.

- `CalculateAntiAffinityPriorityMap`: This policy helps implement
  [pod anti-affinity](/docs/concepts/configuration/assign-pod-node/#affinity-and-anti-affinity).

- `EqualPriorityMap`: Gives an equal weight of one to all nodes.

{{% /capture %}}
{{% capture whatsnext %}}
* [스케줄러 성능 튜닝](/ko/docs/concepts/scheduling/scheduler-perf-tuning/)에 대해 읽기
* [파드 토폴로지 분배 제약 조건](/ko/docs/concepts/workloads/pods/pod-topology-spread-constraints/)에 대해 읽기
* kube-scheduler를 위한 [레퍼런스 문서](/docs/reference/command-line-tools-reference/kube-scheduler/) 읽기
* [다중 스케줄러 구성하기](/docs/tasks/administer-cluster/configure-multiple-schedulers/)에 대해 알아보기
* [토폴로지 관리 정책](/docs/tasks/administer-cluster/topology-manager/)에 대해 알아보기
* [파드 오버헤드](/docs/concepts/configuration/pod-overhead/)에 대해 알아보기
{{% /capture %}}
