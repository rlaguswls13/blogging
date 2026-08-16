---
id: '2277103064200336936'
publishedAt: '2026-08-14T11:28:02.000-07:00'
slug: gof-9-composite-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 9. 컴포지트 패턴 (Composite Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:18:58.084-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-9-composite-pattern-java.html
---

# [GoF 디자인 패턴] 9. 컴포지트 패턴 (Composite Pattern) 개념과 Java 실전 예시

## 요약

컴포지트 패턴(Composite Pattern)은 단일 객체(Leaf)와 복합 객체(Composite)를 동일한 공통 인터페이스(Component)로 묶어, 클라이언트가 둘을 구분하지 않고 똑같은 방식으로 다룰 수 있게 하는 구조 패턴입니다. 폴더와 파일처럼 전체-부분(Whole-Part) 트리 구조를 다룰 때 특히 유용합니다. 이 글에서는 파일 시스템 용량 계산 예제를 통해 재귀적 구조가 어떻게 동작하는지, 그리고 HTML DOM 트리나 Java Swing 같은 실제 프레임워크에서 이 패턴이 어떻게 쓰이는지 다룹니다.

## 본문

### 1. 배경 및 문제점

소프트웨어 개발에서 폴더와 파일, 메뉴와 서브메뉴 같은 전체-부분(Whole-Part) 트리 구조를 다룰 때 개별 객체(Leaf)와 그룹 객체(Composite)를 다르게 처리하면 코드가 지저분해집니다.

- **조건문(if-else) 도배**: "이 객체가 파일인가, 폴더인가?"를 일일이 `instanceof`로 체크해야 합니다.
- **확장성의 한계**: 새로운 종류의 하위 그룹이 추가될 때마다 트리 탐색 알고리즘 전체를 고쳐야 합니다.

### 2. 해결책 및 동작 메커니즘

컴포지트 패턴은 단일 객체(Leaf)와 복합 객체(Composite)를 동일한 공통 인터페이스(Component)로 묶어 다룹니다. 클라이언트는 대상이 단일 항목인지 그룹인지 상관없이 동일한 `getSize()`나 `render()` 명령을 내릴 수 있으며, 복합 객체는 하위 자식들에게 재귀적으로 명령을 전파해 결과를 합산합니다.

**실제 서비스 동작 예시**: 쇼핑몰의 카테고리 트리를 생각해 보면, 대분류(디지털기기) → 중분류(스마트폰) → 소분류(특정 상품) 구조에서 하위 개별 상품이든 상위 카테고리 그룹이든 구분 없이 동일한 "상품 개수 조회" 인터페이스로 일관되게 처리할 수 있습니다. 동작 흐름은 카테고리 선택 → 공통 `getSize()` 호출 → 하위 모든 소분류 상품을 재귀적으로 합산 → 렌더링 순입니다.

**비유**: 컴퓨터의 파일과 폴더 구조를 떠올리면 이해가 쉽습니다. 폴더 안에 파일이 들어갈 수도 있고 또 다른 폴더가 들어갈 수도 있지만, 사용자는 그 차이를 신경 쓰지 않고 우클릭 후 똑같이 "속성(용량 보기)" 버튼을 누릅니다. 이렇게 트리 구조 데이터 조작을 단순화하고, 단일/복합 객체를 무차별적(Uniform)으로 처리할 수 있다는 것이 이 패턴의 핵심 이점입니다.

### 3. 실무 주의점: 안전성 vs 투명성의 설계 타협

공통 인터페이스에 `add()`나 `remove()` 같은 자식 추가 메서드를 정의하면, 단일 파일(Leaf) 객체에서는 이 메서드를 쓸 수 없어 호출 시 예외를 던져야 합니다(투명성 우선, 안전성 희생). 반대로 이런 메서드를 복합 객체(Directory)에만 정의하면, 부모 타입(Component)으로 다룰 때 형변환이 필요해집니다(안전성 우선, 투명성 희생). 실무에서는 트리 구조의 변경 빈도와 타입 안전성 요구 수준에 따라 이 두 방식 중 하나를 선택해야 합니다.

### 4. 실제 동작하는 Java 완벽 예시 코드

```java
import java.util.ArrayList;
import java.util.List;

// 1. 공통 인터페이스 (Component) - 단일 객체와 복합 객체가 함께 구현
interface FileSystemComponent {
    String getName();
    int getSize();
    void print(String indent);
}

// 2. 단일 객체 (Leaf) - 더 이상 자식을 가질 수 없는 객체 (파일)
class FileLeaf implements FileSystemComponent {
    private final String name;
    private final int size;

    public FileLeaf(String name, int size) {
        this.name = name;
        this.size = size;
    }

    @Override
    public String getName() { return name; }

    @Override
    public int getSize() { return size; }

    @Override
    public void print(String indent) {
        System.out.println(indent + "파일: " + name + " (" + size + " KB)");
    }
}

// 3. 복합 객체 (Composite) - 자식들을 포함하는 객체 (디렉토리)
class DirectoryComposite implements FileSystemComponent {
    private final String name;
    private final List<FileSystemComponent> children = new ArrayList<>();

    public DirectoryComposite(String name) {
        this.name = name;
    }

    public void addComponent(FileSystemComponent component) {
        children.add(component);
    }

    // 재귀적으로 하위 모든 컴포넌트의 용량을 합산
    @Override
    public int getSize() {
        int totalSize = 0;
        for (FileSystemComponent child : children) {
            totalSize += child.getSize(); // 재귀 호출
        }
        return totalSize;
    }

    @Override
    public String getName() { return name; }

    @Override
    public void print(String indent) {
        System.out.println(indent + "디렉토리: " + name + " [총 용량: " + getSize() + " KB]");
        for (FileSystemComponent child : children) {
            child.print(indent + "    "); // 하위 트리 재귀 출력
        }
    }
}

public class CompositePatternMain {
    public static void main(String[] args) {
        DirectoryComposite rootDir = new DirectoryComposite("Root_System");

        DirectoryComposite docsDir = new DirectoryComposite("Documents");
        docsDir.addComponent(new FileLeaf("resume.pdf", 500));
        docsDir.addComponent(new FileLeaf("portfolio.docx", 1200));

        DirectoryComposite imgDir = new DirectoryComposite("Images");
        imgDir.addComponent(new FileLeaf("profile.png", 300));
        imgDir.addComponent(new FileLeaf("background.jpg", 800));

        rootDir.addComponent(docsDir);
        rootDir.addComponent(imgDir);
        rootDir.addComponent(new FileLeaf("system_config.env", 50));

        System.out.println("=== 파일 시스템 트리 출력 및 재귀 용량 계산 ===");
        rootDir.print("");
        System.out.println("전체 시스템 총 용량: " + rootDir.getSize() + " KB");
    }
}
```

실행하면 하위 디렉토리들의 용량이 먼저 재귀적으로 합산되고, 루트 디렉토리는 이 값들을 다시 합산해 전체 용량(2850KB)을 계산합니다. 클라이언트 코드는 대상이 파일인지 디렉토리인지 한 번도 구분하지 않았다는 점이 이 패턴의 핵심입니다.

### 5. 실무 프레임워크 적용 사례

- **HTML DOM Tree**: `Node` 인터페이스 아래 `Element`와 텍스트 노드가 재귀적으로 결합되어 DOM 탐색을 수행합니다.
- **Java AWT/Swing**: `Container` 클래스가 `Component` 객체들을 소유하며 `paint()` 메서드로 재귀 렌더링을 수행합니다. `Container` 자체도 `Component`를 상속하기 때문에, 컨테이너 안에 또 다른 컨테이너를 중첩할 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 컴포지트 패턴은 단일 객체와 복합 객체를 동일한 인터페이스로 묶어 클라이언트가 구분 없이 다루게 한다 | verified | Design Patterns (Gamma et al., 1994) Composite 챕터 |
| CLAIM-002: 복합 객체(Composite)는 하위 자식들에게 재귀적으로 연산을 위임해 결과를 합산한다 | verified | Design Patterns (Gamma et al., 1994) Composite 챕터 |
| CLAIM-003: 공통 인터페이스에 자식 관리 메서드를 둘지 여부는 안전성과 투명성 사이의 트레이드오프다 | verified | Design Patterns (Gamma et al., 1994) Composite의 Implementation 논의 |
| CLAIM-004: java.awt.Container는 Component를 상속하며 내부에 다른 Component들을 담아 컴포지트 구조를 이룬다 | verified | Oracle Java SE 8 API 문서 (java.awt.Container) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

컴포지트 패턴을 처음 배울 때는 "그냥 트리 구조 아닌가?"라고 넘기기 쉽지만, 실무에서 진짜 가치가 드러나는 지점은 재귀 호출 자체가 아니라 클라이언트 코드가 단일/복합 객체를 구분하지 않아도 된다는 점이라고 생각합니다. 예를 들어 권한 시스템에서 "사용자 한 명"과 "사용자 그룹"에게 동일한 `checkPermission()` 인터페이스를 적용할 수 있다면, 권한 로직을 호출하는 쪽 코드는 대상이 개인인지 그룹인지 전혀 신경 쓸 필요가 없어집니다. 다만 실무에서 `add()`/`remove()`를 공통 인터페이스에 넣을지 여부는 프로젝트마다 팀 컨벤션이 갈리는 부분이라, 트리 구조가 자주 변경되는 도메인인지 먼저 판단하고 결정하는 것을 권장합니다.

## 한계와 반론

컴포지트 패턴은 트리 깊이가 매우 깊어질 경우 재귀 호출로 인한 스택 오버플로우 위험이 있고, 모든 재귀 호출마다 함수 콜 오버헤드가 누적되므로 대규모 트리에서는 성능 저하가 발생할 수 있습니다. 또한 안전성을 위해 자식 관리 메서드를 Composite 서브클래스에만 두면, 클라이언트가 트리를 순회하며 자식을 추가하려 할 때마다 다운캐스팅이 필요해 컴파일 타임 타입 안전성이 약해진다는 반론도 있습니다. 이런 이유로 일부 팀은 컴포지트 패턴 대신 명시적인 방문자 패턴(Visitor)이나 별도의 트리 순회 유틸리티 클래스를 선호하기도 합니다.

## 참고문헌

1. [Composite pattern - Wikipedia](https://en.wikipedia.org/wiki/Composite_pattern) (확인일: 2026-08-17)
2. [java.awt.Container - Java SE 8 API Documentation](https://docs.oracle.com/javase/8/docs/api/java/awt/Container.html) (확인일: 2026-08-17)
3. [Design Patterns: Elements of Reusable Object-Oriented Software - Wikipedia](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

컴포지트 패턴의 본질은 재귀적 자료구조 자체가 아니라, "부분과 전체를 동일하게 취급한다"는 설계 철학에 있습니다. 파일 시스템, DOM 트리, UI 컴포넌트 트리처럼 계층 구조가 자연스럽게 등장하는 도메인이라면 이 패턴을 적용했을 때 코드가 극적으로 단순해지는 경우가 많습니다. 다만 안전성과 투명성 사이의 트레이드오프는 은탄환이 없는 설계 결정이므로, 트리 구조가 얼마나 자주 변경되고 클라이언트가 자식 관리 기능에 얼마나 자주 접근해야 하는지를 먼저 분석한 뒤 인터페이스 설계 방향을 정하는 것이 바람직합니다.

## 꼬리질문

1. **트리 깊이가 매우 깊은 컴포지트 구조에서 재귀 호출 대신 반복(iterative) 순회로 전환하면 어떤 트레이드오프가 생기는가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Composite_pattern
2. **Visitor 패턴을 컴포지트 구조와 결합하면 안전성과 투명성 트레이드오프 문제를 어떻게 완화할 수 있는가?**
   - 추천 참고 URL: https://en.wikipedia.org/wiki/Design_Patterns

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)