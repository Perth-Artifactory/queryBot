from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
import json

import logging
from slack_logger import SlackFormatter, SlackHandler

with open("config.json","r") as f:
    config = json.load(f)

# Set up logging
if config["bot"]["debug"]:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

if config["bot"]["slack_error_webhook"]:
    sh = SlackHandler(config["slack_webhook"])
    sh.setFormatter(SlackFormatter())
    sh.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(sh)

# Warn about development mode
if config["bot"]["dev"]:
    logging.info("Running in development mode, some resource intensive tasks will be skipped")

# This is going to prefetch some stuff so set up logging first
import gpt

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

def clean_messages(messages):
    clean = []
    for message in messages:
        for command in config["bot"]["restricted_commands"]:
            message["text"] = message["text"].replace(f'!{command}',"")
        clean.append(message)
    return clean

# matchers

def gpt_emoji(event) -> bool:
    return event.get("reaction") == "chat-gpt"

def approval_emoji(event) -> bool:
    return event.get("reaction") in ["+1","-1"]

def authed(event):
    control_channel_members = []
    for channel in config["unrestricted_channels"]:
        control_channel_members += app.client.conversations_members(channel=channel).data["members"]
    return event.get("user") in control_channel_members

def unrestricted_channel(event):
    return event.get("channel") in config["unrestricted_channels"]

app = App(token=config["bot_token"])

@app.event(event="app_mention", matchers=[authed,unrestricted_channel])
def tagged(body, event, say):
    # pull out info
    id = body["authorizations"][0]["user_id"]
    ts = event.get("ts")
    message = event.get("text").replace(f'<@{id}>',"QueryBot")
    # send a stalling message to let users know we've received the request
    r = say(":spinthinking:",thread_ts=ts)
    stalling_id = r.data["message"]["ts"]

    # Retrieve extra context for messages if present
    struct = [{"role": "user", "content": message}]
    if event.get("thread_ts"):
        result = app.client.conversations_replies(
            channel=event.get("channel"),
            inclusive=True,
            ts=event.get("thread_ts"))
        struct = structure_reply(bot_id=id,messages=result.data["messages"])

    # Replace message with ChatGPT response
    gpt_response = gpt.respond(prompts=struct)
    app.client.chat_update(
        channel=event.get("channel"),
        ts=stalling_id, 
        as_user=True, 
        text=gpt_response 
    )
    
@app.event(event="app_mention")
def tagged(event):
    logging.info(f'Tagged in a channel that wasn\'t whitelisted or by a user that isn\'t authed. ({event.get("user")} in {event.get("channel")})')

@app.event(event="reaction_added", matchers=[gpt_emoji, authed])
def emoji_prompt(event, say, body):
    message_ts = event["item"]["ts"]
    id = body["authorizations"][0]["user_id"]
    r = say(":spinthinking:",thread_ts=message_ts)
    stalling_id = r.data["message"]["ts"]
    result = app.client.conversations_replies(
        channel=event["item"].get("channel"),
        inclusive=True,
        ts=message_ts)
    
    logging.info(f'Got authed :chat-gpt: in {event["item"]["channel"]}')
    struct = structure_reply(bot_id=id,messages=clean_messages(result.data["messages"]),ignore_mention=True)
    struct[-1]["content"] += " !calendar !slack"
    gpt_response = gpt.respond(prompts=struct)
    caveat = "\n(This response was automatically generated)"
    app.client.chat_update(
        channel=event["item"].get("channel"),
        ts=stalling_id,
        as_user=True,
        text = gpt_response+caveat
    )
    app.client.reactions_add(
        channel=event["item"].get("channel"),
        timestamp=stalling_id,
        name="+1"
    )
    app.client.reactions_add(
        channel=event["item"].get("channel"),
        timestamp=stalling_id,
        name="-1"
    )

@app.event(event="reaction_added", matchers=[approval_emoji, authed])
def killswitch(event, say, body, logger):
    logger.info(body)
    message_ts = event["item"]["ts"]
    id = body["authorizations"][0]["user_id"]
    # Only react if the message being reacted to is us and don't react if we're the one reacting
    if event.get("user") != id and event.get("item_user") == id:
        if event.get("reaction") == "-1":
            app.client.chat_update(
                channel=event["item"].get("channel"),
                ts=event["item"].get("ts"),
                as_user=True,
                text = f'I\'m sorry, the response I generated for this query was marked as innacurate by <@{event.get("user")}>'
            )
        elif event.get("reaction") == "+1":
            pass
        app.client.reactions_remove(
            channel=event["item"].get("channel"),
            timestamp=event["item"].get("ts"),
            name="+1"
        )
        app.client.reactions_remove(
            channel=event["item"].get("channel"),
            timestamp=event["item"].get("ts"),
            name="-1"
        )

@app.event("reaction_added")
def handle_reaction_added_events(body, logger):
    logger.info(body)

@app.event("message")
def handle_message_events(body, logger):
    pass

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["app_token"])
    logging.debug("Ready")
    handler.start()