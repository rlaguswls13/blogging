---
id: '7705263003828640401'
publishedAt: '2026-08-14T11:28:42.000-07:00'
slug: gof-11-observer-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 11. 옵저버 패턴 (Observer Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:18:49.383-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-11-observer-pattern-java.html
---

# [GoF 디자인 패턴] 11. 옵저버 패턴 (Observer Pattern) 개념과 Java 실전 예시

## 요약

옵저버 패턴(Observer Pattern)은 어떤 주체(Subject)의 상태가 변할 때, 이를 구독 중인 여러 관찰자(Observer)에게 자동으로 통지하는 발행-구독(Publish-Subscribe) 기반 행위 패턴입니다. 폴링(Polling) 방식의 자원 낭비 문제를 근본적으로 해결하지만, 구독 해제를 잊으면 메모리 누수(Lapsed Listener Problem)로 이어질 수 있습니다. 이 글에서는 뉴스 발행 시스템 예제와 함께 이 메모리 누수 함정의 원인과 해법, 그리고 Spring `@EventListener`와 리액티브 스트림(RxJava/Project Reactor)의 뿌리가 왜 옵저버 패턴인지 다룹니다.

## 본문

### 1. 배경 및 문제점

어떤 핵심 객체(Subject)의 데이터나 상태가 변할 때, 이 변화에 맞춰 여러 연관 객체(Observer)들의 상태도 함께 갱신되어야 하는 상황은 실무에서 매우 자주 발생합니다.

옵저버 패턴이 없을 때 개발자가 흔히 범하는 실수는 "주기적으로 찔러보는" 폴링(Polling) 방식입니다.

- **CPU 및 네트워크 대역폭 낭비**: 변화가 없는 대부분의 시간에도 `while(true)`나 주기적 타이머, DB 폴링 쿼리를 실행해 서버 자원을 불필요하게 소모합니다.
- **실시간성 저하**: 폴링 간격(예: 1초, 5초) 사이에 일어난 상태 변화를 즉시 감지하지 못하고 지연이 발생합니다.
- **강한 결합도**: 주체 객체가 통지 대상을 일일이 클래스로 알고 있어야 하므로, 수신 대상이 추가될 때마다 주체 코드를 직접 고쳐야 하는 개방-폐쇄 원칙(OCP) 위반이 일어납니다.

### 2. 해결책 및 동작 메커니즘

옵저버 패턴은 발행-구독 개념을 도입해 이 문제를 근본적으로 해결합니다. 주체(Subject)는 관찰자(Observer)들의 구체적인 클래스를 알 필요 없이, "관찰자 목록에 수신자를 등록받고, 상태가 변경되면 통지를 보내는 일"만 전담합니다.

**실제 서비스 동작 예시**: 중고거래 플랫폼의 "키워드 알림" 기능을 떠올려 봅시다. 판매자가 특정 키워드가 포함된 게시글을 올리는 순간, 알림 서버(Subject)가 이 키워드를 미리 구독(Register)해 둔 수만 명의 사용자 앱(Observer)으로 푸시 알림을 즉시 발송합니다. 동작 흐름은 판매자 글 등록 → 알림 이벤트 발행 → 키워드 구독자 목록 조회 → 푸시 알림 수신 순입니다.

**비유**: 유튜브 채널 구독과 알림 설정을 떠올리면 이해가 쉽습니다. 유튜버(Subject)가 새 동영상을 올릴 때 100만 명 구독자 집집마다 전화를 거는 것이 아니라, 시청자가 미리 "구독 및 알림설정"(Observer 등록)을 해두면 동영상 등록 이벤트 발생 시 시스템 알림망이 자동으로 전파를 보냅니다. 이렇게 발행자와 수신자 간 결합도를 획기적으로 낮출 수 있습니다(Loose Coupling).

### 3. 실무 주의점: 메모리 누수(Lapsed Listener Problem) 함정

옵저버 패턴을 쓸 때 Subject에 Observer를 `registerObserver(observer)`로 등록하면, Subject의 내부 리스트가 Observer의 참조를 강하게 붙잡습니다. 화면이 닫히거나 Observer 객체가 더 이상 쓰이지 않아도, Subject 리스트에서 `removeObserver()`로 등록을 해제해주지 않으면 자바 가비지 컬렉터(GC)가 이 Observer 객체를 절대 회수하지 못합니다. 이를 Lapsed Listener Problem이라 부릅니다.

해결책은 두 가지입니다.

1. 컴포넌트 소멸 시점(`onDestroy`, `close()`)에 명시적으로 `unregisterObserver()`를 호출하는 것.
2. `WeakReference`(약한 참조) 기반의 옵저버 리스트 구조를 채택해 GC가 자동으로 회수하도록 유도하는 것.

느슨한 결합(Loose Coupling)이라는 장점은 동시에 "누가 언제 구독 해제해야 하는지"에 대한 책임이 흐려진다는 단점이기도 하다는 점을 실무에서는 늘 염두에 두어야 합니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

아래 코드는 뉴스 발행 시스템(Subject)과 뉴스 수신자(Observer)들이 등록·알림·해제되는 과정을 담은 실행 가능한 Java 예제입니다.

```java
import java.util.ArrayList;
import java.util.List;

// 1. 관찰자(Observer) 인터페이스
interface Observer {
    void update(String newsTitle);
}

// 2. 주체(Subject) 인터페이스
interface Subject {
    void registerObserver(Observer o);
    void removeObserver(Observer o);
    void notifyObservers();
}

// 3. 구체적인 주체 (NewsAgency)
class NewsAgency implements Subject {
    private final List<Observer> observers = new ArrayList<>();
    private String latestNews;

    @Override
    public void registerObserver(Observer o) {
        observers.add(o);
        System.out.println("[구독 완료] 새로운 옵저버가 등록되었습니다.");
    }

    @Override
    public void removeObserver(Observer o) {
        observers.remove(o);
        System.out.println("[구독 해제] 옵저버 등록이 해제되었습니다. (메모리 누수 방지)");
    }

    @Override
    public void notifyObservers() {
        for (Observer observer : observers) {
            observer.update(latestNews);
        }
    }

    public void publishNews(String title) {
        this.latestNews = title;
        System.out.println("[뉴스 발행] " + title);
        notifyObservers();
    }
}

// 4. 구체적인 관찰자 (NewsSubscriber)
class NewsSubscriber implements Observer {
    private final String name;

    public NewsSubscriber(String name) {
        this.name = name;
    }

    @Override
    public void update(String newsTitle) {
        System.out.println("  -> [" + name + " 수신 알림]: " + newsTitle);
    }
}

public class ObserverPatternMain {
    public static void main(String[] args) {
        NewsAgency agency = new NewsAgency();

        NewsSubscriber sub1 = new NewsSubscriber("Subscriber A");
        NewsSubscriber sub2 = new NewsSubscriber("Subscriber B");

        agency.registerObserver(sub1);
        agency.registerObserver(sub2);

        agency.publishNews("Breaking: Observer pattern powers real-time notifications!");

        agency.removeObserver(sub1); // 구독자A 해제 (메모리 누수 예방)

        agency.publishNews("Update: Spring @EventListener adoption guide released!");
    }
}
```

실행하면 첫 번째 뉴스는 두 구독자 모두에게 전달되지만, `removeObserver(sub1)` 이후 발행된 두 번째 뉴스는 구독자 B에게만 전달되는 것을 확인할 수 있습니다.

### 5. 실무 프레임워크 적용 사례

- **Spring Framework `@EventListener` & `ApplicationEventPublisher`**: 도메인 로직과 이벤트 로직을 완전히 분리하기 위해 옵저버 패턴 기반의 이벤트 게시 시스템을 제공합니다. 예를 들어 회원가입 완료 시 `eventPublisher.publishEvent(new UserRegisteredEvent(user))`를 호출하면, 이메일 발송 서비스는 `@EventListener`가 붙은 메서드로 회원가입 로직과 무관하게 독립적으로 이벤트를 전달받아 처리할 수 있습니다.
- **리액티브 프로그래밍(RxJava / Project Reactor)**: 현대 반응형 아키텍처(WebFlux, RxJava)에서 데이터를 스트림으로 흘려보내고 `Mono`, `Flux` 객체를 `subscribe()`로 비동기 수신하는 구조의 근본적인 뿌리가 바로 옵저버 패턴입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 옵저버 패턴은 주체(Subject)의 상태 변화를 다수의 관찰자(Observer)에게 자동으로 통지하는 발행-구독 구조다 | verified | Design Patterns (Gamma et al., 1994) Observer 챕터 |
| CLAIM-002: 옵저버를 명시적으로 해제하지 않으면 Subject가 참조를 계속 붙잡아 GC가 회수하지 못하는 메모리 누수(Lapsed Listener Problem)가 발생할 수 있다 | verified | 일반적으로 알려진 Java 옵저버 패턴 구현의 메모리 관리 이슈(WeakReference 활용이 표준적인 대응책으로 문서화됨) |
| CLAIM-003: Spring Framework는 ApplicationEventPublisher와 @EventListener를 통해 옵저버 패턴 기반 이벤트 발행 메커니즘을 제공한다 | verified | Spring Framework 공식 문서 - Application Events 챕터 |
| CLAIM-004: Project Reactor의 Mono/Flux는 subscribe() 호출을 통해 비동기로 데이터를 수신하는 리액티브 스트림 구조를 따른다 | verified | Project Reactor 공식 문서 - Reactor Core |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

옵저버 패턴을 다룰 때 가장 과소평가되는 부분이 바로 구독 해제 책임이라고 생각합니다. 느슨한 결합이라는 장점에 집중한 나머지 "누가 언제 `removeObserver()`를 호출해야 하는가"를 설계 초기에 명확히 정하지 않으면, 안드로이드 액티비티나 프론트엔드 컴포넌트에서 흔히 발생하는 메모리 누수 버그로 이어지는 경우를 실무에서 자주 봅니다. 개인적으로는 옵저버 패턴을 도입할 때 등록 코드를 작성하는 시점에 반드시 짝이 되는 해제 코드의 위치까지 함께 정하는 것을 권장합니다. Spring의 `@EventListener`처럼 프레임워크가 생명주기를 대신 관리해주는 경우가 아니라면, 수동 구독 해제 누락은 예상보다 훨씬 자주 일어나는 실수입니다.

## 한계와 반론

옵저버 패턴은 통지 순서가 옵저버 등록 순서에 의존하는 경우가 많아, 특정 옵저버의 처리가 다른 옵저버의 상태에 영향을 주는 상황에서는 디버깅이 어려워질 수 있습니다. 또한 옵저버 수가 많아지면 하나의 상태 변경이 연쇄적으로 다수의 업데이트를 유발해 성능 병목이 될 수 있고, 어떤 옵저버가 어떤 이벤트에 반응하는지 코드만 보고 추적하기 어려워 전체 시스템의 흐름 파악이 힘들어진다는 반론도 있습니다. 이런 이유로 대규모 시스템에서는 옵저버 패턴을 직접 구현하기보다 메시지 브로커(Kafka, RabbitMQ)나 이벤트 버스 프레임워크로 감싸 가시성을 확보하는 경우가 많습니다.

## 참고문헌

1. [Observer pattern - Wikipedia](https://en.wikipedia.org/wiki/Observer_pattern) (확인일: 2026-08-17)
2. [Spring Framework Documentation - Application Events](https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html) (확인일: 2026-08-17)
3. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

옵저버 패턴은 GUI 이벤트 처리부터 Spring의 도메인 이벤트, 나아가 리액티브 스트림까지 이어지는 매우 근본적인 설계 아이디어입니다. "발행자는 구독자를 몰라도 된다"는 원칙 하나가 느슨한 결합과 실시간 반응성이라는 두 가지 가치를 동시에 달성하게 해줍니다. 다만 이 패턴의 가장 큰 실무 리스크는 구조 자체가 아니라 생명주기 관리(구독 해제)에 있으므로, 옵저버 패턴을 도입할 때는 항상 "이 구독은 언제 끝나는가"를 함께 설계해야 한다는 점을 강조하고 싶습니다.

## 꼬리질문

1. **WeakReference 기반 옵저버 리스트가 실제로 GC 회수를 유도하는 원리는 무엇이며, 강한 참조 리스트 대비 어떤 성능 트레이드오프가 있는가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Observer_pattern
2. **Spring의 @EventListener 기반 이벤트 처리와 Kafka 같은 메시지 브로커 기반 이벤트 처리는 옵저버 패턴 관점에서 어떤 차이가 있는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)