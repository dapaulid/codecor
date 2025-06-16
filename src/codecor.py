import yaml

import argparse
import re
import os
from pathlib import Path

def load_text(filename):
	with open(filename, 'r') as file:
		return file.read()

def write_text(filename, text):
	with open(filename, "w") as file:
		file.write(text)

def process_file(filename, config, args):
	# load the file
	text = load_text(filename)

	# process all sections in config
	modified = False
	text_orig = text
	for section in config['sections']:
		# what to do?
		if args.remove:
			# remove comments
			comment = ""
		else:
			# substitute with comments
			comment = format_comment(section['comment'])
		# end if	
		# maximum number of subsitutions (0 == unlimited)
		count = section.get('count') or 0

		# do the substitution
		text = re.sub(section['pattern'], comment, text, count, flags=re.MULTILINE)
		# do it again to check if it is not changing anymore
		text2 = re.sub(section['pattern'], comment, text, count, flags=re.MULTILINE)
		if text2 != text:
			print(text2)
			raise Exception('replacement for section "%s" is not idempotent, please check pattern in config' % section['caption'])
		
		# remember if the original text was modified (at least once)
		modified = modified or text != text_orig
	# end for
	
	# done
	if modified:
		# file content changed, write it back
		write_text(filename, text)
		return True
	else:
		# nothing changed
		return False
	# end if
		
def format_comment(comment):
	formatted = []
	for line in comment.splitlines():
		# TODO generalize for arbitrary file paths
		if "{file:LICENSE}" in line:
			text = load_text('LICENSE')
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
