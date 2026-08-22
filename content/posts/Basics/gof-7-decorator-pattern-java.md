---
id: '1920448605652878906'
publishedAt: '2026-08-14T11:27:53.754-07:00'
slug: gof-7-decorator-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 7. 데코레이터 패턴 (Decorator Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T12:02:42.806-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-7-decorator-pattern-java.html
---

# [GoF 디자인 패턴] 7. 데코레이터 패턴 (Decorator Pattern) 개념과 Java 실전 예시

## 요약

데코레이터 패턴(Decorator Pattern)은 상속 대신 객체를 겹겹이 감싸는 방식으로 기능을 동적으로 추가하는 구조 패턴입니다. 상속으로 기능 조합을 표현하면 경우의 수만큼 서브클래스가 폭발적으로 늘어나는데, 데코레이터 패턴은 원본 객체를 수정하지 않고도 런타임에 필요한 기능만 유연하게 조합할 수 있게 해줍니다. 이 글에서는 패턴의 동작 메커니즘, 실제 동작하는 Java 코드, 그리고 Java I/O 클래스 체계 같은 실무 적용 사례를 다룹니다.

## 본문

### 1. 배경 및 문제점

상속을 통해 기능을 조합하려고 하면 경우의 수마다 새로운 서브클래스가 필요합니다. 예를 들어 커피에 우유를 추가한 버전, 모카를 추가한 버전, 우유와 모카를 모두 추가한 버전을 각각 서브클래스로 만들면 조합 가짓수가 늘어날수록 클래스 수가 기하급수적으로 증가하는 클래스 폭발(Class Explosion) 문제가 발생합니다. 이런 구조는 새로운 옵션이 하나만 추가되어도 관련된 모든 조합의 서브클래스를 새로 만들거나 수정해야 하므로 유지보수가 매우 어려워집니다.

### 2. 해결책 및 동작 메커니즘

데코레이터 패턴은 객체를 동일한 인터페이스를 구현하는 감싸개(Wrapper) 데코레이터로 겹겹이 포장하여, 원본 소스 코드를 수정하지 않고도 런타임에 동적으로 새로운 기능을 추가하고 조합합니다. 각 데코레이터는 원본 객체(또는 다른 데코레이터)를 감싸고 있다가, 자신의 부가 기능을 수행한 뒤 감싸고 있는 대상에게 나머지 작업을 위임합니다.

**실제 서비스 동작 예시**: 커피숍의 커스텀 주문 시스템을 생각해보면, 에스프레소 객체를 생성한 뒤 그 위에 모카 데코레이터를 씌우고, 다시 휘핑크림 데코레이터를 씌우는 방식으로 객체의 설명과 가격이 동적으로 누적됩니다.

**비유**: 에스프레소라는 원형은 건드리지 않은 채로, 손님의 취향에 따라 우유 추가, 시럽 추가, 휘핑크림 토핑을 포장지로 겹겹이 싸듯이 얹어 새로운 메뉴를 즉석에서 만들어내는 것과 같습니다.

### 3. 실무 주의점: 디버깅 난이도 상승

데코레이터를 여러 겹으로 쌓을수록 실제 호출 스택이 매우 깊어집니다. 데코레이터를 10개 이상 겹겹이 감싸면 어느 한 지점에서 예외가 발생했을 때 스택 트레이스(Stack Trace)를 따라가며 원인을 추적하기가 꽤 까다로워집니다. 또한 데코레이터의 적용 순서에 따라 최종 결과가 달라질 수 있어(예: 할인 데코레이터를 먼저 적용하느냐 세금 데코레이터를 먼저 적용하느냐), 조합 순서 자체가 비즈니스 로직의 일부가 된다는 점도 실무에서 주의해야 할 부분입니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
package com.gof.decorator;

// 1. 기본 컴포넌트 인터페이스 (Component)
interface Coffee {
    String getDescription();
    int getCost();
}

// 2. 기본 구현체 (Concrete Component) - 베이스가 되는 원본 객체
class Espresso implements Coffee {
    @Override
    public String getDescription() { return "에스프레소"; }
    @Override
    public int getCost() { return 3000; }
}

class Americano implements Coffee {
    @Override
    public String getDescription() { return "아메리카노"; }
    @Override
    public int getCost() { return 3500; }
}

// 3. 추상 데코레이터 (Decorator) - Coffee를 구현함과 동시에 Coffee를 필드로 보유
abstract class CoffeeDecorator implements Coffee {
    protected Coffee decoratedCoffee; // 포장할 대상 객체

    public CoffeeDecorator(Coffee decoratedCoffee) {
        this.decoratedCoffee = decoratedCoffee;
    }

    @Override
    public String getDescription() {
        return decoratedCoffee.getDescription(); // 원본 객체 위임
    }

    @Override
    public int getCost() {
        return decoratedCoffee.getCost(); // 원본 객체 위임
    }
}

// 4. 구체 데코레이터 (Concrete Decorators) - 토핑들
class MilkDecorator extends CoffeeDecorator {
    public MilkDecorator(Coffee coffee) { super(coffee); }

    @Override
    public String getDescription() {
        return super.getDescription() + " + 스팀 밀크";
    }

    @Override
    public int getCost() {
        return super.getCost() + 500; // 우유 추가비용 500원 누적
    }
}

class MochaDecorator extends CoffeeDecorator {
    public MochaDecorator(Coffee coffee) { super(coffee); }

    @Override
    public String getDescription() {
        return super.getDescription() + " + 모카 시럽";
    }

    @Override
    public int getCost() {
        return super.getCost() + 800;
    }
}

class WhipDecorator extends CoffeeDecorator {
    public WhipDecorator(Coffee coffee) { super(coffee); }

    @Override
    public String getDescription() {
        return super.getDescription() + " + 휘핑 크림";
    }

    @Override
    public int getCost() {
        return super.getCost() + 700;
    }
}

public class DecoratorDemo {
    public static void main(String[] args) {
        System.out.println("=== 커피 커스텀 주문 시스템 ===");

        // 1. 기본 에스프레소 주문
        Coffee espresso = new Espresso();
        System.out.println("주문 1: " + espresso.getDescription() + " | 가격: " + espresso.getCost() + "원");

        // 2. 에스프레소 + 스팀 밀크 + 모카 시럽 (카페모카)
        Coffee cafeMocha = new Espresso();
        cafeMocha = new MilkDecorator(cafeMocha); // 우유 포장
        cafeMocha = new MochaDecorator(cafeMocha); // 그 위에 모카 포장
        System.out.println("주문 2: " + cafeMocha.getDescription() + " | 가격: " + cafeMocha.getCost() + "원");

        // 3. 아메리카노 + 휘핑크림 + 시럽 2번 (Java I/O와 동일한 체이닝 방식)
        Coffee customCoffee = new WhipDecorator(
                                new MochaDecorator(
                                  new MochaDecorator(
                                    new Americano()
                                  )
                                )
                              );
        System.out.println("주문 3: " + customCoffee.getDescription() + " | 가격: " + customCoffee.getCost() + "원");
    }
}
```

세 번째 주문 예시에서 볼 수 있듯, 데코레이터는 여러 겹으로 자유롭게 중첩할 수 있으며 각 데코레이터가 감싸는 순서대로 설명과 가격이 누적됩니다.

### 5. 실무 프레임워크 적용 사례

Java I/O 클래스 체계가 데코레이터 패턴의 가장 대표적인 실무 사례입니다. `new BufferedReader(new InputStreamReader(System.in))`처럼 기본 스트림 객체를 다른 스트림 객체로 겹겹이 감싸서 버퍼링, 문자 인코딩 변환 같은 기능을 동적으로 추가합니다. `Collections.synchronizedList()`도 원본 리스트 객체를 감싸 동기화 기능을 추가하는 데코레이터 패턴의 구현체입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 데코레이터 패턴은 상속 대신 객체를 감싸는 방식으로 런타임에 동적으로 기능을 추가하는 구조 패턴이다 | verified | Gamma et al., Design Patterns (1994) |
| CLAIM-002: 상속만으로 기능 조합을 표현하면 조합 가짓수에 비례해 서브클래스 수가 급격히 늘어나는 클래스 폭발 문제가 발생한다 | verified | Gamma et al., Design Patterns (1994), Decorator 동기(Motivation) 섹션 |
| CLAIM-003: java.io.BufferedReader와 InputStreamReader의 조합은 데코레이터 패턴의 실제 구현 사례다 | verified | Oracle Java SE 8 API, java.io 패키지 구조 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

데코레이터 패턴은 Java I/O를 다뤄본 사람이라면 이미 무의식적으로 써본 패턴이라고 생각합니다. `BufferedReader`와 `InputStreamReader`를 겹쳐 쓰는 코드를 처음 배울 때는 왜 이렇게 복잡하게 감싸는지 이해하기 어려웠지만, 각 클래스가 단일 책임만 지도록 쪼개고 필요한 조합만 골라 쓸 수 있다는 점에서 상속보다 훨씬 유연한 설계라는 걸 나중에야 체감했습니다. 다만 실무에서 데코레이터를 4~5겹 이상 쌓아야 하는 상황이 온다면, 그 자체가 설계를 다시 점검해야 한다는 신호일 수 있다고 봅니다. 조합이 지나치게 많아지면 차라리 빌더 패턴이나 설정 객체로 옵션을 명시적으로 관리하는 편이 가독성 측면에서 나을 때가 많습니다.

## 한계와 반론

데코레이터 패턴은 겹겹이 쌓인 래퍼 객체들 때문에 디버깅 시 실제 원본 객체의 상태를 파악하기 어렵고, 객체 식별(Identity) 문제도 발생할 수 있습니다(래핑된 객체와 원본 객체가 `equals()` 상에서 다르게 취급될 수 있음). 반론으로는, 이런 복잡성은 데코레이터 자체의 문제가 아니라 조합 개수를 과도하게 늘린 설계의 문제이며, 각 데코레이터를 작고 단일한 책임으로 유지하면 충분히 관리 가능한 수준이라는 의견도 있습니다. 실무에서는 데코레이터의 중첩 깊이에 어느 정도 상한선을 정해두는 것이 현실적인 절충안입니다.

## 참고문헌

1. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
2. [Java SE 8 API - BufferedReader](https://docs.oracle.com/javase/8/docs/api/java/io/BufferedReader.html) (확인일: 2026-08-17)
3. [Refactoring.Guru - Decorator Pattern](https://refactoring.guru/design-patterns/decorator) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

데코레이터 패턴은 "상속의 경직성"이라는 객체지향 설계의 오래된 고민에 대한 실용적인 답입니다. Java I/O 클래스 체계처럼 이미 언어 표준 라이브러리에 깊이 녹아든 패턴이라는 점에서, 이론적인 개념을 넘어 실제로 검증된 설계 전략임을 알 수 있습니다. 다만 이 패턴을 도입할 때는 조합의 유연성과 디버깅 난이도 사이의 트레이드오프를 항상 함께 고려해야 하며, 조합 경우의 수가 지나치게 많아지는 시점에는 다른 패턴과의 혼합 적용도 검토할 필요가 있습니다.

## 꼬리질문

1. **데코레이터 체인이 깊어질 때 발생하는 성능 오버헤드(메서드 호출 위임 비용)는 실무에서 어느 정도까지 허용 가능한가?**
   - 추천 참고 URL: https://refactoring.guru/design-patterns/decorator
2. **데코레이터 패턴과 프록시 패턴은 구조가 유사한데, 두 패턴을 구분하는 실질적인 설계 기준은 무엇인가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Design_Patterns

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)