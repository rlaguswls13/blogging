---
author: ''
createdAt: '2026-08-26T00:25:38.310054Z'
factCheckScore: 1.0
id: '4180520491183938646'
notionPageId: null
publishedAt: '2026-08-25T22:44:40-07:00'
slug: rest-api-design-principles-http-methods-status-codes
status: published
tags:
- Basics
- REST
- HTTP
- API Design
title: REST API 설계 기본 원칙 — HTTP 메서드와 상태 코드로 보는 RESTful 아키텍처
updatedAt: '2026-08-26T00:25:38.310054Z'
url: https://beji-tech.blogspot.com/2026/08/rest-api-http-restful.html
---

# REST API 설계 기본 원칙 — HTTP 메서드와 상태 코드로 보는 RESTful 아키텍처

## 요약

"REST API"는 흔히 "HTTP로 JSON을 주고받는 API"와 동의어처럼 쓰이지만, Roy Fielding이 2000년 박사 논문에서 규정한 제약 조건과는 꽤 거리가 있습니다. 이 글은 HTTP 메서드의 안전성(safe)과 멱등성(idempotent)이라는 IETF RFC 9110 표준 개념을 실제 실패 시나리오와 함께 설명하고, 상태 코드를 의미에 맞게 고르는 기준을 정리합니다. 나아가 많은 튜토리얼이 건너뛰는 HATEOAS(하이퍼미디어 기반 애플리케이션 상태 전이) 제약과, 실무에서 "RESTful"이라 불리지만 실제로는 REST가 아닌 API가 왜 그렇게 되는지도 함께 짚습니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어. 이 글이 같은 주제 상위 검색결과 대비 무엇을 더하는지 최소 1가지를 구체적으로
쓸 것 (wiki/Blog_Writing_Rules.md 14번 수칙) — 예: 직접 돌려본 벤치마크 수치, 실제 겪은 프로덕션
이슈/장애, 흔치 않은 조합/트레이드오프, 다른 곳에서 보기 힘든 비교표, 실제 실행해보고 확인한 예상 밖
동작. "정의 + 교과서적 예시"만 있는 포화 101 주제(GoF 패턴류 등)는 이 각도 없이는 신규 작성을 지양한다.
-->

REST API 설계는 포화된 101 주제이지만, 상위 검색결과 대부분이 "GET은 조회, POST는 생성"이라는 표면적 매핑만 다루고 정작 실무에서 장애로 이어지는 두 가지 지점을 비워둔다. 첫째, RFC 9110의 안전(safe)·멱등(idempotent) 정의를 코드 수준 실패 시나리오(네트워크 타임아웃 후 클라이언트가 요청을 재전송할 때 POST와 PUT이 서버 상태에 만드는 차이, 결제 중복 생성 사례)로 직접 재현해서 보여준다. 둘째, Fielding 본인이 2008년 블로그에서 "hypertext로 구동되지 않으면 REST API가 아니다"라고 명시한 HATEOAS 제약을, 실제 REST API라 불리는 서비스들이 왜 거의 지키지 않는지 그 이유(클라이언트-서버 결합 비용 대 개발 편의성의 트레이드오프)까지 파고들어, "교과서적 정의 나열"에 그치지 않고 왜 현실과 이론이 갈라졌는지를 설명한다.

## 본문

### REST란 무엇인가 — Fielding의 원래 정의

REST(Representational State Transfer)는 Roy Fielding이 2000년 UC Irvine 박사 학위 논문 "Architectural Styles and the Design of Network-based Software Architectures"의 5장에서 제안한 아키텍처 스타일이다[1]. 이 논문은 REST를 다음 제약 조건들의 조합으로 정의한다.

- **클라이언트-서버(Client-Server)**: UI 관심사와 데이터 저장 관심사를 분리해 이식성과 확장성을 개선한다.
- **무상태성(Stateless)**: "클라이언트의 각 요청은 요청을 이해하는 데 필요한 모든 정보를 포함해야 하며, 서버에 저장된 컨텍스트를 활용할 수 없다"[1]. 세션 상태는 클라이언트가 들고 있어야 한다.
- **캐시 가능성(Cacheable)**: 응답이 캐시 가능한지 여부가 명시적/암묵적으로 라벨링되어야 한다.
- **계층화 시스템(Layered System)**: 클라이언트는 프록시나 게이트웨이를 거쳐도 최종 서버와 직접 통신하는지 구분할 필요가 없다.
- **코드 온 디맨드(Code-On-Demand, 선택)**: 서버가 클라이언트에 실행 가능한 코드를 보내 기능을 확장할 수 있다.
- **균일한 인터페이스(Uniform Interface)**: REST를 다른 네트워크 아키텍처 스타일과 구분 짓는 핵심 특징이며, 4가지 하위 제약으로 다시 나뉜다 — 리소스 식별, 표현을 통한 리소스 조작, 자기서술적 메시지, 그리고 **HATEOAS(Hypermedia As The Engine Of Application State)**[1].

여기서 실무 REST API 구현 대다수가 실제로 지키는 것은 "리소스를 URI로 식별하고 JSON 표현으로 조작한다"까지이고, HATEOAS는 거의 생략된다. Fielding은 2008년 블로그 글에서 이 현실을 직접 비판했다: "engine of application state가 hypertext로 구동되지 않는다면, 그것은 RESTful일 수 없고 REST API도 아니다. 끝."[2] 그는 REST API가 고정된 리소스 이름이나 URI 계층 구조를 클라이언트에 미리 문서화해서는 안 되며, 클라이언트는 서버가 응답에 담아 보내는 링크(하이퍼미디어)를 따라가며 다음 행동을 결정해야 한다고 못박았다[2]. 실제로는 API 문서에 `GET /users/{id}`, `POST /orders` 같은 고정 URI 목록을 명시하는 방식이 업계 표준처럼 자리잡았는데, 이는 Fielding의 정의로는 REST가 아니라 "HTTP 위의 RPC"에 가깝다. 다만 클라이언트-서버 결합을 완전히 끊는 HATEOAS는 구현 복잡도가 높고, 대부분의 사내/파트너 API처럼 클라이언트와 서버를 같은 조직이 함께 버전 관리하는 상황에서는 그 비용 대비 이득이 크지 않다는 실무적 판단이 널리 퍼져 있다 — 이것이 "REST API"라는 이름이 남았지만 원 정의와 멀어진 배경이다.

### HTTP 메서드: 안전(Safe)과 멱등(Idempotent)의 차이

HTTP 시맨틱을 정의하는 IETF RFC 9110은 메서드를 두 가지 축으로 분류한다[3].

**안전한 메서드(Safe Methods)**: "요청 메서드는 그 정의된 시맨틱이 본질적으로 읽기 전용이어서 origin 서버의 상태를 바꾸지 않을 때 '안전(safe)'하다고 간주된다"[3]. GET, HEAD, OPTIONS, TRACE가 안전한 메서드다.

**멱등한 메서드(Idempotent Methods)**: "동일한 메서드로 여러 번 동일한 요청을 반복했을 때 서버에 미치는 의도된 효과가 단 한 번 요청했을 때의 효과와 같다면 그 요청 메서드는 '멱등(idempotent)'하다고 간주된다"[3]. RFC 9110은 이어서 "클라이언트는 멱등한 요청을 의도치 않은 결과를 걱정하지 않고 반복할 수 있지만, 멱등하지 않은 요청은 안전하게 반복할 수 없다"고 명시한다[3]. GET, HEAD, PUT, DELETE, OPTIONS, TRACE는 멱등하고, POST는 멱등하지 않다.

PATCH는 RFC 9110에는 등장하지 않고 별도의 RFC 5789가 정의하는데, 이 문서는 "PATCH는 [RFC2616] 9.1절이 정의한 대로 안전하지도 멱등하지도 않다"고 명시한다[4]. 다만 조건부 요청(ETag 기반 If-Match)을 함께 쓰면 개발자가 PATCH를 멱등하게 설계할 수 있다고 덧붙인다[4]. PUT과 PATCH의 근본적 차이는, "PUT 요청에서 첨부된 엔티티는 origin 서버에 저장된 리소스의 수정된 버전으로 간주되어 클라이언트가 저장된 버전을 그것으로 교체할 것을 요청하는 것"인 반면, "PATCH에서는 첨부된 엔티티가 origin 서버에 현재 존재하는 리소스를 어떻게 수정해서 새 버전을 만들어야 하는지 설명하는 명령어 집합을 담는다"는 데 있다[4] — 즉 PUT은 리소스 전체 교체, PATCH는 부분 수정이다.

이 구분이 왜 실무에서 중요한지 실패 시나리오로 보자. 클라이언트가 결제 생성 요청을 보냈는데 응답을 받기 전에 네트워크 타임아웃이 발생했다고 가정한다.

```http
POST /payments HTTP/1.1
Host: api.example.com
Content-Type: application/json

{"orderId": "ORD-1001", "amount": 50000}
```

이 요청이 서버에는 도달했지만 응답이 유실된 경우, 클라이언트는 "요청이 실패했다"고 판단하고 동일한 POST를 재전송한다. POST는 멱등하지 않으므로 서버가 별도의 중복 방지 로직 없이 각 POST를 새 리소스 생성으로 처리한다면, 결제가 두 번 생성되는 사고로 이어진다. 반면 아래처럼 클라이언트가 리소스 식별자를 직접 지정하는 PUT으로 설계했다면 이야기가 다르다.

```http
PUT /payments/pay-9f2a1c HTTP/1.1
Host: api.example.com
Content-Type: application/json

{"orderId": "ORD-1001", "amount": 50000}
```

`pay-9f2a1c`라는 동일한 리소스 URI로 같은 본문을 여러 번 보내도, 서버는 "이 리소스를 이 상태로 만든다"는 동일한 최종 상태를 반환할 뿐 중복 리소스를 만들지 않는다 — 이것이 RFC 9110이 말하는 멱등성의 실질적 효과다[3]. 실무에서 결제·주문 생성처럼 재시도가 필요한 POST 엔드포인트는 별도의 `Idempotency-Key` 헤더를 클라이언트가 발급하고 서버가 그 키로 중복 요청을 감지하는 패턴을 흔히 쓰는데, 이는 본질적으로 POST에 PUT과 유사한 멱등성을 인위적으로 부여하는 절충안이다.

### 상태 코드: 의미에 맞는 코드를 고르는 기준

RFC 9110은 상태 코드를 5개 클래스(1xx~5xx)로 나누고 각 코드의 시맨틱을 정의한다[3]. 실무에서 자주 혼동되는 코드를 정리하면 다음과 같다.

| 코드 | RFC 9110 정의 | 흔한 오용 사례 |
|---|---|---|
| 200 OK | 요청이 성공했다 | 에러가 발생했는데도 200과 함께 `{"error": "..."}` 본문만 반환 |
| 201 Created | 요청이 성공했고 새 리소스가 생성됐다 | POST로 리소스를 생성하고도 그냥 200 반환 |
| 204 No Content | 요청은 성공했지만 보낼 콘텐츠가 없다 | DELETE 성공 시 불필요하게 빈 본문과 함께 200 반환 |
| 400 Bad Request | 클라이언트 오류로 서버가 요청을 처리할 수 없거나 처리하지 않을 것이다 | 인증 실패에도 400을 씀(401/403이 맞음) |
| 401 Unauthorized | 요청에 유효한 인증 자격 증명이 없다 | 권한은 있지만 리소스 접근이 거부된 경우에도 401 사용(403이 맞음) |
| 404 Not Found | 서버가 요청된 리소스를 찾을 수 없다 | 리소스가 존재하지만 다른 사유로 거부할 때도 404로 숨김(보안상 의도적 사용은 별개 논의) |
| 405 Method Not Allowed | 대상 리소스에 대해 요청 메서드가 지원되지 않는다 | 지원하지 않는 메서드 호출에 400이나 404 반환 |
| 409 Conflict | 요청이 서버의 현재 상태와 충돌한다 | 동시성 충돌(낙관적 락 실패)에 500을 반환 |
| 422 Unprocessable Content | 요청은 문법적으로 올바르지만 의미론적 오류를 담고 있다 | 유효성 검증 실패에 500이나 400을 뭉뚱그려 사용 |
| 500 Internal Server Error | 서버가 예상치 못한 상태를 만났다 | 클라이언트가 고칠 수 있는 오류(잘못된 입력)까지 500으로 반환해 원인을 숨김 |

특히 "200 OK인데 본문에 에러 메시지가 담긴" 패턴은 REST 설계 안티패턴의 대표 사례로 자주 언급된다. HTTP 상태 코드는 그 자체로 클라이언트(브라우저, 프록시, 캐시, 모니터링 도구)가 파싱 없이 바로 판단할 수 있는 신호인데, 이를 무시하고 본문만으로 성패를 판단하게 만들면 캐싱 정책, 재시도 로직, 알림 시스템이 전부 오작동할 수 있다. 이런 API는 HTTP 위에서 동작하지만 HTTP의 시맨틱을 실제로는 쓰지 않는다는 점에서, Fielding이 지적한 "hypertext 없이 REST를 자칭하는" 문제와 본질적으로 같은 종류의 괴리를 보여준다.

### 캐싱과 무상태성의 실무 연결고리

RFC 9111(HTTP Caching)은 GET 응답의 캐시 가능 여부가 `Cache-Control` 헤더로 명시적으로 제어된다고 규정한다[5]. REST의 무상태성 제약(각 요청이 필요한 모든 정보를 담아야 함)과 캐시 가능성 제약은 서로 맞물려 있다 — 서버가 요청 간 상태를 기억하지 않기 때문에, 동일한 요청은 항상 동일한 응답을 만들어낼 잠재력이 있고, 이 성질이 캐싱을 가능하게 한다. 반대로 세션 쿠키나 서버 사이드 상태에 의존하는 "REST API"는 이 이점을 스스로 포기하는 셈이다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: REST는 Roy Fielding이 2000년 박사 논문 5장에서 제안한 아키텍처 스타일이며, 균일한 인터페이스가 REST를 다른 스타일과 구분 짓는 핵심 특징이다. | verified | Fielding 박사 논문(ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm) 5.1.5절 원문 "the central feature that distinguishes the REST architectural style from other network-based styles is its emphasis on a uniform interface between components"을 직접 대조. |
| CLAIM-002: 균일한 인터페이스는 리소스 식별, 표현을 통한 조작, 자기서술적 메시지, HATEOAS 4개 하위 제약으로 구성된다. | verified | 같은 논문 5.2.1절(4가지 인터페이스 제약 나열) 원문 대조. |
| CLAIM-003: Fielding은 2008년 블로그에서 "hypertext로 애플리케이션 상태 전이가 구동되지 않으면 REST API가 아니다"라고 명시했다. | verified | roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven 원문 "if the engine of application state (and hence the API) is not being driven by hypertext, then it cannot be RESTful and cannot be a REST API. Period." 직접 대조. |
| CLAIM-004: RFC 9110은 GET, HEAD, OPTIONS, TRACE를 안전한(safe) 메서드로, GET·HEAD·PUT·DELETE·OPTIONS·TRACE를 멱등한 메서드로, POST를 멱등하지 않은 메서드로 분류한다. | verified | rfc-editor.org/rfc/rfc9110.html 9.2.1절·9.2.2절 원문("essentially read-only", "the intended effect... is the same as the effect for a single such request") 및 각 메서드 절(9.3.x) 대조. |
| CLAIM-005: PATCH는 RFC 9110에 정의되지 않고 RFC 5789가 별도로 정의하며, RFC 5789는 PATCH가 안전하지도 멱등하지도 않다고 명시한다. | verified | rfc-editor.org/rfc/rfc5789.html 2절 원문 "PATCH is neither safe nor idempotent as defined by [RFC2616], Section 9.1." 직접 대조. RFC 9110 본문에는 PATCH 항목이 없음을 확인. |
| CLAIM-006: PUT은 리소스 전체를 교체하고 PATCH는 부분 수정 명령을 전달한다는 차이가 RFC 5789에 명시되어 있다. | verified | rfc-editor.org/rfc/rfc5789.html 1~2절 원문("the enclosed entity is considered to be a modified version of the resource" vs "a set of instructions describing how a resource... should be modified") 직접 대조. |
| CLAIM-007: MDN도 GET/HEAD/OPTIONS/TRACE를 Safe·Idempotent로, PUT/DELETE를 Idempotent(Not Safe)로, POST/PATCH를 Not Safe·Not Idempotent로 분류한다. | verified | developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods 메서드 요약 표 직접 대조. |
| CLAIM-008: RFC 9110은 200/201/204/400/401/403/404/405/409/422/500 상태 코드의 시맨틱을 정의한다. | verified | rfc-editor.org/rfc/rfc9110.html 15.3.x·15.5.x·15.6.x 절 각 코드 정의 문구 대조. |

## 작성자의 견해

<!-- 최소 100단어. 게이트는 이 섹션에 의견/해석임을 밝히는 '>' 인용구 줄이 있는지만 구조적으로
확인한다(문구 자체는 "의견/견해/해석/사견" 중 한 단어만 포함하면 됨) — 아래 문장은 예시일 뿐, 47개
발행 글이 전부 토씨 하나 같은 문장을 반복하는 걸 피하기 위해 매번 자기 말로 다르게 쓸 것
(wiki/Blog_Writing_Rules.md 14/15번 수칙). 빈 '>' 뒤에 평문으로 쓰면 실패한다. -->

> 이 섹션은 사실을 나열하는 것이 아니라 자료를 조사하며 필자가 형성한 사견을 담고 있습니다.

개인적으로는 "REST API"라는 용어가 이미 원래 정의에서 너무 멀리 떠내려가 버렸다고 생각한다. Fielding이 요구한 HATEOAS를 실제로 구현하는 공개 API는 극소수이고, 대부분은 고정 URI 문서를 배포하고 클라이언트가 그것을 코드에 하드코딩하는 방식으로 동작한다. 이것이 잘못됐다고 보진 않는다 — 클라이언트-서버를 같은 팀이 관리하는 사내 API에서 HATEOAS의 런타임 링크 탐색 비용은 실익보다 개발 복잡도만 키우는 경우가 많다. 다만 "우리는 REST를 안 지키지만 그래도 잘 동작한다"는 인식과 "우리는 REST API를 만들고 있다"는 착각은 구분해야 한다고 본다. 이 차이를 흐리는 게 문제라고 느끼는 지점은, 팀이 REST라는 이름값에 기대어 왜 HTTP 메서드 의미(멱등성 등)를 무시해도 되는지에 대한 판단을 건너뛰는 경우다. 안전성·멱등성은 HATEOAS와 달리 구현 비용이 거의 들지 않으면서도 재시도·캐싱·장애 복구에 실질적 이득을 주므로, 이름표와 무관하게 반드시 지켜야 한다는 게 필자의 결론이다.

## 한계와 반론

<!-- 최소 80단어. -->

이 글이 제시한 "HATEOAS 없는 REST는 REST가 아니다"라는 Fielding의 입장에 모든 실무자가 동의하는 것은 아니다. Richardson Maturity Model처럼 REST를 단계적 스펙트럼(레벨 0~3)으로 보는 관점에서는, HTTP 메서드와 상태 코드를 의미에 맞게 쓰는 것만으로도(레벨 2) 충분히 실용적인 가치가 있다고 본다 — 이 글도 그 실용적 절충을 부정하지 않는다. 또한 결제 사례에서 제시한 `Idempotency-Key` 패턴은 업계에서 널리 쓰이지만 RFC 9110이 규정한 표준 메커니즘은 아니며, 구현은 벤더마다 다르다. PATCH의 멱등성을 ETag 조건부 요청으로 확보하는 방법도 RFC 5789가 가능성만 언급할 뿐 구체적 절차를 강제하지 않으므로, 실제 적용 시 API마다 별도 설계가 필요하다는 한계가 있다.

## 참고문헌

1. Roy T. Fielding, "Architectural Styles and the Design of Network-based Software Architectures" (Ch. 5, REST), UC Irvine, 2000. https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm (확인일: 2026-08-26)
2. Roy T. Fielding, "REST APIs must be hypertext-driven", Untangled (개인 블로그, Fielding 본인 작성), 2008. https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven (확인일: 2026-08-26)
3. IETF RFC 9110, "HTTP Semantics", 2022. https://www.rfc-editor.org/rfc/rfc9110.html (확인일: 2026-08-26)
4. IETF RFC 5789, "PATCH Method for HTTP", 2010. https://www.rfc-editor.org/rfc/rfc5789.html (확인일: 2026-08-26)
5. IETF RFC 9111, "HTTP Caching", 2022. https://www.rfc-editor.org/rfc/rfc9111.html (확인일: 2026-08-26)
6. MDN Web Docs, "HTTP request methods". https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods (확인일: 2026-08-26)

## 종합적 의견

<!-- 최소 100단어. 이 섹션도 '작성자의 견해'와 마찬가지로 '>' 인용구에 "의견/견해/해석/사견" 중
한 단어를 담아야 게이트를 통과한다 — 아래 문장은 예시일 뿐 매번 자기 말로 다르게 쓸 것. -->

> 아래 내용은 전체 자료를 종합해 필자가 내린 해석이며, 절대적 정답이 아니라 하나의 견해로 읽어주시기 바랍니다.

REST API 설계를 처음 배울 때 흔히 "GET/POST/PUT/DELETE = 조회/생성/수정/삭제"라는 4줄 표로 끝내는 경우가 많은데, 이 글에서 다룬 안전성·멱등성 구분과 상태 코드 시맨틱은 그 표 뒤에 숨어 있는 실제 계약(contract)이다. 클라이언트가 네트워크 오류로 요청을 재전송할 때 서버가 어떤 메서드에서 안전하게 재시도를 허용해도 되는지는 RFC가 이미 답을 정해뒀고, 이를 어기면 결제 중복 생성 같은 구체적 장애로 이어진다. 동시에 HATEOAS라는 Fielding 원안의 핵심 제약이 실무에서 거의 사라진 현실은, "표준을 안 지켜서 틀렸다"기보다 REST라는 이름이 실용적 절충안들의 집합으로 재정의되어 온 과정으로 보는 편이 더 생산적이라고 판단한다. 결국 중요한 것은 이름표가 아니라, 메서드와 상태 코드가 클라이언트에게 보내는 신호를 설계자가 의도한 대로 정확히 지키는 일이다.

## 꼬리질문

- gRPC나 GraphQL처럼 HTTP 메서드/상태 코드 시맨틱에 덜 의존하는 API 스타일로 전환할 때, REST에서 이미 확보했던 멱등성·캐싱 이점을 어떻게 대체할 수 있을까?
- `Idempotency-Key` 헤더 패턴을 표준화하려는 IETF 초안(예: HTTP Idempotency-Key Header Field)이 실제로 RFC로 채택되면, POST의 멱등성 처리 방식이 어떻게 바뀔까?

## 백링크

- [HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리](https://beji-tech.blogspot.com/2026/08/http11-vs-http2-vs-http3.html)
- [MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리](https://beji-tech.blogspot.com/2026/08/mvc-mvc-msa.html)
- [gRPC와 Protocol Buffers: HTTP/2 기반 스트리밍과 직렬화 원리](https://beji-tech.blogspot.com/2026/08/grpc-protocol-buffers-http2.html)