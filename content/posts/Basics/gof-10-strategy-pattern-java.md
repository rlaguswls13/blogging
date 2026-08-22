---
id: '4385136898835167457'
publishedAt: '2026-08-14T11:28:07.000-07:00'
slug: gof-10-strategy-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 10. 전략 패턴 (Strategy Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:18:54.106-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-10-strategy-pattern-java.html
---

# [GoF 디자인 패턴] 10. 전략 패턴 (Strategy Pattern) 개념과 Java 실전 예시

## 요약

전략 패턴(Strategy Pattern)은 실행 중에 알고리즘(전략)을 선택할 수 있게 해주는 행위 패턴입니다. 각 알고리즘을 캡슐화된 클래스로 분리하고 공통 인터페이스를 구현하게 하여, 클라이언트(Context)의 코드 변경 없이도 전략을 동적으로 교체할 수 있습니다. 이 글에서는 쇼핑카트 할인 정책 예제를 통해 전략 패턴의 동작 원리를 살펴보고, `Comparator`나 `PasswordEncoder`처럼 Java·Spring 생태계에서 이 패턴이 실제로 어떻게 쓰이는지 다룹니다.

## 본문

### 1. 배경 및 문제점

특정 작업을 수행하는 알고리즘이나 비즈니스 규칙이 여러 개 존재할 때, 이를 하나의 클래스 내에 수많은 if-else 블록으로 하드코딩하면 코드가 거대해지고 유지보수가 불가능해집니다. 새로운 정책이 추가될 때마다 기존 코드를 직접 수정해야 하므로 개방-폐쇄 원칙(OCP)을 위배하게 됩니다.

### 2. 해결책 및 동작 메커니즘

전략 패턴은 각 알고리즘을 캡슐화된 클래스로 분리하고 공통 인터페이스를 구현하게 하여, 클라이언트(Context)의 코드 변경 없이도 전략을 동적으로 교체할 수 있게 합니다.

**실제 서비스 동작 예시**: 택시 호출 서비스에서 일반 호출, 스마트 호출, 프리미엄 호출 등 호출 방식에 따라 요금 계산 산식이 완전히 다른 경우를 생각해 봅시다. "요금 계산"이라는 Context에 각 호출 방식별 "계산 전략(Strategy)" 객체만 동적으로 갈아끼우면, 요금 정책이 추가되어도 Context 코드는 건드릴 필요가 없습니다.

**비유**: 내비게이션 길찾기를 떠올리면 이해가 쉽습니다. 목적지까지 가는 경로 탐색 자체는 동일하지만, 사용자가 "최단 거리", "무료 도로 우선", "고속도로 우선" 중 어떤 옵션(전략)을 선택하느냐에 따라 안내 알고리즘이 실시간으로 교체되어 작동합니다.

### 3. 실무 주의점

전략의 개수가 늘어날수록 관리해야 할 클래스 수가 함께 증가합니다. 또한 클라이언트가 적절한 전략을 선택하려면 각 전략이 내부적으로 어떻게 동작하는지, 즉 구현체 간의 차이점을 어느 정도 인지하고 있어야 한다는 단점이 있습니다. 전략이 3~4개를 넘어가면 어떤 상황에 어떤 전략을 선택해야 하는지 결정하는 로직(전략 선택 로직) 자체가 또 다른 if-else 덩어리가 될 수 있어, 이 경우 팩토리 패턴과 결합해 전략 선택 자체를 캡슐화하는 것이 일반적입니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
import java.util.ArrayList;
import java.util.List;

// 1. 전략 인터페이스 (Strategy)
interface DiscountStrategy {
    int applyDiscount(int originalPrice);
}

// 2. 구체적인 전략 클래스들 (Concrete Strategies)
class NoDiscountStrategy implements DiscountStrategy {
    @Override
    public int applyDiscount(int originalPrice) {
        return originalPrice; // 할인 없음
    }
}

class VipDiscountStrategy implements DiscountStrategy {
    @Override
    public int applyDiscount(int originalPrice) {
        return (int) (originalPrice * 0.8); // VIP 20% 할인
    }
}

class CouponDiscountStrategy implements DiscountStrategy {
    private final int couponAmount;

    public CouponDiscountStrategy(int couponAmount) {
        this.couponAmount = couponAmount;
    }

    @Override
    public int applyDiscount(int originalPrice) {
        int finalPrice = originalPrice - couponAmount;
        return Math.max(finalPrice, 0); // 쿠폰액 차감 (0원 이하 방지)
    }
}

// 3. 컨텍스트 (Context) - 전략을 사용하는 쇼핑 카트
class ShoppingCart {
    private final List<String> items = new ArrayList<>();
    private int totalAmount = 0;
    private DiscountStrategy discountStrategy; // 전략 객체 보유

    public ShoppingCart() {
        this.discountStrategy = new NoDiscountStrategy();
    }

    public void setDiscountStrategy(DiscountStrategy discountStrategy) {
        this.discountStrategy = discountStrategy;
    }

    public void addItem(String item, int price) {
        items.add(item);
        totalAmount += price;
    }

    public void checkout() {
        int finalPrice = discountStrategy.applyDiscount(totalAmount);
        System.out.println("주문 총액: " + totalAmount + "원");
        System.out.println("결제 금액(할인 적용): " + finalPrice + "원");
    }
}

public class StrategyPatternDemo {
    public static void main(String[] args) {
        ShoppingCart cart = new ShoppingCart();
        cart.addItem("wireless earbuds", 100000);
        cart.addItem("power bank", 30000);

        System.out.println("=== 1. 일반 결제 (할인 없음) ===");
        cart.checkout();

        System.out.println("=== 2. VIP 회원 전환 및 재결제 ===");
        cart.setDiscountStrategy(new VipDiscountStrategy());
        cart.checkout();

        System.out.println("=== 3. 쿠폰 적용 ===");
        cart.setDiscountStrategy(new CouponDiscountStrategy(50000));
        cart.checkout();
    }
}
```

실행하면 동일한 `ShoppingCart` 인스턴스가 `setDiscountStrategy()` 호출만으로 할인 정책을 실시간 교체하는 것을 볼 수 있습니다. 새로운 할인 정책이 추가되어도 `ShoppingCart` 클래스는 단 한 줄도 수정할 필요가 없습니다.

### 5. 실무 프레임워크 적용 사례

- **Java `Collections.sort(List, Comparator)`**: `Comparator` 인터페이스 자체가 전략입니다. 오름차순, 내림차순, 길이순 등 정렬 전략을 런타임에 넘겨주는 방식이 전략 패턴 그 자체입니다.
- **Spring Security `PasswordEncoder`**: 암호화 방식을 결정할 때 BCrypt, SCrypt 등 다양한 구현체(전략)를 주입받아 비밀번호 해싱을 수행합니다. 어떤 인코더를 빈으로 등록하느냐에 따라 애플리케이션 전체의 해싱 전략이 교체됩니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 전략 패턴은 알고리즘군을 캡슐화하고 상호 교체 가능하게 만들어 런타임에 알고리즘을 선택할 수 있게 한다 | verified | Design Patterns (Gamma et al., 1994) Strategy 챕터 |
| CLAIM-002: 전략 패턴은 개방-폐쇄 원칙(OCP)을 지키면서 새로운 알고리즘을 추가할 수 있게 해준다 | verified | Design Patterns (Gamma et al., 1994) Strategy의 Motivation 논의 |
| CLAIM-003: java.util.Comparator는 정렬 알고리즘을 Collections.sort() 호출 시점에 주입하는 전략 패턴의 실제 사례다 | verified | Oracle Java SE 8 API 문서 (java.util.Comparator) |
| CLAIM-004: Spring Security의 PasswordEncoder는 여러 구현체를 상호 교체 가능한 형태로 제공한다 | verified | Spring Security 공식 문서 PasswordEncoder 챕터 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

전략 패턴은 GoF 패턴 중에서도 가장 "이미 매일 쓰고 있지만 이름을 몰랐던" 패턴이라고 생각합니다. `Comparator`를 넘겨 정렬 기준을 바꾸는 코드를 작성해 본 개발자라면 이미 전략 패턴을 실전에서 써본 셈입니다. 개인적으로는 if-else 블록이 3개를 넘어가고, 그 분기들이 "같은 입력을 받아 다른 알고리즘으로 처리한다"는 공통점을 가질 때가 전략 패턴 도입을 검토할 신호라고 봅니다. 다만 전략이 1~2개뿐인 상황에서 미리 인터페이스를 파두는 것은 과도한 설계(YAGNI 위반)가 될 수 있어, 실제로 분기가 늘어나는 시점에 리팩터링으로 도입하는 것을 선호합니다.

## 한계와 반론

전략의 개수가 늘어날수록 클래스 파일 수가 함께 증가해 프로젝트 구조가 복잡해질 수 있습니다. 또한 각 전략 구현체가 서로 다른 파라미터나 사전 조건을 요구하는 경우, 공통 인터페이스만으로는 이 차이를 표현하기 어려워 클라이언트가 내부 구현을 어느 정도 알아야 하는 캡슐화 누수가 발생할 수 있습니다. 이런 이유로 전략이 극소수(1~2개)이거나 거의 변경되지 않는 경우에는, 전략 패턴 대신 단순 함수 파라미터나 람다 표현식으로 충분하다는 반론도 있습니다.

## 참고문헌

1. [Strategy pattern - Wikipedia](https://en.wikipedia.org/wiki/Strategy_pattern) (확인일: 2026-08-17)
2. [java.util.Comparator - Java SE 8 API Documentation](https://docs.oracle.com/javase/8/docs/api/java/util/Comparator.html) (확인일: 2026-08-17)
3. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

전략 패턴의 핵심 가치는 "알고리즘의 변경을 그 알고리즘을 사용하는 코드로부터 완전히 분리한다"는 데 있습니다. Java의 `Comparator`나 Spring Security의 `PasswordEncoder`처럼 이미 널리 쓰이는 표준 API 안에 전략 패턴이 자연스럽게 녹아 있다는 사실은, 이 패턴이 이론적 개념을 넘어 실무에서 검증된 설계임을 보여줍니다. 다만 모든 조건 분기를 전략 패턴으로 바꿔야 하는 것은 아니며, 분기 로직의 변경 빈도와 복잡도를 고려해 적용 시점을 판단하는 것이 중요합니다.

## 꼬리질문

1. **전략의 개수가 많아질 때 전략 선택 로직 자체를 팩토리 패턴과 결합하면 어떤 장단점이 생기는가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Strategy_pattern
2. **Java 8 람다 표현식 도입 이후 전략 패턴을 별도 클래스 대신 함수형 인터페이스로 구현하는 방식은 어떤 트레이드오프를 가지는가?**
   - 추천 참고 URL: https://docs.oracle.com/javase/8/docs/api/java/util/Comparator.html

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)