---
name: blogger-rules
description: Blogger publishing, page structuring, and styling formatting guidelines.
---

# Blogger Publishing & Theme Rules

본 블로그 프로젝트에서 준수해야 하는 배포/퍼블리싱의 고정 규칙과 테마 연동 규격입니다. 상세한 Blogger XML/가젯 기술 명세는 [Blogger Layouts V3 종합 기술 레퍼런스](file:///d:/blogging/templates/blogger_layout_thema_widget.md)를 참조하십시오.

## 1. 글 (Posts) 배포 규칙
- **URL 규칙**: `https://${domain}.blogspot.com/${year}/${month}/[post-slug].html`
- **본문 UI/UX**: 지정된 글 테마로 글을 등록하며 가독성 높은 인터랙티브 UI로 지속해서 개선합니다.
- **규칙 1 (검증 내용 제거)**: 사실 검증 결과(`## 사실 검증 결과`)나 작업 체크리스트(`## 꼬리질문`) 같은 내부 검증 사항은 로컬 기록(`final.md` 및 `state.json`)에만 보관하고, **실제 배포되는 본문 글 HTML에서는 완전히 제거**합니다.
- **규칙 2 (참고문헌 하이퍼링크)**: 본문 내 참고문헌 리스트 및 일반 raw URL들은 모두 클릭 가능한 `<a>` 하이퍼링크로 자동 치환하여 배포합니다.
- **규칙 3 (블로그 스타일화)**: Notion/GitBook과 같은 모던하고 가독성 높은 문서 뷰어 레이아웃으로 스타일링 템플릿을 고도화합니다.

## 2. 페이지 (Pages) 배포 규칙
- **URL 규칙**: `https://${domain}.blogspot.com/p/about.html`
- **고정 페이지 배포**: 최초 배포 시에는 고정될 페이지 구조로 뼈대를 올리고, 이후에 실제 수정된 제목과 본문 내용을 채워 업데이트합니다.

## 3. 라벨 (Labels) 운영 규칙
- 글에 지정되는 태그(라벨)들은 Blogger의 카테고리/라벨 매핑 시스템을 기반으로 동적 작동합니다.

## 4. 블로그 전체 레이아웃 (Theme & Gadget Architecture)
- 글, 페이지, 라벨의 각 라우팅 규칙에 부합하도록 상단 메뉴 GNB, 카테고리 필터 바 및 1/2단 그리드 뷰포트를 일치시킵니다.
- **가젯(Gadget) 중심 동적 테마 구성**:
  - 특정 HTML을 하드코딩하지 않고, Blogger 공식 가젯 시스템(`<b:section showaddelement='true'>` 및 `<b:defaultmarkups>`)을 구현하여 사용자가 Blogger 대시보드의 **레이아웃(Layout)** GUI에서 가젯(라벨, 인기글, HTML/자바스크립트, 텍스트 등)을 마우스 드래그 앤 드롭으로 자유롭게 추가, 수정, 삭제 및 위치 변경할 수 있도록 디자인합니다.
  - 가젯 종류별(`Label`, `PopularPosts`, `Text`, `HTML`, `Header`, `PageList`)로 `<b:defaultmarkup>`을 정의하여 대시보드에서 가젯을 추가했을 때 블로그 테마의 커스텀 CSS(`.widget-box`, `.widget-title` 등)가 자동 적용되도록 아키텍처를 설계합니다.

---

## 5. 관련 기술 레퍼런스 문서
- **Blogger Layouts V3 종합 기술 레퍼런스**: [blogger_layout_thema_widget.md](file:///d:/blogging/templates/blogger_layout_thema_widget.md)
  * Blogger XML 최상위 계층, 조건문, 데이터 표현식 및 위젯 타입 전체 목록
- **프론트엔드 스타일 및 레이아웃 가이드**: [frontend-only-style.md](file:///d:/blogging/.agents/skills/blogger-rules/frontend-only-style.md)
  * 디자인 토큰(CSS 변수), 다크 모드, Grid/Flexbox 레이아웃 규격 및 정적 데이터 디커플링 규칙

