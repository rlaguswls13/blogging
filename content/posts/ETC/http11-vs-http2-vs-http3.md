---
id: '2154819577472731345'
publishedAt: '2026-08-11T09:54:14.052-07:00'
slug: http11-vs-http2-vs-http3
status: published
tags:
- HTTP
- HTTP2
- HTTP3
- Network
- QUIC
- WebPerformance
- ETC
title: 'HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리'
updatedAt: '2026-08-13T21:02:31.971-07:00'
url: https://beji-tech.blogspot.com/2026/08/http11-vs-http2-vs-http3.html
---

# HTTP/1.1 vs HTTP/2 vs HTTP/3: 프로토콜 발전사로 보는 웹 성능 최적화 원리

## 요약

현대 웹 트래픽 환경에서 웹 성능 최적화는 단순히 자바스크립트 코드나 이미지 용량을 줄이는 것에 그치지 않고, 네트워크 전송 계층 프로토콜의 발전 과정과 밀접하게 연계되어 있습니다. 본 아티클에서는 HTTP/1.1의 텍스트 기반 구조 및 애플리케이션 레벨의 Head-of-Line(HOL) Blocking 병목에서부터, HTTP/2의 바이너리 프레이밍 계층과 다중화(Multiplexing)를 통한 단일 TCP 연결 혁신, 그리고 HTTP/3가 UDP 기반 QUIC 프로토콜을 도입하여 TCP 수준의 HOL Blocking을 근본적으로 해결하고 0-RTT 연결 및 Connection Migration을 성취한 원리를 체계적으로 다룹니다.

## 본문

### 1. 서론: HTTP 프로토콜의 진화 배경과 웹 성능 최적화의 필요성

웹 애플리케이션이 발전함에 따라 웹 페이지를 구성하는 자원의 개수와 용량은 급격히 증가했습니다. 초기 웹이 단일 HTML 문서와 몇 개의 텍스트 자원을 주고받던 시절과 달리, 현대의 웹은 수십 개에서 수백 개에 달하는 CSS, JavaScript, 미디어 파일을 동시에 다운로드해야 합니다[1][2].

이러한 환경에서 네트워크 왕복 시간(Round-Trip Time, RTT)과 패킷 손실, 그리고 연결 수립 오버헤드는 사용자 체감 성능(Largest Contentful Paint 등 Core Web Vitals)에 결정적인 영향을 미치게 됩니다. HTTP 프로토콜은 기본 메시지 시맨틱(URI, HTTP Method, Status Code, Header)을 유지하면서도, 전송 계층의 병목을 해결하기 위해 HTTP/1.1, HTTP/2, 그리고 HTTP/3로 끊임없이 진화해 왔습니다[1].

### 2. HTTP/1.1의 동작 원리와 성능 병목 요인 (HOL Blocking, Connection Overhead)

HTTP/1.1은 1999년 RFC 2616 표준으로 제정되며 수십 년간 웹의 표준 프로토콜로 자리 잡았습니다. HTTP/1.1은 기존 HTTP/1.0의 단발성 연결 문제를 개선하기 위해 Persistent Connection(Keep-Alive)을 도입하여 하나의 TCP 연결에서 여러 요청을 재사용할 수 있도록 지원했습니다[1][2].

그러나 HTTP/1.1은 텍스트 기반 메시지 형식을 채택하고 있었으며, 요청과 응답이 반드시 순차적으로 처리되어야 하는 직렬 전송 제약을 가지고 있었습니다.

HTTP/1.1은 텍스트 기반 프로토콜로서 Persistent Connection을 지원하지만, 단일 TCP 연결 내 요청/응답의 직렬 처리 구조로 인해 이전 요청의 처리가 지연되면 후속 요청들이 모두 대기해야 하는 애플리케이션 레벨의 Head-of-Line(HOL) Blocking 병목을 야기합니다[1][2].

이러한 HOL Blocking 병목으로 인해 웹 브라우저가 다수의 리소스를 다운로드할 때 심각한 지연이 발생했습니다.

HTTP/1.1 시대의 웹 개발자들은 HOL Blocking을 회피하고 자원 다운로드를 병렬화하기 위해 브라우저가 동일 도메인당 최대 6개의 TCP 연결만을 허용하는 제약을 우회하는 Domain Sharding 기법과, 여러 이미지를 하나의 큰 이미지 파일로 합쳐 요청 수 자체를 줄이는 Image Sprites, JS/CSS Inline 번들링 등의 획기적인 웹 최적화 기법을 사용했습니다[2][6].

그러나 Domain Sharding은 새로운 TCP Handshake 및 TLS Handshake 오버헤드를 유발하여 서버와 네트워크 자원을 과도하게 소비하는 한계를 보였습니다.

### 3. HTTP/2의 혁신: 바이너리 프레이밍과 다중화(Multiplexing)

2015년 제정된 HTTP/2(RFC 7540)는 HTTP/1.1의 애플리케이션 레벨 HOL Blocking과 헤더 오버헤드를 획기적으로 개선한 바이너리 기반 프로토콜입니다[3].

HTTP/2는 기존의 텍스트 기반 메시지 구조 대신 바이너리 프레이밍 계층(Binary Framing Layer)을 도입하여, 요청과 응답 데이터를 독립적인 프레임(Frame) 단위로 분할하고 단일 TCP 연결 상에서 여러 스트림(Stream)을 동시 교차 전송하는 다중화(Multiplexing)를 지원합니다[3].

이를 통해 HTTP/1.1의 애플리케이션 레벨 HOL Blocking이 해결되었으며, 단 하나의 TCP 연결만으로 수백 개의 웹 자원을 병렬로 빠르게 주고받을 수 있게 되었습니다. 또한 텍스트 헤더의 중복 문제를 극복하기 위한 압축 기술이 도입되었습니다.

HTTP/2는 HPACK 압축 알고리즘을 도입하여 허프만 코딩(Huffman Coding)과 정적/동적 테이블(Static/Dynamic Table)을 활용해 이전 요청과의 중복 헤더를 효율적으로 압축함으로써 네트워크 전송 오버헤드를 대폭 줄였습니다[3].

그러나 HTTP/2에도 근본적인 한계가 존재했습니다.

HTTP/2는 애플리케이션 레벨의 HOL Blocking을 해결하였으나, 전송 계층 프로토콜이 여전히 TCP 기반이므로 패킷 손실(Packet Loss)이 발생할 경우 TCP의 신뢰성 보장 메커니즘(순서 보장)에 의해 손실된 패킷이 재전송될 때까지 해당 TCP 연결에 속한 모든 스트림의 데이터 처리가 정지되는 TCP 수준의 HOL Blocking 문제가 남아있습니다[3][6].

### 4. HTTP/3와 QUIC: UDP 기반 프로토콜 전환 및 연결 수립 최적화

HTTP/2의 TCP 레벨 HOL Blocking 한계를 극복하기 위해 2022년 RFC 9114로 제정된 HTTP/3는 전송 계층의 거대한 패러다임 전환을 이뤄냈습니다[4][5].

HTTP/3는 전송 계층 프로토콜을 기존의 TCP에서 UDP 기반으로 설계된 QUIC(Quick UDP Internet Connections, RFC 9000) 프로토콜로 완전히 전환함으로써, 스트림별 독립적 흐름 제어 및 손실 복구를 실현하고 전송 계층 수준의 HOL Blocking을 근본적으로 제거했습니다[4][5].

QUIC 프로토콜은 전송 계층 내부에 TLS 1.3 암호화를 기본으로 통합하였습니다.

HTTP/3에 적용된 QUIC 프로토콜은 전송 계층 핸드셰이크와 TLS 1.3 암호화 핸드셰이크를 결합하여 최초 연결 시 1-RTT만에 연결을 완결하며, 기존 세션 재연결 시 0-RTT Connection Resumption을 지원합니다[5].

또한 모바일 사용자 환경에서의 네트워크 전환에 대한 획기적인 해결책을 제시합니다.

QUIC은 IP 주소와 포트 번호의 조합 대신 unique한 Connection ID를 기반으로 식별하기 때문에, 사용자가 이동 중에 Wi-Fi에서 5G 셀룰러 망으로 전환되는 등 IP가 변경되어도 재연결 오버헤드 없이 세션을 끊김 없이 유지하는 Connection Migration 기능을 제공합니다[5].

### 5. 프로토콜별 성능 비교 및 웹 성능 최적화 실전 적용 전략

프로토콜의 발전은 웹 애플리케이션 개발자와 인프라 엔지니어의 최적화 모범 사례(Best Practice)를 완전히 재정의하였습니다.

Cloudflare의 글로벌 네트워크 벤치마크 리포트에 따르면, 2% 이상의 패킷 손실률이 발생하는 열악한 모바일 네트워크 환경에서 HTTP/3는 HTTP/2 대비 렌더링 시작 시간(Page Load Time)을 최대 40% 이상 단축시키는 탁월한 성능 개선을 보여줍니다[6].

웹 최적화 관점에서의 주요 변화는 다음과 같습니다:

- **번들링 및 도메인 샤딩 전략의 변화**: HTTP/1.1 시대 필수적이었던 Domain Sharding과 대형 번들링(Big Bundling)은 HTTP/2 및 HTTP/3 환경에서는 오히려 캐시 효율을 저하시키는 반패턴(Anti-pattern)이 되었습니다. 최신 환경에서는 Fine-grained Code Splitting 및 ES Modules 분할 배포가 권장됩니다[2][3].

- **점진적 프로토콜 협상 (Alt-Svc)**: 클라이언트는 서버가 HTTP 응답에 포함시켜 전송하는 `Alt-Svc` (Alternative Service) 응답 헤더(예: `alt-svc: h3=":443"; ma=86400`)를 통해 HTTP/3 지원 여부를 감지하고, 기존 HTTP/1.1 또는 HTTP/2 연결을 유지한 상태에서 차기 요청부터 HTTP/3로 무중단 점진적 프로토콜 업그레이드를 수행합니다[4][6].

### 6. 결론: 웹 프로토콜 발전사가 주는 시사점 및 미래 전망

HTTP/1.1에서 HTTP/2, 그리고 HTTP/3로 이어지는 프로토콜 진화의 핵심 동인은 **지연 시간(Latency) 최소화**와 **네트워크 손실 환경에서의 복원력 확보**였습니다[1][5]. 애플리케이션 개발자와 인프라 설계자는 각 프로토콜이 해결하고자 했던 병목의 원리를 명확히 이해하고, CDN 및 엣지 서버 단에서 HTTP/3 및 QUIC 설정을 적극 활성화함으로써 현대 웹 성능 최적화의 이점을 극대화해야 합니다.

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

프로토콜의 기술적 우수성에도 불구하고 실무 엔지니어링 관점에서는 패킷 처리 및 인프라 호환성 비용을 신중하게 고려해야 합니다. TCP는 수십 년간 OS 커널 수준에서 하드웨어 오프로드(TSO, LRO 등) 최적화가 이루어진 반면, UDP 기반의 QUIC 및 HTTP/3는 사용자 공간(User Space) 패킷 파싱 비율이 높아 고트래픽 서버에서 상대적으로 더 많은 CPU 리소스를 소비할 수 있습니다. 따라서 온프레미스 웹 서버 단독 구성보다는 글로벌 CDN(Cloudflare, Fastly 등)을 엣지 프록시로 활용하여 HTTP/3를 터미네이션하고 오리진 서버와는 지속 가능한 연결을 유지하는 하이브리드 토폴로지가 현재 시점에서 가장 현실적이고 효율적인 최적화 아키텍처라고 판단됩니다.

## 한계와 반론

- **기업망/방화벽에서의 UDP 차단 문제**: 일부 엄격한 기업 네트워크 환경이나 보수적인 ISP 방화벽 정책으로 인해 UDP 443 포트 트래픽이 차단되는 케이스가 존재합니다. 이 경우 브라우저는 Alt-Svc 타임아웃 후 HTTP/2로 폴백(Fallback)하므로 초기 연결 시 미세한 지연이 발생할 수 있습니다.

- **손실 없는 초고속 유선망에서의 성능 체감 한계**: 패킷 손실률이 0%에 가까운 근거리 유선망 환경에서는 TCP와 QUIC 간의 성능 차이가 사용자가 미세하게 체감하기 어려운 수준일 수 있습니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

HTTP/1.1에서 HTTP/3까지의 발전사는 웹 어플리케이션의 복잡도 증가에 대응하여 웹 전송 계층의 병목을 하나씩 극복해 온 기술 진화의 역사입니다. HTTP/1.1이 persistent connection을 통해 기본 연결 효율을 세웠다면, HTTP/2는 바이너리 프레이밍과 다중화를 통해 애플리케이션 단의 효율성을 극대화했고, HTTP/3는 전송 계층을 UDP/QUIC으로 과감히 재설계하여 패킷 손실 및 네트워크 이동성이라는 현대 모바일 웹의 근본 과제를 해결했습니다. 엔지니어는 최신 프로토콜 도입 시 단순 전환을 넘어 기존의 자원 번들링 및 샤딩 습관을 재점검하고 프로토콜 특성에 맞춤화된 웹 최적화 전략을 수립해야 합니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- MDN Web Docs, "Evolution of HTTP", [https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Evolution_of_HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Evolution_of_HTTP) (확인일: 2026-08-12)

- IETF RFC 2616, "Hypertext Transfer Protocol -- HTTP/1.1", [https://datatracker.ietf.org/doc/html/rfc2616](https://datatracker.ietf.org/doc/html/rfc2616) (확인일: 2026-08-12)

- IETF RFC 7540, "Hypertext Transfer Protocol Version 2 (HTTP/2)", [https://datatracker.ietf.org/doc/html/rfc7540](https://datatracker.ietf.org/doc/html/rfc7540) (확인일: 2026-08-12)

- IETF RFC 9114, "HTTP/3", [https://datatracker.ietf.org/doc/html/rfc9114](https://datatracker.ietf.org/doc/html/rfc9114) (확인일: 2026-08-12)

- IETF RFC 9000, "QUIC: A UDP-Based Multiplexed and Secure Transport", [https://datatracker.ietf.org/doc/html/rfc9000](https://datatracker.ietf.org/doc/html/rfc9000) (확인일: 2026-08-12)

- Cloudflare Blog, "HTTP/3 vs HTTP/2: Performance and Architecture Comparison", [https://blog.cloudflare.com/http-3-vs-http-2/](https://blog.cloudflare.com/http-3-vs-http-2/) (확인일: 2026-08-12)

## 백링크

- [gRPC와 Protocol Buffers: HTTP/2 기반 스트리밍과 직렬화 원리](https://beji-tech.blogspot.com/2026/08/grpc-protocol-buffers-http2.html)
- [TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가](https://beji-tech.blogspot.com/2026/08/tlsssl-handshake-https-tls-13-1-rtt.html)
- [Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화](https://beji-tech.blogspot.com/2026/08/linux-epoll-eventloop-c10k-io.html)