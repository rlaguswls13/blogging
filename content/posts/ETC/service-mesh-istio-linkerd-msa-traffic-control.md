---
author: ''
createdAt: '2026-08-26T00:25:48.619405Z'
factCheckScore: 0
id: '5514550242311234628'
notionPageId: null
publishedAt: '2026-08-25T22:45:51-07:00'
slug: service-mesh-istio-linkerd-msa-traffic-control
status: published
tags:
- ETC
- Kubernetes
- MSA
title: Service Mesh 트래픽 제어 심층 비교 — Istio의 Envoy 사이드카 vs Linkerd의 Rust 프록시, 그리고 Ambient
  Mesh 전환
updatedAt: '2026-08-26T00:25:48.619405Z'
url: https://beji-tech.blogspot.com/2026/08/service-mesh-istio-envoy-vs-linkerd.html
---

# Service Mesh 트래픽 제어 심층 비교 — Istio의 Envoy 사이드카 vs Linkerd의 Rust 프록시, 그리고 Ambient Mesh 전환

## 요약

마이크로서비스 아키텍처(MSA)가 커질수록 서비스 간 통신을 애플리케이션 코드가 아니라 인프라 레이어에서 제어하려는 요구가 커지며, 이를 해결하는 표준 패턴이 Service Mesh입니다. 본 글은 CNCF 그래듀에이트 프로젝트인 Istio와 Linkerd를 데이터 플레인 아키텍처 관점에서 비교합니다 — Istio는 Envoy 기반의 기능이 풍부한 사이드카 프록시를, Linkerd는 Rust로 새로 만든 초경량 마이크로 프록시(linkerd2-proxy)를 채택하며, 두 프로젝트가 각각 공식 문서에서 공개한 리소스 사용량 수치를 근거로 실제 트레이드오프를 짚습니다. 또한 mTLS 자동화, 가중치 기반 카나리 라우팅을 VirtualService/DestinationRule과 Gateway API HTTPRoute 실제 설정 예시로 설명하고, 사이드카 리소스 오버헤드 비판에 대한 대응으로 등장한 Istio Ambient Mesh(ztunnel + waypoint)의 구조와 그 의미를 정리합니다.

## 차별화 포인트

이 글의 차별화 지점은 "Istio는 무겁고 Linkerd는 가볍다"는 흔한 요약을 실제 공식 벤치마크 수치로 뒷받침한다는 점입니다. Istio 1.24 공식 성능 문서는 초당 1000 요청·1KB 페이로드 조건에서 사이드카 프록시 1개당 약 0.20 vCPU·60MB, ambient 모드의 노드 프록시(ztunnel)는 약 0.06 vCPU·12MB를 사용한다고 명시합니다. Linkerd는 자체 공개 벤치마크(2.10.2 vs Istio 1.10.0, 2000 RPS 조건)에서 프록시당 최대 메모리 17.8MB, CPU 10ms로 Istio 대비 약 8~9배 적은 리소스를 사용했다고 밝혔습니다. 이 두 수치를 나란히 놓고 "왜 이런 차이가 나는가"를 Envoy(범용 프록시)와 linkerd2-proxy(서비스 메시 전용 마이크로 프록시)의 설계 철학 차이로 설명하는 것이 흔한 요약형 글과 다른 지점입니다. 아울러 Linkerd의 SMI TrafficSplit이 공식적으로 deprecated 상태이고 Gateway API 기반 동적 라우팅으로 전환 중이라는, 실제로 최신 공식 문서를 확인하지 않으면 놓치기 쉬운 세부사항도 다룹니다.

## 본문

### 1. 서론 — MSA 트래픽 제어를 애플리케이션 밖으로 꺼내는 이유

마이크로서비스가 수십, 수백 개로 늘어나면 서비스 간 통신에는 로드 밸런싱, 재시도, 타임아웃, 서킷 브레이커, mTLS 암호화, 카나리 배포를 위한 트래픽 분할 같은 공통 관심사가 반복적으로 등장합니다. 이런 로직을 각 서비스 코드에 라이브러리(Netflix OSS류)로 심으면 언어별 구현이 갈라지고 버전 관리가 어려워집니다. Service Mesh는 이 문제를 애플리케이션과 나란히 배치되는 별도의 인프라 레이어(데이터 플레인)와 이를 중앙에서 제어하는 컨트롤 플레인으로 분리해 해결합니다. Kubernetes 생태계에서 이 데이터 플레인은 보통 각 Pod 옆에 붙는 프록시 컨테이너, 즉 사이드카(Sidecar) 형태로 구현되어 왔고, Istio와 Linkerd는 이 모델의 대표 구현체입니다. 두 프로젝트 모두 CNCF Graduated 프로젝트입니다 — Linkerd는 2021년 7월, Istio는 2023년 7월에 졸업했습니다.

이 글에서 반복해서 앞으로 나올 상위 개념 관계는 다음 두 축입니다. 첫째는 "데이터 플레인 프록시를 무엇으로 만들었는가"(Envoy vs 자체 Rust 프록시)이고, 둘째는 "그 프록시를 어디에 배치하는가"(Pod마다 vs 노드마다)입니다. 이 두 축이 실제 리소스 사용량과 운영 복잡도를 가르는 핵심 변수입니다.

### 2. 데이터 플레인 아키텍처 — Envoy 사이드카(Istio) vs Rust 마이크로 프록시(Linkerd)

Istio의 데이터 플레인은 Envoy 프록시로 구성됩니다. Istio 공식 아키텍처 문서는 "Envoy 프록시는 서비스에 사이드카로 배포되어, Envoy의 다양한 내장 기능으로 서비스를 논리적으로 증강한다"고 설명합니다. Envoy는 동적 서비스 디스커버리, 지능형 로드 밸런싱, TLS 종료, HTTP/2·gRPC 지원, 서킷 브레이커, 헬스 체크, 트래픽 스플리팅, 장애 주입(fault injection), 풍부한 텔레메트리 수집까지 지원하는 범용 L7 프록시입니다. 컨트롤 플레인인 istiod는 상위 수준의 라우팅 규칙을 Envoy 전용 설정으로 변환해 각 사이드카에 전파하고, 서비스 디스커버리를 표준화하며, 인증서 발급(CA) 기관 역할을 겸합니다.

반면 Linkerd는 Envoy를 채택하지 않고 linkerd2-proxy라는 자체 프록시를 Rust로 새로 만들었습니다. Linkerd 공식 문서는 이 프록시를 "서비스 메시 사용 사례를 위해 특별히 설계된 초경량 투명 마이크로 프록시(ultralight, transparent micro-proxy)"이며 "범용 프록시로 설계되지 않았다"고 명시합니다. HTTP/1.1·HTTP/2·TCP 투명 프록시, 지연시간을 고려한 L7 로드 밸런싱, 논-HTTP 트래픽을 위한 L4 로드 밸런싱, 자동 mTLS, Prometheus 메트릭 자동 노출 등 서비스 메시에 필요한 기능만 선택적으로 구현하고 나머지는 의도적으로 배제한 것이 설계 철학입니다. Linkerd 공식 블로그는 "왜 Linkerd는 Envoy를 쓰지 않는가"라는 글을 별도로 낼 정도로 이 선택을 프로젝트의 핵심 차별점으로 강조합니다.

이 아키텍처 차이는 실측 리소스 수치로 드러납니다. Istio 1.24 공식 성능·확장성 문서(`istio.io/latest/docs/ops/deployment/performance-and-scalability/`)는 2개 워커 스레드, 초당 1000 HTTP 요청, 1KB 페이로드, mTLS 활성화 조건에서 사이드카 프록시 1개당 약 0.20 vCPU, 60MB 메모리를 사용한다고 공개합니다. Linkerd는 자체 벤치마크(linkerd 2.10.2 vs istio 1.10.0, 베어메탈 클러스터, 2000 RPS 조건)에서 프록시당 최대 메모리 17.8MB, CPU 10ms를 기록해 Istio Envoy 프록시(154.6MB, 88ms) 대비 약 8.7배 적은 메모리, 8.8배 적은 CPU를 사용했다고 발표했습니다. 두 벤치마크는 서로 다른 시점·버전·조건에서 각 프로젝트가 자체 측정한 수치이므로 절대값을 직접 비교하기보다는, 두 프로젝트 모두 "Envoy 기반 사이드카가 목적 특화 경량 프록시보다 무겁다"는 방향성에는 일관되게 동의한다는 점이 핵심입니다. Pod 수가 수백 개로 늘어나는 대규모 클러스터에서는 이 프록시당 차이가 누적되어 클러스터 전체 리소스 예산에 실질적인 영향을 줍니다.

### 3. 트래픽 제어 실전 — Istio VirtualService/DestinationRule 카나리 라우팅

Istio에서 가중치 기반 카나리 배포는 `VirtualService`와 `DestinationRule` 두 CRD의 조합으로 구현합니다. `DestinationRule`은 실제 워크로드를 라벨 기준으로 subset(버전)으로 나누고, `VirtualService`는 그 subset들 사이의 트래픽 비율을 지정합니다.

```yaml
# DestinationRule: 버전별 subset 정의
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
# VirtualService: v1에 75%, v2(카나리)에 25% 트래픽 분배
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 75
    - destination:
        host: reviews
        subset: v2
      weight: 25
```

이 설정을 적용하면 애플리케이션 코드나 클라이언트 변경 없이 istiod가 이를 Envoy Route/Cluster 설정으로 변환해 각 사이드카에 전파하고, 사이드카가 실제 요청 단위로 가중치 라우팅을 수행합니다. 점진적으로 `weight` 값을 25 → 50 → 100으로 올리며 점검하는 것이 전형적인 카나리 롤아웃 절차입니다.

mTLS는 `PeerAuthentication` 리소스로 제어합니다. STRICT 모드로 지정하면 해당 워크로드는 평문 트래픽을 아예 거부합니다.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: reviews-strict-mtls
  namespace: foo
spec:
  selector:
    matchLabels:
      app: reviews
  mtls:
    mode: STRICT
```

istiod는 워크로드가 시작될 때 개인키와 CSR을 생성하도록 하고, 이를 istiod의 내장 CA가 검증·서명해 Envoy에 SDS(Secret Discovery Service) API로 전달합니다. 인증서 만료도 istiod가 주기적으로 감지해 자동 로테이션합니다 — 즉 애플리케이션은 TLS 인증서를 전혀 직접 다루지 않습니다.

### 4. 트래픽 제어 실전 — Linkerd의 TrafficSplit deprecation과 Gateway API 전환

Linkerd도 카나리·블루/그린 배포를 위한 트래픽 분할 기능을 제공하지만, 구현 방식이 Istio와 다릅니다. 기존에는 SMI(Service Mesh Interface) 표준의 `TrafficSplit` CRD로 트래픽 비율을 지정했습니다. 그러나 Linkerd 공식 문서는 이 기능이 현재 deprecated 상태이며 "동적 요청 라우팅(dynamic request routing)"으로 대체되고 있다고 명시합니다. 새로운 방식은 Kubernetes 표준 Gateway API의 `HTTPRoute` 리소스를 확장해 백엔드별 가중치를 지정하는 형태로, Istio가 자체 CRD(VirtualService)를 쓰는 것과 달리 Linkerd는 점차 Kubernetes SIG-Network가 표준화한 Gateway API 쪽으로 트래픽 라우팅 설정을 옮기는 방향을 택하고 있습니다. 이는 두 프로젝트의 또 다른 철학 차이를 보여줍니다 — Istio는 독자 API 표면(VirtualService/DestinationRule/PeerAuthentication)을 넓게 유지하는 대신 세밀한 제어를 제공하고, Linkerd는 가능한 한 Kubernetes 표준 API에 올라타 학습 곡선과 벤더 종속을 낮추는 쪽을 선호합니다. mTLS의 경우도 Linkerd는 별도 CRD 설정 없이 메시에 편입된 워크로드 사이의 통신을 기본적으로 자동 암호화하도록 설계되어 있어, Istio의 `PeerAuthentication`처럼 명시적 정책 리소스를 작성하지 않아도 되는 대신 세부 모드(PERMISSIVE 등) 조정의 유연성은 상대적으로 낮습니다.

### 5. 사이드카의 근본적 한계와 Ambient Mesh(ztunnel + waypoint)

사이드카 모델은 Pod 하나당 프록시 컨테이너 하나가 항상 따라붙는 구조이므로, 클러스터의 Pod 수가 늘어날수록 프록시 개수도 선형으로 늘어나 리소스 사용량이 누적됩니다. 또한 사이드카 주입(injection) 시점에 애플리케이션 컨테이너와 네트워크 네임스페이스를 공유해야 하므로 Pod 시작 순서(sidecar가 먼저 준비돼야 함), 업그레이드 시 Pod 재시작 필요성 같은 운영 복잡도도 함께 따라옵니다.

이런 비판에 대한 Istio 진영의 대응이 Ambient Mesh입니다. Istio 공식 문서는 Ambient 모드를 "사이드카 없이(sidecar-less)" 메시 기능을 제공하는 대안 데이터 플레인으로 소개하며, 기능을 두 계층으로 분리합니다. 1계층은 ztunnel — "노드마다 하나씩 배치되는 목적 특화 프록시"로, mTLS·인증·L4 인가처럼 L3/L4 수준 기능만 담당하고 HTTP 헤더는 들여다보지 않습니다. HBONE(HTTP CONNECT 기반 터널링 프로토콜)으로 트래픽을 라우팅합니다. 2계층은 waypoint 프록시 — L7 라우팅, L7 인가, 상세 텔레메트리가 필요한 네임스페이스에만 선택적으로 배치되는 별도의 Envoy 기반 프록시입니다. Istio 1.24 공식 성능 문서 기준 ztunnel은 프록시당 약 0.06 vCPU·12MB, waypoint는 사이드카와 비슷한 약 0.25 vCPU·60MB를 사용한다고 공개되어 있습니다. 즉 L7 기능이 필요 없는 대다수 서비스는 ztunnel만으로 훨씬 적은 리소스로 mTLS와 기본 트래픽 제어 혜택을 받고, 세밀한 L7 제어가 필요한 일부 네임스페이스에만 waypoint를 추가로 배치하는 점진적 채택이 가능해집니다. Linkerd는 아직 이런 노드 단위 공유 프록시 모델을 정식 채택하지 않고 사이드카 모델을 유지하고 있는데, 이는 프록시 자체가 이미 매우 가볍기 때문에 Ambient 같은 구조적 전환의 상대적 이득이 Istio만큼 크지 않다는 판단으로 볼 수 있습니다.

### 6. 실무 선택 기준 요약

정리하면 Envoy 기반 사이드카(Istio)는 트래픽 미러링, 헤더 기반 라우팅, 정교한 서킷 브레이커, WASM 확장 등 기능 폭이 넓은 대신 프록시당 리소스 사용량과 학습해야 할 API 표면이 크고, Rust 마이크로 프록시(Linkerd)는 기능을 서비스 메시 핵심 요구사항으로 제한하는 대신 훨씬 가볍고 설정이 단순합니다. Ambient Mesh는 이 트레이드오프를 "사이드카냐 아니냐"의 이분법에서 "필요한 네임스페이스에만 L7 기능을 얹는" 점진적 모델로 재구성하려는 시도입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Istio 데이터 플레인은 Envoy 프록시를 사이드카로 배포하며, istiod가 라우팅 규칙을 Envoy 설정으로 변환해 전파한다 | verified | istio.io 공식 아키텍처 문서(`istio.io/latest/docs/ops/deployment/architecture/`) 원문 확인 — "Envoy proxies are deployed as sidecars to services... Istiod converts high level routing rules that control traffic behavior into Envoy-specific configurations, and propagates them to the sidecars at runtime." |
| Linkerd는 Envoy 대신 Rust로 작성한 자체 마이크로 프록시(linkerd2-proxy)를 사용하며, 범용 프록시로 설계되지 않았다고 공식 문서가 명시한다 | verified | linkerd.io 공식 아키텍처 문서(`linkerd.io/2/reference/architecture/`) 원문 확인 — "an ultralight, transparent micro-proxy written in Rust... not designed as a general-purpose proxy." |
| Istio 1.24 공식 문서는 초당 1000 요청·1KB 페이로드 조건에서 사이드카 프록시 1개당 약 0.20 vCPU·60MB, ztunnel(ambient 노드 프록시)은 약 0.06 vCPU·12MB, waypoint는 약 0.25 vCPU·60MB를 사용한다고 공개했다 | verified | istio.io 공식 성능·확장성 문서(`istio.io/latest/docs/ops/deployment/performance-and-scalability/`) 원문의 벤치마크 수치 확인 |
| Linkerd 공식 벤치마크(2.10.2 vs Istio 1.10.0, 2000 RPS)는 Linkerd 프록시가 최대 메모리 17.8MB·CPU 10ms로 Istio Envoy 프록시(154.6MB·88ms) 대비 약 8~9배 적은 리소스를 사용했다고 발표했다 | verified | linkerd.io 공식 블로그(`linkerd.io/2021/05/27/linkerd-vs-istio-benchmarks/`) 원문의 수치 확인 |
| Istio 카나리 배포는 DestinationRule로 subset을 정의하고 VirtualService의 weight 필드로 트래픽 비율을 분배하는 방식으로 구현한다 | verified | istio.io 공식 트래픽 관리 문서(`istio.io/latest/docs/concepts/traffic-management/`) 원문의 VirtualService/DestinationRule 예시 및 weight 필드 설명 확인 |
| Istio는 PeerAuthentication 리소스의 STRICT/PERMISSIVE/DISABLE 모드로 mTLS를 제어하며, istiod가 CA 역할을 맡아 인증서를 발급·자동 로테이션한다 | verified | istio.io 공식 보안 문서(`istio.io/latest/docs/concepts/security/`) 원문의 PeerAuthentication 설명 및 인증서 발급 절차 확인 |
| Linkerd의 SMI TrafficSplit은 현재 deprecated 상태이며 Gateway API HTTPRoute 기반 동적 요청 라우팅으로 대체되고 있다 | verified | linkerd.io 공식 트래픽 스플리트 문서(`linkerd.io/2/features/traffic-split/`) 원문 — "The feature is currently deprecated in favor of dynamic request routing" 문구 확인 |
| Istio Ambient Mesh는 ztunnel(노드 단위 L3/L4 프록시)과 waypoint(선택적 L7 Envoy 프록시) 2계층 구조로, 사이드카 없이 메시 기능을 제공하는 대안 데이터 플레인이다 | verified | istio.io 공식 Ambient 개요 문서(`istio.io/latest/docs/ambient/overview/`) 원문의 ztunnel/waypoint 구조 설명 확인 |
| Istio와 Linkerd는 둘 다 CNCF Graduated 프로젝트이며, Linkerd는 2021년 7월, Istio는 2023년 7월에 졸업했다 | verified | CNCF 공식 발표(`www.cncf.io/announcements/2021/07/28/...linkerd-graduation/`, `www.cncf.io/announcements/2023/07/12/...istio-maturity-with-project-graduation/`) 원문의 졸업 일자 확인 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 벤치마크 수치를 실제 설계 결정에 어떻게 반영할지에 대한 필자 개인의 해석입니다.

두 프로젝트의 공식 벤치마크를 나란히 보면서 든 생각은, "리소스가 가벼우니 Linkerd가 항상 정답"이라는 단순한 결론으로 가면 안 된다는 것입니다. Envoy가 무거운 이유는 애초에 트래픽 미러링, WASM 필터, 다양한 로드 밸런싱 알고리즘, 풍부한 관측성 훅처럼 대규모 조직이 실제로 요구하는 세밀한 기능을 폭넓게 담고 있기 때문입니다. 팀 규모가 작고 요구사항이 mTLS·기본 재시도·간단한 카나리 정도라면 Linkerd의 가벼움과 단순한 운영 모델이 명백히 유리하지만, 헤더 기반 A/B 테스트나 커스텀 필터 체인처럼 세밀한 L7 제어가 실무에서 자주 필요한 조직이라면 Envoy의 기능 폭이 오히려 개발 생산성을 높여줍니다. 개인적으로 흥미로운 지점은 Ambient Mesh가 이 이분법 자체를 무력화하려 한다는 것입니다 — ztunnel로 리소스 가벼운 기본 계층을 깔고 필요한 네임스페이스에만 waypoint를 얹는 구조는, 사실상 "우리 팀은 Linkerd처럼 가볍게 시작해서 필요할 때만 Istio처럼 무겁게 확장한다"는 절충안을 Istio 생태계 안에서 구현한 셈입니다. 다만 Ambient는 아직 상대적으로 신생 기능이라 waypoint 다중 홉 환경의 지연시간, HBONE 터널링의 운영 도구 성숙도 등은 사이드카 모델만큼 검증되지 않았다는 점도 함께 고려해야 합니다.

## 한계와 반론

본 글이 인용한 두 벤치마크(Istio 1.24 공식 문서, Linkerd 2.10.2 vs Istio 1.10.0 벤치마크)는 측정 시점과 Istio 버전이 서로 다르고, 각 프로젝트가 자체적으로 측정·공개한 수치이므로 동일 조건에서의 제3자 중립 벤치마크는 아닙니다. 절대 수치를 그대로 프로덕션 용량 산정에 대입하기보다는 클러스터별로 재현해 검증하는 것이 안전합니다. 더 근본적으로, Service Mesh 도입 자체를 재고할 필요도 있습니다 — 서비스 수가 10개 미만인 소규모 시스템이거나, 이미 API Gateway와 클라이언트 라이브러리 수준에서 재시도·타임아웃·mTLS를 충분히 처리하고 있다면 메시 도입은 컨트롤 플레인 운영, 사이드카 업그레이드, 인증서 관리라는 새로운 운영 부담만 추가할 뿐 실익이 크지 않습니다. 특히 사이드카 주입이 Pod 시작 순서 문제(istio-init 컨테이너 경합 등)나 리소스 요청/제한 계산의 복잡도를 늘리는 것은 실제 도입 조직들이 공통으로 겪는 초기 마찰입니다. 메시 도입 여부는 "MSA를 쓰는가"가 아니라 "서비스 간 트래픽 정책을 중앙에서 일관되게 강제해야 할 만큼 조직·서비스 규모가 커졌는가"를 기준으로 판단해야 합니다.

## 참고문헌

1. Istio, "Istio Architecture (Envoy sidecar, istiod)", istio.io, https://istio.io/latest/docs/ops/deployment/architecture/ (확인일: 2026-08-26)
2. Istio, "Performance and Scalability (프록시 리소스 벤치마크)", istio.io, https://istio.io/latest/docs/ops/deployment/performance-and-scalability/ (확인일: 2026-08-26)
3. Istio, "Ambient Mesh Overview (ztunnel, waypoint)", istio.io, https://istio.io/latest/docs/ambient/overview/ (확인일: 2026-08-26)
4. Istio, "Traffic Management Concepts (VirtualService, DestinationRule)", istio.io, https://istio.io/latest/docs/concepts/traffic-management/ (확인일: 2026-08-26)
5. Istio, "Security (PeerAuthentication, mTLS)", istio.io, https://istio.io/latest/docs/concepts/security/ (확인일: 2026-08-26)
6. Linkerd, "Architecture (linkerd2-proxy)", linkerd.io, https://linkerd.io/2/reference/architecture/ (확인일: 2026-08-26)
7. Linkerd, "Traffic Split (TrafficSplit deprecation)", linkerd.io, https://linkerd.io/2/features/traffic-split/ (확인일: 2026-08-26)
8. Linkerd, "Benchmarking Linkerd and Istio", linkerd.io, https://linkerd.io/2021/05/27/linkerd-vs-istio-benchmarks/ (확인일: 2026-08-26)
9. CNCF, "Linkerd Project Page", cncf.io, https://www.cncf.io/projects/linkerd/ (확인일: 2026-08-26)
10. CNCF, "Cloud Native Computing Foundation Reaffirms Istio Maturity with Project Graduation", cncf.io, https://www.cncf.io/announcements/2023/07/12/cloud-native-computing-foundation-reaffirms-istio-maturity-with-project-graduation/ (확인일: 2026-08-26)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과, 사이드카 모델의 미래에 대한 필자 개인의 견해를 담고 있습니다.

Istio와 Linkerd의 아키텍처 대비는 결국 "얼마나 많은 기능을 얼마나 적은 자원으로 감당할 것인가"라는 인프라 소프트웨어의 오래된 트레이드오프가 서비스 메시 영역에서 재현된 것입니다. 흥미로운 점은 두 프로젝트가 서로 다른 방향에서 같은 결론으로 수렴하고 있다는 것입니다. Linkerd는 애초에 프록시를 8~9배 가볍게 만들어(자체 벤치마크 기준 17.8MB vs 154.6MB) 사이드카 모델의 비용 자체를 낮추는 전략을 택했고, Istio는 무거운 Envoy 사이드카(약 0.20 vCPU·60MB)를 유지하되 Ambient Mesh의 ztunnel(약 0.06 vCPU·12MB)로 "모든 Pod에 프록시를 강제하지 않는" 방향으로 구조를 바꾸고 있습니다. 두 접근 모두 궁극적으로는 "메시 도입 비용을 낮춰 채택 장벽을 없앤다"는 같은 문제의식에서 출발합니다. 다만 Ambient Mesh처럼 노드 단위 공유 프록시로 가는 구조는 L3/L4와 L7 책임을 물리적으로 분리하면서 장애 발생 시 원인 추적 지점이 늘어나는 새로운 관측성 과제를 만들어낼 가능성도 있어, 이 구조가 사이드카 모델만큼 충분히 검증되려면 시간이 더 필요하다고 봅니다. 실무 관점에서는 신규로 메시를 도입하는 조직이라면 Istio Ambient나 Linkerd처럼 리소스 오버헤드를 낮춘 옵션을 먼저 검토하고, 기존 Istio 사이드카 환경을 이미 운영 중인 조직은 네임스페이스 단위로 Ambient를 점진 전환해보는 것이 두 세계의 장점을 함께 취하는 현실적인 경로라고 생각합니다.

## 꼬리질문

1. Istio Ambient Mesh의 ztunnel-waypoint 2계층 구조에서, waypoint를 거치는 요청의 실제 지연시간(hop 추가로 인한 오버헤드)은 기존 사이드카 모델 대비 어느 정도 차이가 나는가?
2. Linkerd가 TrafficSplit을 deprecated 처리하고 Gateway API HTTPRoute 기반 라우팅으로 완전히 전환하면, Flagger 같은 progressive delivery 도구들의 통합 방식은 어떻게 바뀌는가?

## 백링크

- [Kubernetes Operator 패턴의 이해와 활용: Custom Controller를 통한 자동화 설계](https://beji-tech.blogspot.com/2026/08/kubernetes-operator-custom-controller.html)
- [대규모 시스템을 위한 로드 밸런싱(Load Balancing) 알고리즘과 L4 vs L7 스위치의 차이](https://beji-tech.blogspot.com/2026/08/load-balancing-l4-vs-l7.html)
- [Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)