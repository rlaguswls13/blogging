# ETC — Backlink MOC

글 본문 `## 백링크` 섹션(실제 라이브 URL)을 파싱해 자동 생성했습니다. 그룹 표제는 각 글의 실제 `tags`에서 가져온 것이며, 화살표는 백링크 방향(A → B: A의 본문이 B를 인용)입니다. 다시 생성하려면 `python src/tools/build_moc.py`를 재실행하세요(수동 편집 시 다음 재생성에서 덮어써집니다).

## LLM

- [[rag-graphrag|RAG(검색 증강 생성) 시스템의 한계 극복을 위한 GraphRAG 아키텍처와 엔티티 추출 원리]]
  - → [[cap-pacelc-kafka-cassandra-replication|분산 시스템의 CAP 정리와 PACELC 정리 — Kafka ISR과 Cassandra 튜너블 컨시스턴시로 보는 실전 트레이드오프]] *(Advanced)*
  - → [[mcp-2026-07-28-spec-stateless-a2a|MCP(Model Context Protocol) 2026-07-28 스펙 갱신: Stateless 아키텍처 전환과 멀티 에이전트 시대의 표준화]]
  - → [[vector-database-hnsw-ann-indexing|Vector Database ANN 인덱싱: HNSW 알고리즘과 RAG 파이프라인에서의 역할]] *(Advanced)*
- [[mcp-2026-07-28-spec-stateless-a2a|MCP(Model Context Protocol) 2026-07-28 스펙 갱신: Stateless 아키텍처 전환과 멀티 에이전트 시대의 표준화]]
  - → [[llm-agent-autogen-vs-langgraph|LLM Agent 오케스트레이션 프레임워크 비교 분석: AutoGen vs LangGraph]]
  - → [[rag-graphrag|RAG(검색 증강 생성) 시스템의 한계 극복을 위한 GraphRAG 아키텍처와 엔티티 추출 원리]]

## WebPerformance

- [[http11-vs-http2-vs-http3|HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리]]
  - → [[grpc-protobuf-http2-streaming-serialization|gRPC와 Protocol Buffers: HTTP/2 기반 스트리밍과 직렬화 원리]] *(Advanced)*
  - → [[linux-epoll-event-loop-c10k|Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화]] *(Advanced)*
  - → [[tls-ssl-handshake-https-certificate-verification|TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가]] *(Basics)*

## Operator-Pattern

- [[kubernetes-operator-custom-controller|Kubernetes Operator 패턴의 이해와 활용: Custom Controller를 통한 자동화 설계]]
  - → [[google-blogger-api-oauth-20-python|Google Blogger API 사용법: OAuth 2.0 연동과 Python을 통한 글 배포 자동화]] *(Advanced)*
  - → [[kafka|Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략]] *(Advanced)*
  - → [[saga-msa-choreography-vs-orchestration|Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략]] *(Advanced)*

## Software Architecture

- [[llm-agent-autogen-vs-langgraph|LLM Agent 오케스트레이션 프레임워크 비교 분석: AutoGen vs LangGraph]]
  - → [[4-activemq-kafka-rabbitmq-redis|4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드]] *(Advanced)*
  - → [[gof-14|GoF 핵심 14가지 디자인 패턴 분석 및 개별 포스트 인덱스 가이드]] *(Basics)* *(허브)*
  - → [[msa-non-blocking-retry-dlq|이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략]] *(Advanced)*
