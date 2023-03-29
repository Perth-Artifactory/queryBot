import openai
import json
from pprint import pprint
import re

from data import events

openai.api_key_path = './key'

with open("data.json","r") as f:
    data = json.load(f)

# Create optional information flags
optional = {}

# prefetch internet pages
from data import matryoshka
with open("babushka.json","r") as f:
    webpages = json.load(f)
    pages = matryoshka.format_pages(webpages)

# prefetch slack channels on launch and add to optionals
from data import workspace
optional["slack"] = workspace.format_channels

def respond(prompts):
    # Add command time optionals
    optional["calendar"] = events.format_events
    optional["url"] = matryoshka.single_page

    # Insert optionals
    extras = []
    r_prompts = []
    used = []
    for p in prompts:
        for option in optional:
            command_search = re.findall(f'!{option}-([^\s]+)', p["content"])
            if command_search:
                p["content"] = re.sub(f'!{option}-[^\s]+', "", p["content"])
                pprint(command_search)
                extras.append(optional[option](command_search[0]))
                #extras.append({"role": "user", "content": optional[option](command_search[0])})
            elif "!"+option in p["content"]:
                p["content"] = p["content"].replace("!"+option, "")
                if option not in used:
                    extras.append({"role": "user", "content": optional[option]()})
                    used.append(option)
        r_prompts.append(p)

    messages=[{"role": "system", "content": "You are a helpful assistant tasked with drafting replies to questions from the public on behalf of the Perth Artifactory. You are receiving requests from a channel on the artifactory slack team and your name is QueryBot. If you are ever unsure of information, ask for clarification."},
              {"role": "user", "content": data["bot primer"]},
              {"role": "user", "content": data["workshop usage"]}]
    messages = messages + pages + extras + r_prompts

    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)

    except openai.error.InvalidRequestError as e:
        print(e)
        #print(f'EXCEEDED {r["usage"]["prompt_tokens"]}, {r["usage"]["completion_tokens"]}, {r["usage"]["total_tokens"]}/4096')
        return "This conversation has exceeded the number of things I can process at once. If this is a thread try deleting some of the previous comments first."
    pprint(messages)
    print(f'{r["usage"]["prompt_tokens"]}, {r["usage"]["completion_tokens"]}, {r["usage"]["total_tokens"]}/4096')
    return r["choices"][0]["message"]["content"]