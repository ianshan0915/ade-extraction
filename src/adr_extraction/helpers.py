# -*- coding=utf-8 -*-

import numpy as np
from fuzzywuzzy import fuzz

# from watson_developer_cloud import NaturalLanguageUnderstandingV1
# from watson_developer_cloud.natural_language_understanding_v1 import Features, KeywordsOptions

import textrazor

def flatten(nested_array):
  """
  flatten out a nested array
  """
  result_array = [item for sublist in nested_array for item in sublist]
  return result_array

def split_by_diff(arr):
  """
  split an array into multiple sublists with each sublist contain a sequence like [1,2,3], [6,7],[9]

  input: np.array [1,2,3,6,7,9]
  output: [[1,2,3],[6,7],[9]]
  """

  diff_vals = np.diff(np.array(arr))
  split_index = np.where(diff_vals>1)[0]
  sublists = np.split(arr, split_index+1)

  return sublists

def check_soc_term(term, soc_terms):
  """
  check if a term is a soc term, if yes, return True
  """

  fuzz_ratios = [fuzz.ratio(term, soc_term) for soc_term in soc_terms]

  return any(i>=92 for i in fuzz_ratios)

# def ibmwaston_nlu(adr_sentence):
#   """
#   use IBM waston-NLU to process texutal input of ADRs
#   """

#   usernm = '1a5fba40-ab91-4b36-92a0-f957b6abeb0f'
#   passwd = 'jut4J5KJaoXe'
#   natural_language_understanding = NaturalLanguageUnderstandingV1(username= usernm, password= passwd, version='2018-11-16')
#   # text = repo_description.encode('utf-8')
#   response = natural_language_understanding.analyze(
#     text= adr_sentence,
#     language = 'en',
#     features=Features(
#       keywords=KeywordsOptions(
#         limit=15)))

#   keywords = [item['text'] for item in response['keywords']]
#   kw_str = ', '.join(keywords)

#   return kw_str

def text_razor(adr_sentence):
  """
  Use TextRazor to process textual input
  """

  textrazor.api_key = '5f6331ac5ecb61dfe6e57d9706eeb4f9e7bceaa82a4a37b128cb0201'
  textrazor.language_override = 'en'
  client = textrazor.TextRazor(extractors=['entities'])
  response = client.analyze(adr_sentence)
  phrases = response.entities()
  keywords = [item.matched_text for item in phrases if 'Disease' in item.dbpedia_types]
  keywords = list(set([item for item in keywords if not ('adverse' in item or 'side' in item or item=='pain')]))
  # kw_str = ', '.join(keywords)

  return keywords