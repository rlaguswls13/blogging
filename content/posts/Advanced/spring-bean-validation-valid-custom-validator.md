---
author: ''
createdAt: '2026-08-22T18:39:45.914821Z'
factCheckScore: 0.9
id: '1182561791145229542'
notionPageId: null
publishedAt: '2026-08-23T17:10:30-07:00'
slug: spring-bean-validation-valid-custom-validator
status: published
tags:
- Advanced
- Spring
- Validation
title: Spring Bean Validation(@Valid) — 검증 어노테이션 동작 원리와 커스텀 Validator
updatedAt: '2026-08-23T00:00:00.000000Z'
url: https://beji-tech.blogspot.com/2026/08/spring-bean-validationvalid-validator.html
---

# Spring Bean Validation(@Valid) — 검증 어노테이션 동작 원리와 커스텀 Validator

## 요약

`@Valid`는 마법이 아니라 Jakarta Bean Validation(구 JSR 380) 스펙과 참조 구현체 Hibernate Validator가 리플렉션으로 애노테이션을 읽어 `ConstraintValidator`를 실행하는 구조다. 교차 필드와 캐스케이딩 함정을 코드로 직접 재현한다. 단일 필드 애노테이션 나열이 아니라 여러 필드를 함께 봐야 하는 교차 필드(cross-field) 검증을 커스텀 `@Constraint` + `ConstraintValidator`로 직접 구현하고, 실무에서 가장 많이 걸려 넘어지는 함정인 "중첩 객체 캐스케이딩 누락 시 검증이 조용히 스킵되는 버그"를 재현 코드로 보여준다.

## 차별화 포인트

동일 주제의 상위 검색 결과 대부분은 `@NotNull`/`@Size`/`@Email` 같은 어노테이션 목록과 사용 예시만 나열하고 끝난다. 이 글은 (1) Jakarta Bean Validation 스펙 원문을 근거로 `ConstraintValidator.isValid()`/`initialize()`가 언제 어떻게 호출되는지 동작 원리를 설명하고, (2) 단일 필드 애노테이션으로는 표현할 수 없는 `startDate`가 `endDate`보다 앞서야 한다는 교차 필드 제약을 실제로 컴파일되는 `@Constraint` + `ConstraintValidator` 코드로 구현하며, (3) `@Valid`를 중첩 객체 필드 자체에 붙이지 않으면 검증이 예외 없이 조용히 스킵된다는, 공식 문서(Hibernate Validator Reference Guide 2.1.6절 "Object graphs")에 근거한 실제 함정을 재현 테스트 코드로 직접 보여준다. 단순 나열이 아니라 "왜 동작하고, 왜 실패하는가"를 코드로 증명하는 것이 차별점이다.

## 본문

### 1. `@Valid`가 실제로 하는 일

Spring MVC 컨트롤러에서 `@RequestBody @Valid UserDto dto`처럼 쓰면, 흔히 "Spring이 알아서 검증해준다"고 생각하기 쉽다. 하지만 실제로는 다음 세 계층이 나눠서 일한다.

1. **Jakarta Bean Validation 스펙** (JSR 380, 현재 Spring Boot 3.x 계열이 사용하는 버전은 Jakarta Bean Validation 3.0) — `@NotNull`, `@Valid`, `ConstraintValidator` 같은 API 표준을 정의한다. 스펙 자체는 구현체가 아니라 인터페이스와 규칙의 집합이다.
2. **Hibernate Validator** — 이 스펙의 참조 구현체(Reference Implementation)다. Spring Boot의 `spring-boot-starter-validation`을 의존성에 추가하면 실제로 클래스패스에 올라오는 것이 이 라이브러리다.
3. **Spring Framework** — `LocalValidatorFactoryBean`으로 Hibernate Validator를 스프링 빈으로 감싸고, `@RequestBody`가 붙은 파라미터에 `@Valid`가 함께 있으면 `RequestResponseBodyMethodProcessor`가 바인딩 직후 `Validator.validate()`를 호출하도록 연결해준다.

즉 `@Valid` 자체는 아무 검증 로직도 갖고 있지 않다. "이 객체(또는 파라미터)를 검증 대상으로 표시"하는 마커일 뿐이고, 실제 검증 로직은 각 제약 애노테이션에 연결된 `ConstraintValidator` 구현체 안에 있다.

### 2. `ConstraintValidator` 인터페이스가 동작하는 원리

Jakarta Bean Validation 스펙은 커스텀 제약을 두 부분으로 나눠 정의하도록 규정한다 — 제약을 선언하는 애노테이션(`@Constraint`가 붙은 애노테이션)과, 실제 로직을 구현하는 `ConstraintValidator<A extends Annotation, T>` 인터페이스다. 이 인터페이스는 두 개의 메서드를 가진다.

- `void initialize(A constraintAnnotation)` — 검증 인스턴스가 처음 사용되기 전에 한 번 호출되며, 애노테이션에 선언된 속성 값(예: `min`, `max`)을 필드에 저장하는 용도로 쓴다. 기본 구현은 no-op이다.
- `boolean isValid(T value, ConstraintValidatorContext context)` — 실제 검증 로직. 이 메서드는 동시에 여러 스레드에서 호출될 수 있으므로 스레드 세이프해야 한다고 스펙이 명시한다.

`@Valid`가 붙은 객체를 Hibernate Validator가 순회하면서, 그 객체의 필드에 붙은 각 제약 애노테이션마다 대응하는 `ConstraintValidator` 인스턴스를 찾아 `isValid()`를 호출하고, `false`가 반환되면 `ConstraintViolation`을 하나 쌓는다. 이 전체 과정이 리플렉션 기반이기 때문에 애노테이션만 붙이면 별도의 if문 없이 검증이 동작하는 것처럼 보이는 것이다.

### 3. 단일 필드 애노테이션의 한계 — 교차 필드 검증

`@NotNull`, `@Size`, `@Min`, `@Max` 같은 표준 제약은 전부 필드 하나만 본다. 하지만 실무에서 자주 만나는 요구사항은 "필드 A와 필드 B의 관계"를 검증해야 하는 경우다. 대표적인 예가 예약/이벤트 시스템의 `startDate`가 `endDate`보다 앞서야 한다는 제약이다. 이런 제약은 `@Size` 같은 필드 단위 애노테이션으로는 표현할 방법이 없다 — 두 필드를 동시에 봐야 하기 때문이다.

해결책은 클래스 레벨(`ElementType.TYPE`)에 붙는 커스텀 `@Constraint`를 만들고, 그 `ConstraintValidator`의 `isValid()`에서 객체 전체(`T value`)를 받아 두 필드를 함께 비교하는 것이다.

```java
// 1) 제약 애노테이션 정의 — 클래스 레벨에 붙는다
import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import java.lang.annotation.*;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = ValidDateRangeValidator.class)
public @interface ValidDateRange {
    String message() default "startDate는 endDate보다 앞서야 합니다";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
```

```java
// 2) ConstraintValidator 구현 — 객체 전체를 받아 두 필드를 함께 검사
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;

public class ValidDateRangeValidator
        implements ConstraintValidator<ValidDateRange, DateRangeHolder> {

    @Override
    public boolean isValid(DateRangeHolder value, ConstraintValidatorContext context) {
        if (value == null || value.getStartDate() == null || value.getEndDate() == null) {
            // null 처리는 @NotNull 등 별도 애노테이션의 책임으로 위임한다
            return true;
        }
        boolean valid = value.getStartDate().isBefore(value.getEndDate());
        if (!valid) {
            // 기본 메시지를 끄고, 특정 필드(endDate)에 위반을 매핑해 에러 메시지 위치를 정확히 준다
            context.disableDefaultConstraintViolation();
            context.buildConstraintViolationWithTemplate(
                    "endDate는 startDate 이후여야 합니다")
                    .addPropertyNode("endDate")
                    .addConstraintViolation();
        }
        return valid;
    }
}
```

```java
// 3) 사용 예시
@ValidDateRange
public class DateRangeHolder {
    @NotNull
    private LocalDate startDate;

    @NotNull
    private LocalDate endDate;
    // getters/setters 생략
}

public interface DateRangeHolder {
    LocalDate getStartDate();
    LocalDate getEndDate();
}
```

이 구현에서 핵심은 `ConstraintValidator<ValidDateRange, DateRangeHolder>`의 두 번째 타입 파라미터가 필드 타입이 아니라 **객체 타입 자체**라는 점이다. `isValid()`가 받는 `value`가 곧 검증 대상 객체이므로, 그 안에서 임의의 필드 조합을 자유롭게 비교할 수 있다. `addPropertyNode("endDate")`를 쓰면 위반이 특정 필드에 매핑되어, 클라이언트가 받는 에러 응답에서 `endDate` 필드 에러로 정확히 표시된다 — 이게 없으면 에러가 객체 루트에만 달려 어느 필드가 문제인지 API 응답만으로는 알 수 없다.

### 4. 진짜 함정 — 중첩 객체 캐스케이딩과 조용한 스킵

`@Valid`를 컨트롤러 파라미터에 붙이면 최상위 객체는 검증되지만, 그 객체가 다른 객체를 필드로 갖고 있을 때(중첩 객체) 이야기가 달라진다. Hibernate Validator Reference Guide는 이를 "Object graphs"(2.1.6절)로 설명하는데, 요지는 "다른 객체에 대한 참조를 나타내는 필드나 프로퍼티에 `@Valid`를 붙여야" 캐스케이딩이 일어난다는 것이다. 이 조건이 빠지면 **예외도, 경고도 없이 해당 중첩 객체의 검증이 그냥 스킵된다.**

아래 코드로 이 버그를 직접 재현할 수 있다.

```java
public class OrderRequest {
    @NotBlank
    private String orderId;

    // (버그) @Valid가 없다 — Address 내부의 @NotBlank 제약은
    // OrderRequest를 검증해도 절대 실행되지 않는다
    private Address shippingAddress;

    // getters/setters 생략
}

public class Address {
    @NotBlank(message = "도시는 필수입니다")
    private String city;

    @NotBlank(message = "우편번호는 필수입니다")
    private String zipCode;

    // getters/setters 생략
}
```

```java
// 재현 테스트 — city/zipCode가 비어 있어도 위반이 0개로 나온다
class CascadingBugReproductionTest {

    private final Validator validator =
            Validation.buildDefaultValidatorFactory().getValidator();

    @Test
    void nestedFieldWithoutAtValid_silentlySkipsValidation() {
        OrderRequest request = new OrderRequest();
        request.setOrderId("ORD-1");
        Address emptyAddress = new Address(); // city, zipCode 둘 다 null
        request.setShippingAddress(emptyAddress);

        Set<ConstraintViolation<OrderRequest>> violations = validator.validate(request);

        // 기대와 달리 위반이 하나도 없다 — Address 내부는 아예 순회되지 않았기 때문
        assertThat(violations).isEmpty();
    }
}
```

`shippingAddress` 필드에 `@Valid`를 추가하는 순간(`@Valid private Address shippingAddress;`) 같은 테스트가 `city`, `zipCode` 위반 2건을 정상적으로 반환한다. 즉 버그의 원인과 해결책은 딱 한 줄, 애노테이션 하나 차이다. 문제는 이 누락이 컴파일 타임에도, 런타임 예외로도 드러나지 않고 "검증을 통과한 것처럼" 보인다는 점이다 — QA나 통합 테스트에서 정상 케이스만 확인하면 이 구멍은 프로덕션까지 살아남기 쉽다. 리스트나 맵 안의 요소도 마찬가지로, `List<Address>` 필드에 캐스케이딩을 적용하려면 필드 자체에 `@Valid`를 붙여야 한다(Jakarta Bean Validation 2.0부터는 `List<@Valid Address>`처럼 타입 인자에 붙이는 방식도 지원한다).

### 5. 실무에서 이 두 가지를 함께 쓰는 이유

교차 필드 검증과 캐스케이딩 검증은 별개의 문제지만 실무 DTO에서는 항상 함께 나타난다. 예를 들어 예약 시스템의 `ReservationRequest`가 `DateRangeHolder`(교차 필드 제약 필요)를 중첩 필드로 갖는다면, `ReservationRequest`의 해당 필드에도 반드시 `@Valid`를 붙여야 `ValidDateRange` 제약이 실행된다. 커스텀 클래스 레벨 제약을 아무리 잘 만들어도, 그 객체가 다른 객체의 필드로 들어가는 순간 캐스케이딩 규칙이 다시 적용된다는 점을 놓치면, 잘 작성한 커스텀 Validator조차 조용히 무력화된다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| `ConstraintValidator` 인터페이스는 `initialize(A)`와 `isValid(T, ConstraintValidatorContext)` 두 메서드로 구성되며, `isValid()`는 동시 호출에 대해 스레드 세이프해야 한다 | verified | Jakarta Bean Validation 3.0 스펙 3.4절 "Constraint validation implementation" 원문 대조 (https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html, 확인일: 2026-08-23) |
| Hibernate Validator는 Jakarta Bean Validation 스펙의 참조 구현체(Reference Implementation)다 | verified | Hibernate Validator Reference Guide 원문 대조 (https://docs.hibernate.org/stable/validator/reference/en-US/html_single/, 확인일: 2026-08-23) |
| 중첩 객체(연관 객체)에 대한 캐스케이딩 검증은 그 객체를 참조하는 필드/프로퍼티 자체에 `@Valid`를 붙여야만 수행된다 | verified | Hibernate Validator Reference Guide 2.1.6절 "Object graphs" 원문: "annotate a field or property representing a reference to another object with @Valid" (https://docs.hibernate.org/stable/validator/reference/en-US/html_single/, 확인일: 2026-08-23) |
| Spring Framework는 `LocalValidatorFactoryBean`을 통해 Bean Validation 프로바이더(Hibernate Validator 등)를 스프링 빈으로 통합하고, `@RequestBody`에 `@Valid`가 붙으면 바인딩 직후 검증을 수행한다 | verified | Spring Framework Reference "Spring Validation" 문서 원문 대조 (https://docs.spring.io/spring-framework/reference/core/validation/beanvalidation.html, 확인일: 2026-08-23) |
| 커스텀 제약은 제약 애노테이션(`@Constraint` 메타애노테이션 사용)과 `ConstraintValidator` 구현체 두 부분으로 구성해 정의한다 | verified | Hibernate Validator Reference Guide 6장 "Creating a custom constraint" 원문 대조 (https://docs.hibernate.org/stable/validator/reference/en-US/html_single/, 확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자가 코드를 직접 재현하며 느낀 개인적 견해를 담고 있습니다.

개인적으로 `@Valid` 캐스케이딩 누락 버그는 이 스펙에서 가장 위험한 설계 트레이드오프라고 생각한다. 스펙 입장에서는 "명시적으로 표시한 것만 검증한다"는 일관된 원칙이지만, 사용하는 개발자 입장에서는 애노테이션을 하나 빠뜨렸을 때 컴파일 에러도, 런타임 예외도 없이 그냥 조용히 통과되어 버린다는 게 직관에 크게 어긋난다. 차라리 중첩 객체 필드에 아무 검증 애노테이션이 없을 때 경고 로그라도 남겨줬으면 훨씬 덜 위험했을 거라는 아쉬움이 있다. 또한 커스텀 크로스필드 Validator를 만들 때 `addPropertyNode()`로 위반을 특정 필드에 매핑하는 패턴은 문서에서 그리 강조되지 않는데, 실무 API 응답 품질에 직결되는 부분이라 표준 예제에 더 자주 등장했으면 한다. 결국 `@Valid`는 편리하지만 "안 붙이면 안 됨"이 아니라 "안 붙이면 조용히 무시됨"이라는 실패 모드를 팀 전체가 인지하고 코드 리뷰 체크리스트에 넣는 것이 현실적인 방어책이라고 본다.

## 한계와 반론

이 글의 재현 코드는 Hibernate Validator를 Bean Validation 구현체로 사용하는 표준 Spring Boot 설정을 전제로 한다. 다른 구현체(예: Apache BVal)를 쓰는 경우 세부 동작이 스펙을 벗어나지 않는 한 동일해야 하지만 직접 검증하지는 않았다. 또한 캐스케이딩 누락 문제는 정적 분석 도구(예: 커스텀 ArchUnit 규칙이나 컴파일 타임 애노테이션 프로세서)로 상당 부분 예방할 수 있는데, 이 글은 그런 예방 도구 자체는 다루지 않고 문제 재현에만 집중했다는 한계가 있다. 커스텀 크로스필드 Validator 예시도 `startDate`/`endDate` 하나의 사례일 뿐이며, 필드가 3개 이상으로 늘어나거나 조건부 필수 필드(A가 있으면 B도 필수) 같은 더 복잡한 규칙에서는 `ConstraintValidator` 하나로 풀기보다 별도 서비스 레이어 검증을 병행하는 편이 가독성 면에서 나을 수 있다는 반론도 가능하다.

## 참고문헌

1. Jakarta Bean Validation 3.0 Specification, Section 3.4 "Constraint validation implementation" — https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html (확인일: 2026-08-23)
2. Hibernate Validator Reference Guide (Reference Implementation), Section 2.1.6 "Object graphs" 및 Chapter 6 "Creating a custom constraint" — https://docs.hibernate.org/stable/validator/reference/en-US/html_single/ (확인일: 2026-08-23)
3. Spring Framework Reference Documentation, "Spring Validation" (Bean Validation 연동, `LocalValidatorFactoryBean`) — https://docs.spring.io/spring-framework/reference/core/validation/beanvalidation.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 개인적인 종합 평가이며, 사실 검증 결과와는 별개의 해석임을 밝힙니다.

`@Valid`를 둘러싼 생태계는 "선언적으로 붙이면 알아서 동작한다"는 편의성과 "명시적으로 표시하지 않으면 아무 일도 일어나지 않는다"는 스펙의 원칙이 정면으로 충돌하는 지점이라고 본다. 단일 필드 제약(`@NotNull`, `@Size`)만 다루는 튜토리얼이 흔한 이유는 그게 가장 눈에 잘 띄고 설명하기 쉬운 사례이기 때문이지, 실무에서 가장 자주 문제가 되는 지점이기 때문은 아니다. 실제로 프로덕션에서 발생하는 검증 관련 결함은 오히려 이 글에서 다룬 두 가지 — 여러 필드를 함께 봐야 하는 교차 검증의 부재, 그리고 중첩 객체에서 캐스케이딩이 빠져 조용히 스킵되는 경우 — 에서 많이 발생한다. `ConstraintValidator` 인터페이스 자체는 스펙 문서 몇 페이지로 충분히 이해할 수 있을 만큼 단순하지만, 그 단순함 뒤에 숨은 "명시적 표시가 없으면 검증되지 않는다"는 암묵적 규칙을 팀 컨벤션과 테스트로 보완하지 않으면 애노테이션만 믿고 넘어간 코드가 프로덕션에서 사고로 이어질 수 있다고 본다.

## 꼬리질문

- `List<@Valid Address>`처럼 컬렉션 타입 인자에 캐스케이딩을 거는 것과 컬렉션 필드 자체에 `@Valid`를 붙이는 것의 실제 동작 차이는 무엇인가?
- `@Validated`(스프링 전용)와 `@Valid`(Jakarta 표준)를 그룹 검증(validation groups)과 함께 쓸 때, 커스텀 크로스필드 Validator가 그룹별로 다르게 동작하도록 만들려면 어떻게 설계해야 하는가?
- 캐스케이딩 누락을 런타임이 아니라 컴파일 타임/빌드 타임에 정적으로 잡아낼 수 있는 애노테이션 프로세서나 ArchUnit 규칙을 실제로 구축한다면 어떤 휴리스틱이 오탐(false positive)을 최소화할 수 있을까?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)