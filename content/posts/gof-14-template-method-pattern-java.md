---
id: "1254433254714617011"
title: "[GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시"
slug: "gof-14-template-method-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-14-template-method-pattern-java.html"
publishedAt: "2026-08-14T11:29:01.000-07:00"
updatedAt: "2026-08-15T16:18:40.008-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
생성자에 전달해야 할 매개변수가 많아지면 인자의 순서가 헷갈려 잘못된 값이 주입되거나, 선택적 매개변수 처리를 위해 수많은 생성자 오버로딩(Telescoping Constructor)이 발생합니다.

  
## 2. 해결책 및 동작 메커니즘

  
객체 생성을 별도의 Builder 클래스로 위임하여, 가독성 높은 메서드 체이닝 방식으로 원하는 필드만 선택적으로 입력받아 안전하게 최종 불변 객체를 생성합니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 요*요 / 배민 음식 맞춤 옵션 주문

      
Order.builder().menu('떡볶이').spicy('매운맛').addOption('치즈추가').build() 체이닝으로 헷갈리지 않고 안전하게 맞춤 주문 객체 조립

    

    
      
#### 🍔 비유: 서브웨이 샌드위치 / 수제버거 맞춤 주문

      
빵 종류 선택 -> 패티 추가 -> 피클 빼고 -> 올리브 추가처럼, 원하는 재료 조합을 사용자가 순서대로 조립해서 완성합니다. 순서가 바뀌어도 무방합니다.

    
  

  
## 3. 실무 주의점

  
    

      💡 **Lombok 주의:** `@Builder` 사용 시 클래스 레벨에 부여하면 `package-private` 전체 생성자가 노출됩니다. 또한 초기값이 있는 필드는 `@Builder.Default`를 명시해야 값이 덮어씌워지지 않습니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.builder;

import java.util.ArrayList;
import java.util.List;

// 불변(Immutable) 객체로 설계된 Pizza 클래스
class Pizza {
    private final String dough;       // 필수
    private final String sauce;       // 필수
    private final boolean cheese;     // 선택
    private final boolean pepperoni;  // 선택
    private final List toppings; // 선택

    // private 생성자: 외부에서는 직접 생성 불가, 오직 Builder를 통해서만 생성 가능
    private Pizza(PizzaBuilder builder) {
        this.dough = builder.dough;
        this.sauce = builder.sauce;
        this.cheese = builder.cheese;
        this.pepperoni = builder.pepperoni;
        this.toppings = builder.toppings;
    }

    public void showPizza() {
        System.out.println("🍕 주문하신 피자 완성!");
        System.out.println(" - 도우: " + dough);
        System.out.println(" - 소스: " + sauce);
        System.out.println(" - 치즈 추가: " + (cheese ? "O" : "X"));
        System.out.println(" - 페퍼로니 추가: " + (pepperoni ? "O" : "X"));
        System.out.println(" - 추가 토핑: " + (toppings.isEmpty() ? "없음" : toppings));
        System.out.println("---------------------------------");
    }

    // 정적 내부 빌더 클래스
    public static class PizzaBuilder {
        // 필수 파라미터
        private final String dough;
        private final String sauce;
        
        // 선택 파라미터 (기본값 설정 가능)
        private boolean cheese = false;
        private boolean pepperoni = false;
        private List toppings = new ArrayList<>();

        // 필수 값은 빌더의 생성자로 받음
        public PizzaBuilder(String dough, String sauce) {
            this.dough = dough;
            this.sauce = sauce;
        }

        // 체이닝(Chaining)을 위해 this를 반환하는 Setter 메서드들
        public PizzaBuilder addCheese() {
            this.cheese = true;
            return this;
        }

        public PizzaBuilder addPepperoni() {
            this.pepperoni = true;
            return this;
        }

        public PizzaBuilder addTopping(String topping) {
            this.toppings.add(topping);
            return this;
        }

        // 최종 객체 생성 및 유효성 검증
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
        // 1. 치즈 피자 (필수 옵션 + 치즈)
        Pizza cheesePizza = new Pizza.PizzaBuilder("씬 도우", "토마토 소스")
                .addCheese()
                .build();
        
        // 2. 프리미엄 페퍼로니 피자 (체이닝 방식의 유연함)
        Pizza premiumPizza = new Pizza.PizzaBuilder("치즈크러스트", "바베큐 소스")
                .addCheese()
                .addPepperoni()
                .addTopping("올리브")
                .addTopping("피망")
                .addTopping("할라피뇨")
                .build();

        cheesePizza.showPizza();
        premiumPizza.showPizza();
    }
}

/*
▶ 실행 결과 (Expected Output):
🍕 주문하신 피자 완성!
 - 도우: 씬 도우
 - 소스: 토마토 소스
 - 치즈 추가: O
 - 페퍼로니 추가: X
 - 추가 토핑: 없음
---------------------------------
🍕 주문하신 피자 완성!
 - 도우: 치즈크러스트
 - 소스: 바베큐 소스
 - 치즈 추가: O
 - 페퍼로니 추가: O
 - 추가 토핑: [올리브, 피망, 할라피뇨]
---------------------------------
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Lombok `@Builder`, Spring `UriComponentsBuilder`, Java `StringBuilder`
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
