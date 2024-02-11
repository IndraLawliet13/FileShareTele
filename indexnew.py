from telethon import TelegramClient, events, Button, functions
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import *
import asyncio, json, base64, re, random, time
from datetime import timedelta

# Data Bot
data = json.loads(open("config.json", 'r', encoding='utf-8').read())
api_id = int(data["api_id"])
api_hash = data["api_hash"]
token = data["bot_token"]
grupDB = data["grupDB"]

client = TelegramClient('session/filesharebot', api_id, api_hash, use_ipv6=False).start(bot_token=token)

async def isPrem(user_id: int):
    with open("premusers.json", "r+", encoding="utf-8") as f:
        users = json.loads(f.read())
        if str(user_id) in users:
            if int(time.time()) > users[f"{user_id}"]["expired"]:
                del users[f"{user_id}"]
                with open("premusers.json", "w", encoding='utf-8') as f:
                    f.write(json.dumps(users, indent=4, ensure_ascii=False))
                return False
            else: return True
        else: return False

async def checkDuration(user_id: int):
    if await isPrem(user_id):
        with open("premusers.json", "r+", encoding="utf-8") as f:
            expired = json.loads(f.read())[f"{user_id}"]["expired"]
            return timedelta(seconds=expired-int(time.time()))
    else: return 0

async def addPrem(user_id: int, expired: int):
    with open("premusers.json", "r+", encoding="utf-8") as f: users = json.loads(f.read())
    users.update({f"{user_id}": {"expired": expired}})
    with open("premusers.json", "w", encoding='utf-8') as f: f.write(json.dumps(users, indent=4, ensure_ascii=False))
    return

async def cek():
    mode = 0
    cf = json.loads(open("config.json", "r", encoding="utf-8").read())
    chgc = cf["chgc"]
    # check number of joined
    semua = []
    ch_belum_selesai = []
    for a in chgc:
        ch = a["ch"]
        target = int(a["target"])
        if target == 0:
            ch_belum_selesai.append(a)
            semua.append(f"ch {ch} tidak ada batasan subs")
            continue
        try: count = (await client(GetFullChannelRequest(channel=ch))).full_chat.participants_count
        except: count = 0
        if int(count) > target:
            mode = 1
            semua.append(f"ch {ch} sudah selesai upsubs ({target} : {count})")
        else:
            ch_belum_selesai.append(a)
            semua.append(f"ch {ch} belum selesai upsubs ({target} : {count})")
    cf["chgc"] = ch_belum_selesai
    with open("config.json", "w", encoding='utf-8') as f:
        f.write(json.dumps(cf, indent=4, ensure_ascii=False))
    if mode == 1: return True, "\n".join(semua)
    elif mode == 0: return False, ""

#	user biasa
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handler2(event):
    message = event.message
    if "/start" in message.message:
        if message.message == "/start":
            sender = await event.get_sender()
            prem = "Premium User" if await isPrem(sender.id) else "You're Not Premium User"
            durasi = await checkDuration(sender.id)
            try: await event.reply(f"Welcome {sender.first_name}\nYour ID : {sender.id}\nStatus Premium : {prem}\nPremium Duration : {durasi}\nwant to become a premium member? chat @OrderPremium_Bot")
            except Exception as e: print(e)
        else:
            if not await isPrem(message.peer_id.user_id):
                chgc = json.loads(open("config.json", 'r', encoding='utf-8').read())["chgc"]
                # disini cek udah join channel atau belum
                for channel in chgc:
                    try: result = await client(functions.channels.GetParticipantRequest(channel=await client.get_entity(channel["ch"]), participant=message.peer_id.user_id))
                    except UserNotParticipantError:
                        link = "https://t.me/"+(await client.get_me()).username+"?start="+message.message.split(" ")[1]
                        await event.reply("kamu belum join channel, bergabung sebagai premium user untuk menikmati konten tanpa harus join channel, chat @OrderPremium_Bot", parse_mode="html", buttons=
                            [
                                [Button.url(f"ch/gc {no+1}", "https://t.me/"+c["ch"].split("@")[1]) for no,c in enumerate(chgc)],
                                [Button.url("coba lagi", link)]
                            ]
                        )
                        return
                    except Exception as e:
                        print(channel, e)
                        return
            try:
                param = message.message.split(" ")[1]
                param = ((base64.b64decode(param)).decode()).split("|")
                msg = await client.get_messages(int(param[1]), ids=int(param[0]))
                if random.randint(1,10) <= 2:
                    try:
                        status, msg = await cek()
                        if status: await client.send_message(data["grupDB"], msg)
                    except: pass
                await client.send_message(message.peer_id, msg)
                print(f"in -> {param}, {message.peer_id}")
            except Exception as e: print(e)

#	hanya admin
@client.on(events.NewMessage(incoming=True, chats=[grupDB]))
async def handler(event):
    message = event.message
    admins = await client.get_participants(message.peer_id, filter=ChannelParticipantsAdmins)
    if not event.sender in admins:
        if message.message == "/text": await event.reply("You're not admin!!"); return
    if message.message == "/text":
        try: msgid = message.reply_to.reply_to_msg_id
        except: await client.send_message(message.peer_id, "can't get message id, please retry your action!"); return
        link = base64.b64encode(f"{msgid}|{message.peer_id.channel_id}".encode("utf-8")).decode()
        link = "https://t.me/"+(await client.get_me()).username+"?start="+link
        await event.reply(f"this is your link >> {link}")
    elif message.message == "/all":
        a = json.loads(open("config.json", 'r', encoding='utf-8').read())
        if len(a["chgc"]) == 0: teks = "Tidak ada ch/gc"
        elif len(a["chgc"]) > 0: teks = ", ".join([f"{a['ch']} ({a['target']})" for a in a["chgc"]])
        else: teks = "Ada error"
        await client.send_message(message.peer_id, teks)
    elif message.message.startswith("/add1"):
        chgc = json.loads(open("config.json", 'r', encoding='utf-8').read())["chgc"]
        channels = re.findall('(@[A-Za-z0-9_]+|http[^ \n]+)', message.message)
        subs = re.search(r"\bsubs_(\d+)", message.message)
        if subs: subs = int(subs.group(1))
        else: subs = 0
        a = json.loads(open("config.json", 'r+', encoding='utf-8').read())
        c = []
        for chn in channels:
            if not subs == 0: c.append({"ch": chn, "target": str(f"{subs+(await client(GetFullChannelRequest(channel=chn))).full_chat.participants_count}")})
            else: c.append({"ch": chn, "target": "0"})
        c = a["chgc"]+c
        a["chgc"] = c
        open("config.json", "w", encoding='utf-8').write(json.dumps(a, indent=4, ensure_ascii=False))
        teks = ", ".join([f"{a['ch']} ({a['target']})" for a in a["chgc"]])
        await event.reply(f"ch/gc berhasil ditambahkan!\n{teks}")
    elif message.message.startswith("/del1"):
        chgc = json.loads(open("config.json", 'r', encoding='utf-8').read())["chgc"]
        channels = re.findall('(@[A-Za-z0-9_]+|http[^ \n]+)', message.message)
        a = json.loads(open("config.json", 'r+', encoding='utf-8').read())
        chn = []
        for no, ch in enumerate(chgc):
            if not ch['ch'] in channels: chn.append({"ch": ch["ch"], "target": ch["target"]})
        a["chgc"] = chn
        open("config.json", "w", encoding='utf-8').write(json.dumps(a, indent=4, ensure_ascii=False))
        teks = ", ".join([f"{a['ch']} ({a['target']})" for a in a["chgc"]])
        await event.reply(f"ch/gc berhasil dihapus!\n{teks}")
    elif message.message.startswith("/prem1"):
        data = re.findall(r"\d+", message.message)[1:]
        id = int(data[0])
        expired = int(data[1])
        await addPrem(id, expired)
        await event.reply(f"user {id} berhasil di tambahkan ke premium users")
        return
    elif message.message == "/cek":
        status, msg = await cek()
        if status: await event.reply(msg)

            
async def main(): await client.run_until_disconnected()
loop = asyncio.get_event_loop()
loop.run_until_complete(main())


