---
id: "1920448605652878906"
title: "[GoF 디자인 패턴] 7. 데코레이터 패턴 (Decorator Pattern) 개념과 Java 실전 예시"
slug: "gof-7-decorator-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-7-decorator-pattern-java.html"
publishedAt: "2026-08-14T11:27:53.754-07:00"
updatedAt: "2026-08-14T12:02:42.806-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 7. 데코레이터 패턴 (Decorator Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
상속을 통해 기능을 조합하려고 하면 경우의 수(예: 커피+우유, 커피+모카, 커피+우유+모카)마다 무수한 서브클래스가 생기는 클래스 폭발(Class Explosion) 문제가 일어납니다.

  
## 2. 해결책 및 동작 메커니즘

  
객체를 동일한 인터페이스를 구현하는 감싸개(Wrapper) 데코레이터로 겹겹이 포장하여, 원본 소스 수정 없이 런타임에 동적으로 새로운 기능을 추가 및 조합합니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 커피숍 커스텀 주문 시스템

      
에스프레소 객체를 생성하고, 그 위에 모카 데코레이터를 씌우고, 다시 휘핑크림 데코레이터를 씌워 객체 기능과 가격을 동적으로 누적시킵니다.

    

    
      
#### ☕ 비유: 에스프레소 베이스에 토핑 추가

      
에스프레소 원형은 건드리지 않고, 손님 취향에 따라 우유 추가, 시럽 추가, 휘핑크림 토핑을 포장지로 겹겹이 싸�� 새로운 메뉴를 만들어 냅니다.

    
  

  
## 3. 실무 주의점

  
    

      디버깅 난이도 상승: 데코레이터를 10개 이상 겹겹이 싸면 자바 객체 스택 깊이가 매우 깊어져, 내부에서 에러가 났을 때 원인을 추적(Stack Trace)하기 꽤 까다로워집니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.decorator;

// 1. 기본 컴포넌트 인터페이스 (Component)
interface Coffee {
    String getDescription();
    int getCost();
}

// 2. ��본 구현체 (Concrete Component) - 베이스가 되는 원본 객체
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

// 3. 추상 데코레이터 (Decorator) - 핵심! Coffee를 구현함과 동시에 Coffee를 품고 있음
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
        System.out.println("=== ☕ 커피 커스텀 주문 시스템 ===");

        // 1. 기본 에스프레소 주문
        Coffee espresso = new Espresso();
        System.out.println("주문 1: " + espresso.getDescription() + " | 가격: " + espresso.getCost() + "원");

        // 2. 에스프레소 + 스팀 밀크 + 모카 시럽 (카페모카)
        Coffee cafeMocha = new Espresso();
        cafeMocha = new MilkDecorator(cafeMocha); // 우유 포장
        cafeMocha = new MochaDecorator(cafeMocha); // 그 위에 모카 ���장
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

/*
▶ 실행 결과 (Expected Output):
=== ☕ 커피 커스텀 주문 시스템 ===
주문 1: 에스프레소 | 가격: 3000원
주문 2: 에스프레소 + 스팀 밀크 + 모카 시럽 | 가격: 4300원
주문 3: 아메리카노 + 모카 시럽 + 모카 시럽 + 휘핑 크림 | 가격: 5800원
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Java I/O 클래스 `new BufferedReader(new InputStreamReader(System.in))`, `Collections.synchronizedList()`
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
