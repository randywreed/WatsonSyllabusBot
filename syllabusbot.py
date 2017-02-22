#author niyatip
#install before running
# sudo pip install slackclient
# sudo pip install apiclient
# sudo pip install watson-developer-cloud
# sudo pip install --upgrade google-api-python-client
# sudo pip install configparser

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
import apscheduler.schedulers.background
#from apscheduler.schedulers.background import BackgroundScheduler




# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None

param=sys.argv[1]
print(param)
confi=configparser.ConfigParser()
confi.read(param)
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
CALENDAR_NAME=config['CLASS_NAME']
ATTENDANCE_NAME=CALENDAR_NAME+"_Attendance"
EXTRA_CREDIT_NAME=CALENDAR_NAME+"_Extra_Credit"

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
attendanceDict={}


def get_credentials(user):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    #credential_dir = os.path.join(home_dir, '.credentials')
    credential_dir = os.getcwd()
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
    try:
        return datetime.datetime.strptime(eDate['start']['dateTime'], '%Y-%m-%dT%H:%M:%SZ').strftime("%m-%d-%Y")
    except ValueError:
        return datetime.datetime.strptime(eDate['start']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S').strftime("%m-%d-%Y")



def fmtLongDateTime(edate):
    return datetime.datetime.strptime(eDate, '%Y-%m-%dT%H:%M:%SZ').strftime("%m-%d-%Y")


def fmtDateTime(eDate):
    return datetime.datetime.strptime(eDate['start']['date'], '%Y-%m-%d').strftime("%m-%d-%Y")

def fmtGenDateTime(eDate):
    return datetime.datetime.strptime(eDate, '%Y-%m-%d').strftime("%m-%d-%Y")


def fmtNDDateTime(eDate):
    return datetime.datetime.strftime(eDate, "%m-%d-%Y")


def fmtDateOut(eDate):
    return datetime.datetime.strptime(eDate, "%m-%d-%Y").strftime('%a, %b %d, %Y')

def MyPresQuery(user, intent, entities):
    responseFromCalendar = ""
    response=None
    fixeduser=FIXED_USER
    credentials = get_credentials(fixeduser)
    searchStr=intent+":"
    searchStr=searchStr.lower()
    print('Search String=',searchStr)
    response=intent+" for "+ CALENDAR_NAME
    dataList = []
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    calID=getGoogleCalendarID(CALENDAR_NAME, service)


    responseFromCalendar = ""
    response = None
    fixeduser = FIXED_USER
    credentials = get_credentials(fixeduser)
    searchStr = intent + ":"
    searchStr = searchStr.lower()
    print('Search String=', searchStr)
    response = intent + " for " + CALENDAR_NAME
    dataList = []
    attachList=[]
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    calID = getGoogleCalendarID(CALENDAR_NAME, service)

    eventsResult = service.events().list(
        calendarId=calID, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    # walk events and search for ['topic'] and presentation build datalist
    # first extact topic
    topic=entities[0]['value']
    searchStr=topic.lower()
    searchStr=stem(searchStr)
    for event in events:
        if str(event['summary']).lower().find(searchStr) >= 0 and str(event['summary']).lower().find("assignment")>=0 and str(event['summary']).lower().find("presentation")>=0 :
            attachmentObject = {}
            attachmentObject['color'] = "#2952A3"
            attachmentObject['title'] = event['summary']
            attachmentObject['text'] = fmtDatewtime(event)
            dataList.append(attachmentObject)
            dataList.append(event)
    # create attachments

    if len(dataList)>0:
        return dataList
    else:
        attachmentObject={}
        attachmentObject['color']="#ff0000"
        attachmentObject['title']="Nothing scheduled"
        schedStr="No "+ topic+ " is scheduled"
        attachmentObject['text'] = schedStr
        dataList.append(attachmentObject)
        return dataList

def AttendanceSet(user, intent, entities):
    gc=pygsheets.authorize(outh_file='client_secret_sheets.json', outh_nonlocal=True )
    sh=gc.open('Rel 1010 Spr 2017_Attendance')
    wks=sh[0]





def calendarQuery(user, intent, entities):
    """ 
    using the date entites, query the google calendar api
    """

    responseFromCalendar = ""
    response=None
    fixeduser=FIXED_USER
    credentials = get_credentials(fixeduser)
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
    tallyEnt=[]
    entText=[]
    entDateOnlyFlag=True
    for entity in entities:
        try:
            chekEnt=entity['value']
            entDate.append(fmtGenDateTime(chekEnt))
            tallyEnt.append(fmtGenDateTime(chekEnt))
        except ValueError:
            entText.append(entity['value'])
            entDateOnlyFlag=False
            pass

    print("entity date=", entDate)

    print('Getting the different assignments/topics/readings')
    eventsResult = service.events().list(
        calendarId=calID, timeMin=now, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if len(tallyEnt)==0: #no date included in request
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
            if datetime.datetime.strptime(entDate[0], "%m-%d-%Y")<= datetime.datetime.strptime(eventDate,'%m-%d-%Y') <= datetime.datetime.strptime(entDate[1], "%m-%d-%Y"):
                #eventDate is in the window.
                if str(event['summary']).lower().find(searchStr)>=0:
                    if entDateOnlyFlag==False and str(event['summary']).lower().find(str(entText[0]).lower())>=0:
                        attachmentObject = {}
                        attachmentObject['color'] = "#2952A3"
                        attachmentObject['title'] = event['summary']
                        attachmentObject['text'] = fmtDateOut(eventDate)
                        if 'description' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['description']
                        if searchStr.lower()=='event:' and 'location' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['location']
                        dataList.append(attachmentObject)
                    elif entDateOnlyFlag==True:
                        attachmentObject = {}
                        attachmentObject['color'] = "#2952A3"
                        attachmentObject['title'] = event['summary']
                        attachmentObject['text'] = fmtDateOut(eventDate)
                        if 'description' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['description']
                        if searchStr.lower()=='event:' and 'location' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['location']
                        dataList.append(attachmentObject)


        else: 
            if entDate[0]==eventDate:
                if str(event['summary']).lower().find(searchStr)>=0:
                    if entDateOnlyFlag == False and str(event['summary']).lower().find(str(entText[0]).lower()) >= 0:
                        attachmentObject = {}
                        attachmentObject['color'] = "#2952A3"
                        attachmentObject['title'] = event['summary']
                        attachmentObject['text'] = fmtDateOut(eventDate)
                        if 'description' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['description']
                        if searchStr.lower()=='event:' and 'location' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['location']
                        dataList.append(attachmentObject)
                    elif entDateOnlyFlag == True:
                        attachmentObject = {}
                        attachmentObject['color'] = "#2952A3"
                        attachmentObject['title'] = event['summary']
                        attachmentObject['text'] = fmtDateOut(eventDate)
                        if 'description' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['description']
                        if searchStr.lower()=='event:' and 'location' in event:
                            attachmentObject['text']=attachmentObject['text']+"\n"+event['location']
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
        if len(entDate)>1:
            schedStr=schedStr+" thru "+fmtDateOut(entDate[1])
        attachmentObject['text'] = schedStr
        dataList.append(attachmentObject)
        return dataList

def startAttendance(user, intent, entities):
    # this opens attendance by setting the attendance flag to true, and setting the attendance end time
    if user!=FIXED_USER:
        return
    global attendanceEnd
    global attendanceflag
    global holdConversationID
    global holdIntent
    global attendanceCol
    global attendanceDict
    attendanceflag=True
    for entity in entities:
        if entity['entity']=="sys-time":
            h,m,s=re.split(':',str(entity['value']))
    attendanceEnd=datetime.datetime.now()+datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    gc = pygsheets.authorize(outh_file="sheets.googleapis.com-python.json")
    sh = gc.open(ATTENDANCE_NAME)
    wks = sh[0]
    # look for current date
    # datetime_obj_pacific = timezone('Asia/Kolkata').localize(now)
    now = datetime.datetime.now()
    curdate = timezone('America/New_York').localize(now)
    curdate = curdate.strftime("%m/%d/%Y")
    datcolrow = re.findall(r'\d+', str(wks.find(curdate)))
    # pdb.set_trace()
    if len(datcolrow) == 0:
        # add date, first take row 1
        daterow=wks.get_row(1)
        newcol = len(daterow) + 1
    else:
        newcol=datcolrow[1]

    d1 = wks.cell('A1')
    d1.col = newcol
    d1.value = curdate
    attendanceMat=wks.get_col(1)
    for attend in attendanceMat:
        attendanceDict[attend]=""
    holdConversationID=""
    holdIntent=""
    attendanceCol=newcol
    scheduler=BackgroundScheduler()
    scheduler.add_job(func="closeAttendance", tigger="date", run_date=attendanceEnd )
    scheduler.start()
    scheduler.print_jobs()

    return

def closeAttendance():
    global attendanceflag
    global attendanceCol
    global attendanceDict
    print("attendance is being closed")
    attendanceflag=False
    gc = pygsheets.authorize(outh_file="sheets.googleapis.com-python.json")
    sh = gc.open(ATTENDANCE_NAME)
    wks = sh[0]
    for attend in attendanceDict:
        findvar=wks.find(attend)
        colrow = re.findall(r'\d+', str(findvar[0]))
        a1 = wks.cell('A1')
        a1.row=int(colrow[0])
        a1.col=int(attendanceCol)
        newval=attendanceDict[attend]
        a1.value=newval
        try:
            a1.value=newval
        except TypeError:
            pass
    print("attendance written to file")
    #write attendance to spreadsheet

def getAttendance(user, intent, entities, userEmail):
    # check if attendanceflg==true (attendance is open), check if attendance time has elapsed, if it has close attendance
    global attendanceEnd
    global attendanceflag
    global attendanceCol
    global attendanceDict

    if attendanceflag==True:
        if attendanceEnd>datetime.datetime.now():
            # update spread sheet
            # gc = pygsheets.authorize(outh_file='client_secret_all.json', outh_nonlocal=True)
            # sh = gc.open(ATTENDANCE_NAME)
            # wks = sh[0]
            # findvar = wks.find(str(userEmail).lower())
            #
            # import pdb
            # if len(findvar)==0:
            #     #add student to class
            #     wks.add_rows(1)
            #     newrow=wks.rows
            #     c1=wks.cell('A1')
            #     c1.row=newrow
            #     c1.value=userEmail
            # else:
            #     colrow = re.findall(r'\d+', str(findvar[0]))
            #
            #
            # # update the student with the seat number
            # a1=wks.cell('A1')
            # a1.row=int(colrow[0])
            # a1.col=int(attendanceCol)
            # newval=entities[0]['value']
            # a1.value=newval
            # try:
            #     a1.value=newval
            # except TypeError:
            #     pass

            #update attendance dict
            attendanceDict[userEmail.lower()]=entities[0]['value']
            response="Attendance has been recorded!"
            return response
        else:
            attendanceflag=False
    response="Attendance is currently closed"
    return response

def CheckAttendance(user, intent, entities, userEmail):
    #calculate attendance, absences, present and percentage
    gc = pygsheets.authorize(outh_file="sheets.googleapis.com-python.json")
    sh = gc.open(ATTENDANCE_NAME)
    wks = sh[0]
    findvar = wks.find(str(userEmail).lower())
    colrow = re.findall(r'\d+', str(findvar[0]))
    attend=wks.get_row(int(colrow[0]))
    absence=0
    present=0
    totdays=len(attend)-5
    for i in range (5, len(attend)):
        if attend[i]=="":
            absence=absence+1
        else:
            present=present+1
    response="Days Present:"+str(present)+",  Days Absent:"+str(absence)+",  Attendance Precentage:{0:.1%}".format((present/totdays))
    return response

def startEventChat(user, intent, entities, userName, userEmail, intext):
    global eventID
    global context
    global eventRow
    global totWords
    global eventProcess
    if eventID=="":
        #get eventID and create entry in spreadsheet
        now = datetime.datetime.now()
        curdate = timezone('America/New_York').localize(now)
        curdate = curdate.strftime("%m-%d-%Y-%H:%M")
        eventID=user+str(curdate)
        eventProcess[user]['event_in_process']=True
        eventProcess[user]['event_name']=False
        response="What is the name of the event?"
        botTalk("",userName,response)
        return
    else:
        if eventProcess[user]['event_name']==False:
            #create event in spreadsheet
            gc = pygsheets.authorize(outh_file="sheets.googleapis.com-python.json")
            sh = gc.open(EXTRA_CREDIT_NAME)
            wks = sh[0]
            i=1
            while wks.get_row(i)!=['']:
                i=i+1

            eventRow=i
            c1=wks.cell('A1')
            c1.row=eventRow
            c1.value=userEmail
            #sleep(0.05)
            c1.col=2
            c1.value=eventID
            #sleep(0.05)
            c1.col=3
            c1.value=intext
            eventProcess[user]['event_name']=intext
            totWords[user]=0
            response="start talking about the event. When finished send !done! in a separate message"
            botTalk("", userName, response)
            return
        else:
            # Event ID and event name set.
            # check if we have the done flage
            if intext=="!done!":
                eventProcess[user]['event_in_process']=False
                eventProcess[user]['event_name']=False
                eventID=""
                #report the number of words
                response="Event notes logged. Total words="+str(totWords[user])
                botTalk("",userName, response)
                return
            else:
                # log notes to extra credit spreadsheet
                gc = pygsheets.authorize(outh_file="sheets.googleapis.com-python.json")
                sh = gc.open(EXTRA_CREDIT_NAME)
                wks = sh[0]
                ## check if col 4 has data
                c1=wks.cell('A1')
                c1.row=eventRow
                c1.col=4
                if c1.value!="":
                    ## add row
                    c1.col=1
                    eventRow=eventRow+1
                    c1.row=eventRow
                    #sleep(0.05)
                    c1.value = userEmail
                    c1.col = 2
                    #sleep(0.05)
                    c1.value = eventID
                    c1.col=3
                    #sleep(0.05)
                    c1.value=eventProcess[user]['event_name']
                    c1.col=4
                c1.value=intext
                totWords[user]=totWords[user]+len(intext.split())
                randomResponse=['Interesting! tell me more! \n(Type !done! to end)','Is there more? \n(Type !done! to end)','I like that, what else? \n(Type !done! to end)','Hmm. I\'ll have to think about that. Keep going. \n(Type !done! to end)']
                response=random.choice(randomResponse)+"\n Total words: "+str(totWords[user])
                botTalk("",userName,response)
                return


            
        


def botTalk (output, userName, inresponse):
    if len(inresponse)>0 or len(output)>0:
         response=userName+", "+inresponse+" "
         try:
             response = response+ output['output']['text'][0]
         except:
             pass
         if len(response)>len(userName)+3:
             slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=response)
    return


def botTalkAttachments(output, userName, response, attachments):
    try:
        response = userName + ", " +response+"\n"
        if output != "":
            response=response+output['output']['text'][0]
        slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=response,attachments=attachments)
    except:
        pass
    return


def handle_command(command, channel, user):
    global context
    global holdConversationID
    global holdIntent
    global eventProcess
    """
        Receives commands directed at the bot and determines if they
        are valid commands.
        If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    #slack_client.rtm_send_message(channel,'{id=1, type="typing", channel='+channel+'}')
    waitresponse=["typing..."]

    slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=random.choice(waitresponse))

    fixeduser=FIXED_USER
    attachments = ""
    #response = "Not sure what you mean."
    response=""
    if command.startswith("token"):
        store_status = set_auth_token(fixeduser, command[6:].strip())
        if store_status is None:
            response = "You must first start the authorization process with @"+ BOT_NAME+" hello."
        elif store_status == -1:
            response = "The token you sent is wrong."
        elif store_status == 0:
            response = "Authentication successful!You can now communicate with Watson."
    elif get_credentials(fixeduser) is None or command.startswith("reauth"):
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
        # if the response is longer than 1024, truncate and hold the whole text in a holding variable
        holdCommand=""
        if len(command)>250:
            holdCommand=command
            command=command[:250]
        if holdConversationID!="":
            context['conversation_id']=holdConversationID
        responseFromWatson = conversation.message(
            workspace_id=WORKSPACE_ID,
            message_input={'text': command},
            context=context
        )
        print(responseFromWatson['context'])
        context=responseFromWatson['context']
        #Get intent of the query
        if responseFromWatson['context']['conversation_id']==holdConversationID:
            intent=holdIntent
        else:
            intent = responseFromWatson['intents'][0]['intent']
        #get entities from Wtson
        entities=responseFromWatson['entities']
        print(entities)
        userInfo=slack_client.api_call('users.info',user=user, token=SLACK_TOKEN)
        userName=userInfo['user']['profile']['first_name']
        userEmail=userInfo['user']['profile']['email']
        try:
            if eventProcess[user]['event_in_process']==True:
                intent="event_start"
            else:
                botTalk(responseFromWatson,userName,"")
        except KeyError:
            botTalk(responseFromWatson,userName,"")
            
        #if the entity is help_topics, reset the intent to help
        if len(entities)>0:
            if 'help_active' in context and context['help_active']=="True":
                intent="help"
        
        print("intent="+intent)

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
        elif intent == "individual_assignment":
            if len(entities)>0:
                if 'entity' in entities[0] and entities[0]['entity']=='topic':
                    #botTalk(responseFromWatson, userName, "")
                    response = entities[0]['value']+" Presentations:"
                    attachments = MyPresQuery(user, intent, entities)
            #else:
                #botTalk(responseFromWatson, userName,"")
        elif intent=="start_attendance":
            if len(entities)==0:
                holdConversationID=responseFromWatson['context']['conversation_id']
                holdIntent=intent
            else:
                startAttendance(user, intent, entities)
        elif intent=="attendance":
            if 'terminus' in responseFromWatson['context']:
                if responseFromWatson['context']['terminus']=='True':
                    response=getAttendance(user, intent, entities, userEmail)
                    context['terminus']="False"
        elif intent=="check_attendance":
            response=CheckAttendance(user,intent, entities, userEmail)
        elif intent=="event_start":
            if holdCommand=="":
                startEventChat(user,intent,entities,userName,userEmail,responseFromWatson['input']['text'])
            else:
                startEventChat(user, intent, entities, userName, userEmail, holdCommand)


        if len(attachments)>0:
            try:
                botTalkAttachments("", userName, response, attachments)
            except:
                response="Not sure what you mean"
                botTalk(responseFromWatson, userName, response)
                #slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=response,
                #  attachments=attachments)
        else:
            try:
                botTalk("",userName,response)
            except:
                botTalk("",userName,"Not sure what you mean, can you rephrase?")


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        This parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        #print(output_list)
        for output in output_list:
            print(output)
            try:
                if output and 'bot_id' in output:
                    return None, None, None
                if output and 'text' in output and AT_BOT in output['text'] and output['channel'][0]=="C" :
                    #if output and 'text' in output and (AT_BOT in output['text'] or output['channel']==DM_CHANNEL):
                    print(output['text'], output['type'], output['channel'], output['user'])
                    # return text after the @ mention, whitespace removed
                    return output['text'].split(AT_BOT)[1].strip(), \
                           output['channel'], output['user']
                elif output and 'text' in output and output['user']!=BOT_ID and output['channel'][0]=="D":
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

