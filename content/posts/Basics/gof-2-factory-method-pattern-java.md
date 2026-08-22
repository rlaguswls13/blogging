---
id: '190544593785401394'
publishedAt: '2026-08-14T11:27:14.811-07:00'
slug: gof-2-factory-method-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
- GoF_Series
title: '[GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T11:27:14.811-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-2-factory-method-pattern-java.html
---

# [GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시

## 요약

팩토리 메서드 패턴(Factory Method Pattern)은 객체를 생성하는 코드를 별도의 메서드로 분리하고, 실제로 어떤 구체 클래스를 생성할지 결정하는 책임을 서브클래스에게 위임하는 생성 패턴입니다. 클라이언트 코드가 `new ConcreteProduct()`를 직접 호출하는 대신 팩토리 메서드를 호출하게 만들면, 새로운 제품 타입이 추가되어도 기존 클라이언트 코드를 건드리지 않고 확장할 수 있습니다. 이 글에서는 결제 수단이 늘어날 때마다 코드를 고쳐야 하는 문제를 팩토리 메서드로 어떻게 해결하는지, 그리고 실무 프레임워크에서의 활용 사례를 다룹니다.

## 본문

### 1. 배경 및 문제점

여러 결제 수단(카드, 카카오페이, 토스페이 등)을 지원하는 결제 시스템을 만든다고 가정해 봅니다. 클라이언트 코드에서 `if (type.equals("kakao")) { new KakaoPayProcessor(); } else if (...) { ... }`처럼 조건문으로 직접 객체를 생성하면, 새로운 결제 수단이 추가될 때마다 이 조건문을 찾아서 고쳐야 합니다. 이는 개방-폐쇄 원칙(Open-Closed Principle) — "확장에는 열려 있고 변경에는 닫혀 있어야 한다" — 을 정면으로 위배합니다. 결제 로직을 사용하는 클라이언트 코드 곳곳에 이런 분기문이 흩어져 있다면, 결제 수단 하나를 추가하기 위해 여러 파일을 동시에 수정해야 하는 상황에 빠집니다.

### 2. 패턴 정의 및 동작 메커니즘

팩토리 메서드 패턴은 객체 생성을 담당하는 추상 메서드(팩토리 메서드)를 상위 클래스(Creator)에 선언하고, 실제 생성 로직은 하위 클래스(Concrete Creator)가 오버라이드해서 구현하도록 합니다. 상위 클래스는 "어떤 제품이 만들어질지"는 몰라도 "제품이 만들어진 뒤 어떻게 쓰일지"에 대한 공통 로직(템플릿)은 그대로 소유할 수 있습니다. 새로운 제품 종류를 추가하고 싶으면, 기존 클래스를 수정하는 대신 새로운 Concrete Creator/Concrete Product 클래스 쌍을 추가하기만 하면 됩니다.

### 3. 실제 서비스 적용 예시

배달 애플리케이션의 결제 화면을 떠올려 보면, 사용자가 카카오페이·토스페이·신용카드 중 하나를 선택했을 때 각 수단에 맞는 결제 프로세서 객체를 생성해야 합니다. 팩토리 메서드로 설계하면 "결제창을 열고, 프로세서를 통해 승인을 요청하고, 결과를 화면에 보여준다"는 공통 흐름은 상위 `PaymentFactory` 클래스가 담당하고, "어떤 프로세서 객체를 만들 것인가"만 각 하위 팩토리 클래스가 결정합니다. 새로운 간편결제 수단이 생기면 새 하위 팩토리 클래스 하나만 추가하면 됩니다.

### 4. Java 실전 구현 코드

```java
// 1. 제품(Product) 인터페이스
interface PaymentProcessor {
    void processPayment(int amount);
}

// 2. 구체적인 제품(Concrete Product)들
class KakaoPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("[카카오페이] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

class TossPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("[토스페이] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

class CardPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("[신용카드] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

// 3. 생성자(Creator) 추상 클래스 - 팩토리 메서드를 선언
abstract class PaymentFactory {
    // 팩토리 메서드: 서브클래스에서 실제 구현을 결정
    public abstract PaymentProcessor createPaymentProcessor();

    // 공통 로직(템플릿): 어떤 제품이든 동일한 절차로 사용됨
    public void checkout(int amount) {
        PaymentProcessor processor = createPaymentProcessor();
        System.out.println("결제 준비 중... 프로세서 할당 완료");
        processor.processPayment(amount);
        System.out.println("결제 완료 처리 후 종료되었습니다.\n");
    }
}

// 4. 구체적인 팩토리(Concrete Creator)들
class KakaoPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() { return new KakaoPayProcessor(); }
}

class TossPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() { return new TossPayProcessor(); }
}

class CardPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() { return new CardPayProcessor(); }
}

public class FactoryMethodDemo {
    public static void main(String[] args) {
        PaymentFactory kakaoFactory = new KakaoPayFactory();
        kakaoFactory.checkout(15000);

        PaymentFactory tossFactory = new TossPayFactory();
        tossFactory.checkout(20000);

        PaymentFactory cardFactory = new CardPayFactory();
        cardFactory.checkout(35000);
    }
}

/*
▶ 실행 결과 (Expected Output):
결제 준비 중... 프로세서 할당 완료
[카카오페이] 15000원 결제가 정상적으로 처리되었습니다.
결제 완료 처리 후 종료되었습니다.

결제 준비 중... 프로세서 할당 완료
[토스페이] 20000원 결제가 정상적으로 처리되었습니다.
결제 완료 처리 후 종료되었습니다.

결제 준비 중... 프로세서 할당 완료
[신용카드] 35000원 결제가 정상적으로 처리되었습니다.
결제 완료 처리 후 종료되었습니다.
*/
```

새 간편결제 수단(예: 네이버페이)을 추가하려면 `NaverPayProcessor`와 `NaverPayFactory` 두 클래스만 새로 작성하면 되고, `PaymentFactory.checkout()`이나 기존 팩토리 클래스는 전혀 수정할 필요가 없습니다.

### 5. 실무 주의점 및 트레이드오프

제품 종류가 늘어날 때마다 Concrete Product와 Concrete Creator를 항상 쌍으로 추가해야 하므로, 관리해야 할 클래스 수가 선형적으로 증가하는 "클래스 폭발(Class Explosion)" 문제가 있습니다. 제품 종류가 2~3개 수준으로 적고 앞으로도 크게 늘어날 가능성이 낮다면, 단순한 `if-else`나 `switch` 분기가 오히려 코드를 읽기 쉽게 만드는 경우도 있어 무조건 패턴을 적용하는 것이 능사는 아닙니다.

### 6. 실무 프레임워크 적용 사례

Java 표준 라이브러리의 `Calendar.getInstance()`는 팩토리 메서드의 대표적인 예시로, 호출하는 시스템의 로케일과 타임존에 따라 내부적으로 다른 구체 클래스(`GregorianCalendar` 등)의 인스턴스를 반환합니다. Spring Framework의 `FactoryBean` 인터페이스도 이 패턴을 응용해, 빈 컨테이너가 복잡한 초기화 로직을 가진 객체를 생성할 때 `getObject()` 메서드에 그 생성 책임을 위임합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 팩토리 메서드 패턴은 객체 생성을 서브클래스에 위임해 개방-폐쇄 원칙을 지키도록 돕는 생성 패턴이다 | verified | Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software* (1994) |
| CLAIM-002: `Calendar.getInstance()`는 로케일/타임존에 따라 다른 구체 클래스 인스턴스를 반환하는 팩토리 메서드 사례이다 | verified | Oracle Java SE Javadoc, `java.util.Calendar#getInstance()` |
| CLAIM-003: Spring의 `FactoryBean` 인터페이스는 `getObject()`를 통해 빈 생성 책임을 위임하는 구조를 제공한다 | verified | Spring Framework Reference Documentation, FactoryBean |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

팩토리 메서드 패턴은 "언젠가 제품 종류가 늘어날 것"이 확실할 때 가장 빛을 발한다고 생각합니다. 반대로 제품 종류가 처음부터 정해져 있고 거의 바뀌지 않는 도메인이라면, 클래스 계층 구조를 미리 만들어두는 비용이 오히려 과한 설계(Over-engineering)로 느껴질 수 있습니다. 실무에서는 이 패턴을 순수하게 클래스 상속으로 구현하기보다, Java의 람다나 `Map<String, Supplier<PaymentProcessor>>` 같은 함수형 인터페이스 기반 레지스트리로 훨씬 가볍게 구현하는 경우를 더 자주 봅니다. 다만 팩토리 메서드가 제공하는 "생성 로직과 사용 로직의 분리"라는 핵심 아이디어 자체는 구현 방식이 무엇이든 여전히 유효한 설계 원칙입니다.

## 한계와 반론

**한계점**: 제품군이 커질수록 병렬로 늘어나는 클래스 계층 구조가 코드베이스를 복잡하게 만들고, 새로운 개발자가 전체 구조를 파악하는 데 시간이 걸립니다.

**반론**: Java 8 이후의 함수형 인터페이스를 활용하면 별도의 Concrete Creator 클래스 없이도 `Map<String, Supplier<PaymentProcessor>>` 형태의 레지스트리로 동일한 유연성을 훨씬 적은 클래스 수로 구현할 수 있습니다. 다만 이 경우 컴파일 타임 타입 체크의 이점이 줄어들고, 등록되지 않은 키로 조회했을 때의 런타임 예외 처리를 별도로 신경 써야 하는 트레이드오프가 있습니다.

## 참고문헌

1. Oracle Java SE Javadoc, "Calendar", [https://docs.oracle.com/javase/8/docs/api/java/util/Calendar.html](https://docs.oracle.com/javase/8/docs/api/java/util/Calendar.html) (확인일: 2026-08-17)
2. Spring Framework Reference Documentation, "Customizing Instantiation Logic with a FactoryBean", [https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html) (확인일: 2026-08-17)
3. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

팩토리 메서드 패턴의 본질은 "무엇을 만들지 결정하는 코드"와 "만들어진 것을 사용하는 코드"를 분리하는 데 있습니다. 전통적인 상속 기반 구현이든, 함수형 인터페이스를 활용한 경량 구현이든, 이 분리 원칙만 지켜진다면 새로운 제품 타입 추가가 기존 코드에 영향을 주지 않는 확장성을 얻을 수 있습니다. 제품 종류의 증가 가능성과 팀의 코드 복잡도 허용치를 함께 고려해 구현 방식을 선택하는 것이 실무적으로 합리적입니다.

## 꼬리질문

1. **Java의 `Supplier<T>` 함수형 인터페이스와 `Map` 레지스트리로 팩토리 메서드 패턴을 구현할 때, 상속 기반 구현 대비 어떤 성능/유지보수 트레이드오프가 발생하는가?**
   - 추천 참고 URL: [https://docs.oracle.com/javase/8/docs/api/java/util/function/Supplier.html](https://docs.oracle.com/javase/8/docs/api/java/util/function/Supplier.html)
2. **Spring의 `FactoryBean`과 일반 `@Bean` 메서드는 둘 다 객체 생성을 캡슐화하는데, 언제 `FactoryBean`을 선택해야 하는가?**
   - 추천 참고 URL: [https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html)

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)