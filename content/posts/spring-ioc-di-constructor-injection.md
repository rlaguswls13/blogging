---
id: "3618849208375254193"
title: "Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가"
slug: "spring-ioc-di-constructor-injection"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html"
publishedAt: "2026-08-14T10:25:17.442-07:00"
updatedAt: "2026-08-14T10:25:17.442-07:00"
tags: ["Backend Development","Constructor Injection","Dependency Injection","IoC","Java","Spring Framework"]
---

# Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가

## Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의

## 요약

자바 생태계에서 엔터프라이즈급 애플리케이션 개발을 주도하는 Spring Framework의 핵심 철학은 **'IoC(Inversion of Control)'**와 **'DI(Dependency Injection)'**에 있습니다. 객체의 생성과 관리 주권을 프레임워크가 가져감으로써 결합도를 획기적으로 낮추는 구조입니다. 본 아티클에서는 IoC와 DI의 개념을 구조적으로 재정립하고, DI를 수행하는 대표적 방식인 필드 주입, 수정자 주입, 생성자 주입의 작동 원리와 차이점을 조명합니다. 아울러 스프링 팀이 왜 생성자 주입(Constructor Injection)을 공식적으로 최우선 권장하는지 순환 참조 예방, 불변성 보장, 테스트 격리 관점에서 증명합니다.

목차

- [1. 서론: 제어의 역전(IoC)과 의존성 주입(DI)의 구조적 정의](#1-서론-제어의-역전ioc과-의존성-주입di의-구조ᄌ��ᆨ-정의)

- [2. 의존성 주입(DI)의 3가지 주입 방식과 트레이드오프](#2-의존성-주입di의-3가지-주입-방식과-트레이드오프)

- [3. 생성자 주입(Constructor Injection)을 무조건 선택해야 하는 이유](#3-생성자-주입constructor-injection을-무조건-선택해야-하는-이유)

## 본문

### 1. 서론: 제어의 역전(IoC)과 의존성 주입(DI)의 구조적 정의

전통적인 소프트웨어 개발에서는 개발자가 직접 객체를 생성하고 의존성을 결합하는 제어권(Control Flow)을 가졌습니다 (예: `MyService` 내부에서 `MyRepository repo = new MyRepositoryImpl()`로 객체 인스턴스를 직접 생성). 하지만 이는 코드의 결합도를 높여 부품 교체와 단위 테스트를 극히 어렵게 만듭니다. 스프링 프레임워크는 이러한 제어권을 외부 컨테이너로 위임하는 **IoC(제어의 역전)**를 도입했습니다.

- 제어의 역전(IoC)은 소프트웨어의 제어 주권이 개발자의 명령형 코드에서 프레임워크의 라이프사이클 엔진으로 반전되는 패러다임이며, 이를 통해 결합도가 낮은 유연한 소프트웨어 아키텍처가 실현된다.

![Spring IoC 및 DI 아키텍처 다이어그램](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/spring_ioc_di_1786728203178.jpg)

**DI(의존성 주입)**는 이 IoC 철학을 실제로 구현하는 메커니즘입니다.

- **의존 관계**: 한 클래스가 동작하기 위해 다른 클래스의 기능(메서드 등)을 필요로 하는 결합 상태입니다.

- **주입**: 객체가 자신의 의존성을 직�� `new`로 찍어 생성하는 대신, 외부 컨테이너(`ApplicationContext`)가 런타임에 빈(Bean) 인스턴스를 주입해 줍니다. 결과적으로 인터페이스에 의존하는 클라이언트 코드는 실제 구체화 클래스(`Impl`)를 알 필요가 없어 결합성이 비약적으로 낮아집니다.

- 의존성 주입(DI)은 빈 간의 의존 결합을 컨테이너가 런타임에 설정 파일이나 어노테이션 정의를 토대로 동적으로 매핑해 주는 주입 행위이며, OCP(개방-폐쇄 원칙)와 DIP(의존역전 원칙) 설계 원칙을 실현하기 위한 핵심 동력이다.

### 2. 의존성 주입(DI)의 3가지 주입 방식과 트레이드오프

스프링 프레임워크는 크게 세 가지 방식의 의존성 주입 경로를 지원합니다.

#### A. 필드 주입 (Field Injection)

멤버 변수 선언부에 `@Autowired` 어노테이션을 붙여 필드에 직접 주입하는 방식입니다.

- **장점**: 코드가 극도로 짧아지고 눈에 잘 들어옵니다.

- **치명적 단점**: 프레임워크 바깥(예: 스프링 컨테이너 없이 구동되는 순수 자바 단위 테스트 환경)에서는 의존성을 외부에서 넣어줄 통로가 전무하므로, 테스트 중 `NullPointerException`이 발생하여 테스트 대역(Mock)을 꽂아 넣기 위해 리플렉션을 강제로 해킹해야 하는 등의 난제를 유발합니다. 또한 `final` 키워드를 적용할 수 없어 객체의 오염 위험에 노출됩니다.

#### B. 수정자 주입 (Setter Injection)

의존성을 설정하는 `setter` 메서드를 개설하고 여기에 `@Autowired`를 부여하는 방식입니다.

- **특징**: 주입할 의존성이 런타임 중에 변경될 여지가 있거나, 필수 의존성이 아니어서 누락되어도 괜찮을 때 주로 기용됩니다.

- **단점**: 언제든지 객체의 중요 컴포넌트가 임의로 외부에서 교체(Mutable)되거나 조작될 수 있어 캡슐화가 오염됩니다.

#### C. 생성자 주입 (Constructor Injection)

클래스의 생성자를 통해 의존성을 공급받는 방식입니다. 스프링 4.3 버전부터는 생성자가 단 1개만 존재할 경우 `@Autowired` 어노테이션까지 완전히 생략해도 컨테이너가 자동으로 바인딩해 줍니다.

- **스프링 공식 권장**: 스프링 팀은 이 생성자 주입 방식을 단연 최우선으로 권장하며 필드 주입을 지양하라고 공식 선언하고 있습니다.

- 필드 주입은 외부에서 의존성을 주입할 메서드나 생성자가 없어 테스트 컨텍스트 독립성을 파괴하고 프레임워크와 결합이 너무 조밀해지기 때문에, 스프링 공식 개발 가이드라인은 이를 권장하지 않고 우회할 것�� 명시하고 있다.

### 3. 생성자 주입(Constructor Injection)을 무조건 선택해야 하는 이유

생성자 주입은 다른 주입 방식과 비교해 단순히 코딩 취향의 차이를 넘어서는 **엄격한 아키텍처적 및 안정성 격차**를 제공합니다.

#### 1) 객체의 안전한 불변성(Immutability) 획득

생성자 주입을 사용하면 필드 선언 시 **`final`** 지시어를 사용할 수 있습니다. 객체가 최초 기동 및 생성되는 시점에 주입이 완료되어야 하므로, 런타임 중에 실수로 의존성이 변경되거나 유실되는 휴먼 에러를 원천 봉쇄할 수 있습니다.

#### 2) 순환 참조(Circular Dependency)의 컴파일 타임 감지

필드 주입이나 수정자 주입은 객체 생성 이후 시점에 의존성이 대입되므로, A 클래스가 B를 원하고 B 클래스가 A를 원하는 순환 참조 관계에 빠지더라도 서버가 에러 없이 조용히 기동해 버립니다. 이후 실제 메서드를 호출하는 찰나에 메모리가 터지는 대참사(`StackOverflowError`)를 맞이합니다.
반면 생성자 주입은 애플리케이션 실행 시점에 서로의 생성자를 연쇄 호출해야 하므로, **기동 찰나의 컴파일 타임(엄밀히는 애플리케이션 초기화 단계)에 바로 `BeanCurrentlyInCreationException` 에러를 뿜으며 자폭(Fail-Fast)**합니다. 이 덕분에 아키텍처적 문제를 기동 즉시 파악하고 수정할 수 있습니다.

#### 3) 누락 방지 및 단위 테스트(Unit Test)의 투명성

순수한 자바 기반 단위 테스트 시, 생성자 주입 클래스는 `new MyService(mockRepository)` 형태로 컴파일 수준에서 주입을 강제합니다. 주입해야 할 의존성 파라미터가 비어 있다면 아예 컴��일 에러를 내며 빌드가 차단되므로 누락 실수가 절대 발생할 수 없습니다.

- 생성자 주입은 자바 컴파일러 수준에서 빈 초기화 및 final 필드의 값 채움을 강제하므로, 런타임 상의 널 안전성(Null-safety)을 강력하게 보증하고 순환 참조 관계를 서비스 기동 즉시 경고로 드러내는 일방적 안전장치다.

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 롬복(Lombok) 라이브러리의 `@RequiredArgsConstructor` 어노테이션이 생성자 주입의 실무적 대중성을 완전히 평정했다고 봅니다. 이 어노테이션 한 줄이면 `final`로 선언된 모든 필드를 매개변수로 취하는 생성자가 백그라운드 바이트코드에 자동 생성되므로, 생성자 코드를 수동으로 길게 써야 했던 전통적인 단점을 말끔히 해소할 수 있습니다. 다만, 필자는 무비판적으로 이 롬복을 사용하는 것도 가끔 의존성 개수가 7~8개 이���으로 무한히 불어나는 '설계 결함(Single Responsibility Principle 위반)'을 감지하지 못하게 만드는 착시를 유발한다고 봅니다. 생성자 파라미터가 5개가 넘어가면, 이 클래스가 너무 많은 일을 하고 있지는 않은지 구조적 리팩토링의 신호로 삼아야 합니다.

## 한계와 반론

- **한계점**: 의존성 주입이 거의 필수적으로 프레임워크 컨테이너의 영역에서 처리되다 보니, 런타임에 어떤 빈이 최종 매핑되는지 디버깅 중 추적이 어렵고, 대형 프로젝트에서는 다이내믹 바인딩으로 인해 전체 아키텍처 흐름을 한눈에 시각화하기 어렵다는 인지적 복잡성 한계가 따릅니다.

- **반론**: 이에 대해 Dagger와 같이 빌드 타임에 정적으로 의존성 주입 코드를 다이렉트로 검증하여 생성하는 가볍고 직관적인 컴파일 타임 주입(Static DI) 프레임워크가 런타임 반사(Reflection) 비용도 전혀 들지 않고 디버깅 시 직관성도 월등히 뛰어나다는 지지론자들의 날카로운 주장도 존재합니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

IoC와 DI는 복잡한 객체 그물망을 사람이 직접 실로 엮던 시대를 마감하고 설계도(Annotation, Config)만 던지면 시스템이 자동으로 배관을 잇는 시대를 열었습니다. 그리고 생성자 주입은 스프링 생태계가 오랜 경험 끝에 필드 주입의 부작용을 극복하며 정립한 최적의 상식이자 합리적 규칙입니다. 신규 백엔드 프로젝트를 시작하는 엔지니어라면 무조건 의존성은 `final`과 생성자 형태로 선언하고, 롬복을 도구로 결합하여 캡슐화의 안전지대를 탄탄히 수비하는 방식으로 코딩을 전개해야 합니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- Martin Fowler, "Inversion of Control Containers and the Dependency Injection pattern", [https://martinfowler.com/articles/injection.html](https://martinfowler.com/articles/injection.html)

- Robert C. Martin, "Clean Architecture: A Craftsman's Guide to Software Structure and Design", Prentice Hall.

- Spring Framework Reference Documentation, "Core Technologies - Dependency Injection", [https://docs.spring.org/spring-framework/docs/current/reference/html/core.html#beans-dependencies](https://docs.spring.org/spring-framework/docs/current/reference/html/core.html#beans-dependencies)

- Baeldung, "Constructor Injection vs Field Injection in Spring", [https://www.baeldung.com/spring-constructor-injection-vs-field-injection](https://www.baeldung.com/spring-constructor-injection-vs-field-injection)

- Spring Framework Github discussions, "Guidelines for dependency injection style guide", [https://github.com/spring-projects/spring-framework/wiki](https://github.com/spring-projects/spring-framework/wiki)
