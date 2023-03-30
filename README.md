# queryBot

This bot exposes `gpt-3.5-turbo` as a Slack service. It is preprimed to assist with Artifactory related queries and has access to some specific data such as:

* Our website and wiki
* Specific URLs (With extra support for Reddit)
^ Our event calendar
* Slack channel metadata
* TidyHQ contact info

## Installation

### Server

`pip install -r requirements.txt`

### OpenAI

Create an account and generate an API token.

### Slack

* Create a Slack application using `./rsc/slack.manifest.json`
* Add an app level token with `connections:write` and save the app token
* Install the app to your workspace and save the bot token
* Add the :chat-gpt: emoji from `./rsc/chat-gpt.png` as a custom emoji

## Configuration

* `./key` - your OpenAI token
* `./rsc/config.json.example` -> `config.json`
   * `unrestricted_channels` - A list of slack channel IDs for unrestricted channels. Remember that access to these channels includes an ability to cost you money. 
   * `app_token` - Your slack app token 
   * `bot_token` - Your slack bot token
   * `reddit_id` - Create a [reddit personal use script](https://www.reddit.com/prefs/apps)
   * `reddit_secret` - As above
   * `tidyhq_token` - TidyHQ API token
   * `calendar_id` - The ID for the google calendar you want the bot to know about
   * `urls` - Any web pages you want the bot to know about. Supports pages on `artifactory.org.au` and `wiki.artifactory.org.au`
* Run `auth_google.py` to authenticate with google for upcoming events
## Running

`python slack.py`

## Usage

Please only use the bot for Artifactory tasks, while it is relatively cheap to run it's not free.

* The bot will very confidently be completely wrong if it doesn't know the answer to a question. Make sure you fact check any replies before using them elsewhere. It will go so far as to create fictious URLs and businesses.
* It has a a pretty good understanding of upcoming events and pages on our main website. It can access specific pages on the wiki as well but it doesn't always do so well with markdown tables.
* If something is wrong about the message, like the tone etc, ask the bot to change it.
* If you find that you're adding the same instruction frequently (like "We refer to ourselves as The Artifactory rather than Perth Artifactory Inc") let @Fletcher know and we may be able to include it in the priming.

### In the unrestricted channel

Send a message to this channel that tags @queryBot to begin a conversation. Your message should include your complete initial request. If you need to send follow up messages in the same conversation, like correcting details, then reply in a thread and tag @queryBot in the message. Any messages in the thread that do not tag @queryBot will be ignored. This allows us to discuss a response without @queryBot getting confused.

Add the following to a message and the bot should get some info about that category to help inform its answer.

* `!calendar` - The next 20 events
* `!slack` - Some basic information about public slack channels with over 30 people
* `!url-https://your.url` - Information from a custom provided URL. It won't handle big pages or pages with lots of javascript etc. There is some custom logic specifically for our [website](https://artifactory.org.au)/[wiki](https://wiki.artifactory.org.au) and Reddit which allow it to download a "cleaner" version of the page. If you're using a url that's not on those domains you may have more success if you use a "raw" version of the page (like the source view on a wiki etc). Because `!url` adds a url as part of the conversation primer (before anything said on Slack) you may need to specify that it was "the reddit post I sent you earlier" etc if you've used the command in a thread.
* `!nopages` - To exclude some pages from our website that are excluded from the bot by default.
* `!tidyhq` - Some basic information for current Artifactory members.

### Elsewhere on Slack

If @queryBot is in the channel (`/invite @querybot`) you can react to a users message with `:chat-gpt:` and the bot will respond to their message. You won't be able to do follow up messages etc. However, if the message you're reacting to has one of the !commands used in the unrestricted channel then these will be executed. Please be mindful of this (especially when using `!url`)
