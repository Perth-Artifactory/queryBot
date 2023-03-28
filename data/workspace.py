import json
from slack_bolt import App
from pprint import pprint

with open("config.json","r") as f:
    config = json.load(f)
    
app = App(token=config["bot_token"])

def get_channels(min_size=30):
    channels = []
    for channel in app.client.conversations_list(exclude_archived=True).data["channels"]:
        if not channel["is_archived"] and channel["is_channel"] and not channel["is_private"] and channel["num_members"] > min_size:
            channels.append(channel)
    return channels

def format_channels():
    channels = get_channels()
    s = f'This is a list of the top {len(channels)} of the more popular channels on our slack team. If you want to link to a channel in a message just use the link field, not the name.'
    for channel in channels:
        desc = channel["purpose"]["value"].replace("\n\n","\n")
        s += "\n-----"
        s += f'\nChannel name: #{channel["name_normalized"]}'
        #s += f'\nChannel link: <#{channel["id"]}>'
        s += f'\nChannel description: {desc}'
    return s