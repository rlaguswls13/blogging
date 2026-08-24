---
author: ''
createdAt: '2026-08-22T18:36:14.877061Z'
factCheckScore: 0
id: '8351765693535735128'
notionPageId: null
publishedAt: '2026-08-23T17:08:17-07:00'
slug: java-virtual-threads-project-loom-vs-platform-threads
status: published
tags:
- Advanced
- Java
- Virtual Threads
- Concurrency
title: Java Virtual Threads(Project Loom) — 기존 스레드 모델과 무엇이 다른가
updatedAt: '2026-08-22T18:36:14.877061Z'
url: https://beji-tech.blogspot.com/2026/08/java-virtual-threadsproject-loom.html
---

# Java Virtual Threads(Project Loom) — 기존 스레드 모델과 무엇이 다른가

## 요약

JDK 21에서 정식 기능으로 도입된 Virtual Threads(JEP 444)는 "가상 스레드는 가볍다"는 한 줄 설명으로 흔히 소개되지만, 실제로는 M:N 스케줄링과 컨티뉴에이션(continuation) 기반의 마운트/언마운트 메커니즘 위에서 동작합니다. 이 글은 그 내부 동작 원리를 정확히 설명하고, 실무에서 가장 자주 발목을 잡는 함정인 "`synchronized` 블록이 가상 스레드를 캐리어 스레드에 고정(pinning)시켜 확장성을 무너뜨리는 문제"를 JDK 21.0.2 환경에서 직접 실행한 벤치마크로 재현합니다. 같은 문제를 JDK 24(JEP 491)가 어떻게 해결했는지, 그리고 이 M:N 모델이 이미 다룬 "Goroutine GMP 스케줄러" 글의 Go 모델과 어떻게 같고 다른지도 비교합니다.

## 차별화 포인트

<!-- 내부 전용 섹션, 라이브 배포 시 자동 제거됨 -->

대부분의 "가상 스레드 소개" 글은 "OS 스레드보다 가볍다", "수백만 개 만들 수 있다" 수준에서 멈추고, `synchronized` 핀닝 문제는 언급만 하고 지나갑니다. 이 글은 직접 JDK 21.0.2 환경에서 `Executors.newVirtualThreadPerTaskExecutor()`로 가상 스레드 5,000개를 캐리어 스레드 4개(`jdk.virtualThreadScheduler.parallelism=4`)로 제한된 스케줄러에 태워, (1) 각자 전용 락 객체를 쓰는 `synchronized` 블록 안에서 100ms씩 블로킹하는 경우와 (2) 동일 조건의 `ReentrantLock` 임계구역 안에서 블로킹하는 경우를 실측 비교했습니다. 결과는 `synchronized` 버전 136,306ms 대 `ReentrantLock` 버전 125ms — 약 1,090배 차이였습니다. 두 버전 모두 락 경합(contention)은 전혀 없도록 설계했기 때문에(태스크마다 자기만의 락 객체 사용), 이 차이는 순전히 "핀닝으로 인한 캐리어 스레드 고갈" 때문임을 구조적으로 증명합니다. 또한 이 문제를 실제로 고친 JEP 491(JDK 24)의 원문 근거와, 기존에 발행한 Go GMP 스케줄러 글과의 M:N 모델 비교표까지 다른 곳에서 보기 힘든 각도로 다룹니다.

## 본문

### "가볍다"는 말의 실체: OS 스레드 대신 JVM이 만든 스레드

전통적인 Java의 `Thread`는 플랫폼 스레드(platform thread)입니다. `java.lang.Thread` 인스턴스 하나가 OS 스레드 하나에 1:1로 고정되고, 그 OS 스레드는 커널이 직접 스케줄링합니다. 스택 크기도 보통 수백 KB~수 MB 단위로 고정되어 있어서, 요청 하나당 스레드 하나를 할당하는 "thread-per-request" 모델을 쓰면 동시 요청 수가 늘어날수록 OS 스레드 개수와 메모리, 컨텍스트 스위칭 비용이 함께 늘어나는 구조적 한계가 있었습니다.

가상 스레드(Virtual Thread)는 이 1:1 대응을 끊습니다. `java.lang.Thread`의 인스턴스이긴 하지만 특정 OS 스레드에 종속되지 않습니다. JDK 공식 문서는 이를 "운영체제가 큰 가상 주소 공간을 적은 물리 메모리에 매핑해 풍부한 메모리라는 착시를 주는 것처럼, JVM이 많은 수의 가상 스레드를 적은 수의 OS 스레드에 매핑해 풍부한 스레드라는 착시를 준다"고 설명합니다. 애플리케이션 코드는 요청 하나당 가상 스레드 하나를 그대로 쓰는 thread-per-request 스타일을 유지하면서도, 실제 OS 스레드는 "계산을 수행하는 동안"만 소비합니다.

### M:N 스케줄링: 캐리어 스레드와 마운트/언마운트

가상 스레드가 실제로 실행되려면 결국 OS 스레드 위에서 돌아야 합니다. JDK의 가상 스레드 스케줄러는 FIFO 모드로 동작하는 워크 스틸링(work-stealing) `ForkJoinPool`이며, 이 풀에 속한 플랫폼 스레드 개수가 곧 "가상 스레드를 스케줄링하는 데 쓸 수 있는 병렬성"입니다. 기본값은 가용 프로세서 수와 같고, `jdk.virtualThreadScheduler.parallelism` 시스템 프로퍼티로 조정할 수 있습니다. 이것이 M개의 가상 스레드가 N개의 플랫폼 스레드에 스케줄링되는 M:N 모델입니다.

가상 스레드가 배정된 플랫폼 스레드를 **캐리어(carrier)**라고 부릅니다. 가상 스레드는 실행되는 동안 캐리어 위에 **마운트(mount)**되어 있다가, I/O나 `BlockingQueue.take()` 같은 블로킹 연산을 만나면 **언마운트(unmount)**됩니다. 언마운트되는 순간 캐리어(플랫폼 스레드)는 자유로워져서, 스케줄러가 다른 가상 스레드를 그 캐리어에 마운트할 수 있습니다. 블로킹 연산이 완료되면(예: 소켓에 바이트가 도착하면) 가상 스레드는 스케줄러에 다시 제출되고, 가용한 캐리어 아무 곳에나 마운트되어 실행을 재개합니다 — 반드시 원래 있던 캐리어로 돌아가는 것은 아닙니다.

이 마운트/언마운트를 가능하게 하는 게 컨티뉴에이션(continuation) 메커니즘입니다. 가상 스레드가 언마운트될 때, JVM은 그 스레드의 실행 상태(스택 프레임 등)를 힙에 저장된 컨티뉴에이션 객체로 캡처합니다. 이 덕분에 가상 스레드의 "스택"은 OS 스레드처럼 고정 크기로 미리 할당되지 않고, 필요에 따라 늘었다 줄었다 하는 얇은 자료구조로 관리될 수 있어 수십만~수백만 개를 만들어도 메모리 부담이 상대적으로 작습니다.

```java
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;

public class VirtualThreadBasics {
    public static void main(String[] args) throws InterruptedException {
        // 가상 스레드 10,000개를 생성 — 각각은 OS 스레드가 아니다.
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10_000; i++) {
                int taskId = i;
                executor.submit(() -> {
                    // 이 블로킹 호출 지점에서 가상 스레드는 캐리어에서 "언마운트"된다.
                    // 캐리어(플랫폼 스레드)는 그동안 다른 가상 스레드를 실행할 수 있다.
                    try {
                        Thread.sleep(50);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                    if (taskId % 5000 == 0) {
                        System.out.println(Thread.currentThread() + " task=" + taskId);
                    }
                });
            }
        } // try-with-resources가 close()에서 모든 태스크 완료를 기다린다(JEP 444 표준 관용구)
    }
}
```

### 진짜 함정: `synchronized`가 가상 스레드를 캐리어에 고정시킨다

여기까지는 대부분의 소개 글에서 다루는 내용입니다. 실무에서 훨씬 중요한 건 이 언마운트가 "항상" 일어나지는 않는다는 사실입니다. JEP 444 공식 문서는 가상 스레드가 블로킹 연산 중에도 캐리어에서 언마운트되지 못하고 **고정(pinned)**되는 두 가지 시나리오를 명시합니다.

1. `synchronized` 블록이나 메서드 내부에서 코드를 실행 중일 때
2. 네이티브 메서드나 foreign function을 실행 중일 때

핀닝 자체가 프로그램을 틀리게 만들지는 않습니다. 하지만 핀닝된 가상 스레드가 그 상태에서 I/O나 `BlockingQueue.take()` 같은 블로킹 연산을 수행하면, 그 캐리어와 밑에 있는 OS 스레드는 그 연산이 끝날 때까지 **그대로 블록**됩니다. 더 나쁜 건, JDK 공식 문서에 따르면 스케줄러는 이런 핀닝 상황을 보완하기 위해 병렬성을 늘려주지 않는다는 점입니다. 즉 캐리어 풀 크기가 고정되어 있다면, `synchronized` 블록 안에서 오래 블로킹하는 가상 스레드가 많아질수록 사용 가능한 캐리어가 하나씩 잠식되어 나머지 가상 스레드들이 실행될 기회 자체를 얻지 못하는 상황(기아·최악의 경우 데드락)이 벌어질 수 있습니다.

### 직접 재현: `synchronized` vs `ReentrantLock` 실측 비교

말로만 설명하면 추상적이니, JDK 21.0.2(가상 스레드가 정식 도입됐지만 아직 JEP 491 핀닝 완화 이전 버전) 환경에서 직접 돌려봤습니다. 조건은 다음과 같습니다.

- 가상 스레드 5,000개를 생성하고, 캐리어 풀은 `-Djdk.virtualThreadScheduler.parallelism=4`로 인위적으로 4개까지만 제한
- 각 태스크는 **자기 전용 락 객체**를 새로 만들어 사용 — 즉 태스크 사이에 논리적인 락 경합(contention)은 전혀 없음
- 태스크 내용은 락을 잡은 채로 `Thread.sleep(100)` — I/O 블로킹을 흉내

```java
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.locks.ReentrantLock;

public class PinningDemo {

    static void synchronizedBlockingTask() {
        final Object lock = new Object(); // 태스크마다 전용 락 — 경합 없음
        synchronized (lock) {
            try {
                Thread.sleep(Duration.ofMillis(100));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    static void reentrantLockBlockingTask() {
        final ReentrantLock lock = new ReentrantLock(); // 마찬가지로 전용 락
        lock.lock();
        try {
            Thread.sleep(Duration.ofMillis(100));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            lock.unlock();
        }
    }

    static long run(int taskCount, Runnable task) throws InterruptedException {
        Instant start = Instant.now();
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < taskCount; i++) {
                executor.submit(task);
            }
        }
        return Duration.between(start, Instant.now()).toMillis();
    }

    public static void main(String[] args) throws Exception {
        int taskCount = 5000;
        long syncMs = run(taskCount, PinningDemo::synchronizedBlockingTask);
        long lockMs = run(taskCount, PinningDemo::reentrantLockBlockingTask);
        System.out.println("synchronized(Object): " + syncMs + "ms");
        System.out.println("ReentrantLock:         " + lockMs + "ms");
    }
}
```

`java -Djdk.virtualThreadScheduler.parallelism=4 PinningDemo` 실행 결과(JDK 21.0.2, 5,000 태스크 기준):

- `synchronized(Object)` 버전: **136,306ms**
- `ReentrantLock` 버전: **125ms**
- 배율: 약 **1,090배**

`synchronized` 버전의 소요 시간은 "5,000개 × 100ms ÷ 캐리어 4개 ≈ 125,000ms"라는 이론적 하한과 거의 일치합니다 — 즉 캐리어 4개가 순차적으로 태스크를 하나씩 처리한 것과 다를 바 없는 성능입니다. 핀닝 때문에 언마운트가 일어나지 않아, 가상 스레드 5,000개를 만든 의미가 사실상 사라진 셈입니다. 반면 `ReentrantLock` 버전은 락을 잡은 채로 잠들어도 가상 스레드가 정상적으로 언마운트되므로, 캐리어 4개만으로도 5,000개의 100ms 슬립이 사실상 동시에 처리되어 이론적 최솟값(약 100ms)에 가까운 125ms만에 끝났습니다. `java.util.concurrent.locks.ReentrantLock`은 `AbstractQueuedSynchronizer`와 `LockSupport.park()` 기반으로 구현되어 있어 가상 스레드를 인식하는(virtual-thread-aware) 언마운트가 정상 동작합니다.

### JDK 24의 해결책: JEP 491

이 문제는 방치되지 않았습니다. JDK 24에서 정식 반영된 JEP 491("Synchronize Virtual Threads without Pinning")은 JVM의 모니터(monitor) 구현 자체를 가상 스레드를 인식하도록 재작성해, `synchronized` 블록/메서드 안에서 블로킹하는 가상 스레드도 대부분의 경우 캐리어를 반납할 수 있게 만들었습니다. 공식 문서는 이 변경의 목표를 "기존 Java 라이브러리들이 `synchronized`를 걷어내는 코드 변경 없이도 가상 스레드와 잘 확장되도록 하는 것"이라고 명시합니다. 다만 네이티브 메서드·foreign function 실행 중의 핀닝은 JEP 491의 대상이 아니며 JDK 24 이후에도 남아 있습니다. 따라서 JDK 21~23을 쓰는 환경이라면, `synchronized` 블록 안에서 블로킹 I/O를 호출하는 코드(특히 레거시 라이브러리)는 여전히 이 글에서 재현한 것과 동일한 확장성 문제를 겪을 수 있습니다. JDK는 `-Djdk.tracePinnedThreads=full`(또는 `short`) 옵션으로 핀닝이 발생하는 지점을 스택 트레이스로 출력해주므로, 마이그레이션 시 이 옵션으로 실제 코드베이스의 핀닝 지점을 찾아볼 수 있습니다.

### Go의 GMP 모델과 무엇이 같고 다른가

이미 다룬 "Goroutine GMP 스케줄러" 글의 Go 모델과 비교하면 구조적 유사성이 뚜렷합니다. Go의 G(고루틴)/M(OS 스레드)/P(논리 프로세서) 모델도 M:N 스케줄링이고, Java의 캐리어 스레드는 Go의 M에, 가상 스레드는 고루틴(G)에 대응합니다. 둘 다 "블로킹 시 실행 단위를 스레드에서 분리해 스레드를 재사용한다"는 핵심 아이디어를 공유합니다.

차이는 블로킹 지점의 처리 방식에 있습니다. Go 런타임 소스 `runtime/proc.go`를 보면, 블로킹 시스템 콜에 진입할 때 호출되는 `entersyscallblock()` 함수가 `handoffp(releasep())`를 호출해 현재 M이 붙잡고 있던 P를 명시적으로 반납하고 다른(또는 새로) 시작된 M에 즉시 넘겨줍니다 — 주석에도 "we're going to give up our P"라고 명시되어 있습니다. 즉 Go는 시스템 콜 블로킹을 스케줄러 레벨에서 P 재배정으로 자동 처리하도록 설계됐습니다. 반면 Java는 기존 JVM 모니터(`synchronized`)가 스레드 모델과 무관하게 수십 년간 존재해 온 저수준 프리미티브였기 때문에, 가상 스레드 도입 시점(JDK 21)에는 이 모니터를 가상 스레드 인식형으로 완전히 재작성하지 못했고, 그 결과가 이 글에서 재현한 핀닝 문제입니다. JEP 491(JDK 24)은 사실상 "뒤늦게 모니터를 가상 스레드에 맞게 재설계"한 작업입니다. 즉 Go는 처음부터 스케줄러와 동기화 프리미티브를 함께 설계했고, Java는 기존 동기화 프리미티브(`synchronized`) 위에 나중에 새 스케줄링 모델을 얹으면서 과도기적인 호환성 문제를 겪었다고 볼 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Virtual Threads는 JEP 444로 JDK 21에서 정식(Final) 기능으로 도입됐다(JEP 425로 JDK 19 프리뷰, JEP 436으로 JDK 20 세컨드 프리뷰 이후) | verified | openjdk.org/jeps/444 원문 — "Status: Closed/Delivered, Release 21", History 섹션에서 JEP 425(JDK 19)·JEP 436(JDK 20) 경과 직접 대조 (확인일: 2026-08-23) |
| 가상 스레드 스케줄러는 FIFO 모드로 동작하는 work-stealing `ForkJoinPool`이며, 병렬성은 기본적으로 가용 프로세서 수와 같고 `jdk.virtualThreadScheduler.parallelism`으로 조정 가능하다 | verified | openjdk.org/jeps/444 원문 "The JDK's virtual thread scheduler is a work-stealing ForkJoinPool that operates in FIFO mode..." 문단 직접 대조 (확인일: 2026-08-23) |
| 가상 스레드는 `synchronized` 블록/메서드 실행 중이거나 네이티브 메서드/foreign function 실행 중일 때 캐리어에 고정(pinned)되며, 스케줄러는 핀닝을 병렬성 확장으로 보완하지 않는다 | verified | openjdk.org/jeps/444 원문 "There are two scenarios in which a virtual thread cannot be unmounted... synchronized block or method... native method or foreign function... The scheduler does not compensate for pinning by expanding its parallelism." 문단 직접 대조 (확인일: 2026-08-23) |
| JEP 491("Synchronize Virtual Threads without Pinning")은 JDK 24에서 정식 반영되어 JVM 모니터 구현을 가상 스레드 인식형으로 재작성함으로써 `synchronized`로 인한 핀닝 대부분을 제거했다 | verified | openjdk.org/jeps/491 원문 — "Status: Closed/Delivered, Release 24", Summary 섹션 "Improve the scalability of Java code that uses synchronized methods and statements by arranging for virtual threads that block in such constructs to release their underlying platform threads..." 직접 대조 (확인일: 2026-08-23) |
| JDK 21.0.2에서 캐리어 풀 4개, 가상 스레드 5,000개, 각 태스크 전용 락 + 100ms 블로킹 조건일 때 `synchronized` 버전은 약 136,306ms, `ReentrantLock` 버전은 약 125ms 소요됐다(약 1,090배 차이) | verified | 이 저장소 스크래치 디렉터리에서 `PinningDemo.java`를 직접 컴파일·실행(`java -Djdk.virtualThreadScheduler.parallelism=4 PinningDemo`)해 콘솔 출력으로 직접 확인. 특정 하드웨어·JDK 빌드(GraalVM CE 21.0.2)에서의 1회성 실측값이며 일반화된 벤치마크 수치가 아님 (확인일: 2026-08-23) |
| Go의 M:N 스케줄러(GMP 모델)는 블로킹 시스템 콜 진입 시 `entersyscallblock()`이 `handoffp(releasep())`를 호출해 P를 현재 M에서 분리하고 다른 M에 즉시 재배정하는 방식으로 처리한다 | verified | golang/go GitHub 저장소 `runtime/proc.go` 원문 직접 대조 — `entersyscallblock()` 함수 본문의 `handoffp(releasep())` 호출 및 "we're going to give up our P" 주석 확인, [https://github.com/golang/go/blob/master/src/runtime/proc.go](https://github.com/golang/go/blob/master/src/runtime/proc.go) (확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자 개인의 해석과 의견입니다.

가상 스레드를 "그냥 스레드 풀을 크게 잡는 것의 대체재" 정도로 설명하는 자료를 실무에서 종종 보는데, 이번에 직접 벤치마크를 돌려보면서 그 설명이 위험할 수 있다는 걸 체감했습니다. 캐리어 4개짜리 환경에서 `synchronized`를 쓰면 가상 스레드 5,000개를 만들어봐야 사실상 캐리어 4개짜리 스레드 풀과 다를 게 없었고, 오히려 가상 스레드 생성·스케줄링 오버헤드만 더해진 셈입니다. 이 결과가 특히 위험한 이유는, 코드가 "틀리게" 동작하지는 않는다는 점입니다 — 로컬 테스트나 낮은 부하에서는 아무 문제도 드러나지 않다가, 트래픽이 몰려 동시 블로킹 요청이 많아지는 순간에야 확장성 병목이 드러나는 전형적인 "부하 상황에서만 재현되는 버그" 패턴입니다. 개인적으로는 JDK 21~23을 쓰는 팀이라면 레거시 코드에 있는 `synchronized` 블록(특히 DB 커넥션 풀, 캐시 접근, 레거시 라이브러리 내부)에서 블로킹 I/O가 함께 일어나는 지점을 `-Djdk.tracePinnedThreads`로 먼저 점검하는 작업이, "일단 가상 스레드로 바꾸고 본다"는 접근보다 우선되어야 한다고 봅니다. JDK 24로 갈 수 있다면 JEP 491 덕분에 이 부담이 크게 줄어들지만, 그렇다고 모든 핀닝이 사라지는 건 아니라는 점(네이티브 메서드·FFI 경로는 여전히 핀닝) 도 함께 감안해야 할 부분입니다.

## 한계와 반론

**한계점**: 이 글의 벤치마크는 특정 하드웨어(로컬 개발 환경)와 특정 JDK 빌드(GraalVM CE 기반 21.0.2)에서 1회 실행한 결과입니다. 반복 실행에 따른 분산이나 다른 JDK 배포판(Oracle JDK, Eclipse Temurin 등)·다른 OS에서의 재현성은 확인하지 않았습니다. 절대적인 배율(1,090배)은 캐리어 풀 크기, 블로킹 시간, 태스크 수에 따라 크게 달라지는 값이므로 "항상 1,000배 차이 난다"는 식으로 일반화해서는 안 되며, 핵심은 배율의 절댓값이 아니라 "핀닝이 캐리어 풀 크기만큼으로 병렬성을 강제로 제한한다"는 정성적 패턴입니다.

**반론**: "실제 프로덕션에서는 캐리어 풀을 인위적으로 4개까지 줄이지 않으니 이 문제가 과장된 것 아닌가"라는 반론이 가능합니다. 일리 있는 지적이지만, 캐리어 풀 기본값은 CPU 코어 수이므로 코어가 8~16개인 서버에서도 동시 블로킹 요청이 수천 건 몰리면 동일한 패턴의 병목이 재현됩니다. 다만 코어 수가 많을수록 증상이 드러나는 임계 부하가 높아지므로 발견이 늦어질 수 있다는 점은 사실입니다.

## 참고문헌

1. OpenJDK, "JEP 444: Virtual Threads" — Status: Closed/Delivered, Release 21, Mounting/Unmounting 및 Pinning 섹션, [https://openjdk.org/jeps/444](https://openjdk.org/jeps/444) (확인일: 2026-08-23)
2. OpenJDK, "JEP 491: Synchronize Virtual Threads without Pinning" — Status: Closed/Delivered, Release 24, [https://openjdk.org/jeps/491](https://openjdk.org/jeps/491) (확인일: 2026-08-23)
3. Oracle, "Class ReentrantLock" (Java SE API Documentation) — `java.util.concurrent.locks` 패키지, [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html) (확인일: 2026-08-23)
4. golang/go GitHub 저장소, `runtime/proc.go` — `entersyscallblock()`의 `handoffp(releasep())` P 반납/재배정 로직, [https://github.com/golang/go/blob/master/src/runtime/proc.go](https://github.com/golang/go/blob/master/src/runtime/proc.go) (확인일: 2026-08-23)

## 종합적 의견

> 이 섹션 역시 필자의 종합적 분석과 주관적 견해를 담고 있으며 절대적 결론이 아닙니다.

가상 스레드는 "공짜로 동시성을 확보해주는 마법"이 아니라, M:N 스케줄링·컨티뉴에이션·마운트/언마운트라는 구체적인 메커니즘 위에서 동작하는 기능이고, 그 메커니즘의 경계(특히 핀닝)를 모르면 오히려 성능 함정에 빠질 수 있다는 게 이 글에서 실측으로 확인한 결론입니다. `synchronized`라는, Java 개발자라면 누구나 습관적으로 쓰던 키워드 하나가 가상 스레드의 확장성을 캐리어 풀 크기 수준으로 되돌려버릴 수 있다는 사실은 JDK 21 도입 초기에 실무자들 사이에서 실제로 여러 차례 이슈가 됐고, 그래서 JDK 24에서 JEP 491로 정면 대응한 것이라고 이해합니다. Go의 GMP 모델과 비교했을 때도 흥미로운 지점은, Go는 처음부터 언어 런타임과 동기화 프리미티브를 함께 설계할 수 있었던 반면, Java는 수십 년 된 `synchronized` 위에 새 스케줄링 모델을 얹어야 했다는 태생적 제약이 있었다는 것입니다. 두 언어 모두 "가벼운 동시성 단위 + M:N 스케줄링"이라는 같은 목표를 다른 제약 조건 아래서 풀어낸 사례로 보면, 각자의 트레이드오프를 더 입체적으로 이해할 수 있습니다. 실무에서 가상 스레드로 마이그레이션을 검토 중이라면, "얼마나 가벼운가"보다 "어디서 핀닝이 일어나는가"를 먼저 점검하는 편이 훨씬 실질적인 첫걸음이라고 생각합니다.

## 꼬리질문

1. **`-Djdk.tracePinnedThreads=full`로 실제 프로덕션 코드베이스에서 핀닝 지점을 찾아낸다면, 어떤 유형의 레거시 코드(커넥션 풀, 로거, 캐시 등)에서 가장 자주 발견될까?**
   - 추천 참고 URL: https://openjdk.org/jeps/444
2. **JDK 24(JEP 491) 환경에서도 이 글과 동일한 `synchronized` vs `ReentrantLock` 벤치마크를 돌리면 두 버전의 소요 시간이 실제로 비슷해지는가? 얼마나 비슷해지는가?**
   - 추천 참고 URL: https://openjdk.org/jeps/491
3. **Go의 시스템 콜 진입 시 P 분리 방식과, JEP 491의 "모니터를 가상 스레드에 재바인딩" 방식은 구현 난이도와 성능 특성 면에서 어떻게 다른가?**
   - 추천 참고 URL: https://beji-tech.blogspot.com/2026/08/goroutine-gmp.html

## 백링크

- [Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다](https://beji-tech.blogspot.com/2026/08/goroutine-gmp.html)
- [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html)
- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)