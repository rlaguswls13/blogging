---
title: "Index"
tags: [MOC]
---

# 발행 글 인덱스 (Obsidian Map of Content)

이 볼트는 `python main.py publish`로 라이브 배포된 글의 정식 아카이브(`content/posts/`)입니다.
카테고리 폴더(`Basics/`, `Advanced/`, `ETC/`)는 각 글의 frontmatter `tags`에 실제로 붙은
블로그 상단 탭 라벨과 1:1로 대응합니다(`wiki/Blog_Writing_Rules.md` 7번 수칙 — 키워드 추론이
아니라 태그 기준). 새 글이 추가될 때마다 `git mv`로 폴더가 이동하므로, 이 인덱스는 수동으로
최신화해야 합니다(자동 생성 아님).

각 글의 frontmatter `url` 필드가 실제 라이브 Blogger 주소입니다. 이 볼트 안의 `[[위키링크]]`는
Obsidian 그래프/탐색 전용이며, 라이브 사이트의 "🔗 관련 글" 백링크는 별도로 각 글 본문의
`## 백링크` 섹션에 실제 URL로 관리됩니다(둘을 혼동하지 말 것).

카테고리별로 글들이 실제 백링크로 어떻게 엮여 있는지는 `python src/tools/build_moc.py`가
생성하는 아래 MOC를 참고하세요(태그 기준 그룹 + 실제 백링크 화살표, 자동 생성이라 수동
편집하면 다음 재생성 때 사라집니다):

- [[Basics/_MOC|Basics MOC]]
- [[Advanced/_MOC|Advanced MOC]]
- [[ETC/_MOC|ETC MOC]]

## Basics (30)

- [[gof-1-singleton-pattern-java|[GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시]]
- [[gof-10-strategy-pattern-java|[GoF 디자인 패턴] 10. 전략 패턴 (Strategy Pattern) 개념과 Java 실전 예시]]
- [[gof-11-observer-pattern-java|[GoF 디자인 패턴] 11. 옵저버 패턴 (Observer Pattern) 개념과 Java 실전 예시]]
- [[gof-12-command-pattern-java|[GoF 디자인 패턴] 12. 커맨드 패턴 (Command Pattern) 개념과 Java 실전 예시]]
- [[gof-13-state-pattern-java|[GoF 디자인 패턴] 13. 상태 패턴 (State Pattern) 개념과 Java 실전 예시]]
- [[gof-14-template-method-pattern-java|[GoF 디자인 패턴] 14. 템플릿 메서드 패턴 (Template Method Pattern) 개념과 Java 실전 예시]]
- [[gof-14|GoF 핵심 14가지 디자인 패턴 분석 및 개별 포스트 인덱스 가이드]]
- [[gof-2-factory-method-pattern-java|[GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시]]
- [[gof-3-abstract-factory-pattern-java|[GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시]]
- [[gof-4-builder-pattern-java|[GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시]]
- [[gof-5-prototype-pattern-java|[GoF 디자인 패턴] 5. 프로토타입 패턴 (Prototype Pattern) 개념과 Java 실전 예시]]
- [[gof-6-adapter-pattern-java|[GoF 디자인 패턴] 6. 어댑터 패턴 (Adapter Pattern) 개념과 Java 실전 예시]]
- [[gof-7-decorator-pattern-java|[GoF 디자인 패턴] 7. 데코레이터 패턴 (Decorator Pattern) 개념과 Java 실전 예시]]
- [[gof-8-proxy-pattern-java|[GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시]]
- [[gof-9-composite-pattern-java|[GoF 디자인 패턴] 9. 컴포지트 패턴 (Composite Pattern) 개념과 Java 실전 예시]]
- [[java-collections-list-set-map-guide|Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가]]
- [[jvm-heap-stack-metaspace-gc-basics|JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리]]
- [[mvc-msa-architecture-evolution|MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리]]
- [[mvc|MVC 패턴: 자판기에서 동적 웹 서비스까지의 진화 및 아키텍처 분석]]
- [[nosql-1-key-value-document-db-redis-vs|[NoSQL 깊이 읽기 #1] Key-Value & Document DB: Redis vs MongoDB 아키텍처 및 실무 가이드]]
- [[nosql-2-column-family-graph-db|[NoSQL 깊이 읽기 #2] Column-Family & Graph DB: Cassandra vs Neo4j 핵심 원리와 활용법]]
- [[rdbms-1-open-source-rdbms-mysql-vs|[RDBMS 깊이 읽기 #1] Open Source RDBMS 대표주자: MySQL vs MariaDB vs PostgreSQL 기술 비교]]
- [[rdbms-2-enterprise-rdbms-oracle-vs|[RDBMS 깊이 읽기 #2] Enterprise RDBMS 거인: Oracle vs Microsoft SQL Server (MSSQL) 비교]]
- [[rdbms-basics-concept-benefits-when-to-use|RDBMS(관계형 데이터베이스)란 무엇인가 — 개념, 장점, 그리고 실무에서 언제 선택해야 하는가]]
- [[solid-principles-java-guide|SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시]]
- [[sql-basics-select-insert-update-delete-join|SQL 기본 문법 입문 — SELECT/INSERT/UPDATE/DELETE와 JOIN, WHERE, GROUP BY 실전 예시]]
- [[sql-vs-nosql-sqlnosql-acid-vs-base-cap|[SQL vs NoSQL] 데이터베이스 기초와 패러다임 비교: SQL/NoSQL 정의, 탄생 배경, ACID vs BASE, CAP 정리]]
- [[tcp-application-layer-imap-pop3|TCP 기반 애플리케이션 계층 통신 원리 — 이메일(IMAP/POP3) 프로토콜이 TCP 위에서 동작하는 방식]]
- [[tcp-handshake-time-wait-socket-demo|TCP 3-Way/4-Way Handshake와 TIME_WAIT — 실제로 소켓을 열고 닫아 눈으로 확인하기]]
- [[tls-ssl-handshake-https-certificate-verification|TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가]]

## Advanced (20)

- [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]]
- [[cap-pacelc-kafka-cassandra-replication|분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프]]
- [[google-blogger-api-oauth-20-python|Google Blogger API 사용법: OAuth 2.0 연동과 Python을 통한 글 배포 자동화]]
- [[goroutine-gmp-scheduler-channel-mutex|Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다]]
- [[grpc-protobuf-http2-streaming-serialization|gRPC와 Protocol Buffers: HTTP/2 기반 스트리밍과 직렬화 원리]]
- [[imap-vs-pop3-email-protocol|IMAP vs POP3 이메일 통신 프로토콜 비교 및 동작 절차]]
- [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]]
- [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]]
- [[load-balancing-l4-vs-l7|대규모 시스템을 위한 로드 밸런싱(Load Balancing) 알고리즘과 L4 vs L7 스위치의 차이]]
- [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]]
- [[mysql-innodb-btree-covering-index|MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피]]
- [[os-process-vs-thread|OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리]]
- [[push-activemq-vs-pull-kafka|메시지 컨슘 모델의 트레이드오프: Push 방식(ActiveMQ) vs Pull 방식(Kafka) 아키텍처 분석]]
- [[redis-distributed-lock-redlock-clock|Redis 분산 락(Distributed Lock)의 한계와 극복: Redlock 알고리즘과 시계 드리프트(Clock Drift) 정합성 딜레마]]
- [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]]
- [[spring-aop-proxy-jdk-dynamic-proxy-vs|Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석]]
- [[spring-ioc-di-constructor-injection|Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가]]
- [[spring-webflux-reactor-schedulers-troubleshooting|Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅]]
- [[sync-vs-async-blocking-vs-non-blocking|동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의]]
- [[vector-database-hnsw-ann-indexing|Vector Database ANN 인덱싱: HNSW 알고리즘과 RAG 파이프라인에서의 역할]]

## ETC (5)

- [[http11-vs-http2-vs-http3|HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리]]
- [[kubernetes-operator-custom-controller|Kubernetes Operator 패턴의 이해와 활용: Custom Controller를 통한 자동화 설계]]
- [[llm-agent-autogen-vs-langgraph|LLM Agent 오케스트레이션 프레임워크 비교 분석: AutoGen vs LangGraph]]
- [[mcp-2026-07-28-spec-stateless-a2a|MCP(Model Context Protocol) 2026-07-28 스펙 갱신: Stateless 아키텍처 전환과 멀티 에이전트 시대의 표준화]]
- [[rag-graphrag|RAG(검색 증강 생성) 시스템의 한계 극복을 위한 GraphRAG 아키텍처와 엔티티 추출 원리]]
