import json
import logging
import time
from typing import Iterable
import csv
from pathlib import Path

import scrapy
from scrapy.http import Response, TextResponse
from scrapy import Request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup

from ..items import VacancyItem  # from parser.dou.items import VacancyItem


VACANCY_CSS = "li.l-vacancy"
VACANCY_URL = "a.vt::attr(href)"
VACANCY_TITLE = "h1.g-h2::text"
VACANCY_DESCRIPTION = "div.b-typo.vacancy-section"


class VacanciesSpider(scrapy.Spider):
    name = "vacancies"
    allowed_domains = ["jobs.dou.ua"]
    start_urls = ["https://jobs.dou.ua/vacancies/?category=Python"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.technologies = self.load_technologies("technologies.json")
        self.driver = webdriver.Chrome()
        self.csv_file_path = "vacancies.csv"
        self.init_csv(self.csv_file_path)

    def start_requests(self) -> Iterable[Request]:

        self.driver.get(self.start_urls[0])
        while True:
            try:
                more_button = WebDriverWait(self.driver, 10).until(
                    ec.visibility_of_element_located((By.CLASS_NAME, "more-btn"))
                )
                if more_button.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView();", more_button)

                    link = more_button.find_element(By.TAG_NAME, "a")
                    link.click()

                    time.sleep(1)
                else:
                    break

            except Exception as e:
                logging.info(f"An error occurred: {e}")
                break

        html = self.driver.page_source
        response = TextResponse(
            url=self.start_urls[0],
            body=html,
            encoding="utf-8"
        )
        yield from self.parse(response)

    def close(self, reason: str):
        self.driver.quit()

    def parse(self, response: Response, **kwargs) -> Response:
        for vacancy in response.css(VACANCY_CSS):
            url = vacancy.css(VACANCY_URL).get()
            if url:
                yield response.follow(
                    url, callback=self.parse_vacancy
                )

    def parse_vacancy(self, response: Response) -> VacancyItem:
        item = VacancyItem()

        item["title"] = response.css(VACANCY_TITLE).get()

        description = response.css(VACANCY_DESCRIPTION).getall()
        cleaned_description = [
            BeautifulSoup(text, "html.parser").get_text(strip=True)
            for text in description
        ]
        string_description = " ".join(cleaned_description).replace("\xa0", " ")
        item["description"] = string_description

        item["technologies"] = [
            technology
            for technology in self.technologies
            if technology in string_description.lower()
        ]

        self.write_to_csv(self.csv_file_path, item)

        yield item

    @staticmethod
    def load_technologies(file_path: str) -> list[str]:
        path = Path(file_path)
        return json.loads(path.read_text())

    @staticmethod
    def init_csv(file_path: str):
        fieldnames = ["title", "description", "technologies"]
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

    @staticmethod
    def write_to_csv(file_path: str, item: VacancyItem):
        fieldnames = ["title", "description", "technologies"]
        with open(file_path, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writerow(item)
