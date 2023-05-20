



import requests
from bs4 import BeautifulSoup
import re
import csv
import time
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller


category = "web3-crypto-series-a"


url = 'https://signal-api.nfx.com/graphql'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
           'Cookie': 'intercom-id-ula4qov4=21030241-48b1-4ddc-8684-76a41099bc75; intercom-session-ula4qov4=; intercom-device-id-ula4qov4=9d396455-d9cf-486e-874f-58fa71bd9164; cf_chl_2=5c759d22a12eab4; cf_clearance=DGblQAz6XErfa26DlmxetyVeWQbW1Xd9lYA4J1qedFU-1678979640-0-160'}
headers_gq = {
    'authority': 'signal-api.nfx.com',
    'accept': '*/*',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'dnt': '1',
    'origin': 'https://signal.nfx.com',
    'referer': 'https://signal.nfx.com/',
    'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
}


payload = {
    'operationName': 'vclInvestors',
    'variables': {
        'slug': 'ai-pre-seed',
        'order': [
            {},
        ],
        'after': 'OA',
    },
    'query': 'query vclInvestors($slug: String!, $after: String) {\n  list(slug: $slug) {\n    id\n    slug\n    investor_count\n    vertical {\n      id\n      display_name\n      kind\n      __typename\n    }\n    location {\n      id\n      display_name\n      __typename\n    }\n    stage\n    firms {\n      id\n      name\n      slug\n      __typename\n    }\n    scored_investors(first: 8, after: $after) {\n      pageInfo {\n        hasNextPage\n        hasPreviousPage\n        endCursor\n        __typename\n      }\n      record_count\n      edges {\n        node {\n          ...investorListInvestorProfileFields\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment investorListInvestorProfileFields on InvestorProfile {\n  id\n  person {\n    id\n    first_name\n    last_name\n    name\n    slug\n    is_me\n    is_on_target_list\n    __typename\n  }\n  image_urls\n  position\n  min_investment\n  max_investment\n  target_investment\n  is_preferred_coinvestor\n  firm {\n    id\n    name\n    slug\n    __typename\n  }\n  investment_locations {\n    id\n    display_name\n    location_investor_list {\n      id\n      slug\n      __typename\n    }\n    __typename\n  }\n  investor_lists {\n    id\n    stage_name\n    slug\n    vertical {\n      id\n      display_name\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n',
}


def retry(iters):
    def _retry(func):
        def wrapper(*args, **kwargs):
            for i in range(iters):
                try:
                    val = func(*args, **kwargs)
                    return val
                except:
                    time.sleep(1)
            else:
                return ''
        return wrapper
    return _retry


class Parser:
    def __init__(self):
        self.init_webdriver()        
        self.write_row([['Name', 'Title', 'LinkedIn']])
        self.parse_all_pages()
        print(f'Найдено инвесторов: {len(self.all_pages)}')
        for i, investor in enumerate(self.all_pages):
            print(f'Парсинг {i+1}/{len(self.all_pages)}')
            self.parse_investor(investor)
        self.driver.quit()

    def init_webdriver(self):
        chromedriver_autoinstaller.install()
        opt = Options()
        caps = DesiredCapabilities.CHROME
        caps['pageLoadStrategy'] = "eager"
        opt.add_argument("--headless")
        self.driver = uc.Chrome(options=opt, desired_capabilities=caps)

    def parse_all_pages(self):
        r = requests.get(f'https://signal.nfx.com/investor-lists/top-{category}-investors', headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        self.all_pages = [i['href'].replace('/investors/', '') for i in soup.find_all('a') if '/investors/' in i['href']]
        while True:
            data_ = requests.post(url, headers=headers_gq, json=payload)
            if data_.status_code==200:
                json_data_= data_.json()
                try:
                    json_data = json_data_['data']['list']['scored_investors']
                    self.all_pages.extend([i['node']['person']['slug'] for i in json_data['edges']])
                    if not json_data['pageInfo']['hasNextPage']:
                        break
                    payload['variables']['after'] = json_data['pageInfo']['endCursor']
                except Exception as _:
                    print(f"{_}\n{json_data_=}")

            else:
                print(f"ERR {data_.status_code}\n{data_.text}")


    def parse_investor(self, investor):
        self.driver.get(f'https://signal.nfx.com/investors/{investor}')
        while 'Checking if the site connection is secure' in self.driver.page_source:
            time.sleep(1)
        name = self.get_name()
        if not name:
            print('Нет данных о ', investor)
            return
        if '<' in name:
            name = name[:name.find('<')]
        title = self.get_params(By.CSS_SELECTOR, 'h3.subheader.lower-subheader.pb2','innerHTML')
        linkedin = self.get_params(By.XPATH, '//a[contains(@href, "https://www.linkedin.com/")]', 'href')
        self.write_row([[name, title, linkedin]])

    @retry(iters=250)
    def get_name(self):
        name_ = self.driver.find_element(By.TAG_NAME, 'h1')
        return name_.get_attribute('innerHTML')

    @retry(iters=10)
    def get_params(self, type_, val, attrib):
        val_ = self.driver.find_element(type_, val)
        return val_.get_attribute(attrib)

    def write_row(self, mas):
        with open(f'{category}.csv', 'a', newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(mas)    


if __name__ == '__main__':
    p = Parser()