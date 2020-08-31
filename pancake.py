from flask import Flask, render_template, send_from_directory, jsonify, request, redirect
import requests
import json
import sqlite3
import random
import time
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from astral import LocationInfo
from astral.sun import sun

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def welcome():
    return render_template('index.html')

@app.route('/groupme/activate', methods=['GET', 'POST'])
def activate():
    accesstoken = request.args.get('access_token')

    headers = {
        'content-type': 'application/json',
        'x-access-token': accesstoken
    }

    getInfo = requests.get('https://api.groupme.com/v3/users/me', headers=headers)
    getInfo = getInfo.json()['response']
    name = getInfo['name']
    email = getInfo['email']
    phone = getInfo['phone_number']
    user_id = getInfo['user_id']

    chatName = []
    params = {"per_page": 100}
    groups = requests.get('https://api.groupme.com/v3/groups', headers=headers, params=params)
    groups = groups.json()
    chatCount = 0
    for x in groups['response']:
        chatCount += 1
        if x['creator_user_id'] == user_id:
            chatName.append(f"{x['group_id']} - {x['name']}")

    for x in chatName:
        print(x.split("-")[0].strip())

    conn = sqlite3.connect('pancake.db')
    c = conn.cursor()
    for row in c.execute(f"SELECT * FROM chats WHERE token = ?", (accesstoken,)):
        for x in chatName:
            if row[1] == x.split("-")[0].strip():
                chatName.remove(x)
    c.close()

    return render_template("activate.html", chatName=chatName, name=name, email=email, phone=phone, chatCount=chatCount, accesstoken=accesstoken)

@app.route('/middleman', methods=['GET', 'POST'])
def redirection():
    accesstoken = request.args.get('tok')
    group = request.args.get('group')
    try:
        group = group.split("-")[0].strip()
        print(group)
    except:
        return redirect("https://pancakebot.me/groupme/error?errormsg=no+group+selected")
    checkbox = request.args.get('checkbox')

    headers = {
        'content-type': 'application/json',
        'x-access-token': accesstoken
    }

    params = {"bot[name]":"Pancake","bot[group_id]":group,"bot[avatar_url]":"https://i.groupme.com/256x256.png.4cf0628a26b3470e9c73d627b85d39cf.avatar","bot[callback_url]":"https://pancakebot.me/pancake"}
    create = requests.post('https://api.groupme.com/v3/bots', headers=headers,params=params)
    try:
        botId = json.loads(create.content)['response']['bot']['bot_id']
    except:
        return redirect("https://pancakebot.me/groupme/error?errormsg=pancake+already+exists+in+selected+groupchat")

    conn = sqlite3.connect('pancake.db')
    c = conn.cursor()
    c.execute("INSERT INTO chats (token,id,botid) VALUES (?,?,?)", (accesstoken,group,botId))
    conn.commit()
    c.close()


    return redirect("groupme/success", code=302)

@app.route('/groupme/success', methods=['GET', 'POST'])
def success():
    return render_template('success.html')

@app.route('/groupme/error', methods=['GET', 'POST'])
def error():
    errormsg = request.args.get("errormsg")
    return render_template('error.html', errormsg=errormsg)

@app.route('/groupme/terms', methods=['GET', 'POST'])
def terms():
    return render_template('terms.html')

@app.route('/discord/error', methods=['GET', 'POST'])
def discorderror():
    return('coming soon')

@app.route('/commands', methods=['GET', 'POST'])
def commands():
    return('coming soon')

@app.route('/faq', methods=['GET', 'POST'])
def faq():
    return('coming soon')

@app.route('/pancake', methods=['GET', 'POST'])
def gmAll():
    # initialize
    data = request.get_json()
    data['text'] = data['text'].strip()
    message = data['text'].split()
    count = 0
    send = None
    
    # find bot id
    conn = sqlite3.connect('pancake.db')
    c = conn.cursor()
    for row in c.execute(f"SELECT * FROM chats WHERE id = ?", (data['group_id'],)):
        botid = row[2]
        accesstoken = row[0]

    try:
        botid     
    except:
        print("invalid group")
        return("invalid group")

    headers = {
        'content-type': 'application/json',
        'x-access-token': accesstoken
    }

    getInfo = requests.get('https://api.groupme.com/v3/users/me', headers=headers)
    getInfo = getInfo.json()['response']
    user_id1 = getInfo['user_id']

    c.close()

    if data['sender_type']=='system':
        if "added the Pancake bot" in data['text']:
            time.sleep(0.5)
            send = "Hi! I'm Pancake. I'm a fun GroupMe bot designed to spice up any groupchat!\n\nHere are a list of commands:\n\np!lmgtfy {search term}\np!pick {option 1},{option 2}\np!coinflip\np!urban {search term}\np!love {firstname1} {firstname2}\np!madgab (use command twice)\np!8ball {your question}\np!sun\np!joke\n\np!help\np!leave (can only be used by owner)\np!ban/p!unban @whoever (can only be used by owner)\n\nI highly recommend using p!madgab to start some friendly competition in this groupchat!"
 
    if data['sender_type']=='user':

        conn = sqlite3.connect('databases/banned.db')
        c = conn.cursor()

        adminList = []
        for row in c.execute(f"SELECT * FROM banned"):
            adminList.append(row[0])
        if int(data['user_id']) in adminList:
            return("banned user")
        
        c.close()

        conn = sqlite3.connect('databases/whitelist.db')
        c = conn.cursor()
        adminList = []
        for row in c.execute(f"SELECT * FROM white WHERE group_id = ?", (data['group_id'],)):
            adminList.append(row[0])

        if data['user_id'] == user_id1:
            pass
        elif adminList == []:
            pass
        elif data['user_id'] not in adminList:
            return("banned user")
        
        c.close()

        if ((str(message[0])) == 'p!ban') and (str(data['sender_id'])==user_id1):
            conn = sqlite3.connect('databases/banned.db')
            c = conn.cursor()
            try:
                for x in data['attachments'][0]['user_ids']:
                    c.execute("INSERT INTO banned (user_id) VALUES (?)", (x,))
                    conn.commit()
                send = f"banned member"
            except Exception as e:
                print(str(e))
                send = "error"
            c.close()
        elif ((str(message[0])) == 'p!unban') and (str(data['sender_id'])==user_id1):
            conn = sqlite3.connect('databases/banned.db')
            c = conn.cursor()
            try:
                send = None
                for x in data['attachments'][0]['user_ids']:
                    c.execute("DELETE FROM banned WHERE user_id = ?", (x,))
                    conn.commit()
                    send = "unbanned member"
                if send == None:
                    send = "member was not banned"
            except:
                send = "error"
            c.close()
        elif ((str(message[0])) == 'p!whitelist') and (str(data['sender_id'])==user_id1):
            if message[1].lower() == "add":
                conn = sqlite3.connect('databases/whitelist.db')
                c = conn.cursor()
                try:
                    for x in data['attachments'][0]['user_ids']:
                        c.execute("INSERT INTO white (user_id, group_id) VALUES (?,?)", (x,data['group_id']))
                        conn.commit()
                    send = f"added member to whitelist"
                except Exception as e:
                    print(str(e))
                    send = "error"
                c.close()
            if message[1].lower() == "remove":
                conn = sqlite3.connect('databases/whitelist.db')
                c = conn.cursor()
                try:
                    send = None
                    for x in data['attachments'][0]['user_ids']:
                        c.execute("DELETE FROM white WHERE user_id = ? and group_id = ?", (x,data['group_id']))
                        conn.commit()
                        send = "removed member"
                    if send == None:
                        send = "member was not removed"
                except Exception as e:
                    print(str(e))
                    send = "error"
                c.close()
            if message[1].lower() == "off":
                conn = sqlite3.connect('databases/whitelist.db')
                c = conn.cursor()
                try:
                    c.execute("DELETE FROM white WHERE group_id = ?", (data['group_id'],))
                    conn.commit()
                    send = "whitelist off"
                except:
                    send = "error"
                c.close()


        #leave
        if message[0].lower() == 'p!leave' and data['user_id']==user_id1:
            conn = sqlite3.connect('pancake.db')
            c = conn.cursor()
            c.execute("DELETE FROM chats WHERE id = ?", (data['group_id'],))
            conn.commit()
            c.close()

            params = {"bot_id":botid,"text":"pancake is shutting down"}
            create = requests.post('https://api.groupme.com/v3/bots/post', headers=headers, params=params)

            params = {"bot_id":botid}
            create = requests.post('https://api.groupme.com/v3/bots/destroy', headers=headers, params=params)
            return("removed")
        if message[0].lower() == 'p!help':
            send = "Hi! I'm Pancake. I'm a fun GroupMe bot designed to spice up any groupchat!\n\nHere are a list of commands:\n\np!lmgtfy {search term}\np!pick {option 1},{option 2}\np!coinflip\np!urban {search term}\np!love {firstname1} {firstname2}\np!madgab (use command twice)\np!8ball {your question}\np!sun\np!joke\n\np!help\np!leave (can only be used by owner)\np!ban/p!unban @whoever (can only be used by owner)\n\nI highly recommend using p!madgab to start some friendly competition in this groupchat!"
        #lmgtfy
        if message[0].lower() == 'p!lmgtfy':
            message.pop(0)
            send = "https://lmgtfy.com/?q=" + '+'.join(message)
        #choose
        elif message[0].lower() == 'p!pick':
            text = data['text'][6:].split(",")
            for i in range(len(text)):
                text[i] = text[i].strip()
            num = random.randint(0,len(text)-1)
            
            send = "i pick \"" + text[num] + "\""
        #coinflip
        elif message[0].lower() == 'p!coinflip':
            num = random.randint(0,11)
            listOne = [0,1,2,3,4,5]
            listTwo = [6,7,8,9,10,11]
            if num in listOne:
                send = "Heads"
            elif num in listTwo:
                send = "Tails"
        #urban
        elif message[0].lower() == 'p!urban':
            message.pop(0)
            urbanTerm = ' '.join(message)
            urban = requests.get(f"http://api.urbandictionary.com/v0/define?term={urbanTerm}")
            try:
                send = urban.json()['list'][0]['definition']
            except IndexError:
                send = f"couldn't find a definition for {urbanTerm}"
        #love
        elif message[0].lower() == 'p!love':
            try:
                first = message[1].lower()
                second = message[2].lower()
                love = requests.get(f"https://www.lovecalculator.com/love.php?name1={first}&name2={second}")
                lovesoup = BeautifulSoup(love.text, "lxml")
                score = lovesoup.findAll("div", {"class": "result__score"})[0].text.strip()
                send = score
            except:
                send = "invalid syntax"
        #madgab
        elif message[0].lower() == 'p!madgab':
            conn = sqlite3.connect('databases/madgab.db')
            c = conn.cursor()

            questions = []
            answers = []
            channels = []
            requestions = []

            for x in open("databases/question.txt", "r"):
                questions.append(x)
            for x in open("databases/answer.txt", "r"):
                answers.append(x)
            for row in c.execute(f"SELECT * FROM gameplay"):
                channels.append(row[0])
                requestions.append(row[1])
            
            if data['group_id'] in channels:
                active = True
            else:
                active = False

            if active == True:
                sendAnswer = 0
                for x in range(len(channels)):
                    if data['group_id'] == channels[x]:
                        sendAnswer = answers[int(requestions[x])] 

                c.execute("DELETE FROM gameplay WHERE channel = ?", (data['group_id'],))
                conn.commit()
                send = sendAnswer
            else:
                num = random.randint(0,len(questions)-1)
                c.execute("INSERT INTO gameplay (channel,question) VALUES (?,?)", (data['group_id'],num))
                conn.commit()
                send = questions[num]

            c.close()
        elif message[0].lower() == 'p!8ball':
            responses = [
                'Don’t count on it.',
                'It is certain.',
                'It is decidedly so.',
                'Most likely.',
                'My reply is no.',
                'My sources say no.',
                'Signs point to yes.',
                'Very doubtful.',
                'Without a doubt.',
                'Yes.',
                'Yes – definitely.',
                'You may rely on it.',
                'As I see it, yes.',
                'Ask again later.',
                'Better to not tell you now.',
                'Cannot predict now.',
                'Concentrate and ask again.'
            ]
            send = random.choice(responses)
        elif message[0].lower() == "p!sun": 
            city_name = 'Atlanta'
            city = LocationInfo()
            city.latitude = 33.7490
            city.longitude = -84.3880
            city.timezone = 'US/Eastern'
            s = sun(city.observer, date=datetime.now(), tzinfo=city.timezone)
            send = f"Sun Info For Atlanta\n\nDawn:    {s['dawn'].strftime('%I:%M %p')}\nSunrise: {s['sunrise'].strftime('%I:%M %p')}\nNoon:    {s['noon'].strftime('%I:%M %p')}\nSunset:  {s['sunset'].strftime('%I:%M %p')}\nDusk:    {s['dusk'].strftime('%I:%M %p')}\n"
        elif message[0].lower() == "p!joke":
            jheaders = {
                'User-Agent': 'curl/7.55.1'
            }
            joke = requests.get("https://icanhazdadjoke.com/", headers=jheaders)
            send = joke

        if send != None:
            params = {"bot_id":botid,"text":send}
            create = requests.post('https://api.groupme.com/v3/bots/post', headers=headers, params=params)
            return("message received")

    if send != None:
        params = {"bot_id":botid,"text":send}
        create = requests.post('https://api.groupme.com/v3/bots/post', headers=headers, params=params)

    return("message received!")