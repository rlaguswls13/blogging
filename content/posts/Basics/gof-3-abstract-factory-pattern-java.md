---
id: '4830808000976056585'
publishedAt: '2026-08-14T11:27:16.305-07:00'
slug: gof-3-abstract-factory-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
- GoF_Series
title: '[GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T11:27:16.305-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-3-abstract-factory-pattern-java.html
---

# [GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시

## 요약

추상 팩토리 패턴(Abstract Factory Pattern)은 서로 관련이 있거나 함께 사용되어야 하는 객체들의 집합(제품군, Family)을 생성하기 위한 인터페이스를 제공하는 생성 패턴입니다. 클라이언트는 구체적인 클래스를 지정하지 않고도, 서로 호환되는 제품 세트를 일관되게 만들어낼 수 있습니다. 이 글에서는 라이트/다크 테마처럼 "세트로 맞아떨어져야 하는" UI 컴포넌트를 예시로, 추상 팩토리가 팩토리 메서드와 어떻게 다르고 왜 필요한지를 다룹니다.

## 본문

### 1. 배경 및 문제점

애플리케이션에 라이트 모드와 다크 모드 두 가지 테마를 지원한다고 가정해 봅니다. 버튼(Button)과 체크박스(Checkbox)를 각각 따로 생성하면, 실수로 라이트 모드 버튼과 다크 모드 체크박스가 한 화면에 섞여 렌더링되는 상황이 벌어질 수 있습니다. 제품 하나하나를 독립적으로 생성하는 방식으로는 "이 부품들이 서로 어울리는 세트인가"를 보장할 방법이 없습니다. 제품 종류가 늘어날수록(버튼, 체크박스, 라디오버튼, 슬라이더...) 이 호환성 관리 문제는 기하급수적으로 복잡해집니다.

### 2. 패턴 정의 및 동작 메커니즘

추상 팩토리 패턴은 관련된 여러 제품을 만드는 메서드들을 하나의 팩토리 인터페이스에 묶어서 선언합니다. 예를 들어 `UIFactory` 인터페이스에 `createButton()`과 `createCheckbox()`를 함께 선언해두고, `LightUIFactory`와 `DarkUIFactory`라는 구체 팩토리가 각각 이 메서드들을 구현하도록 합니다. 클라이언트는 팩토리 하나만 선택하면, 그 팩토리에서 나오는 모든 제품이 자동으로 같은 세트(테마)에 속한다는 것이 보장됩니다. 팩토리 메서드 패턴이 "제품 하나"를 만드는 데 집중한다면, 추상 팩토리는 "서로 관련된 제품 여러 개를 한 세트로" 만드는 데 집중한다는 점이 핵심적인 차이입니다.

### 3. 실제 서비스 적용 예시

크로스플랫폼 UI 프레임워크가 대표적인 사례입니다. 같은 애플리케이션을 Windows와 macOS에서 각각 그 운영체제 고유의 룩앤필로 보여줘야 할 때, `WindowsUIFactory`와 `MacUIFactory`를 두고 각 팩토리가 해당 운영체제 스타일의 버튼·체크박스 세트를 생성하도록 하면 클라이언트 코드는 운영체제 분기 없이 동일한 방식으로 UI를 구성할 수 있습니다. 가구 쇼핑몰의 "북유럽풍 세트"와 "모던풍 세트"처럼, 의자·테이블·조명이 스타일별로 세트를 이뤄야 하는 전자상거래 카탈로그 시스템에도 같은 원리가 적용됩니다.

### 4. Java 실전 구현 코드

```java
// 1. 추상 제품(Abstract Products)
interface Button { void paint(); }
interface Checkbox { void render(); }

// 2. 구체 제품 - 라이트 모드
class LightButton implements Button {
    public void paint() { System.out.println("[라이트 모드] 흰색 배경에 검은 글씨 버튼 생성"); }
}
class LightCheckbox implements Checkbox {
    public void render() { System.out.println("[라이트 모드] 밝은 체크박스 생성"); }
}

// 3. 구체 제품 - 다크 모드
class DarkButton implements Button {
    public void paint() { System.out.println("[다크 모드] 검은 배경에 흰 글씨 버튼 생성"); }
}
class DarkCheckbox implements Checkbox {
    public void render() { System.out.println("[다크 모드] 어두운 체크박스 생성"); }
}

// 4. 추상 팩토리 - 제품군(세트) 생성 인터페이스
interface UIFactory {
    Button createButton();
    Checkbox createCheckbox();
}

// 5. 구체 팩토리
class LightUIFactory implements UIFactory {
    public Button createButton() { return new LightButton(); }
    public Checkbox createCheckbox() { return new LightCheckbox(); }
}
class DarkUIFactory implements UIFactory {
    public Button createButton() { return new DarkButton(); }
    public Checkbox createCheckbox() { return new DarkCheckbox(); }
}

// 6. 클라이언트 애플리케이션
class Application {
    private final Button button;
    private final Checkbox checkbox;

    // 구체 팩토리를 주입받으므로, 구체 제품 클래스에 직접 의존하지 않음
    public Application(UIFactory factory) {
        this.button = factory.createButton();
        this.checkbox = factory.createCheckbox();
    }

    public void paintUI() {
        button.paint();
        checkbox.render();
    }
}

public class AbstractFactoryDemo {
    public static void main(String[] args) {
        System.out.println("=== 1. 라이트 테마 적용 ===");
        Application lightApp = new Application(new LightUIFactory());
        lightApp.paintUI();

        System.out.println("\n=== 2. 다크 테마 적용 ===");
        Application darkApp = new Application(new DarkUIFactory());
        darkApp.paintUI();
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 1. 라이트 테마 적용 ===
[라이트 모드] 흰색 배경에 검은 글씨 버튼 생성
[라이트 모드] 밝은 체크박스 생성

=== 2. 다크 테마 적용 ===
[다크 모드] 검은 배경에 흰 글씨 버튼 생성
[다크 모드] 어두운 체크박스 생성
*/
```

`Application` 클래스는 `LightButton`이나 `DarkButton` 같은 구체 클래스 이름을 코드 어디에도 직접 언급하지 않습니다. 어떤 테마가 적용될지는 오직 생성자에 어떤 `UIFactory` 구현체를 넘겨주느냐로만 결정됩니다.

### 5. 실무 주의점 및 트레이드오프

기존 제품군에 새로운 종류의 제품(예: 라디오버튼)을 추가하려면, `UIFactory` 인터페이스와 그것을 구현하는 모든 구체 팩토리(`LightUIFactory`, `DarkUIFactory`, ...)를 전부 수정해야 합니다. 반대로 새로운 테마(예: 블루 모드)를 통째로 추가하는 것은 `UIFactory`를 구현하는 새 클래스 하나만 만들면 되므로 매우 쉽습니다. 즉 "제품군 추가"는 쉽지만 "제품군 내 신규 제품 종류 추가"는 어렵다는 비대칭적인 확장성을 갖고 있다는 점을 설계 시점에 인지하고 있어야 합니다.

### 6. 실무 프레임워크 적용 사례

Java AWT/Swing의 `Toolkit` 클래스는 운영체제별로 서로 다른 네이티브 UI 컴포넌트 구현체 세트를 생성하는 추상 팩토리 역할을 합니다. XML 파싱에 쓰이는 `javax.xml.parsers.DocumentBuilderFactory`도 내부적으로 벤더마다 다른 파서 구현체 세트를 생성한다는 점에서 이 패턴을 응용한 사례로 볼 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 추상 팩토리 패턴은 관련된 여러 제품(제품군)을 함께 생성하기 위한 인터페이스를 제공하는 생성 패턴이다 | verified | Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software* (1994) |
| CLAIM-002: 추상 팩토리는 기존 제품군에 새 제품 종류를 추가하기 어렵지만, 새로운 제품군 전체를 추가하기는 쉽다는 비대칭적 확장성을 갖는다 | verified | Gamma et al., 동일 도서의 Abstract Factory 장(Consequences 섹션) |
| CLAIM-003: `javax.xml.parsers.DocumentBuilderFactory`는 벤더별 XML 파서 구현체를 생성하는 팩토리 클래스이다 | verified | Oracle Java SE Javadoc, `javax.xml.parsers.DocumentBuilderFactory` |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

추상 팩토리는 팩토리 메서드보다 실무에서 순수한 형태로 마주치는 빈도가 훨씬 낮다고 생각합니다. "제품군을 통째로 세트로 바꿔야 하는" 상황 자체가 크로스플랫폼 UI 툴킷이나 DB 벤더별 드라이버 추상화처럼 비교적 제한된 도메인에서만 뚜렷하게 나타나기 때문입니다. 다만 이 패턴이 가르쳐주는 "제품군 내 신규 제품 추가는 어렵고 신규 제품군 추가는 쉽다"는 트레이드오프 인식 자체는, 추상 팩토리를 명시적으로 쓰지 않는 코드에서도 인터페이스 설계 시 항상 염두에 둘 만한 유용한 기준이라고 봅니다.

## 한계와 반론

**한계점**: 제품군에 새로운 제품 종류가 추가될 때마다 인터페이스와 모든 구체 팩토리를 동시에 수정해야 하므로, 제품 종류가 자주 바뀌는 도메인에는 적합하지 않습니다.

**반론**: 제품 종류의 변경 빈도가 제품군(테마) 종류의 변경 빈도보다 압도적으로 낮다는 것이 사전에 명확하다면, 이 한계는 실질적인 문제가 되지 않습니다. 실제로 UI 툴킷이나 DB 드라이버처럼 이 패턴이 자주 쓰이는 도메인은 "제품의 종류(버튼, 체크박스 등)"는 오랫동안 고정되어 있고 "제품군(테마, 벤더)"만 계속 늘어나는 특성을 갖고 있어, 이 비대칭성이 오히려 패턴의 장점으로 작용합니다.

## 참고문헌

1. Oracle Java SE Javadoc, "DocumentBuilderFactory", [https://docs.oracle.com/javase/8/docs/api/javax/xml/parsers/DocumentBuilderFactory.html](https://docs.oracle.com/javase/8/docs/api/javax/xml/parsers/DocumentBuilderFactory.html) (확인일: 2026-08-17)
2. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
3. Refactoring.Guru, "Abstract Factory", [https://refactoring.guru/design-patterns/abstract-factory](https://refactoring.guru/design-patterns/abstract-factory) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

추상 팩토리 패턴의 핵심 가치는 "이 객체들이 서로 호환되는 세트인지"를 컴파일 타임과 설계 구조로 보장한다는 데 있습니다. 팩토리 메서드가 단일 제품 생성의 확장성을 다룬다면, 추상 팩토리는 여러 제품 간의 일관성을 다루는 상위 개념입니다. 크로스플랫폼 소프트웨어나 멀티 테마 UI처럼 "세트 단위 호환성"이 명확한 요구사항일 때 이 패턴을 적용하면, 잘못된 조합이 섞이는 런타임 버그를 설계 단계에서 원천적으로 방지할 수 있습니다.

## 꼬리질문

1. **추상 팩토리 패턴과 빌더 패턴을 함께 사용해 "세트 구성 + 단계별 조립"이 모두 필요한 복잡한 객체를 만드는 실무 설계는 어떻게 구성하는가?**
   - 추천 참고 URL: [https://refactoring.guru/design-patterns/abstract-factory](https://refactoring.guru/design-patterns/abstract-factory)
2. **`DocumentBuilderFactory.newInstance()`가 클래스패스에서 실제 구현체를 찾는 내부 탐색 순서(META-INF/services 등)는 어떻게 되는가?**
   - 추천 참고 URL: [https://docs.oracle.com/javase/8/docs/api/javax/xml/parsers/DocumentBuilderFactory.html](https://docs.oracle.com/javase/8/docs/api/javax/xml/parsers/DocumentBuilderFactory.html)

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)