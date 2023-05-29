#-- AI융합학부 --#
# 공지사항 내에서 추출한 모든 데이터 저장 형식
# - admin: 작성자
# - url: 해당 공지사항의 링크
# - title: 제목
# - date: 작성일자
# - content: 내용 -> html 소스파일 그대로 긁어옴
# dic = {
#     'admin': 'AI융합학부',
#     'url': None,
#     'title': None,
#     'date': None,
#     'content': None}


from flask import Flask
from bs4 import Tag

import requests
from bs4 import BeautifulSoup
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import time


BASE_URL = "http://aix.ssu.ac.kr/"
# 크롤링할 사이트의 URL 정보 -> 공지사항 리스트 페이지의 URL은 page만 변경됨
# 1페이지는 page 값이 1, 2페이지는 page 값이 2, ... N페이지는 page 값이 N
NOTICE_LIST_URL = BASE_URL + "notice.html?&page="


# ================== 각 페이지에서 html 가져오기 ===================
# - url에 해당하는 페이지에서 html 소스코드 가져오기
# - 페이지에서 가져온 html 소스의 타입은 <class 'bs4.element.Tag'>
# * parameter: url -> 크롤링할 페이지의 링크   
# * return 값: html -> 페이지에서 긁어온 html 소스  
def get_html(url):
    
    try:
        response = requests.get(url)

    except requests.exceptions.MissingSchema:
        print("잘못된 URL입니다.")
        exit()
        
    html = BeautifulSoup(response.content.decode('utf-8','replace'), "html.parser")
    
    return html


# =================== 공지사항이 더 존재하는지 확인 ====================
# - 만약 더 이상 공지사항이 없으면 해당 페이지의 공지사항은 비어있음
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: True/False
def hasNotice(html):
    temp = html.select("div.table-responsive > table.table td")
    
    # 빈 리스트인 경우(더 이상 공지사항이 없는 경우) -> False
    if not temp:
        return False
    else:
        return True


# ==================== 각 공지사항들의 링크 추출 ====================
# - 공지사항 리스트 페이지에서 a 태그를 활용하여 각 공지사항들의 링크를 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: urls -> 각 공지사항들의 링크를 저장한 리스트
def extractURLs(html):
    unprocessed_urls = []
    urls = []
    
    # 공지사항 리스트 페이지에서 공지사항의 링크 부분 추출
    temp = html.select("div.table-responsive > table.table td > a")
    unprocessed_urls.extend(temp)
    
    # 링크 부분에서 링크만 추출 후, 절대경로로 가공하여 저장
    for url in unprocessed_urls:
        notice_url = url.attrs["href"]
        urls.append(BASE_URL + notice_url)
    
    return urls

  
# ================== 각 공지사항들의 작성일자 추출 ===================
# - 공지사항 리스트 페이지에서 table 태그 활용하여 작성일자 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: dates -> 각 공지사항들의 작성일자를 저장한 리스트
def extractDate(html):
    unprocessed_dates = []
    dates = []
    
    # 공지사항 리스트 페이지에서 공지사항의 작성일자 부분 추출
    temp = html.select("div.table-responsive > table.table td")
    unprocessed_dates.extend(temp)
        
    for i in range(2, len(unprocessed_dates), 4):
        date = unprocessed_dates[i].get_text().strip()        
        dates.append(date)
    
    return dates
    

# ==================== 각 공지사항들의 제목 추출 ====================
# - 각 공지사항 내에서 table 태그 활용하여 제목 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: title -> 해당 공지사항의 제목
def extractTitle(html):
    title = html.select_one("div.table-responsive table.table tr h4").get_text().strip()
    
    return title


# ==================== 각 공지사항들의 내용 추출 ====================
# - 각 공지사항 내에서 table 태그 활용하여 공지사항 내용 추출
# - 추출한 값의 type은 <class 'bs4.element.Tag'> x, <class 'str'> O
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: content -> 해당 페이지의 내용
def extractContent(html):
    contents = html.select("div.table-responsive table.table tr td p")
    content = ""
    for c in contents:
        content += c.get_text().strip()

    return content


# # ============= 추출한 데이터들을 JSON 파일로 변환하여 저장 ==============
# # - 모든 데이터를 저장하고 있는 리스트의 값을 바탕으로 JSON 파일 생성
# # * parameter: homepage_software -> 소프트웨어 공지사항에서 추출한 모든 데이터
# def toJSON(homepage_ai):
#     file_path = "./json/homepage_ai.json"
    
# #     with open(file_path, 'w', encoding='utf-8') as file:
# #     json.dump(data, file, indent="\t")
    
#     with open(file_path, "w") as outfile:
#         outfile.write(json.dumps(homepage_ai, indent=4, ensure_ascii=False))
    

def main():
    # AI 융합학부 공지사항에서 추출한 모든 데이터를 저장할 리스트
    # 리스트의 각 요소들은 각 공지사항에서 추출한 모든 데이터를 담고 있는 딕셔너리(dic)
    homepage_ai = []
    # 각 공지사항에서 추출할 데이터 리스트
    dic_keys = ['admin', 'url', 'title', 'date', 'content']

    # 공지사항 리스트의 첫번째 페이지부터 크롤링 진행
    page = 1

    # 공지사항 리스트 페이지에서 각 공지사항의 링크, 작성일자 추출
    while True:
        print("공지사항 페이지" + str(page))
        # 공지사항 리스트 페이지의 링크 -> 크롤링할 대상
        noticeList_url = NOTICE_LIST_URL + str(page)
        
        html = get_html(noticeList_url)
        
        # 더 이상 페이지가 없으면 반복문 종료
        if hasNotice(html) is False:
            break

        # 공지사항 리스트 페이지에서 링크, 작성일자 추출
        # 추출한 데이터들은 각각의 리스트(urls, dates)에 저장됨
        urls = extractURLs(html)
        dates = extractDate(html)

        # homepage_ai 리스트에 추출한 값들 저장
        for url, date in zip(urls, dates):
            # 공지사항 내에서 추출한 데이터를 저장할 딕셔너리 생성
            # 딕셔너리의 키 값들은 dic_keys 값
            # dic_keys = ['admin', 'url', 'title', 'date', 'content']
            # 우선 추출한 링크, 작성일자 저장
            url = url.text if isinstance(url, Tag) else url
            date = date.text if isinstance(date, Tag) else date

            dic = dict(zip(dic_keys, ['AI융합학부', url, None, date, None]))

            # 공지사항의 정보를 담은 딕셔너리를 homepage_ai 리스트에 저장
            homepage_ai.append(dic)
        
        # 다음 페이지 크롤링하기 위함
        page += 1
        

    # 모든 공지사항의 링크(url), 작성일자(date) 추출 완료
    # -> 이는 모두 homepage_ai 리스트 내에 저장되어 있음
    # 다음은 각각의 공지사항의 링크를 활용하여 공지사항 내의 제목, 내용 추출
    for i in range(0, len(homepage_ai)):  
        print("공지사항" + str(i))
        html = get_html(homepage_ai[i]['url'])

        # 공지사항 내에서 제목, 내용 추출
        # 추출한 제목과 내용은 해당하는 리스트에 해당되는 요소 내에 저장
        title = extractTitle(html)
        content = extractContent(html)

        homepage_ai[i]['title'] = title.text if isinstance(title, Tag) else title
        homepage_ai[i]['content'] = content.text if isinstance(content, Tag) else content

    # toJSON(homepage_ai)
    # data = json.dumps(homepage_ai)
    data = json.dumps(homepage_ai, indent=4, ensure_ascii=False)

    # print(data)

# ==========================================================================
# ========================= 코드 주기적으로 자동 실행 ============================
# ==========================================================================

# BackgroundScheduler 를 사용 시,
# stat를 먼저 -> add_job 을 이용해 수행할 것을 등록
sched = BackgroundScheduler()
sched.start()

# interval - 매 3초마다 실행
# sched.add_job(main, 'interval', seconds=3, id="test_2")

# cron 사용 - 매 5분마다 job 실행
# 	: id 는 고유 수행번호로 겹치면 수행되지 않습니다.
# 	만약 겹치면 다음의 에러 발생 => 'Job identifier (test_1) conflicts with an existing job'
sched.add_job(main, 'cron', minute='*/5', id="main")

# cron 으로 하는 경우는 다음과 같이 파라미터를 상황에 따라 여러개 넣어도 됩니다.
# 	매시간 0분 0초에 실행한다는 의미
# sched.add_job(main, 'cron', minute="0", second="0", id="main")

while True:
    print("Running main process...............")
    time.sleep(1)
    

