---
id: "7904583536125221669"
title: "[GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시"
slug: "gof-4-builder-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-4-builder-pattern-java.html"
publishedAt: "2026-08-14T11:27:17.829-07:00"
updatedAt: "2026-08-14T11:27:17.829-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 4. 빌더 패턴 (Builder Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **생성 패턴 (Creational)**

    
# 4. 빌더 패턴 (Builder Pattern)

  

  
## 1. 패턴 핵심 정의

  
복잡한 객체의 생성 과정과 표현 방법을 분리하여 동일한 생성 절차에서 서로 다른 표현 결과를 만들 수 있게 하는 패턴입니다.

  
## 2. Java 실전 구현 코드 예시

  
`public class User {
    private final String name;
    private final int age;

    private User(Builder builder) {
        this.name = builder.name;
        this.age = builder.age;
    }

    public static class Builder {
        private String name;
        private int age;

        public Builder name(String name) { this.name = name; return this; }
        public Builder age(int age) { this.age = age; return this; }
        public User build() { return new User(this); }
    }
}`

  

  
    📌 GoF 14대 디자인 패턴 전체 목차 보기

    
[[GoF 14대 디자인 패턴 실전 종합 인덱스 포스트 바로가기]](https://beji-tech.blogspot.com/2026/08/gof-14.html)
