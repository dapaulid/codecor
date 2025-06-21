import yaml

import argparse
import re
import os
from pathlib import Path

# helper class to load/save text files preserving line ending format
class TextFile:
	def __init__(self, filename):
		self.filename = filename
		self.text = None
		self.newline = None
		self.load()
	def load(self):
		with open(self.filename, 'r') as f:
			self.text = f.read()
			self.newline = f.newlines[0] if type(f.newlines) is tuple else f.newlines
	def save(self):
		with open(self.filename, 'w', newline=self.newline) as f:
			f.write(self.text)


def substitute(pattern, repl, text):
	# we do two passes here (remove/insert instead of replace), because
	# of subtleties how how regex with lookahead work,
	# otherwise we may end up in the string being inserted twice.

	# remove first
	text = re.sub(pattern, "", text, flags=re.MULTILINE)
	# insert if necessary
	if repl: 
		text = re.sub(pattern, repl, text, flags=re.MULTILINE)
	return text

def process_file(filename, config, args):
	# load the file
	file = TextFile(filename)
	orig_text = file.text	

	# process all sections in config
	for section in config['sections']:
		# what to do?
		if args.remove:
			# remove comments
			comment = ""
		else:
			# substitute with comments
			comment = format_comment(section['comment'])
		# end if	
		# do the substitution
		file.text = substitute(section['pattern'], comment, file.text)
		# do it again to check if it is not changing anymore
		text2 = substitute(section['pattern'], comment, file.text)
		if text2 != file.text:
			print(text2)
			raise Exception('replacement for section "%s" is not idempotent, please check pattern in config' % section['caption'])
	# end for
	
	# file content changed?
	if file.text != orig_text:
		# yes -> write it back
		file.save()
		return True
	else:
		# no -> nothing to do
		return False
	# end if
		
def format_comment(comment):
	formatted = []
	for line in comment.splitlines():
		# TODO generalize for arbitrary file paths
		if "{file:LICENSE}" in line:
			text = TextFile('LICENSE').text
			for line2 in text.splitlines():
				formatted.append(line.replace("{file:LICENSE}", line2))
		else:
			formatted.append(line)
		# end if
	# end for
	# TODO use EOL according to input file		
	return "\n".join(formatted) + "\n"

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)

parser = argparse.ArgumentParser()
parser.add_argument('path', nargs='?', default='.',
	help="file or directory to process")
parser.add_argument("--remove", action="store_true",
	help="remove any previously generated comments")
args = parser.parse_args()

# read config files into dict that maps file extensions to config
configs = {}
config_files = Path(root_dir, 'config').rglob('*.yml')
for filename in config_files:
	with open(filename, 'r') as file:
		config = yaml.safe_load(file)
		for file_ext in config['file_ext'].split():
			configs[file_ext] = config
	# end with
# end for

# process files
files_total = 0
files_modified = 0
file_list = Path(args.path).rglob('*.*')
for filename in file_list:
	# does a config exist for this file type?
	file_ext = os.path.splitext(filename)[1].lower()
	if file_ext in configs:
		# yes -> process the file according to config
		modified = process_file(filename, configs[file_ext], args)
		if modified:
			print("modified: %s" % filename)
			files_modified += 1
		files_total += 1
	# end if
# end for
	
# done
print("\ndone, %d of %d files modified." % (files_modified, files_total))
