import json

import praw

with open("config.json","r") as f:
    config: dict = json.load(f)

if not config.get("reddit_id") and config.get("reddit_secret"):
    def format_post(post):
        return f'You can\'t access {post} because you\'re not configured to access Reddit URLs.'
else:
    reddit = praw.Reddit(
        client_id=config["reddit_id"],
        client_secret=config["reddit_secret"],
        user_agent="queryBot (by u/FletcherAU)",
    )

    def format_post(post: str) -> str:
        data = get_post(post)
        s = f'This is a reddit post by /u/{data["submission"].author.name} titled "{data["submission"].title}"\n{data["submission"].selftext}\n---'
        s += "\nThese are the first 20 comments"
        for comment in data["comments"][:20]:
            s += f"\n/u/{comment[0]} says: {comment[1]}"
        return s

    def get_post(url: str) -> dict:
        submission = reddit.submission(url=url["url"])
        submission.comments.replace_more(limit=None)
        data = {"submission":submission,"comments":[]}
        for comment in submission.comments:
            if comment.author:
                if comment.author.name != "AutoModerator":
                    data["comments"].append((comment.author.name,comment.body))
        return data