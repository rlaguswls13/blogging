---
id: '1254433254714617011'
publishedAt: '2026-08-14T11:29:01.000-07:00'
slug: gof-14-template-method-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 14. 템플릿 메서드 패턴 (Template Method Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:18:40.008-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-14-template-method-pattern-java.html
---

# [GoF 디자인 패턴] 14. 템플릿 메서드 패턴 (Template Method Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **행위 패턴 (Behavioral)**

## 요약

템플릿 메서드 패턴은 알고리즘의 전체 골격(순서)은 부모 클래스에 고정해 두고, 그 안의 세부 단계 일부만 자식 클래스가 오버라이드하도록 열어두는 행위 패턴입니다. "커피와 차를 끓이는 과정은 거의 같은데 우려내는 재료만 다르다"처럼, 여러 클래스가 공유하는 알고리즘 뼈대가 있고 그중 일부 단계만 달라질 때 코드 중복을 없앨 수 있습니다. 이 글에서는 템플릿 메서드 패턴의 동작 원리, `final` 키워드를 활용한 골격 고정 방법, 완전한 Java 예제, 그리고 Spring의 `JdbcTemplate`이나 JUnit 테스트 라이프사이클처럼 이 패턴이 널리 쓰이는 실무 사례를 다룹니다.

## 본문

### 1. 배경 및 문제점

커피를 만드는 과정과 차를 만드는 과정을 각각 별도 클래스로 구현한다고 해보겠습니다. 두 과정 모두 "물 끓이기 → 우려내기 → 컵에 따르기 → 첨가물 넣기"라는 거의 동일한 순서를 따르지만, "우려내기"(커피 원두 vs 찻잎)와 "첨가물"(설탕/우유 vs 레몬)만 다릅니다. 이걸 각 클래스에서 처음부터 따로 작성하면, 물을 끓이고 컵에 따르는 로직이 두 클래스에 그대로 중복됩니다. 새로운 음료(코코아 등)가 추가될 때마다 이 중복된 골격 코드를 또 복사해야 하는 문제가 생깁니다.

### 2. 패턴 정의 및 동작 메커니즘

템플릿 메서드 패턴은 알고리즘의 전체 순서를 부모 클래스의 `final` 메서드(템플릿 메서드) 안에 한 번만 정의하고, 그 순서 안에서 호출되는 개별 단계들은 `abstract` 메서드나 기본 구현이 있는 `hook` 메서드로 선언합니다. 자식 클래스는 템플릿 메서드 자체는 건드릴 수 없고(그래서 `final`), 오직 `abstract`로 열어둔 단계만 자신에게 맞게 오버라이드합니다. 즉 "무엇을 할지의 순서"는 부모가 통제하고, "각 단계를 어떻게 할지"만 자식이 결정하는 제어의 역전(Inversion of Control)이 일어납니다.

**실제 서비스 적용 예시: 데이터 처리 파이프라인** — "파일 읽기 → 데이터 검증 → 변환 → 저장"이라는 배치 처리 골격은 모든 데이터 소스(CSV, JSON, XML)에서 동일하지만, "파일 읽기"와 "검증" 단계의 구체적인 구현만 소스 형식마다 다릅니다. 템플릿 메서드로 골격을 고정하면 새로운 형식이 추가되어도 파이프라인 순서 자체는 실수로 바뀔 수 없습니다.

**비유: 요리 레시피 카드** — 레시피의 큰 순서("재료 손질 → 조리 → 플레이팅")는 정해져 있고 요리사가 마음대로 순서를 바꿀 수 없지만, "조리" 단계에서 굽는지 끓이는지는 요리(자식 클래스)마다 다릅니다.

### 3. Java 실전 구현 코드

아래는 커피와 차를 만드는 과정을 템플릿 메서드 패턴으로 구현한 예제입니다. `prepareBeverage()`가 템플릿 메서드이며 `final`로 순서를 고정합니다.

```java
package com.gof.templatemethod;

// 1. 추상 클래스 (Abstract Class) - 알고리즘의 골격을 정의
abstract class CaffeineBeverage {

    // 2. 템플릿 메서드 - final로 선언하여 자식 클래스가 순서를 바꿀 수 없게 함
    public final void prepareBeverage() {
        boilWater();
        brew();          // 추상 메서드 - 자식이 반드시 구현
        pourInCup();
        if (customerWantsCondiments()) { // 훅(Hook) 메서드 - 선택적으로 오버라이드
            addCondiments();
        }
    }

    private void boilWater() {
        System.out.println("💧 물을 끓입니다.");
    }

    private void pourInCup() {
        System.out.println("☕ 컵에 따릅니다.");
    }

    // 3. 추상 메서드 (Abstract Method) - 자식 클래스가 반드시 구현해야 함
    protected abstract void brew();
    protected abstract void addCondiments();

    // 4. 훅 메서드 (Hook Method) - 기본 구현이 있어 자식이 선택적으로 오버라이드 가능
    protected boolean customerWantsCondiments() {
        return true; // 기본값: 첨가물을 넣는다
    }
}

// 5. 구체 클래스 - Coffee
class Coffee extends CaffeineBeverage {
    @Override
    protected void brew() {
        System.out.println("☕ 필터로 커피 원두를 우려냅니다.");
    }

    @Override
    protected void addCondiments() {
        System.out.println("🥛 설탕과 우유를 추가합니다.");
    }
}

// 6. 구체 클래스 - Tea (훅 메서드를 오버라이드해 첨가물 단계를 건너뜀)
class Tea extends CaffeineBeverage {
    @Override
    protected void brew() {
        System.out.println("🍵 찻잎을 우려냅니다.");
    }

    @Override
    protected void addCondiments() {
        System.out.println("🍋 레몬을 추가합니다.");
    }

    @Override
    protected boolean customerWantsCondiments() {
        return false; // 이번엔 첨가물 없이 마시고 싶다는 의사를 훅으로 표현
    }
}

public class TemplateMethodMain {
    public static void main(String[] args) {
        System.out.println("=== 커피 준비 ===");
        CaffeineBeverage coffee = new Coffee();
        coffee.prepareBeverage();

        System.out.println("\n=== 차 준비 (첨가물 없이) ===");
        CaffeineBeverage tea = new Tea();
        tea.prepareBeverage();
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 커피 준비 ===
💧 물을 끓입니다.
☕ 필터로 커피 원두를 우려냅니다.
☕ 컵에 따릅니다.
🥛 설탕과 우유를 추가합니다.

=== 차 준비 (첨가물 없이) ===
💧 물을 끓입니다.
🍵 찻잎을 우려냅니다.
☕ 컵에 따릅니다.
*/
```

### 4. 실무 주의점 및 트레이드오프

템플릿 메서드 패턴은 상속(Inheritance)을 기반으로 하기 때문에, 자바처럼 단일 상속만 지원하는 언어에서는 이미 다른 부모 클래스를 상속하고 있는 경우 적용하기 어렵습니다. 이런 경우 전략 패턴처럼 상속 대신 위임(합성)으로 각 단계를 주입받는 방식을 대안으로 고려할 수 있습니다. 또한 자식 클래스가 늘어날수록 부모의 템플릿 메서드가 정의하는 "고정된 순서"를 이해하지 못한 채 개별 단계만 보고 오버라이드하면 전체 흐름을 잘못 이해할 위험도 있습니다.

### 5. 실무 프레임워크 적용 사례

Spring의 `JdbcTemplate`, `RestTemplate`, `TransactionTemplate` 같은 `*Template` 클래스들이 템플릿 메서드 패턴의 대표적인 실무 사례입니다 — 커넥션을 열고 닫거나 예외를 처리하는 반복적인 골격은 프레임워크가 고정해 두고, 개발자는 실제 쿼리나 요청 로직만 콜백으로 채워 넣습니다. `java.util.AbstractList`도 `get()`, `size()`만 구현하면 `iterator()`나 `indexOf()` 같은 나머지 메서드들이 템플릿 메서드로 이미 완성되어 있는 구조입니다. JUnit의 `@BeforeEach`/테스트 메서드/`@AfterEach` 실행 순서 역시 프레임워크가 고정한 템플릿을 각 테스트 클래스가 채워 넣는 방식과 개념적으로 같습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 템플릿 메서드 패턴은 알고리즘의 골격을 부모 클래스에 고정하고 일부 단계만 자식이 오버라이드하게 하는 행위 패턴이다 | verified | Gamma et al., Design Patterns (1994) Template Method 챕터 |
| CLAIM-002: 템플릿 메서드는 자식이 순서를 바꾸지 못하도록 보통 final로 선언하며, 선택적 단계는 기본 구현이 있는 훅(Hook) 메서드로 제공한다 | verified | Gamma et al., Design Patterns Template Method 챕터의 Hook Method 개념 |
| CLAIM-003: Spring의 JdbcTemplate은 커넥션 처리 등 반복 골격을 캡슐화하고 사용자 로직만 콜백으로 받는 템플릿 메서드 패턴 기반 클래스다 | verified | Spring Framework 공식 문서(JdbcTemplate 데이터 접근 챕터) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

템플릿 메서드 패턴은 GoF 패턴 중에서도 가장 자주 무의식적으로 쓰이는 패턴이라고 생각합니다. Spring의 `*Template` 계열 클래스를 매일 쓰면서도 "이게 템플릿 메서드 패턴이다"라고 인지하지 못하는 개발자가 많습니다. 다만 직접 새로운 추상 클래스 계층을 설계할 때는 신중해야 한다고 봅니다 — 상속은 결합도가 강해서, 나중에 골격 순서 자체를 바꿔야 하는 요구사항이 생기면 모든 자식 클래스에 영향을 줄 수 있습니다. 저는 팀 내에서 재사용될 고정된 프로세스(배치 파이프라인, 검증 절차)에는 템플릿 메서드를, 자주 바뀔 가능성이 있는 로직에는 전략 패턴 기반의 합성을 우선 고려하는 편입니다.

## 한계와 반론

템플릿 메서드 패턴은 상속을 전제로 하므로 자바의 단일 상속 제약을 그대로 물려받습니다. 자식 클래스가 다른 목적의 부모 클래스를 이미 상속하고 있다면 적용할 수 없다는 반론이 있고, 이 경우 전략 패턴처럼 합성 기반으로 각 단계를 함수형 인터페이스로 주입받는 방식이 더 유연하다는 대안이 자주 제시됩니다. 다만 전략 패턴은 매번 전략 객체를 조립해서 주입해야 하므로, 골격이 거의 고정되어 있고 변경이 드문 경우라면 템플릿 메서드 쪽이 오히려 더 단순합니다.

## 참고문헌

1. Spring, "Data Access with JDBC", [https://docs.spring.io/spring-framework/reference/data-access/jdbc.html](https://docs.spring.io/spring-framework/reference/data-access/jdbc.html) (확인일: 2026-08-17)
2. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
3. Refactoring.Guru, "Template Method Design Pattern", [https://refactoring.guru/design-patterns/template-method](https://refactoring.guru/design-patterns/template-method) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

템플릿 메서드 패턴의 핵심 가치는 "반복되는 순서"를 한 곳에 고정해서 실수로 순서가 어긋나는 것을 원천 차단하는 데 있습니다. 전략 패턴과 자주 비교되지만, 전략 패턴이 알고리즘 전체를 통째로 갈아끼우는 것이라면 템플릿 메서드는 큰 틀은 유지한 채 일부 단계만 바꾼다는 점에서 목적이 다릅니다. Spring의 `*Template` 계열 클래스들이 보여주듯, 반복적인 준비/정리 로직과 사용자 정의 로직을 분리해야 하는 상황이라면 여전히 매우 실용적인 선택지입니다.

## 꼬리질문

1. **템플릿 메서드 패턴과 전략 패턴을 함께 사용해서, 골격은 고정하되 특정 단계의 알고리즘만 런타임에 교체하는 하이브리드 설계는 어떻게 구현하는가?**
   - 추천 참고 URL: https://refactoring.guru/design-patterns/template-method
2. **Spring의 JdbcTemplate이 내부적으로 커넥션 획득/해제와 예외 변환을 어떤 콜백 인터페이스(PreparedStatementCallback 등)로 위임하는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/data-access/jdbc.html

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)