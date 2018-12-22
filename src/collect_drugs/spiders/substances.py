import string
import scrapy

class ScrpaySubstance(scrapy.Spider):
  name = 'scrapy-substances'

  # prepare urls
  upper_letters = list(string.ascii_uppercase)
  urls = [ 'https://www.medicines.org.uk/emc/browse-ingredients/'+ letter for letter in upper_letters]

  start_urls = urls

  def parse(self, response):
    page_urls = response.css("ul.browse li a::attr(href)").extract()[1:27]
    lis_left = response.css('div.col-md-6.ingredients.ieleft ul li')
    lis_right = response.css('div.col-md-6.ingredients.ieright ul li')
    lis = lis_left + lis_right
    for substance in lis:
      yield {
        'name': substance.css("a.key::text").extract_first(),
        'url_link': response.urljoin(substance.css("a.key::attr(href)").extract_first())
      }
    
    # i = 1
    # if i <= 25:
    #   next_page_url = page_urls[i]
    #   yield scrapy.Request(response.urljoin(next_page_url))
    #   i +=1