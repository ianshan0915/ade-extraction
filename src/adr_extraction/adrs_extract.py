# -*- coding=utf-8 -*-

"""
Created on Wed Jan. 8, 2019

@author: ianshan0915

extract adverse drug reactions from the preprocessed (clean) data scraped from www.medicines.org.uk
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
from time import time
import re
from collections import Counter

from helpers import flatten, split_by_diff, check_soc_term, text_razor

import numpy as np

def load_data():
  """
  load the textual data
  """

  drugs = json.load(open("./../data/side-effects-content-merged.json", 'r'))

  # load soc terms
  soc_terms = json.load(open("./../data/soc-terms.json", 'r'))

  # split tabular content into subsets with each representing a table
  for drug in drugs:
    tbl_marks = [i for i, x in enumerate(drug['content_cleaned']) if re.match('table structure,',x) ]

    # in case there are more than one tables, we split the content list 
    # into multiple subset with each contains data from a table    
    if drug['struct_type'] == 'tablular' and len(tbl_marks)>0:
      start_inds = [i for i in tbl_marks]
      end_list = tbl_marks + [len(drug['content_cleaned'])]
      end_inds = [i for i in end_list[1:]]
      pairs_inds = [pair for pair in zip(start_inds, end_inds)]
      tbls_content = []
      for pair in pairs_inds:
        content_tbl = drug['content_cleaned'][pair[0]:pair[1]]
        # remove content with only text in (), e.g. "(> 5x \u2013 20 x uln)"
        # content_tbl = [ item for item in content_tbl if re.sub(r'^\(.+\)$','',item).strip()]        
        tbls_content.append(content_tbl)

      drug['content_cleaned'] = tbls_content
    elif drug['struct_type'] in ['structured-a', 'structured-b']:
      # remove special characters in the beginning e.g. - or \u2022
      drug['content_cleaned'] = [re.sub(r'^\u2022|^-','',item).strip() for item in drug['content_cleaned'] ]
      # remove content with only text in (), e.g. "(> 5x \u2013 20 x uln)"
      drug['content_cleaned'] = [ item for item in drug['content_cleaned'] if re.sub(r'^\(.+\)$','',item).strip()]
      freqs = [r'^very +common', r'.+: very common', r'^common', r'.+: common', r'^uncommon', r'.+: uncommon', r'^rare', \
               r'.+: rare', r'^very +rare', r'.+: very rare']
      nested_content = [item.split(':') if (any(re.match(freq,item) for freq in freqs ) or 'known' in item) else [item] \
                        for item in drug['content_cleaned']]
      drug_content = flatten(nested_content)
      drug['content_cleaned'] = [item.strip() for item in drug_content if item.strip()]
    else:
      pass


  return drugs, soc_terms['terms']

def extract_adrs(drugs, soc_terms):
  """
  Extract adrs from semi-/unstructured textual data, textual data divided into three main types: 
    - tabular, 
    - structured,
    - and free-text
  
  Parameters
    drugs: textual content of side effects of all drugs, 
    soc_terms: a list of soc terms 

  @return
    None
  """

  for drug in drugs:
    print(drug['url_drug'])
    drug_adrs = []
    if drug['struct_type'] == 'tablular':
      num_tbl = len(drug['content_cleaned'])
      for tbl in drug['content_cleaned']:
        adrs_tbl = {}
        if tbl[1] == "table type: horizontal":
          freq_inds, most_common_diff = get_frequences_ind(tbl)
          num_cols, num_diff, count_disorders= get_tbl_struct_info(tbl)
          tbl_label = get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders)
          if tbl_label in [0,1]:
            adrs_tbl = extract_adrs_tbl(tbl, freq_inds, tbl_label, num_cols, soc_terms)
            print('horizontal-tbl done')
          # elif tbl_label in [2,3]: # 7236  (410, 1922 manual update the content)
          #   # print(drug['url_drug'])
          #   # adrs = extract_adrs_tbl(tbl, freq_inds, tbl_label, num_cols, soc_terms)
          #   # adrs = {k:v for (k,v) in adrs.items() if k !='system of class'}
          #   # print(adrs)
          #   # handle exceptions
          #   pass
          else: # 7236  (410, 1922 manual update the content), and table_label == -1
            freq_inds = [i for i in freq_inds if i < len(tbl)/2]
            if len(freq_inds) ==0:
              adrs_tbl = extract_freetext(tbl)
            else:
              adrs_tbl = extract_adrs_tbl(tbl, freq_inds, tbl_label, num_cols, soc_terms)
          adrs_tbl = {k:v for (k,v) in adrs_tbl.items() if k !='system of class'}
          print('horizontal-tbl exception done')
        else:
          adrs_tbl = extract_vertical(tbl, soc_terms)
          print('vertical-tbl done')
        if adrs_tbl:
          drug_adrs.append(adrs_tbl)
      # aggreate dict list by keys if there are multiple tables
      drug_adrs = {key: flatten([d.get(key) for d in drug_adrs if d.get(key)]) for key in set().union(*drug_adrs)}
    elif drug['struct_type'] == 'structured-a': # done
      drug_adrs = extract_structured(drug['content_cleaned'], soc_terms)
      print('structured-a done')
    elif drug['struct_type'] == 'structured-b': # done
      nested_content = [item.split(':') for item in drug['content_cleaned']]
      drug_content = [item.strip() for item in flatten(nested_content) if item.strip()]
      freq_inds, soc_inds = get_structured_inds(drug_content, soc_terms)
      adrs_content = [drug_content[i] for i in range(len(drug_content)) if i not in soc_inds]
      # print(adrs_content)
      drug_adrs = extract_freetext(adrs_content)
      print('structured-b done')
    else: # not structured text
      drug_adrs = extract_freetext(drug['content_cleaned'])
      print('free-text done')   
    
    drug['adrs'] = drug_adrs
  #   print(drug_adrs)
  keys_included = ['url_drug', 'adrs', 'atc_code', 'updated_date']
  drugs_adrs = [ {k:v for k, v in item.items() if k in keys_included} for item in drugs ]
  
  with open("/Users/ianshen/Documents/drug-adrs.json", "w") as write_file:
    json.dump(drugs_adrs, write_file, indent=2)

  return None

def get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders):
  """
  - get the type of a horizontal table, the type will decide the following extraction process
  count_disorders is not very useful currently, because we know that all tables we collected contain 'disorder', 
  but it is added for better scalability. 

  Output: True or False, True means we can go ahead to extract adrs, 
  False means that some necessary exception handling steps are needed
  """

  # if soc_label equals to 0, there is no separate column for system of classself.
  # therefore, the 
  soc_label = num_cols - len(freq_inds)

  if most_common_diff !=1:
    # mislabelled table type, the table should be vertical
    tbl_label = -1
  elif soc_label >1:
    # a type of exception that is similar to 7236, the extraction can still be easily done, 
    # but a careful check of the freqeuncy list is needed
    tbl_label = 2
  elif soc_label ==0 and count_disorders>0:
    # 'system of class' is not put inot a separate column 
    tbl_label = 0
  elif num_diff==2:
    # standard horizaontal table, very easy to extract 
    tbl_label = 1
  elif num_diff <0 and num_diff>-5:
    # one more step of check table structure, then just like standard table extraction
    tbl_label = 1
  else:
    # first we need to use soc names as marks, and for rows that exceed the number of columns
    # we simply remove some cells, 410, 1922
    tbl_label = 3

  return tbl_label

def get_frequences_ind(content_tbl):
  """
  get the ordered frequencies list from the content list

  return
    - inds
    - most common diff
  """

  freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
  inds = []
  for freq in freqs:
    freq_inds = [i for i, x in enumerate(content_tbl) if re.match(freq,x) ]
    if len(freq_inds) >0:
      inds +=freq_inds

  unknown = [i for i, x in enumerate(content_tbl) if "known" in x]
  inds += unknown

  most_common_diff = 0
  # clean the frequency indexes list: remove the non frequency term, 
  if len(inds)>1:
    sorted_inds = np.sort(inds)
    inds_diff = np.diff(sorted_inds)
    abnormal_inds = [i+1 for i, x in enumerate(inds_diff) if x>1 ]
    abnormal_val = [sorted_inds[i] for i in abnormal_inds]
    most_common_diff = Counter(inds_diff).most_common(1)[0][0]
    if most_common_diff ==1 and len(abnormal_val)>0:
      inds = list(set(inds) - set(abnormal_val))

  return np.unique(inds), most_common_diff

def get_tbl_struct_info(content_tbl):
  """
  get the structural information of a table, including:
    - the number of columns
    - the difference between the number of actual cells and the estimated cells
  """

  tbl_struct = content_tbl[0].split(',')
  tbl_struct = [int(val) for val in tbl_struct[1:]]
  tbl_struct_cols = tbl_struct[0:3]+ [tbl_struct[4]]
  num_cols = max(tbl_struct_cols)

  num_estimated_tds = sum(tbl_struct[0:3]) + (tbl_struct[3]-3)*tbl_struct[4]
  num_diff = len(content_tbl) - num_estimated_tds

  count_disorders = len([i for i, x in enumerate(content_tbl) if "disorders" in x])

  return num_cols, num_diff, count_disorders

def normalize_freq_terms(col_nms):
  """
  since frequence terms are in various format, such as with or without percentage info, e.g. very  common   (≥1/10),
  we use this function to normalize these terms
  """

  freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
  freq_terms = ['very common', 'common', 'uncommon', 'rare', 'very rare']
  normalized_terms = []

  for term in col_nms:
    freq_inds = [freq_term for freq_term, x in zip(freq_terms, freqs) if re.match(x,term) ]
    normalized_terms +=freq_inds

    if "known" in term:
      normalized_terms += ['unknown']

  normalized_terms = ['system of class'] +normalized_terms

  return normalized_terms

def clean_cell_text(adr_text):
  """
  clean up the text obtain from cells of a table
  """
  # adr_text= re.sub(r'[\n\t]+', ' ! ', adr_text)

  # split adr_text when there is comma in ()
  if ',' in adr_text:
    r = re.compile(r'(?:[^,(]|\([^)]*\))+')
    adrs = r.findall(adr_text)

    if len(adrs)==1:
      r = re.compile(r'\n')
      adrs = r.split(adr_text)
  else:
    r = re.compile(r'\n')
    adrs = r.split(adr_text)

  # sometimes there are both comma and \n 
  r_extra = re.compile('\*|\n')
  adrs = flatten([r_extra.split(adr.strip()) for adr in adrs])

  adrs = [re.sub(r'\(see.+\)|\(when.+\)', '',adr).strip() for adr in adrs ] # remove (see xxx) 
  # adrs that not empty and contains more than 3 letters are included
  adrs =  [ adr for adr in adrs if re.search('[a-z]{3,}', adr) and adr] 

  return adrs

def extract_adrs_tbl(tbl_content, freq_inds, tbl_label, num_cols, soc_terms):
  """
  extract adrs from a given content table
  """

  # set the row length and column names
  if tbl_label==0:
    seq_len = num_cols +1
    col_nms = ['system of class'] + [tbl_content[i] for i in freq_inds]
  else:
    seq_len = num_cols
    if freq_inds[0] ==3:
      col_nms = [tbl_content[2]] + [tbl_content[i] for i in freq_inds]
    else:
      col_nms=['system of class'] + [tbl_content[i] for i in freq_inds]
  col_nms = normalize_freq_terms(col_nms)

  # get adrs content and split it into N sublist of seq_len size, each sublist represents
  # a row in the table
  adrs_arr = tbl_content[freq_inds[-1]+1:]

  # if the adrs array could be split into N rows of equal size, then we guess the adrs starts from the second
  # also we need to make sure that the second element is not SOC term. 
  if len(adrs_arr) % seq_len !=0 and not check_soc_term(adrs_arr[0], soc_terms):
    adrs_arr = tbl_content[freq_inds[-1]+2:]
  
  # fetch adrs content from table using relative positions
  tbl_adr = {}
  num_rows = len(adrs_arr)//seq_len
  for i, col_nm in enumerate(col_nms):
    relative_pos = [i + nrow*seq_len for nrow in range(num_rows)]
    adrs = [adrs_arr[i] for i in relative_pos if i <len(adrs_arr)]
    nested_adrs = [clean_cell_text(adr) for adr in adrs]
    tbl_adr[col_nm] = [item for sublist in nested_adrs for item in sublist] # flatten out the nested list

  return tbl_adr

def extract_horizontal(tbl_content, soc_terms):
  """
  - extract adrs from the horizontal table,
  A horizontal table is table structure classified in the data processing step
  """

  freq_inds, most_common_diff = get_frequences_ind(tbl_content)
  num_cols, num_diff, count_disorders = get_tbl_cols(tbl_content)

  # get the type of table
  tbl_label = get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders)
  
  if tbl_label in [0,1,2]:
    adrs = extract_adrs_tbl(tbl_content, freq_inds, tbl_label, num_cols, soc_terms)
  else:
    pass # some exception handling scripts

  return adrs

def drugs_horizontal(drugs, soc_terms):
  """
  extract adrs from drugs, this function does the extraction from horizontal tables 
  """

  for drug in drugs:
    if drug['struct_type'] == 'tablular':
      drug_adrs = []
      num_tbl = len(drug['content_cleaned'])
      # for each table, extract the adrs, before extraction, we first check whether the table structure is normal    
      for tbl in drug['content_cleaned']:
        # only horizontal tables
        if tbl[1] == "table type: horizontal":
          adrs = extract_horizontal(tbl, soc_terms)
          drug_adrs += adrs
        else:
          adrs = extract_vertical(tbl, soc_terms)
          drug_adrs += adrs
    elif drug['struct_type'] == 'structured':
      freq_inds, soc_inds = get_vertical_inds(drug['content_cleaned'])
    else:
      pass
    drug['adrs'] = drug_adrs

  return drugs

def get_vertical_inds(content_tbl, soc_terms):
  """
  obtain indexes of the frequency terms, and SOC terms
  """

  freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
  inds = []
  for freq in freqs:
    freq_inds = [i for i, x in enumerate(content_tbl) if re.match(freq,x) ]
    if len(freq_inds) >0:
      inds +=freq_inds

  content_tbl = [re.sub(r'\(cannot be estimated.+\)', '',item).strip() for item in content_tbl ]
  unknown = [i for i, x in enumerate(content_tbl) if "known" in x and len(x.split())<4]
  inds += unknown

  soc_inds = [i for i, x in enumerate(content_tbl) if check_soc_term(x, soc_terms) ]

  # get minimum column number
  tbl_struct = content_tbl[0].split(',')
  tbl_struct = [int(val) for val in tbl_struct[1:]]
  tbl_struct_cols = tbl_struct[0:3]+ [tbl_struct[4]]
  len_tr = tbl_struct[3]
  num_cols = max(tbl_struct_cols)

  return np.sort(inds), np.sort(soc_inds), len_tr, num_cols

def get_vertical_struct_info(freq_inds):
  """
  get structural information about a vertical table so we can label it
  different types of vertical tables will be processed with different extraction methods
  """

  freq_inds_diffs = Counter(np.diff(freq_inds))

  if 1 in freq_inds_diffs.keys():
    count_1_perc = round(freq_inds_diffs[1]/len(freq_inds),2)
  else:
    count_1_perc = 0

  return count_1_perc * 100

def explore_vertical_content(tbl_content):
  """
  a bit exploratory analysis on content to find a good way of further cleaning it
  """

  freq_terms = ['common', 'rare', 'known']
  for item in tbl_content:
    if re.search(r':.+|\n', item) and any( term in item for term in freq_terms):
      print(item)

  return None

def standardize_freq_term(term):
  """
  standardize the frequency term
  """

  freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
  freq_terms = ['very common', 'common', 'uncommon', 'rare', 'very rare']
  term_match = [freq_term for freq_term, x in zip(freq_terms, freqs) if re.match(x,term) ]
  if len(term_match)>0:
    standard_term = term_match[0]
  else:
    standard_term = 'unknown'

  return standard_term

def extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, tbl_content):
  """
  extract adrs given the indexes of frequency terms and soc terms
  """

  adrs_tbl = []

  if gap_soc_freq ==0:
    pass # 816,5534 no frequency terms
  elif gap_soc_freq ==1:
    for freq_ind in freq_inds_sub:
      item = {}
      freq_term = standardize_freq_term(tbl_content[freq_ind])
      freq_inds_left = list(set(freq_inds_sub) - set([freq_ind]))
      adrs = []
      for i in range(1,len(tbl_content)):
        adr_ind = freq_ind +i
        # print(adr_ind, len(tbl_content))
        if adr_ind in freq_inds_left or adr_ind in soc_inds or adr_ind >=len(tbl_content):
          break
        else:
          adrs +=clean_cell_text(tbl_content[adr_ind])
      item[freq_term]=adrs
      adrs_tbl.append(item)
  else:
    for freq_ind in freq_inds_sub:
      item = {}
      freq_inds_left = list(set(freq_inds_sub) - set([freq_ind]))
      freq_term = standardize_freq_term(tbl_content[freq_ind])
      adrs = []
      for i in range(1,len(tbl_content)):
        adr_ind = freq_ind -i
        if adr_ind in freq_inds_left or adr_ind in soc_inds or adr_ind >=len(tbl_content):
          break
        else:
          adrs +=clean_cell_text(tbl_content[adr_ind])
      item[freq_term]=adrs
      adrs_tbl.append(item)

  # aggreate dict list by keys
  adrs_tbl = {key: flatten([d.get(key) for d in adrs_tbl if d.get(key)]) for key in set().union(*adrs_tbl)}

  return adrs_tbl

def extract_adrs_structured(freq_sublists, soc_inds, gaps, tbl_content):
  """
  """

  adrs = []
  if len(freq_sublists)==len(gaps):
    for gap, sublist in zip(gaps,freq_sublists):
      adrs_inds = [ freq+gap for freq in sublist if freq+gap not in soc_inds and freq+gap <len(tbl_content)]
      terms = [tbl_content[freq] for freq in sublist[-len(adrs_inds):]]
      freq_terms = [standardize_freq_term(term) for term in terms]
      adrs_soc = [ {freq_term: clean_cell_text(tbl_content[adr])} for freq_term, adr in zip(freq_terms,adrs_inds)]
      adrs += adrs_soc
  else:
    # another exception, e.g. 4763
    pass
  # aggreate dict list by keys
  adrs_tbl = {key: flatten([d.get(key) for d in adrs if d.get(key)]) for key in set().union(*adrs)}

  return adrs_tbl

def extract_vertical(tbl_content, soc_terms):
  """
  - extract adrs from the vertical table,
  A vertical table is table structure classified in the data processing step
  """

  adrs_tbl = {}
  freq_inds, soc_inds, len_tr, num_cols = get_vertical_inds(tbl_content, soc_terms)
  if len(soc_inds) >0:
    freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
    count_1_perc = get_vertical_struct_info(freq_inds_sub)

    if len(freq_inds_sub)>0:
      gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
    else:
      gap_soc_freq = 0 # no frequency
    if count_1_perc==0:
      adrs_tbl = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, tbl_content)
      # print(adrs_tbl)
      # print('not count_1_pert', num_cols, gap_soc_freq)
      # print("frequencies: ", freq_inds_sub, "soc indexes: ", soc_inds)
    # elif gap_soc_freq>10: # this is an exception, wrongly labelled table, 9417
    #   print('not count_1_pert', num_cols, gap_soc_freq)
    elif gap_soc_freq ==1: # frequency before adrs
      freq_sublists = split_by_diff(freq_inds_sub)
      gaps = [len(sublist) for sublist in freq_sublists]
      adrs_tbl = extract_adrs_structured(freq_sublists, soc_inds, gaps, tbl_content)
      # print("frequency before adrs")
    else: # frequency after adrs
      freq_sublists = split_by_diff(freq_inds_sub)
      gaps = [[e for e in (i - np.array(freq_inds_sub)) if e<0] for i in soc_inds ]
      gaps = [max(gap)+1 for gap in gaps if len(gap)>0]   
      if all(gap ==-1 for gap in gaps):
        # frequencies in horizontal
        remove_inds = np.array([freq_inds[i+1] for i in np.where(np.diff(freq_inds)==1)])
        adrs_content = [tbl_content[i] for i in range(len(tbl_content)) if i not in remove_inds[0] and i>=soc_inds[0]]
        adrs_tbl = extract_structured(adrs_content, soc_terms)
        # print(adrs)
      elif len_tr > len(gaps)*2 and num_cols>=3: # 4763 is statified this condiction, this should be addressed
        # frequencies in horizontal
        remove_inds = np.array([freq_inds[i+1] for i in np.where(np.diff(freq_inds)==1)])
        adrs_content = [tbl_content[i] for i in range(len(tbl_content)) if i not in remove_inds[0] and i>=soc_inds[0]]
        adrs_tbl = extract_structured(adrs_content, soc_terms)
        # print(adrs_tbl)
      else:
        # pass
        # frequencies in vertical
        adrs_tbl = extract_adrs_structured(freq_sublists, soc_inds, gaps, tbl_content)
        # print(adrs_tbl)
        # print(gap_soc_freq, gaps, 'vertical', num_cols)
        # two cases:  multiple frequencies in a line, e.g. 8052; multiple frequencies in a column, e.g. 9036
  else:
    adrs_tbl = []
    for freq_ind in freq_inds:
      item = {}
      freq_term = standardize_freq_term(tbl_content[freq_ind])
      freq_inds_left = list(set(freq_inds) - set([freq_ind]))
      adrs = []
      for i in range(1,len(tbl_content)):
        adr_ind = freq_ind +i
        # print(adr_ind, len(tbl_content))
        if adr_ind in freq_inds_left or adr_ind >=len(tbl_content):
          break
        else:
          adrs +=clean_cell_text(tbl_content[adr_ind])
      item[freq_term]=adrs
    adrs_tbl.append(item)
    # aggreate dict list by keys
    adrs_tbl = {key: flatten([d.get(key) for d in adrs_tbl if d.get(key)]) for key in set().union(*adrs_tbl)}
    # print(adrs_tbl)
  return adrs_tbl

def get_structured_inds(content_tbl, soc_terms):
  """
  obtain indexes of the frequency terms, and SOC terms
  """

  freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
  inds = []
  for freq in freqs:
    freq_inds = [i for i, x in enumerate(content_tbl) if re.match(freq,x) ]
    if len(freq_inds) >0:
      inds +=freq_inds

  content_tbl = [re.sub(r'\(cannot be estimated.+\)', '',item).strip() for item in content_tbl ]
  unknown = [i for i, x in enumerate(content_tbl) if "known" in x and len(x.split())<4]
  inds += unknown

  soc_inds = [i for i, x in enumerate(content_tbl) if check_soc_term(x, soc_terms) ]


  return np.sort(inds), np.sort(soc_inds)

def extract_structured(content, soc_terms):
  """
  - extract adrs from the structured text,
  instead of using tables to present adrs, sometimes structured text is used.
  """

  freq_inds, soc_inds = get_structured_inds(content, soc_terms)
  adrs = {}
  if len(soc_inds) >0:
    freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
    count_1_perc = get_vertical_struct_info(freq_inds_sub)

    if len(freq_inds_sub)>0:
      gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
    else:
      gap_soc_freq = 0
    if count_1_perc==0 and gap_soc_freq in [1,2]:
      adrs = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, content)
      # print(adrs)
      # pass
    elif count_1_perc==0 and gap_soc_freq>=4: # emc/90/ gap_soc_freq =4
      cutting_adr_index = [i for i, x in enumerate(content) if 'post-marketing' in x]
      if len(cutting_adr_index) >0:
        content = content[cutting_adr_index[0]:]
        freq_inds, soc_inds = get_structured_inds(content, soc_terms)
        # if len(soc_inds) >0:
        freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
        count_1_perc = get_vertical_struct_info(freq_inds_sub)

        if len(freq_inds_sub)>0:
          gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
        else:
          gap_soc_freq = 0
        adrs = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, content)
        # print(adrs)
      else:
        # exception 4205, use free-text extraction to obtain the adrs
        adrs_content = [content[i] for i in range(len(content)) if i not in soc_inds and i >soc_inds[0]]
        adrs = extract_freetext(adrs_content)
    else:
      # there are the exceptions, mainly 7861, 2380, frequency terms next to each others
      if len(freq_inds_sub) ==0:
        # print('no frequency terms')
        adrs_content = [content[i] for i in range(len(content)) if i not in soc_inds]
        adrs = extract_freetext(adrs_content)
      else:
        if count_1_perc>10: # 7861, exception
          tbl_marks = [i for i, x in enumerate(content) if 'treatment-related' in x ]
          cut_val = tbl_marks[1]
          freq_inds_sub = [ i for i in freq_inds_sub if i<cut_val]
          soc_inds = [ i for i in soc_inds if i<cut_val]
          content_sub = content[:cut_val]
          adrs = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, content_sub)
          # print(adrs)
        else: # 2380
          adrs_content = [content[i] for i in range(len(content)) if i not in soc_inds]
          adrs = extract_freetext(adrs_content)
          # print(count_1_perc, gap_soc_freq)
  else:
    # if frequency terms not next to each others, then do the same as count_1_perc==0 and gap_soc_freq==1
    # should treat these as free-text, 4466, 6666, 5705
    # print(freq_inds, 'no soc terms')
    if len(freq_inds) >5: # 4466, 5705
      adrs = []
      for freq_ind in freq_inds:
        item = {}
        freq_term = standardize_freq_term(content[freq_ind])
        item[freq_term] = clean_cell_text(content[freq_ind+1])
        adrs.append(item)
      adrs = {key: flatten([d.get(key) for d in adrs if d.get(key)]) for key in set().union(*adrs)}
      # print(adrs)
    else: # 6666
      adrs = extract_freetext(content)

  return adrs

def extract_freetext(content):
  """
  - extract adrs from the free text,
  Sometimes adrs are hidden in the free text, here we extract adrs and their frequencies
  """
  adrs = {}
  raw_content = '. '.join(content)
  # content = [ re.sub('e.g.','such as ',item) for item in content]
  # freqs = [' common', ' frequent', 'occasional']
  # nested_content = [item.split('.') for item in content]
  # drug_content = [item.strip() for item in flatten(nested_content) if item.strip()]
  # adrs_content = [item for item in drug_content if any(freq in item for freq in freqs)]
  # adrs_extracted = [text_razor(item) for item in drug_content]

  # use textrazor to extract ades
  adrs_extracted = text_razor(raw_content)
  adrs['not known'] = adrs_extracted
  # print(content)
  # print(adrs)

  return adrs

def main():
  """ the extraction process """
  start_time = time()
  drugs, soc_terms = load_data() # load drugs

  extract_adrs(drugs, soc_terms)
  dur = time() - start_time
  print('Duration is %s' %dur )
  return None

if __name__ == "__main__":
  main()