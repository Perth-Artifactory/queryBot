import json
import logging
from pprint import pprint

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_logger import SlackFormatter, SlackHandler

with open("config.json","r") as f:
    config: dict = json.load(f)

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

def structure_reply(bot_id: str,messages: list,ignore_mention: bool = False) -> list[dict]:
    """Takes a list of Slack messages and returns a list formatted for GPT.
    Also replaces mentions of the bot with the bot's name."""
    conversation = []
    for message in messages:
        # deslackify
        mentioned = ignore_mention
        if bot_id in message["text"]:
            mentioned = True
        message["text"]: str = message["text"].replace(f'<@{bot_id}>',config["bot"]["name"])

        # Only add messages that are either added by the bot or mention the bot directly.
        if message["user"] == bot_id:
            conversation.append({"role": "assistant", "content": message["text"]})
        
        elif mentioned == True:
            conversation.append({"role": "user", "content": message["text"]})
    return conversation

def clean_messages(messages: list[dict]) -> list[dict]:
    """Takes a list of Slack messages and removes any restricted commands from them."""
    clean = []
    # Process command aliases first so that we can remove any restricted commands in the alias
    messages = command_alias(messages)
    # Remove restricted commands
    for message in messages:
        for command in config["bot"]["restricted_commands"]:
            message["text"] = message["text"].replace(f'!{command}',"")
        clean.append(message)
    return clean

def command_alias(messages):
    """Takes a list of Slack messages and replaces any aliases with the command they're aliased to."""
    if type(messages) != list:
        for alias in config["aliases"]:
            messages = messages.replace(f'!{alias}',f'{config["aliases"][alias]}')
        return messages
    used = []
    for message in messages:
        for alias in config["aliases"]:
            if alias not in used:
                used.append(alias)
                message["text"] = message["text"].replace(f'!{alias}',f'{config["aliases"][alias]}')
            else:
                message["text"] = message["text"].replace(f'!{alias}',"")
    return messages

# matchers

def gpt_emoji(event: dict) -> bool:
    return event.get("reaction") == config["bot"]["emoji"]["trigger"]

def approval_emoji(event: dict) -> bool:
    return event.get("reaction") in [config["bot"]["emoji"]["approve"],
                                     config["bot"]["emoji"]["remove"]]

def authed(event: dict) -> bool:
    """Checks if the user is in a unrestricted channel"""
    control_channel_members = []
    for channel in config["unrestricted_channels"]:
        control_channel_members += app.client.conversations_members(channel=channel).data["members"]
    return event.get("user") in control_channel_members

def unrestricted_channel(event: dict) -> bool:
    return event.get("channel") in config["unrestricted_channels"]

app = App(token=config["bot_token"])

@app.event(event="app_mention", matchers=[authed,unrestricted_channel])
def tagged(body, event, say):
    # pull out info
    id = body["authorizations"][0]["user_id"]
    ts = event.get("ts")
    message = event.get("text").replace(f'<@{id}>',config["bot"]["name"])
    # send a stalling message to let users know we've received the request
    r = say(f':{config["bot"]["emoji"]["stalling"]}:',thread_ts=ts)
    stalling_id = r.data["message"]["ts"]

    # Retrieve extra context for messages if present
    struct = [{"role": "user", "content": command_alias(message)}]
    if event.get("thread_ts"):
        result = app.client.conversations_replies(
            channel=event.get("channel"),
            inclusive=True,
            ts=event.get("thread_ts"))
        struct = structure_reply(bot_id=id,messages=command_alias(result.data["messages"][:-1]))

    # Replace message with ChatGPT response
    gpt_response = gpt.respond(prompts=struct,model=config["models"]["unrestricted"])
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
    channel = event["item"].get("channel")
    r = say(f':{config["bot"]["emoji"]["stalling"]}:',thread_ts=message_ts)
    stalling_id = r.data["message"]["ts"]
    result = app.client.conversations_replies(
        channel=channel,
        inclusive=True,
        ts=message_ts)
    message = result.data["messages"][-2]

    if channel in config["channel_maps"]:
        message["text"] = f'{message["text"]} {config["channel_maps"][channel]}'

    messages = clean_messages([message])
    app.client.chat_postMessage(
        channel=config["unrestricted_channels"][0],
        text=f'Got authed emoji trigger in <#{channel}> from <@{event["user"]}>.\n {messages[-1]["text"]}'
    )
    logging.info(f'Got authed :{config["bot"]["emoji"]["trigger"]}: in {channel}')

    struct = structure_reply(bot_id=id,messages=messages,ignore_mention=True)
    gpt_response = gpt.respond(prompts=struct,model=config["models"]["emoji"])
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
        name=config["bot"]["emoji"]["approve"]
    )
    app.client.reactions_add(
        channel=event["item"].get("channel"),
        timestamp=stalling_id,
        name=config["bot"]["emoji"]["remove"]
    )

@app.event(event="reaction_added", matchers=[approval_emoji, authed])
def killswitch(event, body, logger):
    logger.info(body)
    message_ts = event["item"]["ts"]
    id = body["authorizations"][0]["user_id"]
    # Only react if the message being reacted to is us and don't react if we're the one reacting
    if event.get("user") != id and event.get("item_user") == id:
        if event.get("reaction") == config["bot"]["emoji"]["remove"]:
            app.client.chat_update(
                channel=event["item"].get("channel"),
                ts=event["item"].get("ts"),
                as_user=True,
                text = f'I\'m sorry, the response I generated for this query was marked as innacurate by <@{event.get("user")}>'
            )
        elif event.get("reaction") == config["bot"]["emoji"]["approve"]:
            pass
        app.client.reactions_remove(
            channel=event["item"].get("channel"),
            timestamp=event["item"].get("ts"),
            name=config["bot"]["emoji"]["approve"]
        )
        app.client.reactions_remove(
            channel=event["item"].get("channel"),
            timestamp=event["item"].get("ts"),
            name=config["bot"]["emoji"]["remove"]
        )

@app.event("reaction_added")
def handle_reaction_added_events():
    pass

@app.event("message")
def handle_message_events():
    pass

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["app_token"])
    logging.debug("Ready")
    handler.start()