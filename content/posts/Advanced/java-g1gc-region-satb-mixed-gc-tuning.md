---
author: AI Tech Editor
createdAt: '2026-08-22T18:35:46.298095Z'
factCheckScore: 1.0
id: '4155974160298077233'
notionPageId: null
publishedAt: '2026-08-23T17:07:59-07:00'
slug: java-g1gc-region-satb-mixed-gc-tuning
status: published
tags:
- Advanced
- Java
- GC
- G1GC
title: Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전
updatedAt: '2026-08-23T00:00:00.000000Z'
url: https://beji-tech.blogspot.com/2026/08/java-g1gc-gc.html
---

# Java G1GC — 힙 리전 구조와 튜닝 파라미터로 보는 GC 튜닝 실전

## 요약

G1(Garbage-First) GC는 힙을 균등한 크기의 리전(Region)으로 나눈다는 사실만 알아서는 실전 튜닝에 쓸모가 없습니다. 진짜 관건은 리전 단위 회수가 가능하려면 리전 간 참조를 어떻게 추적하는지(Remembered Set), 애플리케이션을 멈추지 않고 어떻게 살아있는 객체를 판별하는지(SATB), 그리고 Young GC만으로 끝나지 않고 Old 영역까지 회수하는 Mixed GC 사이클이 언제 어떻게 도는지입니다. 본 아티클은 이 세 메커니즘을 실제 JVM 플래그·GC 로그와 함께 다루고, 현업에서 흔히 저지르는 튜닝 실수 — `-XX:MaxGCPauseMillis`를 공격적으로 낮췄다가 오히려 Young GC 빈도가 늘고 Evacuation Failure(승격 실패)가 터지는 상황 — 을 `-Xlog:gc*` 로그로 어떻게 진단하는지까지 다룹니다.

## 차별화 포인트

동일 블로그의 "JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 GC" 기초 글은 Heap/Method Area/Stack 같은 JVM 명세 수준의 런타임 데이터 영역 구조와 Young/Old 세대 분리, Minor/Major GC 개념을 다뤘고 G1은 "리전 기반이며 가비지가 많은 곳부터 회수한다" 정도로만 언급하고 끝났습니다. 이 글은 그 이후 단계, 즉 G1이 CMS와 근본적으로 다른 지점(Remembered Set·SATB·리전 압축)과, `-XX:MaxGCPauseMillis`가 "보장"이 아니라 "목표치"에 불과해서 지나치게 낮게 잡으면 오히려 GC가 더 자주 돌고 Evacuation Failure로 이어질 수 있다는 실전 튜닝 함정을, 실제 JVM 플래그 조합과 `-Xlog:gc*` 로그 판독 방법까지 곁들여 다룹니다. 이런 pause-time 목표와 실제 결과의 괴리는 공식 문서에도 명시적 경고문으로 나오지 않아 실무에서 반복적으로 재발하는 문제이기도 합니다.

## 본문

### 1. 기초 글과 무엇이 다른가 — "리전으로 나뉜다"의 다음 단계

G1은 힙을 동일한 크기의 리전으로 나누고, 각 리전은 특정 시점에 Young(Eden/Survivor) 또는 Old 세대에 배정됩니다. 리전 크기는 기본적으로 최대 힙 크기를 기준으로 대략 2048개의 리전이 나오도록 어고노믹스(ergonomics)하게 결정되며, 최대 32MB까지 자동으로 설정될 수 있습니다. 사용자가 `-XX:G1HeapRegionSize`로 직접 지정할 때는 1MB~512MB 범위의 2의 거듭제곱 값이어야 합니다[1]. 여기까지는 이미 널리 알려진 "리전 기반" 설명입니다. 문제는 그다음입니다 — 힙 전체가 아니라 리전 몇 개만 골라 회수하려면, 그 리전을 가리키는 참조가 힙의 다른 어디에 있는지 알아야 합니다. 이걸 가능하게 하는 장치가 Remembered Set(RSet)입니다.

### 2. Remembered Set(RSet) — 리전 단위 회수를 가능하게 하는 장치

G1은 각 리전마다 RSet을 유지하는데, 이는 "해당 리전을 가리키는, 리전 외부의 참조 위치 집합"입니다[1]. RSet 자체는 카드(Card)라는 512바이트 단위 논리 파티션으로 표현되며, RSet 엔트리는 이 카드에 대한 압축된 참조입니다[1]. 즉 어떤 객체가 다른 리전의 객체를 참조하면, 그 참조가 속한 카드가 대상 리전의 RSet에 기록됩니다. 덕분에 G1은 GC 시점에 힙 전체를 스캔하지 않고도 "이 리전을 회수하려면 어디를 추가로 훑어야 하는지"를 빠르게 알아낼 수 있습니다. RSet은 대부분 지연 생성(lazily)되며, 여러 리전을 묶어 관리해 메모리 오버헤드를 줄입니다 — 예를 들어 Remark와 Cleanup 사이 구간에 마킹 대상 후보 리전들의 RSet을 재구축합니다[1]. RSet 유지 자체에 쓰기 배리어(write barrier) 비용이 들어가는데, 이는 CMS의 카드 테이블과 유사한 아이디어지만 G1은 이를 리전 단위 회수 결정과 직접 연결한다는 점이 다릅니다.

### 3. SATB(Snapshot-At-The-Beginning) — CMS와 갈라지는 지점

G1의 동시 마킹(Concurrent Marking)은 SATB(Snapshot-At-The-Beginning) 알고리즘을 씁니다. Concurrent Start pause 시점에 힙의 가상 스냅샷을 찍고, 마킹이 시작된 시점에 살아있던 모든 객체는 마킹이 끝날 때까지 계속 살아있는 것으로 간주합니다[1]. 이 방식의 함의는 명확합니다 — 마킹이 진행되는 도중에 죽은(unreachable이 된) 객체도 이번 회수 사이클에서는 살아있는 것으로 취급되어, 다른 컬렉터보다 다소 많은 메모리를 "잘못 붙잡고" 있을 수 있습니다. 대신 SATB는 Remark pause에서 더 나은 지연시간을 제공합니다[1]. 이것이 G1과 CMS가 근본적으로 갈라지는 지점 중 하나입니다 — CMS도 동시 마킹을 하지만 컴팩션(압축)을 하지 않는 반면, G1은 리전을 통째로 다른 리전으로 evacuate(퇴거)시키면서 압축과 회수를 동시에 수행합니다. Oracle의 Java 8 GC 튜닝 가이드는 이 차이를 다음과 같이 명시합니다: "G1은 힙의 한 개 이상의 리전에서 객체를 다른 하나의 리전으로 복사하는 과정에서 압축과 메모리 회수를 함께 수행한다 ... CMS(Concurrent Mark Sweep) 가비지 컬렉션은 컴팩션을 하지 않는다"[2]. 같은 문서는 G1을 "CMS의 장기적인 대체재로 계획되었다"고 명시하며, 컴팩션 여부와 pause 목표 지정 가능 여부를 핵심 차이로 꼽습니다[2]. 실제로 CMS는 JDK 9에서 사용 중단(JEP 291)이 예고된 뒤 JDK 14에서 완전히 제거되었습니다(JEP 363)[3][4].

### 4. Young-Only 단계에서 Mixed GC까지 — 실제 사이클

G1은 크게 두 국면을 오갑니다. **Young-Only 단계**는 Old 영역을 점진적으로 채워가는 일반적인 Young GC들로 구성되고, **Space-Reclamation 단계**는 Young GC에 더해 Old 영역 리전 일부까지 함께 회수하는 **Mixed GC**로 구성됩니다[1]. 두 국면의 전환은 Old 영역 점유율이 IHOP(Initiating Heap Occupancy Percent, `-XX:InitiatingHeapOccupancyPercent`, 기본 45%)에 도달하면 Concurrent Start 컬렉션으로 마킹이 시작되면서 트리거됩니다[1]. 마킹은 Remark와 Cleanup이라는 두 번의 STW pause로 마무리되고, Cleanup에서 회수할 가치가 있다고 판단되면 Space-Reclamation 단계가 시작됩니다[1]. Mixed GC는 매번 "최소 회수 진행을 보장하기 위한 최소 Old 리전 집합"과 "시간이 남으면 추가로 회수할 후보 리전"을 함께 골라 수집 대상(Collection Set)을 구성하며, `-XX:G1MixedGCCountTarget`(기본 8)으로 이 Mixed GC들을 몇 번에 걸쳐 나눠 수행할지 목표를 잡습니다[1]. 회수할 만큼의 공간이 안 나온다고 판단되면 Space-Reclamation 단계는 종료되고 다시 Young-Only 단계로 돌아갑니다[1].

### 5. `-XX:MaxGCPauseMillis`는 목표이지 보장이 아니다

여기가 실전에서 가장 많이 오해되는 지점입니다. Oracle 문서는 G1을 이렇게 설명합니다: "G1 컬렉터는 실시간(real-time) 컬렉터가 아니다. 높은 확률로, 더 긴 시간에 걸쳐 설정된 pause-time 목표를 만족시키려 시도하지만, 특정 pause에 대해 항상 절대적으로 보장하지는 않는다"[1]. `-XX:MaxGCPauseMillis`(기본값 200ms)의 공식 설명도 "최대 pause 시간에 대한 목표(goal)"이지 상한선 강제가 아닙니다[1]. G1은 이 목표를 맞추기 위해 `-XX:G1NewSizePercent`/`-XX:G1MaxNewSizePercent`로 제한된 범위 안에서 Young(Eden) 영역 크기를 적응적으로 조절합니다 — 과거 비슷한 크기의 Young 영역을 회수하는 데 걸린 시간, 복사해야 했던 객체 수, 객체 간 연결도 같은 과거 관측치를 근거로 삼습니다[1].

### 6. 실전 튜닝 함정 — 공격적인 pause 목표가 부르는 역효과

`-XX:MaxGCPauseMillis`를 애플리케이션 SLA에 맞춰 무작정 낮게(예: 50ms) 잡으면 어떻게 될까요? 위 메커니즘상 G1은 그 목표를 맞추기 위해 Eden 크기를 줄이는 방향으로 적응합니다. Eden이 작아지면 같은 할당 속도(allocation rate) 하에서 Eden이 더 빨리 차므로 **Young GC 빈도 자체가 늘어납니다** — pause 하나하나는 짧아질 수 있어도 전체 처리량(throughput)은 떨어지고, 애플리케이션이 GC에 뺏기는 시간의 총합은 오히려 늘 수 있습니다. 더 심각한 문제는 순간적으로 할당이 몰리는 트래픽 스파이크 상황입니다. Young GC가 Survivor/Old로 객체를 evacuate하려는 순간 목적지 공간이 부족하면 Evacuation Failure가 발생하고, 이는 GC 로그에 `Evacuation Failure: Allocation`(또는 `Pinned`)로 표시됩니다[1]. G1이 이번 GC에서 전혀 공간을 회수하지 못하는 최악의 경우, 힙 전체를 제자리 압축하는 Full GC로 폴백하는데 이는 매우 느릴 수 있습니다[1]. 즉 "pause를 짧게 만들려고" pause 목표를 지나치게 낮춘 설정이, 역설적으로 가장 느리고 긴 Full GC를 유발하는 방아쇠가 될 수 있다는 것이 이 튜닝 함정의 핵심입니다.

### 7. `-Xlog:gc*`로 실제로 진단하기

이 문제를 실제로 진단하려면 통합 로깅(Unified JVM Logging)을 켜야 합니다.

```bash
# JVM 시작 시 G1 GC를 명시하고, 통합 로깅으로 상세 GC 로그를 파일에 기록
java -XX:+UseG1GC -Xms2g -Xmx2g \
     -XX:MaxGCPauseMillis=200 \
     -XX:InitiatingHeapOccupancyPercent=45 \
     -XX:G1MixedGCCountTarget=8 \
     -Xlog:gc*:file=gc.log:time,uptime,level,tags \
     -jar app.jar

# Evacuation Failure까지 포함해 세부 단계별 시간을 보고 싶다면
java -XX:+UseG1GC -Xlog:gc*,gc+phases=info:file=gc.log:time,level,tags -jar app.jar
```

Oracle 문서가 제시하는 실제 Evacuation Failure 로그 예시는 다음과 같습니다[1]:

```
[9,740s][info ][gc] GC(26) Pause Young (Normal) (G1 Evacuation Pause) (Evacuation Failure: Allocation/Pinned) 2159M->402M(3000M) 6,108ms
```

`Pause Young (Normal)`은 순수 Young GC, `Pause Young (Concurrent Start)`은 마킹을 함께 시작하는 GC, `Pause Young (Mixed)`은 Old 리전까지 포함한 Mixed GC, `Pause Full`은 최후의 수단인 Full GC를 뜻합니다. 아래는 `MaxGCPauseMillis`를 지나치게 낮게 잡았을 때 로그에서 흔히 관찰되는 패턴을 예시로 재구성한 것입니다(실제 계측치가 아니라 위 메커니즘을 보여주기 위한 예시 로그입니다):

```
[10.021s] GC(140) Pause Young (Normal) (G1 Evacuation Pause) 1780M->1690M(2048M) 48,2ms
[10.093s] GC(141) Pause Young (Normal) (G1 Evacuation Pause) 1790M->1705M(2048M) 51,7ms
[10.151s] GC(142) Pause Young (Normal) (G1 Evacuation Pause) 1795M->1712M(2048M) 47,9ms
[10.244s] GC(143) Pause Young (Normal) (G1 Evacuation Pause) (Evacuation Failure: Allocation) 1802M->1798M(2048M) 210,4ms
```

이 예시처럼 `Pause Young (Normal)` 간격이 급격히 짧아지고(Eden이 작아 자주 찬다는 신호), 그러다 `Evacuation Failure: Allocation`이 섞여 나오기 시작하면 — Old 세대로 승격할 공간이 부족하다는 뜻이므로 — `MaxGCPauseMillis`를 완화하거나 `-Xmx`/`-XX:G1NewSizePercent` 하한을 올려 Eden에 여유를 주는 방향으로 재조정해야 합니다. GC 로그의 `->` 앞뒤 힙 점유율 변화 폭이 갈수록 줄어드는 것도 회수 여력이 줄고 있다는 보조 신호입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| G1은 힙을 균등한 크기의 리전으로 나누며, 기본 리전 크기는 최대 힙 크기 기준 약 2048개 리전이 나오도록 어고노믹스하게 결정되고 최대 32MB이다. `-XX:G1HeapRegionSize`로 지정 시 1~512MB 범위의 2의 거듭제곱 값이어야 한다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Garbage-First Garbage Collector" 챕터, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| G1은 리전별로 Remembered Set(RSet)을 관리하며, 512바이트 카드 단위로 리전 외부에서 들어오는 참조를 기록해 리전 단위 회수를 가능하게 한다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, 동일 챕터 "Remembered Set" 절, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| G1의 동시 마킹은 SATB(Snapshot-At-The-Beginning) 알고리즘을 사용하며, Concurrent Start pause 시점의 가상 스냅샷을 기준으로 그 시점에 살아있던 객체를 마킹 기간 내내 살아있는 것으로 간주한다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Marking" 절, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| G1은 Young-Only 단계와 Space-Reclamation 단계(Mixed GC)를 오가며, 전환은 Old 영역 점유율이 IHOP(기본 45%)에 도달할 때 트리거된다. `-XX:G1MixedGCCountTarget`(기본 8)은 Mixed GC를 몇 회에 걸쳐 수행할지의 목표치다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Garbage Collection Cycle" 및 "Space-Reclamation Phase" 절, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| `-XX:MaxGCPauseMillis`(기본 200ms)는 "최대 pause 시간에 대한 목표"일 뿐이며, G1은 "실시간 컬렉터가 아니고" 이 목표를 절대적으로 보장하지 않는다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Basic Concepts" 및 "Ergonomic Defaults" 절, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| G1은 `-XX:G1NewSizePercent`/`-XX:G1MaxNewSizePercent`로 제한된 범위 안에서 과거 회수 소요 시간 등을 근거로 Young(Eden) 영역 크기를 적응적으로 조절해 pause 목표를 맞추려 한다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Young-Only Phase Generation Sizing" 절, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| Evacuation Failure는 GC 로그에 `Evacuation Failure: Allocation` 또는 `Pinned`로 표시되며, G1이 전혀 공간을 회수하지 못하는 최악의 경우 힙 전체를 제자리 압축하는 Full GC로 폴백한다 | verified | Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide, "Evacuation Failure" 절 및 예시 로그, https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html |
| CMS(Concurrent Mark Sweep)는 컴팩션을 수행하지 않는 반면 G1은 리전 evacuate 과정에서 압축과 회수를 함께 수행하는 컴팩팅 컬렉터이며, G1은 CMS의 장기적 대체재로 계획되었다 | verified | Oracle, Java SE 8 HotSpot Garbage Collection Tuning Guide, "9 Garbage-First Garbage Collector", https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/g1_gc.html |
| CMS는 JDK 9에서 사용 중단(Deprecated)이 예고되었고(JEP 291) JDK 14에서 완전히 제거되었다(JEP 363) | verified | OpenJDK, "JEP 291: Deprecate the Concurrent Mark Sweep (CMS) Garbage Collector" / "JEP 363: Remove the Concurrent Mark Sweep (CMS) Garbage Collector", https://openjdk.org/jeps/291 , https://openjdk.org/jeps/363 |

## 작성자의 견해

> 이 섹션은 공식 문서의 사실 진술이 아니라, 그 사실들을 실무 튜닝 관점에서 재해석한 저의 개인적인 견해입니다.

공식 문서를 다 찾아봐도 "`MaxGCPauseMillis`를 너무 낮게 잡지 마라"는 직접적인 경고 문구는 어디에도 없습니다. 문서는 이 플래그가 "목표(goal)"라는 사실과, Eden 크기가 이 목표에 의해 제약된다는 메커니즘만 담담하게 설명할 뿐, 그 둘을 조합했을 때 벌어지는 부작용(Eden 축소 → Young GC 빈발 → 스파이크 상황에서 Evacuation Failure)은 사용자가 스스로 유추해야 합니다. 저는 이 지점이 G1 튜닝에서 가장 위험한 함정이라고 봅니다. SLA 문서에 "p99 GC pause 50ms 이하"라는 숫자가 적혀 있으면 튜닝 담당자는 반사적으로 `-XX:MaxGCPauseMillis=50`을 넣고 싶어지지만, 이 값은 상한을 강제하는 스위치가 아니라 G1의 내부 휴리스틱에 던지는 힌트에 가깝습니다. 오히려 힙 크기(`-Xmx`)를 워킹셋보다 넉넉히 잡고, `-XX:InitiatingHeapOccupancyPercent`를 낮춰 마킹을 더 일찍 시작하게 만들어 Mixed GC가 Old 영역을 미리미리 정리하도록 유도하는 편이, 무작정 pause 목표만 낮추는 것보다 실제 지연시간 안정성에 더 도움이 된다고 판단합니다. 다만 이건 어디까지나 문서에 근거해 추론한 튜닝 전략이며, 워크로드별로 실측 검증이 반드시 필요하다는 점은 분명히 해두고 싶습니다.

## 한계와 반론

본 아티클이 인용한 Evacuation Failure 로그 한 줄을 제외하면, "MaxGCPauseMillis를 낮췄을 때 Young GC 빈도가 실제로 몇 % 증가하는가" 같은 정량적 벤치마크 수치는 직접 측정하지 않았습니다. 7절의 4줄짜리 로그 예시도 명시했듯 실제 프로덕션 계측치가 아니라 메커니즘을 보여주기 위해 구성한 예시이므로, 독자가 자신의 워크로드에서 같은 패턴이 그대로 재현된다고 단정해서는 안 됩니다. 또한 `-XX:G1NewSizePercent`/`-XX:G1MaxNewSizePercent`의 정확한 기본값(%)은 이번 리서치에서 공식 문서 원문으로 명확히 확인하지 못해 본문에서 구체적인 숫자를 밝히지 않았습니다 — 실제 튜닝 시에는 `-XX:+PrintFlagsFinal`로 현재 JDK 버전의 실제 기본값을 직접 확인할 것을 권장합니다. 마지막으로 ZGC/Shenandoah처럼 더 낮은 지연시간을 목표로 하는 컬렉터와의 정량 비교, 그리고 컨테이너 cgroup 메모리 제한 환경에서의 G1 리전 크기 결정 방식은 이번 글의 범위 밖입니다.

## 참고문헌

1. Oracle, "HotSpot Virtual Machine Garbage Collection Tuning Guide — Garbage-First (G1) Garbage Collector" (JDK 25), [https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html](https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html) (확인일: 2026-08-23)
2. Oracle, "Java SE 8 HotSpot Virtual Machine Garbage Collection Tuning Guide — 9 Garbage-First Garbage Collector", [https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/g1_gc.html](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/g1_gc.html) (확인일: 2026-08-23)
3. OpenJDK, "JEP 291: Deprecate the Concurrent Mark Sweep (CMS) Garbage Collector", [https://openjdk.org/jeps/291](https://openjdk.org/jeps/291) (확인일: 2026-08-23)
4. OpenJDK, "JEP 363: Remove the Concurrent Mark Sweep (CMS) Garbage Collector", [https://openjdk.org/jeps/363](https://openjdk.org/jeps/363) (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션 역시 사실 나열이 아니라 전체 주제를 관통하는 제 나름의 해석을 담고 있습니다.

G1을 둘러싼 튜닝 논의는 결국 "리전이라는 단위를 도입해서 무엇을 얻었는가"라는 질문으로 수렴한다고 생각합니다. RSet은 힙 전체를 훑지 않고도 리전 하나를 안전하게 회수할 수 있게 해주고, SATB는 그 회수 판단을 애플리케이션을 멈추지 않고도(동시에) 내릴 수 있게 해주며, Mixed GC는 그렇게 확보한 유연성을 Old 영역까지 점진적으로 확장한 결과물입니다. CMS가 컴팩션을 포기하고 프래그먼테이션이라는 대가를 치렀던 것과 달리, G1은 애초에 리전을 evacuate하는 방식을 택해 회수와 압축을 한 번에 해결했고, 그 대가로 얻은 여유를 pause-time 목표라는 사용자 친화적 다이얼로 바꿔 내놓았습니다. 하지만 다이얼이 있다는 것과 그 다이얼을 마음대로 돌려도 안전하다는 것은 다른 이야기입니다. `MaxGCPauseMillis`는 Eden 크기라는 실제 자원을 깎아서 만들어내는 목표치이기 때문에, 목표를 낮추는 행위 자체가 공짜가 아니라는 사실을 이해하지 못하면 오히려 Full GC라는 최악의 결과로 이어질 수 있습니다. G1을 잘 쓴다는 것은 결국 "짧은 pause"라는 표면적 목표가 아니라 그 뒤에서 움직이는 리전·RSet·SATB·IHOP이라는 실제 메커니즘을 이해하고, 그것들이 서로 어떤 트레이드오프로 묶여 있는지를 로그로 검증하는 습관에 가깝다고 봅니다.

## 꼬리질문

1. **`-XX:G1NewSizePercent`/`-XX:G1MaxNewSizePercent`의 실제 기본값은 JDK 버전별로 어떻게 다르며, `-XX:+PrintFlagsFinal`로 확인했을 때 운영 중인 JDK에서는 실제로 어떤 값이 적용되고 있는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html
2. **`-XX:InitiatingHeapOccupancyPercent`를 낮춰 마킹을 더 일찍 시작시키는 전략이 실제로 CPU 오버헤드(동시 마킹 스레드 점유)와 지연시간 안정성 사이에서 어떤 트레이드오프를 만드는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html
3. **ZGC/Shenandoah는 G1과 달리 컬러 포인터·로드 배리어 방식으로 Evacuation Failure에 해당하는 상황 자체를 어떻게 원천적으로 회피하는가?**
   - 추천 참고 URL: https://docs.oracle.com/en/java/javase/25/gctuning/z-garbage-collector.html

## 백링크

- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)
- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)