# Advanced — Backlink MOC

글 본문 `## 백링크` 섹션(실제 라이브 URL)을 파싱해 자동 생성했습니다. 그룹 표제는 각 글의 실제 `tags`에서 가져온 것이며, 화살표는 백링크 방향(A → B: A의 본문이 B를 인용)입니다. 다시 생성하려면 `python src/tools/build_moc.py`를 재실행하세요(수동 편집 시 다음 재생성에서 덮어써집니다).

## Spring

- [[spring-batch-chunk-oriented-architecture|Spring Batch — 대용량 데이터 처리를 위한 Chunk 지향 아키텍처]]
  - → [[mysql-innodb-btree-covering-index|MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피]]
  - → [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
- [[spring-mvc-vs-webflux-when-to-choose-reactive|Spring MVC vs WebFlux — 언제 리액티브를 선택해야 하는가(실측 처리량 비교)]]
  - → [[mvc-msa-architecture-evolution|MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리]] *(Basics)*
  - → [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
- [[spring-security-filter-chain-request-lifecycle|Spring Security Filter Chain — 인증/인가 요청이 통과하는 전 과정]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*
  - → [[tls-ssl-handshake-https-certificate-verification|TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가]] *(Basics)*
- [[spring-async-thread-pool-exception-propagation-pitfalls|Spring @Async — 비동기 처리 시 스레드 풀 설정과 예외 전파 함정]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
- [[spring-bean-validation-valid-custom-validator|Spring Bean Validation(@Valid) — 검증 어노테이션 동작 원리와 커스텀 Validator]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*
- [[spring-cache-abstraction-cacheable-invalidation-strategy|Spring Cache Abstraction(@Cacheable) — 캐시 추상화 동작 원리와 실전 무효화 전략]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*
- [[spring-data-jpa-n-plus-1-fetch-join-entitygraph-benchmark|Spring Data JPA N+1 문제 — 원인과 fetch join/EntityGraph 실측 벤치마크]]
  - → [[mysql-innodb-btree-covering-index|MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피]]
  - → [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
- [[spring-hikaricp-pool-sizing-formula-leak-detection|Spring 커넥션 풀(HikariCP) — 풀 사이즈 설계 공식과 커넥션 누수 진단]]
  - → [[gof-1-singleton-pattern-java|[GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시]] *(Basics)*
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*
- [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
  - → [[goroutine-gmp-scheduler-channel-mutex|Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다]]
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]

## System Architecture

- [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[push-activemq-vs-pull-kafka|메시지 컨슘 모델의 트레이드오프: Push 방식(ActiveMQ) vs Pull 방식(Kafka) 아키텍처 분석]]
  - → [[redis-distributed-lock-redlock-clock|Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마]]
- [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[push-activemq-vs-pull-kafka|메시지 컨슘 모델의 트레이드오프: Push 방식(ActiveMQ) vs Pull 방식(Kafka) 아키텍처 분석]]
  - → [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]
- [[load-balancing-l4-vs-l7|대규모 시스템을 위한 로드 밸런싱(Load Balancing) 알고리즘과 L4 vs L7 스위치의 차이]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[redis-distributed-lock-redlock-clock|Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마]]
- [[push-activemq-vs-pull-kafka|메시지 컨슘 모델의 트레이드오프: Push 방식(ActiveMQ) vs Pull 방식(Kafka) 아키텍처 분석]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[cap-pacelc-kafka-cassandra-replication|분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
- [[redis-distributed-lock-redlock-clock|Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[load-balancing-l4-vs-l7|대규모 시스템을 위한 로드 밸런싱(Load Balancing) 알고리즘과 L4 vs L7 스위치의 차이]]
- [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
  - → [[redis-distributed-lock-redlock-clock|Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마]]

## Java

- [[java-classloader-parent-delegation-model|Java ClassLoader — 클래스 로딩 과정과 계층 구조(Bootstrap/Platform/App)]]
  - → [[jvm-heap-stack-metaspace-gc-basics|JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리]] *(Basics)*
  - → [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*
- [[java-completablefuture-async-callback-exception-handling|Java CompletableFuture — 비동기 콜백 체이닝과 예외 처리 실전 패턴]]
  - → [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]]
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
  - → [[sync-vs-async-blocking-vs-non-blocking|동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의]]
- [[java-virtual-threads-project-loom-vs-platform-threads|Java Virtual Threads(Project Loom) — 기존 스레드 모델과 무엇이 다른가]]
  - → [[goroutine-gmp-scheduler-channel-mutex|Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다]]
  - → [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
- [[jvm-jit-tiered-compilation-c1-c2-deoptimization|JVM JIT 티어드 컴파일 — C1/C2 컴파일러와 역최적화(Deoptimization)가 실행 성능을 바꾸는 원리]]
  - → [[java-compiled-or-interpreted-language|자바는 컴파일 언어인가, 인터프리터 언어인가 — 바이트코드 기준으로 정리]] *(Basics)*
  - → [[java-g1gc-region-satb-mixed-gc-tuning|Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전]]
  - → [[jvm-heap-stack-metaspace-gc-basics|JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리]] *(Basics)*
- [[java-g1gc-region-satb-mixed-gc-tuning|Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전]]
  - → [[jvm-heap-stack-metaspace-gc-basics|JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리]] *(Basics)*
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
- [[java-record-immutable-dto-lombok-value-tradeoff|Java Record — 불변 DTO 설계와 기존 Lombok @Value 대비 트레이드오프]]
  - → [[solid-principles-java-guide|SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시]] *(Basics)*
  - → [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]] *(허브)*

## Networking

- [[sync-vs-async-blocking-vs-non-blocking|동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의]]
  - → [[gof-14|GoF 핵심 14가지 디자인 패턴 분석 및 개별 포스트 인덱스 가이드]] *(Basics)* *(허브)*
  - → [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]]
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
- [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]]
  - → [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[sync-vs-async-blocking-vs-non-blocking|동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의]]
- [[imap-vs-pop3-email-protocol|IMAP vs POP3 이메일 통신 프로토콜 비교 및 동작 절차]]
  - → [[sync-vs-async-blocking-vs-non-blocking|동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의]]

## Kafka

- [[cap-pacelc-kafka-cassandra-replication|분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
- [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
  - → [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]

## Search

- [[elasticsearch-inverted-index-search-performance|Elasticsearch 역색인(Inverted Index) 구조와 검색 성능 최적화 원리]]
  - → [[cap-pacelc-kafka-cassandra-replication|분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프]]
  - → [[java-g1gc-region-satb-mixed-gc-tuning|Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전]]
  - → [[mysql-innodb-btree-covering-index|MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피]]

## Python

- [[google-blogger-api-oauth-20-python|Google Blogger API 사용법: OAuth 2.0 연동과 Python을 통한 글 배포 자동화]]
  - → [[kubernetes-operator-custom-controller|Kubernetes Operator 패턴의 이해와 활용: Custom Controller를 통한 자동화 설계]] *(ETC)*

## Concurrency

- [[goroutine-gmp-scheduler-channel-mutex|Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다]]
  - → [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]]
  - → [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]

## gRPC

- [[grpc-protobuf-http2-streaming-serialization|gRPC와 Protocol Buffers: HTTP/2 기반 스트리밍과 직렬화 원리]]
  - → [[http11-vs-http2-vs-http3|HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리]] *(ETC)*
  - → [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]

## mysql

- [[mysql-innodb-btree-covering-index|MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피]]
  - → [[gof-14|GoF 핵심 14가지 디자인 패턴 분석 및 개별 포스트 인덱스 가이드]] *(Basics)* *(허브)*

## OpenTelemetry

- [[opentelemetry-distributed-tracing-msa|분산 트레이싱과 OpenTelemetry: MSA 비동기 메시징 경계에서 트레이스 컨텍스트가 끊기는 지점과 샘플링 전략]]
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
  - → [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]

## thread

- [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
  - → [[goroutine-gmp-scheduler-channel-mutex|Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다]]
  - → [[jvm-heap-stack-metaspace-gc-basics|JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리]] *(Basics)*
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]

## Spring Boot

- [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
  - → [[mvc-msa-architecture-evolution|MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리]] *(Basics)*

## Vector Database

- [[vector-database-hnsw-ann-indexing|Vector Database ANN 인덱싱: HNSW 알고리즘과 RAG 파이프라인에서의 역할]]
  - → [[llm-agent-autogen-vs-langgraph|LLM Agent 오케스트레이션 프레임워크 비교 분석: AutoGen vs LangGraph]] *(ETC)*
  - → [[rag-graphrag|RAG(검색 증강 생성) 시스템의 한계 극복을 위한 GraphRAG 아키텍처와 엔티티 추출 원리]] *(ETC)*

## 🔗 허브: Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가 (10개 글이 참조)

- [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]]
  - ← [[java-classloader-parent-delegation-model|Java ClassLoader — 클래스 로딩 과정과 계층 구조(Bootstrap/Platform/App)]]
  - ← [[java-record-immutable-dto-lombok-value-tradeoff|Java Record — 불변 DTO 설계와 기존 Lombok @Value 대비 트레이드오프]]
  - ← [[java-checked-vs-unchecked-exception-spring-dataaccessexception|Java 예외 처리 전략 — Checked vs Unchecked Exception, 언제 무엇을 쓸 것인가]] *(Basics)*
  - ← [[mvc-msa-architecture-evolution|MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리]] *(Basics)*
  - ← [[solid-principles-java-guide|SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시]] *(Basics)*
  - ← [[spring-bean-validation-valid-custom-validator|Spring Bean Validation(@Valid) — 검증 어노테이션 동작 원리와 커스텀 Validator]]
  - ← [[spring-bean-lifecycle-postconstruct-beanpostprocessor-order|Spring Bean 생명주기(Lifecycle) — 컨테이너가 Bean을 생성·초기화·소멸시키는 전 과정]] *(Basics)*
  - ← [[spring-cache-abstraction-cacheable-invalidation-strategy|Spring Cache Abstraction(@Cacheable) — 캐시 추상화 동작 원리와 실전 무효화 전략]]
  - ← [[spring-security-filter-chain-request-lifecycle|Spring Security Filter Chain — 인증/인가 요청이 통과하는 전 과정]]
  - ← [[spring-hikaricp-pool-sizing-formula-leak-detection|Spring 커넥션 풀(HikariCP) — 풀 사이즈 설계 공식과 커넥션 누수 진단]]
