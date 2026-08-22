---
id: '7904583536125221669'
publishedAt: '2026-08-14T11:27:17.829-07:00'
slug: gof-4-builder-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T11:27:17.829-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-4-builder-pattern-java.html
---

# [GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시

## 요약

빌더 패턴(Builder Pattern)은 복잡한 객체의 생성 과정을 단계별 메서드 호출로 분리해, 동일한 조립 절차로도 다양한 조합의 최종 객체를 만들 수 있게 하는 생성 패턴입니다. 특히 생성자에 넘겨야 할 인자가 많고 그중 다수가 선택적(optional)일 때, 가독성 높은 메서드 체이닝 방식으로 필요한 필드만 골라 안전하게 불변 객체를 만들 수 있습니다. 이 글에서는 생성자 인자 폭발 문제를 빌더가 어떻게 해결하는지, 그리고 Lombok `@Builder`를 실무에서 쓸 때 주의할 점까지 다룹니다.

## 본문

### 1. 배경 및 문제점

피자 주문 객체를 만든다고 가정해 봅니다. 도우·소스는 필수, 치즈·페퍼로니·토핑은 선택 사항입니다. 생성자 하나로 이를 다 처리하려 하면 `new Pizza(dough, sauce, cheese, pepperoni, toppings)`처럼 인자가 늘어나고, 선택 항목의 조합마다 오버로딩된 생성자를 계속 추가하는 "텔레스코핑 생성자(Telescoping Constructor)" 안티패턴에 빠지기 쉽습니다. 인자가 5개, 10개로 늘어나면 호출부에서 `new Pizza("씬도우", "토마토소스", true, false, null)`처럼 각 위치가 무엇을 의미하는지 코드만 보고는 알기 어려워지고, 인자 순서를 실수로 바꿔 넣어도 컴파일러가 잡아주지 못하는 버그가 발생합니다.

### 2. 패턴 정의 및 동작 메커니즘

빌더 패턴은 객체 생성을 전담하는 별도의 Builder 클래스를 두고, 이 클래스가 필드 하나씩을 설정하는 메서드(예: `addCheese()`, `addTopping()`)를 제공합니다. 각 설정 메서드는 자기 자신(`this`)을 반환해 메서드 체이닝이 가능하도록 하고, 마지막에 `build()` 메서드를 호출하면 그동안 설정된 값을 바탕으로 최종 불변 객체를 생성합니다. 원본 클래스의 생성자는 `private`으로 감춰서, 오직 Builder를 거쳐서만 인스턴스를 만들 수 있도록 강제하는 것이 일반적입니다.

### 3. 실제 서비스 적용 예시

배달 애플리케이션의 메뉴 커스텀 주문 화면이 대표적인 예시입니다. "떡볶이 선택 → 맵기 조절 → 치즈 토핑 추가 → 사리 추가"처럼 사용자가 순서대로 옵션을 골라 나가는 흐름을 `Order.builder().menu("떡볶이").spicy("매운맛").addTopping("치즈").build()`와 같은 체이닝 코드로 그대로 옮길 수 있습니다. 서브웨이나 수제버거 매장에서 "빵 선택 → 패티 추가 → 야채 빼기 → 소스 추가" 순서로 조립하는 것과 동일한 구조이며, 순서가 바뀌어도(치즈를 먼저 넣든 나중에 넣든) 최종 결과에는 영향이 없다는 점도 실제 커스텀 주문과 닮아 있습니다.

### 4. Java 실전 구현 코드

```java
import java.util.ArrayList;
import java.util.List;

// 불변(Immutable) 객체로 설계된 Pizza 클래스
class Pizza {
    private final String dough;        // 필수
    private final String sauce;        // 필수
    private final boolean cheese;      // 선택
    private final boolean pepperoni;   // 선택
    private final List<String> toppings; // 선택

    // private 생성자: 외부에서는 직접 생성 불가, 오직 Builder를 통해서만 생성 가능
    private Pizza(PizzaBuilder builder) {
        this.dough = builder.dough;
        this.sauce = builder.sauce;
        this.cheese = builder.cheese;
        this.pepperoni = builder.pepperoni;
        this.toppings = builder.toppings;
    }

    public void showPizza() {
        System.out.println("주문하신 피자 완성!");
        System.out.println(" - 도우: " + dough);
        System.out.println(" - 소스: " + sauce);
        System.out.println(" - 치즈 추가: " + (cheese ? "O" : "X"));
        System.out.println(" - 페퍼로니 추가: " + (pepperoni ? "O" : "X"));
        System.out.println(" - 추가 토핑: " + (toppings.isEmpty() ? "없음" : toppings));
    }

    // 정적 내부 빌더 클래스
    public static class PizzaBuilder {
        private final String dough;   // 필수 - 빌더 생성자로 받음
        private final String sauce;   // 필수 - 빌더 생성자로 받음

        private boolean cheese = false;
        private boolean pepperoni = false;
        private List<String> toppings = new ArrayList<>();

        public PizzaBuilder(String dough, String sauce) {
            this.dough = dough;
            this.sauce = sauce;
        }

        // 체이닝을 위해 this를 반환하는 메서드들
        public PizzaBuilder addCheese() { this.cheese = true; return this; }
        public PizzaBuilder addPepperoni() { this.pepperoni = true; return this; }
        public PizzaBuilder addTopping(String topping) { this.toppings.add(topping); return this; }

        public Pizza build() {
            if (dough == null || sauce == null) {
                throw new IllegalStateException("필수 재료가 누락되었습니다.");
            }
            return new Pizza(this);
        }
    }
}

public class BuilderDemo {
    public static void main(String[] args) {
        Pizza cheesePizza = new Pizza.PizzaBuilder("씬 도우", "토마토 소스")
                .addCheese()
                .build();

        Pizza premiumPizza = new Pizza.PizzaBuilder("치즈크러스트", "바베큐 소스")
                .addCheese()
                .addPepperoni()
                .addTopping("올리브")
                .addTopping("피망")
                .build();

        cheesePizza.showPizza();
        premiumPizza.showPizza();
    }
}
```

`PizzaBuilder("씬 도우", "토마토 소스")`처럼 필수 값은 빌더 생성자로 강제하고, 선택 값은 체이닝 메서드로만 노출해 실수로 필수 값을 누락할 여지를 없앴습니다.

### 5. 실무 주의점 및 트레이드오프

Lombok의 `@Builder`를 클래스 레벨에 붙이면 모든 필드를 인자로 받는 패키지 프라이빗(package-private) 생성자가 함께 생성되는데, 이를 통해 빌더를 우회한 직접 생성이 가능해질 수 있다는 점을 인지해야 합니다. 또한 필드에 기본값을 미리 지정해 두었다면 `@Builder.Default` 애노테이션을 명시하지 않는 한 빌더가 그 기본값을 무시하고 `null`이나 `0`으로 덮어써 버리는, 실무에서 자주 발생하는 함정이 있습니다. 필드가 2~3개뿐인 단순한 객체에 빌더를 적용하면 오히려 보일러플레이트 코드만 늘어나는 과잉 설계가 될 수 있습니다.

### 6. 실무 프레임워크 적용 사례

Lombok의 `@Builder` 애노테이션은 이 패턴을 어노테이션 프로세서로 자동 생성해 주는 가장 널리 쓰이는 도구입니다. Spring의 `UriComponentsBuilder`는 URL을 스킴·호스트·경로·쿼리 파라미터 단위로 체이닝하며 조립하는 데 이 패턴을 사용하고, Java 표준 라이브러리의 `StringBuilder`도 `append()`를 반복 호출해 문자열을 단계적으로 조립한다는 점에서 넓은 의미의 빌더 패턴 응용 사례로 볼 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 빌더 패턴은 복잡한 객체의 생성 과정을 표현과 분리해 단계적으로 조립할 수 있게 하는 생성 패턴이다 | verified | Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software* (1994) |
| CLAIM-002: 텔레스코핑 생성자 안티패턴은 선택적 인자 조합마다 오버로딩된 생성자를 추가하며 발생하는 문제로, 빌더 패턴이 이를 완화한다 | verified | Joshua Bloch, *Effective Java*, Item 2 (Consider a builder when faced with many constructor parameters) |
| CLAIM-003: Lombok `@Builder`는 필드에 기본값이 있어도 `@Builder.Default`를 명시하지 않으면 빌더 생성 시 그 기본값이 무시된다 | verified | Lombok 공식 문서, `@Builder.Default` 설명 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

빌더 패턴은 GoF 패턴 중에서도 실무에서 가장 자주, 그리고 가장 가볍게 쓰이는 패턴이라고 생각합니다. 다만 그만큼 남용도 흔합니다. 생성자 인자가 2~3개뿐이고 전부 필수 값인 단순한 DTO에까지 습관적으로 `@Builder`를 붙이는 경우를 종종 보는데, 이런 경우엔 오히려 일반 생성자가 더 읽기 쉽고 실수 여지도 적습니다. 개인적으로는 "선택적 인자가 3개 이상이거나, 호출부만 봐서는 인자 순서를 헷갈릴 수 있는 경우"를 빌더 적용의 실질적인 기준으로 삼는 편이 과잉 설계를 막는 데 도움이 된다고 봅니다.

## 한계와 반론

**한계점**: 빌더 클래스 자체가 별도의 보일러플레이트 코드이므로, 단순한 객체에 적용하면 코드량만 늘어나고 이해에 드는 인지 비용이 오히려 증가할 수 있습니다.

**반론**: Lombok의 `@Builder` 애노테이션 하나로 이 보일러플레이트 문제는 사실상 해소되었습니다. 어노테이션 프로세서가 컴파일 시점에 빌더 클래스를 자동 생성해 주므로, 개발자가 직접 빌더 코드를 손으로 작성해야 하는 부담 없이도 체이닝 방식의 가독성과 안전성을 얻을 수 있습니다. 다만 앞서 언급한 `@Builder.Default` 함정처럼 자동 생성 도구 특유의 미묘한 동작 방식은 별도로 숙지해야 합니다.

## 참고문헌

1. Lombok Project, "@Builder", [https://projectlombok.org/features/Builder](https://projectlombok.org/features/Builder) (확인일: 2026-08-17)
2. Spring Framework Javadoc, "UriComponentsBuilder", [https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/util/UriComponentsBuilder.html](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/util/UriComponentsBuilder.html) (확인일: 2026-08-17)
3. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

빌더 패턴은 "무엇을 필수로 강제하고 무엇을 선택으로 남길 것인가"를 API 설계 단계에서 명시적으로 표현하는 도구입니다. Lombok 같은 도구 덕분에 구현 비용은 거의 사라졌지만, 그렇다고 해서 모든 클래스에 기계적으로 적용할 이유는 되지 않습니다. 선택적 필드가 충분히 많고 조합의 가독성이 중요한 도메인 객체에 선별적으로 적용할 때, 빌더 패턴은 생성자 인자 순서 실수를 원천 차단하면서도 코드를 자연어에 가깝게 읽히도록 만드는 실질적인 이점을 제공합니다.

## 꼬리질문

1. **Lombok `@Builder`가 생성하는 패키지 프라이빗 전체 인자 생성자를 통해 빌더를 우회하는 것을 막으려면 어떤 추가 설정이 필요한가?**
   - 추천 참고 URL: [https://projectlombok.org/features/Builder](https://projectlombok.org/features/Builder)
2. **빌더 패턴과 팩토리 패턴을 함께 사용해 "제품군 선택 + 단계별 조립"을 모두 지원하는 설계는 어떻게 구성하는가?**
   - 추천 참고 URL: [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns)

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)