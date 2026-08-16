---
id: "2849321457966386896"
title: "[GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시"
slug: "gof-8-proxy-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-8-proxy-pattern-java.html"
publishedAt: "2026-08-14T11:27:58.000-07:00"
updatedAt: "2026-08-15T16:19:02.691-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴
    구조 패턴 (Structural Patterns) 시리즈 #8
  

  
## 1. 배경 및 문제점 (Problem & Motivation)

  
객체 생성 비용이 매우 크거나, 객체에 대한 접근 제어(보안), 로깅, Caching이 필요한 경우 클라이언트가 직접 원본 객체를 호출하면 다양한 문제점이 발생합니다.

  
    
- **불필요한 리소스 남용:** 실제로 사용되지도 않을 무거운 객체를 초기화 시점에 미리 로딩하��� 초기 응답 속도가 현저히 떨어집니다.
    
- **비즈니스 로직의 오염:** 원본 서비스 코드 안에 보안 검사, 트랜잭션, 캐시 확인 로직이 지저분하게 섞여 관리가 불가능해집니다.
  

  
## 2. 해결책 및 동작 메커니즘 (Solution & How It Works)

  
**프록시 패턴(Proxy Pattern)**은 진짜 객체(Real Subject)와 동일한 인터페이스를 구현하는 대리자(Proxy) 객체를 중간에 배치합니다.

  
클라���언트는 프록시를 통해 요청을 전달하며, 프록시는 요청을 대신 받아 지연 로딩(Lazy Loading), 접근 제어, Caching 등의 부가 작업을 처리한 뒤 필요 시에만 진짜 객체를 호출합니다.

  
  
    
      
#### 📱 실제 서비스 동작 예시: 넷*릭스(Netflix) 썸네일 지연 로딩

      
1,000개 영화 고화질 영상 데이터를 한 번에 다운로드하지 않고, 프록시가 가벼운 이미지 썸네일만 보여주다가 사용자가 마우스를 올리는 순간에만 진짜 영상(Real Subject)을 뒤늦게 지연 로딩합니다.

      
      
🔄 **Working Flow:** 화면 진입 ➔ Proxy가 가벼운 썸네일 렌더링 ➔ 마우스 호버 ➔ RealVideo 로딩 및 재생

    

    
      
#### 🕴️ 비유: 연예인/CEO의 업무를 전담하는 비서 및 매니저

      
팬들이 연예인 본인에게 직접 다짜고짜 전화할 수 없듯이, 매니저가 중간에서 불필요한 스케줄 전화를 걸러내고(보안/캐싱) 꼭 필요한 순간에만 연예인 본인에게 연결합니다.

      
      
🎯 **필요 이유:** 핵심 비즈니스 로직과 부가 로직(보안/지연로딩/캐싱)의 완벽 분리

    
  

  
## 3. 프록시 패턴의 실무 주의점 및 트레이드오프

  
    

      ⚠️ **Spring AOP 프록시 내부 호출(Self-Invocation) 함정:**
      Spring의 `@Transactional`이나 `@Cacheable`은 CGLIB Dynamic Proxy 기반으로 작동합니다. 따라서 같은 클래스 내부에서 `this.method()` 형태로 직접 호출하면 프록시를 타지 않아 트랜잭션 및 캐시 기능이 통째로 무력화됩니다!
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`// 1. 공통 인터페이스 (Subject)
interface Video {
    void play();
}

// 2. 진짜 객체 (Real Subject) - 생성이 매우 무거운 객체
class RealVideo implements Video {
    private final String fileName;

    public RealVideo(String fileName) {
        this.fileName = fileName;
        loadFromDisk(); // 고용량 디스크 로딩 시뮬레이션
    }

    private void loadFromDisk() {
        System.out.println("💾 [디스크 로딩] 고화질 영상 파일 " + fileName + " 읽는 중... (대용량 메모리 소모)");
    }

    @Override
    public void play() {
        System.out.println("▶️ [영상 재생] " + fileName + " 스트리밍을 시작합니다.");
    }
}

// 3. 프록시 객체 (Proxy) - 지연 로딩 & 접근 제어 대리자
class ProxyVideo implements Video {
    private final String fileName;
    private final String userRole;
    private RealVideo realVideo; // 지연 로딩을 위한 참조

    public ProxyVideo(String fileName, String userRole) {
        this.fileName = fileName;
        this.userRole = userRole;
    }

    @Override
    public void play() {
        // 권한 검사 (보호 프록시 역할)
        if (!"VIP".equals(userRole) && !"ADMIN".equals(userRole)) {
            System.out.println("🔒 [접근 거부] " + fileName + " 은 VIP 전용 영상입니다. (현재 권한: " + userRole + ")");
            return;
        }

        // 지연 로딩 (가상 프록시 역할)
        if (realVideo == null) {
            System.out.println("⚡ [프록시] 최초 요청 감지! 진짜 객체를 지연 로딩(Lazy Loading)합니다.");
            realVideo = new RealVideo(fileName);
        } else {
            System.out.println("🚀 [프록시] 이미 ��딩된 진짜 객체(RealSubject)를 재사용합니다.");
        }

        realVideo.play();
    }
}

// 4. 실행 테스트 (Main)
public class ProxyPatternMain {
    public static void main(String[] args) {
        System.out.println("=== 1. 일반 회원 영상 클릭 ===");
        Video freeUserVideo = new ProxyVideo("오징어게임_시즌2_EP01.mp4", "GUEST");
        freeUserVideo.play(); // 접근 거부

        System.out.println("\n=== 2. VIP 회원 최초 클릭 (지연 로딩 발생) ===");
        Video vipUserVideo = new ProxyVideo("오징어게임_시즌2_EP01.mp4", "VIP");
        vipUserVideo.play(); // 최초 로딩 후 재생

        System.out.println("\n=== 3. VIP 회원 두 번째 클릭 (재로딩 없이 재사용) ===");
        vipUserVideo.play(); // 이미 생성된 객체 즉시 재생
    }
}
`

  
#### 💻 실행 결과 (Expected Output)

```

=== 1. 일반 회원 영상 클릭 ===
🔒 [접근 거부] 오징어게임_시즌2_EP01.mp4 은 VIP 전용 영상입니다. (현재 권한: GUEST)

=== 2. VIP 회원 최초 클릭 (지연 로딩 발��) ===
⚡ [프록시] 최초 요청 감지! 진짜 객체를 지연 로딩(Lazy Loading)합니다.
💾 [디스크 로딩] 고화질 영상 파일 오징어게임_시즌2_EP01.mp4 읽는 중... (대용량 메모리 소모)
▶️ [영상 재생] 오징어게임_시즌2_EP01.mp4 스트리밍을 시작합니다.

=== 3. VIP 회원 두 번째 클릭 (재로딩 없이 재사용) ===
🚀 [프록시] 이미 로딩된 진짜 객체(RealSubject)를 재사용합니다.
▶️ [영상 재생] 오징어게임_시즌2_EP01.mp4 스트리밍을 시작합니다.

```

  
## 5. 실무 프레임워크 적용 사례 (Real-World Frameworks)

  
    🌱 **Spring AOP:** `@Transactional`, `@Cacheable` 적용 시 CGLIB/JDK Dynamic Proxy 객체가 자동 생성되어 AOP 부가 기능 전파.
    📦 **Hibernate ORM:** 연관 엔티티 지연 로딩(Lazy Loading) 적용 시 실제 DB 조회 전까지 프록시 엔티티 객�� 유지.
  

  
## 6. 참고자료 (References)

  
    
- Inpa Dev Blog - GoF 프록시(Proxy) 패턴 제대로 배워보자
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru - Proxy Design Pattern
