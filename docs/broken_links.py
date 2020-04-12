import re
import os
import argparse

from colorama import Fore, Back, Style

files = list()
os.chdir("source")
path = os.getcwd()
broken_count = 0
clean_count = 0

parser = argparse.ArgumentParser(description='Check broken links')
parser.add_argument('--verbose', default=False, help="Verbosity level (1: Show all links)")

args = parser.parse_args()

def shortpath(path):
    return os.path.relpath(path)

def check_broken_links(file):
    global broken_count
    global clean_count
    with open(file,"r") as f:
#        matches = re.findall(r"(\[.*\])\(((?!http)[^\)]*)\)",f.read())
#        matches = re.findall(r"(\[.*\])\(((?!http)[^#\)]*)([A-Za-z0-9]*)\)",f.read())
        matches = re.findall(r"\[([^\]]+)\]\((?!http)([^[\)#]+)",f.read())
        if matches:
            print(Fore.BLUE, "{file}...".format(file=shortpath(file)), Style.RESET_ALL)
            for match in matches:
                if match[1]:
                    extra = match[2] if len(match)>=3 else ""
                    link_dest = os.path.realpath(os.path.join(os.path.dirname(file), match[1] +".md"))
                    if not os.path.exists(link_dest):
                        print("\t\t", Back.RED, Fore.WHITE, "Broken : {link}{extra}".format(link=shortpath(link_dest),extra=extra), Style.RESET_ALL)
                        broken_count += 1
                    else:
                        if args.verbose:
                            print(Fore.GREEN, "\t\tClean : {link}{extra}".format(link=shortpath(link_dest), extra=extra), Style.RESET_ALL)
                            clean_count += 1
        else:
            if args.verbose:
                print(Fore.RED, "{file} has no links".format(file=shortpath(file)), Style.RESET_ALL)

def get_md_files(path):
    global files
    for file in os.listdir(path):
        absolute_path=os.path.join(path, file)
        if os.path.isdir(absolute_path): # directory
            get_md_files(absolute_path)
        else:
            if ".md" in absolute_path:
                files.append(absolute_path)
                check_broken_links(absolute_path)

print("Starting broken link checker...")
get_md_files(path)
print("Done.")
print("Broken links: {num}".format(num=broken_count))
print("Clean links: {num}".format(num=clean_count))
