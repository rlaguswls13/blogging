---
author: ''
createdAt: '2026-08-22T18:33:07.546401Z'
factCheckScore: 1.0
id: '7376604336147062720'
notionPageId: null
publishedAt: '2026-08-22T16:19:12-07:00'
slug: java-generics-type-erasure-wildcard-pecs
status: published
tags:
- Basics
- Java
- Generics
title: Java 제네릭(Generics) — 타입 소거(Type Erasure)와 와일드카드(? extends/? super)
updatedAt: '2026-08-22T18:33:07.546401Z'
url: https://beji-tech.blogspot.com/2026/08/java-generics-type-erasure-extends-super.html
---

# Java 제네릭(Generics) — 타입 소거(Type Erasure)와 와일드카드(? extends/? super)

## 요약

Java 제네릭은 컴파일 시점에만 존재하고 런타임에는 `타입 소거(Type Erasure)`로 지워진다. 이 글은 "타입 소거란 무엇인가"를 정의로만 설명하지 않고, 타입 소거 때문에 실제로 벌어지는 3가지 제약 — `new T[]` 배열 생성 금지, 제네릭 타입만 다른 메서드 오버로드 금지, PECS(Producer Extends, Consumer Super) 원칙을 어긴 와일드카드 사용 — 을 로컬 JDK로 직접 컴파일해 재현하고, 실제 `javac` 오류 메시지를 그대로 보여준다. 이어서 각 문제의 원인을 Oracle 공식 문서 및 JLS(Java Language Specification) 원문과 대조해 설명하고, PECS를 어긴 코드를 실제로 고쳐 정상 실행되는 것까지 확인한다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
-->

동일 주제의 상위 검색 결과 대다수는 "타입 소거란 컴파일 후 제네릭 타입 정보가 사라지는 것"이라는 정의와, `new T[]`가 안 된다는 서술만 텍스트로 나열하고 끝난다. 이 글은 그 서술을 실제로 검증한다 — OpenJDK 21.0.2(javac 21.0.2, GraalVM CE 21.0.2+13.1) 로컬 환경에서 (1) `T[] arr = new T[10]`과 `List<String>[] lists = new List<String>[10]` 두 배열 생성 코드를 실제로 컴파일해 `generic array creation` 오류를 그대로 캡처했고, (2) `print(Set<String>)`/`print(Set<Integer>)` 오버로드를 컴파일해 `name clash: ... have the same erasure` 오류를 재현했으며, (3) PECS를 어긴 `List<? extends Number> dest`에 `.add()`를 호출하는 코드를 컴파일해 `incompatible types: Number cannot be converted to CAP#1` 오류를 얻은 뒤, `? super Number`로 고쳐 실제로 컴파일·실행에 성공하는 것(`[1, 2, 3]` 출력)까지 확인했다. 즉 "설명"이 아니라 "재현 로그"를 근거로 쓴다는 점이 차별화 지점이다.

## 본문

### 1. 제네릭은 왜 있고, 왜 런타임에는 사라지는가

Java 제네릭은 Java 5(JDK 5)에서 도입됐다. Oracle 공식 튜토리얼은 제네릭 도입 목적을 다음과 같이 설명한다.

> "Generics were introduced to the Java language to provide tighter type checks at compile time and to support generic programming."
> (Oracle, *The Java Tutorials: Type Erasure*)

즉 제네릭의 1차 목적은 "런타임 동작을 바꾸는 것"이 아니라 "컴파일 시점에 타입 오류를 더 엄격하게 잡아내는 것"이다. 이 목적을 구현하는 방식이 **타입 소거(type erasure)** 다. 같은 문서는 컴파일러가 소거 과정에서 하는 일을 세 가지로 요약한다.

1. 제네릭 타입의 타입 매개변수를 그 상한 바운드(bound)로, 바운드가 없으면 `Object`로 치환한다 — "Replace all type parameters in generic types with their bounds or Object if the type parameters are unbounded."
2. 타입 안전성을 지키기 위해 필요한 곳에 형변환(cast)을 삽입한다.
3. 확장된 제네릭 타입에서 다형성을 보존하기 위해 브리지(bridge) 메서드를 생성한다.

JLS(Java Language Specification) SE 21판 §4.6은 이를 더 형식적으로 정의한다.

> "Type erasure is a mapping from types (possibly including parameterized types and type variables) to types (that are never parameterized types or type variables). We write |T| for the erasure of type T."

쉽게 말해 `List<String>`과 `List<Integer>`는 컴파일러 눈에는 서로 다른 타입이지만, `.class` 파일 안에는 똑같이 `List`(raw type)로 남는다. Oracle 튜토리얼은 이 설계의 이유도 명시한다 — "Type erasure ensures that no new classes are created for parameterized types; consequently, generics incur no runtime overhead." 즉 제네릭 정보를 지우는 대신 런타임 오버헤드가 없다는 트레이드오프다. 이 트레이드오프가 아래에서 다룰 두 가지 제약(배열 생성 금지, 오버로드 금지)의 직접적인 원인이다.

### 2. 실전 결과 1 — `new T[]`가 컴파일되지 않는 이유를 직접 재현

아래 코드를 실제로 작성하고 `javac 21.0.2`로 컴파일했다.

```java
import java.util.List;

public class GenericArrayFail<T> {

    // (1) generic array creation is illegal
    void createArray() {
        T[] arr = new T[10];
    }

    // (2) array of a parameterized type is illegal
    void createParameterizedArray() {
        List<String>[] lists = new List<String>[10];
    }
}
```

`javac GenericArrayFail.java`를 실행하면 아래 오류가 그대로 출력된다(파라프레이즈가 아닌 실제 컴파일러 출력).

```text
GenericArrayFail.java:7: error: generic array creation
        T[] arr = new T[10];
                  ^
GenericArrayFail.java:12: error: generic array creation
        List<String>[] lists = new List<String>[10];
                               ^
2 errors
```

왜 이게 막히는지는 Oracle의 *Restrictions on Generics* 페이지가 명확한 이유를 든다. 배열은 런타임에 자신이 담을 수 있는 원소 타입을 기억하고 있다가, 타입이 맞지 않는 값이 들어오면 `ArrayStoreException`을 던져 방어한다. 그런데 제네릭 타입은 소거로 인해 런타임에 실제 타입 인자를 알 수 없다. 문서는 다음 예시로 이를 설명한다.

```java
Object[] stringLists = new List<String>[2];  // 컴파일러가 막지만, 만약 허용된다면
stringLists[0] = new ArrayList<String>();    // OK
stringLists[1] = new ArrayList<Integer>();   // ArrayStoreException이 던져져야 하지만
                                              // 런타임은 이를 감지할 수 없다
```

원문 그대로: "If arrays of parameterized lists were allowed, the previous code would fail to throw the desired ArrayStoreException." 즉 배열의 런타임 타입 체크와 제네릭의 컴파일 타임 전용 타입 정보가 근본적으로 충돌하기 때문에, 컴파일러가 아예 생성 자체를 막는다. `T[] arr = new T[10]`도 같은 이유다 — `T`가 소거되면 `new Object[10]`이 되어버리는데, 호출자가 기대하는 실제 타입(`Integer[]`, `String[]` 등)으로 안전하게 캐스팅할 방법이 없다.

### 3. 실전 결과 2 — 제네릭 타입만 다른 메서드 오버로드가 안 되는 이유

같은 원리가 메서드 오버로드에도 적용된다. 아래 코드를 실제로 컴파일했다.

```java
import java.util.Set;

public class OverloadFail {

    public void print(Set<String> strSet) {
        System.out.println("strings: " + strSet);
    }

    public void print(Set<Integer> intSet) {
        System.out.println("integers: " + intSet);
    }
}
```

`javac OverloadFail.java` 실행 결과:

```text
OverloadFail.java:9: error: name clash: print(Set<Integer>) and print(Set<String>) have the same erasure
    public void print(Set<Integer> intSet) {
                ^
1 error
```

Oracle 튜토리얼은 이 제약을 다음 문장으로 명시한다 — "A class cannot have two overloaded methods that will have the same signature after type erasure." 위 두 `print` 메서드는 컴파일 전에는 `Set<String>`, `Set<Integer>`로 서로 다른 시그니처처럼 보이지만, 소거 후에는 둘 다 `print(Set)`이 된다. JVM 바이트코드 수준에서 메서드는 시그니처(이름 + 매개변수 타입)로 구분되는데, 소거 후 시그니처가 완전히 같은 두 메서드가 같은 클래스 파일에 동시에 존재할 수 없기 때문에 컴파일러가 이를 "이름 충돌(name clash)"로 판정해 막는다. 실무에서는 이 제약이 "제네릭 타입 매개변수만으로는 오버로드를 구분할 수 없다"는 형태로 자주 부딪힌다 — 예를 들어 `process(List<String>)`과 `process(List<Integer>)`를 따로 두려는 시도는 항상 이 오류로 막힌다.

### 4. PECS 원칙 — Producer Extends, Consumer Super

와일드카드(`? extends T`, `? super T`)는 제네릭 컬렉션을 다루는 API를 유연하게 만들기 위한 장치다. Oracle의 *Guidelines for Wildcard Use* 페이지는 PECS라는 표현을 직접 쓰지는 않지만 동일한 내용을 "in 변수"/"out 변수"라는 용어로 규정한다.

> "An 'in' variable is defined with an upper bounded wildcard, using the extends keyword."
> "An 'out' variable is defined with a lower bounded wildcard, using the super keyword."

여기서 "in 변수"는 코드에 데이터를 **공급(produce)**하는 변수, "out 변수"는 코드가 데이터를 **소비(consume)**하며 채워 넣는 변수를 뜻한다. 이를 줄인 별칭이 PECS다 — Producer(공급자)는 `extends`, Consumer(소비자)는 `super`. 같은 문서는 "in이면서 동시에 out으로도 접근해야 하면 와일드카드를 쓰지 말라(do not use a wildcard)"는 지침과, "메서드 반환 타입에는 와일드카드를 쓰지 말라"는 지침도 함께 제시한다.

### 5. 실전 결과 3 — PECS를 어긴 코드의 컴파일 오류와 수정

`List` 두 개를 받아 하나의 값을 다른 하나로 복사하는 메서드를 생각해보자. `src`는 값을 꺼내기만 하는 **생산자**, `dest`는 값을 넣기만 하는 **소비자**다. 아래는 두 파라미터 모두 `? extends Number`로 잘못 선언한 코드다.

```java
import java.util.List;

public class PecsWrong {

    // WRONG: dest는 .add()로 값을 소비하는 컨슈머인데
    // "? extends Number"(프로듀서용 와일드카드)로 잘못 선언했다.
    public static void copyWrong(List<? extends Number> src, List<? extends Number> dest) {
        for (Number n : src) {
            dest.add(n);
        }
    }
}
```

`javac PecsWrong.java` 실행 결과:

```text
PecsWrong.java:9: error: incompatible types: Number cannot be converted to CAP#1
            dest.add(n);
                     ^
  where CAP#1 is a fresh type-variable:
    CAP#1 extends Number from capture of ? extends Number
Note: Some messages have been simplified; recompile with -Xdiags:verbose to get full output
1 error
```

`? extends Number`는 "`Number`이거나 그 하위 타입인 알 수 없는 구체 타입"을 의미한다. 컴파일러 입장에서는 그 알 수 없는 타입이 `Integer`인지 `Double`인지 확정할 수 없으므로, `Number`를 그 안에 넣는 것 자체를 안전하지 않다고 보고 막는다(`CAP#1`은 컴파일러가 그 알 수 없는 타입에 붙인 캡처 변수 이름이다). PECS 원칙대로 `dest`를 소비자로 인식해 `? super Number`로 바꾸면 문제가 해결된다.

```java
import java.util.ArrayList;
import java.util.List;

public class PecsFixed {

    // FIXED: src는 생산자 -> ? extends Number
    //        dest는 소비자 -> ? super Number  (PECS)
    public static void copy(List<? extends Number> src, List<? super Number> dest) {
        for (Number n : src) {
            dest.add(n);
        }
    }

    public static void main(String[] args) {
        List<Integer> ints = new ArrayList<>(List.of(1, 2, 3));
        List<Number> nums = new ArrayList<>();
        copy(ints, nums);
        System.out.println(nums);
    }
}
```

`javac PecsFixed.java && java PecsFixed`를 실행하면 컴파일이 성공하고 `[1, 2, 3]`이 출력된다. `? super Number`는 "`Number`이거나 그 상위 타입인 알 수 없는 구체 타입"을 의미하므로, 그 타입의 변수에는 `Number`(및 그 하위 타입인 `Integer` 등)를 안전하게 넣을 수 있다는 것을 컴파일러가 보장할 수 있다. 이 패턴은 JDK 표준 라이브러리에도 그대로 쓰인다 — 예컨대 `Collections.copy(List<? super T> dest, List<? extends T> src)`가 정확히 같은 구조다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| 제네릭은 컴파일 시점 타입 검사 강화를 목적으로 도입됐다 | verified | Oracle, *The Java Tutorials: Type Erasure*, https://docs.oracle.com/javase/tutorial/java/generics/erasure.html — "Generics were introduced to the Java language to provide tighter type checks at compile time..." 원문 대조 (확인일: 2026-08-22) |
| 타입 소거는 타입 매개변수를 바운드 또는 Object로 치환하고, 필요한 형변환 삽입 및 브리지 메서드 생성을 포함한다 | verified | Oracle, *The Java Tutorials: Type Erasure*, https://docs.oracle.com/javase/tutorial/java/generics/erasure.html; JLS SE21 §4.6, https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html#jls-4.6 원문 대조 (확인일: 2026-08-22) |
| `T[] arr = new T[10]` 및 `List<String>[]` 같은 매개변수화 타입 배열 생성은 컴파일 오류다 | verified | Oracle, *The Java Tutorials: Restrictions on Generics*, https://docs.oracle.com/javase/tutorial/java/generics/restrictions.html 원문 대조 + OpenJDK 21.0.2(javac) 로컬 컴파일로 "generic array creation" 오류 직접 재현 (확인일: 2026-08-22) |
| 소거 후 시그니처가 같은 두 오버로드 메서드는 컴파일 오류가 된다 | verified | Oracle, *The Java Tutorials: Restrictions on Generics*, https://docs.oracle.com/javase/tutorial/java/generics/restrictions.html — "A class cannot have two overloaded methods that will have the same signature after type erasure." 원문 대조 + OpenJDK 21.0.2(javac) 로컬 컴파일로 "have the same erasure" 오류 직접 재현 (확인일: 2026-08-22) |
| PECS(Producer Extends, Consumer Super) 원칙은 Oracle 공식 가이드라인의 "in 변수는 extends, out 변수는 super" 지침과 일치한다 | verified | Oracle, *The Java Tutorials: Guidelines for Wildcard Use*, https://docs.oracle.com/javase/tutorial/java/generics/wildcardGuidelines.html 원문 대조 (확인일: 2026-08-22) |
| 소비자로 쓰이는 파라미터를 `? extends`로 선언하면 `.add()` 호출 시 컴파일 오류가 나고, `? super`로 고치면 해결된다 | verified | OpenJDK 21.0.2(javac 21.0.2, GraalVM CE 21.0.2+13.1) 로컬 환경에서 직접 컴파일 — 오류 재현("incompatible types: Number cannot be converted to CAP#1") 및 수정 후 정상 실행("[1, 2, 3]" 출력) 확인 (확인일: 2026-08-22) |

## 작성자의 견해

> 이 섹션은 검증된 사실이 아니라 작성자의 개인적 해석을 담고 있습니다.

타입 소거를 처음 배울 때 "제네릭은 컴파일러 눈속임일 뿐"이라는 식으로 폄하하는 설명을 종종 본다. 개인적으로는 이게 정확한 비유가 아니라고 생각한다. 위에서 재현한 세 가지 오류 — 배열 생성 금지, 오버로드 금지, PECS 위반 — 는 전부 "타입 소거가 존재하기 때문에 어쩔 수 없이 생기는 부작용"이 아니라, "런타임 오버헤드 없이 타입 안전성을 확보한다"는 설계 목표가 만들어낸 논리적으로 필연적인 결과에 가깝다고 본다. 배열이 런타임 타입 체크를 요구하는 자료구조라는 사실과, 제네릭이 컴파일 타임 전용 정보라는 사실은 애초에 양립할 수 없다 — 이 둘을 억지로 맞추려 했다면 배열마다 실제 타입 인자를 갖고 다니는 리플렉션 오버헤드가 필요했을 것이다. PECS도 마찬가지다. `? extends`와 `? super`는 임의로 정해진 문법이 아니라, "알 수 없는 하위 타입에서 안전하게 값을 꺼낼 수 있는 조건"과 "알 수 없는 상위 타입에 안전하게 값을 넣을 수 있는 조건"을 타입 시스템으로 강제한 결과다. 이 관점에서 보면 컴파일 오류 메시지들은 "제약"이 아니라 "설계가 의도대로 동작하고 있다는 증거"로 읽힌다.

## 한계와 반론

이 글의 실습은 JDK 21(OpenJDK 21.0.2, GraalVM CE 빌드) `javac` 기준이며, 오류 메시지의 정확한 문구는 JDK 버전마다 조금씩 달라질 수 있다(예: 더 오래된 JDK는 "unchecked" 경고 문구가 다르게 표기되기도 한다). 또한 이 글은 타입 소거의 "제약" 측면에만 집중했고, `Class<T>` 토큰을 명시적으로 넘기는 슈퍼 타입 토큰(super type token) 패턴이나 `Array.newInstance(Class, int)`로 제네릭 배열을 우회 생성하는 실무 기법은 다루지 않았다 — 이는 별도 글의 주제로 남긴다. PECS 원칙도 "복사(copy)"라는 가장 단순한 예시로만 보였는데, 실제로는 `Comparator<? super T>`처럼 비교/정렬 API에서 더 복잡한 형태로 나타나며, 와일드카드 캡처(wildcard capture) 자체가 오류가 되는 경우(헬퍼 메서드로 우회해야 하는 경우)는 별도로 학습이 필요하다. 마지막으로 이 글이 인용한 Oracle 튜토리얼은 최신 JDK 21/25 문법(예: 레코드, sealed 타입)을 반영해 개정된 페이지가 아니므로, 제네릭과 신규 문법의 상호작용까지 보장하는 내용은 아니다.

## 참고문헌

1. Oracle, "The Java Tutorials — Type Erasure," https://docs.oracle.com/javase/tutorial/java/generics/erasure.html (확인일: 2026-08-22)
2. Oracle, "The Java Tutorials — Restrictions on Generics," https://docs.oracle.com/javase/tutorial/java/generics/restrictions.html (확인일: 2026-08-22)
3. Oracle, "The Java Tutorials — Guidelines for Wildcard Use," https://docs.oracle.com/javase/tutorial/java/generics/wildcardGuidelines.html (확인일: 2026-08-22)
4. Oracle, "The Java Language Specification, Java SE 21 Edition — §4.6 Type Erasure," https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html#jls-4.6 (확인일: 2026-08-22)

## 종합적 의견

> 이 섹션은 사실 나열이 아니라 전체 주제를 관통하는 작성자의 종합적 해석입니다.

타입 소거와 PECS는 별개의 두 주제로 다뤄지는 경우가 많지만, 이 글에서 직접 컴파일해본 결과 둘은 사실상 같은 원인에서 갈라져 나온 두 가지 증상이라는 인상을 받았다. 둘 다 "런타임에는 실제 타입 인자를 알 수 없다"는 하나의 제약에서 출발한다 — 배열/오버로드 제한은 그 제약을 "생성/정의 시점"에 미리 막는 방식이고, PECS는 그 제약을 "사용 시점"에 안전하게 다루는 방식이다. 실무에서 제네릭 관련 컴파일 오류를 만났을 때 "이게 왜 안 되지"라고 문법을 외우려 하기보다, "이 값이 지금 생산자로 쓰이는가 소비자로 쓰이는가, 그리고 런타임에 이 타입 정보가 남아있어야 하는 코드인가"를 먼저 물어보면 오류 메시지가 훨씬 예측 가능해진다는 것이 이번에 직접 재현해보며 얻은 결론이다. 특히 `CAP#1`처럼 낯선 캡처 변수 이름이 섞인 오류 메시지는 처음 보면 당황스럽지만, PECS 프레임으로 다시 읽으면 "이 파라미터는 소비자인데 프로듀서용 와일드카드를 썼다"는 한 문장으로 항상 요약된다는 점을 강조하고 싶다.

## 꼬리질문

- `Comparator<? super T>`처럼 비교/정렬 API에서 PECS가 적용되는 실제 JDK 표준 라이브러리 시그니처를 더 찾아보면 어떤 패턴이 반복될까?
- 와일드카드 캡처(wildcard capture) 오류가 발생할 때 헬퍼 메서드로 우회하는 패턴(capture helper)은 구체적으로 어떻게 작성해야 하는가?
- 슈퍼 타입 토큰(super type token)이나 `TypeReference` 패턴으로 런타임에 제네릭 타입 정보를 우회 보존하는 방법은 타입 소거의 어떤 한계를 얼마나 해결해주는가?

## 백링크

- [Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가](https://beji-tech.blogspot.com/2026/08/java-list-vs-set-vs-map.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)

