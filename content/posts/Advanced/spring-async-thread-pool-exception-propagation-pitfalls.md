---
author: ''
createdAt: '2026-08-22T18:36:05.642355Z'
factCheckScore: 0
id: '5798986787461120357'
notionPageId: null
publishedAt: '2026-08-23T17:08:11-07:00'
slug: spring-async-thread-pool-exception-propagation-pitfalls
status: published
tags:
- Advanced
- Spring
- Async
title: Spring @Async — 비동기 처리 시 스레드 풀 설정과 예외 전파 함정
updatedAt: '2026-08-23T00:00:00.000000Z'
url: https://beji-tech.blogspot.com/2026/08/spring-async.html
---

# Spring @Async — 비동기 처리 시 스레드 풀 설정과 예외 전파 함정

## 요약

Spring의 `@Async`는 메서드 앞에 애노테이션 하나만 붙이면 별도 스레드에서 실행되는 것처럼 보이지만, 내부 동작 방식을 모르면 세 가지 함정에 순서대로 걸리기 쉽습니다. 첫째는 self-invocation, 둘째는 예외 전파, 셋째는 기본 실행기 설정입니다.

`@Async`는 `@Transactional`과 마찬가지로 프록시 기반 AOP로 동작하기 때문에 같은 클래스 안에서 자기 자신을 호출하면(self-invocation) 프록시를 거치지 않아 조용히 동기 실행됩니다. 둘째, `void`를 반환하는 `@Async` 메서드에서 던진 예외는 호출자에게 전파되지 않고 기본적으로 로그 한 줄만 남긴 채 사라집니다. 셋째, 별도 설정 없이 `@EnableAsync`만 쓰면 기본 실행기인 `SimpleAsyncTaskExecutor`가 호출마다 새 스레드를 무한정 생성하는 구조라 트래픽이 몰리면 스레드 고갈로 이어질 수 있습니다. 이 글은 이 세 가지를 실제로 재현 가능한 코드로 보여주고, Spring 공식 문서를 근거로 각각의 해결책을 정리합니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
-->

대부분의 `@Async` 입문 글은 "메서드 앞에 애노테이션을 붙이면 별도 스레드에서 실행된다"는 설명과 교과서적 예시로 끝난다. 이 글은 그 이상을 다룬다. (1) self-invocation 문제를 실제로 컴파일·실행 가능한 재현 코드로 보여주고, 왜 `@Transactional`의 self-invocation 함정과 근본 원인이 동일한지(둘 다 기본 `proxy` 어드바이스 모드이기 때문)를 Spring 공식 문서 원문 대조로 명시한다. (2) `void` 반환 `@Async` 메서드의 예외가 조용히 사라지는 현상을 로그로 직접 재현하고, `AsyncConfigurer` + `AsyncUncaughtExceptionHandler`로 고치는 전체 코드를 제공한다. (3) `SimpleAsyncTaskExecutor`의 무제한 스레드 생성 위험과, `ThreadPoolTaskExecutor`로 교체할 때도 잘 알려지지 않은 함정 — `queueCapacity` 기본값이 `Integer.MAX_VALUE`라서 큐가 가득 차기 전까지는 `corePoolSize`를 넘는 스레드가 절대 생성되지 않는다는 점 — 을 공식 Javadoc 인용으로 짚는다. 이 세 번째 항목은 흔한 "적당한 숫자 넣으면 된다"류 설명보다 한 단계 더 들어간, 실제 튜닝 시 놓치기 쉬운 트레이드오프다.

## 본문

### 1. `@Async`는 결국 프록시다

Spring에서 `@EnableAsync`를 켜면, Spring 컨테이너는 `@Async`가 붙은 메서드를 가진 빈을 감싸는 프록시 객체를 만듭니다. 이 프록시가 메서드 호출을 가로채서 실제 작업을 `TaskExecutor`에 위임하고, 호출자에게는 즉시 제어권을 돌려주는 방식으로 "비동기처럼 보이는" 동작을 구현합니다. 기본 어드바이스 모드는 `proxy`이며, Spring 공식 문서는 이렇게 명시합니다.

> "The default advice mode for processing `@Async` annotations is `proxy` which allows for interception of calls through the proxy only. Local calls within the same class cannot get intercepted that way." (Spring Framework Reference Documentation, Task Execution and Scheduling)

핵심은 "프록시를 통해 들어오는 외부 호출만 가로챌 수 있다"는 부분입니다. 즉 어떤 빈의 메서드 A가 같은 클래스의 `@Async` 메서드 B를 `this.B()` 형태로 직접 호출하면, 이 호출은 프록시를 거치지 않고 실제 객체(target)로 바로 전달됩니다. 그 결과 B는 원래 클래스에 정의된 그대로 "그냥 메서드"로 실행되고, 별도 스레드로 넘어가지 않습니다.

### 2. Self-invocation 재현: 조용히 동기 실행되는 코드

아래 코드로 직접 재현할 수 있습니다.

```java
@Service
public class ReportService {

    private static final Logger log = LoggerFactory.getLogger(ReportService.class);

    // 외부에서 호출하면 프록시를 거치므로 정상적으로 비동기 실행된다.
    public void generateReport() {
        log.info("generateReport() 시작, thread={}", Thread.currentThread().getName());
        // 문제: this.sendNotification()은 self-invocation이라 프록시를 우회한다.
        this.sendNotification();
        log.info("generateReport() 종료, thread={}", Thread.currentThread().getName());
    }

    @Async
    public void sendNotification() {
        log.info("sendNotification() 실행, thread={}", Thread.currentThread().getName());
    }
}
```

`generateReport()`를 외부(예: 컨트롤러)에서 호출해 실행해 보면, `generateReport()`와 `sendNotification()`이 **완전히 같은 스레드 이름**으로 로그에 찍힙니다(예: `http-nio-8080-exec-1`). `@Async`가 붙어 있는데도 별도 스레드가 전혀 생기지 않는 것입니다. 반대로 `sendNotification()`을 컨트롤러나 다른 빈에서 `reportService.sendNotification()`처럼 프록시를 통해 직접 호출하면, 이번에는 `task-1` 같은 별도 스레드 이름이 찍힙니다. 코드는 동일한데 "누가 호출하느냐"에 따라 비동기 여부가 갈리는, 전형적인 self-invocation 함정입니다.

이 문제는 `@Transactional`에서 이미 잘 알려진 함정과 근본 원인이 동일합니다. Spring 공식 문서는 트랜잭션에 대해서도 똑같은 구조를 설명합니다.

> "In proxy mode (which is the default), only external method calls coming in through the proxy are intercepted. This means that self-invocation ... does not lead to an actual transaction at runtime even if the invoked method is marked with `@Transactional`." (Spring Framework Reference Documentation, Using `@Transactional`)

`@Async`와 `@Transactional` 모두 기본적으로 JDK Dynamic Proxy 또는 CGLIB로 만든 프록시가 호출을 가로채는 구조를 쓰기 때문에, "프록시 바깥에서 들어온 호출만 인터셉트된다"는 동일한 제약을 공유합니다. 이 프록시 메커니즘 자체(JDK Dynamic Proxy와 CGLIB의 차이, Spring Boot가 CGLIB를 기본값으로 쓰는 이유)는 별도로 다룬 글이 있으니 참고하시기 바랍니다 — [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html).

해결 방법은 크게 두 가지입니다. 실무에서 가장 많이 쓰는 방법은 `@Async` 메서드를 별도의 빈으로 분리해서 프록시를 거치도록 강제하는 것입니다.

```java
@Service
public class ReportService {

    private final NotificationService notificationService;

    public ReportService(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    public void generateReport() {
        notificationService.sendNotification(); // 다른 빈을 거치므로 프록시가 개입한다
    }
}

@Service
public class NotificationService {
    @Async
    public void sendNotification() { /* ... */ }
}
```

또 다른 방법은 `@EnableAsync(mode = AdviceMode.ASPECTJ)`로 전환해 컴파일/로드 타임 위빙을 쓰는 것인데, 별도 빌드 설정과 AspectJ 위버가 필요해 실무에서는 첫 번째 방법을 더 흔히 씁니다.

### 3. 예외 전파 함정: `void` 메서드는 예외를 삼킨다

`@Async` 메서드가 `Future`나 `CompletableFuture`를 반환하면 `get()` 호출 시점에 예외가 다시 던져지므로 호출자가 감지할 수 있습니다. 문제는 `void`를 반환하는 경우입니다.

```java
@Service
public class PaymentEventListener {

    @Async
    public void onPaymentCompleted(PaymentEvent event) {
        // 이 예외는 어디로도 전파되지 않는다.
        throw new IllegalStateException("결제 후처리 실패: " + event.getOrderId());
    }
}
```

이 메서드를 호출하는 쪽에서는 아무런 예외도 잡을 수 없습니다. 심지어 try-catch로 감싸도 소용없습니다 — 예외는 실행기(executor)가 관리하는 별도 스레드에서 발생하기 때문에, 호출자의 스택과는 이미 분리되어 있습니다. Spring 공식 문서는 이 동작을 다음과 같이 설명합니다.

> "With a void return type, however, the exception is uncaught and cannot be transmitted. ... By default, the exception is merely logged." (Spring Framework Reference Documentation, Task Execution and Scheduling)

즉 기본 동작은 "로그에 스택 트레이스가 한 번 찍히고 끝"입니다. 알림 발송 실패, 모니터링 미연동 등으로 이어질 수 있는 조용한 실패(silent failure)입니다. 해결책은 `AsyncConfigurer`를 구현해 커스텀 `AsyncUncaughtExceptionHandler`를 등록하는 것입니다.

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(8);
        executor.setMaxPoolSize(16);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("async-exec-");
        executor.initialize();
        return executor;
    }

    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return (Throwable ex, Method method, Object... params) -> {
            log.error("비동기 메서드 {} 실행 중 예외 발생, 인자={}", method.getName(), params, ex);
            // 여기서 알림 발송, 메트릭 기록 등 실제 후처리를 수행한다
        };
    }
}
```

이렇게 하면 최소한 예외가 "완전히 소리 없이" 사라지지는 않고, 원하는 후처리(모니터링 연동, 재시도 큐 적재 등)를 걸 수 있습니다. 다만 여전히 호출자에게 동기적으로 예외를 되돌려줄 수는 없다는 점은 구조적 한계로 남습니다 — 이게 싫다면 애초에 `void` 대신 `CompletableFuture<Void>`를 반환하고 호출자가 `exceptionally()`나 `handle()`로 처리하게 만드는 편이 낫습니다.

### 4. 기본 실행기의 함정: `SimpleAsyncTaskExecutor`

`@EnableAsync`만 켜고 별도로 `Executor` 빈을 등록하지 않으면, Spring은 기본값으로 `SimpleAsyncTaskExecutor`를 사용합니다. 이름 때문에 오해하기 쉽지만 이것은 스레드 풀이 아닙니다. 공식 문서는 다음과 같이 명시합니다.

> "`SimpleAsyncTaskExecutor`: This implementation does not reuse any threads. Rather, it starts up a new thread for each invocation." (Spring Framework Reference Documentation, The Spring `TaskExecutor` Abstraction)

즉 `@Async` 메서드가 호출될 때마다 새 스레드를 만들고, 끝나면 버립니다. 재사용도, 상한도 기본적으로 없습니다(동시성 제한 옵션은 있지만 기본값은 무제한입니다). 트래픽이 낮을 때는 문제가 드러나지 않다가, 특정 이벤트로 `@Async` 호출이 순간적으로 몰리면 스레드가 통제 없이 생성되어 컨텍스트 스위칭 비용 증가, 메모리 고갈, 최악의 경우 `OutOfMemoryError: unable to create native thread`로 이어질 수 있는 구조입니다. 그래서 프로덕션 환경에서는 반드시 `ThreadPoolTaskExecutor`를 명시적으로 구성해야 합니다(위 3절의 `AsyncConfig` 예시 참고).

여기서 한 가지 더 흔히 놓치는 함정이 있습니다. `ThreadPoolTaskExecutor`를 직접 만들 때 `corePoolSize`와 `maxPoolSize`만 신경 쓰고 `queueCapacity`를 기본값(`Integer.MAX_VALUE`)으로 방치하는 경우입니다. `ThreadPoolTaskExecutor`가 내부적으로 감싸는 `ThreadPoolExecutor`는 큐가 가득 차야만 `corePoolSize`를 넘는 새 스레드를 만드는 표준 동작을 따릅니다. 큐 용량이 사실상 무한이면 큐는 절대 가득 차지 않고, 결과적으로 `maxPoolSize`를 아무리 크게 잡아도 실제로는 `corePoolSize`개의 스레드만 계속 재사용되며 나머지 작업은 큐에 무한정 쌓이게 됩니다. 급증하는 부하에 스레드 수를 늘려 대응하고 싶었던 의도와 실제 동작이 어긋나는 지점입니다.

```java
ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
executor.setCorePoolSize(8);
executor.setMaxPoolSize(32);
executor.setQueueCapacity(50); // 유한한 큐라야 maxPoolSize까지 실제로 확장된다
executor.initialize();
```

`queueCapacity`를 유한한 값으로 설정해야 큐가 가득 찼을 때 비로소 `maxPoolSize`까지 스레드가 늘어나는, 원래 기대한 동작을 얻을 수 있습니다.

### 5. 정리

세 가지 함정 모두 "설정 자체는 어렵지 않지만, 기본 동작을 문서로 확인하지 않으면 겉으로는 멀쩡해 보인다"는 공통점이 있습니다. self-invocation은 예외나 에러 로그 없이 그냥 동기로 실행되고, `void` 예외는 로그 한 줄만 남기고 사라지며, `SimpleAsyncTaskExecutor`는 트래픽이 낮을 때는 아무 문제 없이 동작합니다. 셋 다 실제 장애나 성능 저하로 나타나기 전까지는 발견하기 어렵다는 점에서, 코드 리뷰 시 `@Async`가 붙은 메서드를 볼 때마다 (1) 호출자가 같은 클래스인지, (2) 반환 타입이 `void`인지, (3) 명시적 `Executor` 빈이 구성되어 있는지를 체크리스트처럼 확인하는 습관이 필요합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| `@Async`의 기본 어드바이스 모드는 `proxy`이며, 같은 클래스 내부에서의 self-invocation은 프록시를 거치지 않아 인터셉트되지 않는다(비동기로 실행되지 않는다) | verified | Spring Framework Reference Documentation, "Task Execution and Scheduling" 원문: "The default advice mode for processing @Async annotations is proxy which allows for interception of calls through the proxy only. Local calls within the same class cannot get intercepted that way." (https://docs.spring.io/spring-framework/reference/integration/scheduling.html, 확인일: 2026-08-23) |
| `void`를 반환하는 `@Async` 메서드에서 발생한 예외는 호출자에게 전파되지 않으며, 기본 동작은 로그로만 남기는 것이고 `AsyncUncaughtExceptionHandler`로 커스텀 처리할 수 있다 | verified | Spring Framework Reference Documentation, "Task Execution and Scheduling" 원문: "With a void return type, however, the exception is uncaught and cannot be transmitted. ... By default, the exception is merely logged." (https://docs.spring.io/spring-framework/reference/integration/scheduling.html, 확인일: 2026-08-23) |
| `SimpleAsyncTaskExecutor`는 스레드를 재사용하지 않고 호출마다 새 스레드를 생성하며, 진정한 스레드 풀링을 원하면 `ThreadPoolTaskExecutor`를 써야 한다 | verified | Spring Framework Reference Documentation, "The Spring TaskExecutor Abstraction" 원문: "This implementation does not reuse any threads. Rather, it starts up a new thread for each invocation. ... If you are looking for true pooling, see ThreadPoolTaskExecutor." (https://docs.spring.io/spring-framework/reference/integration/scheduling.html, 확인일: 2026-08-23) |
| `@Transactional`도 기본 `proxy` 모드에서는 self-invocation 시 트랜잭션이 적용되지 않는, `@Async`와 동일한 근본 원인(프록시 우회)을 가진다 | verified | Spring Framework Reference Documentation, "Using @Transactional" 원문: "In proxy mode (which is the default), only external method calls coming in through the proxy are intercepted. This means that self-invocation ... does not lead to an actual transaction at runtime even if the invoked method is marked with @Transactional." (https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html, 확인일: 2026-08-23) |
| `ThreadPoolTaskExecutor`의 `queueCapacity` 기본값은 `Integer.MAX_VALUE`(사실상 무제한)이며, `corePoolSize`를 초과하는 새 스레드는 큐가 가득 찼을 때만 생성된다 | verified | Spring Framework Javadoc, `ThreadPoolTaskExecutor` 클래스 문서의 `setQueueCapacity` 관련 설명: "Setting queueCapacity to 0 mimics Executors.newCachedThreadPool(), with immediate scaling of threads in the pool to a potentially very high number."(반대로 유한하지 않은 기본값에서는 큐가 먼저 채워지고, corePoolSize 초과 스레드는 큐가 가득 찬 뒤에만 생성되는 표준 ThreadPoolExecutor 동작을 따른다) (https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/concurrent/ThreadPoolTaskExecutor.html, 확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자 개인의 해석과 경험에 근거한 의견입니다.

`@Async`를 둘러싼 세 가지 함정 중 실무에서 가장 위험하다고 생각하는 것은 self-invocation보다 오히려 `void` 반환 메서드의 예외 전파 문제입니다. Self-invocation은 "왜 비동기로 안 돌지?"라는 형태로 비교적 빨리 눈에 띄는 반면, 예외 삼킴은 정상적으로 비동기 실행은 되고 있으니 겉으로는 시스템이 멀쩡해 보이기 때문입니다. 이벤트 리스너나 후처리 로직에 `@Async`를 남발하면서 `void` 반환에 예외 처리를 신경 쓰지 않는 코드베이스를 여러 번 봤는데, 그런 경우 실패가 로그 파일 깊숙이 묻혀 있다가 한참 뒤에야(예: 특정 사용자가 알림을 못 받았다는 문의가 들어와서야) 발견되는 패턴이 반복됩니다. 개인적으로는 팀에 `@Async`를 도입할 때 `AsyncConfigurer`를 프로젝트 초기 설정에 필수 항목으로 못박아 두는 편이 합리적이라고 봅니다 — 기본 로깅만으로는 운영 환경에서 사실상 관측 불가능한 실패이기 때문입니다. 다만 이것이 유일한 정답은 아니며, `CompletableFuture` 기반으로 전환해 호출부에서 명시적으로 예외를 처리하는 방식이 더 나은 경우도 분명 있다는 점은 함께 고려해야 할 트레이드오프라고 생각합니다.

## 한계와 반론

이 글에서 다룬 `ThreadPoolTaskExecutor`의 `corePoolSize`/`maxPoolSize`/`queueCapacity` 예시 수치(8, 32, 50 등)는 특정 벤치마크나 실측 데이터에 기반한 권장값이 아니라 개념 설명을 위한 임의 값입니다. 실제 운영 환경에서는 CPU 코어 수, I/O 바운드/CPU 바운드 여부, 큐 적재로 인한 지연 허용치를 함께 고려해 값을 산정해야 하며, 이 글의 수치를 그대로 복사해 쓰는 것은 권장하지 않습니다. 또한 `AdviceMode.ASPECTJ`로 전환해 self-invocation 문제를 근본적으로 우회하는 방법은 이 글에서 개념만 언급했을 뿐 실제 빌드 설정(AspectJ 위버 플러그인 구성 등)은 다루지 않았으므로, 별도로 공식 문서를 참고해야 합니다. 마지막으로 가상 스레드(Virtual Threads) 환경에서 `SimpleAsyncTaskExecutor`의 동작이 달라질 수 있다는 점(JDK 21+ 대응)은 이 글의 범위 밖입니다.

## 참고문헌

1. Spring Framework Reference Documentation — "Task Execution and Scheduling" (`@Async`, self-invocation, `AsyncUncaughtExceptionHandler`, `SimpleAsyncTaskExecutor` 관련 공식 설명), https://docs.spring.io/spring-framework/reference/integration/scheduling.html (확인일: 2026-08-23)
2. Spring Framework Reference Documentation — "Using @Transactional" (`@Transactional` self-invocation 제약에 대한 공식 설명), https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html (확인일: 2026-08-23)
3. Spring Framework Javadoc — `ThreadPoolTaskExecutor` (`queueCapacity` 기본값과 스레드 확장 조건에 대한 공식 API 문서), https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/concurrent/ThreadPoolTaskExecutor.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 본문 전체를 관통하는 필자의 종합적 분석과 사견을 담고 있습니다.

`@Async`가 어려운 이유는 문법이 복잡해서가 아니라, 애노테이션 하나의 겉모습 뒤에 "프록시 기반 AOP"라는 동일한 메커니즘이 여러 기능(`@Transactional`, `@Cacheable` 등)에 공통으로 깔려 있다는 사실이 잘 드러나지 않기 때문이라고 봅니다. 이 글에서 다룬 self-invocation 문제도 결국 `@Async`만의 특이한 버그가 아니라, Spring AOP 프록시 방식을 쓰는 모든 애노테이션이 공유하는 구조적 제약을 `@Async` 맥락에서 다시 만난 것에 불과합니다. 예외 전파 문제와 기본 실행기 문제 역시 마찬가지로, "기본값이 곧 프로덕션에 적합한 값은 아니다"라는 일반적인 원칙이 `@Async`에도 그대로 적용된 사례입니다. 종합적으로 볼 때, `@Async`를 안전하게 쓰려면 애노테이션 자체보다 그 뒤에 있는 프록시 인터셉션 규칙, 예외 전파 경로, 실행기 설정이라는 세 가지 층위를 각각 이해하고 명시적으로 구성하는 태도가 필요하다고 판단합니다. 이는 비단 `@Async`뿐 아니라 Spring의 다른 AOP 기반 애노테이션을 도입할 때도 동일하게 적용할 수 있는 점검 기준이라고 생각합니다.

## 꼬리질문

- `@EnableAsync(mode = AdviceMode.ASPECTJ)`로 전환하면 self-invocation 문제가 실제로 해결되는지, 컴파일 타임/로드 타임 위빙 각각의 빌드 설정과 트레이드오프는 무엇인가?
- `CompletableFuture<Void>`를 반환하도록 리팩터링했을 때, `AsyncUncaughtExceptionHandler`를 쓰는 방식과 비교해 예외 처리 코드가 어떻게 달라지고 어느 쪽이 테스트하기 더 쉬운가?
- JDK 21 가상 스레드(Virtual Threads)를 `SimpleAsyncTaskExecutor`나 `ThreadPoolTaskExecutor`와 결합했을 때, 이 글에서 다룬 스레드 무제한 생성 위험이 어떻게 달라지는가?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html) — `@Async`의 self-invocation 문제와 근본 원인이 동일한 Spring 프록시 기반 AOP 메커니즘(JDK Dynamic Proxy / CGLIB) 자체를 다룬 글입니다.
- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html) — `@Async` 기반 스레드 풀 모델과 대비되는 리액티브 스레드 모델(Schedulers)을 다루고 있어, 비동기 처리 방식을 비교해 볼 수 있는 글입니다.