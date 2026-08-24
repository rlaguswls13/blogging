---
author: ''
createdAt: '2026-08-22T18:37:08.206967Z'
factCheckScore: 0
id: '9173334814177418194'
notionPageId: null
publishedAt: '2026-08-23T17:10:24-07:00'
slug: spring-cache-abstraction-cacheable-invalidation-strategy
status: published
tags:
- Advanced
- Spring
- Cache
title: Spring Cache Abstraction(@Cacheable) — 캐시 추상화 동작 원리와 실전 무효화 전략
updatedAt: '2026-08-23T00:00:00.000000Z'
url: https://beji-tech.blogspot.com/2026/08/spring-cache-abstractioncacheable.html
---

# Spring Cache Abstraction(@Cacheable) — 캐시 추상화 동작 원리와 실전 무효화 전략

## 요약

Spring의 `@Cacheable`/`@CacheEvict`/`@CachePut`는 편해 보이지만, 실제로는 프록시 기반 AOP 인터셉션 위에서 동작하는 애노테이션입니다. [Spring AOP와 프록시 아키텍처](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)의 `@Transactional`처럼, 자기 호출 시 캐싱이 조용히 무시됩니다. 이 글은 이 프록시 메커니즘을 실제 동작 순서로 짚고, 실무에서 가장 자주 터지는 캐시 무효화 버그 — `key` SpEL 표현식이 `@Cacheable`과 `@CacheEvict`/`@CachePut` 사이에서 어긋나 캐시가 절대 지워지지 않는 사례 — 를 실행 가능한 코드로 재현합니다. 마지막으로 `null` 캐싱과 `unless`/`condition`의 실제 평가 시점 차이도 다룹니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어.
-->

이 글은 "@Cacheable은 메서드 결과를 캐싱한다"는 설명에서 멈추지 않는다. 첫째, 프록시 기반 인터셉션이 `@Transactional`/`@Async`와 같은 계열의 self-invocation 함정을 공유한다는 점을 이미 발행된 Spring AOP/프록시 글과 명시적으로 교차 참조해, 독립된 개념이 아니라 하나의 반복 패턴임을 보여준다. 둘째, "캐시가 안 지워진다"는 실무에서 가장 흔한 버그를 추상적으로 설명하지 않고 `key` SpEL이 `@Cacheable`과 `@CacheEvict` 사이에서 서로 다른 필드를 참조해 캐시가 영원히 stale 상태로 남는 상황을 엔티티 업데이트 예제 코드로 직접 재현한다(실행 시나리오까지 단계별로 서술). 셋째, `unless`/`condition`의 기본 동작으로 인해 `null`이 그대로 캐시에 박제되는, 공식 문서를 실제로 대조하지 않으면 놓치기 쉬운 gotcha를 다룬다.

## 본문

### 1. `@Cacheable`은 무엇을 가로채는가 — 프록시 인터셉션 복습

`@Cacheable`, `@CachePut`, `@CacheEvict`는 그 자체로 마법을 부리는 애노테이션이 아닙니다. Spring이 이 애노테이션이 붙은 빈을 감지하면, 원본 빈을 감싸는 **AOP 프록시**를 생성해 빈 컨테이너에 등록합니다. 기본 advice mode는 `proxy`이며, 공식 레퍼런스는 이를 다음과 같이 명시합니다.

> "The default advice mode for processing caching annotations is `proxy`, which allows for interception of calls through the proxy only." (Spring Framework 7.0.9 Reference)

즉 클라이언트가 스프링 컨테이너에서 꺼낸 빈(사실은 프록시)의 메서드를 호출하면, 프록시가 먼저 요청을 가로채 캐시 스토어를 조회하고, 캐시 미스면 실제 타깃 객체로 위임 호출한 뒤 결과를 캐시에 저장합니다. 이 구조는 [Spring AOP와 프록시 아키텍처](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)에서 다룬 `@Transactional`의 트랜잭션 시작/커밋 인터셉션과 완전히 동일한 골격입니다.

### 2. Self-Invocation — 같은 함정이 캐시에도 그대로 있다

`@Transactional`을 써본 개발자라면 "같은 클래스 안에서 메서드를 직접 호출하면 트랜잭션이 걸리지 않는다"는 함정을 한 번쯤 겪습니다. `@Cacheable`도 동일한 계열의 함정을 공유합니다. 공식 문서는 이렇게 못박습니다.

> "In proxy mode (the default), only external method calls coming in through the proxy are intercepted. This means that self-invocation ... does not lead to actual caching at runtime even if the invoked method is marked with `@Cacheable`. ... Local calls within the same class cannot get intercepted that way." (Spring Framework 7.0.9 Reference)

```java
@Service
public class CatalogService {

    @Cacheable(cacheNames = "products", key = "#sku")
    public Product findBySku(String sku) {
        return productRepository.findBySku(sku).orElseThrow();
    }

    public List<Product> loadCatalog(List<String> skus) {
        // this.findBySku(...) 형태의 자기 호출 -> 프록시를 거치지 않음
        // findBySku가 @Cacheable이어도 이 경로에서는 매번 DB를 친다.
        return skus.stream().map(this::findBySku).toList();
    }
}
```

이 문제를 회피하는 실무 해법은 세 가지입니다. (1) 캐시 대상 메서드를 별도 빈으로 분리해 항상 프록시를 거쳐 호출하게 만든다. (2) `AopContext.currentProxy()`로 현재 프록시를 얻어 그것을 통해 호출한다(단, `exposeProxy=true` 설정 필요). (3) advice mode를 `aspectj`로 바꿔 컴파일/로드타임 위빙을 쓴다 — 다만 빌드 체인이 복잡해지므로 실무에서는 (1)을 가장 많이 씁니다. `@Transactional`/`@Async`를 다룰 때 배운 "프록시는 클래스 경계를 통과하는 외부 호출만 가로챈다"는 규칙이 캐시에도 토씨 하나 안 틀리고 그대로 적용된다는 점이 핵심입니다.

### 3. 진짜 흔한 버그 — `key` SpEL 불일치로 캐시가 절대 안 지워진다

가장 실무에서 자주 터지는 사고는 `@CacheEvict`/`@CachePut`의 `key` SpEL이 `@Cacheable`이 저장할 때 쓴 키와 다른 필드를 참조하는 경우입니다. 아래는 그대로 재현 가능한 예제입니다.

```java
@Service
@RequiredArgsConstructor
public class ProductService {

    private final ProductRepository productRepository;

    // 조회는 sku(String) 기준으로 캐시에 저장된다.
    @Cacheable(cacheNames = "products", key = "#sku")
    public Product findBySku(String sku) {
        return productRepository.findBySku(sku).orElseThrow();
    }

    // 버그: 가격을 갱신하면서 캐시를 지우려 하지만, key가 id(Long) 기준이다.
    // 캐시에는 애초에 "SKU-001" 같은 sku 키로만 저장돼 있으므로,
    // key = "#product.id" (예: 42) 로는 캐시에 존재하지 않는 키를 지우는 셈이다 -> evict가 항상 빗나간다.
    @CacheEvict(cacheNames = "products", key = "#product.id")
    public Product updatePrice(Product product, BigDecimal newPrice) {
        product.setPrice(newPrice);
        return productRepository.save(product);
    }
}
```

재현 절차는 이렇습니다.

1. `findBySku("SKU-001")` 호출 → 캐시 미스, DB 조회 후 `products` 캐시에 `key="SKU-001"`로 저장(가격 10,000원).
2. `updatePrice(product, new BigDecimal("8000"))` 호출 → DB에는 8,000원으로 정상 반영. 하지만 `@CacheEvict`는 `key = "#product.id"`(예: `42`)를 지우려 시도하는데, 캐시에는 애초에 `42`라는 키가 존재한 적이 없다. evict는 "조용히 성공"(예외 없이 아무것도 지우지 못함)한다.
3. 다시 `findBySku("SKU-001")` 호출 → 여전히 캐시 히트, 여전히 10,000원 반환. DB는 8,000원인데 응답은 10,000원 — 전형적인 stale read.

가장 골치 아픈 점은 이 버그가 **예외를 던지지 않는다**는 것입니다. `@CacheEvict`는 지울 키가 캐시에 없어도 에러 없이 통과하므로, 로그만 봐서는 이상 징후가 전혀 안 보입니다. 통합 테스트에서 "갱신 후 재조회 값이 최신인가"를 명시적으로 검증하지 않으면 프로덕션까지 그대로 흘러갑니다. 고치는 방법은 단순히 키 표현식을 통일하는 것입니다.

```java
// 수정: evict의 key도 sku 기준으로 맞춘다.
@CacheEvict(cacheNames = "products", key = "#product.sku")
public Product updatePrice(Product product, BigDecimal newPrice) {
    product.setPrice(newPrice);
    return productRepository.save(product);
}

// 또는 evict 대신 캐시를 최신 값으로 즉시 갱신하고 싶다면 @CachePut을 쓰되,
// 마찬가지로 key는 반드시 @Cacheable과 동일해야 한다.
@CachePut(cacheNames = "products", key = "#product.sku")
public Product updatePriceAndRefreshCache(Product product, BigDecimal newPrice) {
    product.setPrice(newPrice);
    return productRepository.save(product);
}
```

`allEntries = true` 옵션으로 캐시 전체를 비우는 방식도 있는데, 이 경우 `key`는 아예 무시됩니다. 공식 문서는 "the framework ignores any key specified in this scenario as it does not apply"라고 명시합니다. 부분 무효화가 아니라 전체 무효화가 목적이라면 이쪽이 더 안전한 선택일 수 있습니다 — 다만 트래픽이 큰 캐시를 통째로 비우면 그 순간 DB에 요청이 몰리는 캐시 스탬피드(cache stampede) 위험은 별도로 관리해야 합니다.

### 4. `null` 캐싱 gotcha — `unless`/`condition`을 안 쓰면 벌어지는 일

`condition`과 `unless`는 이름은 비슷하지만 평가 시점이 다릅니다. `condition`은 **메서드 실행 전**에 평가되어 캐싱 여부(그리고 캐시 조회 여부) 자체를 결정하고, `unless`는 **메서드 실행 후** 반환값(`#result`)을 보고 캐시에 저장할지 말지를 거부(veto)합니다.

```java
@Cacheable(cacheNames = "products", key = "#sku")
public Product findBySku(String sku) {
    // sku에 해당하는 상품이 없으면 null 반환
    return productRepository.findBySku(sku).orElse(null);
}
```

`unless`를 지정하지 않으면 이 `null` 반환값도 그대로 캐시에 저장됩니다. 즉 아직 등록되지 않은 상품을 조회한 시점의 "없음" 결과가 캐시에 박제되고, 이후 실제로 그 상품이 등록되어도 캐시가 만료되거나 명시적으로 evict되기 전까지는 계속 `null`이 반환됩니다 — "방금 등록했는데 왜 안 보이지"라는 문의로 이어지는 전형적인 패턴입니다. 이를 막으려면 다음처럼 `unless`로 명시적으로 거부해야 합니다.

```java
@Cacheable(cacheNames = "products", key = "#sku", unless = "#result == null")
public Product findBySku(String sku) {
    return productRepository.findBySku(sku).orElse(null);
}
```

`Optional<T>`을 반환 타입으로 쓰는 경우는 조금 다릅니다. 공식 문서는 "If an `Optional` value is _present_, it will be stored in the associated cache. If an `Optional` value is not present, `null` will be stored in the associated cache"라고 밝히고 있어, `Optional.empty()`인 경우에도 결국 캐시에는 `null`이 저장된다는 점을 명확히 합니다. 즉 반환 타입을 `Optional`로 바꾸는 것만으로는 이 gotcha가 자동으로 해결되지 않으며, 여전히 `unless`로 의도를 명시하거나 별도 정책(예: negative caching에 짧은 TTL을 두는 캐시 스토어 설정)을 세워야 합니다.

### 5. 캐시 스토어 선택은 별개의 관심사

`@Cacheable`이 어떤 저장소를 쓰는지는 `CacheManager` 구현체가 결정하며, 애노테이션 자체와는 독립적입니다. 공식 문서에 정리된 대표 구현체는 테스트/단순 용도의 `ConcurrentMapCacheManager`, 온디맨드로 캐시를 생성하는 `CaffeineCacheManager`, JSR-107 호환 스토어(Ehcache 3.x 포함)를 감싸는 `JCacheCacheManager`, 그리고 분산 환경에서 흔히 쓰이는 Redis(Spring Data Redis 경유) 등입니다. 이 글에서 다룬 self-invocation과 key 불일치 문제는 어떤 `CacheManager`를 쓰든 동일하게 발생합니다 — 프록시 인터셉션과 SpEL 키 계산은 스토리지 계층보다 위(추상화 계층)에서 일어나기 때문입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| `@Cacheable` 등 캐시 애노테이션의 기본 advice mode는 proxy이며, 프록시를 통하지 않는 self-invocation에는 캐싱이 적용되지 않는다 | verified | Spring Framework 7.0.9 Reference, "Annotations" — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html (원문: "self-invocation ... does not lead to actual caching at runtime even if the invoked method is marked with @Cacheable") |
| `@CacheEvict`의 `allEntries=true` 옵션 사용 시 `key` 속성은 무시되고 캐시 전체가 삭제된다 | verified | 위와 동일 문서, "the framework ignores any key specified in this scenario as it does not apply" — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html |
| `@CacheEvict`의 `beforeInvocation` 기본값은 false이며, 메서드가 정상 완료된 이후에 캐시 제거가 실행된다(예외 발생 시 제거되지 않음) | verified | 위와 동일 문서, "eviction should occur after (the default) or before the method is invoked ... If the method does not run ... or an exception is thrown, the eviction does not occur" — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html |
| `condition`은 메서드 실행 전에 평가되어 캐싱 여부를 결정하고, `unless`는 메서드 실행 후 `#result`를 참조해 캐시 저장을 거부(veto)할 수 있다 | verified | 위와 동일 문서, "unless expressions are evaluated after the method has been invoked" — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html |
| `Optional` 반환 타입에서 값이 없으면(`Optional.empty()`) `null`이 그대로 캐시에 저장된다 | verified | 위와 동일 문서, "If an Optional value is not present, null will be stored in the associated cache" — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html |
| Spring Cache 추상화는 ConcurrentMap 기반, Caffeine, JSR-107(Ehcache 3.x 포함), Redis(Spring Data 경유) 등 다양한 `CacheManager` 구현체를 지원한다 | verified | Spring Framework 7.0.9 Reference, "Cache Storage" — https://docs.spring.io/spring-framework/reference/integration/cache/store-configuration.html |

## 작성자의 견해

> 이 글에서 가장 강조하고 싶은 견해는, `@Cacheable`을 단독 기능으로 외우면 오히려 함정에 걸리기 쉽다는 점입니다.

`@Transactional`, `@Async`, `@Cacheable`을 각각 별개의 애노테이션으로 암기하면 "왜 이 메서드는 안 걸리지?"라는 질문이 나올 때마다 매번 새로 찾아봐야 합니다. 하지만 세 애노테이션 모두 "빈 컨테이너가 반환하는 것은 원본 객체가 아니라 프록시"라는 동일한 전제 위에 서 있다는 것을 한 번 제대로 이해하면, self-invocation 문제는 세 애노테이션에 대해 동시에 해결됩니다. 실무에서는 이 프록시 함정보다 `key` SpEL 불일치가 훨씬 자주, 훨씬 조용히 사고를 냅니다 — 컴파일 에러도, 런타임 예외도 없이 그냥 옛날 데이터가 계속 나오기 때문입니다. 제 개인적인 해석으로는, `@CacheEvict`/`@CachePut`를 추가할 때마다 "이 key 표현식이 원본 `@Cacheable`의 key와 정확히 같은 값을 만들어내는가"를 리뷰 체크리스트에 명시적으로 넣는 것이 코드 리뷰 단계에서 가장 비용 대비 효과가 큰 방어선이라고 봅니다. 이런 종류의 실수는 단위 테스트만으로는 잘 안 잡히고, "갱신 후 재조회" 시나리오를 도는 통합 테스트가 있어야 드러나는 경우가 많습니다.

## 한계와 반론

이 글에서 제시한 재현 예제는 단순화된 시나리오이며, 실제 서비스 코드에서는 `Product` 엔티티에 `equals`/`hashCode` 오버라이드, 복합 키, `@EmbeddedId` 등 더 복잡한 상황이 얽혀 key 불일치 문제가 다른 양상으로 나타날 수 있습니다. 또한 Redis처럼 원격 캐시 스토어를 쓰는 경우 직렬화 방식(Jackson vs. JDK 직렬화)에 따라 키 문자열 표현이 미묘하게 달라져, 여기서 다룬 SpEL 불일치와는 별개로 "같은 의도의 키인데 실제 저장된 문자열이 다른" 유형의 사고도 발생할 수 있는데 이는 이번 글의 범위 밖입니다. `unless = "#result == null"` 처방도 만능은 아닙니다 — negative caching 자체가 유효한 설계일 때도 있으므로(예: 존재하지 않는 리소스에 대한 반복 조회를 막고 싶을 때), 무조건 null 캐싱을 막는 것이 항상 정답은 아니라는 점을 반론으로 남겨둡니다. `AopContext.currentProxy()` 방식은 성능·가독성 트레이드오프가 있어 이 글에서는 권장 우선순위를 낮게 뒀지만, 팀 컨벤션에 따라 선호될 수도 있습니다.

## 참고문헌

1. Spring Framework Reference — Annotations (Cache Abstraction), "The Spring Framework — Integration — Caching" (확인일: 2026-08-23) — https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html
2. Spring Framework Reference — Cache Storage Configuration, "The Spring Framework — Integration — Caching" (확인일: 2026-08-23) — https://docs.spring.io/spring-framework/reference/integration/cache/store-configuration.html

## 종합적 의견

> 종합하면, `@Cacheable`은 "결과를 저장했다가 재사용한다"는 단순한 그림 뒤에 프록시 인터셉션이라는 구체적인 실행 모델을 감추고 있다는 것이 제 의견입니다.

이 실행 모델을 모르면 self-invocation 버그를 "가끔 캐시가 안 먹는 이상한 현상"으로만 인식하게 되고, key SpEL 불일치는 더 나쁘게도 "버그 자체를 인지하지 못하는 상태"로 이어집니다. 이 글에서 다룬 세 가지 — 프록시 인터셉션과 self-invocation, key 불일치로 인한 무효화 실패, null 캐싱 기본 동작 — 는 서로 독립된 토픽이 아니라, "캐시 애노테이션도 결국 AOP 프록시가 SpEL을 평가해 캐시 스토어를 다루는 코드"라는 하나의 실행 모델에서 파생된 증상들이라고 봅니다. 실무에서 캐시 관련 버그를 리포트받으면 저는 항상 이 세 가지를 순서대로 의심합니다 — 먼저 호출 경로가 프록시를 거치는지, 그다음 evict/put의 key가 원본과 정확히 일치하는지, 마지막으로 null/Optional 처리가 의도한 대로인지. 이 순서 자체가 이 글이 전달하고 싶은 실전 체크리스트입니다.

## 꼬리질문

- `AopContext.currentProxy()`를 쓰지 않고도 self-invocation 문제를 구조적으로 피하려면 어떤 설계 패턴(예: 메서드 분리, 이벤트 기반 위임)이 가장 실용적일까?
- Redis 기반 분산 캐시에서 `@Cacheable`의 key SpEL이 만들어내는 실제 저장 키 문자열은 직렬화 방식에 따라 어떻게 달라지며, 이를 테스트로 어떻게 검증할 수 있을까?
- `@Caching` 컴포지트 애노테이션으로 여러 `@CacheEvict`/`@CachePut`를 조합할 때, key 불일치를 컴파일 타임 혹은 정적 분석으로 미리 잡아낼 방법이 있을까?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)