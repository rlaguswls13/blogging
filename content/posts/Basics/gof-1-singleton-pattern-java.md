---
id: '69223418079411748'
publishedAt: '2026-08-14T11:27:13.150-07:00'
slug: gof-1-singleton-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-14T11:27:13.150-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-1-singleton-pattern-java.html
---

# [GoF 디자인 패턴] 1. 싱글톤 패턴 (Singleton Pattern) 개념과 Java 실전 예시

## 요약

싱글톤 패턴(Singleton Pattern)은 클래스의 인스턴스가 애플리케이션 전체에서 오직 1개만 존재하도록 보장하고, 어디서든 그 하나의 인스턴스에 접근할 수 있는 전역 진입점을 제공하는 생성 패턴입니다. 설정 객체, 커넥션 풀, 로거처럼 여러 개가 생기면 오히려 문제가 되는 자원을 다룰 때 주로 사용합니다. 이 글에서는 왜 이 패턴이 필요한지, 멀티스레드 환경에서 안전하게 구현하는 방법(Double-Checked Locking, `enum` 방식), 그리고 실무에서 자주 지적받는 안티패턴 논쟁까지 다룹니다.

## 본문

### 1. 배경 및 문제점

애플리케이션 설정값을 담는 `AppConfig` 클래스가 있다고 가정해 봅니다. 이 클래스를 여러 곳에서 각자 `new AppConfig()`로 생성하면, 설정 파일을 읽는 무거운 초기화 작업이 호출될 때마다 반복되고, 더 심각하게는 각 인스턴스가 서로 다른 메모리 주소를 가지므로 한쪽에서 설정값을 변경해도 다른 쪽에는 반영되지 않는 데이터 불일치 문제가 생깁니다. 커넥션 풀이나 스레드 풀처럼 시스템 자원을 관리하는 객체가 여러 개 생기면 자원 고갈이나 동시성 충돌로 이어질 수도 있습니다.

### 2. 패턴 정의 및 동작 메커니즘

싱글톤 패턴은 클래스 스스로가 자신의 인스턴스 생성을 통제하도록 만듭니다. 생성자를 `private`으로 막아 외부에서 `new`를 직접 호출하지 못하게 하고, 클래스 내부에 자기 자신의 유일한 인스턴스를 `static` 필드로 보관한 뒤, `getInstance()`라는 정적 메서드를 통해서만 그 인스턴스에 접근하도록 합니다. 최초 호출 시에만 인스턴스를 생성하고, 이후 호출부터는 이미 만들어진 인스턴스를 재사용합니다.

### 3. 실제 서비스 적용 예시

로그를 기록하는 `Logger` 객체를 떠올려 보면 이해가 쉽습니다. 여러 모듈이 각자 `Logger` 인스턴스를 따로 만들면 로그 파일 쓰기 작업이 충돌하거나 순서가 뒤섞일 수 있습니다. 싱글톤으로 만든 `Logger`는 애플리케이션 전체가 동일한 파일 핸들과 버퍼를 공유하므로, 로그 순서와 파일 쓰기 락(lock) 관리가 한 곳에서 일관되게 이루어집니다. 데이터베이스 커넥션 풀(`HikariCP`의 `DataSource` 등)도 마찬가지로, 풀 자체가 여러 개 생기면 실제 DB 커넥션 개수를 예측·제어할 수 없게 되므로 애플리케이션당 하나만 유지하는 것이 일반적입니다.

### 4. Java 실전 구현 코드

멀티스레드 환경에서 안전하게 동작하는 싱글톤은 생각보다 구현이 까다롭습니다. 가장 널리 쓰이는 방식은 `volatile` 키워드와 이중 검사 잠금(Double-Checked Locking, DCL)을 결합한 형태입니다.

```java
public class Singleton {
    // volatile: 여러 스레드가 이 필드를 동시에 볼 때 최신 값을 보장(메모리 가시성)
    private static volatile Singleton instance;

    private Singleton() {
        // 생성자를 private으로 막아 외부의 직접 인스턴스화를 차단
    }

    public static Singleton getInstance() {
        if (instance == null) {                 // 1차 검사: 락 없이 빠르게 확인
            synchronized (Singleton.class) {
                if (instance == null) {          // 2차 검사: 락을 잡은 상태에서 재확인
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

더 안전하고 간결한 대안으로 자바의 `enum`을 활용하는 방식도 널리 권장됩니다. `enum` 값은 JVM이 클래스 로딩 시점에 단 한 번만, 스레드 안전하게 생성하는 것을 언어 차원에서 보장하기 때문입니다.

```java
public enum SingletonEnum {
    INSTANCE;

    public void doSomething() {
        System.out.println("싱글톤 enum 인스턴스에서 작업 수행");
    }
}

// 사용: SingletonEnum.INSTANCE.doSomething();
```

### 5. 실무 주의점 및 트레이드오프

싱글톤은 전역 상태(Global State)를 만들기 때문에 단위 테스트에서 상태가 테스트 케이스 간에 공유되어 테스트 순서에 따라 결과가 달라지는 부작용을 유발하기 쉽습니다. 또한 클래스 간의 의존 관계가 코드 어디에서나 `getInstance()`로 숨겨져 버려서, 의존성 주입(DI) 방식보다 결합도 파악이 어려워진다는 비판을 받습니다. 리플렉션(Reflection)이나 직렬화(Serialization)를 이용하면 `private` 생성자를 우회해 인스턴스를 추가로 만들어낼 수 있다는 보안적 허점도 있어, 엄격하게 막으려면 `enum` 방식이나 `readResolve()` 구현이 필요합니다.

### 6. 실무 프레임워크 적용 사례

Spring Framework는 `@Component`나 `@Bean`으로 등록한 빈(Bean)을 기본적으로 싱글톤 스코프로 관리합니다. 다만 이는 GoF의 순수 싱글톤 패턴과는 구현 방식이 다릅니다 — 클래스 자신이 `private` 생성자로 인스턴스 생성을 통제하는 것이 아니라, Spring의 `ApplicationContext`라는 컨테이너가 빈 하나당 인스턴스 하나만 만들어 관리하는 "컨테이너 관리형 싱글톤"입니다. 자바 표준 라이브러리에서는 `Runtime.getRuntime()`이 JVM 런타임 정보를 담은 유일한 `Runtime` 인스턴스를 반환하는 대표적인 싱글톤 사례입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 싱글톤 패턴은 클래스의 인스턴스를 하나로 제한하고 전역 접근점을 제공하는 생성 패턴이다 | verified | Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software* (1994) |
| CLAIM-002: `enum` 기반 싱글톤은 JVM이 클래스 로딩 시점에 스레드 안전하게 인스턴스를 생성함을 언어 차원에서 보장한다 | verified | Java Language Specification, enum 타입의 인스턴스 생성 규칙 |
| CLAIM-003: 리플렉션은 `private` 생성자의 접근 제어를 우회해 추가 인스턴스를 생성할 수 있다 | verified | `java.lang.reflect.Constructor.setAccessible()` 동작 원리(Java 공식 문서) |
| CLAIM-004: Spring의 기본 빈 스코프는 싱글톤이며, 이는 컨테이너가 관리하는 방식으로 GoF 원 패턴과 구현 메커니즘이 다르다 | verified | Spring Framework Reference Documentation, Bean Scopes |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 싱글톤을 직접 구현할 일은 생각보다 많지 않습니다. Spring 같은 DI 프레임워크를 쓰는 프로젝트에서는 빈 스코프 설정만으로 사실상 싱글톤의 이점을 얻을 수 있기 때문에, GoF 원형 그대로의 `getInstance()` 패턴을 새로 작성해야 하는 상황은 프레임워크 바깥의 유틸리티 클래스나 순수 자바 라이브러리를 만들 때 정도로 한정된다고 생각합니다. 다만 "테스트하기 어렵다"는 비판만으로 싱글톤 자체를 무조건 피해야 한다고 보지는 않습니다. 전역적으로 유일해야만 하는 자원(예: 하드웨어 드라이버 핸들, 락 매니저)이라면 싱글톤이 오히려 가장 정직한 표현이며, 문제는 패턴 자체가 아니라 무분별하게 아무 클래스나 싱글톤으로 만들어 전역 변수처럼 남용하는 습관에 있다고 봅니다.

## 한계와 반론

**한계점**: 싱글톤은 클래스 간 의존성을 코드 표면에 드러내지 않고 숨기기 때문에, 특정 클래스가 어떤 싱글톤에 의존하는지 시그니처만 보고는 알 수 없습니다. 이는 대규모 코드베이스에서 영향 범위 파악을 어렵게 만듭니다.

**반론**: 의존성 주입(Dependency Injection)을 적극적으로 사용하면 이 한계를 상당 부분 해소할 수 있습니다. 싱글톤 인스턴스를 직접 `getInstance()`로 호출하는 대신, 생성자나 필드 주입으로 명시적으로 전달받도록 설계하면 코드만 보고도 의존 관계를 파악할 수 있고, 테스트 시에는 목(Mock) 객체로 손쉽게 대체할 수 있습니다. Spring 컨테이너가 관리하는 싱글톤 빈이 바로 이 절충안에 해당합니다.

## 참고문헌

1. Oracle, "Enum Types (The Java Tutorials)", [https://docs.oracle.com/javase/tutorial/java/javaOO/enum.html](https://docs.oracle.com/javase/tutorial/java/javaOO/enum.html) (확인일: 2026-08-17)
2. Spring Framework Reference Documentation, "Bean Scopes", [https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html](https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html) (확인일: 2026-08-17)
3. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

싱글톤 패턴은 GoF 23개 패턴 중 가장 단순해 보이지만, 멀티스레드 환경에서 올바르게 구현하려면 메모리 가시성과 초기화 순서까지 신경 써야 하는 만만치 않은 패턴입니다. 순수한 형태의 `getInstance()` 싱글톤은 오늘날 DI 프레임워크의 컨테이너 관리형 싱글톤 스코프로 대체되는 추세이지만, 패턴이 해결하려는 근본 문제 — "이 자원은 애플리케이션 전체에서 유일해야 한다" — 는 여전히 유효합니다. 새 코드를 작성할 때는 직접 `getInstance()`를 구현하기보다, 가능하면 프레임워크의 싱글톤 스코프 기능을 활용해 테스트 용이성과 결합도 문제를 함께 해결하는 편을 권장합니다.

## 꼬리질문

1. **`enum` 싱글톤과 DCL 기반 싱글톤 중 어느 쪽이 클래스 로딩 시점(Lazy vs Eager)과 성능 측면에서 더 유리한가?**
   - 추천 참고 URL: [https://docs.oracle.com/javase/tutorial/java/javaOO/enum.html](https://docs.oracle.com/javase/tutorial/java/javaOO/enum.html)
2. **Spring 빈 스코프를 `singleton`에서 `prototype`으로 바꿨을 때 실제로 어떤 생명주기 차이가 발생하는가?**
   - 추천 참고 URL: [https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html](https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html)

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)