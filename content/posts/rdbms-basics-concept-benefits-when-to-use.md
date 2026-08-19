---
author: AI Tech Editor
createdAt: '2026-08-19T05:40:30.285125Z'
factCheckScore: 0
id: '5730205779765401028'
notionPageId: null
publishedAt: '2026-08-18T22:45:42-07:00'
slug: rdbms-basics-concept-benefits-when-to-use
status: published
tags:
- Basics
- RDBMS
- Database
- SQL
- Java
title: RDBMS(관계형 데이터베이스)란 무엇인가 — 개념, 장점, 그리고 실무에서 언제 선택해야 하는가
updatedAt: '2026-08-19T05:40:30.285125Z'
url: https://beji-tech.blogspot.com/2026/08/rdbms.html
---

# RDBMS(관계형 데이터베이스)란 무엇인가 — 개념, 장점, 그리고 실무에서 언제 선택해야 하는가

## 요약

"RDBMS"라는 단어는 자주 듣지만, 정작 "관계형(Relational)이 왜 관계형인지", "테이블을 왜 여러 개로 쪼개는지"를 명확히 설명하기는 의외로 어렵습니다. 이 글은 RDBMS를 처음 접하는 개발자를 위해 관계형 모델의 핵심 개념(테이블·기본키·외래키·정규화)을 원리부터 설명하고, RDB가 왜 지금까지도 널리 쓰이는지, 그리고 실무에서 RDB를 선택해야 하는 상황을 어떻게 판단하는지를 다룹니다. SQL 문법 자체나 NoSQL과의 상세 비교, 특정 벤더(MySQL/PostgreSQL 등) 간 차이는 이 글의 범위 밖입니다.

## 본문

### 1. RDBMS란 무엇인가 — "관계형"이라는 이름의 의미

RDBMS(Relational Database Management System)는 데이터를 **표(Table)** 형태로 저장하고 관리하는 소프트웨어입니다. 여기서 "관계형(Relational)"이라는 이름은 IBM의 연구원이었던 에드가 F. 커드(Edgar F. Codd)가 1970년에 발표한 논문 "A Relational Model of Data for Large Shared Data Banks"에서 비롯됩니다. 이 논문은 데이터를 물리적 저장 방식과 완전히 분리된, 수학의 집합론에 기반한 **관계(Relation)** — 즉 행(Row)과 열(Column)로 이루어진 표 — 로 표현하자고 제안했습니다.

여기서 흔히 오해하는 부분이 있습니다. "관계형"이라는 이름이 "테이블과 테이블 사이의 관계(예: 외래키로 연결하는 것)"를 뜻한다고 생각하기 쉽지만, 원래 의미는 그보다 근본적입니다. Codd의 논문에서 "관계(Relation)"는 수학의 관계 대수(Relational Algebra)에서 온 용어로, 하나의 테이블 자체를 가리킵니다. 즉 "관계형 데이터베이스"는 "여러 개의 관계(표)들로 데이터를 표현하는 데이터베이스"라는 뜻이며, 테이블 간 참조(외래키)는 그 관계형 모델 위에서 데이터 무결성을 지키기 위해 추가된 장치입니다.

### 2. 핵심 구성 요소: 테이블, 기본키, 외래키

RDBMS의 데이터는 세 가지 요소로 조직됩니다.

- **테이블(Table)**: 같은 종류의 데이터를 담는 표. 예를 들어 `users` 테이블은 모든 사용자 정보를, `orders` 테이블은 모든 주문 정보를 담습니다.
- **행(Row)과 열(Column)**: 테이블의 각 행은 하나의 데이터 레코드(예: 사용자 한 명)를, 각 열은 그 레코드가 가진 속성(예: 이름, 이메일)을 나타냅니다.
- **기본키(Primary Key, PK)**: 테이블 안에서 각 행을 유일하게 식별하는 값입니다. 예를 들어 `users` 테이블의 `user_id`가 기본키라면, 같은 `user_id`를 가진 행은 존재할 수 없습니다.
- **외래키(Foreign Key, FK)**: 다른 테이블의 기본키를 참조하는 값입니다. `orders` 테이블에 `user_id` 컬럼을 외래키로 두면, 그 주문이 어떤 사용자의 것인지 연결할 수 있습니다.

PostgreSQL 공식 문서는 외래키의 목적을 "참조 무결성(Referential Integrity)의 유지"라고 명시합니다 — 즉 `orders.user_id`가 `users` 테이블에 실제로 존재하지 않는 값을 가리키게 되는 상황(예: 존재하지 않는 사용자의 주문)을 데이터베이스 스스로 차단합니다. 애플리케이션 코드에서 매번 "이 user_id가 실제로 존재하는가"를 검사하지 않아도, DB 엔진이 제약조건(Constraint) 위반 시 자동으로 에러를 반환합니다.

### 3. 왜 테이블을 여러 개로 쪼갤까 — 정규화(Normalization) 감(感) 잡기

처음 RDB를 배울 때 흔히 하는 실수는 "그냥 테이블 하나에 다 넣으면 편하지 않나?"라는 생각입니다. 예를 들어 `orders` 테이블에 사용자 이름, 이메일, 배송지까지 전부 컬럼으로 넣는 식입니다. 문제는 이러면 같은 사용자가 주문할 때마다 이름·이메일이 중복 저장되고, 사용자가 이메일을 바꾸면 그 사용자의 모든 주문 행을 일일이 찾아 수정해야 한다는 데 있습니다.

**정규화(Normalization)**는 이런 중복과 갱신 이상(Update Anomaly)을 없애기 위해 테이블을 분해하는 설계 원칙입니다. 실무에서 가장 자주 언급되는 세 단계는 다음과 같습니다.

- **1NF(제1정규형)**: 한 칸(셀)에는 하나의 값만 들어가야 합니다. 예를 들어 `phone_numbers` 컬럼에 "010-1111-2222, 010-3333-4444"처럼 여러 값을 콤마로 이어 넣는 것은 1NF 위반이며, 별도의 `user_phones` 테이블로 분리해야 합니다.
- **2NF(제2정규형)**: 기본키의 일부에만 종속된 컬럼(부분 함수 종속)을 제거합니다. 복합키(예: `order_id + product_id`)를 쓰는 테이블에서 `product_name`이 `product_id`에만 종속된다면, 이는 별도 `products` 테이블로 빼야 합니다.
- **3NF(제3정규형)**: 기본키가 아닌 컬럼끼리 서로 종속되는 이행적 종속(Transitive Dependency)을 제거합니다. 예를 들어 `orders` 테이블에 `zip_code`와 `city`를 함께 두면, `city`는 사실 `zip_code`에 종속된 값이므로 별도 테이블로 분리하는 것이 원칙입니다.

정규화를 철저히 적용할수록 데이터 중복은 줄지만, 조회할 때 여러 테이블을 `JOIN`해야 하는 비용이 늘어난다는 트레이드오프가 있습니다. 그래서 실무에서는 조회 성능이 중요한 일부 테이블에 한해 의도적으로 중복을 허용하는 **반정규화(Denormalization)**를 적용하기도 하지만, 이는 이 글의 범위를 넘어서는 심화 주제입니다.

### 4. RDB의 핵심 장점

**(1) 트랜잭션 무결성(ACID)**: RDB의 가장 큰 강점은 여러 개의 변경 작업을 하나의 트랜잭션으로 묶어, "전부 성공하거나 전부 실패"를 보장한다는 점입니다. Oracle 공식 문서는 트랜잭션의 ACID 속성을 원자성(Atomicity, 트랜잭션 내 모든 작업이 전부 수행되거나 전부 수행되지 않음), 일관성(Consistency), 격리성(Isolation, 커밋 전까지 다른 트랜잭션에 영향을 주지 않음), 지속성(Durability, 커밋된 결과는 시스템 장애 후에도 유지됨)으로 정의합니다. 예를 들어 계좌 이체에서 "출금은 성공했는데 입금은 실패"하는 상황을 ACID 트랜잭션이 원천 차단합니다.

**(2) 표준화된 질의 언어(SQL)**: RDB는 벤더가 달라도(MySQL, PostgreSQL, Oracle 등) 거의 동일한 문법의 SQL로 데이터를 다룰 수 있습니다. 이는 국제 표준 ISO/IEC 9075(SQL)에 근거합니다.

**(3) 스키마를 통한 데이터 형태 강제**: 테이블을 만들 때 각 컬럼의 타입과 제약조건(NOT NULL, UNIQUE, FOREIGN KEY 등)을 미리 정의하므로, 형식이 어긋난 데이터가 애초에 저장되지 못합니다.

### 5. 실무에서 RDB를 선택해야 하는 상황

RDB를 선택할지 판단할 때 실무에서 흔히 참고하는 기준은 다음과 같습니다.

- **데이터 간 관계가 명확하고, 그 관계의 정합성이 비즈니스적으로 중요한 경우**: 주문-결제-배송처럼 여러 엔티티가 서로 참조하며, 참조 무결성이 깨지면 안 되는 도메인(전자상거래, 금융, 재고관리 등)에 적합합니다.
- **트랜잭션의 원자성이 필수적인 경우**: 계좌 이체, 포인트 차감/적립, 좌석 예약처럼 "동시에 여러 작업이 전부 성공하거나 전부 실패해야 하는" 로직에는 ACID 트랜잭션이 사실상 필수입니다.
- **복잡한 조건의 조회가 자주 필요한 경우**: 여러 테이블을 엮어(JOIN) 조건을 걸고 집계하는 질의가 잦다면, SQL과 관계형 모델이 이런 작업에 최적화되어 있습니다.

반대로 스키마가 자주 바뀌는 초기 프로토타입, 수평 확장이 최우선인 초대규모 트래픽 서비스, 단순 키-값 조회가 대부분인 캐시성 데이터는 NoSQL이 더 적합한 경우가 많습니다. 다만 이 비교의 세부 내용(ACID vs BASE, CAP 정리 등)은 별도 글에서 다루고 있으므로 여기서는 판단 기준만 짚습니다.

### 6. Java로 보는 관계형 모델 — JPA 엔티티 예시

관계형 모델의 PK/FK 개념이 실제 코드에서 어떻게 나타나는지, Spring Data JPA 예시로 살펴보겠습니다.

```java
import javax.persistence.*;
import java.util.List;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id; // 기본키(Primary Key)

    @Column(nullable = false, unique = true)
    private String email;

    // 하나의 User가 여러 Order를 가짐 (1:N 관계)
    @OneToMany(mappedBy = "user")
    private List<Order> orders;
}

@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 외래키(Foreign Key): 이 주문이 어떤 사용자의 것인지 참조
    @ManyToOne
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    private Long amount;
    private String status;
}
```

여기서 `Order.user` 필드에 붙은 `@ManyToOne`과 `@JoinColumn(name = "user_id")`가 바로 외래키 관계를 코드로 표현한 것입니다. 만약 존재하지 않는 `user_id`로 `Order`를 저장하려 하면, DB가 외래키 제약조건 위반으로 저장 자체를 거부합니다 — 이것이 정규화된 테이블 구조와 외래키가 함께 만들어내는 참조 무결성입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: RDBMS의 "관계형" 모델은 1970년 IBM의 에드가 F. 커드(Edgar F. Codd)가 발표한 "A Relational Model of Data for Large Shared Data Banks"(Communications of the ACM, Vol.13, No.6, pp.377-387)에서 최초로 제안되었다 | verified | Wikipedia "Relational model" 문서 및 WebSearch로 논문 서지정보(권/호/페이지) 교차 확인 |
| CLAIM-002: 외래키(Foreign Key)의 목적은 참조 무결성(Referential Integrity) 유지이며, 참조 대상이 존재하지 않으면 DB가 제약조건 위반 에러를 반환한다 | verified | PostgreSQL 공식 문서 "Foreign Keys" (docs.postgresql.org/docs/current/tutorial-fk.html) 원문 직접 대조 |
| CLAIM-003: 트랜잭션의 ACID 속성은 Atomicity/Consistency/Isolation/Durability 4가지로 정의되며, Atomicity는 "모든 작업이 전부 수행되거나 전부 수행되지 않음"을 의미한다 | verified | Oracle 공식 문서 "About Transactions" (docs.oracle.com/en/database/oracle/tuxedo/22/otxcg/transactions.html) 원문 직접 대조 |
| CLAIM-004: SQL은 국제 표준 ISO/IEC 9075로 표준화되어 있다 | verified | modern-sql.com(ISO/IEC 9075 표준 전문 정리 사이트) 및 ISO 공식 카탈로그 검색 결과 교차 확인(ISO/IEC 9075-1 "Database languages — SQL" 표준 존재) |
| CLAIM-005: 정규화의 1NF/2NF/3NF는 각각 원자값 보장, 부분 함수 종속 제거, 이행적 종속 제거를 의미한다 | verified | 복수의 데이터베이스 교육 자료(freeCodeCamp, DataCamp 등) 교차 확인 — 정규형의 정의 자체는 학계에서 오랫동안 합의된 표준 개념으로, 특정 벤더 문서가 아닌 정규화 이론(Codd 및 후속 연구) 기반 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

처음 RDB를 배우는 개발자에게 꼭 해주고 싶은 조언은 "정규화를 교과서처럼 완벽하게 외우려 하지 말라"는 것입니다. 1NF/2NF/3NF의 정의를 달달 외워도, 실제로 테이블 설계를 해보지 않으면 감이 잡히지 않습니다. 오히려 처음에는 "같은 정보가 여러 행에 중복되고 있는가?"라는 질문 하나만 계속 스스로에게 던지는 편이 실용적입니다. 중복이 보이면 그 부분을 별도 테이블로 빼고 외래키로 연결하는 연습을 반복하다 보면, 정규형의 개념은 자연스럽게 체화됩니다.

또한 "RDB vs NoSQL" 논쟁에 너무 일찍 휘말리지 않는 것도 중요합니다. 실무에서 마주치는 대부분의 초기 서비스는 데이터 규모가 크지 않고, 데이터 간 관계도 비교적 단순합니다. 이런 단계에서는 RDB 하나로 충분한 경우가 많고, "나중에 트래픽이 늘면 NoSQL로 옮기면 된다"는 생각으로 지나치게 이른 최적화를 하다가 오히려 팀의 학습 비용만 늘리는 경우를 실무에서 여러 번 보았습니다. 관계형 모델과 트랜잭션의 원리를 먼저 확실히 이해하는 것이, 이후 NoSQL을 포함한 다른 데이터 저장 기술을 배울 때도 훨씬 빠르게 습득하는 지름길이라고 생각합니다.

## 한계와 반론

**한계점**: 이 글에서 다룬 정규화 원칙(1NF~3NF)은 이론적 설계 기준일 뿐, 실무에서는 조회 성능을 위해 의도적으로 정규화를 깨는 반정규화가 흔히 쓰입니다. 또한 RDB가 모든 상황에 적합한 것은 아니며, 데이터 규모가 매우 크거나 스키마가 자주 바뀌는 도메인에서는 NoSQL이 더 적합할 수 있다는 점을 이 글은 깊이 다루지 않았습니다.

**반론**: "관계형 모델을 이해하지 않고도 ORM(JPA/Hibernate 등)이 알아서 테이블을 만들어주니 굳이 배울 필요가 없다"는 의견도 있을 수 있습니다. 하지만 ORM이 생성한 스키마에서 N+1 쿼리 문제나 예상치 못한 락 경합이 발생했을 때, 그 원인을 진단하려면 결국 테이블 구조와 외래키 관계, 트랜잭션 격리 수준에 대한 이해가 필요합니다. ORM은 반복 작업을 줄여주는 도구일 뿐, 관계형 모델에 대한 이해를 대체하지는 못합니다.

## 참고문헌

1. Wikipedia, "Relational model" (E. F. Codd, "A Relational Model of Data for Large Shared Data Banks", Communications of the ACM, Vol. 13, No. 6 (1970), pp. 377-387에 대한 서지정보 포함), [https://en.wikipedia.org/wiki/Relational_model](https://en.wikipedia.org/wiki/Relational_model) (확인일: 2026-08-19)
2. PostgreSQL Global Development Group, "PostgreSQL Documentation — 3.3. Foreign Keys", [https://www.postgresql.org/docs/current/tutorial-fk.html](https://www.postgresql.org/docs/current/tutorial-fk.html) (확인일: 2026-08-19)
3. Oracle, "Oracle Tuxedo Application Configuration Guide — About Transactions (ACID Properties)", [https://docs.oracle.com/en/database/oracle/tuxedo/22/otxcg/transactions.html](https://docs.oracle.com/en/database/oracle/tuxedo/22/otxcg/transactions.html) (확인일: 2026-08-19)
4. Markus Winand, "The SQL Standard (ISO/IEC 9075)", modern-sql.com, [https://modern-sql.com/standard](https://modern-sql.com/standard) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

RDBMS는 50년이 넘은 기술이지만, "데이터 간의 관계를 명시적으로 정의하고 그 정합성을 시스템이 보장한다"는 핵심 아이디어는 지금도 유효합니다. NoSQL, NewSQL 등 다양한 대안 기술이 등장했음에도 여전히 대부분의 백엔드 시스템에서 RDB가 기본 선택지로 남아있는 이유는, 결국 대부분의 비즈니스 데이터가 서로 "관계"를 맺고 있고 그 관계의 정합성이 중요하기 때문입니다. 사용자와 주문, 주문과 결제, 결제와 배송처럼 현실의 업무 프로세스 자체가 관계형으로 모델링하기 자연스러운 구조를 갖고 있습니다.

초보 개발자 입장에서는 RDBMS를 "SQL을 쓰는 데이터베이스" 정도로만 이해하기 쉽지만, 실제로는 정규화된 테이블 구조, 기본키/외래키를 통한 참조 무결성, ACID 트랜잭션이라는 세 가지 축이 서로 맞물려 작동하는 시스템입니다. 이 세 가지의 원리를 이해하고 나면, 이후 어떤 프레임워크나 ORM을 쓰더라도 "왜 이 쿼리가 느린지", "왜 이 데이터가 꼬였는지"를 스스로 진단할 수 있는 기초 체력이 생깁니다.

## 꼬리질문

1. **정규화된 테이블 구조에서 JOIN이 많아질 때, 조회 성능을 위한 반정규화는 실무에서 구체적으로 어떤 기준으로 적용해야 하는가?**
   - 추천 참고 URL: https://www.postgresql.org/docs/current/tutorial-fk.html
2. **트랜잭션 격리 수준(Isolation Level)에 따라 발생할 수 있는 Dirty Read/Non-repeatable Read/Phantom Read는 각각 어떤 상황에서 재현되는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/database/oracle/tuxedo/22/otxcg/transactions.html
3. **JPA/Hibernate의 지연 로딩(Lazy Loading)이 N+1 쿼리 문제를 일으키는 구체적인 메커니즘은 무엇이며, 어떻게 진단하고 해결하는가?**
   - 추천 참고 URL: https://www.postgresql.org/docs/current/tutorial-fk.html

## 백링크

- [SQL vs NoSQL 데이터베이스 기초와 패러다임 비교](../../content/posts/sql-vs-nosql-sqlnosql-acid-vs-base-cap.md)
- [RDBMS 깊이 읽기 #1: MySQL vs MariaDB vs PostgreSQL](../../content/posts/rdbms-1-open-source-rdbms-mysql-vs.md)

<!-- AUTO:related-sessions:start -->

## 관련 세션
이 문서와 관련된 세션 아카이브(자동 생성 — 태그 매칭 기반):

- [2026-08-16](../sessions/raw/2026-08-16.md)

<!-- AUTO:related-sessions:end -->