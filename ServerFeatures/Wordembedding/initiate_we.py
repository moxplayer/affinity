import os, io
import numpy as np
import subprocess


### THIS still has to be designed! questions: 
# - how do we update when new users update their histories?
# - what is the average time to update via fasttext?
# - does it make sense to keep all the user history for that? or should there be a certain time window?
# - I guess trainWEforallfiles can be removed and replaced bz trainWEwithuserfile --> renaming it to trainRefModel or so

# train a word embedding (in particular: a fasttext model) upon a corpus,
# which is simply the concatenation of all *.txt files in <rootdir> whose size is at least <min_bytes>

def trainWEforallfiles(min_bytes = 1000): #trainWEwithReferenceFiles():
	# set directories
	rootdir                = './ServerFeatures/Userdata/Reference_User_Histories/'
	reference_WE_name      = './ServerFeatures/Wordembedding/reference_model'
	temp_corpus_name       = './ServerFeatures/Userdata/temp_corpus'
	# set fasttext parameters
	minCount = str(1)
	
	# create a temporary corpus by concatenating all *.txt-files in the <rootdir> to <temp_list>
	with open(temp_corpus_name, mode = 'w') as temp_corpus:
		for root, dirs, files in os.walk(rootdir):
			for file_ in files:
				tooShort = os.path.getsize(os.path.join(root, file_)) < min_bytes
				isTxt    = file_.endswith(".txt")

				# if the chatHistory is a *.txt file and not too short
				if isTxt and not tooShort:
					with open(os.path.join(root, file_), 'r') as chatHistory:
						text = chatHistory.read()
						if type(text) == unicode:	
							text = text.encode('utf-8')
						elif type(text) == str:
							text = text.decode('utf-8').encode('utf-8')
						temp_corpus.write(text)
				elif not tooShort:
					print("The reference file is not a txt-file and is thus skipped.")
					print(" ")
				elif isTxt:
					print("The reference file is too short and is thus skipped.")
					print(" ")
	
	# Train a reference model 
	subprocess.call(['./ServerFeatures/Wordembedding/fastText/fasttext', 'skipgram','-input', temp_corpus_name, '-minCount' , minCount, '-output', reference_WE_name])

	return 

### old version
def trainWEforallfilesX():
	# set directories
	rootdir                = './ServerFeatures/Userdata/Reference_User_Histories/'
	reference_we_name      = './ServerFeatures/Wordembedding/reference_model'
	reference_we_name_temp = './ServerFeatures/Wordembedding/reference_model_temp'
	# set fasttext parameters
	minCount = str(1)
	
	document_list = []
	corpus = []

	# concatenate all txt-files in the <rootdir> to <document_list>
	for root, dirs, files in os.walk(rootdir):
		for file_ in files:
			tooShort = os.path.getsize(os.path.join(root, file_))<1000
			isTxt    = file_.endswith(".txt")
			if not tooShort and isTxt:
				with open(os.path.join(root, file_),'r', encoding='utf-8') as history:
					corpus.append(history.read())
					document_list.append(os.path.join(root, file_))
			elif not tooShort:
				print("The reference file is not a txt-file and is thus skipped.")
			elif isTxt:
				print("The reference file is too short and is thus skipped.")
			print(" ")

	# Train an initial word embedding with the first user history
	subprocess.call(['./ServerFeatures/fastText/fasttext', 'skipgram','-input', document_list[0], '-minCount' , minCount, '-output', reference_we_name])

	# Incrementally train with rest of the user histories	
	for document in document_list[1:]:
		subprocess.call(['./SeverFeatures/fastText/fasttext', 'skipgram','-input', document, '-inputModel', reference_we_name+'.bin', '-minCount' , minCount , '-output', reference_we_name_temp, '-incr'])
		# replace <reference_we_name> with <reference_we_name_temp> 
		os.rename('./'+reference_we_name_temp+'.bin',reference_we_name+'.bin')	

	print("Fasttext is trained (incrementally) with the reference documents in ",rootdir)
	return 



# evolve the current reference word embedding
def trainWEwithuserfile(chatHistoryPath):
	# set directories
	reference_we_name      = './ServerFeatures/Wordembedding/reference_model'
	reference_we_name_temp = './ServerFeatures/Wordembedding/reference_model_temp'
	# set fasttext parameters
	minCount = str(1)
	
	# if a reference_model has been trained ...
	if os.path.isfile(reference_we_name+".bin"):
		# ... run fasttext on the chatHistory incrementally initializing the reference_model
		subprocess.call(['./ServerFeatures/Wordembedding/fastText/fasttext', 'skipgram', '-inputModel', reference_we_name,'-input', chatHistoryPath,  '-minCount' , minCount, '-output', reference_we_name_temp])
		os.rename(reference_we_name_temp + '.bin', reference_we_name+'.bin')
		os.remove(reference_we_name_temp + '.bin')
	# else train a reference_model on the input text
	else:
		print("No reference model found. Train on ")
		subprocess.call(['./ServerFeatures/Wordembedding/fastText/fasttext', 'skipgram','-input', chatHistoryPath , '-minCount' , minCount , '-output', reference_we_name])
		
		
	print("Fasttext is trained with file ", chatHistoryPath)







