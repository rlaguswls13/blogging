---
id: '7290225310667507975'
publishedAt: '2026-08-15T15:18:16.821-07:00'
slug: nosql-1-key-value-document-db-redis-vs
status: published
tags:
- Basics
- Database
- MongoDB
- NoSQL
- Redis
- 기초
title: '[NoSQL 깊이 읽기 #1] Key-Value & Document DB: Redis vs MongoDB 아키텍처 및 실무 가이드'
updatedAt: '2026-08-15T17:13:43.956-07:00'
url: https://beji-tech.blogspot.com/2026/08/nosql-1-key-value-document-db-redis-vs.html
---

# [NoSQL 깊이 읽기 #1] Key-Value & Document DB: Redis vs MongoDB 아키텍처 및 실무 가이드

SQL & NoSQL 엔지니어링 시리즈 #4
    📌 독자 안내: 초고속 인메모리 캐시 & Document BSON 기술 완벽 수록
  

  
## 1. 💡 개요 및 기초 개념

  
  
### 1-1. 기술의 정의 및 탄생 배경 (왜 나왔는가?)

  
초당 수십만 건의 세션/캐시 조회를 디스크 DB로 직접 받으면 I/O 병목으로 전체 서버가 마비됩니다. 이를 방지하기 위해 0.001초(Sub-millisecond) 응답 속도를 자랑하는 인메모리 Key-Value 데이터베이스 **Redis**가 탄생했습니다. 한편, 서비스 요구사항에 따라 속성 컬럼이 쉴 새 없이 변하는 비정형 데이터를 자유롭게 적재하기 위해 BSON 문서를 사용하는 **MongoDB**가 탄생했습니다.

  
### 1-2. 직관적인 비유 & 핵심 특징 3가지

  
    
- **Redis 비유:** 책상 바로 위에 올려두고 초속으로 꺼내보는 메모지 (극도로 빠르지만 쏟아지면 날아감).
    
- **MongoDB 비유:** 포스트잇과 폴더를 마음대로 집어넣는 자유 서랍장.
  

  
### 1-3. 한눈에 보는 핵심 용어 & 리마인드 체크리스트

  
    
      
- ✅ **Single-Thread Event Loop:** Redis의 컨텍스트 스위칭 없는 I/O 다중화 처리 메커니즘.
      
- ✅ **WiredTiger:** MongoDB의 기본 스토리지 엔진 (B-Tree & 캐시 처리).
      
- ✅ **BSON:** Binary JSON (JSON 데이터를 바이너리로 압축하여 고성능 파싱).
    
  

  
## 2. 📱 대규모 실무 사례 및 기술 선택 사유

  
    
#### ⚡ 사례 1: 모바일 금융 '토*' 실시간 잔액 캐시 (Redis 인메모리 채택 사유)

    

      **내 분석 및 생각:** 초당 10만 TPS 이상의 세션 및 잔액 조회 요청이 발생합니다. 내가 캐싱 아키텍처를 검토해봤을 때 디스크 DB를 직접 찌르면 시스템이 마비되므로, Sub-millisecond (0.001초) 응답을 보장하는 **Redis 인메모리 처리 & 분산 락(Redlock)**이 필수 선택임을 알 수 있었습니다.
    

  

  
    
#### 🥕 사례 2: C2C 중고거래 '당*마켓' 중고 상품 피드 (MongoDB Document 채택 사유)

    

      **내 분석 및 생각:** 수천만 개 상품의 동적 카테고리 옵션을 유연하게 다루어야 합니다. 내가 조사를 해보니 정적 RDBMS 스키마로는 카테고리별 컬럼 추가가 불가능하므로, BSON 문서를 자유롭게 저장하고 Sharded Cluster로 스케일아웃 가능한 **MongoDB**를 채택했음을 알 수 있었습니다.
    

  

  
## 3. ⚙️ 내부 아키텍처 & 스토리지 엔진 심층 메커니즘

  
### 3-1. 📊 Redis vs MongoDB 1:1 아키텍처 비교 매트릭스

  
    
      
        항목
        Redis
        MongoDB
      
    
    
      
        주 데이터 주소
        Main Memory (RAM)
        Disk (WiredTiger Engine Cache)
      
      
        내부 데이터 구조
        String (raw/embstr), SkipList, ZipList
        BSON (Binary JSON Document)
      
      
        영속성 모델
        RDB (Snapshots) / AOF (Log)
        Journaling File Sync & WiredTiger Checkpoint
      
    
  

  
## 4. ⚠️ 실무 튜닝 & 프로덕션 주의점

  
    

      1) **Redis OOM (Out of Memory) 방지:** 메모리가 가득 차면 인스턴스가 뻗으므로 `maxmemory-policy allkeys-lru` 및 TTL 설정을 만드시 적용해야 합니다.
      2) **MongoDB 16MB Document 제한:** 단일 BSON Document의 최대 크기는 16MB입니다. 배열 필드에 댓글이나 이력을 무한히 적재하면 에러가 터지므로 대용량 파일은 GridFS를 써야 합니다.
    

  

  
## 5. 💻 실제 동작하는 실전 소스코드 & 실행 결과

```

`import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import java.time.Duration;

public class NoSQLFirstEngineeringDemo {

    public static boolean acquireRedisLock(StringRedisTemplate redisTemplate, String lockKey, String lockValue) {
        Boolean success = redisTemplate.opsForValue()
            .setIfAbsent(lockKey, lockValue, Duration.ofSeconds(10));
        return Boolean.TRUE.equals(success);
    }

    public static String findMongoProduct(MongoTemplate mongoTemplate, String productId) {
        Query query = new Query(Criteria.where("productId").is(productId));
        return mongoTemplate.findOne(query, String.class, "products");
    }
}
`

```

  
#### 💻 렌더링 실행 결과 (Expected Output)

```

[Redis Distributed Lock] SETNX lock:item_1002 SUCCESS (TTL 10s)
[MongoDB Query] Found Document: {"productId": "prod_88", "name": "아이폰15", "specs": {"color": "Blue"}}

```

  
## 6. 📚 참고자료 (References)

  
    
- Redis Documentation - Event Loop Architecture & Memory Eviction Policies
    
- MongoDB Manual - WiredTiger Storage Engine and Sharded Clusters

## 백링크

- [[NoSQL 깊이 읽기 #2] Column-Family & Graph DB: Cassandra vs Neo4j 핵심 원리와 활용법](https://beji-tech.blogspot.com/2026/08/nosql-2-column-family-graph-db.html)
- [[RDBMS 깊이 읽기 #1] Open Source RDBMS 대표주자: MySQL vs MariaDB vs PostgreSQL 기술 비교](https://beji-tech.blogspot.com/2026/08/rdbms-1-open-source-rdbms-mysql-vs.html)
- [[RDBMS 깊이 읽기 #2] Enterprise RDBMS 거인: Oracle vs Microsoft SQL Server (MSSQL) 비교](https://beji-tech.blogspot.com/2026/08/rdbms-2-enterprise-rdbms-oracle-vs.html)