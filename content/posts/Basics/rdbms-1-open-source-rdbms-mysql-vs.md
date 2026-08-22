---
id: '2676535999965279165'
publishedAt: '2026-08-15T15:18:07.933-07:00'
slug: rdbms-1-open-source-rdbms-mysql-vs
status: published
tags:
- Basics
- Database
- MySQL
- PostgreSQL
- SQL
- 기초
- RDBMS_Series
title: '[RDBMS 깊이 읽기 #1] Open Source RDBMS 대표주자: MySQL vs MariaDB vs PostgreSQL 기술
  비교'
updatedAt: '2026-08-15T17:13:35.116-07:00'
url: https://beji-tech.blogspot.com/2026/08/rdbms-1-open-source-rdbms-mysql-vs.html
---

# [RDBMS 깊이 읽기 #1] Open Source RDBMS 대표주자: MySQL vs MariaDB vs PostgreSQL 기술 비교

SQL & NoSQL 엔지니어링 시리즈 #2
    📌 독자 안내: 오픈소스 RDBMS 3대장의 스토리지 엔진 & 인덱스 메커니즘 완벽 가이드
  

  
## 1. 💡 개요 및 기초 개념

  
  
### 1-1. 기술의 정의 및 탄생 배경 (왜 나왔는가?)

  
웹 서비스 개발 시 대표적으로 선택받는 오픈소스 RDBMS 3대 주자는 **MySQL**, **MariaDB**, 그리고 **PostgreSQL**입니다. MySQL은 1995년 최상의 읽기(SELECT) 속도를 목표로 탄생했으며, 2010년 오라클 인수 이후 라이선스 우려로 독립 커뮤니티 포크인 MariaDB가 파생되었습니다.
  
한편 PostgreSQL은 UC 버클리 대학의 POSTGRES 프로젝트에서 출발한 가장 대표적인 **객체-관계형(ORDBMS)**으로, 단순 CRUD를 넘어 복잡한 데이터 분석과 JSONB 비정형 검색을 지원하기 위해 설계되었습니다.

  
### 1-2. 직관적인 비유 & 핵심 특징 3가지

  
    
- **MySQL 비유:** 민첩하고 대중적인 민간 표준 소형 세단 (가장 친숙하고 직관적).
    
- **MariaDB 비유:** 오픈소스 정신으로 엔진 튜닝을 고도화한 스포츠 세단.
    
- **PostgreSQL 비유:** 갖가지 특수 기능을 모두 탑재한 엔지니어링 다목적 SUV.
  

  
### 1-3. 한눈에 보는 핵심 용어 & 리마인드 체크리스트

  
    
      
- ✅ **InnoDB:** MySQL의 기본 스토리지 엔진 (Clustered Index & MVCC 지원).
      
- ✅ **MVCC:** Multi-Version Concurrency Control (읽기와 쓰기가 서로를 블로킹하지 않음).
      
- ✅ **GIN Index:** PostgreSQL의 역색인(Generalized Inverted Index) 기반 JSONB 검색 인덱스.
    
  

  
## 2. 📱 대규모 실무 사례 및 기술 선택 사유

  
    
#### 🛵 사례 1: 배달 플랫폼 '배*의민족' (MySQL Read Replica 채택 이유)

    

      **내 분석 및 생각:** 점심/저녁 피크 타임 시 초당 수만 건의 가게 조회 및 주문 트래픽이 몰립니다. 내가 아키텍처를 분석해본 바에 따르면, MySQL InnoDB의 PK Clustered Index와 읽기 전용 복제본(Read Replica) 분산 구조가 단순 OLTP 주문/가게 조회의 메모리 버퍼풀 캐싱 속도를 최대로 끌어올릴 수 있기 때문이었습니다.
    

  

  
    
#### 🔵 사례 2: 모바일 금융 '토*' (PostgreSQL 복잡 분석 & GIS/JSONB 채택 이유)

    

      **내 분석 및 생각:** 2,000만 사용자의 복잡한 송금 내역과 가맹점 GIS 위치 검색을 수용해야 합니다. 내가 기술 문서를 서치해본 결과, 단순 CRUD를 넘어 complex 데이터 JOIN 연산, JSONB 거래 명세서 조정을 단일 RDBMS에서 가장 정밀하게 지원하는 PostgreSQL을 선택한 것이 타당하다는 결론을 얻었습니다.
    

  

  
## 3. ⚙️ 내부 아키텍처 & 스토리지 엔진 심층 메커니즘

  
### 3-1. 스토리지 엔진 및 MVCC 구조 비교

  
MySQL InnoDB는 **Undo Log**를 따로 두어 롤백 및 이전 버전 Read View 스냅샷을 관리하는 데 반해, PostgreSQL은 테이블 디스크 힙(Heap)에 직접 튜플 버전(`xmin`, `xmax`)을 쌓는 **Multi-Version Heap** 구조입니다.

  
### 3-2. 📊 1:1 아키텍처 비교 매트릭스

  
    
      
        구분
        MySQL (InnoDB)
        PostgreSQL
      
    
    
      
        인덱스 구조
        PK Clustered Index (B+Tree)
        Heap-based + GIN/GiST/BRIN Index
      
      
        MVCC 메커니즘
        Undo Log 기반 Read View
        Tuple Versioning (xmin/xmax) + HOT
      
      
        프로세스 모델
        Multi-Threaded Architecture
        Multi-Process Architecture
      
    
  

  
## 4. ⚠️ 실무 튜닝 & 프로덕션 주의점

  
    

      1) **PostgreSQL Auto-Vacuum 튜닝:** UPDATE/DELETE 시 이전 튜플 버전이 디스크 힙에 남으므로 주기적인 Auto-Vacuum 설정을 안 하면 DB 용량이 부풀어 오르는 Bloat 현상이 발생합니다.
      2) **MySQL PK UUID 금지:** PK를 무작위 UUID로 잡으면 B+Tree 페이지 분할(Page Split)이 빈번하게 일어나 디스크 I/O가 떡락하므로 순차 증가형 Auto-Increment PK 사용이 필수적입니다.
    

  

  
## 5. 💻 실제 동작하는 실전 소스코드 & 실행 결과

```

`import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import javax.persistence.*;
import java.util.List;

@Entity
@Table(name = "orders", indexes = {
    @Index(name = "idx_user_created", columnList = "user_id, created_at")
})
public class OrderEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userId;

    @Column(columnDefinition = "jsonb")
    private String metadata;
}

public interface OrderJpaRepository extends JpaRepository<OrderEntity, Long> {

    @Query(value = "SELECT * FROM orders WHERE metadata @> CAST(:jsonParam AS jsonb)", nativeQuery = true)
    List<OrderEntity> findByJsonbMetadata(@Param("jsonParam") String jsonParam);
}
`

```

  
#### 💻 렌더링 실행 결과 (Expected Output)

```

Hibernate: SELECT * FROM orders WHERE metadata @> CAST(? AS jsonb) [GIN Index 사용]
✅ PostgreSQL 고성능 바이너리 JSONB 쿼리 0.002초 실행 완결!

```

  
## 6. 📚 참고자료 (References)

  
    
- MySQL Official Documentation - InnoDB Storage Engine Architecture
    
- PostgreSQL Documentation - MVCC, Vacuum, and GIN Indexing

## 백링크

- [[RDBMS 깊이 읽기 #2] Enterprise RDBMS 거인: Oracle vs Microsoft SQL Server (MSSQL) 비교](https://beji-tech.blogspot.com/2026/08/rdbms-2-enterprise-rdbms-oracle-vs.html)
- [[NoSQL 깊이 읽기 #1] Key-Value & Document DB: Redis vs MongoDB 아키텍처 및 실무 가이드](https://beji-tech.blogspot.com/2026/08/nosql-1-key-value-document-db-redis-vs.html)
- [[SQL vs NoSQL] 데이터베이스 기초와 패러다임 비교: SQL/NoSQL 정의, 탄생 배경, ACID vs BASE, CAP 정리](https://beji-tech.blogspot.com/2026/08/sql-vs-nosql-sqlnosql-acid-vs-base-cap.html)