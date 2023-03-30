import openai
import json
from pprint import pformat
import re
import logging

from data import events

openai.api_key_path = './key'

# Create optional information flags
optional = {}

# prefetch internet pages
logging.info("Prefetching internet pages")
from data import matryoshka
with open("babushka.json","r") as f:
    webpages = json.load(f)
    pages = matryoshka.format_pages(webpages)

# prefetch slack channels on launch and add to optionals
from data import workspace
logging.info("Prefetching Slack channel info")
optional["slackpopular"] = workspace.format_channels

from data import tidyhq
logging.info("Prefetching TidyHQ data")
tidy_data = tidyhq.format_tidyhq()
def tidy():
    return tidy_data
optional["tidyhq"] = tidy

def respond(prompts):
    # Add command time optionals
    optional["calendar"] = events.format_events
    optional["url"] = matryoshka.single_page
    optional["slackmsg"] = workspace.find_channels

    # Insert optionals
    extras = []
    r_prompts = []
    used = []
    current_pages = pages
    for p in prompts:
        # Only listen to commands if they're issued by users
        if p["role"] == "user":
            for option in optional:
                command_search = re.findall(f'!{option}-([^\s]+)', p["content"])
                if command_search:
                    p["content"] = re.sub(f'!{option}-[^\s]+', "", p["content"])
                    extras.append({"role": "user", "content": optional[option](command_search[0])})
                    logging.debug(f'Found: {command_search[0]}')
                elif "!"+option in p["content"]:
                    logging.debug(f'Found: {option}')
                    p["content"] = p["content"].replace("!"+option, "")
                    if option not in used:
                        content = optional[option](p["content"])
                        logging.debug(content)
                        extras.append({"role": "user", "content": content})
                        used.append(option)
                    else:
                        logging.debug(f'{option} already used')
            if '!nopages' in p["content"]:
                logging.debug(f'Found nopages, removing pages')
                p["content"] = p["content"].replace("!nopages", "")
                current_pages = []
        r_prompts.append(p)

    try:
        with open("prompts.txt","r") as f:
            pro = f.readlines()[0]
            pro = pro.split("\n")
        sys = True
        initial_prompts = []
        for line in pro:
            if sys:
                initial_prompts.append({"role": "system", "content": line})
                sys = False
            else:
                initial_prompts.append({"role": "user", "content": line})

    except FileNotFoundError:
        initial_prompts = [{"role": "system", "content": "You are a helpful assistant tasked with drafting replies and answering queries. You are receiving requests from a Slack channel"}]
        logging.warn("System prompt not set in prompts.txt, using default")

    messages = initial_prompts + current_pages + extras + r_prompts
    logging.debug(pformat(messages))
    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)

    except openai.error.InvalidRequestError:
        return "Something has gone wrong (It's likely that this conversation has exceeded the number of things I can process at once.) If this is a thread try deleting some of the previous comments first."
    logging.info(f'{r["usage"]["prompt_tokens"]}, {r["usage"]["completion_tokens"]}, {r["usage"]["total_tokens"]}/4096')
    return r["choices"][0]["message"]["content"]