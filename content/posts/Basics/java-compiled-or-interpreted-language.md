---
author: ''
createdAt: '2026-08-24T09:52:53.384405Z'
factCheckScore: 1.0
id: '4924239618354743973'
notionPageId: null
publishedAt: '2026-08-24T03:32:34-07:00'
slug: java-compiled-or-interpreted-language
status: published
tags:
- Java
- JVM
- Basics
title: 자바는 컴파일 언어인가, 인터프리터 언어인가 — 바이트코드 기준으로 정리
updatedAt: '2026-08-25T00:00:00.000000Z'
url: https://beji-tech.blogspot.com/2026/08/blog-post.html
---

# 자바는 컴파일 언어인가, 인터프리터 언어인가 — 바이트코드 기준으로 정리

## 요약

실용적인 분류 기준으로는 자바를 컴파일 언어라고 단언하는 게 맞습니다. "결국 다 기계어로 실행되니 전부 컴파일 아니냐"는 논리도, "실행 환경(JVM)이 바이트코드를 인터프리터로 해석하는 구간도 있으니 인터프리터 또는 하이브리드 언어 아니냐"는 논리도 구분력이 없는 잘못된 기준입니다. 실행과 분리된 빌드 단계에서 바이트코드가 나오면 컴파일 언어이며, 자바가 정확히 이 경우입니다. 그래서 컴파일 언어입니다. 이 글은 `Java Language Specification` 원문으로 이를 확인하고, JVM이 그 바이트코드를 이후 어떻게 실행하는지(인터프리터/JIT/AOT)는 완전히 다음 레이어의 질문임을 `Java Virtual Machine Specification` 원문과 HotSpot·GraalVM 사례로 구분해서 보여줍니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어.
-->

첫째, "결국 다 기계어로 실행되니 전부 컴파일"이라는 주장과 "JVM이 실행 중 바이트코드를 인터프리터로 해석하는 구간이 있으니 인터프리터 또는 하이브리드 언어"라는 정반대 방향의 주장을 모두 명시적으로 반박하고, 실제로 구분력 있는 기준(실행과 분리된 명시적 빌드 단계에서 중간 산출물이 나오는가)을 먼저 세운 뒤에 자바를 컴파일 언어로 판정합니다. 둘째, 언어 분류 문제(바이트코드 생성 여부)와 런타임 실행 전략 문제(인터프리터/JIT/AOT)를 서로 다른 레이어로 명확히 분리해, 왜 파이썬은 관례적으로 인터프리터 언어로 분류되고 자바는 컴파일 언어로 분류되는지까지 대조합니다 — 이 대조는 대부분의 튜토리얼에서 생략됩니다. 셋째, 그 위에 심화 레이어로 `Java Virtual Machine Specification` 원문("인터프리터일 필요가 없다"), HotSpot의 5단계 계층형 컴파일, GraalVM Native Image의 AOT 컴파일까지 실제 실행 전략을 근거와 함께 다룹니다.

## 본문

<!--
게시 게이트(src/core/publish_gate.json::sectionMinWords) 기준 최소 800단어.
-->

### 1. "결국 다 기계어니까 컴파일"과 "실행 중 인터프리터도 쓰니 인터프리터"는 왜 둘 다 틀린 기준인가

"컴파일 vs 인터프리터"를 나누려 할 때 가장 흔히 빠지는 함정은 "어차피 CPU는 0과 1로 된 기계어만 실행하니까, 결국 모든 프로그램은 기계어로 변환되어 실행되는 것 아니냐 — 그럼 다 컴파일 아니냐"는 논리입니다. 이 논리는 사실관계는 맞지만(모든 프로그램은 최종적으로 CPU 명령어로 실행됩니다) 분류 기준으로는 틀렸습니다. 셸 스크립트를 한 줄씩 읽어 실행하는 배시(bash)도, 초창기 BASIC 인터프리터도 결국 내부적으로는 CPU 명령어를 실행합니다. "결국 기계어가 되는가"를 기준으로 삼으면 예외 없이 모든 프로그램이 컴파일 언어가 되어버려서, 애초에 아무것도 구분하지 못하는 무의미한 기준이 됩니다.

반대 방향의 반론도 마찬가지로 흔합니다. "그래도 실행 환경(JVM)이 바이트코드를 인터프리터로 해석하는 구간이 실제로 있지 않냐 — 그럼 자바도 인터프리터 언어이거나 최소한 하이브리드 아니냐"는 주장입니다. 이 반론은 첫 번째 오류와 뿌리가 같습니다. 핵심은 그 인터프리터가 "무엇을" 해석하느냐입니다. HotSpot의 인터프리터는 자바 소스(`.java`)를 한 줄씩 읽는 게 아니라, `javac`가 실행과 무관하게 이미 만들어 놓은 바이트코드(`.class`)를 해석합니다. 즉 인터프리터가 개입하는 시점은 "실행과 분리된 빌드 단계"가 이미 끝난 다음입니다. 반면 셸 스크립트 같은 진짜 인터프리터 언어는 애초에 그런 독립적 빌드 산출물이 없고, 매 실행마다 소스(또는 그에 준하는 표현)를 처음부터 다시 해석합니다. 그래서 "실행 중에 인터프리터가 쓰이는가"도 언어 분류 기준이 될 수 없습니다 — 이건 뒤에서 별도로 다룰 JVM의 실행 전략(인터프리터/JIT/AOT) 문제일 뿐입니다.

그래서 실제로 구분력이 있는 전통적(레거시) 기준은 "최종적으로 기계어가 되는가"가 아니라, "실행과 분리된 별도의 빌드 단계에서, 소스가 즉시 실행 가능한 중간 산출물(바이트코드 등)로 먼저 번역되는가"입니다. 이 기준으로 보면 C/C++처럼 네이티브 실행 파일을 만드는 언어와, 자바처럼 바이트코드를 만드는 언어는 같은 편(컴파일 언어)에 서고, 인터프리터가 소스(또는 그에 준하는 표현)를 그때그때 읽어 실행하며 배포 가능한 독립 산출물을 남기지 않는 셸 스크립트 같은 언어는 다른 편(인터프리터 언어)에 섭니다.

### 2. javac는 진짜 컴파일러다

자바 소스(`.java`)를 바이트코드(`.class`)로 바꾸는 `javac`는 이름 그대로 컴파일러입니다. 아래는 이 파이프라인을 그대로 보여주는 완전한 예제입니다.

```java
public class Adder {

    public static int add(int a, int b) {
        return a + b;
    }

    public static void main(String[] args) {
        int result = add(3, 4);
        System.out.println("3 + 4 = " + result);
    }
}
```

```bash
javac Adder.java      # 1단계: 소스 -> 바이트코드(Adder.class), 여기가 "컴파일"
java Adder             # 2단계: 바이트코드 -> JVM이 실행
```

`javac Adder.java`를 실행하면 `Adder.class`라는 바이너리가 생성됩니다. 이 시점에서 `add(int, int)`는 아직 x86이나 ARM 명령어가 아니라 JVM 바이트코드로만 존재합니다. `javap -c Adder`로 이 클래스를 역어셈블하면, `add` 메서드 본문은 대략 다음과 같은 명령어 시퀀스로 나타납니다(정확한 오프셋은 컴파일러 버전에 따라 미세하게 달라질 수 있지만, 이 명령어 자체는 `JVM Specification` 6장에 정의된 표준 산술 명령어입니다).

```
iload_0     // 첫 번째 인자(a)를 피연산자 스택에 push
iload_1     // 두 번째 인자(b)를 push
iadd        // 스택 top 두 값을 정수 덧셈
ireturn     // 결과를 반환
```

여기까지가 "컴파일" 단계입니다. 중요한 건 이 단계가 `java Adder`로 실행하는 것과 완전히 분리된, 독립적으로 호출 가능한 빌드 단계라는 점입니다 — `Adder.class`는 소스 없이도 배포·버전관리·재사용할 수 있는 산출물입니다. `Java Language Specification, Java SE 21 Edition` 1장은 이 두 단계를 이렇게 명시적으로 구분합니다.

> "Compile time normally consists of translating programs into a machine-independent byte code representation. Run-time activities include loading and linking of the classes needed to execute a program, optional machine code generation and dynamic optimization of the program, and actual program execution."

### 3. 판정: 이 기준으로는 자바는 컴파일 언어다

앞서 세운 기준(실행과 분리된 빌드 단계에서 중간 산출물을 만드는가)을 그대로 적용하면 답은 명확합니다. 자바는 컴파일 언어입니다. `javac`가 실행 전에 독립적으로 호출되어 `.class` 바이트코드를 만들고, 이 산출물은 원본 소스 없이도 배포·실행할 수 있기 때문입니다. `iload_0`, `iadd` 같은 명령어가 x86/ARM 네이티브 명령어가 아니라는 사실은 이 판정을 바꾸지 않습니다 — 애초에 "네이티브 기계어까지 도달하는가"는 앞서 기각한, 구분력 없는 기준이기 때문입니다.

이 기준이 왜 실질적으로 유의미한지는 파이썬과 비교하면 분명해집니다. CPython도 내부적으로 `.py`를 바이트코드로 컴파일해 `.pyc`로 캐싱합니다. 하지만 이 과정은 `javac`처럼 개발자가 명시적으로 호출하는 별도 빌드 단계가 아니라, 실행 시점에 인터프리터가 알아서 수행하는 부수적 캐싱입니다 — 배포 산출물은 여전히 `.py` 소스 자체이고, `.pyc`만 따로 배포하는 것은 관례가 아닙니다. 반면 자바는 애초에 소스를 배포하지 않고 `.class`/`.jar`만 배포하는 것이 표준 관행입니다. "빌드 산출물이 실행과 분리되어 있고, 그 산출물만으로 배포가 완결되는가"라는 기준으로 보면 자바와 파이썬이 관례적으로 다르게 분류되는 이유가 설명됩니다.

### 4. 여기서 끝이 아니다 — 그 바이트코드를 JVM이 어떻게 실행하는가는 다음 질문

앞 절에서 "자바는 컴파일 언어"라는 판정은 이미 끝났습니다. 하지만 실제로 프로그램을 실행할 때 자바 프로세스 내부에서 무슨 일이 일어나는지, 특히 JVM 메모리 영역이나 실행 성능을 고려해야 하는 시점부터는 또 다른 질문이 남습니다 — `.class` 바이트코드를 JVM이 실제로 어떻게 처리하느냐입니다. 이건 언어 분류 문제가 아니라 순수하게 JVM 구현체의 실행 전략 문제입니다.

### 5. JVM은 인터프리터여야 한다는 규정이 없다

많은 사람이 "바이트코드는 인터프리터로 실행된다"고 단정하지만, `JVM Specification` 자체는 그렇게 요구하지 않습니다. 명세 1장 원문입니다.

> "It is not inherently interpreted, but can just as well be implemented by compiling its instruction set to that of a silicon CPU. It may also be implemented in microcode or directly in silicon."

즉 JVM은 본질적으로 인터프리터가 아니며, 바이트코드 명령어 집합을 실리콘 CPU 명령어로 컴파일해 구현해도 되고, 심지어 마이크로코드나 하드웨어로 직접 구현해도 명세를 위반하지 않습니다. 명세가 규정하는 건 오직 `.class` 파일 포맷과 바이트코드 명령어의 의미(semantics)뿐이고, 그걸 어떻게 실행할지는 순수히 구현체의 선택입니다.

### 6. HotSpot의 실제 답 — 인터프리터와 JIT을 둘 다 쓴다

우리가 `java` 명령으로 실행하는 기본 JVM인 HotSpot은 이 자유도를 활용해 인터프리터와 컴파일러를 동시에 씁니다. 이게 바로 "계층형 컴파일(Tiered Compilation)"입니다. OpenJDK HotSpot 문서 기준으로 실행 레벨은 다음 5단계로 나뉩니다.

| 티어 | 실행 방식 | 특징 |
|---|---|---|
| Tier 0 | 인터프리터 | 프로파일링 정보(호출 횟수, 분기 확률 등)를 수집하며 한 줄씩 실행 |
| Tier 1 | C1 (클라이언트 컴파일러, 프로파일링 없음) | 매우 단순한 메서드를 빠르게 네이티브 코드로 |
| Tier 2 | C1 (호출·백엣지 카운터만) | 가벼운 최적화 |
| Tier 3 | C1 (풀 프로파일링) | Tier 4 승격을 위한 통계 수집까지 포함 |
| Tier 4 | C2 (서버 컴파일러) | 인라이닝, 탈출 분석 등 공격적 최적화로 최고 성능의 네이티브 코드 생성 |

메서드는 처음엔 Tier 0(인터프리터)에서 실행되다가, 호출 횟수가 임계치를 넘으면 C1으로 빠르게 컴파일되고(Tier 3), 그래도 계속 뜨겁게 호출되면 C2가 다시 컴파일해 최고 수준으로 최적화합니다. 반복문 안에서만 뜨거워지는 메서드는 OSR(On-Stack Replacement)로 실행 도중에도 컴파일된 코드로 갈아탈 수 있습니다. 앞서 본 `add(int, int)` 같은 메서드도 프로그램 시작 직후에는 `iload_0`/`iadd` 바이트코드를 인터프리터가 한 줄씩 해석하지만, 반복 호출되면 어느 시점부터는 C1 또는 C2가 만든 네이티브 기계어가 대신 실행됩니다. 즉 같은 메서드가 프로그램 실행 중에 "인터프리트되는 시기"와 "컴파일된 코드로 실행되는 시기"를 모두 거칩니다.

### 7. 실행 전략의 또 다른 선택지 — GraalVM Native Image

같은 자바 소스를 두고, 실행 전략을 인터프리터도 JIT도 아예 쓰지 않는 쪽으로 택할 수도 있습니다. `GraalVM Native Image`는 애플리케이션을 빌드 타임에 통째로 네이티브 실행 파일로 AOT 컴파일합니다. 공식 문서는 이렇게 설명합니다.

> "Native Image is a technology to compile Java code ahead-of-time to a binary—a native executable... This entire process is called build time to clearly distinguish it from the compilation of Java source code to bytecode."

즉 `javac`가 소스를 바이트코드로 컴파일하는 것(이미 끝난 "컴파일 언어" 판정의 근거)과는 별개로, `native-image` 도구가 그 바이트코드(와 도달 가능한 클래스 전체)를 다시 빌드 타임에 완전한 기계어 바이너리로 컴파일합니다. 결과물은 JVM도, 인터프리터도, 런타임 JIT도 필요 없는 단일 실행 파일입니다. 실행 전략만 놓고 보면 이건 전통적인 C/C++ 실행 모델에 가장 가깝지만, 소스 코드도 언어도 여전히 똑같은 자바입니다 — 즉 "컴파일 언어냐"와 "런타임에 인터프리터를 쓰느냐"는 서로 독립적인 질문이라는 걸 보여주는 실제 사례입니다.

### 8. JVM 실행 전략 3원 비교 (언어 분류와는 별개 레이어)

| 실행 모델 | 바이트코드 생성 시점 | 기계어 생성 시점 | 실행 중 재최적화 |
|---|---|---|---|
| 순수 인터프리터 (JVM 사양상 가능, 실무에선 거의 안 씀) | 컴파일 타임 (`javac`) | 매 실행마다 반복 해석, 기계어 없음 | 없음 |
| HotSpot 기본 동작 | 컴파일 타임 (`javac`) | 런타임, 계층형 JIT(C1→C2) | 있음 (OSR, 역최적화) |
| GraalVM Native Image | 컴파일 타임 (`javac`) | 빌드 타임 (`native-image`), 배포 전 완료 | 없음 (실행 시점엔 이미 고정) |

정리하면, 언어 분류 질문("자바는 컴파일 언어인가")과 실행 전략 질문("JVM이 바이트코드를 어떻게 처리하는가")은 층위가 다릅니다. 전자는 `javac`가 실행과 분리된 빌드 단계에서 바이트코드를 만드는 시점에 이미 "컴파일 언어"로 확정되고, 이 표에 있는 세 가지 실행 모델 중 무엇을 쓰든 바뀌지 않습니다. 후자는 JVM 메모리 구조나 실행 성능처럼 더 깊은 런타임 영역을 다룰 때만 추가로 필요한 질문이며, 위 표처럼 순수 인터프리터·계층형 JIT·AOT 중 구현체가 자유롭게 선택할 수 있는 별도의 설계 공간입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| JLS(SE21) §1: 컴파일 타임에 소스가 머신 독립적 바이트코드로 번역되고, 런타임에 선택적 머신코드 생성/동적 최적화가 이뤄진다 | verified | docs.oracle.com의 `Java Language Specification, SE21` §1 원문("Compile time normally consists of translating programs into a machine-independent byte code representation...")과 직접 대조 (확인일: 2026-08-24) |
| JVMS(SE21) §1: JVM은 본질적으로 인터프리터가 아니며, 명령어 집합을 실리콘 CPU 명령어로 컴파일하거나 마이크로코드/하드웨어로 구현해도 무방하다 | verified | docs.oracle.com의 `Java Virtual Machine Specification, SE21` §1 원문("It is not inherently interpreted, but can just as well be implemented by compiling...")과 직접 대조 (확인일: 2026-08-24) |
| HotSpot은 인터프리터(Tier 0)와 C1(Tier 1~3), C2(Tier 4)로 구성된 5단계 계층형 컴파일을 기본으로 사용하며, 뜨거운 메서드가 카운터 임계치를 넘으면 C1/C2 컴파일 코드로 전환된다 | verified | openjdk.org의 HotSpot 공식 문서(HotSpot Glossary of Terms / Tiered Compilation 자료, 도메인: openjdk.org)와 대조 (확인일: 2026-08-24) |
| GraalVM Native Image는 자바 코드를 빌드 타임에 AOT 컴파일해 별도 JVM 인터프리터/JIT 없이 실행되는 독립 네이티브 바이너리를 생성한다 | verified | docs.oracle.com의 `GraalVM Native Image Reference Manual` 원문("Native Image is a technology to compile Java code ahead-of-time to a binary—a native executable...")과 직접 대조 (확인일: 2026-08-24) |
| `static int add(int a, int b) { return a + b; }` 형태의 단순 정수 덧셈 메서드는 `iload`/`iadd`/`ireturn` 계열 바이트코드 명령어로 컴파일된다 | verified | docs.oracle.com의 `JVM Specification` 6장(Java Virtual Machine 명령어 집합)에 정의된 `iload_n`, `iadd`, `ireturn` 명령어 시맨틱스와 대조 — 실제 바이트 오프셋은 컴파일러 버전마다 달라질 수 있어 본문에도 이 점을 명시함 (확인일: 2026-08-24) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

개인적으로 "자바는 컴파일도 되고 인터프리트도 된다"는 절충형 답변이 오히려 정확한 이해를 방해한다고 생각합니다. 제 견해로는 "결국 다 기계어로 실행되니 전부 컴파일 아니냐"는 논리가 왜 틀렸는지부터 짚어야, 그 반작용으로 "그럼 뭘 기준으로 삼아야 하나"라는 진짜 질문에 도달할 수 있습니다. 기준을 "실행 결과"가 아니라 "실행 전에 무엇이 만들어지는가"로 옮기면, 자바가 컴파일 언어라는 결론은 흔들릴 이유가 없습니다 — `javac`는 실행과 분리된 빌드 단계이고 그 산출물만으로 배포가 완결되기 때문입니다. 흥미로운 지점은 이 판정과 JVM 내부의 실행 전략이 전혀 충돌하지 않는다는 사실입니다. JVM 명세가 "인터프리터일 필요가 없다"고 명시적으로 열어둔 이유도, 애초에 실행 전략은 언어 분류와 무관한 구현 디테일이기 때문이라고 봅니다. 만약 실행 전략이 언어 분류를 좌우한다면, 같은 자바 소스가 HotSpot에서 실행되느냐 GraalVM Native Image로 빌드되느냐에 따라 "자바가 컴파일 언어였다가 아니었다가" 왔다 갔다 해야 하는데, 이는 직관적으로도 이상합니다. 그래서 저는 "자바는 컴파일 언어다, 다만 그 바이트코드를 JVM이 실행하는 방식은 구현체마다 다르다"는 2단 구조로 나눠 이해하는 쪽이 훨씬 덜 헷갈린다고 생각합니다.

## 한계와 반론

이 글이 세운 "실행과 분리된 빌드 단계에서 중간 산출물이 나오는가"라는 기준에도 몇 가지 한계가 있습니다. 첫째, 이 기준 자체가 완벽하게 엄밀한 정의는 아닙니다 — CPython도 `.pyc` 캐싱이라는 형태로 바이트코드를 만들며, "명시적 빌드 단계냐 부수적 캐싱이냐"의 경계가 항상 깔끔하게 나뉘는 것은 아닙니다. 이 글은 이 기준이 "왜 통념상 자바=컴파일, 파이썬=인터프리터로 갈리는가"를 설명하는 실용적 도구로 제시한 것이지, 모든 언어에 예외 없이 적용되는 형식적 정의로 제시한 것은 아닙니다. 둘째, "자바는 컴파일 언어"라는 판정이 끝났다고 해서 JVM 실행 전략에 대한 이해가 불필요해지는 건 아닙니다 — 성능 튜닝, GC 튜닝, 시작 속도가 중요한 배포 환경(컨테이너, 서버리스)을 고려해야 하는 순간부터는 이 글 후반부에서 다룬 인터프리터/JIT/AOT 레이어를 반드시 별도로 이해해야 합니다. 셋째, 이 특성은 자바만의 고유한 것이 아닙니다. 코틀린, 스칼라, 클로저 등 JVM 위에서 동작하는 언어들도 동일한 바이트코드-JVM 파이프라인을 공유하므로 여기서 설명한 내용이 거의 그대로 적용됩니다. 넷째, GraalVM Native Image도 완전히 "순수한" AOT는 아닙니다 — `native-image` 빌드 도구 자체는 내부적으로 Graal 컴파일러(JIT 인프라에서 파생된 컴파일러)를 빌드 타임에 실행해 기계어를 생성하므로, JIT 관련 기술이 런타임이 아니라 빌드 타임으로 옮겨간 것에 더 가깝습니다. Native Image도 선택적으로 런타임 프로파일 기반 최적화(PGO)를 함께 쓰는 구성을 지원하므로, 실행 전략 비교표의 "실행 중 재최적화 없음"은 기본 구성 기준입니다.

## 참고문헌

1. [Java Virtual Machine Specification, Java SE 21 Edition, Chapter 1 (Introduction)](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-1.html) (확인일: 2026-08-24)
2. [Java Language Specification, Java SE 21 Edition, Chapter 1 (Introduction)](https://docs.oracle.com/javase/specs/jls/se21/html/jls-1.html) (확인일: 2026-08-24)
3. [GraalVM Native Image Reference Manual, Oracle GraalVM for JDK 25](https://docs.oracle.com/en/graalvm/jdk/25/docs/reference-manual/native-image/) (확인일: 2026-08-24)
4. [HotSpot Glossary of Terms / Tiered Compilation](https://openjdk.org/groups/hotspot/docs/HotSpotGlossary.html) (확인일: 2026-08-24)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

이 글을 종합하면 결론은 두 층으로 나뉩니다. 실용적/레거시 기준(실행과 분리된 빌드 단계에서 중간 산출물이 나오는가)으로는 자바는 명확히 컴파일 언어입니다 — "결국 다 기계어가 되니 전부 컴파일"이라는 구분력 없는 기준으로 이 판정을 흐릴 필요는 없다고 봅니다. 이 1차 판정은 JVM이 그 바이트코드를 이후 어떻게 처리하는지와 무관하게 성립하며, `Java Language Specification`의 컴파일 타임/런타임 구분이 이를 뒷받침합니다. 다만 여기서 끝나지 않고 JVM 메모리 영역이나 실행 성능처럼 더 깊은 층위를 고려해야 하는 순간에는, "자바 언어가 컴파일 언어인가"와는 별개로 "지금 이 바이트코드를 JVM 구현체가 인터프리터·계층형 JIT·AOT 중 무엇으로 실행하는가"라는 2차 질문을 새로 던져야 합니다. 예를 들어 짧게 실행되고 종료되는 CLI 도구나 서버리스 함수처럼 시작 속도가 중요한 워크로드에는 GraalVM Native Image의 AOT 모델이, 오래 실행되며 처리량이 중요한 백엔드 서비스에는 HotSpot의 계층형 JIT이 각각 더 유리한 트레이드오프를 제공합니다. 요약하면 "자바는 컴파일 언어"는 확정된 답이고, "이 실행 환경에서 JVM이 어떤 전략을 쓰는가"는 상황에 따라 달라지는 별개의 질문이라는 것이 이 글의 결론입니다.

## 꼬리질문

- HotSpot의 계층형 컴파일에서 메서드가 Tier 3(C1 풀 프로파일링)에서 Tier 4(C2)로 승격되는 정확한 호출 횟수 임계값은 얼마이며, `-XX:CompileThreshold`나 `-XX:Tier4CompileThreshold` 같은 JVM 옵션으로 이를 어떻게 튜닝할 수 있는가?
- GraalVM Native Image가 지원하는 PGO(Profile-Guided Optimization) 구성은 HotSpot의 런타임 프로파일링과 실제로 얼마나 다른 성능 특성을 보이는가?
- 안드로이드의 ART(Android Runtime)는 이 글에서 다룬 인터프리터/JIT/AOT 3원 모델 중 어디에 해당하며, 자바 바이트코드 대신 자체 DEX 포맷을 쓰는 것이 실행 전략 선택에 어떤 제약을 추가하는가?

## 백링크

- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)
- [Java ClassLoader — 클래스 로딩 과정과 계층 구조(Bootstrap/Platform/App)](https://beji-tech.blogspot.com/2026/08/java-classloader-bootstrapplatformapp.html)
- [Java 제네릭(Generics) — 타입 소거(Type Erasure)와 와일드카드(? extends/? super)](https://beji-tech.blogspot.com/2026/08/java-generics-type-erasure-extends-super.html)