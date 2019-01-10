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

  return drugs

def check_tbl(num_tbl, content_tbl):
  """
  check if the content of a table have common, rare, or unknown
  if not, the table will not be kept for the following step
  """

  count_common = len([i for i, x in enumerate(content_tbl) if 'common' in x ])
  count_rare = len([i for i, x in enumerate(content_tbl) if 'rare' in x ])
  count_unknown = len([i for i, x in enumerate(content_tbl) if "known" in x])
  count_disorders = len([i for i, x in enumerate(content_tbl) if "disorders" in x])
  count_digits = len([i for i, x in enumerate(content_tbl) if re.findall(r'^[0-9]+$', x.strip())])
  if num_tbl >8:
    return True
  elif all(i <=1 for i in [count_common, count_rare, count_unknown]) or count_disorders==0 or count_digits>3:
    return False
  else:
    return True

def get_tbl_type(num_tbl, num_cols, len_tr, content_tbl):
  """
  obtain table type based on table features
  """

  count_very_common = len([i for i, x in enumerate(content_tbl) if re.match(r'^very common',x) ])
  count_common = len([i for i, x in enumerate(content_tbl) if re.match(r'^common',x) ])
  count_uncommon = len([i for i, x in enumerate(content_tbl) if re.match(r'^uncommon',x) ])
  count_rare = len([i for i, x in enumerate(content_tbl) if re.match(r'^rare',x) ])
  count_very_rare = len([i for i, x in enumerate(content_tbl) if re.match(r'^very rare',x) ])
  count_unknown = len([i for i, x in enumerate(content_tbl) if "known" in x])
  count_feats = [count_very_common,count_common,count_uncommon,count_rare,count_very_rare,count_unknown]

  if num_cols>3 and sum(count_feats) > num_cols+5:
    tbl_type = 'table type: vertical'
  elif ((all(i <2 for i in count_feats) and num_tbl<=5) or num_cols>4) and len_tr>2:
    tbl_type = 'table type: horizontal'
  else:
    tbl_type = 'table type: vertical'

  return tbl_type

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
    xpath_tr_2nd = "//div//div[" + str(i) + "]//tr[2]//td"
    xpath_tr_3rd = "//div//div[" + str(i) + "]//tr[3]//td"
    xpath_td = "//div//div[" + str(i) + "]//td"
    content_tbl = html_content.xpath(xpath_string)
    content_tbl = [ item.lower().strip() if re.search('[a-zA-Z]{3,}', item) else item.lower() for item in content_tbl ]

    if check_tbl(num_tbl, content_tbl):
      len_tr = len(html_content.xpath(xpath_tr))
      len_tr_1st = len(html_content.xpath(xpath_tr_1st))
      len_tr_2nd = len(html_content.xpath(xpath_tr_2nd))
      len_td = len(html_content.xpath(xpath_td))

      if len_tr >=3:
        len_tr_3rd = len(html_content.xpath(xpath_tr_3rd))
      else:
        len_tr_3rd = 0

      if len_tr<=2:
        num_cols = round(len_td/len_tr)
      else:
        num_cols = round((len_td - len_tr_1st - len_tr_2nd)/(len_tr-2))

      # table structure: number of columns in the first row, number of rows, number of columns
      tbl_structure = 'table structure,' + str(len_tr_1st) + ',' + str(len_tr_2nd) + \
                      ',' + str(len_tr_3rd) + ','+ str(len_tr) + ',' + str(num_cols)
      if get_tbl_type(num_tbl, num_cols, len_tr, content_tbl)=='table type: vertical':
        content_tbl = [ re.sub(r'[\n\t]+', '', item, flags=re.M)  for item in content_tbl ]
      else:
        content_tbl = [td.text_content() for td in html_content.xpath(xpath_td)]
      content_tbl = [tbl_structure, get_tbl_type(num_tbl, num_cols, len_tr, content_tbl)] + content_tbl

      contents +=content_tbl


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

      # if all the tables donot have meaningful info
      if len(content)==0:
        # print('exception drug url: ', drug['url_drug'])
        content = html_content.xpath("//div//text()")
        content = [ re.sub(r'[\n\t]+', '', item, flags=re.M)  for item in content ]
    else:
      content = html_content.xpath("//div//text()")
      content = [ re.sub(r'[\n\t]+', '', item, flags=re.M)  for item in content ]

    # convert to lowercase, and strip spaces
    adr_content = [ item.lower().strip() if re.search('[a-zA-Z]{3,}', item) else item.lower() for item in content ]

    # remove strings that are spaces, tabs or newlines
    # content_cleaned= [ re.sub(r'(^[ \t\n]+|[ \t]+(?=:))', '', item, flags=re.M)  for item in adr_content ]
    content_cleaned = adr_content

    # remove empty strings and string that 
    drug['content_cleaned'] = [ item for item in content_cleaned if item and (re.search('[a-z]{3,}', item) or re.search(r'[\n\t]+', item)) ]

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

  keys_included = ['url_drug', 'content_cleaned', 'atc_code', 'updated_date', 'html_content']
  drugs_sub = [ {k:v for k, v in item.items() if k in keys_included} for item in drugs ]
  
  with open("./../data/side-effects-content-new.json", "w") as write_file:
    json.dump(drugs_sub, write_file, indent=2)

  return drugs_sub

def extract_features(feats_drugs):
  """
  Conducting some exploratory analysis to know the textual content of side effects
  """

  # # load the drugs
  # uniDrugs = json.load(open("./../data/side-atccodes.json", 'r'))

  for feats_drug in feats_drugs:
    feats_drug['count_table'] = len([i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^table structure',x) ])
    feats_drug['very_common'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^very common',x) ]
    feats_drug['common'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^common',x) ]
    feats_drug['uncommon'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^uncommon',x) ]
    feats_drug['rare'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^rare',x) ]
    feats_drug['very_rare'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if re.match(r'^very rare',x) ]
    feats_drug['unknown'] = [i for i, x in enumerate(feats_drug['content_cleaned']) if "known" in x]
    feats_drug['count_veryCommon'] = len(feats_drug['very_common'])
    feats_drug['count_common'] = len(feats_drug['common'])
    feats_drug['count_unommon'] = len(feats_drug['uncommon'])
    feats_drug['count_rare'] = len(feats_drug['rare'])
    feats_drug['count_veryRare'] = len(feats_drug['very_rare'])
    feats_drug['count_unknown'] = len(feats_drug['unknown'])

  # keys_included = ['url_drug', 'count_table', 'very_common', 'common', 'uncommon', 'rare', 'very_rare', 'unknown']
  keys_included = ['url_drug', 'count_table', 'count_veryCommon', 'count_common', 'count_unommon', 'count_rare', \
                   'count_veryRare', 'count_unknown']
  # keys_included = ['url_drug', 'content','content_cleaned','html_content']
  feats_drugs_sub = [ {k:v for k, v in item.items() if k in keys_included} for item in feats_drugs ]

  with open("./../data/side-effects-features.json", "w") as write_file:
    json.dump(feats_drugs_sub, write_file, indent=2)

  return feats_drugs_sub

def drugs_group():
  """
  """

  # load the extracted features
  feats = json.load(open("./../data/side-effects-features.json", 'r'))

  for drug in feats:
    if drug['count_table']==0:
      drug_vals = list(drug.values())[2:len(drug.values())]
      feats_vals = [ val for val in drug_vals[1:len(drug_vals)-1]]
      if any(i>1 for i in feats_vals) or sum(drug_vals)>=5:
        drug['struct_type'] = 'structured'
      else:
        drug['struct_type'] = 'free-text'
    else:
      drug['struct_type'] = 'tablular'

  feats_sub = [ {k:v for k, v in item.items() if k in ['url_drug', 'struct_type']} for item in feats ]

  return feats_sub

def explore_structural_html_content(drugs):
  """
  explore the structural characteristics of html content
  """

  # check how many drugs have the side effects structuredly presented in table
  tbled_drugs = [ item for item in drugs if '<table ' not in item['html_content']]
  print("The number of drugs with sides effects not in table(s): ", len(tbled_drugs))

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

def explore_structural_extracted_content():
  """
  explore the structural characteristics of the extracted content
  """

  # load the features
  feats = json.load(open("./../data/side-effects-features.json", 'r'))

  for drug in feats:
    if drug['count_table']==0:
      drug_vals = list(drug.values())[2:len(drug.values())]
      feats_vals = [ val for val in drug_vals[1:len(drug_vals)-1]]
      if any(i>1 for i in feats_vals) or sum(drug_vals)>=5:
        drug['struct_type'] = 'structured'
      else:
        print(drug)   
        drug['struct_type'] = 'free-text'
    else:
      drug['struct_type'] = 'tablular'
  
  feats_sub = [ {k:v for k, v in item.items() if k in ['url_drug', 'struct_type']} for item in feats ]

  return feats_sub

def merge_json_list(drugs, groups_drug):
  """
  """

  merged = [{**drug, **group} for drug, group in zip(drugs, groups_drug)]
  for item in merged:
    if item['struct_type'] =='tablular':
      html_item = html.fromstring(item['html_content'])
      item['content_freetext'] = html_item.xpath('//div/p/text()')

  merged = [ {k:v for k, v in item.items() if k not in ['html_content']} for item in merged ]
  with open("./../data/side-effects-content-merged.json", "w") as write_file:
    json.dump(merged, write_file, indent=2)

  return None

def main():
  
  # # atc codes extraction
  # atc_codes_extraction()

  # clean content extracted from the 4.8 section
  drugs = clean_html_content()
  drugs = extract_clean_content(drugs)

  # explore_structural_html_content(drugs)
  # explore_structural_extracted_content()

  # feature engineering, obtain the structure features of the content in section 4.8
  # drugs_extra_feats = extract_features(drugs)
  groups = drugs_group()
  merge_json_list(drugs, groups)

if __name__ == "__main__":
  main()