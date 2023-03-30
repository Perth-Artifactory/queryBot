from datetime import datetime
import os.path
import json
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

with open("config.json","r") as f:
    config = json.load(f)

def pull_events():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar.readonly'])
    if not creds:
        logging.error("You need to run auth_google.py")
    elif not creds.valid:
        logging.warn("Google credentials invalid?")
    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        logging.info("Pulling calendar")
        events_result = service.events().list(calendarId=config["calendar_id"], timeMin=now,
                                              maxResults=20, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        logging.debug(f'Got {len(events)} events')

        if not events:
            return []
        return events

    except HttpError as e:
        return []

def format_events(message=None):
    s = f'The time right now is {datetime.now()}. These are the next 20 events:'
    descriptions = {}
    for event in pull_events():
        f = '%Y-%m-%dT%H:%M:%S+08:00'
        start_dt = datetime.strptime(event["start"]["dateTime"], f)
        end_dt = datetime.strptime(event["end"]["dateTime"], f)
        start_f = "%H:%M on %A %d %B"
        end_f = "%H:%M"
        s += f'\n{event["summary"]} starts at {start_dt.strftime(start_f)} until {end_dt.strftime(end_f)}'
        if event["summary"] not in descriptions:
            descriptions[event["summary"]] = event["description"]
    s += "\nThese are a the descriptions for the events listed above."
    for description in descriptions:
        s += "\n" + description
        s += "\n" + descriptions[description]
        s += "\n------"
    return s