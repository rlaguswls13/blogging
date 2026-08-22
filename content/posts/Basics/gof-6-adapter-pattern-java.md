---
id: '828163006431739155'
publishedAt: '2026-08-14T11:27:49.183-07:00'
slug: gof-6-adapter-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
- GoF_Series
title: '[GoF 디자인 패턴] 6. 어댑터 패턴 (Adapter Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T12:02:38.603-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-6-adapter-pattern-java.html
---

# [GoF 디자인 패턴] 6. 어댑터 패턴 (Adapter Pattern) 개념과 Java 실전 예시

## 요약

어댑터 패턴(Adapter Pattern)은 서로 호환되지 않는 두 인터페이스 사이에 변환기를 두어, 기존 코드를 고치지 않고도 함께 동작하게 만드는 구조 패턴입니다. 레거시 시스템을 새 표준 인터페이스와 연결해야 하거나, 외부 라이브러리처럼 직접 수정할 수 없는 코드를 통합해야 할 때 특히 유용합니다. 이 글에서는 클래스 어댑터와 객체 어댑터의 차이, 실제 동작하는 Java 코드, 그리고 Spring MVC의 `HandlerAdapter` 같은 실무 적용 사례를 다룹니다.

## 본문

### 1. 배경 및 문제점

서로 다른 두 클래스의 인터페이스 규격이 맞지 않아 함께 사용할 수 없는 상황은 실무에서 자주 발생합니다. 특히 문제가 되는 경우는 한쪽이 구형(Legacy) 시스템이거나 외부에서 가져온 라이브러리라서 소스 코드를 직접 고칠 수 없을 때입니다. 클라이언트 코드가 요구하는 인터페이스와 기존 시스템이 제공하는 인터페이스가 다르면, 둘을 그대로 연결할 방법이 없어 통합 작업이 막히게 됩니다.

### 2. 해결책 및 동작 메커니즘

어댑터 패턴은 중간에 어댑터(Adapter) 클래스를 두어, 호환되지 않는 기존 인터페이스를 클라이언트가 요구하는 표준 인터페이스 규격으로 변환해 줍니다. 클라이언트는 어댑터의 표준 인터페이스만 바라보고, 어댑터 내부에서 기존(레거시) 객체로 요청을 위임하는 방식입니다.

**실제 서비스 동작 예시**: 소셜 로그인 기능을 구현할 때 구글, 카카오, 네이버 등 플랫폼마다 회원 정보 JSON 응답 규격이 제각각입니다. 각 플랫폼의 응답을 우리 서비스의 표준 `UserProfile` 규격으로 변환하는 어댑터를 두면, 애플리케이션 나머지 코드는 어떤 플랫폼으로 로그인했는지 신경 쓰지 않고 동일한 방식으로 사용자 정보를 다룰 수 있습니다.

**비유**: 한국에서 쓰던 220V 드라이기를 일본의 110V 콘센트에 그대로 꽂을 수는 없습니다. 드라이기 자체를 개조하는 대신, 중간에 돼지코(변환 플러그)를 끼우면 모양과 전압을 맞춰 그대로 사용할 수 있습니다. 어댑터도 마찬가지로 원본 객체를 건드리지 않고 중간에서 규격을 맞춰줍니다.

### 3. 실무 주의점: 클래스 어댑터 vs 객체 어댑터

어댑터는 상속으로 구현하는 클래스 어댑터와, 내부 필드로 기존 객체를 보유하는 객체 어댑터로 나뉩니다. Java는 클래스의 다중 상속을 지원하지 않으므로, 어댑터가 기존 클래스와 새 인터페이스를 동시에 상속받아야 하는 클래스 어댑터 방식은 구조적으로 제약이 많습니다. 반면 합성(Composition)을 기반으로 하는 객체 어댑터는 인터페이스만 구현하고 내부에 기존 객체의 참조를 필드로 갖는 방식이라 유연성이 훨씬 높아, 실무에서는 객체 어댑터가 압도적으로 많이 쓰입니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
package com.gof.adapter;

// 1. 클라이언트가 기대하는 최신 표준 인터페이스 (Target)
interface ModernPaymentSystem {
    void processJsonPayment(String jsonRequest);
}

// 2. 과거의 레거시 시스템 (Adaptee) - 수정 불가능하다고 가정
class LegacyXmlPaymentSystem {
    public void doPaymentInXml(String xmlData) {
        System.out.println("[레거시 시스템 처리] XML 데이터로 결제 승인 완료: " + xmlData);
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
        System.out.println("[어댑터] JSON 요청 수신: " + jsonRequest);

        // JSON을 XML로 변환하는 로직 (가상의 파싱 로직)
        String convertedXml = convertJsonToXml(jsonRequest);
        System.out.println("[어댑터] JSON -> XML 변환 완료");

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
        String jsonPayload = "{\"amount\": 50000}";
        paymentAdapter.processJsonPayment(jsonPayload);
    }
}
```

실행 결과를 보면 클라이언트(`AdapterDemo`)는 JSON 기반의 `ModernPaymentSystem` 인터페이스만 호출했을 뿐인데, 실제 결제 처리는 XML 기반의 레거시 시스템에서 이루어졌음을 확인할 수 있습니다. 클라이언트 코드는 레거시 시스템의 존재조차 알 필요가 없습니다.

### 5. 실무 프레임워크 적용 사례

Spring MVC의 `HandlerAdapter`가 대표적인 예입니다. Spring MVC는 `@Controller` 기반 컨트롤러, `HttpRequestHandler`, 레거시 `Controller` 인터페이스 등 여러 방식의 핸들러를 지원해야 하는데, `DispatcherServlet`이 각 핸들러 타입을 직접 알 필요 없이 `HandlerAdapter`가 이를 표준화된 방식으로 호출하도록 중간에서 변환해 줍니다. Java 표준 라이브러리에서는 바이트 스트림을 문자 스트림으로 변환하는 `InputStreamReader(InputStream)`도 어댑터 패턴의 실제 구현체입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 어댑터 패턴은 호환되지 않는 인터페이스 사이에 변환 계층을 두어 기존 코드 수정 없이 함께 동작시키는 구조 패턴이다 | verified | Gamma et al., Design Patterns (1994) |
| CLAIM-002: Java는 클래스 다중 상속을 지원하지 않으므로 실무에서는 상속 기반 클래스 어댑터보다 합성 기반 객체 어댑터가 더 널리 쓰인다 | verified | Java Language Specification, 단일 상속 원칙 |
| CLAIM-003: java.io.InputStreamReader는 바이트 기반 InputStream을 문자 기반 Reader로 변환하는 어댑터 역할을 한다 | verified | Oracle Java SE 8 API, java.io.InputStreamReader |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

어댑터 패턴은 개념 자체는 단순하지만, 실무에서 가장 자주 마주치는 패턴 중 하나라고 생각합니다. 외부 API 연동, 레거시 시스템 마이그레이션, 서로 다른 팀이 만든 모듈을 통합하는 상황마다 사실상 알게 모르게 어댑터를 만들고 있는 경우가 많습니다. 다만 어댑터가 여러 겹으로 쌓이기 시작하면 원래 데이터가 어떤 경로로 변환되었는지 추적하기 어려워지므로, 어댑터는 "임시방편"이 아니라 명확한 경계를 가진 설계 요소로 다뤄야 한다고 봅니다. 특히 레거시 시스템을 완전히 교체하기 전 과도기 단계에서 어댑터를 도입하는 것은 실무적으로 매우 합리적인 선택이라고 생각합니다.

## 한계와 반론

어댑터 패턴은 변환 로직 자체가 복잡해지면 어댑터 클래스가 비대해지고, 원본 데이터 구조와 변환된 구조 사이의 불일치로 인한 정보 손실이 발생할 수 있다는 한계가 있습니다. 또한 어댑터가 여러 단계로 중첩되면 디버깅 시 실제 문제가 원본 시스템에 있는지 변환 로직에 있는지 파악하기 어려워집니다. 반론으로는, 애초에 인터페이스 설계 단계에서 표준을 잘 맞췄다면 어댑터가 필요 없었을 것이라는 지적이 있을 수 있으나, 외부 라이브러리나 레거시 코드처럼 통제할 수 없는 영역이 존재하는 한 어댑터 패턴의 필요성은 현실적으로 사라지지 않습니다.

## 참고문헌

1. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
2. [Java SE 8 API - InputStreamReader](https://docs.oracle.com/javase/8/docs/api/java/io/InputStreamReader.html) (확인일: 2026-08-17)
3. [Refactoring.Guru - Adapter Pattern](https://refactoring.guru/design-patterns/adapter) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

어댑터 패턴은 "고칠 수 없는 것과 어떻게 함께 일할 것인가"라는 실무적 문제에 대한 답입니다. 클래스 어댑터보다 객체 어댑터가 Java 생태계에서 훨씬 유연하게 쓰이는 이유도 결국 상속보다 합성을 우선하라는 일반적인 설계 원칙과 맞닿아 있습니다. Spring MVC의 `HandlerAdapter`처럼 프레임워크 내부에도 이 패턴이 널리 쓰이고 있다는 점은, 어댑터 패턴이 단순한 이론이 아니라 대규모 시스템에서 실제로 검증된 통합 전략임을 보여줍니다. 다만 어댑터를 도입할 때는 항상 "언제 이 어댑터를 걷어낼 것인가"라는 출구 전략도 함께 고려하는 것이 바람직합니다.

## 꼬리질문

1. **여러 개의 어댑터가 체인처럼 중첩될 때 발생하는 성능 오버헤드와 디버깅 난이도는 어떻게 관리해야 하는가?**
   - 추천 참고 URL: https://refactoring.guru/design-patterns/adapter
2. **Spring MVC의 HandlerAdapter가 여러 컨트롤러 타입을 지원하기 위해 내부적으로 어떤 우선순위 선택 메커니즘을 사용하는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)