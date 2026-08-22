---
author: ''
createdAt: '2026-08-22T11:03:02.808339Z'
factCheckScore: 1.0
id: '8685306171021339018'
notionPageId: null
publishedAt: '2026-08-22T05:11:23-07:00'
slug: tls-ssl-handshake-https-certificate-verification
status: published
tags:
- Basics
- TLS
- Network
- Security
title: TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가
updatedAt: '2026-08-22T11:03:02.808339Z'
url: https://beji-tech.blogspot.com/2026/08/tlsssl-handshake-https-tls-13-1-rtt.html
---

# TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가

## 요약

브라우저 주소창에 자물쇠 아이콘이 뜨기까지, TCP 연결 위에서는 TLS(Transport Layer Security) 핸드셰이크가 먼저 끝나야 한다. 이 글은 TLS 1.2와 TLS 1.3의 핸드셰이크 메시지 흐름을 실제 `openssl s_client`로 직접 캡처한 트레이스로 비교하고, HTTPS 인증서 체인이 왜 신뢰되는지(SAN 검증, 루트 CA 체인), 그리고 TLS 1.3의 0-RTT 모드가 왜 재전송(replay) 위험을 안고 있는지를 RFC 원문 근거와 함께 정리한다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
-->

대부분의 "TLS 핸드셰이크 정리" 글은 RFC 다이어그램을 그대로 옮기거나 교과서적 순서만 나열한다. 이 글은 `openssl s_client -msg -state`로 `www.google.com:443`에 TLS 1.2와 TLS 1.3 양쪽으로 실제 접속해 캡처한 원시 메시지 트레이스를 그대로 제시하고, TLS 1.2는 ServerHello/Certificate/ServerKeyExchange/ServerHelloDone이 별도 플라이트로 분리되는 반면 TLS 1.3은 이들이 서버 측 단일 플라이트로 합쳐지는 것을 바이트 단위 로그로 직접 보여준다. 또한 이 캡처 과정에서 예상 밖의 사실을 하나 발견했다: 2026년 8월 시점 `www.google.com`은 TLS 1.3 키 교환 그룹으로 순수 X25519가 아니라 `X25519MLKEM768`라는 포스트 퀀텀 하이브리드 그룹을 기본 협상하고 있었다 — 대부분의 "TLS 기초" 글이 다루지 않는, 실전에서 이미 진행 중인 변화다. 인증서 체인도 실제 `-showcerts` 출력의 `depth=0/1/2`를 근거로 leaf-intermediate-root 구조를 설명한다.

## 본문

![TLS 핸드셰이크 — 클라이언트와 서버가 세션 키를 합의하고 서로를 인증하는 과정](file:///d:/coding-project/2026-project/ai-blogging/content/images/tls_handshake_thumbnail.svg)

### TLS가 해결하는 세 가지 문제

TLS는 전송 계층(TCP) 위에서 세 가지를 보장한다.

1. **기밀성(Confidentiality)**: 세션 키로 대칭 암호화해 도청을 막는다.
2. **무결성(Integrity)**: AEAD(Authenticated Encryption with Associated Data)로 변조를 탐지한다.
3. **인증(Authentication)**: 인증서 기반으로 접속 대상 서버(선택적으로 클라이언트)의 신원을 확인한다.

이 세 가지를 확보하기 위해 클라이언트와 서버는 실제 데이터를 주고받기 전에 "핸드셰이크"로 세션 키를 합의하고 서로를 인증한다. 문제는 이 핸드셰이크 자체가 왕복(RTT)마다 지연을 더한다는 점이고, TLS 1.2와 TLS 1.3의 가장 큰 차이가 바로 이 왕복 횟수다.

### TLS 1.2 풀 핸드셰이크 — 2-RTT

TLS 1.2(RFC 5246, RFC 8446로 대체됨)의 전체 핸드셰이크는 아래처럼 진행된다.

```
Client                                               Server

ClientHello                  -------->
                                                 ServerHello
                                                Certificate
                                          ServerKeyExchange
                              <--------      ServerHelloDone
ClientKeyExchange
ChangeCipherSpec
Finished                     -------->
                                          ChangeCipherSpec
                              <--------             Finished
Application Data              <------->      Application Data
```

실제로 `www.google.com:443`에 TLS 1.2로 접속해 `-msg -state` 옵션으로 캡처한 메시지 순서는 다음과 같다(직접 실행, 2026-08-22).

```text
>>> TLS 1.2, Handshake, ClientHello
<<< TLS 1.2, Handshake, ServerHello
<<< TLS 1.2, Handshake, Certificate
<<< TLS 1.2, Handshake, ServerKeyExchange
<<< TLS 1.2, Handshake, ServerHelloDone
>>> TLS 1.2, Handshake, ClientKeyExchange
>>> TLS 1.2, ChangeCipherSpec
>>> TLS 1.2, Handshake, Finished
<<< TLS 1.2, Handshake, NewSessionTicket
```

서버는 `Certificate`와 `ServerKeyExchange`(ECDHE 키 교환용 임시 공개키)를 별도 메시지로 보내고, 클라이언트가 이를 다 받은 뒤에야 `ClientKeyExchange`를 보낼 수 있다. 즉 클라이언트→서버→클라이언트→서버로 왕복이 두 번 필요해 "2-RTT"라고 부른다.

### TLS 1.3 풀 핸드셰이크 — 1-RTT

TLS 1.3(RFC 8446)은 클라이언트가 `ClientHello`에 이미 키 교환에 필요한 `key_share`(공개키)를 실어 보내는 방식으로 왕복을 줄였다. 서버가 클라이언트의 키 교환 그룹을 수용할 수 있으면, `ServerHello` 이후의 나머지 메시지(`EncryptedExtensions`, `Certificate`, `CertificateVerify`, `Finished`)를 한 플라이트로 묶어 응답한다. RFC 8446 §2는 이 기본 흐름을 다음처럼 표기한다.

```
       ClientHello
       + key_share             -------->
                                                  ServerHello
                                                  + key_share
                                        {EncryptedExtensions}
                                        {Certificate}
                                        {CertificateVerify}
                                        {Finished}
                                <--------
       {Finished}               -------->
       [Application Data]       <------->      [Application Data]
```

같은 서버(`www.google.com:443`)에 TLS 1.3으로 접속해 캡처한 실제 트레이스는 다음과 같다.

```text
>>> TLS 1.3, Handshake, ClientHello
<<< TLS 1.3, Handshake, ServerHello
<<< TLS 1.3, ChangeCipherSpec
<<< TLS 1.3, Handshake, EncryptedExtensions
<<< TLS 1.3, Handshake, Certificate
<<< TLS 1.3, Handshake, CertificateVerify
<<< TLS 1.3, Handshake, Finished
>>> TLS 1.3, ChangeCipherSpec
>>> TLS 1.3, Handshake, Finished
```

TLS 1.2 트레이스와 나란히 보면, TLS 1.2에서 별도 메시지였던 `ServerKeyExchange`/`ServerHelloDone`이 TLS 1.3에서는 아예 사라지고(키 교환 정보는 이미 `ServerHello`의 `key_share`에 포함됨), `Certificate` 다음에 `ServerKeyExchange` 없이 곧바로 `CertificateVerify`(서버가 자신의 개인키로 지금까지의 핸드셰이크 트랜스크립트에 서명한 것)가 온다. `ChangeCipherSpec`은 TLS 1.3 자체에는 없는 개념이지만, 중간 방화벽/프록시가 TLS 1.2 트래픽으로 오인해 차단하는 것을 막기 위한 호환성용 더미 레코드로 여전히 전송된다. 이 세션에서 협상된 알고리즘도 함께 확인했다.

![TLS 1.2(2-RTT)와 TLS 1.3(1-RTT) 핸드셰이크 왕복 횟수 비교 — 위 실제 트레이스를 단순화한 다이어그램](file:///d:/coding-project/2026-project/ai-blogging/content/images/tls12-vs-tls13-handshake-rtt.svg)

```text
$ openssl s_client -connect www.google.com:443 -tls1_3 -brief
Protocol version: TLSv1.3
Ciphersuite: TLS_AES_256_GCM_SHA384
Negotiated TLS1.3 group: X25519MLKEM768
```

`X25519MLKEM768`은 고전 타원곡선 X25519와 NIST가 표준화한 격자 기반 포스트 퀀텀 KEM인 ML-KEM-768을 결합한 하이브리드 그룹이다. 같은 서버를 TLS 1.2로 접속하면 `Peer Temp Key: X25519, 253 bits`로 순수 고전 곡선만 협상된다 — TLS 1.3 쪽에만 하이브리드 그룹이 붙는 것은, "미래에 양자컴퓨터가 지금 가로챈 트래픽을 나중에 복호화하는" 저장 후 복호화(harvest-now-decrypt-later) 위협에 대비해 최신 클라이언트/서버가 TLS 1.3 확장으로 점진적으로 도입 중인 실전 변화다.

### 인증서 체인은 왜 신뢰되는가

핸드셰이크의 `Certificate` 메시지에는 서버 인증서 하나만 오는 게 아니라 체인이 통째로 온다. 같은 세션을 `-showcerts`로 열어보면 다음과 같은 검증 경로가 나온다.

```text
depth=2 C=US, O=Google Trust Services LLC, CN=GTS Root R4
verify return:1
depth=1 C=US, O=Google Trust Services, CN=WE2
verify return:1
depth=0 CN=www.google.com
verify return:1
```

즉 `www.google.com`(leaf, depth 0) 인증서는 `WE2`(intermediate CA, depth 1)가 서명했고, `WE2`는 `GTS Root R4`(root CA, depth 2)가 서명했다. 클라이언트(브라우저/OS)는 미리 설치된 신뢰 저장소(trust store)에 `GTS Root R4`가 이미 들어있기 때문에, 이 서명 체인을 역으로 타고 올라가 신뢰를 전이(transitive trust)시킨다. 여기서 흔히 오해하는 지점이 있는데, 체인 서명이 유효하다고 해서 "이 인증서가 이 도메인의 것"이 자동으로 증명되지는 않는다. 별도로 호스트명 검증이 필요하다.

RFC 6125는 클라이언트가 호스트명을 검증할 때 인증서 subject의 CN(Common Name)이 아니라 `subjectAlternativeName`(SAN) 확장의 `dNSName` 항목을 우선 확인하도록 규정한다. SAN에 유효한 DNS 식별자가 하나라도 있으면 클라이언트는 CN 매칭을 아예 시도하지 말아야 한다("A client MUST NOT seek a match for a reference identifier of CN-ID if the presented identifiers include a DNS-ID..."). 즉 CN은 SAN이 전혀 없을 때만 쓰는 폴백일 뿐이며, 현대 CA는 SAN 없는 인증서를 사실상 발급하지 않는다.

### 0-RTT의 대가: 재전송 위험

TLS 1.3은 이전에 접속한 적이 있는 서버라면 `PSK`(Pre-Shared Key, 세션 재개 티켓)를 이용해 왕복 없이(0-RTT) 첫 애플리케이션 데이터를 바로 보낼 수도 있다. 하지만 이 속도는 공짜가 아니다. RFC 8446 §2.3은 명확히 경고한다: "There are no guarantees of non-replay between connections... 0-RTT data does not depend on the ServerHello and therefore has weaker guarantees[재전송 방지에 대한 보장이 없다... 0-RTT 데이터는 ServerHello에 의존하지 않으므로 더 약한 보증만 가진다]." 즉 공격자가 같은 0-RTT ClientHello + 초기 데이터를 네트워크에서 그대로 캡처해 재전송하면, 서버가 이를 구분하지 못하고 같은 요청을 두 번 처리할 수 있다. 이 때문에 0-RTT로 보내는 요청은 반드시 멱등(idempotent)해야 하며(예: 결제 요청 같은 비멱등 작업 금지), RFC 8446 §8은 서버가 재전송 위험을 줄이는 보조 메커니즘(single-use 티켓 등)을 함께 설명한다.

### 레거시 TLS 버전은 왜 금지됐나

`TLS 1.0`(1999)과 `TLS 1.1`(2006)은 알려진 암호학적 약점(BEAST, POODLE 등과 연관된 CBC 모드 취약점) 때문에 RFC 8996(2021)으로 공식 폐지(deprecated)됐다. RFC 8996은 "TLS 1.0 MUST NOT be used... Negotiation of TLS 1.0 from any version of TLS MUST NOT be permitted[TLS 1.0을 사용해서는 안 되며, 어떤 버전에서도 TLS 1.0으로의 협상이 허용되어서는 안 된다]"라고 강제성 있게 못박는다. TLS 1.1도 동일한 문구로 금지된다. 실무에서 서버 설정에 `TLSv1`, `TLSv1.1`을 명시적으로 비활성화해야 하는 근거가 바로 이 RFC다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-1: TLS 1.3의 전체(풀) 핸드셰이크는 1-RTT로 완료되며, 이는 TLS 1.2의 2-RTT 대비 왕복이 절반으로 줄어든 것이다 | verified | RFC 8446(rfc-editor.org) §2 원문의 메시지 흐름도(ClientHello+key_share → ServerHello+key_share/EncryptedExtensions/Certificate/CertificateVerify/Finished) 직접 대조 + `openssl s_client -msg -state`로 www.google.com에 TLS 1.2/1.3 각각 접속해 캡처한 실제 메시지 순서(2026-08-22) |
| CLAIM-2: TLS 1.3의 0-RTT(조기 데이터)는 재전송(replay) 공격에 대한 방어 보장이 TLS 1.3 1-RTT 데이터보다 약하다 | verified | RFC 8446 §2.3 원문("0-RTT data does not depend on the ServerHello and therefore has weaker guarantees") 직접 대조 |
| CLAIM-3: RFC 8996은 TLS 1.0과 TLS 1.1을 공식 폐지하고 어떤 버전으로부터도 이 두 버전으로의 협상을 금지(MUST NOT)한다 | verified | RFC 8996(rfc-editor.org) Abstract 및 본문의 "TLS 1.0 MUST NOT be used" / "TLS 1.1 MUST NOT be used" 문구 직접 대조 |
| CLAIM-4: 호스트명 검증 시 클라이언트는 인증서의 SAN(subjectAlternativeName) 중 DNS 식별자를 우선 확인해야 하며, SAN에 DNS 식별자가 있으면 CN(Common Name) 매칭은 시도하지 않아야 한다 | verified | RFC 6125(rfc-editor.org) §6.4.4 원문("A client MUST NOT seek a match for a reference identifier of CN-ID if the presented identifiers include a DNS-ID...") 직접 대조 |
| CLAIM-5: 2026-08-22 시점 www.google.com은 TLS 1.3 접속 시 순수 X25519가 아니라 포스트 퀀텀 하이브리드 그룹인 X25519MLKEM768을 기본 협상한다 | verified | `openssl s_client -connect www.google.com:443 -tls1_3 -brief` 직접 실행 결과("Negotiated TLS1.3 group: X25519MLKEM768") — 서버 설정은 시점에 따라 바뀔 수 있어 이후 재현 결과가 다를 수 있음을 "한계와 반론"에서 별도로 밝힘 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 견해를 담고 있습니다.

TLS 1.3의 1-RTT 단축을 다룬 글은 많지만, 실제로 메시지 트레이스를 캡처해서 "무엇이 사라졌는지"를 눈으로 보여주는 글은 드물다고 생각한다. RFC의 순서도만 보면 추상적으로 느껴지지만, `ServerKeyExchange`와 `ServerHelloDone`이라는 두 메시지가 통째로 없어졌다는 걸 실제 로그로 확인하면 왜 1-RTT가 되는지가 훨씬 직관적으로 이해된다. 개인적으로 더 흥미로웠던 발견은 X25519MLKEM768이었다. "TLS 1.3 기초"라는 주제로 검색하면 대부분 2018년 RFC 8446 발표 당시 기준의 설명에서 멈추는데, 실제로 대형 서비스가 이미 포스트 퀀텀 하이브리드 키 교환을 기본값으로 굴리고 있다는 사실은 이 주제가 "완결된 기초 지식"이 아니라 지금도 계속 움직이는 영역이라는 걸 보여준다. 이런 실전 스냅샷은 시간이 지나면 값이 바뀔 수 있다는 한계가 있지만, 그럼에도 "지금 이 순간 실제로 무슨 일이 일어나는지"를 확인하는 습관 자체가 스펙만 읽는 것보다 얻는 게 많다는 게 내 해석이다.

## 한계와 반론

이 글의 실습 결과는 2026-08-22 시점, `www.google.com` 한 서버, 특정 OpenSSL 3.5.7 클라이언트 조합에서만 확인한 것이다. 협상되는 그룹/암호군은 서버 설정과 클라이언트 라이브러리 버전에 따라 달라지므로, 다른 서버나 다른 시점에 같은 명령을 실행하면 `X25519MLKEM768` 대신 순수 `X25519`나 다른 그룹이 나올 수 있다. 또한 이 글은 "풀 핸드셰이크(전체 협상)" 경로만 다뤘고, TLS 1.3의 세션 재개(resumption)나 0-RTT 자체의 실제 왕복 절감 효과는 별도로 측정하지 않았다. 0-RTT의 재전송 위험도 RFC 원문 근거는 확인했지만, 실제 공격 시나리오를 재현하지는 않았으므로 이론적 근거 확인에 그친다는 한계가 있다. 반론이 있을 수 있는 지점은 "TLS 1.3이 항상 더 빠르다"는 단순화인데, 실제로는 미들박스(방화벽/프록시)가 TLS 1.3을 오인식해 폴백이 발생하거나 세션 재개가 실패하는 환경도 존재해, 왕복 수 감소가 체감 지연 감소로 항상 1:1 대응하지는 않는다.

## 참고문헌

1. IETF, "RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3" (확인일: 2026-08-22) — https://www.rfc-editor.org/rfc/rfc8446
2. IETF, "RFC 6125: Representation and Verification of Domain-Based Application Service Identity within Internet PKI Certificates" (확인일: 2026-08-22) — https://www.rfc-editor.org/rfc/rfc6125
3. IETF, "RFC 8996: Deprecating TLS 1.0 and TLS 1.1" (확인일: 2026-08-22) — https://www.rfc-editor.org/rfc/rfc8996

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

TLS 핸드셰이크는 "암호학"이라는 무거운 주제로 소개되는 경우가 많지만, 실제로는 왕복 횟수를 줄이기 위한 프로토콜 설계 최적화의 역사이기도 하다. TLS 1.2에서 1.3으로의 변화는 단순히 "더 안전해졌다"가 아니라 "키 교환에 필요한 정보를 첫 메시지에 최대한 미리 실어 보내는" 구조적 재설계에 가깝고, 이 관점으로 보면 QUIC/HTTP3가 다시 한번 같은 방향(연결 설정 지연 최소화)으로 나아가는 흐름과도 자연스럽게 연결된다. 인증서 체인 검증 역시 "서명이 유효한가"와 "이 서버가 맞는가"라는 서로 다른 두 질문(신뢰 체인 vs 호스트명 검증)을 분리해서 봐야 헷갈리지 않는다는 게 이 글을 쓰며 다시 확인한 지점이다. 0-RTT처럼 성능과 안전성이 정면으로 트레이드오프되는 기능은, 스펙이 "가능하다"고 말하는 것과 "항상 써도 안전하다"고 말하는 것이 다르다는 걸 애플리케이션 설계자가 직접 인지하고 있어야 한다고 본다.

## 꼬리질문

- TLS 1.3 세션 재개(PSK resumption)와 0-RTT의 실제 왕복/지연 절감 효과를 벤치마크로 직접 측정하면 얼마나 차이가 날까?
- 포스트 퀀텀 하이브리드 키 교환(X25519MLKEM768 등)이 주요 CDN/클라우드 제공자 사이에서 얼마나 넓게 기본값으로 채택돼 있는가?
- OCSP Stapling과 CRL, 최신 브라우저의 CT(Certificate Transparency) 검증이 실제 핸드셰이크 지연에 어떤 영향을 주는가?

## 백링크

- [TCP 3-Way/4-Way Handshake와 TIME_WAIT — 실제로 소켓을 열고 닫아 눈으로 확인하기](https://beji-tech.blogspot.com/2026/08/tcp-3-way4-way-handshake-timewait.html)
- [HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리](https://beji-tech.blogspot.com/2026/08/http11-vs-http2-vs-http3.html)
- [TCP 기반 애플리케이션 계층 통신 원리 — 이메일(IMAP/POP3) 프로토콜이 TCP 위에서 동작하는 방식](https://beji-tech.blogspot.com/2026/08/tcp-imappop3-tcp.html)