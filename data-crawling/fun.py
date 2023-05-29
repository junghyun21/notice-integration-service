#-- 펀시스템 --#
# 각각의 카테고리 내에서 1~9페이지 내의 데이터 크롤링
# 공지사항 내에서 추출한 모든 데이터 저장 형식
# fun_system = [
#     {'admin': '펀시스템',
#      'url': 각 공지사항들의 url, 
#      'category': 각 공지사항들의 카테고리,
#      'title': 공지사항 제목,
#      'applyPeriod': 신청 기간 = [시작일자, 종료일자],
#      'operatePeriod': 운영 기간 = [시작일자, 종료일자],
#      'cover': 커버 사진,
#      'tag': 태그 = [태그1, 태그2, ...],
#      'target': 모집대상 = [전체 학생/대학원생/교수/교직원, 학년, 성별, 학과],
#      'summary': 공지사항 요약
#      'content': 공지사항 세부 내용
#      'attach': {attach_name: attach, 
#                 attach_name: attach, 
#                         .
#                         .
#                         .
#                 attach_name: attach}


from flask import Flask
from bs4 import Tag

import requests
from bs4 import BeautifulSoup
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import time


BASE_URL = "https://fun.ssu.ac.kr"
# 각각의 카테고리에 해당하는 url을 크롤링할 url -> 카테고리 중 '전체'에 해당
ALL_URL = "https://fun.ssu.ac.kr/ko/program/all"
# BASE_URL + '카테고리 별 url' + PAGE_URL + page
PAGE_URL = "/list/all/"

PAGE_NUM = 9 # 1~9페이지까지 크롤링, 크롤링할 페이지 변경시키고 싶으면 해당 변수 변경하면 됨


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

    html = BeautifulSoup(response.text, "html.parser")
    
    return html


# ================ 각 공지사항들의 카테고리와 링크 추출 =================
# - 프로그램 전체 페이지에서 각 카테고리들의 명칭과 링크 추출
# - 추출한 값의 type은 <class 'str'>
# - 추출한 값 중 카테고리 명칭은 key, 링크는 value에 저장
# * parameter: html -> 페이지에서 긁어온 html 소스    
# * return 값: categories -> 각 카테고리의 명칭과 링크를 짝지어 저장한 딕셔너리
def get_categories(html):
    categories = {}
    
    unprocessed_categories = html.select("main.program > nav.category > div.container > ul > li > a")

    for c in unprocessed_categories:
        category_name = c.get_text()
        category_url = BASE_URL + c.attrs["href"]
        
        categories[category_name] = category_url

    # categories 내에 '전체'에 해당하는 카테고리의 정보도 저장됨
    # 이 페이지는 크롤링할 대상에 포함되지 않으므로 삭제
    del categories['전체']
    
    return categories
    
    
# ==================== 각 공지사항들의 링크 추출 ====================
# - 공지사항 리스트 페이지에서 a 태그를 활용하여 각 공지사항들의 링크를 추출
# - 추출한 값들은 모두 urls 리스트 내에 저장
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: urls -> 각 공지사항들의 링크를 저장한 리스트
def get_URLs(html):
    urls = []
    
    unprocessed_urls = html.select("main.program > div.container ul.columns-4 li a")

    for u in unprocessed_urls:
        url = BASE_URL + u.attrs["href"]
        urls.append(url)

    return urls


# =================== 각 공지사항들의 신청기간 추출 ===================
# - 공지사항 리스트 페이지에서 각 공지사항들의 신청기간 추출
# - 신청기간을 저장한 리스트의 각 요소들은 [시작일자, 종료일자]로 구성되어 있음
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: applyPeriods -> 각 공지사항들 내 프로그램의 신청기간을 저장한 리스트
def get_applyPeriods(html):
    applyPeriods = []
    
    periods = html.select("main.program > div.container ul.columns-4 li a > div.content > small > time")
    
    for i in range(0, len(periods), 4):
        start = periods[i].get_text().strip()
        end = periods[i+1].get_text().strip()

        # 종료일자에 시간만 있는 경우 -> 시작일자와 종료일자가 동일한 경우
        # 시작일자의 일자 부분과 종료 시간을 합쳐야함
        if end[2] == ':':
            end = start[:len(start)-5] + end
        
        period = [start, end]
        
        applyPeriods.append(period)
        
    return applyPeriods


# =================== 각 공지사항들의 운영기간 추출 ===================
# - 공지사항 리스트 페이지에서 각 공지사항들의 운영기간 추출
# - 운영기간을 저장한 리스트의 각 요소들은 [시작일자, 종료일자]로 구성되어 있음
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: operatePeriods -> 각 공지사항 내 프로그램의 운영기간을 저장한 리스트
def get_operatePeriods(html):
    operatePeriods = []
    
    periods = html.select("main.program > div.container ul.columns-4 li a > div.content > small > time")
    
    for i in range(2, len(periods), 4):
        start = periods[i].get_text().strip()
        end = periods[i+1].get_text().strip()

        # 종료일자에 시간만 있는 경우 -> 시작일자와 종료일자가 동일한 경우
        # 시작일자의 일자 부분과 종료 시간을 합쳐야함
        if end[2] == ':':
            end = start[:len(start)-5] + end
        
        period = [start, end]
        
        operatePeriods.append(period)
        
    return operatePeriods


# ====================== 공지사항의 제목 추출 ======================
# - 공지사항 페이지 내에서 제목 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: title -> 공지사항의 제목
def get_title(html):
    title = html.select_one("div.container div.box > div.title > h4").get_text().strip()
    
    return title


# ===================== 공지사항의 커버사진 추출 ====================
# - 공지사항 페이지 내에서 커버 사진 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: cover -> 공지사항의 커버 사진
def get_cover(html):
    # fun 시스템에서는 커버사진을 자바스크립트 함수 호출을 통해 페이지에 나타냄
    # -> background-image:url(/attachment/view/111839/cover.jpg?ts=1683606560);
    # 위의 코드에서 소괄호 안에 있는 커버사진의 링크를 추출
    unprocessed_cover = html.select_one("div.box > div.cover").get('style')

    # 커버이미지가 없는 경우도 있음
    if unprocessed_cover is None:
        cover = None
    else:
        index_start = unprocessed_cover.find('(') + 1
        index_end = unprocessed_cover.find(')')

        unprocessed_cover = unprocessed_cover[index_start : index_end]

        cover = BASE_URL + unprocessed_cover
    
    return cover


# ===================== 공지사항의 요약본 추출 =====================
# - 공지사항 페이지 내에서 공지사항의 요약본 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: summary -> 공지사항의 내용 요약본
def get_summary(html):
    summary = html.select_one("div.container div.box div > div.text").get_text()
    
    return summary


# ==================== 공지사항의 상세내용 추출 ====================
# - 공지사항 페이지 내에서 공지사항의 내용 추출
# - 우선은 이미지 없이 텍스트만 추출
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: content -> 공지사항 내용
def get_content(html):
    content = html.select_one("div.context > div.description > div").get_text()
    
    return content


# ===================== 공지사항의 태그 추출 =====================
# - 공지사항 페이지 내에서 공지사항에 해당하는 태그들 추출
# - 추출한 값들은 모두 tags 리스트 내에 저장
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: tags -> 공지사항의 태그를 저장한 리스트
def get_tags(html):
    tags = []
    
    unprocessed_tags = html.select("div.container div.box div.title li.tag a")
    
    # 태그는 모두 '#...' 형태이므로, # 제거
    for t in unprocessed_tags:
        tag = t.get_text().strip()
        tag = tag[1:]
        
        tags.append(tag)
    
    return tags


# ==================== 공지사항의 모집 대상 추출 ===================
# - 공지사항 페이지 내에서 해당 프로그램에 참여할 수 있는 모집대상들 추출
# - 추출한 값들은 모두 targets 리스트 내에 저장
# - 추출한 값의 type은 <class 'str'>
# * parameter: html -> 페이지에서 긁어온 html 소스
# * return 값: targets -> 모집하는 대상/학년/성별/학과를 저장한 리스트
def get_targets(html):
    targets = []
    
    unprocessed_targets = html.select("div.container div.box div.title li > span")
    
    for t in unprocessed_targets:
        target = t.get_text().strip()
        
        # '/'이 존재하면 '/'을 기준으로 데이터를 나눠야함
        # ex. 전체 학년/전체 성별 -> 전체 학년, 전체 성별
        if '/' in target:
            index = -1
            # find()는 특정 문자가 없으면 -1 반환
            while True:
                index = target.find('/')
                if index == -1:
                    break
                
                targets.append(target[:index])
                target = target[index+1:]
                
        targets.append(target)
    
    return targets


# ==================== 공지사항의 첨부파일 추출 ====================
# - 각 공지사항 내에서 첨부파일과 첨부파일명 추출
# - 추출한 값들의 type은 <class 'str'>
# - 첨부파일명(attach_name)은 key, 첨부파일(attach)은 value로 딕셔너리에 저장
# - 첨부파일은 0개 이상, 첨부파일의 개수는 attachs의 key의 개수와 동일
# * parameter: html -> 페이지에서 긁어온 html 소스 
# * return 값: attachs -> 첨부파일명과 첨부파일들을 짝지어 저장한 딕셔너리
def get_attachs(html):
    attachs = {}

    unprocessed_attachs = html.select("div.context > div.description > div > ul > li > a")
    
    for a in unprocessed_attachs:
        attach_name = a.get_text().strip()
        attach = BASE_URL + a.attrs["href"]
        
        attachs[attach_name] = attach
 
    return attachs


# # ============= 추출한 데이터들을 JSON 파일로 변환하여 저장 ==============
# # - 모든 데이터를 저장하고 있는 리스트의 값을 바탕으로 JSON 파일 생성
# # * parameter: fun_system -> 펀시스템 프로그램 공지사항에서 추출한 모든 데이터
# def toJSON(fun_system):
#     file_path = "./fun_system.json"
    
# #     with open(file_path, 'w', encoding='utf-8') as file:
# #     json.dump(data, file, indent="\t")
    
#     with open(file_path, "w") as outfile:
#         outfile.write(json.dumps(fun_system, indent=4, ensure_ascii=False))
    

def main(): 
    # 펀시스템 공지사항에서 추출한 모든 데이터를 저장할 리스트
    # 리스트의 각 요소들은 각 공지사항에서 추출한 모든 데이터를 담고 있는 딕셔너리(dic)
    fun_system = []
    # 각 공지사항에서 추출할 데이터 리스트
    dic_keys = ['admin',
                'url',
                'category', 
                'title', 
                'applyPeriod',
                'operatePeriod',
                'cover',
                'tag',
                'target',
                'summary',
                'content',
                'attach']
    
    # '펀시스템 > 프로그램 > 전체' 에서 각각의 카테고리들의 링크를 추출하여 dictionary에 저장
    # info_categories = {'카테고리명1': '링크1', '카테고리명2': '링크2', ...}
    info_categories = {}
    html = get_html(ALL_URL)
    info_categories = get_categories(html)
    
    # 각각의 카테고리의 url에 접속하여 필요한 정보 추출 및 저장
    # 추출 -> url, applyPeriod, operatePeriod
    # 저장 -> 추출한 데이터, admin, category
    # 각 공지사항에 해당하는 딕셔너리에 데이터들 저장한 후 fun_system의 요소로 저장
    for category, category_url in info_categories.items():
        category = category.text if isinstance(category, Tag) else category

        # 각각의 공지사항 리스트 페이지에서 1~9페이지에 해당하는 공지사항의 정보들만 추출
        for page in range(1, PAGE_NUM + 1):
            notice_list_url = category_url + PAGE_URL + str(page)
            
            html = get_html(notice_list_url)
            
            urls = get_URLs(html)
            applyPeriods = get_applyPeriods(html)
            operatePeriods = get_operatePeriods(html)
            
            # dic_keys = ['admin','url','category', 'title', 'applyPeriod', 'operatePeriod', 'cover', 'tag', 'target', 'summary', 'content', 'attach']
            for url, applyPeriod, operatePeriod in zip(urls, applyPeriods, operatePeriods):
                url = url.text if isinstance(url, Tag) else url
                applyPeriod = applyPeriod.text if isinstance(applyPeriod, Tag) else applyPeriod
                operatePeriod = operatePeriod.text if isinstance(operatePeriod, Tag) else operatePeriod

                dic = dict(zip(dic_keys, ['펀시스템', url, category, None, applyPeriod, operatePeriod, None, None, None, None, None, None]))
                fun_system.append(dic)
    
    # 각 카테고리 별로 1~9페이지의 공지사항 내 일부 데이터 추출 및 fun_system 리스트에 저장 완료
    # 다음은 각각의 공지사항의 링크를 활용하여 공지사항 내에서 나머지 데이터 추출
    # -> 제목, 커버사진, 태그, 모집대상, 요약본, 상세내용, 첨부파일
    # 각 공지사항의 링크는 fun_system 리스트 내 저장되어 있음
    for i in range(0, len(fun_system)):
        html = get_html(fun_system[i]['url'])

        title = get_title(html)
        cover = get_cover(html)
        summary = get_summary(html)
        content = get_content(html)
        
        # 태그와 모집대상은 리스트에 저장
        tags = get_tags(html)
        targets = get_targets(html)
        
        # 첨부파일은 딕셔너리에 저장
        # key는 첨부파일명, value는 첨부파일 링크
        attachs = get_attachs(html)
        
        # 각각의 공지사항의 데이터를 저장한 요소에서 key에 해당하는 value 값 저장
        fun_system[i]['title'] = title.text if isinstance(title, Tag) else title
        fun_system[i]['cover'] = cover.text if isinstance(cover, Tag) else cover
        fun_system[i]['summary'] = summary.text if isinstance(summary, Tag) else summary
        fun_system[i]['content'] = content.text if isinstance(content, Tag) else content
        fun_system[i]['tag'] = tags.text if isinstance(tags, Tag) else tags
        fun_system[i]['target'] = targets.text if isinstance(targets, Tag) else targets
        fun_system[i]['attach'] = attachs.text if isinstance(attachs, Tag) else attachs
        
        # print(fun_system[i]['category'], fun_system[i]['title'], fun_system[i]['cover'])

    # toJSON(fun_system)
    # data = json.dumps(fun_system)
    data = json.dumps(fun_system, indent=4, ensure_ascii=False)

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
