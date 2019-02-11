import os, sys, subprocess

# train a word embedding (in particular: a binary fasttext model) upon a corpus,
# which is simply the concatenation of all *.txt files in <rootdir> whose size is at least <min_bytes>
# requires:
# [rootdir]     : directory of .txt files to consider
# [output_name] : name of the output word embedding
# [min_bytes]   : min number of bytes under which a txt files is not considered in the training corpus
# 
def trainWEforallfiles(rootdir, output_name, min_bytes = 1000, fasttext= "./ServerFeatures/WordEmbedding/fastText/fasttext"):
    # set name for temporary corpus
    temp_corpus_name       = rootdir + '/tempcorpus'
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
    subprocess.call([fasttext, 'skipgram','-input', temp_corpus_name, '-minCount' , minCount, '-output', output_name])
    # remove the temp corpus
    os.remove(temp_corpus_name)	
    return



# evolve the current reference word embedding [NOT PRODUCTION READY!]
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

	
	
	
def main():
	rootdir     = sys.argv[1]
	output_name = sys.argv[2]
	fasttext    = sys.argv[3]
	# train a fasttext model (named : <output_name>) based on a corpus made out of txt files in <rootdir>, using the <fasttext> library
	trainWEforallfiles(rootdir, output_name, min_bytes = 1000, fasttext = fasttext)
	return
	
if __name__ == "__main__":
	main()
