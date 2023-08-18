import argparse
import requests
import json
from io import BytesIO
from PIL import Image, ImageFile
import csv
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunsplit, urlencode
import urllib.request
import shutil
import os
import sys
import urllib3
from tqdm import tqdm

try:
    import utils
except ImportError:
    sys.exit("utils module is required!")
try:
    import config
except ImportError:
    config = None
try:
    import extract
except ImportError:
    extract = None

schema = "https"
host = "web.archive.org"
api_path = "/cdx/search/cdx"
web_path = "/web/"
if_suffix = "if_/"
output = "json"

filename_history = ".history"
filename_ext_urls = "urls_external.csv"
filename_ignored_images = "urls_ignored.csv"
filename_error_log = "error.log"

def strip_archive_url(base_directory, url):
    clean_url = None
    if url is not None:
        try:
            url_array = urlparse(url.strip("<>")).path.split("://")
            if (len(url_array) == 2):
                scheme = url_array[0][url_array[0].rindex("/") + 1 : len(url_array[0])]
                clean_url = urlparse(scheme + "://" + url_array[1])
        except Exception as e:
            utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + url)
            print(e)
    return clean_url

def get_archive_timestamp(resource_url, original_url):
    return resource_url.lstrip(schema + "://").lstrip(host).lstrip(web_path).rstrip(if_suffix + original_url)

def extract_external_urls(resource_url, original_url, soup, base_directory):
    original_url = urlparse(original_url)
    links = soup.find_all('a')
    for l in links:
        href = l.get('href')
        href = href.strip('/')
        href_url = strip_archive_url(base_directory, href)
        if href_url is not None:
            href_host = href_url.hostname
            if (original_url.hostname != href_host):
                exists = False
                with open(base_directory + "\\" + filename_ext_urls, 'r') as csvfile:
                    try:
                        rows = csv.reader(csvfile)
                        for r in rows:
                            if href.endswith('.jpg') or href.endswith('.jpeg') or href.endswith('.png'):
                                utils.write_to_csv(base_directory + "\\" + filename_ext_urls, [resource_url, href, href_host])
                                break
                            elif r[2] == href_host:
                                exists = True
                                break
                    except Exception as e:
                        utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + resource_url)
                        print(e)
                if (exists == False):
                    utils.write_to_csv(base_directory + "\\" + filename_ext_urls, [resource_url, href, href_host])

def save_image(mimetype, resource_url, original_url, data, base_directory, sub_directory, filename):
    description = ""

    ImageFile.LOAD_TRUNCATED_IMAGES = True

    try:
        with Image.open(BytesIO(data)) as img:

            #get image sitze
            width, height = img.size
            description = original_url + " (" + str(width) + "x" + str(height) + ")"

            if width >= int(min_width) and height >= int(min_height):

                directory = utils.create_directory(base_directory + "\\" + sub_directory)

                #save image
                img.save(directory + "\\" + filename);

            else:
                utils.write_to_csv(base_directory + "\\" + filename_ignored_images, [resource_url, mimetype, width, height])

    except Exception as e:
        utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + resource_url)
        print(e)

    return description

def save_site(resource_url, original_url, soup, base_directory, sub_directory, filename):
    
    #create directory
    directory = utils.create_directory(base_directory + "\\" + sub_directory)

    #get all <img> tags
    images = soup.find_all('img')

    #replace src value
    for i in images:

        src = i.get('src')
        if src.startswith(web_path):
            src = urlunsplit((schema, host, src, "", ""))
        src_url = strip_archive_url(base_directory, src)

        #set relative URL
        # current_path = original_url.path.strip("/")
        # relative_path = os.path.relpath(image_path, current_path).replace("\\", "/")
        # if relative_path.startswith("../"):
        #     image_path = relative_path

        if src_url is not None and src_url.scheme == "http" or src_url.scheme == "https":

            #check if image is available
            site_list = get_site_list(
                query = {
                    "output": output,
                    "url": src_url.geturl(),
                    "collapse": "digest",
                    "matchtype": "prefix"
                },
                included_mimetype = [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/bmp",
                    "image/svg+xml"
                ],
                included_status = [200]
            )

            #set image URL
            if len(site_list) > 0:
                i['src'] = src_url.path
            else:
                i['src'] = utils.create_placeholder_image(100, 100, directory, src_url, i)

    #further tags with URL attribute
    # replace css and js
    # objects = soup.find_all('object')
    # embeded = soup.find_all('embed')
    # videos = soup.find_all('video')
    # iframes = soup.find_all('iframe')
    # links = soup.find_all('link')

    #set filename
    if filename == "":
        filename = get_archive_timestamp(resource_url, original_url) + ".html"
    elif filename.endswith(".html") == False:
        filename = filename.replace(".", "_") + ".html"

    #save site
    with open(directory + "\\" + filename, "w", encoding = 'utf-8') as file:
        file.write(str(soup.prettify()))

def save_others(resource_url, mimetype, response, base_directory, sub_directory, filename):
    directory = utils.create_directory(base_directory + "\\" + sub_directory)

    #save file
    try:
        with open(directory + "\\" + filename, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
    except Exception as e:
        utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + resource_url)
        print(e)

    #extract images and audio from SWF
    if extract is not None and mimetype == "application/x-shockwave-flash":
        try:
            extract.execute(directory + "\\" + filename)
        except Exception as e:
            print("Error when extracting " + resource_url)
            print(e)

def get_site_list(query, excluded_mimetypes = [], included_mimetype = [], excluded_status = [], included_status = []):

    if type(excluded_mimetypes) is str:
        excluded_mimetypes = excluded_mimetypes.split(",")

    if type(included_mimetype) is str:
        included_mimetype = included_mimetype.split(",")
    
    if type(excluded_status) is str:
        excluded_status = excluded_status.split(",")

    if type(included_status) is str:
        included_status = included_status.split(",")

    #set filter
    filter = []
    filter = filter + ["!mimetype:" + s for s in excluded_mimetypes]
    filter = filter + ["mimetype:" + s for s in included_mimetype]
    filter = filter + ["!statuscode:" + str(s) for s in excluded_status]
    filter = filter + ["statuscode:" + str(s) for s in included_status]
    query["filter"] = filter

    query = urlencode(query, doseq=True, safe="*!:/") #+ "&limit=1710&offset=389"

    try:
        api_url = urlunsplit((schema, host, api_path, query, ""))
    except Exception as e:
        print(e)

    #call API / retrieve JSON
    data_json = None
    try:
        response = urllib.request.urlopen(api_url)
        data_json = json.loads(response.read())
    except Exception as e:
        print(e)

    return data_json

def download(source):

    domains = []

    source = utils.strip_protocol(source)

    if os.path.isfile(source):
        with open(source) as f:
            domains = f.read().splitlines()
    else:
        domains = [source]
        
    for d in domains:

        site_list = get_site_list(
            query = {
                "output":output,
                "url":d + "/*",
                "collapse":collapse,
                "matchtype":matchtype
            },
            excluded_mimetypes = excluded,
            included_status = [200]
        )

        if site_list is not None:

            base_directory = utils.get_base_directory(d)

            #create CSVs
            utils.write_to_csv(base_directory + "\\" + filename_ignored_images, ["url", "mime", "width", "height"])
            if extract_urls.lower() in ['1', 'true', 'yes', 'y']:
                utils.write_to_csv(base_directory + "\\" + filename_ext_urls, ["source", "href", "original"])

            #read past resources
            with open(base_directory + "\\" + filename_history, "a+") as h:
                h.seek(0)
                digestlist = h.read().splitlines()

            pbar = tqdm(site_list)
            for i in pbar:

                #read JSON columns
                timestamp = i[1]
                original_url = i[2]
                mimetype = i[3]
                statuscode = i[4]
                digest = i[5]

                sub_directory = utils.get_sub_directory(original_url)

                if statuscode == "200" and digest not in digestlist:

                    #build resource URL
                    try:
                        resource_url = urlunsplit((schema, host, web_path + timestamp + if_suffix + original_url, "", ""))
                    except Exception as e:
                        print(e)

                    #retrieve resource
                    r = None
                    try:
                        r = requests.get(resource_url, stream = True)
                    except Exception as e:
                        utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + resource_url)
                        print(e)

                    if r is not None and r.status_code == 200:

                        filename = urllib.parse.unquote(os.path.basename(urlparse(original_url).path))
                        description = original_url
                        
                        #IMAGE
                        if mimetype.startswith("image"):
                            try:
                                description = save_image(mimetype, resource_url, original_url, r.raw.data, base_directory, sub_directory, filename)
                            except urllib3.exceptions.ProtocolError as e:
                                utils.write_to_log(base_directory + "\\" + filename_error_log, "ERROR: " + resource_url)
                                print(e)
                        #HTML
                        elif mimetype == "text/html":

                            soup = BeautifulSoup(r.text, 'html.parser')

                            #save sites
                            if download_sites is not None and download_sites.lower() in ['1', 'true', 'yes', 'y']:
                                save_site(resource_url, original_url, soup, base_directory, sub_directory, filename)

                            #extract external URLs
                            if extract_urls is not None and extract_urls.lower() in ['1', 'true', 'yes', 'y']:
                                extract_external_urls(resource_url, original_url, soup, base_directory)

                        #OTHER MIME TYPES
                        elif filename != "" and included is not None and mimetype.split("/")[0] in included.split(","):
                            save_others(resource_url, mimetype, r, base_directory, sub_directory, filename)
                        
                        #UNSUPPORTED MIME TYPES
                        else:
                            utils.write_to_log(base_directory + "\\" + filename_error_log, "UNSUPPORTED MIME TYPE: " + mimetype + "|" + resource_url)
                        
                    pbar.set_description_str(description)

                #store history
                digestlist.append(digest)
                utils.write_to_log(base_directory + "\\" + filename_history, digest)

if (__name__ == '__main__'):

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source')
    parser.add_argument('-m', '--matchtype')
    parser.add_argument('-c', '--collapse')
    parser.add_argument('-e', '--excluded')
    parser.add_argument('-i', '--included')
    parser.add_argument('-W', '--Width')
    parser.add_argument('-H', '--Height')
    parser.add_argument('-U', '--Urls')
    parser.add_argument('-S', '--Sites')

    #add help section

    args = parser.parse_args()
    source = args.source
    matchtype = args.matchtype if args.matchtype is not None else (config.matchtype if config is not None and config.matchtype is not None else None)
    collapse = args.collapse if args.collapse is not None else (config.collapse if config is not None and config.collapse is not None else None)
    excluded = args.excluded if args.excluded is not None else (config.excluded if config is not None and config.excluded is not None else None)
    included = args.included if args.included is not None else (config.included if config is not None and config.included is not None else None)
    min_width = args.Width if args.Width is not None else (config.min_width if config is not None and config.min_width is not None else None)
    min_height = args.Height if args.Height is not None else (config.min_height if config is not None and config.min_height is not None else None)
    extract_urls = args.Urls if args.Urls is not None else (config.extract_urls if config is not None and config.extract_urls is not None else None)
    download_sites = args.Sites if args.Sites is not None else (config.download_sites if config is not None and config.download_sites is not None else None)

    download(source)