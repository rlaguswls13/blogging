---
author: ''
createdAt: '2026-08-19T06:18:38.069812Z'
factCheckScore: 0
id: '9096340761346102671'
notionPageId: null
publishedAt: '2026-08-22T06:10:56-07:00'
slug: cap-pacelc-kafka-cassandra-replication
status: published
tags:
- Advanced
- CAP Theorem
- PACELC
- Kafka
- Cassandra
- Distributed Systems
title: 분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프
updatedAt: '2026-08-19T06:18:38.069812Z'
url: https://beji-tech.blogspot.com/2026/08/cap-pacelc-kafka-isr-cassandra.html
---

# 분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프

## 요약

CAP 정리는 "일관성·가용성·파티션 허용성 중 두 개만 가질 수 있다"는 단순한 문구로 자주 인용되지만, 이 요약만으로는 실제 분산 시스템 설계에 거의 도움이 되지 않습니다. 파티션은 항상 일어나는 게 아니고, 파티션이 없을 때조차 지연시간(Latency)과 일관성(Consistency) 사이의 트레이드오프는 사라지지 않기 때문입니다. 이 글은 Eric Brewer의 CAP 원전과 Gilbert-Lynch의 수학적 증명을 정확한 정의부터 짚고, Daniel Abadi가 제안한 PACELC 정리로 그 한계를 어떻게 보완하는지 설명한 뒤, 이 이론이 실제 시스템에서 어떻게 구현되는지를 Kafka의 ISR(In-Sync Replicas)과 Cassandra의 튜너블 컨시스턴시(Tunable Consistency) 두 사례로 구체적으로 분석합니다.

## 차별화 포인트

<!-- 내부 전용 섹션, 라이브 배포 시 자동 제거됨 -->

대부분의 "CAP 정리 요약" 글은 브루어의 세 속성 정의를 나열하고 끝나지만, 이 글은 Brewer의 PODC 기조연설 원문(PDF), Gilbert-Lynch의 SIGACT News 증명 논문 원문, Abadi의 PACELC IEEE Computer 논문 원문을 직접 확인해 서지정보(권/호/페이지)까지 대조했고, 여기서 그치지 않고 Kafka의 `acks`/`min.insync.replicas`, Cassandra의 Consistency Level과 `W + R > RF` 공식이라는 실제 운영 설정값을 CAP/PACELC 좌표에 정확히 매핑하는 비교표를 제시한다. "이 DB는 CP다/AP다"라는 흔한 이분법적 라벨링이 왜 실무에서 위험한 단순화인지를 설정값 수준에서 논증하는 접근은 다른 CAP 개론 글에서 보기 어렵다.

## 본문

### 1. CAP 정리의 정확한 정의 — 흔한 오해부터 바로잡기

CAP이라는 이름은 Eric Brewer가 2000년 7월 19일 ACM PODC(Principles of Distributed Computing) 심포지엄 기조연설 "Towards Robust Distributed Systems"에서 처음 제시했습니다. 당시 Brewer는 이를 엄밀한 수학적 정리로 증명하지 않고, Inktomi에서의 실무 경험을 바탕으로 "공유 데이터 시스템은 아래 세 속성 중 최대 두 개만 동시에 만족할 수 있다"는 실무적 관찰로 제시했습니다.

- **Consistency(일관성)**: 모든 노드가 같은 순간에 같은 데이터를 본다.
- **Availability(가용성)**: 장애가 없는 노드는 항상 요청에 대해 (에러가 아닌) 응답을 반환한다.
- **Partition Tolerance(파티션 허용성)**: 네트워크가 노드 그룹 사이의 메시지를 임의로 유실해도 시스템이 계속 동작한다.

이 관찰을 수학적으로 형식화하고 실제로 증명한 것은 2002년 Seth Gilbert와 Nancy Lynch가 ACM SIGACT News(Vol. 33, pp. 51-59)에 발표한 논문 "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services"입니다. 이 논문은 비동기 네트워크 모델에서 세 속성을 동시에 만족하는 것이 불가능함을 증명했습니다.

**가장 흔한 오해**: "CAP 중 두 개를 고른다"는 문구를 "언제나 셋 중 두 개를 자유롭게 선택할 수 있다"는 뜻으로 오해하기 쉽습니다. 하지만 실제로는 **파티션이 발생했을 때만** 강제로 선택해야 하는 상황이 옵니다. 파티션이 없는 평상시(Normal Operation)에는 이론적으로 C와 A를 모두 만족시키는 게 가능합니다. 문제는 분산 시스템에서 네트워크 파티션은 "일어날 수도 있는 예외 상황"이 아니라 **반드시 대비해야 하는 전제조건**이라는 점입니다. 그래서 실무에서는 사실상 "파티션이 발생했을 때 C를 포기할 것인가(AP), A를 포기할 것인가(CP)"의 선택지로 좁혀집니다.

### 2. PACELC 정리 — CAP이 말하지 않는 "평상시"의 트레이드오프

CAP 정리의 한계는 "파티션이 없을 때는 어떻게 되는가"를 설명하지 않는다는 점입니다. Daniel Abadi는 2012년 IEEE Computer(45권 2호)에 발표한 논문 "Consistency Tradeoffs in Modern Distributed Database System Design: CAP is Only Part of the Story"에서 이 공백을 지적하고 **PACELC 정리**를 제안했습니다.

PACELC는 다음과 같이 읽습니다: **"파티션(P)이 발생하면 가용성(A)과 일관성(C) 중 하나를 선택해야 하고, 그렇지 않으면(Else, E) 지연시간(L)과 일관성(C) 중 하나를 선택해야 한다"**. 즉 CAP의 "P → A or C" 트레이드오프에 "평상시 → L or C"라는 두 번째 축을 추가한 것입니다.

이 관점이 중요한 이유는, 복제(Replication)를 쓰는 모든 분산 데이터베이스가 평상시에도 이 트레이드오프에서 자유롭지 않기 때문입니다. 쓰기 요청이 들어왔을 때 모든 복제본에 동기적으로 반영하고 나서 응답할지(강한 일관성, 높은 지연시간), 리더 노드에만 반영하고 바로 응답할지(낮은 지연시간, 약한 일관성)를 시스템은 파티션 여부와 무관하게 매번 결정해야 합니다. Abadi는 이 프레임워크로 여러 시스템을 분류했는데, 예를 들어 전통적 RDBMS 복제본 구성은 대체로 PC/EC(파티션 시 일관성 우선, 평상시도 일관성 우선)에, Dynamo 계열 NoSQL은 PA/EL(파티션 시 가용성 우선, 평상시 지연시간 우선)에 가깝게 분류됩니다.

### 3. Kafka의 ISR — CAP/PACELC 스펙트럼 위의 실제 좌표

Apache Kafka의 복제 메커니즘을 PACELC 프레임워크로 읽어보면, Kafka는 **설정 가능한(Configurable) 지점**에 있다는 게 명확해집니다. Kafka는 하나의 값으로 고정되어 있지 않고, 운영자가 명시적으로 트레이드오프를 조정합니다.

Confluent 공식 문서는 Kafka의 복제 구조를 다음과 같이 설명합니다. 각 파티션은 하나의 리더(Leader)와 여러 팔로워(Follower)를 가지며, Kafka는 리더를 따라잡은(caught-up) 팔로워 집합인 **ISR(In-Sync Replicas)**을 동적으로 유지합니다. 팔로워가 `replica.lag.time.max.ms`(기본 10초) 안에 리더의 로그를 따라잡지 못하면 ISR에서 제외됩니다. 리더 장애 시 새 리더는 반드시 ISR 멤버 중에서만 선출됩니다.

프로듀서의 `acks` 설정과 토픽의 `min.insync.replicas` 설정이 조합되면서 CAP/PACELC 좌표가 결정됩니다.

```properties
# 토픽 레벨 설정 예시 (server.properties 또는 kafka-topics.sh --config)
min.insync.replicas=2

# 프로듀서 레벨 설정 예시
acks=all
```

`acks=all`이고 `min.insync.replicas=2`, `replication.factor=3`이라면, 쓰기는 리더를 포함한 최소 2개 복제본이 응답할 때까지 기다립니다(지연시간 증가, 일관성/내구성 강화). 이 조합에서는 브로커 1대까지의 장애를 데이터 손실 없이 견딜 수 있습니다. 반대로 `acks=1`을 쓰면 리더가 로컬에 쓰는 즉시 응답하므로 지연시간은 줄지만, 리더가 팔로워에 복제하기 전에 죽으면 데이터가 유실될 수 있습니다. 즉 Kafka는 PACELC의 "Else(평상시) → Latency vs Consistency" 축을 `acks`/`min.insync.replicas` 설정값으로 운영자에게 그대로 넘겨준 시스템입니다. 파티션 상황(브로커 다수 장애로 ISR이 `min.insync.replicas` 미만으로 줄어드는 경우)에서는, `acks=all` 프로듀서의 쓰기 자체가 `NotEnoughReplicasException`으로 거부됩니다 — 이는 가용성보다 일관성을 우선하는 CP 성향의 선택입니다.

### 4. Cassandra의 튜너블 컨시스턴시 — 요청 단위로 좌표를 옮기다

Cassandra는 한 걸음 더 나아가, 시스템 전체가 아니라 **개별 읽기/쓰기 요청 단위**로 CAP/PACELC 좌표를 옮길 수 있게 설계되었습니다. Cassandra 공식 문서(Dynamo 아키텍처 문서)는 이를 "Consistency Level을 통한 일관성-가용성 간의 연산 단위 트레이드오프"로 설명합니다.

대표적인 Consistency Level은 다음과 같습니다.

```cql
-- 클라이언트 세션 단위로 컨시스턴시 레벨을 지정하는 CQL 예시
CONSISTENCY QUORUM;
SELECT * FROM users WHERE user_id = 123;

CONSISTENCY ONE;
INSERT INTO events (event_id, payload) VALUES (uuid(), 'click');
```

- **ONE**: 복제본 중 1개만 응답하면 성공 처리. 지연시간이 가장 낮지만 일관성이 가장 약함.
- **QUORUM**: 과반수(⌊n/2⌋ + 1, n은 복제 계수) 복제본이 응답해야 성공. 예를 들어 복제 계수(Replication Factor) 3에서 QUORUM은 2입니다.
- **ALL**: 모든 복제본이 응답해야 성공. 가장 강한 일관성이지만 복제본 하나만 장애가 나도 요청이 실패해 가용성이 가장 낮음.

여기서 중요한 실무 공식이 **W + R > RF**입니다. 쓰기 시 필요한 복제본 수(Write Consistency, W)와 읽기 시 필요한 복제본 수(Read Consistency, R)의 합이 복제 계수(RF)보다 크면, 읽기 집합과 쓰기 집합이 반드시 최소 1개 이상 겹치도록 보장되어 강한 일관성(Strong Consistency)을 얻습니다. 예를 들어 RF=3에서 쓰기와 읽기 모두 QUORUM(=2)을 쓰면 2+2=4 > 3이므로, 가장 최근에 쓴 값을 항상 읽는다는 보장이 성립합니다. 반대로 쓰기는 ONE, 읽기도 ONE으로 설정하면(1+1=2 ≤ 3) 지연시간은 최소화되지만 최신 값을 못 읽을 가능성(최종적 일관성, Eventual Consistency)을 감수해야 합니다.

이 설계가 PACELC 프레임워크에서 흥미로운 지점은, Cassandra 하나의 시스템 안에서도 **테이블마다, 심지어 쿼리마다** PA/EL(가용성·지연시간 우선)과 PC/EC(일관성 우선) 사이를 자유롭게 오갈 수 있다는 것입니다. 결제처럼 정합성이 중요한 쓰기는 QUORUM으로, 로그성 이벤트 적재처럼 속도가 중요한 쓰기는 ONE으로 — 같은 클러스터 안에서 서로 다른 좌표를 동시에 운용할 수 있습니다.

### 5. 두 시스템을 나란히 놓고 보기

| 항목 | Kafka | Cassandra |
|---|---|---|
| 트레이드오프 조정 단위 | 토픽/프로듀서 설정 (`acks`, `min.insync.replicas`) | 요청(쿼리) 단위 (Consistency Level) |
| 파티션 시 기본 성향 | `acks=all`이면 CP(가용성보다 일관성) | 설정한 Consistency Level에 따라 W/R 재계산, ALL이면 CP에 근접 |
| 평상시(Else) 성향 | `acks`로 L vs C 직접 제어 | Consistency Level로 L vs C를 요청마다 제어 |
| 강한 일관성 확보 조건 | `acks=all` + `min.insync.replicas`가 과반수 이상 | W + R > RF |

두 시스템 모두 "고정된 CAP 좌표에 박혀 있는 시스템"이 아니라, **설정을 통해 CAP/PACELC 스펙트럼 위를 이동할 수 있는 시스템**이라는 공통점이 있습니다. 이는 CAP 정리를 "이 DB는 CP다, 저 DB는 AP다"라는 이분법적 라벨로 외우는 것이 왜 실무에서 위험한 단순화인지를 잘 보여줍니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CAP 정리는 Eric Brewer가 2000년 7월 19일 ACM PODC 기조연설 "Towards Robust Distributed Systems"에서 최초 제시했으며, 당시엔 수학적으로 증명되지 않은 실무적 관찰이었다 | verified | WebSearch로 PODC 기조연설 서지정보(날짜·제목·venue) 교차 확인, PDF 원문(people.eecs.berkeley.edu) 다운로드로 실재 확인 |
| CAP 정리는 2002년 Seth Gilbert와 Nancy Lynch가 ACM SIGACT News(Vol.33, pp.51-59)에서 비동기 네트워크 모델 하에 수학적으로 증명했다 | verified | WebSearch로 논문 서지정보(권/호/페이지, ACM DOI 10.1145/564585.564601) 확인, PDF 원문(cs.cornell.edu) 다운로드로 실재 확인 |
| Daniel Abadi는 2012년 IEEE Computer(45권 2호)에서 PACELC 정리를 제안했으며, 핵심은 "파티션 시 A vs C, 평상시(Else)엔 L vs C"이다 | verified | WebSearch로 논문 서지정보 확인, PDF 원문(cs.umd.edu) 다운로드로 실재 확인 |
| Kafka는 ISR(팔로워가 리더를 따라잡은 복제본 집합)을 동적으로 유지하며, `replica.lag.time.max.ms` 초과 시 ISR에서 제외되고 새 리더는 ISR 멤버 중에서만 선출된다 | verified | Confluent 공식 문서(docs.confluent.io/kafka/design/replication.html) 원문 대조 |
| `acks=all` + `min.insync.replicas=2`(RF=3) 조합은 브로커 1대 장애까지 데이터 손실 없이 견디며, ISR이 `min.insync.replicas` 미만이면 쓰기가 거부된다 | verified | Confluent/커뮤니티 공식·준공식 자료(min.insync.replicas 동작 방식) 교차 확인 |
| Cassandra는 요청 단위로 Consistency Level(ONE/QUORUM/ALL 등)을 지정할 수 있으며, QUORUM은 ⌊n/2⌋+1이다 | verified | Apache Cassandra 공식 문서(cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html) 원문 대조 |
| Cassandra에서 W + R > RF이면 읽기·쓰기 복제본 집합이 항상 겹쳐 강한 일관성이 보장된다 | verified | Apache Cassandra 공식 문서 및 DataStax 문서의 Consistency Level 설명 교차 확인 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 CAP 정리가 가장 잘못 쓰이는 방식은 "이 DB는 CP고 저 DB는 AP다"라는 식으로 제품을 통째로 라벨링하는 것이라고 생각합니다. Kafka와 Cassandra 둘 다 살펴보면 알 수 있듯, 실제 시스템은 설정 값 하나로 CAP 스펙트럼 위의 다른 지점으로 이동합니다. `acks=1`로 설정한 Kafka와 `acks=all`로 설정한 Kafka는 같은 소프트웨어이지만 전혀 다른 CAP 성향을 갖습니다. 그래서 아키텍처 설계 문서에 "우리는 AP 시스템을 쓴다"라고만 적어놓는 것은 사실상 아무 정보도 주지 않는 문장입니다. 대신 "이 토픽은 `acks=all`, `min.insync.replicas=2`로 설정해서 지연시간을 희생하고 데이터 손실을 방지한다"처럼 구체적인 설정값과 그 근거를 문서화하는 것이 실무에서 훨씬 유용합니다. 또한 PACELC의 "Else" 축(평상시 L vs C)은 CAP만 알고 있으면 완전히 놓치는 부분인데, 실제로 시스템이 파티션 상태에 있는 시간보다 정상 상태에 있는 시간이 압도적으로 길기 때문에, 오히려 이 평상시 트레이드오프가 사용자 체감 성능에 더 큰 영향을 준다고 봅니다. 그래서 저는 신규 시스템을 설계할 때 "파티션이 나면 어떻게 할까"보다 "평상시 지연시간을 얼마나 희생하고 얼마나 강한 일관성을 살 것인가"를 먼저 구체적인 SLA 숫자로 정하고, 그다음에 그 숫자를 만족하는 Consistency Level/`acks` 조합을 역산하는 순서로 접근하는 것을 권장합니다.

## 한계와 반론

**한계점**: 이 글에서 다룬 CAP/PACELC 분류는 이론적 프레임워크이며, 실제 프로덕션 환경에서는 네트워크 파티션이 "전부 단절" 또는 "전혀 없음"의 이분법이 아니라 부분적 지연·간헐적 패킷 유실 같은 회색 지대(Gray Failure)로 나타나는 경우가 훨씬 많습니다. Kafka의 `replica.lag.time.max.ms`나 Cassandra의 타임아웃 설정은 이런 회색 지대를 "파티션 발생" 또는 "정상"의 이분법으로 강제 변환하는 근사치일 뿐이며, 그 임계값을 어떻게 잡느냐에 따라 실제 동작이 CAP 이론이 가정하는 깔끔한 모델과 어긋날 수 있습니다.

**반론**: "CAP 정리는 오래되고 단순화된 모델이라 이제는 실무에 참고할 가치가 낮다"는 의견도 있습니다. 실제로 Brewer 본인도 이후 발표한 글("CAP Twelve Years Later")에서 C·A·P를 이진(binary) 속성이 아니라 정도의 문제로 봐야 한다고 스스로 정정한 바 있습니다. 하지만 이 글의 관점은 CAP/PACELC를 "정답을 알려주는 공식"이 아니라 "설계 결정을 언어화하는 어휘"로 보는 것입니다. Kafka의 `acks` 설정이나 Cassandra의 Consistency Level을 고를 때 "이건 CP 쪽으로 붙이는 결정"이라고 명확히 인식하고 그 트레이드오프를 팀 안에서 합의하는 것 자체가, 정확한 수학적 예측보다 실무적으로 더 중요한 가치라고 생각합니다.

## 참고문헌

1. Eric A. Brewer, "Towards Robust Distributed Systems" (PODC 2000 Keynote, 2000-07-19), [https://people.eecs.berkeley.edu/~brewer/cs262b-2004/PODC-keynote.pdf](https://people.eecs.berkeley.edu/~brewer/cs262b-2004/PODC-keynote.pdf) (확인일: 2026-08-19)
2. Seth Gilbert, Nancy Lynch, "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services", ACM SIGACT News, Vol. 33, No. 2 (2002), pp. 51-59, [https://www.cs.cornell.edu/courses/cs6464/2009sp/papers/brewer.pdf](https://www.cs.cornell.edu/courses/cs6464/2009sp/papers/brewer.pdf) (확인일: 2026-08-19)
3. Daniel J. Abadi, "Consistency Tradeoffs in Modern Distributed Database System Design: CAP is Only Part of the Story", IEEE Computer, 45(2), 2012, [http://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf](http://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf) (확인일: 2026-08-19)
4. Confluent, "Kafka Replication and Committed Messages", [https://docs.confluent.io/kafka/design/replication.html](https://docs.confluent.io/kafka/design/replication.html) (확인일: 2026-08-19)
5. Apache Cassandra, "Dynamo — Tunable Consistency", [https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

CAP 정리와 PACELC 정리를 함께 이해하면, 분산 데이터 시스템의 설계 문제를 "어떤 제품을 쓸 것인가"가 아니라 "어떤 설정으로 어떤 트레이드오프를 살 것인가"의 문제로 재구성할 수 있습니다. Kafka와 Cassandra의 사례는 이 재구성이 이론적 논의로 그치지 않고, `acks`·`min.insync.replicas`·Consistency Level 같은 실제 설정값으로 직접 이어진다는 것을 보여줍니다. 두 시스템 모두 하나의 CAP 좌표에 고정된 것이 아니라, 운영자가 요청 단위 또는 토픽 단위로 그 좌표를 능동적으로 선택하도록 설계되어 있습니다. 이 관점에서 보면 "이 시스템은 CP다/AP다"라는 질문보다 "이 특정 쓰기/읽기 경로는 지금 어떤 트레이드오프를 선택하고 있고, 그것이 비즈니스 요구사항과 일치하는가"라는 질문이 훨씬 생산적입니다. 분산 시스템을 설계하거나 운영하는 개발자라면, CAP을 암기용 삼각형 다이어그램이 아니라 이런 구체적인 설정값을 판단하는 도구로 다시 이해하는 것이 실무적으로 훨씬 유용합니다.

## 꼬리질문

1. **Kafka의 `min.insync.replicas`를 설정값보다 크게 유지하지 못하는 상황(브로커 다수 장애)에서, 운영자는 가용성을 되찾기 위해 어떤 복구 절차를 밟아야 하며 그 과정에서 데이터 손실 위험은 어떻게 관리하는가?**
   - 추천 참고 URL: https://docs.confluent.io/kafka/design/replication.html
2. **Cassandra의 LOCAL_QUORUM과 EACH_QUORUM은 멀티 데이터센터 환경에서 각각 어떤 시나리오에 적합하며, 데이터센터 간 네트워크 파티션이 발생했을 때 두 레벨의 동작은 구체적으로 어떻게 갈리는가?**
   - 추천 참고 URL: https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html
3. **Brewer가 스스로 "CAP Twelve Years Later"에서 C·A·P를 이진 속성이 아닌 정도(spectrum)의 문제로 재정의했다는데, 이 관점을 Kafka/Cassandra의 설정 파라미터에 정량적으로 매핑하는 방법이 있는가?**

## 백링크

- [Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략](https://beji-tech.blogspot.com/2026/08/kafka.html)
- [4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드](https://beji-tech.blogspot.com/2026/08/4-activemq-kafka-rabbitmq-redis.html)
- [이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략](https://beji-tech.blogspot.com/2026/08/msa-non-blocking-retry-dlq.html)