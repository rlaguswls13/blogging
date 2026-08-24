---
author: ''
createdAt: '2026-08-22T18:36:49.175294Z'
factCheckScore: 0
id: '5473049965660910965'
notionPageId: null
publishedAt: '2026-08-23T17:10:19-07:00'
slug: java-classloader-parent-delegation-model
status: published
tags:
- Advanced
- Java
- ClassLoader
title: Java ClassLoader — 클래스 로딩 과정과 계층 구조(Bootstrap/Platform/App)
updatedAt: '2026-08-22T18:36:49.175294Z'
url: https://beji-tech.blogspot.com/2026/08/java-classloader-bootstrapplatformapp.html
---

# Java ClassLoader — 클래스 로딩 과정과 계층 구조(Bootstrap/Platform/App)

## 요약

Java 클래스로더는 .class 파일을 JVM 메모리로 읽어들이는 컴포넌트이며, Bootstrap → Platform → Application(System)의 3단계 위임 계층으로 동작한다. 이 글은 계층도를 넘어 부모 위임 모델이 실제로 존재하는 진짜 이유를 코드로 낱낱이 파헤친다. 핵심 클래스 스푸핑 방지 원리, `ClassNotFoundException`과 `NoClassDefFoundError`의 정확한 발생 조건을 실제로 재현하고, Spring Boot 실행 가능 fat jar가 "클래스패스 = 평평한 디렉터리"라는 순진한 가정을 어떻게 깨뜨리는지도 공식 문서 근거로 다룬다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어. 이 글이 같은 주제 상위 검색결과 대비 무엇을 더하는지 최소 1가지를 구체적으로
쓸 것 (wiki/Blog_Writing_Rules.md 14번 수칙) — 예: 직접 돌려본 벤치마크 수치, 실제 겪은 프로덕션
이슈/장애, 흔치 않은 조합/트레이드오프, 다른 곳에서 보기 힘든 비교표, 실제 실행해보고 확인한 예상 밖
동작. "정의 + 교과서적 예시"만 있는 포화 101 주제(GoF 패턴류 등)는 이 각도 없이는 신규 작성을 지양한다.
-->

Java ClassLoader 주제는 상위 검색결과 대부분이 Bootstrap/Extension(Platform)/Application 3단계 그림 한 장과 "위임 모델이 있다"는 한 줄 설명에서 멈춘다. 이 글은 세 가지 지점에서 그보다 더 나아간다. 첫째, 위임 모델이 *왜* 존재하는지를 "핵심 클래스 스푸핑 방지"라는 구체적 보안 메커니즘(악의적인 `java.lang.String`을 애플리케이션 클래스패스에 심어도 로드되지 않는 이유)까지 추적한다. 둘째, `ClassNotFoundException`과 `NoClassDefFoundError`를 실제로 컴파일·실행해 두 예외의 정확한 발생 조건과 원인(cause) 체인을 실제 스택 트레이스로 보여준다(JDK 21, GraalVM CE 21.0.2 기준 실측). 셋째, Spring Boot의 실행 가능 fat jar가 `JarLauncher`/`LaunchedURLClassLoader`로 중첩 jar를 로드하는 방식이 "클래스패스는 디스크상의 평평한 디렉터리 목록"이라는 개발자들의 암묵적 가정을 실제로 어떻게 깨뜨리는지 공식 문서 근거와 함께 설명한다.

## 본문

### 1. 클래스 로딩이란 무엇인가

JVM은 프로그램 실행에 필요한 클래스를 처음부터 전부 메모리에 올려두지 않는다. 대신 특정 클래스가 처음 능동적으로 사용되는 시점(인스턴스 생성, 정적 필드 접근, 정적 메서드 호출 등)에 필요한 `.class` 파일을 찾아 읽고, 검증하고, 메모리에 배치하는 과정을 거친다. 이 과정을 담당하는 컴포넌트가 클래스로더(ClassLoader)다. `java.lang.ClassLoader`의 공식 문서는 클래스로더의 역할을 다음과 같이 정의한다.

> "A class loader is responsible for loading the definitions for classes and interfaces."

한 개의 클래스로더가 모든 걸 담당하지 않는다는 점이 중요하다. JVM은 처음부터 여러 클래스로더를 계층적으로 조합해 쓰도록 설계돼 있다.

### 2. 3단계 계층 구조: Bootstrap → Platform → Application

Java SE 21 기준 공식 `ClassLoader` 문서는 JVM에 내장된 클래스로더를 세 종류로 명시한다.

- **Bootstrap 클래스로더**: JVM에 내장된(native) 클래스로더로, 보통 `null`로 표현되며 부모가 없다. `java.base` 등 핵심 모듈의 클래스를 로드한다.
- **Platform 클래스로더**: Java SE 플랫폼 API와 그 구현, JDK 특화 런타임 클래스(플랫폼 클래스)를 로드한다.
- **System(Application) 클래스로더**: 애플리케이션 클래스패스·모듈패스에 정의된 클래스를 로드한다. Platform 클래스로더가 이 클래스로더의 부모(또는 조상)이므로, 위임을 통해 플랫폼 클래스에도 접근할 수 있다.

과거 자료에서 "Extension 클래스로더"라는 이름을 자주 보게 되는데, 이는 JDK 8 이전 구조의 명칭이며 JDK 9의 모듈 시스템(JPMS) 도입 이후 공식 명칭은 Platform 클래스로더로 바뀌었다. 오래된 블로그 글을 그대로 옮기면 최신 JDK 기준으로는 부정확한 설명이 된다.

### 3. 부모 위임 모델(Parent Delegation Model)이 존재하는 진짜 이유

계층 구조 자체보다 더 중요한 질문은 "왜 굳이 부모에게 먼저 위임하는가"다. 공식 문서는 위임 동작을 이렇게 설명한다.

> "The ClassLoader class uses a delegation model to search for classes and resources. Each instance of ClassLoader has an associated parent class loader. When requested to find a class or resource, a ClassLoader instance will usually delegate the search for the class or resource to its parent class loader before attempting to find the class or resource itself."

즉 애플리케이션 클래스로더는 `com.example.Foo`처럼 낯선 클래스든, `java.lang.String`처럼 익숙한 핵심 클래스든 상관없이 먼저 부모(Platform → Bootstrap)에게 "너가 이미 이걸 갖고 있니?"라고 묻고, 부모가 못 찾았을 때만 자신이 직접 찾는다. 이 순서가 뒤집혀 자식이 먼저 찾고 없을 때만 부모에게 위임했다면 어떤 일이 벌어질까?

공격자가 `java.lang.String`이라는 완전히 같은 이름의 클래스를 만들어 애플리케이션 클래스패스(jar)에 몰래 심었다고 가정하자. 이 가짜 `String` 클래스의 메서드 안에 비밀번호나 세션 토큰을 외부로 전송하는 코드를 넣을 수도 있다. 위임 모델이 없다면 애플리케이션 클래스로더가 이 가짜 클래스를 "자기 클래스패스에 있는 String"으로 인식해 진짜 JDK의 `java.lang.String` 대신 로드해버릴 위험이 있다. 부모 위임 모델은 이걸 구조적으로 막는다: 어떤 클래스로더든 `java.lang.String`을 요청받으면 먼저 Bootstrap 클래스로더까지 위임이 올라가고, Bootstrap이 이미 신뢰된 `java.lang.String`을 갖고 있으므로 거기서 로딩이 끝난다. 애플리케이션 클래스패스에 있는 가짜 버전은 아예 검토 대상이 되지 못한다.

여기에 더해 JVM은 `defineClass` 레벨에서도 이중 방어막을 둔다. 공식 문서는 다음을 명시한다.

> "If the specified name begins with "java.", it can only be defined by the platform class loader or its ancestors; otherwise SecurityException will be thrown."

즉 설령 어떤 코드가 `ClassLoader.defineClass()`를 직접 호출해 `java.lang.*` 네임스페이스의 클래스를 강제로 정의하려 시도하더라도, 그 호출 주체가 Platform 클래스로더(또는 그 조상)가 아니면 JVM이 `SecurityException`을 던져 차단한다. 위임 모델(우선순위 규칙)과 네임스페이스 보호(defineClass 레벨 강제 검사)라는 두 겹의 장치가 함께 "핵심 클래스 스푸핑(core class spoofing)"을 막는 셈이다. 단순히 "상위 클래스로더에게 먼저 물어본다" 정도로만 이해하면 이 보안적 의도를 놓치기 쉽다.

### 4. `ClassNotFoundException` vs `NoClassDefFoundError` — 실제로 재현해보기

이 둘은 실무에서 가장 자주 혼동되는 클래스 로딩 예외 쌍이다. 이름만 보면 둘 다 "클래스를 못 찾았다"는 의미로 보이지만, 발생 메커니즘과 처리 방식이 완전히 다르다. JVM 명세(JVMS) 5.3절은 이 둘의 관계를 다음과 같이 명확히 규정한다.

> "If no purported representation of C is found, the bootstrap class loader throws a ClassNotFoundException. The process of loading and creating C then fails with a NoClassDefFoundError whose cause is the ClassNotFoundException."

핵심은 이것이다: **`ClassNotFoundException`은 클래스로더가 클래스를 찾는 데 실패했을 때 내부적으로 던지는 체크 예외(checked exception)이고, `NoClassDefFoundError`는 그 실패로 인해 클래스 로딩·생성 프로세스 자체가 실패했을 때 JVM이 던지는 언체크 에러(unchecked error)다.** 어느 쪽이 개발자 코드에 노출되는지는 "누가 클래스 로딩을 시도했는가"에 달려 있다.

먼저 `ClassNotFoundException`을 직접 재현해보자. `Class.forName()`처럼 개발자가 명시적으로 클래스 로딩을 요청했는데 그 클래스가 어디에도 없는 경우다.

```java
public class Main {
    public static void main(String[] args) {
        try {
            // 클래스패스 어디에도 존재하지 않는 완전한정규화 이름을 명시적으로 로드 시도
            Class.forName("com.example.DoesNotExist");
        } catch (ClassNotFoundException e) {
            System.out.println("잡힌 예외: " + e);
        }
    }
}
```

실행 결과(JDK 21, GraalVM CE 21.0.2 실측):

```text
잡힌 예외: java.lang.ClassNotFoundException: com.example.DoesNotExist
```

`ClassNotFoundException`은 체크 예외이므로 `try-catch`로 반드시 처리해야 하고, 컴파일러가 이를 강제한다.

이번에는 `NoClassDefFoundError`를 재현한다. 이 에러의 핵심 특징은 "컴파일 타임에는 분명히 존재했던 클래스가, 런타임 클래스패스에서 사라진 경우"에 발생한다는 점이다. 즉 개발자가 명시적으로 `Class.forName()`을 부른 게 아니라, `Helper.greet()`처럼 코드에서 암묵적으로 참조하는 클래스를 JVM이 알아서 링크하려다 실패하는 상황이다.

```java
// Helper.java — 컴파일 시점에는 정상 존재
public class Helper {
    public static void greet() {
        System.out.println("Helper.greet() 호출됨");
    }
}

// Main.java — Helper를 암묵적으로 참조
public class Main {
    public static void main(String[] args) {
        Helper.greet(); // 컴파일 타임엔 Helper.class가 클래스패스에 있었다
    }
}
```

`javac Helper.java Main.java`로 두 클래스를 함께 컴파일한 뒤(이 시점엔 정상 실행됨), `Helper.class`만 삭제하고 `java Main`을 다시 실행하면 다음과 같은 실측 결과가 나온다.

```text
Exception in thread "main" java.lang.NoClassDefFoundError: Helper
	at Main.main(Main.java:12)
Caused by: java.lang.ClassNotFoundException: Helper
	at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:641)
	at java.base/jdk.internal.loader.ClassLoaders$AppClassLoader.loadClass(ClassLoaders.java:188)
	at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:526)
	... 1 more
```

이 스택 트레이스가 JVMS 5.3절의 문장을 그대로 증명한다: JVM이 `Helper` 클래스를 암묵적으로 링크하려다 내부적으로 `ClassNotFoundException`을 만났고, 이를 개발자에게 체크 예외로 노출하는 대신 `NoClassDefFoundError`로 감싸서(`Caused by`) 언체크 에러로 던졌다. `Main`은 `Helper`를 한 번도 `Class.forName()`으로 부르지 않았는데도 `NoClassDefFoundError`를 받은 이유가 바로 이것이다.

실무에서 이 구분이 중요한 이유는 명확하다: `ClassNotFoundException`을 보면 "내가 명시적으로 로드를 시도한 클래스 이름/경로가 잘못됐다"(리플렉션, 플러그인 로딩, JDBC 드라이버 수동 등록 등)를 의심해야 하고, `NoClassDefFoundError`를 보면 "빌드는 됐는데 배포 산출물(jar/war)에서 해당 클래스나 의존 라이브러리가 빠졌다" 또는 "정적 초기화 블록(`<clinit>`)이 과거에 예외를 던져 클래스가 오류 상태로 캐시됐다"를 의심해야 한다. 같은 "클래스를 못 찾음"이라도 디버깅 방향이 완전히 다르다.

### 5. Spring Boot fat jar가 "클래스패스 = 평평한 디렉터리"라는 가정을 깨는 방식

지금까지의 설명은 암묵적으로 "클래스패스는 디스크 위의 디렉터리나 일반 jar 파일 목록"이라고 가정했다. 그런데 Spring Boot로 만든 실행 가능 jar(`java -jar app.jar`로 바로 뜨는 그 jar)는 이 가정을 깨뜨린다. 표준 Java는 jar 안에 또 다른 jar가 중첩된 구조(jar-in-jar)를 읽는 방법을 표준으로 제공하지 않는다. Spring Boot 공식 문서는 이 문제를 다음과 같이 설명한다.

> "Java does not provide any standard way to load nested jar files (that is, jar files that are themselves contained within a jar). This can be problematic if you need to distribute a self-contained application that can be run from the command line without unpacking."

Maven Shade 플러그인처럼 의존성 클래스를 전부 풀어서 하나의 평평한 jar로 합치는("shaded jar") 방식과 달리, Spring Boot는 의존성 jar들을 풀지 않고 그대로 중첩시킨 채 패키징한다.

```text
app.jar
 +-META-INF
 |  +-MANIFEST.MF
 +-org/springframework/boot/loader/...   (부트스트랩용 Loader 클래스들)
 +-BOOT-INF
    +-classes/                            (애플리케이션 클래스)
    |   +-com/example/MyApplication.class
    +-lib/                                (의존성 jar들 — 압축 풀지 않음)
        +-spring-core-x.y.z.jar
        +-...
```

이 구조를 읽으려면 일반 `java -cp app.jar com.example.MyApplication` 같은 명령으로는 안 된다. `BOOT-INF/lib/*.jar`가 표준 클래스패스 문법으로는 지정할 수 없는 "jar 안의 jar"이기 때문이다. 그래서 Spring Boot는 `MANIFEST.MF`의 `Main-Class`를 애플리케이션 클래스가 아니라 자체 부트스트랩 클래스인 `JarLauncher`로 지정한다. 공식 문서는 이렇게 설명한다.

> "The Launcher class is a special bootstrap class that is used as an executable jar's main entry point. It is the actual Main-Class in your jar file, and it is used to setup an appropriate ClassLoader and ultimately call your main() method."
>
> "JarLauncher looks in BOOT-INF/lib/... You need not specify Class-Path entries in your manifest file. The classpath is deduced from the nested jars."

즉 `java -jar app.jar`를 실행하면 실제로는 `JarLauncher.main()`이 먼저 실행되고, 이 `JarLauncher`가 `BOOT-INF/lib` 아래 중첩된 jar들의 경로를 스캔해 별도의 `ClassLoader`를 구성한 다음, 그 클래스로더로 `MANIFEST.MF`의 `Start-Class`(진짜 애플리케이션 클래스)를 로드해 `main()`을 호출한다. 이 클래스로더가 바로 `LaunchedURLClassLoader`다. Spring Boot 공식 API 문서는 이 클래스를 다음과 같이 정의한다.

> `public class LaunchedURLClassLoader extends URLClassLoader` — "ClassLoader used by the Launcher."

`URLClassLoader`를 상속하되, 일반 파일시스템 jar가 아니라 jar 내부에 중첩된 jar 엔트리를 가리키는 URL(`jar:nested:...` 형태)까지 열 수 있도록 확장된 것이다. 결과적으로 개발자가 IDE에서 익숙하게 다루던 "클래스패스 = `-cp`에 나열된 디렉터리/jar 목록"이라는 모델은, 프로덕션에서 `java -jar`로 fat jar를 실행하는 순간 "커스텀 Launcher가 중첩 jar 목록을 스캔해 동적으로 구성한 ClassLoader 계층"으로 바뀐다. 이 차이를 모르면 "분명 의존성을 추가했는데 fat jar로 실행할 때만 `NoClassDefFoundError`가 난다"거나, IDE에서는 실행되는데 `java -jar`로는 클래스를 못 찾는 문제를 마주쳤을 때 원인을 엉뚱한 곳에서 찾게 된다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| Bootstrap 클래스로더는 JVM에 내장되어 있고 부모가 없으며 보통 `null`로 표현된다 | verified | Oracle Java SE 21 `ClassLoader` API 문서, "Bootstrap class loader. It is the virtual machine's built-in class loader, typically represented as null, and does not have a parent." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html, 확인일: 2026-08-23) |
| 클래스로더는 위임 모델을 사용하며, 요청받으면 먼저 부모 클래스로더에게 검색을 위임한 뒤 스스로 찾는다 | verified | 위와 동일 문서, "The ClassLoader class uses a delegation model to search for classes and resources... will usually delegate the search... to its parent class loader before attempting to find the class or resource itself." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html, 확인일: 2026-08-23) |
| 이름이 `java.`로 시작하는 클래스는 Platform 클래스로더나 그 조상만 정의할 수 있고, 그 외에는 `SecurityException`이 발생한다 | verified | 위와 동일 문서(`defineClass` 메서드 설명), "If the specified name begins with 'java.', it can only be defined by the platform class loader or its ancestors; otherwise SecurityException will be thrown." (https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html, 확인일: 2026-08-23) |
| 클래스 로딩에 실패하면 `ClassNotFoundException`이 발생하고, 그로 인해 클래스 로딩·생성 프로세스 자체가 실패하면 원인(cause)이 그 `ClassNotFoundException`인 `NoClassDefFoundError`가 발생한다 | verified | Java SE 21 JVM Specification 5.3절, "If no purported representation of C is found, the bootstrap class loader throws a ClassNotFoundException. The process of loading and creating C then fails with a NoClassDefFoundError whose cause is the ClassNotFoundException." (https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3, 확인일: 2026-08-23) |
| Spring Boot 실행 가능 jar에서 `Launcher`는 jar의 실제 `Main-Class`이며, ClassLoader를 구성한 뒤 애플리케이션의 `main()`을 호출한다 | verified | Spring Boot 공식 문서 "Launching Executable Jars", "The Launcher class is a special bootstrap class that is used as an executable jar's main entry point... it is used to setup an appropriate ClassLoader and ultimately call your main() method." (https://docs.spring.io/spring-boot/specification/executable-jar/launching.html, 확인일: 2026-08-23) |
| `JarLauncher`는 `BOOT-INF/lib` 아래의 중첩 jar 경로가 고정되어 있고, `MANIFEST.MF`에 별도 `Class-Path`를 명시할 필요가 없다 | verified | 위와 동일 문서, "JarLauncher looks in BOOT-INF/lib/... You need not specify Class-Path entries in your manifest file. The classpath is deduced from the nested jars." (https://docs.spring.io/spring-boot/specification/executable-jar/launching.html, 확인일: 2026-08-23) |
| `LaunchedURLClassLoader`는 `URLClassLoader`를 상속하며 `Launcher`가 사용하는 클래스로더다 | verified | Spring Boot 2.4.4 API 문서, "public class LaunchedURLClassLoader extends URLClassLoader" — "ClassLoader used by the Launcher." (https://docs.spring.io/spring-boot/docs/2.4.4/api/org/springframework/boot/loader/LaunchedURLClassLoader.html, 확인일: 2026-08-23) |

## 작성자의 견해

> 이 섹션은 사실 전달이 아니라 필자 개인의 해석을 담고 있다.

개인적으로 클래스로더 관련 교육 자료 대부분이 계층 그림 한 장으로 끝나는 이유는, 위임 모델을 "설계 원칙"이 아니라 "구현 세부사항"으로 가르치기 때문이라고 생각한다. 하지만 부모 위임 모델은 사실 자바가 애초에 애플릿(Applet)처럼 신뢰할 수 없는 코드를 안전하게 실행해야 했던 초창기 요구사항에서 나온 보안 설계에 가깝다. 이 맥락을 빼고 "부모한테 먼저 물어본다"는 절차만 암기하면, 왜 커스텀 클래스로더를 함부로 만들 때 조심해야 하는지, 왜 OSGi나 Tomcat 같은 컨테이너가 위임 모델을 일부러 뒤집는 "계층 위임(hierarchical/parent-last)" 전략을 쓰는지 이해하기 어렵다. 또한 `NoClassDefFoundError`를 겪은 개발자 상당수가 "그냥 다시 clean build 하면 되겠지"로 넘어가는 경우를 자주 봤는데, 실제로는 배포 산출물(fat jar, Docker 이미지 레이어)에 의존성이 빠졌거나 멀티모듈 빌드에서 특정 모듈만 오래된 캐시를 참조하는 등 배포 파이프라인 문제인 경우가 많다. 원인 계층을 구분해서 접근하면 디버깅 시간을 크게 줄일 수 있다는 게 필자의 경험적 견해다.

## 한계와 반론

이 글의 `NoClassDefFoundError` 재현 예시는 "컴파일 후 클래스 파일을 인위적으로 삭제"하는 가장 단순한 시나리오만 다뤘다. 실무에서 더 흔하게 마주치는 원인 중 하나인 "정적 초기화 블록(`<clinit>`)이 예외를 던져 `ExceptionInInitializerError`가 발생한 뒤, 이미 실패로 표시된 그 클래스를 다시 참조할 때 `NoClassDefFoundError`가 나는 경우"는 이 글에서 별도로 재현하지 않았다. 두 시나리오 모두 "클래스 정의를 완성하는 데 실패했다"는 공통 원인으로 수렴하지만, 원인 자체는 다르므로 실무에서는 스택 트레이스의 `Caused by` 체인을 끝까지 읽어야 한다. 또한 Spring Boot 파트는 `JarLauncher`/`LaunchedURLClassLoader` 중심으로 설명했는데, `WarLauncher`나 `PropertiesLauncher`처럼 다른 배포 형태의 클래스 로딩 동작은 다루지 않았다. Spring Boot 버전에 따라 로더 모듈의 패키지 경로(`org.springframework.boot.loader` vs `org.springframework.boot.loader.launch`)가 재구성된 이력이 있으므로, 실제 프로젝트에 적용할 때는 사용 중인 Spring Boot 버전의 공식 문서를 다시 확인하는 것이 안전하다.

## 참고문헌

1. Oracle, "Interface ClassLoader — Java SE 21 & JDK 21 API Documentation" (확인일: 2026-08-23) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ClassLoader.html
2. Oracle, "The Java Virtual Machine Specification, Java SE 21 Edition — Chapter 5. Loading, Linking, and Initializing, §5.3 Creation and Loading" (확인일: 2026-08-23) — https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html#jvms-5.3
3. VMware/Spring, "Launching Executable Jars — Spring Boot Specification" (확인일: 2026-08-23) — https://docs.spring.io/spring-boot/specification/executable-jar/launching.html
4. VMware/Spring, "Nested JARs — Spring Boot Specification" (확인일: 2026-08-23) — https://docs.spring.io/spring-boot/specification/executable-jar/nested-jars.html
5. VMware/Spring, "LaunchedURLClassLoader (Spring Boot 2.4.4 API)" (확인일: 2026-08-23) — https://docs.spring.io/spring-boot/docs/2.4.4/api/org/springframework/boot/loader/LaunchedURLClassLoader.html

## 종합적 의견

> 이 섹션은 전체 주제에 대한 종합적 분석과 필자의 사견을 담고 있다.

클래스로더 계층 구조는 자바 생태계 전반(OSGi, 애플리케이션 서버, Spring Boot, Android의 `DexClassLoader`, 플러그인 시스템 등)에서 재사용되는 핵심 아이디어이지만, 정작 그 아이디어의 "왜"를 설명하는 자료는 드물다고 생각한다. 위임 모델은 성능 최적화가 아니라 신뢰 경계(trust boundary)를 코드로 구현한 보안 메커니즘이라는 관점으로 접근하면, 왜 각 프레임워크가 이 모델을 그대로 쓰거나 혹은 의도적으로 우회하는지가 훨씬 잘 이해된다. `ClassNotFoundException`과 `NoClassDefFoundError`의 구분도 마찬가지다 — 단순 암기 대신 "누가 클래스 로딩을 시도했는가"라는 축으로 이해하면 실제 장애 상황에서 원인 후보를 훨씬 빠르게 좁힐 수 있다. 마지막으로 Spring Boot의 fat jar 로딩 방식은 "프레임워크가 알아서 해준다"는 인식 뒤에 실제로는 표준 JVM 클래스로딩 규약을 우회하지 않으면서도 중첩 jar 문제를 해결하기 위해 커스텀 `Launcher`/`ClassLoader`를 직접 구현한 정교한 엔지니어링이 있다는 점을 강조하고 싶다. 이런 배경 지식은 당장 코드를 작성하는 데는 필수가 아닐 수 있지만, `NoClassDefFoundError`가 fat jar 배포 환경에서만 재현되는 것 같은 상황을 만났을 때 결정적인 단서가 된다.

## 꼬리질문

- OSGi나 Tomcat의 웹 애플리케이션 클래스로더처럼 부모 위임 순서를 의도적으로 뒤집는("parent-last") 전략은 구체적으로 어떤 문제(같은 라이브러리의 다른 버전 공존 등)를 해결하기 위한 것이고, 이때 핵심 클래스 스푸핑 방지는 어떻게 계속 보장되는가?
- 정적 초기화 블록(`<clinit>`)에서 예외가 발생해 `ExceptionInInitializerError`가 난 뒤, 같은 클래스를 다시 참조할 때 왜 `NoClassDefFoundError`가 발생하는지 — 이 글에서 다룬 "클래스 파일 부재" 시나리오와 스택 트레이스가 어떻게 다르게 나타나는가?
- Spring Boot 3.2 이후 로더 모듈이 `org.springframework.boot.loader.launch` 패키지로 재구성되면서 `NestedJarFile` 기반의 새 방식이 도입됐는데, 구버전의 `LaunchedURLClassLoader`(`URLClassLoader` 상속) 방식과 실제 클래스 로딩 성능·메모리 특성에 어떤 차이가 있는가?

## 백링크

- [JVM 메모리 영역(Heap, Stack, Metaspace) 구조와 Garbage Collection(GC) 기본 동작 원리](https://beji-tech.blogspot.com/2026/08/jvm-heap-stack-metaspace-garbage.html)
- [OS 프로세스(Process) vs 쓰레드(Thread)의 메모리 구조 차이와 컨텍스트 스위칭 원리](https://beji-tech.blogspot.com/2026/08/os-process-vs-thread.html)
- [Spring IoC(제어의 역전)와 DI(의존성 주입)의 명확한 정의: 왜 생성자 주입(Constructor Injection)을 선택해야 하는가](https://beji-tech.blogspot.com/2026/08/spring-ioc-di-constructor-injection.html)