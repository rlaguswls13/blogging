---
id: "190544593785401394"
title: "[GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시"
slug: "gof-2-factory-method-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-2-factory-method-pattern-java.html"
publishedAt: "2026-08-14T11:27:14.811-07:00"
updatedAt: "2026-08-14T11:27:14.811-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 2. 팩토리 메서드 패턴 (Factory Method Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **생성 패턴 (Creational)**

    
# 2. 팩토리 메서드 패턴 (Factory Method Pattern)

  

  
## 1. 패턴 핵심 정의

  
객체 생성 인스턴스화 로직을 서브클래스로 위임하여, 부모 클래스는 인스턴스화 시점을 몰라도 상위 구성을 유지할 수 있게 만드는 패턴입니다.

  
## 2. Java 실전 구현 코드 예시

  
`interface Product { void use(); }
class ConcreteProductA implements Product { public void use() { System.out.println("Product A 사용"); } }

abstract class Creator {
    public abstract Product createProduct();
    public void someOperation() {
        Product p = createProduct();
        p.use();
    }
}
class ConcreteCreatorA extends Creator {
    public Product createProduct() { return new ConcreteProductA(); }
}`

  

  
    📌 GoF 14대 디자인 패턴 전체 목차 보기

    
[[GoF 14대 디자인 패턴 실전 종합 인덱스 포스트 바로가기]](https://beji-tech.blogspot.com/2026/08/gof-14.html)
