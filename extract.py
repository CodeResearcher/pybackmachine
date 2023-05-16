import subprocess
import re
import os
from os import listdir
from os.path import exists
import shutil
import pathlib
import sys
import getopt

try:
    import utils
except ImportError:
    sys.exit("utils module is required!")
try:
    import config
except ImportError:
    sys.exit("config module is required!")

#const
temp_swf = "output.swf"
temp_mp3 = "output.mp3"
        
def copy_folder(src, dst):
    utils.create_directory(dst)
    if src != dst:
        if src != config.temp_dir:
            src_folder = pathlib.PurePath(src).name
            try:
                if os.path.isdir(dst + "\\" + src_folder):
                    src_folder = int(src_folder) + 1
                    copy_folder(src, dst + "\\" + str(src_folder))
                else:
                    shutil.move(src, dst)
            except Exception as e:
                print(e)
        else:
            allfiles = os.listdir(src)
            for f in allfiles:
                try:
                    src_path = os.path.join(src, f)
                    dst_path = os.path.join(dst, f)
                    shutil.move(src_path, dst_path)
                except Exception as e:
                    print(e)

def get_swf_info(args):
    result = subprocess.run(args, stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    return output.splitlines()

def get_swf_object(list, type):
    item = filter(lambda x: type in x , list)
    item = next(item, None)
    if item == None:
        return None
    else:
        if ("ID(s)" in item):
            return item.split("ID(s)")[1]
        else:
            return True
    
def extract_movies(args):
    subprocess.run(args)

def extract_jpegs(ids, dir, filename):
    #max length for dir = 60 chars
    if ids != None:
        utils.create_directory(dir)
        ids = re.sub(r"\s", "", ids)
        args = [config.cmd, "-P", "-j", ids, "--outputformat", dir + "\\extract_%06d.%s", filename]
        subprocess.run(args)
        copy_folder(dir, root_dir)

def extract_pngs(ids, dir, filename):
    #max length for dir = 60 chars
    if ids != None:
        utils.create_directory(dir)
        ids = re.sub(r"\s", "", ids)
        args = [config.cmd, "-P", "-p", ids, "--outputformat", dir + "\\extract_%06d.%s", filename]
        subprocess.run(args)
        copy_folder(dir, root_dir)

def extract_mp3(has_mp3, filename):
    if has_mp3:
        try:
            args = [config.cmd, "-P", "-m", filename]
            subprocess.run(args)
        except Exception as e:
            print(e)

def extract(dir, file, i):

    print(str(i) + " " + file)
    i += 1
    if (i > config.recursion_limit):
        return

    #get SWF info
    swf_objects = get_swf_info([config.cmd, "-o", "-n output", file])

    #extract JPEGs
    jpeg_ids = get_swf_object(swf_objects, "JPEGs")
    extract_jpegs(jpeg_ids, dir, file)

    #extract PNGs
    png_ids = get_swf_object(swf_objects, "PNGs")
    extract_pngs(png_ids, dir, file)

    #extract MP3
    has_mp3 = get_swf_object(swf_objects, "MP3")
    extract_mp3(has_mp3, file)

    #extract Movies
    movie_ids = get_swf_object(swf_objects, "MovieClips")
    if movie_ids != None:
        movie_ids = movie_ids.split(",")
        for m in movie_ids:
            try:
                movie_id = m.strip()
                extract_movies([config.cmd, "-P", "-i", movie_id, file])
                extract(config.temp_dir + "\\" + movie_id, temp_swf, i)
            except Exception as e:
                print(e)

def execute(path):

    global root_dir
    utils.create_directory(config.temp_dir)

    if (path.endswith(".swf")):
        files = [path]
    else:
        files = [f for f in listdir(path) if f.endswith(".swf")]

    for f in files:
        root_dir = f.strip(".swf")
        extract(config.temp_dir, f, 0)
        if exists(temp_mp3):
            name = os.path.split(root_dir)[1]
            os.rename(temp_mp3, root_dir + "\\" + name + ".mp3")
        if exists(temp_swf):
            os.remove(temp_swf)

if (__name__ == '__main__'):

    argv = sys.argv[1:]
    opts, args = getopt.getopt(argv, "p:", [
        "path"
    ])

    for opt, arg in opts:
        if opt in ['-p', '--path']:
            path = arg

    execute(path)