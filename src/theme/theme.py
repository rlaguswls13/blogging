import os
import sys
import shutil
import datetime
import webbrowser
import time
from pathlib import Path
from dotenv import load_dotenv

def manage_theme(upload: bool = False):
    load_dotenv()
    
    from src.core.paths import project_root, theme_xml_path
    theme_path = theme_xml_path
    
    if not theme_path.exists():
        print(f"오류: 테마 파일이 존재하지 않습니다. 경로: {theme_path}", file=sys.stderr)
        sys.exit(1)
        
    print("\n======================================================")
    print("[Theme] 작성된 블로그 테마 파일 확인")
    print(f"- 테마 경로: {theme_path}")
    print("- 파일 크기: {:,} bytes".format(theme_path.stat().st_size))
    print("======================================================\n")
    
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        print("오류: .env 파일에 BLOGGER_BLOG_ID가 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)
        
    if not upload:
        # 수동 가이드 및 로컬 백업 흐름
        try:
            response = input("이 테마 파일을 백업하고 Blogger 테마 설정 페이지를 여시겠습니까? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
            sys.exit(0)
            
        if response not in ('y', 'yes'):
            print("작업이 취소되었습니다.")
            return
            
        # 백업 생성
        backup_dir = project_root / "temp" / "backups" / "theme"
        os.makedirs(backup_dir, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"blogger_site_theme_{now_str}.xml"
        
        try:
            shutil.copy2(theme_path, backup_path)
            print(f"[성공] 테마 백업 완료: temp/backups/theme/{backup_path.name}")
        except Exception as e:
            print(f"[오류] 백업 중 오류 발생: {str(e)}", file=sys.stderr)
            sys.exit(1)
            
        url = f"https://www.blogger.com/blog/themes/{blog_id}"
        print(f"[접속] Blogger 테마 설정 페이지 접속 중: {url}")
        print("[안내] 브라우저창에서 '복원(Restore)' 버튼을 눌러 새 테마를 적용해 주세요.")
        webbrowser.open(url)
        
    else:
        # Playwright 자동 테마 업로드 흐름
        print("[Theme] Playwright 기반 자동 테마 업로드를 시작합니다.")
        
        # 백업 생성
        backup_dir = project_root / "temp" / "backups" / "theme"
        os.makedirs(backup_dir, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"blogger_site_theme_{now_str}.xml"
        try:
            shutil.copy2(theme_path, backup_path)
            print(f"[성공] 테마 백업 완료: temp/backups/theme/{backup_path.name}")
        except Exception as e:
            print(f"[오류] 백업 중 오류 발생: {str(e)}", file=sys.stderr)
            sys.exit(1)

        from playwright.sync_api import sync_playwright
        
        # 프로젝트 하위에 전용 세션 프로필 디렉토리 지정
        profile_dir = project_root / "temp" / "automation_profile"
        os.makedirs(profile_dir.parent, exist_ok=True)
        
        url = f"https://www.blogger.com/blog/themes/{blog_id}"
        
        with sync_playwright() as p:
            print(f"[Theme] 크롬 브라우저를 구동 중입니다. (세션 프로필: {profile_dir.name})")
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                channel="chrome"
            )
            
            page = context.new_page()
            
            try:
                page.goto(url)
                
                # 구글 로그인 창 감지 및 대기
                if "accounts.google.com" in page.url:
                    print("\n[Blogger] [경고] 구글 로그인 세션이 존재하지 않습니다.")
                    print("[Blogger] [대기] 열린 브라우저 창에서 구글 로그인을 완료해 주세요. (5분 대기)")
                    
                    max_wait = 300
                    waited = 0
                    while ("themes" not in page.url or "accounts.google.com" in page.url) and waited < max_wait:
                        time.sleep(1)
                        waited += 1
                        
                    if "themes" not in page.url:
                        raise TimeoutError("구글 로그인 대기 시간 초과")
                    else:
                        print("[Blogger] 로그인 성공 감지! 테마 관리 화면으로 진입합니다.")
                        page.wait_for_load_state("networkidle")
                
                print("[Blogger] 테마 설정 버튼 로딩 대기 중 (최대 30초)...")
                
                active_frame = None
                target_element = None
                
                max_wait_secs = 30
                for sec in range(max_wait_secs):
                    for frame in page.frames:
                        try:
                            for kw in ["맞춤설정", "Customize"]:
                                loc = frame.get_by_text(kw, exact=False).first
                                if loc.count() > 0 and loc.is_visible():
                                    target_element = loc
                                    active_frame = frame
                                    break
                            if target_element:
                                break
                        except Exception:
                            continue
                    if target_element:
                        break
                    time.sleep(1)
                
                if not target_element or not active_frame:
                    raise TimeoutError("맞춤설정(Customize) 텍스트를 찾을 수 없습니다.")

                # 조상 엘리먼트를 거슬러 올라가며 공통 부모 컨테이너에서 dropdown 버튼 탐색
                dropdown_btn = None
                curr = target_element
                for _ in range(4):
                    try:
                        for sib_selector in ["following-sibling::button", "following-sibling::div", "following-sibling::*"]:
                            sib = curr.locator(f"xpath={sib_selector}").first
                            if sib.count() > 0 and sib.is_visible():
                                dropdown_btn = sib
                                break
                        if dropdown_btn:
                            break
                        curr = curr.locator("xpath=..").first
                    except Exception:
                        break

                if not dropdown_btn or not dropdown_btn.is_visible():
                    dropdown_btn = active_frame.locator("button[aria-label='더보기'], button[aria-label='More options']").first

                if dropdown_btn.count() == 0:
                    raise RuntimeError("맞춤설정 옵션(더보기) 버튼을 찾을 수 없습니다.")

                print("[Blogger] 맞춤설정 옵션(더보기) 버튼 클릭 시도")
                dropdown_btn.click()
                active_frame.wait_for_timeout(2000)

                # 드롭다운 메뉴 오픈 여부 확인용 디버그 스크린샷
                click_shot_path = "C:/Users/rlagu/.gemini/antigravity/brain/af7d9d0f-bcbe-46da-b9b8-4b47e058a573/blogger_dropdown_clicked.png"
                try:
                    page.screenshot(path=click_shot_path)
                    print(f"[디버그] 드롭다운 클릭 후 스크린샷 저장 완료: {click_shot_path}")
                except Exception as se:
                    print(f"[디버그] 스크린샷 저장 실패: {str(se)}", file=sys.stderr)

                # '복원' 또는 'Restore' 선택
                restore_item = None
                for selector in ["text=복원", "text=Restore", "span:has-text('복원')", "span:has-text('Restore')"]:
                    loc = active_frame.locator(selector).first
                    if loc.count() > 0 and loc.is_visible():
                        restore_item = loc
                        break
                
                if not restore_item:
                    raise RuntimeError("복원(Restore) 메뉴 아이템을 찾을 수 없습니다.")

                print("[Blogger] 복원(Restore) 메뉴 아이템 강제 클릭 이벤트 디스패치")
                restore_item.dispatch_event('click')
                active_frame.wait_for_timeout(3000)

                # 복원 모달 팝업이 나타날 때까지 대기
                print("[Blogger] 복원 대화상자 모달 대기 중...")
                try:
                    active_frame.wait_for_selector("div[role='dialog']", timeout=8000)
                except Exception:
                    pass

                # 모달 팝업 내부에서만 업로드 버튼 찾기
                theme_uploaded = False
                try:
                    dialog = active_frame.locator("div[role='dialog']").first
                    upload_btn = None
                    if dialog.count() > 0:
                        for kw in ["업로드", "Upload"]:
                            loc = dialog.locator(f"button:has-text('{kw}'), div[role='button']:has-text('{kw}'), span:has-text('{kw}')").first
                            if loc.count() > 0 and loc.is_visible():
                                upload_btn = loc
                                break

                    if not upload_btn:
                        # 폴백: 대화상자가 제대로 안 잡혔을 경우 프레임 전체에서 탐색
                        for kw in ["업로드", "Upload"]:
                            loc = active_frame.locator(f"button:has-text('{kw}'), div[role='button']:has-text('{kw}')").first
                            if loc.count() > 0 and loc.is_visible():
                                upload_btn = loc
                                break

                    print(f"[Blogger] 복원 대화상자 내 업로드 버튼 지정 완료. 클릭 및 파일 지정 감시...")
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        upload_btn.click(force=True)
                    file_chooser = fc_info.value
                    file_chooser.set_files(str(theme_path))
                    print("[Blogger] 파일 가로채기를 통한 테마 파일 전송 완료!")
                    theme_uploaded = True
                except Exception as e:
                    print(f"[Blogger] 업로드 가로채기 실패 ({str(e)}). input[type=file] 강제 주입을 시도합니다.")

                if not theme_uploaded:
                    try:
                        file_input = active_frame.locator("input[type='file']").first
                        if file_input.count() > 0:
                            file_input.set_input_files(str(theme_path))
                            file_input.dispatch_event('change')
                            print("[Blogger] input[type='file']에 직접 파일 지정 및 change 이벤트 트리거 성공!")
                            theme_uploaded = True
                    except Exception as fe:
                        raise RuntimeError(f"테마 복원 업로드 처리가 불가능합니다. 오류: {str(fe)}")

                # 업로드 서버 완료 토스트 감시 (최대 30초 대기)
                print("[Blogger] 테마 복원 완료 토스트 감시 시작 (최대 30초)...")
                restored_toast_found = False
                for i in range(1, 16):
                    active_frame.wait_for_timeout(2000)
                    step_shot_path = f"C:/Users/rlagu/.gemini/antigravity/brain/af7d9d0f-bcbe-46da-b9b8-4b47e058a573/blogger_upload_step_{i}.png"
                    try:
                        page.screenshot(path=step_shot_path)
                        print(f"[디버그] 업로드 단계 {i}/8 스크린샷 저장: {step_shot_path}")
                    except Exception:
                        pass

                    # 토스트 메시지나 에러 다이얼로그 탐색
                    try:
                        toast_loc = page.locator("div[role='status'], .Y70upo, .toast, .snackbar").first
                        if toast_loc.count() > 0 and toast_loc.is_visible():
                            print(f"[Blogger 감지] 토스트 알림: {toast_loc.text_content().strip()}")
                    except Exception:
                        pass

                print("[Blogger] 테마 업로드 및 복원 처리 완료!")
                
                # 성공 스크린샷 저장
                success_shot_path = "C:/Users/rlagu/.gemini/antigravity/brain/af7d9d0f-bcbe-46da-b9b8-4b47e058a573/blogger_success.png"
                try:
                    page.screenshot(path=success_shot_path)
                    print(f"[디버그] 성공 스크린샷 저장 완료: {success_shot_path}")
                except Exception as se:
                    print(f"[디버그] 스크린샷 저장 실패: {str(se)}", file=sys.stderr)
                
            except Exception as e:
                print(f"[오류] 자동화 중 예외 발생: {str(e)}", file=sys.stderr)
                print(f"[오류] 현재 URL: {page.url}")
                print(f"[오류] 현재 타이틀: {page.title()}")
                
                # 에러 화면 스크린샷 저장
                shot_path = "C:/Users/rlagu/.gemini/antigravity/brain/af7d9d0f-bcbe-46da-b9b8-4b47e058a573/blogger_error.png"
                try:
                    page.screenshot(path=shot_path)
                    print(f"[디버그] 에러 스크린샷 저장 완료: {shot_path}")
                except Exception as se:
                    print(f"[디버그] 스크린샷 저장 실패: {str(se)}", file=sys.stderr)
                    
                context.close()
                sys.exit(1)
                
            context.close()
            print("[Theme] 자동 테마 복원 프로세스가 정상 종료되었습니다.")
