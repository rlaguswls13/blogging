---
author: ''
createdAt: '2026-08-22T18:32:47.313778Z'
factCheckScore: 0
id: '6018427474278816240'
notionPageId: null
publishedAt: '2026-08-22T16:19:02-07:00'
slug: java-optional-null-safety-anti-patterns
status: published
tags:
- Basics
- Java
- Optional
title: Java Optional — null 안전성 올바른 사용법과 안티패턴
updatedAt: '2026-08-22T18:32:47.313778Z'
url: https://beji-tech.blogspot.com/2026/08/java-optional-null.html
---

# Java Optional — null 안전성 올바른 사용법과 안티패턴

## 요약

`Optional` 클래스는 Java 8부터 `null` 대신 "값이 없을 수 있다"는 상태를 타입으로 표현하기 위해 도입된 컨테이너 클래스다. 그러나 실무 코드베이스에서는 필드, 파라미터, 심지어 직렬화되는 DTO에까지 `Optional`을 습관적으로 붙이거나, `isPresent()` 체크 없이 `get()`을 호출하는 경우가 흔하다. 이 글은 Optional을 그냥 정의하고 넘어가는 대신, 실제로 NPE·직렬화 예외를 일으키는 5가지 안티패턴을 Before/After 코드로 보여주고, 각각이 왜 문제인지를 JDK 공식 Javadoc과 Jackson 라이브러리의 실제 동작 변화를 근거로 설명한다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어. 이 글이 같은 주제 상위 검색결과 대비 무엇을 더하는지 최소 1가지를 구체적으로
쓸 것 (wiki/Blog_Writing_Rules.md 14번 수칙) — 예: 직접 돌려본 벤치마크 수치, 실제 겪은 프로덕션
이슈/장애, 흔치 않은 조합/트레이드오프, 다른 곳에서 보기 힘든 비교표, 실제 실행해보고 확인한 예상 밖
동작. "정의 + 교과서적 예시"만 있는 포화 101 주제(GoF 패턴류 등)는 이 각도 없이는 신규 작성을 지양한다.
-->

Optional 소개 글은 이미 검색 상위에 수십 개가 있지만, 대부분 "값이 있으면 map, 없으면 orElse" 수준의 API 나열에 그친다. 이 글의 차별점은 두 가지다. 첫째, Optional을 필드/파라미터/DTO에 쓰면 "왜 나쁜가"를 추상적으로 말하지 않고, 각 안티패턴이 실제로 어떤 예외(NullPointerException, `InvalidDefinitionException` 등)를 어떤 조건에서 던지는지 Before/After 코드로 재현 가능하게 보여준다. 둘째, Jackson 2.16 이후 `Optional` 필드 직렬화 시 발생하는 `InvalidDefinitionException` 회귀(jackson-databind GitHub 이슈 #4499)처럼, 국내 Optional 입문 글에서는 거의 다루지 않는 최신(2026년 기준) 라이브러리 동작 변화를 실제 이슈 트래커 원문 대조로 반영했다.

## 본문

<!--
게시 게이트(src/core/publish_gate.json::sectionMinWords) 기준 최소 800단어.
코드펜스(예: ```java ... ```) 또는 이미지 중 최소 1개는 반드시 포함할 것 — 둘 다 없으면
발행 게이트에서 오류로 차단된다(2026-08-22부터 경고 아님).
-->

### Optional은 왜 만들어졌나

`java.util.Optional<T>`는 Java 8(JDK 8)에서 도입된 "값이 있을 수도, 없을 수도 있는" 상태를 표현하는 불변 컨테이너 클래스다. Oracle 공식 Javadoc은 클래스 설명에 다음과 같은 API Note를 명시한다.

> "Optional is primarily intended for use as a method return type where there is a clear need to represent 'no result,' and where using null is likely to cause errors."

핵심은 "method return type"이라는 단어다. Optional은 애초에 메서드의 반환 타입으로 쓰라고 설계된 것이지, 클래스 필드나 메서드 파라미터, DTO의 데이터 캐리어로 쓰라고 만든 게 아니다. Java 언어 아키텍트인 Brian Goetz도 Stack Overflow 답변에서 "라이브러리 메서드가 결과를 반환하지 못할 수 있음을 명확히 표현해야 할 때 쓰는 제한적인 메커니즘"이라고 그 용도를 못박았다. 이 설계 의도를 이해하면 아래 안티패턴들이 왜 문제인지가 명확해진다.

### 안티패턴 1 — Optional을 클래스 필드로 사용하기

```java
// Before: 안티패턴 — Optional을 필드 타입으로 선언
public class Member {
    private String name;
    private Optional<String> nickname; // 문제의 필드

    public Member(String name, Optional<String> nickname) {
        this.name = name;
        this.nickname = nickname;
    }
}
```

이 코드는 두 가지 방식으로 깨질 수 있다. 첫째, Javadoc이 "Optional 타입 변수는 절대 null 자체가 되어서는 안 된다"고 명시하지만, 생성자 인자로 `null`이 그대로 전달되는 걸 막을 방법이 없다. 즉 `new Member("kim", null)`을 호출하면 `nickname` 필드가 `null`이 되어, Optional을 쓴 의미가 사라지고 오히려 `member.getNickname().isPresent()`에서 NPE가 난다. 둘째, `Optional`은 `Serializable`을 구현하지 않는다 — Oracle Javadoc의 클래스 선언은 `public final class Optional<T> extends Object`로, 어떤 인터페이스도 구현하지 않는다. 즉 이 필드를 가진 객체를 Java 직렬화(`ObjectOutputStream`)로 저장하려 하면 `NotSerializableException`이 발생한다.

```java
// After: 필드는 nullable 참조로 두고, 접근 시점에만 Optional로 감싼다
public class Member {
    private String name;
    private String nickname; // null 허용, 필드 자체는 Optional이 아님

    public Member(String name, String nickname) {
        this.name = name;
        this.nickname = nickname;
    }

    // 값을 꺼내 쓰는 지점에서만 Optional로 감싸 API를 명확히 한다
    public Optional<String> getNickname() {
        return Optional.ofNullable(nickname);
    }
}
```

필드는 그대로 `null` 허용 참조로 두고, "값이 없을 수 있다"는 신호는 getter의 반환 타입에서만 표현한다. 이것이 Optional의 원래 설계 의도인 "반환 타입"과 정확히 일치한다.

### 안티패턴 2 — isPresent() 체크 없이 get() 호출하기

```java
// Before: get()을 그냥 호출 — Optional을 쓴 의미가 없다
Optional<Member> memberOpt = repository.findById(id);
Member member = memberOpt.get(); // 값이 없으면 NoSuchElementException
```

`get()`을 무조건 호출하는 코드는 사실상 `null.someMethod()`와 다를 바 없는 위험을 그대로 옮겨놓은 것이다. 다만 예외 타입만 `NullPointerException`에서 `NoSuchElementException`으로 바뀔 뿐이다. Oracle 공식 Javadoc의 `get()` 메서드 설명에는 API Note로 "The preferred alternative to this method is `orElseThrow()`"라고 명시되어 있다 — `get()`은 존재하지만 권장되지 않는 메서드라는 뜻이다.

```java
// After: 의도를 드러내는 방식으로 값을 꺼낸다
Member member = repository.findById(id)
    .orElseThrow(() -> new MemberNotFoundException(id));

// 또는 기본값으로 대체
String displayName = repository.findById(id)
    .map(Member::getName)
    .orElse("탈퇴한 회원");
```

`orElseThrow()`는 `get()`과 동일하게 값이 없으면 예외를 던지지만, 어떤 예외를 던질지 호출부에서 명시적으로 선택할 수 있어 디버깅 시 원인 파악이 훨씬 쉽다. `orElse`/`map`은 값이 없는 경우의 대체 로직을 코드 흐름 안에서 표현하므로 분기문(`if (member == null)`)이 사라진다.

### 안티패턴 3 — Optional.of(null)의 NPE 트랩

```java
// Before: of()에 null이 들어올 수 있는 값을 넣는 실수
String externalValue = fetchFromExternalApi(); // null일 수 있음
Optional<String> opt = Optional.of(externalValue); // externalValue가 null이면 즉시 NPE
```

Oracle Javadoc은 `Optional.of(T value)`에 대해 "Throws: NullPointerException - if value is null"이라고 명시한다. `of()`는 "값이 확실히 존재한다"는 걸 전제로 하는 팩토리 메서드이기 때문에, `null`이 들어오면 그 자리에서 바로 `NullPointerException`을 던지도록 설계되어 있다. 이는 버그가 아니라 의도된 동작이지만, 외부 API 응답이나 DB 조회 결과처럼 `null` 가능성이 있는 값에 실수로 `of()`를 쓰면 오히려 순수 `null` 참조보다 더 이른 시점에, 그러나 여전히 예상치 못한 곳에서 NPE가 터진다.

```java
// After: null 가능성이 있는 값은 ofNullable()로 감싼다
String externalValue = fetchFromExternalApi();
Optional<String> opt = Optional.ofNullable(externalValue); // null이면 빈 Optional
```

`of()`는 "이 값은 null이 아님을 내가 보장한다"는 명시적 계약이고, `ofNullable()`은 "null일 수도 있다"는 것을 전제로 한 팩토리 메서드다. 값의 출처가 외부 시스템이나 사용자 입력이라면 반드시 `ofNullable()`을 써야 한다.

### 안티패턴 4 — Optional을 메서드 파라미터로 사용하기

```java
// Before: 파라미터 타입으로 Optional 사용
public void updateNickname(Member member, Optional<String> nickname) {
    member.setNickname(nickname.orElse(null));
}

// 호출부가 오히려 번거로워진다
updateNickname(member, Optional.of("newName"));
updateNickname(member, Optional.empty()); // null 대신 명시적으로 감싸야 함
```

파라미터에 Optional을 쓰면 호출부가 `Optional.of(...)`나 `Optional.empty()`로 값을 감싸야 하는 불필요한 보일러플레이트가 생기고, 여전히 호출자가 `null`을 그대로 넘기는 걸 막을 방법이 없다 — 컴파일러는 `Optional<String>` 타입 파라미터에 `null`을 넣는 것도 허용한다. 즉 필드와 마찬가지로 "Optional 자체가 null이면 안 된다"는 계약을 타입 시스템이 강제해주지 못한다.

```java
// After: 오버로드 또는 nullable 파라미터 + 메서드 내부에서만 Optional 활용
public void updateNickname(Member member, String nickname) {
    member.setNickname(nickname); // 필요하면 내부에서만 Optional.ofNullable 사용
}
```

파라미터가 선택적이라는 걸 표현하고 싶다면 오버로드 메서드를 추가하거나, 빌더 패턴을 쓰는 편이 Optional 파라미터보다 호출부 코드를 단순하게 만든다.

### 안티패턴 5 — 직렬화되는 DTO 필드에 Optional 사용하기

```java
// Before: REST API 응답 DTO에 Optional 필드 사용
public class MemberResponseDto {
    private String name;
    private Optional<String> nickname; // JSON으로 직렬화될 DTO

    // getter/setter 생략
}
```

Spring Boot 같은 프레임워크에서 이 DTO를 Jackson으로 JSON 직렬화하면 문제가 생긴다. Jackson은 기본적으로 `Optional`을 특별 취급하지 않는 일반 POJO처럼 다루기 때문에, `jackson-datatype-jdk8` 모듈 없이 직렬화하면 `{"nickname":"kim"}`이 아니라 `Optional` 객체 내부 구조가 그대로 노출되는(`{"present":true}`류) 결과가 나오거나, 최신 버전에서는 아예 예외가 발생한다. 실제로 jackson-databind GitHub 이슈 #4499에 따르면 2.16.0부터는 `Jdk8Module`을 명시적으로 등록하지 않은 상태에서 `Optional` 필드를 직렬화하려 하면 다음과 같은 메시지의 `InvalidDefinitionException`이 발생한다.

```
Java 8 optional type java.util.Optional not supported by default:
add Module 'com.fasterxml.jackson.datatype:jackson-datatype-jdk8' to enable handling
```

즉 로컬 개발 환경에서는 우연히 구버전 Jackson이나 이미 등록된 모듈 덕분에 동작하던 코드가, 라이브러리 버전을 올리는 순간 프로덕션 API에서 500 에러로 터질 수 있다는 뜻이다.

```java
// After: DTO는 순수 nullable 필드로, Optional은 서비스 계층에서만 사용
public class MemberResponseDto {
    private String name;
    private String nickname; // null이면 JSON에서 "nickname": null (또는 필드 생략)

    // getter/setter 생략
}

// 서비스 계층에서 값을 조립할 때만 Optional 활용
MemberResponseDto toDto(Member member) {
    MemberResponseDto dto = new MemberResponseDto();
    dto.setName(member.getName());
    dto.setNickname(Optional.ofNullable(member.getNickname()).orElse(null));
    return dto;
}
```

DTO나 Entity처럼 직렬화·영속화 대상이 되는 클래스는 Optional을 필드 타입으로 절대 노출하지 않고, 값을 조립하는 서비스 계층 로직 내부에서만 Optional의 `map`/`orElse` 체이닝을 활용하는 것이 안전하다.

### 정리: Optional을 쓸 때와 쓰지 않을 때

Optional은 "메서드가 값을 못 찾을 수도 있다"는 사실을 시그니처에 드러내고 싶을 때, 그리고 그 반환값을 곧바로 `map`/`filter`/`orElse` 체이닝으로 처리할 때 가장 효과적이다. 반대로 필드, 파라미터, DTO처럼 "값을 담아 옮기는" 용도로 쓰면 원래 설계 의도에서 벗어나 직렬화 실패, NPE, 불필요한 보일러플레이트라는 부작용만 남는다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Optional은 "메서드 반환 타입"으로 사용하도록 설계되었다는 공식 API Note가 존재한다 | verified | Oracle Java SE 21 Javadoc, `java.util.Optional` 클래스 설명 API Note: "Optional is primarily intended for use as a method return type where there is a clear need to represent 'no result,' and where using null is likely to cause errors." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html, 확인일: 2026-08-22) |
| Optional 타입 변수 자체는 null이 되어서는 안 된다고 Javadoc이 명시한다 | verified | 동일 Javadoc: "A variable whose type is Optional should never itself be null; it should always point to an Optional instance." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html, 확인일: 2026-08-22) |
| Optional.of(null)은 NullPointerException을 던진다 | verified | Oracle Java SE 21 Javadoc, `Optional.of(T value)` 메서드 Throws 절: "NullPointerException - if value is null" (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html#of(T), 확인일: 2026-08-22) |
| get()보다 orElseThrow()가 공식적으로 권장된다 | verified | 동일 Javadoc, `get()` 메서드 API Note: "The preferred alternative to this method is orElseThrow()." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html#get(), 확인일: 2026-08-22) |
| Optional 클래스는 Serializable을 구현하지 않는다 | verified | Oracle Java SE 21 Javadoc, 클래스 선언: "public final class Optional<T> extends Object" — 구현 인터페이스 목록에 Serializable이 없음 (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html, 확인일: 2026-08-22) |
| Jackson 2.16.0부터는 jackson-datatype-jdk8 모듈 없이 Optional 필드를 직렬화하면 InvalidDefinitionException이 발생한다 | verified | FasterXML/jackson-databind GitHub 이슈 #4499 원문 대조 — 2.15.4까지는 별도 모듈 없이 동작했으나 2.16.0부터 "Java 8 optional type java.util.Optional not supported by default: add Module 'com.fasterxml.jackson.datatype:jackson-datatype-jdk8' to enable handling" 메시지와 함께 InvalidDefinitionException 발생 (https://github.com/FasterXML/jackson-databind/issues/4499, 확인일: 2026-08-22) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자 개인의 해석과 경험적 견해를 담고 있습니다.

실무에서 Optional 관련 코드 리뷰를 하다 보면, 문제의 근원은 API를 몰라서가 아니라 "null-safety"라는 단어에 대한 과도한 신념이라고 생각한다. Optional을 필드나 파라미터에 붙이면 왠지 더 안전해 보이지만, 실제로는 타입 시스템이 "Optional 변수도 null일 수 없다"는 걸 강제해주지 않기 때문에 안전성이 늘어나는 게 아니라 오히려 한 겹의 래퍼와 보일러플레이트만 늘어난다. 개인적으로는 Optional을 "이 메서드는 값을 못 찾을 수도 있다"를 호출부에 알려주는 신호로만 국한해서 쓰고, 데이터를 담아 옮기는 용도(필드, DTO, Entity)에는 절대 쓰지 않는 규칙을 팀 컨벤션으로 못박는 게 가장 실용적이라고 본다. 특히 Jackson 버전 업그레이드로 DTO에 남아있던 Optional 필드가 갑자기 500 에러를 일으키는 사례는, 라이브러리 마이너 버전 업데이트만으로 프로덕션 장애가 날 수 있다는 걸 보여주는 좋은 반례라서, 코드 리뷰 체크리스트에 "DTO/Entity 필드에 Optional 금지"를 명시적으로 넣어두는 걸 권장한다.

## 한계와 반론

이 글은 Optional의 기본 사용법과 5가지 안티패턴에 집중했지만, 몇 가지 한계가 있다. 첫째, Optional을 필드로 쓰는 것에 대해 Brian Goetz를 포함한 다수가 반대하지만, 일부 팀은 도메인 모델 내부(외부에 노출되지 않는 private 필드, getter만 Optional 반환)에 한해 제한적으로 허용하기도 한다 — "절대 금지"보다는 "공개 API 표면(필드/파라미터/DTO)에는 금지"가 더 정확한 표현일 수 있다. 둘째, Jackson의 Optional 직렬화 동작은 라이브러리 버전에 따라 계속 바뀌고 있어(2.16, 2.17 사이에도 정책이 달라짐), 이 글에서 인용한 동작이 향후 버전에서 다시 바뀔 가능성이 있다. 셋째, 성능 측면 — Optional은 래퍼 객체이므로 매우 빈번하게 호출되는 hot path에서는 객체 생성 오버헤드가 문제될 수 있다는 주장도 있으나, 이 글에서는 실측 벤치마크를 직접 수행하지 않았으므로 해당 주장은 다루지 않았다.

## 참고문헌

1. Oracle, "Optional (Java SE 21 & JDK 21)", Java Platform, Standard Edition Documentation. https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html (확인일: 2026-08-22)
2. FasterXML, "Serializing Optional not enabled by default since 2.16.0 · Issue #4499", jackson-databind GitHub repository. https://github.com/FasterXML/jackson-databind/issues/4499 (확인일: 2026-08-22)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인적 견해를 담고 있습니다.

Optional은 등장한 지 10년이 넘은 기능이지만, 여전히 "null 안전성을 보장해주는 마법"으로 오해받는 경우가 많다. 실제로 JDK 공식 문서가 명시한 설계 의도는 훨씬 좁다 — 메서드 반환 타입에서 "값이 없을 수 있다"를 표현하는 용도로 한정된다. 이 글에서 다룬 5가지 안티패턴(필드, get() 오용, of(null), 파라미터, 직렬화 DTO)은 모두 이 좁은 설계 의도를 벗어나 Optional을 "일반적인 null 방지 도구"로 확장 해석했을 때 발생한다. 특히 직렬화 관련 사례는 Jackson 라이브러리 버전이 바뀌면서 과거에는 조용히 넘어가던 코드가 갑자기 예외를 던지게 된 경우로, 정적 타입 언어에서도 라이브러리의 암묵적 계약에 의존한 코드는 여전히 런타임에 깨질 수 있다는 걸 보여준다. 결국 Optional을 안전하게 쓰는 방법은 API를 외우는 것이 아니라, "이건 반환 타입 전용 도구"라는 설계 의도를 팀 전체가 합의하고 코드 리뷰로 강제하는 것이라고 본다.

## 꼬리질문

- Kotlin의 nullable 타입(`String?`)이나 nullability 애노테이션(`@Nullable`/`@NonNull`) 기반 정적 분석 도구는 Optional과 비교했을 때 null 안전성 측면에서 어떤 트레이드오프가 있는가?
- Optional을 도메인 모델의 private 필드로 제한적으로 허용하는 팀 컨벤션은 실제로 버그를 줄이는 효과가 있는가, 아니면 여전히 필드/파라미터 구분의 일관성을 해치는가?
- Jackson 외에 Gson, Kotlin Serialization 등 다른 JSON 라이브러리는 Optional 필드를 기본적으로 어떻게 처리하며, 팀이 라이브러리를 교체할 때 이 차이가 실제로 장애로 이어진 사례가 있는가?

## 백링크

- [Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가](https://beji-tech.blogspot.com/2026/08/java-collections-list-set-map-guide.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-gc-basics.html)
- [SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시](https://beji-tech.blogspot.com/2026/08/solid-principles-java-guide.html)