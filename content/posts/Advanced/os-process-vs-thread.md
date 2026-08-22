---
id: '5933790533382613955'
publishedAt: '2026-08-15T19:16:32.606-07:00'
slug: os-process-vs-thread
status: published
tags:
- concurrency
- memory
- operatingsystem
- process
- thread
- Advanced
title: OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리
updatedAt: '2026-08-15T19:18:51.826-07:00'
url: https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html
---

# OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리

> 

**TL;DR**: **프로세스(Process)**는 운영체제로부터 독립된 메모리 공간(Code, Data, Heap, Stack)을 할당받는 작업의 단위이고, **쓰레드(Thread)**는 프로세스 내부에서 `Stack` 영역만 독점하고 `Code`, `Data`, `Heap` 영역을 공유하는 실행의 흐름입니다. 프로세스 간 컨텍스트 스위칭은 TLB 캐시 플러시와 가상 메모리 매핑 전환으로 인해 높은 오버헤드가 발생하는 반면, 쓰레드 간 스위칭은 메모리 공간을 공유하므로 레지스터 세트 변경만으로 빠르게 이루어집니다.

---

## 요약

현대 멀티태스킹 운영체제 환경에서 프로세스와 쓰레드의 메모리 자원 분리 및 공유 아키텍처를 이해하는 것은 고성능 동시성 서버 설계의 시작점입니다. 본 문서에서는 두 실행 단위의 메모리 영역 구조, 컨텍스트 스위칭 메커니즘, 동시성 동기화 이슈, 그리고 실무 적용 레시피를 상세히 살펴봅니다.

---

## 본문

### 1. 개요 및 왜 필요한가? (Background & Motivation)

서버 애플리케이션의 요청 처리 모델을 설계할 때 멀티 프로세스 모델(예: PostgreSQL)을 선택할지, 멀티 쓰레드 모델(예: Java Netty, WebFlux)을 선택할지에 따라 메모리 사용량, 격리성(Isolation), 동시성 락(Lock) 경합 및 컨텍스트 스위칭 오버헤드가 크게 달라집니다.

---

### 2. 메모리 구조 아키텍처 비교 (Memory Architecture)

#### 2.1 프로세스의 독립 메모리 구조

각 프로세스는 운영체제로부터 독립된 4GB(32비트 기준) 또는 256TB(64비트 가상 주소 공간 기준)의 독자적인 가상 메모리 공간을 할당받습니다. 다른 프로세스의 메모리 영역에 직접 접근할 수 없으며, 접근 시 `Segmentation Fault` 에러가 발생합니다.

#### 2.2 쓰레드의 공유 메모리 구조

동일한 프로세스 내에서 생성된 멀티 쓰레드는 프로세스의 `Code`, `Data`, `Heap` 영역을 공유하며, 오직 각 쓰레드의 함수 호출 추적 및 지역 변수 보관을 위한 독자적인 **`Stack` 영역**만을 할당받습니다.

graph TD
    subgraph Process1 ["프로세스 1 (Process A)"]
        P1_Code["Code 영역 (기계어 코드)"]
        P1_Data["Data 영역 (전역/정적 변수)"]
        P1_Heap["Heap 영역 (동적 할당 객체)"]
        
        subgraph P1_Threads ["프로세스 A 전용 쓰레드"]
            P1_T1["Thread 1 Stack (지역변수/스택프레임)"]
            P1_T2["Thread 2 Stack (지역변수/스택프레임)"]
        end
    end

    subgraph Process2 ["프로세스 2 (Process B - 독립 공간)"]
        P2_Code["Code 영역 (독립)"]
        P2_Data["Data 영역 (독립)"]
        P2_Heap["Heap 영역 (독립)"]
        P2_Stack["Thread 1 Stack (독립)"]
    end

#### 2.3 프로세스 vs 쓰레드 영역별 상세 자원 공유 비교

  메모리 영역
  프로세스 간 공유 여부
  쓰레드 간 공유 여부
  주요 역할 및 저장되는 데이터

  **Code (Text)**
  ❌ 불가능 (독립)
  ⭕ 공유
  실행될 컴파일된 기계어 프로그램 명령어 코드

  **Data / BSS**
  ❌ 불가능 (독립)
  ⭕ 공유
  전역 변수(Global Variable), 정적 변수(Static Variable)

  **Heap**
  ❌ 불가능 (독립)
  ⭕ 공유
  `malloc()` 또는 `new` 키워드로 동적 할당되는 객체 자원

  **Stack**
  ❌ 불가능 (독립)
  ❌ **독점 (비공유)**
  함수 호출 시 생성되는 스택 프레임, 지역 변수, 매개변수

  **Register Set**
  ❌ 불가능 (독립)
  ❌ **독점 (비공유)**
  PC(Program Counter), SP(Stack Pointer) 등 CPU 상태값

---

### 3. 컨텍스트 스위칭(Context Switching) 내부 동작 원리

컨텍스트 스위칭은 CPU가 한 프로세스/쓰레드에서 다른 프로세스/쓰레드로 제어권을 넘길 때 현재 레지스터 상태를 저장하고 새로운 상태를 복원하는 과정입니다.

sequenceDiagram
    participant CPU as CPU 레지스터
    participant P1 as Process A (PCB A)
    participant OS as Kernel Scheduler
    participant P2 as Process B (PCB B)

    P1->>OS: 1. 인터럽트/시스템 콜 발생
    OS->>P1: 2. Process A 상태를 PCB A에 저장
    OS->>OS: 3. 메모리 매핑 전환 & TLB Cache Flush (오버헤드 발생)
    OS->>P2: 4. PCB B에서 Process B 레지스터 상태 복원
    P2->>CPU: 5. Process B 실행 재개

#### 3.1 프로세스 컨텍스트 스위칭 (Process Context Switching)

- **높은 오버헤드**:
CPU 레지스터 저장 및 **PCB(Process Control Block)** 업데이트

- 페이지 테이블 Base Register(CR3) 교체로 인한 **가상 메모리 주소 공간 전환**

- **TLB(Translation Lookaside Buffer) 캐시 완전 플러시(Flush)** ➔ 스위칭 직후 Cache Miss 집중 발생

#### 3.2 쓰레드 컨텍스트 스위칭 (Thread Context Switching)

- **낮은 오버헤드**:
CPU 레지스터 세트(PC, SP) 저장 및 **TCB(Thread Control Block)** 업데이트

- 메모리 주소 공간(페이지 테이블)을 전환할 필요가 없음

- **TLB 캐시가 유효하게 유지됨** ➔ 캐시 미스로 인한 메모리 딜레이 최소화

---

### 4. 실무 멀티 쓰레드 구현 예제 (Complete Runnable Code)

아래 예제는 Java 언어로 작성된 완전 구동 가능한 코드로, 멀티 쓰레드가 프로세스의 공유 메모리(`Heap` 영역의 객체 상태)를 동시에 수정할 때 발생하는 **경합 조건(Race Condition)**과 이를 방지하는 동기화 메커니즘을 명확히 보여줍니다.

`package com.example.concurrency;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 프로세스 내 쓰레드 간 Heap 공유 메모리 동시성 검증 예제
 */
public class ProcessThreadMemoryDemo {

    // 쓰레드들이 공유하는 Process Heap 영역의 데이터
    private static int sharedUnsafeCounter = 0;
    private static final AtomicInteger sharedSafeCounter = new AtomicInteger(0);

    public static void main(String[] args) throws InterruptedException {
        int threadCount = 10;
        int loopCount = 1000;
        CountDownLatch latch = new CountDownLatch(threadCount);

        System.out.println("=== 멀티 쓰레드 공유 메모리 동시 접근 테스트 시작 ===");
        System.out.println("생성된 쓰레드 수: " + threadCount + "개, 쓰레드당 가산 횟수: " + loopCount + "회");

        for (int i = 0; i < threadCount; i++) {
            new Thread(() -> {
                try {
                    for (int j = 0; j < loopCount; j++) {
                        // 1. 비동기화 경합 발생 (Unsafe)
                        sharedUnsafeCounter++;
                        // 2. 원자적 동기화 처리 (Safe)
                        sharedSafeCounter.incrementAndGet();
                    }
                } finally {
                    latch.countDown();
                }
            }).start();
        }

        latch.await();

        System.out.println("\n=== 실행 완료 결과 (Expected Output) ===");
        System.out.println("기대되는 총 카운트 수: " + (threadCount * loopCount));
        System.out.println("비동기화 공유 변수 결과 (Unsafe Counter): " + sharedUnsafeCounter + " (경합으로 소실 가능)");
        System.out.println("원자적 동기화 공유 변수 결과 (Safe Counter): " + sharedSafeCounter.get() + " (100% 정합성 보장)");
    }
}
`

#### 💻 실행 콘솔 결과 (Expected Output)

```
`=== 멀티 쓰레드 공유 메모리 동시 접근 테스트 시작 ===
생성된 쓰레드 수: 10개, 쓰레드당 가산 횟수: 1000회

=== 실행 완료 결과 (Expected Output) ===
기대되는 총 카운트 수: 10000
비동기화 공유 변수 결과 (Unsafe Counter): 8742 (경합으로 소실 가능)
원자적 동기화 공유 변수 결과 (Safe Counter): 10000 (100% 정합성 보장)
`
```

---

## 작성자의 견해

본 포스팅에서 다룬 프로세스와 쓰레드의 메모리 영역 분리 및 컨텍스트 스위칭 비용 모델은 전통적인 OS 커널 구조에 기초하고 있습니다. 본 설명은 단순한 사실 전달이 아니라 작성자의 해석과 견해를 바탕으로 작성되었습니다.

---

## 한계와 반론

- **한계**: OS 커널 스케줄러 구현(Linux CFS vs Windows Thread Scheduler)에 따라 실제 측정되는 스위칭 오버헤드 지표는 CPU 캐시 라인 크기 및 NUMA 아키텍처 구조에 따라 달라질 수 있습니다.

- **반론**: 유저 공간(User Space)에서 협동조합형으로 동작하는 경량 쓰레드(Goroutine, Java Virtual Thread)는 커널 수준의 컨텍스트 스위칭을 우회하므로 쓰레드의 Stack 독점 구조 특성을 유지하면서도 스위칭 비용을 수십 나노초 단위로 단축시킵니다.

---

## 종합적 의견

프로세스는 완벽한 메모리 격리성과 안정성을 제공하는 대신 스위칭 오버헤드가 크며, 쓰레드는 메모리 자원 효율성과 빠른 스위칭 속도를 제공하는 대신 세심한 동시성 동기화 처리가 필수적입니다. 시스템의 동시성 요구사항과 안정성 타협점을 명확히 분석하여 아키텍처를 결정해야 합니다.

---

  📚 참고문헌 (클릭하여 열기)
  
    

- [Linux Kernel Memory Management Architecture](https://www.kernel.org/doc/html/latest/admin-guide/mm/index.html)

- [POSIX Threads (pthreads) Programming Specification](https://man7.org/linux/man-pages/man7/pthreads.7.html)

- [Intel 64 and IA-32 Architectures Software Developer Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)

---

## 백링크

- [Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다](https://beji-tech.blogspot.com/2026/08/goroutine-gmp.html)
- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)
- [Kafka 파티셔닝의 한계와 극복: 동시성과 순서 연속성을 동시에 보장하는 아키텍처 설계 전략](https://beji-tech.blogspot.com/2026/08/kafka.html)