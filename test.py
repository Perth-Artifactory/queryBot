import json
from slack_bolt import App
from pprint import pprint
import logging
import sys

from data import workspace

logging.basicConfig(level=logging.DEBUG)

print(workspace.format_channel("bot-testing"))