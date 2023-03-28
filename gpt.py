import openai
import json

from data import events

openai.api_key_path = './key'

with open("data.json","r") as f:
    data = json.load(f)

# prefetch internet pages
from data import matryoshka
with open("babushka.json","r") as f:
    webpages = json.load(f)
    pages = matryoshka.format_pages(webpages)

def respond(prompts):
    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant tasked with drafting replies to questions from the public on behalf of the Perth Artifactory. You are receiving requests from a channel on the artifactory slack team and your name is QueryBot."},
                {"role": "user", "content": data["bot primer"]},
                {"role": "user", "content": data["workshop usage"]},
                {"role": "user", "content": events.format_events()}
                ]+pages+prompts
            )
    except openai.error.InvalidRequestError:
        return "This has gotten a bit complex for my brain to handle sorry :("
    return r["choices"][0]["message"]["content"]