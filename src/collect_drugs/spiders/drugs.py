import json
import scrapy

class ScrpayDrugs(scrapy.Spider):
  name = 'scrapy-drugs'

  # prepare urls
  substances = json.load(open('/Users/ianshen/Documents/github/ade-extraction/data/substances.json','r'))
  urls = [ item['url_link'] for item in substances]

  start_urls = urls[:10]

  def parse(self, response):
    results = response.css('div#browse-results div.row')
    for drug in results:
      drug_name = drug.css('div.col-sm-9 h2 a::text').extract_first()
      drug_url = response.urljoin(drug.css("div.col-sm-9 h2 a::attr(href)").extract_first())
      if 'tablets' in drug_name.lower() and 'smpc' in drug_url:
        yield {
          'substance': response.request.url,
          'name': drug_name,
          'url_drug': drug_url,
        }
        break