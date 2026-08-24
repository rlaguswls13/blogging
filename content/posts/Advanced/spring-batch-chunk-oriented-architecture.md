---
author: ''
createdAt: '2026-08-22T18:36:39.991593Z'
factCheckScore: 0
id: '2976561461352377425'
notionPageId: null
publishedAt: '2026-08-23T17:10:13-07:00'
slug: spring-batch-chunk-oriented-architecture
status: published
tags:
- Advanced
- Spring
- Batch
title: Spring Batch — 대용량 데이터 처리를 위한 Chunk 지향 아키텍처
updatedAt: '2026-08-22T18:36:39.991593Z'
url: https://beji-tech.blogspot.com/2026/08/spring-batch-chunk.html
---

# Spring Batch — 대용량 데이터 처리를 위한 Chunk 지향 아키텍처

## 요약

Spring Batch의 Chunk 지향 처리가 왜 행 단위도 Job 전체 단위도 아닌 절충안인지, 실제 코드와 함께 정리한 글입니다. `Job`-`Step`-`ItemReader`/`ItemProcessor`/`ItemWriter` 구조를 나열하는 글은 이미 많지만, "왜 하필 Chunk 단위로 커밋하는가"와 "그 경계가 실패 시 실제로 어떻게 동작하는가"를 코드와 함께 보여주는 글은 드뭅니다. 이 글은 Chunk 지향 처리가 행(row) 단위 커밋과 Job 전체 단위 커밋 사이의 절충안으로 설계된 이유를 메모리 상한과 재시작 안전성 관점에서 설명하고, 실제로 돌아가는 `ItemReader`/`ItemProcessor`/`ItemWriter` 예제로 커밋 경계를 시연합니다. 이어서 Chunk 중간에 쓰기(Write) 예외가 발생했을 때 정확히 무엇이 롤백되고 무엇이 이미 영구히 커밋된 상태로 남는지, 그리고 Job을 재시작하면 어느 지점부터 재개되는지를 Spring Batch 공식 레퍼런스 문서에 근거해 구체적으로 다룹니다.

## 차별화 포인트

<!-- 내부 전용 섹션 -->

Job/Step/Reader/Processor/Writer의 정의만 나열하는 "개념 설명형" 글과 달리, 이 글은 두 가지를 실제로 파고듭니다. 첫째, Chunk 지향 처리가 왜 "행 단위 트랜잭션"도 "Job 전체 트랜잭션"도 아닌 절충안인지를 메모리 사용량과 트랜잭션 오버헤드의 트레이드오프로 설명합니다. 둘째, 실무에서 가장 자주 오해하는 지점인 "Chunk 중간 실패"를 실제 예제 데이터(주문 CSV 300건, commit-interval 100)로 재현하여, ItemWriter에서 예외가 나면 이미 Processor를 통과한 나머지 아이템까지 포함해 해당 Chunk 전체가 롤백된다는 사실과, JobRepository가 어떤 상태를 저장하며 재시작 시 정확히 몇 번째 행부터 재개되는지를 Spring Batch 공식 레퍼런스 문서(commit-interval, controlling-rollback, restart 페이지)와 대조해 구체적으로 보여줍니다. "재시작 가능하다"는 주장만 반복하는 대신, ExecutionContext에 저장되는 값과 재시작 후 실제 읽기 시작 위치까지 명시한다는 점이 다른 글과의 핵심 차이입니다.

## 본문

### 1. 왜 "행 단위"도 "Job 전체 단위"도 아닌 Chunk 단위인가

대용량 데이터를 배치로 처리할 때 가장 단순한 두 가지 접근은 다음과 같습니다.

- **행(row) 단위 커밋**: 한 건을 처리할 때마다 트랜잭션을 열고 닫습니다. 안전하지만 수백만 건을 처리할 때 트랜잭션 오버헤드(커넥션 획득, 커밋 I/O, 로그 플러시)가 건수만큼 반복되어 처리량이 급격히 떨어집니다.
- **Job 전체 단위 커밋**: 전체 데이터를 한 트랜잭션에서 처리합니다. 트랜잭션 오버헤드는 최소화되지만, 수백만 건을 메모리에 올려두거나 DB 트랜잭션 로그(undo/redo)가 무한정 누적되고, 마지막 1건에서 실패하면 이미 처리한 수백만 건이 통째로 롤백됩니다. 또한 장시간 유지되는 트랜잭션은 락 경합과 커넥션 점유 문제를 일으킵니다.

Spring Batch의 Chunk 지향 처리는 이 둘 사이의 절충점입니다. 공식 레퍼런스 문서는 Chunk 지향 처리를 다음과 같이 설명합니다: 데이터를 한 건씩 읽어 "Chunk"를 구성하고, 이 Chunk는 트랜잭션 경계 안에서 한꺼번에 기록됩니다. 읽은 아이템 수가 commit-interval(커밋 간격)에 도달하면 `ItemWriter`가 해당 Chunk 전체를 기록하고, 그 시점에 트랜잭션이 커밋됩니다 (Spring Batch Reference, Chunk-oriented Processing, 확인일: 2026-08-23). 즉 "몇 건마다 커밋할지"를 명시적으로 조절할 수 있게 되어, 메모리 사용량은 Chunk 크기만큼으로 상한이 걸리고, 실패 시 되돌려야 할 작업량도 Chunk 크기만큼으로 제한됩니다.

### 2. Chunk 지향 처리의 구조: Job → Step → Reader/Processor/Writer

Spring Batch에서 `Job`은 하나 이상의 `Step`으로 구성되고, 각 `Step`은 다시 `ItemReader`(입력 한 건 읽기) → `ItemProcessor`(가공/검증, 선택적) → `ItemWriter`(Chunk 단위 일괄 기록)의 반복 사이클로 구성됩니다. `JobRepository`는 이 모든 실행 상태(`JobExecution`, `StepExecution`, 읽기/쓰기/커밋 카운트, `ExecutionContext`)를 메타데이터 테이블(`BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`, `BATCH_JOB_EXECUTION_CONTEXT`, `BATCH_STEP_EXECUTION_CONTEXT` 등)에 영속화합니다(Spring Batch Reference, Meta-Data Schema, 확인일: 2026-08-23). 이 메타데이터가 바로 재시작 시 "어디까지 진행됐는지"를 판단하는 근거가 됩니다.

### 3. 실전 예제: 주문 CSV를 Chunk 단위로 검증하고 적재하기

아래는 300건의 주문 CSV 파일을 `commit-interval = 100`으로 처리하는 실제 구성입니다. 3개의 Chunk(1~100번째, 101~200번째, 201~300번째 행)로 나뉘어 각각 별도의 트랜잭션에서 커밋됩니다.

```java
@Configuration
public class OrderBatchConfig {

    @Bean
    public FlatFileItemReader<OrderRecord> orderItemReader() {
        return new FlatFileItemReaderBuilder<OrderRecord>()
                .name("orderItemReader")
                .resource(new FileSystemResource("input/orders.csv"))
                .delimited()
                .names("orderId", "customerId", "amount")
                .targetType(OrderRecord.class)
                // saveState(기본값 true): 매 Chunk 커밋 시점마다 현재까지 읽은 라인 수를
                // ExecutionContext에 저장한다 -> 재시작 시 이 위치부터 재개된다.
                .saveState(true)
                .build();
    }

    @Bean
    public ItemProcessor<OrderRecord, OrderEntity> orderItemProcessor() {
        return record -> {
            if (record.getAmount() == null || record.getAmount().signum() <= 0) {
                // 검증 실패 아이템 - 이 예외는 Writer가 아니라 Processor에서 발생하므로
                // fault-tolerant 설정 없이는 해당 Chunk 전체 롤백을 유발한다.
                throw new IllegalArgumentException("잘못된 주문 금액: " + record.getOrderId());
            }
            OrderEntity entity = new OrderEntity();
            entity.setOrderId(record.getOrderId());
            entity.setCustomerId(record.getCustomerId());
            entity.setAmount(record.getAmount());
            entity.setStatus("VALIDATED");
            return entity;
        };
    }

    @Bean
    public JdbcBatchItemWriter<OrderEntity> orderItemWriter(DataSource dataSource) {
        return new JdbcBatchItemWriterBuilder<OrderEntity>()
                .dataSource(dataSource)
                .sql("INSERT INTO orders (order_id, customer_id, amount, status) "
                        + "VALUES (:orderId, :customerId, :amount, :status)")
                .beanMapped()
                .build();
    }

    @Bean
    public Step orderImportStep(JobRepository jobRepository,
                                 PlatformTransactionManager transactionManager,
                                 ItemReader<OrderRecord> orderItemReader,
                                 ItemProcessor<OrderRecord, OrderEntity> orderItemProcessor,
                                 ItemWriter<OrderEntity> orderItemWriter) {
        return new StepBuilder("orderImportStep", jobRepository)
                // chunk(100, ...) = commit-interval 100건. 100건을 읽을 때마다
                // 하나의 트랜잭션으로 묶어 Writer가 일괄 기록한다.
                .<OrderRecord, OrderEntity>chunk(100, transactionManager)
                .reader(orderItemReader)
                .processor(orderItemProcessor)
                .writer(orderItemWriter)
                .build();
    }

    @Bean
    public Job orderImportJob(JobRepository jobRepository, Step orderImportStep) {
        return new JobBuilder("orderImportJob", jobRepository)
                .start(orderImportStep)
                .build();
    }
}
```

이 구성에서 `chunk(100, transactionManager)`가 핵심입니다. 100건을 읽어 Processor로 가공한 뒤, 그 100건 묶음을 하나의 트랜잭션 안에서 `JdbcBatchItemWriter`가 일괄 INSERT하고 커밋합니다. 개별 행마다 커넥션을 얻고 커밋하는 대신 100건 단위로 묶이므로 트랜잭션 오버헤드가 1/100로 줄고, 동시에 300만 건이 아니라 100건만 메모리에 유지하면 되므로 메모리 사용량도 상한선이 생깁니다.

### 4. Chunk 중간 실패 vs Job 전체 실패 — 실제 커밋 경계와 재시작 동작

여기서부터가 이 아키텍처를 제대로 이해했는지 갈리는 지점입니다. 위 예제에서 201번째 행(세 번째 Chunk, 201~300번째 구간)의 주문 금액이 잘못되어 Processor에서 예외가 발생했다고 가정합니다.

**커밋 경계**: 첫 번째 Chunk(1~100행)와 두 번째 Chunk(101~200행)는 이미 각각 별도의 트랜잭션으로 커밋을 마쳤습니다. 이 200건은 세 번째 Chunk의 실패와 무관하게 DB에 영구히 남습니다. 반면 세 번째 Chunk(201~300행)는 통째로 롤백됩니다 — 설령 202번째, 203번째 행이 Processor 검증을 무사히 통과했더라도, 같은 트랜잭션에 묶여 있었기 때문에 함께 롤백됩니다. Spring Batch 공식 문서는 이를 명확히 규정합니다: 기본적으로 재시도(retry)나 건너뛰기(skip) 설정과 무관하게 `ItemWriter`에서 발생한 예외는 해당 Step이 관리하는 트랜잭션 전체를 롤백시킵니다(Spring Batch Reference 5.2, Controlling Rollback, 확인일: 2026-08-23). 이 예제에서는 예외가 Processor에서 났지만, 기본 동작에서 Processor의 예외 역시 Chunk 처리 루프 안에서 발생하는 한 동일하게 해당 Chunk의 트랜잭션을 롤백시킵니다 — "일부는 이미 처리됐으니 살아있을 것"이라는 가정이 실무에서 가장 흔한 오판입니다.

**JobRepository 상태**: Job이 실패하면 `BATCH_STEP_EXECUTION`에는 `orderImportStep`의 상태가 `FAILED`로, 읽기/쓰기/커밋 카운트는 정확히 200(성공적으로 커밋된 두 Chunk 분량)으로 기록됩니다. `FlatFileItemReader`는 매 Chunk 커밋 시점마다 현재까지 읽은 라인 수를 `ExecutionContext`에 저장하므로(`AbstractItemCountingItemStreamItemReader` 기반 구현체의 표준 동작), `BATCH_STEP_EXECUTION_CONTEXT`에는 "200번째 행까지 읽었다"는 상태가 남습니다(Spring Batch Reference / API 문서, 확인일: 2026-08-23).

**재시작 시 실제 동작**: 동일한 Job 파라미터로 Job을 재실행하면, 같은 `JobInstance`에 대해 새 `JobExecution`이 생성됩니다. 이전 실행에서 `COMPLETED` 상태였던 Step은 기본적으로 건너뛰고, `COMPLETED`가 아니었던 Step만 다시 실행됩니다(Spring Batch Reference, Configuring a Step for Restart, 확인일: 2026-08-23). `orderImportStep`은 `FAILED` 상태였으므로 다시 실행되는데, 이때 `FlatFileItemReader`는 처음부터(1번째 행) 읽는 것이 아니라 `ExecutionContext`에 저장된 상태를 복원해 201번째 행부터 다시 읽기 시작합니다. 즉 재시작은 "마지막으로 읽은 행"이 아니라 "마지막으로 커밋된 Chunk의 경계"부터 재개됩니다 — 202~300행 중 일부가 이전 실행에서 Processor를 통과했었다는 사실은 재시작 동작에 전혀 영향을 주지 않습니다. 실무에서는 이 특성 때문에 Writer가 외부 API 호출처럼 부작용이 있는 연산을 수행한다면, 같은 Chunk가 재시작 후 다시 실행될 때 멱등성(idempotency)을 보장하지 않으면 중복 처리가 발생할 수 있다는 점을 설계 단계에서 고려해야 합니다.

### 5. 개별 아이템 실패를 Chunk 롤백 없이 넘기려면: Fault Tolerant

모든 검증 실패가 Chunk 전체를 롤백시키길 원하지 않는다면, `.faultTolerant().skip(IllegalArgumentException.class).skipLimit(10)`처럼 skip/retry 정책을 추가할 수 있습니다. 이 경우 예외가 발생하면 Spring Batch는 해당 Chunk를 롤백한 뒤, 각 아이템을 1건씩 독립된 트랜잭션(mini-chunk)으로 재처리하여 실패한 아이템만 정확히 식별해 건너뛰고 나머지는 정상 커밋합니다(Spring Batch Reference, Configuring Retry Logic / Skip Logic, 확인일: 2026-08-23). 이것이 바로 앞서 설명한 "Chunk 전체 롤백" 기본 동작의 성능 비용(1건 실패로 99건 재처리)을 완화하기 위한 장치입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Chunk 지향 처리는 데이터를 한 건씩 읽어 Chunk를 구성하고, 읽은 아이템 수가 commit-interval에 도달하면 Writer가 해당 Chunk를 기록한 뒤 트랜잭션이 커밋된다 | verified | Spring Batch Reference, "Chunk-oriented Processing", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html (확인일: 2026-08-23) |
| 기본적으로 retry/skip 설정과 무관하게 ItemWriter에서 발생한 예외는 Step이 관리하는 트랜잭션 전체를 롤백시킨다 | verified | Spring Batch Reference 5.2, "Controlling Rollback", https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/controlling-rollback.html (확인일: 2026-08-23) |
| 재시작 시 이전 실행에서 COMPLETED 상태였던 Step은 기본적으로 건너뛰며, COMPLETED가 아니었던 Step만 다시 실행된다 | verified | Spring Batch Reference, "Configuring a Step for Restart", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/restart.html (확인일: 2026-08-23) |
| JobRepository는 JobExecution/StepExecution 등을 BATCH_JOB_EXECUTION, BATCH_STEP_EXECUTION 같은 메타데이터 테이블에 저장한다 | verified | Spring Batch Reference, "Meta-Data Schema", https://docs.spring.io/spring-batch/reference/schema-appendix.html (확인일: 2026-08-23) |
| FlatFileItemReader와 같이 AbstractItemCountingItemStreamItemReader를 상속한 리더는 ExecutionContext에 아이템 카운트(읽기 위치)를 저장해 재시작을 지원한다 | verified | Spring Batch 5.2.x API 문서, AbstractItemCountingItemStreamItemReader, https://docs.spring.io/spring-batch/docs/current/api/org/springframework/batch/item/support/AbstractItemCountingItemStreamItemReader.html (확인일: 2026-08-23) |
| fault-tolerant 설정 시 skip 대상 예외가 발생하면 Chunk를 롤백한 뒤 아이템을 1건씩 독립 트랜잭션으로 재처리해 실패 아이템만 식별하고 건너뛴다 | verified | Spring Batch Reference, "Configuring Retry Logic", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/retry-logic.html (확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자의 해석을 담고 있습니다.

Chunk 지향 처리를 처음 접하면 "Job 전체를 트랜잭션으로 감싸면 더 안전하지 않은가"라는 의문이 자연스럽게 듭니다. 하지만 실제로 대용량 배치를 운영해 보면 그 반대라는 걸 체감하게 됩니다. 장시간 열려 있는 대형 트랜잭션은 DB의 undo 세그먼트나 트랜잭션 로그를 계속 누적시키고, 커넥션 풀을 오래 점유하며, 다른 세션과의 락 경합 가능성도 키웁니다. Chunk 단위로 쪼개는 설계는 "실패를 완전히 막는" 접근이 아니라 "실패의 영향 범위를 commit-interval만큼으로 국소화"하는 접근이라고 보는 게 더 정확한 이해라고 생각합니다. 개인적으로 가장 위험하다고 보는 지점은 이 글에서 다룬 "Chunk 중간 실패 시 이미 처리된 것처럼 보이는 아이템도 함께 롤백된다"는 사실을 놓치고 Writer에 외부 시스템 호출(이메일 발송, 결제 API 호출 등)을 그대로 넣는 경우입니다. 재시작 시 같은 Chunk가 다시 실행되면 그 외부 호출도 다시 실행되므로, Writer의 부작용에 멱등성을 설계하지 않으면 재시작이 오히려 중복 부작용을 만드는 역설이 발생합니다. commit-interval 값 자체도 정답이 없고, 값이 작으면 트랜잭션 오버헤드가 커지고 값이 크면 실패 시 되돌릴 작업량과 재시작 시 재처리해야 할 부작용의 범위가 커지는 트레이드오프이므로, 처리 대상 데이터의 특성과 Writer의 부작용 여부를 함께 고려해 결정해야 한다고 봅니다.

## 한계와 반론

이 글의 예제는 단일 Step, 단일 스레드 Chunk 처리에 한정되어 있습니다. 실무에서는 `Partitioning`이나 `Remote Chunking`으로 여러 스레드/프로세스가 Chunk를 병렬 처리하는 경우가 많은데, 이 경우 각 파티션(Worker)이 독립적인 StepExecution을 가지므로 재시작 동작이 이 글에서 설명한 단일 Step 시나리오보다 복잡해집니다. 또한 이 글은 JDBC 기반 `JobRepository`(관계형 DB)를 전제로 설명했으며, 인메모리 `JobRepository`를 사용하면 애플리케이션 재시작 시 메타데이터 자체가 사라져 재시작 기능이 무의미해진다는 점도 별도로 고려해야 합니다. 아울러 skip/retry의 mini-chunk 재처리 방식은 예외가 자주 발생하는 데이터셋에서는 성능 저하를 유발할 수 있으므로, skipLimit을 지나치게 높게 설정하는 것은 오히려 전체 처리 시간을 늘릴 위험이 있습니다. 이 글에서 제시한 commit-interval 100이라는 값도 특정 예제를 위한 것일 뿐 모든 상황에 적용 가능한 권장값이 아니며, 실제 운영에서는 트랜잭션 로그 증가량과 DB 락 경합을 모니터링하며 조정해야 합니다.

## 참고문헌

1. Spring Batch Reference Documentation, "Chunk-oriented Processing", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html (확인일: 2026-08-23)
2. Spring Batch Reference Documentation (5.2), "Controlling Rollback", https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/controlling-rollback.html (확인일: 2026-08-23)
3. Spring Batch Reference Documentation, "Configuring a Step for Restart", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/restart.html (확인일: 2026-08-23)
4. Spring Batch Reference Documentation, "Meta-Data Schema", https://docs.spring.io/spring-batch/reference/schema-appendix.html (확인일: 2026-08-23)
5. Spring Batch API Documentation, "AbstractItemCountingItemStreamItemReader", https://docs.spring.io/spring-batch/docs/current/api/org/springframework/batch/item/support/AbstractItemCountingItemStreamItemReader.html (확인일: 2026-08-23)
6. Spring Batch Reference Documentation, "Configuring Retry Logic", https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/retry-logic.html (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 필자의 견해를 담고 있습니다.

Chunk 지향 아키텍처는 Spring Batch만의 독창적 발명이라기보다, 대용량 데이터 처리 전반에서 반복적으로 등장하는 "메모리 상한 + 실패 범위 국소화 + 재시작 가능성"이라는 세 가지 요구를 트랜잭션 경계 설계 하나로 동시에 만족시키는 절충안이라고 정리할 수 있습니다. 이 절충은 공짜가 아닙니다. commit-interval을 선택하는 순간 "실패 시 되돌릴 작업량"과 "트랜잭션 오버헤드"를 맞바꾸는 트레이드오프에 들어서게 되고, Writer에 부작용이 있는 로직을 넣는 순간 재시작이 그 부작용을 중복 실행시킬 위험을 함께 떠안게 됩니다. 이 글에서 실제 예제로 보였듯, "재시작 가능하다"는 문장 하나로는 이 아키텍처를 안전하게 쓰기에 부족합니다 — 정확히 어느 지점부터 재개되는지, 그 지점 이전에 어떤 부작용이 이미 실행됐는지를 설계 시점에 검토해야 실제 운영에서 재시작 기능이 의도대로 동작합니다. 개인적으로는 Chunk 크기와 skip/retry 정책을 데이터 특성에 맞게 조율하는 작업이 Spring Batch를 다루는 실무에서 가장 과소평가된 튜닝 포인트라고 생각하며, 단순히 프레임워크 문서의 기본값을 그대로 쓰기보다 커밋 경계가 실패 시나리오에서 어떻게 움직이는지를 직접 재현해 확인하는 습관이 필요하다고 봅니다.

## 꼬리질문

- Partitioning(파티셔닝)이나 Remote Chunking으로 병렬화된 Step에서는 각 Worker의 실패가 전체 Job의 재시작 지점에 어떤 영향을 주는가?
- Writer가 외부 API 호출처럼 멱등하지 않은 부작용을 포함할 때, Chunk 재처리로 인한 중복 실행을 막기 위한 표준적인 설계 패턴(예: 멱등키, 처리 완료 마킹 테이블)은 무엇인가?
- commit-interval 값을 데이터 볼륨/DB 트랜잭션 로그 증가량에 따라 동적으로 조정하는 것이 실무에서 유효한 전략인가, 아니면 고정값을 쓰고 파티셔닝으로 확장하는 편이 더 안정적인가?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)
- [MySQL InnoDB B+Tree 인덱스 내부 구조 및 커버링 인덱스(Covering Index) 성능 튜닝 레시피](https://beji-tech.blogspot.com/2026/08/mysql-innodb-btree-covering-index.html)