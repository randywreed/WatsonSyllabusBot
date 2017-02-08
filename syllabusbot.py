#author niyatip
#install before running
# sudo pip install slackclient
# sudo pip install apiclient
# sudo pip install watson-developer-cloud
# sudo pip install --upgrade google-api-python-client
# sudo pip install configparser

from __future__ import print_function
from apiclient import discovery
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1

import os
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

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

confi=configparser.ConfigParser()
confi.read('params.ini')
config=confi['P']
# starterbot's ID as an environment variable
BOT_ID = config['BOT_ID']
DM_CHANNEL=config['DM_CHANNEL']
# constants
AT_BOT = "<@" + BOT_ID + ">"

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_id.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'
CALENDAR_NAME="REL 1010 Spr 2017"

# instantiate Slack & Twilio clients
slack_client = SlackClient(config['SLACK_BOT_TOKEN'])

#instantiate workspace and context for Conversation service
WORKSPACE_ID = config['WATSON_ID']
PASSWORD= config['WATSON_PASS']
USERNAME = config['WATSON_USER']
context = {}
BOT_NAME="tajane"
#print('Slack bot id',BOT_ID)

FLOW_MAP = {}

def get_credentials(user):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart-' + user + '.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()

    return credentials

def get_auth_url(user):
    """ Creates a Flow Object from a clients_secrets.json which stores client parameters
        like client ID, client secret and other JSON parameters.

    Returns:
        Authorization server URI.
    """
    existing_flow = FLOW_MAP.get(user)
    if existing_flow is None:
        #urn:ietf:wg:oauth:2.0:oob to not redirect anywhere, but instead show the token on the auth_uri page
        flow = client.flow_from_clientsecrets(filename = CLIENT_SECRET_FILE, scope = SCOPES, redirect_uri = "urn:ietf:wg:oauth:2.0:oob")
        flow.user_agent = APPLICATION_NAME
        auth_url = flow.step1_get_authorize_url()
        print(auth_url)
        FLOW_MAP[user] = flow
        return auth_url
    else:
        return existing_flow.step1_get_authorize_url()

def set_auth_token(user, token):
    """ Exchanges an authorization flow for a Credentials object.
    Passes the token provided by authorization server redirection to this function.
    Stores user credentials.
    """
    flow = FLOW_MAP.get(user)
    if flow is not None:
        try:
            credentials = flow.step2_exchange(token)
        except oauth2client.client.FlowExchangeError:
            return -1

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart-' + user + '.json')

        store = oauth2client.file.Storage(credential_path)
        print("Storing credentials at " + credential_path)
        store.put(credentials)
        return 0
    else:
        return None

def getGoogleCalendarID(calName, service):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == calName:
                return calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
           break
def fmtDatewtime(eDate):
    return datetime.datetime.strptime(eDate['start']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S').strftime("%m-%d-%Y")

def fmtDateTime(eDate):
    return datetime.datetime.strptime(eDate['start']['date'], '%Y-%m-%d').strftime("%m-%d-%Y")

def fmtGenDateTime(eDate):
    return datetime.datetime.strptime(eDate, '%Y-%m-%d').strftime("%m-%d-%Y")


def fmtNDDateTime(eDate):
    return datetime.datetime.strftime(eDate, "%m-%d-%Y")


def fmtDateOut(eDate):
    return datetime.datetime.strptime(eDate, "%m-%d-%Y").strftime('%a, %b %d, %Y')

def calendarQuery(user, intent, entities):
    """ 
    using the date entites, query the google calendar api
    """

    responseFromCalendar = ""
    response=None

    credentials = get_credentials(user)
    searchStr=intent+":"
    searchStr=searchStr.lower()
    print('Search String=',searchStr)
    response=intent+" for "+ CALENDAR_NAME
    dataList = []
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    calID=getGoogleCalendarID(CALENDAR_NAME, service)
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    nownd=date.today()
    # create the dates we are looking for, based on entities from Watson, store in entDate
    entDate = []

    for entity in entities:
        entDate.append(fmtGenDateTime(entity['value']))
        print("entity date=", entDate)

    print('Getting the different assignments/topics/readings')
    eventsResult = service.events().list(
        calendarId=calID, timeMin=now, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if len(entities)==0: #no date included in request
        #find the first date after now
        for cevent in events:
            if 'dateTime' in cevent['start']:
                if fmtDatewtime(cevent)>=fmtNDDateTime(nownd):
                    entDate.append(fmtDatewtime(cevent))
                    break
            elif 'date' in cevent['start']:
                if fmtDateTime(cevent)>=fmtNDDateTime(nownd):
                    entDate.append(fmtDateTime(cevent['start']['date']))
                    break

    for event in events:
        if 'dateTime' in event['start']:
            #print(event['start']['dateTime'])
            eventDate=fmtDatewtime(event)
        else:
            #print(event['start']['date'])
            eventDate=fmtDateTime(event)
        print('event date= ',eventDate)
        print(event['summary'])
        if len(entDate)>1:
            if datetime.datetime.strptime(entDate[0], "%m-%d-%Y")< datetime.datetime.strptime(eventDate,'%m-%d-%Y') < datetime.datetime.strptime(entDate[1], "%m-%d-%Y"):
                #eventDate is in the window.
                if str(event['summary']).lower().find(searchStr)>=0:

                    attachmentObject = {}
                    attachmentObject['color'] = "#2952A3"
                    attachmentObject['title'] = event['summary']
                    attachmentObject['text'] = fmtDateOut(eventDate)
                    dataList.append(attachmentObject)
        else: 
            if entDate[0]==eventDate:
                if str(event['summary']).lower().find(searchStr)>=0:
                    attachmentObject = {}
                    attachmentObject['color'] = "#2952A3"
                    attachmentObject['title'] = event['summary']
                    attachmentObject['text'] = fmtDateOut(eventDate)
                    dataList.append(attachmentObject)

    if len(dataList)==0:
        response="No " +searchStr+" found for requested date(s)"

    if len(dataList)>0:
        return dataList
    else:
        attachmentObject={}
        attachmentObject['color']="#ff0000"
        attachmentObject['title']="Nothing scheduled"
        schedStr="No "+ intent+ " is scheduled for "+fmtDateOut(entDate[0])
        if len(entDate)>0:
            schedStr=schedStr+" thru "+fmtDateOut(entDate[1])
        attachmentObject['text'] = schedStr
        dataList.append(attachmentObject)
        return dataList
            
        

# def calendarUsage(user, intent):
#     """Shows basic usage of the Google Calendar API.
#
#     Creates a Google Calendar API service object and outputs a list of the next
#     10 events on the user's calendar.
#     """
#
#     responseFromCalendar = ""
#     credentials = get_credentials(user)
#
#     http = credentials.authorize(httplib2.Http())
#     service = discovery.build('calendar', 'v3', http=http)
#
#     now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
#     print('Getting the 10 upcoming events')
#     eventsResult = service.events().list(
#         calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
#         orderBy='startTime').execute()
#     events = eventsResult.get('items', [])
#
#     if intent == "schedule":
#
#         dataList = []
#         if not events:
#             dataList = 'No upcoming events found.'
#         for event in events:
#             if 'dateTime' in event['start']:
#                 start = datetime.datetime.strptime(event['start']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S").strftime("%I:%M %p, %a %b %d")
#             else:
#                 if 'date' in event['start']:
#                     start = datetime.datetime.strptime(event['start']['date'],"%Y-%m-%d").strftime("%a %b %d")
#                 else:
#                     start="whole day"
#
#
#             attachmentObject = {}
#             attachmentObject['color'] = "#2952A3"
#             attachmentObject['title'] = event['summary']
#             attachmentObject['text']= start
#             dataList.append(attachmentObject)
#             print(event['summary'])
#
#         return dataList
#
#     if intent == "free_time":
#         if not events:
#             response = "You are free all day."
#         else:
#             #grab the date of the calendar request
#             date, time = events[0]['start']['dateTime'].split('T')
#
#             #assume a starting time of 8 AM
#             checkTime = datetime.datetime.strptime(date+"T08:00:00","%Y-%m-%dT%H:%M:%S")
#             endTime = datetime.datetime.strptime(date+"T17:00:00","%Y-%m-%dT%H:%M:%S")
#             response = "You are free"
#
#             #loop over events, if they start before 5 PM check to see if there is space between the start of the event and the end of the previous
#             for event in events:
#                 print(event['start'])
#                 if 'dateTime' in event['start']:
#                     start = datetime.datetime.strptime(event['start']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S")
#                     try:
#                         checkDate
#                     except NameError:
#                         checkDate=None
#                     oldDate=checkDate
#                     checkDate =datetime.datetime.strptime(event['start']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S")
#                     if start < endTime:
#                         if start > checkTime:
#                             if oldDate!=checkDate:
#                                 response +=" on "+checkDate.strftime('%m-%d-%Y') + " from " + checkTime.strftime("%I:%M %p") + " to " + start.strftime("%I:%M %p") + ","
#                             else:
#                                 response +=" and from " + checkTime.strftime("%I:%M %p") + " to " + start.strftime("%I:%M %p") + ","
#
#                         checkTime = datetime.datetime.strptime(event['end']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S")
#
#             #if last event ends before 5 PM, set hard limit at 5. Otherwise, change sentence formatting appropriately
#                     if checkTime < endTime:
#                         response += " and from " + checkTime.strftime("%I:%M %p") + " to 05:00 PM"
#                     else:
#                         response = response[:-1]
#                         r = response.rsplit(',',1)
#                         if len(r)>1:
#                             response = r[0] + ", and" + r[1]
#                     if response == "You are fre":
#                         response = "No free times"
#                 else:
#                     if 'date' in event['start']:
#                         checkDate=datetime.datetime.strptime(event['start']['date'],"%Y-%m-%d")
#                         response +=" You may have a whole day event "+ checkDate.strftime('%m-%d-%Y')
#
#         return response
    
    
def handle_command(command, channel, user):
    """
        Receives commands directed at the bot and determines if they
        are valid commands.
        If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    #slack_client.rtm_send_message(channel,'{id=1, type="typing", channel='+channel+'}')
    attachments = ""
    response = "Not sure what you mean."
    if command.startswith("token"):
        store_status = set_auth_token(user, command[6:].strip())
        if store_status is None:
            response = "You must first start the authorization process with @"+ BOT_NAME+" hello."
        elif store_status == -1:
            response = "The token you sent is wrong."
        elif store_status == 0:
            response = "Authentication successful!You can now communicate with Watson."
    elif get_credentials(user) is None or command.startswith("reauth"):
        response = "Visit the following URL in the browser: " +  get_auth_url(user) \
                   + " \n Then send watson the authorization code like @" + BOT_NAME+" token abc123." \
                   + "\n if you are direct messaging the bot, you do not need the '@'"
    else :
        #Link to Watson Conversation as Auth is completed
        # Replace with your own service credentials
        conversation = ConversationV1(
            username= USERNAME,
            password= PASSWORD,
            version='2016-09-20',
            url="https://gateway.watsonplatform.net/conversation/api"
        )

        #Get response from Watson Conversation
        responseFromWatson = conversation.message(
            workspace_id=WORKSPACE_ID,
            message_input={'text': command},
            context=context
        )

        #Get intent of the query
        intent = responseFromWatson['intents'][0]['intent']
        #get entities from Wtson
        entities=responseFromWatson['entities']

        #Render response on Bot
        #Format Calendar output on the basis of intent of query
        # if intent == "schedule":
        #     #response = "Here are your upcoming events: "
        #     #attachments = calendarUsage(user, intent)
        #     response=None
        # elif intent == "free_time":
        #     #response = calendarUsage(user, intent)
        #
        if intent == "assignment":
             response="Assignments are:"
             attachments = calendarQuery(user, intent, entities)
        elif intent=="reading":
            response="Readings are:"
            attachments = calendarQuery(user, intent, entities)
        elif intent=="topic":
            response="Topics are:"
            attachments = calendarQuery(user, intent, entities)
        elif intent=="event":
            response="Events are:"
            attachments=calendarQuery(user, intent, entities)
        elif intent=="study_group":
            response="Study Groups:"
            attachments=calendarQuery(user, intent, entities)
        else:
            response = responseFromWatson['output']['text'][0]
        
    slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=response,
                      attachments=attachments)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        This parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        #print(output_list['text'])
        for output in output_list:
            print(output)
            try:
                if output and 'text' in output and AT_BOT in output['text']:
                    #if output and 'text' in output and (AT_BOT in output['text'] or output['channel']==DM_CHANNEL):

                    # return text after the @ mention, whitespace removed
                    return output['text'].split(AT_BOT)[1].strip(), \
                           output['channel'], output['user']
                elif output and 'text' in output and output['channel']==DM_CHANNEL and output['user']!=BOT_ID:
                    return output['text'], output['channel'], output['user']
            except KeyError:
                pass
    return None, None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        while True:
            command, channel, user = parse_slack_output(slack_client.rtm_read())
            if command and channel and user:
                handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")