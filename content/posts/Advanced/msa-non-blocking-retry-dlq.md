---
id: '7724585666360944080'
publishedAt: '2026-08-12T22:41:11.006-07:00'
slug: msa-non-blocking-retry-dlq
status: published
tags:
- DLQ
- Event-Driven
- Kafka
- Microservices
- Resilience
- Retry Pattern
- Software Architecture
- Advanced
title: 이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략
updatedAt: '2026-08-13T20:55:08.522-07:00'
url: https://beji-tech.blogspot.com/2026/08/msa-non-blocking-retry-dlq.html
---

# 이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략

## 요약

이벤트 기반 마이크로서비스 아키텍처(Event-Driven MSA)에서 메시지 소비(Consume) 도중 발생하는 비즈니스 논리 오류나 인프라 장애에 대한 대처는 시스템의 복구 탄력성(Resilience)을 결정짓는 핵심 요소입니다. 메시지 처리 실패 시 단순 루프 재시도 기법은 특정 컨슈머 스레드를 점유하여 전체 메시지 파이프라인의 처리 병목을 유발하는 치명적인 차단(Blocking) 문제를 야기합니다. 본 아티클에서는 이러한 한계를 극복하기 위해 아파치 카프카(Apache Kafka) 환경에서 활용되는 비차단 재시도(Non-blocking Retry) 설계 기법과 다단계 재시도 토픽(Multi-tiered Retry Topics) 구조, 그리고 최종 실패 메시지를 격리하는 데드 레터 큐(DLQ, Dead Letter Queue) 패턴의 모범 사례를 심층 검토합니다.

## 본문

### 1. 서론: 이벤트 기반 분산 시스템에서 메시지 처리 실패의 복잡성

분산 환경의 마이크로서비스들은 네트워크 단절, 데이터베이스 일시 잠금, 혹은 외부 API의 레이턴시 지연 등 예측 불가능한 장애 상황에 빈번히 직면합니다 [1], [5]. 이때 일시적 예외(Transient Exception)와 영구적 오류(Fatal Exception)를 구별하지 않고 즉각 처리를 거부하거나 무조건 재시도를 무한 반복하는 방식은 메시지 유실 또는 시스템 전체의 동반 장애를 초래합니다 [1], [4].

- 메시지 브로커 환경에서 예외 처리 체계가 부재할 경우, 소비 실패 시 오프셋(Offset) 커밋 거부로 인한 동일 메시지의 무한 루프 수신 현상이 발생하거나 메시지가 즉각 증발하는 불안정성을 띤다 [1], [4].

- 전통적인 동기식 재시도(In-place Retry)는 컨슈머의 폴링 루프(Polling Loop)를 장시간 차단하여 카프카의 하트비트 세션 유실에 따른 컨슈머 그룹 리밸런싱을 유발하므로 상용 인프라에서 회피해야 한다 [3], [5].

### 2. 비차단 재시도(Non-blocking Retry) 아키텍처 설계와 다단계 재시도 토픽 구조

컨슈머의 블로킹 현상을 완벽하게 피하면서 복구력을 확보하기 위해, 일시적 장애를 겪은 메시지를 메인 스트림에서 격리하여 전용 재시도 토픽으로 전환하는 아키텍처를 도입해야 합니다 [2], [3], [6].

![비차단 재시도 및 DLQ 흐름도](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/retry_dlq_diagram_1786601094572.jpg)

- 
**다단계 백오프 토픽(Multi-tiered Backoff Topics)**: 처리 실패 횟수에 비례하여 점진적으로 대기 시간을 늘리는 지수적 백오프(Exponential Backoff)를 구현하기 위해 여러 단계의 재시도 전용 토픽을 생성합니다. (예: `main-topic` ➔ 실패 ➔ `retry-topic-5s` ➔ 실패 ➔ `retry-topic-30s` ➔ 실패 ➔ `retry-topic-5m`) [2], [3].

- 
**소비 지연 제어 (Consumer Sleep)**: 재시도 토픽을 바라보는 전용 컨슈머들은 메시지 헤더에 기록된 최초 실패 시각 및 백오프 타겟 시각을 평가하여, 대기 잔여 시간 동안 스레드를 수면(Sleep) 상태로 제어함으로써 조기 재시도로 인한 리소스 낭비를 방지합니다 [3], [6].

- 
다단계 백오프 토픽 구성은 에러 발생 메시지만을 메인 토픽 뒤쪽 파이프라인으로 전송하므로, 정상 메시지들이 병목 없이 초고속 저지연 처리를 유지할 수 있게 보장한다 [2], [3].

- 
재시도 메시지 헤더에 타임스탬프와 누적 시도 횟수(Retry Count) 정보를 기록하여 전파하는 메커니즘을 적용하면 노드 간 무상태(Stateless) 이벤트 추적이 용이해진다 [3], [6].

### 3. 데드 레터 큐(DLQ)의 역할과 알림 및 운영 모범 사례

사전에 정의된 최대 재시도 임계값(예: 3회 또는 5회)을 초과하도록 예외 상황이 지속되면, 해당 이벤트를 독성 메시지(Poison Pill)로 판단하고 데드 레터 큐(DLQ) 토픽으로 최종 영구 이적시킵니다 [1], [2], [5].

- 
**독성 메시지 격리**: DLQ로 격리된 메시지는 정상적인 트래픽 소비 파이프라인을 전혀 방해하지 않아 시스템 가동 상태를 무중단으로 유지합니다 [1], [5].

- 
**모니터링 및 복구 자동화**: DLQ에 신규 메시지가 누적될 때 실시간 슬랙 알림이나 모니터링 경보(Prometheus Alertmanager 등)를 발생시키고, 장애 유발 버그가 핫픽스되어 백엔드가 정상화되면 관리자 UI를 통해 DLQ 이벤트를 메인 토픽이나 복구 토픽으로 안전하게 재주입(Redelivery/Replay)하는 도구를 구축합니다 [2], [5], [6].

- 
DLQ는 데이터의 영구적 소실을 차단하는 최후의 안전망 역할을 하며, 장애 원인 파악을 위한 실시간 사후 분석 데이터 소스를 제공한다 [1], [2].

- 
비즈니스 로직 상의 포맷 오류나 스키마 불합격 등 영구적 예외(Fatal Exception)를 감지했을 때는 다단계 재시도를 건너뛰고 즉각 DLQ로 바로 전송(Direct routing)하는 분기 필터링 정책이 비용 제어에 효과적이다 [5], [6].

### 4. 아키텍처적 트레이드오프 및 설계 선택 가이드

재시도 토픽 아키텍처는 놀라운 안정성을 제공하지만 인프라 복잡도의 트레이드오프가 수반됩니다 [2], [3], [5].

  비교 항목
  인플레이스 동기 재시도 (In-place Blocking)
  비차단 다단계 재시도 (Non-blocking Retry)

  파이프라인 병목
  매우 높음 (에러 1건 발생 시 해당 파티션 전체 대기)
  없음 (정상 메시지는 병렬 통과)

  인프라 관리 리소스
  극도로 낮음 (단일 토픽, 단일 컨슈머)
  높음 (다수의 N단계 재시도 토픽 및 컨슈머 관리 오버헤드)

  메시지 순서 보장
  보장됨 (에러를 먼저 해결한 후 순차 소비)
  **깨짐** (에러 발생 메시지가 뒤로 밀림)

  상용 환경 적합도
  배치 처리 등 단발성 워크플로우에 적합
  실시간 대규모 온라인 트랜잭션 처리에 적합

- 다단계 비차단 재시도 구조를 도입하면 뒤이어 도착한 정상 메시지가 먼저 소비되므로, 순서가 극도로 엄격해야 하는 주문 결제 시퀀스 같은 도메인에서는 별도의 순서 제어 캐시나 락킹이 요구될 수 있다 [2], [5].

- 스프링 카프카(Spring Kafka) 프레임워크의 `@RetryableTopic` 등 오픈소스 기술의 기본 추상화를 활용하면 다단계 토픽 생성 및 헤더 백오프 연산 코딩 오버헤드를 극적으로 축소시킬 수 있다 [3], [4].

### 5. 결론: 무중단 고가용성 MSA 구축을 위한 장애 대응 설계 제언

이벤트 기반 마이크로서비스 아키텍처에서 시스템 복구 탄력성은 장애를 아예 예방하는 것이 아니라 "장애가 발생했을 때 어떻게 무중단으로 우아하게 격리하고 신속히 자가 복구할 것인가"의 설계에 달려 있습니다 [1], [5], [6].

따라서 실무 인프라를 구성할 때는, 메시지의 전후 인과관계가 아주 엄격하게 일치해야 하는 순차 영역은 인라인 파티션 락을 통해 엄격하게 차단 처리하고, 사용자 프로필 갱신, 알림 발송, 검색 인덱스 적재처럼 순서보다 실시간 대용량 트래픽 처리량 및 가동성이 훨씬 중요한 일반 비즈니스 도메인에서는 3단계의 점진적 지수 백오프 비차단 재시도 토픽과 DLQ 자동 경보 시스템을 전면 구축하는 것이 대규모 엔터프라이즈 시스템 구축의 최선책입니다 [2], [6].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 이벤트 기반 마이크로서비스에서 DLQ의 존재 목적이 단순히 실패한 메시지를 쌓아두는 '쓰레기통'이 아닌, 서비스 오케스트레이션과 무중단 복구 도구로 확장되어야 한다고 판단합니다. 대다수 팀들이 복구 전략을 세울 때 수동 CLI 쉘 스크립트를 통해 DLQ 이벤트를 복원하느라 장애 대응 시간을 허비하곤 합니다. 따라서 프로덕션 구축 초기 단계부터 DLQ 토픽의 입구를 모니터링하여 실패 메시지를 일시 보관하고, 관리자가 문제 있는 백엔드 서비스를 재배포 완료한 즉시 버튼 하나로 해당 시점의 DLQ 파티션 오프셋을 역추적해 자동 재생(Replay Engine)시키는 전용 어드민 툴을 반드시 결합해 둘 것을 권장합니다.

## 한계와 반론

- **한계점**: 본 아티클에서 소개한 다단계 지수 백오프 토픽 패턴은 실패하는 메시지의 분산 흐름을 완벽히 흡수하지만, 인프라의 복잡도가 비대해집니다. 실패율이 급증하는 네트워크 장애 상황에서는 N개의 지연 토픽으로 수억 건의 이벤트가 전치되면서 디스크 I/O 임계 성능 부하 및 네트워크 트래픽 비용이 단기간에 폭증하는 'Write Amplification' 임계 상황을 초래할 수 있습니다.

- **반론**: 카프카 내에 굳이 여러 개의 꼬리 토픽을 직접 개설하는 것보다 RabbitMQ처럼 단일 큐 내부에서 헤더 기반의 TTL(Time-To-Live)을 이용해 한 브로커 내에서 자체 지연 후 재진입시키는 구조가 훨씬 간결하다는 지적이 있습니다. 그러나 대용량 분산 환경인 Kafka에서는 개별 파티션의 순차 큐 구조 특성상 중간 오프셋 메시지만을 콕 집어 TTL을 주는 행위가 디스크 순차 읽기 성능 구조 위반을 뜻하므로, 대량 트래픽 하에서는 토픽 다단계 격리 구조가 훨씬 높은 아키텍처적 완성도를 입증합니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

장애 대응을 설계할 때 가장 경계해야 할 부분은 복잡성에 매몰되는 것입니다. 무작정 5단계 이상의 촘촘한 백오프 재시도 토픽을 구축하는 것은 인프라 자원의 낭비이자 장애 추적 난이도만 증대시킬 뿐입니다. 대다수 실무 장애의 성격은 30초 내외의 네트워크 단절이나 일시적 데이터베이스 락 경합 등 짧은 주기 장애입니다. 따라서 1단계(15초 대기)와 2단계(3분 대기) 수준의 간결한 2-tier 백오프 구조만 설계하고, 해결되지 않는 이슈는 즉시 DLQ로 넘기는 타임아웃 밸런스를 잡는 것이 아키텍처 가독성과 운영 단순성 면에서 가장 모범적인 설계라고 생각합니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- AWS Prescriptive Guidance, "Designing resilient event-driven architectures with dead-letter queues", [https://docs.aws.amazon.com/prescriptive-guidance/latest/resilient-event-driven-architectures/dead-letter-queues.html](https://docs.aws.amazon.com/prescriptive-guidance/latest/resilient-event-driven-architectures/dead-letter-queues.html)

- Uber Engineering Blog, "Reliable Reprocessing in Apache Kafka: Multi-tier Dead Letter Queuing", [https://www.uber.com/blog/reliable-reprocessing-in-apache-kafka/](https://www.uber.com/blog/reliable-reprocessing-in-apache-kafka/)

- Spring Framework Reference, "Non-Blocking Retries and Dead Letter Queue Support in Spring for Apache Kafka", [https://docs.spring.io/spring-kafka/reference/html/#retry-topic](https://docs.spring.io/spring-kafka/reference/html/#retry-topic)

- Microsoft Azure Architecture Center, "Retry pattern for microservices and cloud applications", [https://learn.microsoft.com/en-us/azure/architecture/patterns/retry](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)

- Confluent Developer Guide, "Error Handling Patterns in Apache Kafka: Retry and Dead Letter Queue", [https://developer.confluent.io/patterns/event-flow/error-handling/](https://developer.confluent.io/patterns/event-flow/error-handling/)

- Google Cloud Architecture, "Designing reliable event-driven systems using Google Cloud Pub/Sub DLQ", [https://cloud.google.com/pubsub/docs/dead-letter-topics](https://cloud.google.com/pubsub/docs/dead-letter-topics)

## 백링크

- [Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)
- [Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략](https://beji-tech.blogspot.com/2026/08/kafka.html)
- [4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드](https://beji-tech.blogspot.com/2026/08/4-activemq-kafka-rabbitmq-redis.html)