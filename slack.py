from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
import json

import gpt

with open("config.json","r") as f:
    config = json.load(f)

def structure_reply(bot_id,messages):
    conversation = []
    for message in messages:
        # deslackify
        mentioned = False
        if bot_id in message["text"]:
            mentioned = True
        message["text"] = message["text"].replace(f'<@{bot_id}>',"QueryBot")

        # Only add messages that are either added by the bot or mention the bot directly.
        if message["user"] == bot_id:
            conversation.append({"role": "assistant", "content": message["text"]})
        
        elif mentioned == True:
            conversation.append({"role": "user", "content": message["text"]})
    return conversation

app = App(token=config["bot_token"])

@app.event("app_mention")
def tagged(body, say):
    if body["event"]["channel"] == config["channel"]:
        # pull out info
        id = body["authorizations"][0]["user_id"]
        ts = body["event"]["ts"]
        message = body["event"]["text"].replace(f'<@{id}>',"QueryBot")

        # send a stalling message to let users know we've received the request
        r = say("One moment, gears are turning.",thread_ts=ts)
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
        say(f'I am not authorised to communicate here. Head to <{config["channel"]}>')

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["app_token"])
    handler.start()