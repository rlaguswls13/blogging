---
id: '2849321457966386896'
publishedAt: '2026-08-14T11:27:58.000-07:00'
slug: gof-8-proxy-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
- GoF_Series
title: '[GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:19:02.691-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-8-proxy-pattern-java.html
---

# [GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시

## 요약

프록시 패턴(Proxy Pattern)은 진짜 객체(Real Subject)와 동일한 인터페이스를 구현하는 대리자(Proxy) 객체를 클라이언트와 원본 객체 사이에 배치하는 구조 패턴입니다. 객체 생성 비용이 크거나, 접근 제어·로깅·캐싱 같은 부가 기능이 필요할 때 원본 코드를 건드리지 않고 이 부가 기능을 프록시에 위임할 수 있습니다. 이 글에서는 지연 로딩(Lazy Loading)과 접근 제어를 모두 수행하는 실전 Java 예제와, Spring AOP·Hibernate ORM에서 프록시 패턴이 실제로 어떻게 쓰이는지, 그리고 실무에서 자주 걸리는 Self-Invocation 함정까지 다룹니다.

## 본문

### 1. 배경 및 문제점

객체 생성 비용이 매우 크거나, 객체에 대한 접근 제어(보안), 로깅, 캐싱이 필요한 경우 클라이언트가 원본 객체를 직접 호출하면 다음과 같은 문제가 발생합니다.

- **불필요한 리소스 남용**: 실제로 사용되지도 않을 무거운 객체를 초기화 시점에 미리 로딩하면 초기 응답 속도가 현저히 떨어집니다.
- **비즈니스 로직의 오염**: 원본 서비스 코드 안에 보안 검사, 트랜잭션, 캐시 확인 로직이 뒤섞여 관리가 어려워집니다.

### 2. 해결책 및 동작 메커니즘

프록시 패턴은 진짜 객체(Real Subject)와 동일한 인터페이스를 구현하는 대리자(Proxy) 객체를 중간에 배치합니다. 클라이언트는 프록시를 통해 요청을 전달하며, 프록시는 요청을 대신 받아 지연 로딩(Lazy Loading), 접근 제어, 캐싱 등의 부가 작업을 처리한 뒤 필요할 때만 진짜 객체를 호출합니다.

**실제 서비스 동작 예시**: 대용량 영상 스트리밍 서비스는 1,000개 영화의 고화질 영상 데이터를 한 번에 다운로드하지 않습니다. 프록시가 가벼운 썸네일만 먼저 보여주다가, 사용자가 재생 버튼을 누르는 순간에만 진짜 영상(Real Subject)을 지연 로딩합니다. 동작 흐름은 화면 진입 → 프록시가 가벼운 썸네일 렌더링 → 재생 클릭 → RealVideo 로딩 및 재생 순입니다.

**비유**: 연예인이나 CEO의 업무를 전담하는 매니저를 떠올리면 이해가 쉽습니다. 팬이 연예인 본인에게 직접 전화할 수 없듯, 매니저가 중간에서 불필요한 요청을 걸러내고(보안·캐싱) 꼭 필요한 순간에만 본인에게 연결합니다. 이렇게 하면 핵심 비즈니스 로직과 부가 로직(보안·지연 로딩·캐싱)을 완벽히 분리할 수 있습니다.

### 3. 실무 주의점: Spring AOP Self-Invocation 함정

Spring의 `@Transactional`이나 `@Cacheable`은 CGLIB 동적 프록시 기반으로 작동합니다. 따라서 같은 클래스 내부에서 `this.method()` 형태로 직접 호출하면 프록시를 거치지 않아 트랜잭션과 캐시 기능이 통째로 무력화됩니다. 이 문제는 프록시 패턴의 구조적 한계에서 비롯되며, 원본 객체 내부에서의 자기 호출은 애초에 프록시를 경유하지 않기 때문에 발생합니다. 실무에서는 자가 호출이 필요한 로직을 별도 컴포넌트로 분리하거나, `ApplicationContext`에서 자신의 프록시 빈을 다시 조회하는 방식으로 우회합니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
// 1. 공통 인터페이스 (Subject)
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
        System.out.println("[디스크 로딩] 고화질 영상 파일 " + fileName + " 읽는 중...");
    }

    @Override
    public void play() {
        System.out.println("[영상 재생] " + fileName + " 스트리밍을 시작합니다.");
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
        if (!"VIP".equals(userRole) && !"ADMIN".equals(userRole)) {
            System.out.println("[접근 거부] " + fileName + " 은 VIP 전용 영상입니다. (현재 권한: " + userRole + ")");
            return;
        }

        if (realVideo == null) {
            System.out.println("[프록시] 최초 요청 감지! 진짜 객체를 지연 로딩합니다.");
            realVideo = new RealVideo(fileName);
        } else {
            System.out.println("[프록시] 이미 로딩된 진짜 객체를 재사용합니다.");
        }

        realVideo.play();
    }
}

public class ProxyPatternMain {
    public static void main(String[] args) {
        System.out.println("=== 1. 일반 회원 영상 클릭 ===");
        Video freeUserVideo = new ProxyVideo("sample_ep01.mp4", "GUEST");
        freeUserVideo.play(); // 접근 거부

        System.out.println("=== 2. VIP 회원 최초 클릭 (지연 로딩 발생) ===");
        Video vipUserVideo = new ProxyVideo("sample_ep01.mp4", "VIP");
        vipUserVideo.play(); // 최초 로딩 후 재생

        System.out.println("=== 3. VIP 회원 두 번째 클릭 (재로딩 없이 재사용) ===");
        vipUserVideo.play(); // 이미 생성된 객체 즉시 재생
    }
}
```

실행하면 GUEST 요청은 접근이 거부되고, VIP의 첫 재생 요청에서만 디스크 로딩이 일어나며, 두 번째 재생부터는 이미 생성된 객체를 재사용해 로딩 로그가 다시 출력되지 않는 것을 확인할 수 있습니다.

### 5. 실무 프레임워크 적용 사례

- **Spring AOP**: `@Transactional`, `@Cacheable`을 적용하면 CGLIB 또는 JDK Dynamic Proxy 객체가 자동 생성되어 트랜잭션·캐싱 같은 부가 기능이 전파됩니다.
- **Hibernate ORM**: 연관 엔티티를 지연 로딩(Lazy Loading)으로 설정하면, 실제 DB 조회 전까지 프록시 엔티티 객체가 자리를 대신 지킵니다.
- **JDK 표준 라이브러리**: `java.lang.reflect.Proxy`는 인터페이스 기반 동적 프록시를 런타임에 생성하는 표준 API로, Spring AOP의 JDK Dynamic Proxy 모드가 바로 이 클래스를 사용합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 프록시 패턴은 원본 객체와 동일한 인터페이스를 구현하는 대리자를 통해 접근을 제어한다 | verified | Design Patterns (Gamma et al., 1994) Proxy 챕터 |
| CLAIM-002: 지연 로딩(Lazy Loading)은 프록시 패턴의 대표적인 활용 사례 중 하나다 | verified | Design Patterns (Gamma et al., 1994); Hibernate 공식 문서의 지연 로딩 설명 |
| CLAIM-003: Spring AOP의 `@Transactional`/`@Cacheable`은 CGLIB 또는 JDK Dynamic Proxy 기반으로 동작한다 | verified | Spring Framework 공식 문서 AOP 챕터 |
| CLAIM-004: 같은 클래스 내부에서의 self-invocation(this.method())은 Spring 프록시를 우회해 AOP 어드바이스가 적용되지 않는다 | verified | Spring Framework 공식 문서 AOP 제약사항 설명 |
| CLAIM-005: java.lang.reflect.Proxy는 인터페이스 기반 동적 프록시를 생성하는 JDK 표준 API다 | verified | Oracle Java SE 8 API 문서 (java.lang.reflect.Proxy) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 프록시 패턴을 가장 자주 마주치는 곳은 직접 구현한 프록시 클래스가 아니라 Spring AOP처럼 프레임워크가 대신 만들어주는 프록시입니다. 그래서 오히려 "프록시가 어떻게 동작하는지" 감이 없는 상태로 `@Transactional`을 습관적으로 붙이다가, self-invocation 문제로 트랜잭션이 조용히 무시되는 사고를 자주 목격합니다. 이 글의 예제처럼 프록시를 직접 한 번 구현해 보면, 왜 같은 클래스 내부 호출이 프록시를 타지 않는지 구조적으로 이해가 되고, 이후 Spring 코드를 읽을 때도 "이 메서드 호출이 프록시를 거치는가"를 자연스럽게 따지는 습관이 생깁니다. 개인적으로는 프록시 패턴을 단순 암기가 아니라 이런 자가 호출 예제를 직접 실행해보며 익히는 쪽을 권장합니다.

## 한계와 반론

프록시 패턴은 인터페이스 하나를 두고 대리자를 세우는 구조라 간단해 보이지만, 프록시 체인이 여러 겹 쌓이면(로깅 프록시 → 캐싱 프록시 → 보안 프록시) 실제 호출 스택이 깊어져 디버깅이 어려워질 수 있습니다. 또한 JDK Dynamic Proxy는 인터페이스가 없는 클래스에는 적용할 수 없어 CGLIB 같은 바이트코드 조작 방식이 추가로 필요하며, 이는 대상 클래스가 `final`이면 아예 프록시 생성 자체가 불가능하다는 제약으로 이어집니다. 성능 면에서도 프록시를 한 겹 거칠 때마다 약간의 오버헤드가 발생하므로, 초고빈도 호출 경로에는 신중하게 적용해야 합니다.

## 참고문헌

1. [Proxy pattern - Wikipedia](https://en.wikipedia.org/wiki/Proxy_pattern) (확인일: 2026-08-17)
2. [java.lang.reflect.Proxy - Java SE 8 API Documentation](https://docs.oracle.com/javase/8/docs/api/java/lang/reflect/Proxy.html) (확인일: 2026-08-17)
3. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

프록시 패턴은 "대신 처리해주는 대리인을 세운다"는 단순한 아이디어지만, 그 파급력은 지연 로딩부터 트랜잭션 관리, 원격 프록시, 보안 필터링까지 현대 백엔드 프레임워크 전반에 걸쳐 있습니다. Spring AOP나 Hibernate처럼 프레임워크가 프록시 생성을 자동화해 줄수록, 개발자가 그 이면의 동작 원리를 모른 채 사용하는 경우가 늘어나고 있습니다. 하지만 self-invocation 함정처럼 프록시의 구조적 한계에서 비롯되는 버그는 프록시가 정확히 어떻게 개입하는지 이해하고 있어야만 예방할 수 있습니다. 따라서 프록시 패턴은 단순히 "알아두면 좋은 옛날 패턴"이 아니라, Spring 기반 실무 개발자가 트랜잭션·캐싱 버그를 진단할 때 반드시 되짚어야 할 기초 지식이라고 판단합니다.

## 꼬리질문

1. **CGLIB이 클래스 바이트코드를 런타임에 동적으로 변경할 때, final 클래스나 final 메서드는 왜 프록시 생성 자체가 불가능한가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Proxy_pattern
2. **Self-Invocation 문제를 피하기 위해 자기 자신의 프록시 빈을 `ApplicationContext`에서 다시 조회하는 방식은 왜 안티패턴으로 여겨지는가?**
   - 추천 참고 URL: https://docs.oracle.com/javase/8/docs/api/java/lang/reflect/Proxy.html

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)