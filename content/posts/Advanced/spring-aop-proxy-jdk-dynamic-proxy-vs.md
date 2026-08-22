---
id: '8854084684219861285'
publishedAt: '2026-08-14T10:25:20.752-07:00'
slug: spring-aop-proxy-jdk-dynamic-proxy-vs
status: published
tags:
- AspectJ
- CGLIB
- JDK Dynamic Proxy
- Proxy Pattern
- Spring AOP
- Spring Boot
- Advanced
title: 'Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석'
updatedAt: '2026-08-14T10:25:20.752-07:00'
url: https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html
---

# Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석

## 요약

엔터프라이즈 자바 개발에서 트랜잭션 처리(`@Transactional`), 보안 인가, 성능 로깅 등 핵심 로직 도처에 스며드는 공통 부가 기능을 비즈니스 비즈니스 코드로부터 분리해 내는 패러다임이 **'AOP(Aspect-Oriented Programming)'**입니다. Spring AOP는 컴파일러나 클래스로더를 직접 변조하는 대신, 데코레이터 패턴 형식으로 타겟을 제어하는 **'런타임 프록시(Proxy)'** 방식으로 구현되었습니다. 본 아티클에서는 AOP의 핵심 개념을 도식화하고, 자바 네이티브 동적 리플렉션을 응용하는 JDK Dynamic Proxy와 바이트코드를 조작하는 CGLIB Proxy 기술의 아키텍처적 구동 차이를 정밀 분석합니다. 아울러 스프링 부트에서 CGLIB를 기본 프록시 도구로 채택한 사유와 프록시 내부 호출(Self-Invocation)의 기술적 한계 및 해법을 도출합니다.

## 본문

### 1. 서론: OOP의 한계를 극복하는 AOP와 프록시 패턴의 관계

객체지향 프로그래밍(OOP)은 책임을 기준으로 모듈화하여 비즈니스를 유연하게 풀어가지만, 여러 클래스에 걸쳐 중복되어 구현되는 공통 관심 사항(Cross-cutting Concerns)에 대해서는 중복 코드가 양산되는 한계를 겪습니다 (예: 계좌 이체 로직 전후에 트랜잭션 시작과 커밋/롤백 코드, 시간 측정 로깅 코드가 삽입되어 본질을 오염시키는 현상). **AOP(관점 지향 프로그래밍)**는 이러한 흩어진 관심사들을 하나의 **'Aspect'**로 묶어 독립적으로 캡슐화하는 설계 도구입니다 [1], [3], [5].

- AOP는 핵심 도메인 비즈니스 연산에서 공통 관심사(횡단 관심사)를 선언적으로 격리 추출하여 모듈화하는 프로그래밍 패러다임이며, 코드 중복을 제거하고 단일 책임 원칙(SRP)을 완성시킨다 [1], [3].

#### 프록시 패턴 (Proxy Pattern):

Spring AOP는 대다수 다른 AOP 프레임워크처럼 복잡하고 이식성이 까다로운 바이트코드 로더 변조(AspectJ LTW 등) 대신, 가볍고 범용성이 보장되는 **런타임 디자인 패턴인 프록시**를 응용합니다.

- **프록시의 역할**: 클라이언트와 원본 타겟 객체(Target Object) 사이에 프록시(대리인) 객체를 중간에 끼워 넣습니다. 클라이언트가 타겟의 메서드를 부르면, 대리인인 프록시가 먼저 요청을 가로채서(Intercept) 공통 작업(예: `@Transactional`이 있으면 트랜잭션 시작)을 수행한 뒤 실제 원본 객체의 비즈니스를 위임 호출하고, 작업이 끝나면 최종 트랜잭션을 닫는(Commit) 구조입니다.

- Spring AOP는 컴파일이나 클래스로딩 변조 없이 타겟 빈을 가리키는 프록시 래퍼를 빈 컨테이너에 자동 등록해 주어, 런타임에 다형성 및 메서드 위임 구조를 통과하여 측면 공통 동작을 원활히 삽입한다 [3], [5].

### 2. JDK Dynamic Proxy vs CGLIB: 프록시 생성 기법 비교

스프링 프레임워크는 타겟 클래스의 형태와 구성 스펙에 맞춰 프록시 객체를 동적으로 생성하기 위해 두 종류의 핵심 프록시 엔진을 사용합니다 [3], [4].

![JDK Dynamic Proxy와 CGLIB Proxy 아키텍처 비교](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/spring_aop_proxy_1786728240130.jpg)

#### A. JDK Dynamic Proxy (인터페이스 기반 동적 프록시)

자바 표준 라이브러리(Java Reflection API)가 제공하는 네이티브 동적 프록시 메커니즘입니다 [3].

- **작동 제약**: 타겟 클래스가 **반드시 1개 이상의 인터페이스(Interface)를 구현**하고 있어야 프록시 생성이 가능합니다.

- **동작 방식**: `java.lang.reflect.Proxy` 클래스를 사용하며, 생성된 프록시 클래스는 타겟 클래스와 동등한 형제 관계로서 인터페이스를 공유합니다. 메서드가 호출되면 내부의 **`InvocationHandler`** 인터페이스의 `invoke()` 메서드가 리플렉션을 통해 동적으로 타겟의 실제 코드를 가로채어 실행시킵니다 [3], [4].

- JDK Dynamic Proxy 기술은 자바 리플렉션을 통해 런타임에 주어지는 인터페이스 정보를 활용하여 동적 프록시 객체를 빌드하므로, 구현체 인터페이스가 전무한 구체 클래스 단독형 빈(Concrete Bean)에는 적용할 수 없다 [3], [4].

#### B. CGLIB Proxy (클래스 상속 기반 프록시)

CGLIB(Code Generation Library)는 오픈 소스 기반 바이트코드 조작 라이브러리(ASM)를 내장하여 구동되는 프록시 엔진입니다 [3], [4].

- **작동 제약**: 타겟 클래스가 **인터페이스가 없는 일반 구체 클래스**이더라도 프록시 생성을 온전히 지원합니다.

- **동작 방식**: 타겟 클래스를 상속받는 하위 클래스(Subclass)의 바이트코드를 런타임에 직접 동적 생성해 냅니다. 프록시 객체는 타겟의 자식 객체(Child)로 매핑되며, 호출이 발생하면 바이트코드 단에서 꽂히는 **`MethodInterceptor`**가 부모의 원래 메서드를 재정의(Override)하는 구조로 가로채어 처리합니다 [3], [4].

- CGLIB 프록시는 타겟 구체 클래스를 직접 상속(Extends)하는 동적 서브클래스를 즉석에서 코딩(바이트코드 조작)하여 락을 우회하기 때문에, 상속을 허용하지 않는 `final` 클래스나 `final` 메서드에는 AOP가 적용되지 않는 한계를 지닌다 [3], [4].

### 3. 스프링 부트(Spring Boot)에서 CGLIB를 전면 기본값으로 채택한 사유

초기 Spring Legacy 시절에는 인터페이스가 있으면 JDK Dynamic Proxy, 없으면 CGLIB를 동적으로 조합해 썼으나, **Spring Boot 2.x 버전부터는 인터페이스 존재 여부에 무관하게 CGLIB 프록시 생성을 기본값(Default)으로 하이재킹**했습니다 [5]. 과거 CGLIB는 몇 가지 크리티컬한 기술적 불안요소를 안고 있었으나, 스프링 팀이 버전업을 거듭하며 CGLIB 자체를 프레임워크 패키지 내부로 섀도잉하고 아래의 문제를 차례로 극복해 냈기 때문입니다 [4], [5].

- **기본 생성자 강제 호출 문제 해결**: CGLIB는 부모 클래스(타겟)를 상속하므로 자바 규칙상 부모의 기본 생성자를 한 번 더 호출해야 했습니다. 스프링은 **`Objenesis`** 라이브러리를 동합 결합하여 생성자를 통하지 않고도 바이트코드 조작을 통해 인스턴스를 즉각 복제 및 생성해내어 이 문제를 완벽하게 회피했습니다.

- **생성자 두 번 실행 성능 손실 극복**: Objenesis 덕분에 생성자가 1회만 호출되어 성능 병목이 완전히 사라졌습니다.

- **인터페이스 캐스팅(Casting) 오류 완전 해결**: JDK Dynamic Proxy는 인터페이스 공유 형제이므로 빈을 구현 클래스 타입(`MyServiceImpl`)으로 다이렉트 자동 주입(`@Autowired`) 받으려 하면 타입 캐스팅 에러(ClassCastException)를 터트리는 최악의 약점이 있었습니다. 반면 CGLIB는 부모-자식 관계이므로 자식 타입인 구체 클래스로 안전하게 대입 주입이 가능합니다.

- 스프링 부트는 Objenesis 도입을 통해 CGLIB의 시그니처 한계인 부모 생성자 중복 실행 부작용을 극복했으며, 구현 인터페이스 캐스팅 예외 안전성을 확보하기 위해 CGLIB를 디폴트 프록시 엔진으로 일원화했다 [4], [5].

### 4. 프록시 아키텍처의 한계와 실무 극복: 내부 호출(Self-Invocation) 문제

Spring AOP의 프록시 방식은 런타임에 다형성 대리 객체를 태우는 극도로 가벼운 구조를 취했지만, **'자가 호출(Self-Invocation)'**이라는 결정적 구조적 취약점을 지닙니다 [3], [5].

#### 내부 호출 문제 상황:

같은 클래스 내의 일반 메서드 `A()`가 같은 클래스 내의 다른 `@Transactional`이 달린 메서드 `B()`를 다이렉트로 호출할 때 발생합니다.

- **현상**: 트랜잭션이 전혀 동작하지 않습니다.

- **원인**: AOP 가로채기는 클라이언트가 프록시 객체의 메서드를 외부에서 호출해 올 때만 유효합니다. 프록시를 통해 이미 한 번 진입된 원본 타겟 내부에서는 자바의 `this` 지시자가 프록시 객체가 아니라 순수 원본 객체의 메모리 영역을 직접 바라보기 때문에, `B()`를 직접 부르면 프록시의 `MethodInterceptor`를 거치지 않고 다이렉트로 원본 코드가 실행되어 AOP 어드바이스가 완전히 우회되는 것입니다.

#### 실무 해결 방안:

- **가장 권장하는 구조적 해결책 (서비스 분리)**: 자가 호출이 일어나는 핵심 비즈니스 클래스를 별도의 컴포넌트(`Dependency Service`)로 외부에 분리 선언하고 의존성을 주입받아 호출하여 물리적으로 내부 진입을 통과하게 개조합니다.

- **대안책 (ApplicationContext 직접 조회)**: `ObjectProvider<MyService>`를 활용하여 필요한 시점에 런타임 빈 컨테이너에서 프록시 객체를 지연 룩업하여 동적으로 위임해주는 구조를 취합니다 [3].

- Spring AOP의 자가 호출(Self-Invocation) 누락 버그는 프록시 내부 진입 이후 자바의 static 바인딩 구조상 this 호출이 프록시 프레임을 우회하여 원본 인스턴스를 직진으로 찌르기 때문에 일어나며, 서비스의 격리 설계로 이를 방어해야 한다 [3], [5].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 `@Transactional` 메서드의 오작동이나 롤백 유실 장애의 90% 이상이 바로 이 내부 호출(Self-Invocation) 실수에서 기인한다고 단언합니다. 특히 동일 클래스 안에서 초기 데이터 파싱(Non-transactional) 이후 세부 DB 저장(Transactional) 메서드를 private이나 public으로 한 클래스 내부에서 쪼개 부를 때 가장 흔하게 사고가 터집니다. 초보 개발자들은 `@Transactional`을 붙였으니 롤백이 될 것이라 굳게 믿지만, 실제 프록시의 한계로 인해 무방비로 로우 쿼리가 튀어 나가는 상황을 흔히 목격합니다. 따라서 사전에 트랜잭션의 시작 영역을 진입 메서드 단위로 아예 엄격히 외부에서 끌고 오거나 컴포넌트를 정교하게 찢어 두는 습관이 견고한 비즈니스 신뢰성을 만듭니다.

## 한계와 반론

- **한계점**: Spring AOP는 프록시 기반이므로 `private` 메서드나 동일 객체 내부 호출, 혹은 생성자 내부에서의 특정 로직 가로채기(AspectJ가 지원하는 모든 Joinpoint 영역)를 지원하지 못하는 본질적인 기능적 제약을 갖습니다.

- **반론**: 만약 생성자 호출 시점이나 `private` 메서드, 정적 메서드(`static`)에도 완벽하게 부가 기능(AOP Aspect)을 주입해야 한다면, 무겁긴 하지만 컴파일 시점에 바이트코드를 통째로 다시 빌드하는 AspectJ 컴파일러(AJC)나 로딩 시점에 자바 에이전트를 동반하여 바이트코드를 재구성하는 LTW(Load-Time Weaving) 아키텍처를 결합하면 이 모든 기술적 제약을 완전히 걷어낼 수 있다는 반론도 정당성을 가집니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

Spring AOP는 대리인을 두어 횡단을 통제하는 실용적인 실천을 보편화시켰습니다. JDK Dynamic Proxy의 리플렉션 오버헤드와 인터페이스 강제를 해결하기 위한 CGLIB의 상속 기법 및 Objenesis 바이트코드 제어는 자바가 추구해 온 프레임워크 레벨 기술 진화의 대표적인 기념비입니다. 성능의 격차가 사실상 거의 무너진 현대에는 캐스팅 트러블을 방지하기 위해 CGLIB를 주축으로 삼되, 프록시가 지닌 본질적인 자가 호출 한계를 항상 의식하며 컴포넌트 경계를 아름답게 격리해 나가는 설계 역량이 현대 백엔드 엔지니어에게 강하게 요구됩니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- Gregor Kiczales et al., "Aspect-Oriented Programming", ECOOP 1997.

- Erich Gamma et al., "Design Patterns: Elements of Reusable Object-Oriented Software", Addison-Wesley.

- Spring Framework Reference Documentation, "Aspect Oriented Programming with Spring", [https://docs.spring.org/spring-framework/docs/current/reference/html/core.html#aop](https://docs.spring.org/spring-framework/docs/current/reference/html/core.html#aop)

- CGLIB Project Github Wiki, "Code Generation Library principles and performance metrics", [https://github.com/cglib/cglib/wiki/Architecture](https://github.com/cglib/cglib/wiki/Architecture)

- Spring Boot Reference Guide, "AOP Auto-configuration properties and CGLIB default strategies", [https://docs.spring.org/spring-boot/docs/current/reference/html/features.html#features.aop](https://docs.spring.org/spring-boot/docs/current/reference/html/features.html#features.aop)

## 백링크

- [[GoF 디자인 패턴] 8. 프록시 패턴 (Proxy Pattern) 개념과 Java 실전 예시](https://beji-tech.blogspot.com/2026/08/gof-8-proxy-pattern-java.html)
- [4대 메시징 미들웨어 비교분석: ActiveMQ, Kafka, RabbitMQ, Redis의 아키텍처적 장단점과 솔루션 선택 가이드](https://beji-tech.blogspot.com/2026/08/4-activemq-kafka-rabbitmq-redis.html)
- [MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리](https://beji-tech.blogspot.com/2026/08/mvc-mvc-msa.html)