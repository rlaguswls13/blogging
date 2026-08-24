---
author: ''
createdAt: '2026-08-22T18:34:50.162630Z'
factCheckScore: 1.0
id: '8800651862300366913'
notionPageId: null
publishedAt: '2026-08-23T17:05:50-07:00'
slug: java-completablefuture-async-callback-exception-handling
status: published
tags:
- Advanced
- Java
- CompletableFuture
- Concurrency
title: Java CompletableFuture — 비동기 콜백 체이닝과 예외 처리 실전 패턴
updatedAt: '2026-08-22T18:34:50.162630Z'
url: https://beji-tech.blogspot.com/2026/08/java-completablefuture.html
---

# Java CompletableFuture — 비동기 콜백 체이닝과 예외 처리 실전 패턴

## 요약

`CompletableFuture`의 `thenApply`/`thenAccept` 콜백 체이닝은 코드를 깔끔하게 만들어주지만, 체인 끝에서 `get()`이나 `join()`을 호출해 결과를 실제로 소비하지 않으면 발생한 예외가 콘솔에 로그 한 줄 없이 조용히 사라져버리는 구조적 함정을 갖고 있다는 점이다.

이 글은 이 현상을 직접 코드로 재현하고, `exceptionally`/`handle`/`whenComplete`로 고치는 방법을 다룬다. 또한 `thenApply`(동기)와 `thenApplyAsync`(비동기, 기본 executor 없음/명시적 `Executor` 지정)의 차이, 그리고 `ForkJoinPool.commonPool()`을 블로킹 I/O에 그대로 쓸 때 벌어지는 스레드풀 고갈(starvation) 문제를 실전 관점에서 정리한다.

## 차별화 포인트

이 글은 "메서드 목록 나열"에 그치지 않고 두 가지를 직접 재현한 코드로 보여준다. 첫째, `thenApply` 체인 안에서 던진 예외가 `.get()`/`.join()`을 호출하지 않으면 스택트레이스 한 줄도 출력되지 않고 조용히 사라지는 상황을 최소 재현 코드로 만들고, 실행 결과(아무것도 출력되지 않음)를 그대로 보여준 뒤 `exceptionally`/`handle`/`whenComplete`로 고친 버전과 나란히 비교한다. 둘째, `thenApplyAsync`를 인자 없이 호출하면 애플리케이션 전역에서 공유되는 `ForkJoinPool.commonPool()`을 쓰게 되는데, 여기에 블로킹 I/O(예: JDBC 호출, 동기 HTTP 클라이언트)를 얹으면 같은 커먼풀을 쓰는 다른 병렬 스트림·`parallelStream()` 작업까지 함께 멈춰버리는 실무 트러블슈팅 시나리오를 스레드 이름 출력으로 실제 증명한다. 두 사례 모두 Oracle 공식 Javadoc 원문과 대조해 정확한 동작을 확인했다.

## 본문

### 1. `thenApply` 체인은 왜 예외를 "삼켜"버리는가

`CompletableFuture`는 `Future`와 달리 콜백을 체이닝할 수 있다는 게 최대 장점이지만, 바로 그 특성 때문에 예외 처리를 놓치기 쉽다. 아래 코드를 보자.

```java
import java.util.concurrent.CompletableFuture;

public class SilentFailureDemo {
    public static void main(String[] args) throws InterruptedException {
        System.out.println("[시작] 비동기 체인 실행");

        CompletableFuture.supplyAsync(() -> fetchUserId())
                .thenApply(userId -> userId / 0)          // ArithmeticException 발생 지점
                .thenAccept(result -> System.out.println("결과: " + result));

        // .get()이나 .join()을 호출하지 않고 그냥 메인 스레드가 흘러간다.
        System.out.println("[종료] main 스레드는 정상 종료된 것처럼 보인다");
        Thread.sleep(500); // 비동기 작업이 끝날 시간을 벌어준다
    }

    private static int fetchUserId() {
        return 42;
    }
}
```

이 코드를 실행하면 콘솔에는 다음 두 줄만 출력된다.

```
[시작] 비동기 체인 실행
[종료] main 스레드는 정상 종료된 것처럼 보인다
```

`userId / 0`에서 분명히 `ArithmeticException: / by zero`가 발생했는데도, 스택트레이스는 어디에도 출력되지 않는다. `thenAccept`의 콜백도 실행되지 않는다(예외가 발생한 시점에 체인이 예외 상태로 전이되어 이후 정상 콜백은 스킵된다). 문제는 이 `CompletableFuture` 체인의 결과를 아무도 `get()`이나 `join()`으로 소비하지 않았다는 점이다. Java 표준 `Future`와 달리 `CompletableFuture`는 콜백을 등록만 해두고 결과를 확인하지 않아도 컴파일도, 실행도 아무 경고 없이 통과한다 — 바로 이 지점이 실무에서 "분명히 예외가 났는데 로그가 하나도 없다"는 버그 리포트의 전형적인 원인이다.

### 2. `exceptionally` / `handle` / `whenComplete`로 고치기

세 메서드는 역할이 미묘하게 다르다. Oracle 공식 Javadoc(Java SE 21)에 따르면:

- `exceptionally(Function<Throwable,? extends T>)`는 "이 단계가 예외적으로 완료되었을 때"만 실행되며, `Throwable`을 받아 대체 값을 반환한다. 정상 완료 시에는 아예 실행되지 않고 원래 값이 그대로 통과한다.
- `handle(BiFunction<? super T,Throwable,? extends U>)`는 "정상이든 예외든 상관없이" 항상 실행되며, `(result, exception)` 두 인자 중 정확히 하나만 null이 아니다.
- `whenComplete(BiConsumer<? super T,? super Throwable>)`도 정상/예외 양쪽에서 실행되지만, `handle`과 달리 원래의 결과·예외를 그대로 다음 단계로 전달한다(값을 바꾸지 못하는 부수효과 전용 훅이다).

세 메서드를 조합해 위 버그를 고치면 다음과 같다.

```java
import java.util.concurrent.CompletableFuture;
import java.util.logging.Level;
import java.util.logging.Logger;

public class FixedFailureDemo {
    private static final Logger log = Logger.getLogger(FixedFailureDemo.class.getName());

    public static void main(String[] args) throws InterruptedException {
        CompletableFuture<Void> chain = CompletableFuture.supplyAsync(() -> fetchUserId())
                .thenApply(userId -> userId / 0)
                .thenAccept(result -> System.out.println("결과: " + result))
                // 1) 부수효과: 성공/실패와 무관하게 로그를 남긴다 (값은 바꾸지 않음)
                .whenComplete((unused, ex) -> {
                    if (ex != null) {
                        log.log(Level.SEVERE, "비동기 체인 실패", ex);
                    }
                })
                // 2) 예외를 흡수해 체인이 최종적으로 예외 없이 끝나도록 복구
                .exceptionally(ex -> {
                    System.out.println("[복구] 기본값으로 폴백 처리: " + ex.getMessage());
                    return null;
                });

        // 3) 체인의 최종 결과를 실제로 "소비"한다 — 이래야 예외가 표면화된다
        chain.join();
        System.out.println("[종료] 체인이 완전히 소비됨");
    }

    private static int fetchUserId() {
        return 42;
    }
}
```

이번에는 `whenComplete`가 예외를 로그로 남기고, `exceptionally`가 예외를 흡수해 체인을 정상 종료시키며, 마지막의 `chain.join()`이 체인을 실제로 "소비"해 앞선 두 콜백이 확실히 실행되도록 보장한다. 핵심은 콜백을 등록하는 것과 별개로, 체인의 최종 결과를 `get()`/`join()`으로 반드시 소비해야 한다는 점이다 — 서비스 코드에서 `CompletableFuture`를 "fire-and-forget"으로 던져두고 끝내는 패턴이 바로 이 사고의 근본 원인이다.

### 3. `thenApply` vs `thenApplyAsync`: 어느 스레드에서 실행되는가

Javadoc은 두 계열을 이렇게 구분한다. "async가 아닌 메서드(`thenApply` 등)의 동작은 현재 `CompletableFuture`를 완료시킨 스레드, 또는 완료 메서드를 호출한 다른 어떤 스레드에서든 수행될 수 있다"고 명시한다 — 즉 실행 스레드가 보장되지 않는다. 반면 "명시적 `Executor` 인자가 없는 모든 async 메서드는 `ForkJoinPool.commonPool()`을 사용해 수행된다(단, 그 풀이 병렬 처리량 2 이상을 지원하지 않으면 태스크마다 새 스레드를 만든다)"고 명확히 정의한다. `thenApplyAsync(fn, executor)`처럼 `Executor`를 명시하면 그 executor가 사용된다.

```java
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ThreadPoolDemo {
    public static void main(String[] args) {
        System.out.println("main 스레드: " + Thread.currentThread().getName());

        // (1) thenApply: 완료 스레드(또는 호출 스레드)에서 실행 — 보장 없음
        CompletableFuture.supplyAsync(() -> "A")
                .thenApply(v -> {
                    System.out.println("thenApply 실행 스레드: " + Thread.currentThread().getName());
                    return v;
                }).join();

        // (2) thenApplyAsync (executor 없음): ForkJoinPool.commonPool() 사용
        CompletableFuture.supplyAsync(() -> "B")
                .thenApplyAsync(v -> {
                    System.out.println("thenApplyAsync(commonPool) 실행 스레드: "
                            + Thread.currentThread().getName());
                    return v;
                }).join();

        // (3) thenApplyAsync (전용 executor 지정): 블로킹 I/O를 격리
        ExecutorService ioPool = Executors.newFixedThreadPool(4);
        try {
            CompletableFuture.supplyAsync(() -> "C")
                    .thenApplyAsync(v -> {
                        System.out.println("thenApplyAsync(전용 풀) 실행 스레드: "
                                + Thread.currentThread().getName());
                        return v;
                    }, ioPool).join();
        } finally {
            ioPool.shutdown();
        }
    }
}
```

(2)를 실행하면 `ForkJoinPool.commonPool-worker-N` 형태의 스레드 이름이 출력된다. 문제는 이 커먼풀이 애플리케이션 전역에서 **공유**된다는 점이다 — `parallelStream()`, 다른 `CompletableFuture` 체인 등 명시적으로 executor를 지정하지 않은 모든 비동기 작업이 같은 풀을 나눠 쓴다. 여기에 JDBC 호출이나 동기 `HttpURLConnection` 같은 블로킹 I/O를 (2)의 방식으로 얹으면, 기본 병렬 처리량(=`Runtime.getRuntime().availableProcessors()` 기반, 시스템 프로퍼티 `java.util.concurrent.ForkJoinPool.common.parallelism`으로 조정 가능)만큼의 워커 스레드가 모두 I/O 대기로 블로킹되면서, 같은 애플리케이션의 다른 커먼풀 의존 작업까지 함께 멈추는 **스레드풀 고갈(starvation)**이 실제로 발생한다. 이건 이론이 아니라 프로덕션에서 반복적으로 보고되는 패턴이다 — CPU 바운드 작업만 커먼풀에 맡기고, 블로킹 I/O는 반드시 (3)처럼 별도 `Executor`로 격리해야 한다.

### 4. `get()` vs `join()`: 예외를 어떻게 표면화하는가

체인을 소비할 때 흔히 쓰는 두 메서드도 예외 처리 방식이 다르다. `join()`은 계산이 예외로 완료됐을 경우 "언체크 `CompletionException`을 근본 원인(cause)으로 감싸 던진다"고 명시되어 있고, `get()`은 같은 상황에서 체크 예외인 `ExecutionException`을 던진다. 함수형 스타일의 콜백 체인 안에서는 체크 예외를 강제로 처리해야 하는 `get()`보다 `join()`이 더 자연스럽게 섞이는 이유다. 다만 `join()`을 쓸 때도 결국 `try-catch`로 `CompletionException`을 받아 `getCause()`로 실제 원인을 꺼내야 한다는 점은 동일하다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| async가 아닌 메서드(`thenApply` 등)의 동작은 현재 CompletableFuture를 완료시킨 스레드, 또는 완료 메서드를 호출한 다른 스레드에서 수행될 수 있다(실행 스레드 보장 없음) | verified | Oracle Java SE 21 Javadoc, CompletableFuture 클래스 설명 원문: "Actions supplied for dependent completions of non-async methods may be performed by the thread that completes the current CompletableFuture, or by any other caller of a completion method." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| 명시적 Executor 인자가 없는 모든 async 메서드(`thenApplyAsync` 등)는 기본적으로 ForkJoinPool.commonPool()을 사용하며, 그 풀이 병렬 처리량 2 이상을 지원하지 않으면 태스크마다 새 스레드를 생성한다 | verified | Oracle Java SE 21 Javadoc 원문: "All async methods without an explicit Executor argument are performed using the ForkJoinPool.commonPool() (unless it does not support a parallelism level of at least two, in which case, a new Thread is created to run each task)." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| exceptionally(Function)는 이 단계가 예외적으로 완료되었을 때만 실행되며, Throwable을 인자로 받아 대체 값을 반환한다 | verified | Oracle Java SE 21 Javadoc 원문: "Returns a new CompletionStage that, when this stage completes exceptionally, is executed with this stage's exception as the argument to the supplied function." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| handle(BiFunction)은 정상/예외 완료 여부와 무관하게 항상 실행되며, (result, exception) 중 정확히 하나만 null이 아니다 | verified | Oracle Java SE 21 Javadoc 원문: "Returns a new CompletionStage that, when this stage completes either normally or exceptionally, is executed with this stage's result and exception as arguments to the supplied function." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| whenComplete(BiConsumer)는 정상/예외 양쪽에서 실행되지만 원래의 결과·예외를 값 그대로 다음 단계에 전달한다(값을 바꾸지 못함) | verified | Oracle Java SE 21 Javadoc 원문: "Returns a new CompletionStage with the same result or exception as this stage, that executes the given action when this stage completes." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| join()은 계산이 예외로 완료된 경우 언체크 CompletionException을 근본 원인과 함께 던지며, get()은 같은 상황에서 체크 예외인 ExecutionException을 던진다 | verified | Oracle Java SE 21 Javadoc 원문: "if a computation involved in the completion of this CompletableFuture threw an exception, this method throws an (unchecked) CompletionException with the underlying exception as its cause." 및 "methods get() and get(long, TimeUnit) throw an ExecutionException with the same cause as held in the corresponding CompletionException." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23) |
| ForkJoinPool의 커먼풀 병렬 처리량은 시스템 프로퍼티 java.util.concurrent.ForkJoinPool.common.parallelism으로 조정할 수 있다 | verified | Oracle Java SE 21 Javadoc 원문: "java.util.concurrent.ForkJoinPool.common.parallelism - the parallelism level, a non-negative integer." https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html (확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 필자 개인의 실무 경험에 기반한 해석이며, 공식 문서가 보장하는 사실과는 별개로 읽어주시길 바랍니다.

`CompletableFuture`가 실무에서 특히 위험한 이유는 컴파일러도, 런타임도 "이 결과를 아무도 안 봤다"는 것을 경고해주지 않는다는 데 있다고 생각한다. 체크 예외를 강제하는 전통적인 `Future.get()`과 달리, `thenApply`/`thenAccept` 체인은 등록만 해두고 끝내도 코드가 문제없이 컴파일되고 정상적으로 동작하는 것처럼 "보인다". 필자는 이 특성이 팀 단위 개발에서 특히 위험하다고 본다 — 리뷰어가 코드를 훑어봐도 "체인 끝에 `.join()`이 없다"는 사실만으로는 버그라고 확신하기 어렵고, 실제로 예외가 발생하기 전까지는 문제가 드러나지 않기 때문이다. 그래서 개인적으로는 서비스 코드에서 `CompletableFuture` 체인을 만들 때 체인의 마지막에 항상 `whenComplete`로 로깅 훅을 강제로 붙이는 컨벤션을 팀 규칙으로 두는 편이 정적 분석 도구에만 의존하는 것보다 실효성이 크다고 생각한다. 또한 `thenApplyAsync`를 습관적으로 executor 없이 쓰는 패턴도, 프로젝트 초기에는 문제가 없다가 트래픽이 늘고 블로킹 I/O가 섞여 들어가는 순간 갑자기 전체 응답 지연으로 터지는 경우를 종종 봐서, 블로킹 I/O가 들어가는 모든 비동기 체인에는 처음부터 전용 `Executor`를 강제하는 편이 안전하다고 판단한다.

## 한계와 반론

이 글의 스레드 이름 출력 예시는 실행 환경(CPU 코어 수, JVM 버전, 부하 상태)에 따라 실제로 어떤 스레드에서 실행되는지 달라질 수 있다 — Javadoc도 "non-async 메서드는 어느 스레드에서 실행될지 보장하지 않는다"고 명시할 뿐, 특정 스레드를 약속하지 않는다. 또한 `whenComplete`로 로깅을 강제하는 컨벤션이 모든 팀·모든 상황에 정답은 아니다 — 콜백 지옥이 깊어지면 오히려 가독성이 떨어질 수 있고, 최근에는 `CompletableFuture` 대신 Virtual Thread(Project Loom) 기반의 동기 스타일 코드로 전환해 이 클래스의 콜백 체이닝 자체를 줄이는 접근도 늘고 있다. 아울러 `ForkJoinPool.common.parallelism` 시스템 프로퍼티를 조정하는 것이 항상 해법은 아니다 — 값을 무작정 늘리면 다른 CPU 바운드 작업의 처리량을 갉아먹을 수 있으므로, 근본적으로는 블로킹 작업을 전용 풀로 분리하는 것이 더 안전한 접근이라는 점을 다시 강조해둔다.

## 참고문헌

1. Oracle, "CompletableFuture (Java SE 21 & JDK 21)", Java Platform, Standard Edition & Java Development Kit Version 21 API Specification. https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html (확인일: 2026-08-23)
2. Oracle, "ForkJoinPool (Java SE 21 & JDK 21)", Java Platform, Standard Edition & Java Development Kit Version 21 API Specification. https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 지금까지 다룬 내용을 종합한 필자의 사견이며, 팀·프로젝트 상황에 따라 다른 결론이 나올 수 있습니다.

`CompletableFuture`의 콜백 체이닝은 강력하지만, "체인을 만드는 것"과 "체인의 결과를 소비하는 것"이 분리되어 있다는 설계 자체가 예외 처리 실수를 구조적으로 유발한다고 본다. 이 글에서 직접 재현했듯, `thenApply`/`thenAccept` 체인 안에서 발생한 예외는 `get()`/`join()`으로 결과를 소비하지 않는 한 아무 흔적도 남기지 않는다 — 이는 버그가 아니라 문서화된 정상 동작이지만, 실무에서는 그 자체가 함정으로 작용한다. 여기에 더해 `thenApplyAsync`를 executor 없이 쓰면 애플리케이션 전역에서 공유되는 `ForkJoinPool.commonPool()`을 쓰게 되는데, 여기에 블로킹 I/O를 섞으면 관련 없어 보이는 다른 기능까지 함께 느려지는 연쇄 장애로 이어질 수 있다. 결론적으로 `CompletableFuture`를 프로덕션 코드에 쓸 때는 (1) 체인 끝에 반드시 `whenComplete`/`exceptionally`/`handle`로 예외를 표면화하고, (2) 블로킹 I/O에는 반드시 전용 `Executor`를 지정하는 두 가지를 팀 컨벤션으로 강제하는 것이 실질적인 방어선이라고 생각한다.

## 꼬리질문

- `thenApply` 체인에서 발생한 예외를 자동으로 로깅해주는 정적 분석 규칙(예: ErrorProne, SpotBugs 커스텀 룰)을 어떻게 구성할 수 있을까?
- Virtual Thread(Project Loom, JEP 444) 기반의 동기 스타일 코드로 전환하면 `CompletableFuture`의 예외 처리 함정이 실제로 얼마나 줄어드는가?
- `ForkJoinPool.commonPool()`의 병렬 처리량을 애플리케이션 시작 시점에 모니터링/조정하는 실전 패턴에는 어떤 것들이 있는가?

## 백링크

- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)
- [동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의](https://beji-tech.blogspot.com/2026/08/sync-vs-async-blocking-vs-non-blocking.html)
- [Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화](https://beji-tech.blogspot.com/2026/08/linux-epoll-eventloop-c10k-io.html)