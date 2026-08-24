---
author: ''
createdAt: '2026-08-22T18:35:48.608273Z'
factCheckScore: 0
id: '6558788394353553258'
notionPageId: null
publishedAt: '2026-08-23T17:08:05-07:00'
slug: java-record-immutable-dto-lombok-value-tradeoff
status: published
tags:
- Advanced
- Java
- Record
title: Java Record — 불변 DTO 설계와 기존 Lombok @Value 대비 트레이드오프
updatedAt: '2026-08-22T18:35:48.608273Z'
url: https://beji-tech.blogspot.com/2026/08/java-record-dto-lombok-value.html
---

# Java Record — 불변 DTO 설계와 기존 Lombok @Value 대비 트레이드오프

## 요약

Java 16(JDK 16, JEP 395)에서 정식으로 도입된 `record`는 불변 데이터 캐리어를 언어 차원에서 지원하는 클래스 종류다. 그동안 이 역할은 Lombok의 `@Value`가 사실상 표준처럼 담당해 왔는데, 둘은 "불변 DTO를 짧게 쓴다"는 결과만 같을 뿐 내부 동작 방식은 상당히 다르다. 이 글은 두 방식을 항목별로 비교하고, Record만이 가진 compact constructor(축약 생성자) 검증 패턴을 실제 컴파일 가능한 코드로 보여준 뒤, JPA 엔티티 호환성·직렬화·빌더 패턴이라는 세 가지 실무 트레이드오프를 짚는다.

## 차별화 포인트

<!-- 내부 전용 섹션 -->

"Record는 불변 클래스를 간결하게 만든다"는 설명은 이미 수많은 글에 있다. 이 글의 차별화는 다음 세 가지다. 첫째, Record의 compact constructor와 Lombok `@Value`의 명시적 생성자를 나란히 놓고 "필드 대입 보일러플레이트가 어느 쪽에서 얼마나 남는가"를 실제 코드로 비교했다 — 이는 Lombok 공식 문서(projectlombok.org)의 "명시적 생성자를 작성하면 Lombok의 자동 생성자 생성이 취소된다"는 사실과 직접 대조한 결과다. 둘째, JPA `@Entity`에 Record를 못 쓰는 이유를 "그냥 안 된다"가 아니라 Hibernate 공식 유저 가이드가 요구하는 "no-arg 생성자"·"non-final 클래스" 두 조건과 Record의 언어 스펙 제약을 직접 매핑해 설명했다. 셋째, 9개 항목(불변성 보장 방식, 생성자 커스터마이징, 빌더 지원, equals/hashCode, JPA Entity/Embeddable, 직렬화, 상속, 의존성)을 하나의 표로 정리해, 단편적으로 흩어진 비교를 한 곳에서 볼 수 있게 했다.

## 본문

### 왜 불변 DTO가 필요한가

여러 스레드가 같은 객체를 동시에 읽는 상황에서 그 객체가 생성 이후 절대 바뀌지 않는다면, 락(lock) 없이도 안전하게 공유할 수 있다. DTO(Data Transfer Object)는 특히 계층 간 데이터 전달용으로만 쓰이므로 생성 이후 값이 바뀔 이유가 없는 경우가 대부분이다. 이런 배경에서 Java 진영은 오랫동안 Lombok의 `@Value` 애노테이션으로 "필드는 `private final`, setter 없음, 생성자·getter·`equals`/`hashCode`/`toString` 자동 생성"이라는 패턴을 사실상 표준처럼 써왔다. JDK 16부터는 같은 목적을 언어 자체가 `record` 키워드로 지원한다.

### Record 기본 문법

```java
public record Point(int x, int y) {
}
```

이 한 줄로 `x()`, `y()` 접근자, 모든 컴포넌트를 인자로 받는 canonical constructor(정준 생성자), `equals()`/`hashCode()`/`toString()`이 자동 생성된다. 컴파일러는 각 컴포넌트를 `private final` 필드로 만들고, 클래스 자체를 암묵적으로 `final`로 선언하며 `java.lang.Record`를 상속시킨다. 이 특성들은 Oracle 공식 언어 가이드(Java SE 17 Language Updates)에 명시돼 있다.

### Record만의 기능: compact constructor 검증

Record가 Lombok `@Value`와 실질적으로 갈라지는 지점은 생성자 커스터마이징 방식이다. Record는 "compact constructor(축약 생성자)"라는 전용 문법을 제공한다. 매개변수 목록을 다시 선언하지 않고 `public OrderRequest { ... }` 형태로 검증/정규화 로직만 작성하면, 필드 대입(`this.x = x` 등)은 컴파일러가 블록 끝에서 자동으로 수행한다. 실제로 실행 가능한 예시는 다음과 같다.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public record OrderRequest(String productId, int quantity, BigDecimal unitPrice) {

    // compact constructor: 매개변수 목록을 다시 쓰지 않는다.
    public OrderRequest {
        if (productId == null || productId.isBlank()) {
            throw new IllegalArgumentException("productId는 비어 있을 수 없습니다.");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity는 1 이상이어야 합니다: " + quantity);
        }
        if (unitPrice == null || unitPrice.signum() < 0) {
            throw new IllegalArgumentException("unitPrice는 0 이상이어야 합니다: " + unitPrice);
        }
        // 정규화: 소수점 둘째 자리로 통일 (this.unitPrice = ... 대입은 컴파일러가 처리)
        unitPrice = unitPrice.setScale(2, RoundingMode.HALF_UP);
    }

    public BigDecimal totalPrice() {
        return unitPrice.multiply(BigDecimal.valueOf(quantity));
    }
}

class OrderRequestDemo {
    public static void main(String[] args) {
        OrderRequest valid = new OrderRequest("SKU-1001", 3, new BigDecimal("19.999"));
        System.out.println(valid);            // unitPrice가 20.00으로 정규화되어 출력됨
        System.out.println(valid.totalPrice()); // 60.00

        try {
            new OrderRequest("SKU-1002", 0, new BigDecimal("10.00"));
        } catch (IllegalArgumentException e) {
            System.out.println("검증 실패: " + e.getMessage());
        }
    }
}
```

이 코드는 `quantity`가 0 이하이거나 `unitPrice`가 음수면 `IllegalArgumentException`을 던지고, 유효한 값이 들어오면 소수점을 정규화한다. 핵심은 필드가 3개든 10개든 대입 코드를 손으로 옮겨 적을 필요가 없다는 점이다 — 검증/정규화 로직만 추가하면 나머지 보일러플레이트는 컴파일러가 채운다.

### Lombok @Value로 같은 검증을 하면

Lombok `@Value`에는 compact constructor에 대응하는 문법이 없다. 검증 로직이 필요한 순간, Lombok 공식 문서가 밝히듯 "명시적 생성자를 작성하면 Lombok은 생성자를 더 이상 자동 생성하지 않는다." 즉 필드 대입까지 전부 손으로 써야 한다.

```java
import lombok.Value;
import java.math.BigDecimal;
import java.math.RoundingMode;

@Value
public class OrderRequestLombok {
    String productId;
    int quantity;
    BigDecimal unitPrice;

    public OrderRequestLombok(String productId, int quantity, BigDecimal unitPrice) {
        if (productId == null || productId.isBlank()) {
            throw new IllegalArgumentException("productId는 비어 있을 수 없습니다.");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity는 1 이상이어야 합니다: " + quantity);
        }
        if (unitPrice == null || unitPrice.signum() < 0) {
            throw new IllegalArgumentException("unitPrice는 0 이상이어야 합니다: " + unitPrice);
        }
        this.productId = productId;
        this.quantity = quantity;
        this.unitPrice = unitPrice.setScale(2, RoundingMode.HALF_UP);
    }
}
```

필드가 늘어날수록 `this.field = field` 대입 목록도 그만큼 길어지고, Lombok이 원래 없애주려던 보일러플레이트가 검증 로직이 필요한 순간 그대로 되살아난다. 이것이 "Record가 Lombok보다 나은 특정 기능"의 실체다 — 단순히 어노테이션 개수가 적다는 취향 문제가 아니라, 검증 로직 추가라는 흔한 요구사항 앞에서 자동 생성이 유지되는지 여부가 갈린다.

### 항목별 비교표

| 항목 | Java Record | Lombok `@Value` |
|---|---|---|
| 불변성 보장 방식 | 언어(컴파일러) 차원 강제 — 컴포넌트는 암묵적으로 `private final` | 애노테이션 기반 — `private final` 필드 + getter만 생성, setter 미생성 |
| 생성자 검증/정규화 | compact constructor로 필드 재선언 없이 로직만 추가 가능 | 명시적 생성자 작성 시 Lombok의 자동 생성자 생성이 취소되어 전체 필드 대입을 수기로 작성해야 함 |
| 빌더 패턴 | 표준 미지원(직접 구현 필요) | `@Builder` 병행 가능. 단, `@Value`와 함께 쓰면 `@Builder`가 생성하는 package-private 전체 인자 생성자가 우선 적용됨 |
| equals/hashCode/toString | 컴파일러가 모든 컴포넌트를 기준으로 자동 생성, 커스터마이징 여지 제한적 | Lombok이 생성하며 `@EqualsAndHashCode(exclude=...)` 등으로 세밀한 조정 가능 |
| JPA `@Entity` | 사용 불가 — no-arg 생성자 없음, 클래스가 암묵적 `final`이라 프록시 생성 불가 | 사용 가능 — `@NoArgsConstructor(force=true)` 추가하고 클래스를 `final`로 만들지 않으면 엔티티 요건 충족 |
| JPA `@Embeddable` | 최신 Hibernate에서 값 객체로 지원되는 방향으로 발전 중(버전별 세부 지원 범위는 변동 가능) | 예전부터 no-arg 생성자만 추가하면 문제없이 사용 |
| 직렬화 커스터마이징 | `writeObject`/`readObject` 등 커스텀 직렬화 메서드 정의 자체가 금지됨(컴포넌트가 직렬화 형태를 결정) | 일반 클래스이므로 `Serializable` 구현 시 커스텀 직렬화 메서드를 자유롭게 정의 가능 |
| 상속 | `java.lang.Record`를 암묵적으로 상속, 다른 클래스를 extends 불가 | 일반 클래스라 상속 가능(다만 불변 설계 취지상 권장되지 않음) |
| 컴파일 의존성 | JDK 16+ 표준 기능, 추가 라이브러리 불필요 | `lombok` 라이브러리 + 애노테이션 프로세서 설정 필요 |

### JPA 엔티티에 Record를 쓸 수 없는 이유

Hibernate 공식 유저 가이드는 엔티티 클래스가 지켜야 할 요건으로 "no-argument 생성자를 구현할 것"과 "가능하면 `final` 클래스를 피할 것"을 명시한다. 두 요건 모두 Record의 언어 스펙과 정면으로 충돌한다. Record는 canonical constructor만 자동 생성하며 별도의 no-arg 생성자를 가지지 않고, 클래스 자체가 암묵적으로 `final`이라 Hibernate가 지연 로딩(lazy loading)에 쓰는 런타임 프록시를 만들 수 없다. 그래서 `record`에 `@Entity`를 붙이면 컨테이너 구동 시점에 오류가 나거나, 최악의 경우 DB에서 읽은 값이 제대로 채워지지 않는 문제로 이어질 수 있다. 반면 DTO/값 객체(value object) 용도로 Record를 쓰고, 엔티티는 별도의 일반 클래스(혹은 Lombok `@Entity` 조합)로 유지하는 구조는 문제없이 동작한다 — 애초에 Record의 설계 목적이 "영속성 계층의 변경 가능한 관리 대상"이 아니라 "값을 옮기기만 하는 불변 데이터"이기 때문이다.

### 직렬화 차이

Record는 커스텀 직렬화 메서드(`writeObject`, `readObject`, `readObjectNoData`, `writeExternal`, `readExternal`)를 정의하는 것 자체가 금지된다. 직렬화·역직렬화는 컴포넌트 목록과 canonical constructor를 기준으로 컴파일러/런타임이 일관되게 처리한다. Lombok `@Value`로 만든 클래스는 문법상 평범한 클래스이므로 `Serializable`을 구현하면서 원하는 대로 커스텀 직렬화 로직을 넣을 수 있다. 레거시 직렬화 포맷을 유지해야 하거나 필드 마이그레이션이 잦은 도메인이라면 이 차이가 실질적인 선택 기준이 된다.

### 빌더 패턴과의 관계

Record는 표준 빌더 문법을 제공하지 않는다. 필드가 많고 선택적 매개변수가 섞인 DTO라면 Lombok `@Builder`를 그대로 쓸 수 있는 `@Value` 조합이 여전히 유리할 수 있다. 다만 `@Value`와 `@Builder`를 함께 쓰면 `@Builder`가 생성하는 전체 인자 생성자가 package-private으로 바뀌어 `@Value`가 기본으로 만드는 public 생성자보다 우선 적용된다는 점은 실무에서 놓치기 쉬운 세부사항이다. Record에서 빌더가 필요하면 별도 정적 팩토리 메서드나 수동 빌더 클래스를 직접 작성해야 한다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Record의 compact constructor는 매개변수 목록을 재선언하지 않고, 컴포넌트 필드 대입은 컴파일러가 생성자 블록 끝에서 암묵적으로 수행한다 | verified | Oracle Java SE 17 Language Updates, Records 문서(compact constructor 섹션): "the fields... cannot be assigned in the body but are automatically assigned"(확인일: 2026-08-23), https://docs.oracle.com/en/java/javase/17/language/records.html |
| Record 클래스는 암묵적으로 final이며 java.lang.Record를 상속하고 다른 클래스를 extends할 수 없다 | verified | Oracle Java SE 17 Language Updates, Records 문서 Restrictions 섹션(확인일: 2026-08-23), https://docs.oracle.com/en/java/javase/17/language/records.html |
| Record는 writeObject/readObject 등 커스텀 직렬화 메서드를 정의할 수 없으며, 직렬화는 컴포넌트와 canonical constructor를 기준으로 처리된다 | verified | Oracle Java SE 17 Language Updates, Records 문서 Serialization 섹션(확인일: 2026-08-23), https://docs.oracle.com/en/java/javase/17/language/records.html |
| Hibernate 공식 유저 가이드는 엔티티 클래스에 no-argument 생성자 구현과 non-final 클래스 사용을 권장 요건으로 명시한다 | verified | Hibernate ORM 6.4 User Guide, "Entity" 챕터 3.4절(확인일: 2026-08-23), https://docs.hibernate.org/orm/6.4/userguide/html_single/Hibernate_User_Guide.html |
| Lombok @Value는 기본적으로 no-args 생성자를 생성하지 않으며, 명시적 생성자를 작성하면 Lombok의 자동 생성자 생성이 취소된다 | verified | Project Lombok 공식 문서, @Value 기능 페이지(확인일: 2026-08-23), https://projectlombok.org/features/Value |
| Lombok @Value와 @Builder를 함께 쓰면 @Builder가 생성하는 package-private 전체 인자 생성자가 @Value의 기본 public 생성자보다 우선 적용된다 | verified | Project Lombok 공식 문서, @Value 기능 페이지(확인일: 2026-08-23), https://projectlombok.org/features/Value |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자 개인의 해석과 의견입니다.

개인적으로는 신규 DTO를 설계할 때 Record를 기본 선택지로 두는 편이 합리적이라고 본다. 언어 차원에서 불변성이 강제되므로 "누군가 실수로 setter를 추가한다"는 흔한 회귀를 원천 차단할 수 있고, 별도 라이브러리 의존성이 없다는 점도 장기적으로 빌드 구성을 단순하게 유지하는 데 도움이 된다. 다만 이걸 "Lombok은 이제 필요 없다"는 결론으로 확대하는 건 성급하다고 생각한다. 엔티티 클래스처럼 애초에 가변성과 프록시가 필요한 영역에서는 Lombok(`@Getter`, `@Setter`, `@NoArgsConstructor` 등)이 여전히 자연스러운 선택이고, 필드가 10개를 넘는 복잡한 DTO에 선택적 값이 섞여 있다면 `@Builder` 조합이 Record보다 가독성 좋은 생성 코드를 만들어 준다. 결국 두 도구는 경쟁 관계라기보다, "이 클래스가 진짜로 불변 값 객체인가, 아니면 나중에 필드가 늘고 프레임워크가 관리해야 하는 대상인가"라는 질문에 따라 갈라 쓰는 게 맞다고 본다. 팀 차원에서는 이 기준을 코드 컨벤션 문서에 명시해 두는 편이 "왜 어떤 DTO는 record고 어떤 DTO는 Lombok 클래스인지"에 대한 불필요한 논쟁을 줄여줄 것이다.

## 한계와 반론

이 글의 비교는 JDK 17/Hibernate 6.x 시점 공식 문서를 기준으로 한다. Record 관련 언어 스펙은 JEP 395 확정 이후 큰 변경이 없었지만, JPA/Hibernate 쪽의 Record 지원 범위(특히 `@Embeddable`)는 마이너 버전마다 달라질 수 있어 실제 프로젝트에 적용하기 전 사용 중인 정확한 Hibernate 버전 문서를 재확인해야 한다. 또한 이 글은 Lombok `@Value` 한 가지만 비교 대상으로 삼았는데, Lombok에는 `@Data`, `@Builder`만 단독 사용하는 조합 등 변형이 많아 팀에서 실제로 쓰는 조합에 따라 트레이드오프가 달라질 수 있다. 성능(예: 리플렉션 기반 직렬화 라이브러리에서 Record 처리 속도 차이) 측면은 이 글에서 직접 벤치마크하지 않았으므로, 성능이 결정적 기준이라면 별도 측정이 필요하다.

## 참고문헌

1. Oracle, "Records", Java SE 17 Language Updates, docs.oracle.com (확인일: 2026-08-23) — https://docs.oracle.com/en/java/javase/17/language/records.html
2. OpenJDK, "JEP 395: Records", openjdk.org (확인일: 2026-08-23) — https://openjdk.org/jeps/395
3. Red Hat / Hibernate Team, "Hibernate ORM 6.4 User Guide", Chapter 3 "Domain Model", docs.hibernate.org (확인일: 2026-08-23) — https://docs.hibernate.org/orm/6.4/userguide/html_single/Hibernate_User_Guide.html
4. Project Lombok, "@Value", projectlombok.org (확인일: 2026-08-23) — https://projectlombok.org/features/Value

## 종합적 의견

> 이 섹션은 전체 주제를 관통하는 종합 분석과 작성자의 해석을 담고 있습니다.

Record와 Lombok `@Value`는 "불변 DTO를 짧게 쓴다"는 표면적 목표는 같지만, 그 아래 동작 방식은 언어 기능과 애노테이션 프로세서라는 전혀 다른 층위에 있다. 이 차이는 평범한 getter/toString 생성 시점에는 거의 드러나지 않다가, 검증 로직이 필요한 순간(compact constructor vs 전체 필드 수기 대입)과 프레임워크 통합이 필요한 순간(JPA 엔티티 요건, 커스텀 직렬화)에 뚜렷하게 갈린다. 실무에서 이 선택을 잘못하면, 나중에 "Record인 줄 알고 불변이라 믿었던 DTO가 사실 JPA 엔티티로 슬쩍 재사용되며 문제가 생기는" 식의 설계 오류로 이어질 수 있다고 본다. 그래서 이 글의 결론은 단순하다 — 새로 DTO/값 객체를 만든다면 Record를 기본값으로 검토하되, 그 클래스가 조금이라도 영속성 계층·가변 상태·복잡한 빌더 요구와 얽힐 가능성이 있다면 처음부터 Lombok 기반 일반 클래스로 설계하는 편이 나중에 되돌리는 비용보다 싸다. 두 기술 중 하나가 절대적으로 우월하다기보다, 클래스가 맡을 역할을 먼저 정하고 그에 맞는 도구를 고르는 순서가 중요하다는 게 이 글이 전달하고 싶은 핵심 견해다.

## 꼬리질문

- Record를 JPA `@Embeddable`로 쓸 때 실제 Hibernate 버전별(6.0/6.2/6.4+) 지원 범위와 필요한 최소 설정은 정확히 어떻게 다른가?
- Jackson, Gson 등 주요 JSON 라이브러리는 Record의 compact constructor 검증 로직을 역직렬화 시점에 그대로 통과시키는가, 아니면 리플렉션으로 우회하는 경우가 있는가?
- 대규모 필드를 가진 DTO에서 Record 기반 정적 팩토리/빌더 패턴과 Lombok `@Builder` 기반 패턴의 실제 생성 코드 가독성·성능 차이를 벤치마크로 비교하면 어떤 결과가 나올까?

## 백링크

- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)
- [SOLID 원칙이란 무엇인가](https://beji-tech.blogspot.com/2026/08/solid-java-5.html)
- [[GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시](https://beji-tech.blogspot.com/2026/08/gof-4-builder-pattern-java.html)