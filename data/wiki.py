import requests
import html
import re
from pprint import pprint
import json

def get_pages():
    with open("config.json","r") as f:
        config = json.load(f)
    urls = config["wiki_urls"] 

    # get markdown for each wiki page

    pages = []
    for url in urls:
        p = requests.get(url.replace("https://wiki.artifactory.org.au/en", "https://wiki.artifactory.org.au/s/en"))
        decodedHtml = html.unescape(p.text)
        lines = decodedHtml.split("\n")[3:]
        page = "\n".join(lines)
        pages.append({"url":url,
                    "title":re.findall("<title[^>]*>(.*)<\/title>", p.text)[0].split(" |")[0],
                    "content":page})
        return pages
    
def format_pages():
    pages = get_pages()
    prompts = []
    for page in pages:
        prompts.append({"role": "user", "content": f'There is a page on our wiki titled {page["title"]}. It can be accessed at {page["url"]} This is the content in markdown format:\n{page["content"]}'})
    return prompts