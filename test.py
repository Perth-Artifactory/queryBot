import json
import logging
import sys
from pprint import pprint

from slack_bolt import App

from data import workspace

logging.basicConfig(level=logging.DEBUG)

print(workspace.format_channel("bot-testing"))