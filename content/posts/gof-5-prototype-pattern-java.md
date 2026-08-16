---
id: '5255194139828588121'
publishedAt: '2026-08-14T11:27:19.308-07:00'
slug: gof-5-prototype-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 5. 프로토타입 패턴 (Prototype Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T12:02:34.274-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-5-prototype-pattern-java.html
---

# [GoF 디자인 패턴] 5. 프로토타입 패턴 (Prototype Pattern) 개념과 Java 실전 예시

## 요약

프로토타입 패턴(Prototype Pattern)은 객체를 매번 `new` 키워드로 새로 생성하는 대신, 이미 만들어진 원본 객체를 복제(Clone)해서 필요한 객체를 빠르게 얻는 생성 패턴입니다. DB 조회나 네트워크 I/O처럼 초기화 비용이 큰 객체를 반복 생성해야 할 때 특히 유용하며, Java에서는 `Cloneable` 인터페이스와 `Object.clone()`을 통해 구현합니다. 이 글에서는 패턴이 필요한 배경, 얕은 복사와 깊은 복사의 차이, 실제 동작하는 Java 코드, 그리고 Spring Prototype Scope Bean 같은 실무 적용 사례까지 다룹니다.

## 본문

### 1. 배경 및 문제점

객체를 새로 생성하는 비용이 항상 저렴한 것은 아닙니다. DB 조회, 네트워크 I/O, 파일 파싱처럼 무거운 초기화 작업이 포함된 객체를 매번 `new`로 처음부터 다시 만들면 애플리케이션의 응답 속도가 눈에 띄게 저하됩니다. 예를 들어 문서 템플릿을 DB에서 읽어와 초기화하는 데 1초가 걸린다면, 같은 템플릿을 기반으로 한 문서를 100개 만드는 데 100초가 걸리는 셈입니다. 이미 로드된 데이터를 재사용할 수 있다면 이 비용을 크게 줄일 수 있습니다.

### 2. 해결책 및 동작 메커니즘

프로토타입 패턴은 이미 존재하는 무거운 객체를 복사(Clone)해서 새로운 객체를 생성함으로써 초기화 비용과 시간을 최소화합니다. 원본 객체는 한 번만 무겁게 생성하고, 이후로는 그 원본을 복제해서 필요한 부분만 수정하는 방식입니다.

**실제 서비스 동작 예시**: '여행 리뷰 템플릿'을 선택할 때 처음부터 레이아웃을 다시 그리지 않고, 이미 로드된 원본 템플릿을 복사해와서 글자만 고쳐 포스팅합니다.

**비유**: 100페이지짜리 표준 계약서를 처음부터 일일이 새로 타이핑하는 대신, 기존 원본을 복사기로 1초 만에 복제한 뒤 이름과 날짜만 고쳐 씁니다.

### 3. 실무 주의점: 얕은 복사 vs 깊은 복사

`Object.clone()`은 기본적으로 얕은 복사(Shallow Copy)를 수행합니다. 즉 필드 값 자체는 복사되지만, 리스트나 맵 같은 참조 타입 필드는 원본과 복사본이 같은 메모리 주소를 공유하게 됩니다. 이 상태에서 복사본의 리스트에 항목을 추가하면 원본의 리스트에도 그 항목이 함께 추가되는 버그가 발생합니다. 이를 방지하려면 `clone()`을 오버라이딩해서 참조 타입 필드를 직접 새로 복사하는 깊은 복사(Deep Copy)를 구현해야 하며, 이때 원본과 복사본의 독립성이 실제로 보장되는지 반드시 테스트로 검증해야 합니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
package com.gof.prototype;

import java.util.ArrayList;
import java.util.List;

// Cloneable 인터페이스 구현
class DocumentTemplate implements Cloneable {
    private String title;
    private String format;
    private List<String> placeholders; // 참조 타입 필드

    public DocumentTemplate(String title, String format) {
        System.out.println("DB에서 템플릿 정보를 읽어와 무거운 초기화를 진행합니다... [" + title + "]");
        try {
            Thread.sleep(1000); // 무거운 작업 시뮬레이션
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        this.title = title;
        this.format = format;
        this.placeholders = new ArrayList<>();
        this.placeholders.add("NAME");
        this.placeholders.add("DATE");
    }

    public void setTitle(String title) { this.title = title; }
    public void addPlaceholder(String placeholder) { this.placeholders.add(placeholder); }

    public void printDocument() {
        System.out.println("문서 제목: " + title + " | 형식: " + format + " | 서명란: " + placeholders);
    }

    // 핵심: 깊은 복사(Deep Copy)를 지원하는 clone() 오버라이딩
    @Override
    public DocumentTemplate clone() {
        try {
            // 1. 기본 얕은 복사 수행
            DocumentTemplate cloned = (DocumentTemplate) super.clone();

            // 2. 참조 타입(List)의 깊은 복사 수동 처리
            // 이 작업을 안 하면 원본과 복사본이 동일한 리스트 메모리를 공유하게 됨
            cloned.placeholders = new ArrayList<>(this.placeholders);

            return cloned;
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException("복사 실패", e);
        }
    }
}

public class PrototypeDemo {
    public static void main(String[] args) {
        // 1. 최초 객체 생성 (매우 오래 걸림)
        System.out.println("=== 1. 원본 객체 생성 ===");
        DocumentTemplate originalContract = new DocumentTemplate("표준 근로 계약서", "PDF");
        originalContract.printDocument();

        System.out.println("=== 2. 프로토타입 복제 (즉시 생성) ===");
        DocumentTemplate copyContract1 = originalContract.clone();
        copyContract1.setTitle("홍길동 근로 계약서");
        copyContract1.addPlaceholder("SIGNATURE");

        DocumentTemplate copyContract2 = originalContract.clone();
        copyContract2.setTitle("이순신 근로 계약서");

        // 3. 깊은 복사 확인
        System.out.println("=== 3. 독립성 검증 (깊은 복사) ===");
        originalContract.printDocument(); // 원본에는 SIGNATURE가 없어야 정상
        copyContract1.printDocument();    // 복사본 1에는 SIGNATURE가 있어야 정상
        copyContract2.printDocument();    // 복사본 2에는 원본과 같아야 정상
    }
}
```

실행하면 원본 객체는 1초의 초기화 시간이 걸리지만, 복제된 두 객체는 그 시간 없이 즉시 생성되면서도 서로 독립적인 상태를 유지하는 것을 확인할 수 있습니다.

### 5. 실무 프레임워크 적용 사례

Spring Framework의 Bean Scope 중 `prototype` 스코프는 이름 그대로 이 패턴에서 유래했습니다. `singleton` 스코프가 컨테이너당 인스턴스 하나만 유지하는 것과 달리, `prototype` 스코프로 등록된 빈은 요청할 때마다 새 인스턴스를 만들어 반환합니다. Java 표준 라이브러리에서도 `Object.clone()`과 `Cloneable` 마커 인터페이스 자체가 프로토타입 패턴의 직접적인 구현체입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 프로토타입 패턴은 객체를 새로 생성하는 대신 기존 인스턴스를 복제하여 생성 비용을 절감하는 생성 패턴이다 | verified | Gamma et al., Design Patterns (1994) |
| CLAIM-002: Java의 Object.clone()은 기본적으로 얕은 복사를 수행하며, 참조 타입 필드의 독립성을 보장하려면 clone()을 오버라이딩해 깊은 복사를 직접 구현해야 한다 | verified | Oracle Java SE 8 API, java.lang.Object#clone |
| CLAIM-003: Spring Framework의 prototype 빈 스코프는 빈을 요청할 때마다 새 인스턴스를 생성해 반환한다 | verified | Spring Framework Reference Documentation |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 프로토타입 패턴을 직접 `Cloneable`로 구현하는 경우는 생각보다 많지 않습니다. Java의 `Cloneable`은 마커 인터페이스일 뿐이라 `clone()`의 접근 제한자나 예외 처리를 직접 신경 써야 하고, 얕은 복사 함정에 걸리기 쉬워 실수가 잦은 편입니다. 그래서 실제로는 복사 생성자(Copy Constructor)나 정적 팩토리 메서드로 같은 효과를 내는 경우가 더 흔하다고 봅니다. 다만 초기화 비용이 매우 큰 객체를 다루는 상황이라면, 프로토타입 패턴의 핵심 아이디어인 "무거운 원본을 한 번만 만들고 복제로 재사용한다"는 발상 자체는 여전히 유효하며, Spring의 prototype 스코프처럼 프레임워크 레벨에서 이미 이 개념을 차용하고 있다는 점도 실무적으로 눈여겨볼 만합니다.

## 한계와 반론

프로토타입 패턴은 객체 내부에 순환 참조나 복잡하게 얽힌 참조 그래프가 있을 경우 깊은 복사 구현이 매우 까다로워진다는 한계가 있습니다. 이런 경우 직렬화(Serialization) 기반 복사나 별도의 복사 라이브러리를 쓰는 편이 나을 수 있습니다. 반론으로는, 애초에 객체 생성 비용이 그리 크지 않은 대다수의 일반적인 도메인 객체에는 이 패턴을 적용할 실익이 적으며, 오히려 코드 복잡도만 높인다는 지적도 있습니다. 따라서 프로토타입 패턴은 만능 해법이 아니라, 생성 비용이 실제로 병목이 되는 특정 상황에 한정해 선택적으로 적용하는 것이 바람직합니다.

## 참고문헌

1. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
2. [Java SE 8 API - Object.clone()](https://docs.oracle.com/javase/8/docs/api/java/lang/Object.html) (확인일: 2026-08-17)
3. [Refactoring.Guru - Prototype Pattern](https://refactoring.guru/design-patterns/prototype) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

프로토타입 패턴은 "생성 비용이 큰 객체를 어떻게 저렴하게 재사용할 것인가"라는 실용적인 질문에서 출발한 패턴입니다. Java의 `Cloneable` 메커니즘 자체는 얕은 복사의 함정 때문에 다루기 까다롭지만, 그 핵심 아이디어는 Spring의 prototype 스코프처럼 현대 프레임워크에도 그대로 녹아 있습니다. 이 패턴을 도입할지 판단할 때는 단순히 "새 객체가 필요한가"가 아니라 "그 객체의 초기화 비용이 실제로 병목인가"를 먼저 확인하는 것이 중요하며, 그렇지 않다면 오히려 복사 생성자 같은 더 단순한 대안을 우선 고려하는 것이 실무적으로 합리적입니다.

## 꼬리질문

1. **직렬화(Serialization) 기반 깊은 복사와 clone() 오버라이딩 방식은 성능과 안전성 측면에서 어떤 트레이드오프가 있는가?**
   - 추천 참고 URL: https://docs.oracle.com/javase/8/docs/api/java/lang/Object.html
2. **Spring의 prototype 스코프 빈이 singleton 빈 내부에 주입될 때 발생하는 스코프 불일치 문제는 어떻게 해결하는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)