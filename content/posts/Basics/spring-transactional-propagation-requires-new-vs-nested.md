---
author: ''
createdAt: '2026-08-22T18:34:28.967291Z'
factCheckScore: 0
id: '3256622525429505094'
notionPageId: null
publishedAt: '2026-08-23T17:05:37-07:00'
slug: spring-transactional-propagation-requires-new-vs-nested
status: published
tags:
- Basics
- Spring
- Transaction
title: Spring @Transactional 전파 옵션(Propagation) — REQUIRES_NEW vs NESTED 실전 차이
updatedAt: '2026-08-22T18:34:28.967291Z'
url: https://beji-tech.blogspot.com/2026/08/spring-transactional-propagation.html
---

# Spring @Transactional 전파 옵션(Propagation) — REQUIRES_NEW vs NESTED 실전 차이

## 요약

Spring의 `@Transactional`에는 7가지 전파(Propagation) 옵션이 있지만, 실무에서 진짜 헷갈리는 건 그중 딱 두 개, `REQUIRES_NEW`와 `NESTED`입니다. 둘 다 트랜잭션 경계를 새로 만들지만, 메커니즘은 전혀 다릅니다. 이 글은 7개 옵션을 전부 나열하는 대신, "외부 트랜잭션이 롤백돼도 반드시 남아야 하는 감사 로그(Audit Log)"라는 구체적 시나리오 하나로 두 옵션의 실제 동작 차이를 코드로 재현하고, `NESTED`가 JDBC 세이브포인트를 지원하는 트랜잭션 매니저에서만 동작하며 JPA(Hibernate) 환경에서는 기본적으로 예외를 던진다는, 실제 스프링 소스코드로 확인한 저평가된 함정을 다룹니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨).
-->

동일 주제의 검색 상위 글 대부분은 7개 전파 옵션을 표로 나열하고 "NESTED는 세이브포인트를 쓴다" 한 줄로 끝냅니다. 이 글은 다릅니다. 첫째, `REQUIRES_NEW`/`NESTED`만 골라 "감사 로그가 외부 트랜잭션 롤백에도 살아남아야 한다"는 실제 프로덕션 요구사항 시나리오로 두 옵션을 직접 실행 가능한 JdbcTemplate 코드로 대조합니다. 둘째, "NESTED는 조용히 REQUIRES_NEW처럼 동작한다"는 흔한 블로그 서술을 그대로 옮기지 않고, Spring Framework GitHub 소스(`AbstractPlatformTransactionManager`, `DataSourceTransactionManager`, `JpaTransactionManager`)를 직접 열어 실제로는 `NestedTransactionNotSupportedException`이라는 명시적 런타임 예외가 발생한다는 사실을 원문 인용으로 정정합니다. 셋째, 같은 애노테이션·같은 코드가 DataSourceTransactionManager(JDBC 단독)에서는 정상 동작하다가 spring-boot-starter-data-jpa를 추가하는 순간(JpaTransactionManager로 자동 전환) 런타임에서만 깨지는, 컴파일 타임에 잡히지 않는 실무 함정을 짚습니다.

## 본문

### 1. 왜 이 둘만 헷갈리는가

Spring의 `Propagation` 열거형에는 `REQUIRED`, `REQUIRES_NEW`, `NESTED`, `SUPPORTS`, `NOT_SUPPORTED`, `MANDATORY`, `NEVER` 7개 값이 있습니다. 이 중 대부분은 "트랜잭션이 있으면 참여/없으면 무엇을 할지"를 정하는 단순한 규칙이지만, `REQUIRES_NEW`와 `NESTED`는 공통적으로 "지금 실행 중인 코드 블록만 독립적으로 롤백시킬 수 있다"는 인상을 줍니다. 그래서 많은 개발자가 이 둘을 "거의 같은데 NESTED가 더 가벼운 버전" 정도로 오해합니다. 실제로는 물리 트랜잭션의 개수 자체가 다릅니다.

- `REQUIRES_NEW`: 기존 트랜잭션을 일시 중단(suspend)하고, 완전히 독립된 새 물리 트랜잭션(새 DB 커넥션)을 시작합니다. 두 트랜잭션은 서로 다른 커밋/롤백 생명주기를 가집니다.
- `NESTED`: 기존 트랜잭션이 있으면 그 **단일 물리 트랜잭션 안에서** JDBC 세이브포인트(Savepoint)를 찍습니다. 물리 트랜잭션은 하나뿐이고, 세이브포인트는 그 안의 되돌리기 지점일 뿐입니다.

Spring 공식 레퍼런스는 이 차이를 다음과 같이 명시합니다.

> "PROPAGATION_REQUIRES_NEW ... always uses an independent physical transaction for each affected transaction scope ... the underlying resource transactions are different and, hence, can commit or roll back independently, with an outer transaction not affected by an inner transaction's rollback status." — Spring Framework Reference, Transaction Propagation

> "PROPAGATION_NESTED uses a single physical transaction with multiple savepoints that it can roll back to. ... This setting is typically mapped onto JDBC savepoints, so it works only with JDBC resource transactions." — Spring Framework Reference, Transaction Propagation

### 2. 실전 시나리오: 롤백돼도 살아남아야 하는 감사 로그

"주문 처리 트랜잭션이 실패해도, '주문을 시도했다'는 감사 로그(Audit Log)는 반드시 DB에 남아야 한다"는 흔한 요구사항으로 두 옵션을 직접 비교해 보겠습니다. `AuditLogService`에 같은 로직을 전파 옵션만 다르게 두 벌 만듭니다.

```java
@Service
public class AuditLogService {

    private final JdbcTemplate jdbcTemplate;

    public AuditLogService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logWithRequiresNew(String action, String detail) {
        jdbcTemplate.update(
            "INSERT INTO audit_log (action, detail, created_at) VALUES (?, ?, NOW())",
            action, detail);
    }

    @Transactional(propagation = Propagation.NESTED)
    public void logWithNested(String action, String detail) {
        jdbcTemplate.update(
            "INSERT INTO audit_log (action, detail, created_at) VALUES (?, ?, NOW())",
            action, detail);
    }
}
```

```java
@Service
public class OrderService {

    private final JdbcTemplate jdbcTemplate;
    private final AuditLogService auditLogService;

    public OrderService(JdbcTemplate jdbcTemplate, AuditLogService auditLogService) {
        this.jdbcTemplate = jdbcTemplate;
        this.auditLogService = auditLogService;
    }

    @Transactional
    public void placeOrderThenFail(boolean useRequiresNew) {
        jdbcTemplate.update(
            "INSERT INTO orders (product, status) VALUES (?, 'PENDING')", "keyboard");

        if (useRequiresNew) {
            auditLogService.logWithRequiresNew("ORDER_ATTEMPT", "keyboard order attempted");
        } else {
            auditLogService.logWithNested("ORDER_ATTEMPT", "keyboard order attempted");
        }

        // 재고 확인 실패로 외부(주문) 트랜잭션 전체를 롤백시키는 상황을 재현한다.
        throw new IllegalStateException("재고 부족: 주문을 처리할 수 없습니다");
    }
}
```

`placeOrderThenFail(true)`를 호출하면(REQUIRES_NEW 경로) 결과는 이렇습니다: `orders` 테이블의 INSERT는 외부 트랜잭션과 함께 롤백되어 사라지지만, `audit_log`의 INSERT는 이미 별도의 물리 트랜잭션으로 커밋을 마쳤기 때문에 **그대로 남습니다**. 외부 트랜잭션의 예외는 이미 커밋된 독립 트랜잭션에 영향을 줄 수 없습니다.

반면 `placeOrderThenFail(false)`를 호출하면(NESTED 경로) 결과가 다릅니다: `IllegalStateException`이 세이브포인트 이후 코드에서 발생하지만, 이 예외를 아무도 잡지 않고 그대로 전파(propagate)시켰기 때문에 `AbstractPlatformTransactionManager`는 세이브포인트 롤백이 아니라 **물리 트랜잭션 전체**를 롤백합니다. `audit_log` INSERT는 세이브포인트 "이후"에 실행됐을 뿐, 여전히 같은 물리 트랜잭션·같은 커넥션에 속해 있으므로 함께 사라집니다. "NESTED니까 REQUIRES_NEW처럼 살아남겠지"라고 기대했다면 정확히 틀립니다.

### 3. NESTED가 실제로 보호하는 방향은 반대다

NESTED의 진짜 용도는 "내부 실패로부터 외부를 지키는 것"이지 "외부 실패로부터 내부를 지키는 것"이 아닙니다. 즉, 세이브포인트 이후 코드에서 예외가 나도 **그 예외를 호출부에서 잡아서** 세이브포인트로만 되돌리면, 바깥 트랜잭션은 계속 진행해 정상적으로 커밋될 수 있습니다.

```java
@Transactional
public void placeOrderPartialTolerant() {
    jdbcTemplate.update(
        "INSERT INTO orders (product, status) VALUES (?, 'PENDING')", "keyboard");

    try {
        auditLogService.logWithNested("ORDER_ATTEMPT", "keyboard order attempted");
    } catch (DataAccessException ex) {
        // 세이브포인트로만 롤백되고, 바깥 주문 트랜잭션은 영향받지 않고 계속 진행된다.
        log.warn("감사 로그 기록 실패, 세이브포인트로 롤백하고 주문은 계속 진행", ex);
    }

    jdbcTemplate.update("UPDATE orders SET status = 'CONFIRMED' WHERE product = ?", "keyboard");
}
```

이 코드에서는 `logWithNested` 호출이 실패해도(예: 감사 로그 테이블 제약조건 위반) `orders` 트랜잭션 자체는 커밋됩니다. 반대로 첫 번째 시나리오처럼 예외를 잡지 않고 흘려보내면 세이브포인트 구간과 물리 트랜잭션 전체가 함께 롤백됩니다. 이 "예외를 잡느냐 마느냐"에 따라 결과가 완전히 달라진다는 점이 NESTED를 REQUIRES_NEW와 혼동하게 만드는 근본 원인입니다.

### 4. 진짜 함정: 세이브포인트를 지원하는 트랜잭션 매니저가 필요하다

여기까지는 두 옵션의 롤백 범위 차이였고, 더 저평가된 함정은 따로 있습니다. `NESTED`는 아무 트랜잭션 매니저에서나 동작하지 않습니다. Spring GitHub 소스를 보면, JDBC 전용 `DataSourceTransactionManager`는 생성자에서 `setNestedTransactionAllowed(true)`를 호출해 기본적으로 세이브포인트 기반 NESTED를 허용합니다(단, 실제 JDBC 드라이버가 `java.sql.Savepoint`를 지원해야 합니다).

반면 JPA(Hibernate)를 쓸 때 자동 구성되는 `JpaTransactionManager`는 정반대입니다. 공식 Javadoc은 다음과 같이 명시합니다.

> "This transaction manager supports nested transactions via JDBC Savepoints. The 'nestedTransactionAllowed' flag defaults to 'false' ... Note that JPA itself does not support nested transactions! Hence, do not expect JPA access code to semantically participate in a nested transaction." — `JpaTransactionManager` Javadoc, Spring Framework

`nestedTransactionAllowed`가 `false`인 상태에서 `NESTED`를 쓰면 `AbstractPlatformTransactionManager.handleExistingTransaction()`이 `NestedTransactionNotSupportedException`을 던집니다("Transaction manager does not allow nested transactions by default"). 즉 "조용히 REQUIRES_NEW처럼 동작"하는 게 아니라 **명시적인 런타임 예외**로 실패합니다. 다만 이게 왜 위험하냐면: 컴파일 타임에는 전혀 드러나지 않기 때문입니다. JDBC 기반(예: MyBatis, JdbcTemplate만 쓰는 프로젝트)에서 멀쩡히 동작하던 `@Transactional(propagation = Propagation.NESTED)` 코드가, 나중에 `spring-boot-starter-data-jpa`를 추가해 트랜잭션 매니저가 `JpaTransactionManager`로 자동 전환되는 순간 해당 메서드가 처음 호출될 때 예외를 던집니다. 테스트 커버리지가 그 경로를 놓치면 프로덕션에서야 발견됩니다.

`nestedTransactionAllowed`를 수동으로 `true`로 켜더라도 완전히 안전해지는 건 아닙니다. Javadoc이 명시하듯 JPA 자체는 중첩 트랜잭션 개념이 없으므로, JDBC 커넥션 레벨의 세이브포인트는 롤백되어도 `EntityManager`의 영속성 컨텍스트(1차 캐시)는 그 롤백을 인지하지 못합니다. 세이브포인트 이전에 영속화한 엔티티의 메모리 상태와 실제 DB 상태가 어긋날 수 있다는 뜻입니다.

### 5. 프록시 기반 AOP와의 연결점

`REQUIRES_NEW`와 `NESTED` 모두 Spring AOP의 프록시(Proxy)를 거쳐야만 적용됩니다. 같은 클래스 안에서 `this.logWithNested(...)`처럼 자기 자신을 직접 호출(self-invocation)하면 프록시를 우회하기 때문에 전파 옵션 자체가 무시되고 그냥 같은 트랜잭션 안에서 실행됩니다. 반드시 위 예제처럼 다른 빈(`AuditLogService`)에 주입받아 호출해야 합니다. 이 프록시 메커니즘 자체(JDK Dynamic Proxy vs CGLIB)에 대한 자세한 내용은 [Spring AOP와 프록시 아키텍처 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)에서 다뤘습니다.

### 6. 실무 가이드

정리하면: "실패해도 절대 사라지면 안 되는 독립적인 기록"(감사 로그, 결제 시도 이력 등)에는 `REQUIRES_NEW`를 씁니다. 대신 커넥션 풀 고갈 위험이 있으니(공식 문서가 명시적으로 경고합니다) 남발하지 않습니다. "일부 하위 작업이 실패해도 전체를 계속 진행하고 싶은" 부분 허용 시나리오에는 `NESTED`가 어울리지만, 반드시 예외를 호출부에서 잡아야 하고, 프로젝트의 `PlatformTransactionManager` 구현체가 세이브포인트를 실제로 지원하는지(JDBC 단독 vs JPA) 먼저 확인해야 합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| PROPAGATION_REQUIRES_NEW은 항상 독립된 새 물리 트랜잭션을 생성하며, 외부 트랜잭션의 롤백 상태와 무관하게 독립적으로 커밋/롤백된다 | verified | Spring Framework Reference, "Transaction Propagation" https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html (확인일: 2026-08-23) |
| PROPAGATION_NESTED은 단일 물리 트랜잭션 안에서 JDBC 세이브포인트를 사용하며, JDBC 리소스 트랜잭션에서만 동작한다 | verified | Spring Framework Reference, 동일 URL https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html + Propagation Javadoc https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/annotation/Propagation.html (확인일: 2026-08-23) |
| DataSourceTransactionManager는 생성자에서 setNestedTransactionAllowed(true)를 호출해 기본적으로 세이브포인트 기반 NESTED를 허용한다(단, JDBC 드라이버가 Savepoint를 지원해야 함) | verified | Spring Framework 소스코드, DataSourceTransactionManager.java https://github.com/spring-projects/spring-framework/blob/main/spring-jdbc/src/main/java/org/springframework/jdbc/datasource/DataSourceTransactionManager.java (확인일: 2026-08-23) |
| JpaTransactionManager는 nestedTransactionAllowed 기본값이 false이며, JPA 자체는 중첩 트랜잭션을 지원하지 않는다(세이브포인트를 켜도 EntityManager 영속성 컨텍스트는 참여하지 않음) | verified | JpaTransactionManager Javadoc https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/orm/jpa/JpaTransactionManager.html (확인일: 2026-08-23) |
| nestedTransactionAllowed가 false인 상태에서 PROPAGATION_NESTED을 쓰면 AbstractPlatformTransactionManager가 NestedTransactionNotSupportedException을 명시적으로 던진다(조용히 다른 전파로 대체되지 않는다) | verified | Spring Framework 소스코드, AbstractPlatformTransactionManager.java https://github.com/spring-projects/spring-framework/blob/main/spring-tx/src/main/java/org/springframework/transaction/support/AbstractPlatformTransactionManager.java (확인일: 2026-08-23) |
| PROPAGATION_REQUIRES_NEW은 커넥션 풀 크기가 동시 스레드 수보다 여유롭지 않으면 커넥션 고갈이나 데드락을 유발할 수 있다 | verified | Spring Framework Reference, "Transaction Propagation" 경고문 https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html (확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 나열이 아니라 실제로 소스를 뒤져본 뒤의 개인적 해석과 견해임을 밝힙니다.

개인적으로 `NESTED`는 스프링 전파 옵션 중 가장 "설명은 쉬운데 실제로는 위험한" 옵션이라고 생각합니다. "세이브포인트로 부분 롤백"이라는 한 줄 설명만 들으면 REQUIRES_NEW보다 가볍고 안전해 보이지만, 실제로는 (1) 예외를 잡아야만 의도한 효과가 나고, (2) 트랜잭션 매니저 구현체에 따라 아예 지원되지 않을 수 있고, (3) 그 실패가 컴파일 타임이 아니라 특정 코드 경로가 처음 실행되는 런타임에만 드러난다는, 세 가지 함정이 겹쳐 있습니다. 특히 세 번째가 가장 실무에서 위험하다고 봅니다 — JDBC 단독 프로젝트에서 잘 동작하던 코드를 JPA 기반 프로젝트에 그대로 복사해 넣었다가 프로덕션에서야 `NestedTransactionNotSupportedException`을 처음 보는 팀을 실제로 본 적이 있습니다. 그래서 저는 팀 컨벤션 차원에서 "정말 부분 롤백이 필요하다는 게 명확히 검증된 경우"가 아니면 NESTED 대신 REQUIRES_NEW + try-catch 조합으로 통일하는 쪽을 선호합니다. 예측 가능성이 스마트함보다 우선한다는 게 제 견해입니다.

## 한계와 반론

이 글의 코드 예제는 `JdbcTemplate` + `DataSourceTransactionManager` 조합을 기준으로 검증했으며, MyBatis나 다른 JDBC 기반 프레임워크에서의 세부 동작까지 전부 재현하지는 않았습니다. 또한 세이브포인트 생성/롤백에 따른 성능 오버헤드는 벤치마크로 다루지 않았는데, 이는 DB 벤더·드라이버별 편차가 커서 일반화하기 어렵기 때문입니다. 반론도 있을 수 있습니다: 일부 팀은 "REQUIRES_NEW로 통일하라"는 작성자의 견해에 반대하며, 커넥션 풀 고갈 위험이 있는 REQUIRES_NEW보다 JDBC 단일 트랜잭션 매니저 환경이 확실하다면 NESTED가 커넥션 자원 측면에서 더 효율적이라고 주장할 수 있습니다. 이는 타당한 트레이드오프이며, 이 글은 "어느 쪽이 항상 옳다"가 아니라 "두 옵션의 실제 동작과 전제 조건을 정확히 알고 선택하라"는 데 초점을 둡니다.

## 참고문헌

1. Spring Framework Reference Documentation, "Transaction Propagation" — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html (확인일: 2026-08-23)
2. Spring Framework Javadoc, `Propagation` (annotation enum) — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/annotation/Propagation.html (확인일: 2026-08-23)
3. Spring Framework Javadoc, `JpaTransactionManager` — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/orm/jpa/JpaTransactionManager.html (확인일: 2026-08-23)
4. Spring Framework 소스코드, `AbstractPlatformTransactionManager.java` / `DataSourceTransactionManager.java` (spring-projects/spring-framework, main 브랜치) — https://github.com/spring-projects/spring-framework/blob/main/spring-tx/src/main/java/org/springframework/transaction/support/AbstractPlatformTransactionManager.java , https://github.com/spring-projects/spring-framework/blob/main/spring-jdbc/src/main/java/org/springframework/jdbc/datasource/DataSourceTransactionManager.java (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 개인적 해석을 담고 있으며, 실제 프로젝트 상황에 따라 결론이 달라질 수 있다는 사견임을 밝힙니다.

REQUIRES_NEW와 NESTED는 "둘 다 부분적으로 트랜잭션을 분리한다"는 표면적 유사성 때문에 실무에서 가장 자주 오용되는 전파 옵션 조합이라고 생각합니다. 이번에 소스코드까지 직접 확인하면서 새롭게 느낀 점은, Spring 팀이 이미 이 위험성을 알고 Javadoc과 레퍼런스 문서에 상당히 구체적으로 경고해 뒀는데도(커넥션 풀 고갈 경고, JPA 미지원 경고 모두 공식 문서에 명시돼 있습니다) 정작 이 정보가 실무 개발자들에게는 잘 전달되지 않는다는 점입니다. 이는 "NESTED가 REQUIRES_NEW의 가벼운 버전"이라는 식으로 단순화한 요약 콘텐츠가 검색 결과 상위를 차지하면서, 정작 전제 조건(트랜잭션 매니저 종류, 예외 처리 위치)은 생략되기 때문이라고 봅니다. 결국 두 옵션 중 무엇을 쓰든, 실제로 로컬에서 롤백 시나리오를 직접 실행해 DB 상태를 확인해 보는 것이 문서만 읽는 것보다 훨씬 신뢰할 수 있는 검증 방법이라는 게 이 글을 쓰며 다시 확인한 결론입니다.

## 꼬리질문

- `NESTED`를 여러 단계로 중첩(세이브포인트 안에 또 세이브포인트)하면 롤백 순서와 범위는 어떻게 되는가?
- Kotlin coroutine 기반 `suspend` 함수와 `@Transactional(propagation = REQUIRES_NEW)`를 함께 쓸 때 스레드 전환으로 인한 트랜잭션 컨텍스트 유실 위험은 없는가?
- R2DBC(리액티브) 스택에서는 REQUIRES_NEW/NESTED에 대응하는 전파 개념이 어떻게 구현되어 있는가?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)