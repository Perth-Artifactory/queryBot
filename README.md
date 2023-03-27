# queryBot

This bot exposes ChatGPT in a shared environment (slack channel) with configurable pre "training".

## Installation

### Server

`pip install -r requirements.txt`

### OpenAI

Create an account and generate an API token.

### Slack

Create a Slack application with:

* Socket mode enabled and an event subscription to `app_mention`
* The following OAuth permissions: `app_mentions:read`, `channels:history`, `chat:write`, `groups:history`

## Configuration

* `./key` - your OpenAI token
* `config.json.example` -> `config.json`
  * `channel` - ID of your Slack channel, remember that access to this channel includes an ability to cost you money. 
   * `app_token` - Your slack app token 
   * `bot_token` - Your slack bot token
   * `calendar_id` - The ID for the google calendar you want the bot to know about
   * `wiki_urls` - Any wiki pages you want the bot to know about.
* Run `auth_google.py` to authenticate with google for upcoming events
## Running

`python slack.py`