import json
from pprint import pprint

with open("data.json","r") as f:
    data = json.load(f)

data["asdf"] = """asdf"""

with open("data.json","w") as f:
    json.dump(data, f, indent=4)