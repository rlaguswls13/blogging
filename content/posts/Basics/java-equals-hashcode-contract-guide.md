---
author: ''
createdAt: '2026-08-22T18:33:01.605302Z'
factCheckScore: 0
id: '9083572303998755319'
notionPageId: null
publishedAt: '2026-08-22T16:19:08-07:00'
slug: java-equals-hashcode-contract-guide
status: published
tags:
- Basics
- Java
title: Java equals()/hashCode() 계약 — 왜 함께 오버라이드해야 하는가
updatedAt: '2026-08-22T18:33:01.605302Z'
url: https://beji-tech.blogspot.com/2026/08/java-equalshashcode.html
---

# Java equals()/hashCode() 계약 — 왜 함께 오버라이드해야 하는가

## 요약

equals()만 오버라이드하고 hashCode()는 그대로 두면 컴파일도 되고 equals() 단독 호출도 정상 동작해 코드 리뷰에서도 쉽게 놓치지만, 정작 그 인스턴스를 HashSet·HashMap에 넣는 순간부터 중복 삽입과 조회 실패가 조용히 발생한다.

이 글은 이 버그를 실제 Java 코드로 직접 재현해 콘솔 출력을 보여주고, `hashCode()`를 추가해 고친 뒤 같은 코드가 정상 동작하는 것까지 확인한다. 이어서 실무에서 더 자주 발생하는 JPA 엔티티의 `equals()/hashCode()` 함정 — Hibernate 프록시로 인한 `getClass()` 비교 문제와 자동 생성 ID 기반 해시코드가 컬렉션 계약을 깨는 사례도 다룬다.

## 차별화 포인트

대부분의 "equals/hashCode 계약" 글은 Java `Object` 클래스 Javadoc의 5가지 규칙(반사성/대칭성/추이성/일관성/null)을 나열하고 끝난다. 이 글은 거기서 멈추지 않고 (1) `equals()`만 오버라이드한 클래스를 실제로 `HashSet`/`HashMap`에 넣어 `size()`가 기대와 다르게 나오고 `contains()`/`get()`이 실패하는 실제 콘솔 출력을 코드와 함께 보여주고, (2) 같은 클래스에 `hashCode()`를 추가한 뒤 동일 코드를 재실행해 정상 동작으로 바뀌는 전후 비교를 제공한다. 또한 (3) 교과서 예시에는 잘 안 나오는 JPA/Hibernate 프록시 정체성 문제 — `getClass()` 비교가 지연 로딩 프록시와 실제 엔티티를 다른 타입으로 오판해 `equals()`가 항상 `false`를 반환하는 실무 장애 패턴과, `@GeneratedValue` ID를 `hashCode()`에 그대로 쓰면 영속화 전후로 해시값이 바뀌어 `Set` 계약이 깨지는 구체적 실패 시나리오까지 다룬다.

## 본문

### 1. 문제 상황: equals()만 오버라이드하면 무슨 일이 벌어지나

Java의 `Object` 클래스는 `equals(Object)`와 `hashCode()`를 함께 정의하고 있고, 둘 사이에는 명시적인 계약이 있다. Oracle 공식 Java SE 21 API 문서의 `Object#hashCode()` 설명은 다음과 같이 규정한다.

> "If two objects are equal according to the `equals(Object)` method, then calling the `hashCode` method on each of the two objects must produce the same integer result."

즉 "두 객체가 `equals()`로 같다고 판정되면, 두 객체의 `hashCode()`도 반드시 같은 값을 반환해야 한다"는 규칙이다. 이 규칙은 컴파일러가 강제하지 않는다. `equals()`만 오버라이드하고 `hashCode()`를 그대로 두면, 클래스는 여전히 `Object`가 제공하는 기본 `hashCode()`(객체의 메모리 주소 기반 identity hash)를 그대로 물려받는다. 그 결과 논리적으로 같은 값을 가진 두 인스턴스가 서로 다른 해시코드를 갖게 되고, 이 값을 키로 사용하는 `HashSet`/`HashMap`은 서로 다른 버킷(bucket)에 두 인스턴스를 저장해버린다.

### 2. 버그 재현: equals()만 있는 클래스를 HashSet에 넣어보기

좌표를 나타내는 간단한 `Point` 클래스를 만들되, 의도적으로 `equals()`만 오버라이드하고 `hashCode()`는 오버라이드하지 않는다.

```java
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class Point {
    private final int x;
    private final int y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Point)) return false;
        Point other = (Point) o;
        return x == other.x && y == other.y;
    }

    // hashCode()를 의도적으로 오버라이드하지 않음 (버그 재현용)

    public static void main(String[] args) {
        Point p1 = new Point(1, 2);
        Point p2 = new Point(1, 2); // p1과 equals()로는 같은 값
        Point p3 = new Point(1, 2); // 조회용으로 쓸 세 번째 인스턴스

        Set<Point> points = new HashSet<>();
        points.add(p1);
        points.add(p2);

        System.out.println("p1.equals(p2) = " + p1.equals(p2));
        System.out.println("Set 크기 = " + points.size());
        System.out.println("contains(p3) = " + points.contains(p3));

        Map<Point, String> map = new HashMap<>();
        map.put(new Point(1, 2), "first");
        map.put(new Point(1, 2), "second");
        System.out.println("Map 크기 = " + map.size());
        System.out.println("get(new Point(1,2)) = " + map.get(new Point(1, 2)));
    }
}
```

이 코드를 실행하면 다음과 같은 결과가 출력된다.

```
p1.equals(p2) = true
Set 크기 = 2
contains(p3) = false
Map 크기 = 2
get(new Point(1,2)) = null
```

`p1.equals(p2)`는 분명히 `true`다. 하지만 `Set` 크기는 1이 아니라 2다 — 논리적으로 같은 값인 `p1`, `p2`가 둘 다 저장됐다는 뜻이다. `contains(p3)`는 `p3.equals(p1)`이 `true`임에도 `false`를 반환한다. `HashMap` 쪽도 마찬가지로 `put()`을 두 번 했을 때 덮어쓰기가 되지 않고 엔트리가 2개로 늘어나며, 방금 넣은 것과 논리적으로 같은 키로 `get()`을 호출해도 `null`이 돌아온다. 이유는 단순하다. `hashCode()`가 오버라이드되지 않았으니 `p1`, `p2`, `p3`는 각각 다른 identity hash 값을 갖고, `HashSet`/`HashMap`은 그 해시값으로 버킷을 결정하기 때문에 세 인스턴스가 서로 다른 버킷에 흩어진다. 버킷이 다르면 애초에 `equals()` 비교 대상에 오르지도 못한다 — `equals()`가 아무리 정확해도 해시가 어긋나면 컬렉션 입장에서는 "다른 버킷에 있는, 검사조차 안 해본 객체"일 뿐이다.

### 3. 수정: hashCode()를 추가하고 다시 실행

같은 클래스에 `equals()`와 일관된 `hashCode()`를 추가한다.

```java
import java.util.Objects;

@Override
public int hashCode() {
    return Objects.hash(x, y);
}
```

`equals()`에서 비교에 사용한 필드(`x`, `y`)와 정확히 같은 필드를 `hashCode()` 계산에도 사용하는 것이 핵심이다. 이 메서드를 추가한 뒤 앞서와 동일한 `main()` 코드를 다시 실행하면 결과가 이렇게 바뀐다.

```
p1.equals(p2) = true
Set 크기 = 1
contains(p3) = true
Map 크기 = 1
get(new Point(1,2)) = first
```

`Set` 크기는 기대대로 1이 되고, `contains(p3)`는 `true`, `Map`은 중복 `put()`이 덮어쓰기로 처리되어 크기가 1로 유지되며, `get()`도 정상적으로 값을 찾아온다. `equals()`와 `hashCode()`가 같은 필드 집합에 대해 일관되게 동작해야 해시 기반 컬렉션이 "논리적으로 같은 객체"를 실제로 같은 버킷에 모을 수 있다는 것을 코드 레벨에서 확인할 수 있다.

### 4. 실무 함정: JPA 엔티티와 Hibernate 프록시

교과서 예시에서 한 단계 더 들어가면, 실무에서는 JPA 엔티티의 `equals()/hashCode()`가 훨씬 더 까다로운 문제를 만든다. 두 가지 대표적인 함정이 있다.

**(1) getClass() 비교가 프록시와 충돌한다.** Hibernate는 지연 로딩(lazy loading)되는 연관관계를 실제 엔티티 클래스가 아니라 그 클래스를 상속한 프록시 서브클래스(`HibernateProxy`를 구현한 동적 생성 클래스)로 반환한다. 이때 `equals()`를 `getClass() != o.getClass()`처럼 클래스 동일성으로 비교하면, 같은 DB row를 가리키는 실제 엔티티와 프록시 객체를 비교할 때 `getClass()`가 다르다는 이유로 항상 `false`가 나온다. Hibernate ORM 공식 User Guide는 이런 이유로 `getClass()` 대신 `instanceof` 기반 비교를 권장한다.

```java
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class Member {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String email;

    protected Member() {
        // JPA 스펙상 기본 생성자 필요
    }

    public Member(String email) {
        this.email = email;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        // getClass() 비교 대신 instanceof를 써야 Hibernate 프록시와도
        // 올바르게 비교된다 (프록시는 Member의 서브클래스로 생성됨).
        if (!(o instanceof Member)) return false;
        Member other = (Member) o;
        return email != null && email.equals(other.email);
    }

    @Override
    public int hashCode() {
        // 클래스 고정 해시 - 비즈니스 키(email)가 아직 없는 상태에서도
        // 안전하게 사용 가능하다.
        return getClass().hashCode();
    }
}
```

**(2) 자동 생성 ID를 hashCode()에 쓰면 컬렉션 계약이 깨진다.** `@GeneratedValue`로 채번되는 ID는 `persist()`가 실행되기 전까지 `null`이다. 만약 `hashCode()`를 `id.hashCode()`처럼 구현하면, 엔티티를 `HashSet`에 먼저 넣고 그 다음 저장(`save()`/`persist()`)했을 때 ID가 `null`에서 실제 값으로 바뀌면서 해시코드도 바뀐다. `hashCode()`의 두 번째 계약 조항 — "객체 상태가 바뀌지 않는 한 같은 실행 중에는 항상 같은 값을 반환해야 한다" — 을 위반하는 것이다. 이미 `HashSet`에 들어간 엔티티는 저장 전 해시값을 기준으로 잘못된 버킷에 남아 있게 되어 이후 `contains()`가 실패한다. 이 문제를 피하려면 이메일, 주민등록번호처럼 변하지 않는 비즈니스 키를 기준으로 `equals()/hashCode()`를 구현하거나, 비즈니스 키가 마땅치 않다면 위 예시처럼 클래스 고정 해시(`getClass().hashCode()`)를 쓰는 방식이 실무에서 널리 쓰인다.

### 5. 정리

`equals()`와 `hashCode()`는 독립적으로 작동하는 두 메서드가 아니라, `HashSet`/`HashMap` 같은 해시 기반 컬렉션이 전제하는 하나의 계약이다. 이 계약을 지키지 않으면 컴파일 에러도, 런타임 예외도 없이 조용히 데이터가 중복되거나 사라진 것처럼 보이는 버그가 만들어진다. IDE의 "equals와 hashCode 함께 생성" 기능이나 Lombok의 `@EqualsAndHashCode`, Java 16+의 `record` 타입을 쓰면 이 실수를 원천 차단할 수 있지만, JPA 엔티티처럼 두 메서드를 수동으로 구현해야 하는 상황에서는 이 글에서 재현한 실패 패턴을 기억해두는 것이 실질적인 방어선이 된다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| equals()로 같다고 판정되는 두 객체는 반드시 같은 hashCode()를 반환해야 하며, 이를 어기면 HashMap/HashSet 같은 해시 기반 컬렉션이 논리적으로 같은 값을 다른 버킷에 저장해 중복 삽입·조회 실패가 발생한다 | verified | Oracle Java SE 21 API 문서 `Object#hashCode()`: "If two objects are equal according to the equals(Object) method, then calling the hashCode method on each of the two objects must produce the same integer result." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html, 확인일: 2026-08-23) |
| equals()의 일반 계약은 반사성(reflexive), 대칭성(symmetric), 추이성(transitive), 일관성(consistent), null 비교 시 false 반환의 5가지 속성을 요구한다 | verified | 동일 Oracle Javadoc `Object#equals(Object)` 섹션 (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html, 확인일: 2026-08-23) |
| Hibernate는 지연 로딩된 연관관계를 실제 엔티티 클래스의 프록시 서브클래스로 반환하므로, getClass() 기반 equals()는 프록시와 실제 엔티티를 비교할 때 항상 false를 반환할 수 있어 instanceof 비교가 권장된다 | verified | Hibernate ORM 공식 User Guide, "Implementing equals() and hashCode()" 섹션 (https://docs.hibernate.org/stable/orm/userguide/html_single/#mapping-model-pojo-equalshashcode, 확인일: 2026-08-23); Vlad Mihalcea, "How to implement equals and hashCode using the JPA entity identifier" (https://vladmihalcea.com/how-to-implement-equals-and-hashcode-using-the-jpa-entity-identifier/, 확인일: 2026-08-23) |
| @GeneratedValue로 채번되는 JPA 엔티티 ID는 persist() 전까지 null이므로, ID 기반 hashCode()는 영속화 전후로 값이 바뀌어 이미 컬렉션에 들어간 엔티티의 hashCode 일관성 계약을 깰 수 있다 | verified | Hibernate ORM 공식 User Guide 동일 섹션 및 Vlad Mihalcea 동일 자료 (확인일: 2026-08-23) |

## 작성자의 견해

> 이 문제는 개인적으로 실무에서 가장 "재현이 늦게 되는" 버그 중 하나라고 생각한다. 단위 테스트에서는 보통 하나의 인스턴스만 만들어 `equals()`를 검증하기 때문에 통과하고, `HashSet`/`HashMap`을 실제로 대량의 데이터로 채우는 통합 테스트나 운영 트래픽에서야 중복·조회 실패가 드러난다. 특히 JPA 엔티티는 `equals()/hashCode()`를 수동 구현해야 하는 경우가 많아서 이 계약을 놓치기 쉬운데, `getClass()` 비교처럼 겉보기엔 더 "엄격해 보이는" 구현이 오히려 Hibernate 프록시 환경에서는 버그를 만든다는 점이 역설적이다. 개인적인 의견으로는, 팀 차원에서 Lombok `@EqualsAndHashCode`나 Java `record`처럼 컴파일러가 계약을 보장해주는 방식을 기본값으로 삼고, JPA 엔티티처럼 수동 구현이 불가피한 예외 케이스만 이 글에서 다룬 체크리스트(instanceof 비교, 비즈니스 키 또는 클래스 고정 해시)로 리뷰하는 게 실질적으로 더 안전한 접근이라고 본다. EqualsVerifier 같은 테스트 라이브러리로 계약 위반을 CI에서 자동 검출하는 것도 고려할 만하다.

## 한계와 반론

이 글의 버그 재현은 `HashSet`/`HashMap`의 기본 구현(자바 표준 라이브러리)을 기준으로 한 것으로, `TreeSet`/`TreeMap`처럼 `Comparable`/`Comparator` 기반 정렬 컬렉션에는 해당 계약이 다르게 적용된다 — 이 경우 `equals()`가 아니라 `compareTo()`의 일관성이 더 중요하다. 또한 JPA 엔티티의 `equals()/hashCode()` 구현 전략(식별자 기반 vs 비즈니스 키 기반 vs 클래스 고정 해시)은 커뮤니티 내에서도 완전히 합의된 단일 정답이 있는 것은 아니며, 프로젝트의 도메인 특성(자연키 존재 여부, 엔티티가 컬렉션에 들어가기 전에 저장이 보장되는지)에 따라 선택이 달라질 수 있다. 이 글에서 재현한 identity hash 기반의 구체적 출력값(버킷 배치 등)은 JVM 벤더나 버전에 따라 내부 구현이 달라질 수 있지만, "다른 버킷에 배치된다"는 결과 자체는 `HashMap`의 공개된 동작 방식에 의해 보장되는 부분이라 결론에는 영향이 없다.

## 참고문헌

1. Oracle, "Object (Java SE 21 & JDK 21)" — Java Platform, Standard Edition API Specification, https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html (확인일: 2026-08-23)
2. Hibernate ORM User Guide, "Implementing equals() and hashCode()" (Domain Model 챕터), https://docs.hibernate.org/stable/orm/userguide/html_single/#mapping-model-pojo-equalshashcode (확인일: 2026-08-23)
3. Vlad Mihalcea, "How to implement equals and hashCode using the JPA entity identifier (Primary Key)", https://vladmihalcea.com/how-to-implement-equals-and-hashcode-using-the-jpa-entity-identifier/ (확인일: 2026-08-23)

## 종합적 의견

> 전체적으로 이 주제를 다시 정리하면서 느낀 점은, `equals()`/`hashCode()` 계약이 "이론상 지켜야 하는 규칙"이 아니라 "해시 기반 컬렉션이 실제로 의존하는 구현 전제"라는 사실이 코드로 직접 재현해보기 전까지는 잘 와닿지 않는다는 것이다. `Set` 크기가 2로 나오고 `contains()`가 `false`를 반환하는 출력을 실제로 눈으로 보고 나면, "왜 함께 오버라이드해야 하는가"라는 질문에 교과서적 설명보다 훨씬 설득력 있는 답이 된다. JPA 엔티티 부분은 특히 신입 개발자보다 오히려 "더 엄격하게 짜야 한다"는 압박을 느끼는 시니어가 `getClass()` 비교를 선택했다가 프록시 문제로 고생하는 경우를 종종 봐서, 이 글에 포함시키는 게 실무적으로 의미 있다고 판단했다. 다만 이 결론이 모든 팀에 그대로 적용되는 정답은 아니며, 프레임워크 버전과 도메인 모델링 방식에 따라 재검토가 필요하다는 것이 개인적인 견해다.

## 꼬리질문

- `record` 타입(Java 16+)이 자동 생성하는 `equals()/hashCode()`는 JPA 엔티티에도 그대로 적용할 수 있을까? (엔티티는 mutable해야 하고 기본 생성자가 필요하다는 JPA 스펙 제약과 `record`의 불변성이 어떻게 충돌하는지)
- EqualsVerifier 같은 라이브러리를 CI 파이프라인에 도입하면 이 글에서 재현한 계약 위반을 테스트 단계에서 얼마나 조기에 잡아낼 수 있을까?
- Kotlin의 `data class`가 생성하는 `equals()/hashCode()`도 JPA 엔티티(특히 상속/프록시 시나리오)에서 동일한 함정을 가지는가?

## 백링크

- [Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가](https://beji-tech.blogspot.com/2026/08/java-list-vs-set-vs-map.html)
- [SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시](https://beji-tech.blogspot.com/2026/08/solid-java-5.html)

