from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
import numpy as np
import sys
sys.path.append('./ServerFeatures/Usermanagement')
from dbdetails import connect_mysql, createUserDetail, populateBoWReferenceCorpus, populateUsersBoW, fetchdistinctUsercount, fetchDocumentcount, fetchUserBoW, fetchUserName, checkValidUser, fetchProcessStatus, fetchTimestamp, updateTFIDF, fetchTopNtfidf, updateProcessStatus, updateMessageTimestamp, updateFBEmailid

# translate a chatHistory by <userid> defined in <chatHistoryPath> into a vocabulary and corresponding bag-of-words
# populate the DB and retrieve the reponse code

def generateUserBoW(app, userid, chatHistoryPath, crossvalidate = False):

	# TODO: failover: if userid is negative
	# TODO: add print messages for debugging
	# TODO: fix duplicates in the userBoW table
	# TODO: in order to add max_df, and min_df, loading a corpus (list of documents), where a document is a user is necessary. --> there have to be enough 
	#       documents, perhaps adding a try/except block is necessary


	# read chatHistoryPath (single document); can handle more documents
	with open(chatHistoryPath,'r') as chatHistory:
		chatHistory =  [chatHistory.read().decode('utf-8')]#
		
		# Create a Bag-of-Words [X]
		vectorizer   = CountVectorizer(stop_words='english', ngram_range=(1,1))
		X            = vectorizer.fit_transform(chatHistory)

	# unicode strings of vocabulary words (featurenames)
	featurenames = vectorizer.get_feature_names()

	# array of word occurrences
	X_array = X.toarray()[0]
	
	response_code = populateUsersBoW(app, int(userid), featurenames, X_array, crossvalidate = crossvalidate)
	# "1" : success
	#

	if response_code == "1":
		# set process status to '5'
		updateProcessStatus(app, int(userid), '5')	

	return response_code


