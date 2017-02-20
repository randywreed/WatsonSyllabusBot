import os
import sys
import configparser
from slackclient import SlackClient


#BOT_NAME = 'tajoan'

param=sys.argv[1]
confi=configparser.ConfigParser()
confi.read(param)
config=confi['P']
SLACK_TOKEN=config['SLACK_BOT_TOKEN']
BOT_NAME=config['BOT_NAME']

slack_client = SlackClient(SLACK_TOKEN)


if __name__ == "__main__":
    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        # retrieve all users so we can find our bot
        users = api_call.get('members')
        for user in users:
            print(user.get('name')+" "+user.get('id'))
            if 'name' in user and user.get('name') == BOT_NAME:
                print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
    else:
        print("could not find bot user with the name " + BOT_NAME)
    api_call=slack_client.api_call("channels.list")
    if api_call.get('ok'):
        #retrieve all channels so we can find out bot dm
        channels=api_call.get('channels')
        for channel in channels:
            print(channel.get('name')+" ",channel.get('id'))
            if 'name' in channel  and channel.get('name')==BOT_NAME:
                print ("Bot Channel for '"+channel['name'])+ "' is "+ channel.get('id')