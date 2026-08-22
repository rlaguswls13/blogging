---
id: '5260378206272592514'
publishedAt: '2026-08-14T11:28:55.000-07:00'
slug: gof-13-state-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
- GoF_Series
title: '[GoF 디자인 패턴] 13. 상태 패턴 (State Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T12:02:25.808-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-13-state-pattern-java.html
---

# [GoF 디자인 패턴] 13. 상태 패턴 (State Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **행위 패턴 (Behavioral)**

## 요약

상태 패턴은 객체의 내부 상태에 따라 행동이 달라져야 할 때, 그 상태 각각을 별도의 클래스로 분리하여 객체가 마치 클래스를 바꾼 것처럼 행동하게 만드는 행위 패턴입니다. 주문 상태(결제 대기/배송 중/배송 완료), 자판기 상태(대기/동전 투입/상품 배출) 같은 상태 기계(State Machine)를 다룰 때, 거대한 `switch`문 없이 상태 전이를 깔끔하게 표현할 수 있습니다. 이 글에서는 상태 패턴이 해결하는 문제, 상태 전이를 캡슐화하는 방법, 완전한 Java 예제, 그리고 실무 프레임워크에서의 활용 사례를 다룹니다.

## 본문

### 1. 배경 및 문제점

온라인 쇼핑몰의 주문(Order) 객체를 생각해 보겠습니다. 주문은 "결제 대기 → 결제 완료 → 배송 중 → 배송 완료" 같은 여러 상태를 거치며, 상태에 따라 "취소 가능 여부", "배송 조회 가능 여부" 같은 동작이 달라집니다. 이걸 하나의 `Order` 클래스 안에서 `if (status == PENDING) {...} else if (status == PAID) {...} else if (status == SHIPPED) {...}`처럼 처리하면, 상태가 늘어날수록 이 조건문이 모든 메서드마다 반복되어 거대해지고, 새로운 상태가 추가될 때마다 관련된 모든 메서드를 찾아 수정해야 하는 위험한 구조가 됩니다.

### 2. 패턴 정의 및 동작 메커니즘

상태 패턴은 각 상태(PENDING, PAID, SHIPPED 등)를 별도의 클래스로 만들고, 공통 `State` 인터페이스를 구현하게 합니다. `Order`(Context) 객체는 현재 상태 객체에 대한 참조 하나만 갖고 있으며, 실제 동작 요청이 들어오면 그 요청을 현재 상태 객체에게 위임합니다. 상태 객체는 자기 자신의 로직을 수행한 뒤, 필요하면 Context가 참조하는 상태 객체 자체를 다음 상태로 교체합니다. 즉 Context 코드는 상태가 몇 개든, 새로운 상태가 추가되든 전혀 수정할 필요가 없습니다.

**실제 서비스 적용 예시: 자동판매기 상태 관리** — 자판기는 "동전 없음 → 동전 투입됨 → 상품 배출 중" 상태를 오갑니다. 동전 없음 상태에서 상품 버튼을 누르면 "동전을 넣어주세요"라고만 반응하고, 동전 투입됨 상태에서 같은 버튼을 누르면 실제로 상품을 배출하고 "동전 없음" 상태로 되돌아갑니다. 각 상태 클래스가 자신이 받을 수 있는 요청과 다음 상태로의 전이를 스스로 책임집니다.

**비유: 신호등** — 신호등은 빨강/노랑/초록이라는 상태를 가지며, 각 상태에서 "다음"이라는 동일한 신호를 받아도 전이되는 다음 색깔이 다릅니다(빨강 다음엔 초록, 초록 다음엔 노랑). 신호등 자체는 "지금 무슨 색인지"만 기억할 뿐, 색깔이 바뀌는 규칙은 각 색깔(상태)이 스스로 알고 있습니다.

### 3. Java 실전 구현 코드

아래는 주문 상태를 상태 패턴으로 구현한 예제입니다. 각 상태 클래스가 자신이 처리할 수 있는 동작과 다음 상태로의 전이를 담당합니다.

```java
package com.gof.state;

// 1. 상태 인터페이스 (State)
interface OrderState {
    void pay(OrderContext order);
    void ship(OrderContext order);
    String getStatusName();
}

// 2. 컨텍스트 (Context) - 현재 상태를 위임받아 처리
class OrderContext {
    private OrderState currentState;

    public OrderContext() {
        this.currentState = new PendingState(); // 초기 상태: 결제 대기
    }

    public void setState(OrderState state) {
        this.currentState = state;
    }

    public void pay() {
        currentState.pay(this);
    }

    public void ship() {
        currentState.ship(this);
    }

    public String getCurrentStatus() {
        return currentState.getStatusName();
    }
}

// 3. 구체적인 상태 (Concrete States)
class PendingState implements OrderState {
    @Override
    public void pay(OrderContext order) {
        System.out.println("💳 결제가 완료되었습니다.");
        order.setState(new PaidState()); // 다음 상태로 전이
    }

    @Override
    public void ship(OrderContext order) {
        System.out.println("⚠️ 결제 전에는 배송을 시작할 수 없습니다.");
    }

    @Override
    public String getStatusName() { return "결제 대기"; }
}

class PaidState implements OrderState {
    @Override
    public void pay(OrderContext order) {
        System.out.println("⚠️ 이미 결제가 완료된 주문입니다.");
    }

    @Override
    public void ship(OrderContext order) {
        System.out.println("🚚 배송을 시작합니다.");
        order.setState(new ShippedState());
    }

    @Override
    public String getStatusName() { return "결제 완료"; }
}

class ShippedState implements OrderState {
    @Override
    public void pay(OrderContext order) {
        System.out.println("⚠️ 이미 배송이 시작된 주문은 재결제할 수 없습니다.");
    }

    @Override
    public void ship(OrderContext order) {
        System.out.println("⚠️ 이미 배송 중인 주문입니다.");
    }

    @Override
    public String getStatusName() { return "배송 중"; }
}

public class StatePatternMain {
    public static void main(String[] args) {
        OrderContext order = new OrderContext();

        System.out.println("=== 현재 상태: " + order.getCurrentStatus() + " ===");

        System.out.println("\n=== 배송 시도 (결제 전) ===");
        order.ship(); // 결제 대기 상태이므로 거부됨

        System.out.println("\n=== 결제 진행 ===");
        order.pay(); // 결제 대기 -> 결제 완료로 전이
        System.out.println("현재 상태: " + order.getCurrentStatus());

        System.out.println("\n=== 배송 시작 ===");
        order.ship(); // 결제 완료 -> 배송 중으로 전이
        System.out.println("현재 상태: " + order.getCurrentStatus());
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 현재 상태: 결제 대기 ===

=== 배송 시도 (결제 전) ===
⚠️ 결제 전에는 배송을 시작할 수 없습니다.

=== 결제 진행 ===
💳 결제가 완료되었습니다.
현재 상태: 결제 완료

=== 배송 시작 ===
🚚 배송을 시작합니다.
현재 상태: 배송 중
*/
```

### 4. 실무 주의점 및 트레이드오프

상태 클래스의 개수가 상태 종류만큼 늘어나며, 상태 전이 로직이 여러 클래스에 흩어지기 때문에 전체 상태 기계의 흐름을 한눈에 파악하기가 오히려 어려워질 수 있습니다. 상태 전이 규칙이 복잡하거나 상태 수가 매우 많다면(수십 개 이상), 개별 클래스 대신 상태 전이표(Transition Table)를 데이터로 관리하는 방식이나 전용 상태 기계 라이브러리를 검토하는 것이 낫습니다. 또한 상태 객체를 매번 `new`로 생성할지, 상태가 무상태(stateless)라면 싱글톤으로 재사용할지도 설계 시 결정해야 할 트레이드오프입니다.

### 5. 실무 프레임워크 적용 사례

Spring 생태계에는 상태 기계를 전문적으로 다루는 `Spring Statemachine` 프로젝트가 있어, 상태와 전이 규칙을 선언적으로 정의하고 상태 변화 시 이벤트를 발행할 수 있습니다. TCP 소켓의 연결 상태(CLOSED/LISTEN/ESTABLISHED 등)나 워크플로우 엔진의 작업 상태 관리도 상태 패턴의 개념을 그대로 따르는 대표적인 실무 사례입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 상태 패턴은 객체의 상태별 행동을 별도 클래스로 캡슐화하여 조건문 분기를 대체하는 행위 패턴이다 | verified | Gamma et al., Design Patterns (1994) State 챕터 |
| CLAIM-002: 상태 패턴에서 상태 전이는 각 상태 객체가 스스로 Context의 상태를 교체하는 방식으로 이루어진다 | verified | Gamma et al., Design Patterns State 챕터 |
| CLAIM-003: Spring Statemachine은 상태와 전이 규칙을 선언적으로 정의할 수 있는 공식 프로젝트다 | verified | Spring 공식 문서(Spring Statemachine 프로젝트 소개) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

상태 패턴은 배워두면 매우 유용하지만, 실무에서 상태가 2~3개뿐이고 전이 규칙도 단순하다면 굳이 클래스를 분리하지 않고 enum과 짧은 switch문으로 처리해도 충분하다고 생각합니다. 반대로 상태 수가 늘어나고("결제 대기/결제 완료/배송 준비/배송 중/배송 완료/환불 요청/환불 완료" 같은 7~8개 이상), 상태마다 허용되는 동작이 크게 다르다면 상태 패턴으로 전환하는 것이 유지보수성 면에서 확실히 낫습니다. 결국 "지금 이 switch문이 앞으로 더 복잡해질 가능성이 있는가"를 기준으로 판단하는 게 실용적입니다.

## 한계와 반론

상태 패턴은 상태 수가 적을 때는 오히려 클래스 수만 늘리는 과설계가 될 수 있습니다. 이 경우 enum 기반의 단순 조건 분기가 더 읽기 쉽다는 반론이 있습니다. 또한 상태 전이 로직이 여러 상태 클래스에 분산되어 있어, "이 상태 기계가 전체적으로 어떻게 동작하는가"를 파악하려면 모든 상태 클래스를 다 살펴봐야 하는 단점도 있습니다. 상태 전이표를 문서나 다이어그램으로 별도 관리하면 이 단점을 어느 정도 보완할 수 있습니다.

## 참고문헌

1. Spring, "Spring Statemachine Reference Documentation", [https://docs.spring.io/spring-statemachine/docs/current/reference/](https://docs.spring.io/spring-statemachine/docs/current/reference/) (확인일: 2026-08-17)
2. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
3. Refactoring.Guru, "State Design Pattern", [https://refactoring.guru/design-patterns/state](https://refactoring.guru/design-patterns/state) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

상태 패턴의 본질은 "상태에 따라 달라지는 행동"을 하나의 거대한 조건문이 아니라, 각 상태가 스스로 책임지는 여러 개의 작은 클래스로 나누는 것입니다. 이 덕분에 새로운 상태가 추가되어도 기존 상태 클래스나 Context를 건드릴 필요 없이 새 클래스 하나만 추가하면 되고, 각 상태의 규칙이 한 곳에 모여 있어 테스트하기도 쉬워집니다. 다만 모든 상태 기계에 무조건 적용할 필요는 없으며, 상태 수와 전이 복잡도가 실제로 이 구조적 비용을 정당화할 만큼 커졌을 때 도입하는 것이 합리적입니다.

## 꼬리질문

1. **상태 전이 규칙이 매우 복잡해질 때 상태 패턴 대신 상태 전이표(Transition Table) 기반 설계로 전환하는 기준은 무엇인가?**
   - 추천 참고 URL: https://refactoring.guru/design-patterns/state
2. **Spring Statemachine에서 상태 변화 시 이벤트를 리스너에게 전파하는 메커니즘은 옵저버 패턴과 어떻게 결합되어 있는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-statemachine/docs/current/reference/

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)