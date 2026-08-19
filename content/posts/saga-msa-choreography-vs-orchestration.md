---
id: '3954787395289334886'
publishedAt: '2026-08-14T10:20:51.161-07:00'
slug: saga-msa-choreography-vs-orchestration
status: published
tags:
- Choreography
- Distributed Transactions
- Microservices
- Orchestration
- Saga Pattern
- System Architecture
title: 'Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계
  전략'
updatedAt: '2026-08-14T10:20:51.161-07:00'
url: https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html
---

# Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략

## Saga 패턴을 활용한 MSA 분산 트랜잭션 제어

## 요약

단일 모놀리식 아키텍처에서 마이크로서비스 아키텍처(MSA)로 전환될 때 발생하는 가장 강력한 장애물은 **'분산 트랜잭션(Distributed Transaction)의 정합성 유지'**입니다. 데이터베이스가 물리적으로 격리(Database-per-Service)된 분산 네트워크 구조 하에서는 과거의 2단계 커밋(2PC) 프로토콜이 성능 병목과 복잡한 락킹으로 인해 기피됩니다. 본 아티클에서는 이를 해결하는 사실상의 표준(de facto standard) 아키텍처 패턴인 **'Saga 패턴'**을 상세 비교 분석합니다. 이벤트 기반의 안무가(Choreography) 방식과 중앙 제어형 지휘자(Orchestration) 방식의 특징과 장단점을 비교하고, 비즈니스 에러 발생 시 데이터 정합성을 복구해 내는 보상 트랜잭션(Compensating Transaction) 및 멱등성 보장 설계를 위한 아키텍처 수립 전략을 제시합니다.

목차

- [1. 서론: 분산 데이터베이스 환경의 트랜잭션 딜레마와 2PC의 한계](#1-서론-분산-데이터베이스-환경의-트랜잭션-딜레마와-2pc의-한계)

- [2. Saga 패턴의 구조와 2대 설계 토폴로지 비교](#2-saga-패턴의-구조와-2대-설계-토폴로지-비교)

- [3. 보상 트랜잭션(Compensating Transaction) 설계와 멱등성 보장 기법](#3-보상-트랜잭션compensating-transaction-설계와-멱등성-보장-기법)

## 본문

### 1. 서론: 분산 데이터베이스 환경의 트랜잭션 딜레마와 2PC의 한계

마이크로서비스 아키텍처(MSA)는 서비스 간의 독립된 생명주기와 느슨한 결합을 보장하기 위해 서비스마다 고유의 데이터베이스를 소유하는 Database-per-Service 패턴을 권장합니다 [1], [5]. 그러나 이 구조에서는 여러 마이크로서비스에 걸쳐 실행되는 비즈니스 작업(예: 주문 등록 -> 결제 승인 -> 재고 차감 -> 배송 지시)이 단일 데이터베이스 트랜잭션(`ACID`)의 롤백 범위를 벗어나 네트워크 유실과 부분 장애 리스크에 무방비하게 노출되는 문제점이 발생합니다 [1], [2], [6].

- 분산 환경에서 물리적으로 분리된 여러 로컬 DB 트랜잭션들을 하나로 묶어 완벽한 일관성(Consistency)을 유지하는 것은 불가능에 가까우며, 성능 병목을 최소화하는 타협적 아키텍처가 필수적이다 [1], [2].

#### 2단계 커밋(2PC, Two-Phase Commit)의 치명적 한계:

2PC는 조정자(Coordinator) 노드가 다중 노드에 대해 준비(Prepare)와 커밋(Commit)의 2단계에 걸쳐 원자적 합의를 이루는 전통적 기법입니다.

- **성능 병목**: 모든 참여 노드가 커밋을 승인하고 네트워크 응답을 보낼 때까지 관련된 모든 데이터베이스 로우(Row)에 락(Lock)을 쥐고 대기해야 하므로, 처리 대역폭이 극단적으로 좁아집니다.

- **장애 취약성**: 조정자 노드가 Prepare 단계 직후 다운되면 모든 참여 노드는 영구히 블로킹되는 단일 장애점(SPOF) 리스크를 내포합니다.

- **현대적 기피**: 확장성을 중시하는 클라우드 환경에서는 성능 저하와 가용성 유실 문제로 인해 2PC 사용을 지양하고 느슨한 일관성(Eventual Consistency)을 획득하는 Saga 패턴을 선호합니다 [2], [6].

- 2PC 프로토콜은 분산 참여 노드의 통신이 모두 완료될 때까지 전역 락킹(Global Locking) 상태를 유발하여 가용성을 현저히 떨어뜨리기 때문에 대규모 분산 아키텍처에는 적합하지 않다 [2], [6].

### 2. Saga 패턴의 구조와 2대 설계 토폴로지 비교

Saga 패턴은 전역 트랜잭션을 하나의 거대한 결합적 락킹으로 묶지 않고, 각 서비스별로 실행되는 **독립적인 로컬 트랜잭션(T1, T2, T3...)들의 선형적인 체인 구조**로 쪼개어 해결합니다 [1], [3]. 앞선 로컬 트랜잭션이 성공하면 완료 이벤트를 발행하고, 다음 마이크로서비스가 이를 수신하여 자신의 로컬 트랜잭션을 수행해 나가는 비동기 흐름 제어 기법입니다 [3], [5].

![Saga 디자인 패턴 비교분석](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/saga_pattern_orchestration_1786727970805.jpg)

#### A. 안무가 방식: Choreography Saga (이벤트 기반 비중앙화)

중앙에서 상태를 총괄하는 컴포넌트 없이, 개별 마이크로서비스들이 카프카(Kafka)나 래빗MQ(RabbitMQ) 등 이벤트 버스를 통해 자율적으로 통신하는 방식입니다 [3], [5].

- **장점**: 구성이 극도로 단순하여 빠르게 설계할 수 있고, 서비스 간의 느슨한 결합이 극대화되며 단일 장애점(SPOF)이 없습니다.

- **단점**: 서비스가 늘어날수록 흐름이 꼬여 복잡도가 급상승하며(스파게티 코드 리스크), "주문이 완료되었을 때 결제와 재고가 최종적으로 어떤 상태인지" 전체 워크플로우를 모니터링하기가 대단히 어렵습니다.

- Choreography Saga 방식은 분산 서비스들의 자율적인 Pub/Sub 구조를 보장하므로 중앙 통제 장치의 단일 실패점 부담을 덜어주나, 트랜잭션 순환 구조(Cyclic Dependency) 등 디버깅 복잡도가 상승한다 [3], [5].

#### B. 지휘자 방식: Orchestration Saga (중앙 상태 기계 제어)

트랜잭션의 총괄 지휘를 주도하는 전용 중앙 서비스 객체인 **'Saga Orchestrator'**(State Machine)를 두어 관리하는 방식입니다 [3], [5].

- **장점**: 복잡한 비즈니스 로직과 복구 흐름을 지휘자 코드 한곳에 집중하므로 전체 트랜잭션 상태를 직관적으로 이해하고 디버깅하기가 쉽습니다.

- **단점**: 오케스트레이터 자체가 또 다른 마이크로서비스로서 관리 대상이 되며, 모든 비즈니스 트래픽이 집중되므로 고도의 이중화 설계가 동반되어야 합니다.

- Orchestration Saga는 분산 트랜잭션의 전역 상태 기계(State Machine)를 가시적으로 관리하므로 복잡한 보상 처리 경로와 상태 예외 핸들링을 명료하게 구현할 수 있는 실무적 지향점을 지닌다 [3], [5].

### 3. 보상 트랜잭션(Compensating Transaction) 설계와 멱등성 보장 기법

Saga 패턴은 롤백을 구현할 때 ACID 트랜잭션처럼 물리적 DB 롤백 명령(Undo)을 사용할 수 없습니다. 이미 완료된 로컬 트랜잭션은 커밋되어 하드디스크에 영구 기록되었기 때문입니다. 따라서, 비즈니스 중간 단계에서 실패(예: 결제는 성공했으나 재고 부족으로 강제 차단)가 발생하면, 앞서 실행된 성공 작업들의 데이터적 효과를 역방향으로 취소·상쇄시키는 **'보상 트랜잭션(C1, C2...)'**을 발행해야 합니다 [4], [5].

- **보상 트랜잭션 작성 시 필수 준수 사항**:
**보상 트랜잭션은 무조건 성공해야 한다**: 보상 트랜잭션이 네트워크 순간 유실로 실패하더라도 성공할 때까지 무한 재시도(Retry)하거나 데드 레터 큐(DLQ)에 실어 관리자 개입으로 최종 해결되어야 합니다.

- **멱등성(Idempotency)의 절대 보장**: 네트워크 지연으로 이벤트가 중복 발행(At-least-once 배달 방식)되더라도 데이터베이스 값이 중복 증감하지 않도록, `Transaction ID` 또는 고유 식별값(UUID)을 활용하여 "이미 완료된 보상 주문 취소 트랜잭션"인지를 검증하고 동일 요청을 거부하는 방어막 로직을 두어야 합니다.

- Saga 패턴의 보상 트랜잭션은 이미 커밋 완료된 이전 상태를 취소하는 데이터 보완(Compensation) 행위이므로, 비대칭 네트워크에서 유실되지 않고 무조건 1회 이상 성공할 때까지 재시도되는 멱등적 보장 장치가 수반되어야 한다 [4], [5].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 실무에서 Saga 패턴을 디자인할 때, 우선순위 1순위로 'Orchestration' 방식을 도입할 것을 강하게 권장합니다. 초기 학습 곡선은 안무가(Choreography) 방식이 완만해 보이지만, 실제 서비스 규모가 커져서 참여 마이크로서비스가 5개를 넘어가는 순간, 누가 어떤 이벤트를 구독하고 발행하는지 머릿속으로 조작할 수 없는 지경에 이릅니다. 이때 스프링 생태계에서 지원하는 Temporal.io나 AWS Step Functions, 혹은 자체 데이터베이스로 구동되는 가벼운 오케스트레이터 코드를 도입하면, 중앙 상태 머신 하나로 전체 흐름을 일목요연하게 파악할 수 있는 유지 보수성의 비약적인 상승을 체감할 수 있습니다.

## 한계와 반론

- **한계점**: Saga 패턴은 전역 락(Lock)을 쥐지 않고 로컬에서 개별 커밋하므로 **'격리성(Isolation)'**이 보장되지 않는 고유한 결함이 있습니다. 즉, 트랜잭션이 아직 최종 성공/실패로 확정되지 않은 과도기적인 찰나에 다른 사용자가 읽기(Read)를 수행하면, 오염되거나 취소될 예정인 데이터(Dirty Read)를 조회하게 되는 위험이 상존합니다.

- **반론**: 비격리성 문제에 대해 무조건 Saga를 기피할 필요는 없습니다. 비즈니스 설계를 통해 계좌 입출금 대기 상태를 임시 플래그 컬럼(`status: PENDING_PAYMENT`)으로 기록하고, 결제가 완전히 매듭지어지거나 취소(보상)되기 전까지 사용자 화면 노출에서 필터링하는 방식의 애플리케이션 레벨 격리 튜닝(Semantic Lock 패턴)을 적극 결합하면, Saga의 확장성도 살리고 정합성 리스크도 저비용으로 통제할 수 있습니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

분산 환경에서의 트랜잭션 처리는 결국 '성능'과 '정합성'이라는 두 마리 토끼 중 한쪽에 무게를 더 실어야 하는 비즈니스 가치 판단의 영역입니다. 2PC라는 엄격한 정합성을 선택하면 단 몇 백 명의 사용자 트래픽 속에서도 시스템 전체가 얼어붙게 됩니다. 반면 Saga라는 확장성을 선택하면 최종적 정합성(Eventual Consistency)에 도달하기 전까지의 미세한 상태 불안정을 감당하고 멱등성 및 보상 트랜잭션이라는 무거운 수동 방어벽 코드를 견고하게 짜내야 합니다. 결국 정답은 없습니다. 도메인의 데이터 성격에 맞추어 결제나 송금 같은 최고 보안 도메인에는 제한적으로 락과 버전을, 일반 정보 기록과 알림 배송 도메인에는 비동기 Saga 방식을 조합하는 유연함이 필요합니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- Chris Richardson, "Microservices Patterns: With examples in Java", Manning Publications, Chapter 3 & 4.

- Chris Richardson, Microservices.io Pattern Catalog, "Pattern: Event-driven architecture", [https://microservices.io/patterns/data/event-driven-architecture.html](https://microservices.io/patterns/data/event-driven-architecture.html)

- Microservices.io Pattern Catalog, "Saga Pattern (Choreography and Orchestration)", [https://microservices.io/patterns/data/saga.html](https://microservices.io/patterns/data/saga.html)

- Martin Kleppmann, "Designing Data-Intensive Applications", O'Reilly Media, Chapter 9.

- IBM Cloud Architecture, "Event-driven Solution - Saga Orchestration", [https://ibm-cloud-architecture.github.io/eda-saga-orchestration/](https://ibm-cloud-architecture.github.io/eda-saga-orchestration/)

- Chris Richardson, Microservices.io Pattern Catalog, "Pattern: Database per service", [https://microservices.io/patterns/data/database-per-service.html](https://microservices.io/patterns/data/database-per-service.html)