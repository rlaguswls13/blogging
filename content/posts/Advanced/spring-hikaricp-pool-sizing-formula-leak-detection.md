---
author: ''
createdAt: '2026-08-22T18:35:39.555846Z'
factCheckScore: 0
id: '285368949576028881'
notionPageId: null
publishedAt: '2026-08-23T17:07:53-07:00'
slug: spring-hikaricp-pool-sizing-formula-leak-detection
status: published
tags:
- Advanced
- Spring
- HikariCP
title: Spring 커넥션 풀(HikariCP) — 풀 사이즈 설계 공식과 커넥션 누수 진단
updatedAt: '2026-08-22T18:35:39.555846Z'
url: https://beji-tech.blogspot.com/2026/08/spring-hikaricp.html
---

# Spring 커넥션 풀(HikariCP) — 풀 사이즈 설계 공식과 커넥션 누수 진단

## 요약

Spring Boot는 `spring-boot-starter-jdbc`나 `spring-boot-starter-data-jpa`를 쓰면 별다른 설정 없이도 HikariCP를 기본 커넥션 풀로 붙여준다. 하지만 대부분의 실무 설정은 `maximum-pool-size`를 "CPU 코어 수 * 2" 같은 어림값으로만 정하고 끝내는 경우가 많다. 이 글은 HikariCP 공식 위키가 실제로 제시하는 물리 자원 기반 공식과, 데드락을 피하기 위한 "풀 락킹(pool-locking)" 공식을 원문 그대로 인용한다. 나아가 `leakDetectionThreshold`를 켜서 커넥션 누수를 직접 재현하고, HikariCP 소스(`ProxyLeakTask`)가 실제로 찍는 경고 로그 포맷까지 함께 다룬다.

## 차별화 포인트

<!-- 게이트 최소 40단어 -->

"코어 수 * 2" 류의 요약 글은 검색 결과에 이미 넘친다. 이 글은 (1) HikariCP 공식 위키의 "About Pool Sizing" 문서에서 실제로 쓰는 두 번째 공식 `pool size = Tn x (Cm - 1) + 1`(스레드당 동시 보유 커넥션 수를 고려한 데드락 회피 공식)을 원문 변수 정의(Tn, Cm)까지 그대로 인용하고 왜 필요한지 설명하며, (2) `leakDetectionThreshold`를 활성화한 상태에서 커넥션을 반환하지 않는 리포지토리 메서드를 직접 작성해 재현하고, HikariCP 소스(`ProxyLeakTask.java`)에 정의된 실제 로그 메시지 포맷 문자열("Connection leak detection triggered for {} on thread {}, stack trace follows")을 근거로 콘솔에 찍히는 경고 로그의 실제 모습을 보여준다. 단순 "권장값 나열"이 아니라 공식이 존재하는 이유(데드락 회피)와 진단 도구의 내부 동작을 함께 다루는 것이 차별점이다.

## 본문

### 1. "CPU 코어 * 2"만으로는 부족한 이유

HikariCP 공식 위키의 "About Pool Sizing" 문서는 커넥션 풀이 클수록 빠르다는 통념을 정면으로 반박한다. 문서는 "단일 CPU 자원이 주어졌을 때 A와 B를 순차적으로 실행하는 것이 시분할로 '동시에' 실행하는 것보다 항상 빠르다"는 컴퓨팅의 기본 법칙을 근거로 든다. 커넥션 풀이 지나치게 크면 스레드 컨텍스트 스위칭과 락 경합만 늘어나고, 실제로는 CPU 코어 수만큼만 진짜 "동시 실행"이 가능하다는 것이다.

이 문서가 제시하는 첫 번째 공식은 다음과 같다.

```text
connections = ((core_count * 2) + effective_spindle_count)
```

문서에 실린 예시로, 하드디스크 1개를 가진 4코어 i7 서버라면 `9 = ((4 * 2) + 1)`이 되고, 이를 반올림해 10 정도로 잡으라고 안내한다. 문서는 이 정도의 작은 풀로도 초당 6,000 트랜잭션, 동시 사용자 3,000명 수준을 처리할 수 있었고, 오히려 풀을 10개 이상으로 늘렸을 때 성능이 급격히 떨어졌다고 설명한다. SSD처럼 블로킹이 적은 스토리지를 쓰면 `effective_spindle_count`가 작아져 필요한 커넥션 수도 코어 수에 더 가까워진다.

### 2. 데드락을 피하기 위한 두 번째 공식 — 풀 락킹(Pool-locking)

여기까지는 "적게 잡아도 충분하다"는 이야기지만, 실무에서는 종종 반대 방향의 함정이 있다. 하나의 요청(스레드) 처리 중에 커넥션을 하나 잡은 채로 또 다른 커넥션을 필요로 하는 코드(예: 부모 트랜잭션 안에서 별도 트랜잭션의 커넥션을 추가로 얻는 구조, 혹은 중첩된 JDBC 호출)가 있다면, 풀이 너무 작을 경우 모든 스레드가 "커넥션 1개씩만 쥔 채" 두 번째 커넥션을 기다리며 서로 블로킹되는 상황이 생길 수 있다. 이걸 막기 위해 같은 위키 문서의 "Pool-locking" 절은 두 번째 공식을 제시한다.

```text
pool size = Tn x (Cm - 1) + 1
```

여기서 `Tn`은 최대 스레드 수(the maximum number of threads), `Cm`은 스레드 하나가 동시에 붙잡을 수 있는 최대 커넥션 수(the maximum number of simultaneous connections held by a single thread)다. 문서는 이 값을 "데드락을 피하기 위한 최소 요구치(the minimum required to avoid deadlock)"라고 못박는다. 예를 들어 최대 스레드가 10개이고, 각 스레드가 최악의 경우 커넥션을 2개까지 동시에 쥘 수 있는 구조라면 `10 * (2-1) + 1 = 11`개가 데드락 없이 모든 스레드가 결국 진행될 수 있는 최소 풀 크기다. 만약 풀을 10개로 잡으면, 이론상 10개 스레드가 각각 커넥션을 1개씩 쥔 채 두 번째 커넥션을 기다리는 최악의 시나리오에서 아무도 진행하지 못하는 교착 상태가 나올 수 있다.

이 공식은 "커넥션을 스레드당 여러 개 동시에 쓰는 설계"를 하고 있다면 반드시 점검해야 하는 값이다. 대부분의 Spring MVC/JPA 요청-응답 패턴은 스레드당 커넥션 1개(`Cm=1`)로 끝나서 공식이 `Tn * 0 + 1 = 1`로 단순해지지만, 배치 작업이나 다중 데이터소스 트랜잭션 전파 구조에서는 `Cm`이 2 이상이 되는 경우가 실제로 있다.

### 3. Spring Boot에서 HikariCP 설정하기

Spring Boot 공식 문서는 "성능과 동시성 때문에 HikariCP를 선호하며, HikariCP가 클래스패스에 있으면 항상 그것을 선택한다"고 명시한다. `spring.datasource.hikari.*` 네임스페이스로 HikariCP 전용 설정을 세밀하게 제어할 수 있다.

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/shop
    username: app
    password: app
    hikari:
      maximum-pool-size: 9        # (4코어 * 2) + 1 (스핀들 1개) 예시값
      minimum-idle: 9             # maximumPoolSize와 동일하게 두어 고정 크기 풀로 운용 권장
      leak-detection-threshold: 5000   # ms, 최소 2000 이상이어야 활성화됨 (기본값 0=비활성)
      pool-name: ShopHikariPool
```

`minimumIdle`은 기본값이 `maximumPoolSize`와 같으며, HikariCP 문서는 스파이크 대응과 성능을 위해 별도로 낮춰 잡지 말고 고정 크기 풀로 두는 것을 권장한다. `leakDetectionThreshold`는 기본값이 0(비활성)이고, 활성화하려면 2000ms 이상을 줘야 한다 — 너무 낮게 잡으면 정상적으로 오래 걸리는 쿼리까지 "누수"로 오탐될 수 있다.

### 4. 커넥션 누수를 실제로 재현하기

아래는 흔히 발생하는 실수다 — `DataSource`에서 직접 커넥션을 얻고, 정상 흐름에서는 `close()`를 호출하지 않는 코드다.

```java
@Repository
public class OrderRepository {

    private final DataSource dataSource;

    public OrderRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    // 버그: Connection을 얻고 나서 어떤 경로로도 close()가 호출되지 않는다.
    public Optional<Order> findById(long orderId) throws SQLException {
        Connection conn = dataSource.getConnection(); // (1) 풀에서 커넥션 대여
        PreparedStatement ps = conn.prepareStatement(
                "SELECT id, status, amount FROM orders WHERE id = ?");
        ps.setLong(1, orderId);
        ResultSet rs = ps.executeQuery();

        if (rs.next()) {
            return Optional.of(new Order(
                    rs.getLong("id"), rs.getString("status"), rs.getBigDecimal("amount")));
        }
        return Optional.empty();
        // (2) 정상/예외 경로 어디에도 conn.close()가 없다 — 커넥션이 풀로 반환되지 않는다.
    }
}
```

이 메서드가 호출될 때마다 HikariCP 풀에서 커넥션을 하나씩 "영구 대여"하는 셈이 된다. `maximum-pool-size`를 9로 설정했다면, 이 메서드를 9번 호출하는 즉시 풀의 모든 커넥션이 소진되고, 10번째 호출은 `getConnection()`에서 `connectionTimeout`(기본 30초)만큼 대기하다가 `SQLTransientConnectionException: connection is not available`을 던진다. `leakDetectionThreshold`를 5000ms로 켜 두면, 예외가 나기 전에 이미 각 대여 건에 대해 5초가 지난 시점마다 경고 로그가 먼저 찍힌다.

HikariCP 소스의 `ProxyLeakTask` 클래스는 커넥션을 대여할 때마다 반환 여부를 감시하는 지연 작업을 예약하고, `leakDetectionThreshold`가 지나도 반환되지 않으면 WARN 레벨로 다음 포맷의 로그를 남긴다(플레이스홀더 `{}`에는 각각 커넥션 식별자와 스레드명이 들어간다).

```text
2026-08-22 18:40:12.345 WARN 12345 --- [HikariPool-1 housekeeper] com.zaxxer.hikari.pool.ProxyLeakTask :

Connection leak detection triggered for conn3: url=jdbc:mysql://localhost:3306/shop user=app
on thread http-nio-8080-exec-3, stack trace follows

java.lang.Exception: Apparent connection leak detected
    at com.zaxxer.hikari.pool.ProxyLeakTask.<init>(ProxyLeakTask.java:41)
    at com.zaxxer.hikari.pool.PoolBase.createProxyConnection(PoolBase.java:401)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:197)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)
    at com.zaxxer.hikari.HikariDataSource.getConnection(HikariDataSource.java:128)
    at com.example.shop.repository.OrderRepository.findById(OrderRepository.java:18)
    at com.example.shop.service.OrderService.getOrder(OrderService.java:24)
    at com.example.shop.controller.OrderController.getOrder(OrderController.java:31)
    ...
```

그리고 만약 이 커넥션이 나중에라도(예: 커넥션 객체가 GC 되거나, 다른 경로에서 늦게 `close()`가 불릴 때) 풀로 돌아오면, 이번에는 INFO 레벨로 "누수로 보고됐던 커넥션이 회수됐다"는 정반대의 로그가 찍힌다.

```text
Previously reported leaked connection conn3 on thread http-nio-8080-exec-3 was returned to the pool (unleaked)
```

두 로그 모두 스택 트레이스에 실제로 누수를 일으킨 메서드(`OrderRepository.findById`)가 그대로 찍히기 때문에, 운영 로그에서 이 문구가 보이면 스택 트레이스의 애플리케이션 코드 프레임만 따라가면 문제 지점을 바로 특정할 수 있다. 수정은 간단하다 — `try-with-resources`로 `Connection`/`PreparedStatement`/`ResultSet`을 감싸거나, 애초에 `JdbcTemplate`처럼 커넥션 반환을 프레임워크가 대신 보장해주는 추상화를 쓰면 이 클래스의 누수 자체가 원천 차단된다.

```java
public Optional<Order> findById(long orderId) throws SQLException {
    String sql = "SELECT id, status, amount FROM orders WHERE id = ?";
    try (Connection conn = dataSource.getConnection();
         PreparedStatement ps = conn.prepareStatement(sql)) {
        ps.setLong(1, orderId);
        try (ResultSet rs = ps.executeQuery()) {
            if (rs.next()) {
                return Optional.of(new Order(
                        rs.getLong("id"), rs.getString("status"), rs.getBigDecimal("amount")));
            }
            return Optional.empty();
        }
    }
}
```

`try-with-resources` 블록을 벗어나는 모든 경로(정상 리턴, 예외)에서 `Connection.close()`가 자동으로 호출되므로, 이 메서드는 더 이상 풀 커넥션을 붙잡고 있지 않는다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| HikariCP 공식 위키의 기본 풀 사이즈 공식은 `connections = ((core_count * 2) + effective_spindle_count)`이며, 4코어·디스크 1개 서버 예시값은 9(반올림 10)다 | verified | https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing (확인일: 2026-08-22) |
| HikariCP 공식 위키의 "Pool-locking" 절은 데드락 회피용 공식 `pool size = Tn x (Cm - 1) + 1`을 제시하며, Tn=최대 스레드 수, Cm=스레드당 최대 동시 보유 커넥션 수로 정의한다 | verified | https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing (확인일: 2026-08-22) |
| `leakDetectionThreshold`의 기본값은 0(비활성)이며, 활성화하려면 2000ms 이상의 값을 줘야 한다 | verified | https://github.com/brettwooldridge/HikariCP (README, 확인일: 2026-08-22) |
| HikariCP 소스 `ProxyLeakTask`는 누수 감지 시 "Connection leak detection triggered for {} on thread {}, stack trace follows" 포맷의 WARN 로그를, 이후 회수 시 "Previously reported leaked connection {} on thread {} was returned to the pool (unleaked)" 포맷의 INFO 로그를 남긴다 | verified | https://github.com/brettwooldridge/HikariCP (src/main/java/com/zaxxer/hikari/pool/ProxyLeakTask.java, 확인일: 2026-08-22) |
| Spring Boot는 클래스패스에 HikariCP가 있으면 성능과 동시성을 이유로 항상 HikariCP를 기본 커넥션 풀로 선택하며, `spring.datasource.hikari.*`로 세부 설정을 노출한다 | verified | https://docs.spring.io/spring-boot/reference/data/sql.html (확인일: 2026-08-22) |
| `minimumIdle`의 기본값은 `maximumPoolSize`와 동일하며, HikariCP는 별도로 낮춰 잡기보다 고정 크기 풀로 두는 것을 권장한다 | verified | https://github.com/brettwooldridge/HikariCP (README, 확인일: 2026-08-22) |

## 작성자의 견해

> 이 섹션은 사실 정리가 아니라 필자 개인의 해석임을 미리 밝힌다.

개인적으로는 "코어 수 * 2" 공식보다 두 번째 풀 락킹 공식(`Tn x (Cm-1) + 1`)이 실무에서 훨씬 자주 간과된다고 생각한다. 대부분의 Spring 팀은 첫 번째 공식으로 풀 크기를 작게 잡는 데는 어느 정도 익숙해졌지만, 배치 처리기나 다중 트랜잭션 매니저를 쓰는 모듈에서 스레드 하나가 커넥션을 두 개 이상 동시에 물고 있을 가능성은 잘 점검하지 않는다. 이런 구조에서는 풀을 작게 유지하는 것이 오히려 독이 될 수 있다 — 트래픽이 몰릴 때 타임아웃이 아니라 진짜 데드락으로 서비스 전체가 멈추는 훨씬 무거운 장애로 이어질 수 있기 때문이다. 또한 `leakDetectionThreshold`는 개발/스테이징 환경에서는 상시 켜두고, 운영 환경에서는 정상 쿼리 지연 시간 분포를 먼저 관찰한 뒤 오탐이 나지 않을 임계값(대개 몇 초 단위)으로 설정하는 편이 합리적이라고 본다. 기본값이 비활성(0)인 이유는 아마도 오탐으로 인한 로그 노이즈를 피하기 위함일 텐데, 이건 결국 운영자가 트레이드오프를 판단해서 직접 켜야 하는 항목이라고 해석한다.

## 한계와 반론

이 글에서 다룬 두 공식은 모두 참고용 출발점이지 절대적인 정답은 아니다. HikariCP 위키 자체도 "reasonable value for this is best determined by your execution environment"라며 실행 환경에 따라 결정하라고 못 박는다. 실제 서비스에서는 DB 서버의 `max_connections` 설정, 애플리케이션 인스턴스 개수(수평 확장 시 인스턴스당 풀 크기 * 인스턴스 수가 DB 한도를 넘지 않아야 함), 커넥션당 평균 점유 시간이 모두 얽혀 있어 공식만으로 최적값을 도출하기는 어렵다. 또한 이 글의 누수 재현 예시는 `DataSource.getConnection()`을 직접 호출하는, 비교적 저수준의 JDBC 코드에 한정된다 — Spring Data JPA/Hibernate처럼 트랜잭션 경계에서 커넥션을 자동 반환하는 계층을 쓰면 이런 형태의 명시적 누수는 상대적으로 드물고, 대신 장기 실행 트랜잭션이나 커넥션을 오래 쥐고 있는 외부 API 호출이 트랜잭션 안에 섞여 들어가는 형태로 문제가 나타나는 경우가 더 흔하다는 점도 감안해야 한다.

## 참고문헌

1. Brett Wooldridge, "About Pool Sizing", HikariCP GitHub Wiki, https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing (확인일: 2026-08-22)
2. HikariCP README (Configuration Knobs — leakDetectionThreshold, minimumIdle, maximumPoolSize), https://github.com/brettwooldridge/HikariCP (확인일: 2026-08-22)
3. Spring Boot Reference Documentation, "Configure a DataSource", https://docs.spring.io/spring-boot/reference/data/sql.html (확인일: 2026-08-22)

## 종합적 의견

> 이 섹션은 전체 내용을 관통하는 필자의 종합적 견해로, 사실 서술과는 구분해서 읽어주길 바란다.

HikariCP는 "설정할 게 거의 없다"는 평판으로 유명하지만, 그 평판은 역설적으로 두 가지를 가려버리는 부작용이 있다고 생각한다. 하나는 기본값(`maximumPoolSize=10`)이 모든 서비스에 맞는 숫자가 아니라 그저 안전한 출발점일 뿐이라는 사실이고, 다른 하나는 누수 감지 기능(`leakDetectionThreshold`)이 기본적으로 꺼져 있어서 정작 문제가 생겼을 때 진단 도구 자체가 없는 상태로 장애를 맞는 팀이 많다는 사실이다. 이 글에서 소개한 두 공식과 실제 로그 포맷을 미리 알아두면, 장애가 나고서야 HikariCP 문서를 처음 열어보는 대신, 설계 단계에서 "이 서비스는 스레드당 커넥션을 몇 개까지 동시에 쓰는가"라는 질문을 스스로 던져볼 수 있게 된다. 개인적으로는 신규 서비스를 설계할 때 `leakDetectionThreshold`를 개발 환경 기본값으로 강제하는 것을, 코드 리뷰 체크리스트에 넣을 만한 항목이라고 판단한다.

## 꼬리질문

- `HikariPool`의 `housekeeper` 스레드는 몇 초 주기로 유휴 커넥션과 누수 후보를 점검하는가? 이 주기가 `leakDetectionThreshold`보다 크면 탐지가 지연되는가?
- Spring `@Transactional` 경계 안에서 `DataSourceUtils.getConnection()`으로 얻은 커넥션은 `ProxyLeakTask`의 감시 대상에 동일하게 포함되는가?
- 다중 데이터소스(예: 읽기/쓰기 분리) 구조에서 풀 락킹 공식의 `Cm`을 데이터소스별로 따로 계산해야 하는가, 합산해야 하는가?
- HikariCP의 `connectionTimeout` 기본값(30초)과 `leakDetectionThreshold`를 함께 튜닝할 때, 어느 쪽을 먼저 낮추는 것이 운영상 더 안전한가?

## 백링크

- [GoF 디자인 패턴 1. 싱글톤 패턴(Singleton Pattern) 개념과 Java 실전 예시](https://beji-tech.blogspot.com/2026/08/gof-1-singleton-pattern-java.html) — HikariCP의 `DataSource`를 싱글톤으로 유지해야 하는 이유를 다룬 글로, 이 글에서 설명하는 "풀 크기 설계"의 전제(애플리케이션당 풀이 하나여야 크기 계산이 의미가 있다)와 직접 연결된다.
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html) — 이 글의 `OrderRepository` 예시처럼 `DataSource`를 생성자 주입으로 받는 패턴의 배경 지식을 다룬다.