---
id: "5255194139828588121"
title: "[GoF 디자인 패턴] 5. 프로토타입 패턴 (Prototype Pattern) 개념과 Java 실전 예시"
slug: "gof-5-prototype-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-5-prototype-pattern-java.html"
publishedAt: "2026-08-14T11:27:19.308-07:00"
updatedAt: "2026-08-14T12:02:34.274-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 5. 프로토타입 패턴 (Prototype Pattern) 개념과 Java 실전 예시

## 1. 배경 및 문제점

  
객체를 새로 생성하는 DB 조회나 네트워크 IO 연산 비용이 너무 커서, 매번 `new` 키워드로 생성하면 애플리케이션의 성능이 급격히 저하됩니다.

  
## 2. 해결책 및 동작 메커니즘

  
이미 존재하는 무거운 객체를 복사(Clone)하여 새로운 객체를 생성함으로써 생성 비용과 시간을 최소화합니다.

  
    
      
#### 📱 실제 서비스 동작 예시: 문서 서식 템플릿 복사 (Clone)

      
'여행 리뷰 템플릿' 선택 시 처음부터 레이아웃을 다시 그리지 않고 기존에 로드된 원본 템플릿을 복사해와서 글자만 고쳐서 포스팅

    

    
      
#### 📄 비유: 100페이지 계약서 서류 복사기 (Clone)

      
100페이지짜리 계약서를 처음부터 일일이 새로 타이핑하는 대신, 기존 원본을 복사기로 1초 만에 복제한 뒤 이름과 날짜만 고쳐 씁니다.

    
  

  
## 3. 실무 주의점

  
    

      얕은 복사(Shallow) vs 깊은 복사(Deep) 함정: `Object.clone()`은 기본적으로 얕은 복사를 수행하므로 참조 객체(List 등)가 공유되는 버그가 발생합니다. 깊은 복사를 직접 구현해야 독립성을 보장합니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`package com.gof.prototype;

import java.util.ArrayList;
import java.util.List;

// Cloneable 인터페이스 구현
class DocumentTemplate implements Cloneable {
    private String title;
    private String format;
    private List placeholders; // 참조 타입 필드

    public DocumentTemplate(String title, String format) {
        System.out.println("⏳ DB에서 템플릿 정보를 읽어와 무거운 초기화를 진행합니다... [" + title + "]");
        try { Thread.sleep(1000); } catch (InterruptedException e) {} // 무거운 작업 시뮬레이션
        
        this.title = title;
        this.format = format;
        this.placeholders = new ArrayList<>();
        this.placeholders.add("NAME");
        this.placeholders.add("DATE");
    }

    public void setTitle(String title) { this.title = title; }
    public void addPlaceholder(String placeholder) { this.placeholders.add(placeholder); }
    
    public void printDocument() {
        System.out.println("📄 문서 제목: " + title + " | 형식: " + format + " | 서명란: " + placeholders);
    }

    // ⭐ 핵심: 깊은 복사(Deep Copy)를 지원하는 clone() 오버라이딩
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
        
        System.out.println("\n=== 2. 프로토타입 복제 (즉시 생성) ===");
        // 2. 복제를 통한 객체 생성 (즉시 완료됨)
        DocumentTemplate copyContract1 = originalContract.clone();
        copyContract1.setTitle("홍길동 근로 계약서");
        copyContract1.addPlaceholder("SIGNATURE"); // 복사본 1에만 항목 추가

        DocumentTemplate copyContract2 = originalContract.clone();
        copyContract2.setTitle("이순신 근로 계약서");

        // 3. 깊은 복사 확인
        System.out.println("\n=== 3. 독립성 검증 (깊은 복사) ===");
        originalContract.printDocument(); // 원본에는 SIGNATURE가 없어야 정상
        copyContract1.printDocument();    // 복사본 1에는 SIGNATURE가 있어야 정상
        copyContract2.printDocument();    // 복사본 2에는 원본과 같아야 정상
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 1. 원본 객체 생성 ===
⏳ DB에서 템플릿 정보를 읽어와 무거운 초기화를 진행합니다... [표준 근로 계약서]
📄 문서 제목: 표준 근로 계약서 | 형식: PDF | 서명란: [NAME, DATE]

=== 2. 프로토타입 복제 (즉시 생성) ===

=== 3. 독립성 검증 (깊은 복사) ===
📄 문서 제목: 표준 근로 계약서 | 형식: PDF | 서명란: [NAME, DATE]
📄 문서 제목: 홍길동 근로 계약서 | 형식: PDF | 서명란: [NAME, DATE, SIGNATURE]
📄 문서 제목: 이순신 근로 계약서 | 형식: PDF | 서명란: [NAME, DATE]
*/`

  
## 5. 실무 프레임워크 적용 사례

  
    🌱 Spring Framework Prototype Scope Bean, Java `Object.clone()`, `Cloneable` 인터페이스
  

  
## 6. 참고자료

  
    
- Inpa Dev Blog - GoF 디자인 패턴 제대로 배워보자 시리즈
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru Design Patterns Catalog
