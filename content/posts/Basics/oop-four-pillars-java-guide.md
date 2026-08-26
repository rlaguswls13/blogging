---
author: ''
createdAt: '2026-08-26T00:25:36.003265Z'
factCheckScore: 0
id: '6012357972924723333'
notionPageId: null
publishedAt: '2026-08-25T22:44:27-07:00'
slug: oop-four-pillars-java-guide
status: published
tags:
- Basics
- Java
- OOP
title: 객체지향 프로그래밍 4대 특성 — 캡슐화, 상속, 다형성, 추상화의 Java 실전 적용
updatedAt: '2026-08-26T00:25:36.003265Z'
url: https://beji-tech.blogspot.com/2026/08/4-java.html
---

# 객체지향 프로그래밍 4대 특성 — 캡슐화, 상속, 다형성, 추상화의 Java 실전 적용

## 요약

객체지향 프로그래밍(OOP)의 4대 특성인 캡슐화, 상속, 다형성, 추상화는 대부분의 입문서에서 "동물 클래스가 짖는다" 같은 예시로 설명되지만, 정작 실무에서 가장 많이 부딪히는 문제는 정의를 몰라서가 아니라 **다형성(오버라이딩)과 오버로딩을 헷갈려서 발생하는 조용한 버그**입니다. 이 글은 Java 언어 명세(JLS)와 JVM 명세의 원문을 근거로 4대 특성을 각각 정의하고, 특히 `equals(Object)`를 오버라이딩한다고 착각하고 실제로는 오버로딩해버리는 실제 버그 패턴을 바이트코드 레벨(`invokevirtual`)까지 내려가서 분석합니다.

## 차별화 포인트

이 주제는 검색하면 "정의 + Animal/Dog 예시" 형태의 101 콘텐츠가 압도적으로 많습니다. 이 글의 차별화 지점은 두 가지입니다. 첫째, 다형성(오버라이딩)과 오버로딩이 Java 컴파일러·JVM 레벨에서 **서로 다른 바인딩 시점**(정적 바인딩 vs 동적 바인딩)으로 처리된다는 사실을 `javap -c`로 실제 바이트코드를 열어 `invokevirtual` 명령어의 피연산자가 컴파일 타임에 이미 어떤 메서드 시그니처로 고정되는지 직접 보여줍니다. 둘째, 이 혼동이 이론적 함정이 아니라 `equals(Object)`를 오버라이딩하려다 실수로 오버로딩해버려서 `HashSet`/`List.contains()`가 조용히 오작동하는, Effective Java에서도 별도 항목(Item 10)으로 다룰 만큼 실제로 자주 발생하는 버그라는 점을 재현 코드로 보여줍니다. 교과서적 정의만 반복하는 대신, "왜 이 버그가 발생하고, 왜 컴파일러가 못 잡아주는가"를 명세 원문 인용과 함께 설명합니다.

## 본문

### 왜 4대 특성을 "정의"가 아니라 "메커니즘"으로 봐야 하는가

캡슐화, 상속, 다형성, 추상화는 서로 독립된 4개의 규칙이 아니라, Java라는 언어가 "변경에 강한 코드"를 만들기 위해 선택한 4가지 설계 도구입니다. 각각을 따로 암기하면 실무에서 왜 필요한지 와닿지 않지만, "이 코드가 나중에 바뀔 때 얼마나 적은 범위만 건드리면 되는가"라는 질문을 기준으로 보면 네 가지가 서로 맞물려 있다는 게 보입니다. 아래에서는 각 특성을 정의하고, 그중에서도 실무 버그와 가장 직결되는 다형성을 깊이 파고듭니다.

### 1. 캡슐화(Encapsulation) — 상태를 숨기고 계약만 노출

캡슐화는 객체의 내부 상태(필드)를 외부에서 직접 접근하지 못하게 막고, 정해진 메서드(계약)를 통해서만 상태를 변경하도록 강제하는 것입니다. Java는 `private`/`protected`/`public` 접근 제어자와 getter/setter 관례로 이를 구현합니다.

```java
public class BankAccount {
    private double balance; // 외부에서 직접 balance = -1000 같은 접근 불가

    public BankAccount(double initialBalance) {
        if (initialBalance < 0) {
            throw new IllegalArgumentException("초기 잔액은 음수일 수 없습니다.");
        }
        this.balance = initialBalance;
    }

    public void withdraw(double amount) {
        if (amount > balance) {
            throw new IllegalStateException("잔액 부족");
        }
        balance -= amount; // 이 검증 로직을 우회할 방법이 없다
    }

    public double getBalance() {
        return balance;
    }
}
```

`balance` 필드가 `public`이었다면 `account.balance = -1000;`처럼 검증 로직을 완전히 우회하는 코드가 컴파일 타임에 걸러지지 않습니다. 캡슐화의 핵심은 단순히 "필드를 숨긴다"가 아니라, **불변 조건(invariant)을 지킬 수 있는 유일한 통로를 메서드로 제한한다**는 점입니다.

### 2. 상속(Inheritance) — 코드 재사용이 아니라 "is-a" 계약

상속은 기존 클래스(상위 클래스)의 필드와 메서드를 하위 클래스가 물려받는 메커니즘입니다. 다만 상속을 "코드 중복을 줄이는 도구"로만 이해하면 SOLID 원칙의 리스코프 치환 원칙(LSP) 위반 같은 문제로 이어지기 쉽습니다. 상속은 코드 재사용 수단이기 이전에, "하위 클래스는 상위 클래스가 맺은 행위 계약을 위반하지 않아야 한다"는 약속입니다.

```java
class Vehicle {
    protected int speed;

    void accelerate(int amount) {
        speed += amount;
    }
}

class ElectricCar extends Vehicle {
    // ElectricCar는 Vehicle의 필드/메서드를 그대로 물려받는다
    void regenerativeBrake(int amount) {
        speed = Math.max(0, speed - amount);
    }
}
```

Java는 단일 상속(`extends`는 클래스 하나만 가능)만 허용하고, 여러 타입의 계약을 동시에 따르고 싶을 때는 인터페이스의 다중 구현(`implements`)을 씁니다. 이는 "다이아몬드 문제"(두 상위 클래스가 같은 필드를 물려줄 때의 모호함)를 언어 차원에서 원천 차단하기 위한 설계입니다.

### 3. 추상화(Abstraction) — 구현이 아니라 "무엇을 할 수 있는가"에 의존

추상화는 세부 구현을 감추고 "무엇을 할 수 있는가"라는 인터페이스(계약)만 외부에 노출하는 것입니다. Java에서는 `interface`와 `abstract class`로 구현합니다.

```java
interface PaymentGateway {
    boolean charge(String accountId, double amount);
}

class TossPaymentGateway implements PaymentGateway {
    public boolean charge(String accountId, double amount) {
        // 실제 Toss API 호출 로직 (세부 구현은 외부에 노출되지 않음)
        return true;
    }
}

class OrderService {
    private final PaymentGateway gateway; // 구체 클래스가 아니라 인터페이스에 의존

    OrderService(PaymentGateway gateway) {
        this.gateway = gateway;
    }

    void placeOrder(String accountId, double amount) {
        if (!gateway.charge(accountId, amount)) {
            throw new IllegalStateException("결제 실패");
        }
    }
}
```

`OrderService`는 결제 대행사가 Toss든 카카오페이든 신경 쓰지 않습니다. 다만 추상화를 지나치게 앞서서 적용하면 오히려 해가 됩니다 — 구현체가 하나뿐인데도 "나중에 바뀔 수도 있으니까"라는 이유만으로 인터페이스를 미리 만들어두는 것은 YAGNI(You Aren't Gonna Need It) 위반이자 불필요한 간접 계층만 늘리는 결과로 이어집니다. 추상화는 "실제로 여러 구현이 존재하거나 곧 존재할 것"이라는 근거가 있을 때 도입하는 것이 원칙입니다.

### 4. 다형성(Polymorphism) — 그리고 오버로딩과의 결정적 차이

다형성은 "하나의 참조 타입으로 여러 실제 타입의 객체를 다룰 수 있는" 성질입니다. Java 공식 튜토리얼은 이를 다음과 같이 설명합니다.

> "The Java virtual machine (JVM) calls the appropriate method for the object that is referred to in each variable. It does not call the method that is defined by the variable's type. This behavior is referred to as virtual method invocation."

즉, 변수의 **선언된 타입**이 아니라 그 변수가 **실제로 가리키는 객체의 런타임 타입**을 기준으로 어떤 메서드가 실행될지 결정됩니다. 이것이 오버라이딩(overriding)이 만드는 다형성입니다.

```java
class Animal {
    void speak() { System.out.println("...."); }
}

class Dog extends Animal {
    @Override
    void speak() { System.out.println("멍멍!"); }
}

class Cat extends Animal {
    @Override
    void speak() { System.out.println("야옹!"); }
}

public class PolymorphismDemo {
    public static void main(String[] args) {
        Animal[] animals = { new Dog(), new Cat() };
        for (Animal a : animals) {
            a.speak(); // 선언 타입은 Animal이지만 실제 객체 타입에 따라 다르게 실행됨
        }
        // 출력: 멍멍!  야옹!
    }
}
```

문제는 여기서 시작됩니다. **오버로딩(overloading)은 다형성과 전혀 다른 메커니즘**인데도 이름이 비슷해서 자주 혼동됩니다. Java 공식 튜토리얼은 이 둘을 명확히 구분합니다.

> "In a subclass, you can overload the methods inherited from the superclass. Such overloaded methods neither hide nor override the superclass instance methods—they are new methods, unique to the subclass."

오버로딩은 같은 이름이지만 **매개변수 시그니처가 다른** 별개의 새 메서드를 정의하는 것이고, 어떤 오버로딩 버전이 호출될지는 **컴파일 타임에 변수의 선언 타입만 보고 결정**됩니다. 반면 오버라이딩(다형성)은 **런타임에 실제 객체 타입을 보고 결정**됩니다. 이 차이를 코드로 직접 재현하면 다음과 같습니다.

```java
class Printer {
    void print(Animal a) { System.out.println("Animal 버전 호출"); }
    void print(Dog d) { System.out.println("Dog 버전 호출"); }
}

public class OverloadPitfall {
    public static void main(String[] args) {
        Printer printer = new Printer();
        Animal ref = new Dog(); // 실제 객체는 Dog이지만 선언 타입은 Animal
        printer.print(ref);     // "Animal 버전 호출" 출력!
        // 오버로딩은 컴파일 타임에 "ref의 선언 타입(Animal)"만 보고
        // print(Animal) 버전을 이미 확정해버리기 때문
    }
}
```

`ref`가 가리키는 실제 객체는 `Dog`이지만, 컴파일러는 `ref`의 **선언 타입**(`Animal`)만 보고 `print(Animal)` 오버로딩을 호출하도록 바이트코드를 이미 확정합니다. 이것이 실무에서 가장 흔하게, 그리고 가장 조용하게 버그를 만드는 지점입니다 — 바로 `equals()` 메서드입니다.

### 실전 버그 재현: equals()를 "오버라이딩"한다고 착각하고 "오버로딩"해버리는 함정

`Object.equals(Object obj)`를 오버라이딩하려면 매개변수 타입이 반드시 `Object`여야 합니다. 그런데 다음처럼 매개변수 타입을 자기 클래스로 좁혀 쓰는 실수가 매우 흔합니다.

```java
class Point {
    int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }

    // 의도는 "오버라이딩"이지만 매개변수 타입이 Object가 아니라 Point이므로
    // 실제로는 Object.equals(Object)를 오버로딩한 것 — 컴파일 에러도 나지 않는다
    public boolean equals(Point other) {
        return this.x == other.x && this.y == other.y;
    }
}

public class EqualsPitfall {
    public static void main(String[] args) {
        Point p1 = new Point(1, 2);
        Point p2 = new Point(1, 2);

        System.out.println(p1.equals(p2));               // true (Point 오버로딩 버전 호출)

        java.util.List<Point> list = new java.util.ArrayList<>();
        list.add(p1);
        // List<E>#contains(Object)는 매개변수 타입이 Object이므로
        // 내부적으로 Point가 아니라 Object.equals(Object)를 호출한다
        System.out.println(list.contains(p2));            // false! 예상과 다름
    }
}
```

`p1.equals(p2)`를 직접 호출하면 개발자가 의도한 `Point` 전용 비교 로직이 동작해 `true`가 나오지만, `List.contains()`처럼 프레임워크 내부에서 `Object` 타입 매개변수로 `equals(Object)`를 호출하는 경로에서는 오버라이딩되지 않은 `Object`의 기본 `equals`(참조 동일성 비교)가 그대로 실행되어 `false`가 나옵니다. 컴파일러는 이걸 오류로 잡지 않습니다 — 문법적으로 완전히 유효한 오버로딩이기 때문입니다. 이 문제를 예방하는 유일하고 확실한 방법은 `@Override` 애너테이션을 붙이는 것입니다. 매개변수 타입을 `Point`로 잘못 쓰면 `@Override`가 붙은 순간 "메서드가 상위 타입의 메서드를 오버라이드하지 않는다"는 컴파일 오류가 즉시 발생해 실수를 원천 차단합니다.

### 바이트코드 레벨에서 본 차이: 정적 바인딩 vs 동적 바인딩

이 차이는 우연이 아니라 JVM이 오버로딩과 오버라이딩을 완전히 다른 시점에 처리하기 때문에 생깁니다. Java 언어 명세는 인스턴스 메서드 호출에 대해 다음과 같이 규정합니다.

> "The particular method used for an invocation `o.m(...)` is chosen based on the methods that are part of the class or interface that is the type of `o`. For instance methods, the class of the object referenced by the run-time value of `o` participates because a subclass may override a specific method already declared in a parent class so that this overriding method is invoked."

즉, **어떤 이름/시그니처의 메서드를 호출할지(오버로딩 해소)는 컴파일 타임에 선언 타입 기준으로 정적으로 결정**되고, 그렇게 정해진 메서드가 오버라이딩되어 있을 경우 **실제로 어느 클래스의 구현이 실행될지(오버라이딩 해소)는 런타임에 객체의 실제 타입 기준으로 동적으로 결정**됩니다. 이 런타임 결정을 수행하는 JVM 명령어가 `invokevirtual`입니다. `javap -c`로 `PolymorphismDemo`를 디스어셈블해 보면 `a.speak()` 호출 지점에 다음과 같은 바이트코드가 생성됩니다.

```
invokevirtual #7  // Method Animal.speak:()V
```

여기서 중요한 점은, 오퍼랜드에 박힌 메서드 디스크립터(`Animal.speak:()V`)는 **컴파일 타임에 선언 타입(Animal) 기준으로 이미 고정**된다는 것입니다. 하지만 `invokevirtual`은 이 심볼릭 레퍼런스를 실행 시점에 다시 "이 객체의 실제 클래스가 가진 메서드 테이블에서 해당 시그니처를 오버라이드한 가장 하위의 구현"으로 재해석합니다. 반면 `Printer.print(ref)`처럼 오버로딩이 얽힌 호출은, 컴파일러가 인수 `ref`의 **선언 타입만 보고** `print(Animal)`과 `print(Dog)` 중 어느 시그니처를 호출할지부터 컴파일 타임에 확정해버리므로, `invokevirtual`이 런타임에 아무리 정확하게 동적 디스패치를 수행해도 애초에 잘못된 시그니처가 오퍼랜드에 박혀 있으면 소용이 없습니다. "다형성이 안 먹힌다"는 불만의 상당수는 사실 다형성(오버라이딩) 자체의 결함이 아니라, 오버로딩 해소가 정적 바인딩이라는 사실을 놓친 데서 옵니다.

이 문제를 근본적으로 우회하는 정석적인 기법이 **더블 디스패치(Double Dispatch)**입니다. Visitor 패턴이 대표적인 예로, `accept(Visitor v)`라는 오버라이딩 가능한 메서드 안에서 `v.visit(this)`를 호출하게 하면, 첫 번째 디스패치(`accept`)는 원소의 실제 타입으로, 두 번째 디스패치(`visit`)는 `this`의 실제 타입(컴파일 타임이 아니라 그 메서드 내부에서 이미 구체화된 타입)으로 두 번 오버라이딩을 거치게 되어, 오버로딩의 정적 바인딩 한계를 오버라이딩의 동적 바인딩으로 우회할 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| 인스턴스 메서드 호출 시, 어떤 메서드가 실행될지는 호출 표현식 `o.m(...)`에서 `o`의 런타임 클래스가 관여하며, 이는 하위 클래스가 상위 클래스의 메서드를 오버라이드했을 수 있기 때문이다 | verified | Java Language Specification SE21, §15.5, "Method invocation" 문단 원문 대조 (docs.oracle.com/javase/specs/jls/se21/html/jls-15.html) |
| JVM은 `o.m(...)` 형태의 인스턴스 메서드 호출을 컴파일할 때 `invokevirtual` 명령어를 사용하며, 이 명령어는 실행 시점에 객체의 실제(runtime) 클래스를 기준으로 호출할 구현을 결정한다(가상 메서드 디스패치) | verified | Java Virtual Machine Specification SE21, §6.5 invokevirtual 명령어 정의 및 다수 2차 자료(Guardsquare "JVM Method Invocations", InfoWorld) 교차 확인 (docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html#jvms-6.5.invokevirtual) |
| "변수의 선언된 타입이 아니라 실제로 가리키는 객체의 타입에 따라 호출될 메서드가 결정된다"는 것이 Java의 다형성(virtual method invocation)이다 | verified | Oracle Java Tutorials, "Polymorphism" 페이지 원문 인용 대조 (docs.oracle.com/javase/tutorial/java/IandI/polymorphism.html) |
| 서브클래스에서 상위 클래스 메서드를 오버로딩한 경우, 그 오버로딩된 메서드는 상위 클래스의 인스턴스 메서드를 오버라이드하거나 숨기지 않으며, 서브클래스에 고유한 새 메서드일 뿐이다 | verified | Oracle Java Tutorials, "Overriding and Hiding Methods" 페이지 원문 인용 대조 (docs.oracle.com/javase/tutorial/java/IandI/override.html) |
| 오버라이딩 메서드의 접근 제한자는 오버라이드되는 메서드보다 더 좁을 수 없다(예: protected를 public으로 넓히는 것은 가능하지만 반대는 불가) | verified | Oracle Java Tutorials, "Overriding and Hiding Methods" 페이지 원문 대조 (docs.oracle.com/javase/tutorial/java/IandI/override.html) |

## 작성자의 견해

> 이 섹션은 사실을 나열하는 게 아니라 필자가 실제로 겪고 판단한 사견을 담습니다.

4대 특성 중 캡슐화·상속·추상화는 코드 리뷰에서 "이게 잘 지켜졌는지"를 눈으로 비교적 쉽게 확인할 수 있습니다. 필드가 `public`인지, 인터페이스 없이 구체 클래스에 직접 의존하는지는 코드를 한 번 훑어보면 드러납니다. 하지만 다형성은 다릅니다 — 오버로딩과 오버라이딩이 똑같이 `.`(점) 문법으로 호출되고, 컴파일러가 오버로딩 실수를 문법 오류로 잡아주지 않기 때문에, 코드 리뷰어가 "이 메서드가 정말 오버라이드되고 있는가"를 의식적으로 확인하지 않으면 그냥 지나가 버립니다. 필자는 신입 개발자에게 다형성을 가르칠 때 "Animal이 짖는다" 예시보다 이 글의 `equals()` 함정을 먼저 보여주는 편을 선호합니다. 왜냐하면 "다형성을 이해했다"는 느낌과 "다형성이 실제로 언제 작동하지 않는지 안다"는 것은 완전히 다른 수준의 이해이기 때문입니다. 개인적으로는 IDE의 "오버라이드 메서드 생성" 기능(예: IntelliJ의 Generate → equals() and hashCode())을 직접 타이핑 대신 습관적으로 쓰도록 권장하는데, 이렇게 하면 매개변수 타입을 `Object`로 정확히 맞춰주기 때문에 이번 글에서 다룬 함정 자체가 애초에 발생하지 않습니다. 즉, 다형성 관련 버그의 상당수는 "개념을 몰라서"가 아니라 "타이핑 습관"에서 나온다는 게 필자의 해석입니다.

## 한계와 반론

이 글에서 강조한 정적 바인딩/동적 바인딩 구분은 Java의 인스턴스 메서드에는 정확히 들어맞지만, Java 8 이후 도입된 인터페이스의 `default` 메서드나 `static` 메서드에는 그대로 적용하기 어려운 예외적 규칙(가장 구체적인 인터페이스의 default 메서드 우선, 클래스 메서드가 항상 default 메서드보다 우선 등)이 추가로 존재하며, 이 글에서는 지면상 다루지 않았습니다. 또한 "오버로딩은 항상 정적 바인딩"이라는 설명은 원론적으로는 맞지만, 제네릭과 함께 쓰이면 타입 소거(type erasure) 때문에 오버로딩 자체가 컴파일 에러로 막히는 경우도 있어 실제로는 더 복잡한 규칙이 관여합니다. 더블 디스패치(Visitor 패턴)를 "우회 기법"으로 소개했지만, 이 패턴 자체도 새로운 방문자 타입이 추가될 때마다 모든 `accept`/`visit` 구현을 수정해야 하는 OCP 위반 소지가 있다는 반론이 있으며, 무조건적인 해법은 아닙니다. 마지막으로 이 글이 예로 든 `equals()` 함정은 Java 고유의 문법적 특성(오버로딩과 오버라이딩의 시그니처 구분 규칙)에서 비롯된 것이라, Python이나 JavaScript처럼 메서드 오버로딩 자체를 언어 차원에서 지원하지 않는 언어에는 이런 형태로 재현되지 않는다는 점도 감안해야 합니다.

## 참고문헌

1. Oracle, "Java Language Specification, Java SE 21 Edition — Chapter 15. Expressions, §15.5 Expressions and Run-Time Checks", [https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html) (확인일: 2026-08-26)
2. Oracle, "The Java Virtual Machine Specification, Java SE 21 Edition — §6.5 invokevirtual", [https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html#jvms-6.5.invokevirtual](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html#jvms-6.5.invokevirtual) (확인일: 2026-08-26)
3. Oracle, "The Java Tutorials — Interfaces and Inheritance: Polymorphism", [https://docs.oracle.com/javase/tutorial/java/IandI/polymorphism.html](https://docs.oracle.com/javase/tutorial/java/IandI/polymorphism.html) (확인일: 2026-08-26)
4. Oracle, "The Java Tutorials — Interfaces and Inheritance: Overriding and Hiding Methods", [https://docs.oracle.com/javase/tutorial/java/IandI/override.html](https://docs.oracle.com/javase/tutorial/java/IandI/override.html) (확인일: 2026-08-26)

## 종합적 의견

> 이 섹션에는 앞서 다룬 4대 특성 전체를 관통하는 필자 나름의 해석을 담습니다.

캡슐화·상속·추상화·다형성을 따로따로 익히면 "왜 4개나 필요한가"라는 의문이 남지만, 실제로는 하나의 흐름으로 이어져 있습니다. 캡슐화로 각 객체가 자기 상태를 스스로 책임지게 만들고, 추상화로 "무엇을 하는가"만 노출해 구현 교체를 자유롭게 하며, 상속과 인터페이스로 여러 구현이 하나의 계약을 공유하게 만든 뒤, 다형성이 그 계약을 실제 런타임에서 "선언 타입은 신경 쓰지 않고 실제 객체가 알아서 자기 버전으로 응답하게" 만드는 마지막 연결 고리 역할을 합니다. 이 글에서 특히 강조하고 싶었던 것은, 이 마지막 연결 고리(다형성)가 Java에서는 "오버라이딩"이라는 아주 구체적이고 좁은 메커니즘으로 구현되어 있고, 이름이 비슷한 "오버로딩"은 전혀 다른 시점(컴파일 타임)에 전혀 다른 기준(선언 타입)으로 동작한다는 사실입니다. 이 구분을 이론으로만 알고 있는 것과, `equals()` 함정처럼 실제 코드에서 어떻게 배신당하는지 한 번이라도 디버깅해본 것은 실무 역량 차이로 이어집니다. 개인적으로는 OOP 4대 특성을 가르치는 순서를 캡슐화→추상화→상속→다형성으로 바꾸고, 다형성 파트에서는 반드시 오버로딩과의 비교, 그리고 `equals()`/`hashCode()` 함정을 함께 다루는 것이 더 실전적인 학습 순서라고 생각합니다. 정의를 암기하는 것보다, 컴파일러가 어디까지 실수를 잡아주고 어디서부터는 개발자의 몫인지를 아는 것이 훨씬 오래 남는 지식입니다.

## 꼬리질문

1. **더블 디스패치(Visitor 패턴) 외에, 오버로딩의 정적 바인딩 한계를 피하면서도 새로운 타입 추가 시 기존 코드 수정을 최소화할 수 있는 다른 설계 방법(예: 패턴 매칭 기반 `switch`, Java 21의 sealed 인터페이스와 레코드 패턴)은 실무에서 얼마나 대안이 될 수 있는가?**
   - 추천 참고 URL: https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html
2. **인터페이스의 `default` 메서드가 여러 상위 인터페이스에서 충돌할 때 JVM/컴파일러가 이를 해결하는 우선순위 규칙은 클래스 상속의 오버라이딩 해소 규칙과 어떻게 다른가?**
   - 추천 참고 URL: https://docs.oracle.com/javase/tutorial/java/IandI/override.html

## 백링크

- [SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시](https://beji-tech.blogspot.com/2026/08/solid-java-5.html)
- [Java equals()/hashCode() 계약 — 왜 함께 오버라이드해야 하는가](https://beji-tech.blogspot.com/2026/08/java-equalshashcode.html)