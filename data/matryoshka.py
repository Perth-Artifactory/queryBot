import requests
import json
import html
import re
from pprint import pprint
import hashlib
import openai
import logging

from data import reddit

with open("config.json","r") as f:
    config = json.load(f)

def download_page(pagedata):
    p = requests.get(pagedata["download_url"])
    pagedata["content"] = html.unescape(p.text)
    titles = re.findall("<title[^>]*>(.*)<\/title>", p.text)
    if titles:
        pagedata["title"] = titles[0]
    return pagedata

def mrkdwn(pagedata):
    pagedata["title"] = re.findall("\ntitle: '*?(.*)'*?", pagedata["content"])[0].replace("'","")
    return pagedata

def process_page(url):
    if url[0] == "<" and url[-1] == ">":
        url = url[1:-1]
    for block in url_conversions:
        if block["search"] in url:
            i = {"url":url,"download_url":url.replace(block["find"],block["replace"])+block["suffix"]}
            for f in block["functions"]:
                i = f(i)
            return i
    i = {"url":url,"download_url":url,"title":"Webpage"}
    return download_page(i)

def process_pages(url=None):
    if url:
        urls = [url]
    else:
        urls = config["urls"]

    out = {}

    for url in urls:
        out[hashlib.md5(url.encode()).hexdigest()] = process_page(url)
    return out

def gpt_summarise(pagedata):
    if config["bot"]["dev"]:
        pagedata["summary"] = "Page summary not grabbed because we're running in development mode"
        logging.info(f'Not summaring {pagedata["title"]} in development mode')
        return pagedata
    openai.api_key_path = './key'
    logging.info(f'initiating summary of {pagedata["title"]}')
    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful worker being run by the Perth Artifactory. You are tasked with summarising the content of web pages in a format that can be used by other iterations of GPT."},
                {"role": "user", "content": f'This is the contents of the webpage "{pagedata["title"]}"\n{pagedata["content"]}'}
                ]
            )
    except openai.error.InvalidRequestError:
        pagedata["summary"] = " "
        return pagedata
    pagedata["summary"] = r["choices"][0]["message"]["content"]
    return pagedata

def format_pages(pages):
    prompts = []
    for k in pages:
        pagedata = pages[k]
        prompts.append({"role": "user", "content": f'There is a webpage titled {pagedata["title"]} at {pagedata["url"]} This is a summary of the page written by a version of GPT:\n{pagedata["summary"]}'})
    return prompts

def single_page(url):
    if url[0] == "<" and url[-1] == ">":
        url = url[1:-1]
    pages = process_pages(url=url)
    for page in pages:
        p = pages[page]
    if type(p) == str:
        return {"role": "user", "content": p}
    return {"role": "user", "content": f'There is a webpage titled {p["title"]} at {p["url"]} It contains:\n{p["content"]}'}

url_conversions = [{"search":"wiki.artifactory.org.au/en/",
                   "find":"wiki.artifactory.org.au/en/",
                   "replace":"raw.githubusercontent.com/Perth-Artifactory/wiki/main/",
                   "suffix":".md",
                   "functions":[download_page,mrkdwn]},
                  {"search":"artifactory.org.au/pages/",
                   "find":"artifactory.org.au/pages/",
                   "replace":"raw.githubusercontent.com/Perth-Artifactory/website/master/_pages/",
                   "suffix":".md",
                   "functions":[download_page,mrkdwn]},
                  {"search":"reddit.com/r/",
                   "find":"",
                   "replace":"",
                   "suffix":"",
                   "functions":[reddit.format_post]}
                   ]

data_new = process_pages()
try:
    with open("babushka.json","r") as f:
        try:
            data_old = json.load(f)
        except:
            data_old = {}
except FileNotFoundError:
    data_old = {}
data_final = {}
logging.info(f'Have {len(data_new)} items from config {len(data_old)} in cache')

for d in data_new:
    if d not in data_old:
        logging.debug(f'{d} not in cache')
        data_final[d] = gpt_summarise(data_new[d])
    elif data_new[d]["content"] != data_old[d]["content"]:
        logging.debug(f'Version of {d} in cache is stale')
        data_final[d] = gpt_summarise(data_new[d])
    else:
        data_final[d] = data_old[d]

with open("babushka.json","w") as f:
    json.dump(data_final, f, indent=2)