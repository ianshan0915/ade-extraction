import json
import scrapy

class ScrpaySideEffects(scrapy.Spider):
  name = 'scrapy-side-effects'

  # prepare urls
  drugs = json.load(open('/Users/ianshen/Documents/github/ade-extraction/data/drugs-2.json','r'))
  urls = [ item['url_drug'] for item in drugs]

  start_urls = urls

  def parse(self, response):
    side_effects_text = response.xpath("//div[contains(.//text(), 'effects')]/following-sibling::div").extract_first()
    if side_effects_text:
      yield {
        'url_drug': response.request.url,
        'html_content': side_effects_text,
        'content': response.xpath("//div[contains(.//text(), 'effects')]/following-sibling::div[1]//text()").extract()
      }    