import json
from slack_bolt import App
import slack_sdk
from pprint import pprint
import logging
from datetime import datetime
import re

with open("config.json","r") as f:
    config = json.load(f)
    
app = App(token=config["bot_token"])

def find_channel_id(name):
    name = name.replace("#","")
    for result in app.client.conversations_list(exclude_archived=True,types="public_channel"):
        for channel in result["channels"]:
            if channel["name"] == name:
                return channel["id"]
            
def get_user_info(id):
    u = app.client.users_profile_get(user=id).data["profile"]
    if not u.get("display_name_normalized"):
        u["display_name_normalized"] = u.get("first_name")
    return {"username":u.get("display_name_normalized"),
            "real_name":u.get("real_name_normalized")}

def get_channels(min_size=30):
    channels = []
    for channel in app.client.conversations_list(exclude_archived=True).data["channels"]:
        if not channel["is_archived"] and channel["is_channel"] and not channel["is_private"] and channel["num_members"] > min_size:
            channels.append(channel)
    logging.info(f'Retrieved {len(channels)} channels')
    return channels

def format_channels(channel=None,message=None):
    if channel:
        return format_channel(channel)
    channels = get_channels()
    s = f'This is a list of the top {len(channels)} of the more popular channels on our slack team. If you want to link to a channel in a message just use the link field, not the name.'
    for channel in channels:
        desc = channel["purpose"]["value"].replace("\n\n","\n")
        s += "\n-----"
        s += f'\nChannel name: #{channel["name_normalized"]}'
        #s += f'\nChannel link: <#{channel["id"]}>' Removed to reuduce tokens
        s += f'\nChannel description: {desc}'
    return s

def get_single_channel(channel):
    logging.info(f'Getting last 30 messages from #{channel}')
    clean_messages = []
    ids = {}
    try:
        messages = app.client.conversations_history(
            channel=find_channel_id(channel),
            limit=30
        ).data["messages"]

        for message in messages:
            if not message.get("user"):
                continue
            if message["user"] not in ids:
                ids[message["user"]] = get_user_info(message["user"])
            
            for id in re.findall('<@([^>]*)>',message["text"]):
                if id not in ids:
                    ids[id] = get_user_info(id)
                message["text"] = message["text"].replace(f'<@{id}>',ids[id]["username"])

            clean_messages.append({"id":message["user"],
                                   "name":ids[message["user"]],
                                   "text":message["text"],
                                   "time":datetime.fromtimestamp(int(message["ts"].split(".")[0]))})
        clean_messages.reverse()
    except slack_sdk.errors.SlackApiError as e:
        pass
    logging.debug(f'Got {len(clean_messages)} messages from #{channel}')
    return clean_messages

def format_channel(channel):
    messages = get_single_channel(channel)
    if not messages:
        return f'You can\'t access detailed information regarding #{channel} because you are not in that channel. You could ask me to type "/invite @queryBot" from #{channel} to get access.'
    s = f'Last {len(messages)} messages from #{channel}'
    for message in messages:
        s += f'\n{message["time"].strftime("%Y-%m-%d %H:%M")} {message["name"]["username"]} - {message["text"]}'
    return s

def find_channels(message=None):
    s = ""
    for channel in re.findall('<#C[A-Z0-9]*\|([^>]*)>',message):
        s += "\n---"
        s += format_channel(channel)
        logging.debug(f'{channel} found in message: {message}')
    return s