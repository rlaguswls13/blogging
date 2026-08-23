---
author: ''
createdAt: '2026-08-22T18:33:18.549867Z'
factCheckScore: 0
id: '8786507852850674084'
notionPageId: null
publishedAt: '2026-08-22T16:19:17-07:00'
slug: java-checked-vs-unchecked-exception-spring-dataaccessexception
status: published
tags:
- Basics
- Java
- Exception
- Spring
title: Java 예외 처리 전략 — Checked vs Unchecked Exception, 언제 무엇을 쓸 것인가
updatedAt: '2026-08-22T18:33:18.549867Z'
url: https://beji-tech.blogspot.com/2026/08/java-checked-vs-unchecked-exception.html
---

# Java 예외 처리 전략 — Checked vs Unchecked Exception, 언제 무엇을 쓸 것인가

## 요약

Checked exception과 unchecked exception의 차이는 "컴파일러가 처리를 강제하는가"라는 문법적 사실 하나뿐이지만, 이 선택이 실무 코드베이스에 미치는 영향은 훨씬 크다. 이 글은 정의 나열에서 멈추지 않고, JDBC의 `SQLException`은 checked인데 Spring의 `DataAccessException`은 왜 unchecked로 설계됐는지를 Rod Johnson의 원래 논리와 Spring 공식 문서를 근거로 추적한다. Checked exception이 호출 스택을 타고 여러 계층의 메서드 시그니처를 오염시키는 과정, 그리고 그 압박이 결국 "예외 삼킴(exception swallowing)"이라는 안티패턴으로 귀결되는 구체적인 코드 흐름을 before/after로 비교하고, 언제 checked를 쓰고 언제 unchecked를 써야 하는지에 대한 실무 기준을 제시한다.

## 차별화 포인트

<!-- 내부 전용 섹션 -->

이 글은 "checked는 컴파일러가 체크하고 unchecked는 안 한다"는 교과서적 정의에서 멈추지 않는다. 실제로 JDBC 3계층(Repository-Service-Controller) 구조에서 `throws SQLException`이 시그니처를 타고 전파되는 과정을 직접 코드로 재현하고, 그 압박 때문에 개발자가 `catch (SQLException e) {}`로 예외를 삼키게 되는 안티패턴 발생 경로를 보여준다. 또한 Spring이 `DataAccessException`을 unchecked로 설계한 이유를 Rod Johnson의 저서(Expert One-on-One J2EE Design and Development, 9장)를 근거로 명시한 Spring 공식 Javadoc 원문과, 선언적 트랜잭션의 기본 롤백 정책이 unchecked에만 적용된다는 Spring 공식 레퍼런스 문서를 직접 대조해 "왜 프레임워크 설계자가 JDBC의 기본 설계(checked)를 의도적으로 뒤집었는가"라는, 단순 개념글에서는 다루지 않는 실제 엔지니어링 트레이드오프를 다룬다. Oracle 공식 Java 튜토리얼이 명시한 "Unchecked Exceptions — The Controversy" 문서의 판단 기준과 Spring의 실제 선택을 나란히 놓고 비교하는 것이 이 글의 핵심 차별점이다.

## 본문

### 1. Checked와 Unchecked, 문법적 차이부터

Java의 예외 계층은 `Throwable` 아래 `Error`와 `Exception`으로 나뉜다. `Exception`의 하위 클래스 중 `RuntimeException`과 그 자손이 아닌 모든 클래스가 checked exception이고, `RuntimeException`(과 `Error`)의 자손은 unchecked exception이다. Java 언어 명세(JLS)는 이 구분을 다음과 같이 설명한다.

> "The unchecked exception classes are exempted from compile-time checking... Runtime exception classes are exempted because, in the judgment of the designers of the Java programming language, having to declare such exceptions would not aid significantly in establishing the correctness of programs."

즉 unchecked exception이 컴파일 타임 체크에서 면제된 이유는 "선언을 강제해도 프로그램의 정확성 증명에 별 도움이 안 된다"는 언어 설계자들의 판단 때문이다. 반대로 checked exception은 메서드가 던질 수 있는 예외를 `throws` 절에 명시하도록 강제해서, 호출자가 그 예외를 "알고 대응"하게 만드는 것이 원래 취지다. Oracle 공식 Java 튜토리얼은 이 판단 기준을 아주 명확하게 정리한다.

> "If a client can reasonably be expected to recover from an exception, make it a checked exception. If a client cannot do anything to recover from the exception, make it an unchecked exception."

JDBC의 `java.sql.SQLException`은 `java.lang.Exception`을 직접 상속하는 checked exception이다. DB 연결이 끊기거나 SQL 문법이 틀리거나 제약조건을 위반하는 등, "호출자가 복구를 시도할 수도 있는" 상황으로 간주해 checked로 설계된 것이다.

### 2. Checked Exception이 시그니처를 오염시키는 과정 (Before)

문제는 여러 계층을 거치는 실무 코드에서 이 checked exception이 어떻게 전파되는지다. Raw JDBC를 그대로 쓰는 3계층 구조를 재현하면 이렇게 된다.

```java
// Repository 계층 — SQLException을 그대로 던진다
public class UserRepository {
    private final DataSource dataSource;

    public UserRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public User findById(Long id) throws SQLException {
        String sql = "SELECT id, name, email FROM users WHERE id = ?";
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                return new User(rs.getLong("id"), rs.getString("name"), rs.getString("email"));
            }
        }
    }
}

// Service 계층 — 자신은 SQL을 모르지만 throws SQLException을 그대로 떠안는다
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public UserDto getUser(Long id) throws SQLException {
        User user = userRepository.findById(id);
        if (user == null) {
            throw new NoSuchElementException("user not found: " + id);
        }
        return UserDto.from(user);
    }
}

// Controller 계층 — 비즈니스 로직과 무관한 SQLException까지 알아야 한다
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    public UserDto handleGetUser(Long id) throws SQLException {
        return userService.getUser(id);
    }
}
```

`UserService`와 `UserController`는 JDBC를 직접 다루지 않는데도 `throws SQLException`을 강제로 떠안는다. 컴파일러가 강제하니 무시할 수 없고, 그렇다고 이 계층에서 SQL 예외를 의미 있게 복구할 방법도 없다. 이 압박이 실무에서 흔히 두 가지 결과로 이어진다.

첫째, 상위 계층 전체가 특정 저장소 기술(JDBC)의 예외 타입을 알아야 하는 결합이 생긴다. 나중에 JPA로 바꾸면 `SQLException` 대신 `PersistenceException`이 등장하면서 시그니처를 전부 다시 고쳐야 한다.

둘째, 더 흔하고 위험한 결과인 "예외 삼킴(exception swallowing)" 안티패턴이 나온다. `throws`를 계속 전파하기 귀찮아진 개발자가 이렇게 처리해 버리는 경우다.

```java
// 예외 삼킴 안티패턴 — 컴파일은 통과하지만 실패를 완전히 숨긴다
public UserDto getUser(Long id) {
    try {
        User user = userRepository.findById(id);
        return UserDto.from(user);
    } catch (SQLException e) {
        return null; // DB 장애든 타임아웃이든 조용히 null만 반환
    }
}
```

컴파일러의 강제가 오히려 "일단 컴파일만 되게 만들자"는 동기를 만들어, 로그 한 줄 없이 예외를 삼키고 `null`을 반환하는 코드가 프로덕션에 배포된다. 이건 checked exception이 막으려던 바로 그 문제(호출자가 실패를 인지 못 하는 것)를 정반대로 만들어내는 셈이다.

### 3. Spring의 반례: DataAccessException은 왜 unchecked인가 (After)

Spring은 이 문제를 checked exception 자체를 없애는 방식으로 풀지 않고, JDBC의 `SQLException`을 자신의 `DataAccessException` 계층(unchecked)으로 감싸 다시 던지는 방식을 택했다. `JdbcTemplate`을 쓰면 원래 시그니처가 이렇게 바뀐다.

```java
import org.springframework.dao.DataAccessException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

// Repository — DataAccessException은 unchecked이므로 throws 선언이 필요 없다
public class UserRepository {
    private final JdbcTemplate jdbcTemplate;

    public UserRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public User findById(Long id) {
        String sql = "SELECT id, name, email FROM users WHERE id = ?";
        return jdbcTemplate.queryForObject(sql, this::mapRow, id);
    }

    private User mapRow(ResultSet rs, int rowNum) throws SQLException {
        return new User(rs.getLong("id"), rs.getString("name"), rs.getString("email"));
    }
}

// Service — 시그니처가 깨끗하다. 저장소 기술이 무엇인지 알 필요가 없다
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public UserDto getUser(Long id) {
        try {
            User user = userRepository.findById(id);
            return UserDto.from(user);
        } catch (EmptyResultDataAccessException e) {
            // 정말로 이 지점에서 처리 가능한 특정 서브타입만 선택적으로 캐치
            throw new UserNotFoundException(id, e);
        }
        // 그 외 DataAccessException(연결 실패, 제약조건 위반 등)은
        // 여기서 처리할 방법이 없으므로 굳이 잡지 않고 전역 핸들러로 흘려보낸다.
    }
}
```

`Service`와 `Controller`는 더 이상 `throws SQLException`을 알 필요가 없고, `EmptyResultDataAccessException`처럼 실제로 의미 있게 처리할 수 있는 서브타입만 선택적으로 잡는다. Spring 공식 Javadoc은 `DataAccessException`을 unchecked로 설계한 이유를 다음과 같이 명시한다(원문, 확인일: 2026-08-23).

> "This exception hierarchy aims to let user code find and handle the kind of error encountered without knowing the details of the particular data access API in use (for example, JDBC)... As this class is a runtime exception, there is no need for user code to catch it or subclasses if any error is to be considered fatal (the usual case)."

이 문서는 근거로 Rod Johnson의 저서 *Expert One-on-One J2EE Design and Development* 9장을 직접 인용한다. 핵심 논리는 Oracle 튜토리얼의 판단 기준("호출자가 합리적으로 복구할 수 있는가")을 데이터 접근 계층에 그대로 적용한 것이다 — 낙관적 락 실패나 제약조건 위반 같은 대부분의 `DataAccessException` 서브타입은, 상위 계층(Service/Controller)이 "JDBC냐 JPA냐"를 몰라도 되고 애초에 그 지점에서 복구할 수 없는 경우가 대다수이므로, 매 시그니처마다 선언을 강제할 실익이 없다고 본 것이다.

이 설계 선택은 트랜잭션 롤백 정책과도 직접 연결된다. Spring 공식 레퍼런스 문서는 선언적 트랜잭션의 기본 동작을 다음과 같이 규정한다(원문, 확인일: 2026-08-23).

> "In its default configuration, the Spring Framework's transaction infrastructure code marks a transaction for rollback only in the case of runtime, unchecked exceptions... Checked exceptions that are thrown from a transactional method do not result in a rollback in the default configuration."

즉 `@Transactional` 메서드에서 checked exception이 던져지면 기본적으로 롤백이 일어나지 않는다 — `rollbackFor`로 명시해야만 롤백된다. `DataAccessException`이 unchecked였기 때문에 "저장소 계층 실패는 기본적으로 롤백된다"는 안전한 기본값이 자연스럽게 성립한 것이고, 이는 checked/unchecked 선택이 예외 전파 편의성을 넘어 트랜잭션 정합성에까지 영향을 미친다는 걸 보여준다.

### 4. 그래서 언제 checked를, 언제 unchecked를 쓸 것인가

Oracle 공식 가이드라인과 Spring의 실제 선택을 종합하면 실무 기준은 명확해진다.

- **Checked를 쓰는 경우**: 호출자가 그 자리에서 "다른 분기로 복구"할 수 있는, 비즈니스 로직상 예상 가능한 실패. 예: 재고 부족으로 다른 창고를 조회해야 하는 경우, 결제 거절로 다른 결제 수단을 시도해야 하는 경우. 이때는 호출자가 반드시 이 케이스를 인지하고 분기 처리하게 만드는 게 유의미하다.
- **Unchecked를 쓰는 경우**: 프로그래밍 오류(`NullPointerException`, `IllegalArgumentException`)이거나, 인프라/외부 시스템 실패처럼 호출한 그 지점에서 복구가 불가능하고 상위 계층(전역 예외 핸들러 등)에서나 다룰 수 있는 실패. `DataAccessException`이 후자에 해당한다.

이 기준을 지키지 않고 "그냥 컴파일만 통과시키자"는 이유로 checked exception을 무분별하게 잡아 삼키거나, 반대로 "귀찮으니 전부 RuntimeException"으로 만드는 두 극단 모두 Oracle 튜토리얼이 명시적으로 경고하는 안티패턴이다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| `java.sql.SQLException`은 `java.lang.Exception`을 직접 상속하는 checked exception이다 | verified | Oracle 공식 Java SE 문서, [SQLException (Java SE 21 & JDK 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/SQLException.html) — "public class SQLException extends Exception" 명시 (확인일: 2026-08-23) |
| JLS는 `RuntimeException`(및 하위 클래스)과 `Error`(및 하위 클래스)만 컴파일 타임 체크에서 면제하며, 그 이유로 "선언 강제가 프로그램 정확성 증명에 별 도움이 안 된다"는 설계자 판단을 명시한다 | verified | Java Language Specification, [Chapter 11. Exceptions](https://docs.oracle.com/javase/specs/jls/se8/html/jls-11.html), 11.1.1절 원문 대조 (확인일: 2026-08-23) |
| Oracle 공식 Java 튜토리얼은 "호출자가 합리적으로 복구할 수 있으면 checked, 복구할 수 없으면 unchecked로 만들라"는 기준을 명시적으로 제시한다 | verified | Oracle 공식 Java Tutorials, [Unchecked Exceptions — The Controversy](https://docs.oracle.com/javase/tutorial/essential/exceptions/runtime.html) 원문 대조 (확인일: 2026-08-23) |
| Spring의 `DataAccessException`은 `NestedRuntimeException`을 상속하는 unchecked exception이며, Rod Johnson의 저서 *Expert One-on-One J2EE Design and Development* 9장의 논리를 근거로 설계됐다 | verified | Spring Framework 공식 Javadoc, [DataAccessException](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/dao/DataAccessException.html) 클래스 설명 원문 대조 (확인일: 2026-08-23) |
| Spring 선언적 트랜잭션의 기본 롤백 정책은 unchecked exception(`RuntimeException`/`Error`)에만 적용되며, checked exception은 `rollbackFor`로 명시해야 롤백된다 | verified | Spring Framework 공식 레퍼런스, [Rolling Back a Declarative Transaction](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html) 원문 대조 (확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 확인된 사실이 아니라 필자 개인의 해석을 담고 있습니다.

개인적으로는 Spring의 이 선택이 "checked exception이 틀렸다"는 주장이라기보다, "checked exception의 원래 취지(호출자가 복구 가능한 경우에만 강제)를 데이터 접근 계층에 엄격하게 적용한 결과"라고 본다. JDBC의 `SQLException`은 커넥션 끊김부터 문법 오류, 제약조건 위반까지 성격이 완전히 다른 실패를 한 타입에 뭉쳐 놓았는데, 이 중 상위 계층이 실제로 "다르게 대응"할 수 있는 경우는 소수다. Spring은 그 소수(`EmptyResultDataAccessException`, `DuplicateKeyException` 등)를 세분화된 서브타입으로 분리해 선택적으로 잡을 수 있게 하면서도, 나머지 대다수는 강제 선언 없이 흘려보내게 만들었다. 즉 checked를 없앤 게 아니라 "복구 불가능한 다수"를 unchecked로, "복구 가능한 소수"를 구체적 타입으로 정리한 것에 가깝다고 생각한다. 다만 이 판단은 결국 "이 예외를 호출자가 복구할 수 있는가"를 설계자가 매번 스스로 판단해야 한다는 뜻이기도 해서, 팀 컨벤션 없이 각자 판단에 맡기면 결국 실무에서는 "귀찮으니 전부 unchecked"로 흘러가는 경우를 여러 번 봤다. 그래서 이 원칙은 코드 리뷰 체크리스트로 명문화해두지 않으면 오래 지켜지기 어렵다는 게 필자의 생각이다.

## 한계와 반론

이 글의 비교는 Spring/JDBC 조합에 한정된 사례라는 한계가 있다. Kotlin처럼 언어 자체가 checked exception을 아예 강제하지 않는 경우, 이 논쟁 자체가 성립하지 않는다. 또한 "unchecked로 감싸면 시그니처가 깨끗해진다"는 장점의 반대급부로, 호출자가 IDE 자동완성이나 `throws` 선언만 보고는 어떤 예외가 발생할 수 있는지 전혀 알 수 없다는 반론도 유효하다 — 결국 Javadoc이나 별도 문서화에 의존하게 되는데, 실무에서 이 문서화가 누락되는 경우가 흔하다. 아울러 이 글이 제시한 "복구 가능/불가능" 기준도 실제로는 애매한 회색지대가 많다 — 예를 들어 낙관적 락 실패(`OptimisticLockingFailureException`)는 재시도로 복구 가능한 경우도 있어, Spring이 이를 unchecked로 분류한 것에 대한 반론도 커뮤니티에 존재한다.

## 참고문헌

1. Oracle, "SQLException (Java SE 21 & JDK 21)", https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/SQLException.html (확인일: 2026-08-23)
2. Oracle, "The Java Language Specification, Chapter 11. Exceptions", https://docs.oracle.com/javase/specs/jls/se8/html/jls-11.html (확인일: 2026-08-23)
3. Oracle, "The Java Tutorials — Unchecked Exceptions: The Controversy", https://docs.oracle.com/javase/tutorial/essential/exceptions/runtime.html (확인일: 2026-08-23)
4. Spring Framework, "DataAccessException (Spring Framework Javadoc)", https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/dao/DataAccessException.html (확인일: 2026-08-23)
5. Spring Framework, "Rolling Back a Declarative Transaction", https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 필자의 종합적 견해를 담고 있습니다.

Checked vs unchecked 논쟁은 결국 "예외를 언어가 강제로 알려줄 것인가, 프레임워크/팀 컨벤션이 알려줄 것인가"의 트레이드오프라고 정리하고 싶다. Java 언어 설계자는 전자를, Spring은 데이터 접근 계층에 한해 후자를 택했고, 두 선택 모두 나름의 근거가 있다. 이 글에서 재현한 것처럼 checked exception을 무분별하게 여러 계층에 전파시키면 시그니처 오염과 예외 삼킴이라는 실질적인 비용이 발생하지만, 그렇다고 모든 예외를 unchecked로 만들면 호출자가 실패 가능성을 전혀 인지하지 못한 채 코드를 작성하게 되는 반대 방향의 위험이 생긴다. 결국 실무에서 중요한 건 "우리 팀은 어떤 기준으로 checked/unchecked를 나눌 것인가"를 문서화하고 일관되게 지키는 것이지, 둘 중 하나를 절대적으로 옳다고 못 박는 게 아니라고 본다. Spring의 `DataAccessException` 사례는 그 기준을 "호출자가 실제로 복구할 수 있는가"라는 하나의 질문으로 압축해서 보여준 좋은 선례라고 생각한다.

## 꼬리질문

- Kotlin은 checked exception 개념 자체를 언어 차원에서 제거했는데, 이것이 Java/Spring 생태계와 상호운용될 때(Kotlin에서 Java checked exception을 던지는 메서드를 호출할 때) 실제로 어떤 차이를 만드는가?
- Spring의 `OptimisticLockingFailureException`처럼 "재시도로 복구 가능할 수도 있는" unchecked exception은, 애초에 checked로 남겨뒀어야 한다는 반론이 실무에서 얼마나 타당한가?
- `@Transactional(rollbackFor = ...)`를 팀 전체에 일관되게 적용하지 않아서 실제로 checked exception 발생 시 롤백이 안 된 채 커밋된 사고 사례는 어떤 패턴으로 발생하는가?

## 백링크

- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)
- [SOLID 원칙이란 무엇인가 — Java 기준 객체지향 설계 5대 원칙과 실전 예시](https://beji-tech.blogspot.com/2026/08/solid-java-5.html)

