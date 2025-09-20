from playwright.sync_api import sync_playwright, TimeoutError
import time
from pprint import pprint


def login_recruitment_site(url):
    p = sync_playwright().start()
    your_path = r"/Users/rain/Library/Application Support/Google/Chrome/Profile 1"
    context = p.chromium.launch_persistent_context(
        user_data_dir=your_path,
        slow_mo=50,
        viewport=None,
        channel="chrome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--start-maximized"
        ],
        headless=False
    )
    page = context.new_page()
    
    page.goto(url)
    pprint(f"현재사이트: {url}")
    pprint("브라우저에서 로그인 한 뒤, 초기 설정을 마치세요")
    input("모든 작업이 끝났으면 Enter을 누르세요")
    return p, context, page


def get_iframe_or_page(page):
    try:
        iframe_element = page.query_selector("iframe#quick_apply_layer_frame")
        if not iframe_element:
            return page, False
        
        iframe = iframe_element.content_frame()
        if iframe:
            pprint("iframe 접근 성공")
            return iframe, True
        else:
            return page, False
    except:
        return page, False


def close_popup(page):
    try:
        frame, is_iframe = get_iframe_or_page(page)
        
        close_btn = frame.query_selector("button.btn_apply_form_close")
        if close_btn and close_btn.is_visible():
            close_btn.click()
            page.wait_for_timeout(300)
            pprint("닫기 버튼 클릭 성공!")
            return True
    except:
        pass
    
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        pprint("ESC 키로 팝업 닫기")
        return True
    except:
        return False


def handle_box_free(frame, page):
    try:
        pprint("box_free 발견 - 처리 시작")
        
        first_button = frame.query_selector("#app > div > div.area_scroll > div.box_free > div > button:nth-child(1)")
        if first_button and first_button.is_visible():
            first_button.click()
            page.wait_for_timeout(500)
            pprint("box_free 첫 번째 버튼 클릭 완료")
        else:
            pprint("box_free 첫 번째 버튼을 찾을 수 없음")
            return False
        
        blue_button = frame.query_selector("button.btn.btn_type_blue")
        if blue_button and blue_button.is_visible():
            blue_button.click()
            page.wait_for_timeout(1000)
            pprint("blue 버튼 클릭 완료")
            return True
        else:
            pprint("blue 버튼을 찾을 수 없음")
            return False
            
    except Exception as e:
        pprint(f"box_free 처리 중 오류: {e}")
        return False


def process_application(frame, page):
    box_free = frame.query_selector("div.box_free")
    if box_free:
        if handle_box_free(frame, page):
            frame, is_iframe = get_iframe_or_page(page)
            pprint("box_free 처리 완료 - 원래 로직으로 복귀")
        else:
            return False

    select = frame.query_selector("select#inpApply")
    option_count = len(select.query_selector_all("option")) if select else 0
    desc_elem = frame.query_selector("p.desc_download_form")
    already_notice = frame.query_selector("div.already_notice")
    
    if option_count == 1 and not desc_elem and not already_notice:
        pprint("조건 충족: 빠른지원 진행")
        
        chk_label = frame.query_selector("label[for='chk_speed_matching']")
        if chk_label:
            chk_speed = frame.query_selector("input#chk_speed_matching")
            if chk_speed and not chk_speed.is_checked():
                pprint("speed matching 체크박스 체크 중...")
                chk_label.click()
                page.wait_for_timeout(300)
        

        quick_btn = frame.query_selector("button.btn.kakao_pixel_event.meta_pixel_event")
        if quick_btn and quick_btn.is_visible():
            quick_btn.click(timeout=3000)
            page.wait_for_timeout(1000)
            
            confirm_img = page.wait_for_selector("#quick_apply_layer > button > img", timeout=3000)
            if confirm_img:
                confirm_img.click()
                page.wait_for_timeout(1000)
                pprint("빠른지원 완료!")
                return True
            else:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        else:
            pprint("빠른지원 버튼 미발견")
            close_popup(page)
    else:
        pprint("조건 불충족: 일반지원 - 팝업 닫기")
        close_popup(page)
    
    return False


def process_single_button(page, btn, index):
    MAX_PROCESS_TIME = 10
    
    start_time = time.time()
    
    try:
        if not btn.is_visible():
            return
        

        page.set_default_timeout(5000)
        btn.click()
        page.wait_for_timeout(500)
        
        frame, is_iframe = get_iframe_or_page(page)
        
        already_applied = frame.query_selector("div.already_notice")
        if already_applied:
            pprint("이미 지원한 공고 - 빠르게 닫기")
            close_popup(page)
            return
        
        try:
            frame.wait_for_selector("select#inpApply", state="attached", timeout=1000)
            pprint("지원서 양식 요소 로드 완료")
        except TimeoutError:
            pprint("select#inpApply 로드 대기 시간 초과")
        
        if time.time() - start_time > MAX_PROCESS_TIME:
            pprint(f"버튼 {index+1} 처리 시간 초과 - 강제 종료")
            close_popup(page)
            return
        
        process_application(frame, page)
            
    except TimeoutError:
        pprint(f"버튼 {index+1} 처리 중 타임아웃 발생")
        close_popup(page)
    except Exception as e:
        pprint(f"버튼 {index+1} 처리 중 오류: {str(e)[:100]}")
        close_popup(page)
    finally:
        page.set_default_timeout(30000)


def auto_apply(page):
    while True:
        buttons = page.query_selector_all("span.sri_btn_immediately")
        if not buttons:
            pprint("현재 페이지에 더 이상 즉시지원 버튼이 없습니다.")
            break

        for i, btn in enumerate(buttons):
            try:
                process_single_button(page, btn, i)
            except Exception as e:
                pprint(f"버튼 {i+1} 처리 실패: {e}")
                continue

        if not go_to_next_page(page):
            pprint("더 이상 이동할 페이지가 없습니다.")
            return


def go_to_next_page(page):
    try:
        active_btn = page.query_selector("span.BtnType.SizeS.active")
        if active_btn:
            current_num = int(active_btn.inner_text().strip())
            target_num = current_num + 1
            pprint(f"다음 페이지 목표: {target_num}")
            
            all_page_buttons = page.query_selector_all("button.BtnType.SizeS")
            for btn in all_page_buttons:
                if btn.inner_text().strip() == str(target_num) and btn.is_visible():
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=5000)
                    page.wait_for_timeout(1000)
                    return True
        
        next_btn = page.query_selector("button.BtnType.SizeS.BtnNext")
        if next_btn and next_btn.is_enabled():
            next_btn.click()
            page.wait_for_load_state("networkidle", timeout=5000)
            page.wait_for_timeout(1000)
            return True
            
        return False
        
    except Exception as e:
        pprint(f"페이지 이동 중 오류: {e}")
        return False


def main():
    url = "https://www.saramin.co.kr/zf_user/"
    p, context, page = login_recruitment_site(url)
    
    try:
        auto_apply(page)
    except KeyboardInterrupt:
        pprint("사용자에 의해 중단되었습니다.")
    except Exception as e:
        pprint(f"예상치 못한 오류: {e}")
    finally:
        input("엔터를 누르면 브라우저가 종료됩니다...")
        context.close()
        p.stop()


if __name__ == "__main__":
    main()