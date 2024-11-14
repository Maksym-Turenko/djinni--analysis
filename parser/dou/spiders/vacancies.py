import scrapy
from scrapy.http import Response


class VacanciesSpider(scrapy.Spider):
    name = "vacancies"
    allowed_domains = ["jobs.dou.ua"]
    start_urls = ["https://jobs.dou.ua/vacancies/?category=Python"]

    def parse(self, response: Response, **kwargs):
        filename = "test.html"
        with open(filename, "wb") as f:
            f.write(response.body)
        self.log(f"Saved {filename}")
