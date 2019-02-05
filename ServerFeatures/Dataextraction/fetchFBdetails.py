from flask import Flask,request,jsonify
from fbchat import Client
from fbchat.models import *
from subprocess import *
import os,json,sys

sys.path.append('./ServerFeatures/Usermanagement')
from dbdetails import createUserDetail, populateBoWReferenceCorpus, populateUsersBoW, fetchdistinctUsercount, fetchDocumentcount, fetchUserBoW, fetchUserName, checkValidUser, fetchProcessStatus, fetchTimestamp, updateTFIDF, fetchTopNtfidf, updateProcessStatus, updateMessageTimestamp, updateFBEmailid
sys.path.append('./ServerFeatures/Preprocessing')
from userBoWgeneration import generateUserBoW

sys.path.append('./ServerFeatures/util')
from utilities import write_log

import subprocess
import time
from flask import session
#import latentfeatures

###################################################################################################################################################
#Code peforms
#	Fetches the FB Details for "id" and generates the chat history file
###################################################################################################################################################

#
# 1. Login to FB with FB-credentials      --> update to process status '2'
# 2. Fetch chat-interlocutors of <userid> --> update to process status '3'
# 3. Fetch chatHistories for all interlocutors of <userid>
# 4. Extract all conversations which have not been fetched before and assign them a 'conversation language' (most frequently predicted language) with the fasttext library 		
# 5. Filter empty conversations
# 6. Build separate chat histories for <userid> for each conversation language



# NOTE: FB may initialize a conversation thread between two befriended users even if no message has been sent by either one of them! (empty conversation)


def fetchFBInformation(app, userid, fbemailid, fbpassword):
	####
	# 0. Set base variables
	############
	messagefile_complete_name     = "all_messages_"
	messagefile_complete_filetype = ".txt"

	############
	# 1. Login into the FB account	
	###############################
	try:    # define a FB connector
		client = Client(fbemailid, fbpassword)
		# Update FBemailid for the <userid> 	
		updateFBEmailid(app, int(userid), fbemailid)
		# Update the process status to '2' for successful login
		updateProcessStatus(app, int(userid), '2')	
	except Exception as wrongLoginCredentials:	
		print("Wrong User name or password")
		return(-1)
	
	#########
	# 2. Fetch chat-interlocutors of <userid>
	##############################################
	interlocutors   = client.fetchAllUsers()	
	print("Number of Users: " + str(len(users)))
	
	# Update the process status to '3' for having fetched FB chat data
	updateProcessStatus(app, int(userid), '3')
	

	#########
	# 3. Fetch chatHistories for all interlocutors of <userid> that happen after <maxTimeStamp>; if <maxTimeStamp> is "1" : fetch all
	##################################################################################################################################
	# initialize a list for all conversation threads of <userid>
	conversations      = []
	# initialize a list of interlocutor uids with whom <userid> has more than 1 message exchanged
	interlocutor_uids  = []
	# fetch the timestamp when the last FB fetch happened and cast it to <int>-type
	maxTimestampDB     = fetchTimestamp(app, int(userid))
	maxTimestampDB     = int(maxTimestampDB);
	
	# Fetch messages <userid> chats with and append it to <conversations>
	for interlocutor in interlocutors:
		try:    # try to fetch the last 1000 messages from the conversation between <userid> and <interlocutor>
			threadMessages = client.fetchThreadMessages(thread_id   =    interlocutor.uid, limit = 10000)
			messageCount   = len(threadMessages)
			# if more than one message has been exchanged ...
			if (len(threadMessages)>1) :
				# remember thread messages in the <conversations>-list
				conversations.append(client.fetchThreadMessages(thread_id = interlocutor.uid))
				# remember the interlocutor_uid
				interlocutor_uids.append(interlocutor.uid)
		except fetchFBchatException:
			#print("## Error ##   ","UID: ",user.uid, "  Name: ", user.first_name, " ", user.last_name, "# of msgs: ")
			pass	# Error conversations that contain no messages (i.e. conversations started automatically by messenger after becoming friends on FB
	print("Fetched  ", "conversations: " + str(len(conversations)), "  userlist length: "+str(len(userlist)))

	##########
	# 4. Extract all non-empty conversations which have not been fetched before
	##########################################################################
	write_log("Threads Fetched. Start language classfication.")

	# set paths

	## path that will contain all messages as a single file in JSON format
	#messagefolder_json     = "./Messages_json/"
	#
	## path that will contain all messages as a single file in plain text format
	#messagefolder_plain    = "./Messages_plain/"

	# path that will contain all messages the user has ever sent in one single file per language used
	messagefolder_complete = "./ServerFeatures/Userdata/Messages_complete/" + str(userid) + "/"
	# file-name to store a message temporarily for language classification
	message_tempfile_path  = "./ServerFeatures/Userdata/Messages_complete/" + str(uderid) + "/tempfile.txt"
	# initialize a list for the languages used in <userid>'s conversations
	languages      = []
	# initialize (WRITE WHAT)
	language_count = []
	# initialize a counting variable for the considered conversations
	interlocutor_number    = 0
	# return value of the function (all English messages in one string)  # VERIFY - probably the timestamps for the conversations
	max_message_timestamps  = []

	# create message folders if not existing yet
	#if not os.path.exists(messagefolder_json):
	#	os.makedirs(messagefolder_json)
	#if not os.path.exists(messagefolder_plain):
	#	os.makedirs(messagefolder_plain)
	if not os.path.exists(messagefolder_complete):
		os.makedirs(messagefolder_complete)


	# clear all message files if existent # TODO: this will have to be removed
	# otherwise, running the script multiple times will cause messages to appear multiple times in the files
	# TODO: change later for updating
	#for root, dirs, files in os.walk(messagefolder_json):
	#	for file_ in files:
	#		if file_.endswith(".txt"):
	#			os.remove(os.path.join(root, file_))
	#for root, dirs, files in os.walk(messagefolder_plain):
	#	for file_ in files:
	#		if file_.endswith(".txt"):
	#			os.remove(os.path.join(root, file_))

	# collect all *.txt files in <messagefolder_complete>
	# (only relevant if the user has stored FB messages in the past
	for root, dirs, files in os.walk(messagefolder_complete):
		for file_ in files:
			if file_.endswith(".txt"):
				os.remove(os.path.join(root, file_))

	# for all conversations (with more than one message)
	for conversation in conversations:
		# set sub directory paths for each chat partner in the
		#userdir_json = messagefolder_json + "/" + str(userlist[user_number])
		#userdir_plain = messagefolder_plain + "/" + str(userlist[user_number])
		#
		## make directories if not yet existent
		#if not os.path.exists(userdir_json):
		#	os.makedirs(userdir_json)
		#if not os.path.exists(userdir_plain):
		#	os.makedirs(userdir_plain)##

		# remember all thread messages, their predicted language, and the number of considered messages of the conversation
		conversation_messages          = []
		conversation_message_languages = []
		conversation_message_counter   = 0
		text_returned_en               = ""
		conversation_empty = True
		# for all messages in the conversation
		for message in conversation:
			# get message text, author, timestamp
			message_text      = message.text
			message_author    = message.author
			message_timestamp = message.timestamp
			# encode <message_text> to utf-8
			if type(message_text) == 'unicode':
				message_text = message_text.encode('utf-8')
			elif type(message_text) == str:
				message_text.decode('utf-8').encode('utf-8')
			# remember the timestamp of the message
			max_message_timestamps.append(message_timestamp)

			# (e.g. exclude automatically generated call messages)
			# if <message_text> is not empty 
			# AND
			# the message has not been fetched in the past (maxTimestampDB indicates the most recent point in time <userid> fetched FB messages
			# AND
			# if the message was sent by <userid> and not by <interlocutor>
			message_not_empty          = (message_text != None)
			message_sent_by_userid     = (message_author == client.uid)
			message_not_fetched_before = (int(message_timestamp) > int(maxTimestampDB))

			if ( message_not_empty & message_sent_by_userid & message_not_fetched_before ) :
				conversation_empty = False
				# set message file paths for the json and text message files
				#messagedir_plain = userdir_plain + "/" + message_timestamp + ".txt"
				#messagedir_json = userdir_json + "/" + message_timestamp + ".txt"

				# remove newlines (\n) and carriage returns (\r) (for language classification - otherwise this would produce multiple outputs)
				message_text = message_text.replace('\n', ' ').replace('\r', '')

				## write message json file
				#message_dictionary = {'timestamp': message_timestamp, 'author_id': message_author, 'text': message_text}
				#with open(messagedir_json, "w") as outfile:
				#	json.dump(message_dictionary, outfile)
				#	outfile.close()

				# write message text file
				#with open(messagedir_plain, "w") as outfile:
				#	outfile.write(message_text)
				#	outfile.close()

				# put <message_text> into a temporary file for languge prediction
				with open(message_tempfile_path, "w") as tempfile:
					tempfile.write(message_text)

				# try to predict the message's language with the original fasttext algorithm
				try:
					message_language = check_output(['./ServerFeatures/Wordembedding/fastText-original/fasttext', 'predict', './ServerFeatures/Preprocessing/Languageprediction/pretrainedmodel.bin', message_tempfile_path])
					# remove newlines (\n) from <message_language>
					message_language = str(message_language).replace('\n', '')
				except CalledProcessError as e:
					raise RuntimeError(
						"command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

				# keep track of every language prediction for the conversation and count the messages in the conversation
				# e.g.
				# conversation_messages          = [msg1, msg2, msg3]
				# conversation_message_languages = ['__label__en', '__label__de', '__label__en']
				conversation_messages.append(message_text)
				conversation_message_languages.append(message_language)
				conversation_message_counter += 1
		####
		# 5. Filter out empty conversations
		########################################3
		if conversation_empty:
			continue # with the next iteration of the loop
		""" # this code only focuses on English conversations
		# extract the languages used in the conversation and their respective counts
		conversation_message_languages_and_count = [ ( conversation_messages_languages.count(language), language) for language in set(conversation_message_languages) ]
		
		# pick the majority language, max finds the maximum in the 0-th elements of the duples
		majority_language = max(conversation_message_languages_and_count)[1]
		
		"""
		####
		# 6. Build separate chat histories for <userid> for each conversation language
		############################################################################
		conversation_languages      = []
		conversation_language_count = []
		# for all recorded conversation languages
		for message_language in conversation_message_languages:
			message_language_known      = False
			conversation_language_index = 0
			# for 
			for conversation_language in conversation_languages:
				if conversation_language == message_language:
					conversation_language_count[conversation_language_index] = conversation_language_count[
					conversation_language_index] + 1
					message_language_known = True
					break;
				conversation_language_index = conversation_language_index + 1
			if (message_language_known == False):
				conversation_languages.append(message_language)
				conversation_language_count.append(1)

		# retrieve final conversation language for the whole conversation
		max_language_count = 0
		conversation_language = ''
		conversation_language_index = 0
		for x in conversation_languages:
			if (conversation_language_count[conversation_language_index] > max_language_count):
				max_language_count = conversation_language_count[conversation_language_index]
				conversation_language = conversation_languages[conversation_language_index]
			conversation_language_index = conversation_language_index + 1
		#print("Final conversation language: ", conversation_language)

		
		# add conversation language use to the global language use of the user
		language_index = 0
		language_known = False
		for language in languages:
			if language == conversation_language:
				language_count[language_index] = language_count[language_index] + len(conversation_messages)
				language_known = True
				break;
		if (language_known == False):
			languages.append(conversation_language)
			language_count.append(len(conversation_messages))


		# append all conversation messages to the respective complete history with regard to the conversation language
		# format e.g.: "./ServerFeatures/Userdata/Messages_complete/testid/all_messages___label__en.txt"
		complete_history_path         = messagefolder_complete + messagefile_complete_name + str(userid) + conversation_language + messagefile_complete_filetype
		# the conversation messages are encoded in 'utf-8', see above
		with open(complete_history_path, "a+") as complete_file:
			for conversation_message in conversation_messages:
				append_message = (conversation_message.decode('utf-8') + " ").encode('utf-8')
				complete_file.write(append_message)

				# append message to the return string if it is english // TODO: potentially change later
				if (conversation_language == '__label__en'):
					text_returned_en = text_returned_en + conversation_message + " "

		interlocutor_number += 1
		# print("Conversation languages: ",conversation_languages)
		# print("Conversation language count: ",conversation_language_count)

		print("Overall languages used: ",      languages)
		print("Overall languages used count:", language_count)

	
	# delete tempfile
	if(os.path.isfile(message_tempfile_path)):
		os.remove(message_tempfile_path)

	# Update the process status to '4'
	updateProcessStatus(app,int(userid),'4')

	######
	# 7. Extract language usage statistics of <userid>
	##################################
	# for testing only
	# get language statistics
	msg_count_en    = 0
	msg_count_total = 0
	index           = 0

	for language in languages:
		if(language == '__label__en'):
			msg_count_en = msg_count_en + language_count[index]
		msg_count_total = msg_count_total + language_count[index]
		index = index + 1

		
	write_log("Finished language classification")

	######
	# 8. Update <maxTimeStamp> in the userinfo TABLE if necessary
	####################################################
	complete_EN_history_path = messagefolder_complete + messagefile_complete_name + str(userid) + '__label__en' + messagefile_complete_filetype
	# if an English chat history path exists
	EN_chatHistory_exists = os.path.isfile(complete_EN_history_path)
	if EN_chatHistory_exists:
		new_non_empty_conversations_fetched = len(max_message_timestamps) > 0
		if new_non_empty_conversations_fetched:
			print("Update maxTimeStamp in the userinfo TABLE")		
			word_count_en = len(text_returned_en.split())
			write_log("Fetched {} Facebook messages. Number of english classified messages: {}. Number of english words: {}".format(msg_count_total, msg_count_en, word_count_en))
			# Update maxTimeStamp in the userinfo TABLE
			status = updateMessageTimestamp(app, int(userid), max(max_message_timestamps)) 
		# return the chat history path for English conversations
		return complete_EN_history_path

	# return "-1" if no changes were made
	return "-1"
	
