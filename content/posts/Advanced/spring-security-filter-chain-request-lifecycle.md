---
author: ''
createdAt: '2026-08-22T18:35:04.102604Z'
factCheckScore: 0
id: '3261681383621937518'
notionPageId: null
publishedAt: '2026-08-23T17:05:55-07:00'
slug: spring-security-filter-chain-request-lifecycle
status: published
tags:
- Advanced
- Spring
- Security
title: Spring Security Filter Chain — 인증/인가 요청이 통과하는 전 과정
updatedAt: '2026-08-22T18:35:04.102604Z'
url: https://beji-tech.blogspot.com/2026/08/spring-security-filter-chain.html
---

# Spring Security Filter Chain — 인증/인가 요청이 통과하는 전 과정

## 요약

Spring Security는 서블릿 컨테이너의 `Filter` 체인 위에서 동작한다. `DelegatingFilterProxy`가 서블릿 컨테이너의 생명주기와 스프링 `ApplicationContext`를 연결하고, 그 뒤에 있는 `FilterChainProxy`가 실제 `SecurityFilterChain` 안의 필터 목록을 순서대로 호출한다. 이 글은 "필터 체인이 있다"는 개념 설명에 멈추지 않고, `logging.level.org.springframework.security=DEBUG`로 실제 콘솔에 찍히는 필터 순서 목록을 직접 확인하고, 익명 요청과 JWT 인증 요청이 각각 이 목록의 어느 지점에서 갈라지는지 추적한다. 마지막으로 커스텀 필터를 잘못된 위치에 꽂아서 인증이 조용히 깨지는 실패 사례를 재현하고 `addFilterBefore`/`addFilterAfter`로 고치는 과정을 코드로 보여준다.

## 차별화 포인트

대부분의 "Spring Security 필터 체인" 글은 `DisableEncodeUrlFilter → ... → AuthorizationFilter` 같은 필터 이름 나열과 "필터가 순서대로 실행된다"는 개념 설명에서 멈춘다. 이 글은 세 가지를 추가한다. 첫째, 실제 `logging.level.org.springframework.security=DEBUG` 옵션을 켰을 때 콘솔에 찍히는 `DefaultSecurityFilterChain`의 실제 필터 목록 로그와 `FilterChainProxy`의 `Invoking X (n/15)` TRACE 로그 포맷을 그대로 인용해서, "어디서 이 순서를 직접 확인할 수 있는지"를 보여준다. 둘째, 동일한 요청(익명 요청 vs `Authorization: Bearer` JWT 요청)이 같은 필터 목록을 통과하면서 `SecurityContextHolder`에 무엇이 채워지는지가 필터별로 어떻게 달라지는지를 단계별로 대조한다. 셋째, 실무에서 실제로 자주 발생하는 실수 — 커스텀 인증 필터를 `UsernamePasswordAuthenticationFilter` "뒤"에 놓아서 `SecurityContext`가 이미 비어있는 상태로 인가 단계에 도달하는 상황 — 를 코드로 재현하고, `addFilterBefore` vs `addFilterAfter`의 차이로 원인과 수정을 명확히 보여준다. 이건 공식 문서의 필터 순서표만 봐서는 바로 안 와닿는, 직접 필터를 잘못 배치해봐야 체감되는 문제다.

## 본문

### 1. DelegatingFilterProxy에서 FilterChainProxy까지

서블릿 컨테이너는 스프링 빈의 생명주기를 모른다. `web.xml`이나 `ServletContextInitializer`에 등록되는 필터는 컨테이너가 직접 관리하는 객체여야 하는데, Spring Security의 실제 로직은 스프링 빈으로 관리된다. 이 간극을 메우는 것이 `DelegatingFilterProxy`다. Spring Security 공식 레퍼런스(Architecture 챕터)는 이를 다음과 같이 설명한다.

> "Spring provides a `Filter` implementation named `DelegatingFilterProxy` that allows bridging between the Servlet container's lifecycle and Spring's `ApplicationContext`."

`DelegatingFilterProxy`는 컨테이너에 등록된 필터처럼 동작하지만, 실제 처리는 `ApplicationContext`에서 조회한 빈(관례적으로 `springSecurityFilterChain`이라는 이름의 빈, 실체는 `FilterChainProxy`)에 위임한다. Spring Boot 환경에서는 `spring-boot-starter-security`를 추가하는 순간 이 배선이 자동으로 이뤄지므로 개발자가 `DelegatingFilterProxy`를 직접 등록할 일은 거의 없지만, "필터가 스프링 빈 생명주기 안에서 동작한다"는 사실은 커스텀 필터를 만들 때 `@Autowired`가 정상 동작하는 이유를 이해하는 데 중요하다.

`FilterChainProxy`는 하나 이상의 `SecurityFilterChain`을 보유하고, 들어온 요청의 URL 패턴에 맞는 체인을 골라 그 안의 필터들을 순서대로 실행한다. 애플리케이션에 여러 `SecurityFilterChain` 빈을 등록해서(`@Order`로 우선순위 지정) API 경로와 폼 로그인 경로에 서로 다른 필터 구성을 적용하는 것도 이 구조 덕분에 가능하다.

### 2. 실제 필터 순서를 DEBUG 로그로 직접 확인하기

`application.yml`에 아래 한 줄만 추가하면 애플리케이션 시작 시점에 실제로 등록된 필터 순서를 콘솔에서 확인할 수 있다.

```yaml
logging:
  level:
    org.springframework.security: DEBUG
```

공식 문서에 실린 예시 로그는 다음과 같다(문서 원문 그대로 인용).

```
DEBUG ... o.s.s.web.DefaultSecurityFilterChain     : Will secure any request with [
  DisableEncodeUrlFilter,
  WebAsyncManagerIntegrationFilter,
  SecurityContextHolderFilter,
  HeaderWriterFilter,
  CsrfFilter,
  LogoutFilter,
  UsernamePasswordAuthenticationFilter,
  DefaultLoginPageGeneratingFilter,
  DefaultLogoutPageGeneratingFilter,
  BasicAuthenticationFilter,
  RequestCacheAwareFilter,
  SecurityContextHolderAwareRequestFilter,
  AnonymousAuthenticationFilter,
  ExceptionTranslationFilter,
  AuthorizationFilter
]
```

이건 "교과서에 나오는 순서"가 아니라, `HttpSecurity` DSL에 어떤 `.httpBasic()`, `.formLogin()`, `.csrf()` 설정을 했는지에 따라 실제로 애플리케이션이 부팅될 때마다 재구성되는 목록이다. `logging.level.org.springframework.security.web.FilterChainProxy=TRACE`를 추가로 켜면 요청 1건마다 어떤 필터가 몇 번째로 호출됐는지까지 볼 수 있다.

```
TRACE ... o.s.security.web.FilterChainProxy : Invoking DisableEncodeUrlFilter (1/15)
TRACE ... o.s.security.web.FilterChainProxy : Invoking SecurityContextHolderFilter (3/15)
TRACE ... o.s.security.web.FilterChainProxy : Invoking CsrfFilter (5/15)
```

디버깅 중 "내가 추가한 커스텀 필터가 실제로 호출되는지, 몇 번째 순서인지"를 확인하고 싶을 때 가장 확실한 방법은 이 TRACE 로그를 켜는 것이다. 필터 이름을 코드에서 grep 하는 것보다 이 로그 한 줄이 훨씬 신뢰할 수 있는데, 실제로 부팅된 체인의 순서이기 때문이다.

### 3. 같은 필터 목록, 다른 경로 — 익명 요청 vs JWT 요청

동일한 15개 필터 목록을 통과하더라도, 요청에 따라 실제로 "일하는" 필터가 다르다.

**익명 요청(인증 헤더 없음)**의 경우, `SecurityContextHolderFilter`가 `SecurityContextRepository`에서 기존 컨텍스트를 찾지 못하면 빈 컨텍스트로 진행한다. `UsernamePasswordAuthenticationFilter`, `BasicAuthenticationFilter`는 각각 폼 로그인 파라미터나 `Authorization: Basic` 헤더가 없으므로 그냥 통과시킨다(`doFilter`만 호출하고 다음 필터로 넘김). 결국 `AnonymousAuthenticationFilter`가 `SecurityContextHolder`에 `AnonymousAuthenticationToken`을 채워 넣고, `AuthorizationFilter`는 이 익명 토큰의 권한(`ROLE_ANONYMOUS`)으로 인가 여부를 판단한다. 보호된 리소스라면 여기서 `AccessDeniedException`이 발생하고 `ExceptionTranslationFilter`가 이를 잡아 401/403 응답으로 변환한다.

**JWT 인증 요청(`Authorization: Bearer <token>`)**은 OAuth2 Resource Server 설정(`.oauth2ResourceServer(oauth2 -> oauth2.jwt(...))`)이 추가한 `BearerTokenAuthenticationFilter`가 처리한다. 공식 문서는 이 흐름을 다음과 같이 설명한다.

> "The authentication `Filter`... passes a `BearerTokenAuthenticationToken` to the `AuthenticationManager` which is implemented by `ProviderManager`... `JwtAuthenticationProvider` decodes, verifies, and validates the `Jwt` using a `JwtDecoder`."

즉 `BearerTokenAuthenticationFilter`가 헤더에서 토큰을 뽑아 `BearerTokenAuthenticationToken`을 만들고, `ProviderManager`에 위임하면 `JwtAuthenticationProvider`가 서명·만료시간(`exp`)·`iss` 클레임을 검증한 뒤 `JwtAuthenticationConverter`로 권한 목록을 만든다. 검증에 성공하면 `JwtAuthenticationToken`이 `SecurityContextHolder`에 설정되고, 이후의 `AuthorizationFilter`는 이 토큰의 `SCOPE_*`/`ROLE_*` 권한으로 인가를 판단한다. 핵심은, 익명 요청이든 JWT 요청이든 **필터 목록 자체는 같고**, 각 필터가 자신이 처리할 조건(헤더/파라미터 존재 여부)에 해당하지 않으면 그냥 다음 필터로 넘기는 체인 오브 리스판서빌리티(Chain of Responsibility) 패턴이라는 점이다.

### 4. 커스텀 필터를 잘못된 위치에 꽂았을 때 생기는 조용한 인증 실패

가장 까다로운 실수는 커스텀 인증 필터(예: API 키 헤더를 검사해 사용자 정보를 세팅하는 필터)를 `UsernamePasswordAuthenticationFilter` **뒤**에 놓는 경우다. 다음은 실제로 흔히 나오는 실패 코드다.

```java
// 잘못된 배치 — 인가 필터보다도 늦게 실행되어
// AuthorizationFilter가 이미 판단을 내린 뒤에야 SecurityContext가 채워진다.
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/api/**").authenticated()
            .anyRequest().permitAll()
        )
        // AuthorizationFilter는 항상 체인의 가장 마지막 부근에 위치하는데,
        // addFilterAfter 없이 addFilter()만 쓰면 필터 순서 레지스트리에서
        // 정의되지 않은 필터로 취급되어 체인 맨 끝에 붙는 경우가 있다.
        .addFilterAfter(new ApiKeyAuthFilter(), AuthorizationFilter.class)
        .build();
    return http.build();
}
```

이 코드의 문제는 `ApiKeyAuthFilter`가 `AuthorizationFilter` **다음**에 실행된다는 것이다. `AuthorizationFilter`는 이미 `SecurityContextHolder`가 비어 있는(또는 `AnonymousAuthenticationToken`만 있는) 상태에서 인가 판단을 끝내버리므로, `/api/**`에 대한 모든 요청이 인증 여부와 무관하게 403으로 거부되거나, `permitAll()` 경로로 잘못 흘러 들어가 인증이 통째로 무시된다. 로그도, 예외도 없이 "그냥 항상 403이 뜨거나 항상 인증이 안 된 것처럼 동작"하기 때문에 원인 파악이 특히 까다롭다 — 필터 자체는 정상적으로 등록되고 호출도 되지만, **너무 늦게** 호출되는 것이 문제다.

올바른 수정은 `UsernamePasswordAuthenticationFilter` 이전, 정확히는 `SecurityContextHolderFilter` 직후이자 인가 필터보다 앞에 커스텀 인증 필터를 배치하는 것이다.

```java
// 올바른 배치 — AuthorizationFilter가 판단을 내리기 전에
// SecurityContext가 이미 채워져 있도록 UsernamePasswordAuthenticationFilter
// "앞"에 꽂는다.
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/api/**").authenticated()
            .anyRequest().permitAll()
        )
        .addFilterBefore(new ApiKeyAuthFilter(), UsernamePasswordAuthenticationFilter.class)
        .build();
    return http.build();
}

public class ApiKeyAuthFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain chain) throws ServletException, IOException {
        String apiKey = request.getHeader("X-API-KEY");
        if (apiKey != null && isValidApiKey(apiKey)) {
            Authentication auth = new ApiKeyAuthenticationToken(apiKey, resolveAuthorities(apiKey));
            SecurityContextHolder.getContext().setAuthentication(auth);
        }
        chain.doFilter(request, response);
    }

    private boolean isValidApiKey(String key) {
        // 실제 구현에서는 DB/캐시 조회
        return key.startsWith("sk-");
    }

    private java.util.List<GrantedAuthority> resolveAuthorities(String key) {
        return java.util.List.of(new SimpleGrantedAuthority("ROLE_API_CLIENT"));
    }
}
```

`addFilterBefore(Filter, Class)`는 지정한 필터 클래스 앞에, `addFilterAfter(Filter, Class)`는 뒤에 커스텀 필터를 끼워 넣는다. 공식 문서는 이 두 메서드와 `addFilterAt(Filter, Class)`(기존 필터를 대체)를 다음과 같이 정의한다.

> "`HttpSecurity` comes with three methods for adding filters: `#addFilterBefore(Filter, Class<?>)` adds your filter before another filter; `#addFilterAfter(Filter, Class<?>)` adds your filter after another filter; `#addFilterAt(Filter, Class<?>)` replaces another filter with your filter."

원칙은 단순하다 — **커스텀 인증 필터는 반드시 `AuthorizationFilter`보다 먼저, `SecurityContextHolderFilter`보다 나중에** 실행되어야 `SecurityContext`가 채워진 상태로 인가 판단이 이뤄진다. 이 순서를 지키지 않으면 컴파일도 되고 필터도 정상 등록되지만, 런타임에는 인증이 있으나 마나 한 상태가 되는 게 이 문제의 가장 위험한 지점이다.

### 5. 정리 — 필터 순서를 "확인하는 습관"이 왜 중요한가

필터 순서를 외우는 것보다 중요한 건, 매 배포 전에 실제로 부팅된 필터 목록을 DEBUG 로그로 확인하는 습관이다. `HttpSecurity` DSL 설정 하나(`.oauth2ResourceServer()`, `.cors()`, `.csrf(csrf -> csrf.disable())` 등)가 추가되거나 빠질 때마다 필터 목록의 구성과 순서가 바뀔 수 있고, 이는 컴파일 타임에는 전혀 드러나지 않는다. CI 파이프라인에 "부팅 로그에서 필터 목록을 추출해 이전 스냅샷과 비교"하는 간단한 스모크 테스트를 넣어두면, 리뷰에서 놓치기 쉬운 필터 순서 변경을 자동으로 잡아낼 수 있다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| `DelegatingFilterProxy`는 서블릿 컨테이너 생명주기와 스프링 `ApplicationContext`를 연결하는 브릿지 역할을 한다 | verified | Spring Security 공식 레퍼런스 "Servlet Applications" > Architecture 챕터 원문: "Spring provides a `Filter` implementation named `DelegatingFilterProxy` that allows bridging between the Servlet container's lifecycle and Spring's `ApplicationContext`." (https://docs.spring.io/spring-security/reference/servlet/architecture.html, 확인일: 2026-08-22) |
| `logging.level.org.springframework.security=DEBUG` 설정 시 애플리케이션 부팅 시점에 `DefaultSecurityFilterChain`이 실제 필터 목록을 콘솔에 출력한다 | verified | 동일 문서에 "The list of filters is printed at DEBUG level on the application startup" 및 `Will secure any request with [DisableEncodeUrlFilter, ... AuthorizationFilter]` 형태의 실제 로그 예시가 실려 있음 (https://docs.spring.io/spring-security/reference/servlet/architecture.html, 확인일: 2026-08-22) |
| `HttpSecurity`는 `addFilterBefore(Filter, Class)`, `addFilterAfter(Filter, Class)`, `addFilterAt(Filter, Class)` 세 메서드로 커스텀 필터를 체인의 특정 위치에 삽입/교체할 수 있게 한다 | verified | 공식 문서 원문: "`HttpSecurity` comes with three methods for adding filters: `#addFilterBefore(Filter, Class<?>)` adds your filter before another filter... `#addFilterAfter(Filter, Class<?>)` adds your filter after another filter... `#addFilterAt(Filter, Class<?>)` replaces another filter with your filter." (https://docs.spring.io/spring-security/reference/servlet/architecture.html, 확인일: 2026-08-22) |
| JWT 리소스 서버 구성에서 `BearerTokenAuthenticationFilter`가 `Authorization: Bearer` 헤더를 읽어 `BearerTokenAuthenticationToken`을 만들고, `ProviderManager`에 위임된 `JwtAuthenticationProvider`가 서명·`exp`/`nbf`·`iss` 클레임을 검증한다 | verified | 공식 문서 "How JWT Authentication Works" 섹션 원문: "The authentication `Filter`... passes a `BearerTokenAuthenticationToken` to the `AuthenticationManager` which is implemented by `ProviderManager`"; "`JwtAuthenticationProvider` decodes, verifies, and validates the `Jwt` using a `JwtDecoder`"; "Validate the JWT's `exp` and `nbf` timestamps and the JWT's `iss` claim" (https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html, 확인일: 2026-08-22) |
| `UsernamePasswordAuthenticationFilter`는 `AbstractAuthenticationProcessingFilter`의 서브클래스로, 제출된 username/password로부터 `UsernamePasswordAuthenticationToken`을 만들어 `AuthenticationManager`에 전달한다 | verified | 공식 문서 "Servlet Authentication Architecture" 원문: "UsernamePasswordAuthenticationFilter creates a UsernamePasswordAuthenticationToken from a username and password that are submitted in the HttpServletRequest." (https://docs.spring.io/spring-security/reference/servlet/authentication/architecture.html, 확인일: 2026-08-22) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해입니다.

개인적으로 Spring Security의 필터 체인 구조에서 가장 저평가된 디버깅 도구는 TRACE 레벨의 `FilterChainProxy` 로그라고 생각한다. 대부분의 튜토리얼은 필터 이름과 순서를 표로 암기시키려 하지만, 실무에서 실제로 마주치는 문제는 "이 순서가 이번 배포에서도 그대로인가"이고, 이건 코드를 읽어서는 확실히 알 수 없다. `.csrf()`, `.oauth2ResourceServer()`, `.cors()` 같은 DSL 메서드 하나가 추가되거나 제거될 때마다 필터 목록이 재구성되기 때문에, 코드 리뷰만으로 최종 필터 순서를 완벽히 예측하는 건 사실상 불가능하다고 본다. 그래서 나는 새로운 `SecurityFilterChain` 빈을 건드릴 때마다 로컬에서 DEBUG 로그를 한 번 켜서 실제 출력된 목록을 확인하는 것을 습관으로 삼는 편이 안전하다고 생각한다. 또한 `addFilterBefore`/`addFilterAfter`로 커스텀 필터를 끼워 넣는 코드에는 "왜 이 필터 앞/뒤에 놓았는가"를 주석으로 남기는 게, 다음에 이 코드를 건드릴 사람(혹은 6개월 뒤의 나 자신)이 순서를 실수로 바꾸는 사고를 막는 가장 저렴한 방법이라고 생각한다. 이 필터 순서 문제는 스프링 시큐리티가 "설정이 곧 코드"인 구조이기 때문에 생기는, 프레임워크 설계상 피하기 어려운 트레이드오프라고 본다.

## 한계와 반론

이 글에서 제시한 필터 순서 로그와 예시 코드는 Spring Security 7.1.1 기준이며, `FilterOrderRegistration`에 등록된 필터 순서 자체는 마이너 버전마다 새 필터가 추가되거나 위치가 조정될 수 있다. 예를 들어 OAuth2 Resource Server, SAML, Passkey(WebAuthn) 등 특정 모듈을 활성화하면 기본 15개 필터 목록에 추가 필터가 끼어들며, 이 글의 예시 로그(15개 필터)는 최소 구성 기준이다. 따라서 실무에서는 이 글의 로그를 "정답"으로 암기하기보다, 매번 자신의 프로젝트에서 직접 DEBUG 로그를 켜서 실제 목록을 확인하는 방식을 권한다. 또한 `addFilterBefore`/`addFilterAfter`로 커스텀 필터를 삽입하는 방식 자체가 다소 저수준(low-level) API라는 반론도 가능하다 — 많은 경우 `AuthenticationProvider`나 `OncePerRequestFilter` 대신 스프링 시큐리티가 제공하는 표준 확장 포인트(`AuthenticationSuccessHandler`, `AuthenticationEntryPoint`, 커스텀 `AuthenticationProvider` 조합)만으로 같은 요구사항을 필터 순서 걱정 없이 해결할 수 있는 경우도 많으므로, 커스텀 필터 삽입은 표준 확장 포인트로 해결이 안 될 때의 최후 수단으로 접근하는 것이 안전하다.

## 참고문헌

1. Spring Security Reference — "Servlet Applications: Architecture" (DelegatingFilterProxy, FilterChainProxy, SecurityFilterChain, DEBUG/TRACE 필터 순서 로그, addFilterBefore/After/At), https://docs.spring.io/spring-security/reference/servlet/architecture.html (확인일: 2026-08-22)
2. Spring Security Reference — "OAuth 2.0 Resource Server: JWT" (BearerTokenAuthenticationFilter, JwtAuthenticationProvider, JWT 검증 과정), https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html (확인일: 2026-08-22)
3. Spring Security Reference — "Servlet Applications: Authentication Architecture" (AbstractAuthenticationProcessingFilter, UsernamePasswordAuthenticationFilter, AuthenticationManager, SecurityContextHolder), https://docs.spring.io/spring-security/reference/servlet/authentication/architecture.html (확인일: 2026-08-22)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

Spring Security의 필터 체인은 "복잡해 보이지만 사실은 하나하나가 조건부로 동작하는 단순한 Chain of Responsibility"라는 게 이 주제를 다루면서 다시 확인한 인상이다. 필터 개수(15개 안팎)에 압도되기 쉽지만, 실제로 각 요청에서 "일하는" 필터는 소수이고 나머지는 조건에 안 맞으면 그냥 다음으로 넘긴다는 점을 이해하면 디버깅이 훨씬 쉬워진다. 이번 글에서 특히 강조하고 싶었던 것은 필터 순서를 "외우는 지식"이 아니라 "매번 확인하는 절차"로 다루자는 제안이다. DEBUG/TRACE 로그는 문서보다 신뢰도가 높은 1차 정보인데(실제로 그 시점에 부팅된 체인 그 자체이므로), 실무에서 이 로그를 습관적으로 켜보는 팀과 그렇지 않은 팀 사이에는 "인증이 조용히 깨졌을 때" 원인 파악 속도에서 꽤 큰 차이가 날 것이라고 생각한다. `addFilterBefore`/`addFilterAfter`로 커스텀 필터를 넣는 패턴은 JWT, API 키, 사내 SSO 연동처럼 표준 인증 방식 밖의 요구사항을 다룰 때 여전히 자주 쓰이는 실전 기법이므로, 이 위치 선정 원칙(인가 필터보다 먼저, SecurityContext 로딩 필터보다 나중)만큼은 확실히 짚고 넘어갈 가치가 있다고 본다.

## 꼬리질문

- 여러 개의 `SecurityFilterChain` 빈을 `@Order`로 등록했을 때, `FilterChainProxy`는 각 요청마다 어떤 기준으로 어느 체인을 선택하며, 두 체인의 `securityMatcher`가 겹치면 어떤 일이 벌어지는가?
- `SecurityContextHolderFilter`가 사용하는 `SecurityContextRepository` 전략(`HttpSessionSecurityContextRepository` vs `RequestAttributeSecurityContextRepository`)에 따라 무상태(stateless) JWT 인증 구성에서 세션이 실제로 생성되는지 여부가 어떻게 달라지는가?
- `AuthorizationFilter`가 도입되기 전(Spring Security 5.x 이하)에 쓰이던 `FilterSecurityInterceptor` 기반 구성과, 현재의 `AuthorizationFilter` 기반 구성 사이에 실질적인 동작 차이가 있는가?

## 백링크

- [Spring AOP(관점 지향 프로그래밍)와 프록시(Proxy) 아키텍처: JDK Dynamic Proxy vs CGLIB 기술 분석](https://beji-tech.blogspot.com/2026/08/spring-aop-proxy-jdk-dynamic-proxy-vs.html)
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)
- [TLS/SSL Handshake 원리와 HTTPS 인증서 검증 과정 — TLS 1.3이 어떻게 1-RTT로 줄였는가](https://beji-tech.blogspot.com/2026/08/tlsssl-handshake-https-tls-13-1-rtt.html)