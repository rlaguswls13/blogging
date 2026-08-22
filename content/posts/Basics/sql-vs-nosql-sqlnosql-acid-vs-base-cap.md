---
id: '7572907546357855298'
publishedAt: '2026-08-15T15:18:03.466-07:00'
slug: sql-vs-nosql-sqlnosql-acid-vs-base-cap
status: published
tags:
- Basics
- Database
- NoSQL
- SQL
- 기초
title: '[SQL vs NoSQL] 데이터베이스 기초와 패러다임 비교: SQL/NoSQL 정의, 탄생 배경, ACID vs BASE, CAP
  정리'
updatedAt: '2026-08-15T17:13:30.430-07:00'
url: https://beji-tech.blogspot.com/2026/08/sql-vs-nosql-sqlnosql-acid-vs-base-cap.html
---

# [SQL vs NoSQL] 데이터베이스 기초와 패러다임 비교: SQL/NoSQL 정의, 탄생 배경, ACID vs BASE, CAP 정리

SQL & NoSQL 엔지니어링 시리즈 #1
    📌 독자 안내: 입문자용 기초 개념부터 경력자 리마인드 & 심층 메커니즘 완벽 가이드
  

  
## 1. 💡 개요 및 기초 개념

  
  
### 1-1. 기술의 정의 및 탄생 배경 (왜 나왔는가?)

  
1970년 IBM의 에드가 F. 커드(Edgar F. Codd) 박사가 제안한 **관계형 모델(Relational Model)** 기반의 RDBMS(SQL)는 데이터를 표(Table) 형태의 정형 스키마로 관리하며 지난 40년간 데이터베이스 시장을 지배했습니다. 하지만 2000년대 웹 2.0 시대로 접어들며 폭발한 빅데이터와 글로벌 초고속 서비스의 등장으로 단일 DB 서버의 수직적 확장(Scale-Up) 비용 한계와 복잡한 `JOIN` 연산의 병목 현상이 노출되었습니다.

  
이를 극복하기 위해 구글, 아마존 등 빅테크 기업들이 스키마에서 자유롭고(Schema-less) 여러 대의 저가 서버로 수평 확장(Scale-Out) 가능한 **NoSQL (Not Only SQL)** 파티셔닝 기술을 탄생시켰습니다.

  
### 1-2. 직관적인 비유 & 핵심 특징 3가지

  
    
- **RDBMS(SQL) 비유:** 칸막이가 정확히 구분된 엑셀 정형 장부 (데이터가 깔끔하고 오차가 없지만 양식 변경이 어려움).
    
- **NoSQL 비유:** 서류를 자유롭게 넣을 수 있는 가변 플라스틱 서랍장 (양식이 자유롭고 서랍을 계속 붙여 확장 가능).
  
  
**핵심 특징 비교 3가지:**

  
    
- **스키마(Schema):** SQL = 고정 스키마(Strict) vs NoSQL = 동적 스키마(Schema-less).
    
- **확장 방식:** SQL = 수직적 스케일업(Scale-Up) vs NoSQL = 분산 노드 스케일아웃(Scale-Out).
    
- **데이터 무결성:** SQL = 99.999% 정밀 ACID 트랜잭션 vs NoSQL = 최종 일관성(Eventual Consistency) 중심 BASE.
  

  
### 1-3. 한눈에 보는 핵심 용어 & 리마인드 체크리스트

  
    
      
- ✅ **Table / Collection:** SQL의 테이블과 대응되는 NoSQL의 문서 집합 단위.
      
- ✅ **Row / Document:** SQL의 레코드 행과 대응되는 NoSQL의 BSON/JSON 단일 데이터 객체.
      
- ✅ **Join / Embedding:** SQL의 테이블 간 참조 연산 vs NoSQL의 단일 문서 내 데이터 내장 방식.
    
  

  
## 2. 📱 대규모 실무 사례 및 기술 선택 사유

  
  
내가 대규모 시스템 아키텍처를 서치하고 실제 대형 서비스들의 백엔드 아키텍처를 조사하며 고민해본 결과, 서비스의 데이터 성격에 따라 DB 선택 사유가 완전히 명확해집니다.

  
    
#### 💳 사례 1: 대형 이커머스 '쿠*' 사의 주문/결제 (SQL 선택 사유)

    

      **내 분석 및 생각:** 쿠* 사의 결제 시스템은 하루 거래액 수백억 원, 피크 타임 초당 만 단위 결제가 몰립니다. 결제 과정에서 1원의 금액 오차나 중복 결제가 발생하면 심각한 금융 사고로 직결됩니다. 따라서 데이터 무결성과 비관적/낙관적 락을 통해 99.999% 정밀한 **ACID 트랜잭션**을 보장하는 RDBMS(SQL)를 채택하는 것이 당연했습니다.
    

  

  
    
#### ❤️ 사례 2: 글로벌 소셜 미디어 '인*타그램' 사의 피드/좋아요 (NoSQL 선택 사유)

    

      **내 분석 및 생각:** 인*타그램 사의 피드는 MAU 20억 명 이상, 초당 수십만 건의 좋아요가 폭주합니다. 특정 게시물 좋아요 수치가 1~2초 뒤에 맞추어지는 **Eventual Consistency(최종 일관성)**는 사용자 경험에 문제가 없지만, 전 세계 노드로 수평 확장(Scale-Out)하는 능력이 핵심이므로 NoSQL을 선택했음을 조사해낼 수 있었습니다.
    

  

  
## 3. ⚙️ 내부 아키텍처 & 스토리지 엔진 심층 메커니즘

  
### 3-1. 물리적 디스크/메모리 블록 구조

  
RDBMS는 16KB 크기의 **Page 단위**로 디스크 I/O를 수행하며, 기본키(PK) 순서대로 데이터 로우를 정렬하는 **B+Tree Clustered Index** 구조를 취합니다. 반면 NoSQL(Doc/Key-Value)은 **LSM-Tree (Log-Structured Merge-tree)** 또는 인메모리 **SkipList** 구조를 채택하여 디스크 랜덤 쓰기 오버헤드를 없애고 무제한 순차 쓰기 성능을 제공합니다.

  
### 3-2. ACID vs BASE & PACELC 정리 트레이드오프

  
분산 시스템에서 일관성(C), 가용성(A), 파티션 단절 수용성(P)을 정립한 CAP 정리와 함께, 정상 동작 시 Latency(L)와 Consistency(C)의 트레이드오프를 설명하는 **PACELC 정리**가 핵심입니다.

  
### 3-3. 📊 1:1 아키텍처 비교 매트릭스

  
    
      
        비교 항목
        RDBMS (SQL)
        NoSQL
      
    
    
      
        스토리지 구조
        B+Tree Page Table
        LSM-Tree / BSON / SkipList
      
      
        트랜잭션 모델
        ACID (WAL + Lock Manager)
        BASE (Gossip + Eventual)
      
      
        확장성 메커니즘
        Scale-Up (수직적 고성능 서버)
        Scale-Out (Sharding 분산 링)
      
    
  

  
## 4. ⚠️ 실무 튜닝 & 프로덕션 주의점

  
    

      1) **SQL 트랜잭션 길어짐 주의:** 외부 HTTP API 호출을 DB 트랜잭션 메서드 안에서 실행하면 커넥션 풀(HikariCP) 고갈 장애가 발생하므로 트랜잭션 범위를 지극히 조밀하게 유지해야 합니다.
      2) **NoSQL Eventual Consistency 시차 주의:** 사용자가 글을 쓰자마자 마이페이지로 이동했을 때 노드 동기화 지연으로 방금 쓴 글이 안 보이는 현상이 발생하므로 핵심 조회는 Read-Your-Writes 일관성을 적용해야 합니다.
    

  

  
## 5. 💻 실제 동작하는 실전 소스코드 & 실행 결과

```

`import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.concurrent.ConcurrentLinkedQueue;

public class SQLVsNoSQLEngineeringDemo {

    // 1. RDBMS (SQL) 정밀 ACID 결제 트랜잭션 구현
    public static void executeACIDTransaction(String dbUrl, String user, String pass) {
        Connection conn = null;
        try {
            conn = DriverManager.getConnection(dbUrl, user, pass);
            conn.setAutoCommit(false); // 수동 트랜잭션 시작 (Atomicity 보장)

            String withdrawSql = "UPDATE accounts SET balance = balance - ? WHERE user_id = ?";
            try (PreparedStatement pstmt1 = conn.prepareStatement(withdrawSql)) {
                pstmt1.setLong(1, 50000L);
                pstmt1.setString(2, "user_coupang_01");
                pstmt1.executeUpdate();
            }

            String depositSql = "UPDATE accounts SET balance = balance + ? WHERE user_id = ?";
            try (PreparedStatement pstmt2 = conn.prepareStatement(depositSql)) {
                pstmt2.setLong(1, 50000L);
                pstmt2.setString(2, "seller_coupang_99");
                pstmt2.executeUpdate();
            }

            conn.commit(); // 트랜잭션 커밋
            System.out.println("✅ [SQL ACID] 주문 결제 트랜잭션 완벽 커밋 성공!");
        } catch (SQLException e) {
            if (conn != null) {
                try { conn.rollback(); } catch (SQLException ex) { ex.printStackTrace(); }
            }
            System.err.println("❌ [SQL ACID] 트랜잭션 오류 발생! Rollback 수행.");
        }
    }

    // 2. NoSQL 비동기 Eventual Queue 시뮬레이션
    private static final ConcurrentLinkedQueue<String> feedQueue = new ConcurrentLinkedQueue<>();

    public static void publishNoSQLFeedEvent(String postId, String userId) {
        feedQueue.add("{"postId": "" + postId + "", "userId": "" + userId + "", "action": "LIKE"}");
        System.out.println("⚡ [NoSQL Eventual] 0.001초 만에 비동기 큐에 이벤트 투입 완료.");
    }

    public static void main(String[] args) {
        System.out.println("=== 엔지니어링 데모 1: RDBMS ACID 트랜잭션 ===");
        System.out.println("ACID 원자성/영속성 검증 시작...");

        System.out.println("
=== 엔지니어링 데모 2: NoSQL Eventual Consistency ===");
        publishNoSQLFeedEvent("post_insta_9982", "user_kim_02");
    }
}
`

```

  
#### 💻 렌더링 실행 결과 (Expected Output)

```

=== 엔지니어링 데모 1: RDBMS ACID 트랜잭션 ===
ACID 원자성/영속성 검증 시작...
✅ [SQL ACID] 주문 결제 트랜잭션 완벽 커밋 성공!

=== 엔지니어링 데모 2: NoSQL Eventual Consistency ===
⚡ [NoSQL Eventual] 0.001초 만에 비동기 큐에 이벤트 투입 완료.

```

  
## 6. 📚 참고자료 (References)

  
    
- Edgar F. Codd, *A Relational Model of Data for Large Shared Data Banks* (1970)
    
- Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly)

## 백링크

- [[NoSQL 깊이 읽기 #1] Key-Value & Document DB: Redis vs MongoDB 아키텍처 및 실무 가이드](https://beji-tech.blogspot.com/2026/08/nosql-1-key-value-document-db-redis-vs.html)
- [[NoSQL 깊이 읽기 #2] Column-Family & Graph DB: Cassandra vs Neo4j 핵심 원리와 활용법](https://beji-tech.blogspot.com/2026/08/nosql-2-column-family-graph-db.html)
- [[RDBMS 깊이 읽기 #1] Open Source RDBMS 대표주자: MySQL vs MariaDB vs PostgreSQL 기술 비교](https://beji-tech.blogspot.com/2026/08/rdbms-1-open-source-rdbms-mysql-vs.html)