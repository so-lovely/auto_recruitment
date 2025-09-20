from playwright.sync_api import sync_playwright
import sys
import time
from pprint import pprint
def login_recruitment_site(url):
    p = sync_playwright().start()
    your_path = r"/Users/rain/Library/Application Support/Google/Chrome/Profile 1" #여기에 이렇게 복사하세용!
    context = p.chromium.launch_persistent_context(user_data_dir=your_path,
                                                   slow_mo=100,
                                                   viewport=None,
                                                   channel="chrome",
                                                   args=[
                                                       "--disable-blink-features=AutomationControlled",
                                                       "--disable-infobars",
                                                       "--start-maximized"
                                                   ],
                                                   headless=False)
    page = context.new_page()
    
    page.goto(url)
    pprint(f"현재사이트:{url}")
    pprint("브라우저에서 로그인 한 뒤,초기 설정을 마치세요")
    input("모든 작업이 끝났으면 Enter을 누르세요")
    return p, context, page

def extract_resume_titles_wanted(context):
    """
    유저가 이력서를 번호로 선택하면, 해당 이력서의 'key'를 반환
    """
    url = "https://www.wanted.co.kr/api/chaos/resumes/v1?offset=0&limit=20"

    try:
        response = context.request.get(url)
        if not response.ok:
            pprint("이력서 목록을 불러오지 못했습니다.")
            return None

        data = response.json()
        resumes = data.get("data", [])

        if not resumes:
            pprint("이력서가 없습니다.")
            return None

        for i, resume in enumerate(resumes, 1):
            title = resume.get("title", "제목 없음")
            pprint(f"{i}. {title}")

        while True:
            try:
                select_num = int(input("\n이력서 번호를 선택하세요: "))
                if 1 <= select_num <= len(resumes):
                    selected_resume = resumes[select_num - 1]
                    resume_key = selected_resume.get("key")
                    pprint(f"선택됨: {selected_resume.get('title')} → key: {resume_key}")
                    return resume_key
                else:
                    pprint("번호가 범위를 벗어났습니다. 다시 입력하세요.")
            except ValueError:
                pprint("숫자만 입력하세요.")

    except Exception as e:
        pprint(f"오류 발생: {e}")
        return None


def fetch_category_data_wanted(context):
    url = "https://static.wanted.co.kr/tags?tags=category"
    try:
        response = context.request.get(url)
        if not response.ok:
            pprint(f"카테고리 데이터 요청 실패: {response.status}")
            return []

        data = response.json()
        category_list = data.get("category", [])
        if not category_list:
            pprint("카테고리 데이터가 비어있습니다.")
            return []

        dev_category = next((cat for cat in category_list if cat["id"] == 518), None)
        if not dev_category:
            pprint("개발 관련 카테고리를 찾을 수 없습니다.")
            return []

        tags = dev_category.get("tags", [])
        if not tags:
            pprint("태그 목록이 비어있습니다.")
            return []
        tag_dict = {}
        pprint("\n=== 지원할 직무 태그를 선택하세요 ===")
        for idx, tag in enumerate(tags, 1):
            tag_id = tag["id"]
            title = tag["title"]
            job_count = tag["counts"]["job"]
            tag_dict[idx] = {"id": tag_id, "title": title}
            pprint(f"{idx}. [{job_count}개 공고] {title}")

        pprint(f"{len(tags)+1}. 선택 완료")

        selected_ids = set()
        while True:
            try:
                choice = input(f"\n번호를 선택하세요 (1~{len(tags)+1}): ").strip()
                choice_num = int(choice)

                if 1 <= choice_num <= len(tags):
                    selected_tag = tag_dict[choice_num]
                    tag_id = selected_tag["id"]
                    title = selected_tag["title"]

                    if tag_id in selected_ids:
                        pprint(f"이미 선택됨: {title}")
                    else:
                        selected_ids.add(tag_id)
                        pprint(f"선택됨: {title} (ID: {tag_id})")
                    selected_titles = [tag_dict[i]["title"] for i in tag_dict if tag_dict[i]["id"] in selected_ids]
                    pprint(f"현재 선택된 태그: {selected_titles}")
                elif choice_num == len(tags) + 1:
                    if not selected_ids:
                        pprint("최소 하나 이상 선택해주세요.")
                        continue
                    pprint("\n최종 선택된 태그:")
                    for tid in selected_ids:
                        matched = next((t for t in tags if t["id"] == tid), None)
                        if matched:
                            pprint(f" - {matched['title']} (ID: {tid})")
                    return list(selected_ids)

                else:
                    pprint("유효하지 않은 번호입니다.")

            except ValueError:
                pprint("숫자만 입력하세요.")
            except KeyboardInterrupt:
                pprint("\n사용자 중단.")
                return []
    except Exception as e:
        pprint(f"에러발생:{e}")

def fetch_and_process_data_wanted(context, selected_tag_ids):
    job_ids = set()
    page_num = 0
    limit = 20

    while True:

        timestamp = int(time.time() * 1000)
        base_url = "https://www.wanted.co.kr/api/chaos/navigation/v1/results"

        query_parts = [
            f"{timestamp}=",
            "job_group_id=518",
            "country=all",
            "job_sort=job.latest_order",
            "years=-1",
            f"limit={limit}"
        ]
        for tag_id in selected_tag_ids:
            query_parts.append(f"job_ids={tag_id}")

        if page_num > 0:
            query_parts.append(f"offset={page_num * limit}")

        full_url = base_url + "?" + "&".join(query_parts)
        pprint(f"[요청 {page_num + 1}] URL: {full_url}")

        try:
            response = context.request.get(full_url)
            if not response.ok:
                pprint(f"요청 실패: {response.status} - {response.text()}")
                break

            data = response.json()
        except Exception as e:
            pprint(f"응답 파싱 실패: {e}")
            break

        job_list = data.get("data", [])
        if not job_list:
            pprint("더 이상 데이터가 없습니다. 종료합니다.")
            break

        for job in job_list:
            job_id = job.get("id")
            if job_id is not None:
                job_ids.add(job_id)
                pprint(f"공고 ID 수집: {job_id}")

        pprint(f"현재까지 수집된 고유 공고 ID 수: {len(job_ids)}")

        page_num += 1
        time.sleep(1)
    pprint(f"공고ID:, {list(job_ids)}")
    return list(job_ids)

def submit_resume_wanted(context, resume_key, job_ids):
    """
    context: 로그인된 Playwright context (API 요청용)
    resume_key: 선택된 이력서의 key
    job_ids: 지원할 공고 ID 리스트
    """
    if not job_ids:
        pprint("지원할 공고가 없습니다.")
        return

    print("\n=== 지원자 정보 입력 ===")
    email = input("이메일: ").strip()
    username = input("이름: ").strip()
    mobile = input("휴대폰 번호 (예: +821012345678): ").strip()

    print("\n=== 최종 제출 정보 확인 ===")
    pprint(f"이메일: {email}")
    pprint(f"이름: {username}")
    pprint(f"휴대폰: {mobile}")
    pprint(f"이력서 선택됨")
    pprint(f"총 지원할 공고 수: {len(job_ids)}개")

    confirm = input("\n위 정보로 제출하시겠습니까? (y/n): ").strip().lower()
    if confirm != 'y':
        pprint("제출이 취소되었습니다.")
        return

    success_count = 0
    fail_count = 0

    for idx, job_id in enumerate(job_ids, 1):
        pprint(f"\n[{idx}/{len(job_ids)}] 공고 ID {job_id} 지원 중...")

        payload = {
            "email": email,
            "username": username,
            "mobile": mobile,
            "resume_keys": [resume_key],
            "job_id": job_id,
            "nationality_code": "KR",
            "visa": None,
            "status": "apply"
        }

        timestamp = int(time.time() * 1000)
        url = f"https://www.wanted.co.kr/api/chaos/applications/v1?{timestamp}="

        try:
            response = context.request.post(url, data=payload)
            if response.ok:
                pprint(f"지원 성공!")
                success_count += 1
            else:
                pprint(f"지원 실패 - 상태코드: {response.status}, 응답: {response.text()}")
                fail_count += 1

            time.sleep(1) # 딜레이조정

        except Exception as e:
            pprint(f"처리 중 오류 발생: {e}")
            fail_count += 1
            continue

    pprint(f"\n=== 지원 완료 ===")
    pprint(f"성공: {success_count}건")
    pprint(f"실패: {fail_count}건")
    pprint(f"총 {len(job_ids)}건 처리됨")


if __name__ == "__main__":
    target_url = "https://www.wanted.co.kr/"
    p, context, page = login_recruitment_site(target_url)
    resume_key = extract_resume_titles_wanted(context)
    if not resume_key:
        pprint("이력서 선택 실패")
        context.close()
        p.stop()
        sys.exit(0)
    selected_tag_ids = fetch_category_data_wanted(context)
    job_ids = fetch_and_process_data_wanted(context, selected_tag_ids)
    submit_resume_wanted(page,resume_key, job_ids)
    input("제출완료. 끝내려면 아무키나 누르고 Enter을 누르세요")
    context.close()
    p.stop()
