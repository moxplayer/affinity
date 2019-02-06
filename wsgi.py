import sys
# add some paths
sys.path.append('ServerFeatures')
sys.path.append('ServerFeatures/WordEmbedding')
sys.path.append('ServerFeatures/Processing/wmd/python-emd-master')

from servermain import app

if __name__ == "__main__":
	app.run()
