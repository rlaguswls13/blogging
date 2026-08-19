---
author: AI Tech Editor
createdAt: '2026-08-19T05:41:19.127261Z'
factCheckScore: 0
id: '1308939585332553199'
notionPageId: null
publishedAt: '2026-08-18T22:44:47-07:00'
slug: mvc-msa-architecture-evolution
status: published
tags:
- Basics
- MVC
- MSA
- Spring
- Architecture
title: MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리
updatedAt: '2026-08-19T05:41:19.127261Z'
url: https://beji-tech.blogspot.com/2026/08/mvc-mvc-msa.html
---

# MVC 패턴은 왜 여전히 중요한가 — 모놀리식 MVC에서 현대 MSA 지향 개발로의 아키텍처적 연결고리

## 요약

"요즘은 다들 MSA(마이크로서비스 아키텍처)로 간다는데, 그럼 MVC는 낡은 기술인가요?" — 입문 개발자가 흔히 헤매는 질문입니다. 결론부터 말하면 MVC는 사라진 게 아니라 **역할이 재배치됐습니다**. 하나의 애플리케이션 안에 있던 Model/View/Controller가, 서비스 여러 개로 흩어지면서 View는 클라이언트(SPA)로, Controller는 API Gateway와 각 서비스의 REST Controller로 나뉘어 옮겨간 것입니다. 이 글은 전통적인 MVC 웹앱이 왜 MSA로 진화 압력을 받았는지, 그 과정에서 MVC의 각 역할이 구체적으로 어디로 이동했는지를 Java/Spring 코드와 함께 단계별로 설명합니다. MVC 패턴 자체(Model/View/Controller 3역할 분리)에 대한 기초 설명은 이미 [MVC 패턴: 자판기에서 동적 웹 서비스까지의 진화 및 아키텍처 분석](https://beji-tech.blogspot.com/2026/08/mvc.html)에서 다뤘으므로, 이 글은 그 뒤를 잇는 "MVC 다음 이야기"에 집중합니다.

## 본문

### 1. 먼저, MVC를 한 줄로 복습하기

MVC(Model-View-Controller)는 애플리케이션의 책임을 세 가지로 나눕니다. **Model**은 데이터와 비즈니스 로직, **View**는 화면 렌더링, **Controller**는 사용자 입력을 받아 Model을 조작하고 어떤 View를 보여줄지 결정하는 역할입니다. Spring MVC에서는 이 흐름의 진입점을 `DispatcherServlet`이 담당하는데, 이는 모든 HTTP 요청을 받아 적절한 핸들러로 라우팅하는 "Front Controller 패턴"의 구현체입니다(Spring 공식 문서 기준). 여기까지는 자판기 비유로 설명한 이전 글과 동일한 내용이니, 이 글에서는 반복하지 않고 다음 질문으로 바로 넘어갑니다: **"이 세 역할이 왜 하나의 애플리케이션 안에 머물지 못하게 됐는가?"**

### 2. 전통적인 모놀리식 MVC 웹앱의 전형적인 모습

초기 Spring MVC 애플리케이션에서 `@Controller`는 사용자 요청을 처리한 뒤, JSP나 Thymeleaf 같은 서버 사이드 템플릿의 "뷰 이름"을 문자열로 반환했습니다. 뷰 리졸버(View Resolver)가 이 이름을 실제 HTML 템플릿 파일과 매칭해 서버에서 완성된 HTML을 만들어 브라우저로 보내는 구조입니다.

```java
@Controller
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/products/{id}")
    public String productDetail(@PathVariable Long id, Model model) {
        Product product = productService.findById(id);
        model.addAttribute("product", product);
        return "product-detail"; // 뷰 이름 반환 -> product-detail.html 렌더링
    }
}
```

이 구조에서는 Model(비즈니스 로직/데이터), View(HTML 템플릿), Controller(요청 처리)가 전부 하나의 애플리케이션, 하나의 배포 단위, 하나의 데이터베이스 안에 있었습니다. 초기에는 이게 문제가 되지 않습니다. 오히려 개발 속도가 빠르고 배포도 단순합니다.

### 3. 왜 하나의 MVC 애플리케이션으로는 한계에 부딪히는가

서비스가 커지면서 세 가지 압력이 동시에 발생합니다.

- **팀 확장의 압력**: 팀원이 늘어나면 하나의 코드베이스에 여러 팀이 동시에 커밋하면서 충돌과 배포 병목이 생깁니다. 한 기능의 버그 수정이 전체 애플리케이션의 재배포를 요구하게 됩니다.
- **클라이언트 다양화의 압력**: 웹 브라우저뿐 아니라 모바일 앱, 외부 파트너 API 연동까지 요구되면, 서버가 만들어주는 HTML은 더 이상 유일한 응답 형식이 아니게 됩니다. 모바일 앱은 HTML이 아니라 JSON이 필요합니다.
- **확장성의 압력**: 특정 기능(예: 검색, 결제)만 트래픽이 몰릴 때, 애플리케이션 전체를 통째로 스케일아웃하는 건 비효율적입니다. 트래픽이 몰리는 부분만 독립적으로 확장하고 싶어집니다.

이 세 압력이 겹치면서 등장한 답이 마이크로서비스 아키텍처(MSA)입니다. 그리고 MSA로 전환되는 과정에서, 기존 MVC의 세 역할은 사라지지 않고 각각 다른 곳으로 옮겨갑니다.

### 4. View의 이동: 서버 렌더링에서 SPA + REST API로

가장 먼저 이동하는 건 View입니다. 서버가 HTML을 완성해서 내려주는 대신, 서버는 순수한 데이터(JSON)만 내려주고, 화면을 그리는 책임은 React/Vue 같은 SPA(Single Page Application)로 넘어갑니다. Spring에서는 같은 `@Controller` 애노테이션 체계를 그대로 쓰면서 `@RestController`(`@Controller` + `@ResponseBody`의 결합)를 사용하면, 반환값이 뷰 이름이 아니라 `HttpMessageConverter`를 거쳐 JSON으로 직렬화됩니다.

```java
@RestController
@RequestMapping("/api/products")
public class ProductRestController {

    private final ProductService productService;

    public ProductRestController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/{id}")
    public ProductResponse productDetail(@PathVariable Long id) {
        Product product = productService.findById(id);
        return ProductResponse.from(product); // 객체 반환 -> JSON으로 직렬화
    }
}
```

두 코드를 비교하면 구조는 거의 똑같습니다. 다른 건 애노테이션 하나와 반환 타입뿐입니다. 즉 **View 계층이 서버에서 클라이언트로 물리적으로 이관됐을 뿐, "Controller가 요청을 받아 Model을 조작하고 결과를 돌려준다"는 MVC의 핵심 흐름 자체는 그대로 유지**되고 있는 것입니다.

### 5. Controller의 재편: REST Controller에서 API Gateway로

서비스가 여러 개의 독립된 마이크로서비스로 쪼개지면, 클라이언트가 서비스마다 다른 주소로 직접 요청을 보내야 하는 문제가 생깁니다. 이걸 해결하기 위해 등장한 것이 **API Gateway 패턴**입니다. Chris Richardson의 마이크로서비스 패턴 카탈로그(microservices.io)에 따르면, API Gateway는 "마이크로서비스 기반 애플리케이션의 모든 클라이언트에 대해 단일 진입점 역할을 하는 서비스"로 정의됩니다. 클라이언트는 개별 서비스 주소를 몰라도 되고, 인증/로깅/CORS 같은 공통 관심사를 게이트웨이 한 곳에서 처리할 수 있습니다.

이 흐름에서 예전 MVC의 Controller가 하던 "요청을 받아 적절한 곳으로 라우팅한다"는 역할이, 애플리케이션 레벨의 `DispatcherServlet`에서 인프라 레벨의 API Gateway로 한 단계 더 앞으로 이동한 셈입니다.

### 6. BFF(Backend For Frontend) 패턴: 클라이언트마다 다른 게이트웨이

모바일 앱과 웹 브라우저는 필요한 데이터의 형태와 양이 다릅니다. 모바일 화면은 작아서 데이터를 축약해서 받는 게 유리하고, 웹은 더 풍부한 데이터를 한 번에 받는 게 유리할 수 있습니다. 하나의 API Gateway가 모든 클라이언트를 만족시키려다 보면 API가 점점 비대해지고, 한 클라이언트를 위한 변경이 다른 클라이언트에 영향을 주는 결합이 생깁니다.

이 문제의 해법으로 SoundCloud에서 처음 등장한 것이 BFF(Backend For Frontend) 패턴입니다. Sam Newman의 정리에 따르면 이 이름은 SoundCloud 출신 엔지니어 Phil Calçado가 만든 용어이며, "범용 API 백엔드 하나 대신, 사용자 경험(UI)마다 전용 백엔드를 둔다"는 아이디어입니다. 즉 모바일 전용 BFF, 웹 전용 BFF를 각각 두고, 그 BFF가 각 UI에 최적화된 형태로 데이터를 가공해 내려주는 것입니다. microservices.io도 이 패턴을 API Gateway 패턴의 변형(variation)으로 함께 소개하고 있습니다.

### 7. 그래서 MVC는 사라졌는가? — 아니, 서비스 내부로 들어갔다

여기서 중요한 반전이 있습니다. MSA로 전환됐다고 해서 MVC가 완전히 없어진 게 아닙니다. **개별 마이크로서비스 내부를 열어보면, 그 서비스는 여전히 Controller(요청 처리) - Service(비즈니스 로직, 옛 Model의 확장) - Repository(데이터 접근) 형태의 계층 구조를 쓰고 있는 경우가 대부분**입니다. 다만 서버가 View를 렌더링하지 않으니 "View" 계층만 빠지고, Controller가 REST API 응답을 반환하는 형태로 축소된 것입니다. 결국 MSA는 MVC를 대체한 게 아니라, MVC가 감당하던 여러 책임(요청 처리, 라우팅, 화면 렌더링, 데이터 가공)을 애플리케이션 경계 밖의 여러 컴포넌트(SPA, API Gateway, BFF, 개별 서비스)로 재배치한 결과에 가깝습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Spring MVC의 `DispatcherServlet`은 Front Controller 패턴을 구현하며 모든 HTTP 요청의 진입점 역할을 한다 | verified | Spring Framework 공식 문서 (docs.spring.io/spring-framework/reference/web/webmvc.html) |
| `@Controller`는 뷰 이름(문자열)을 반환해 뷰 리졸버가 HTML을 렌더링하고, `@RestController`(`@Controller`+`@ResponseBody`)는 객체를 `HttpMessageConverter`로 직렬화해 JSON으로 응답한다 | verified | Spring Framework 공식 문서 (docs.spring.io/spring-framework/reference/web/webmvc.html) |
| API Gateway 패턴은 마이크로서비스 기반 애플리케이션에서 모든 클라이언트에 대한 단일 진입점 역할을 하는 서비스로 정의된다 | verified | Chris Richardson, Microservices.io Pattern Catalog (microservices.io/patterns/apigateway.html) |
| BFF(Backend For Frontend)라는 용어는 SoundCloud 출신 엔지니어 Phil Calçado가 만들었으며, Sam Newman이 2015년 공식 문서화·대중화했다 | verified | Sam Newman, "Backends For Frontends" (samnewman.io/patterns/architectural/bff/, 게시일 2015-11-18) |
| microservices.io는 BFF 패턴을 API Gateway 패턴의 변형(variation)으로 함께 소개한다 | verified | Chris Richardson, Microservices.io Pattern Catalog (microservices.io/patterns/apigateway.html) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

개인적으로 초보 개발자들에게 "MVC 대 MSA"라는 구도 자체가 오해를 만든다고 생각합니다. 이 둘은 같은 층위의 개념이 아닙니다. MVC는 "코드를 어떻게 역할별로 나눌 것인가"에 대한 답이고, MSA는 "그 역할들을 담은 서비스를 어떻게 배포 단위로 나눌 것인가"에 대한 답입니다. 그래서 "MSA로 가면 MVC를 안 써도 되나요?"라는 질문은 성립하지 않습니다. 실제로 Spring Boot 기반 마이크로서비스를 열어보면 여전히 `@RestController` - `@Service` - `@Repository` 계층이 있고, 이건 MVC의 정신을 그대로 계승한 구조입니다. 오히려 제가 신입 개발자에게 강조하고 싶은 건, MSA로의 전환이 "기술적으로 멋있어서" 필요한 게 아니라 이 글의 3절에서 짚은 세 가지 압력(팀 확장, 클라이언트 다양화, 부분 확장성)이 실제로 존재할 때만 정당화된다는 점입니다. 트래픽도 적고 팀도 작은 초기 서비스에 처음부터 MSA를 적용하는 건, 얻는 이득보다 네트워크 호출·분산 트랜잭션·운영 복잡도 같은 비용이 훨씬 큰 경우가 많습니다. MVC 기반의 잘 정리된 모놀리식 애플리케이션으로 시작해서, 실제로 압력이 느껴지는 지점부터 서비스를 분리해나가는 점진적 접근이 대부분의 팀에게 더 현실적인 선택이라고 봅니다.

## 한계와 반론

- **한계점**: 이 글에서 설명한 "View→클라이언트, Controller→Gateway" 이동 경로는 REST API + SPA 조합을 전제로 한 것입니다. 서버 사이드 렌더링(SSR)을 유지하는 Next.js 같은 프레임워크나, 여전히 Thymeleaf 기반 서버 렌더링을 쓰는 조직에서는 View가 완전히 클라이언트로 넘어가지 않고 서버와 클라이언트 사이 어딘가(BFF 레이어의 SSR 등)에 남아있는 하이브리드 구조도 흔합니다. 이 글의 도식이 모든 조직에 획일적으로 적용되는 정답은 아닙니다.

- **반론**: "MVC의 역할이 재배치됐다"는 설명에 대해, 일부 아키텍트는 MSA 환경에서의 API Gateway/BFF를 MVC의 Controller와 동일 선상에 놓는 비유가 지나치게 단순화됐다고 지적할 수 있습니다. API Gateway는 라우팅·인증·레이트리미팅 같은 인프라적 관심사를 주로 다루는 반면, 전통적 MVC의 Controller는 애플리케이션 로직에 가까운 요청 처리를 담당했기 때문에 둘의 책임 범위가 완전히 같지는 않습니다. 이 글의 비유는 "이해를 돕기 위한 개념적 연결고리"로 받아들이는 게 정확하며, API Gateway를 Controller의 1:1 대체물로 오해해서는 안 됩니다.

## 참고문헌

1. Spring Framework, "Web on Servlet Stack — Spring Web MVC", [https://docs.spring.io/spring-framework/reference/web/webmvc.html](https://docs.spring.io/spring-framework/reference/web/webmvc.html) (확인일: 2026-08-19)
2. Chris Richardson, Microservices.io Pattern Catalog, "Pattern: API Gateway / Backends for Frontends", [https://microservices.io/patterns/apigateway.html](https://microservices.io/patterns/apigateway.html) (확인일: 2026-08-19)
3. Sam Newman, "Backends For Frontends", [https://samnewman.io/patterns/architectural/bff/](https://samnewman.io/patterns/architectural/bff/) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

MVC와 MSA를 대립 관계로 이해하면 "요즘 MVC는 안 쓰나요?" 같은 질문에 빠지기 쉽지만, 실제로는 포함 관계에 가깝습니다. MSA는 MVC가 하던 일들을 서비스 경계 여러 개로 재배치한 상위 구조이고, 그 재배치된 조각들(REST Controller, Service, Repository) 하나하나는 여전히 MVC적 사고방식으로 설계됩니다. 초보 개발자 입장에서 이 관계를 이해하고 나면, "언제 MSA로 가야 하는가"라는 질문도 더 명확해집니다. 팀이 커지고, 클라이언트가 다양해지고, 특정 기능만 트래픽이 몰리는 압력이 실제로 느껴지기 전까지는 잘 구조화된 모놀리식 MVC 애플리케이션이 오히려 더 생산적인 선택일 수 있습니다. 아키텍처 선택은 유행이 아니라 팀의 규모와 서비스가 실제로 겪는 문제에 따라 결정되어야 하며, MVC에서 MSA로의 전환은 "더 나은 기술로 갈아탄다"가 아니라 "같은 관심사 분리 원칙을 다른 배포 단위에 적용한다"는 관점으로 이해하는 것이 정확합니다.

## 꼬리질문

1. **API Gateway 자체가 SPOF(단일 장애점)나 병목이 될 위험이 있는데, 실무에서는 이걸 어떻게 이중화하고 확장하는가?**
   - 추천 참고 URL: https://microservices.io/patterns/apigateway.html
2. **BFF 패턴을 도입하면 BFF 계층 자체의 유지보수 인력(누가 이 코드를 소유하는가)은 어떤 팀 구조로 배치하는 것이 이상적인가?**
   - 추천 참고 URL: https://samnewman.io/patterns/architectural/bff/
3. **Next.js 같은 SSR 프레임워크를 MSA 환경에 적용할 때, View 렌더링 책임은 정확히 어느 계층(BFF vs 별도 SSR 서버)에 두는 것이 실무적으로 권장되는가?**

## 백링크

- [MVC 패턴: 자판기에서 동적 웹 서비스까지의 진화 및 아키텍처 분석](https://beji-tech.blogspot.com/2026/08/mvc.html)
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)

<!-- AUTO:related-sessions:start -->

## 관련 세션
이 문서와 관련된 세션 아카이브(자동 생성 — 태그 매칭 기반):

- [2026-08-16](../sessions/raw/2026-08-16.md)

<!-- AUTO:related-sessions:end -->