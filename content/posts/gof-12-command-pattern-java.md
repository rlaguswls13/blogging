---
id: "2647152662034823524"
title: "[GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시"
slug: "gof-12-command-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-12-command-pattern-java.html"
publishedAt: "2026-08-14T11:28:48.000-07:00"
updatedAt: "2026-08-15T16:18:44.656-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
클라이언트 코드 내부에서 `new ConcreteProduct()`를 직접 호출하면, 새로운 제품 타입이 추가될 때마다 클라이언트의 분기 코드를 직접 수정해야 하므로 개방-폐쇄 원칙(OCP)이 깨집니다.

  
## 2. 해결책 및 동작 메커니즘

  
객체 생성 처리를 템플릿 팩토리 메서드로 추상화하고, 하위 구체 팩토리 클래스에서 어떤 제품 객체를 생성할지 결정하게 만들어 결합도를 낮춥니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 배*의민족 결제 수단 선택 (카*오페이 / 토*페이 / 신용카드)

      
사용자가 '카*오페이'를 선택하면 KakaoPayProcessor, '토*페이'를 선택하면 TossPayProcessor 객체를 팩토리가 알아서 분기 생성해 결제 승인

    

    
      
#### 🍕 비유: 프랜차이즈 피자 본사와 지역 지점 매장

      
본사는 '피자 조리 절차'만 정해두고, 실제로 치즈피자를 만들지 페퍼로니피자를 만들지는 각 지점 매장이 결정합니다. 본사 시스템을 안 고치고 지점만 새로 내면 되는 유연함을 얻습니다.

    
  

  
## 3. 실무 주의점

  
    

      클래스 폭발 (Class Explosion): 제품(Product)이 새로 추가될 때마다 구체 팩토리(Concrete Factory) 클래스도 반드시 쌍으로 하나씩 더 만들어야 하므로 관리해야 할 자바 파일 수가 늘어납니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.factorymethod;

// 1. 제품(Product) 인터페이스
interface PaymentProcessor {
    void processPayment(int amount);
}

// 2. 구체적인 제품(Concrete Product)
class KakaoPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("🟡 [카*오페이] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

class TossPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("🔵 [토*페이] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

class CardPayProcessor implements PaymentProcessor {
    @Override
    public void processPayment(int amount) {
        System.out.println("💳 [신용카드] " + amount + "원 결제가 정상적으로 처리되었습니다.");
    }
}

// 3. 생성자(Creator) 추상 클래스 - 팩토리 메서드 정의
abstract class PaymentFactory {
    // 팩토리 메서드 (서브클래스에서 구현)
    public abstract PaymentProcessor createPaymentProcessor();

    // 템플릿 메서드처럼 결제 프로세스 전체를 관장할 수도 있음
    public void checkout(int amount) {
        PaymentProcessor processor = createPaymentProcessor();
        System.out.println("🔄 결제 준비 중... 프로세서 할당 완료");
        processor.processPayment(amount);
        System.out.println("✅ 결제 완료 처리가 종료되었습니다.\n");
    }
}

// 4. 구체적인 팩토리(Concrete Creator)
class KakaoPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() {
        return new KakaoPayProcessor(); // 카*오페이 프로세서 생성
    }
}

class TossPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() {
        return new TossPayProcessor(); // 토*페이 프로세서 생성
    }
}

class CardPayFactory extends PaymentFactory {
    @Override
    public PaymentProcessor createPaymentProcessor() {
        return new CardPayProcessor(); // 신용카드 프로세서 생성
    }
}

public class FactoryMethodDemo {
    public static void main(String[] args) {
        System.out.println("=== 팩토리 메서드 패턴 결제 시스템 ===\n");

        // 1. 카*오페이 결제 진행
        PaymentFactory kakaoFactory = new KakaoPayFactory();
        kakaoFactory.checkout(15000);

        // 2. 토*페이 결제 진행
        PaymentFactory tossFactory = new TossPayFactory();
        tossFactory.checkout(20000);

        // 3. 신용카드 결제 진행
        PaymentFactory cardFactory = new CardPayFactory();
        cardFactory.checkout(35000);
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 팩토리 메서드 패턴 결제 시스템 ===

🔄 결제 준비 중... 프로세서 할당 완료
🟡 [카*오페이] 15000원 결제가 정상적으로 처리되었습니다.
✅ 결제 완료 처리 후 종료되었습니다.

🔄 결제 준비 중... 프로세서 할당 완료
🔵 [토*페이] 20000원 결제가 정상적으로 처리되었습니다.
✅ 결제 완료 처리가 종료되었습니다.

🔄 결제 준비 중... 프로세서 할당 완료
💳 [신용카드] 35000원 결제가 정상적으로 처리되었습니다.
✅ 결제 완료 처리가 종료되었습니다.
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Spring의 `FactoryBean`, Java `Calendar.getInstance()`
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
