---
id: "5197370985728599772"
title: "동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의"
slug: "sync-vs-async-blocking-vs-non-blocking"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/sync-vs-async-blocking-vs-non-blocking.html"
publishedAt: "2026-08-11T09:54:07.059-07:00"
updatedAt: "2026-08-13T21:02:28.387-07:00"
tags: ["Architecture","AsyncIO","ComputerScience","Networking","OperatingSystem"]
---

# 동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의

## 동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의

## 요약

개발 현장에서 빈번히 오용되는 동기/비동기(Synchronous/Asynchronous)와 블로킹/논블로킹(Blocking/Non-blocking)의 차이를 관점(Dimension) 분리를 통해 명확하게 정리합니다. 블로킹/논블로킹은 **"호출된 함수가 제어권을 즉시 반환하는가(대기 여부)"**에 관한 시스템 콜 관점이며, 동기/비동기는 **"작업의 완료 통지 주체와 결과 순서를 누가 처리하는가(동기화 여부)"**에 관한 흐름 제어 관점입니다. 이 두 축을 결합한 2x2 매트릭스(Sync-Blocking, Sync-Nonblocking, Async-Blocking, Async-Nonblocking)의 작동 방식과 실제 Linux `epoll`, Java NIO 등 아키텍처 사례를 다룹니다.

목차

- [1. 서론: 실행 흐름과 제어권의 혼란](#1-서론-실행-흐름과-제어권의-혼란)

- [2. 제어권과 작업 완료 통지: 동기(Synchronous) vs 비동기(Asynchronous)](#2-제어권과-작업-완료-통지-동기synchronous-vs-비동기asynchronous)

- [3. 제어권의 주도권과 대기 상태: 블로킹(Blocking) vs 논블로킹(Non-blocking)](#3-제어권의-주도권과-대기-상태-블로킹blocking-vs-논블로킹non-blocking)

- [4. 4가지 조합 매트릭스 분석](#4-4가지-조합-매트릭스-분석)

- [5. 실무 아키텍처 및 OS 레벨 적용 예시](#5-실무-아키텍처-및-os-레벨-적용-예시)

- [6. 결론: 올바른 I/O 모델 선택과 아키텍처 가이드](#6-결론-올바른-io-모델-선택과-아키텍처-가이드)

## 본문

### 1. 서론: 실행 흐름과 제어권의 혼란

소프트웨어 아키텍처 설계와 고성능 네트워크 서버 구축 시 "동기/비동기"와 "블로킹/논블로킹"이라는 용어는 혼용되기 일쑤입니다 [[1]][[3]]. 많은 개발자가 '동기=블로킹', '비동기=논블로킹'으로 동일시하지만, 이는 서로 다른 차원(Dimension)의 기술 사상을 하나로 뭉뚱그린 오해에서 비롯됩니다. 시스템의 I/O 병목을 해결하고 대규모 동시성을 확보하기 위해서는 제어권(Control)과 작업 완료(Completion)라는 두 가지 관점을 정확히 분리해야 합니다.

### 2. 제어권과 작업 완료 통지: 동기(Synchronous) vs 비동기(Asynchronous)

동기(Synchronous)와 비동기(Asynchronous)를 나누는 핵심 기준은 **"작업 완료의 주체 및 결과 처리의 순서 일치 여부"**입니다 [[1]][[2]].

- **동기(Synchronous)**: 작업을 요청한 호출자(Caller)가 작업의 진행 상태나 완료 여부를 직접 신경 쓰고 챙기는 방식입니다 . 호출된 함수가 결과를 반환할 때까지 대기하거나, 주기적으로 작업 완료를 확인(Polling)하면서 작업 완료 시점에 맞춰 다음 로직을 순차적으로 실행합니다 [[1]].

- **비동기(Asynchronous)**: 작업을 요청할 때 완료 시 실행될 콜백(Callback)이나 시그널(Signal)을 함께 전달하고, 호출자는 즉시 자신의 다음 코드를 실행합니다. 작업을 이행하는 피호출자(Callee/OS 커널)가 작업이 완료되면 이벤트 알림이나 콜백을 호출하여 완료를 통지합니다 [[2]].

특히 POSIX 및 W. Richard Stevens의 *UNIX Network Programming* 정의에 의하면, Kernel 공간의 데이터를 User 공간 메모리로 복사하는 과정에 애플리케이션 스레드가 직접 대기하거나 관여한다면 그것은 모두 **동기(Synchronous) I/O**로 분류됩니다  [[1]]. 반면 진정한 **비동기(Asynchronous) I/O**는 Kernel이 유저 버퍼로의 메모리 복사까지 완료한 후 애플리케이션에 완수 통지를 보냅니다  [[1]][[2]].

### 3. 제어권의 주도권과 대기 상태: 블로킹(Blocking) vs 논블로킹(Non-blocking)

블로킹(Blocking)과 논블로킹(Non-blocking)의 구별 기준은 **"호출된 함수(시스템 콜)가 제어권을 즉시 반환하는가"**입니다  [[1]][[3]].

- **블로킹(Blocking)**: A 함수가 B 함수를 호출하면, B 함수는 자신의 작업이 끝날 때까지 제어권을 쥐고 돌아오지 않습니다. A 함수는 제어권을 상실하여 B 작업이 완료될 때까지 실행을 멈추고 대기 상태(Wait State)에 빠집니다 [[1]][[3]].

- **논블로킹(Non-blocking)**: A 함수가 B 함수를 호출할 때, B 함수는 작업의 완료 여부와 상관없이 즉시 제어권(과 에러 코드 또는 미완료 상태값, 예: `EWOULDBLOCK`)을 A에게 반환합니다 [[1]]. A 함수는 제어권을 유지한 채 곧바로 다음 코드를 실행할 수 있습니다 [[3]].

### 4. 4가지 조합 매트릭스 분석

동기/비동기 축과 블로킹/논블로킹 축을 조합하면 총 4가지 형태의 I/O 처리 매트릭스가 완성됩니다 [[1]][[2]][[3]][[5]].

  구 분
  블로킹 (Blocking)
  논블로킹 (Non-blocking)

  **동기 (Sync)**
  **Sync-Blocking**(가장 흔한 직렬식 모델)
  **Sync-Nonblocking**(폴링 기반 완료 대기 모델)

  **비동기 (Async)**
  **Async-Blocking**(의도치 않은 병목/의존 모델)
  **Async-Nonblocking**(최고 성능의 이벤트 드라이븐 모델)

- **Sync-Blocking (동기 + 블로킹)**: 호출자는 제어권을 넘겨주고 작업 완료 시까지 대기합니다. C 언어의 표준 `read()`, 전통적인 Java InputStream 등 대부분의 기본 I/O가 이에 해당합니다 [[1]].

- **Sync-Nonblocking (동기 + 논블로킹)**: 호출자가 B를 호출하면 B는 즉시 제어권을 반환합니다. 그러나 호출자는 B의 작업이 완료되었는지 주기적으로 확인(Polling)하는 루프를 돈다 . Java NIO의 초기 Selector 폴링 구조나 POSIX non-blocking read 루프가 이 형태입니다 [[1]][[5]].

- **Async-Blocking (비동기 + 블로킹)**: 비동기로 콜백을 전달하며 요청했지만, 하위 Layer나 라이브러리가 블로킹 요소(예: Blocking DB Driver)를 포함하여 결과적으로 호출 스레드가 대기하게 되는 비효율적 상태입니다 [[2]].

- **Async-Nonblocking (비동기 + 논블로킹)**: 호출 시 제��권을 즉시 반환받으며, 작업 완수와 데이터 복사까지 커널이 끝낸 후 콜백으로 알림을 받습니다. Linux의 POSIX AIO/`io_uring`, Windows의 IOCP, Node.js의 libuv asynchronous I/O 작업이 이에 해당합니다 [[2]][[3]].

### 5. 실무 아키텍처 및 OS 레벨 적용 예시

고성능 서버엔진(NGINX, Netty, Node.js)은 Linux의 `epoll` 및 Java NIO와 같은 I/O Multiplexing 기법을 활용합니다 [[4]][[5]].

Linux `epoll` 시스템 콜은 수만 개의 Socket 소켓 연결을 효율적으로 감시합니다 [[4]]. 이때 `epoll` 자체는 I/O 준비 여부를 알릴 때까지 `epoll_wait()`에서 대기하므로 동기(Sync)적 감시 모델입니다. 하지만 감시 대상 소켓을 Non-blocking으로 설정하고, Edge-Triggered(ET) 모드에서는 `EAGAIN` 에러가 반환될 때까지 소켓 버퍼 데이터를 반복하여 읽어들입니다  [[4]]. 이로써 한 스레드가 대량의 소켓 I/O를 논블로킹으로 전담 처리하는 이벤트 루프 구조를 달성합니다 [[4]][[5]].

### 6. 결론: 올바른 I/O 모델 선택과 아키텍처 가이드

시스템 구축 시 동기/비동기와 블로킹/논블로킹을 정확히 구분하여 설계해야 합니다 [[2]][[3]]. CPU 연산 집중형 작업(CPU-bound)에는 굳이 복잡한 Async-Nonblocking을 도입하기보다 멀티스레드 Sync 모델이 유리할 수 있지만, 수만 개의 동시 접속을 처리해야 하는 I/O 집중형(I/O-bound) 애플리케이션에서는 Async-Nonblocking 및 I/O Multiplexing 아키텍처 선택이 필수적입니다 [[2]][[3]].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무 개발자들이 가장 자주 겪는 혼란은 '고수준 언어의 syntactic sugar(예: JavaScript의 `async/await`)'를 사용할 때 발생합니다. `async/await` 코��는 문법적으로 동기식 코드처럼 읽히지만 내부적으로 프로미스 객체와 이벤트 루프를 사용하는 비동기-논블로킹 처리를 수행합니다. 언어 수준의 표현 방식과 OS 디바이스 드라이버 수준의 I/O 동작 원리를 독립된 레이어로 구분해서 바라보는 직관이 필수적입니다.

## 한계와 반론

- **개념적 엄밀함과 실무 용어 간의 격차**: POSIX 기준으로는 `select`/`poll`/`epoll`을 사용하는 I/O 멀티플렉싱도 "커널->유저 메모리 데이터 복사 동안 스레드가 기다리므로 Synchronous Non-blocking I/O"로 분류되나, Node.js나 Netty 개발 환경에서는 이를 상위 수준에서 묶어 "Async I/O Architecture"라고 통칭하는 경우가 많습니다.

- **성능의 트레이드오프**: Async-Nonblocking 아키텍처가 항상 빠른 것은 아닙니다. 요청 처리량이 적거나 단일 실행 작업 위주의 시스템에서는 이벤트 루프 관리 및 Context Switching 오버헤드로 인해 오히려 전통적인 Sync-Blocking 모델보다 복잡도만 높아지고 성능 이점이 적을 수 있습니다.

## 종합적 의견

> 

이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

동기/비동기, 블로킹/논블로킹은 단순한 취향의 차이가 아니라 애플리케이션의 자원 효율성(Resource Utilization)을 결정짓는 핵심 설계 패러다임입니다. 현대 클라우드 네이티브 아키텍처에서는 무거운 OS 스레드 생성을 최소화하고, 단일 스레드 혹은 소수의 링 버퍼 기반 스레드로 대량의 I/O를 처리하는 방향으로 진화하고 있습니다. 따라서 이 두 가지 축의 의미를 명확히 판별하고 적재적소에 I/O 모델을 배치하는 능력이 엔지니어의 핵심 역량이 될 것입니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- W. Richard Stevens, *UNIX Network Programming, Volume 1 (3rd Edition)*, Addison-Wesley. ([<https://man7.org/linux/man-pages/man7/epoll.7.html](https://man7.org/linux/man-pages/man7/epoll.7.html)>)

- M. Tim Jones, *Boost application performance using asynchronous I/O*, IBM Developer. ([<https://developer.ibm.com/articles/l-async/](https://developer.ibm.com/articles/l-async/)>)

- Node.js Foundation, *Overview of Blocking vs Non-Blocking*, Node.js Official Guides. ([<https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/](https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/)>)

- Linux Man-pages Project, *epoll(7) - Linux Programmer's Manual*. ([<https://man7.org/linux/man-pages/man7/epoll.7.html](https://man7.org/linux/man-pages/man7/epoll.7.html)>)

- Oracle Corporation, *Java New I/O (NIO) Architecture & Non-blocking I/O*. ([<https://docs.oracle.com/javase/8/docs/technotes/guides/io/index.html](https://docs.oracle.com/javase/8/docs/technotes/guides/io/index.html)>)
