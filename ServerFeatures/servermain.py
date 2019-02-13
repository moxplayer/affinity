from flask import Flask,request,jsonify
from fbchat import Client
from fbchat.models import *
from subprocess import call
import sys

sys.path.append('./ServerFeatures/util')
from utilities import write_log, split_text, safe_normalize_vec

sys.path.append('./ServerFeatures/Dataextraction')
from fetchFBdetails import fetchFBInformation

sys.path.append('./ServerFeatures/Preprocessing')
from userTFIDFgeneration import generateTFIDF
from prepareWMD import createPickle, pickle_directory
from userBoWgeneration import generateUserBoW

sys.path.append('./ServerFeatures/Processing/wmd')
from wmd_adapted import cosine_distance, euclidean_distance, calc_similarity, load_pickle                                        

sys.path.append('./ServerFeatures/Usermanagement')
from dbdetails import createUserDetail, populateBoWReferenceCorpus, populateUsersBoW, fetchdistinctUsercount, fetchDocumentcount, fetchUserBoW, fetchUserName, checkValidUser, fetchProcessStatus, fetchTimestamp, updateTFIDF, fetchUserId, fetchTopNtfidf, updateProcessStatus, updateMessageTimestamp, updateFBEmailid

sys.path.append('./ServerFeatures/Userdata')
from createreferenceusers import referenceUserCreation

sys.path.append('./ServerFeatures/Wordembedding')
from initiate_we import trainWEforallfiles, trainWEwithuserfile

import os
import json
from datetime import datetime

#########################################
#### PROCESS - STATUS LIST ##############
#########################################
# error                            # -1 #
# account created                  #  1 #
# succ. FB login                   #  2 #
# fetch FB messages                #  3 #
# lang. class. (drop non-English)  #  4 #
# BoW generated                    #  5 #
# TFIDF generated                  #  6 #
# pickle file generated            #  7 #
# IDLE (ready to compare)          #  8 #
#########################################



#################################################################################################################################################
#Code 																		#
# - fetches the FB Details for "id" sent by the client by											#
#		a) fetching the email id from the DB 												#
#		b) returning the fetched conversation back to the client									#
#	Modified on 14-08-18															#
#################################################################################################################################################

app= Flask(__name__)


# for debugging purposes only!
@app.route("/", methods =['GET'])
def hello():
	return "<h1 style='color:blue'>Hello There! You landed on the affinity application's root folder. Send HTTP requests to the corresponding subpages!</h1>"


# Create a new user account in the DB;
# requires : [username, emailid, password] (<string>, <string>, <string>)
@app.route('/createuser', methods=['GET','POST'])
def processUserCreationRequest():
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to create a user account.</h1>"
	
	elif request.method == 'POST':
		createuser = request.get_json(force=True)
		returndata = {}
		# Call DB procedure to create user details
		print("Values to be inserted into the Data Base are Name: ",createuser['username']," Emailid: ",createuser['emailid'])
		# userid = -1           : emailid is already registered
		#        = -2           : username is already registered
		#        = -3           : error with writing into the DB
		#        = pos. integer : fine
		userid = createNewUser(app, createuser['username'],createuser['emailid'],createuser['password'],'user')
		returndata['userid']   = userid
		returndata['username'] = createuser['username']
		return(json.dumps(returndata))
	return "<h1 style='color:blue'>Nothing happened. Please inspect your input.</h1>"

def createNewUser(app, username, email, password, usertype):
	return createUserDetail(app, username, email, password, usertype)



# Create a reference user account in the DB;
# requires :
#  [path, useforretrain] (<string>,<bool>)
# path          : path to a reference corpus (*.xml) or a single user's reference file (*.txt) to train the reference fasttext model on
# useforretrain : True, if the created reference user(s) should be used to update the model
# after downloading 'smsCorpus_en_2015.03.09_all.xml'
# use e.g.: "path" : "./ServerFeatures/Userdata/smsCorpus_en_2015.03.09_all.xml", "useforretrain" : "False"

# NOTE: 1. the input .xml file is dissolved into distinct users' reference files
#       2. training a fasttext model will result in worker timeouts unless setting the '-t' flag on invocation of gunicorn

# if a *.XML file is passed:
#	1. dissolve XML corpus into separated *.TXT files 
#	2. create userids (format: 'R'-username) in the DB  [user type: reference]
#	3. run the process pipeline on all referenceuserids
# if a *.TXT file is passed:
#	1. create a userid (format: 'R'-username) in the DB [user type: reference]
#	2. run the process pipeline on the referenceuserid

@app.route('/createreferenceuser', methods=['GET','POST'])
def processReferenceUserCreationRequest():
	# set path to the folder with all extracted chat histories
	dir_ref_histories 	= "./ServerFeatures/Userdata/Reference_User_Histories"
	# minimum amount of bytes a reference chatHistory has to contain in order to be considered for training
	min_bytes               = 1000

	# extract the request body
	referencedetails    = request.get_json(force=True)
	reference_file_path = referencedetails['path']

	if(referencedetails['useforretrain'] == "True"):	
		useforretrain = True
	else:
		useforretrain = False

	# if GET-request
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to create a reference user account.</h1>"
	# elif POST-request
	elif request.method == 'POST':
		# Start creating reference users  ### put this into a separate function!!!
		print("Create reference users...")
		# XML
		if(reference_file_path.endswith(".xml")):

			# dissolve the reference corpus' user chat histories to <dir_ref_histories> into separate *.txt chatHistories
			referenceUserCreation(app,reference_file_path, dir_ref_histories)                        

			# run the process pipeline on all referenceusers (*.TXT files) in dir_ref_histories that have more than <min_bytes> text
			for root, dirs, files in os.walk(dir_ref_histories):
				for file_ in files:
					# set reference username
					reference_username = 'R-' + file_
					print("Reference file: ", file_)
					# if 'file_' is a text-file and contains at least <min_bytes> bytes... ADD A LOGIC TO THIS AND CONCAT A BIG CORPUS BEFORE RUNNING THE PROCESS PIPELINE
					tooShort = os.path.getsize(os.path.join(root, file_)) < min_bytes
					isTxt    = file_.endswith(".txt")
					if not tooShort and isTxt:
						# Create a 'reference' user
						referenceuserid = createNewUser(app, reference_username, reference_username, '', 'reference')
						# if the referenceuserid has been registered before
						if referenceuserid == "-1":
							referenceuserid = fetchUserId(app, reference_username)
					
						print("The userid for the reference file " + file_ + " is: " + referenceuserid)

						# Start the Process Pipeline in order to fill in BoW and TFIDF values in the DB
						# NOTE: starting the processPipeline is not recommendable for many small reference files!
						refchatHistoryPath  = os.path.join(root, file_)
						processPipeline(app, referenceuserid, refchatHistoryPath, useforretrain)
					elif not tooShort:
						print("The reference file is not a txt-file and is thus skipped.")
					elif isTxt:
						print("The reference file is too short and is thus skipped.")
					print(" ")


			return "createreferenceuser/XML"

		# TXT
		elif reference_file_path.endswith(".txt"):
			# set the reference_username
			file_ = os.path.split(reference_file_path)[1]
			reference_username = 'R-' + file_
			print("Reference file: ", file_)
			# create a 'reference' user
			referenceuserid = createNewUser(app, reference_username, reference_username, '', 'reference')
			# if the referenceuserid has been registered before
			if referenceuserid == "-1":
				referenceuserid = fetchUserId(app, reference_username)
			print("Userid for the reference file " + file_ + " is: " + referenceuserid)
			# start the process pipeline if the file is a .txt file and has at least <min_bytes> bytes				
			tooShort = os.path.getsize(reference_file_path) < min_bytes
			isTxt    = file_.endswith(".txt")
			if not tooShort and isTxt:
				processPipeline(app, referenceuserid, reference_file_path, useforretrain)
			elif not tooShort:
				print("The reference file is not a txt-file and is thus skipped.")
			elif isTxt:
				print("The reference file is too short and is thus skipped.")

			return "createreferenceuser/TXT"

	return "<h1 style='color:blue'>Nothing happened. Please inspect your input.</h1>"



# Login to 'affinity'
# requires : [emailid, password] (<string>,<string>)
# return:
# userid   = -1; username = ''    : wrong credentials
@app.route('/login', methods=['GET','POST'])
def checkIfValidUser():
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to login to 'affinity'.</h1>"
	if request.method == 'POST':
		checkuser  = request.get_json(force=True)
		returndata = {}
		print("Check credentials for " + checkuser['emailid'])
		username, userid       = checkValidUser(app,checkuser['emailid'],checkuser['password'])
		returndata['userid']   = userid
		returndata['username'] = username
		return(json.dumps(returndata))
	return "<h1 style='color:blue'>Nothing happened. Please inspect your input.</h1>"
	

# Return process status for <userid>
# requires : [userid]
@app.route('/checkstatus', methods=['GET','POST'])
def checkProcessStatus():
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to check your process status.</h1>"
	elif request.method == 'POST':
		checkuserid = request.get_json(force=True)
		returndata  = {}
	
		userid       = int(checkuserid['userid'])
		useridstatus = fetchProcessStatus(app, userid)
		print("Check status of userid: ", userid)
		returndata['statuscode'] = useridstatus
		print("Status of Userid's is:",useridstatus)
		return(json.dumps(returndata))
	return "<h1 style='color:blue'>Nothing happened. Please inspect your input.</h1>"

# Fetch FB chat-information of the user, and integrate the additional user text to the BoW/TFIDF information stored in the DB
# requires : [userid, fbemailid, fbpassword] (<string>,<string>,<string>)
@app.route('/processdetails', methods=['GET','POST'])
def fetchUserDetail():
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to fetch FB chat information from your facebook account.</h1>"
	elif request.method == 'POST':
		write_log("Start fetching userDetail()")

		clientdetails   = request.get_json(force=True)
		userid          = clientdetails['userid']
		userfbemailid   = clientdetails['fbemailid']
		userfbpassword  = clientdetails['fbpassword']
		print("FB User-id: ", userfbemailid)
		# fetch chat messages by <userid> from FB, split them into separate chat histories depending on their language and
		# return the chat history path to the English conversation messages, if successful
		# or "-1" if it failed
		chatHistoryPath = fetchFBInformation(app, userid, userfbemailid, userfbpassword)

		# if fetching an English FB chat history was successfull
		if chatHistoryPath != "-1":
			write_log("Fetched Facebook Info")
			print("Path", chatHistoryPath)
			# decide whether the reference model should be adjusted upon uploading a text file
			useforretrain = False
			# process the pipeline
			processPipeline(app, userid, chatHistoryPath, useforretrain)
		# why is '-1' returned?
		return (jsonify('-1'))
	return "<h1 style='color:blue'>Nothing happened. Please inspect your input.</h1>"



# PROCESS PIPELINE
# INPUT: <userid>, <chatHistoryPath> : path to a TXT-document by <userid> (chatHistory)
# 
# 0. Check if there is a pretrained <referene_model> (word_embedding): if not --> train a reference model (TO BE IMPLEMENTED)
# 1. if <useforretrain> == True : re-train the <reference_model>, with the input document (*.TXT) by <userid>                   ## only use the useforretrain carefully!
# 2. create Bag-of-words for the chatHistory													[status ('1')/('4') --> '5']
# 3. populate the DB with the Bag-of-words 
# 4. create TFIDF values																		[status    ('5')    --> '6']
# 5. populate/update the DB with TFIDF values													[status    ('6')    --> '7']
# 6. fetch the most important terms for <userid> and their (truncated) Bag-of-Words; truncated because not all wors are being considered here	
# 7. pickle the most important terms for <userid> and their word_vectors into an individual pickle file for future unpickling and comparison	[status    ('7')    --> '8']
#
#
#
# NOTE: useNormalization is set to False for initial purposes
#       for the future passing from status 2-4 will not be necessary I believe
# if crossvalidate = True, the BoWHistory TABLE will not be updated! --> the user is invisibile to the ecosystem

def processPipeline(app, userid, chatHistoryPath, useforretrain, useNormalization = False, crossvalidate = False):
	reference_model_path = './ServerFeatures/WordEmbedding/reference_model.bin'
	reference_file_dir   = './ServerFeatures/Userdata/Reference_User_Histories'
	model_output_name	 = './ServerFeatures/WordEmbedding/reference_model'
	
	referenceModelExists = False
	########
	# 0. Check if a reference model exists
	########
	#print('Check if a reference model exists.')
	if os.path.isfile(reference_model_path):
		#print('A reference model has been found.')
		referenceModelExists = True
	# if not, train a reference model
	else:
		print('No reference model has been found. Start training a reference model upon the reference chatHistories.')
		trainWEforallfiles(reference_file_dir, model_output_name, min_bytes = 1000)
		

	##########
	# 1. Retrain an existing reference model with <userid>'s chatHistory, if specified
	##########
	if useforretrain:
		write_log("Start retraining the reference model incrementally with {}'s chat history.".format(userid))
		# update the reference-fasttext-model
		trainWEwithuserfile(chatHistoryPath) 
		write_log("Finished retraining the reference model incrementally")

	########
	# start the pipeline
	#########################
	# pick <top_tfidf_limit> vocabulary words for similarity comparison
	top_tfidf_limit     = 1500 		
	# dimension of the embedded vectors in real space
	embedding_dimension = 100
	# fetch process status 
	processstatus = fetchProcessStatus(app, userid)

	#######
	# 2./3. Generate and Populate BoW
	#######################################################
	if (processstatus == '1') or (processstatus == '4') :
		write_log("Start BoW generation")
		# BoWgenerated =  "1" : SUCCESS;
		# BoWgenerated = "-1" : error adding occurrences for a term into the UserBoW TABLE;
		# BoWgenerated = "-2" : error adding a new term to the BoWHistory TABLE;
		# BoWgenerated = "-3" : error updating an existing term to the BoWHistory TABLE;
		BoWgenerated = generateUserBoW(app, int(userid), chatHistoryPath, crossvalidate = crossvalidate)
		write_log("BoW generated")

	# fetch the process status
	processstatus = fetchProcessStatus(app, userid)

	# if the process status states that the BoWs have been generated populate the DB
	if processstatus == "5":
		BoWgenerated = "1"
	else:
		BoWgenerated = "0"

	if (BoWgenerated == '1'): 
		##########
		# 4./5. Generate TFIDF
		##########
		write_log("Calculate TF-IDF")
		# TFIDFgenerated  "1" : Successfully calculate and update tfidf values in the userBoW TABLE
		#		 "-1" : Error while updating tfidf.
		TFIDFgenerated = generateTFIDF(app,userid)
		write_log("TF-IDF generated")

	# fetch the process status
	processstatus = fetchProcessStatus(app, userid)


	# if the process status states that the BoWs have been generated populate the DB
	if (processstatus == "6") | (processstatus == "7"): 
		TFIDFgenerated = "1"
	else:
		TFIDFgenerated = "0"

	if (TFIDFgenerated == '1'):
		###########
		# 6. Fetch the most important terms for <userid> (in the sequel they will be referred to as 'truncated')	
		###########
		# fetchedTopN = "1" : successfully fetched the top N
		write_log("Select TOP N TFIDF terms")
		try:    # CAVEAT: so far the number of retrieved words could be less than N
			truncated_featurenames, truncated_occurrences = fetchTopNtfidf(app, userid, top_tfidf_limit)	
			fetchedTopN =  "1" 
			write_log("Top TFIDF fetched.")
		except:
			fetchedTopN = "-1"
		
		if (fetchedTopN == '1'):
			###########
			# 7. Generate pickle files of the transposed truncated (normalized if <useNormalization> == True) word vectors and their bag-of-words
			# this information is used in order to calculate the similarity between two users via the WMD
			# pickle-name-format : pickle_directory + "pickle_output_" + str(userid) + ".pk"
			# with
			# pickle_directory = './ServerFeatures/Userdata/pickle_files/'
			###########
			write_log("Generate Pickle Files.")
			# picklefilegenerated  "1" : Successfully generated pickle files of (??)
			#                     "-1" : Error while pickling
			picklefilegenerated = createPickle(app, userid, truncated_featurenames, truncated_occurrences, embedding_dimension, useNormalization)
			

	return(jsonify(userid))


# Calculate similarity between two <userid>'s
# requires : [userid1, userid2] with process status '8'
@app.route('/comparedetails', methods=['GET','POST'])
def compareUserDetails():
	if request.method == 'GET':
		return "<h1 style='color:blue'>Send a POST request [Accept:application/json] in order to calculate the similarity between two users.</h1>"
	if request.method == 'POST':
		clientdetails = request.get_json(force=True)
		userid1       = clientdetails['userid1']
		userid2       = clientdetails['userid2']

		# set signature size (max. number of words to use per user)
		sig_size = 50
		
		# use_cosine : True <-> use cosine_distance; else euclidean_distance
		use_cosine    = True
		if use_cosine:
			dist = cosine_distance
			cosine_adjustment = True
		else:
			dist = euclidean_distance
			cosine_adjustment = False
		# 
		#normalize    = False
		
		returndata    = {}
		print("Compare similarity between userid ", userid1, " and ", userid2)
		
		# fetch the signatures of userid1 and userid2
		pickle_path1 = os.path.join(pickle_directory, "pickle_output_" + str(userid1) + ".pk")
		pickle_path2 = os.path.join(pickle_directory, "pickle_output_" + str(userid2) + ".pk")
		signature1 = load_pickle(pickle_path1)
		signature2 = load_pickle(pickle_path2)
		
		# transpose the word vectors (embedding_dim x word_vectors --> word_vectors x embedding_dim)
		signature1[0] = signature1[0].T
		signature2[0] = signature2[0].T
		
		# cast numpy.ndarray to list
		signature1 = [el.tolist() for el in signature1]
		signature2 = [el.tolist() for el in signature2]
		
		# truncate to signature_size word:eight pairs
		signature1 = [el[:sig_size] for el in signature1]
		signature2 = [el[:sig_size] for el in signature2]

		# make weights floats
		signature1[1] = safe_normalize_vec(signature2[1])
		signature2[1] = safe_normalize_vec(signature2[1])
		
		# assemble comparisonpair
		comparisonpair = [signature1, signature2]
		
		# calculate their distance
		similarity  = calc_similarity(comparisonpair, distance = dist, cosine_adjustment = cosine_adjustment)
		
		username1 = fetchUserName(app, userid1)
		username2 = fetchUserName(app, userid2)
		print("Similarity between ", username1, " and ", username2, " is:", similarity)
		returndata['userid1']    = userid1
		returndata['userid2']    = userid2
		returndata['username1']  = username1
		returndata['username2']  = username2
		returndata['similarity'] = similarity*100
		return(json.dumps(returndata))
	

	
	
### FOR TESTING ONLY!!!
# calculate the pairwise  distances between a list of userids
# export is a (Gephi) edge graph
# requires : [userids] , comma-separated userids
# format : "1,2,3": WRONG: "1, 2, 3"
@app.route('/pairwisedist', methods=['POST'])
def calcPairwiseDist():

	# use cosine
	use_cosine = True

	# export as gephi edge graph file
	as_gephi = True

	if request.method == 'POST':
		from collections import namedtuple
		sys.path.append('./ServerFeatures/Processing/wmd/python-emd-master')
		from emd import emd
		from math import sqrt
		from utilities import cosine_distance, euclidean_distance
		#1. insert a couple of userids
		data    = request.get_json(force=True)
		userids = data['userids']
		userids = userids.split(',')
		try:
			userids = [int(el) for el in userids]
		except:
			pass
		#2. Calculate pairs
		id_pairs = []
		N = len(userids)
		for i in xrange(N):
			for j in xrange(i+1,N):
				id_pairs.append((userids[i],userids[j]))
		#3. For all pairs run emd
		similarities = []
		for userid1, userid2 in id_pairs:
			similarities.append(calc_similarity(app, userid1, userid2, use_cosine))

		# convert to gephi edge-graph format
		if as_gephi:
			result = "source,target,weight\n"
			for id_pair, similarity in zip(id_pairs, similarities):
				line   = str(id_pair[0])+','+str(id_pair[1])+','+str(similarity)+'\n'
				result += line
		else:
			result = str(list(zip(id_pairs, similarities)))[1:-1]

		# define a timesting (hour_minute_second) in order to specify the time the sim_file has been generated
		time_string = datetime.now().strptime("%Y_%m_%d_%H_%M_%S")
		with open(time_string+'_sims.csv', mode = 'w') as f:
			f.write(result)
			print('Wrote a file with pairwise similarities')
		return(json.dumps(result))


### FOR EVALUATION: take a text and chunk it into equal-sized subparts in order to calculate intra-user similarities

# ASSUMPTION: leaving out a chunk of one user in the eco-system does not affect the idf
# NEW IDEA:
# 1. create n equal-sized text chunks for a given user
# 2. create n equal-sized texts by leaving out one chunk each
# 3. create .txt files for all those chunks in a special folder
# 4. run the reference-user procedure for all such chunks (.txt files) WITHOUT changing the BoWHistory TABLE

# requires:	[path]         : filename of the textfile of the user to calculate cross-validation
#		[n]            : number of chunks
#		[useforretrain]: False

@app.route('/crossvalidate', methods = ['POST'])
def crossValidate():
	from sklearn.feature_extraction.text import CountVectorizer
	if request.method == 'POST':
		# load request data
		data    = request.get_json(force=True)
		path    = data['path']
		n       = data['n']
		n       = int(n)

		useforretrain = False
		username = 'R-' + os.path.split(path)[1]
		userid = fetchUserId(app, username)

		# 1. split the textfile into n chunks
		print("Read and split the text into {} parts.".format(n))		
		with open(path, mode ='r') as f:
			reference_text = f.read()
			reference_text = reference_text.replace('\n','')
			
			text_parts = split_text(reference_text, n)

		# 2. create n equal-sized texts by leaving out one chunk each

		for i in range(n):
			ind_list = list(range(n))
			ind_list.pop(i)
			chunk = ''
			for j in ind_list:
				chunk += text_parts[j]
			chunks.append(chunk + " ")

		# 3. create .txt files for all those chunks in a special folder
		for i in range(len(chunks)):
			filename  = userid+'_chunk_{}_{}.txt'.format(i+1,n)
			chunk_dir = './ServerFeatures/Userdata/Reference_User_Histories/chunks/'
			filepath  = chunk_dir + filename
			with open(filepath, mode = 'w') as f:
				f.write(chunks[i])
			

		# 4. run the reference-user procedure for all such chunks (.txt files) WITHOUT changing the BoWHistory TABLE


		# set path to the folder with all extracted chat histories
		dir_ref_histories 	= "./ServerFeatures/Userdata/Reference_User_Histories"
		# minimum amount of bytes a reference chatHistory has to contain in order to be considered for training
		min_bytes               = 1000

		# extract the request body
		referencedetails    = request.get_json(force=True)
		reference_file_path = referencedetails['path']

		# start creating reference users  
		print("Create reference users for a user's text chunks...")
		dir_chunk_histories = './ServerFeatures/Userdata/Reference_User_Histories/chunks/'

		# run the process pipeline on all referenceusers (*.TXT files) in dir_chunk_histories that have more than <min_bytes> text
		# with 'crossvalidate == True'!!!
		for root, dirs, files in os.walk(dir_chunk_histories):
			for file_ in files:
				# set reference username
				reference_username = 'R-' + file_
				print("Reference file: ", file_)
				# if 'file_' is a text-file and contains at least <min_bytes> bytes...
				tooShort = os.path.getsize(os.path.join(root, file_)) < min_bytes
				isTxt    = file_.endswith(".txt")
				if not tooShort and isTxt:
					# Create a 'reference' user
					referenceuserid = createNewUser(app, reference_username, reference_username, '', 'chunk')
					# if the referenceuserid has been registered before
					if referenceuserid == "-1":
						referenceuserid = fetchUserId(app, reference_username)
				
					print("The userid for the reference file " + file_ + " is: " + referenceuserid)
					# Start the Process Pipeline in order to fill in BoW and TFIDF values in the DB
					# NOTE: starting the processPipeline is not recommendable for many small reference files!
					refchatHistoryPath  = os.path.join(root, file_)
					processPipeline(app, referenceuserid, refchatHistoryPath, useforretrain, crossvalidate = True)
				elif not tooShort:
					print("The reference file is not a txt-file and is thus skipped.")
				elif isTxt:
					print("The reference file is too short and is thus skipped.")
				print(" ")

	# the chunk users are now ready for comparison.
	return "1"


if __name__ == "__main__":
	app.run(host='0.0.0.0')
