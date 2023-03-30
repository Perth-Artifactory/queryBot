import openai
import json
from pprint import pprint
import re
import logging

from data import events

openai.api_key_path = './key'

with open("data.json","r") as f:
    data = json.load(f)

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
optional["slack"] = workspace.format_channels

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

    # Insert optionals
    extras = []
    r_prompts = []
    used = []
    current_pages = pages
    for p in prompts:
        for option in optional:
            command_search = re.findall(f'!{option}-([^\s]+)', p["content"])
            if command_search:
                p["content"] = re.sub(f'!{option}-[^\s]+', "", p["content"])
                extras.append(optional[option](command_search[0]))
                logging.debug(f'Found: {command_search[0]}')
            elif "!"+option in p["content"]:
                logging.debug(f'Found: {option}')
                p["content"] = p["content"].replace("!"+option, "")
                if option not in used:
                    content = optional[option]()
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

    messages=[{"role": "system", "content": "You are a helpful assistant tasked with drafting replies to questions from the public on behalf of the Perth Artifactory. You are receiving requests from a channel on the artifactory slack team and your name is QueryBot. If you are ever unsure of information, ask for clarification."},
              {"role": "user", "content": data["bot primer"]},
              {"role": "user", "content": data["workshop usage"]}]
    messages = messages + current_pages + extras + r_prompts

    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)

    except openai.error.InvalidRequestError:
        return "Something has gone wrong (It's likely that this conversation has exceeded the number of things I can process at once.) If this is a thread try deleting some of the previous comments first."
    logging.info(f'{r["usage"]["prompt_tokens"]}, {r["usage"]["completion_tokens"]}, {r["usage"]["total_tokens"]}/4096')
    return r["choices"][0]["message"]["content"]