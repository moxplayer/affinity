from flaskext.mysql import MySQL
import os,json,sys,math
###################################################################################################################################################
#Code performs
#	Fetches performs DB's activity
###################################################################################################################################################

# Connect to MySQL as root-user to the table 'FBUserData'
def connect_mysql(app):
	# configure MySQL
	mysql = MySQL()
	app.config['MYSQL_DATABASE_USER']     = 'root'
	app.config['MYSQL_DATABASE_PASSWORD'] = 'toor'        # HERE the password has to be different (depending on the setup)
	app.config['MYSQL_DATABASE_DB']       = 'FBUserData'
	app.config['MYSQL_DATABASE_HOST']     = 'localhost'
	mysql.init_app(app)

	# Connect to the DB
	conn   = mysql.connect()
	cursor = conn.cursor()
	return conn, cursor



# input [username, emailid, password]; output: correct userid
# error codes:  "-1" : emailid already exists in the DB
#               "-2" : username already exists in the DB
#               "-3" : writing on DB fails
def createUserDetail(app, username, emailid, password, usertype):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	# Check if the emailaddress is already registered
	print("Try to create new user...")	
	try:
		cursor.execute("SELECT id FROM userinfo where useremailid= %s", (emailid))
		data = cursor.fetchall()
		data = data[0]                                     # breaks if no data has been fetched <--> data == ()
		print("The given emailid is already registered!")
		print("It's corresponding id is: ", data[0])
		conn.close()
		return ("-1")
	# Check if the username has been registered before
	except:
		try:	
			cursor.execute("SELECT id FROM userinfo where username= %s", (username))
			data = cursor.fetchall()
			data = data[0]                                     # breaks if no data has been fetched <--> data == ()
			print("The given username is already registered!")
			print("It's corresponding id is: ", data)# fetchUserId(app, username))
			conn.close()
			return ("-2")
		# else create a new user
		except Exception as userNotExits:
			try:	
				cursor.execute("INSERT INTO userinfo(usertype, useremailid, username, password, status, maxtimestamp) VALUES(%s,%s,%s,%s,%s,%s)",(usertype, emailid, username, password, '1', '1'))
				conn.commit()
				# fetch all user id's with the same emailid
				cursor.execute("SELECT id FROM userinfo WHERE useremailid= %s", (emailid))
				data   = cursor.fetchall()
				# extract fetched data
				userids = extract_fetched_data(data, 1)
				userid  = userids[0]
				print("Success! The account's user id is : ", userid)
				conn.close()
				return str(userid)
			except Exception as userCreateException: 
				print("Exception while creating the User details")
				conn.close()
				return ("-3")

# not in use currently
def populateBoWReferenceCorpus(app,document_names,featurenames,X_array):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)


	#Populate BoW details for each document
	for docname, Xarray in zip(document_names,X_array):
		print("Inserting records for the Document", docname)
		try:
			for term,Xvalarray in zip(featurenames,Xarray):
				cursor.execute("INSERT INTO userBoW(id,feature_names,occurrences) VALUES(%s,%s,%s)",('R-'+docname,term.encode("utf-8"),int(Xvalarray)))
				
		except Exception as BoWInsertException:
			print("Exception at BoW inserting")
			return ("F")
		conn.commit()
	#Populate BoW History
	try:
		cursor.execute("SELECT feature_names,COUNT(distinct id) FROM userBoW GROUP BY feature_names")
		data = cursor.fetchall()
		print("Gathering details")
		for values in data:
			cursor.execute("INSERT INTO BoWHistory(feature_names,no_occurrences) VALUES(%s,%s)",(values[0].encode("utf-8"),values[1]))
		conn.commit()
	except Exception as BoWHistoryException:
		print("Exception at BoW History population")	
	conn.close()
	return ("S")


# MySQL queried data looks as such : ((attr1, attr2), (attr1, attr2),)  <fetched_data>
# this function outputs: [ [attr1, attr1], [attr2, attr2]]
# num_attr : number of attributes fetched 
# NOTE: num_attr might not be zero despite the query being empty '()'
def extract_fetched_data(fetched_data, num_attr):
	# extract attributes
	attributes = []
	for i in xrange(num_attr):
		attribute = [el[i] for el in fetched_data]
		attributes.append(attribute)
	if num_attr == 1:
		return attributes[0]
	return attributes


# 'occurences'    : counts the occurences of a term used by a user	
# 'no_occurences' : counts the unique ids who used a certain term
# 'featurename'   : vocabulary of words             e.g. ['I','am'] --> text contains one 'I' and two 'am'
# 'X_array'       : array of word occurrence counts e.g. [1,2]


### THIS IS STILL IN THE MAKING AND TRYING TO SPEED UP THE MYSQL INSERTIONS
def test(app, userid, featurenames, X_array):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	# steps 1. - 4.
	# 1. update the occurrence and featurename in the userBoW TABLE
	# NOTE: - featurenames are of type 'unicode'
	#       - fetching feature names from the MySQL database, they are of python type 'unicode'

	## in this test we use pandas in order to speed up the process
	# featurenames, X_array --> pandas.DataFrame
	# fetch featurenames and occurrences from <userid>
	# --> pandas.DataFrame
	# join dataframes
	# add columns of the joined dataframe
	# input all into the DB (using ON DUPLICATE KEY UPDATE)

	# fetch userBoW info of <userid>
	cursor.execute("SELECT occurrences, feature_names FROM userBoW WHERE id=%s", (int(userid), featurename))
	fetched_data = curosr.fetchall()
	recorded_occurrences, recorded_featurenames = extract_fetched_data(fetched_data, 2)
	recorded_df = pd.DataFrame(recorded_occurrences, index = recorded_featurenames)

	# get a pandas DataFrame from the new BoW info 
	new_df = pd.DataFrame(list(X_array), index = featurenames)

	# join the dataframes
	joined_df = recorded_df.join(new_df, lsuffix= '_recorded', rsuffix = '_new', how= 'outer') 
	joined_df = joind_df.fillna(0)
	updated_occurrences = list(joined_df[:,'0_recorded'] + joined_df[:,'0_new'])
	updated_featurenames= list(joined_df.index)

	# insert into DB with replacement if a featurename had been recorded
	for updated_occurrence, updated_featurename in zip(updated_occurrences, updated_featurenames):
		cursor.execute("INSERT INTO userBoW(id, feature_names , occurrences) VALUES (%s,%s,%s)", (int(userid), updated_featurename, int(updated_occurrence)))

		cursor.execute("SELECT occurrences, feature_names FROM userBoW WHERE id=%s AND feature_names COLLATE utf8mb4_bin=%s", (int(userid), featurename))
		fetched_data                                = cursor.fetchall()
		recorded_occurrences, recorded_featurenames = extract_fetched_data(fetched_data, 2)
		fetched_row_count                           = cursor.rowcount
		# 2. if <featurename> has never been recorded for <userid>
		if   fetched_row_count == 0: 
			cursor.execute("INSERT INTO userBoW(id, feature_names , occurrences) VALUES (%s,%s,%s)", (int(userid), featurename, int(occurrence)))
		# 3. if <featurename> has been recorded once
		elif fetched_row_count == 1: 
			recorded_occurrence  = recorded_occurrences[0]
			recorded_featurename = recorded_featurenames[0]
			cursor.execute("UPDATE userBoW SET occurrences=%s WHERE id=%s AND feature_names=%s", (int(recorded_occurrence + occurrence), int(userid), featurename))
		# 4. if <featurename> has been recorded more than once: TODO: merge the records and update with <occurrence>
		else:
			pass
	conn.commit()



# Populate BoW details for each document
# populate : 
# 	1. fetch bag-of-words information from userBoW' info for <userid>
#	2. if <userid> has not used a word in <featurenames> in the past
#		- insert the word into userBoW
#	3. elif it has been recorded once before
#		- add the new occurrence count to the recorded occurrence count
#	4. elif it has been recorded more than once before TODO
#		- merge the recorded entries
#		- add the new occurrence count to the recorded occurrence count
#	ONLY run, if crossvalidate = False: (the text statistics will not be published to the public)
#		5. Initialize newly-seen words in the BoWHistory TABLE
#		6. Update all words in the BoWHistory TABLE

def populateUsersBoW(app, userid, featurenames, X_array, crossvalidate = False):


	print('Update {} featurenames in the userBoW TABLE...'.format(str(len(featurenames))))
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	# steps 1. - 4.
	# 1. update the occurrence and featurename in the userBoW TABLE
	# NOTE: - featurenames are of type 'unicode'
	#       - fetching feature names from the MySQL database, they are of python type 'unicode'
	for occurrence, featurename in zip(X_array, featurenames):
		# recorded* : information from MySQL DB
		# *         : information to update the MySQL DB with                                      
		### NOTE    : use 'feature_names COLLATE ut8mb4_bin=%s' instead of 'feature_names=%s' in order to circumvent collation --> slow
		cursor.execute("SELECT occurrences, feature_names FROM userBoW WHERE id=%s AND feature_names COLLATE utf8mb4_bin=%s", (int(userid), featurename))
		fetched_data                                = cursor.fetchall()
		recorded_occurrences, recorded_featurenames = extract_fetched_data(fetched_data, 2)
		fetched_row_count                           = cursor.rowcount
		# 2. if <featurename> has never been recorded for <userid>
		if   fetched_row_count == 0: 
			cursor.execute("INSERT INTO userBoW(id, feature_names , occurrences) VALUES (%s,%s,%s)", (int(userid), featurename, int(occurrence)))
		# 3. if <featurename> has been recorded once
		elif fetched_row_count == 1: 
			recorded_occurrence  = recorded_occurrences[0]
			recorded_featurename = recorded_featurenames[0]
			cursor.execute("UPDATE userBoW SET occurrences=%s WHERE id=%s AND feature_names=%s", (int(recorded_occurrence + occurrence), int(userid), featurename))
		# 4. if <featurename> has been recorded more than once: TODO: merge the records and update with <occurrence>
		else:
			pass
	conn.commit()


	#####################################
	# 5. Initialize newly-seen words in the BoWHistory TABLE
	# this has to be done BEFORE updating the existing <no_occurrences> for else fetching newly used words  will not be updated immediately in the BoWHistory TABLE
	# SKIP THIS IF crossvalidate = True
	if crossvalidate == False:

		# select distinct <feature_names> from the userBoW TABLE of <userid> which have not been filed before
		cursor.execute("SELECT DISTINCT feature_names FROM userBoW WHERE id= %s AND feature_names NOT IN (SELECT DISTINCT feature_names FROM BoWHistory)",userid)
		fetched_data        = cursor.fetchall()
		update_featurenames = extract_fetched_data(fetched_data, 1)
		print("Insert newly-seen featurenames into the BoWHistory TABLE")
		print("Update featurenames:", update_featurenames)
	
		# insert them into the BoWHistory TABLE
		for update_featurename in update_featurenames:
			cursor.execute("INSERT INTO BoWHistory(feature_names, no_occurrences) VALUES(%s,%s)",(update_featurename, 1))

		conn.commit()	


	#####################################
	# 6. Update existing <no_occurrences> in the BoWHistory TABLE
	# NOTE: <no_occurrences> is equivalent to document-frequency, where a user's chat history is a document
	# SKIP THIS IF crossvalidate = True
	if crossvalidate == False:

		# select <no_occurences> used by <userid>
		cursor.execute("SELECT DISTINCT no_occurrences, feature_names FROM BoWHistory WHERE feature_names IN (SELECT DISTINCT feature_names FROM userBoW WHERE id= %s)",userid)
		fetched_data                                   = cursor.fetchall()
		recorded_no_occurrences, recorded_featurenames = extract_fetched_data(fetched_data, 2)
		print('Update no_occurrences in the BoWHistory table.')
		# <recorded_no_occurrences>, <recorded_featurenames> have to be updated
		for recorded_no_occurrence, recorded_featurename in zip(recorded_no_occurrences, recorded_featurenames):
			# an SQL query with ... COUNT(DISTINCT id) ... somehow does not work
			cursor.execute("SELECT COUNT(*) FROM ( SELECT DISTINCT id FROM  userBoW WHERE feature_names=%s) AS CountTable", (recorded_featurename))
			countdata        = cursor.fetchall()
			new_no_occurrence = extract_fetched_data(countdata, 1)[0]
			cursor.execute("UPDATE BoWHistory SET no_occurrences=%s WHERE feature_names=%s ", (new_no_occurrence, recorded_featurename))	
		conn.commit()


	# close MySQL connection
	conn.close()
	# report success
	return ("1")


# fetch the number of users ready to compare (status = '8')
def fetchdistinctUsercount(app):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	cursor.execute("SELECT distinct id from userinfo where status='8'")
	data = cursor.fetchall()
	conn.close()
	#print("Total number of distinct documents: ",int(usercount))
	return data

# fetch the number of distinct registered <userid>s
# NOTE: #<userid>s = #documents
def fetchDocumentcount(app):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	cursor.execute("SELECT COUNT( DISTINCT id) FROM userBoW")
	fetched_data = cursor.fetchall()
	try:
		doccount     = extract_fetched_data(fetched_data,1)[0]
	except:
		doccount     = 0

	conn.close()
	return int(doccount)

# Fetch the BoW entries (vocab_words, term_counts, document_counts, user_counts, document_frequencies) of <userid> for
# min_df : <float> between 0.0 and 1.0 specifying the minimal percentage over all documents in which a term occurs
# max_df : <float> between 0.0 and 1.0 specifting the minimal percentage over all documents in which a term occurs
def fetchUserBoW(app, userid, min_df = 0.0, max_df = 1.0):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	userBoW     = []
	doccount = fetchDocumentcount(app)
	# ub: userBoW
	# bh: BoWHistory
	try:
		SQL_query  =  ""#  count(distinct ub.id), 
		# select vocabulary words, their term counts, their document counts, number of <userid>s which used at least one word in the vocabulary, their document frequency
		SQL_query  += " SELECT   ub.feature_names, ub.occurrences, bh.no_occurrences, COUNT(DISTINCT ub.id),  (bh.no_occurrences/{}) FROM BoWHistory bh, userBoW ub ".format(doccount)
		# that <userid> used
		SQL_query  += " WHERE    bh.feature_names = ub.feature_names "
		SQL_query  += " AND      ub.id = {} ".format(userid)
		# such that their document frequencies are between <min_df> and <max_df>
		SQL_query  += " AND      (bh.no_occurrences/{}) BETWEEN {} AND {} ".format(doccount, str(min_df), str(max_df))
		# group the results by vocabulary words
		SQL_query  += " GROUP BY ub.feature_names, ub.occurrences, bh.no_occurrences "

		cursor.execute(SQL_query)
		fetched_data                                                                 = cursor.fetchall()

		vocab_words, term_counts, document_counts, user_counts, document_frequencies = extract_fetched_data(fetched_data, 5)
		#		 

	except Exception as FetchBowException:
		print("At FetchBoWException")
		return("-1")
	conn.close()
	return(vocab_words, term_counts, document_counts, user_counts, document_frequencies)


def fetchUserId(app, username):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Received username: ", username)
		cursor.execute("SELECT id from userinfo where username= %s",(username))
		data = cursor.fetchall()

		ids  = extract_fetched_data(data, 1)

		# if exactly one userid has been found, return it
		if len(ids) == 1:
			user_id = ids[0]
		# if more than one userid have been found, return "-1"
		elif len(ids) > 1:
			print("The requested userid for the username {} has already been registered.".format(username))
			user_id = "-1"
		# if none has been registered, return "0"
		elif len(ids) == 0:
			print("The requested username has not been registered.")
			user_id = "-2"

		conn.close()
		return str(user_id)

	except	Exception as statusNotFound:	
		print("Exception while fetching username for the userid")
		return ("-3")



def fetchUserName(app,userid):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Received User id: ",userid)
		cursor.execute("SELECT username from userinfo where id= %s",(userid))
		data = cursor.fetchall()
		for values in data:
			username=values[0]
			print("Username in DB is: ",username)
		conn.close()
		return(username)
	except	Exception as statusNotFound:	
		print("Exception while fetching username for the userid")
		return ("-1")

def checkValidUser(app,emailid,password):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	# Check User already existing or not	
	print("Try to login...")
	try:
		cursor.execute("SELECT id,username FROM userinfo WHERE useremailid=%s AND password=%s",(emailid,password))
		data = cursor.fetchall()
		#for values in data:
		#	username = values[1]
		#	userid   = values[0]		
		username = data[1]
		userid   = data[0]
		print("SUCCESS! ", username," with userid ", userid, " is now logged in.")
		conn.close()
		return (username, userid)
	except Exception as userNotExists:
		print("Invalid credentials")
		return("","-1")

# Fetch the process status code of <userid>
def fetchProcessStatus(app, userid):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Fetch process status of userid: ",userid)
		cursor.execute("SELECT status FROM userinfo WHERE id= %s", ( userid)) # add "\'" if you encounter for example ".txt" userids
		data = cursor.fetchall()
		status_s = extract_fetched_data(data, 1)
		if len(status_s)   == 1:
			status = status_s[0]
			print("The process status is {}.".format(status))
		elif len(status_s) == 0:
			status = "-2"
			print("No status found for userid {}.".format(userid))
		elif len(status_s) >  1:
			status = "-3"
			print("More than one status found for userid {}".format(userid))
		conn.close()
		return status
	except	Exception as statusNotFound:	
		print("Exception while fetching status for the userid")
		return ("-1")
	
# Fetch the timestamp of <userid>
def fetchTimestamp(app, userid):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Received User id: ", userid)
		cursor.execute("SELECT maxtimestamp from userinfo where id= %s",(userid))
		data = cursor.fetchall()
		for values in data:
			print("Max-Timestamp Fetched from DB is: ",values[0])
			maxval=values[0]
		conn.close()
		return(maxval)
	except	Exception as statusNotFound:	
		print("Exception while fetching max-timestamp for the userid")
		return ("-1")
	
# Update TFIDF values in the userBoW TABLE by <userid>
def updateTFIDF(app, userid, featurenames, tfidf_vector):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	# Update TFIDF values in the userBoW TABLE by <userid>
	try:
		for featurename, tfidf in zip(featurenames, tfidf_vector):
			cursor.execute("UPDATE userBoW SET tfidf=%s WHERE id=%s AND feature_names=%s", (tfidf, userid, featurename))
		response_code = "1"
	except Exception as tfidfNotUpdated:
		print("Error while updating tfidf.")
		response_code = "-1"

	conn.commit()	
	conn.close()

	return response_code

# Fetch an ordered vector of vocabulary words (featurenames) with descending tfidf values of <userid>
def fetchTopNtfidf(app, userid, N):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)
	# fetch featurenames corresponding to the top N tfidf values of <userid>
	cursor.execute("SELECT feature_names, occurrences FROM userBoW WHERE id=%s ORDER BY tfidf DESC LIMIT %s", (userid, N))
	fetched_data              = cursor.fetchall()
	featurenames, occurrences = extract_fetched_data(fetched_data, 2)
	print("Fetched the top N = ", N," tfidf valued terms by userid : ", userid)
	# fetch the process status
	process_status = int(fetchProcessStatus(app, userid))
	# if the process status is smaller or equal 7
	if process_status <= 7:
		# Update the process status to '7'
		updateProcessStatus(app, int(userid), '7')

	conn.close()

	return featurenames, occurrences

# Update Process Status of <userid> in the userinfo TABLE
def updateProcessStatus(app, userid, status):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		cursor.execute("UPDATE userinfo SET status=%s WHERE id=%s",(status,userid))
		print("Status for the userid : ",userid," is updated to : ",status)
		conn.commit()
		conn.close()
		return ("0")
	except	Exception as statusNotUpdated:	
		print("Exception while updating status for the userid")
		return ("-1")
	
# Update <maxTimeStamp> by <timestamp> for <userid> in the userinfo TABLE
def updateMessageTimestamp(app, userid, timestamp):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Received User id for Timestamp update: ",userid)
		cursor.execute("UPDATE userinfo SET maxtimestamp=%s WHERE id=%s",(timestamp,userid))
		print("Max-Timestamp for the: ",userid," is updated as: ",timestamp)
		conn.commit()
		conn.close()
		return ("0")
	except	Exception as timestampNotUpdated:	
		print("Exception while updating timestamp for the userid")
		return ("-1")
	
# add a fbemailid to the userinfo TABLE
def updateFBEmailid(app, userid, fbemailid):
	# Connect to MySQL - FBUserData
	conn, cursor = connect_mysql(app)

	try:
		print("Received User id for FBemail id Email update: ",userid)
		cursor.execute("UPDATE userinfo SET fbemailid=%s WHERE id=%s", (fbemailid,userid))
		print("FB EMailid for the: ",userid," is updated as: ",fbemailid)
		conn.commit()
		conn.close()
		return ("0")
	except	Exception as fbemailidNotUpdated:	
		print("Exception while updating timestamp for the userid")
		return ("-1")		
	
