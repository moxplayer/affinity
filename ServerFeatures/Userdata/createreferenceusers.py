import xml.etree.ElementTree as ET
import os
import sys

# extract user-specific chat messages from a text corpus specified in <reference_file_path> and store them
# in the folder <dir_ref_histories>
# test with reference_file_path = './ServerFeatures/Userdata/smsCorpus_en_2015.03.09_all.xml'

def referenceUserCreation(app, reference_file_path, dir_ref_histories):
	# get tree of XML file containing all messages
	print("Parse the file: ",reference_file_path)
	tree = ET.parse(reference_file_path) 
	root = tree.getroot()

	# keep track of the user IDs in the XML file
	known_users = []

	# count number of all messages included
	number_of_messages = 0

	# create folder with all extracted chat histories if not yet present
	if not os.path.exists(dir_ref_histories):
		os.makedirs(dir_ref_histories)
	print("Start reading the parsed messages")

	# remember all seen users in order to append messages to existing chatHistories instead of creating a new chatHistory
	known_users = set()

	# iterate through all messages
	for child in root:  
    	
		# extract message text 
		message_text = child[0].text
		# [X] : cast message text to unicode
		if type(message_text) == str:
			message_text = message_text.decode('utf-8')

		# extract user id from message
		user_id      = child[1][2][0].text

		# set user-specific file path
		messagefile = dir_ref_histories + "/" + user_id + ".txt"

		# if user_id has not been seen before, create empty file the first time a user is seen
		if user_id not in known_users:
			with open(messagefile, "w") as file: 
				pass

		# remember user_id
		known_users.add(user_id)

		# append chat message ('utf-8' encoded) to the user chatHistory of <userid>
		with open(messagefile,"a") as file: 
			# in python2 str is bytes! and therefore, if the double HEX is >= 128 lacks decoding properties (into a glyph/code point)
			# if type == str
			# if type == unicode (unicode cannot be decoded, because it is not an encoding : glyph/code point --> byte sequence
			# if unicode --> encode to utf-8 bytes
			if type(message_text) == unicode:
				file.write((message_text + " ").encode('utf-8'))
			# if str, message_text is already a bytes object and hopefully already 'utf-8' encoded, if not, this has to be changed
			# NOTE that due to [X], the else case will not happen
			elif type(message_text) == str:
				file.write((message_text.decode('utf-8') + " ").encode('utf-8'))


	print("Number of users: "    + str(len(known_users)))
	print("Number of messages: " + str(len(root)))

	return "1"


