# -*- coding=utf-8 -*-
#!/usr/bin/env python3

"""
Created on Wed Jan. 8, 2019

@author: ianshan0915

extract adverse drug reactions from the preprocessed (clean) data scraped from www.medicines.org.uk
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import re
from collections import Counter

from helpers import flatten

import numpy as np
from fuzzywuzzy import fuzz

def load_data():
  """
  load the textual data
  """

  drugs = json.load(open("./../data/side-effects-content-merged.json", 'r'))

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
        tbls_content.append(content_tbl)

      drug['content_cleaned'] = tbls_content
    elif drug['struct_type'] == 'structured':
      # remove special characters in the beginning e.g. - or \u2022
      drug['content_cleaned'] = [re.sub(r'^\u2022|^-','',item).strip() for item in drug['content_cleaned'] ]      
      freqs = [r'^very +common', r'^common', r'^uncommon', r'^rare', r'^very +rare']
      nested_content = [item.split(':') if (any(re.match(freq,item) for freq in freqs ) or 'known' in item) else [item] \
                        for item in drug['content_cleaned']]
      drug_content = flatten(nested_content)
      drug['content_cleaned'] = [item for item in drug_content if item.strip()]
    else:
      pass

  return drugs

def test(drugs):
  """
  testing some techniuqes
  """

  for drug in drugs:
    if drug['struct_type'] == 'tablular':
      num_tbl = len(drug['content_cleaned'])
      for tbl in drug['content_cleaned']:
        if tbl[1] == "table type: horizontal":

          freq_inds, most_common_diff = get_frequences_ind(tbl)
          num_cols, num_diff, count_disorders= get_tbl_struct_info(tbl)
          tbl_label = get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders)
          if tbl_label == -1:
            print(drug['url_drug'])
            # explore_vertical_content(tbl)
            # extract_vertical(tbl)
            # adrs = extract_adrs_tbl(tbl, freq_inds, tbl_label, num_cols)
            # for key in adrs.keys():
            #   print(adrs[key])
        else:
          print(drug['url_drug'])
          # explore_vertical_content(tbl)
          extract_vertical(tbl)
    # elif drug['struct_type'] == 'structured':
    #   print(drug['url_drug'])
    #   freq_inds, soc_inds = get_vertical_inds(drug['content_cleaned'])
    #   if len(soc_inds) >0:
    #     freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
    #     count_1_perc = get_vertical_struct_info(freq_inds_sub)

    #     if len(freq_inds_sub)>0:
    #       gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
    #     else:
    #       gap_soc_freq = 0
    #     # print(freq_inds, soc_inds)
    #     print(count_1_perc, gap_soc_freq)
    #     if count_1_perc==0 and gap_soc_freq==1:
    #       # adrs_tbl = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, drug['content_cleaned'])
    #       # print(adrs_tbl)
    #       pass
    #     elif count_1_perc==0 and gap_soc_freq>=4: # emc/90/ gap_soc_freq =4
    #       cutting_adr_index = [i for i, x in enumerate(drug['content_cleaned']) if 'post-marketing' in x]
    #       if len(cutting_adr_index) >0:
    #         drug['content_cleaned'] = drug['content_cleaned'][cutting_adr_index[0]:]
    #         freq_inds, soc_inds = get_vertical_inds(drug['content_cleaned'])
    #         # print(freq_inds, soc_inds)
    #         if len(soc_inds) >0:
    #           freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
    #           count_1_perc = get_vertical_struct_info(freq_inds_sub)

    #           if len(freq_inds_sub)>0:
    #             gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
    #           else:
    #             gap_soc_freq = 0
    #           # print(freq_inds, soc_inds)
    #           print(count_1_perc, gap_soc_freq)
    #     else:
    #       # there are the exceptions, mainly 7861, 2380, frequency terms next to each others
    #       pass               
    #   else:
    #     # if frequency terms not next to each others, then do the same as count_1_perc==0 and gap_soc_freq==1
    #     print(freq_inds, 'no soc terms')
    else:
      # free-text
      pass
  return None

def check_soc_term(term):
  """
  check if a term is a soc term, if yes, return True
  """
  # load soc terms
  soc_terms = json.load(open("./../data/soc-terms.json", 'r'))

  fuzz_ratios = [fuzz.ratio(term, soc_term) for soc_term in soc_terms['terms']]

  return any(i>=92 for i in fuzz_ratios)

def get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders):
  """
  - get the type of a horizontal table, the type will decide the following extraction process
  ! count_disorders is not very useful currently, because we know that all tables we collected contain 'disorder', 
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
    # we simply remove some cells
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

def extract_adrs_tbl(tbl_content, freq_inds, tbl_label, num_cols):
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
  if len(adrs_arr) % seq_len !=0 and not check_soc_term(adrs_arr[0]):
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

def extract_horizontal(tbl_content):
  """
  - extract adrs from the horizontal table,
  A horizontal table is table structure classified in the data processing step
  """

  freq_inds, most_common_diff = get_frequences_ind(tbl_content)
  num_cols, num_diff, count_disorders = get_tbl_cols(tbl_content)

  # get the type of table
  tbl_label = get_horizontal_table_type(freq_inds, most_common_diff, num_cols, num_diff, count_disorders)
  
  if tbl_label in [0,1,2]:
    adrs = extract_adrs_tbl(tbl_content, freq_inds, tbl_label, num_cols)
  else:
    pass # some exception handling scripts

  return adrs

def drugs_horizontal(drugs):
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
          adrs = extract_horizontal(tbl)
          drug_adrs += adrs
        else:
          adrs = extract_vertical(tbl)
          drug_adrs += adrs
    elif drug['struct_type'] == 'structured':
      freq_inds, soc_inds = get_vertical_inds(drug['content_cleaned'])
    else:
      pass
    drug['adrs'] = drug_adrs

  return drugs

def get_vertical_inds(content_tbl):
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

  soc_inds = [i for i, x in enumerate(content_tbl) if check_soc_term(x) ]

  return np.sort(inds), np.sort(soc_inds)

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
    pass # 816 no soc terms
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
      freq_term = standardize_freq_term(tbl_content[freq_ind])
      adrs = []
      for i in range(1,len(tbl_content)):
        adr_ind = freq_ind -i
        if adr_ind in soc_inds or adr_ind >=len(tbl_content):
          break
        else:
          adrs +=clean_cell_text(tbl_content[adr_ind])
      item[freq_term]=adrs
      adrs_tbl.append(item)

  # aggreate dict list by keys
  adrs_tbl = {key: flatten([d.get(key) for d in adrs_tbl if d.get(key)]) for key in set().union(*adrs_tbl)}

  return adrs_tbl

def extract_vertical(tbl_content):
  """
  - extract adrs from the vertical table,
  A vertical table is table structure classified in the data processing step
  """

  freq_inds, soc_inds = get_vertical_inds(tbl_content)
  if len(soc_inds) >0:
    freq_inds_sub = [i for i in freq_inds if i > soc_inds[0]]
    count_1_perc = get_vertical_struct_info(freq_inds_sub)

    if len(freq_inds_sub)>0:
      gap_soc_freq = freq_inds_sub[0]-soc_inds[0]
    else:
      gap_soc_freq = 0 # no frequency

    if count_1_perc==0:
      # adrs_tbl = extract_adrs_vertical_tbl(freq_inds_sub, soc_inds, gap_soc_freq, tbl_content)
      # print(adrs_tbl)
      # print("frequencies: ", freq_inds_sub, "soc indexes: ", soc_inds)
      pass
    elif gap_soc_freq ==1: # frequency before adrs
      print(count_1_perc, gap_soc_freq)
      print("frequencies: ", freq_inds_sub, "soc indexes: ", soc_inds)
      # pass
    else: # frequency after adrs
      # two cases:  multiple frequencies in a line, e.g. 8052; multiple frequencies in a column, e.g. 9036
  else:
    # pass
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
    print(adrs_tbl)
  return None

def extract_structured():
  """
  - extract adrs from the structured text,
  instead of using tables to present adrs, sometimes structured text is used.
  """

  pass

  return adrs

def extract_freetext():
  """
  - extract adrs from the free text,
  Sometimes adrs are hidden in the free text, here we extract adrs and their frequencies
  """

  pass

  return adrs

def main():
  """ the extraction process """

  drugs = load_data() # load drugs

  test(drugs)

  return None

if __name__ == "__main__":
  main()