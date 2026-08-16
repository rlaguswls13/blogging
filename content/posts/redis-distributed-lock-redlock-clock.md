---
id: "5415411891794983817"
title: "Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마"
slug: "redis-distributed-lock-redlock-clock"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/redis-distributed-lock-redlock-clock.html"
publishedAt: "2026-08-14T10:20:47.695-07:00"
updatedAt: "2026-08-14T10:20:47.695-07:00"
tags: ["Concurrency Control","Distributed Lock","Redis","Redisson","Redlock","System Architecture"]
---

# Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마

## Redis 분산 락(Distributed Lock)의 한계와 극복

## 요약

동일한 공유 자원에 대해 여러 분산 노드가 동시에 접근하는 분산 아키텍처(MSA 등)에서, 데이터 레이스 컨디션(Race Condition)을 통제하기 위한 **'분산 락(Distributed Lock)'** 구현은 필수적입니다. 이 중 고속 메모리 아키텍처를 지닌 Redis는 분산 락 구현의 사실상 표준(de facto standard)으로 활발히 기용되고 있습니다. 본 아티클에서는 대표적 Redis 클라이언트 라이브러리인 Lettuce와 Redisson의 락 획득 메커니즘 차이를 심층 규명하고, 다중 노드 합의 프로토콜인 Redlock 알고리즘의 동작 방식과 시계 드리프트(Clock Drift) 등 분산 네트워크 환경 하의 내재된 한계를 도출합니다. 아울러 이를 극복하기 위한 펜싱 토큰(Fencing Token) 보완 패턴을 제시합니다.

목차

- [1. 서론: 분산 환경에서의 동시성 제어와 Redis의 기용 이유](#1-서론-분산-환경에서의-동시성-제어와-redis의-기용-이유)

- [2. Lettuce vs Redisson: 스핀 락(Spin Lock)과 Pub/Sub 스핀 방지 차이](#2-lettuce-vs-redisson-스핀-락spin-lock과-pubsub-스핀-방지-차이)

- [3. Redlock 알고리즘의 동작 방식과 시계 드리프트(Clock Drift) 한계](#3-redlock-알고리즘의-동작-방식과-시계-드리프트clock-drift-한계)

- [4. 분산 락의 한계 극복: 펜싱 토큰(Fencing Token) 패턴](#4-분산-락의-한계-극복-펜싱-토큰fencing-token-패턴)

## 본문

### 1. 서론: 분산 환경에서의 동시성 제어와 Redis의 기용 이유

단일 프로세스 내부의 동기화 키워드(예: Java의 `synchronized`)는 다중 서버 인프라 환경에서 작동하지 않습니다. 따라서 여러 WAS 노드가 공유하는 외부 스토리지 기반의 분산 락이 필요하게 됩니다 [1], [5]. 관계형 데이터베이스(RDBMS)의 비관적 락(Pessimistic Lock)은 긴 디스크 대기 트래픽으로 인해 동시성 대역폭이 극단적으로 좁아지는 병목을 겪는 반면, Redis는 극도로 빠른 인메모리 처리 속도와 명령의 단일 스레드 원자성(Atomicity)을 통해 초저지연 분산 락 인프라를 이상적으로 지원합니다 [1], [2], [6].

- 분산 환경에서 임계 영역(Critical Section)의 데이터 독점권을 제어하기 위해서는 다중 서버가 공용으로 바라보는 상태 브로커가 필수적이며, Redis는 싱글 스레드 이벤트 루프를 통한 명령어의 원자적 보장성으로 ���를 완벽히 지원한다 [1], [2].

- RDBMS의 네이티브 네임드 락(Named Lock)이나 행 단위 락킹은 트랜잭션 커넥션 풀을 과도하게 점유하여 병목을 유발하지만, Redis 기반 분산 락은 DB 연결 풀 부하 없이 분리된 인메모리 메모리 스페이스에서 조율된다 [2], [6].

### 2. Lettuce vs Redisson: 스핀 락(Spin Lock)과 Pub/Sub 스핀 방지 차이

스프링 프레임워크 생태계에서 Redis 분산 락을 구현할 때 Lettuce와 Redisson은 구현 방식의 극명한 아키텍처적 트레이드오프를 가집니다 [3], [5].

![Redis 분산 락 아키텍처 및 메커니즘](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/redis_distributed_lock_1786727947710.jpg)

#### Lettuce: 스핀 락(Spin Lock) 구조

Lettuce는 `SETNX` (Set if Not Exists) 명령을 루프 형태로 반복 찔러서 락을 획득할 때까지 대기하는 스핀 락 구조로 구동됩니다 [3].

- **한계**: 락을 획득할 때까지 Redis에 무수히 많은 폴링(Polling) 요청을 반복 전송(Busy Waiting)하므로, 스레드 블로킹 연산 비용이 급상승하며 Redis CPU 리소스를 한계까지 소모시킵니다 [3], [5].

#### Redisson: Pub/Sub 채널 구조

Redisson은 Redis가 제공하는 Pub/Sub 메시징 채널을 구독하여 락 대기 오버헤드를 근본적으로 해결합니다 [3], [5].

- **작동 메커니즘**: 락을 선점하지 못한 클라이언트는 락 소유 노드가 임무를 마친 후 `PUBLISH` 명령으로 던지는 "락 해제 알림" 채널을 대기(Subscribe)합니다. 알림을 수신하는 순간에만 락 획득을 시도하므로 네트워크 폴링 트래픽이 발생하지 않습니다.

- **추가적 안정성**: 락 점유 기간의 오버플로우를 차단하기 위해 백그라운드에서 임대 시간 연장 감시 스레드인 **'Watchdog'**이 동작하여 분산 작업 도중의 락 강제 이탈 사고(Timeout)를 자동 예방합니다 [3].

- Lettuce 기반 스핀 락 구조는 대기 중인 클라이언트 수에 비례하여 Redis에 가해지는 질의 트래픽이 지수적으로 증가하지만, Redisson은 Pub/Sub 채널을 통한 상태 이벤트 전파 구조를 지녀 유휴 부하를 발생시키지 않는다 [3], [5].

- Redisson의 Watchdog 스레드는 자바 가상 머신(JVM) 크래시가 나지 않는 한, 락 소유 노드의 비즈니스 수행 시간이 길어질 때 임대 수명(Lease Time)을 실시간으로 갱신해 주어 락의 강제 만료 유실을 차단한다 [3], [5].

### 3. Redlock 알고리즘의 동작 방식과 시계 드리프트(Clock Drift) 한계

Redis 인스턴스가 단 1대뿐인 Single Instance 구조는 단일 장애점(SPOF)을 지닙니다. 이를 보완하기 위해 Redis 원작자 살바토레 산필리포(Antirez)는 다중 독립 마스터 노드(최소 5대) 합의 프로토콜인 **'Redlock 알고리즘'**을 주창했습니다 [1], [5], [6].

#### Redlock 작동 방식:

- 클라이언트는 모든 독립 마스터 노드들(5대)에 아주 짧은 타임아웃 범위 내에서 락 획득을 순차 시도합니다.

- 클라이언트가 과반수 노드(5대 중 3대 이상)로부터 락을 점유하는 데 성공하고, 락 획득에 걸린 소요 시간이 최종 임대 시간보다 작다면 락이 완벽히 취득된 것으로 확정 판정합니다.

#### 분산 분기적 치명적 한계 (Martin Kleppmann의 반론):

학계의 유명한 분산 시스템 연구원 마틴 클랩만(Martin Kleppmann)은 Redlock의 아키텍처적 불안정성을 날카롭게 규명했습니다 [4], [5].

- 
**시계 드리프트 (Clock Drift)**: 가상화 클라우드 노드들은 각각 시스템 시계가 물리적 미세 진동이나 NTP(Network Time Protocol) 조정 등으로 미세하게 다르게 흐르는 현상을 겪습니다. (예: 특정 노드의 시계가 빠르게 흘러 만료 예정 ��간보다 먼저 락 키를 자동 삭제해 버리면, 다른 클라이언트가 과반수를 점령해 동시에 임계 영역에 진입하는 대형 정합성 균열이 일어납니다.) [4], [6].

- 
**GC Pause 및 네트워크 지연**: JVM의 Stop-the-world(Garbage Collection)가 걸려 스레드가 일시 중지된 사이, Redis의 락 수명이 만료되어 반환되면, 잠에서 깬 스레드는 자신이 락을 쥐고 있는 줄 오인하고 이중 쓰기(Double Write)를 유발합니다 [4], [5].

- 
Redlock 알고리즘은 분산 서버 노드 간의 하드웨어 시계 동기화(NTP 일관성)에 대한 수학적 신뢰성에 100% 종속되어 있으므로, 시계 드리프트 현상 발생 시 락의 상호 배제성(Mutual Exclusion)이 무너진다 [4], [6].

### 4. 분산 락의 한계 극복: 펜싱 토큰(Fencing Token) 패턴

이러한 하드웨어적 및 런타임 Stop-the-world 지연 한계를 원천적으로 극복하고 완벽한 데이터 일관성을 지켜내기 ���한 모범 설계 아키텍처가 바로 **'펜싱 토큰(Fencing Token)'**의 도입입니다 [4], [5].

- **동작 원리**:
클라이언트가 락을 정상 획득할 때마다, 락 관리 장치는 단조 증가하는 고유 번호인 '펜싱 토큰(예: 83, 84, 85...)'을 발급해 줍니다.

- 최종 데이터를 저장하는 RDBMS나 분산 파일 스토리지 단에서 쓰기 트랜잭션이 들어올 때, 현재 요청서에 동봉된 펜싱 토큰 값을 검증합니다.

- 스토리지 단은 자신이 기록한 **'가장 최근에 승인된 토큰 번호(예: 85)'**보다 작거나 같은 토큰(예: GC 지연으로 뒤늦게 요청이 날아온 이전의 84번 토큰)을 지닌 쓰기 요청을 발견하면 즉시 거부(Ignore/Reject) 처리합니다.

- 펜싱 토큰(Fencing Token) 패턴은 락 서버의 일시적 오류나 스레드 GC 지연을 우회하여, 최종 쓰기 저장소 단계에서 토큰의 순차 증가 값 검증을 통해 동시성 정합성 파괴를 영구 방지하는 안전망 역할을 한다 [4], [5].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 실무에서 다중 스레드의 분산 처리가 필요할 때, 애플리케이션 레벨의 락 구현보다 더 중요한 것이 "데이터베이스 레벨의 고유 제약 조건(Unique Constraint)"의 활용이라고 믿습니다. 락이라는 메커니즘은 결국 네트워크 타임아웃과 런타임 지연이라는 예외 시나리오에서 100% 안전할 수 없습니다. 따라서 락을 걸고 연산을 수행하기 전에 테이블 단에 `user_id`와 `date` 복합 유니크 키(Unique Key)를 걸어두거나, 버저닝을 통한 낙관적 락(Optimistic Lock)을 2차 안전 기둥으로 반드시 확보해 두는 이중 수비형 설계가 시스템 안정성을 좌우하는 격차를 만든다고 생각합니다.

## 한계와 반론

- **한계점**: 펜싱 토큰 패턴이 완벽하게 동시성 유실을 방지하려면, 최종 저장 스토리지(RDBMS 등)가 이 토큰 검증 연산을 원자적으로 처리할 수 있는 스펙을 내재하고 있어야 합니다. 만약 외부 스토리지나 파일 시스템이 파일 쓰기 단계에서 단순히 오버라이트(Overwrite)만 지원하고 버전 체크 메커니즘이 전혀 없다면 펜싱 토큰은 무용지물이 되는 제약이 있습니다.

- **반론**: 이에 대해 굳이 복잡한 Redlock과 펜싱 토큰을 조합하여 설계 비용을 낭비하느니, 분산 합의 성능이 뛰어난 주키퍼(ZooKeeper)를 사용해 임시 노드(Ephemeral Node)의 강제 자동 삭제 메커니즘을 락 제어에 사용하면 가상 머신 지연 문제나 시계 드리프트 리스크를 분산 일관성 프로토콜 수준에서 훨씬 더 저렴하고 신뢰성 있게 막을 수 있다는 반론도 인프라 측면에서 설득력을 지닙니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

동시성과 정합성의 역사는 늘 트레이드오프의 연속이었습니다. Lettuce의 심플함은 시스템이 한가할 ��� 빠르게 돌지만 몰리면 터지고, Redisson은 조용하지만 Pub/Sub 상태 관리를 위해 브로커 채널을 항상 유지해야 합니다. 아키텍트는 락 라이브러리를 고를 때 현재 비즈니스의 데이터 충돌 강도(Contention Level)를 평가해야 합니다. 충돌이 거의 없는 일상적인 도메인은 Lettuce의 직관적인 구현으로 족하며, 매일 대규모 한정 수량 구매 이벤트가 몰리는 이커머스의 중심부는 Redisson과 펜싱 토큰을 적극 도입해야 합니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- Redis Official Documentation, "Distributed Locks with Redis and the Redlock spec", [https://redis.io/docs/manual/patterns/distributed-locks/](https://redis.io/docs/manual/patterns/distributed-locks/)

- Confluent Developer Guide, "Locking Patterns and Concurrency Management in Large Scale Memory Stores", [https://developer.confluent.io/patterns/event-flow/concurrency/](https://developer.confluent.io/patterns/event-flow/concurrency/)

- Redisson Client Reference Guide, "Distributed Lock implementations and Watchdog configurations", [https://github.com/redisson/redisson/wiki/8.-Distributed-locks-and-Synchronizers](https://github.com/redisson/redisson/wiki/8.-Distributed-locks-and-Synchronizers)

- Martin Kleppmann's Blog, "How to do a distributed lock (Why Redlock is not safe)", [https://martin.kleppmann.com/2016/02/08/how-to-do-a-distributed-lock.html](https://martin.kleppmann.com/2016/02/08/how-to-do-a-distributed-lock.html)

- Confluent Architecture Library, "Comparing Lettuce and Redisson performance in high contention scenarios", [https://developer.confluent.io/courses/architecture/redis-locking-comparison/](https://developer.confluent.io/courses/architecture/redis-locking-comparison/)

- Google Cloud Architecture, "Time synchronization and drift mitigation strategies for distributed transactions", [https://cloud.google.com/solutions/time-sync-in-compute-engine](https://cloud.google.com/solutions/time-sync-in-compute-engine)
