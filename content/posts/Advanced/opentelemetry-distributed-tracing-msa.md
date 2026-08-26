---
author: ''
createdAt: '2026-08-26T00:25:40.357459Z'
factCheckScore: 0
id: '3528564591114885492'
notionPageId: null
publishedAt: '2026-08-25T22:44:51-07:00'
slug: opentelemetry-distributed-tracing-msa
status: published
tags:
- Advanced
- MSA
- Observability
- OpenTelemetry
title: '분산 트레이싱과 OpenTelemetry: MSA 비동기 메시징 경계에서 트레이스 컨텍스트가 끊기는 지점과 샘플링 전략'
updatedAt: '2026-08-26T00:25:40.357459Z'
url: https://beji-tech.blogspot.com/2026/08/opentelemetry-msa.html
---

# 분산 트레이싱과 OpenTelemetry: MSA 비동기 메시징 경계에서 트레이스 컨텍스트가 끊기는 지점과 샘플링 전략

## 요약

마이크로서비스가 10개, 20개로 늘어나면 "이 요청이 어느 서비스에서 얼마나 걸렸는지"는 더 이상 로그 grep으로 답할 수 있는 질문이 아닙니다. 분산 트레이싱은 하나의 요청이 여러 서비스를 거치는 전체 경로를 Trace ID로 묶어 재구성하는 관측 기법이며, OpenTelemetry는 이를 벤더 중립적으로 구현하기 위한 CNCF 표준 계측 프레임워크입니다. 본 아티클은 W3C Trace Context 표준(`traceparent` 헤더)의 바이트 단위 구조를 실제로 뜯어보고, HTTP에서는 잘 작동하던 컨텍스트 전파가 Kafka 같은 비동기 메시징 경계를 넘는 순간 왜 끊어지는지를 Java 코드로 직접 보여줍니다. 또한 head 기반 샘플링과 tail 기반 샘플링 중 어떤 것이 실제 장애 상황에서 "그 트레이스"를 놓치게 만드는지, 스팬 카디널리티가 왜 관측 비용을 폭증시키는지를 정리합니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어. 이 글이 같은 주제 상위 검색결과 대비 무엇을 더하는지 최소 1가지를 구체적으로
쓸 것 (wiki/Blog_Writing_Rules.md 14번 수칙) , 예: 직접 돌려본 벤치마크 수치, 실제 겪은 프로덕션
이슈/장애, 흔치 않은 조합/트레이드오프, 다른 곳에서 보기 힘든 비교표, 실제 실행해보고 확인한 예상 밖
동작. "정의 + 교과서적 예시"만 있는 포화 101 주제(GoF 패턴류 등)는 이 각도 없이는 신규 작성을 지양한다.
-->

분산 트레이싱을 소개하는 대다수 글은 "Trace/Span 개념 + Jaeger UI 스크린샷"에서 끝나고, HTTP 요청 체인만 예시로 다룹니다. 이 글은 그보다 실무에서 실제로 트레이스가 깨지는 지점, 즉 **HTTP 자동계측이 커버하지 못하는 Kafka 프로듀서/컨슈머 경계**에서 `TextMapPropagator`로 헤더를 수동 주입·추출하지 않으면 컨슈머 쪽 스팬이 부모 없는 고아 트레이스로 남는 실패 시나리오를 Producer/Consumer 양쪽 코드로 재현합니다. 여기에 더해 "샘플링률을 5%로 설정했더니 정작 장애 당시의 그 요청은 수집되지 않았다"는 head 기반 샘플링의 근본적 한계를 tail 기반 샘플링과 대비해 비교하고, 스팬 이름에 식별자를 그대로 박아 넣었을 때 벌어지는 카디널리티 폭발 비용 문제까지 하나의 흐름으로 엮습니다.

## 본문

<!--
게시 게이트(src/core/publish_gate.json::sectionMinWords) 기준 최소 800단어.
코드펜스(예: ```java ... ```) 또는 이미지 중 최소 1개는 반드시 포함할 것 , 둘 다 없으면
발행 게이트에서 오류로 차단된다(2026-08-22부터 경고 아님).
-->

### 1. 서론: MSA에서 "요청이 어디서 사라졌는지" 모르는 문제

모놀리식 애플리케이션에서는 스택 트레이스 하나로 요청의 전체 경로를 볼 수 있습니다. 하지만 주문 서비스 → 결제 서비스 → 재고 서비스 → 알림 서비스로 요청이 물리적으로 분리된 프로세스를 넘나드는 MSA 환경에서는, 각 서비스의 로그가 서로 다른 저장소에 흩어져 있고 상관관계를 지어줄 공통 키가 없으면 "결제는 성공했는데 왜 알림이 안 갔는지"조차 재구성할 수 없습니다. 이 글의 시리즈 선행 글인 [Saga 패턴 아티클](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)과 [비차단 재시도/DLQ 아티클](https://beji-tech.blogspot.com/2026/08/msa-non-blocking-retry-dlq.html)에서 다룬 것처럼, MSA는 트랜잭션과 장애 복구를 비동기·이벤트 기반으로 설계할수록 정합성은 확보하지만 "지금 무슨 일이 벌어지고 있는지"를 파악하기는 더 어려워집니다. 분산 트레이싱은 바로 이 관측 공백을 메우기 위한 장치이며, OpenTelemetry는 그 계측 방식을 벤더에 종속되지 않게 표준화한 CNCF 프로젝트입니다.

### 2. OpenTelemetry의 데이터 모델: Trace, Span, SpanContext

OpenTelemetry 공식 문서는 트레이스를 "요청이 애플리케이션을 통과하는 경로"로, 스팬을 그 경로 위의 개별 작업 단위로 정의합니다. 모든 스팬은 불변(immutable) 객체인 `SpanContext`를 가지며, 여기에는 트레이스 전체를 식별하는 Trace ID, 개별 스팬을 식별하는 Span ID, 그리고 샘플링 여부 등을 담는 Trace Flags/Trace State가 들어 있습니다. 자식 스팬은 부모 스팬의 Span ID를 참조함으로써 전체 트레이스가 트리 구조로 재구성됩니다. 즉 트레이싱 시스템이 하는 일의 본질은 "이 Span ID의 부모가 저 Span ID다"라는 링크를 서비스 경계를 넘어서도 끊기지 않게 전달하는 것이고, 이 전달 메커니즘이 바로 컨텍스트 전파(Context Propagation)입니다.

### 3. W3C Trace Context: traceparent 헤더를 바이트 단위로 뜯어보기

컨텍스트 전파가 벤더마다 제각각이면 서로 다른 트레이싱 벤더를 쓰는 팀이 협업할 때마다 계측을 다시 해야 합니다. 이 문제를 해결한 것이 W3C의 Trace Context 표준으로, HTTP 헤더 `traceparent`의 정확한 형식을 다음과 같이 고정합니다.

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

이 문자열은 하이픈으로 구분된 4개 필드입니다.

- `00` , **version**: 16진수 2자(1바이트). 현재는 `00`만 유효합니다.
- `4bf92f3577b34da6a3ce929d0e0e4736` , **trace-id**: 16진수 32자(16바이트). 트레이스 전체를 식별하는 전역 고유 값입니다.
- `00f067aa0ba902b7` , **parent-id**: 16진수 16자(8바이트). 이 요청을 보낸 쪽의 Span ID이며, 수신 서비스는 이 값을 부모로 삼아 자신의 새 스팬을 생성합니다.
- `01` , **trace-flags**: 16진수 2자(1바이트) 비트 필드. 최하위 비트가 `1`이면 sampled(수집 대상), `0`이면 not-sampled를 뜻합니다.

여기에 짝을 이루는 `tracestate` 헤더는 벤더별 부가 정보(최대 32개 키-값 쌍)를 실어 나르는 용도로, 서로 다른 트레이싱 벤더가 공존해도 각자의 메타데이터를 잃지 않게 해줍니다. OpenTelemetry SDK는 HTTP 클라이언트/서버 계측에서 이 두 헤더를 자동으로 주입·추출하므로, `RestTemplate`이나 `WebClient` 같은 동기 HTTP 호출 체인에서는 개발자가 별도 코드를 작성하지 않아도 트레이스가 자연스럽게 이어집니다.

### 4. 진짜 문제는 여기서 시작된다: Kafka 경계에서 컨텍스트가 끊기는 이유

HTTP는 "요청-응답"이라는 명확한 왕복 구조가 있고, OpenTelemetry의 자동계측 에이전트가 이 구조에 훅을 걸어 헤더를 자동으로 처리합니다. 문제는 Kafka처럼 프로듀서가 메시지를 던지고 컨슈머가 나중에, 심지어 전혀 다른 스레드/파드에서 그 메시지를 소비하는 구조입니다. 이때는 HTTP 헤더에 해당하는 것이 Kafka 레코드 헤더(`ProducerRecord.headers()`)이고, 자동계측이 이를 지원하더라도 커스텀 직렬화 계층을 두거나, 배치 리스너를 쓰거나, 계측 라이브러리 버전이 안 맞으면 자동 훅이 걸리지 않는 경우가 실무에서 드물지 않게 발생합니다. 결과적으로 컨슈머 쪽에서 새로 시작된 스팬은 어떤 트레이스에도 속하지 않는 "고아 스팬"이 되고, 트레이싱 UI에서 주문 생성 트레이스를 열어봐도 결제 완료 이후의 흐름이 통째로 잘려 보이지 않습니다.

이걸 명시적으로 막으려면 OpenTelemetry의 `TextMapPropagator` API로 프로듀서 쪽에서 현재 컨텍스트를 헤더에 주입(inject)하고, 컨슈머 쪽에서 그 헤더를 읽어 컨텍스트를 추출(extract)한 뒤 그것을 부모로 새 스팬을 시작해야 합니다. Java/Spring Kafka 기준으로 프로듀서 측 코드는 다음과 같습니다.

```java
// Producer 측: 현재 스팬 컨텍스트를 Kafka 레코드 헤더에 W3C traceparent로 주입
private static final TextMapSetter<ProducerRecord<?, ?>> SETTER =
        (record, key, value) -> record.headers()
                .add(key, value.getBytes(StandardCharsets.UTF_8));

public void publishOrderEvent(String topic, String orderId, OrderEvent event) {
    ProducerRecord<String, OrderEvent> record = new ProducerRecord<>(topic, orderId, event);

    Span span = tracer.spanBuilder(topic + " send")
            .setSpanKind(SpanKind.PRODUCER)
            .setAttribute("messaging.system", "kafka")
            .setAttribute("messaging.destination.name", topic)
            .startSpan();

    try (Scope scope = span.makeCurrent()) {
        openTelemetry.getPropagators().getTextMapPropagator()
                .inject(Context.current(), record, SETTER);
        kafkaProducer.send(record);
    } catch (Exception e) {
        span.recordException(e);
        span.setStatus(StatusCode.ERROR, e.getMessage());
        throw e;
    } finally {
        span.end();
    }
}
```

컨슈머 측은 헤더에서 컨텍스트를 다시 꺼내 그것을 부모로 지정해야만 프로듀서 스팬과 연결됩니다.

```java
// Consumer 측: Kafka 레코드 헤더에서 컨텍스트를 추출해 부모 스팬으로 지정
private static final TextMapGetter<ConsumerRecord<?, ?>> GETTER = new TextMapGetter<>() {
    @Override
    public Iterable<String> keys(ConsumerRecord<?, ?> record) {
        return StreamSupport.stream(record.headers().spliterator(), false)
                .map(Header::key)
                .collect(Collectors.toList());
    }

    @Override
    public String get(ConsumerRecord<?, ?> record, String key) {
        Header header = record.headers().lastHeader(key);
        return header == null ? null : new String(header.value(), StandardCharsets.UTF_8);
    }
};

@KafkaListener(topics = "order-events")
public void onOrderEvent(ConsumerRecord<String, OrderEvent> record) {
    Context extracted = openTelemetry.getPropagators().getTextMapPropagator()
            .extract(Context.current(), record, GETTER);

    Span span = tracer.spanBuilder(record.topic() + " process")
            .setParent(extracted)
            .setSpanKind(SpanKind.CONSUMER)
            .startSpan();

    try (Scope scope = span.makeCurrent()) {
        orderEventHandler.handle(record.value());
    } finally {
        span.end();
    }
}
```

Spring for Apache Kafka는 3.0부터 이 주입/추출 배관 작업을 `observationEnabled=true` 설정 하나로 대체해주는 Micrometer Observation 지원을 제공하지만(`KafkaTemplate`과 리스너 컨테이너 양쪽에 설정 필요), 배치 리스너는 기본적으로 옵저베이션을 생성하지 않는다는 예외가 있어 `recordObservationsInBatch=true`를 별도로 켜지 않으면 배치 처리 구간에서만 트레이스가 다시 끊깁니다. 자동계측을 켰다고 안심하지 말고, 배치 리스너·커스텀 디시리얼라이저·수동 커밋 로직처럼 표준 경로를 벗어나는 구간마다 실제로 트레이스가 이어지는지 확인하는 것이 실무에서 훨씬 중요합니다.

### 5. 샘플링 전략: Head-based vs Tail-based, 그리고 장애 당시 "그 트레이스"를 놓치는 문제

모든 요청의 스팬을 100% 수집하면 관측 비용이 트래픽에 비례해 폭증하므로 샘플링이 필수입니다. OpenTelemetry는 샘플링 시점을 기준으로 두 전략을 구분합니다.

| 구분 | Head 기반 샘플링 | Tail 기반 샘플링 |
|---|---|---|
| 결정 시점 | 트레이스 시작 시점(대개 첫 스팬 생성 시) | 트레이스에 속한 스팬 대부분/전체가 도착한 뒤 |
| 판단 근거 | trace-id 해시 등 트레이스 내용과 무관한 값 | 에러 포함 여부, 전체 지연시간 등 실제 트레이스 내용 |
| 구현 난이도 | 낮음(각 서비스가 독립적으로 결정) | 높음(수집기가 스팬을 임시 버퍼링하는 상태 저장 구조 필요) |
| 장애 시 리스크 | 5% 샘플링이면 정작 에러 난 그 요청이 95% 확률로 누락됨 | 트래픽 급증 시 버퍼 한계로 샘플러가 다운그레이드되며 진단에 필요한 데이터가 빠질 수 있음 |

실무에서 자주 벌어지는 시나리오는 이렇습니다. 평상시 스토리지 비용을 아끼려고 head 기반 샘플링을 5%로 설정해두었는데, 특정 배포 이후 결제 서비스에서 간헐적 오류가 발생했다는 신고가 들어옵니다. 문제는 head 기반 샘플링이 트레이스 내용을 보기 전에 이미 수집 여부를 결정해버리므로, 하필 에러가 난 그 요청이 샘플링 대상에서 빠졌을 확률이 95%라는 점입니다. 로그에는 에러 스택이 남아 있어도 그 요청이 결제 서비스에 도달하기까지 어느 구간에서 지연이 누적됐는지는 트레이스로 재구성할 수 없습니다. 반대로 tail 기반 샘플링(예: OpenTelemetry Collector의 tail sampling processor)은 "에러를 포함한 트레이스는 무조건 100% 보관"하는 규칙을 걸 수 있어 이런 상황에 유리하지만, 모든 스팬을 일단 수집기 메모리에 버퍼링했다가 트레이스가 끝나야 최종 판단을 내리므로 수집기 자체의 메모리·디스크 용량 설계와 트레이스 타임아웃 튜닝이라는 별도의 운영 부담이 따라옵니다.

### 6. 스팬 카디널리티 폭발: 이름 하나 잘못 지어서 발생하는 비용 문제

또 하나 자주 간과되는 실패 패턴은 스팬 이름이나 속성에 고카디널리티 값을 그대로 박아 넣는 것입니다. OpenTelemetry 트레이스 API 명세는 `get_user`처럼 일반화된 이름은 적절하지만, 사용자 ID를 그대로 이어붙인 `get_user/314159` 같은 이름은 카디널리티가 지나치게 높아 부적절하다고 명시적으로 경고합니다. 스팬 이름이나 속성값의 조합이 사실상 무한에 가까운 고유값을 갖게 되면, 트레이싱 백엔드가 이를 인덱싱·집계하는 비용이 기하급수적으로 늘어나고, 저장 비용은 물론 대시보드 조회 속도까지 함께 나빠집니다. 올바른 접근은 스팬 이름은 `get_user`처럼 낮은 카디널리티를 유지하고, 사용자 ID나 주문 번호 같은 가변 값은 `span.setAttribute("user.id", userId)`처럼 속성으로 분리하는 것입니다. 이렇게 하면 백엔드는 스팬 이름 기준으로는 낮은 카디널리티의 집계·알람을 걸 수 있으면서도, 특정 요청을 진단할 때는 속성값으로 정확히 필터링할 수 있습니다.

### 7. 결론

분산 트레이싱을 도입한다는 것은 단순히 OpenTelemetry SDK를 의존성에 추가하는 문제가 아닙니다. HTTP 자동계측이 커버하지 못하는 비동기 메시징 경계마다 컨텍스트 전파가 실제로 이어지는지 직접 검증해야 하고, 샘플링 전략은 평상시 비용과 장애 시 진단 가능성 사이의 트레이드오프임을 이해한 상태에서 선택해야 하며, 스팬 설계 단계에서부터 카디널리티를 의식하지 않으면 트레이싱 도입 자체가 새로운 비용 폭탄이 될 수 있습니다. 이 세 가지 , 전파 경계, 샘플링, 카디널리티 , 를 놓치지 않는 것이 "대시보드에 트레이스가 보이긴 하는데 정작 필요할 때는 못 쓰는" 흔한 실패를 피하는 실질적인 체크리스트입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| W3C Trace Context의 traceparent 헤더는 `version-trace_id-parent_id-trace_flags` 형식이며 각각 16진수 2자(1바이트)-32자(16바이트)-16자(8바이트)-2자(1바이트)로 구성된다 | verified | W3C Trace Context 명세(https://www.w3.org/TR/trace-context/) §3.2 Traceparent Header 원문 확인, 명세 예시값 `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`과 필드 길이 일치 |
| OpenTelemetry의 SpanContext는 Trace ID, Span ID, TraceFlags, TraceState 네 요소로 구성되며, 자식 스팬이 부모 Span ID를 참조해 트리 구조를 형성한다 | verified | opentelemetry.io 공식 개념 문서(https://opentelemetry.io/docs/concepts/signals/traces/) 원문 확인 |
| Head 기반 샘플링은 트레이스 전체 내용을 보기 전에 결정을 내리므로 에러가 포함된 특정 트레이스만 골라 100% 수집하는 것이 불가능하다 | verified | opentelemetry.io 공식 샘플링 문서(https://opentelemetry.io/docs/concepts/sampling/) 원문 확인 |
| Tail 기반 샘플링은 트레이스에 속한 스팬 대부분/전체가 도착한 뒤 판단하므로 수집기 쪽에 상태 저장(stateful) 버퍼링 인프라가 필요하다 | verified | opentelemetry.io 공식 샘플링 문서(https://opentelemetry.io/docs/concepts/sampling/) 원문 확인 |
| OpenTelemetry는 스팬 이름에 `get_user/314159`처럼 사용자 ID를 그대로 붙이는 것을 고카디널리티 문제로 명시적으로 경고하며, `get_user` 같은 저카디널리티 이름을 권장한다 | verified | OpenTelemetry Trace API 명세(https://opentelemetry.io/docs/specs/otel/trace/api/) 원문의 스팬 네이밍 카디널리티 경고 문구("get_user"/"get_user/314159" 예시) 확인 |
| Spring for Apache Kafka는 3.0부터 KafkaTemplate과 리스너 컨테이너에 Micrometer Observation을 지원하며, `observationEnabled=true`로 설정하면 Micrometer Tracing을 거쳐 OpenTelemetry로 연결되고, 배치 리스너는 `recordObservationsInBatch=true`를 켜지 않으면 기본적으로 옵저베이션이 생성되지 않는다 | verified | Spring for Apache Kafka 공식 레퍼런스 "Monitoring" 문서(https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html) 원문 확인 |

## 작성자의 견해

<!-- 최소 100단어. 게이트는 이 섹션에 의견/해석임을 밝히는 '>' 인용구 줄이 있는지만 구조적으로
확인한다(문구 자체는 "의견/견해/해석/사견" 중 한 단어만 포함하면 됨) , 아래 문장은 예시일 뿐, 47개
발행 글이 전부 토씨 하나 같은 문장을 반복하는 걸 피하기 위해 매번 자기 말로 다르게 쓸 것
(wiki/Blog_Writing_Rules.md 14/15번 수칙). 빈 '>' 뒤에 평문으로 쓰면 실패한다. -->

> 이 섹션은 공식 문서 검증을 넘어선 작성자 개인의 실무 해석이므로, 사실 서술이 아닌 견해로 읽어주시기 바랍니다.

필자가 여러 팀의 트레이싱 도입을 지켜보며 느낀 가장 흔한 착시는 "자동계측 라이브러리를 추가했으니 이제 모든 요청이 추적된다"는 가정입니다. 실제로는 HTTP 경로에서는 잘 작동하다가 Kafka나 배치 스케줄러, 혹은 리액티브 스트림처럼 실행 컨텍스트가 스레드 경계를 넘는 지점에서 조용히 끊깁니다. 문제는 이게 에러로 드러나지 않는다는 점입니다. 컨슈머 스팬은 여전히 생성되고 대시보드에도 나타나지만, 그저 부모 없는 새 트레이스로 시작될 뿐이라 겉보기엔 정상처럼 보입니다. 그래서 필자는 새 서비스가 트레이싱 파이프라인에 합류할 때마다, 동기 HTTP 구간뿐 아니라 메시지 큐를 넘나드는 구간에서 하나의 Trace ID가 끝까지 유지되는지를 반드시 눈으로 직접 확인하는 절차를 도입 체크리스트에 포함시켜야 한다고 생각합니다. 자동계측은 출발점이지 완성이 아닙니다.

## 한계와 반론

<!-- 최소 80단어. -->

본문에서 제시한 Kafka 헤더 수동 전파 코드는 원리를 보여주기 위한 예시이며, 실무에서는 Spring Kafka의 Micrometer Observation 지원이나 OpenTelemetry Java 자동계측 에이전트(`opentelemetry-javaagent.jar`)를 우선 검토하는 편이 유지보수 관점에서 더 낫습니다. 수동 계측 코드를 서비스마다 직접 작성하면 스팬 이름·속성 규칙이 팀마다 달라져 오히려 관측 데이터의 일관성이 깨질 위험이 있습니다. 또한 tail 기반 샘플링이 head 기반보다 항상 우월한 것은 아닙니다 , 수집기 버퍼링 비용과 운영 복잡도를 감당할 인프라 여력이 없는 초기 단계 팀이라면, 에러 로그 기반 별도 알림과 head 샘플링을 결합하는 쪽이 현실적인 절충안일 수 있습니다. 이 글은 표준 스펙과 실패 시나리오를 설명하는 데 초점을 맞췄을 뿐, 특정 벤더(Jaeger, Tempo, Datadog 등)의 수집·저장 아키텍처 비교나 실제 운영 비용 수치까지는 다루지 않았다는 점도 한계로 밝혀둡니다.

## 참고문헌

<!--
최소 2개. 신뢰도 등급(wiki/Blog_Writing_Rules.md 10번 수칙) 순으로 우선 채택:
Tier1(IF≥10 논문/IEEE·ACM·Nature급 저널/IETF RFC/W3C 표준) > Tier2(공식 벤더·재단
문서: Oracle/Spring/Kubernetes/CNCF/Linux Foundation 등) > Tier3(방문수 높은 기술
블로그, 최후 수단). 각 항목에 확인일을 표기한다 (예: (확인일: 2026-08-17)).
전부 비공식 출처면 발행이 차단된다(2026-08-22부터 오류) , 후보 URL을
`python src/tools/check_reference_domains.py <url1> <url2> ...`로 미리 확인할 것.
-->

1. W3C, "Trace Context Level 1", W3C Recommendation, [https://www.w3.org/TR/trace-context/](https://www.w3.org/TR/trace-context/) (확인일: 2026-08-26)
2. OpenTelemetry, "Traces" (공식 개념 문서), [https://opentelemetry.io/docs/concepts/signals/traces/](https://opentelemetry.io/docs/concepts/signals/traces/) (확인일: 2026-08-26)
3. OpenTelemetry, "Sampling" (공식 문서), [https://opentelemetry.io/docs/concepts/sampling/](https://opentelemetry.io/docs/concepts/sampling/) (확인일: 2026-08-26)
4. OpenTelemetry Specification, "Trace API", [https://opentelemetry.io/docs/specs/otel/trace/api/](https://opentelemetry.io/docs/specs/otel/trace/api/) (확인일: 2026-08-26)
5. Spring for Apache Kafka Reference Documentation, "Monitoring (Micrometer Observation)", [https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html](https://docs.spring.io/spring-kafka/reference/kafka/micrometer.html) (확인일: 2026-08-26)

## 종합적 의견

<!-- 최소 100단어. 이 섹션도 '작성자의 견해'와 마찬가지로 '>' 인용구에 "의견/견해/해석/사견" 중
한 단어를 담아야 게이트를 통과한다 , 아래 문장은 예시일 뿐 매번 자기 말로 다르게 쓸 것. -->

> 아래 내용은 표준 문서를 근거로 한 사실 정리를 넘어, 도입 우선순위에 대한 작성자의 사견을 포함합니다.

분산 트레이싱 도입을 고민하는 팀에게 필자가 제안하는 순서는 이렇습니다. 먼저 동기 HTTP 경로에 자동계측 에이전트를 붙여 빠르게 가시성을 확보하고, 그다음 단계에서 반드시 메시지 큐·배치·스케줄러처럼 비동기 실행 경계를 하나씩 점검하며 트레이스가 끊기지 않는지 확인해야 합니다. 이 순서를 거꾸로 해서 "일단 다 붙였으니 완료"라고 선언하면, 정작 장애가 터졌을 때 신뢰할 수 없는 반쪽짜리 트레이스만 남게 됩니다. 샘플링 정책도 처음부터 완벽을 노릴 필요는 없습니다. 트래픽이 작을 때는 head 기반 100%로 시작해 실제 스토리지 비용 압박을 체감한 뒤 tail 기반이나 에러 우선 샘플링으로 단계적으로 옮겨가는 편이, 처음부터 복잡한 수집기 아키텍처를 설계하느라 도입 자체가 늦어지는 것보다 실용적입니다. 결국 관측성 도구는 완벽한 설계보다 "지금 무엇을 놓치고 있는지 아는 것"에서 가치가 시작된다고 봅니다.

## 꼬리질문

1. OpenTelemetry Collector의 tail sampling processor를 다중 인스턴스로 수평 확장할 때, 같은 트레이스에 속한 스팬들이 서로 다른 Collector 인스턴스로 분산 수신되면 샘플링 판단을 어떻게 일관되게 내릴 수 있을까?
2. Kafka 대신 gRPC 스트리밍이나 리액티브 스트림(Project Reactor)처럼 실행 컨텍스트가 스레드를 넘나드는 다른 비동기 경계에서는 컨텍스트 전파가 어떤 방식으로 다르게 처리되는가?

## 백링크

<!--
관련 글 및 연관 지식 링크. 2026-08-22부터 이 섹션은 라이브 HTML에 실제로 "[link] 관련 글" 블록으로
렌더링된다(과거엔 통째로 삭제되어 내부링크가 라이브에 전혀 노출되지 않았음 , converter.py 버그 수정).
그러므로:
- 이미 발행된 다른 글의 실제 라이브 URL(https://beji-tech.blogspot.com/...)만 넣을 것.
- `../../wiki/...` 같은 저장소 내부 상대경로는 넣지 말 것 , 공개 사이트에서는 존재하지 않는 링크다.
- 게시 게이트가 본문/백링크/종합적 의견을 합쳐 최소 2개의 내부링크를 요구한다(2026-08-22부터
  오류로 차단, 경고 아님) , 주제와 실제로 관련 있는 이미 발행된 글을 연결할 것
  (wiki/Blog_Writing_Rules.md 15번 수칙).
- 후보를 직접 찾지 말고 `python src/tools/suggest_internal_links.py --tags "<이 글의 태그>"
  [--topic "<주제>"]`로 추천받아 바로 붙여넣을 것(content/posts/ frontmatter 기반 자동 추천).

이 템플릿에는 "## 관련 세션" 섹션을 넣지 않는다 , 예전 버전이 실제 wiki 세션 로그 경로를
예시로 남겨뒀다가 그대로 복사되어 4개 글이 라이브에 내부 경로를 노출한 사고가 있었다
(2026-08-23, converter.py가 이 섹션을 걸러내지 않아서 발생). 관련 세션 기록이 필요하면
wiki 쪽 문서에서만 관리하고, 발행되는 글 본문에는 절대 넣지 말 것.
-->

- [Saga 패턴을 활용한 MSA 분산 트랜잭션 제어: Choreography vs Orchestration 아키텍처와 보상 트랜잭션 설계 전략](https://beji-tech.blogspot.com/2026/08/saga-msa-choreography-vs-orchestration.html)
- [이벤트 드리븐 MSA에서 비차단 재시도(Non-blocking Retry)와 DLQ 패턴 설계 전략](https://beji-tech.blogspot.com/2026/08/msa-non-blocking-retry-dlq.html)