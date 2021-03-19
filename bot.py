#!/usr/bin/env python

'''
    Slack bot to query price/details of a stock symbol
    Author: Omar Busto Santos 
    Date created: 02/13/2021
'''

import os
import logging
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
from flask import Flask
import stock

# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)

# Initialize a Web API client
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# Timestamp of the latest message processed
# NOTE: Mainly for heroku since the service dies after 1h on the free tier and when waking up it sometimes it gets older messages
last_processed = 0

def check_processed(ts):
    """Checks if a timestamp of a message is newer than the last processed"""
    global last_processed
    if ts > last_processed:
        last_processed = ts
        return True
    return False

def get_message_payload(channel_id, msg):
    """Gets the message payload to be sent in the post message api"""
    return {
        "ts": "",
        "channel": channel_id,
        "username": "Market Bot",
        "attachments": [ 
            msg
        ]
    }

def send_price_msg(channel_id, details):
    """Sends price message to the channel"""    
    if details['change'].startswith('-'):
        trend = ":chart_with_downwards_trend:"
        indicator = ":red_circle:"
        color = "#FF0000"
        details['change'] = details['change'].replace("-", "-$")
    else:
        trend = ":chart_with_upwards_trend:"
        indicator = ":large_green_circle:"
        color = "#00FF00"
        details['change'] = "$" + details['change']

    msg = {
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{0} ({1})  {2}".format(details['name'], details['symbol'], indicator),
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Current Price:* ${0}".format(details['current'])
                    },
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Previous Close Price:*"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Change:*"
                        },
                        {
                            "type": "plain_text",
                            "text": "${0}".format(details['previous'])
                        },
                        {
                            "type": "plain_text",
                            "text": "{0} ({1}) {2}".format(details['change'], details['percent'], trend)
                        }
                    ]
                }
            ]
        }
    payload = get_message_payload(channel_id, msg)
    client.chat_postMessage(**payload)

@slack_events_adapter.on("message")
def message(payload):
    """Parse channel messages looking for stock symbols"""
    event = payload.get("event", {})
    text = event.get("text")
    channel_id = event.get("channel")
    ts = payload.get("event_time")

    if check_processed(ts) and text:
        symbols = re.findall(r'\$\b[a-zA-Z]+\b', text)
        for symbol in symbols:            
            details = stock.query_symbol_details(symbol[1:])
            send_price_msg(channel_id, details)

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)