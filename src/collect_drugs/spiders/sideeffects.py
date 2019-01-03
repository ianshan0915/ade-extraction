import json
import re

import scrapy

class ScrpaySideEffects(scrapy.Spider):
  name = 'scrapy-side-effects'

  # prepare urls
  drugs = json.load(open('/Users/ianshen/Documents/github/ade-extraction/data/drugs-2.json','r'))
  urls = [ item['url_drug'] for item in drugs]

  start_urls = urls

  def parse(self, response):
    side_effects_text = response.xpath("//div[contains(.//text(), 'effects')]/following-sibling::div").extract_first()
    atc_arr = response.xpath("//div[contains(.//text(), '5.1 Pharmacodynamic')]/following-sibling::div[1]//text()").extract()
    revision_date = response.xpath("//h3[contains(.//text(), 'Last updated ')]/span//text()").extract_first()

    # 
    atc_text = ''
    for item in atc_arr:
      if re.search(r'([A-Z]{1}[0-9]{2}[A-Z]+[0-9]*)', item.replace(" ", "")):
        atc_text = item
        break

    if side_effects_text:
      yield {
        'url_drug': response.request.url,
        'html_content': side_effects_text,
        'content': response.xpath("//div[contains(.//text(), 'effects')]/following-sibling::div[1]//text()").extract(),
        'atc_text': atc_text,
        'updated_date': revision_date
      }    