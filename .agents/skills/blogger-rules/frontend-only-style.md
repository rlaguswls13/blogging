# 프론트엔드 스타일 및 레이아웃 가이드 (Frontend Style & Layout Rules)

본 문서는 블로그 테마의 프론트엔드 코드(CSS, Grid 레이아웃) 설계 표준과 템플릿 마크업 내의 정적 데이터를 동적으로 분리하기 위한 개발 규칙을 정의합니다.

---

## 1. CSS 디자인 토큰 & 다크 모드 규칙

테마의 일관된 브랜드 아이덴티티와 다크 모드 처리를 위해, 모든 색상과 크기 명세는 CSS 사용자 정의 변수(CSS Custom Properties)를 사용합니다.

### 1.1 기본 라이트/다크 테마 토큰 매핑
```css
:root {
  /* 브랜드/포인트 컬러 */
  --primary-color: #2563eb;
  --primary-light: #eff6ff;
  --primary-dark: #1d4ed8;
  --accent-color: #3b82f6;

  /* 배경 및 표면 컬러 */
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --terminal-bg: #1e293b;

  /* 텍스트 & 경계선 */
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border-color: #e2e8f0;

  /* 타이포그래피 */
  --font-family: 'Inter', 'Noto Sans KR', sans-serif;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #0f172a;
    --card-bg: #1e293b;
    --text-main: #f1f5f9;
    --text-muted: #94a3b8;
    --border-color: #334155;
    --terminal-bg: #020617;
    --primary-light: #1e3a5f;
  }
}
```

---

## 2. 레이아웃 & 그리드 아키텍처 규칙

구조화된 정보 배치를 위해 레이아웃은 Flexbox와 CSS Grid를 사용하여 반응형으로 구조를 잡습니다.

### 2.1 메인 2단/1단 컨테이너 구조 (`.container`)
- **목록형 뷰(홈, 검색, 카테고리 등)**: 메인 포스트 목록 영역과 우측 사이드바 영역을 `2.8fr : 1.2fr` 비율의 2열 Grid 레이아웃으로 설계합니다.
- **상세형 뷰(포스트 본문, 정적 페이지)**: 가독성 극대화를 위해 사이드바를 숨기고 본문 영역을 `max-width: 840px`로 제한하여 1열 중앙 정렬합니다.

```css
.container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  box-sizing: border-box;
}

@media(min-width: 992px) {
  .container {
    grid-template-columns: 2.8fr 1.2fr;
  }
}

/* 상세 뷰 전용 1열 오버라이드 클래스 */
.container.is-single-column {
  grid-template-columns: 1fr !important;
  max-width: 840px;
}
```

### 2.2 포스트 카드 그리드 (`.tech-featured-grid`)
- 모바일(최대 639px)에서는 1열 세로 레이아웃으로 출력하고, 태블릿 이상(640px 이상)부터 2열 카드로 확장합니다.

```css
.tech-featured-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media(min-width: 640px) {
  .tech-featured-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

---

## 3. 정적 데이터 디커플링 규칙 (Static-to-Dynamic Decoupling)

템플릿 마크업(`.xml`) 내부에 테스트용 정적 데이터를 하드코딩하지 않고, 항상 동적인 변수 바인딩을 적용하거나 가젯 설정 메타데이터로 위임해야 합니다.

### 3.1 하드코딩 텍스트 전면 배제 룰
1. **히어로 영역 카운터 규칙**: `ENGINEERING NOTES · 76 ARTICLES` 등과 같은 텍스트를 하드코딩하지 않고, Blogger 변수를 직접 주입하여 글 개수가 반영되도록 작성합니다.
   - **잘못된 예**: `<span>76 ARTICLES</span>`
   - **올바른 예**: `<span class='tech-hero-kicker'>... <data:blog.totalPosts/> ARTICLES</span>`
2. **사이드바 프로필/소개글 규칙**: 소개 문구를 XML 뼈대 HTML에 직접 쓰지 않고, Blogger 가젯 설정값(`b:widget-setting`) 또는 `data:content` 바인딩을 통해 대시보드 레이아웃 UI에서 동적으로 수용할 수 있게 설계합니다.
3. **태그 칩/라벨 렌더링**: 특정 태그(예: `기술 학습`, `문제 해결`)에 대한 마크업을 정적으로 생성하지 않고, 포스트가 보유한 라벨 목록(`data:post.labels`)을 순회하여 동적 태그 배지로 자동 렌더링되게 만듭니다.

### 3.2 배포 정제 규칙 (Build Strip Rules)
- 로컬 마크다운 파일(`final.md`) 상의 검증 로그, 사실 검증 테이블, QA 질문 등 실제 블로그에 배포되면 안 되는 정적 텍스트 블록은 배포 스크립트(`src/publishers/__init__.py`)의 필터링 정규식 패턴을 거쳐 원천 정제(Strip)한 후 업로드해야 합니다.

---

## 4. 인터랙티브 컴포넌트 UX 규칙

### 4.1 터치 타겟 규격화 (모바일 접근성)
- 모바일 환경에서의 오작동 방지를 위해 모든 클릭 가능한 요소(GNB 메뉴, 카테고리 탭, 카드 태그, 소셜 아이콘)는 **최소 44px × 44px** 이상의 터치 영역(Tap Target)을 유지하도록 패딩과 최소 높이를 스타일시트에 적용해야 합니다.
```css
.nav-links a,
.tech-tag,
.back-button {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  box-sizing: border-box;
}
```

### 4.2 마이크로 인터랙션
- **카드 Hover**: `.tech-post-card`는 마우스 오버 시 `translateY(-6px)` 리프트업 애니메이션과 함께 부드러운 그림자(box-shadow) 및 브랜드 포인트 컬러 테두리 변이 효과가 활성화되도록 트랜지션을 적용합니다.
- **Scroll-to-Top**: 400px 이상 스크롤 다운 시 우하단에 서서히 노출되고, 클릭 시 smooth scroll로 뷰포트를 위로 슬라이드합니다.
