# dic = {
#     'admin': '학생회이름',
#     'url': 게시글 url,
#     'img': 대표사진}

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from flask import Flask
from bs4 import Tag

import requests
from bs4 import BeautifulSoup
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
import time


ID = "moassu23"
PW = "moassu2023"

BASE_URL = "https://www.instagram.com"

ID_SOONGSIL = "plussu__63rd" # 총학생회
ID_IT = "it_soongsil" # IT대학 학생회
ID_COMPUTER = "ssu_cse" # 컴퓨터학부 학생회
ID_SOFTWARE = "ssu_soft" # 소프트웨어학부 학생회
ID_GLOBAL = "ssu_globalmedia" # 글로벌미디어학부 학생회
ID_ELECTRONIC = "ssu_electronic_engineering" # 전자정보공학부 학생회
ID_AI = "ssu_ai_conv" # AI융합학부 학생회


# 인스타그램에 로그인하는 함수
# * parameter: browser -> 현재 접속해있는, 로그인을 실행해야하는 화면
def login(browser):
    # 특정 HTML 요소 찾는 함수
    # By 클래스는 한 페이지에서 특정한 요소의 위치를 파악하는데 사용
    browser.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[1]/div/label/input').send_keys(ID)
    browser.find_element(By.XPATH,'//*[@id="loginForm"]/div/div[2]/div/label/input').send_keys(PW)
    browser.find_element(By.XPATH,'//*[@id="loginForm"]/div/div[3]').click()
    time.sleep(10)


def get_html(browser):
    html = BeautifulSoup(browser.page_source, 'html.parser')
    print(html)
    return html


def get_urls(html):
    urls = []

    unprocessed_urls = html.select("div._ac7v._al3n > div._aabd._aa8k._al3l > a")

    for u in unprocessed_urls:
        url = BASE_URL + u.attrs["href"]
        urls.append(url)

    return urls


def get_imgs(html):
    imgs = []

    unprocessed_imgs = html.select("div._ac7v._al3n > div._aabd._aa8k._al3l img")

    for i in unprocessed_imgs:
        img = i.attrs["src"]
        imgs.append(img)

    return imgs


# ============= 추출한 데이터들을 JSON 파일로 변환하여 저장 ==============
# - 모든 데이터를 저장하고 있는 리스트의 값을 바탕으로 JSON 파일 생성
# * parameter: homepage_global -> 소프트웨어 공지사항에서 추출한 모든 데이터
def toJSON(temp):
    file_path = "./json/instagram.json"
    
    with open(file_path, "w") as outfile:
        outfile.write(json.dumps(temp, indent=4, ensure_ascii=False))


def main():
    # 인스타그램에서 추출한 모든 데이터를 저장할 리스트
    # 리스트의 각 요소들은 각 공지사항에서 추출한 모든 데이터를 담고 있는 딕셔너리
    instagram = []
    # 각 게시글에서 추출할 데이터 리스트
    dic_keys = ['admin', 'url', 'img']

    # 크롤링해야하는 인스타그램 계정들의 정보
    admins = ["총학생회", "IT대학생회", "컴퓨터학부학생회", "소프트웨어학부학생회", "글로벌미디어학부학생회", "전자정보공학부학생회", "AI융합학부학생회"]
    ids = [ID_SOONGSIL, ID_IT, ID_COMPUTER, ID_SOFTWARE, ID_GLOBAL, ID_ELECTRONIC, ID_AI]

    # chromedriver_mac_arm64.zip
    # version: 113.0.5672.63
    browser = webdriver.Chrome('./chromedriver')
    browser.set_window_size(999, 777)
    browser.get(BASE_URL)
    time.sleep(10)

    # 인스타그램 로그인
    login(browser)
    
    # 각 학생회 계정에 접속하여 계정 내 게시글의 사진과 링크 긁어오기
    for id, admin in zip(ids, admins):
        url = BASE_URL + '/' + id
        browser.get(url)
        time.sleep(10)

        # 해당 학생회 계정의 인스타그램 html 가져오기
        html = BeautifulSoup(browser.page_source, 'html.parser')

        urls = get_urls(html)
        imgs = get_imgs(html)

        for url, img in zip(urls, imgs):
            admin = admin.text if isinstance(admin, Tag) else admin
            url = url.text if isinstance(url, Tag) else url
            img = img.text if isinstance(img, Tag) else img

            dic = dict(zip(dic_keys, [admin, url, img]))
            instagram.append(dic)
    
    # toJSON(instagram)
    # data = json.dumps(instagram)
    data = json.dumps(instagram, indent=4, ensure_ascii=False)

    # 보낼 스프링 부트 서버 주소 -> ec2 주소 + 아래 데이터 받는 api
    urlspring = 'http://ec2-3-39-206-176.ap-northeast-2.compute.amazonaws.com:8080/savedata/insta'
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