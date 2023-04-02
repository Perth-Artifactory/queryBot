import json
import logging
import re
from datetime import datetime
from pprint import pformat

import openai

from data import events

openai.api_key_path = './key'

with open("config.json","r") as f:
    config: dict = json.load(f)

# Create optional information flags
optional = {}

# Prefetch internet pages and set up prompted URLs.
# This doesn't require any special permissions so isn't optional
logging.info("Prefetching internet pages")
from data import matryoshka

with open("babushka.json","r") as f:
    webpages: dict = json.load(f)
    pages = matryoshka.format_pages(webpages)
optional["url"] = matryoshka.single_page

# Prefetch TidyHQ information as it takes some time to retrieve
# Will not be run if tidyhq_token isn't set

if config.get("tidyhq_token"):
    from data import tidyhq
    logging.info("Prefetching TidyHQ data")
    tidy_data = tidyhq.format_tidyhq()
    def tidy() -> str:
        return tidy_data
    optional["tidyhq"] = tidy

# Information on popular Slack channels and access to some recent public messages
# This doesn't require any special permissions beyond slack scopes so isn't optional

from data import workspace

logging.info("Prefetching Slack channel info")
optional["slackpopular"] = workspace.format_channels
optional["slackmsg"] = workspace.find_channels

# Information from Google Calendar
# Will not be run if calendar_id isn't set

if config.get("calendar_id"):
    optional["calendar"] = events.format_events

def respond(prompts: dict, model: str = "gpt-3.5-turbo") -> str:
    """Accepts a list of prompts and returns a response from a specified GPT model
    Prompts are filtered for commands which are then executed and the results added before the accepted prompts."""
    # Insert optionals
    extras = []
    r_prompts = []
    used = []
    current_pages = pages
    for p in prompts:
        # Only listen to commands if they're from Slack
        if p["role"] == "user":
            for option in optional:
                command_search = re.findall(f'!{option}-([^\s]+)', p["content"])
                # Commands with - should be handled first in case a command supports both
                if command_search:
                    p["content"] = re.sub(f'!{option}-[^\s]+', "", p["content"])
                    extras.append({"role": "user", "content": optional[option](command_search[0])})
                    logging.debug(f'Found: {command_search[0]}')
                elif "!"+option in p["content"]:
                    logging.debug(f'Found: {option}')
                    p["content"] = p["content"].replace("!"+option, "")
                    # Don't add the same command twice
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

    template_variables = {"bot_name":config["bot"]["name"],
                          "org_name":config["bot"]["org_name"],
                          "date":datetime.now().strftime("%Y-%m-%d"),
                          "time":datetime.now().strftime("%H:%M")}

    try:
        with open("prompts.txt","r") as f:
            pro: list = f.readlines()[0]
            pro = pro.split("\n")
        sys = True
        initial_prompts = []
        for line in pro:
            if sys:
                initial_prompts.append({"role": "system", "content": line.format(**template_variables)})
                sys = False
            else:
                initial_prompts.append({"role": "user", "content": line.format(**template_variables)})

    except (FileNotFoundError, IndexError):
        initial_prompts = [{"role": "system", "content": "You are {bot_name} a helpful assistant tasked with drafting replies and answering queries on behalf of {org_name}. You are receiving requests from a Slack channel".format(**template_variables)}]
        logging.warn("System prompt not set in prompts.txt, using default")

    messages = initial_prompts + current_pages + extras + r_prompts
    logging.debug(pformat(messages))
    try:
        r = openai.ChatCompletion.create(
            model=model,
            messages=messages)

    except openai.error.InvalidRequestError as e:
        friendly_error = "Something has gone wrong (It's likely that this conversation has exceeded the number of things I can process at once.) If this is a thread try deleting some of the previous comments first."
        if config["bot"]["dev"] or config["bot"]["debug"]:
            friendly_error += "\nThe error I received from OpenAI was: " + str(e)
        return friendly_error
    logging.info(f'{r["usage"]["prompt_tokens"]}, {r["usage"]["completion_tokens"]}, {r["usage"]["total_tokens"]}/4096')
    return r["choices"][0]["message"]["content"]