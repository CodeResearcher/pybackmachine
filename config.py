matchtype = "domain"
collapse = "digest"
min_width = "200"
min_height = "200"
excluded = [
    "text/css", 
    "application/javascript", 
    "application/x-javascript"
]
included = [
    "video",
    "audio",
    "application",
    "text"
]
download_sites = "yes"
extract_urls = "yes"

cmd = "C:\Program Files (x86)\SWFTools\swfextract.exe"
temp_dir = "C:\\temp"
recursion_limit = 100
request_delay = 10