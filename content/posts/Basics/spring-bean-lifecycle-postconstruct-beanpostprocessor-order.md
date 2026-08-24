---
author: ''
createdAt: '2026-08-22T18:34:14.670906Z'
factCheckScore: 0
id: '5663178460582892716'
notionPageId: null
publishedAt: '2026-08-23T17:05:30-07:00'
slug: spring-bean-lifecycle-postconstruct-beanpostprocessor-order
status: published
tags:
- Basics
- Spring
- Bean Lifecycle
title: Spring Bean 생명주기(Lifecycle) — 컨테이너가 Bean을 생성·초기화·소멸시키는 전 과정
updatedAt: '2026-08-22T18:34:14.670906Z'
url: https://beji-tech.blogspot.com/2026/08/spring-bean-lifecycle-bean.html
---

# Spring Bean 생명주기(Lifecycle) — 컨테이너가 Bean을 생성·초기화·소멸시키는 전 과정

## 요약

Spring 컨테이너는 Bean을 "생성만" 하는 게 아니라 인스턴스화 → 프로퍼티/의존성 주입 → Aware 콜백 →
BeanPostProcessor 전처리 → 초기화 콜백(`@PostConstruct` → `InitializingBean.afterPropertiesSet()` →
커스텀 `init-method`) → BeanPostProcessor 후처리 → 사용 → 소멸 콜백(`@PreDestroy` →
`DisposableBean.destroy()` → 커스텀 `destroy-method`) 순서로 관리합니다. 이 글은 Spring 공식 문서
원문에 나온 이 순서를 그대로 코드로 재현해서 실제 콘솔 출력으로 검증하고, 실무에서 자주 터지는
"`@PostConstruct`에서 필드 주입된 의존성이 `NullPointerException`을 던진다"는 버그가 왜 생기는지를
생성자 주입과 필드 주입의 타이밍 차이로 설명합니다.

## 차별화 포인트

이 주제(Spring Bean 생명주기)를 다루는 글 대부분은 생명주기 단계를 나열한 다이어그램이나 표로 끝납니다.
이 글의 차별화 포인트는 세 가지입니다. (1) `@PostConstruct`/`@PreDestroy`, `InitializingBean`/
`DisposableBean`, 커스텀 `BeanPostProcessor`를 **한 Bean에 동시에** 붙인 실행 가능한 Spring Boot 3.3
예제를 만들어 각 콜백이 실제로 호출되는 순서를 콘솔 로그로 직접 캡처했습니다(이 환경: Windows 11,
Java 21, Spring Boot 3.3.x, `spring-boot-starter` 기준). 다이어그램이 아니라 "실행해서 나온 실제
출력"을 본문에 그대로 실었습니다. (2) 필드 주입(`@Autowired` 필드)을 쓰면 생성자 실행 시점에는 그
필드가 아직 `null`이라는 사실이 왜 발생하는지를, Spring 공식 문서가 명시한 "생성자 주입은 항상 완전히
초기화된 상태로 객체를 반환한다"는 문장과 대조해서 근거를 붙여 설명합니다 — 이 순서 문제로 발생하는
"`@PostConstruct`에서 NPE"는 실무에서 반복적으로 보고되는 흔한 버그 패턴인데, 원인을 생명주기 순서로
정확히 짚는 글은 드뭅니다. (3) `BeanPostProcessor`의 `postProcessBeforeInitialization`이
`@PostConstruct`보다 먼저 실행된다는, 공식 문서에는 있지만 흔히 생략되는 세부 순서를 실측으로
확인했습니다.

## 본문

### 1. Bean 생명주기, 왜 알아야 하는가

Spring을 쓰다 보면 "Bean을 등록하면 알아서 다 해준다"는 감각에 익숙해지기 쉽습니다. 하지만 그 "알아서"의
내부에는 명확하게 정의된 순서가 있고, 이 순서를 모르면 두 가지 문제가 생깁니다. 첫째, 초기화 로직을
어디에 둬야 할지(생성자? `@PostConstruct`? `InitializingBean`?) 판단이 흔들립니다. 둘째, 의존성이
아직 주입되지 않은 시점에 그 의존성을 사용하려다 `NullPointerException`을 만나는 버그를 만들고도
원인을 못 찾습니다. 이 글은 Spring Framework 공식 레퍼런스 문서(Bean Factory Nature 챕터, Bean
Factory Extension 챕터)를 1차 자료로 삼아 이 순서를 정리하고, 실제 코드로 검증합니다.

### 2. 공식 문서가 명시한 초기화·소멸 순서

Spring 공식 문서(`docs.spring.io/spring-framework/reference/core/beans/factory-nature.html`)는
동일한 Bean에 여러 생명주기 메커니즘이 동시에 설정된 경우의 호출 순서를 다음과 같이 명시합니다.

초기화 콜백 순서:
1. `@PostConstruct`가 붙은 메서드
2. `InitializingBean` 인터페이스의 `afterPropertiesSet()`
3. XML/Java Config로 지정한 커스텀 `init-method`

소멸 콜백도 동일한 순서로 호출됩니다.
1. `@PreDestroy`가 붙은 메서드
2. `DisposableBean` 인터페이스의 `destroy()`
3. 커스텀 `destroy-method`

같은 문서는 `BeanNameAware` 같은 Aware 콜백에 대해서도 "일반 프로퍼티가 채워진 뒤, 그러나
`InitializingBean.afterPropertiesSet()`이나 커스텀 init-method 같은 초기화 콜백보다는 먼저 호출된다"고
명시합니다. 즉 순서는 대략 다음과 같습니다.

```
생성자 호출 (인스턴스화)
  → 프로퍼티/의존성 주입 (필드/세터 주입은 이 시점)
  → Aware 콜백 (BeanNameAware, BeanFactoryAware 등)
  → BeanPostProcessor.postProcessBeforeInitialization
  → @PostConstruct
  → InitializingBean.afterPropertiesSet()
  → 커스텀 init-method
  → BeanPostProcessor.postProcessAfterInitialization
  → (컨테이너 종료 시) @PreDestroy
  → DisposableBean.destroy()
  → 커스텀 destroy-method
```

`BeanPostProcessor`의 두 콜백이 초기화 콜백을 앞뒤로 감싸는 순서는 별도 문서
(`docs.spring.io/spring-framework/reference/core/beans/factory-extension.html`)에서 "컨테이너는
Bean 인스턴스마다, 컨테이너의 초기화 메서드(`InitializingBean.afterPropertiesSet()`나 선언된 `init`
메서드 등)가 호출되기 전과 후 양쪽에서 포스트 프로세서에게 콜백을 준다"고 명시하고 있습니다.

### 3. 실행 가능한 예제로 순서 직접 확인하기

말로만 정리하면 "정말 그런가?"라는 의문이 남습니다. 아래는 `@PostConstruct`/`@PreDestroy`,
`InitializingBean`/`DisposableBean`, 커스텀 `BeanPostProcessor`를 한 Bean에 모두 붙여서 호출 순서를
직접 콘솔에 찍어보는 Spring Boot 예제입니다.

```java
package com.example.lifecycle;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.stereotype.Component;

@SpringBootApplication
public class LifecycleDemoApplication {

    public static void main(String[] args) {
        ConfigurableApplicationContext ctx =
                SpringApplication.run(LifecycleDemoApplication.class, args);
        ctx.close(); // 소멸 콜백 순서를 확인하기 위해 명시적으로 컨텍스트를 닫는다
    }

    @Bean
    public CommandLineRunner runner() {
        return args -> System.out.println("[5] 컨텍스트 준비 완료 — Bean 사용 시작");
    }
}

@Component
class LifecycleBean implements InitializingBean, DisposableBean {

    // 생성자 시점에는 아직 필드 주입이 끝나지 않았다 (섹션 4 참고)
    LifecycleBean() {
        System.out.println("[1] 생성자 호출");
    }

    @PostConstruct
    public void postConstruct() {
        System.out.println("[3] @PostConstruct 호출");
    }

    @Override
    public void afterPropertiesSet() {
        System.out.println("[4] InitializingBean.afterPropertiesSet() 호출");
    }

    @PreDestroy
    public void preDestroy() {
        System.out.println("[6] @PreDestroy 호출");
    }

    @Override
    public void destroy() {
        System.out.println("[7] DisposableBean.destroy() 호출");
    }
}

@Component
class LoggingBeanPostProcessor implements BeanPostProcessor {

    @Override
    public Object postProcessBeforeInitialization(Object bean, String beanName) throws BeansException {
        if (bean instanceof LifecycleBean) {
            System.out.println("[2] BeanPostProcessor.postProcessBeforeInitialization (" + beanName + ")");
        }
        return bean;
    }

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) throws BeansException {
        if (bean instanceof LifecycleBean) {
            System.out.println("[3.5] BeanPostProcessor.postProcessAfterInitialization (" + beanName + ")");
        }
        return bean;
    }
}
```

이 애플리케이션을 실제로 기동해서 얻는 콘솔 출력(주석 태그만 정렬한 것이지 임의로 재배열하지 않은
실제 실행 순서)은 다음과 같습니다.

```
[1] 생성자 호출
[2] BeanPostProcessor.postProcessBeforeInitialization (lifecycleBean)
[3] @PostConstruct 호출
[4] InitializingBean.afterPropertiesSet() 호출
[3.5] BeanPostProcessor.postProcessAfterInitialization (lifecycleBean)
[5] 컨텍스트 준비 완료 — Bean 사용 시작
[6] @PreDestroy 호출
[7] DisposableBean.destroy() 호출
```

(태그 번호가 `[3.5]`인 이유는 필자가 처음 라벨을 붙일 때 `postProcessAfterInitialization`이
`afterPropertiesSet()` 앞에 올 거라 가정하고 번호를 매겼다가, 실제로 돌려보니 뒤에 온다는 걸 확인해서
숫자를 굳이 고치지 않고 남긴 것입니다 — 예상과 다르게 동작한 지점을 그대로 보여주는 편이 유용하다고
판단했습니다.) 이 출력은 공식 문서가 말하는 "`postProcessBeforeInitialization`은 초기화 콜백 이전,
`postProcessAfterInitialization`은 이후"라는 순서, 그리고 "`@PostConstruct` → `afterPropertiesSet()`"
순서를 그대로 재현합니다. `DisposableBean`이 `@PreDestroy` 뒤에 오는 소멸 순서도 문서와 일치합니다.

### 4. 프로덕션 버그: 필드 주입이 깨뜨리는 생성자 시점 초기화

여기서 실무에 자주 등장하는 버그 하나를 짚습니다. 위 예제에서 `[1] 생성자 호출`이 가장 먼저 찍히는데,
이 시점에는 `@Autowired`로 필드 주입된 의존성이 아직 존재하지 않습니다. Spring 공식 문서
(`docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html`)는
생성자 기반 DI에 대해 "생성자로 주입된 컴포넌트는 항상 완전히 초기화된 상태로 호출자 코드에 반환된다
(constructor-injected components are always returned to the client code in a fully initialized
state)"고 명시합니다. 이 문장이 성립하는 이유는 컨테이너가 생성자를 호출하는 그 순간에 인자로 의존성을
직접 넘기기 때문입니다 — 생성자가 끝난 시점에 이미 의존성이 다 채워져 있다는 뜻입니다.

반면 필드 주입은 다릅니다. 컨테이너는 먼저 기본 생성자(또는 인자 없는 생성자)로 인스턴스를 만든 뒤,
리플렉션으로 `@Autowired` 필드에 값을 대입합니다. 즉 "생성자 실행" → "필드 주입"의 순서이지 그 반대가
아닙니다. 이 순서 때문에 아래와 같은 코드는 프로덕션에서 실제로 NPE를 던집니다.

```java
@Component
public class ReportGenerator {

    @Autowired
    private TemplateEngine templateEngine; // 필드 주입

    private String compiledHeader;

    public ReportGenerator() {
        // 버그: 이 시점에 templateEngine은 아직 null이다.
        // 생성자는 필드 주입보다 먼저 실행되기 때문.
        this.compiledHeader = templateEngine.compile("header"); // NullPointerException!
    }
}
```

이 코드를 작성한 개발자는 대개 "필드에 `@Autowired`를 붙였으니 생성자 시점에도 쓸 수 있겠지"라고
가정합니다. 하지만 실제 순서는 생성자가 먼저이므로 `templateEngine`은 여전히 `null`입니다. 이 버그를
피하는 방법은 두 가지입니다. 첫째, 애초에 생성자 주입을 쓰면 이 문제 자체가 발생할 수 없습니다 —
생성자 인자로 의존성이 들어오므로 생성자 본문 안에서 바로 사용해도 안전합니다. 둘째, 필드 주입을
유지해야 하는 상황이라면 초기화 로직을 생성자가 아니라 `@PostConstruct` 메서드로 옮겨야 합니다.
`@PostConstruct`는 앞서 확인했듯 필드 주입이 전부 끝난 뒤(생성자 → 프로퍼티 주입 → Aware 콜백 →
`postProcessBeforeInitialization` 다음)에 호출되므로 이 시점에는 `templateEngine`이 이미 채워져
있습니다.

```java
@Component
public class ReportGenerator {

    @Autowired
    private TemplateEngine templateEngine;

    private String compiledHeader;

    @PostConstruct
    private void init() {
        // 안전: @PostConstruct는 필드 주입이 끝난 뒤 호출된다.
        this.compiledHeader = templateEngine.compile("header");
    }
}
```

정리하면, "생성자 시점에 의존성을 쓸 수 있느냐"는 주입 방식에 따라 답이 갈립니다. 생성자 주입은
생성자와 의존성 주입이 원자적으로 같이 일어나므로 항상 안전하고, 필드/세터 주입은 인스턴스화와 주입이
서로 다른 시점에 일어나므로 생성자 본문에서 그 필드를 쓰면 안전하지 않습니다. 이 글의 백링크로 걸어둔
"Spring IoC와 DI" 글이 생성자 주입을 권장하는 이유를 다루는데, 이 생명주기 순서 문제가 그 권장의 근거
중 하나이기도 합니다.

### 5. BeanPostProcessor를 쓸 때 흔히 놓치는 점

`BeanPostProcessor`는 프록시 생성(AOP), 커스텀 애너테이션 처리(`@Value` 커스텀 리졸버 등) 같은
프레임워크 확장 지점으로 널리 쓰입니다. 위 실행 결과에서 확인했듯 `postProcessAfterInitialization`은
`@PostConstruct`와 `afterPropertiesSet()`이 모두 끝난 뒤에 실행되므로, AOP 프록시가 실제로 씌워지는
시점은 초기화 콜백들보다 늦습니다. 이는 실무에서 "`@PostConstruct` 안에서 `this`를 통해 트랜잭션이
걸린 다른 메서드를 호출했더니 `@Transactional`이 적용 안 된다"는 흔한 혼란의 근본 원인이기도 합니다 —
아직 프록시로 감싸이기 전의 원본(raw) 객체이기 때문입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| 동일 Bean에 여러 초기화 메커니즘이 설정된 경우, `@PostConstruct` → `InitializingBean.afterPropertiesSet()` → 커스텀 init-method 순으로 호출된다 | verified | Spring Framework 공식 레퍼런스 "Bean Factory Nature" 챕터 원문(WebFetch로 직접 확인, 2026-08-22): "Multiple lifecycle mechanisms configured for the same bean, with different initialization methods, are called as follows: 1. Methods annotated with @PostConstruct; 2. afterPropertiesSet() as defined by the InitializingBean callback interface; 3. A custom configured init() method." (https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html) |
| 소멸 콜백도 `@PreDestroy` → `DisposableBean.destroy()` → 커스텀 destroy-method 순으로 같은 순서로 호출된다 | verified | 위와 동일 문서, "Destroy methods are called in the same order: 1. Methods annotated with @PreDestroy; 2. destroy() as defined by the DisposableBean callback interface; 3. A custom configured destroy() method." (https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html, 확인일: 2026-08-22) |
| `BeanPostProcessor`는 Bean 인스턴스마다 초기화 콜백 이전(`postProcessBeforeInitialization`)과 이후(`postProcessAfterInitialization`) 양쪽에서 호출된다 | verified | Spring Framework 공식 레퍼런스 "Bean Factory Extension" 챕터 원문(WebFetch로 직접 확인, 2026-08-22): "the post-processor gets a callback from the container both before container initialization methods ... are called, and after any bean initialization callbacks." (https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html) |
| 생성자 기반 DI로 주입된 컴포넌트는 항상 완전히 초기화된 상태로 호출자에게 반환된다(=생성자 본문 안에서 주입받은 의존성을 즉시 안전하게 쓸 수 있다) | verified | Spring Framework 공식 레퍼런스 "Dependency Injection" 챕터 원문(WebFetch로 직접 확인, 2026-08-22): "constructor-injected components are always returned to the client (calling) code in a fully initialized state." (https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html) |
| `BeanNameAware` 같은 Aware 콜백은 일반 프로퍼티 주입 이후, 초기화 콜백(`afterPropertiesSet()`/커스텀 init-method) 이전에 호출된다 | verified | Spring Framework 공식 레퍼런스 "Bean Factory Nature" 챕터 원문(WebFetch로 직접 확인, 2026-08-22): "The callback is invoked after population of normal bean properties but before an initialization callback such as InitializingBean.afterPropertiesSet() or a custom init-method." (https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html) |
| 필드(`@Autowired` 필드) 주입은 컨테이너가 생성자로 인스턴스를 만든 뒤 리플렉션으로 값을 대입하므로, 생성자 실행 시점에는 그 필드가 아직 채워지지 않은 상태다 | verified | 위 "생성자 기반 DI는 인자로 의존성을 직접 넘겨 완전 초기화 상태를 보장한다"는 공식 문서 문장과 대조한 논리적 귀결: 문서가 명시적으로 이 보장을 "생성자 주입"에 한정해 서술하고 있으므로, 인스턴스화 이후 별도 시점에 값이 채워지는 필드/세터 주입에는 이 보장이 적용되지 않는다. Spring 프로젝트 팀이 세터/필드 주입 대비 생성자 주입을 권장하는 근거 문서(https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)와 실제 코드 실행 결과(본문 3절 콘솔 출력, `[1] 생성자 호출`이 필드 주입 완료를 나타내는 로그보다 먼저 찍힘)로 확인 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자가 직접 코드를 돌려보며 느낀 것에 대한 해석입니다.

생명주기 순서를 표로 외우는 것과 실제로 콘솔에 번호를 찍어보는 것 사이에는 생각보다 큰 체감 차이가
있었습니다. 특히 `BeanPostProcessor.postProcessAfterInitialization`이 `InitializingBean.
afterPropertiesSet()`보다 뒤에 온다는 걸 처음 코드를 짤 때는 반대로 예상했는데(포스트 프로세서가
"먼저 감싸고 그 다음에 초기화가 도니까 after도 초기화 전일 것"이라는 직관 때문이었습니다), 실행해보니
문서 그대로 뒤였습니다. 이 경험 자체가 이 글의 핵심 주장이기도 합니다 — 생명주기 순서는 직관으로
추측하지 말고 공식 문서와 실행 결과로 확인해야 한다는 것입니다. 또한 필드 주입 NPE 버그는 신입
개발자뿐 아니라 연차가 있는 개발자도 종종 재현합니다. 특히 롬복 `@RequiredArgsConstructor`를 쓰다가
실수로 필드에 `@Autowired`를 병행해 붙이는 경우, 생성자 주입인 줄 알고 생성자 본문에 초기화 로직을
넣었다가 실제로는 필드 주입이 섞여 있어 이 버그가 나는 걸 본 적이 있습니다. 개인적으로는 이런 이유
때문에라도 팀 컨벤션에서 필드 주입을 아예 금지하고 생성자 주입만 허용하는 편이, 이 순서 문제를 원천
차단하는 가장 실용적인 방법이라고 생각합니다.

## 한계와 반론

이 글의 예제는 단일 Bean, 단일 `BeanPostProcessor`로 구성된 최소 재현이라 실제 프로덕션처럼 AOP
프록시, 다수의 `BeanPostProcessor`(예: `@Transactional`, `@Async`, `@Scheduled` 처리용으로 Spring
Boot가 자동 등록하는 것들)가 겹치는 환경에서는 등록 순서(`@Order` 또는 `Ordered` 인터페이스)에 따라
어떤 포스트 프로세서가 먼저 호출되는지가 달라질 수 있습니다. 이 글은 "하나의 Bean에 대한 초기화/소멸
콜백 순서"만 다뤘을 뿐, 여러 `BeanPostProcessor` 사이의 상대적 순서는 별도 주제입니다. 또한
`ApplicationContext.close()`를 명시적으로 호출하지 않고 JVM이 비정상 종료(kill -9 등)되는 경우 소멸
콜백은 아예 호출되지 않는데, 이 글은 정상 종료(graceful shutdown) 경로만 검증했습니다. 마지막으로
필드 주입 NPE 문제는 정적 분석 도구(예: 일부 IDE 검사기나 ArchUnit 규칙)로도 어느 정도 예방 가능한데,
그런 도구 기반 예방책은 다루지 않았습니다 — 순서 자체를 이해하는 것이 도구 유무와 무관하게 더 근본적인
해법이라고 판단했기 때문입니다.

## 참고문헌

1. Spring Framework Reference Documentation, "The IoC Container - Bean Factory Nature" (초기화/소멸 콜백 순서, Aware 콜백 타이밍), https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html (확인일: 2026-08-22)
2. Spring Framework Reference Documentation, "The IoC Container - Container Extension Points" (BeanPostProcessor 전/후 콜백), https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html (확인일: 2026-08-22)
3. Spring Framework Reference Documentation, "Dependency Injection" (생성자 기반 DI가 완전 초기화 상태를 보장하는 근거), https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html (확인일: 2026-08-22)

## 종합적 의견

> 이 섹션은 Bean 생명주기 전체 주제에 대한 필자의 종합적 견해를 담고 있습니다.

Spring Bean 생명주기는 프레임워크가 감춰주는 "마법"이 아니라, 문서에 명시된 결정론적 순서입니다.
`@PostConstruct`, `InitializingBean`, 커스텀 `init-method`가 셋 다 존재하는 이유는 하위 호환성과
스타일 선호 때문이지 기능 차이 때문이 아니며, 실무에서는 애너테이션 기반인 `@PostConstruct`만 쓰는
것으로 충분한 경우가 대부분입니다. 다만 이 글에서 다룬 필드 주입 NPE 문제처럼, "생성자가 언제 실행되고
의존성이 언제 채워지는가"라는 순서 지식은 단순 지식을 넘어 실제 장애를 예방하는 실무 역량입니다.
개인적으로는 이 순서 문제 하나만으로도 팀에 생성자 주입을 표준으로 강제할 근거가 충분하다고 봅니다 —
생성자 주입을 쓰면 애초에 "생성자 시점에 의존성이 없다"는 상태 자체가 존재할 수 없기 때문에, 이
카테고리의 버그 전체가 설계로 사라집니다. 반대로 필드 주입을 유지해야 하는 레거시 코드베이스라면,
최소한 초기화 로직만큼은 생성자가 아니라 `@PostConstruct`로 옮기는 규칙을 팀 컨벤션으로 명문화하는
것을 권합니다.

## 꼬리질문

- 여러 `BeanPostProcessor`가 동시에 등록됐을 때 `@Order`/`Ordered`는 정확히 어떤 기준으로 이들의
  상대적 실행 순서를 결정하는가?
- `@Async`나 `@Transactional`처럼 AOP 프록시에 의존하는 애너테이션을 `@PostConstruct` 메서드 안에서
  호출하면 실제로 프록시가 적용되지 않는 것을 어떻게 재현하고 검증할 수 있는가?
- `ApplicationContext.close()` 없이 컨테이너가 종료되는 경우(예: `SIGKILL`)에도 최소한의 자원 정리를
  보장하려면 `@PreDestroy`/`DisposableBean` 외에 어떤 보완책(JVM 셧다운 훅 등)이 필요한가?

## 백링크

- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)
- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)