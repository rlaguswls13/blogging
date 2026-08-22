---
author: AI Tech Editor
createdAt: '2026-08-19T06:18:09.455203Z'
factCheckScore: 0
id: '8688895892979592819'
notionPageId: null
publishedAt: '2026-08-19T07:00:09-07:00'
slug: spring-webflux-reactor-schedulers-troubleshooting
status: published
tags:
- Advanced
- WebFlux
- Reactor
- Spring
- Concurrency
title: Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅
updatedAt: '2026-08-19T06:18:09.455203Z'
url: https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html
---

# Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅

## 요약

Spring WebFlux 서비스를 실무에 투입하면 십중팔구 마주치는 문제가 하나 있습니다. 분명 논블로킹으로 짰다고 생각했는데 이벤트 루프 스레드(예: `reactor-http-nio-*`)가 간헐적으로 멈추고, 처리량이 스레드 풀 크기와 무관하게 뚝뚝 끊기는 현상입니다. 원인은 거의 항상 이벤트 루프 스레드 위에서 블로킹 호출(JDBC, 동기 파일 I/O, `Thread.sleep`)이 실행되고 있기 때문입니다. 이 글은 Reactor의 스레드 모델을 코드 레벨에서 짚고, `subscribeOn`과 `publishOn`이 실제로 어떻게 다른 스레드 전환을 만드는지, 블로킹 호출을 자동으로 잡아내는 BlockHound 사용법, 그리고 컨슈머가 발행 속도를 못 따라갈 때 적용하는 Backpressure 전략까지 실무 트러블슈팅 관점에서 다룹니다.

## 본문

### 1. Reactor 스레드 모델의 기본 전제 — 왜 블로킹 호출이 치명적인가

Reactor는 소수의 스레드(기본적으로 CPU 코어 수만큼)로 대량의 요청을 처리하는 이벤트 루프 모델입니다. `Schedulers.parallel()`이나 `Schedulers.boundedElastic()`이 생성하는 스레드 중 일부는 Reactor의 `NonBlocking` 마커 인터페이스를 구현합니다 — 즉 "이 스레드에서는 절대 블로킹 작업을 하지 않는다"는 계약을 코드 레벨로 표현한 것입니다. 문제는 이 계약이 컴파일 타임에 강제되지 않는다는 점입니다. `@RestController`의 리액티브 핸들러 안에서 실수로 JDBC 커넥션을 동기 호출하면, 코드는 정상적으로 컴파일되고 대부분의 경우 테스트도 통과합니다. 다만 트래픽이 몰리는 순간 그 블로킹 호출 하나가 이벤트 루프 스레드를 점유해버려서, 같은 스레드가 처리해야 할 다른 모든 요청이 함께 지연되는 연쇄 장애가 발생합니다. 전통적인 스레드-풀-당-요청(thread-per-request) 모델에서는 스레드 하나가 블로킹돼도 다른 요청은 다른 스레드가 처리하지만, Reactor의 소수 이벤트 루프 모델에서는 그 파급 효과가 훨씬 큽니다.

### 2. subscribeOn vs publishOn — 같은 스레드 전환처럼 보이지만 다르게 동작한다

Reactor Core 공식 레퍼런스 가이드는 두 연산자의 차이를 "배치 위치가 결과에 미치는 영향"으로 설명합니다. `subscribeOn`은 체인 어디에 두든 상관없이 **구독(subscription) 자체가 실행되는 스레드**, 즉 소스(Publisher)가 데이터를 만들어내기 시작하는 스레드를 결정합니다. 반면 `publishOn`은 **그 지점 이후의 다운스트림 연산자들이 실행되는 스레드**만 바꾸고, 그 다음 `publishOn`이 다시 나올 때까지만 적용됩니다. 공식 문서는 `subscribeOn`을 소스 바로 뒤에 두는 것을 권장합니다 — 중간 연산자가 위치를 바꿔도 어차피 전체 체인에 적용되기 때문에 가독성을 위해서입니다.

```java
Flux.range(1, 5)
    .doOnNext(i -> System.out.println("생성: " + Thread.currentThread().getName()))
    .subscribeOn(Schedulers.boundedElastic()) // 소스 생성 자체를 boundedElastic 스레드에서 실행
    .map(i -> i * 2)
    .publishOn(Schedulers.parallel())          // 여기부터 이후 연산자는 parallel 스레드에서 실행
    .doOnNext(i -> System.out.println("가공 후: " + Thread.currentThread().getName()))
    .subscribe();
```

이 코드에서 `doOnNext`(생성 로그)는 `subscribeOn`이 지정한 `boundedElastic` 스레드에서, `map` 이후의 `doOnNext`(가공 후 로그)는 `publishOn`이 지정한 `parallel` 스레드에서 실행됩니다. 실무에서 흔한 실수는 `publishOn`만 여러 번 걸어두고 소스 자체가 여전히 호출한 스레드(예: 이벤트 루프)에서 실행되고 있다는 걸 놓치는 경우입니다 — 소스가 블로킹 호출을 포함하고 있다면 `publishOn`을 아무리 뒤에 걸어도 그 블로킹 자체는 이미 이벤트 루프에서 발생한 뒤입니다.

### 3. 블로킹 호출을 눈으로 찾지 말고 BlockHound로 잡는다

블로킹 호출은 코드 리뷰만으로 찾아내기 어렵습니다. JDBC 드라이버, 로깅 라이브러리, 심지어 일부 서드파티 SDK 내부에 숨어있는 동기 I/O 호출을 사람이 전부 추적하는 건 비현실적입니다. Reactor 팀이 만든 BlockHound는 이 문제를 런타임에 해결합니다. GitHub 공식 저장소에 따르면 BlockHound는 "Java agent to detect blocking calls from non-blocking threads"로, JVM 클래스의 바이트코드를 계측해 블로킹 메서드 호출부에 검사 코드를 삽입합니다. `NonBlocking` 마커가 붙은 스레드(Reactor의 이벤트 루프 스레드 등)에서 블로킹 메서드가 호출되면 `BlockingOperationError`를 던지며 정확한 호출 위치(파일명:줄번호)를 알려줍니다. Reactor 3.3.0부터 기본 통합을 제공하며, RxJava 2 등 다른 리액티브 라이브러리용 SPI도 지원합니다.

```java
// 테스트 초기화 시 1회 설치
@BeforeAll
static void setup() {
    BlockHound.install();
}

@Test
void detectBlockingCall() {
    Mono.fromCallable(() -> {
        Thread.sleep(100); // 이벤트 루프 스레드에서 실행되면 BlockingOperationError 발생
        return "done";
    })
    .subscribeOn(Schedulers.parallel())
    .as(StepVerifier::create)
    .expectError(BlockingOperationException.class)
    .verify();
}
```

실무에서는 프로덕션에 BlockHound를 상시 설치하기보다, CI의 통합 테스트 단계에 설치해 배포 전에 블로킹 회귀를 잡아내는 방식을 주로 씁니다. 예외를 던지는 대신 로그만 남기고 넘어가고 싶다면 `blockingMethodCallback`을 오버라이드해 스택트레이스만 출력하도록 설정할 수도 있습니다.

### 4. 컨슈머가 못 따라갈 때 — Backpressure 전략 선택

Backpressure는 발행자(Publisher)가 소비자(Subscriber)보다 빠르게 데이터를 만들어낼 때, 그 속도 차이를 어떻게 처리할지를 다루는 문제입니다. Reactor는 `onBackpressureBuffer`/`onBackpressureDrop`/`onBackpressureLatest`/`onBackpressureError` 네 가지 기본 전략을 제공합니다.

```java
Flux<Integer> fastSource = Flux.interval(Duration.ofMillis(1)).map(Long::intValue);

// 1) 버퍼 전략: 큐에 쌓아두되, 용량 초과 시 정책 지정 가능
fastSource.onBackpressureBuffer(1000, BufferOverflowStrategy.DROP_OLDEST)
          .subscribe(this::slowConsumer);

// 2) 최신값만 유지: 중간 값은 버리고 항상 가장 최근 값만 소비자에게 전달
fastSource.onBackpressureLatest()
          .subscribe(this::slowConsumer);

// 3) 초과 시 에러로 종료: 데이터 유실이 절대 허용되지 않는 상황에 사용
fastSource.onBackpressureError()
          .subscribe(this::slowConsumer, error -> log.error("오버플로우", error));
```

`onBackpressureBuffer`는 기본적으로 무제한 버퍼링을 시도하지만, `reactor-core` 공식 API 문서는 `BufferOverflowStrategy`로 `DROP_LATEST`(새 요소를 버림, 에러 전파 안 함)와 `DROP_OLDEST`(가장 오래된 요소를 버리고 새 요소를 추가)를 구분해 명시합니다. `onBackpressureLatest()`는 중간값 유실을 감수하고 항상 최신 상태만 필요한 경우(예: 실시간 센서 대시보드)에 적합하고, 반대로 데이터 유실이 절대 허용되지 않는 도메인(결제, 주문 이벤트)에는 `onBackpressureError()`로 명시적으로 실패시키고 상위 레벨에서 재시도나 알림을 트리거하는 편이 안전합니다.

### 5. 실무 트러블슈팅 체크리스트

WebFlux 서비스에서 응답 지연이 발생했을 때 실무에서 확인하는 순서는 보통 다음과 같습니다.

1. **스레드 덤프에서 `reactor-http-nio-*` 스레드의 스택트레이스 확인**: JDBC, `Thread.sleep`, 동기 HTTP 클라이언트 호출이 이벤트 루프 스레드 스택에 보이면 블로킹 호출이 의심됩니다.
2. **BlockHound를 통합 테스트에 설치해 회귀 여부 확인**: 새 라이브러리를 추가했을 때 특히 중요합니다 — 로깅 라이브러리조차 내부적으로 파일 I/O를 블로킹으로 수행하는 경우가 있습니다.
3. **블로킹이 불가피한 레거시 API는 `boundedElastic` 스케줄러로 격리**: `Mono.fromCallable(() -> blockingCall()).subscribeOn(Schedulers.boundedElastic())` 패턴으로 감싸서 이벤트 루프와 분리합니다.
4. **Backpressure 전략이 명시적으로 선택됐는지 확인**: 기본값(무제한 버퍼)을 그냥 쓰고 있다면, 트래픽 급증 시 OOM으로 이어질 수 있는지 점검합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| subscribeOn은 체인 내 위치와 무관하게 소스 구독 실행 스레드를 결정하고, publishOn은 그 지점 이후 다운스트림 연산자의 실행 스레드만 바꾼다(다음 publishOn까지만 적용) | verified | Reactor Core 3.8.6 Reference Guide, "Threading and Schedulers"(projectreactor.io) 원문 직접 대조 |
| BlockHound는 Java agent로, NonBlocking 마커가 붙은 스레드에서 블로킹 메서드가 호출되면 이를 감지해 BlockingOperationError(관련 예외)를 던지며 Reactor 3.3.0부터 기본 통합을 제공한다 | verified | GitHub 공식 저장소 reactor/BlockHound README 원문 직접 대조 |
| Reactor의 BufferOverflowStrategy 중 DROP_LATEST는 버퍼가 가득 찼을 때 새 요소를 에러 없이 버리고, DROP_OLDEST는 가장 오래된 요소를 제거하고 새 요소를 추가한다 | verified | reactor-core 3.8.6 공식 API 문서, BufferOverflowStrategy(projectreactor.io) 원문 직접 대조 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 WebFlux 장애의 상당수는 "논블로킹으로 짰다"는 착각에서 비롯됩니다. Mono/Flux 타입으로 코드를 감싸기만 하면 자동으로 논블로킹이 된다고 오해하는 경우가 많은데, 실제로는 체인 안에 단 하나의 블로킹 호출이 섞여 있어도 그 부분에서 이벤트 루프가 멈춥니다. 개인적으로 팀에 WebFlux를 도입할 때 가장 먼저 강제하는 것이 CI에 BlockHound를 통합 테스트 단계로 걸어두는 일입니다. 사람이 코드 리뷰로 모든 블로킹 호출을 잡아내는 것보다, 런타임에 기계적으로 검출하는 게 훨씬 신뢰할 수 있습니다. 또한 `subscribeOn`/`publishOn`을 "그냥 다른 스레드로 넘기는 마법의 연산자"로 취급하지 말고, 매번 "이 연산자 앞뒤로 어떤 코드가 어느 스레드에서 실행되는가"를 실제로 그려보면서 배치하는 습관이 필요합니다. Backpressure 전략도 마찬가지입니다 — 기본값을 그대로 쓰는 건 "일단 되니까"라는 이유로 잠재적 OOM 위험을 방치하는 것과 다르지 않으며, 도메인의 데이터 유실 허용 범위를 먼저 정의하고 그에 맞는 전략을 명시적으로 고르는 순서가 되어야 합니다.

## 한계와 반론

**한계점**: 이 글에서 다룬 BlockHound는 계측 가능한 "알려진" 블로킹 메서드(JDK 표준 I/O, 특정 라이브러리) 목록을 기반으로 동작하므로, 목록에 없는 네이티브 호출이나 커스텀 블로킹 로직은 탐지하지 못할 수 있습니다. 또한 BlockHound 자체가 바이트코드 계측 오버헤드를 유발하므로, 팀에 따라서는 프로덕션 상시 적용보다 CI/스테이징 환경 한정 적용을 선택하기도 합니다.

**반론**: "리액티브 프로그래밍이 항상 스레드-풀-당-요청 모델보다 우월하다"는 통념에 대해서는 실무에서 반론이 꾸준히 제기됩니다. CPU 바운드 작업이 대부분이거나 팀이 리액티브 디버깅(스택트레이스가 여러 스레드에 걸쳐 끊기는 문제)에 익숙하지 않다면, WebFlux 도입이 오히려 개발 속도와 장애 대응 속도를 늦추는 경우도 있습니다. Reactor 스레드 모델의 이점은 "I/O 바운드 작업이 많고, 동시 연결 수가 매우 많은" 워크로드에서 가장 두드러지며, 모든 서비스에 무조건 적용해야 할 정답은 아닙니다.

## 참고문헌

1. Project Reactor, "Reactor Core 3.8.6 Reference Guide — Threading and Schedulers", [https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html](https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html) (확인일: 2026-08-19)
2. reactor/BlockHound, "Java agent to detect blocking calls from non-blocking threads" (GitHub 공식 저장소), [https://github.com/reactor/BlockHound](https://github.com/reactor/BlockHound) (확인일: 2026-08-19)
3. Project Reactor, "reactor-core 3.8.6 API — BufferOverflowStrategy", [https://projectreactor.io/docs/core/release/api/reactor/core/publisher/BufferOverflowStrategy.html](https://projectreactor.io/docs/core/release/api/reactor/core/publisher/BufferOverflowStrategy.html) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

Reactor 기반 WebFlux 애플리케이션을 안정적으로 운영하는 핵심은 결국 "이벤트 루프 스레드는 절대 블로킹되어서는 안 된다"는 단 하나의 규칙을 코드베이스 전체에서 일관되게 지키는 것입니다. `subscribeOn`과 `publishOn`의 차이를 이해하는 것은 그 규칙을 지키기 위한 도구를 정확히 쓰는 문제이고, BlockHound는 그 규칙이 실제로 지켜지고 있는지 사람 대신 기계적으로 검증하는 안전망입니다. Backpressure 전략 선택 역시 같은 맥락입니다 — 얼마나 많은 데이터를 얼마나 빠르게 처리할 수 있는지에 대한 현실적인 판단 없이 리액티브 스트림을 그냥 연결하면, 트래픽이 몰리는 순간 메모리나 응답 시간 문제로 이어집니다. 실무자 입장에서는 이 세 가지(스레드 격리, 블로킹 검출, Backpressure 정책)를 프로젝트 초기부터 팀의 코딩 컨벤션과 CI 파이프라인에 명시적으로 박아두는 것이, 장애가 난 뒤 원인을 스레드 덤프에서 역추적하는 것보다 훨씬 저렴한 투자입니다.

## 꼬리질문

1. **`Schedulers.boundedElastic()`의 기본 스레드 풀 크기와 큐 용량 한도는 어떤 기준으로 산정되며, 실무에서 커스텀 Scheduler로 교체해야 하는 신호는 무엇인가?**
   - 추천 참고 URL: https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html
2. **리액티브 체인에서 예외 발생 시 스택트레이스가 여러 스레드에 걸쳐 끊기는 문제(디버깅 어려움)를 완화하기 위한 Reactor의 Hooks/Assembly 트레이싱 기능은 실무에서 어떻게 활용하는가?**
3. **BlockHound가 계측하지 못하는 네이티브/커스텀 블로킹 호출을 탐지하기 위한 보완적 관측(Observability) 기법에는 어떤 것들이 있는가?**
   - 추천 참고 URL: https://github.com/reactor/BlockHound

## 백링크

- [이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략](../../../content/posts/msa-non-blocking-retry-dlq.md)

<!-- AUTO:related-sessions:start -->

## 관련 세션
이 문서와 관련된 세션 아카이브(자동 생성 — 태그 매칭 기반):

- [2026-08-16](../sessions/raw/2026-08-16.md)

<!-- AUTO:related-sessions:end -->