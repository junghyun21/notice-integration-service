#-- 글로벌미디어학부 --#
# 공지사항 내에서 추출한 모든 데이터 저장 형식
# homepage_ = [
#     {'admin': '컴퓨터학부',
#      'url': 각 공지사항들의 url,
#      'num': 각 공지사항들의 번호,
#      'title': 공지사항 제목,
#      'date': 작성일자,
#      'content': 공지사항 세부 내용,
#      'attach': {attach_name: attach, 
#                 attach_name: attach, 
#                         .
#                         .
#                         .
#                                     }
#     }
#             .
#             .
#             .
# ]


from flask import Flask
from bs4 import Tag

import requests
from bs4 import BeautifulSoup
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import time


BASE_URL = "http://media.ssu.ac.kr/"
# 크롤링할 사이트의 URL 정보 -> 공지사항 리스트 페이지의 URL은 page만 변경됨
# 1페이지는 page 값이 1, 2페이지는 page 값이 2, ... N페이지는 page 값이 N
FRONT_URL = "sub.php?code=XxH00AXY&mode="
BACK_URL = "&category=1&searchType=&search=&orderType=&orderBy=&page="
NOTICE_URL = "view&board_num="

page = 1

# 글로벌미디어학부의 공지사항에서 번호가 '공지'인 공지사항은 1페이지에서만 나타남
# 따로 '공지'인 공지사항의 개수를 카운트할 필요 없음


# ================== 각 페이지에서 html 가져오기 ===================
# - url에 해당하는 페이지에서 html 소스코드 가져오기
# - 페이지에서 가져온 html 소스의 타입은 <class 'bs4.element.Tag'>
# * parameter: url -> 페이지에서 긁어온 html 소스    
# * return 값: html -> 페이지에서 긁어온 html 소스  
def get_html(url):
    
    try:
        response = requests.get(url)

    except requests.exceptions.MissingSchema:
        print("잘못된 URL입니다.")
        exit()
        
    # 글로벌미디어학부 홈페이지에서 데이터 추출 시 한글이 깨짐현상 발생
    html = BeautifulSoup(response.content.decode('utf-8','replace'), "html.parser")
    
    return html


# ==================== 각 공지사항들의 링크 추출 ====================
# - 공지사항 리스트 페이지에서 a 태그를 활용하여 각 공지사항들의 링크를 추출
# - 추출한 값의 type은 <class 'str'>
# - 페이지 번호에 상관없이 모든 공지사항내에서 정보 추출
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: urls -> 각 공지사항들의 링크를 저장한 리스트
def extractURLs(html):
    unprocessed_urls = []
    urls = []
    
    # 공지사항 리스트 페이지에서 각 공지사항에 해당하는 부분 추출
    temp = html.select("table#boardSkin_s_default > tbody > tr.odd > td > a")
    unprocessed_urls.extend(temp)
    
    # 자바스크립트 함수 호출을 통해 공지사항 페이지를 불러오는 형태
    # 필요한 부분만 추출하여 가공
    for url in unprocessed_urls:
        notice_url = url.attrs["onclick"]
        notice_url = notice_url.replace("viewData('", "")
        notice_url = notice_url.replace("'); return false;", "")
        urls.append(notice_url)
    
    # 실제 링크와 동일하게 데이터 가공
    for i in range(0, len(urls)):
        url = BASE_URL + FRONT_URL + NOTICE_URL + urls[i] + BACK_URL + str(page)
        urls[i] = url
    
    return urls
    

# ==================== 각 공지사항들의 번호 추출 ====================
# - 공지사항 리스트 페이지에서 table 태그 활용하여 각 공지사항들의 번호 추출
# - 추출한 값의 type은 <class 'str'>
# - 추출한 값들은 '공지' or '숫자(공지가 아닌 것)'
# - 첫번째 페이지일 때만 번호가'공지'에 해당하는 공지사항의 번호 부분 데이터 가공
# - 두번째 페이지부터는 모두 추출하고 가공
# * parameter: html -> 페이지에서 긁어온 html 소스 
# * return 값: nums -> 각 공지사항들의 번호를 저장한 리스트
def extractNum(html):
    unprocessed_nums = []
    nums = []
        
    temp = html.select("table#boardSkin_s_default > tbody > tr.odd > td")
    unprocessed_nums.extend(temp)
    
    # 번호 부분 추출
    # '공지'인 경우는 빈 문자열이 저장됨 -> '공지'로 변경
    for i in range(0, len(unprocessed_nums), 5):
        num = unprocessed_nums[i].get_text().strip()
        if num == "":
            num = "공지"
        
        nums.append(num)
    
    return nums

  
# ================== 각 공지사항들의 작성일자 추출 ===================
# - 공지사항 리스트 페이지에서 table 태그 활용하여 작성일자 추출
# - 추출한 값의 type은 <class 'str'>
# - 첫번째 실행될 때에는 모든 공지사항의 작성일자 추출
# - 두번째부터는 번호가 '공지'인 공지사항을 제외한 나머지 공지사항에서만 추출
# - 추출한 값을 dic 'date'의 value에 저장 후, 해당 dic을 dates에 추가
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: dates -> 각 공지사항들의 작성일자를 저장한 리스트
def extractDate(html):
    unprocessed_dates = []
    dates = []

    temp = html.select("table#boardSkin_s_default > tbody > tr.odd > td")
    unprocessed_dates.extend(temp)
        
    # 번호 부분 추출
    for i in range(3, len(unprocessed_dates), 5):
        date = unprocessed_dates[i].get_text().strip()        
        dates.append(date)
    
    return dates
    

# ==================== 각 공지사항들의 제목 추출 ====================
# - 각 공지사항 내에서 table 태그 활용하여 제목 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: title -> 해당 공지사항의 제목
def extractTitle(html):
    title = html.select_one("table#boardSkin_s_default_view > thead").get_text().strip()
    
    return title


# ==================== 각 공지사항들의 내용 추출 ====================
# - 각 공지사항 내에서 table 태그 활용하여 공지사항 내용 추출
# - 추출한 값의 type은 <class 'bs4.element.Tag'> x, <class 'str'> O
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: content -> 해당 페이지의 내용
def extractContent(html):
    content = html.select_one("table#boardSkin_s_default_view td.s_default_view_body_2").get_text().strip()

    return content


# ============== 각 공지사항들의 첨부파일과 첨부파일 추출 ===============
# - 각 공지사항 내에서 table 태그 내 span.file를 활용하여 첨부파일과 첨부파일명 추출
# - 추출한 값들의 type은 <class 'str'>
# - 첨부파일명(attach_name)은 key, 첨부파일(attach)은 value로 딕셔너리에 저장
# - 첨부파일은 0개 이상이기 때문에 각각의 딕셔너리를 리스트인 attachs에 저장
# * parameter: html -> 페이지에서 긁어온 html 소스 
# * return 값: attachs -> 첨부파일명과 첨부파일들을 짝지어 저장한 딕셔너리
def extractAttach(html):
    attachs = {}

    # 공지사항 내 첨부파일 부분 추출
    unprocessed_attachs = html.select("table#boardSkin_s_default_view table table table td > a ")

    for temp in unprocessed_attachs:
        attach_name = temp.get_text().strip()
        attach = temp.attrs["href"]
        
        attachs[attach_name] = attach
 
    return attachs


# # ============= 추출한 데이터들을 JSON 파일로 변환하여 저장 ==============
# # - 모든 데이터를 저장하고 있는 리스트의 값을 바탕으로 JSON 파일 생성
# # * parameter: homepage_global -> 소프트웨어 공지사항에서 추출한 모든 데이터
# def toJSON(homepage_global):
#     file_path = "./json/homepage_global.json"
    
# #     with open(file_path, 'w', encoding='utf-8') as file:
# #     json.dump(data, file, indent="\t")
    
#     with open(file_path, "w") as outfile:
#         outfile.write(json.dumps(homepage_global, indent=4, ensure_ascii=False))
    
    
# ==============================================================    
def main(): 
    global page
    
    # 글로벌미디어학부 공지사항에서 추출한 모든 데이터를 저장할 리스트
    # 리스트의 각 요소들은 각 공지사항에서 추출한 모든 데이터를 담고 있는 딕셔너리(dic)
    homepage_global = []
    # 각 공지사항에서 추출할 데이터 리스트
    dic_keys = ['admin', 'url', 'num', 'title', 'date', 'content', 'attach']

    # 공지사항 리스트 페이지에서 각 공지사항의 링크, 번호, 작성일자 추출
    while True:
        # 마지막 페이지의 마지막 공지사항의 번호는 '1'
        if len(homepage_global) != 0 and homepage_global[len(homepage_global)-1]['num'] == '1':
            break
        
        # 공지사항 리스트 페이지의 링크 -> 크롤링할 대상
        noticeList_url = BASE_URL + FRONT_URL + BACK_URL + str(page)
        html = get_html(noticeList_url)

        # 공지사항 리스트 페이지에서 번호, 링크, 작성일자 추출
        # 추출한 데이터들은 각각의 리스트(nums, urls, dates)에 저장됨
        nums = extractNum(html)
        urls = extractURLs(html)
        dates = extractDate(html)

        # homepage_global 리스트에 추출한 값들 저장
        for url, num, date in zip(urls, nums, dates):
            # 공지사항 내에서 추출한 데이터를 저장할 딕셔너리 생성
            # 딕셔너리의 키 값들은 dic_keys 값
            # dic_keys = ['admin', 'url', 'num', 'title', 'date', 'content', 'attach']
            # 우선 추출한 링크, 번호, 작성일자 저장
            url = url.text if isinstance(url, Tag) else url
            num = num.text if isinstance(num, Tag) else num
            date = date.text if isinstance(date, Tag) else date

            dic = dict(zip(dic_keys, ['글로벌미디어학부', url, num, None, date, None, None]))

            # 공지사항의 정보를 담은 딕셔너리를 homepage_global 리스트에 저장
            homepage_global.append(dic)
        
        # 다음 페이지 크롤링하기 위함
        page += 1
        

    # 모든 공지사항의 링크(url), 번호(num), 작성일자(date) 추출 완료
    # -> 이는 모두 homepage_global 리스트 내에 저장되어 있음
    # 다음은 각각의 공지사항의 링크를 활용하여 공지사항 내의 제목, 내용, 첨부파일 추출
    for i in range(0, len(homepage_global)):
        # 각 공지사항의 링크는 homepage_global 리스트 내에 저장되어 있음
        # 공지사항 내 페이지 가져오기
        html = get_html(homepage_global[i]['url'])

        # 공지사항 내에서 제목, 내용, 첨부파일 추출
        # 추출한 제목과 내용은 해당하는 리스트에 해당되는 요소 내에 저장
        # 추출한 첨부파일들은 딕셔너리(attach)에 저장 -> 첨부파일은 0개 이상 존재
        title = extractTitle(html)
        content = extractContent(html)
        attach = extractAttach(html)

        homepage_global[i]['title'] = title.text if isinstance(title, Tag) else title
        homepage_global[i]['content'] = content.text if isinstance(content, Tag) else content
        homepage_global[i]['attach'] = attach.text if isinstance(attach, Tag) else attach

    # toJSON(homepage_global)
    # data = json.dumps(homepage_global)
    data = json.dumps(homepage_global, indent=4, ensure_ascii=False)
    
    # 보낼 스프링 부트 서버 주소 -> ec2 주소 + 아래 데이터 받는 api => ec2 + /savedata/univ
    urlspring = 'http://ec2-3-39-206-176.ap-northeast-2.compute.amazonaws.com:8080/savedata/gm'
    # 보내기 실행
    response = requests.post(urlspring, data=data, headers={'Content-Type': 'application/json'})

    # print(data)


# ==========================================================================
# ========================= 코드 주기적으로 자동 실행 ============================
# ==========================================================================

app = Flask(__name__)
app.run('0.0.0.0', port=5000, debug=True)

# BackgroundScheduler 를 사용 시,
# stat를 먼저 -> add_job 을 이용해 수행할 것을 등록
sched = BackgroundScheduler()
sched.start()

# interval - 매 3초마다 실행
# sched.add_job(main, 'interval', seconds=3, id="test_2")

# cron 사용 - 매 10분마다 job 실행
# 	: id 는 고유 수행번호로 겹치면 수행되지 않습니다.
# 	만약 겹치면 다음의 에러 발생 => 'Job identifier (test_1) conflicts with an existing job'
sched.add_job(main, 'cron', minute='*/10', id="main")

# cron 으로 하는 경우는 다음과 같이 파라미터를 상황에 따라 여러개 넣어도 됩니다.
# 	매시간 0분 0초에 실행한다는 의미
# sched.add_job(main, 'cron', minute="0", second="0", id="main")

while True:
    print("Running main process...............")
    time.sleep(1)