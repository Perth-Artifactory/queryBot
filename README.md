# queryBot

This bot exposes `gpt-3.5-turbo` as a Slack service. It is preprimed to assist with Artifactory related queries and has access to some specific data such as:

* The Artifactory website and wiki
* Specific URLs (With extra support for Reddit and GitHub)
* YouTube Videos
* Google Calendars
* Slack channel metadata and recent public messages
* TidyHQ contact info

## Demo

On the Artifactory Slack team:

* [@queryBot]() - Running the latest [release](https://github.com/Perth-Artifactory/queryBot/releases).
* [@queryBot-dev]() - Running `main`

## Installation

### Server

* Have at least Python 3.9
* Set up a virtual environment if you want
* `pip install -r requirements.txt`
  * `openai` - Access to GPT
  * `slack_bolt` Access to Slack's API
  * `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib` - Credential negotiation and access to Google's API
  * `praw` - Access to Reddit's API
  * `slack_logger` - Send error messages over Slack
  * `beautifulsoup4`, `youtube_transcript_api` - Processing information regarding YouTube videos

### OpenAI

Create an account and generate an API token. Place in `./key`

### Slack

* Create a Slack application using `./rsc/slack.manifest.json`
* Add an app level token with `connections:write` and save the app token
* Install the app to your workspace and save the bot token
* Add the :chat-gpt: emoji from `./rsc/chat-gpt.png` or `./rsc/chat-gpt_animated.png` as a custom emoji

## Configuration

* `./key` - your OpenAI token
* `./rsc/config.json.example` -> `config.json`
   * `unrestricted_channels` - A list of slack channel IDs for unrestricted channels. Remember that access to these channels includes an ability to cost you money. 
   * `app_token` - Your slack app token 
   * `bot_token` - Your slack bot token
   * `reddit_id` (optional) - Create a [reddit personal use script](https://www.reddit.com/prefs/apps)
   * `reddit_secret` (optional) - As above
   * `tidyhq_token` (optional) - TidyHQ API token
   * `calendar_id` (optional) - The ID for the google calendar you want the bot to know about
   * `urls` - Any web pages you want the bot to know about. See description of `!url` below for details on sites with specific processors.
   * bot
     * `dev [true|false]` - Skips some time/resource intensive data gathering
     * `debug [true|false]` - Outputs debugging data
     * `slack_error_webhook` - Sends logging data to a slack webhook
     * `name` - The name of the bot in Slack
     * `org_name` - Your organisation name (used in various prompts etc)
     * `restricted_commands` - Commands that should only be triggered by @bot tags. (and thus only in `unrestricted_channels`)
    * `aliases` - A mapping of aliases to expanded command sets. The alias does not include a `!` but the command sets do.
    * `channel_maps` - A mapping of channels to commands. When a response is triggered via emoji in a listed channel the mapped command will be apended.
* Run `auth_google.py` to authenticate with google for upcoming events
* `./rsc/prompts.txt.example` -> `prompts.txt`
  * Add lines that should always be added to the bot. The first line is the system prompt and tells the bot what it is and what it's broadly expected to do. OpenAI has a [decent page](https://platform.openai.com/docs/guides/chat/instructing-chat-models) on system prompts.
  * The following templates can be used: (eg. "You are {bot_name} run by {org_name}. It is {date} {time}.")
    * `{bot_name}`
    * `{org_name}`
    * `{date}`
    * `{time}`
  
## Running

`python slack.py`

## Usage

Please only use the bot for Artifactory tasks, while it is relatively cheap to run it's not free.

* The bot will very confidently be completely wrong if it doesn't know the answer to a question. Make sure you fact check any replies before using them elsewhere. It will go so far as to create fictious URLs and businesses.
* It has a a pretty good understanding of upcoming events and pages on our main website. It can access specific pages on the wiki as well but it doesn't always do so well with markdown tables.
* If something is wrong about the message, like the tone etc, ask the bot to change it.
* If you find that you're adding the same instruction frequently (like "We refer to ourselves as The Artifactory rather than Perth Artifactory Inc") let @Fletcher know and we may be able to include it in the priming.

### In unrestricted channels

Send a message to this channel that tags @queryBot to begin a conversation. Your message should include your complete initial request. If you need to send follow up messages in the same conversation, like correcting details, then reply in a thread and tag @queryBot in the message. Any messages in the thread that do not tag @queryBot will be ignored. This allows us to discuss a response without @queryBot getting confused.

Add the following to a message and the bot should get some info about that category to help inform its answer.

* `!calendar` - The next 20 events if Google Calendar is configured.
* `!slackpopular` - Some basic information about public slack channels with over 30 people
* `!slackmsg` - The last 30 messages in any channels mentioned during the conversation **provided that the bot is in the mentioned channel**
* `!url-https://your.url` - Information from a custom provided URL. It won't handle big pages or pages with lots of javascript etc. There is some custom logic specifically for our [website](https://artifactory.org.au)/[wiki](https://wiki.artifactory.org.au), Github, Reddit (with credentials set), and YouTube which allow it to download a "cleaner" version of the page. If you're using a url that's not on those domains you may have more success if you use a "raw" version of the page (like the source view on a wiki etc). Because `!url` adds a url as part of the conversation primer (before anything said on Slack) you may need to specify that it was "the reddit post I sent you earlier" etc if you've used the command in a thread. 
* `!nopages` - To exclude some pages from our website that are included by default.
* `!tidyhq` - Some basic information for current Artifactory members if a TidyHQ token is present. Should be fairly organisation agnostic.

### Elsewhere on Slack

If @queryBot is in the channel (`/invite @querybot`) you can react to a users message with `:chat-gpt:` and the bot will respond to their message. You won't be able to do follow up messages etc. However, if the message you're reacting to has one of the !commands used in the unrestricted channel then these will be executed. Please be mindful of this (especially when using `!url`)

The bot will react with :+1: and :-1: to every message it sends using this method. This makes the feature below easier to use.

Sometimes the bot gets an answer wrong and you may not have permissions on Slack to delete an incorrect message. If you react with a :-1: the bot will replace it's answer with a removal message. If you react with a :+1: it will remove it's own approval emoji from the message to reduce the likelyhood that other users will misclick.

## Understanding conversation order

It's important to understand how commands affect the conversation so that you can communicate effectively with the bot. Sometimes you'll want to reference a url you just gave the bot but it will claim not to know about it. This is because of the built in conversation order.

Before the conversation you see in Slack happens there's a conversation that's gone on in the background.

1. A system prompt - This gives the bot a good idea of what it is and what it's expected to do overall. As an example ChatGPT uses the system prompt "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."
2. Hardcoded follow up prompts in `prompts.txt` - This is typically supplementary information that is useful for most conversations like "We refer to the organisation as 'The Artifactory'"
3. The contents of webpages from `urls` in `config.json` unless `!nopages` is used - Giving the bot access to a webpage containing basic information about the organisation will help most conversations. The exception is when you know that another command you're sending will provide the exact information required. In that instance sending `!nopages` will exclude these pages and save you tokens.
4. The output of any `!commands` you've added anywhere in the conversation - No matter where in the conversation the command was used they output will always end up here instead. **This is what causes the issue raised at the start of this section**
5. The visible conversation from slack - This *excludes* thread replies that don't tag the bot when you're in a unrestricted channel and *only includes* the message you reacted to if it's an emoji triggered response.

A good way to reference command information is to say "That webpage I gave you earlier" etc. As far as the bot is concerned everything except the system prompt actually came from you.
