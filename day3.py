
# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
import requests

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template, jsonify

app = Flask(__name__)

slack_token = "xoxb-503818135714-507351131987-cwH1lExsY4VoL3tOpI9zf2mP"
slack_client_id = "503818135714.507348823507"
slack_client_secret = "8194f60277b7af2f46584293915e356b"
slack_verification = "hgtt6xtPYcb4Oq5TzDPhYFOr"
sc = SlackClient(slack_token)

def sub(a,b):
    return a-b

# 크롤링 함수 구현하기
def _crawl_naver_keywords(text):
    if text == 'Default Fallback Intent':
        return ''
    # 여기에 함수를 구현해봅시다.
    keywords = []
    titles = []
    singer = []

    sourcecode = urllib.request.urlopen('https://music.bugs.co.kr/').read()
    soup = BeautifulSoup(sourcecode, "html.parser")
    for data in soup.find_all("p", class_="title"):
        if not data.get_text() in keywords:
            if len(titles) >= 10:
                break
            titles.append(data.get_text().strip('\n'))

    for data in soup.find_all("p", class_="artist"):
        if not data.get_text() in keywords:
            if len(singer) >= 10:
                break
            singer.append(data.get_text().strip('\n'))
    for i in range(len(titles)):
        keywords.append(str(i + 1) + "위: " + titles[i] + "/" + singer[i])
    # 한글 지원을 위해 앞에 unicode u를 붙혀준다.
    return u'\n'.join(keywords)

def get_answer(text, user_key):
    data_send = {
        'query': text,
        'sessionId': user_key,
        'lang': 'ko',
    }

    data_header = {
        'Authorization': 'Bearer b9be776b160945ccb9ec1f879c9e831d',
        'Content-Type': 'application/json; charset=utf-8'
    }

    dialogflow_url = 'https://api.dialogflow.com/v1/query?v=20150910'
    res = requests.post(dialogflow_url, data=json.dumps(data_send), headers=data_header)

    if res.status_code != requests.codes.ok:
        return '오류가 발생했습니다.'

    data_receive = res.json()
    result = {
        "speech": data_receive['result']['fulfillment']['speech'],
        "intent": data_receive['result']['metadata']['intentName']
    }
    print(result)
    return result

# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    print(slack_event["event"])

    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]
        text = text[13:]
        answer = get_answer(text, 'session')

        keywords = _crawl_naver_keywords(answer['intent'])
        sc.api_call(
            "chat.postMessage",
            channel=channel,
            text= answer['speech'] + "\n" + keywords
        )

        return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)