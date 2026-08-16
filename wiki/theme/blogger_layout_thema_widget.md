# Blogger Layouts V3 종합 기술 레퍼런스

Blogger의 위젯(Widget/Gadget), 테마(Theme), 레이아웃(Layout), 데이터 표현식, XML 구문, CSS 변수 시스템을 포괄하는 상세 명세서입니다.

---

## 1. 아키텍처 개요

### Blogger XML 테마 엔진 vs API v3
- **XML 테마 엔진 (Layouts V3)**: Blogger 서버가 브라우저에 HTML을 렌더링할 때 사용하는 서버사이드 XML 템플릿 마크업 언어. `<b:section>`, `<b:widget>`, `<b:defaultmarkups>` 등의 태그와 `data:view`, `data:post` 등의 표현식으로 동적 레이아웃을 구성합니다.
- **Blogger API v3**: HTTP JSON 기반 RESTful API(`https://www.googleapis.com/blogger/v3/`). 외부 앱에서 블로그, 게시글, 페이지, 댓글 데이터를 CRUD하기 위해 사용합니다.

### Layouts V3 핵심 특징
- `<html b:layoutsVersion='3'>` 선언으로 활성화
- `<b:defaultmarkups>` 시스템으로 가젯 마크업 전역 오버라이드
- `b:defaultwidgetversion='2'` 이상의 최신 가젯 버전 지원
- `b:responsive='true'`로 반응형 모바일 대응
- `b:css='false'`로 기본 CSS 주입 비활성화 (커스텀 CSS 전용)

### 최상위 XML 태그 계층
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html>
<html b:css='false' b:defaultwidgetversion='2' b:layoutsVersion='3' b:responsive='true'
      xmlns:b='http://www.google.com/2005/gml/b'
      xmlns:data='http://www.google.com/2005/gml/data'
      xmlns:expr='http://www.google.com/2005/gml/expr'>
  <head>
    <b:skin><![CDATA[ /* CSS */ ]]></b:skin>
    <b:defaultmarkups> ... </b:defaultmarkups>
  </head>
  <body>
    <b:section id='...'>
      <b:widget id='...' type='...'> ... </b:widget>
    </b:section>
  </body>
</html>
```

---

## 2. XML 태그 레퍼런스

### 2.1 `<b:section>` — 레이아웃 영역
가젯(Widget)들을 배치하는 레이아웃 구획 컨테이너입니다.

| 속성 | 필수 | 값 | 설명 |
|------|------|-----|------|
| `id` | ✅ | 문자열 | 섹션 고유 식별자 |
| `class` | | 문자열 | CSS 클래스명 |
| `showaddelement` | | `'true'`/`'false'` | 대시보드 레이아웃에서 "가젯 추가" 버튼 표시 여부 |
| `maxwidgets` | | 숫자 | 섹션 내 최대 가젯 수 제한 |
| `growth` | | `'vertical'`/`'horizontal'` | 가젯 정렬 방향 (기본: vertical) |

**제약 규칙:**
- `<b:section>` 내부에는 `<b:widget>`만 직계 자식으로 허용 (HTML 태그, 텍스트 직접 삽입 불가)
- `<b:section>` 간 중첩(Nesting) 불가
- 템플릿 전체에서 모든 `id`는 유일해야 함

### 2.2 `<b:widget>` — 가젯 인스턴스

| 속성 | 필수 | 값 | 설명 |
|------|------|-----|------|
| `id` | ✅ | 문자열 | 가젯 고유 ID (예: `Blog1`, `Label1`) |
| `type` | ✅ | 타입명 | 가젯 종류 (예: `Blog`, `Label`, `HTML`) |
| `locked` | | `'true'`/`'false'` | 대시보드에서 이동/삭제 잠금 여부 |
| `title` | | 문자열 | 가젯 표시 제목 |
| `visible` | | `'true'`/`'false'` | 화면 노출 여부 |
| `mobile` | | `'yes'`/`'no'`/`'only'`/`'default'` | 모바일 노출 제어 |
| `version` | | `'1'`/`'2'` | 가젯 버전 |

```xml
<b:widget id='Label1' type='Label' locked='false' title='카테고리'>
  <b:widget-settings>
    <b:widget-setting name='sorting'>ALPHA</b:widget-setting>
    <b:widget-setting name='display'>LIST</b:widget-setting>
    <b:widget-setting name='showFreqNumbers'>true</b:widget-setting>
  </b:widget-settings>
</b:widget>
```

### 2.3 `<b:includable>` — 재사용 템플릿 블록
- `id='main'`: 가젯의 필수 진입점 (렌더링 시작 지점)
- `var` 속성으로 전달받은 데이터 변수명 지정
- `<b:include name='includable-id'/>`: 다른 includable 호출

### 2.4 `<b:defaultmarkups>` — 전역 위젯 템플릿 오버라이드
Layouts V3의 핵심 모듈화 기능. 가젯 유형별 기본 마크업을 중앙 관리합니다.

```xml
<b:defaultmarkups>
  <!-- 공통 모듈: 모든 가젯에서 재사용 -->
  <b:defaultmarkup type='Common'>
    <b:includable id='widget-title'>
      <b:if cond='data:title != ""'>
        <h3 class='widget-title'><data:title/></h3>
      </b:if>
    </b:includable>
  </b:defaultmarkup>

  <!-- 가젯 타입별 오버라이드 -->
  <b:defaultmarkup type='Label'>
    <b:includable id='main'>
      <div class='widget-box'>
        <b:include name='widget-title'/>
        <b:loop values='data:labels' var='label'>
          <a expr:href='data:label.url'><data:label.name/></a>
        </b:loop>
      </div>
    </b:includable>
  </b:defaultmarkup>
</b:defaultmarkups>
```

- `type='Common'`: 전역 재사용 모듈 (모든 가젯에서 `<b:include>` 가능)
- `type='Label'` 등: 해당 타입 가젯이 추가되면 자동으로 이 마크업 적용
- `super.` 구문: 기본 출력 재호출 시 `<b:include name='super.main'/>` 사용

### 2.5 `<b:skin>` — CSS 스타일시트 영역

```xml
<b:skin><![CDATA[
  /* 테마 디자이너 변수 (선택) */
  /*
  <Variable name="body.bg" description="배경 색상" type="color" default="#ffffff" value="#ffffff"/>
  <Variable name="primary.color" description="주요 색상" type="color" default="#2563eb" value="#2563eb"/>
  */

  :root {
    --bg-color: $(body.bg);           /* <Variable> 참조 구문 */
    --primary-color: #2563eb;         /* 또는 직접 값 지정 */
  }
]]></b:skin>
```

- CDATA 블록으로 CSS를 감싸야 XML 파싱 오류 방지
- `$(variable_name)`: 테마 디자이너 UI에서 설정한 값 참조
- `<Variable>` 지원 타입: `color`, `font`, `length`, `string`, `url`, `background`

---

## 3. 제어 태그 레퍼런스

### 조건문
```xml
<b:if cond='data:view.isHomepage'>
  <!-- 홈페이지 전용 -->
<b:elseif cond='data:view.isPost'/>
  <!-- 포스트 상세 -->
<b:else/>
  <!-- 기타 -->
</b:if>
```
지원 연산자: `==`, `!=`, `>`, `<`, `>=`, `<=`, `and`, `or`, `!`, `in`

### 반복문
```xml
<b:loop values='data:post.labels' var='label' index='i'>
  <a expr:href='data:label.url'><data:label.name/></a>
</b:loop>
```
- `values`: 순회할 리스트 데이터
- `var`: 각 항목 변수명
- `index` (선택): 0부터 시작하는 인덱스 변수명

### 다중 분기
```xml
<b:switch var='data:blog.pageType'>
  <b:case value='item'/>    <!-- 글 상세 -->
  <b:case value='static_page'/>  <!-- 고정 페이지 -->
  <b:case value='archive'/>     <!-- 아카이브 -->
  <b:default/>                  <!-- 기본 -->
</b:switch>
```

### 보조 제어 태그
| 태그 | 용도 | 예시 |
|------|------|------|
| `<b:with>` | 지역 변수 별칭 | `<b:with value='data:post.featuredImage' var='img'>` |
| `<b:tag>` | 동적 HTML 태그명 | `<b:tag name='data:view.isPost ? "h1" : "h2"'>` |
| `<b:eval>` | 표현식 평가 출력 | `<b:eval expr='data:blog.totalPosts + 1'/>` |
| `<b:class>` | 조건부 클래스 주입 | `<b:class cond='data:view.isPost' name='single-view'/>` |
| `<b:attr>` | 조건부 속성 주입 | `<b:attr cond='...' name='href' value='...'/>` |
| `expr:` 접두사 | 동적 속성 바인딩 | `expr:href='data:post.url'` |

---

## 4. 데이터 표현식 레퍼런스

### 4.1 뷰 상태 (`data:view.*`)
| 변수 | 타입 | 설명 |
|------|------|------|
| `data:view.isHomepage` | boolean | 메인 홈페이지 여부 |
| `data:view.isPost` | boolean | 게시글 상세 페이지 여부 |
| `data:view.isPage` | boolean | 고정 페이지 여부 |
| `data:view.isSingleItem` | boolean | 단일 아이템(글 또는 페이지) 뷰 여부 |
| `data:view.isMultipleItems` | boolean | 목록 뷰(홈/검색/아카이브) 여부 |
| `data:view.isSearch` | boolean | 검색 뷰 여부 |
| `data:view.isArchive` | boolean | 아카이브 뷰 여부 |
| `data:view.isError` | boolean | 404 에러 페이지 여부 |
| `data:view.search.label` | string | 현재 라벨 검색 뷰의 라벨명 |
| `data:view.search.query` | string | 검색어 |
| `data:view.url` | string | 현재 뷰 URL |
| `data:view.title` | string | 현재 페이지 타이틀 |

### 4.2 블로그 전역 (`data:blog.*`)
| 변수 | 설명 |
|------|------|
| `data:blog.homepageUrl` | 블로그 홈 URL |
| `data:blog.title` | 블로그 제목 |
| `data:blog.totalPosts` | 전체 발행 포스트 수 |
| `data:blog.pageType` | 페이지 유형 (`index`, `item`, `static_page`, `archive`, `error`) |
| `data:blog.locale.language` | 언어 코드 (`ko`, `en` 등) |
| `data:blog.languageDirection` | 텍스트 방향 (`ltr`/`rtl`) |

### 4.3 게시글 객체 (`data:post.*`)
| 변수 | 설명 |
|------|------|
| `data:post.title` | 게시글 제목 |
| `data:post.body` | 본문 전체 HTML |
| `data:post.url` | 영구 링크 (Permalink) |
| `data:post.date` | 작성/발행 일자 |
| `data:post.snippet` | 본문 요약 텍스트 |
| `data:post.author` | 작성자 객체 |
| `data:post.author.name` | 작성자 이름 |
| `data:post.labels` | 라벨 목록 배열 |
| `data:post.featuredImage` | 대표 이미지 URL |
| `data:post.numComments` | 댓글 수 |
| `data:post.allowComments` | 댓글 허용 여부 |

### 4.4 라벨 객체 (`data:label.*`)
| 변수 | 설명 |
|------|------|
| `data:label.name` | 라벨명 |
| `data:label.url` | 라벨 검색 URL |
| `data:label.count` | 해당 라벨 포스트 수 |

### 4.5 가젯 공통 변수
| 변수 | 사용 가젯 | 설명 |
|------|-----------|------|
| `data:title` | 모든 가젯 | 가젯 제목 |
| `data:content` | Text, HTML, Translate | 가젯 본문 콘텐츠 |
| `data:labels` | Label | 전체 라벨 리스트 |
| `data:posts` | Blog, PopularPosts | 게시글 리스트 |
| `data:links` | PageList, LinkList | 링크 리스트 |
| `data:team` / `data:aboutme` | Profile | 프로필 소개글 |

---

## 5. 위젯(가젯) 타입 전체 목록

| 타입 | 설명 | 주요 데이터 변수 |
|------|------|------------------|
| `Blog` | **필수**. 게시글 목록/본문 출력 | `data:posts`, `data:post.*` |
| `Header` | 블로그 제목/설명 헤더 | `data:title`, `data:description` |
| `Label` | 카테고리/라벨 목록 | `data:labels`, `data:label.name/url/count` |
| `PopularPosts` | 인기 게시글 목록 | `data:posts`, `data:post.title/href/snippet` |
| `BlogArchive` | 연도/월별 아카이브 트리 | `data:data`, `data:style` |
| `PageList` | 고정 페이지 메뉴 링크 | `data:links`, `data:link.href/title` |
| `Text` | 텍스트 상자 | `data:title`, `data:content` |
| `HTML` | 커스텀 HTML/JS 코드 | `data:title`, `data:content` |
| `Profile` | 작성자 프로필 | `data:aboutme`, `data:team`, `data:displayname` |
| `BlogSearch` | 블로그 검색창 | `data:title`, `data:targetUrl` |
| `Translate` | 구글 번역 가젯 | `data:title`, `data:content` |
| `AdSense` | 구글 애드센스 광고 | `data:adCode`, `data:client` |
| `FeaturedPost` | 대표 게시물 강조 | `data:post.title/snippet/featuredImage` |
| `LinkList` | 외부/내부 링크 목록 | `data:links`, `data:link.name/target` |
| `TextList` | 텍스트 항목 목록 | `data:items` |
| `ContactForm` | 문의하기 폼 | `data:contactFormMessageUrl` |
| `Image` | 단일 이미지 | `data:sourceUrl`, `data:caption` |
| `Feed` | 외부 RSS/Atom 피드 | `data:feedUrl`, `data:entries` |
| `Attribution` | 저작권/출처 표시 | `data:attribution` |
| `Stats` | 방문자 카운터 | `data:totalCount` |
| `Subscribe` | RSS/이메일 구독 | `data:feedPath` |
| `Navbar` | 구글 상단 내비 (V3 비활성화) | N/A |

---

## 6. 레이아웃 설계 규칙

### 필수 제약 조건
1. **직계 자식 규칙**: `<b:section>` 안에는 오직 `<b:widget>`만 직계 자식으로 배치 가능. HTML 태그나 텍스트 직접 삽입 불가.
2. **중첩 금지**: `<b:section>` 내부에 다른 `<b:section>` 배치 불가.
3. **고유 ID**: 템플릿 전체에서 모든 `b:section id`와 `b:widget id`는 유일해야 함.

### 대시보드 GUI 연동
- `showaddelement='true'`: 레이아웃 메뉴에 "가젯 추가" 버튼 표시
- `locked='false'`: 드래그 앤 드롭 이동/삭제 허용
- `locked='true'`: 고정 (예: Blog1 메인 가젯)

### 모바일 속성
| 값 | 동작 |
|----|------|
| `mobile='yes'` | 데스크톱+모바일 모두 표시 |
| `mobile='no'` | 모바일에서 숨김 |
| `mobile='only'` | 모바일에서만 표시 |
| `mobile='default'` | 기본 테마 정책 따름 |

> **V3 권장**: `b:responsive='true'` 선언 시 `mobile` 속성 대신 CSS 미디어 쿼리로 반응형 처리.

---

## 7. CSS & 반응형 디자인 가이드

### CSS Custom Properties 활용 패턴
```css
:root {
  --primary-color: #2563eb;
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border-color: #e2e8f0;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #0f172a;
    --card-bg: #1e293b;
    --text-main: #f1f5f9;
    --text-muted: #94a3b8;
    --border-color: #334155;
  }
}
```

### 반응형 베스트 프랙티스
1. `<meta name='viewport' content='width=device-width, initial-scale=1'/>` 필수
2. CSS Grid & Flexbox로 레이아웃 구성
3. `<b:defaultmarkups>`로 가젯 UI 일관성 보장
4. 미디어 쿼리 `@media(max-width: 768px)`로 모바일 대응
5. 모든 인터랙티브 요소 최소 터치 영역 44px 이상

---

## 8. 현재 테마 구조 매핑

### 섹션 구성
| Section ID | showaddelement | 용도 |
|------------|----------------|------|
| `main-section` | `false` | 메인 콘텐츠 (Blog1 가젯) |
| `sidebar` | `true` | 사이드바 가젯 영역 (목록 뷰에서만 표시) |
| `footer-section` | `true` | 푸터 가젯 영역 |

### 위젯 목록
| Widget ID | Type | Locked | Title |
|-----------|------|--------|-------|
| `Blog1` | `Blog` | `true` | Blog Posts |
| `Text1` | `Text` | `false` | 소개 (About) |
| `Label1` | `Label` | `false` | 카테고리 |

### defaultmarkup 타입 (10종)
`Common`, `Label`, `PopularPosts`, `Text`, `HTML`, `Profile`, `Header`, `Translate`, `BlogArchive`, `BlogSearch`

### CSS 변수 (11종, 라이트/다크 모드)
`--primary-color`, `--primary-light`, `--primary-dark`, `--bg-color`, `--card-bg`, `--text-main`, `--text-muted`, `--border-color`, `--terminal-bg`, `--accent-color`, `--font-family`

### JavaScript 기능 (4종)
1. **카테고리 탭 활성화**: URL pathname 기반 `.active` 클래스 동적 부여
2. **햄버거 메뉴 토글**: 768px 이하 모바일 네비게이션 드롭다운
3. **읽기 진행 바**: 포스트 상세 페이지 전용 스크롤 진행률 표시
4. **Scroll-to-Top FAB**: 400px 이상 스크롤 시 우하단 원형 버튼 노출

---

## 10. Blogger XML 트러블슈팅 & SAXParseException 예방 규칙 ⚠️

### 10.1 `SAXParseException: The entity name must immediately follow the '&'` 및 `"]]>"` 중복 예외
- **발생 원인**:
  1. 구글 Blogger 테마 XML 엔진은 엄격한 SAX XML 파서를 구동합니다. JavaScript 코드나 HTML 속성 내부에서 `&` 문자를 단순 raw `&`로 사용하거나 Logical AND (`&&`)를 작성하는 경우 파서가 XML Entity 참조 시작으로 오인하여 예외를 발생시킵니다.
  2. `<script type='text/javascript'>` 블록이 다중 중복 삽입되거나 `//<![CDATA[` 짝이 맞지 않은 상태에서 `//]]>` 구문이 노출되면 파서가 `The character sequence "]]>" must not appear in content unless used to mark the end of a CDATA section` 예외를 뿜습니다.
- **필수 준수 규칙**:
  1. `<script type='text/javascript'>` 블록 내부라도 raw `&` 문자를 직접 사용할 수 없으며, 반드시 `//<![CDATA[`와 `//]]>` CDATA 블록으로 완벽히 감싸야 합니다.
  2. CDATA 블록 외부 또는 HTML 표현식(`expr:*`) 내부의 `&` 문자는 100% `&amp;`로 치환해야 합니다 (예: `if (a &amp;&amp; b)`).
  3. XML 내부에서 `<![CDATA[` 가 선언되지 않은 영역에 `]]>` 문자가 단독 노출되지 않도록 스크립트 블록 짝을 1:1로 정확히 검증하고, 스크립트 중간에 `</script>` 태그가 조기 폐쇄되어 `//]]>` 가 일반 HTML 문맥에 단독 노출되는 결함을 100% 방지합니다.

### 10.2 Blogger 1, 2, 3 동적 카드 교체 페이징 엔진 (Dynamic Card Pager Engine)
- **배경**: Blogger 기본 템플릿의 `isHomepage` 조건 및 URL 파라미터 매칭 문제로 인해 클라이언트 페이징 버튼 클릭 시 포스팅 카드가 상위 4개로 고정되는 문제 발생.
- **해결 패턴**:
  1. `Blogger JSON Feed API` (`/feeds/posts/summary?alt=json-in-script&max-results=150`)를 비동기 호출하여 전체 포스팅 인덱스와 날짜/라벨 스냅샷을 획득.
### 10.3 Blogger 카테고리 모달 팝업 포털(Portal) & CSS 특이도(Specificity) 트러블슈팅 (`v17.0.0`)
- **발생 원인**:
  1. **사이드바 상위 DOM 갇힘 (DOM Hierarchy Containment)**: 모달 팝업 오버레이 HTML(`<div id="categories-modal">`)이 사이드바 하위 구조에 조립된 경우, 상위 사이드바 컨테이너의 `280px` 레이아웃 폭 제약 및 `overflow: hidden`, `z-index` 범위 제약으로 인해 화면 전체 반투명 팝업이 출력되지 못하고 갇히는 결함 발생.
  2. **CSS 특이도(Specificity) 우위 파괴**: `<head>` 지점에 선언된 `#categories-modal { display: none !important; }` 스타일과 `theme-style.css` 의 `.modal-overlay.active` 클래스 간 특이도 충돌로 `.active` 가 부여되어도 모달이 계속 숨겨진 상태를 유지함.
  3. **초기 클릭 포인터 가로채기 (Pointer Events Interception)**: 모달 오버레이 요소의 초기 `display: flex` 스타일로 인해 화면 전역을 가려 다른 요소의 클릭을 터치 타임아웃시키는 현상 발생.
- **해결 및 예방 패턴**:
  1. **Body Level Portal 배치**: `#categories-modal` 요소 마크업을 사이드바 밖 `<body>` 최상위 레벨 태그(`<footer>` 직전) 위치로 완전 이동하거나, `window.showCategoriesModal` 실행 시 `if (modal.parentElement !== document.body) document.body.appendChild(modal);` 로 DOM Portal 전이를 보장함.
  2. **Clean Split Specificity & Pointer Events Guard**:
     ```css
     .modal-overlay:not(.active),
     #categories-modal:not(.active) {
       display: none !important;
       visibility: hidden !important;
       opacity: 0 !important;
       pointer-events: none !important;
     }

     .modal-overlay.active,
     #categories-modal.active {
       display: flex !important;
       visibility: visible !important;
       opacity: 1 !important;
       pointer-events: auto !important;
       position: fixed !important;
       top: 0 !important; left: 0 !important;
       width: 100vw !important; height: 100vh !important;
       z-index: 999999 !important;
     }
     ```
  3. **전역 이벤트 위임 (Global Event Delegation)**: 동적 생성되는 `...` 더보기 버튼(`tech-tag-more-btn`)의 버블링 차단 방지를 위해 `document.addEventListener('click', ..., true)` capturing 레벨에서 팝업 함수를 최우선 가로채어 0.0001초 만에 시원한 카테고리 팝업 모달이 노출되도록 보장함.

### 10.4 CDN 캐시 고착 및 XML 완전 인라인 스크립트 엔진 구조 전환 (`v25.0.0`)
- **발생 원인**:
  1. 기존 jsDelivr CDN 기반 `theme-engine.js` 로드 방식에서는 GitHub main 브랜치 업데이트 후에도 CDN edge 캐시 갱신 지연으로 구버전 JS 엔진이 서빙됨.
  2. 스크립트가 IIFE(즉시 실행 함수) 클로저에 갇혀 `window.renderPage` 및 `window.initBloggerFeedPagination` 전역 노출 실패로 비동기 피드 콜백 렌더링이 중단됨.
- **해결 및 예방 패턴**:
  1. 외부 CDN 의존성을 완전 폐기하고 `blogger_site_theme.xml` 하단에 전체 스크립트를 인라인 `<script type='text/javascript'>//<![CDATA[ ... //]]></script>`로 100% 임베딩.
  2. `window.renderPage`, `window.initBloggerFeedPagination`, `window._allPosts`를 `window` 전역 스코프에 노출하여 피드 콜백이 언제든 안전하게 실행되도록 보장.

### 10.5 rockpool 테마 스키마 정합성 & Sticky Nav 오버랩 결함 해결 (`v26.0.0`)
- **발생 원인**:
  1. `b:defaultmessages='false'` 속성 때문에 Blogger 내장 기본 메세지가 차단되는 문제 발생.
  2. `<b:defaultmarkups>`와 `<b:template-skin>` 선언 누락으로 Blogger 기본 페이지네이션(`feedLinks`, `previousPageLink` 등)이 자동 삽입되어 커스텀 JS 페이저와 충돌.
  3. `<b:skin>` 내 `<Variable>` 및 `<Group>` 스키마 정의 누락으로 Blogger 테마 맞춤설정(Theme Designer) UI와 연동되지 않음.
  4. Floating Nav bar(`position: sticky; top: 12px; z-index: 100;`) 아래의 사이드바 최상단 가젯(`HTML1` About 카드)에 충분한 상단 여백이 주어지지 않아 Nav bar 뒤쪽에 시각적으로 겹치는(Overlap) 결함 발생.
- **해결 및 예방 패턴**:
  1. `b:defaultmessages='false'` 제거, `<title><data:view.title.escaped/></title>`로 XSS/SAXParser 이스케이프 보장, `<b:include data='blog' name='all-head-content'/>`로 SEO/OGP 메타태그 자동 렌더링.
  2. `<b:defaultmarkups>`를 통한 기본 페이저 중복 삽입 차단 및 `<b:template-skin>` 레이아웃 UI 보호.
  3. `<b:skin>` 내 `Body`, `Header`, `Feed`, `Widths` `<Group>` 및 `<Variable>` 정의 추가로 테마 맞춤설정 색상/너비 연동 지원.
  4. Visual 겹침 해결: `.main_content_container`에 `padding-top: 80px !important;`, `.sidebar`에 `margin-top: 90px !important;`를 적용하여 상단 Floating Nav bar 아래로 사이드바 가젯 카드가 완전히 이격되도록 렌더링.
  5. `initCategoryTagsLimit()` 인라인 포함: 사이드바 `Label1` 가젯의 수십 개 라벨을 상위 8개 모던 태그 칩 + `...` 더보기 모달 팝업 버튼으로 깔끔히 변환 렌더링.

### 10.6 Layout UI로 추가된 비스타일(Unstyled) 가젯 노출 결함 — `FeaturedPost`/`PopularPosts` (2026-08-16 발견)
- **발생 원인**: Blogger 대시보드 **레이아웃(Layout)** 탭에서 가젯을 드래그앤드롭으로 추가하면, 로컬 저장소의 `content/theme/blogger_site_theme.xml`(소스 오브 트루스)에는 반영되지 않은 채 라이브 사이트에만 위젯이 생성됩니다. 이렇게 추가된 위젯 타입이 `<b:defaultmarkups>` 10종(`Common`, `Label`, `PopularPosts`, `Text`, `HTML`, `Profile`, `Header`, `Translate`, `BlogArchive`, `BlogSearch`) 목록에 없거나(`FeaturedPost`), 있어도 실제로는 Blogger 기본 마크업(`.post`, `.post-title`, `.post-content` raw 클래스)이 적용되면 커스텀 카드 디자인과 전혀 무관하게 100% 비스타일 상태로 렌더링됩니다.
- **실제 사례**: `FeaturedPost1` 위젯이 홈페이지 카드 그리드+페이지네이션 바로 아래에 최신 글의 `data:post.body` **전체 본문**을 스니펫이 아닌 원문 그대로, 아무 CSS 없이 노출(중복 콘텐츠 SEO 감점 + 시각적 붕괴). `PopularPosts1` 위젯은 포스트 상세 페이지 하단에 썸네일/카드 없는 밋밋한 텍스트 링크 목록으로 노출.
- **조치 방향**: 로컬 XML에 없는 위젯이 라이브에만 존재하는 경우 XML 편집으로는 제거되지 않으므로, **Blogger 대시보드 → 레이아웃 → 해당 가젯 편집 → 삭제** 로 직접 제거하는 것이 코드 수정 없이 회귀 위험이 가장 낮음.
- **예방 규칙**: 레이아웃 탭에서 새 가젯을 추가하기 전, 반드시 (1) 해당 타입이 `<b:defaultmarkups>`에 정의되어 있는지, (2) 정의되어 있다면 실제로 `tech-*`/`post-card` 계열 클래스로 스타일링되는지 먼저 확인. 스타일이 없다면 추가하지 않거나, 추가 전 defaultmarkup을 먼저 작성해야 함.

### 10.7 상단 탭(Basics/Advanced/Trends) 키워드 그룹 매칭 중복·누락 결함 (2026-08-16 발견, 10.8에서 최종 정리됨)
- **발생 원인**: `postMatchesFilter()`의 Basics/Advanced 키워드 그룹(`bg`/`ag`)에 `database`, `sql`, `concurrency`, `operatingsystem`, `btreeindex`, `coveringindex` 등 지나치게 범용적인 라벨을 **양쪽 그룹에 중복 등록**해 두어, 실제로는 심화(Advanced) 성격의 글(예: MySQL B+Tree 커버링 인덱스 튜닝, Kafka 파티셔닝)이 Basics 탭에도 동시에 노출되었다. 반대로 어느 그룹 키워드에도 걸리지 않는 글(`Google Blogger API` 연동 가이드, `Spring IoC/DI` — 후자는 `java`라는 범용 라벨 때문에 오히려 Basics로 잘못 분류)은 Advanced/Trends 어디에도 나타나지 않는 결함이 있었다.
- **1차 해결**: 저자가 실제로 붙이는 명시적 라벨(`기초`/`Basics`)로만 Basics를 판정하고, Trends는 기존 특화 키워드 그룹을 유지하며, **Advanced는 "Basics도 Trends도 아닌 나머지 전부"로 판정하는 상호 배타적 규칙**으로 재설계. 클라이언트 필터 함수만 수정해 배포 리스크를 최소화함.

### 10.8 키워드 그룹 완전 폐기 → 실제 라벨 백필 + 한/영 중복 라벨 정리 + Trends→ETC 개명 (2026-08-16)
- **문제의식**: 10.7의 키워드 그룹 방식은 여전히 "글이 늘어날수록 유지보수해야 할 목록"이라는 근본적 확장성 문제가 있었다. 또한 초기엔 저자가 `기초`와 `Basics`를 **동시에** 붙이는 습관이 있어 라벨이 중복되어 있었다.
- **해결 패턴 (3단계, 전부 `src/tools/`에 재사용 가능한 도구로 구현하고 Blogger API로 라이브에 직접 반영)**:
  1. `apply_nav_labels.py`: 38개 기존 글 전수를 조회해 Basics(기초/Basics 라벨 보유)를 제외한 나머지에 `Advanced` 또는 `Trends`(AI Agent/GraphRAG/Kubernetes/DevOps/HTTP3 등 특정 키워드 라벨 보유 시) 라벨을 실제로 추가.
  2. `dedupe_basics_label.py`: `기초`+`Basics`를 동시에 가진 21개 글에서 한국어 `기초`를 제거하고 영어 `Basics`만 남김 (Advanced/Trends가 영어 단일 라벨인 것과 통일).
  3. `rename_trends_to_etc.py`: `Trends` 탭을 `ETC`로 개명(4개 글 라벨을 실제로 `Trends`→`ETC` 치환). AI/Kubernetes/DevOps 등 극소수 특정 주제만 모으는 카테고리라 "트렌드"보다 "기타(ETC)"가 실제 성격에 더 맞다는 판단.
  4. 위 백필이 끝난 뒤 `postMatchesFilter()`를 `lowerLabels.indexOf('basics'/'advanced'/'etc') !== -1` 수준의 **단순 라벨 조회 O(1)**로 완전히 단순화. 키워드 그룹 유지보수가 영구히 불필요해짐.
- **예방 규칙**: 신규 글은 `wiki/Blog_Writing_Rules.md` 7번 규칙에 따라 Basics/Advanced/ETC 중 정확히 하나만, 영어 단일 라벨로 부여한다(한/영 중복 금지).

### 10.9 "100% 인라인"이 실제로는 부분 인라인이었던 함정 — 외부 `theme-style.css` 삭제 시 버튼/모달 스타일 소실 (2026-08-16)
- **발생 원인**: v25에서 JS 엔진은 완전히 인라인화됐지만(10.4), CSS는 `<link href='.../theme-style.css?v=...'/>`로 jsDelivr CDN에서 계속 로드하고 있었다. 이 사실을 모른 채 "이미 다 인라인화됐다"고 가정하고, 중복으로 남아있던 `<link>` 두 개(`?v=7.0.0`, `?v=13.0.0`, 둘 다 동일한 캐시된 내용)를 완전 삭제했더니 **페이지네이션 버튼(`.page-btn`)과 카테고리 모달(`.modal-box`/`.modal-header`/`.modal-close-btn`/`.devlog-tags-popup`)의 CSS가 통째로 사라졌다.** 인라인 `<b:skin>`에는 이 셀렉터들이 애초에 한 번도 옮겨진 적이 없었기 때문이다.
- **교훈**: 외부 `<link>`/`<script>`를 "중복이니 안전하게 지운다"고 판단하기 전에, 반드시 그 파일 실제 내용을 fetch해서 인라인 스킨에 없는 셀렉터가 있는지 diff 확인할 것. jsDelivr `@main` 브랜치 참조는 CORS로 열람 가능하니 브라우저 `fetch()`로 직접 받아 비교하면 된다.
- **해결**: 누락된 셀렉터(`.page-btn` 전체 상태, `.modal-box`, `.modal-header`, `.modal-close-btn`, `.modal-body`, `.devlog-tags-popup`, `.tech-tag-more-btn`)를 외부 파일에서 인라인 `<b:skin>`으로 이식. 외부 파일에 있던 `.modal-overlay`(오버레이 배경/포지셔닝)는 이식 불필요 — `showCategoriesModal()`/`closeCategoriesModal()` JS가 이미 `style.cssText`로 인라인 직접 지정하고 있었음.
- **현재 상태**: `content/theme/theme-style.css`, `theme-engine.js`, `content/theme/css/*`, `content/theme/js/*`는 이제 어디서도 참조되지 않는 죽은 파일(저장소에만 존재). 삭제해도 무방하나 미삭제 상태로 남아있음.

### 10.10 `InvalidVariableException` — CSS 주석 속 raw HTML 태그가 `<SkinVariables>` 파싱을 깨뜨림 (2026-08-16)
- **증상**: `com.google.blogger.b2.layouts.framework.skin.InvalidVariableException: ... not well-formed`. 에러 메시지에 표시된 "Input"이 정상적인 `<Variable>`/`<Group>` 선언 뒤에 `<button class="page-btn"> <a class="page-current">` 같은 엉뚱한 내용이 붙어있었다.
- **발생 원인**: Blogger는 `<b:skin>` CDATA 내부에서 `<Variable .../>`/`<Group>...</Group>` 태그를 포함한 CSS 주석을 찾아 그 내용을 `<SkinVariables>...</SkinVariables>`로 감싸 별도 XML로 파싱한다. 이때 CSS 주석 안에 raw `<`/`>`가 들어간 다른 텍스트(예: 설명용으로 `<button class="page-btn">`라고 실제 태그처럼 적은 주석)가 있으면, 이 텍스트까지 같은 스킨 변수 문서로 흡수되어 태그가 짝이 안 맞는 잘못된 XML이 되어버린다. `ET.parse()`로 전체 XML 자체는 well-formed로 통과하므로(CDATA 내부라 바깥 파서는 문제 없음) 이 함정은 로컬 XML 검증만으로는 잡히지 않는다.
- **예방 규칙**: `<b:skin>` 내부 CSS 주석에는 **절대 raw `<`/`>` 문자를 쓰지 말 것** (`<button class="page-btn">` 대신 `button.page-btn`처럼 태그명.클래스명 표기 사용). 편집 후에는 스킨 변수 주석만 추출해 `<SkinVariables>` + 내용 + `</SkinVariables>`로 감싸 별도로 XML 파싱 테스트하면 이 클래스의 오류를 로컬에서 사전에 잡을 수 있다.

### 10.11 서버가 이미 렌더링한 페이지 1을 JS가 다시 그려서 생기는 "변환 딜레이" (2026-08-16)
- **발생 원인**: Blogger SSR(`<b:loop values='data:posts'>`)이 이미 올바른 카드를 즉시 렌더링해서 내려주는데도, `DOMContentLoaded` 시점에 JS가 `/feeds/posts/summary?...&max-results=150`로 전체 포스트를 다시 fetch해(약 0.9~1.8초 소요) `.tech-featured-grid.innerHTML`을 통째로 덮어썼다. 방문자 대부분이 보는 1페이지에서 "이미 보이던 화면이 잠시 후 다시 그려지는" 눈에 띄는 지연/깜빡임이 발생.
- **해결**: `renderPage()`에 최초 1회 한정 스킵 플래그(`_initialPage1RenderSkipped`)를 두어, 로드 직후 첫 `renderPage(1)` 호출은 DOM을 건드리지 않고 페이지네이션 컨트롤만 붙이도록 함. 2페이지 이상으로 실제 이동할 때만 정상적으로 재렌더링.
- **전제 조건(중요)**: 이 최적화가 성립하려면 **SSR 카드 마크업과 JS(`buildPostCardHtml()`)가 만드는 마크업이 클래스명까지 완전히 동일해야 한다.** 원래 SSR은 `h3`+`.tech-post-card`/`.tech-post-body` 클래스를 쓰고 JS는 `h2.post-card-title`+`.post-card-body` 클래스를 써서 서로 다른 셀렉터를 탔었다(초기엔 JS가 항상 덮어썼기 때문에 안 드러났던 drift). 마크업을 통일하지 않고 이 최적화만 넣으면 1페이지만 스타일이 다르게 보이는 새로운 버그가 생긴다.
- **부수적으로 발견된 결함**: SSR이 `postsPerPage: 4` 위젯 설정과 무관하게 `data:posts`를 더 많이(실측 7개) 내려주고 있었다(지금까지는 JS 재렌더링이 4개로 잘라내서 가려져 있었음). `<b:loop index='i' ...><b:if cond='data:i < 4'>...</b:if></b:loop>`로 SSR 단계에서부터 캡을 씌워 해결.

---

## 11. 공식 참고문헌

### 구글 Blogger 도움말 센터
- [블로그 테마 맞춤설정](https://support.google.com/blogger/answer/176245?hl=ko)
- [가젯 추가/수정/삭제](https://support.google.com/blogger/answer/1227173?hl=ko)
- [블로그 페이지 추가](https://support.google.com/blogger/answer/46871?hl=ko)
- [블로그 레이아웃 구성](https://support.google.com/blogger/answer/46888?hl=ko)
- [블로그 모바일 테마](https://support.google.com/blogger/answer/46995?hl=ko)

### 개발자 문서
- [Blogger Layouts Version 3 공식 발표](https://bloggercode.blogspot.com/2012/06/blogger-layouts-version-3.html)
- [Blogger API v3](https://developers.google.com/blogger/docs/3.0/using)
