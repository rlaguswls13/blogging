# 📌 블로그 포스팅 추천 주제 백로그 (Post Topic Backlog)

본 문서는 AI Blogging Agent 및 관리자가 향후 블로그 글을 배포할 때 참고하고 고를 수 있도록 **기초 개념 주제 5개와 심화 주제 5개를 엄선하여 보관하는 위키 주제 백로그 문서**입니다.

---

## 🟢 1. 기초 / 개념 포스팅 추천 주제 (Basics / Concept Top 5)

| 번호 | 포스팅 추천 주제명 | 핵심 다룰 기술 개념 |
| :---: | :--- | :--- |
| **B-1** | **OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리** | PCB/TCB 메모리 영역(`Stack`, `Heap`, `Data`, `Text`), 컨텍스트 스위칭 CPU 레지스터 및 TLB 플러시 오버헤드 분석 |
| **B-2** | **HTTP/1.1 vs HTTP/2 vs HTTP/3 멀티플렉싱(Multiplexing)과 QUIC 프로토콜 메커니즘** | HOLB(Head-of-Line Blocking) 문제, Binary Framing 레이어, UDP 기반 QUIC 패킷 손실 복구 원리 |
| **B-3** | **JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리** | Young/Old Generation, Minor/Major GC, Stop-The-World 메커니즘 및 G1 GC 기본 동작 |
| **B-4** | **Relational DB (RDBMS) vs NoSQL DB 데이터 모델링 및 ACID vs BASE 트랜잭션 비교** | 원자성/일관성/격리성/지속성(ACID) vs Eventual Consistency(BASE) 및 쿼리 액세스 패턴 차이 |
| **B-5** | **TCP 3-Way / 4-Way Handshake 동작 흐름과 TIME_WAIT 소켓 상태 이해하기** | SYN/ACK 시퀀스 번호 교환, FIN/ACK 소켓 클로징, TIME_WAIT 소켓 재사용(`SO_REUSEADDR`) 옵션 분석 |

---

## 🔴 2. 심화 / Advanced 포스팅 추천 주제 (Advanced / Deep Dive Top 5)

| 번호 | 포스팅 추천 주제명 | 핵심 다룰 기술 개념 |
| :---: | :--- | :--- |
| **A-1** | **Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화** | `select`/`poll` $O(N)$ 한계 극복, $O(1)$ Red-Black Tree & Ready List 커널 메커니즘, Edge-Triggered 모드 핸들링 |
| **A-2** | **MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피** | Clustered vs Secondary Index, Doublewrite Buffer, Random I/O 감소 및 Index Condition Pushdown(ICP) |
| **A-3** | **Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅** | EventLoop 스레드 블로킹 차단법(`BlockHound`), `subscribeOn` vs `publishOn` 차이 및 Backpressure 마이크로 벤치마크 |
| **A-4** | **분산 시스템의 CAP 정리와 PACELC 정리 적용 및 Kafka / Cassandra 리플리케이션 분석** | 일관성(Consistency) vs 가용성(Availability) vs 분할 허용성(Partition Tolerance), ISR(In-Sync Replicas) 메커니즘 |
| **A-5** | **Go routine (Goroutine) GMP 스케줄러 내부 동작 원리와 동시성 락 프리(Lock-free) 채널 메커니즘** | Global/Local Run Queue, Work Stealing, M:N 스케줄링 모델 및 메모리 배리어 락 프리 RingBuffer 구조 |

---

## 🚀 사용 가이드

- 관리자(사용자)가 대화 세션 중 주제 추천을 물어보거나 골라서 생성을 지시할 때, Agent는 본 백로그([`wiki/Post_Topic_Backlog.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Post_Topic_Backlog.md))에서 번호(B-1 ~ B-5, A-1 ~ A-5) 또는 주제를 읽어 즉시 `python main.py new --topic "주제명"` 파이프라인을 구동합니다.
