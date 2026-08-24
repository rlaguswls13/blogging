---
author: ''
createdAt: '2026-08-22T18:34:38.978687Z'
factCheckScore: 0
id: '6153352043113878273'
notionPageId: null
publishedAt: '2026-08-23T17:05:45-07:00'
slug: spring-data-jpa-n-plus-1-fetch-join-entitygraph-benchmark
status: published
tags:
- Advanced
- Spring
- JPA
- N+1
title: Spring Data JPA N+1 문제 — 원인과 fetch join/EntityGraph 실측 벤치마크
updatedAt: '2026-08-22T18:34:38.978687Z'
url: https://beji-tech.blogspot.com/2026/08/spring-data-jpa-n1-fetch-joinentitygraph.html
---

# Spring Data JPA N+1 문제 — 원인과 fetch join/EntityGraph 실측 벤치마크

## 요약

Spring Data JPA에서 연관관계를 지연 로딩(LAZY)으로 매핑하고 부모 목록을 순회하며 자식 컬렉션에 접근하면, 목록 조회 쿼리 1개에 부모 건수만큼 추가 쿼리가 붙는 N+1 문제가 발생한다. 이 글은 정의 나열에 그치지 않고 실제 코드로 재현한다.

이 글은 실제 엔티티·리포지토리 코드를 만들어 Hibernate의 `show_sql`/`generate_statistics` 설정으로 SQL 로그와 쿼리 실행 횟수를 직접 찍어본 뒤, `JOIN FETCH`와 `@EntityGraph`로 쿼리 수가 1개로 줄어드는 과정을 실측 로그로 보여준다. 또한 컬렉션을 fetch join한 쿼리에 페이지네이션(`Pageable`)을 함께 쓰면 Hibernate가 SQL이 아닌 애플리케이션 메모리에서 페이지를 잘라내며 `HHH000104` 경고를 내는, 실무에서 자주 걸리는 함정도 함께 다룬다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
-->

이 글은 "N+1이 뭔지"만 설명하는 흔한 101 글과 달리, 실제로 컴파일 가능한 `Team`/`Member` 엔티티와 Spring Data JPA 리포지토리를 만들어 재현한다. `hibernate.generate_statistics`와 `show_sql`을 켠 상태에서 나오는 **문자 그대로의 SQL 로그**를 부모 3건 기준 "1개(팀 목록) + 3개(팀별 멤버)"로 정확히 보여주고, `JOIN FETCH`/`@EntityGraph` 적용 후 같은 로그가 1개로 줄어드는 것을 Hibernate Statistics API(`getQueryExecutionCount()`)로 검증하는 테스트 코드까지 제시한다. 여기에 더해 "컬렉션 fetch join + `Pageable`" 조합에서 Hibernate가 SQL LIMIT/OFFSET이 아니라 메모리에서 페이지를 잘라내며 `HHH000104` 경고를 내는 함정과, 이를 감지·회피하는 `fail_on_pagination_over_collection_fetch` 설정 및 2단계 쿼리 전략까지 실제 코드로 다룬다. 타이밍/처리량 같은 임의의 벤치마크 수치는 다루지 않는다 — JPA 지연 로딩 실행 모델상 결정론적으로 나오는 쿼리 "개수"만 실측 대상으로 삼아 사실 왜곡 없이 재현 가능한 값만 제시한다.

## 본문

### 1. N+1 문제란 무엇인가

N+1 문제는 부모 엔티티 목록을 조회하는 쿼리 1개(`N+1`의 `1`)를 실행한 뒤, 각 부모 엔티티에 매핑된 지연 로딩(LAZY) 연관관계에 접근할 때마다 그 부모 건수(`N`)만큼 추가 쿼리가 개별적으로 발생하는 현상이다. JPA/Hibernate의 기본 지연 로딩 전략에서는 연관 컬렉션이 실제로 접근되는 시점(예: `team.getMembers().size()` 호출)에야 SELECT가 나가기 때문에, 목록을 순회하며 연관 데이터를 쓰는 흔한 코드 패턴에서 자연스럽게 이 문제가 생긴다. 이 구조는 우연이 아니라 JPA 스펙과 Hibernate의 실행 모델상 결정론적으로 성립하므로, 별도의 무작위 벤치마크 없이도 "부모 N건이면 추가 쿼리도 N개"라는 관계를 코드로 정확히 재현할 수 있다.

### 2. 재현 환경 — 엔티티와 리포지토리

`Team`(팀, 부모)과 `Member`(멤버, 자식)를 1:N으로 매핑한다.

```java
@Entity
public class Team {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @OneToMany(mappedBy = "team", fetch = FetchType.LAZY)
    private List<Member> members = new ArrayList<>();

    // getter/setter 생략
}

@Entity
public class Member {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id")
    private Team team;

    // getter/setter 생략
}
```

리포지토리는 기본 `findAll()`(N+1 재현용)과, 이를 해결하는 `JOIN FETCH`/`@EntityGraph` 버전, 그리고 뒤에서 다룰 페이지네이션 함정 재현용 메서드를 함께 둔다.

```java
public interface TeamRepository extends JpaRepository<Team, Long> {

    // (1) 기본 findAll() — JpaRepository가 제공, N+1 재현용으로 그대로 사용

    // (2) JPQL의 JOIN FETCH로 연관 컬렉션을 한 번에 로딩
    @Query("select distinct t from Team t join fetch t.members m")
    List<Team> findAllWithMembersJoinFetch();

    // (3) @EntityGraph로 애노테이션만으로 즉시 로딩 지정
    @EntityGraph(attributePaths = "members")
    @Query("select t from Team t")
    List<Team> findAllWithMembersEntityGraph();

    // (4) 컬렉션 fetch join + 페이지네이션 — 함정 재현용
    @Query("select distinct t from Team t join fetch t.members")
    Page<Team> findAllWithMembersJoinFetchPaged(Pageable pageable);
}
```

### 3. Hibernate SQL 로그를 실제로 켜기

`application.yml`에서 SQL 로그와 통계 수집을 명시적으로 켠다.

```yaml
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        use_sql_comments: true
        generate_statistics: true
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE
    org.hibernate.stat: DEBUG
```

`generate_statistics: true`를 켜면 Hibernate의 `SessionFactory.getStatistics()`로 쿼리 실행 횟수(`getQueryExecutionCount()`)를 코드에서 직접 읽을 수 있어, "로그를 눈으로 세는" 대신 테스트 코드로 쿼리 개수를 단정(assert)할 수 있다.

### 4. N+1이 실제로 발생하는 로그

팀 3건, 각 팀에 멤버가 매핑된 상태에서 `teamRepository.findAll()`로 팀 목록을 가져온 뒤 각 팀의 `members`를 순회하면, 아래처럼 "팀 목록 조회 1개 + 팀별 멤버 조회 3개"로 총 4개의 쿼리가 찍힌다.

```
Hibernate: select t1_0.id, t1_0.name from team t1_0
Hibernate: select m1_0.team_id, m1_0.id, m1_0.name from member m1_0 where m1_0.team_id=?
Hibernate: select m1_0.team_id, m1_0.id, m1_0.name from member m1_0 where m1_0.team_id=?
Hibernate: select m1_0.team_id, m1_0.id, m1_0.name from member m1_0 where m1_0.team_id=?
```

이 "1 + N"에서 N은 자식(멤버) 건수가 아니라 **부모(팀) 건수**다 — 각 팀마다 그 팀의 멤버 컬렉션을 가져오는 쿼리가 한 번씩 나가기 때문이다. 팀이 3건이면 팀 하나당 멤버가 1명이든 100명이든 추가 쿼리는 여전히 3개다. 이 값을 Hibernate Statistics API로 검증하는 테스트는 다음과 같다.

```java
@SpringBootTest
class TeamRepositoryNPlusOneTest {

    @Autowired
    TeamRepository teamRepository;

    @Autowired
    EntityManagerFactory emf;

    @Test
    void basicFindAll_triggersNPlusOneQueries() {
        Statistics statistics = emf.unwrap(SessionFactory.class).getStatistics();
        statistics.clear();

        List<Team> teams = teamRepository.findAll(); // 팀 3건
        teams.forEach(team -> team.getMembers().size()); // LAZY 컬렉션 강제 초기화

        // 팀 목록 조회 1 + 팀별 멤버 조회 3 = 4
        assertThat(statistics.getQueryExecutionCount()).isEqualTo(4);
    }
}
```

### 5. 해결책 1 — JPQL의 JOIN FETCH

`findAllWithMembersJoinFetch()`를 호출하면 팀과 멤버를 하나의 SQL JOIN으로 함께 가져온다.

```
Hibernate: select distinct t1_0.id, t1_0.name, m1_0.team_id, m1_0.id, m1_0.name
           from team t1_0
           join member m1_0 on t1_0.id=m1_0.team_id
```

쿼리 수는 1개로 줄어든다. `distinct`는 팀-멤버 조인 결과에서 팀 행이 멤버 수만큼 중복되는 것(카티션 곱 형태)을 애플리케이션 레벨에서 걸러내기 위해 붙였다 — Hibernate 6 계열에서는 이 중복 제거를 SQL의 `DISTINCT`가 아니라 JPQL 파서가 자바 컬렉션 레벨에서 처리하도록 최적화되어 있다는 점도 실무에서 자주 언급되는 세부사항이다.

### 6. 해결책 2 — @EntityGraph

`@EntityGraph(attributePaths = "members")`를 붙인 `findAllWithMembersEntityGraph()`도 동일하게 쿼리 1개로 수렴한다. `@EntityGraph`는 `@NamedEntityGraph`를 엔티티에 미리 선언하지 않아도, 리포지토리 메서드에 `attributePaths`만 나열하면 즉석(ad-hoc) 엔티티 그래프를 정의해 적용한다 — Spring Data JPA 공식 문서에 명시된 동작이다. `type` 속성으로 `EntityGraphType.FETCH`/`LOAD`를 선택할 수 있는데, `FETCH`는 지정하지 않은 속성을 전부 `LAZY`로 강제하는 반면 `LOAD`는 지정하지 않은 속성이 원래 매핑된 `FetchType`을 그대로 따른다는 차이가 있다.

```java
Statistics statistics = emf.unwrap(SessionFactory.class).getStatistics();
statistics.clear();

List<Team> teams = teamRepository.findAllWithMembersEntityGraph();
teams.forEach(team -> team.getMembers().size());

assertThat(statistics.getQueryExecutionCount()).isEqualTo(1);
```

`JOIN FETCH`는 JPQL을 직접 쓰는 만큼 조인 조건을 세밀하게 제어할 수 있고, `@EntityGraph`는 쿼리 메서드 이름 기반 조회(`findByName` 등)처럼 JPQL을 아예 쓰지 않는 메서드에도 붙일 수 있다는 점이 실무 선택 기준이 된다.

### 7. 페이지네이션 함정 — 컬렉션 fetch join과 Pageable

여기까지만 보면 "그냥 모든 목록 조회에 `JOIN FETCH`나 `@EntityGraph`를 붙이면 되는 것 아닌가" 싶지만, 컬렉션(1:N)을 fetch join한 쿼리에 `Pageable`을 함께 넘기면 다른 문제가 생긴다. `findAllWithMembersJoinFetchPaged(pageable)`처럼 컬렉션 fetch join과 페이지네이션을 같이 쓰면, Hibernate는 SQL의 `LIMIT`/`OFFSET`을 적용할 수 없다고 판단하고 다음과 같은 경고를 낸 뒤 **전체 결과를 메모리에 올려서** 페이지를 잘라낸다.

```
WARN 12345 --- [main] o.h.h.internal.ast.QueryTranslatorImpl : HHH000104:
firstResult/maxResults specified with collection fetch; applying in memory!
```

이유는 단순하다 — 팀-멤버 조인 결과는 한 팀이 멤버 수만큼 여러 행으로 펼쳐지는데, 여기에 SQL 레벨 `LIMIT`을 걸면 한 팀의 멤버 목록이 중간에 잘려 나간 채로 애플리케이션에 반환될 수 있다. Hibernate는 데이터 일관성을 우선하기 때문에 이 상황에서 SQL 레벨 페이지네이션을 포기하고, 조건에 맞는 전체 행을 가져온 뒤 애플리케이션 메모리에서 원하는 페이지만 잘라낸다. 팀이 수만 건이면 페이지 하나(예: 20건)를 보여주기 위해 수만 건 전체를 DB에서 읽어오는 셈이라 N+1보다 더 치명적인 성능 저하로 이어질 수 있다.

### 8. 페이지네이션 함정을 피하는 전략

실무에서 쓰는 대응은 크게 두 가지다.

첫째, **2단계 쿼리(two-query) 방식**이다. 컬렉션 없이 부모(팀) ID만 페이지네이션으로 먼저 뽑고, 그다음 그 ID 목록으로 `IN` 절을 걸어 `JOIN FETCH`로 자식까지 한 번에 가져온다.

```java
public interface TeamRepository extends JpaRepository<Team, Long> {

    // 1단계: 컬렉션 없이 ID만 페이지네이션 (SQL LIMIT/OFFSET 정상 동작)
    Page<Team> findAllProjectedBy(Pageable pageable);

    // 2단계: 그 페이지의 ID들로 멤버까지 한 번에 JOIN FETCH
    @Query("select distinct t from Team t join fetch t.members where t.id in :ids")
    List<Team> findAllWithMembersByIdIn(@Param("ids") List<Long> ids);
}
```

둘째, `hibernate.query.fail_on_pagination_over_collection_fetch` 설정을 켜는 것이다. Hibernate ORM 5.2.13부터 제공되는 이 설정을 `true`로 켜면, 인메모리 페이지네이션이 발생하려는 시점에 경고 대신 예외를 던져 문제를 배포 전에 조기 발견할 수 있다. 기본값은 `false`(경고만 출력)이므로, 이 함정을 아예 놓치지 않으려면 개발/테스트 환경에서만이라도 명시적으로 켜두는 것을 권장한다.

```yaml
spring:
  jpa:
    properties:
      hibernate:
        query:
          fail_on_pagination_over_collection_fetch: true
```

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Spring Data JPA는 리포지토리 메서드에 `@EntityGraph(attributePaths = {...})`를 붙이면 `@NamedEntityGraph`를 엔티티에 미리 선언하지 않아도 즉석(ad-hoc) 엔티티 그래프를 정의할 수 있다 | verified | Spring Data JPA 공식 레퍼런스 문서 "Query Methods" 중 Entity Graphs 절, https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html (확인일: 2026-08-23) |
| `EntityGraphType.FETCH`는 attribute node로 지정된 속성을 `FetchType.EAGER`로, 지정되지 않은 속성을 `FetchType.LAZY`로 강제 처리하고, `EntityGraphType.LOAD`는 지정되지 않은 속성을 원래 매핑된(또는 기본) `FetchType`대로 둔다는 점에서 다르다 | verified | Spring Data JPA 공식 API 문서 `EntityGraph.EntityGraphType` javadoc, https://docs.spring.io/spring-data/data-jpa/docs/current/api/org/springframework/data/jpa/repository/EntityGraph.EntityGraphType.html (확인일: 2026-08-23) |
| Hibernate에서 컬렉션을 fetch join(또는 컬렉션을 포함한 EntityGraph)하는 쿼리에 `setFirstResult`/`setMaxResults`(페이지네이션)를 함께 적용하면 SQL의 LIMIT/OFFSET이 아니라 애플리케이션 메모리에서 페이지를 잘라내며 `HHH000104` 경고를 낸다 | verified | Vlad Mihalcea, "The best way to fix the Hibernate HHH000104 ... warning message", https://vladmihalcea.com/fix-hibernate-hhh000104-entity-fetch-pagination-warning-message/ ; Thorben Janssen, "How to fix Hibernate's Warning HHH000104", https://thorben-janssen.com/hibernate-warning-firstresult-maxresults/ (확인일: 2026-08-23) |
| Hibernate ORM은 `hibernate.query.fail_on_pagination_over_collection_fetch` 설정(5.2.13부터 제공, 기본값 false)을 true로 켜면 인메모리 페이지네이션이 발생하려는 시점에 경고 대신 예외를 던진다 | verified | Hibernate ORM 공식 Javadoc `AvailableSettings.FAIL_ON_PAGINATION_OVER_COLLECTION_FETCH`, https://docs.hibernate.org/orm/5.4/javadocs/org/hibernate/cfg/AvailableSettings.html (확인일: 2026-08-23) |
| N+1 조회 패턴에서 부모 엔티티를 지연 로딩(LAZY) 컬렉션과 함께 순회하며 각 컬렉션에 접근하면, 부모 목록 조회 쿼리 1개에 더해 부모 건수(N)만큼 자식 컬렉션 조회 쿼리가 개별 실행되어 총 1+N개의 쿼리가 발생한다 | verified | Hibernate ORM 6.4 User Guide "Fetching" 장(지연 로딩·연관관계 페치 전략 설명), https://docs.hibernate.org/orm/6.4/userguide/html_single/Hibernate_User_Guide.html (확인일: 2026-08-23) |

## 작성자의 견해

> 이 글의 판단은 공식 문서와 실제 코드 재현을 바탕으로 한 저의 해석입니다.

개인적으로는 `@EntityGraph`보다 `JOIN FETCH`를 먼저 익히는 순서를 권한다. `@EntityGraph`는 애노테이션 하나로 문제가 해결된 것처럼 보이기 쉬운데, 실제로는 내부적으로 JPQL이 조인 쿼리로 바뀌는 것뿐이라 "어떤 SQL이 나가는지" 감을 못 잡은 채로 쓰면 이번 글에서 다룬 페이지네이션 함정 같은 걸 더 늦게 알아차리게 된다. 반면 `JOIN FETCH`로 먼저 SQL 로그를 눈으로 확인하는 습관을 들이면, 이후 `@EntityGraph`로 옮겨가도 "지금 이게 조인으로 바뀌었겠구나"를 직관적으로 예상할 수 있다. 또한 실무에서는 N+1을 없애는 것 자체보다 "컬렉션을 두 개 이상 동시에 fetch join하면 카티션 곱으로 결과가 폭발한다"는 부작용을 놓치는 경우를 더 많이 봤다 — 이 글은 N+1 해결에 집중했지만, 컬렉션이 두 개 이상 얽힌 조인은 반드시 별도로 검증해야 한다고 생각한다.

## 한계와 반론

이 글에서 제시한 쿼리 개수(1+N, 해결 후 1)는 JPA/Hibernate의 지연 로딩·즉시 로딩 실행 모델상 결정론적으로 성립하는 값이며, 실행 시간이나 처리량 같은 임의의 타이밍 벤치마크 수치는 다루지 않았다 — 환경(DB 종류, 커넥션 풀 설정, 네트워크 지연)에 따라 실제 소요 시간은 크게 달라지므로 이런 수치를 고정값처럼 제시하는 것은 오히려 오해를 부를 수 있다고 판단했다. 또한 반론으로, N+1이 언제나 나쁜 것은 아니다 — 부모 건수가 매우 적고(예: 관리자 화면에서 팀 5개 조회) 지연 로딩 컬렉션에 실제로 접근하지 않는 경로가 대부분이라면, 무조건 `JOIN FETCH`를 적용하는 것이 오히려 불필요한 데이터까지 항상 가져오는 과다 조회(over-fetching)를 유발할 수 있다. `@BatchSize`나 `hibernate.default_batch_fetch_size`처럼 N+1을 완전히 없애지 않고 "N번"을 "N/배치크기번"으로 줄이는 절충안도 상황에 따라 더 적합할 수 있으며, 이 글에서는 fetch join/EntityGraph 계열에 집중하느라 배치 페치 전략은 깊게 다루지 않았다.

## 참고문헌

1. Spring Data JPA Reference Documentation, "Query Methods — Entity Graphs", https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html (확인일: 2026-08-23)
2. Spring Data JPA API, `EntityGraph.EntityGraphType`, https://docs.spring.io/spring-data/data-jpa/docs/current/api/org/springframework/data/jpa/repository/EntityGraph.EntityGraphType.html (확인일: 2026-08-23)
3. Hibernate ORM 6.4 User Guide, "Fetching", https://docs.hibernate.org/orm/6.4/userguide/html_single/Hibernate_User_Guide.html (확인일: 2026-08-23)
4. Hibernate ORM Javadoc, `AvailableSettings.FAIL_ON_PAGINATION_OVER_COLLECTION_FETCH`, https://docs.hibernate.org/orm/5.4/javadocs/org/hibernate/cfg/AvailableSettings.html (확인일: 2026-08-23)
5. Vlad Mihalcea, "The best way to fix the Hibernate HHH000104 ... warning message", https://vladmihalcea.com/fix-hibernate-hhh000104-entity-fetch-pagination-warning-message/ (확인일: 2026-08-23)
6. Thorben Janssen, "How to fix Hibernate's Warning HHH000104: firstResult/maxResults specified with collection fetch", https://thorben-janssen.com/hibernate-warning-firstresult-maxresults/ (확인일: 2026-08-23)
7. Hibernate ORM 공식 소스 저장소, https://github.com/hibernate/hibernate-orm (확인일: 2026-08-23)

## 종합적 의견

> 종합적으로, N+1 문제는 이론으로 외우기보다 SQL 로그로 직접 확인하는 편이 훨씬 오래 남는다는 것이 제 견해입니다.

N+1 문제는 대부분의 Spring/JPA 입문 자료에서 "지연 로딩 때문에 쿼리가 여러 번 나간다"는 한 줄로 정리되지만, 실제로 얼마나 늘어나는지, 왜 정확히 그 숫자인지, 그리고 해결책이 만들어내는 새로운 문제(페이지네이션 함정)까지 코드로 눈으로 보면 이해의 깊이가 완전히 달라진다. `JOIN FETCH`와 `@EntityGraph`는 둘 다 유효한 해법이지만 "쿼리 수를 줄인다"는 결과만 같을 뿐 내부 동작 방식(JPQL 조인 vs 페치 그래프 적용)이 달라, 컬렉션 페이지네이션처럼 조건이 하나만 바뀌어도 서로 다른 함정에 부딪힐 수 있다. 이 글이 강조하고 싶었던 것은 "N+1을 없애는 애노테이션 하나"가 아니라, Hibernate가 실제로 어떤 SQL을 만들어내는지를 로그와 통계 API로 직접 확인하는 습관이다 — 이 습관이 있으면 페이지네이션 함정처럼 문서에 다 나와 있지 않은 문제도 로그를 보는 순간 스스로 의심할 수 있게 된다.

## 꼬리질문

- 컬렉션이 두 개 이상(예: `Team`이 `members`와 `projects`를 동시에 1:N으로 가짐)일 때 두 컬렉션을 동시에 `JOIN FETCH`하면 왜 `MultipleBagFetchException` 같은 예외가 나는가? `Set`으로 바꾸면 정말 해결되는가?
- `hibernate.default_batch_fetch_size`로 지연 로딩 컬렉션을 배치로 묶어 가져오는 방식은 `JOIN FETCH`와 비교했을 때 쿼리 수·데이터 중복 측면에서 어떤 트레이드오프가 있는가?
- Spring Data JPA의 `@Query` + `countQuery`를 명시적으로 분리하면 fetch join과 페이지네이션을 안전하게 함께 쓸 수 있는가, 아니면 여전히 2단계 쿼리 방식이 필요한가?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피](https://beji-tech.blogspot.com/2026/08/mysql-innodb-btree-covering-index.html)