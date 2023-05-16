import os
import csv
import re
import urllib.request
from urllib.parse import urlparse
from PIL import Image
#logging

def write_to_log(filename, content):
    f = open(filename, "a+", encoding='utf-8')
    f.write(content + "\n")
    f.close()

def write_to_csv(filename, content):
    f = open(filename, "a+", newline='', encoding='utf-8')
    writer = csv.writer(f)
    writer.writerow(content)
    f.close()

def get_base_directory(domain):
    if (domain.find('/')):
        domain = domain.split('/')[0]
    base_directory = os.getcwd() + "\\" + domain
    return create_directory(base_directory)

def get_sub_directory(original_url):
    path = urlparse(original_url).path
    sub_directory = urllib.parse.unquote(os.path.dirname(path))
    return sub_directory.rstrip("/").replace("/", "\\")

def create_directory(directory):
    if directory != "" and os.path.exists(directory) == False:
        os.makedirs(directory)
    return directory

def strip_protocol(input):
    if input.startswith("http:") or input.startswith("https:"):
        return re.sub("https?://", "", input)
    else:
        return input

def create_placeholder_image(width, height, directory, url = '', img = None):
    color = (119, 252, 3)
    if img is not None and img.has_attr("width"):
        width = int(img["width"])
        height = int(img["height"])
        color = (245, 66, 230)
    placeholder  = Image.new(mode = "RGB", size = (width, height), color = color)

    placeholder_name = url.path.split("/")
    placeholder_name = placeholder_name[len(placeholder_name) - 1]

    placeholder.save(directory + "\\" + placeholder_name);
    return placeholder_name