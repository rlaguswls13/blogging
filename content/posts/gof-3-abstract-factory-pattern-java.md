---
id: "4830808000976056585"
title: "[GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시"
slug: "gof-3-abstract-factory-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-3-abstract-factory-pattern-java.html"
publishedAt: "2026-08-14T11:27:16.305-07:00"
updatedAt: "2026-08-14T11:27:16.305-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 3. 추상 팩토리 패턴 (Abstract Factory Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **생성 패턴 (Creational)**

    
# 3. 추상 팩토리 패턴 (Abstract Factory Pattern)

  

  
## 1. 패턴 핵심 정의

  
구체적인 클래스를 지정하지 않고 연관된 객체들의 군(Family)을 생성하기 위한 인터페이스를 제공하는 패턴입니다.

  
## 2. Java 실전 구현 코드 예시

  
`interface Button { void render(); }
interface Checkbox { void render(); }

interface GUIFactory {
    Button createButton();
    Checkbox createCheckbox();
}

class WindowsFactory implements GUIFactory {
    public Button createButton() { return () -> System.out.println("Win Button"); }
    public Checkbox createCheckbox() { return () -> System.out.println("Win Checkbox"); }
}`

  

  
    📌 GoF 14대 디자인 패턴 전체 목차 보기

    
[[GoF 14대 디자인 패턴 실전 종합 인덱스 포스트 바로가기]](https://beji-tech.blogspot.com/2026/08/gof-14.html)
