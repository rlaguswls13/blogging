# 동기(Sync) vs 비동기(Async) & 블로킹(Blocking) vs 논블로킹(Non-blocking)의 명확한 정의

개발 현장에서 빈번히 오용되는 동기/비동기(Synchronous/Asynchronous)와 블로킹/논블로킹(Blocking/Non-blocking)의 차이를 관점(Dimension) 분리를 통해 명확하게 정리합니다.

## 1. 제어권과 작업 완료 통지: 동기(Synchronous) vs 비동기(Asynchronous)

동기(Synchronous)와 비동기(Asynchronous)를 나누는 핵심 기준은 **"작업 완료의 주체 및 결과 처리의 순서 일치 여부"**입니다.

- **동기(Synchronous)**: 작업을 요청한 호출자(Caller)가 작업의 진행 상태나 완료 여부를 직접 신경 쓰고 챙기는 방식입니다. 호출된 함수가 결과를 반환할 때까지 대기하거나, 주기적으로 작업 완료를 확인(Polling)하면서 작업 완료 시점에 맞춰 다음 로직을 순차적으로 실행합니다.
- **비동기(Asynchronous)**: 작업을 요청할 때 완료 시 실행될 콜백(Callback)이나 시그널(Signal)을 함께 전달하고, 호출자는 즉시 자신의 다음 코드를 실행합니다. 작업을 이행하는 피호출자(Callee/OS 커널)가 작업이 완료되면 이벤트 알림이나 콜백을 호출하여 완료를 통지합니다.

특히 POSIX 및 W. Richard Stevens의 *UNIX Network Programming* 정의에 의하면, Kernel 공간의 데이터를 User 공간 메모리로 복사하는 과정에 애플리케이션 스레드가 직접 대기하거나 관여한다면 그것은 모두 **동기(Synchronous) I/O**로 분류됩니다. 반면 진정한 **비동기(Asynchronous) I/O**는 Kernel이 유저 버퍼로의 메모리 복사까지 완료한 후 애플리케이션에 완수 통지를 보냅니다.

## 2. 제어권의 주도권과 대기 상태: 블로킹(Blocking) vs 논블로킹(Non-blocking)

블로킹(Blocking)과 논블로킹(Non-blocking)의 구별 기준은 **"호출된 함수(시스템 콜)가 제어권을 즉시 반환하는가"**입니다.

- **블로킹(Blocking)**: A 함수가 B 함수를 호출하면, B 함수는 자신의 작업이 끝날 때까지 제어권을 쥐고 돌아오지 않습니다. A 함수는 제어권을 상실하여 B 작업이 완료될 때까지 실행을 멈추고 대기 상태(Wait State)에 빠집니다.
- **논블로킹(Non-blocking)**: A 함수가 B 함수를 호출할 때, B 함수는 작업의 완료 여부와 상관없이 즉시 제어권(과 에러 코드 또는 미완료 상태값, 예: `EWOULDBLOCK`)을 A에게 반환합니다. A 함수는 제어권을 유지한 채 곧바로 다음 코드를 실행할 수 있습니다.

## 3. 4가지 조합 매트릭스 분석

동기/비동기 축과 블로킹/논블로킹 축을 조합하면 총 4가지 형태의 I/O 처리 매트릭스가 완성됩니다.

| 구 분 | 블로킹 (Blocking) | 논블로킹 (Non-blocking) |
| :--- | :--- | :--- |
| **동기 (Sync)** | **Sync-Blocking**<br>(가장 흔한 직렬식 모델) | **Sync-Nonblocking**<br>(폴링 기반 완료 대기 모델) |
| **비동기 (Async)** | **Async-Blocking**<br>(의도치 않은 병목/의존 모델) | **Async-Nonblocking**<br>(최고 성능의 이벤트 드라이븐 모델) |

1. **Sync-Blocking (동기 + 블로킹)**: 호출자는 제어권을 넘겨주고 작업 완료 시까지 대기합니다. C 언어의 표준 `read()`, 전통적인 Java InputStream 등 대부분의 기본 I/O가 이에 해당합니다.
2. **Sync-Nonblocking (동기 + 논블로킹)**: 호출자가 B를 호출하면 B는 즉시 제어권을 반환합니다. 그러나 호출자는 B의 작업이 완료되었는지 주기적으로 확인(Polling)하는 루프를 돕니다. Java NIO의 초기 Selector 폴링 구조나 POSIX non-blocking read 루프가 이 형태입니다.
3. **Async-Blocking (비동기 + 블로킹)**: 비동기로 콜백을 전달하며 요청했지만, 하위 Layer나 라이브러리가 블로킹 요소(예: Blocking DB Driver)를 포함하여 결과적으로 호출 스레드가 대기하게 되는 비효율적 상태입니다.
4. **Async-Nonblocking (비동기 + 논블로킹)**: 호출 시 제어권을 즉시 반환받으며, 작업 완수와 데이터 복사까지 커널이 끝낸 후 콜백으로 알림을 받습니다. Linux의 POSIX AIO/`io_uring`, Windows of IOCP, Node.js의 libuv asynchronous I/O 작업이 이에 해당합니다.

## 4. 실무 적용 및 OS 레벨 예시

고성능 서버엔진(NGINX, Netty, Node.js)은 Linux의 `epoll` 및 Java NIO와 같은 I/O Multiplexing 기법을 활용합니다.

Linux `epoll` 시스템 콜은 수만 개의 Socket 소켓 연결을 효율적으로 감시합니다. 이때 `epoll` 자체는 I/O 준비 여부를 알릴 때까지 `epoll_wait()`에서 대기하므로 동기(Sync)적 감시 모델입니다. 하지만 감시 대상 소켓을 Non-blocking으로 설정하고, Edge-Triggered(ET) 모드에서는 `EAGAIN` 에러가 반환될 때까지 소켓 버퍼 데이터를 반복하여 읽어들입니다. 이로써 한 스레드가 대량의 소켓 I/O를 논블로킹으로 전담 처리하는 이벤트 루프 구조를 달성합니다.

## 5. 결론 및 선택 가이드

시스템 구축 시 동기/비동기와 블로킹/논블로킹을 정확히 구분하여 설계해야 합니다. CPU 연산 집중형 작업(CPU-bound)에는 굳이 복잡한 Async-Nonblocking을 도입하기보다 멀티스레드 Sync 모델이 유리할 수 있지만, 수만 개의 동시 접속을 처리해야 하는 I/O 집중형(I/O-bound) 애플리케이션에서는 Async-Nonblocking 및 I/O Multiplexing 아키텍처 선택이 필수적입니다.

## 관련 문서
- [위키 인덱스](README.md)
