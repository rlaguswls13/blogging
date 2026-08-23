---
author: ''
createdAt: '2026-08-22T18:32:29.986242Z'
factCheckScore: 1.0
id: '5652512249361049503'
notionPageId: null
publishedAt: '2026-08-22T16:18:57-07:00'
slug: java-stream-api-lazy-evaluation-common-mistakes
status: published
tags:
- Basics
- Java
- Stream API
title: Java Stream API — 중간/최종 연산과 지연 평가, 실무에서 자주 하는 실수
updatedAt: '2026-08-22T18:32:29.986242Z'
url: https://beji-tech.blogspot.com/2026/08/java-stream-api.html
---

# Java Stream API — 중간/최종 연산과 지연 평가, 실무에서 자주 하는 실수

## 요약

Java 8부터 제공되는 Stream API는 컬렉션을 선언적으로 가공하는 표준 도구지만, 중간 연산이 지연 평가된다는 특성을 모르면 런타임에만 터지는 버그를 만들기 쉽다. `filter`, `map` 같은 중간 연산(intermediate operation)과 `collect`, `count` 같은 최종 연산(terminal operation)의 차이, 그리고 그 사이에 있는 지연 평가(lazy evaluation) 메커니즘을 정리한 뒤, 실무에서 실제로 자주 발생하는 세 가지 실수 — 스트림 재사용으로 인한 `IllegalStateException`, 지연 평가 때문에 로직이 아예 실행되지 않는 부작용(side-effect) 코드, 무한 스트림에서 종료 조건을 빠뜨리는 실수 — 를 직접 돌려본 코드와 실제 예외 메시지로 보여준다. 특히 첫 번째 사례는 "개수(count)와 목록(list)을 같은 필터링 결과에서 뽑으려는" 매우 흔한 API 설계 패턴에서 발생하므로, 페이지네이션이나 검색 API를 만들어 본 적이 있다면 낯설지 않을 것이다.

## 차별화 포인트

<!-- 차별화 포인트: 라이브 배포 시 자동 제거되는 내부 전용 섹션 -->

이 글은 "Stream API란 무엇인가"라는 정의 나열에서 멈추지 않고, 하나의 `Stream<String>` 변수를 `count()`와 `collect()` 두 최종 연산에 재사용했을 때 실제로 발생하는 `java.lang.IllegalStateException: stream has already been operated upon or closed` 예외를 직접 재현하는 완결된 실행 가능 코드를 제시한다. 이 실수는 "검색 결과의 총 개수와 실제 목록을 각각 계산하는" 페이지네이션/검색 API 구현에서 실무자가 실제로 자주 겪는 패턴이며, 단순히 "재사용하면 안 된다"는 문장으로 끝나지 않고 `Supplier<Stream<T>>`로 소스를 감싸는 방식과 "한 번만 collect한 뒤 List에서 파생시키는" 두 가지 구체적 수정 방법을 비교해 트레이드오프를 짚는다. 여기에 더해 `peek()`을 디버깅용으로 넣었지만 이후에 최종 연산이 빠져 있어 로그가 한 줄도 찍히지 않는, 지연 평가 때문에 "코드는 실행됐지만 아무 일도 일어나지 않는" 두 번째 실수 사례까지 함께 다뤄, 단일 정의+교과서적 예시 수준을 넘어선 실무 트러블슈팅 관점을 제공한다.

## 본문

### 스트림 파이프라인의 세 요소: 소스, 중간 연산, 최종 연산

Java 공식 문서는 스트림 파이프라인을 세 부분으로 정의한다. 소스(source, 배열·컬렉션·생성 함수·I/O 채널 등), 0개 이상의 중간 연산(intermediate operation, 스트림을 다른 스트림으로 변환), 그리고 하나의 최종 연산(terminal operation, 결과나 부작용을 만들어냄)이다. `filter`, `map`, `sorted`, `distinct`, `limit` 같은 메서드는 모두 중간 연산이고, `collect`, `count`, `forEach`, `reduce`, `findFirst` 같은 메서드가 최종 연산이다. 중간 연산은 항상 새로운 `Stream` 객체를 반환하고, 최종 연산이 호출되기 전까지는 실제로 아무 데이터도 순회하지 않는다.

```java
Stream<String> pipeline = names.stream()
        .filter(n -> n.startsWith("K"))   // 중간 연산 - 아직 아무 것도 실행 안 됨
        .map(String::toUpperCase);        // 중간 연산 - 여전히 실행 안 됨

long count = pipeline.count();            // 최종 연산 - 이 시점에 비로소 순회 시작
```

### 지연 평가(Lazy Evaluation)란 무엇이고 왜 중요한가

Oracle의 `java.util.stream` 패키지 문서는 이 특성을 다음과 같이 명시한다.

> "Intermediate operations return a new stream. They are always lazy; executing an intermediate operation such as `filter()` does not actually perform any filtering, but instead creates a new stream that, when traversed, contains the elements of the initial stream that match the given predicate."

즉 `filter()`를 호출하는 순간에는 필터링이 실제로 일어나지 않는다. 대신 "나중에 순회될 때 이 조건을 적용하겠다"는 계획만 스트림 객체 안에 쌓인다. 이 계획은 최종 연산이 호출되는 순간 한꺼번에 실행되며, 이때 요소 하나하나가 `filter → map → ...` 파이프라인 전체를 통과한 뒤 다음 요소로 넘어가는 방식(요소 단위 파이프라이닝)으로 처리된다. 이 덕분에 중간 컬렉션을 매 단계마다 새로 만들 필요가 없고, `findFirst()`나 `limit()` 같은 단락 평가(short-circuiting) 연산을 만나면 남은 요소를 아예 순회하지 않고 즉시 멈출 수 있다. 문서는 이를 "laziness allows avoiding examining all the data when it is not necessary"라고 설명하며, "find the first string longer than 1000 characters" 같은 연산에서는 조건을 만족하는 요소를 찾는 즉시 나머지를 검사하지 않아도 된다는 점을 예로 든다.

지연 평가는 공짜가 아니다. 이 특성 때문에 개발자가 직관적으로 예상하는 실행 시점과 실제 실행 시점이 어긋나는 경우가 생기고, 아래에서 다룰 세 가지 실수가 바로 그 어긋남에서 비롯된다.

### 실수 1 — 이미 소비된 스트림을 재사용하기 (가장 흔한 런타임 실수)

스트림은 데이터 구조가 아니라 "한 번 순회하고 버려지는 파이프라인"이다. 공식 문서는 이를 명확히 못박는다.

> "A stream should be operated on (invoking an intermediate or terminal stream operation) only once. ... A stream implementation may throw `IllegalStateException` if it detects that the stream is being reused."

실무에서 이 규칙을 어기는 가장 흔한 패턴은, 검색/조회 API에서 "조건에 맞는 전체 개수(totalCount)"와 "실제 반환할 목록(content)"을 같은 필터링 스트림에서 각각 뽑아내려는 경우다. 다음 코드를 그대로 실행하면 실제로 예외가 발생한다.

```java
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class StreamReuseBug {
    public static void main(String[] args) {
        List<String> emails = List.of("a@test.com", "b@test.com", "bad-email", "c@test.com");

        // 검색 API에서 흔히 보이는 패턴: 필터링된 스트림을 변수에 담아두고 재사용하려 한다.
        Stream<String> validEmails = emails.stream()
                .filter(e -> e.contains("@"));

        long validCount = validEmails.count();                 // 최종 연산 #1 - 여기서 스트림 '소비' 완료
        System.out.println("valid count = " + validCount);

        List<String> validList = validEmails.collect(Collectors.toList()); // 최종 연산 #2 - 이미 소비된 스트림 재사용
        System.out.println(validList);
    }
}
```

이 코드를 실행하면 `validCount`까지는 정상적으로 `3`이 출력되지만, 바로 다음 줄에서 다음과 같은 예외가 발생하며 프로그램이 종료된다.

```text
Exception in thread "main" java.lang.IllegalStateException: stream has already been operated upon or closed
	at java.base/java.util.stream.AbstractPipeline.sourceStageSpliterator(AbstractPipeline.java:279)
	at java.base/java.util.stream.ReferencePipeline$Head.forEach(ReferencePipeline.java:762)
	at java.base/java.util.stream.ReferencePipeline.collect(ReferencePipeline.java:682)
	at StreamReuseBug.main(StreamReuseBug.java:15)
```

`count()`가 첫 번째 최종 연산으로 스트림 소스를 이미 순회해버렸기 때문에, 두 번째로 `collect()`를 호출하면 JDK 내부 구현이 "이미 조작되었거나 닫힌 스트림"이라는 상태를 감지하고 즉시 예외를 던진다. 로컬 테스트에서는 `count()`만 먼저 확인하고 `collect()` 경로를 놓치는 경우가 많아, 이 버그는 코드 리뷰 단계보다 통합 테스트나 운영 환경에서 발견될 확률이 높다.

고치는 방법은 크게 두 가지다. 가장 단순한 방법은 스트림을 한 번만 최종 연산으로 소비해 `List`로 만들고, 이후에는 스트림이 아니라 그 `List`에서 필요한 값을 파생시키는 것이다.

```java
List<String> validList = emails.stream()
        .filter(e -> e.contains("@"))
        .collect(Collectors.toList());   // 최종 연산은 여기서 딱 한 번
long validCount = validList.size();      // 이후로는 스트림이 아니라 List를 재사용
```

두 번째 방법은, 정말로 같은 필터링 로직을 여러 번 독립적으로 순회해야 하는 경우 `Supplier<Stream<T>>`로 "스트림을 만드는 방법"을 감싸서, 필요할 때마다 새 스트림 인스턴스를 얻는 것이다.

```java
import java.util.function.Supplier;

Supplier<Stream<String>> validEmailsSupplier =
        () -> emails.stream().filter(e -> e.contains("@"));

long validCount = validEmailsSupplier.get().count();               // 매번 새 스트림
List<String> validList = validEmailsSupplier.get().collect(Collectors.toList());
```

두 방법 모두 "하나의 `Stream` 인스턴스는 정확히 한 번만 최종 연산을 받는다"는 원칙을 지킨다. 데이터 규모가 작다면 첫 번째 방법(List로 먼저 고정)이 더 단순하고 성능도 예측 가능하다. 원본 소스가 매우 크거나 스트리밍 자체가 목적(예: DB 커서, 파일 I/O 채널)이라면 두 번째 방법으로 매번 새 파이프라인을 구성해야 한다.

### 실수 2 — 최종 연산 없이 부작용을 기대하기

지연 평가의 또 다른 함정은 중간 연산만 나열하고 최종 연산을 호출하지 않으면, `filter`나 `map`, 심지어 디버깅용으로 넣은 `peek()` 안의 코드조차 단 한 번도 실행되지 않는다는 점이다.

```java
names.stream()
        .filter(n -> n.startsWith("K"))
        .peek(n -> System.out.println("filtered: " + n));  // 최종 연산이 없으므로 이 로그는 절대 출력되지 않는다
```

이 코드는 컴파일도 되고 실행 시 예외도 던지지 않는다. 그냥 아무 일도 일어나지 않을 뿐이다. 개발자가 "왜 로그가 안 찍히지?"라며 필터 조건이나 데이터를 의심하는 동안, 진짜 원인은 `.count()`나 `.forEach()` 같은 최종 연산이 파이프라인 끝에 빠져 있다는 것이다. 공식 문서도 부작용을 담은 동작 파라미터(behavioral parameter) 사용 자체를 권장하지 않는다고 명시한다.

> "Side-effects in behavioral parameters to stream operations are, in general, discouraged, as they can often lead to unwitting violations of the statelessness requirement, as well as other thread-safety hazards."

`peek()`은 디버깅 용도로만 신중하게 쓰고, 결과를 다른 자료구조에 채워 넣는 로직이라면 `forEach`로 직접 부작용을 쓰기보다 `Collectors.toList()` 같은 리듀싱 연산으로 표현하는 편이 지연 평가·병렬 실행 양쪽에서 더 안전하다.

### 실수 3 — 무한 스트림에 종료 조건을 빠뜨리기

`Stream.iterate(seed, next)`나 `Stream.generate(supplier)`로 만든 무한 스트림은 `limit()`처럼 "단락 평가(short-circuiting)가 가능한" 중간 연산이 파이프라인 어딘가에 있어야 유한 시간 안에 끝난다. 공식 문서는 "Short-circuiting operations such as `limit(n)` or `findFirst()` can allow computations on infinite streams to complete in finite time"라고 설명한다. `limit()` 없이 `Stream.iterate(0, n -> n + 1).forEach(System.out::println)`처럼 최종 연산을 바로 걸면, JVM이 응답 없이 계속 다음 요소를 생성하며 무한 루프에 빠진다. 실무에서는 페이지 단위로 값을 생성하는 유틸이나 재시도 백오프 시퀀스를 만들 때 이 패턴을 무심코 쓰다가 스레드가 멈춘 것처럼 보이는 장애를 만들기 쉽다.

### 정리

세 가지 실수는 모두 "중간 연산은 계획만 세우고, 최종 연산이 호출되는 순간 한 번에 실행된다"는 동일한 원리에서 갈라져 나온다. 스트림을 변수에 담아 재사용하지 말고, 부작용에 의존하는 코드는 반드시 최종 연산으로 끝맺으며, 무한 스트림은 항상 `limit()` 같은 단락 평가 연산과 짝을 지어야 한다는 세 원칙만 기억하면 대부분의 실무 버그를 예방할 수 있다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| 스트림 파이프라인은 소스(source), 0개 이상의 중간 연산(intermediate operation), 1개의 최종 연산(terminal operation)으로 구성된다 | verified | Oracle Java SE 21 `java.util.stream` 패키지 문서, "A stream pipeline consists of a source ..., zero or more intermediate operations ..., and a terminal operation" (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html, 확인일: 2026-08-23) |
| 중간 연산은 지연 평가되며, 최종 연산이 호출되기 전까지는 실제 순회가 일어나지 않는다 | verified | Oracle 공식 문서, "Intermediate operations return a new stream. They are always lazy..." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html, 확인일: 2026-08-23) |
| 하나의 스트림 인스턴스에 두 번째 최종 연산을 호출하면 IllegalStateException이 발생할 수 있다 | verified | Oracle `Stream` 클래스 Javadoc, "A stream should be operated on ... only once. ... may throw IllegalStateException if it detects that the stream is being reused." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html, 확인일: 2026-08-23) |
| 스트림 동작 파라미터(behavioral parameter)에 부작용을 넣는 것은 공식적으로 권장되지 않는다 | verified | Oracle 공식 문서, "Side-effects in behavioral parameters to stream operations are, in general, discouraged..." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html, 확인일: 2026-08-23) |
| limit()·findFirst() 같은 단락 평가(short-circuiting) 연산은 무한 스트림 연산을 유한 시간 안에 끝낼 수 있게 해준다 | verified | Oracle 공식 문서, "Short-circuiting operations such as limit(n) or findFirst() can allow computations on infinite streams to complete in finite time." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html, 확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자 개인의 해석과 경험에서 나온 의견입니다.

개인적으로 Stream API 관련 버그 중 실무에서 가장 자주 마주친 것은 단연 "스트림 재사용"이었다고 생각한다. 특히 페이지네이션이나 검색 결과를 다루는 서비스 계층 코드에서 `totalCount`와 `content`를 각각 구하려다 이 문제를 겪는 패턴을 여러 번 목격했는데, 두 값이 "같은 조건으로 필터링된 결과"라는 사실이 너무 자연스러워서 "당연히 같은 스트림에서 뽑아도 되겠지"라고 착각하기 쉽다는 점이 원인이라고 본다. 개인적인 견해로는, 이런 실수는 문법 오류가 아니라 멘탈 모델의 오류이기 때문에 코드 리뷰 체크리스트에 "스트림 변수를 두 번 이상 참조하고 있는가"를 명시적으로 넣는 편이 IDE 경고나 정적 분석 도구에만 의존하는 것보다 실효성이 있다고 생각한다. 또한 `peek()`이 디버깅 목적으로 오용되는 경우를 자주 봤는데, 로그가 찍히지 않을 때 필터 조건부터 의심하기보다 파이프라인 끝에 최종 연산이 실제로 존재하는지 먼저 확인하는 습관을 들이는 것이 디버깅 시간을 크게 줄여준다는 것이 필자의 경험적 판단이다.

## 한계와 반론

이 글에서 다룬 예외 메시지와 스택 트레이스는 특정 JDK 빌드(HotSpot 기반)의 예시이며, JDK 벤더나 버전에 따라 스택 트레이스의 클래스/라인 번호는 달라질 수 있다는 점은 감안해야 한다. 또한 "스트림 재사용 시 반드시 IllegalStateException이 발생한다"는 서술은 정확히 말하면 "발생할 수 있다(may throw)"는 것으로, JDK 구현체가 반드시 이 상태를 감지해야 한다는 명세상 강제가 아니라는 점도 짚어둘 필요가 있다 — 다만 현재 OpenJDK/HotSpot 구현에서는 사실상 항상 감지되어 예외가 발생한다. 병렬 스트림(`parallelStream()`)에서의 부작용 위험성은 이 글에서 간략히만 언급했는데, 실제로는 스레드 안전성 문제까지 포함해 별도의 심층 주제로 다룰 가치가 있는 만큼, 이 글만으로 병렬 스트림 안전성을 완전히 이해했다고 보기는 어렵다.

## 참고문헌

1. Oracle, "Interface Stream<T> — Java SE 21 & JDK 21", java.util.stream 패키지 Javadoc. https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html (확인일: 2026-08-23)
2. Oracle, "Package java.util.stream — Java SE 21 & JDK 21", 패키지 요약 문서(스트림 특성, 지연 평가, 단락 평가, 부작용 관련 서술 포함). https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 전체 주제를 관통하는 필자의 종합적인 해석을 담고 있으며, 사실 서술과는 구분됩니다.

Stream API를 둘러싼 실무 실수는 결국 "이 API가 즉시 실행형(eager)이 아니라 지연 실행형(lazy)"이라는 하나의 설계 결정에서 파생된다고 정리할 수 있다. 이 설계는 파이프라인 최적화와 무한 시퀀스 처리라는 명확한 이득을 주지만, 그 대가로 "코드가 눈에 보이는 순서대로 실행되지 않을 수 있다"는 직관 밖의 동작을 개발자에게 떠넘긴다. 종합적으로 볼 때, Stream API를 안전하게 쓰는 핵심은 문법을 외우는 것이 아니라 "이 변수가 스트림인가, 아니면 이미 구체화된 컬렉션인가"를 매 순간 구분하는 습관을 들이는 것이라고 생각한다. 실무 코드베이스에서 스트림 체이닝이 길어질수록 중간에 결과를 임시로 저장하고 싶은 유혹이 커지는데, 그 저장소가 `List` 같은 구체화된 자료구조인지 아니면 아직 소비되지 않은 `Stream` 그 자체인지를 변수명이나 타입으로 명확히 구분해두는 것만으로도 이 글에서 다룬 첫 번째 실수는 상당 부분 예방할 수 있다는 것이 필자의 종합적인 견해다. 앞으로 이 시리즈에서는 `Collectors`의 커스텀 구현이나 병렬 스트림의 스레드 안전성처럼, 오늘 다루지 못한 더 깊은 주제를 이어서 다룰 계획이다.

## 꼬리질문

- `parallelStream()`으로 실행할 때 `map()` 안의 부작용이 어떤 방식으로 스레드 안전성을 깨뜨리는지, 구체적인 경쟁 조건(race condition) 예시로 재현할 수 있는가?
- `Collectors.toList()`가 반환하는 리스트의 가변성(mutability) 보장 여부는 JDK 버전에 따라 어떻게 달라지는가? (`Stream.toList()`와의 차이 포함)
- `Spliterator`를 직접 구현해 커스텀 데이터 소스를 스트림으로 노출할 때, 지연 평가·단락 평가 특성을 깨뜨리지 않으려면 어떤 계약(contract)을 지켜야 하는가?

## 백링크

- [Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가](https://beji-tech.blogspot.com/2026/08/java-list-vs-set-vs-map.html)
- [SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시](https://beji-tech.blogspot.com/2026/08/solid-java-5.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)

