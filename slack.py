from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
import json

import gpt

with open("config.json","r") as f:
    config = json.load(f)

def structure_reply(bot_id,messages,ignore_mention=False):
    conversation = []
    for message in messages:
        # deslackify
        mentioned = ignore_mention
        if bot_id in message["text"]:
            mentioned = True
        message["text"] = message["text"].replace(f'<@{bot_id}>',"QueryBot")

        # Only add messages that are either added by the bot or mention the bot directly.
        if message["user"] == bot_id:
            conversation.append({"role": "assistant", "content": message["text"]})
        
        elif mentioned == True:
            conversation.append({"role": "user", "content": message["text"]})
    return conversation

def check_perm(id):
    control_channel_members = []
    for channel in config["unrestricted_channels"]:
        control_channel_members += app.client.conversations_members(channel=config["unrestricted_channels"]).data["members"]
    return id in control_channel_members

app = App(token=config["bot_token"])

@app.event("app_mention")
def tagged(body, say):
    if body["event"]["channel"] in config["unrestricted_channels"]:
        # pull out info
        id = body["authorizations"][0]["user_id"]
        ts = body["event"]["ts"]
        message = body["event"]["text"].replace(f'<@{id}>',"QueryBot")

        # send a stalling message to let users know we've received the request
        r = say(":spinthinking:",thread_ts=ts)
        stalling_id = r.data["message"]["ts"]

        # Retrieve extra context for messages if present
        struct = [{"role": "user", "content": message}]
        if "thread_ts" in body["event"]:
            result = app.client.conversations_replies(
                channel=config["channel"],
                inclusive=True,
                ts=body["event"]["thread_ts"])
            struct = structure_reply(bot_id=id,messages=result.data["messages"])

        # Replace message with ChatGPT response
        gpt_response = gpt.respond(prompts=struct)
        app.client.chat_update(channel=config["channel"], ts=stalling_id, as_user = True, text = gpt_response)
    else:
        print(f'Tagged in a channel that wasn\'t whitelisted. ({body["event"]["channel"]})')

@app.event("reaction_added")
def emoji_prompt(event, say, body):
    message_ts = event["item"]["ts"]
    id = body["authorizations"][0]["user_id"]
    if event["reaction"] == "chat-gpt" and check_perm(id=event["user"]):
        r = say(":spinthinking:",thread_ts=message_ts)
        stalling_id = r.data["message"]["ts"]
        result = app.client.conversations_replies(
            channel=event["item"]["channel"],
            inclusive=True,
            ts=message_ts)
        struct = structure_reply(bot_id=id,messages=result.data["messages"],ignore_mention=True)
        struct[-1]["content"] += " !calendar !slack"
        gpt_response = gpt.respond(prompts=struct)
        caveat = "\n(This response was automatically generated)"
        app.client.chat_update(channel=event["item"]["channel"], ts=stalling_id, as_user = True, text = gpt_response+caveat)

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["app_token"])
    handler.start()