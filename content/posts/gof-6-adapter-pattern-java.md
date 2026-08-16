---
id: "828163006431739155"
title: "[GoF 디자인 패턴] 6. 어댑터 패턴 (Adapter Pattern) 개념과 Java 실전 예시"
slug: "gof-6-adapter-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-6-adapter-pattern-java.html"
publishedAt: "2026-08-14T11:27:49.183-07:00"
updatedAt: "2026-08-14T12:02:38.603-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 6. 어댑터 패턴 (Adapter Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
서로 다른 두 클래스의 인터페이스 규격이 맞아떨어지지 않아 함께 사용할 수 없거나, 구형(Legacy) 서비스 코드를 외부 라이브러리라서 고칠 수 없는 상황이 발생합니다.

  
## 2. 해결책 및 동작 메커니즘

  
중간에 어댑터(Adapter) 클래스를 두어 호환되지 않는 기존 인터페이스를 클라이언트가 요구하는 표준 인터페이스 규격으로 맞추어(매핑) 줍니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 소셜 로그인 (구글 / 카카오 / 네이버)

      
소셜 플랫폼마다 제각각인 회원 정보 JSON을 우리 서비스 표준 UserProfile 규격에 맞춰 어댑터가 중간에 변환하여 애플리케이션으로 전달합니다.

    

    
      
#### 🔌 비유: 해외 여행용 220V -> 110V 돼지코 변환 플러그

      
한국 220V 드라이기를 일본 110V 콘센트에 직접 꽂을 수 없듯이, 코드 수정 없이 중간 돼지코(어댑터)가 모양을 바꿔서 연결해 줍니다.

    
  

  
## 3. 실무 주의점

  
    

      클래스 어댑터 vs 객체 어댑터: 자바는 다중 상속을 지원하지 않으므로 상속을 쓰는 클래스 어댑터보다는, 내부 필드로 기존 객체를 갖는 합성(Composition) 기반의 **객체 어댑터 패턴**이 실무에서 훨씬 유연합니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.adapter;

// 1. 클라이언트가 기대하는 최신 표준 인터페이스 (Target)
interface ModernPaymentSystem {
    void processJsonPayment(String jsonRequest);
}

// 2. 과거의 레거시 시스템 (Adaptee) - 수정 불가능하다고 가정
class LegacyXmlPaymentSystem {
    public void doPaymentInXml(String xmlData) {
        System.out.println("💾 [레거시 시스템 처리] XML 데이터로 결제 승인 완료: " + xmlData);
    }
}

// 3. 객체 어댑터 (Adapter) - 합성(Composition) 방식
// Target 인터페이스를 구현하면서 내부에 Adaptee 객체를 품고 변환 작업을 위임함
class XmlToJsonPaymentAdapter implements ModernPaymentSystem {
    private final LegacyXmlPaymentSystem legacySystem;

    public XmlToJsonPaymentAdapter(LegacyXmlPaymentSystem legacySystem) {
        this.legacySystem = legacySystem;
    }

    @Override
    public void processJsonPayment(String jsonRequest) {
        System.out.println("🔄 [어댑터] JSON 요청 수신: " + jsonRequest);
        
        // JSON을 XML로 변환하는 로직 (가상의 파싱 로직)
        String convertedXml = convertJsonToXml(jsonRequest);
        System.out.println("🔄 [어댑터] JSON -> XML 변환 완료");
        
        // 레거시 시스템의 메서드 호출
        legacySystem.doPaymentInXml(convertedXml);
    }

    private String convertJsonToXml(String json) {
        // 실제로는 Jackson 등의 라이브러리 사용
        return "50000";
    }
}

public class AdapterDemo {
    public static void main(String[] args) {
        System.out.println("=== 결제 시스템 마이그레이션 ===");
        
        // 구형 시스템 인스턴스
        LegacyXmlPaymentSystem legacySystem = new LegacyXmlPaymentSystem();
        
        // 어댑터 생성하여 구형 시스템 연결
        ModernPaymentSystem paymentAdapter = new XmlToJsonPaymentAdapter(legacySystem);
        
        // 클라이언트는 최신 표준 인터페이스(JSON)만 사용하여 결제 호출
        // 내부에서는 어댑터가 구형 XML 시스템으로 연결해 줌
        String jsonPayload = "{ "amount": 50000 }";
        paymentAdapter.processJsonPayment(jsonPayload);
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 결제 시스템 마이그레이션 ===
🔄 [어댑터] JSON 요청 수신: { "amount": 50000 }
🔄 [어댑터] JSON -> XML 변환 완료
💾 [레거시 시스템 처리] XML 데이터로 결제 승인 완료: 50000
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Spring MVC `HandlerAdapter`, Java `InputStreamReader(InputStream)`
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
