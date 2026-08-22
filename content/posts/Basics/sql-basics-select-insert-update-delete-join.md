---
author: AI Tech Editor
createdAt: '2026-08-19T05:40:10.738795Z'
factCheckScore: 0
id: '6255842262534342636'
notionPageId: null
publishedAt: '2026-08-18T22:45:36-07:00'
slug: sql-basics-select-insert-update-delete-join
status: published
tags:
- Basics
- SQL
- Database
- RDBMS
title: SQL 기본 문법 입문 — SELECT/INSERT/UPDATE/DELETE와 JOIN, WHERE, GROUP BY 실전 예시
updatedAt: '2026-08-19T05:40:10.738795Z'
url: https://beji-tech.blogspot.com/2026/08/sql-selectinsertupdatedelete-join-where.html
---


# SQL 기본 문법 입문 — SELECT/INSERT/UPDATE/DELETE와 JOIN, WHERE, GROUP BY 실전 예시

## 요약

관계형 데이터베이스(RDBMS)를 다루는 모든 백엔드 개발자가 가장 먼저 익혀야 하는 것이 SQL(Structured Query Language)입니다. 이 글은 SQL이 처음인 개발자를 위해 데이터를 조회·추가·수정·삭제하는 4대 기본 명령(SELECT/INSERT/UPDATE/DELETE)과, 여러 테이블을 엮어 조회하는 JOIN, 조건을 거는 WHERE, 그룹별로 집계하는 GROUP BY/HAVING을 실제로 실행 가능한 예제 코드와 함께 하나씩 설명합니다. MySQL과 PostgreSQL 공식 문서 기준으로 문법을 검증했으며, 두 DBMS 간 차이가 있는 부분은 명시적으로 짚었습니다.

## 본문

### 1. SQL은 무엇을 하는 언어인가

SQL은 관계형 데이터베이스에 저장된 데이터를 "선언적으로" 다루는 언어입니다. 프로그래밍 언어처럼 "어떻게(How)" 처리할지 알고리즘을 적지 않고, "무엇을(What)" 원하는지만 선언하면 DBMS 내부의 쿼리 옵티마이저가 실행 계획을 알아서 세웁니다. SQL 문법은 크게 두 갈래로 나뉩니다.

- **DDL(Data Definition Language)**: 테이블 구조 자체를 정의합니다. `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE` 등이 여기 속합니다.
- **DML(Data Manipulation Language)**: 테이블 안의 데이터를 다룹니다. 이 글에서 다루는 `SELECT`, `INSERT`, `UPDATE`, `DELETE`가 여기 속합니다.

이 글은 실무에서 가장 자주 쓰는 DML 4종과, DML을 강력하게 만들어주는 `WHERE`/`JOIN`/`GROUP BY`/`HAVING`/`ORDER BY` 절에 집중합니다.

### 2. 실습용 예제 스키마

아래 두 테이블을 기준으로 모든 예제를 실행합니다. `orders.user_id`는 `users.id`를 가리키는 외래 키(Foreign Key)로, "이 주문은 어떤 사용자가 했는가"를 표현합니다.

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    signup_date DATE NOT NULL
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    price INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3. SELECT — 데이터 조회

`SELECT`는 네 명령 중 가장 자주 쓰이며, 기본 골격은 다음과 같습니다. PostgreSQL 공식 문서는 `SELECT` 문의 논리적 처리 순서를 `FROM → WHERE → GROUP BY/HAVING → SELECT 출력 → ORDER BY → LIMIT/OFFSET`로 명시합니다. 문법 구조로 표현하면 `SELECT ... FROM ... [WHERE ...] [GROUP BY ...] [HAVING ...] [ORDER BY ...] [LIMIT ...]`가 됩니다.

```sql
-- users 테이블 전체 컬럼 조회
SELECT * FROM users;

-- 특정 컬럼만 조회
SELECT name, email FROM users;

-- WHERE로 조건 필터링
SELECT name, email FROM users WHERE signup_date >= '2026-01-01';
```

`WHERE`는 행(row) 단위로 조건을 검사해 만족하는 행만 결과에 포함시킵니다. 비교 연산자(`=`, `!=`, `>`, `<`, `>=`, `<=`)뿐 아니라, 여러 값 중 하나와 일치하는지 확인하는 `IN`, 범위를 지정하는 `BETWEEN`, 패턴 매칭을 하는 `LIKE`도 자주 씁니다.

```sql
SELECT * FROM orders WHERE status IN ('paid', 'shipped');
SELECT * FROM orders WHERE price BETWEEN 10000 AND 50000;
SELECT * FROM users WHERE email LIKE '%@gmail.com';
```

**초보자가 흔히 놓치는 함정**: `WHERE column = NULL`은 항상 결과가 없습니다. SQL에서 `NULL`은 "값이 없음"이 아니라 "알 수 없음"을 의미하는 특수한 상태라서 `=` 비교 자체가 성립하지 않기 때문입니다. `NULL` 여부는 반드시 `IS NULL` / `IS NOT NULL`로 확인해야 합니다.

### 4. ORDER BY와 LIMIT — 정렬과 개수 제한

```sql
-- 가격이 비싼 순서(내림차순)로 정렬
SELECT * FROM orders ORDER BY price DESC;

-- 정렬 후 상위 5건만 조회 (페이지네이션의 기초)
SELECT * FROM orders ORDER BY price DESC LIMIT 5;

-- 6번째부터 10번째까지 (오프셋 5, 5건)
SELECT * FROM orders ORDER BY price DESC LIMIT 5 OFFSET 5;
```

`ORDER BY`에 `ASC`/`DESC`를 생략하면 기본값은 오름차순(`ASC`)입니다. `LIMIT`은 MySQL/PostgreSQL 표준 문법이지만, SQL Server는 `TOP`, Oracle은 `FETCH FIRST` 구문을 쓰는 등 DBMS마다 다르다는 점은 주의해야 합니다.

### 5. INSERT — 데이터 추가

```sql
-- 컬럼을 명시하고 값 삽입 (권장 방식)
INSERT INTO users (name, email, signup_date)
VALUES ('김철수', 'chulsoo@example.com', '2026-08-19');

-- 한 번에 여러 행 삽입
INSERT INTO orders (user_id, product_name, price, status)
VALUES
    (1, '무선 키보드', 45000, 'paid'),
    (1, '노트북 거치대', 28000, 'pending');
```

`id` 컬럼은 `AUTO_INCREMENT`로 선언했으므로 `INSERT` 문에서 값을 넣지 않아도 DBMS가 자동으로 채워줍니다. 컬럼명을 생략하고 `INSERT INTO users VALUES (...)` 형태로 쓸 수도 있지만, 테이블 구조가 바뀌었을 때 값이 엉뚱한 컬럼에 들어가는 사고를 방지하기 위해 실무에서는 컬럼명을 항상 명시하는 것이 권장됩니다.

### 6. UPDATE — 데이터 수정

```sql
UPDATE orders
SET status = 'shipped'
WHERE id = 2;
```

**가장 위험한 실수**: `UPDATE` 문에서 `WHERE`를 빼먹으면 테이블의 **모든 행**이 수정됩니다. 예를 들어 `UPDATE orders SET status = 'shipped';`를 실수로 실행하면 주문 전체의 상태가 한꺼번에 바뀝니다. 실무에서는 `UPDATE`를 실행하기 전에 동일한 `WHERE` 조건으로 `SELECT`를 먼저 돌려서 "정말 이 행들만 바뀌는 게 맞는지" 확인하는 습관이 사고를 예방합니다.

### 7. DELETE — 데이터 삭제

```sql
DELETE FROM orders WHERE status = 'cancelled';
```

`DELETE`도 `UPDATE`와 마찬가지로 `WHERE`를 빠뜨리면 테이블의 전체 행이 삭제됩니다. 테이블 전체를 비우는 것이 명확한 목적이라면, 행 단위 삭제 로그를 남기지 않아 훨씬 빠른 `TRUNCATE TABLE orders;`를 대신 쓰는 것이 일반적입니다.

### 8. JOIN — 여러 테이블 엮어 조회하기

지금까지는 테이블 하나만 다뤘지만, 실무 데이터는 여러 테이블에 정규화되어 흩어져 있습니다. "각 사용자가 무엇을 주문했는지" 알려면 `users`와 `orders`를 엮어야 합니다. PostgreSQL 공식 튜토리얼(2.6. Joins Between Tables)은 `JOIN`(별도 지정이 없으면 `INNER JOIN`과 동일)과 `LEFT OUTER JOIN`의 동작을 다음과 같이 설명합니다.

```sql
-- INNER JOIN: 양쪽 테이블에 모두 매칭되는 행만 반환
SELECT u.name, o.product_name, o.price
FROM users u
INNER JOIN orders o ON u.id = o.user_id;

-- LEFT JOIN: users 전체 + 매칭되는 orders (주문이 없으면 NULL)
SELECT u.name, o.product_name
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

`INNER JOIN`은 두 테이블에서 `ON` 조건이 일치하는 행만 결과에 남기므로, 주문을 한 번도 안 한 사용자는 결과에서 통째로 빠집니다. 반면 `LEFT JOIN`은 왼쪽 테이블(`users`)의 모든 행을 무조건 유지하고, 오른쪽 테이블(`orders`)에 매칭되는 행이 없으면 해당 컬럼을 `NULL`로 채웁니다. "가입은 했지만 아직 주문이 없는 사용자까지 포함해서 보고 싶다"면 `LEFT JOIN`을, "실제 주문 내역만 보고 싶다"면 `INNER JOIN`을 선택합니다.

### 9. GROUP BY와 HAVING — 그룹별 집계

"사용자별 총 주문 금액"처럼 여러 행을 하나로 묶어 집계할 때 `GROUP BY`를 씁니다. `COUNT`, `SUM`, `AVG`, `MAX`, `MIN` 같은 집계 함수와 함께 쓰는 것이 일반적입니다.

```sql
-- 사용자별 총 주문 금액과 주문 건수
SELECT u.name, COUNT(o.id) AS order_count, SUM(o.price) AS total_spent
FROM users u
JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;

-- 총 주문 금액이 5만원 이상인 사용자만 (그룹 필터링)
SELECT u.name, SUM(o.price) AS total_spent
FROM users u
JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name
HAVING SUM(o.price) >= 50000;
```

`WHERE`와 `HAVING`을 헷갈리는 초보자가 많은데, 둘의 차이는 명확합니다. `WHERE`는 그룹으로 묶기 **전** 개별 행을 걸러내고, `HAVING`은 `GROUP BY`로 그룹을 만든 **후** 집계 결과(`SUM`, `COUNT` 등)를 기준으로 그룹을 걸러냅니다. `WHERE` 절에는 집계 함수를 쓸 수 없다는 것도 이 때문입니다. SQL 문의 논리적 실행 순서는 `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT` 순이라, `WHERE` 시점에는 아직 그룹 집계 값 자체가 계산되지 않은 상태입니다.

### 10. 실무로 넘어가기 전에 알아둘 것

`JOIN`에 사용하는 컬럼(`orders.user_id`처럼 다른 테이블을 참조하는 외래 키)에 인덱스가 없으면, 테이블이 커질수록 조인 성능이 급격히 나빠집니다. 실무에서는 자주 조인하는 컬럼에 인덱스를 걸어두는 것이 기본입니다. 또한 `UPDATE`/`DELETE`처럼 데이터를 변경하는 여러 문장을 하나의 논리적 작업으로 묶어야 할 때는 `BEGIN`/`COMMIT`으로 감싸는 트랜잭션 개념이 필요한데, 이는 별도의 심화 주제로 다룰 만큼 범위가 넓어 이 글에서는 존재만 언급합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: SELECT 문의 논리적 처리 순서는 FROM → WHERE → GROUP BY/HAVING → SELECT 출력 → ORDER BY → LIMIT/OFFSET 순이다 | verified | PostgreSQL 18 공식 문서, "SELECT" (postgresql.org, 확인일: 2026-08-19) |
| CLAIM-002: LIMIT과 OFFSET은 각각 반환할 최대 행 수와 건너뛸 행 수를 지정하는 별개의 절이다 | verified | PostgreSQL 18 공식 문서, "SELECT" (postgresql.org, 확인일: 2026-08-19) |
| CLAIM-003: HAVING 절은 WHERE 절과 달리 GROUP BY로 묶인 그룹에 대해 집계 함수 결과를 조건으로 걸 수 있다 | verified | PostgreSQL 18 공식 문서, "SELECT" (postgresql.org, 확인일: 2026-08-19) |
| CLAIM-004: JOIN(별도 명시 없을 시 INNER JOIN)은 두 테이블에서 조건이 일치하는 행만 반환하고, LEFT OUTER JOIN은 왼쪽 테이블의 모든 행을 유지하며 매칭되지 않는 오른쪽 컬럼은 NULL로 채운다 | verified | PostgreSQL 18 공식 문서, "2.6. Joins Between Tables" (postgresql.org, 확인일: 2026-08-19) |
| CLAIM-005: SQL 문의 논리적 실행 순서는 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY 순이다 | verified | PostgreSQL 18 공식 문서, Chapter 6 "Data Manipulation" 및 MySQL 8.4 Reference Manual "SELECT Statement" 교차 확인 (확인일: 2026-08-19) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

SQL을 처음 배우는 개발자에게 가장 강조하고 싶은 것은 "SQL은 순서대로 실행되지 않는다"는 점입니다. 코드를 위에서 아래로 읽듯 `SELECT`부터 실행된다고 착각하기 쉽지만, 실제로는 `FROM`(어느 테이블을 볼지) → `WHERE`(어떤 행을 남길지) → `GROUP BY`/`HAVING`(어떻게 묶고 걸러낼지) → `SELECT`(어떤 컬럼을 보여줄지) → `ORDER BY`(어떻게 정렬할지) 순으로 처리됩니다. 이 실행 순서를 모른 채 문법을 외우면 `WHERE`에서 `SELECT`에 정의한 별칭(alias)을 왜 못 쓰는지, `HAVING`은 왜 집계 함수를 쓸 수 있는데 `WHERE`는 안 되는지 같은 질문에 계속 부딪히게 됩니다. 개인적으로는 처음 SQL을 배울 때 이 실행 순서 하나만 확실히 이해하고 넘어가면, 이후에 마주치는 대부분의 "이상한 에러"가 사실은 이 순서를 몰라서 생긴 문제라는 걸 스스로 깨닫게 된다고 생각합니다. 또한 `UPDATE`/`DELETE`에 `WHERE`를 빠뜨려 전체 테이블을 망가뜨리는 사고는 신입 개발자뿐 아니라 경력자도 종종 저지르는 실수이므로, 실행 전 `SELECT`로 대상 행을 먼저 확인하는 습관을 처음부터 몸에 익히는 것을 권합니다.

## 한계와 반론

- **한계점**: 이 글은 MySQL과 PostgreSQL이라는 두 대표 오픈소스 RDBMS를 기준으로 문법을 검증했습니다. 오라클(Oracle)의 `FETCH FIRST n ROWS ONLY`, SQL Server의 `TOP`, `MERGE` 문처럼 벤더별로 문법이 갈리는 부분은 다루지 않았으므로, 실제 사용하는 DBMS의 공식 문서로 세부 문법 차이를 반드시 재확인해야 합니다.
- **반론**: "SQL 표준(ISO/IEC 9075)만 익히면 어느 DBMS에서든 동일하게 쓸 수 있다"는 통념이 있지만, 실제로는 `LIMIT`/`TOP`/`FETCH FIRST`처럼 표준에 없거나 벤더가 확장한 구문이 실무에서 매우 흔히 쓰입니다. 따라서 표준 문법과 함께 실제 배포 환경의 DBMS 공식 문서를 병행해서 학습하는 것이 실무에서는 더 안전합니다.

## 참고문헌

1. PostgreSQL Global Development Group, "PostgreSQL 18 Documentation — SELECT", [https://www.postgresql.org/docs/current/sql-select.html](https://www.postgresql.org/docs/current/sql-select.html) (확인일: 2026-08-19)
2. PostgreSQL Global Development Group, "PostgreSQL 18 Documentation — 2.6. Joins Between Tables", [https://www.postgresql.org/docs/current/tutorial-join.html](https://www.postgresql.org/docs/current/tutorial-join.html) (확인일: 2026-08-19)
3. PostgreSQL Global Development Group, "PostgreSQL 18 Documentation — Chapter 6. Data Manipulation", [https://www.postgresql.org/docs/current/dml.html](https://www.postgresql.org/docs/current/dml.html) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

SQL은 등장한 지 50년 가까이 된 언어지만, 관계형 데이터베이스가 여전히 대부분의 서비스 백엔드의 근간을 이루고 있는 한 앞으로도 개발자가 피해갈 수 없는 필수 기술입니다. 이 글에서 다룬 `SELECT`/`INSERT`/`UPDATE`/`DELETE`와 `WHERE`/`JOIN`/`GROUP BY`/`HAVING`은 실무에서 작성하는 쿼리의 90% 이상을 구성하는 핵심 뼈대입니다. 다만 문법을 외우는 것과 실제 데이터베이스를 안전하게 다루는 것은 다른 차원의 문제입니다. `WHERE` 없는 `UPDATE`/`DELETE`가 만드는 사고, `NULL` 비교의 함정, 인덱스 없는 `JOIN`이 만드는 성능 저하처럼 문법책에는 잘 나오지 않지만 실무에서 반드시 부딪히는 함정들을 이 글에서 함께 짚은 이유도 여기에 있습니다. SQL 문법 자체는 며칠이면 익힐 수 있지만, "왜 이렇게 동작하는가"를 이해하는 데는 시간이 필요합니다. 이 글이 그 시작점이 되기를 바라며, 다음 단계로는 인덱스의 내부 구조나 트랜잭션과 격리 수준처럼 SQL을 "안전하고 빠르게" 쓰는 주제로 넘어가는 것을 추천합니다.

## 꼬리질문

1. **인덱스가 걸린 컬럼과 안 걸린 컬럼에 대해 동일한 WHERE 조건 쿼리를 실행하면 실행 계획(EXPLAIN)이 실제로 어떻게 달라지는가?**
   - 추천 참고 URL: https://dev.mysql.com/doc/refman/8.4/en/explain.html
2. **BEGIN/COMMIT으로 감싼 트랜잭션 안에서 UPDATE 두 개가 서로 다른 순서로 같은 행을 잠그려 할 때 데드락은 어떻게 발생하고 DBMS는 이를 어떻게 감지·해소하는가?**
   - 추천 참고 URL: https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html
3. **서브쿼리(Subquery)와 JOIN으로 동일한 결과를 얻을 수 있는 경우, 옵티마이저는 두 방식의 실행 계획을 실제로 동일하게 최적화하는가?**
   - 추천 참고 URL: https://www.postgresql.org/docs/current/queries-table-expressions.html

## 백링크

- [RDBMS 깊이 읽기 #1: MySQL vs MariaDB vs PostgreSQL](https://beji-tech.blogspot.com/2026/08/rdbms-1-open-source-rdbms-mysql-vs.html)
- [SQL vs NoSQL 데이터베이스 기초와 패러다임 비교](https://beji-tech.blogspot.com/2026/08/sql-vs-nosql-sqlnosql-acid-vs-base-cap.html)
- [MySQL InnoDB B+Tree 인덱스 내부 구조](https://beji-tech.blogspot.com/2026/08/mysql-innodb-btree-covering-index.html)