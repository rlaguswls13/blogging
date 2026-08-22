---
author: AI Tech Editor
createdAt: '2026-08-19T05:40:12.642307Z'
factCheckScore: 0
id: '5923021605105890298'
notionPageId: null
publishedAt: '2026-08-18T22:44:23-07:00'
slug: java-collections-list-set-map-guide
status: published
tags:
- Basics
- Java
- Collections
- Data Structure
title: Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가
updatedAt: '2026-08-19T05:40:12.642307Z'
url: https://beji-tech.blogspot.com/2026/08/java-list-vs-set-vs-map.html
---


# Java 컬렉션 프레임워크 입문 — List vs Set vs Map, 언제 무엇을 써야 하는가

## 요약

Java로 코드를 짜다 보면 배열(Array) 하나로는 금방 한계에 부딪힙니다. 크기를 미리 정해야 하고, 중간에 요소를 넣거나 빼는 게 번거롭고, "이 값이 이미 있는지" 확인하려면 매번 처음부터 끝까지 훑어봐야 합니다. 이런 불편을 해결하기 위해 Java는 `java.util` 패키지 아래에 **컬렉션 프레임워크(Collections Framework)**를 제공합니다. 이 글에서는 그중 가장 자주 쓰이는 세 가지 큰 틀 — **List(순서가 있고 중복을 허용하는 목록)**, **Set(중복을 허용하지 않는 집합)**, **Map(키-값 쌍을 저장하는 사전)** — 이 각각 무엇이고, 그 안에 어떤 구현체(ArrayList/LinkedList, HashSet/LinkedHashSet/TreeSet, HashMap/LinkedHashMap/TreeMap)가 있으며, 실무에서 무엇을 기준으로 골라야 하는지를 Java 공식 문서(Java SE 21 API)를 근거로 정리합니다. 자바를 막 배우기 시작한 개발자가 "그냥 아무거나 쓰면 되는 거 아닌가요?"라는 질문에 스스로 답할 수 있게 되는 것이 이 글의 목표입니다.

## 본문

### 1. 컬렉션 프레임워크 개요 — 왜 배열만으로는 부족한가

배열(`int[]`, `String[]` 등)은 크기가 고정되어 있습니다. 처음에 10개짜리 배열을 만들면 11번째 요소를 넣을 수 없고, 더 큰 배열을 새로 만들어서 기존 값을 전부 복사해야 합니다. 또한 배열은 "이 값이 배열 안에 있는가?"를 확인하려면 처음부터 끝까지 하나씩 비교하는 것 말고는 방법이 없습니다(선형 탐색, O(n)).

컬렉션 프레임워크는 이런 문제를 해결하기 위해 자료구조별로 특화된 인터페이스와 구현체를 제공합니다. 핵심 인터페이스 세 개는 다음과 같습니다.

- **`List<E>`**: 순서가 있고, 같은 값을 여러 번 넣을 수 있는(중복 허용) 목록. 인덱스로 접근합니다(`list.get(0)`).
- **`Set<E>`**: 중복을 허용하지 않는 집합. "이 값이 있는가"를 빠르게 확인하는 데 특화되어 있습니다.
- **`Map<K, V>`**: 키(Key)와 값(Value)을 한 쌍으로 저장합니다. 키로 값을 빠르게 찾을 수 있습니다(`map.get(key)`).

세 인터페이스 모두 여러 구현체를 갖고 있고, 구현체마다 내부 자료구조가 다르기 때문에 성능 특성(시간복잡도)이 다릅니다. 아래에서 각각을 코드와 함께 살펴봅니다.

### 2. List — ArrayList vs LinkedList

`List`의 대표 구현체는 `ArrayList`와 `LinkedList` 두 가지입니다.

**`ArrayList`**는 이름 그대로 내부적으로 배열을 사용합니다. Java 공식 문서는 "Resizable-array implementation of the List interface"라고 명시합니다 — 요소가 추가될 때 배열 용량이 부족하면 자동으로 더 큰 배열을 만들어 기존 값을 복사하는 방식으로 동작합니다. 인덱스로 값을 읽거나(`get`) 바꾸는(`set`) 연산은 배열의 특정 위치에 바로 접근하므로 **O(1)**입니다. 반면 리스트 끝이 아닌 중간에 값을 삽입(`add(index, element)`)하거나 삭제하려면 뒤에 있는 요소들을 전부 한 칸씩 밀어야 하므로 **O(n)**이 걸립니다. 다만 맨 끝에 값을 추가하는 `add(e)`는 "분할 상환 상수 시간(amortized constant time)"이라고 공식 문서에 명시되어 있습니다 — 가끔 배열을 확장하느라 시간이 걸리지만, 평균적으로 보면 거의 O(1)이라는 뜻입니다.

```java
import java.util.ArrayList;
import java.util.List;

List<String> names = new ArrayList<>();
names.add("Alice");   // 끝에 추가: O(1) amortized
names.add("Bob");
names.add(0, "Zack"); // 맨 앞에 삽입: O(n), 기존 요소들이 한 칸씩 밀림
System.out.println(names.get(1)); // 인덱스 접근: O(1) -> "Alice"
```

**`LinkedList`**는 이중 연결 리스트(Doubly-Linked List)로 구현되어 있습니다. 각 노드가 앞 노드와 뒤 노드를 가리키는 포인터를 갖는 구조입니다. 그래서 리스트의 맨 앞이나 맨 뒤에 값을 추가/삭제하는 연산은 포인터만 바꾸면 되므로 **O(1)**입니다. 하지만 `get(index)`처럼 중간의 특정 위치에 접근하려면 앞이나 뒤 중 더 가까운 쪽에서부터 포인터를 따라가며 순회해야 하므로 **O(n)**이 걸립니다. `LinkedList`는 `Deque`(덱, 양쪽 끝에서 넣고 뺄 수 있는 자료구조) 인터페이스도 구현하고 있어서 스택이나 큐 대용으로도 자주 쓰입니다.

```java
import java.util.LinkedList;
import java.util.Deque;

Deque<Integer> stack = new LinkedList<>();
stack.push(1); // 맨 앞에 추가: O(1)
stack.push(2);
System.out.println(stack.pop()); // 맨 앞 제거: O(1) -> 2
```

**선택 기준**: 인덱스로 값을 자주 조회한다면 `ArrayList`, 리스트의 양쪽 끝에서 삽입/삭제가 빈번하다면(예: 큐, 스택) `LinkedList`가 이론적으로 유리합니다. 다만 실무에서는 `ArrayList`가 메모리상에서 연속적으로 배치되어 CPU 캐시 효율이 좋기 때문에, 중간 삽입이 잦은 경우가 아니라면 대부분의 상황에서 `ArrayList`가 기본 선택지로 권장됩니다(이 부분은 '한계와 반론' 절에서 더 자세히 다룹니다).

### 3. Set — HashSet vs LinkedHashSet vs TreeSet

`Set`은 중복 없는 값들의 모음입니다. 세 가지 대표 구현체가 있습니다.

**`HashSet`**은 공식 문서에 "backed by a hash table (actually a HashMap instance)"라고 명시된 대로, 내부적으로 `HashMap`을 그대로 재사용해서 구현됩니다(값을 키로, 더미 값을 밸류로 저장하는 방식). `add`, `remove`, `contains` 연산 모두 해시 함수가 요소를 버킷에 고르게 분산시킨다는 전제 하에 평균 **O(1)**입니다. 대신 순서를 전혀 보장하지 않습니다 — 넣은 순서대로 꺼내진다는 보장이 없습니다.

```java
import java.util.HashSet;
import java.util.Set;

Set<String> tags = new HashSet<>();
tags.add("java");
tags.add("java"); // 중복 - 무시됨, Set 크기는 그대로 1
tags.add("spring");
System.out.println(tags.contains("java")); // O(1) 평균 -> true
```

**`LinkedHashSet`**은 `HashSet`과 마찬가지로 해시 테이블을 쓰지만, 여기에 이중 연결 리스트를 추가로 유지해서 **삽입된 순서**를 기억합니다. 공식 문서 표현으로는 "maintains a doubly-linked list running through all of its entries"입니다. 연산 성능은 `HashSet`과 거의 동일한 O(1)이면서 순회 시 항상 넣은 순서대로 나옵니다.

**`TreeSet`**은 `TreeMap`을 기반으로 구현되며(공식 문서: "A NavigableSet implementation based on a TreeMap"), 내부적으로 레드-블랙 트리(Red-Black Tree, 스스로 균형을 맞추는 이진 탐색 트리)를 사용합니다. 그래서 `add`/`remove`/`contains`가 **O(log n)**이고, 대신 항상 정렬된 순서를 유지합니다.

```java
import java.util.TreeSet;
import java.util.Set;

Set<Integer> scores = new TreeSet<>();
scores.add(90);
scores.add(70);
scores.add(85);
System.out.println(scores); // [70, 85, 90] - 항상 정렬된 상태로 출력됨
```

**선택 기준**: 순서가 전혀 중요하지 않고 속도가 최우선이면 `HashSet`, 넣은 순서를 유지하고 싶으면 `LinkedHashSet`, 항상 정렬된 상태를 유지해야 하면 `TreeSet`을 씁니다.

### 4. Map — HashMap vs LinkedHashMap vs TreeMap

`Map`은 키-값 쌍을 저장합니다. `List`/`Set`과 구조적으로 대응되는 세 가지 구현체가 있습니다.

**`HashMap`**은 버킷(Bucket) 배열 기반 해시 테이블입니다. 공식 문서는 "constant-time performance for the basic operations (get and put)"라고 명시하며, 이는 해시 함수가 키를 버킷에 고르게 분산시킨다는 가정 하의 평균 성능입니다. 기본 초기 용량은 16, 기본 로드 팩터(load factor)는 0.75입니다 — 즉 저장된 항목 수가 (버킷 수 × 0.75)를 넘으면 내부 배열이 약 2배로 늘어나며 재해싱이 일어납니다. `HashMap`은 순서를 보장하지 않지만, `null` 키와 `null` 값을 각각 하나씩 허용한다는 특징이 있습니다(반면 `Hashtable`은 `null`을 허용하지 않습니다).

```java
import java.util.HashMap;
import java.util.Map;

Map<String, Integer> ageOf = new HashMap<>();
ageOf.put("Alice", 30); // O(1) 평균
ageOf.put("Bob", 25);
ageOf.put(null, -1);    // null 키 허용
System.out.println(ageOf.get("Alice")); // O(1) 평균 -> 30
```

**`LinkedHashMap`**은 `HashMap`에 이중 연결 리스트를 더해 삽입 순서(또는 옵션으로 마지막 접근 순서, access-order)를 유지합니다. `removeEldestEntry`를 오버라이드하면 LRU(Least Recently Used) 캐시를 손쉽게 구현할 수 있어서, 캐시 구현체의 기반으로 자주 활용됩니다.

```java
import java.util.LinkedHashMap;
import java.util.Map;

Map<String, Integer> cache = new LinkedHashMap<>(16, 0.75f, true) { // access-order
    protected boolean removeEldestEntry(Map.Entry<String, Integer> eldest) {
        return size() > 3; // 최대 3개까지만 유지하는 간단한 LRU 캐시
    }
};
```

**`TreeMap`**은 레드-블랙 트리 기반이며(공식 문서: "A Red-Black tree based NavigableMap implementation"), `get`/`put`/`remove`/`containsKey`가 모두 **O(log n)**입니다. 키를 자연 순서(또는 지정한 `Comparator`)로 정렬된 상태로 유지하며, `firstEntry()`/`ceilingEntry()`처럼 범위 검색에 특화된 메서드도 제공합니다.

### 5. 시간복잡도 종합 비교와 실무 선택 가이드

지금까지 다룬 8개 구현체의 평균 시간복잡도를 표로 정리하면 다음과 같습니다.

| 구현체 | 내부 구조 | 조회(get/contains) | 삽입(add/put) | 순서 보장 |
|---|---|---|---|---|
| `ArrayList` | 동적 배열 | O(1) (인덱스) | O(1) 끝/O(n) 중간 | 삽입 순서 |
| `LinkedList` | 이중 연결 리스트 | O(n) | O(1) 양끝 | 삽입 순서 |
| `HashSet` | 해시 테이블(HashMap) | O(1) 평균 | O(1) 평균 | 없음 |
| `LinkedHashSet` | 해시 테이블 + 연결 리스트 | O(1) 평균 | O(1) 평균 | 삽입 순서 |
| `TreeSet` | 레드-블랙 트리(TreeMap) | O(log n) | O(log n) | 정렬 순서 |
| `HashMap` | 해시 테이블 | O(1) 평균 | O(1) 평균 | 없음 |
| `LinkedHashMap` | 해시 테이블 + 연결 리스트 | O(1) 평균 | O(1) 평균 | 삽입/접근 순서 |
| `TreeMap` | 레드-블랙 트리 | O(log n) | O(log n) | 정렬 순서 |

실무에서 고를 때는 이렇게 접근하면 됩니다: 특별한 이유가 없다면 **`ArrayList`와 `HashMap`을 기본값**으로 시작하세요 — 이 둘이 가장 범용적이고 빠릅니다. 그 위에 다음 질문을 순서대로 던져보면 됩니다.

1. **순서(넣은 순서)를 그대로 유지해야 하는가?** → `LinkedHashSet`/`LinkedHashMap`을 고려합니다(예: 사용자에게 입력 순서 그대로 보여줘야 할 때, 또는 LRU 캐시).
2. **항상 정렬된 상태가 필요한가?** → `TreeSet`/`TreeMap`을 고려합니다(예: 랭킹, 범위 검색이 잦은 경우).
3. **리스트의 양쪽 끝에서 삽입/삭제가 아주 잦은가?**(스택, 큐 용도) → `LinkedList` 또는 `ArrayDeque`(이 글에서 다루진 않았지만, 스택/큐 용도로는 `LinkedList`보다 더 자주 권장되는 구현체입니다)를 고려합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| ArrayList는 크기가 자동 조정되는 배열 기반이며, get/set은 O(1), 끝에 추가하는 add는 분할 상환 O(1), 중간 삽입/삭제는 O(n)이다 | verified | Oracle Java SE 21 API, `java.util.ArrayList` (확인일: 2026-08-19) |
| LinkedList는 이중 연결 리스트로 구현되며, 인덱스 접근은 O(n), 양쪽 끝에서의 삽입/삭제는 O(1)이다 | verified | Oracle Java SE 21 API, `java.util.LinkedList` (확인일: 2026-08-19) |
| HashSet은 내부적으로 HashMap 인스턴스로 구현되며, add/remove/contains는 평균 O(1)이고 순서를 보장하지 않는다 | verified | Oracle Java SE 21 API, `java.util.HashSet` (확인일: 2026-08-19) |
| LinkedHashSet은 해시 테이블에 이중 연결 리스트를 더해 삽입 순서(encounter order)를 유지한다 | verified | Oracle Java SE 21 API, `java.util.LinkedHashSet` (확인일: 2026-08-19) |
| TreeSet은 TreeMap 기반으로 구현되며 add/remove/contains가 O(log n)이다 | verified | Oracle Java SE 21 API, `java.util.TreeSet` (확인일: 2026-08-19) |
| HashMap은 버킷 기반 해시 테이블이며 get/put이 평균 O(1), 기본 로드 팩터 0.75, null 키와 null 값을 각각 하나씩 허용한다 | verified | Oracle Java SE 21 API, `java.util.HashMap` (확인일: 2026-08-19) |
| LinkedHashMap은 HashMap에 이중 연결 리스트를 추가해 삽입 순서 또는 접근 순서를 유지하며, removeEldestEntry로 LRU 캐시를 구현할 수 있다 | verified | Oracle Java SE 21 API, `java.util.LinkedHashMap` (확인일: 2026-08-19) |
| TreeMap은 레드-블랙 트리 기반이며 get/put/remove/containsKey가 O(log n)을 보장한다 | verified | Oracle Java SE 21 API, `java.util.TreeMap` (확인일: 2026-08-19) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

초보 개발자들이 가장 많이 하는 실수는 "일단 `ArrayList`나 `HashMap`을 쓰고 본다"가 아니라, 오히려 반대로 **모든 상황에 `LinkedList`가 더 빠를 것이라고 착각**하는 경우입니다. "삽입/삭제가 O(1)이니까 LinkedList가 좋다"는 이야기를 어디선가 듣고, 실제로는 인덱스 접근이 훨씬 잦은 코드에 `LinkedList`를 썼다가 성능이 오히려 나빠지는 경우를 실무에서 종종 봅니다. Big-O 표기법은 "연산 횟수가 많아질 때 얼마나 느려지는가"의 추세를 보여줄 뿐, 실제 벽시계 시간(wall-clock time)까지 보장하지는 않습니다. 개인적으로는 컬렉션을 고를 때 "이 자료구조에 어떤 연산을 얼마나 자주 할 것인가"를 먼저 구체적으로 적어보고, 그다음에 표를 보고 고르는 순서를 권합니다. 그리고 정말 성능이 문제가 되는 구간이라면, 추측하지 말고 JMH(Java Microbenchmark Harness) 같은 도구로 실제로 측정해보는 습관을 들이는 것이 장기적으로 훨씬 도움이 됩니다. 컬렉션 선택은 정답이 정해진 시험 문제가 아니라, 데이터의 크기와 접근 패턴에 따라 계속 바뀌는 실무 판단의 영역이라고 생각합니다.

## 한계와 반론

이 글에서 정리한 시간복잡도는 어디까지나 **평균(amortized/average) 케이스**이자 **점근적(asymptotic) 추세**라는 한계가 있습니다. 예를 들어 `HashMap`의 O(1)은 "해시 함수가 키를 버킷에 고르게 분산시킨다"는 전제가 깨지면 무너집니다 — 모든 키가 같은 버킷에 몰리는 최악의 경우, 이론적으로는 O(n)까지 느려질 수 있습니다(다만 Java 8부터는 한 버킷에 일정 개수 이상 엔트리가 쌓이면 연결 리스트 대신 트리 구조로 전환해 최악의 경우에도 성능 저하를 완화하는 최적화가 들어가 있습니다).

또한 "이론적 시간복잡도가 낮다고 실제로 항상 더 빠른 것은 아니다"라는 반론도 중요합니다. `ArrayList`는 메모리에 요소들이 연속적으로 붙어 있어 CPU 캐시 적중률이 높은 반면, `LinkedList`는 노드들이 메모리 여기저기 흩어져 있어 캐시 미스가 잦습니다. 그래서 데이터 개수가 그리 크지 않은 상황(수천~수만 개 수준)에서는, 이론상 O(n)인 `ArrayList`의 중간 삽입이 이론상 O(1)인 `LinkedList`의 순회+삽입보다 실제로는 더 빠르게 측정되는 경우도 흔합니다. Big-O만 보고 자료구조를 고르기보다, 실제 데이터 규모와 벤치마크 결과를 함께 참고하는 것이 안전합니다.

## 참고문헌

1. Oracle, "ArrayList (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html) (확인일: 2026-08-19)
2. Oracle, "LinkedList (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedList.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedList.html) (확인일: 2026-08-19)
3. Oracle, "HashSet (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashSet.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashSet.html) (확인일: 2026-08-19)
4. Oracle, "LinkedHashSet (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashSet.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashSet.html) (확인일: 2026-08-19)
5. Oracle, "TreeSet (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeSet.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeSet.html) (확인일: 2026-08-19)
6. Oracle, "HashMap (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html) (확인일: 2026-08-19)
7. Oracle, "LinkedHashMap (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashMap.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashMap.html) (확인일: 2026-08-19)
8. Oracle, "TreeMap (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

Java 컬렉션 프레임워크를 처음 접하면 구현체 종류가 많아 부담스러울 수 있지만, 결국 핵심은 세 가지 질문으로 요약됩니다. 순서가 있고 중복을 허용해야 하는가(List), 중복 없이 존재 여부만 빠르게 확인하면 되는가(Set), 키로 값을 찾아야 하는가(Map). 그다음 각 인터페이스 안에서는 "정렬이 필요한가 → Tree 계열", "삽입 순서를 지켜야 하는가 → Linked 계열", "둘 다 아니라면 → 기본(Hash/Array) 계열"이라는 동일한 패턴이 반복됩니다. 이 패턴만 기억해도 새로운 상황에서 어떤 컬렉션을 골라야 할지 스스로 판단할 수 있는 기준이 생깁니다. 실무로 넘어가면 `ConcurrentHashMap`처럼 멀티스레드 환경을 위한 동시성 컬렉션, `ArrayDeque`처럼 스택/큐에 더 최적화된 구현체 등 더 넓은 세계가 기다리고 있지만, 오늘 다룬 8개 구현체의 내부 구조와 시간복잡도를 이해하고 나면 그 확장된 컬렉션들도 훨씬 빠르게 이해할 수 있을 것입니다. 결국 자료구조 선택은 "무엇을 자주 하는가"에 대한 질문이며, 정답을 외우기보다 이 질문을 스스로에게 던지는 습관을 들이는 것이 더 오래 남는 배움입니다.

## 꼬리질문

1. **`ConcurrentHashMap`은 `HashMap`과 달리 멀티스레드 환경에서 락 경합을 어떻게 최소화하며 동시성을 보장하는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
2. **Java 8부터 HashMap의 한 버킷 안에서 엔트리 수가 일정 개수(8개)를 넘으면 연결 리스트 대신 레드-블랙 트리로 전환된다는데, 이 트리화(Treeify) 임계값과 되돌리는(Untreeify) 조건은 정확히 어떻게 동작하는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
3. **스택/큐 용도로 `LinkedList`보다 `ArrayDeque`가 더 권장되는 구체적인 이유(메모리 지역성, GC 오버헤드 차이)는 무엇인가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayDeque.html

## 백링크

- [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)