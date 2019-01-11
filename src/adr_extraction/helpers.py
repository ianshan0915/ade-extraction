def flatten(input_array):
  result_array = [item for sublist in input_array for item in sublist]
  return result_array