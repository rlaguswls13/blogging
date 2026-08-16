---
id: "7705263003828640401"
title: "[GoF 디자인 패턴] 11. 옵저버 패턴 (Observer Pattern) 개념과 Java 실전 예시"
slug: "gof-11-observer-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-11-observer-pattern-java.html"
publishedAt: "2026-08-14T11:28:42.000-07:00"
updatedAt: "2026-08-15T16:18:49.383-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 11. 옵저버 패턴 (Observer Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴
    행위 패턴 (Behavioral Patterns) 시리즈 #11
  

  
## 1. 배경 및 문제점 (Problem & Motivation)

  
어떤 핵심 객체(Subject)의 데이터나 상태가 변할 때, 이 상태 변화에 맞춰 다른 여러 연관 객체(Observers)들의 상태도 함께 갱신되어야 하는 상황은 개발 현업에서 매우 자주 발생합니다.

  
  
### ❌ 폴링(Polling) 방식의 치명적인 한계

  
옵저버 패턴이 없을 때 입문자나 개발자들이 흔히 범하는 실수는 **"주기적으로 찔러보는 폴링(Polling) 방식"**입니다.

  
    
- **CPU 및 네트워크 대역폭 낭비:** 변화가 없는 99%의 시간 동안도 `while(true)` 나 주기적 `timer`, `DB polling query`를 실행하여 서버 자원을 불필요하게 소모합니다.
    
- **실시간성 저하 (Latency):** 주기적 폴링 간격(예: 1초, 5초) 사이에 일어난 상태 변화를 즉시 감지하지 못하고 지연이 발생합니다.
    
- **강한 결합도 (Tight Coupling):** 주체 객체가 소식 통지 대상을 일일이 클래스로 직접 알고 있어야 하므로, 수신 대상이 추가될 때마다 주체 코드를 직접 고쳐야 하는 **오픈-클로즈드 원칙(OCP) 위반**이 일어납니다.
  

  
## 2. 해결책 및 동작 메커니즘 (Solution & How It Works)

  
**옵저버 패턴(Observer Pattern)**은 `발행-구독(Publish-Subscribe)` 개념을 도입하여 이 문제를 근본적으로 해결합니다.

  
주체(Subject)는 직접 관찰자(Observer)들의 구체적인 클래스를 알 필요 없이, 단지 **"관찰자 목록(List<Observer>)에 수신자를 등록(register)받고, 상태가 변경되면 notification을 날리는 일"**만 전담합니다.

  
  
    
    
      
#### 📱 실제 서비스 동작 예시: 당*마켓 '키워드 알림'

      
판매자가 '아이폰15' 상품을 게시글로 올리는 순간, 알림 서버(`Subject`)가 이 키워드를 미리 구독(Register)해 둔 수만 명의 사용자 앱(`Observer`)으로 푸시 팝업을 즉시 능동 쏘아 올립니다.

      
      
🔄 **Working Flow:** 판매자 글 등록 ➔ Notification Event 발행 ➔ 키워드 구독자 목록 렌더링 ➔ 푸시 알림 수신

    

    
    
      
#### 🔔 쉬운 비유: 유튜브 채널 구독 및 알림 설정

      
유튜버(Subject)가 새 동영상을 올릴 때 100만 명 구독자 집집마다 전화를 거는 것이 아닙니다. 시청자가 '구독 & 알림설정'(Observer 등록)을 해두면 동영상 등록 이벤트 발생 시 시스템 알림망이 자동으로 수신 전파를 보냅니다.

      
      
🎯 **이점:** 발행자와 수신자 간 결합도를 획기적으로 낮춤 (Loose Coupling)

    
  

  
## 3. 옵저버 패턴의 장단점 및 ⚠️ 실무 주의점 (Memory Leak 함정)

  
  
### 👍 실무에서의 강력한 장점

  
    
- **느슨한 결합 (Loose Coupling):** Subject는 Observer가 내부적으로 어떻게 구현되었는지 몰라도 되며, 인터페이스 구현체이기만 하면 얼마든지 수신 객체를 추가/삭제할 수 있습니다.
    
- **실시간 이벤트 기반 시스템 구축:** 데이터 상태 변경 시 즉시 `notifyObservers()`가 전파되어 즉각적인 반응형 UI 및 비동기 파이프라인 처리가 가능해집니다.
  

  
### ⚠️ 실무자 경험담: 메모리 누수(Memory Leak) 경고! (Lapsed Listener Problem)

  
    
💡 실무에서 자주 범하는 치명적 메모리 누수 사고 사례

    

      옵저버 패턴을 쓸 때 Subject에 Observer를 `registerObserver(observer)`로 등록해 두면, Subject의 내부 리스트가 Observer의 참조(Reference)를 강하게 붙잡게 됩니다.
      이때 화면이 닫히거나 Observer 객체가 더 이상 쓰이지 않아도, **Subject 리스트에서 `removeObserver()`를 통해 등록을 해제해주지 않으면 자바 가비지 컬렉터(GC)가 이 Observer 객체를 절대 회수하지 못합니다!**
    

    

      🔑 **해결책:** 
      1) Component 소멸 시점(`onDestroy`, `close()`)에 명시적 `unregisterObserver()` 호출 필수.
      2) `WeakReference` (약한 참조) 기반의 옵저버 리스트 구조를 채택하�� GC 자동 회수 유도.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

  
아래 코드는 실제 뉴스 발행 시스템(Subject)과 뉴스 수신자(Observer)들이 등록/알림/해제되는 동작 과정을 그대로 담은 완벽한 자바 실행 코드입니다.

`import java.util.ArrayList;
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
        System.out.println("✅ [구독 완료] 새로운 옵저버가 ��록되었습니다.");
    }

    @Override
    public void removeObserver(Observer o) {
        observers.remove(o);
        System.out.println("❌ [구독 해제] 옵저버 등록이 정상 해제되었습니다. (메모리 누수 방지)");
    }

    @Override
    public void notifyObservers() {
        for (Observer observer : observers) {
            observer.update(latestNews);
        }
    }

    public void publishNews(String title) {
        this.latestNews = title;
        System.out.println("\n📢 [뉴스 발행] " + title);
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
        System.out.println("  ➔ 📱 [" + name + " 수신 알림]: " + newsTitle);
    }
}

// 5. 실행 테스트 (Main)
public class ObserverPatternMain {
    public static void main(String[] args) {
        NewsAgency agency = new NewsAgency();

        NewsSubscriber sub1 = new NewsSubscriber("구독자A (김철수)");
        NewsSubscriber sub2 = new NewsSubscriber("구독자B (이영희)");

        // 구독 신청
        agency.registerObserver(sub1);
        agency.registerObserver(sub2);

        // 첫 번째 뉴스 발행
        agency.publishNews("속보: 옵저버 패턴으로 실시간 알림 시스템 구축 성공!");

        // 구독자A 해제 (메모리 누수 예방)
        agency.removeObserver(sub1);

        // 두 번째 뉴스 발행 (이영희 구독자만 수신)
        agency.publishNews("긴급: Spring @EventListener 실무 적용 가이드 공개!");
    }
}
`

  
## 5. 실무 프레임워크 적용 사례 (Real-World Frameworks)

  
  
### 🌱 1) Spring Framework의 `@EventListener` & `ApplicationEventPublisher`

  스프링 프레임워크에서는 도메인 로직과 이벤트 로직을 완전히 분리하기 위해 옵저버 패턴 기반의 이벤트 게시판 시스템을 제공합니다.

  
    
- 회원가입 완료 시 `eventPublisher.publishEvent(new UserRegisteredEvent(user))` 발송
    
- 이메일 발송 서비스는 `@EventListener` 를 붙여 회원가입 로직과 상관없이 독립적으로 이벤트를 전달받아 이메일을 쏩니다.
  

  
### ⚡ 2) Reactive Programming (RxJava / Project Reactor)

  
현대 반응형 아키텍처(WebFlux, RxJava)에서 데이터를 스트림(Stream)으로 흘려보내고, `Mono`, `Flux` 객체를 `subscribe()` 하여 비동기로 수신하는 구조의 근본적인 뿌리가 바로 옵저버 패턴입니다.

  
## 6. 참고자료 (References)

  
    
- Inpa Dev Blog - GoF ���저버(Observer) 패턴 제대로 배워보자: [https://inpa.tistory.com/entry/GOF-...-옵저버-패턴](https://inpa.tistory.com/entry/GOF-%F0%9F%92%A0-%EC%98%B5%EC%A0%80%EB%B2%84Observer-%ED%8C%A8%ED%84%B4-%EC%A0%9C%EB%8C%80%EB%A1%9C-%EB%B0%B0%EC%9B%8C%EB%B3%B4%EC%9E%90)
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley)
    
- Refactoring.Guru - Observer Pattern: [https://refactoring.guru/design-patterns/observer](https://refactoring.guru/design-patterns/observer)
    
- Spring Framework Official Docs - Event Publication Mechanism
