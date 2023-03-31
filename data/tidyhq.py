import json
import logging
from datetime import datetime
from pprint import pprint
from typing import Optional, Union

import requests

with open("config.json","r") as f:
    config: dict = json.load(f)

token = config["tidyhq_token"]
contacts_url = "https://api.tidyhq.com/v1/contacts"
membership_url = "https://api.tidyhq.com/v1/membership_levels/{}/memberships"
membership_full_url = "https://api.tidyhq.com/v1//memberships"
contact_membership_url = "https://api.tidyhq.com/v1/contacts/{}/memberships"

def get_contact(id: str) -> dict:
    """Returns a dict containing the contact data for the TidyHQ contact with the given ID
    Currently breaks if the contact does not exist"""
    r = requests.get(contacts_url+"/"+str(id),params={"access_token":token})
    member = r.json()
    return member

def get_groups(contact: dict) -> list:
    """Returns a list of group IDs that the contact is in"""
    g = []
    for group in contact["groups"]:
        g.append(group["id"])
    return g

def get_memberships(id: Union[str, int], raw: bool = False) -> list[dict]:
    """Returns a list of membership dicts for the contact with the given ID
    Pass raw=True to return the raw data or raw=False to return a list of membership_level_ids"""
    r = requests.get(contact_membership_url.format(id),params={"access_token":token})
    memberships = r.json()
    if raw == True:
        return memberships
    m = []
    for membership in memberships:
        m.append(membership["membership_level_id"])
    return m

def time_since_membership(memberships: list[dict]) -> int:
    """Returns the number of days since the most recent membership expired
    Negative numbers indicate that the membership is still active"""
    newest = 60000
    for membership in memberships:
        try:
            date = datetime.strptime(membership["end_date"], "%Y-%m-%d")
        except ValueError:
            try:
                date = datetime.strptime(membership["end_date"], "%d-%m-%Y")
            except ValueError:
                print(membership)
        since = int((datetime.now()-date).total_seconds()/86400)
        if since < newest:
            newest = int(since)
    return newest

def format_tidyhq(message: Optional[str] = None) -> str:
    """Returns a string containing basic information about TidyHQ contacts that hold active memberships formatted for feeding into GPT"""
    if config["bot"]["dev"]:
        logging.info("TidyHQ data requested but not grabbed in development mode")
        return "Data not grabbed because we're running in development mode"
    logging.info("Getting TidyHQ data")
    r = requests.get(membership_full_url,params={"access_token":token})
    memberships = r.json()
    m_strings = f'These are the current members of {config["bot"]["org_name"]} (from TidyHQ)'
    for membership in memberships:
        if membership["state"] != "expired":
            contact = get_contact(membership["contact_id"])
            m_name = membership["membership_level"]["name"].split(" ")[0]
            
            # Get start date, not currently used due to token limit
            try:
                start_date = datetime.strptime(membership["start_date"], "%Y-%m-%dT%H:%M:%S+08:00")
            except ValueError:
                try:
                    start_date = datetime.strptime(membership["start_date"], "%d-%m-%Y")
                except ValueError as e:
                    print(e)
                    pprint(membership)

            # Index custom field data
            c_data = {}
            for field in contact["custom_fields"]:
                if type(field["value"]) == str:
                    c_data[field["title"]] = field["value"]
                elif type(field["value"]) == list and field["value"]:
                    c_data[field["title"]] = field["value"][0]["title"]

            s = ""
            # Name and membership
            s += f'{contact["first_name"]} {contact["last_name"]} is a {m_name} '

            # Contact
            s += f'Phone: {contact["phone_number"]} emergency contact: {contact["emergency_contact_person"]} ({contact["emergency_contact_number"]}) '

            # Join date, not used due to token limit
            #s += f'They first joined {config["bot"]["org_name"]} {start_date.strftime("%Y-%m-%d")} '

            # Locker assignment
            if "Locker assignment" in c_data:
                s += f'locker is {c_data["Locker assignment"]} '
            else:
                s += 'no locker '
                
            # Key assignment
            if "RFID Issued Key Tag Status" in c_data:
                s += "has 24/7"
            else:
                s += "no 24/7"
            m_strings += "\n"+s
    return m_strings