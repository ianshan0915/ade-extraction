import json
import re

def extract_atc_code(content):
  """
  """

  atc_codes = []
  for item in content:
    atc_content = item['atc_text'].replace(" ", "")
    # atc_content = re.sub(r'[^\w\s]','', item['atc_text'].split(':')[-1].strip())
    try:
      atc_code = re.search(r'([A-Z]{1}[0-9]{2}[A-Z]+[0-9]*)', atc_content).group(1)
    except AttributeError:
      atc_code = ''
    item['atc_code'] = atc_code

  with open("../data/side-effects-atccodes.json", "w") as write_file:
    json.dump(content, write_file)

  return None

def main():
  ## data preprocessing
  data = json.load(open("/Users/ianshen/Documents/github/ade-extraction/data/side-effects-3.json", 'r'))
  extract_atc_code(data)

if __name__ == "__main__":
  main()