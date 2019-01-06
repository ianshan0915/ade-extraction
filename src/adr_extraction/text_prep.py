import json
import re
from lxml import html


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
def clean_html_content():
  """
  """

  # load the unique drugs (647)
  drugs = json.load(open("./../data/side-effects-atccodes.json", 'r'))

  for drug in drugs:
    drug['html_content'] = re.sub('<b>', '', drug['html_content'])
    drug['html_content'] = re.sub('</b>', '', drug['html_content'])
    drug['html_content'] = re.sub('<i>', '', drug['html_content'])
    drug['html_content'] = re.sub('</i>', '', drug['html_content'])
    drug['html_content'] = re.sub('<u>', '', drug['html_content'])
    drug['html_content'] = re.sub('</u>', '', drug['html_content'])
    drug['html_content'] = re.sub(r'<sup>.+?</sup>', '', drug['html_content'])
    drug['html_content'] = re.sub(r'<sub>.+?</sub>', '', drug['html_content'])
    if re.search(r'<sub>[a-z0-9]+</sub>', drug['html_content']):
      print(drug['url_drug'])

  return drugs

def check_tbl(content_tbl):
  """
  check if the content of a table have common, rare, or unknown
  if not, the table will not be kept for the following step
  """

  count_common = [i for i, x in enumerate(content_tbl) if 'common' in x ]
  count_rare = [i for i, x in enumerate(content_tbl) if 'rare' in x ]
  count_unknown = [i for i, x in enumerate(content_tbl) if "known" in x]

  if len(count_common)==0 and len(count_rare)<=2:
    return False
  else:
    return True

def extract_tbls(num_tbl, html_content):
  """
  extract texts in the table and then check whether to keep the extraction or not for each table
  """
  
  contents = []
  # get content of each table
  for i in range(1, num_tbl+1):
    xpath_string = "//div//div[" + str(i) + "]//text()"
    xpath_tr = "//div//div[" + str(i) + "]//tr"
    xpath_tr_1st = "//div//div[" + str(i) + "]//tr[1]//td"
    xpath_td = "//div//div[" + str(i) + "]//td"
    content_tbl = html_content.xpath(xpath_string)

    if check_tbl(content_tbl):
      contents +=content_tbl
      len_tr = len(html_content.xpath(xpath_tr))
      len_tr_1st = len(html_content.xpath(xpath_tr_1st))
      len_td = len(html_content.xpath(xpath_td))

      if len_tr<=1:
        num_cols = round(len_td/len_tr)
      else:
        num_cols = round((len_td - len_tr_1st)/(len_tr-1))

      # table structure: number of columns in the first row, number of rows, number of columns
      tbl_structure = 'table structure,' + str(len_tr_1st) + ',' + str(len_tr) + ',' + str(num_cols)
      contents.append(tbl_structure)

  return contents

def extract_clean_content(drugs):
  """
  extract and clean the content of adr
  """

  # # load the unique drugs (647)
  # drugs = json.load(open("./../data/side-effects-atccodes.json", 'r'))

  for drug in drugs:
    html_content = html.fromstring(drug['html_content'])
    if '<table ' in drug['html_content']:
      count_tbls = sum(1 for _ in re.finditer('<table ', drug['html_content']))
      content = extract_tbls(count_tbls, html_content)

      # if all the tables donot have 
      if len(content)==0:
        print('exception drug url: ', drug['url_drug'])
        content = html_content.xpath("//div//text()")
    else:
      content = html_content.xpath("//div//text()")

    # convert to lowercase, and strip spaces
    adr_content = [ item.lower().strip() if re.search('[a-zA-Z]{3,}', item) else item.lower() for item in content ]

    # remove strings that are spaces, tabs or newlines
    # content_cleaned= [ re.sub(r'(^[ \t\n]+|[ \t]+(?=:))', '', item, flags=re.M)  for item in adr_content ]
    content_cleaned = adr_content

    # remove empty strings and string that 
    drug['content_cleaned'] = [ item for item in content_cleaned if item and (re.search('[a-z]{4,}', item) or re.search(r'[\n\t]+', item)) ]

    tabulated_index = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^tabulated', x)]
    if len(tabulated_index)>0:
      start_ind = tabulated_index[0]
    else:
      start_ind = 0
    
    # remove the content about "reporting of suspected adverse reactions"
    reporting_suspected_index = [i for i, x in enumerate(drug['content_cleaned']) if re.match('reporting of suspected',x)]
    selected_adr_index = [i for i, x in enumerate(drug['content_cleaned']) if 'selected adverse' in x]

    if len(selected_adr_index) >0:
      drug['content_cleaned'] = drug['content_cleaned'][start_ind:selected_adr_index[0]]
    elif len(reporting_suspected_index) >0:
      drug['content_cleaned'] = drug['content_cleaned'][start_ind:reporting_suspected_index[0]]

  keys_included = ['url_drug', 'content_cleaned']
  drugs_sub = [ {k:v for k, v in item.items() if k in keys_included} for item in drugs ]
  with open("./../data/side-effects-content-new.json", "w") as write_file:
    json.dump(drugs_sub, write_file, indent=2)

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
    drug['very_common'] = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^very common',x) ]
    drug['common'] = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^common',x) ]
    drug['uncommon'] = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^uncommon',x) ]
    drug['rare'] = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^rare',x) ]
    drug['very_rare'] = [i for i, x in enumerate(drug['content_cleaned']) if re.match(r'^very rare',x) ]
    drug['unknown'] = [i for i, x in enumerate(drug['content_cleaned']) if "known" in x]
    drug['count_veryCommon'] = len(drug['very_common'])
    drug['count_common'] = len(drug['common'])
    drug['count_unommon'] = len(drug['uncommon'])
    drug['count_rare'] = len(drug['rare'])
    drug['count_veryRare'] = len(drug['very_rare'])
    drug['count_unknown'] = len(drug['unknown'])

  # keys_included = ['url_drug', 'count_table', 'very_common', 'common', 'uncommon', 'rare', 'very_rare', 'unknown']
  keys_included = ['url_drug', 'count_table', 'count_veryCommon', 'count_common', 'count_unommon', 'count_rare', \
                   'count_veryRare', 'count_unknown']
  # keys_included = ['url_drug', 'content','content_cleaned','html_content']
  drugs_sub = [ {k:v for k, v in item.items() if k in keys_included} for item in drugs ]

  with open("./../data/side-effects-features.json", "w") as write_file:
    json.dump(drugs_sub, write_file, indent=2)

  return drugs

def drugs_group():
  """
  """

  # load the extracted features
  feats = json.load(open("./../data/side-effects-features.json", 'r'))

  drugs_multi_tbls = [ item for item in feats if item['count_table']>=2]
  print("drugs with more than 2 tables: ", len(drugs_multi_tbls))

  drugs_no_tbls = [ item for item in feats if item['count_table']>=2 ]

  return None

def explore_structural_char(drugs):
  """
  """
  
  for drug in drugs:
    print(drug['url_drug'])
    count_tbls = sum(1 for _ in re.finditer('<table ', drug['html_content']))
    html_content = html.fromstring(drug['html_content'])
    if count_tbls>0:
      print("# of tds: ", len(html_content.xpath("//div//div[1]//td//text()")))
      print("# of texts: ", len(html_content.xpath("//div//div[1]//text()")))
    else:
      print("# of ps: ", len(html_content.xpath("//div//p//text()")))
      print("# of texts: ", len(html_content.xpath("//div//text()")))
    print('\n')

  return None

def main():
  
  # # atc codes extraction
  # atc_codes_extraction()

  # clean content extracted from the 4.8 section
  drugs = clean_html_content()
  drugs = extract_clean_content(drugs)
  # explore_structural_char(drugs)

  # feature engineering, obtain the structure features of the content in section 4.8
  # drugs_extra_feats = extract_features(drugs)

if __name__ == "__main__":
  main()