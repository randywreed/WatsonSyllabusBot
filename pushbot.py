from __future__ import print_function
from googleapiclient import discovery
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1

import os, sys
import time

import httplib2
import json

import oauth2client
from oauth2client import client
from oauth2client import tools

import logging
logging.basicConfig()

import datetime
from datetime import date
import configparser
import random
import pygsheets
import re
from pytz import timezone
from stemming.porter2 import stem
import sys
from nested_dict import nested_dict
import threading
import time
from datetime import timedelta
#import apscheduler.schedulers.background
#from apscheduler.schedulers.background import BackgroundScheduler
import collections
import threading

from syllabusbot import get_credentials, get_auth_url, set_auth_token, calendarQuery, botTalk, botTalkAttachments
param=sys.argv[1]
print(param)
confi=configparser.ConfigParser()
confi.read(param)
config=confi['P']
# starterbot's ID as an environment variable
BOT_ID = config['BOT_ID']
#DM_CHANNEL=config['DM_CHANNEL']
# constants
AT_BOT = "<@" + BOT_ID + ">"

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_id.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'
CALENDAR_NAME=config['CLASS_NAME']
ATTENDANCE_NAME=CALENDAR_NAME+"_Attendance"
EXTRA_CREDIT_NAME=CALENDAR_NAME+"_Extra_Credit"
SEATING_CHART_NAME=CALENDAR_NAME+"Seating_chart"
SEATING_CHART_ROOM_TEMPLATE="Seating Chart Room "

# instantiate Slack & Twilio clients
SLACK_TOKEN=config['SLACK_BOT_TOKEN']
slack_client = SlackClient(SLACK_TOKEN)

#instantiate workspace and context for Conversation service
WORKSPACE_ID = config['WATSON_ID']
PASSWORD= config['WATSON_PASS']
USERNAME = config['WATSON_USER']
context = {}
BOT_NAME=config['BOT_NAME']
#print('Slack bot id',BOT_ID)
FIXED_USER=config['FIXED_USER']
FLOW_MAP = {}
attendanceflag=False
attendanceEnd=""
attendanceCol=0
holdConversationID=""
holdIntent=""
eventID=""
eventRow=0
totWords={}
eventProcess=nested_dict()
attendanceDict=collections.OrderedDict()

def return_next_tues_thur(dt):
    while True:
        dt += timedelta(days=1)
        dow = dt.strftime("%w")
        if dow == 2 | dow == 4:
           return dt

if __name__ == "__main__":
    entities={}
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        # while True:
        #     try:
        #         command, channel, user = parse_slack_output(slack_client.rtm_read())
        #     except BrokenPipeError:
        #         print("handling broken pipe error")
        #         slack_client.rtm_connect()
        #     if command and channel and user:
        #         handle_command(command, channel, user)
        #     time.sleep(READ_WEBSOCKET_DELAY)
        # query events and post to chatbot
        # set date for today (%Y-%m-%d)
        now=datetime.datetime.now()
        now=now.strftime('%Y-%m-%d')
        intent="Assignment"
        entities['value']=now
        attachments=calendarQuery("@Everyone", intent,entities)
        botTalkAttachments("","<!everyone>","Assignments for Today are:", attachments)
        intent="Event"
        attachments=calendarQuery("@Everyone", intent,entities)
        botTalkAttachments("","<!everyone>","Events for Today are:", attachments)
        tomorrow=datetime.datetime.now()+timedelta(days=1)
        #tomorrow=tomorrow.strptime("%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d')
        nextclass=return_next_tues_thur(tomorrow)
        intent="Reading"
        entities['value']=nextclass
        attachments=calendarQuery("@everyone", intent, entities)
        botTalkAttachments("","<!everyone>", "Readings for next class are:", attachments)




    else:
        print("Connection failed. Invalid Slack token or bot ID?")
