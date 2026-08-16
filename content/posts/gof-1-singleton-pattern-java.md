---
id: "69223418079411748"
title: "[GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시"
slug: "gof-1-singleton-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-1-singleton-pattern-java.html"
publishedAt: "2026-08-14T11:27:13.150-07:00"
updatedAt: "2026-08-14T11:27:13.150-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **생성 패턴 (Creational)**

    
# 1. 싱글톤 패턴 (Singleton Pattern)

  

  
## 1. 패턴 핵심 정의

  
클래스의 인스턴스가 오직 1개만 생성되도록 보장하고 시스템 어디서든 동일 인스턴스에 접근하도록 제어하는 패턴입니다.

  
## 2. Java 실전 구현 코드 예시

  
`public class Singleton {
    // volatile 키워드로 메모리 가시성 보장
    private static volatile Singleton instance;

    private Singleton() {
        // 생성자 외부 호출 방지
    }

    // Double-Checked Locking (DCL) 방식
    public static Singleton getInstance() {
        if (instance == null) {
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}`

  

  
    📌 GoF 14대 디자인 패턴 전체 목차 보기

    
[[GoF 14대 디자인 패턴 실전 종합 인덱스 포스트 바로가기]](https://beji-tech.blogspot.com/2026/08/gof-14.html)
