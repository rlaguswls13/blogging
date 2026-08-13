# Technology Article Wiki (Content RAG Base)

이 위키는 기술 블로그 포스팅 작성을 진행할 때 에이전트가 리서치 및 팩트 교차 검증의 1차 상황 지식으로 참고하는 **콘텐츠용 기술 지식 베이스**입니다.

## 주요 기술 문서 목록

- [Kubernetes Operator 패턴](Kubernetes_Operator_패턴.md)
  - CRD(Custom Resource Definition), Reconciliation Loop, 그리고 Kubebuilder와 Operator SDK 비교 분석이 포함된 Kubernetes Operator 기술 지식입니다.
- [Sync vs Async 및 Blocking vs NonBlocking](Sync_vs_Async_및_Blocking_vs_NonBlocking.md)
  - 제어권 반환 시점과 완료 통지 방식의 차이로 이해하는 동기/비동기, 블로킹/논블로킹 핵심 아키텍처입니다.
- [HTTP 프로토콜 발전사](HTTP_프로토콜_발전사.md)
  - HTTP/1.1 HOL Blocking 병목부터 HTTP/2 다중화, HTTP/3 UDP 기반 QUIC의 0-RTT 및 세션 마이그레이션 기술 정리입니다.
- [대규모 로드 밸런싱 및 L4/L7 스위치](대규모_로드_밸런싱_및_L4_L7_스위치.md)
  - 고가용성 및 스케일아웃을 보장하기 위한 분산 알고리즘(일관성 해싱 등) 및 L4/L7 LB 인프라 비교 스펙입니다.

## RAG 연동 가이드
- 이 폴더 내의 지식들은 `hooks.json`의 `PreInvocation` RAG 훅에 의해 질문 키워드와 매칭되어 자동으로 컨텍스트에 로드됩니다.
- 새로운 기술 사실이나 공식 레퍼런스를 발견하면 즉시 이 폴더 하위의 마크다운 파일을 보강하여 에이전트의 작문 지식을 풍성하게 최신화해 주세요.
