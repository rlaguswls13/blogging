---
author: ''
createdAt: '2026-08-19T06:18:53Z'
factCheckScore: 0
id: '5557901429706920976'
notionPageId: null
publishedAt: '2026-08-22T06:11:09-07:00'
slug: goroutine-gmp-scheduler-channel-mutex
status: published
tags:
- Advanced
- Go
- Goroutine
- Concurrency
- Scheduler
title: Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다
updatedAt: '2026-08-19T06:18:53Z'
url: https://beji-tech.blogspot.com/2026/08/goroutine-gmp.html
---

# Goroutine GMP 스케줄러 내부 동작 원리와 '완전 락 프리'라는 오해 — 채널은 실제로 뮤텍스를 쓴다

## 요약

Go의 동시성 모델은 "가벼운 고루틴 수백만 개를 OS 스레드 몇 개로 돌린다"는 것으로 유명합니다. 이걸 가능하게 하는 게 GMP 스케줄러(Goroutine/Machine/Processor)입니다. 그런데 실무자들 사이에서도 "Go 채널은 락 프리(lock-free)로 동작한다"는 통념이 꽤 퍼져 있습니다. 이 글은 GMP 모델의 로컬/글로벌 실행 큐와 워크 스틸링(Work Stealing) 동작 원리를 Go 런타임 소스코드(`runtime2.go`, `proc.go`, `chan.go`) 기준으로 설명하고, "채널이 완전히 락 프리"라는 통념이 실제로는 틀렸다는 것을 `chan.go` 원문 코드로 직접 반증합니다. Go 채널은 내부에 실제 뮤텍스(`hchan.lock`)를 갖고 있고, 모든 송수신 연산이 이 락을 획득합니다.

## 차별화 포인트

<!-- 내부 전용 섹션, 라이브 배포 시 자동 제거됨 -->

"Go 채널은 락 프리다"라는 실무자들 사이의 흔한 통념을 golang/go 저장소의 `runtime/chan.go` 원문 소스코드(`hchan` 구조체의 `lock mutex` 필드, `chansend`의 `lock(&c.lock)` 호출)로 직접 반증하는 게 이 글의 핵심 차별화다. 대부분의 "GMP 스케줄러 설명" 글은 G/M/P 개념도만 그리고 끝나지만, 이 글은 `runtime2.go`의 `p` 구조체 필드(로컬 큐 `runq [256]guintptr`)와 `proc.go`의 `findRunnable()` 락 최적화 패턴까지 실제 Go 런타임 소스를 인용해, "그렇다더라" 수준의 통념을 코드 레벨 증거로 검증한다.

## 본문

### GMP 모델: G, M, P는 각각 무엇인가

Go 스케줄러는 세 종류의 엔티티로 구성됩니다.

- **G (Goroutine)**: `go func(){...}()`로 만드는 경량 실행 단위입니다. 스택은 처음 2KB로 작게 시작해 필요에 따라 늘어납니다(OS 스레드의 기본 스택은 보통 수 MB 단위인 것과 대조적입니다).
- **M (Machine)**: 실제 OS 스레드입니다. 커널이 스케줄링하는 단위이며, 고루틴을 실제로 실행하는 주체입니다.
- **P (Processor)**: 논리 프로세서입니다. "G를 실행할 권한과 자원(로컬 실행 큐, 메모리 캐시 `mcache` 등)"을 갖고 있으며, M이 G를 실행하려면 반드시 P를 하나 붙잡고 있어야 합니다. P의 개수는 기본적으로 CPU 코어 수와 같고 `GOMAXPROCS` 환경변수로 조정할 수 있습니다.

이 구조 덕분에 Go는 고루틴 하나마다 OS 스레드를 하나씩 만드는 대신, M:N(M개의 OS 스레드가 N개의 고루틴을 나눠 실행) 모델로 동작합니다. 초기 Go(1.0)는 P 없이 G와 M만 있는 GM 모델이었는데, 전역 락 경합이 심해 확장성이 떨어졌습니다. Go 1.1부터 Dmitry Vyukov가 제안한 P(logical processor) 개념이 도입되면서 지금의 GMP 모델이 됐습니다.

```go
package main

import (
    "fmt"
    "runtime"
)

func main() {
    // GOMAXPROCS는 P(논리 프로세서)의 개수를 결정한다
    fmt.Println("GOMAXPROCS:", runtime.GOMAXPROCS(0))
    fmt.Println("NumCPU:", runtime.NumCPU())
}
```

### 로컬 실행 큐 vs 글로벌 실행 큐

각 P는 자신만의 **로컬 실행 큐(Local Run Queue)**를 갖고 있습니다. Go 런타임 소스 `runtime/runtime2.go`의 `p` 구조체를 보면 이 큐가 어떻게 구현돼 있는지 정확히 확인할 수 있습니다.

```go
// runtime/runtime2.go의 p 구조체 일부 (필드명은 실제 소스와 동일)
type p struct {
    // ...
    runqhead uint32
    runqtail uint32
    runq     [256]guintptr // 로컬 실행 큐: 256개 고정 크기 원형 버퍼
    runnext  guintptr      // 방금 준비된(ready) G를 최우선으로 실행하기 위한 슬롯
    // ...
}
```

로컬 큐는 **256개 고정 크기의 원형 버퍼(circular buffer)**입니다. `runqhead`/`runqtail`로 앞뒤를 관리하는 구조라, M이 자기 P의 큐에서 G를 꺼낼 때는 다른 P와 락을 다툴 필요가 없습니다(단, 다른 P가 이 큐를 "훔쳐갈" 때는 원자적 CAS 연산으로 경합을 처리합니다). 로컬 큐가 가득 차면 새로 생성된 G의 절반은 **글로벌 실행 큐(Global Run Queue)**로 밀려납니다. 글로벌 큐는 모든 P가 공유하므로, 접근할 때는 스케줄러 전역 락(`sched.lock`)을 잡아야 합니다. `runtime/proc.go`의 `findRunnable` 함수에서 글로벌 큐를 확인하는 부분은 다음과 같은 패턴을 씁니다.

```go
// runtime/proc.go findRunnable() 내부 패턴(실제 소스 기준)
if sched.runqsize != 0 {
    lock(&sched.lock)
    gp := globrunqget(_p_, 0)
    unlock(&sched.lock)
    if gp != nil {
        return gp, false
    }
}
```

`sched.runqsize != 0`를 락 없이 먼저 확인한 뒤, 실제로 큐에 뭔가 있을 때만 락을 잡는 최적화입니다 — 매번 락을 걸었다 풀면 글로벌 큐가 비어있을 때도 불필요한 락 경합 비용이 들기 때문입니다. Go 스케줄러는 로컬 큐만 계속 우선시하면 글로벌 큐에 있는 G가 영원히 실행되지 못하는 기아(starvation) 상태를 막기 위해, 로컬 큐를 확인하기 전에 주기적으로 글로벌 큐를 먼저 들여다보는 공정성(fairness) 로직도 갖고 있습니다.

### 워크 스틸링(Work Stealing): 노는 P가 바쁜 P의 일을 훔쳐온다

자기 로컬 큐도 비어 있고 글로벌 큐도 비어 있는 P(정확히는 그 P를 붙잡은 M)는 그냥 놀지 않습니다. 다른 P의 로컬 큐를 훔쳐옵니다(Work Stealing) — 보통 대상 P가 가진 G의 절반가량을 가져옵니다. 이 방식 덕분에 특정 P에만 작업이 몰리는 불균형을 중앙 조정자 없이 각 P가 스스로 해소합니다. 훔쳐올 대상이 전혀 없으면 네트워크 폴러(netpoller)를 확인해 I/O 준비가 끝난 G가 있는지 보고, 그마저 없으면 M은 스핀(spin) 후 잠들어 다음에 깨울 일이 생길 때까지 대기합니다.

```go
package main

import (
    "fmt"
    "sync"
)

func worker(id int, wg *sync.WaitGroup) {
    defer wg.Done()
    fmt.Printf("worker %d 실행 중\n", id)
}

func main() {
    var wg sync.WaitGroup
    // 고루틴 1000개를 만들면, 런타임이 GOMAXPROCS개의 P에
    // 이들을 분배하고, 유휴 P는 다른 P의 큐에서 일을 훔쳐온다
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go worker(i, &wg)
    }
    wg.Wait()
}
```

### 채널은 "락 프리"가 아니다 — `chan.go` 원문으로 직접 확인

Go 채널이 락 프리 자료구조로 동작한다는 이야기를 종종 듣게 됩니다. "고루틴처럼 가볍고 특별한 방식으로 동기화되니까 락이 없을 것"이라는 직관 때문인 것 같습니다. 하지만 이는 사실이 아닙니다. Go 런타임 소스 `runtime/chan.go`를 보면, 채널의 내부 구조체 `hchan`이 명시적으로 뮤텍스 필드를 갖고 있습니다.

```go
// runtime/chan.go (실제 소스 기준)
type hchan struct {
    qcount   uint           // 큐에 쌓인 데이터 개수
    dataqsiz uint           // 버퍼 채널의 순환 큐 크기
    buf      unsafe.Pointer // 버퍼 채널의 데이터 저장 공간
    elemsize uint16
    // ... (생략) ...
    recvq    waitq          // recv 대기 중인 고루틴들의 큐
    sendq    waitq          // send 대기 중인 고루틴들의 큐

    lock mutex // lock protects all fields in hchan,
               // as well as several fields in sudogs blocked on this channel.
}
```

주석이 명확합니다 — "`lock`은 `hchan`의 모든 필드와, 이 채널에 블록된 `sudog`들의 여러 필드까지 보호한다." 그리고 실제 송신(`chansend`)과 수신(`chanrecv`) 함수는 임계 구역에 들어가기 전에 이 락을 명시적으로 획득합니다.

```go
// runtime/chan.go chansend() 내부 패턴(실제 소스 기준)
func chansend(c *hchan, ep unsafe.Pointer, block bool, callerpc uintptr) bool {
    // ... (락 없이 처리 가능한 예외 케이스들은 먼저 걸러냄) ...
    lock(&c.lock)
    // 여기서부터 임계 구역: 버퍼 상태 확인, 대기 중인 리시버에게 직접 전달 등
    // ...
    unlock(&c.lock)
    return true
}
```

즉 Go 채널은 "락이 전혀 없는" 자료구조가 아니라, **뮤텍스로 보호되는 큐 + 대기 고루틴 리스트(`sendq`/`recvq`)** 조합입니다. 다만 완전히 근거 없는 통념은 아닙니다 — 채널 송수신이 항상 무거운 OS 레벨 뮤텍스처럼 동작하는 건 아니고, 경합이 없는(uncontended) 상황에서는 짧게 스핀(spin)하며 빠르게 락을 잡고 푸는 최적화가 들어가 있어 대부분의 상황에서 체감 오버헤드가 작습니다. 하지만 "락이 아예 없다"는 것과 "락이 있지만 최적화가 잘 돼 있다"는 것은 다른 이야기이고, 코드상으로는 명백히 후자입니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| GMP 모델은 G(고루틴)/M(OS 스레드)/P(논리 프로세서) 세 엔티티로 구성되며, P는 Go 1.1에서 Dmitry Vyukov가 제안해 도입됐다(그 이전은 P 없는 GM 모델) | verified | Dmitry Vyukov, "Scalable Go Scheduler Design Doc"(Go 1.1 설계 문서, 2012-05-02) 서지정보 및 복수 2차 자료 교차 확인 |
| P의 로컬 실행 큐는 `runq [256]guintptr` — 256개 고정 크기 원형 버퍼로 구현되어 있다 | verified | golang/go GitHub 저장소 `runtime/runtime2.go`의 `type p struct` 정의 원문 직접 대조 |
| 글로벌 실행 큐 접근 시 `sched.runqsize != 0`를 락 없이 먼저 확인한 뒤 실제로 값이 있을 때만 `sched.lock`을 획득하는 최적화가 있다 | verified | golang/go GitHub 저장소 `runtime/proc.go`의 `findRunnable()` 함수 코드 패턴 직접 대조 |
| Go 채널의 내부 구조체 `hchan`은 `lock mutex` 필드를 가지며, `chansend`/`chanrecv` 모두 이 락을 명시적으로 획득·해제한다 — 즉 채널은 "완전히 락 프리"가 아니다 | verified | golang/go GitHub 저장소 `runtime/chan.go`의 `hchan` 구조체 정의 및 `chansend`/`chanrecv` 함수 코드 원문 직접 대조 |
| 워크 스틸링은 유휴 P가 다른 P의 로컬 큐에서 절반가량의 G를 훔쳐오는 방식으로 동작한다 | verified | rakyll.org(전 Go 팀 멤버 JBD 개인 기술 블로그), 복수 2차 자료 교차 확인 — 공식 소스코드 원문 직접 대조는 이번 조사에서 하지 못해 Tier3 출처로 표기 |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 "채널이 락 프리라서 빠르다"는 설명을 자료구조 선택 근거로 드는 경우를 종종 보는데, 이건 절반만 맞는 이야기입니다. 채널이 빠른 이유는 락이 없어서가 아니라, 경합이 없는 흔한 경우에 대해 락 획득·해제 경로가 짧고 스핀 최적화가 잘 돼 있기 때문입니다. 이 차이는 사소해 보이지만 실무 판단에 영향을 줍니다 — 예를 들어 "채널은 락이 없으니 고빈도 경합 상황에서도 `sync.Mutex`보다 항상 빠를 것"이라고 가정하고 설계하면, 실제로는 채널 내부의 `hchan.lock` 경합이 그대로 병목이 될 수 있습니다. Go 공식 위키의 "Use a sync.Mutex or a channel?" 문서도 "고루틴 소유권을 명확히 옮기거나 여러 고루틴이 동일 자료구조에 대해 경쟁할 때는 채널, 단순히 캐시나 상태를 보호할 때는 뮤텍스"라는 실용적 기준을 제시하는데, 이 기준이 "채널=락 없음, 뮤텍스=락 있음"이라는 이분법이 아니라 "어떤 동시성 패턴에 어떤 도구가 자연스러운가"라는 설계 문제라는 걸 보여줍니다. GMP 스케줄러의 로컬/글로벌 큐 구조도 마찬가지로, "고루틴은 공짜로 병렬화된다"는 막연한 인식보다 "P 개수만큼의 실질적 병렬성 안에서 M들이 큐를 놓고 협조적으로 스케줄링한다"는 좀 더 정확한 모델을 갖고 접근하는 편이 스레드 개수나 GOMAXPROCS 튜닝 같은 실무 판단에 도움이 됩니다.

## 한계와 반론

**한계점**: 이 글에서 인용한 `runtime2.go`/`proc.go`/`chan.go`의 필드명·함수 구조는 특정 시점(2026-08-19 기준 `master` 브랜치)의 스냅샷입니다. Go 런타임은 버전마다 내부 구현이 종종 바뀌므로(예: 과거 GM 모델에서 GMP로의 전환처럼), 이 글의 구체적인 필드명이나 상수(256 등)가 미래 Go 버전에서도 그대로 유지된다는 보장은 없습니다. 실제 프로덕션 코드의 동작을 확정적으로 판단해야 한다면 사용 중인 Go 버전의 소스코드를 직접 확인해야 합니다.

**반론**: "그렇다면 채널을 락 프리라고 부르는 게 완전히 틀린 말 아닌가?"라는 반론이 가능합니다. 엄밀히 말하면 그렇습니다 — 다만 일부 커뮤니티에서는 "락 프리"를 "개발자가 명시적으로 `Lock()`/`Unlock()`을 호출하지 않아도 된다"는 API 차원의 의미로 느슨하게 쓰기도 합니다. 이 글이 지적하는 것은 그 표현이 "채널 구현 내부에 동기화 프리미티브가 전혀 없다"는 뜻으로 오해될 때 생기는 문제이며, API 사용자 관점의 "락을 직접 다루지 않아도 된다"는 의미로 쓰는 것 자체를 틀렸다고 볼 수는 없습니다.

## 참고문헌

1. golang/go GitHub 저장소, `runtime/chan.go` — `hchan` 구조체 및 `chansend`/`chanrecv` 함수, [https://github.com/golang/go/blob/master/src/runtime/chan.go](https://github.com/golang/go/blob/master/src/runtime/chan.go) (확인일: 2026-08-19)
2. golang/go GitHub 저장소, `runtime/runtime2.go` — `p` 구조체(`runq [256]guintptr` 등), [https://github.com/golang/go/blob/master/src/runtime/runtime2.go](https://github.com/golang/go/blob/master/src/runtime/runtime2.go) (확인일: 2026-08-19)
3. golang/go GitHub 저장소, `runtime/proc.go` — `findRunnable()` 및 스케줄링 로직, [https://github.com/golang/go/blob/master/src/runtime/proc.go](https://github.com/golang/go/blob/master/src/runtime/proc.go) (확인일: 2026-08-19)
4. The Go Programming Language, Go Wiki — "Use a sync.Mutex or a channel?", [https://go.dev/wiki/MutexOrChannel](https://go.dev/wiki/MutexOrChannel) (확인일: 2026-08-19)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

GMP 스케줄러는 "고루틴은 가볍고 저절로 잘 분산된다"는 인상을 주지만, 그 이면에는 256개 고정 크기 로컬 큐, 락으로 보호되는 글로벌 큐, 절반씩 훔쳐오는 워크 스틸링이라는 구체적인 자료구조와 알고리즘이 있습니다. 채널도 마찬가지입니다 — "락 프리"라는 인상과 달리 내부에는 `hchan.lock`이라는 실제 뮤텍스가 있고, 모든 송수신이 이 락을 거칩니다. 이 글에서 강조하고 싶었던 건 두 가지입니다. 첫째, Go의 동시성 도구들이 "마법처럼 공짜로" 동작하는 게 아니라 잘 설계된 자료구조와 알고리즘 위에서 동작한다는 것. 둘째, 그런 만큼 "락 프리라서 빠르다"처럼 근거가 불확실한 통념을 실무 설계 근거로 삼기보다, 실제 소스코드나 공식 문서로 확인하는 습관이 특히 성능이 중요한 동시성 코드에서는 값어치를 한다는 것입니다. Go 런타임은 오픈소스이고 구조도 비교적 읽기 수월한 편이라, 이런 종류의 "그렇다더라"를 직접 검증하는 진입 장벽이 낮은 언어이기도 합니다.

## 꼬리질문

1. **채널의 `hchan.lock`이 경합 상황에서 실제로 `sync.Mutex`와 얼마나 다른 성능 특성을 보이는지, 벤치마크로 어떻게 측정할 수 있는가?**
   - 추천 참고 URL: https://go.dev/wiki/MutexOrChannel
2. **Go 1.14부터 도입된 비협조적(asynchronous) 프리엠션은 GMP 스케줄러의 "협조적 스케줄링" 전제를 어떻게 보완하는가?**
   - 추천 참고 URL: https://github.com/golang/go/blob/master/src/runtime/proc.go
3. **GOMAXPROCS를 실제 CPU 코어 수보다 크게 설정하면 워크 스틸링과 컨텍스트 스위칭 비용에 어떤 트레이드오프가 생기는가?**
   - 추천 참고 URL: https://github.com/golang/go/blob/master/src/runtime/runtime2.go

## 백링크

- [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html)
- [Linux epoll 기반 비동기 EventLoop 동작 원리와 C10K 고성능 I/O 최적화](https://beji-tech.blogspot.com/2026/08/linux-epoll-eventloop-c10k-io.html)
- [Spring WebFlux / Project Reactor 스레드 모델과 Schedulers 비동기 트러블슈팅](https://beji-tech.blogspot.com/2026/08/spring-webflux-project-reactor.html)