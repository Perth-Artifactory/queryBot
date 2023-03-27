import openai
import json

from data import events

openai.api_key_path = './key'

with open("data.json","r") as f:
    data = json.load(f)

def respond(prompts):
    r = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": "You are a helpful assistant tasked with drafting replies to questions from the public on behalf of the Perth Artifactory. You are receiving requests from a channel on the artifactory slack team and your name is QueryBot."},
            {"role": "user", "content": data["bot primer"]},
            {"role": "user", "content": data["first visit"]},
            {"role": "user", "content": data["membership"]},
            {"role": "user", "content": data["workshop usage"]},
            {"role": "user", "content": events.format_events()}
        ]+prompts
    )
    return r["choices"][0]["message"]["content"]