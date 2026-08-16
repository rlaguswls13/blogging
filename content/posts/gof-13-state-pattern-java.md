---
id: "5260378206272592514"
title: "[GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시"
slug: "gof-13-state-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-13-state-pattern-java.html"
publishedAt: "2026-08-14T11:28:55.000-07:00"
updatedAt: "2026-08-14T12:02:25.808-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
여러 개의 연관된 객체들을 조합하여 생성할 때, 각 객체를 따로 생성하면 서로 어울리지 않거나 호환되지 않는 부품들이 섞여 결합 버그가 일어날 수 있습니다.

  
## 2. 해결책 및 동작 메커니즘

  
서로 관련이 있거나 의존적인 제품군을 생성하기 위한 인터페이스를 제공하여, 클라이언트가 호환성이 검증된 세트 단위 객체들만 생성하도록 만듭니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 다크모드 / 라이트모드 UI 세트 생성

      
사용자가 '다크모드'를 켜면 테마 팩토리가 다크 버튼, 다크 체크박스 등 어울리는 UI 요소 조합을 한 번에 생성합니다.

    

    
      
#### 🛋️ 비유: 가구 브랜드 세트 (이케아 북유럽풍 vs 한샘 모던풍)

      
의자는 북유럽풍인데 테이블은 조선시대 전통 가구면 어색합니다. 세트로 묶인 제품군(의자+테이블+조명)을 세트 단위로 맞춰서 만듭니다.

    
  

  
## 3. 실무 주의점

  
    

      제품군 내 새로운 상품 종류 추가의 어려움: 새로운 테마(예: '블루모드')를 추가하는 것은 쉽지만, 기존 세트에 '라디오버튼'이라는 새로운 종류를 추가하려면 모든 팩토리와 인터페이스를 수정해야 합니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.abstractfactory;

// 1. 추상 제품 (Abstract Products)
interface Button { void paint(); }
interface Checkbox { void render(); }

// 2. 구체 제품 - 라이트 모드 (Concrete Products)
class LightButton implements Button {
    public void paint() { System.out.println("⬜ [라이트 모드] 흰색 배경에 검은 글씨 버튼 생성"); }
}
class LightCheckbox implements Checkbox {
    public void render() { System.out.println("☑️ [라이트 모드] 밝은 체크박스 생성"); }
}

// 3. 구체 제품 - 다크 모드 (Concrete Products)
class DarkButton implements Button {
    public void paint() { System.out.println("⬛ [다크 모드] 검은 배경에 흰 글씨 버튼 생성"); }
}
class DarkCheckbox implements Checkbox {
    public void render() { System.out.println("✅ [다크 모드] 어두운 체크박스 생성"); }
}

// 4. 추상 팩토리 (Abstract Factory) - ��품군(세트) 생성 인터페이스
interface UIFactory {
    Button createButton();
    Checkbox createCheckbox();
}

// 5. 구체 팩토리 (Concrete Factories)
class LightUIFactory implements UIFactory {
    public Button createButton() { return new LightButton(); }
    public Checkbox createCheckbox() { return new LightCheckbox(); }
}

class DarkUIFactory implements UIFactory {
    public Button createButton() { return new DarkButton(); }
    public Checkbox createCheckbox() { return new DarkCheckbox(); }
}

// 6. 클라이언트 애플리케이션 클래스
class Application {
    private Button button;
    private Checkbox checkbox;

    // 클라이언트는 구체 팩토리를 주입받아 사용하므로, 구체적인 제품 클래스에 의존하지 않음
    public Application(UIFactory factory) {
        button = factory.createButton();
        checkbox = factory.createCheckbox();
    }

    public void paintUI() {
        button.paint();
        checkbox.render();
    }
}

public class AbstractFactoryDemo {
    public static void main(String[] args) {
        System.out.println("=== 1. 라이트 테마 적용 ===");
        UIFactory lightFactory = new LightUIFactory();
        Application app1 = new Application(lightFactory);
        app1.paintUI();

        System.out.println("\n=== 2. 다크 테마 적용 ===");
        UIFactory darkFactory = new DarkUIFactory();
        Application app2 = new Application(darkFactory);
        app2.paintUI();
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 1. 라이트 테마 적용 ===
⬜ [라이트 모드] 흰색 배경에 검은 글씨 버튼 생성
☑️ [라이트 모드] 밝은 체크박스 생성

=== 2. 다크 테마 적용 ===
⬛ [다크 모드] 검은 배경에 흰 글씨 버튼 생성
✅ [다크 모드] 어두운 체크박스 생성
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Java AWT/Swing `Toolkit`, `DocumentBuilderFactory`
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
