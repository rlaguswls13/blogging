---
author: ''
createdAt: '2026-08-26T02:19:20.115169Z'
factCheckScore: 0
id: '8856394201745901458'
notionPageId: null
publishedAt: '2026-08-25T22:45:04-07:00'
slug: jvm-jit-tiered-compilation-c1-c2-deoptimization
status: published
tags:
- Advanced
- Java
- JVM
title: JVM JIT 티어드 컴파일 — C1/C2 컴파일러와 역최적화(Deoptimization)가 실행 성능을 바꾸는 원리
updatedAt: '2026-08-26T02:19:20.115169Z'
url: https://beji-tech.blogspot.com/2026/08/jvm-jit-c1c2-deoptimization.html
---

# JVM JIT 티어드 컴파일 — C1/C2 컴파일러와 역최적화(Deoptimization)가 실행 성능을 바꾸는 원리

## 요약

HotSpot JVM은 메서드 하나를 실행하는 동안에도 인터프리터, C1(클라이언트 컴파일러), C2(서버 컴파일러)라는 서로 다른 세 실행 엔진을 5단계 티어(0~4)로 오갑니다. C1은 빠르게 컴파일하되 최적화 수준이 낮고, C2는 느리게 컴파일하되 인라이닝·탈출 분석 같은 공격적 최적화를 수행합니다. 그런데 C2가 만든 네이티브 코드는 "이 호출 지점은 항상 같은 타입만 온다"처럼 실행 중 관찰한 프로파일을 근거로 한 추측(speculation) 위에 지어진 경우가 많고, 그 추측이 깨지면 JVM은 그 코드를 즉시 무효화하고 인터프리터로 되돌아가는 역최적화(Deoptimization)를 수행합니다. 이 글은 이 메커니즘을 실제로 JDK 23.0.1에서 `-XX:+PrintCompilation`과 `-XX:+TraceDeoptimization`으로 직접 재현한 로그와 함께 다루고, 이것이 왜 JMH 같은 도구 없이 즉석에서 잰 벤치마크를 신뢰할 수 없게 만드는지도 설명합니다.

## 차별화 포인트

이 주제의 상위 검색결과 대부분은 "인터프리터로 시작해서 자주 호출되면 JIT이 컴파일한다"는 한 문장과 계층형 컴파일 5단계 표 하나로 끝난다. 이 글은 세 가지 지점에서 더 나아간다. 첫째, 이 글은 실제로 JDK 23.0.1(OpenJDK 64-Bit Server VM, build 23.0.1+11-39)에서 인터페이스 기반 단형(monomorphic) 호출 지점을 C1→C2로 컴파일시킨 뒤, 두 번째 구현 클래스를 투입해 C2가 만든 네이티브 코드가 `reason=class_check`의 uncommon trap으로 실제로 "made not entrant" 처리되고 재컴파일되는 전 과정을 `-XX:+PrintCompilation`/`-XX:+TraceDeoptimization` 원본 로그로 보여준다 — 교과서적 설명이 아니라 직접 실행해 얻은 실측 로그다. 둘째, HotSpot 소스코드(`compilerDefinitions.hpp`, `deoptimization.hpp`)를 직접 열어 5단계 CompLevel enum의 정확한 주석과 DeoptReason/DeoptAction 분류 체계를 원문 그대로 인용한다. 셋째, "정상 동작처럼 보이는데 초반 몇 초만 측정해 결론을 내리는" 워밍업 벤치마킹 함정을 C1/C2 전환 타임라인과 직접 연결해 설명한다.

## 본문

### 1. 왜 인터프리터 하나로 충분하지 않은가

JVM이 바이트코드를 실행하는 가장 단순한 방법은 인터프리터로 한 줄씩 해석하는 것입니다. 하지만 인터프리터는 매번 바이트코드 명령어를 디스패치하는 오버헤드가 크기 때문에, 반복적으로 실행되는 "뜨거운(hot)" 메서드에는 네이티브 기계어로 미리 컴파일해두는 쪽이 훨씬 빠릅니다. 문제는 프로그램 시작 직후에는 어떤 메서드가 뜨거워질지 미리 알 수 없고, 모든 메서드를 처음부터 최고 수준으로 컴파일하려면 컴파일 자체에 시간이 오래 걸려 오히려 시작 속도가 느려진다는 점입니다. HotSpot은 이 딜레마를 인터프리터와 두 개의 서로 다른 JIT 컴파일러를 함께 쓰는 계층형 컴파일(Tiered Compilation)로 해결합니다. Oracle 공식 문서는 이 배경을 다음과 같이 설명합니다.

> "Tiered compilation, introduced in Java SE 7, brings client startup speeds to the server VM. Normally, a server VM uses the interpreter to collect profiling information about methods that is fed into the compiler. In the tiered scheme, in addition to the interpreter, the client compiler is used to generate compiled versions of methods that collect profiling information about themselves."

즉 서버 VM이 인터프리터만으로 프로파일을 모으는 대신, 클라이언트 컴파일러(C1)로 일단 빠르게 컴파일해서 그 컴파일된 코드가 스스로 프로파일 정보까지 함께 수집하게 만들면, 인터프리터보다 훨씬 빠른 속도로 실행되면서 동시에 프로파일도 쌓입니다. 이 프로파일이 충분히 쌓이면 서버 컴파일러(C2)가 최종적으로 최고 수준의 최적화 코드를 만듭니다.

### 2. 5단계 티어의 정확한 정의 — HotSpot 소스코드 원문

"C1과 C2를 섞어 쓴다"는 설명만으로는 실제 동작을 예측하기 어렵습니다. HotSpot이 내부적으로 구분하는 컴파일 레벨은 정확히 5단계이며, 이는 OpenJDK 공식 저장소의 `src/hotspot/share/compiler/compilerDefinitions.hpp` 파일에 `CompLevel` 열거형으로 명시되어 있습니다. 각 값에 달린 주석을 그대로 옮기면 다음과 같습니다.

| 레벨 | HotSpot 소스 주석 | 실행 엔진 | 의미 |
|---|---|---|---|
| 0 | `Interpreter` | 인터프리터 | 프로파일링 정보(호출 횟수, 분기 확률 등)를 모으며 한 줄씩 실행 |
| 1 | `C1` | C1 | 프로파일링 없이 빠르게 네이티브 코드 생성 (매우 단순한 메서드용) |
| 2 | `C1, invocation & backedge counters` | C1 | 호출·백엣지 카운터만 수집하는 가벼운 프로파일링 |
| 3 | `C1, invocation & backedge counters + mdo` | C1 | MDO(MethodData 객체) 기반 풀 프로파일링까지 포함 |
| 4 | `C2` | C2 | 인라이닝·탈출 분석 등 공격적 최적화로 최고 성능 코드 생성 |

메서드는 보통 레벨 0(인터프리터)에서 시작해 레벨 3(C1 풀 프로파일링)으로 빠르게 컴파일된 뒤, 레벨 3에서 쌓인 프로파일이 충분해지면 레벨 4(C2)로 다시 컴파일됩니다. 레벨 1과 2는 "메서드가 너무 단순해서 프로파일링이 무의미하거나(레벨 1)", "C2 컴파일 큐가 밀려 있어 일단 가벼운 프로파일링만 하며 버티는 경우(레벨 2)"처럼 특수한 상황에 쓰이는 경로입니다. 반복문 안에서만 뜨거워지는 메서드는 메서드 전체가 아니라 실행 중인 루프 자체가 On-Stack Replacement(OSR)로 컴파일된 코드로 교체될 수 있습니다.

### 3. 직접 재현한 컴파일→역최적화 전 과정

이론만으로는 "레벨 4까지 갔다가 역최적화된다"는 말이 추상적으로 느껴집니다. 실제로 어떤 상황에서 이런 일이 벌어지는지 직접 실행해 확인했습니다. 인터페이스 타입의 한 호출 지점에 처음에는 구현체 하나(`Circle`)만 반복적으로 흘려보내고, 워밍업이 끝난 뒤에 두 번째 구현체(`Square`)를 투입하는 예제입니다.

```java
public class DeoptDemo {
    interface Shape { double area(); }

    static class Circle implements Shape {
        double r;
        Circle(double r) { this.r = r; }
        public double area() { return Math.PI * r * r; }
    }

    static class Square implements Shape {
        double s;
        Square(double s) { this.s = s; }
        public double area() { return s * s; }
    }

    // 이 호출 지점(sh.area())이 핵심 관찰 대상이다.
    static double compute(Shape sh) {
        return sh.area();
    }

    public static void main(String[] args) {
        Circle c = new Circle(2.0);
        double sum = 0;
        // 1단계: 30만 회 동안 오직 Circle만 흘려보낸다 — 단형(monomorphic) 호출 지점.
        // C2는 "이 호출 지점의 수신자는 항상 Circle"이라는 프로파일을 근거로
        // area() 호출을 직접 인라이닝하도록 투기적으로(speculatively) 최적화할 수 있다.
        for (int i = 0; i < 300_000; i++) {
            sum += compute(c);
        }
        System.out.println("warm sum=" + sum);

        // 2단계: 같은 호출 지점에 Square를 함께 투입한다.
        // 단형 가정이 깨지므로 기존 C2 코드의 인라이닝 speculation이 무효화될 수 있다.
        Square sq = new Square(3.0);
        for (int i = 0; i < 300_000; i++) {
            sum += compute(sq);
            sum += compute(c);
        }
        System.out.println("final sum=" + sum);
    }
}
```

JDK 23.0.1(OpenJDK 64-Bit Server VM, build 23.0.1+11-39)에서 `java -XX:+PrintCompilation -XX:+UnlockDiagnosticVMOptions -XX:+TraceDeoptimization DeoptDemo`로 실행하고 `compute`/`UNCOMMON TRAP` 관련 줄만 골라낸 실제 출력은 다음과 같습니다(밀리초 타임스탬프와 컴파일 작업 ID는 실행 환경에 따라 달라질 수 있으므로, 절대값이 아니라 순서와 전이 패턴에 주목해야 합니다).

```text
   61   72       3       DeoptDemo::compute (7 bytes)
   61   74       4       DeoptDemo::compute (7 bytes)
   62   72       3       DeoptDemo::compute (7 bytes)   made not entrant
   ... (1단계: Circle만 흘려보낸 구간, 레벨3 -> 레벨4로 정상 승격)

UNCOMMON TRAP method=DeoptDemo.compute(LDeoptDemo$Shape;)D  bci=1
  pc=0x000002bbdae74d7c, compiler=c2 compile_id=74
  thread=68256 reason=class_check action=maybe_recompile unloaded_class_index=-1
   ... (2단계: Square 투입 직후 발생 — 레벨4(C2) 코드가 실제로 트랩에 걸림)

   84   74       4       DeoptDemo::compute (7 bytes)   made not entrant
   84  160       4       DeoptDemo::compute (7 bytes)
```

이 로그가 보여주는 순서는 명확합니다. 컴파일 ID 72(레벨 3, C1)가 먼저 나오고, 곧이어 컴파일 ID 74(레벨 4, C2)가 같은 메서드를 다시 컴파일하며, 레벨 3 버전은 "made not entrant"로 표시되어 더 이상 새 호출이 그 코드로 들어가지 않습니다(정상적인 티어 승격입니다). 여기까지는 역최적화가 아니라 그냥 상위 티어로의 전환입니다. 진짜 역최적화는 `Square`를 투입한 직후에 나타납니다 — `UNCOMMON TRAP` 줄이 `reason=class_check`와 함께 컴파일 ID 74(방금 만들어진 C2 코드)를 정확히 지목하고, 곧이어 같은 컴파일 ID 74가 다시 한번 "made not entrant"로 표시됩니다. C2가 단형 호출 지점이라는 가정 위에 지었던 최적화 코드가, 그 가정이 깨지는 순간 통째로 무효화된 것입니다. 그 직후 컴파일 ID 160으로 레벨 4 재컴파일이 다시 일어나는데, 이번에는 두 타입을 모두 감안한(더는 단형이라는 가정을 걸지 않는) 코드로 다시 만들어집니다.

### 4. 역최적화는 왜 필요한가 — 추측 최적화의 대가

C2가 왜 굳이 "항상 이 타입일 것"이라는 위험한 가정을 걸까요? 그래야 인터페이스 메서드 호출처럼 원래는 가상 디스패치(virtual dispatch)가 필요한 코드를, 마치 정적으로 타입이 확정된 것처럼 인라이닝하고 그 위에서 추가 최적화(불필요한 null 체크 제거, 상수 전파 등)를 걸 수 있기 때문입니다. 이런 낙관적 최적화 없이는 C2가 만드는 코드도 인터프리터보다 조금 빠른 수준에 머물렀을 것입니다. 대신 그 가정이 실제로 깨지면 JVM은 안전하게 되돌아갈 수 있어야 하는데, 이 되돌리기 메커니즘이 역최적화입니다. HotSpot 소스코드의 `src/hotspot/share/runtime/deoptimization.hpp`는 역최적화의 원인을 `DeoptReason` 열거형으로, 그에 따른 처리 방식을 `DeoptAction` 열거형으로 구분해 관리합니다 — `class_check`(방금 재현한 타입 가정 실패), `null_check`, `range_check` 등이 대표적인 `DeoptReason` 값입니다. 이렇게 원인을 세분화해두는 이유는 원인마다 대응이 다르기 때문입니다. 예를 들어 이번 실험처럼 `action=maybe_recompile`이면 JVM은 무효화된 코드를 버리고 새로 얻은 프로파일(이제 타입이 둘이라는 사실)을 반영해 즉시 재컴파일을 시도합니다. 만약 같은 지점에서 역최적화가 반복적으로 발생하면 JVM은 그 지점을 아예 컴파일 대상에서 영구 제외하는 더 강한 조치를 취하기도 합니다.

### 5. 워밍업과 벤치마킹 함정

이 전이 과정이 실무에 주는 함의는 명확합니다. 방금 본 예제에서 `compute`가 "제대로 최적화된" 코드로 안정화되기까지 실제로 세 번의 컴파일(레벨 3 → 레벨 4 → 역최적화 후 레벨 4 재컴파일)을 거쳤습니다. 만약 어떤 벤치마크 코드가 애플리케이션 시작 직후 몇 초, 혹은 이런 재컴파일이 끝나기 전 구간을 "실행 성능"으로 측정한다면, 그 수치는 JVM이 아직 프로파일을 모으고 있거나 방금 역최적화를 겪은 과도기 상태를 잰 것이지 실제 정상 상태(steady state) 성능이 아닙니다. 특히 다형성(polymorphism)이 섞인 실전 코드에서는 이런 컴파일→역최적화→재컴파일 사이클이 애플리케이션 초반에 여러 차례 겹쳐 일어날 수 있어, 초반 구간만 측정하면 실제보다 훨씬 느린(혹은 들쭉날쭉한) 수치를 "진짜 성능"으로 오인하기 쉽습니다. JMH 같은 전용 마이크로벤치마킹 도구가 별도의 워밍업 반복(`@Warmup`)을 강제하는 근본 이유도 여기에 있습니다 — 측정 구간을 티어 전환과 역최적화가 어느 정도 가라앉은 이후로 밀어내기 위해서입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| HotSpot의 계층형 컴파일은 정확히 5단계(레벨 0~4)로 구성되며, 레벨 0은 인터프리터, 레벨 1~3은 C1(각기 다른 프로파일링 수준), 레벨 4는 C2다 | verified | OpenJDK 공식 저장소 `src/hotspot/share/compiler/compilerDefinitions.hpp`의 `CompLevel` 열거형 주석("Interpreter", "C1", "C1, invocation & backedge counters", "C1, invocation & backedge counters + mdo", "C2") 원문과 직접 대조. https://github.com/openjdk/jdk/blob/master/src/hotspot/share/compiler/compilerDefinitions.hpp (확인일: 2026-08-26) |
| Java SE 7에서 도입된 티어드 컴파일은, 서버 VM이 인터프리터만으로 프로파일을 모으는 대신 클라이언트 컴파일러(C1에 해당)로 컴파일된 코드가 스스로 프로파일링 정보를 함께 수집하게 해, 서버 VM에서도 클라이언트 VM 수준의 시작 속도를 낼 수 있게 한다 | verified | Oracle 공식 문서 원문("Tiered compilation, introduced in Java SE 7, brings client startup speeds to the server VM... the client compiler is used to generate compiled versions of methods that collect profiling information about themselves.")과 직접 대조. https://docs.oracle.com/javase/7/docs/technotes/guides/vm/performance-enhancements-7.html (확인일: 2026-08-26) |
| 티어드 컴파일이 활성화되면 프로파일링 코드 증가에 대응해 코드 캐시 기본 크기가 5배로 늘어나며, non-method/profiled/non-profiled 3개 세그먼트로 나뉘어 관리된다 | verified | Oracle 공식 문서 원문("To accommodate the additional profiling code that is generated with tiered compilation, the default size of code cache is multiplied by 5x... the code cache is divided into segments")과 직접 대조. https://docs.oracle.com/en/java/javase/21/vm/java-hotspot-virtual-machine-performance-enhancements.html (확인일: 2026-08-26) |
| `jstat -printcompilation`이 출력하는 클래스명/메서드명 필드 형식은 HotSpot의 `-XX:+PrintCompilation` 옵션 출력과 일치하도록 공식 문서에 명시되어 있다 | verified | Oracle 공식 `jstat` 매뉴얼 원문("The format for these two fields is consistent with the HotSpot -XX:+PrintCompilation option.")과 직접 대조. https://docs.oracle.com/en/java/javase/19/docs/specs/man/jstat.html (확인일: 2026-08-26) |
| HotSpot 소스코드는 역최적화의 원인을 `DeoptReason`(예: class_check, null_check, range_check 등) 열거형으로, 처리 방식을 `DeoptAction` 열거형으로 구분해 관리한다 | verified | OpenJDK 공식 저장소 `src/hotspot/share/runtime/deoptimization.hpp`의 `DeoptReason`/`DeoptAction` 열거형 정의 원문과 직접 대조. https://github.com/openjdk/jdk/blob/master/src/hotspot/share/runtime/deoptimization.hpp (확인일: 2026-08-26) |
| JDK 23.0.1에서 인터페이스 기반 단형 호출 지점을 C1(레벨3)→C2(레벨4)로 컴파일시킨 뒤 두 번째 구현 클래스를 투입하면, `reason=class_check`의 uncommon trap이 발생해 해당 C2 컴파일 코드가 "made not entrant"로 무효화되고 재컴파일된다 | verified | 본인이 JDK 23.0.1(OpenJDK 64-Bit Server VM, build 23.0.1+11-39)에서 `-XX:+PrintCompilation -XX:+UnlockDiagnosticVMOptions -XX:+TraceDeoptimization` 플래그로 위 `DeoptDemo` 예제를 직접 컴파일·실행해 확인한 실측 로그(본문 3절 코드블록 원문). |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

개인적으로 계층형 컴파일을 "빠른 컴파일러(C1)와 느린 컴파일러(C2)를 섞어 쓴다"는 한 문장으로 요약하는 설명에는 정보가 절반쯤 빠져 있다고 생각합니다. 진짜 핵심은 C2가 만드는 코드가 확정된 사실이 아니라 프로파일 기반의 "추측"이라는 점이고, 역최적화는 그 추측이 틀렸을 때를 대비한 안전장치라는 점입니다. 이번에 직접 로그를 재현해 보면서 인상 깊었던 지점은, 역최적화가 예외적인 오류 상황이 아니라 JVM이 설계상 정상적으로 반복하는 사이클이라는 사실이었습니다. `class_check` 트랩이 발생한 순간 프로그램이 느려지거나 멈춘 게 아니라, JVM은 그저 무효화된 코드를 버리고 더 정확해진 프로파일로 다시 컴파일했을 뿐입니다. 저는 이 지점이 실무에서 가장 자주 오해되는 부분이라고 봅니다. 개발자들이 "왜 우리 서비스는 배포 직후 몇 분 동안 유독 느리다가 안정화되는가"를 물을 때, 그 답의 상당 부분이 GC나 캐시 워밍업이 아니라 바로 이 계층형 컴파일과 역최적화 사이클 자체에 있을 수 있는데도, 이 설명은 GC 튜닝 논의에 비해 훨씬 덜 다뤄진다고 느낍니다. 그런 의미에서 이 메커니즘을 "예외적 실패"가 아니라 "JVM의 기본 운영 방식"으로 재해석하는 것이 실행 성능을 이해하는 더 정확한 사견이라고 생각합니다.

## 한계와 반론

이 글의 실험은 단일 JDK 빌드(JDK 23.0.1, Windows, 기본 플래그 조합)에서 한 번 재현한 결과이며, JVM 버전이나 OS, JIT 컴파일 큐 상태, 동시 실행 중인 다른 워크로드에 따라 정확히 같은 컴파일 ID나 타이밍이 재현된다는 보장은 없습니다. 본문에서도 밝혔듯 절대적인 밀리초 타임스탬프와 컴파일 작업 ID보다는 "티어 전환 -> uncommon trap -> made not entrant -> 재컴파일"이라는 전이 패턴 자체에 주목해야 합니다. 또한 이 글이 재현한 역최적화 원인은 `class_check` 한 가지뿐이며, `null_check`나 `range_check`, 분기 프로파일이 틀렸을 때 발생하는 `unstable_if` 계열 등 다른 `DeoptReason`들은 별도로 재현하지 않았습니다. 레벨 1(C1, 프로파일링 없음)과 레벨 2(C1, 카운터만)로 가는 경로는 이번 실험에서 자연스럽게 관찰되지 않았는데, 이는 컴파일 큐가 밀리지 않은 단순한 로컬 환경이었기 때문으로 추정됩니다. 마지막으로 "워밍업 구간을 측정하면 성능을 오인한다"는 5절의 주장은 이 글이 관찰한 컴파일 타임라인에 근거한 논리적 추론이며, 실제로 워밍업 구간과 안정화 이후 구간의 처리량(throughput)을 정량적으로 비교 측정하지는 않았습니다.

## 참고문헌

1. OpenJDK, "compilerDefinitions.hpp — CompLevel enum (HotSpot 소스코드)", https://github.com/openjdk/jdk/blob/master/src/hotspot/share/compiler/compilerDefinitions.hpp (확인일: 2026-08-26)
2. OpenJDK, "deoptimization.hpp — DeoptReason/DeoptAction 열거형 (HotSpot 소스코드)", https://github.com/openjdk/jdk/blob/master/src/hotspot/share/runtime/deoptimization.hpp (확인일: 2026-08-26)
3. Oracle, "Java™ HotSpot Virtual Machine Performance Enhancements — Tiered Compilation" (Java SE 7), https://docs.oracle.com/javase/7/docs/technotes/guides/vm/performance-enhancements-7.html (확인일: 2026-08-26)
4. Oracle, "Java HotSpot Virtual Machine Performance Enhancements — Tiered Compilation / Segmented Code Cache" (JDK 21), https://docs.oracle.com/en/java/javase/21/vm/java-hotspot-virtual-machine-performance-enhancements.html (확인일: 2026-08-26)
5. Oracle, "The jstat Command — -printcompilation Output" (JDK 19), https://docs.oracle.com/en/java/javase/19/docs/specs/man/jstat.html (확인일: 2026-08-26)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

이 글을 종합하면, 계층형 컴파일과 역최적화는 서로 반대편이 아니라 하나의 설계 안에서 짝을 이루는 두 장치라는 결론에 이릅니다. C1의 빠른 컴파일과 프로파일 수집이 없다면 C2는 애초에 무엇을 근거로 인라이닝이나 탈출 분석 같은 공격적 최적화를 걸어야 할지 알 수 없고, 역최적화라는 안전한 되돌리기 장치가 없다면 C2는 그런 위험한 추측 최적화를 걸 엄두조차 내지 못했을 것입니다. 즉 역최적화는 JIT 컴파일러가 실패했다는 신호가 아니라, 오히려 JIT 컴파일러가 더 공격적으로 최적화할 수 있도록 뒤에서 받쳐주는 보험 장치에 가깝습니다. 이번에 직접 재현한 실험에서 `class_check` 하나로도 실제 nmethod가 통째로 무효화되고 재컴파일되는 전 과정을 눈으로 확인할 수 있었는데, 이 관찰은 성능 튜닝을 고민할 때 "이 메서드가 컴파일됐는가"만이 아니라 "이 호출 지점이 다형적으로 쓰이고 있어서 역최적화 사이클을 반복하고 있지는 않은가"까지 함께 살펴야 한다는 실무적 시사점으로 이어집니다. 특히 인터페이스나 추상 클래스를 통해 여러 구현체를 다형적으로 다루는 코드, 혹은 의존성 주입으로 런타임에 구현체가 바뀌는 코드에서는 이런 재컴파일 사이클이 반복될 가능성이 이론상 더 높습니다. 벤치마크를 설계하거나 배포 직후 성능 그래프를 해석할 때, GC 로그만이 아니라 이 계층형 컴파일·역최적화의 관점도 함께 고려하는 것이 실행 성능을 정확히 이해하는 데 필요하다고 봅니다.

## 꼬리질문

1. C1의 세 하위 레벨(1~3) 사이 전환을 실제로 결정하는 `-XX:Tier3InvocationThreshold`, `-XX:Tier4CompileThreshold` 같은 구체적 카운터 임계값의 JDK 버전별 기본값은 얼마이며, `-XX:+PrintFlagsFinal`로 확인했을 때 실제 운영 JDK에서는 어떤 값이 적용되고 있는가?
2. 이 글이 재현한 `class_check` 외에 `null_check`, `range_check`, `unstable_if` 같은 다른 `DeoptReason`은 각각 어떤 코드 패턴에서 유발되며, 그 각각이 재컴파일 이후에도 반복적으로 재발할 경우 JVM이 해당 지점을 영구히 컴파일 제외 대상으로 처리하는 구체적 조건은 무엇인가?

## 백링크

- [자바는 컴파일 언어인가, 인터프리터 언어인가 — 바이트코드 기준으로 정리](https://beji-tech.blogspot.com/2026/08/blog-post.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)
- [Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전](https://beji-tech.blogspot.com/2026/08/java-g1gc-gc.html)