#-- 페이지 1부터 10까지의 모든 공지사항 내에서 데이터 추출 --#
# homepage_univ = [
# 		{'admin': '숭실대학교'
#        'url': url, 
# 		 'title': title,
# 		 'category': category,
# 		 'date': date,
# 		 'content': content}
# ]


from flask import Flask
from bs4 import Tag

import requests
from bs4 import BeautifulSoup
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import time


PAGE_NUM = 10 # 1~10페이지까지 크롤링, 크롤링할 페이지 변경시키고 싶으면 해당 변수 변경하면 됨


# # ============= 추출한 데이터들을 JSON 파일로 변환하여 저장 ==============
# # - 모든 데이터를 저장하고 있는 리스트의 값을 바탕으로 JSON 파일 생성
# # * parameter: homepage_computer -> 컴퓨터학부 공지사항에서 추출한 모든 데이터
# def toJSON(homepage_univ):
#     file_path = "./homepage_univ.json"
    
# #     with open(file_path, 'w', encoding='utf-8') as file:
# #     json.dump(data, file, indent="\t")
    
#     with open(file_path, "w") as outfile:
#         outfile.write(json.dumps(homepage_univ, indent=4, ensure_ascii=False)) 
        


def main():
    # 크롤링할 사이트의 URL: 학교 홈페이지 공지사항 첫번째 페이지
    base_url = "https://scatch.ssu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/"
    urls = []

    # 크롤링 대상이 되는 페이지의 URL 추출
    crawling_url = base_url

    # 페이지 1부터 10까지 모든 페이지 내의 공지사항들의 링크 추출
    for page in range(1,PAGE_NUM + 1):
        crawling_url = base_url + "page/" + str(page) +"/"
        
        # 사이트 메인 페이지 가져오기
        try:
            # 웹 페이지 가져오기
            response = requests.get(crawling_url)
        except requests.exceptions.MissingSchema:
            print("잘못된 URL입니다.")
        else:
            # 사용 중인 인코딩 확인 후, 그에 맞게 변환하여 가져옴
            # base_url의 페이지 내의 모든 html을 문자열로 가져옴
            bs_obj = BeautifulSoup(response.text, "html.parser")

            # 각 페이지들의 제목(페이지 링크)를 나타내는 태그 내용 추출
            lis = bs_obj.select("ul.notice-lists > li > div > div.notice_col3 > a")

            # 각 페이지들의 링크 추출 후, urls 리스트 내에 저장
            for li in lis:
                url = li.get("href")
                urls.append(url)

    # 학교 공지홈페이지의 모든 데이터를 저장할 리스트
    homepage_univ = []

    # 각 공지사항(url) 내의 데이터 추출
    for url in urls:
        url = url.text if isinstance(url, Tag) else url

        # 해당 url 내의 데이터들을 저장할 딕셔너리
        dic = {"admin": '숭실대학교', "url": url}
        
        try:
            # 웹 페이지 가져오기
            response = requests.get(url)
        except requests.exceptions.MissingSchema:
            print("잘못된 URL입니다.")
        else:
            # 사용 중인 인코딩 확인 후, 그에 맞게 변환하여 가져옴
            # url의 페이지 내의 모든 html을 문자열로 가져옴
            bs_obj = BeautifulSoup(response.text, "html.parser")

            # 공지사항 페이지에서 공지사항에 해당하는 부분만 추출
            notice = bs_obj.select_one("div.bg-white")

            # 카테고리, 제목 추출
            category = notice.select_one("span.label.small.d-inline-block.border.pl-3.pr-3").get_text()
            title = notice.select_one("h2.font-weight-light.mb-3").get_text()

            # 작성일자, 첨부파일, 내용 추출 -> <div> 태그
            datas = notice.select("div")

            date = datas[1].get_text()

            # 날짜 형식: 2023년 5월 12일 -> 0000-00-00
            date = date.replace(" ", "") # 공백제거
            temp = ""
            for d in date:
                if d == "년" or d == "월":
                    temp += "-"
                elif d == "일":
                    pass
                else:
                    temp += d
            date = temp
            if date[6] == "-":
                date = date[:5] + "0" + date[5:]
            if len(date) != 10:
                date = date[:8] + "0" + date[8:]

            # # 첨부파일 이름
            # attach_name = datas[4].select("ul.download-list > li > a > span")
            # attach_names = []
            # for a in attach_name:
            #     temp = a.get_text()
            #     attach_names.append(temp)
            # # 첨부파일    
            # attach = datas[4].select("ul.download-list > li > a")
            # attachs = []
            # for a in attach:
            #     temp = a.get("href")
            #     attachs.append(temp)

            # 공지사항 내용은 html 소스코드 그대로 저장
            # <ul class="download-list">는 첨부파일 태그이기 때문에 공지사항 내용에서 제외
            # 만약 첨부파일이 없다면(None) -> NoneType은 decompose() 불가
            content = datas[4]
            if datas[4].select_one("ul.download-list") is not None:
                datas[4].select_one("ul.download-list").decompose()
                
            content = content.get_text()

            title = title.text if isinstance(title, Tag) else title
            category = category.text if isinstance(category, Tag) else category
            date = date.text if isinstance(date, Tag) else date
            content = content.text if isinstance(content, Tag) else content
            
            # 딕셔너리에 추출한 데이터들 저장
            dic["title"] = title
            dic["category"] = category
            dic["date"] = date
            dic["content"] = content
            # dic_attach = {}
            # for attach, attach_name in zip(attachs, attach_names):
            #     dic_attach[attach_name] = attach
            # dic["attach"] = dic_attach
            
            # 리스트에 추출한 데이터 저장
            homepage_univ.append(dic)
            
    # toJSON(homepage_univ)
    # data = json.dumps(homepage_univ)
    data = json.dumps(homepage_univ, indent=4, ensure_ascii=False)

    # 보낼 스프링 부트 서버 주소 -> ec2 주소 + 아래 데이터 받는 api => ec2 + /savedata/univ
    urlspring = 'http://ec2-3-39-206-176.ap-northeast-2.compute.amazonaws.com:8080/savedata/univ'
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

