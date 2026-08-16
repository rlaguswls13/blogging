---
id: '2647152662034823524'
publishedAt: '2026-08-14T11:28:48.000-07:00'
slug: gof-12-command-pattern-java
status: published
tags:
- Basics
- Design Patterns
- GoF
- Java
- 기초
title: '[GoF 디자인 패턴] 12. 커맨드 패턴 (Command Pattern) 개념과 Java 실전 예시'
updatedAt: '2026-08-15T16:18:44.656-07:00'
url: https://beji-tech.blogspot.com/2026/08/gof-12-command-pattern-java.html
---

# [GoF 디자인 패턴] 12. 커맨드 패턴 (Command Pattern) 개념과 Java 실전 예시

GoF 14대 핵심 디자인 패턴 시리즈 - **행위 패턴 (Behavioral)**

## 요약

커맨드 패턴은 "실행할 작업"을 하나의 객체로 캡슐화하여, 요청을 보내는 쪽(Invoker)과 실제로 그 요청을 처리하는 쪽(Receiver)을 완전히 분리하는 행위 패턴입니다. 버튼 클릭 같은 UI 이벤트를 큐에 쌓아두거나, 실행 취소(Undo)/다시 실행(Redo) 기능을 만들거나, 여러 작업을 로그로 남겨 재실행해야 할 때 특히 유용합니다. 이 글에서는 커맨드 패턴이 필요한 상황, 인터페이스 설계 방식, 실행 취소까지 지원하는 완전한 Java 예제, 그리고 `Runnable`이나 Spring의 비동기 작업 큐 같은 실무 프레임워크에서 이 패턴이 어떻게 녹아 있는지를 다룹니다.

## 본문

### 1. 배경 및 문제점

리모컨으로 여러 가전제품(TV, 조명, 에어컨)을 제어하는 애플리케이션을 만든다고 가정해 보겠습니다. 리모컨 버튼 클래스가 `if (device == TV) tv.turnOn(); else if (device == LIGHT) light.turnOn();` 처럼 각 가전제품의 구체적인 클래스를 직접 알고 호출하면, 새로운 가전제품이 추가될 때마다 리모컨 코드를 계속 수정해야 합니다. 또한 "마지막으로 누른 버튼을 취소"하는 기능을 만들려면 버튼을 누른 히스토리와 각 동작을 되돌리는 로직을 어딘가에 저장해야 하는데, 요청을 발생시키는 쪽(리모컨)과 요청을 처리하는 쪽(가전제품)이 강하게 결합되어 있으면 이 히스토리 관리 자체가 매우 지저분해집니다.

### 2. 패턴 정의 및 동작 메커니즘

커맨드 패턴은 "TV를 켜라"와 같은 요청 자체를 `Command`라는 하나의 객체로 캡슐화합니다. 이 객체는 내부에 실제 작업을 수행할 `Receiver`(가전제품)에 대한 참조와, `execute()`를 호출하면 그 Receiver에게 어떤 메서드를 어떤 인자로 호출할지에 대한 정보를 갖고 있습니다. `Invoker`(리모컨 버튼)는 `Command` 인터페이스만 알면 되고, 구체적으로 어떤 가전제품의 어떤 메서드가 실행되는지는 전혀 몰라도 됩니다.

**실제 서비스 적용 예시: 텍스트 에디터의 실행 취소(Undo) 기능** — 문서 편집기에서 "글자 삭제", "문단 이동" 같은 각 편집 동작을 Command 객체로 만들어 스택에 쌓아두면, Ctrl+Z를 눌렀을 때 스택에서 마지막 Command를 꺼내 그 안에 미리 구현해 둔 `undo()`를 호출하는 것만으로 실행 취소가 가능합니다.

**비유: 레스토랑 주문서** — 손님(Client)이 웨이터(Invoker)에게 "스테이크 미디엄으로"라고 말하면, 웨이터는 요리 방법을 직접 몰라도 주문서(Command 객체)에 적어서 주방(Receiver)에 전달합니다. 주방은 주문서를 보고 실제 조리를 수행합니다. 웨이터를 바꿔도, 새로운 메뉴가 추가되어도 주문서라는 형식만 지키면 시스템이 무너지지 않습니다.

### 3. Java 실전 구현 코드

아래는 조명(Light)을 켜고 끄는 리모컨 시스템을 실행 취소 기능까지 포함해 구현한 예제입니다.

```java
package com.gof.command;

import java.util.Stack;

// 1. 커맨드 인터페이스 (Command)
interface Command {
    void execute();
    void undo();
}

// 2. 수신자 (Receiver) - 실제 작업을 수행하는 객체
class Light {
    private boolean isOn = false;

    public void turnOn() {
        isOn = true;
        System.out.println("💡 조명이 켜졌습니다.");
    }

    public void turnOff() {
        isOn = false;
        System.out.println("🌑 조명이 꺼졌습니다.");
    }
}

// 3. 구체적인 커맨드 (Concrete Command)
class LightOnCommand implements Command {
    private final Light light;

    public LightOnCommand(Light light) {
        this.light = light;
    }

    @Override
    public void execute() {
        light.turnOn();
    }

    @Override
    public void undo() {
        light.turnOff(); // 켜기의 반대 동작으로 되돌림
    }
}

class LightOffCommand implements Command {
    private final Light light;

    public LightOffCommand(Light light) {
        this.light = light;
    }

    @Override
    public void execute() {
        light.turnOff();
    }

    @Override
    public void undo() {
        light.turnOn();
    }
}

// 4. 발신자 (Invoker) - 커맨드를 실행하고 히스토리를 관리
class RemoteControl {
    private final Stack<Command> history = new Stack<>();

    public void pressButton(Command command) {
        command.execute();
        history.push(command); // 실행 취소를 위해 히스토리에 저장
    }

    public void pressUndo() {
        if (history.isEmpty()) {
            System.out.println("⚠️ 되돌릴 작업이 없습니다.");
            return;
        }
        Command lastCommand = history.pop();
        System.out.println("↩️ 마지막 작업을 취소합니다.");
        lastCommand.undo();
    }
}

public class CommandPatternMain {
    public static void main(String[] args) {
        Light livingRoomLight = new Light();
        RemoteControl remote = new RemoteControl();

        System.out.println("=== 1. 조명 켜기 버튼 클릭 ===");
        remote.pressButton(new LightOnCommand(livingRoomLight));

        System.out.println("\n=== 2. 조명 끄기 버튼 클릭 ===");
        remote.pressButton(new LightOffCommand(livingRoomLight));

        System.out.println("\n=== 3. 실행 취소(Undo) 버튼 클릭 ===");
        remote.pressUndo(); // 마지막 동작(끄기)을 취소 -> 다시 켜짐
    }
}

/*
▶ 실행 결과 (Expected Output):
=== 1. 조명 켜기 버튼 클릭 ===
💡 조명이 켜졌습니다.

=== 2. 조명 끄기 버튼 클릭 ===
🌑 조명이 꺼졌습니다.

=== 3. 실행 취소(Undo) 버튼 클릭 ===
↩️ 마지막 작업을 취소합니다.
💡 조명이 켜졌습니다.
*/
```

### 4. 실무 주의점 및 트레이드오프

Command 객체가 많아질수록 클래스 수가 급격히 늘어난다는 단점이 있습니다. 동작 하나마다 별도 클래스를 만들어야 하므로, 자바 8 이후에는 간단한 Command는 람다식(`Runnable` 등 함수형 인터페이스)으로 대체하는 경우가 많습니다. 다만 `undo()`처럼 상태를 함께 들고 있어야 하는 복잡한 Command는 여전히 별도 클래스로 만드는 것이 명확합니다. 또한 실행 취소 기능을 지원하려면 각 Command가 "되돌리기 위한 상태"를 스스로 기억해야 하는데, 이 상태 저장 범위를 잘못 설계하면 메모리를 과도하게 소모하거나 되돌리기가 불완전해질 수 있습니다.

### 5. 실무 프레임워크 적용 사례

자바의 `Runnable`과 `Callable` 인터페이스 자체가 커맨드 패턴의 실전 사례입니다 — "실행할 작업"을 객체로 감싸 스레드 풀(`ExecutorService`)에 넘기면, 스레드 풀은 작업의 구체적인 내용을 몰라도 `run()`만 호출하면 됩니다. Swing GUI의 `Action` 인터페이스도 버튼 클릭 시 수행할 로직을 캡슐화하는 동일한 개념이며, 메시지 큐 기반 아키텍처(Kafka, RabbitMQ)에서 큐에 적재되는 "작업 메시지" 역시 커맨드 패턴의 분산 시스템 버전으로 볼 수 있습니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: 커맨드 패턴은 요청을 객체로 캡슐화하여 Invoker와 Receiver를 분리하는 행위 패턴이다 | verified | Gamma et al., Design Patterns (1994) Command 챕터 |
| CLAIM-002: 커맨드 패턴은 실행 취소(Undo)/다시 실행(Redo) 기능 구현에 자연스럽게 활용된다 | verified | Gamma et al., Design Patterns Command 챕터의 Undo 지원 논의 |
| CLAIM-003: 자바의 Runnable/Callable 인터페이스는 커맨드 패턴의 실전 적용 사례로 볼 수 있다 | verified | Oracle Java SE Runnable/Callable 공식 Javadoc(작업을 객체로 캡슐화해 실행자에 전달하는 구조) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

실무에서 커맨드 패턴을 "클래스가 늘어나서 번거로운 패턴"으로만 보는 시각이 있지만, 저는 실행 취소나 작업 로깅이 필요 없는 단순한 콜백이라면 굳이 이 패턴 전체를 도입할 필요는 없다고 생각합니다. 반대로 사용자 작업 히스토리를 관리해야 하는 에디터, 결제 승인처럼 실패 시 보상 처리가 필요한 트랜잭션 흐름에서는 커맨드 패턴이 요청과 실행을 분리해주는 덕분에 재시도·로깅·큐잉 같은 부가 기능을 붙이기가 훨씬 쉬워집니다. 결국 이 패턴의 가치는 클래스 수 증가라는 비용보다, "실행을 나중으로 미루거나 되돌릴 수 있는 유연성"이 실제로 필요한지에 달려 있다고 봅니다.

## 한계와 반론

커맨드 패턴은 요청 하나하나를 객체로 만들기 때문에, 아주 단순하고 되돌릴 필요가 없는 동작에는 오히려 오버엔지니어링이 될 수 있습니다. 이런 경우 자바의 람다식이나 메서드 레퍼런스로 대체하면 별도 클래스 없이도 동일한 효과(요청의 캡슐화)를 훨씬 가볍게 얻을 수 있다는 반론이 있습니다. 다만 상태를 가진 실행 취소 로직이나, 커맨드 자체를 직렬화해 큐에 저장해야 하는 경우에는 람다만으로는 부족하므로 여전히 정식 Command 클래스가 필요합니다.

## 참고문헌

1. Oracle, "Runnable (Java SE 21 & JDK 21)", [https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runnable.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runnable.html) (확인일: 2026-08-17)
2. Wikipedia, "Design Patterns (book)", [https://en.wikipedia.org/wiki/Design_Patterns](https://en.wikipedia.org/wiki/Design_Patterns) (확인일: 2026-08-17)
3. Refactoring.Guru, "Command Design Pattern", [https://refactoring.guru/design-patterns/command](https://refactoring.guru/design-patterns/command) (확인일: 2026-08-17)

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 개인 견해를 담고 있습니다.

커맨드 패턴의 핵심은 "무엇을 할지"와 "언제, 누가 실행할지"를 분리하는 것입니다. 이 분리 덕분에 요청을 큐에 쌓거나, 로그로 남기거나, 실행 취소할 수 있는 유연성이 생깁니다. 현대 자바에서는 단순한 콜백이 람다식으로 대체되면서 고전적인 Command 클래스 계층을 직접 만드는 빈도는 줄었지만, 그 근본 아이디어인 "작업의 객체화"는 스레드풀의 `Runnable`, 메시지 큐의 작업 메시지, 이벤트 기반 아키텍처 전반에 여전히 살아 있습니다. 새로운 기능을 설계할 때 "이 작업을 나중에 실행하거나 되돌릴 필요가 있는가?"를 자문해보면 커맨드 패턴 적용 여부를 쉽게 판단할 수 있습니다.

## 꼬리질문

1. **커맨드 패턴으로 여러 동작을 순차 묶어 하나의 트랜잭션처럼 실행하는 매크로 커맨드(Macro Command)는 어떻게 설계하는가?**
   - 추천 참고 URL: https://refactoring.guru/design-patterns/command
2. **Spring의 `@Async` 비동기 처리와 커맨드 패턴의 작업 캡슐화 개념은 어떤 지점에서 만나는가?**
   - 추천 참고 URL: https://docs.spring.io/spring-framework/reference/integration/scheduling.html

## 백링크

- [GoF 14대 디자인 패턴 인덱스](https://beji-tech.blogspot.com/2026/08/gof-14.html)
- [위키 인덱스](../../wiki/README.md)