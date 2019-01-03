import json
import re


def extract_atc_code(content):
  """
  """

  atc_codes = []
  for item in content:
    atc_content = item['atc_text'].replace(" ", "")
    try:
      atc_code = re.search(r'([A-Z]{1}[0-9]{2}[A-Z]+[0-9]*)', atc_content).group(1)
    except AttributeError:
      atc_code = ''
      print(item['url_drug'])
    item['atc_code'] = atc_code

  with open("./../data/side-effects-atccodes.json", "w") as write_file:
    json.dump(content, write_file)

  return None

def atc_codes_extraction():
  ## data load
  data = json.load(open("./../data/side-effects-3.json", 'r'))

  # remove duplicates 
  uniDrugs = list({each['url_drug']: each for each in data}.values())
  print("The number of drugs is: ", len(uniDrugs))

  # extract atc codes
  extract_atc_code(uniDrugs)

  return None

def clean_content():
  """
  """

  # load the unique drugs (647)
  drugs = json.load(open("./../data/side-effects-atccodes.json", 'r'))

  for drug in drugs:
    adr_content = [ item.lower().strip() for item in drug['content'] ]
    content_cleaned= [ re.sub(r'(^[ \t\n]+|[ \t]+(?=:))', '', item, flags=re.M)  for item in adr_content ]
    drug['content_cleaned'] = [ item for item in content_cleaned if item ]

  return drugs

def extract_features(drugs):
  """
  Conducting some exploratory analysis to know the textual content of side effects
  """

  # # load the drugs
  # uniDrugs = json.load(open("./../data/side-atccodes.json", 'r'))

  # check how many drugs have the side effects structuredly presented in table
  tbled_drugs = [ item for item in drugs if '<table ' not in item['html_content']]
  print("The number of drugs with sides effects not in table(s): ", len(tbled_drugs))

  for drug in drugs:
    drug['count_table'] = sum(1 for _ in re.finditer('<table ', drug['html_content']))
    drug['very_common'] = [i for i, x in enumerate(drug['content_cleaned']) if "very common" in x]
    drug['common'] = [i for i, x in enumerate(drug['content_cleaned']) if "common" in x]
    drug['uncommon'] = [i for i, x in enumerate(drug['content_cleaned']) if "uncommon" in x]
    drug['rare'] = [i for i, x in enumerate(drug['content_cleaned']) if "rare" in x]
    drug['very_rare'] = [i for i, x in enumerate(drug['content_cleaned']) if "very rare" in x]
    drug['unknown'] = [i for i, x in enumerate(drug['content_cleaned']) if "known" in x]

  keys_included = ['url_drug', 'count_table', 'very_common', 'common', 'uncommon', 'rare', 'very_rare', 'unknown']
  drugs_sub = [ {k:v for k, v in item.items() if k in keys_included} for item in drugs ]

  with open("./../data/side-effects-features.json", "w") as write_file:
    json.dump(drugs_sub, write_file, indent=2)

  return drugs

def main():
  
  # # atc codes extraction
  # atc_codes_extraction()

  # clean content extracted from the 4.8 section
  drugs = clean_content()

  # feature engineering, obtain the structure features of the content in section 4.8
  drugs_extra_feats = extract_features(drugs)

if __name__ == "__main__":
  main()