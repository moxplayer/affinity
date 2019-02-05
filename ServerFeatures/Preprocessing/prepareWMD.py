import gensim, pdb, sys, scipy.io as io, numpy as np, pickle, string
from gensim.models import FastText
sys.path.append('./ServerFeatures/Usermanagement')
from dbdetails import createUserDetail, populateBoWReferenceCorpus, populateUsersBoW, fetchdistinctUsercount, fetchDocumentcount, fetchUserBoW, fetchUserName, checkValidUser, fetchProcessStatus,\
	fetchTimestamp, updateTFIDF, fetchTopNtfidf, updateProcessStatus, updateMessageTimestamp, updateFBEmailid

sys.path.append('./ServerFeatures/util')
from utilities import safe_normalize

sys.path.append('./ServerFeatures/util')
from utilities import write_log

#this library NEEDS to be installed from the incremental fastText version!
#go to Repository folder ./fastText and run "pip install ."
import fastText

pickle_directory     = './ServerFeatures/Userdata/pickle_files/'
reference_model_path = './ServerFeatures/Wordembedding/reference_model.bin'


# pickle the transposed truncated word vectors, and the truncated bag-of-words by <userid> for comparison via the WMD

def createPickle(app, userid, featurenames, occurrences, embedding_dimension, useNormalization):

	# for the non-incremental/original fasttext version:
	# model = FastText.load_fasttext_format(reference_model_path, encoding='utf8')
	
	print("Generate pickle file for the Userid: ", userid)

	# load the reference model 
	reference_model = fastText.load_model(reference_model_path)

	# convert the list of occurrences into a numpy-array
	np_occurrences  = np.array(occurrences)

    	# extract word counts and word vectors
	# word vectors to compars (words x embedding_size)

	word_vectors = np.array([reference_model.get_word_vector(featurename) for featurename in featurenames])

	# normalize word vectors (only for Euclidean distance)		
	if useNormalization:
		word_vectors = [safe_normalize(word_vector) for word_vector in word_vectors]

	# transpose <word_vectors>
	transposed_wordvectors = word_vectors.T # [~np.all(word_vectors.T == 0, axis=1)]

	# pickle the truncated <transposed_wordvectors> and a numpy array of occurrences (Bag of Words)
	pickle_name = pickle_directory + "pickle_output_" + str(userid) + ".pk" 
	pickle_load = [transposed_wordvectors, np_occurrences]
	
	try:
		with open(pickle_name , 'wb') as f:
			pickle.dump(pickle_load, f)
			f.close()
		response_code = "1"

	except PickleError:
		print("Error pickling transposed word vectors and the truncated bag-of-words.")
		response_code = "-1"

	if response_code == "1":
		# Update process status to '8'
		updateProcessStatus(app, int(userid), '8')

		write_log("Pickle File generated for userid".format(userid))
		print("User information of {} is now ready for comparison".format(userid))

	
	return response_code


