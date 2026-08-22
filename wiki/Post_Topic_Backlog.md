# 📌 블로그 포스팅 추천 주제 백로그 (Post Topic Backlog)

본 문서는 AI Blogging Agent 및 관리자가 향후 블로그 글을 배포할 때 참고하고 고를 수 있도록 **기초 개념 주제, 심화 주제, 최신 이슈/트렌드 주제를 엄선하여 보관하는 위키 주제 백로그 문서**입니다.

---

## 🟢 1. 기초 / 개념 포스팅 추천 주제 (Basics / Concept Top 5)

| 번호 | 상태 | 포스팅 추천 주제명 | 핵심 다룰 기술 개념 |
| :---: | :---: | :--- | :--- |
| **B-1** | ✅ 발행완료 | ~~**OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리**~~ [🔗](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html) | PCB/TCB 메모리 영역(`Stack`, `Heap`, `Data`, `Text`), 컨텍스트 스위칭 CPU 레지스터 및 TLB 플러시 오버헤드 분석 |
| **B-2** | ✅ 발행완료 | ~~**HTTP/1.1 vs HTTP/2 vs HTTP/3 멀티플렉싱(Multiplexing)과 QUIC 프로토콜 메커니즘**~~ [🔗](https://beji-tech.blogspot.com/2026/08/http11-vs-http2-vs-http3.html) | HOLB(Head-of-Line Blocking) 문제, Binary Framing 레이어, UDP 기반 QUIC 패킷 손실 복구 원리 |
| **B-3** | ✅ 발행완료 | ~~**JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리**~~ [🔗](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html) | Young/Old Generation, Minor/Major GC, Stop-The-World 메커니즘 및 G1 GC 기본 동작 |
| **B-4** | ✅ 발행완료 | ~~**Relational DB (RDBMS) vs NoSQL DB 데이터 모델링 및 ACID vs BASE 트랜잭션 비교**~~ [🔗](https://beji-tech.blogspot.com/2026/08/sql-vs-nosql-sqlnosql-acid-vs-base-cap.html) | 원자성/일관성/격리성/지속성(ACID) vs Eventual Consistency(BASE) 및 쿼리 액세스 패턴 차이 |
| **B-5** | ✅ 발행완료 | ~~**TCP 3-Way / 4-Way Handshake 동작 흐름과 TIME_WAIT 소켓 상태 이해하기**~~ [🔗](https://beji-tech.blogspot.com/2026/08/tcp-3-way4-way-handshake-timewait.html) | SYN/ACK 시퀀스 번호 교환, FIN/ACK 소켓 클로징, TIME_WAIT 소켓 재사용(`SO_REUSEADDR`) 옵션 분석 |
| **B-6** | ✅ 발행완료 | ~~**TCP 기반 애플리케이션 계층 통신 원리 — 이메일(IMAP/POP3) 프로토콜이 TCP 위에서 동작하는 방식**~~ [🔗](https://beji-tech.blogspot.com/2026/08/tcp-imappop3-tcp.html) | 연결지향형 스트림 소켓과 포트 바인딩, 텍스트 기반 요청-응답 프로토콜 구조(IMAP/POP3/SMTP 공통 패턴), 신뢰성 있는 순서 보장 전달이 이메일 프로토콜 설계에 미치는 영향 |
| **B-7** | ✅ 발행완료 | ~~**TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가**~~ [🔗](https://beji-tech.blogspot.com/2026/08/tlsssl-handshake-https-tls-13-1-rtt.html) | TLS 1.2(2-RTT) vs TLS 1.3(1-RTT) 핸드셰이크 메시지 흐름(openssl s_client 실제 캡처 비교), SAN vs CN 인증서 체인 검증(RFC 6125), 0-RTT 재전송 위험(RFC 8446 §2.3/§8), RFC 8996의 TLS 1.0/1.1 폐지 |

---

## 🔴 2. 심화 / Advanced 포스팅 추천 주제 (Advanced / Deep Dive Top 5)

| 번호 | 상태 | 포스팅 추천 주제명 | 핵심 다룰 기술 개념 |
| :---: | :---: | :--- | :--- |
| **A-1** | ✅ 발행완료 | ~~**Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화**~~ [🔗](https://beji-tech.blogspot.com/2026/08/linux-epoll-eventloop-c10k-io.html) | `select`/`poll` $O(N)$ 한계 극복, $O(1)$ Red-Black Tree & Ready List 커널 메커니즘, Edge-Triggered 모드 핸들링 |
| **A-2** | ✅ 발행완료 | ~~**MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피**~~ [🔗](https://beji-tech.blogspot.com/2026/08/mysql-innodb-btree-covering-index.html) | Clustered vs Secondary Index, Doublewrite Buffer, Random I/O 감소 및 Index Condition Pushdown(ICP) |
| **A-3** | 🟡 미발행 (차별화 포인트 미정) | **Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅** | EventLoop 스레드 블로킹 차단법(`BlockHound`), `subscribeOn` vs `publishOn` 차이 및 Backpressure 마이크로 벤치마크 |
| **A-4** | 🟡 미발행 (차별화 포인트 미정) | **분산 시스템의 CAP 정리와 PACELC 정리 적용 및 Kafka / Cassandra 리플리케이션 분석** | 일관성(Consistency) vs 가용성(Availability) vs 분할 허용성(Partition Tolerance), ISR(In-Sync Replicas) 메커니즘 |
| **A-5** | 🟡 미발행 (차별화 포인트 미정) | **Go routine (Goroutine) GMP 스케줄러 내부 동작 원리와 동시성 락 프리(Lock-free) 채널 메커니즘** | Global/Local Run Queue, Work Stealing, M:N 스케줄링 모델 및 메모리 배리어 락 프리 RingBuffer 구조 |
| **A-6** | ✅ 발행완료 | ~~**IMAP vs POP3 이메일 통신 프로토콜 비교 및 동작 절차**~~ [🔗](https://beji-tech.blogspot.com/2026/08/imap-vs-pop3.html) | IMAP(서버 동기화, 다중 기기 지원, 포트 143/993) vs POP3(다운로드 후 삭제, 단일 기기, 포트 110/995) 아키텍처 차이, TLS/SSL 암호화 적용, 실제 명령어 시퀀스(IMAP `LOGIN`/`SELECT`/`FETCH`, POP3 `USER`/`PASS`/`RETR`/`DELE`) 분석 |

---

## 🔥 3. 최신 이슈 / 트렌드 (Trending / Recent Issues)

이 섹션은 **기초/심화 표와 달리 고정 리스트를 두지 않습니다.** IT 트렌드는 빠르게 바뀌므로, 관리자가 "트렌드 주제로 써줘" 같은 요청을 하면 Agent는 이 섹션을 채워둔 과거 목록을 재활용하지 말고 **그 시점에 WebSearch로 최근 1~2개월 내 IT 이슈/트렌드를 새로 조사**해서 후보를 제시합니다(예: 새 프레임워크 메이저 릴리스, 업계 화제가 된 장애/보안 이슈, 새로 표준화된 프로토콜 등). 조사한 후보 중 실제로 글을 쓰기로 확정한 것만 아래에 기록해 발행 이력을 남깁니다.

| 번호 | 상태 | 포스팅 추천 주제명 | 조사 시점 |
| :---: | :---: | :--- | :---: |
| **T-1** | ✅ 발행완료 | ~~**MCP(Model Context Protocol) 2026-07-28 스펙 갱신: Stateless 아키텍처 전환과 A2A 멀티 에이전트 오케스트레이션 표준화**~~ [🔗](https://beji-tech.blogspot.com/2026/08/mcpmodel-context-protocol-2026-07-28.html) | 2026-08-17 |

---

## 🚀 사용 가이드

- 관리자(사용자)가 대화 세션 중 주제 추천을 물어보거나 골라서 생성을 지시할 때, Agent는 본 백로그([`wiki/Post_Topic_Backlog.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Post_Topic_Backlog.md))에서 **미발행(🟡)** 상태인 번호(B-5, A-3~A-5) 또는 주제를 읽어 즉시 `python main.py new --topic "주제명"` 파이프라인을 구동합니다. "트렌드"/"최근 이슈" 주제를 요청받으면 위 3번 섹션 규칙대로 매번 새로 조사합니다.
- **발행완료(✅) 항목은 다시 추천하지 않습니다.** 새로 글을 발행했다면 이 표의 상태를 갱신하고, 발행 URL은 `content/posts/<slug>.md`의 frontmatter `url` 필드 또는 `https://beji-tech.blogspot.com/sitemap.xml`에서 확인할 수 있습니다.
- **신규 주제는 차별화 포인트 없이 추천하지 않습니다** (`wiki/Blog_Writing_Rules.md` 14번 수칙, 2026-08-22 추가). 이미 포화된 CS 101 주제(정의+교과서적 예시만 있는 개념글)를 그대로 추천하지 말고, "이 글이 상위 검색결과 대비 무엇을 더하는가"에 대한 구체적 각도를 함께 제시할 것 — 위 표에 "(차별화 포인트 미정)"으로 표시된 항목은 작성 전 이 각도를 먼저 확정해야 합니다.
