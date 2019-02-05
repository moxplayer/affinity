from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
from flask import Flask,request,jsonify
import numpy as np
import sys
sys.path.append('./ServerFeatures/Usermanagement')
from dbdetails import connect_mysql, createUserDetail, populateBoWReferenceCorpus, populateUsersBoW, fetchdistinctUsercount, fetchDocumentcount, fetchUserBoW, fetchUserName, checkValidUser, fetchProcessStatus, fetchTimestamp, updateTFIDF, fetchTopNtfidf, updateProcessStatus, updateMessageTimestamp, updateFBEmailid
import math

# Calculate TFIDF records for <userid>
# requires: [doc_total_words, term_counts, document_counts]
# tf  : term frequency
# idf : inverse document frequency
# NOTE: the calculation of both tf and idf is not fixed, there are many different versions

def get_tfidf(doc_total_words, doc_max_words, overall_doccount, term_count, document_count):
	# number of times a term (word) occurrs in the document/ total number of terms (words) in the document
	tf       =   float(term_count)/float(doc_max_words)
	# logarithm (base 'e') of [number of all documents(= number of registered users)/number of documents the term (word) occurred]
	idf      =   math.log( float(float(overall_doccount)/float(document_count)))
	tfidf    =   tf*idf
	return tfidf


# calculate the TFIDF features for <userid> and populate the DB with the TFIDF feature information

def generateTFIDF(app, userid):
	print("Generate TFIDF for the userid: ", userid)
	
	# Fetch UserBoW;
	# min_df : <float> between 0.0 and 1.0 specifying the minimal percentage over all documents in which a term occurs
	# max_df : <float> between 0.0 and 1.0 specifting the minimal percentage over all documents in which a term occurs
	# returns: [vocab_words, term_counts, document_counts, user_counts, document_frequencies]
	#	success: vocabulary words and their document frequencies (as tuples of tuples)
	#	error  : "-1"
	vocab_words, term_counts, document_counts, user_counts, document_frequencies = fetchUserBoW(app, userid, min_df = 0.05, max_df = 1.0)
	# fetch the number of distinct registered <userid>s
	overall_doccount  = fetchDocumentcount(app)

	# total number of words used by <userid>
	doc_total_words = sum(term_counts)
	# number of occurrences of the most frequently used word by <userid>
	doc_max_words   = max(term_counts)

	print("A total of {} words has been filed by the user with userid {}.".format(doc_total_words, userid))
	# get tfidf values for all terms # some zipping issues
	tfidf_vector = [get_tfidf(doc_total_words, doc_max_words, overall_doccount, term_count, document_count) for term_count, document_count in zip(term_counts, document_counts)]

	# Update TFIDF program
	# response_code  "1" : Successfully calculate and update tfidf values in the userBoW TABLE
	#		"-1" : Error while updating tfidf.
	print("Update TFIDF records for the userid: ",userid)
	response_code = updateTFIDF(app, userid, vocab_words, tfidf_vector)
	
	if response_code == "1":
		# set process status to '6'
		updateProcessStatus(app, int(userid), '6')	


	# report success
	return response_code





