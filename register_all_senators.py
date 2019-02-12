# this python file registers all senators in ./ServerFeatures/Userdata/US115thcongress

import subprocess
import os





def main():
	#
	senator_dir = "./ServerFeatures/Userdata/US115thcongress/"
	# for all files in senator_dir
	for root, dirs, files in os.walk(senator_dir):
			for name in files:
				isTxtFile = os.path.splitext(name)[1] == '.txt'
				# if the file is a .txt file
				if isTxtFile:
					# assemble a curl command in order to register the .txt file as a reference user
					json_string = '{"path":"' + os.path.join(root, name) + '", "useforretrain":"False"}'
					print(json_string)
					# send the command to create a reference user [name = senator-txt-file]
					subprocess.call(["curl", "-X", "POST", "-H", "Content-type:application/json", "-d", json_string ,"http://127.0.0.1:5000/createreferenceuser"])
			
if __name__ == "__main__":
	main()