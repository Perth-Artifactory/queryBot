import json
import logging
import re
from datetime import datetime
from typing import Optional

import slack_sdk
from slack_bolt import App

with open("config.json","r") as f:
    config = json.load(f)
    
app = App(token=config["bot_token"])

def find_channel_id(name: str) -> Optional[str]:
    """Returns the channel ID for the channel with the given name
    Tolerant of channel names with or without the # prefix"""
    name = name.replace("#","")
    for result in app.client.conversations_list(exclude_archived=True,types="public_channel"):
        for channel in result["channels"]:
            if channel["name"] == name:
                return channel["id"]
            
def get_user_info(id: str) -> dict:
    """Returns a dict containing the username and real name for the user with the given ID
    Bots don't have a real name so we use their first name instead.
    Breaks if the user does not exist"""
    u = app.client.users_profile_get(user=id).data["profile"]
    if not u.get("display_name_normalized"):
        u["display_name_normalized"] = u.get("first_name")
    return {"username":u.get("display_name_normalized"),
            "real_name":u.get("real_name_normalized")}

def get_channels(min_size: Optional[int] = 30) -> list[dict]:
    """Returns a list of dicts containing the name, id, and purpose of all channels with more than min_size members"""
    channels = []
    for channel in app.client.conversations_list(exclude_archived=True).data["channels"]:
        if not channel["is_archived"] and channel["is_channel"] and not channel["is_private"] and channel["num_members"] > min_size:
            channels.append(channel)
    logging.info(f'Retrieved {len(channels)} channels')
    return channels

def format_channels(channel: Optional[str] = None,message: Optional[str] = None) -> str:
    """Returns a string containing a list of the top channels on the slack team or the recent messages from a single channel"""
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

def get_single_channel(channel: str) -> list[dict]:
    """Return a list of the last 30 messages from the given channel in the form of a dict"""
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
            
            # Pick out any user mentions and replace them with their username
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

def format_channel(channel: str) -> str:
    """Returns a string containing the last 30 messages from the given channel suitable for GPT"""
    messages = get_single_channel(channel)
    if not messages:
        return f'You can\'t access detailed information regarding #{channel} because you are not in that channel. You could ask me to type "/invite @{config["bot"]["name"]}" from #{channel} to get access.'
    s = f'Last {len(messages)} messages from #{channel}'
    for message in messages:
        s += f'\n{message["time"].strftime("%Y-%m-%d %H:%M")} {message["name"]["username"]} - {message["text"]}'
    return s

def find_channels(message: Optional[str] = None) -> str:
    """Searches for any channel links in the given message and adds a summary of the last 30 messages from that channel in a format suitable for GPT"""
    s = ""
    for channel in re.findall('<#C[A-Z0-9]*\|([^>]*)>',message):
        s += "\n---"
        s += format_channel(channel)
        logging.debug(f'{channel} found in message: {message}')
    return s