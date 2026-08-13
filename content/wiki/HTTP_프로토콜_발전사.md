# HTTP 프로토콜 발전사

HTTP/1.1에서 HTTP/2, 그리고 HTTP/3로 이어지는 웹 전송 프로토콜의 기술적 발전 과정과 웹 성능 최적화 원리를 다룹니다.

## 1. HTTP/1.1의 동작 원리와 성능 병목

HTTP/1.1은 1999년 RFC 2616 표준으로 제정되었습니다. HTTP/1.0의 단발성 연결 문제를 해결하고자 Persistent Connection(Keep-Alive)을 도입하여 단일 TCP 연결 내에서 여러 요청을 재사용할 수 있도록 개선했습니다.

그러나 HTTP/1.1은 요청과 응답이 반드시 순차적으로 처리되어야 하는 직렬 전송 제약이 있습니다. 이 때문에 이전 요청의 처리가 지연되면 후속 요청들이 모두 대기하게 되는 **애플리케이션 레벨의 Head-of-Line(HOL) Blocking 병목**을 야기합니다.

당시 웹 개발자들은 이 병목을 회피하고 자원 다운로드를 병렬화하기 위해 브라우저의 도메인당 최대 TCP 연결 수 제한(보통 6개)을 우회하는 **Domain Sharding** 기법이나, 여러 이미지를 하나의 큰 이미지로 합치는 **Image Sprites**, JS/CSS **Inline 번들링** 기법을 최적화 방법으로 사용했습니다.

## 2. HTTP/2의 다중화(Multiplexing)와 바이너리 프레임

2015년 제정된 HTTP/2(RFC 7540)는 헤더 오버헤드와 애플리케이션 레벨 HOL Blocking을 근본적으로 개선했습니다.

- **바이너리 프레이밍 계층 (Binary Framing Layer)**: 텍스트 기반 메시지 구조 대신 데이터를 바이너리 프레임 단위로 분할하고 단일 TCP 연결 상에서 여러 스트림(Stream)을 동시 교차 전송하는 **다중화(Multiplexing)**를 제공합니다.
- **HPACK 압축 알고리즘**: 허프만 코딩(Huffman Coding)과 정적/동적 테이블을 활용하여 중복 전송되는 헤더 크기를 획기적으로 압축합니다.

그러나 전송 계층 프로토콜이 여전히 TCP이므로 패킷 손실이 발생하면 손실된 패킷이 재전송될 때까지 해당 TCP 연결에 속한 모든 스트림의 데이터 처리가 정지되는 **TCP 수준의 HOL Blocking** 문제가 한계로 남았습니다.

## 3. HTTP/3와 UDP 기반 QUIC 프로토콜

이를 극복하기 위해 2022년 RFC 9114 표준으로 제정된 HTTP/3는 전송 계층의 패러다임 전환을 이룩했습니다.

HTTP/3는 TCP 대신 UDP 기반으로 설계된 **QUIC(Quick UDP Internet Connections)** 프로토콜을 도입하여 스트림별 독립적 흐름 제어 및 손실 복구를 지원하며, 전송 계층 수준의 HOL Blocking을 완벽하게 제거했습니다.

- **빠른 연결 수립 (0-RTT)**: 전송 계층 핸드셰이크와 TLS 1.3 암호화 핸드셰이크를 기본 결합하여 최초 연결 시 1-RTT만에 완결하며, 기존 세션 재연결 시 0-RTT Connection Resumption을 지원합니다.
- **연결 마이그레이션 (Connection Migration)**: IP 주소 대신 unique한 Connection ID를 식별자로 사용하여, Wi-Fi에서 5G 셀룰러 망으로 연결이 전환되어 IP가 변경되더라도 재연결 오버헤드 없이 세션을 유지합니다.

## 4. 웹 성능 최적화 실전 적용 전략

- **번들링 전략 재점검**: HTTP/1.1 시대의 Domain Sharding과 대형 번들링(Big Bundling)은 HTTP/2 및 HTTP/3 환경에서는 캐시 효율을 저하시키는 반패턴입니다. 미세 분할 코드(Fine-grained Code Splitting) 및 ES Modules 분할 배포가 권장됩니다.
- **Alt-Svc(Alternative Service) 활용**: 서버가 HTTP 응답 헤더에 `Alt-Svc` 헤더(예: `alt-svc: h3=":443"; ma=86400`)를 포함하여 보냄으로써 클라이언트가 차기 요청부터 HTTP/3로 무중단 점진적 프로토콜 업그레이드를 수행하도록 설계합니다.

## 관련 문서
- [위키 인덱스](README.md)
