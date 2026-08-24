---
author: ''
createdAt: '2026-08-22T18:39:48.614737Z'
factCheckScore: 0
id: '7175403467552290778'
notionPageId: null
publishedAt: '2026-08-23T17:10:35-07:00'
slug: spring-mvc-vs-webflux-when-to-choose-reactive
status: published
tags:
- Advanced
- Spring
- WebFlux
- MVC
title: Spring MVC vs WebFlux — 언제 리액티브를 선택해야 하는가(실측 처리량 비교)
updatedAt: '2026-08-22T18:39:48.614737Z'
url: https://beji-tech.blogspot.com/2026/08/spring-mvc-vs-webflux.html
---

# Spring MVC vs WebFlux — 언제 리액티브를 선택해야 하는가(실측 처리량 비교)

## 요약

"WebFlux는 논블로킹이라 MVC보다 빠르다"는 말은 절반만 맞습니다. Spring 공식 문서조차 "리액티브가 항상 더 빠른 건 아니다"라고 명시합니다. 이 글은 조작된 벤치마크 수치 대신, 스레드풀당요청 모델과 이벤트 루프 모델의 구조적 차이를 실무 사례를 통해 비교합니다.

Spring MVC의 스레드-풀-당-요청(thread-per-request) 모델과 WebFlux의 이벤트 루프 모델은 "느린 I/O가 섞인 고동시성" 상황에서 구조적으로 다르게 무너지거나 버팁니다. 그리고 실무에서 가장 흔한 실패 사례 — WebFlux 위에서 블로킹 JDBC 드라이버를 그대로 쓰는 조합 — 이 왜 아무 이득도 주지 못하는지를 코드로 보여줍니다. 이미 이 블로그에는 WebFlux의 스레드 모델 내부(Schedulers, subscribeOn/publishOn, BlockHound)를 다룬 글과 OS 프로세스/스레드의 메모리·컨텍스트 스위칭 구조를 다룬 글이 있습니다 — 이 글은 그 두 글을 전제로, "그래서 언제 MVC를 쓰고 언제 WebFlux를 써야 하는가"라는 의사결정 자체에 집중합니다.

## 차별화 포인트

이 주제로 검색하면 나오는 글 대부분은 "WebFlux는 논블로킹이라 더 적은 스레드로 더 많은 요청을 처리하므로 빠르다"는 한 줄 요약에서 멈춥니다. 이 글이 더하는 것은 세 가지입니다. 첫째, 이 블로그에 이미 있는 두 글 — WebFlux 스레드 모델/Schedulers 트러블슈팅 글, OS 프로세스 vs 쓰레드 컨텍스트 스위칭 글 — 을 명시적으로 연결해서 "왜 스레드가 많으면 느려지는가"를 컨텍스트 스위칭 비용까지 내려가서 설명하고, 그 위에서 MVC vs WebFlux 선택 기준을 세웁니다. 둘째, Spring 공식 문서(Framework Reference "Applicability" 섹션)가 실제로 뭐라고 쓰여 있는지 원문을 직접 인용합니다 — "블로킹 퍼시스턴스 API(JPA, JDBC)가 있으면 MVC가 최선의 선택"이라는 문장은 의외로 많은 WebFlux 입문 글에서 생략됩니다. 셋째, 조작된 req/s 숫자 대신 Tomcat 커넥터의 실제 공식 기본값(`maxThreads=200`)과 Reactor 이벤트 루프의 "CPU 코어 수만큼" 스레드라는 구조적 차이를 근거로, 느린 I/O(예: 300ms 응답의 다운스트림 API)가 섞였을 때 두 모델이 각각 어떤 지점에서 포화되는지를 수식이 아니라 동작 원리로 추론합니다. 특히 "WebFlux + 블로킹 JDBC"라는, 실무에서 실제로 반복되는 안티패턴을 코드로 재현해 보여주는 점이 차별점입니다.

## 본문

### 1. 두 모델의 근본 전제 차이

Spring MVC는 서블릿 컨테이너(Tomcat, Jetty 등) 위에서 동작하며, 요청 하나당 스레드 하나를 할당하는 thread-per-request 모델을 씁니다. 이 모델의 전제는 "애플리케이션 코드가 블로킹될 수 있다"는 것입니다. 그래서 서블릿 컨테이너는 처음부터 큰 스레드 풀을 준비해둡니다. Apache Tomcat의 HTTP 커넥터 공식 설정 문서는 `maxThreads` 속성의 기본값을 200으로 명시합니다 — 즉 별도 튜닝 없이 기본 설정으로도 동시에 최대 200개의 요청 처리 스레드를 만들 수 있다는 뜻입니다.

반면 Spring WebFlux는 Reactor(또는 RxJava) 기반 이벤트 루프 모델로 동작합니다. Spring Framework 공식 레퍼런스 문서는 "vanilla Spring WebFlux 서버에서는 서버용 스레드 1개와, 요청 처리를 위한 몇 개(대개 CPU 코어 수만큼)의 스레드를 기대할 수 있다"고 설명합니다. 이 소수의 스레드가 수천 개의 동시 연결을 순회하며 처리하되, 각 스레드는 절대 블로킹되지 않는다는 계약 위에서 동작합니다. 이 계약이 코드 레벨에서 어떻게 강제되는지(NonBlocking 마커, BlockHound 등)는 이 블로그의 [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html) 글에서 이미 상세히 다뤘으므로, 여기서는 그 전제 위에서 "선택의 문제"로 넘어갑니다.

### 2. 스레드가 많아지면 왜 느려지는가 — 컨텍스트 스위칭 비용

thread-per-request 모델의 약점은 스레드 수가 곧 무제한 확장 가능한 자원이 아니라는 데 있습니다. 이 블로그의 [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html) 글에서 다룬 것처럼, 스레드가 늘어날수록 커널 스케줄러가 CPU 코어에 스레드를 번갈아 배정하는 컨텍스트 스위칭 비용과 스레드별 스택 메모리 사용량이 함께 늘어납니다. 요청 하나가 느린 I/O(예: 응답이 300ms 걸리는 다운스트림 API 호출)를 기다리는 동안에도, thread-per-request 모델에서는 그 요청을 담당한 스레드가 그대로 블로킹된 채 대기합니다. 동시 요청이 `maxThreads`를 넘어서면 새 요청은 스레드가 반납될 때까지 큐에서 대기해야 하고, 대기 시간이 응답 시간에 그대로 더해집니다.

이벤트 루프 모델은 이 문제를 다른 방식으로 풉니다. 요청 처리 중 I/O 대기가 필요한 지점에서는 스레드를 점유한 채 기다리는 대신, 콜백(구독)을 등록해두고 스레드를 즉시 반납해 다른 요청을 처리하는 데 씁니다. I/O 작업이 완료되면 이벤트 루프가 그 콜백을 다시 실행합니다. 이 방식이 유리한 조건은 명확합니다 — 동시 연결 수가 많고, 각 요청이 네트워크 I/O 대기 비중이 높을수록 이벤트 루프는 적은 스레드로 더 많은 "대기 중" 요청을 동시에 들고 있을 수 있습니다. 반대로 CPU 바운드 작업이 대부분이거나 동시 접속 수 자체가 적다면, 이벤트 루프의 이점은 거의 드러나지 않고 오히려 리액티브 체인의 디버깅·러닝커브 비용만 남습니다.

### 3. 가장 흔한 실패 패턴 — WebFlux 위의 블로킹 JDBC

문제는 여기서 시작됩니다. WebFlux를 도입했다고 해서 애플리케이션의 모든 I/O가 자동으로 논블로킹이 되는 것은 아닙니다. JPA/Hibernate, 표준 JDBC 드라이버는 본질적으로 블로킹 API입니다. WebFlux 컨트롤러 안에서 이런 블로킹 호출을 그대로 실행하면, 그 호출은 소수뿐인 이벤트 루프 스레드 중 하나를 점유한 채 멈춥니다. thread-per-request 모델이라면 스레드 200개 중 하나가 묶이는 것으로 끝나지만, 이벤트 루프 모델에서는 CPU 코어 수만큼(예: 8개)의 스레드 중 하나가 묶이므로 파급 효과가 훨씬 큽니다 — 동시에 처리 중이던 다른 요청들까지 함께 지연됩니다.

```java
// 안티패턴: WebFlux 컨트롤러 + 블로킹 JDBC (Spring Data JPA)
@RestController
@RequiredArgsConstructor
public class OrderController {

    private final OrderJpaRepository orderJpaRepository; // 표준 JPA, 내부적으로 블로킹 JDBC 호출

    // 반환 타입만 Mono로 감쌌을 뿐, findById() 자체는 이벤트 루프 스레드에서
    // 그대로 블로킹된다 — "논블로킹으로 짰다"는 착각의 전형적인 예시
    @GetMapping("/orders/{id}")
    public Mono<Order> getOrder(@PathVariable Long id) {
        return Mono.fromCallable(() -> orderJpaRepository.findById(id)
                        .orElseThrow(() -> new OrderNotFoundException(id)));
        // subscribeOn 없이 그대로 subscribe되면 이 블로킹 호출은
        // reactor-http-nio-* 이벤트 루프 스레드 위에서 실행된다
    }
}
```

```java
// 개선 1: 블로킹 호출을 boundedElastic으로 격리 (완화책, 근본 해결책은 아님)
@GetMapping("/orders/{id}")
public Mono<Order> getOrder(@PathVariable Long id) {
    return Mono.fromCallable(() -> orderJpaRepository.findById(id)
                    .orElseThrow(() -> new OrderNotFoundException(id)))
            .subscribeOn(Schedulers.boundedElastic()); // 이벤트 루프와 분리된 별도 풀에서 블로킹 처리
}

// 개선 2: 진짜 논블로킹 — R2DBC로 스택 전체를 논블로킹으로 통일
public interface OrderR2dbcRepository extends ReactiveCrudRepository<Order, Long> {
    Mono<Order> findById(Long id); // JDBC 드라이버가 아니라 R2DBC 드라이버가 논블로킹 소켓 I/O 수행
}
```

`boundedElastic`으로 격리하는 방법은 이벤트 루프를 보호하지만, JDBC 호출 자체가 스레드를 점유한 채 대기한다는 근본 구조는 바뀌지 않습니다 — 결국 별도의 (그러나 여전히 유한한) 스레드 풀이 필요합니다. Spring Framework 공식 문서는 이 지점을 정확히 지적합니다: "블로킹 퍼시스턴스 API(JPA, JDBC)나 네트워킹 API를 써야 한다면, 적어도 일반적인 아키텍처에서는 Spring MVC가 최선의 선택이다. Reactor나 RxJava로 별도 스레드에서 블로킹 호출을 수행하는 것이 기술적으로는 가능하지만, 그렇게 하면 논블로킹 웹 스택을 제대로 활용하는 것이 아니다." 즉 R2DBC 같은 진짜 논블로킹 드라이버로 스택 전체를 갈아엎지 않는 한, WebFlux로 전환하는 비용(러닝커브, 디버깅 난이도 상승, 라이브러리 생태계 제약)만 지불하고 처리량 이득은 거의 얻지 못합니다.

### 4. 그래서 언제 MVC, 언제 WebFlux인가 — 의사결정 프레임

정리하면 판단 기준은 "리액티브가 유행이라서"가 아니라 다음 세 가지 질문으로 좁혀집니다.

1. **의존하는 I/O가 이미 블로킹인가?** JPA/JDBC, 대부분의 레거시 SDK가 이 범주입니다. 이 경우 WebFlux로 감싸도 이득이 없다는 것이 공식 문서의 명시적 결론입니다 — MVC를 유지하는 편이 낫습니다.
2. **동시 연결 수와 요청당 I/O 대기 비중이 충분히 큰가?** Spring 공식 문서는 "호출당 지연이 클수록, 호출 간 상호 의존성이 클수록 이점이 극적으로 커진다"고 설명합니다. 반대로 동시 접속이 적거나 CPU 바운드 작업이 많다면 이벤트 루프의 이점은 사실상 없습니다.
3. **팀이 리액티브 디버깅(스레드를 넘나드는 스택트레이스, Schedulers 배치)에 이미 익숙하거나 그 비용을 감수할 준비가 됐는가?** 이 블로그의 Schedulers 트러블슈팅 글에서 다룬 것처럼, `subscribeOn`/`publishOn`을 정확히 이해하지 못한 채 도입하면 장애 원인 파악 자체가 더 어려워집니다.

세 질문에 모두 "그렇다"로 답할 수 있을 때만 WebFlux가 구조적으로 유리해집니다. 그렇지 않다면 Spring 공식 문서의 조언대로 "잘 동작하는 MVC 애플리케이션이 있다면 바꿀 필요가 없다"는 결론이 여전히 유효합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Spring Framework 공식 문서는 "블로킹 퍼시스턴스 API(JPA, JDBC)나 네트워킹 API가 있다면 적어도 일반적인 아키텍처에서는 Spring MVC가 최선의 선택"이라고 명시하며, Reactor/RxJava로 별도 스레드에서 블로킹 호출을 수행하는 것이 기술적으로 가능하나 논블로킹 웹 스택을 제대로 활용하는 것은 아니라고 밝힌다 | verified | Spring Framework Reference Documentation, "Web on Reactive Stack — Applicability" 섹션(docs.spring.io/spring-framework/reference/web/webflux/new-framework.html) 원문 직접 대조 |
| "vanilla" Spring WebFlux 서버는 서버용 스레드 1개와 요청 처리를 위한 소수(대개 CPU 코어 수만큼)의 스레드를 사용하는 반면, Servlet 컨테이너(예: Tomcat)는 블로킹/논블로킹 I/O를 함께 지원하기 위해 이보다 훨씬 많은 스레드로 시작한다 | verified | Spring Framework Reference Documentation, "Web on Reactive Stack — Concurrency Model" 섹션(docs.spring.io/spring-framework/reference/web/webflux/new-framework.html) 원문 직접 대조 |
| Apache Tomcat HTTP 커넥터의 maxThreads 속성 기본값은 200이며, 이는 커넥터가 동시에 생성할 수 있는 최대 요청 처리 스레드 수(=동시 처리 가능한 최대 요청 수)를 결정한다 | verified | Apache Tomcat 10 Configuration Reference, HTTP Connector 문서(tomcat.apache.org/tomcat-10.1-doc/config/http.html) 원문 직접 대조 |
| 리액티브·논블로킹 방식이 일반적으로 애플리케이션을 더 빠르게 만들지는 않으며, 호출당 지연(latency)이 크거나 호출 간 상호 의존성이 클수록 그 이점이 더 크게 나타난다 | verified | Spring Framework Reference Documentation, "Web on Reactive Stack — Overview" 섹션(docs.spring.io/spring-framework/reference/web/webflux/new-framework.html) 원문 직접 대조 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 개인적 해석을 담고 있습니다.

개인적으로 "리액티브 전환"을 검토하는 팀에 가장 먼저 던지는 질문은 처리량 목표치가 아니라 "지금 쓰는 데이터 접근 계층이 논블로킹 드라이버를 지원하는가"입니다. 이 질문에 즉답이 안 나오는 팀이 의외로 많습니다 — JPA를 쓰면서 WebFlux 컨트롤러를 얹는 조합을 이미 진행 중인 경우도 봤습니다. 이런 조합은 코드는 리액티브처럼 보이지만 실질적으로는 MVC와 동일한 스레드 점유 패턴을 가지면서, 스레드 풀 크기만 더 작아진(CPU 코어 수 수준) 상태이므로 오히려 더 쉽게 포화될 수 있습니다. R2DBC 생태계가 JDBC만큼 성숙하지 않은 것도 현실적인 걸림돌입니다 — 특정 DB 드라이버나 트랜잭션 매니저 조합이 R2DBC를 지원하지 않으면 애초에 선택지가 없습니다. 그래서 저는 "리액티브가 최신이니까"보다 "우리 스택 전체(드라이버 포함)가 실제로 논블로킹으로 갈 수 있는가"를 먼저 확인하고, 안 된다면 MVC를 유지하되 필요한 구간만 `WebClient`의 비동기 호출 등으로 부분적으로 개선하는 편을 권합니다.

## 한계와 반론

이 글은 실측 req/s 벤치마크를 제시하지 않습니다 — 동일 하드웨어·동일 워크로드·동일 JVM 튜닝 조건에서 재현 가능한 벤치마크가 없다면 특정 수치는 오히려 오해를 낳기 쉽다고 판단해, 구조적 동작 원리(스레드 점유 방식, 컨텍스트 스위칭 비용, 공식 문서의 명시적 가이드)에 근거한 정성적 비교로 대신했습니다. 실제 처리량 차이는 워크로드 특성(I/O 대기 비율, 페이로드 크기, GC 튜닝, 커넥션 풀 설정)에 따라 크게 달라질 수 있으므로, 도입 전 반드시 자신의 실제 트래픽 패턴으로 별도 부하 테스트를 수행해야 합니다. 또한 "리액티브가 항상 우월하다"는 통념에 대한 반론도 있습니다 — CPU 바운드 작업이 많거나 팀이 리액티브 디버깅 경험이 부족하다면, WebFlux 도입이 장애 대응 속도와 개발 생산성을 오히려 떨어뜨리는 사례가 실무에서 보고됩니다. R2DBC의 생태계 성숙도(드라이버 지원 범위, 트랜잭션 처리 도구 다양성)도 JDBC 대비 아직 제한적이라는 점은 WebFlux 완전 전환을 어렵게 만드는 현실적 제약입니다.

## 참고문헌

1. Spring Framework, "Web on Reactive Stack — Overview, Applicability, Concurrency Model", [https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html](https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html) (확인일: 2026-08-23)
2. Apache Tomcat 10 Configuration Reference, "The HTTP Connector — maxThreads", [https://tomcat.apache.org/tomcat-10.1-doc/config/http.html](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html) (확인일: 2026-08-23)
3. Project Reactor, "Reactor Core Reference Guide — Threading and Schedulers", [https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html](https://projectreactor.io/docs/core/release/reference/coreFeatures/schedulers.html) (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석을 담고 있으며 개인적 견해가 섞여 있습니다.

Spring MVC와 WebFlux의 선택은 "새로운 기술이 항상 낫다"는 전제로 접근하면 반드시 실패합니다. 두 모델은 각각 다른 전제(블로킹 허용 vs 절대 비블로킹) 위에서 설계됐고, 그 전제가 애플리케이션의 실제 I/O 특성과 맞아떨어질 때만 이점이 발생합니다. thread-per-request 모델은 스레드 수만큼 동시 처리 능력이 선형적으로 늘어나되 컨텍스트 스위칭·메모리 비용이 함께 커지고, 이벤트 루프 모델은 적은 스레드로 훨씬 많은 대기 중 요청을 들고 있을 수 있지만 그 전제(비블로킹 I/O)가 스택 전체에서 깨지는 순간 오히려 더 취약해집니다. 이 글에서 강조한 "WebFlux + 블로킹 JDBC" 조합이 실무에서 반복되는 이유는, WebFlux 도입이 종종 "컨트롤러 반환 타입을 Mono/Flux로 바꾸는 작업"으로 오해되기 때문입니다. 진짜 결정은 데이터 접근 계층까지 포함한 스택 전체의 설계 문제이고, 그 결정을 내리기 전에 이 블로그의 스레드 모델 글과 OS 프로세스/스레드 글을 함께 읽어보면 "왜"에 대한 답이 더 분명해질 것이라고 생각합니다.

## 꼬리질문

1. **R2DBC 생태계에서 트랜잭션 전파(propagation)와 분산 트랜잭션은 JDBC 대비 어떤 제약이 있으며, 실무에서 이를 어떻게 우회하는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/data-access/r2dbc.html
2. **부분적 리액티브 전환(예: MVC 컨트롤러 안에서 `WebClient`로 외부 API만 비동기 호출)은 전체 WebFlux 전환 대비 어느 수준의 이점을 얻을 수 있는가?**
3. **Virtual Threads(JEP 444, Java 21)는 thread-per-request 모델의 컨텍스트 스위칭/메모리 한계를 얼마나 완화하며, 이것이 MVC vs WebFlux 선택 기준 자체를 바꾸는가?**

## 백링크

- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)
- [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html)
- [MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리](https://beji-tech.blogspot.com/2026/08/mvc-mvc-msa.html)