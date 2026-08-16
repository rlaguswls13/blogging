---
id: "2277103064200336936"
title: "[GoF 디자인 패턴] 9. 컴포지트 패턴 (Composite Pattern) 개념과 Java 실전 예시"
slug: "gof-9-composite-pattern-java"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/gof-9-composite-pattern-java.html"
publishedAt: "2026-08-14T11:28:02.000-07:00"
updatedAt: "2026-08-15T16:18:58.084-07:00"
tags: ["Basics","Design Patterns","GoF","Java","기초"]
---

# [GoF 디자인 패턴] 9. 컴포지트 패턴 (Composite Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴
    구조 패턴 (Structural Patterns) 시리즈 #9
  

  
## 1. 배경 및 문제점 (Problem & Motivation)

  
소프트웨어 개발 시 폴더와 파일, 메뉴와 서브메뉴 같은 전체-부분(Whole-Part) 트리 구조를 다룰 때 개별 객체(Leaf)와 그룹 객체(Composite)를 다르게 처리하면 코드가 매우 지저분해집니다.

  
    
- **조건문(if-else) 도배:** "이 객체가 파일인가, 폴더인가?"를 일일이 `instanceof`로 체크하여 용량을 계산해야 합니다.
    
- **확장성의 한계:** 새로운 종류의 하위 그룹이 추가될 때마다 트리 탐색 알고리즘 전체를 고쳐야 합니다.
  

  
## 2. 해결책 및 동작 메커니즘 (Solution & How It Works)

  
**컴포지트 패턴(Composite Pattern)**은 단일 객체(Leaf)와 복합 객체(Composite)를 동일한 공통 인터페이스(Component)로 묶어 다룹니다.

  
클라이언트는 대상이 단일 항목인지 그룹 폴더인지 상관없이 동일한 `getSize()` 또는 `render()` 명령을 내릴 수 있으며, 복합 객체는 하위 자식들에게 재귀적으로 명령을 전파하여 결과를 합산합니다.

  
  
    
      
#### 📱 실제 서비스 동작 예시: 당*마켓 카테고리 트리 구조

      
대분류(디지털기기) ➔ 중분류(스마트폰) ➔ 소분류(아이폰) 구조에서 하위 개별 상품이나 상위 카테고리 그룹이나 구분 없이 동일한 '상품 개수 조회' 인터페이스로 일관되게 처리합니다.

      
      
🔄 **Working Flow:** 카테고리 선택 ➔ Component 공통 getSize() 호출 ➔ 하위 모든 소분류 상품 재귀 합산 ➔ 렌더링

    

    
      
#### 📂 비유: 컴퓨터의 파일과 폴더 구조

      
폴더 안에 파일이 들어갈 수도 있고 또 다른 폴더가 들어갈 수도 있지만, 사용자는 신경 쓰지 않고 우클릭 후 똑같이 '속성(용량 보기)' 버튼을 누릅니다.

      
      
🎯 **필요 이유:** 트리 구조 데이터 조작의 단순화 및 단일/복합 객체의 무차별적(Uniform) 처리

    
  

  
## 3. 컴포지트 패턴의 실무 주의점 및 트레이드오프

  
    

      ⚠️ **안전성(Safety) vs 투명성(Transparency)의 설계 타협:**
      공통 인터페이스에 `add()`나 `remove()` 같은 자식 추가 메서드를 정의하면 단일 파일(Leaf) 객체에서는 사용할 수 없어 예외를 던져야 하고, 반대로 복합 객체(Directory)에만 정의하면 부모 타입으로 다룰 때 형변환이 필요한 트레이드오프가 생깁니다.
    

  

  
## 4. 실제 동작하는 Java 완벽 예시 코드

`import java.util.ArrayList;
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
        System.out.println(indent + "📄 파일: " + name + " (" + size + " KB)");
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

    public void removeComponent(FileSystemComponent component) {
        children.remove(component);
    }

    @Override
    public String getName() { return name; }

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
    public void print(String indent) {
        System.out.println(indent + "📂 디렉토리: " + name + " [총 용량: " + getSize() + " KB]");
        for (FileSystemComponent child : children) {
            child.print(indent + "    "); // 하위 트리 재귀 출력
        }
    }
}

// 4. 실행 테스트 (Main)
public class CompositePatternMain {
    public static void main(String[] args) {
        // 루트 디렉토리 생성
        DirectoryComposite rootDir = new DirectoryComposite("Root_System");

        // 서브 디렉토리 1 및 파일 생성
        DirectoryComposite docsDir = new DirectoryComposite("Documents");
        docsDir.addComponent(new FileLeaf("이력서.pdf", 500));
        docsDir.addComponent(new FileLeaf("포트폴리오.docx", 1200));

        // 서브 디렉토리 2 및 파일 생성
        DirectoryComposite imgDir = new DirectoryComposite("Images");
        imgDir.addComponent(new FileLeaf("프로필.png", 300));
        imgDir.addComponent(new FileLeaf("배경.jpg", 800));

        // 루트에 서브 디렉토리 및 단일 파일 추가
        rootDir.addComponent(docsDir);
        rootDir.addComponent(imgDir);
        rootDir.addComponent(new FileLeaf("system_config.env", 50));

        // 전체 트리 구조 및 용량 출력
        System.out.println("=== 파일 시스템 트리 출력 및 재귀 용량 계산 ===");
        rootDir.print("");

        System.out.println("\n📊 [결과] 전체 시스템 총 용량: " + rootDir.getSize() + " KB");
    }
}
`

  
#### 💻 실행 결과 (Expected Output)

```

=== 파일 시스템 트리 출력 및 재귀 용량 계산 ===
📂 디렉토리: Root_System [총 용량: 2850 KB]
    📂 디렉토리: Documents [총 용량: 1700 KB]
        📄 파일: 이력서.pdf (500 KB)
        📄 파일: 포트폴리오.docx (1200 KB)
    📂 디렉토리: Images [총 용량: 1100 KB]
        📄 파일: 프로필.png (300 KB)
        📄 파일: 배경.jpg (800 KB)
    📄 파일: system_config.env (50 KB)

📊 [결과] 전체 시스템 총 용량: 2850 KB

```

  
## 5. 실무 프레임워크 적용 사례 (Real-World Frameworks)

  
    🌐 **HTML DOM Tree:** `Node` 인터페이스 아래 `Element` 및 `TextNode`가 재귀적으로 결합되어 DOM 탐색 수행.
    ☕ **Java AWT/Swing:** `Container` 클래스가 `Component` 객체들을 소유하며 `paint()` 재귀 렌더링 수행.
  

  
## 6. 참고자료 (References)

  
    
- Inpa Dev Blog - GoF 컴포지트(Composite) 패턴 제대로 배워보자
    
- Erich Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*
    
- Refactoring.Guru - Composite Design Pattern
