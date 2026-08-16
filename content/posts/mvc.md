---
id: "162598903523081749"
title: "MVC 패턴: 자판기에서 동적 웹 서비스까지의 진화 및 아키텍처 분석"
slug: "mvc"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/mvc.html"
publishedAt: "2026-08-14T11:23:25.591-07:00"
updatedAt: "2026-08-14T11:32:42.185-07:00"
tags: ["Basics","MVC","Spring","Web Architecture","기초"]
---

# MVC 패턴: 자판기에서 동적 웹 서비스까지의 진화 및 아키텍처 분석

백엔드 프레임워크의 왕좌를 지키고 있는 **MVC(Model-View-Controller) 패턴**은 소프트웨어의 관심사를 명확히 분리(Separation of Concerns)하여 대규모 동적 웹 애플리케이션의 유지보수성을 극대화하는 검증된 아키텍처입니다. 본 아티클에서는 자판기 비유부터 정적 웹에서 동적 웹으로의 역사적 진화 과정, 그리고 실제 동작하는 Java/Spring MVC 예시 코드까지 깊이 있게 다룹니다.

  
    ![MVC 패턴 자판기 비유 인포그래픽](https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/mvc_pattern_diagram.jpg)
    
[그림 1] 자판기 모델 기반 Model-View-Controller(MVC) 역할 분리 구조도

  

  
## 1. 자판기 모델 기반 MVC 3대 역할 분리 기전

  
MVC 패턴의 핵심은 **Controller(입력), Model(상태 및 비즈니스 로직), View(출력 화면)**가 서로 독립적인 책임을 갖는 것입니다.

  
    
- **Controller**: 동전 투입 및 제품 선택 버튼 이벤트를 받아 입력을 검증하고 모델을 호출합니다.
    
- **Model**: 투입 잔액을 연산하고, DB 재고를 차감하는 핵심 비즈니스 로직을 수행합니다.
    
- **View**: 모델이 제공한 상태 데이터(잔액, 처리 결과)를 읽어와서 시각적 렌더링을 담당합니다.
  

  
## 2. 실제 동작하는 Java/Spring 백엔드 예시 코드

  
### [Model Layer] VendingMachineModel.java

  
```
`public class VendingMachineModel {
    private int balance = 0;
    private int itemPrice = 1500;
    private int stockCount = 10;

    public void insertCoin(int amount) {
        if (amount = itemPrice && this.stockCount > 0;
    }

    public String purchase() {
        if (!canPurchase()) return "잔액이 부족하거나 품절되었습니다.";
        this.balance -= itemPrice;
        this.stockCount--;
        return "제품 배출 완결! 남은 잔액: " + this.balance + "원";
    }

    public int getBalance() { return balance; }
}`
```

  
### [View Layer] VendingMachineView.java

  
```
`public class VendingMachineView {
    public void render(int balance, String message) {
        System.out.println("
========== [자판기 LED 디스플레이] ==========");
        System.out.println("현재 잔액: " + balance + "원");
        System.out.println("알림 메시지: " + message);
        System.out.println("============================================
");
    }
}`
```

  
### [Controller Layer] VendingMachineController.java

  
```
`public class VendingMachineController {
    private final VendingMachineModel model = new VendingMachineModel();
    private final VendingMachineView view = new VendingMachineView();

    public void onInsertCoin(int amount) {
        model.insertCoin(amount);
        view.render(model.getBalance(), amount + "원이 투입되었습니다.");
    }

    public void onSelectProduct() {
        String result = model.purchase();
        view.render(model.getBalance(), result);
    }
}`
```

  
## 3. 참고자료 및 공식 문헌 (References)

  
    
- [Spring Framework Official Web MVC Documentation](https://docs.spring.io/spring-framework/reference/web/webmvc.html)
    
- Martin Fowler, *Patterns of Enterprise Application Architecture* (Addison-Wesley)
