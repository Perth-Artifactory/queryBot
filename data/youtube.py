import json
import logging
import os
from datetime import datetime
from pprint import pprint

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

# import our config from config.json
with open('config.json') as f:
    config = json.load(f)

def get_subtitles(video: str):
    """Accepts a YouTube video ID or URL and returns a list of strings containing the subtitles for the video"""

    # If we were given a YouTube URL, extract the video ID
    if 'youtube.com' in video:
        video = video.split('v=')[1]

    # Get the subtitles for the video
    try:
        subtitles = YouTubeTranscriptApi.get_transcript(video)
    except Exception as e:
        logging.error(f'Error getting YouTube subtitles for {video}: {e}')
        return []
    # Iterate over the subtitles and return a list of strings that aren't empty
    return [subtitle['text'] for subtitle in subtitles if subtitle['text']]

def get_metadata(video: str) -> dict:
    """Accepts a YouTube video ID or URL and returns a dict containing the video title and description"""

    # If we were given a video ID, convert it to a URL
    if 'youtube.com' not in video:
        video = f'https://www.youtube.com/watch?v={video}'
      
    r = requests.get(video)
    s = BeautifulSoup(r.text, "html.parser")
    title = s.find("meta", attrs={"name": "title"})["content"]
    description = s.find("meta", attrs={"name": "description"})["content"]
    return {"title":title,
            "description":description,}

def format_video(pagedata: dict) -> str:
    """Accepts a YouTube video ID or URL and returns a string containing the video title and description"""

    video = pagedata["url"]
    metadata = get_metadata(video)
    subtitles = get_subtitles(video)

    # If we couldn't get the metadata or subtitles, return an empty string
    if not metadata or not subtitles:
        logging.error(f'Error formatting YouTube video {video}')
        return ''
    
    # Format the video title and description
    s = f'This is the transcription of a YouTube video titled "{metadata["title"]}"\n---\n'
    # add the subtitles to the string
    s += '\n'.join(subtitles)
    return s