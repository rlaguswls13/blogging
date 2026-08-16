---
id: "4385136898835167457"
title: "[GoF 디자인 패턴] 10. 전략 패턴 (Strategy Pattern) 개념과 Java 실전 예시"
slug: "gof-10-strategy-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-10-strategy-pattern-java.html"
publishedAt: "2026-08-14T11:28:07.000-07:00"
updatedAt: "2026-08-15T16:18:54.106-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 10. 전략 패턴 (Strategy Pattern) 개념과 Java 실전 예시

### Section 1: 배경 및 문제점

특정 작업을 수행하는 알고리즘이나 비��니스 규칙이 여러 개 존재할 때, 이를 하나의 클래스 내에 수많은 if-else 블록으로 하드코딩하면 코드가 거대해지고 유지보수가 불가능해집니다. 새로운 정책이 추가될 때마다 기존 코드를 수정해야 하므로 OCP(개방-폐쇄 원칙)를 위배하게 됩니다.

### Section 2: 해결책 및 동작 메커니즘

전략(Strategy) 패턴은 실행 중에 알���리즘(전략)을 선택할 수 있게 해주는 행위 패턴입니다. 각 알고리즘을 캡슐화된 클래스로 분리하고 공통 인터페이스를 구현하게 하여, 클라이언트(Context)의 코드 변경 없이도 전략을 동적으로 교체할 수 있습니다.

  **실제 서비스 적용 사례: 카*오T 택시 요금 계산**
  카*오T에서 택시를 호출할 때 일반 호출, 스마트 호출, 블루, 벤티 등 호출 방식에 따라 요금 계산 산식이 완전히 다릅니다. 이때 '요금 계산' 이라는 Context에 각 호출 방식별 '계산 전략(Strategy)' 객체만 동적으로 갈아끼워 로직의 결합도를 낮춥니다.

  **실생활 비유: 네비게이션 길찾기**
  목적지까지 가는 경로는 동일하지만, 사용자가 '최단 거리', '무료 도로 우선', '고속도로 우선' 등 어떤 옵션(전략)을 선택하느냐에 따라 안내 알고리즘이 실시간 교체되어 작동합니다.

### Section 3: 실무 주의점

  **주의:** 전략의 개수가 늘어날수록 관리해야 할 클래스의 수가 증가합니다. 또한 클라이언트가 적절한 전략을 선택하기 위해 각각의 전략이 어떻게 동작하는지(구현체의 차이점) 어느 정도 인지하고 있어야 한다는 단점이 있습니다.

### Section 4: 실제 동작하는 Java 완벽 예시 코드

```
`
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
    private int couponAmount;

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
    private List<String> items = new ArrayList<>();
    private int totalAmount = 0;
    private DiscountStrategy discountStrategy; // 전략 객체 보유

    public ShoppingCart() {
        // 기본 전략 설정 (할인 없음)
        this.discountStrategy = new NoDiscountStrategy();
    }

    // 런타임에 전략을 동적으로 변경할 수 있는 Setter
    public void setDiscountStrategy(DiscountStrategy discountStrategy) {
        this.discountStrategy = discountStrategy;
    }

    public void addItem(String item, int price) {
        items.add(item);
        totalAmount += price;
    }

    public void checkout() {
        // 현재 설정된 전략에 따라 최종 결제 금액 계산
        int finalPrice = discountStrategy.applyDiscount(totalAmount);
        System.out.println("주문 총액: " + totalAmount + "원");
        System.out.println("결제 금액 (할인 적용): " + finalPrice + "원\n");
    }
}

// 4. 클라이언트 (Main)
public class StrategyPatternDemo {
    public static void main(String[] args) {
        ShoppingCart cart = new ShoppingCart();
        cart.addItem("무선 이어폰", 100000);
        cart.addItem("보조 배터리", 30000);

        System.out.println("=== 1. 일반 결제 (할인 없음) ===");
        cart.checkout();

        System.out.println("=== 2. VIP 회원 전환 및 재결제 ===");
        // 전략 교체 (동적 변경)
        cart.setDiscountStrategy(new VipDiscountStrategy());
        cart.checkout();

        System.out.println("=== 3. 5만원 깜짝 쿠폰 적용 ===");
        // 또 다른 전략으로 교체
        cart.setDiscountStrategy(new CouponDiscountStrategy(50000));
        cart.checkout();
    }
}
`
```

#### 실행 결과 (Expected Output)

```
`
=== 1. 일반 결제 (할인 없음) ===
주문 총액: 130000원
결제 금액 (할인 적용): 130000원

=== 2. VIP 회원 전환 및 재결제 ===
주문 총액: 130000원
결제 금액 (할인 적용): 104000원

=== 3. 5만원 깜짝 쿠폰 적용 ===
주문 총액: 130000원
결제 금액 (할인 적용): 80000원
`
```

### Section 5: 실무 프레임워크 적용 사례

  
- **Java Collections.sort(List, Comparator):** `Comparator` 인터페이스 자체가 전략이며, 오름차순/내림차순/길이순 등 정렬 전략을 런타임에 넘겨줍니다.
  
- **Spring Security PasswordEncoder:** 암호화 방식을 결정할 때 BCrypt, SHA-256 등 다양한 전략을 주입받아 비밀번호 해싱을 수행합니다.

### Section 6: 참고자료

  
- GoF의 디자인 패턴 (Addison-Wesley)
  
- Effective Java - Item 43
