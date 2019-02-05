import os, numpy as np
from datetime import datetime

# log a message
def write_log(log_message):
	log_file_dir = "./ServerFeatures/logfiles/"
	
	# create a logfile, if it is not there
	if not os.path.exists(log_file_dir):
	    os.makedirs(log_file_dir)
	
	# log event
	with open(log_file_dir + "logfile.log", "a") as logfile:
		logfile.write(str(datetime.now()) + "\t" + log_message + "\n")
	return

# calculate the cosine distance between two vectors of type <list>
# cos_distance(x1,x2) = 1 - cos(x1,x2)    (in [0,1])
# identical non-zero vectors --> 0
# orthogonal vectors         --> 1
def cosine_distance(x1,x2):
	#nonzerofound1 = False
	#nonzerofound2 = False
	#for i in range(0,len(x1)):
	#	if(x1[i] != 0):
	#		nonzerofound1 = True
	#	if(x2[i] != 0):
	#		nonzerofound2 = True
	#if(not (nonzerofound1 & nonzerofound2)):
	#	return 0
	norm_x1 = np.linalg.norm(x1)
	norm_x2 = np.linalg.norm(x2)
	if not (norm_x1 == 0 and norm_x2 == 0):
		dot_product = np.dot(x1,x2)
		cosine_distance = 1.0 - (dot_product / (norm_x1 * norm_x2))
	else:
		cosine_distance = 0.0
	return (cosine_distance)


# calculate the euclidean distance between two vectors of type <list>
def euclidean_distance(x1,x2):
	return np.sqrt( np.sum((np.array(x1) - np.array(x2))**2) )




# calculate the norm of a vector unless it is non-zero.
# return 1 else
def safe_norm(vector):
	norm = np.linalg.norm(vector)
	if norm == 0:
		return 1.0
	return norm

# normalize a matrix of row_vectors safely
def safe_normalize(row_vectors):	
	vector_norms            = [safe_norm(row_vector) for row_vector in row_vectors]
	normalized_row_vectors = (row_vectors.T / vector_norms).T
	return normalized_row_vectors


# split a text into n equal-sized distinct substring
# text : <str> text to split
# n    : number of text chunks
# the chunks have at least len(text.split()) // n words, the last chunk is always the longest

def split_text(text, n):
	# (character) indices to cut the text at
	cutting_indices = [0]
	# set the base index to 0
	index = 0
	# since the initial index is 0, we have to add a " " if it is not there yet
	if text[0] != " ":
		text = " " + text
	# calculate the reference word length of each chunk
	text_word_len   = len(text.split())
	text_char_len   = len(text)
	chunk_size      = text_word_len//n

	# for all words in the text find the index of blanks
	for i in range(text_word_len):
		increment = text[index+1:].find(' ')+1
		index    += increment
		# and only remember every <chunk_size>'th index
		if i % chunk_size == chunk_size-1:
			cutting_indices.append(index)

	# shift the last cutting index to the end of the text, else you will lose words at the end of the text
	cutting_indices[-1] = len(text)

	# slice the text at the cutting indices
	chunks = [text[ind_min + 1: ind_max] for ind_min, ind_max in zip(cutting_indices[:-1], cutting_indices[1:])]

	return chunks


















