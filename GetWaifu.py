import os
import gdown

import sqlite3
import re

import hashlib
import uuid
import asyncio

import pendulum

from wonderwords import RandomWord

from hikka import loader, utils, types
from hikkatl.events import NewMessage

@loader.tds
class GetWaifu(loader.Module):

    strings = {
        "name": "GetWaifu"
    }

    def __init__(self):

        self.name_chat_save = "chat_info3"

    async def client_ready(self):
        print("hm")

        self.client.add_event_handler(
            self.on_message,
            NewMessage()
        )


    def get_random_word(self):
        return RandomWord().random_words()

    def check_column_exists(self, db_path, table_name, column_name):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            column_exists = any(col[1] == column_name for col in columns)
            
            return column_exists
        except sqlite3.Error as e:
            return False
        finally:
            if conn:
                conn.close()

    async def on_message(self, message):  

        if "channel_id" in message.peer_id.__dict__:

            chat_id = message.peer_id.channel_id
            index = -1

            chats1 = self.get(self.name_chat_save, []) or []
            for i, chat in enumerate(chats1):

                if chat["id"] == chat_id:
                    index = i
                    break
                    
            else: return

            if int(message.sender_id) == 6704842953:  
                
                if "О, что это тут? Вайфу заблудилась!" in message.text:

                    photo_bytes = await message.download_media(bytes)

                    if not photo_bytes: return

                    ahash = self._calculate_image_hash(photo_bytes)
                    name_image = self._find_image_by_hash('hashes.db', ahash)

                    if name_image:
                        await self._client.send_message(
                            chat_id, f"/claim {name_image}"
                        )

                        chats1 = self.get(self.name_chat_save, []) or []
                        last_json = chats1.copy()

                        for idx, id_chat in enumerate(last_json):
                            updated_timestamp = pendulum.now().int_timestamp + (60 * 60 * 4)
                            last_json[idx]["timestamp"] = updated_timestamp
                        
                        self.set(self.name_chat_save, last_json)

                if "Вы недавно уже отгадывали персонажа" in message.text and str(self.client.tg_id) in message.text:
                    if index == -1: return
                    
                    chat_info = {}

                    for chat in chats1:
                        
                        if chat["id"] == chat_id:
                            chat_info = chat
                            break
                    
                    add_time_timestamp = self.parse_time_to_seconds(message.text.splitlines()[-1])
                    current_timestamp = pendulum.now().int_timestamp + add_time_timestamp

                    chats1[index]["timestamp"] = current_timestamp

                if "тут вайфу нет." in message.text and str(self.client.tg_id) in message.text:
                    if index == -1: return
                    
                    chat_info = {}

                    for chat in chats1:
                        
                        if chat["id"] == chat_id:
                            chat_info = chat
                            break
                    
                    current_timestamp = pendulum.now().int_timestamp + 360

                    chats1[index]["timestamp"] = current_timestamp



    async def _download_db(self):

        try:
            url = "https://drive.google.com/uc?id=1MamiOEusJI_rSAjYaoeuKIsbZyRa8-WQ"
            gdown.download(url, quiet=True)
            return [True, 1]
        except Exception as e: return [False, e]
        
    def _extract_character_info(self, text):
        
        id_match = re.search(r'🆔\s*<code>(\d{4,})<\/code>', text)
        name_match = re.search(r'👤 Полное имя:\s*(.+?)(?:\n|<)', text)
        title_match = re.search(r'🌸 Тайтл:\s*(.+?)(?:\n|<)', text)
        
        if id_match and name_match and title_match:

            character_id = id_match.group(1)
            full_name = name_match.group(1).strip()
            title = title_match.group(1).strip()

            return {
                "id": character_id, 
                "full_name": full_name,
                "title": title
            }
        else: return None

    def _calculate_image_hash(self, image_bytes):

        try:
            
            return hashlib.md5(image_bytes).hexdigest()
        
        except Exception: return None
           
    def _extract_name(self, path):

        match = re.search(r"\\([^\\]+)_", path)
        if match: return match.group(1)

        return None
        
    def _find_image_by_hash(self, db_path, target_hash):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name_waifu FROM hashes WHERE hashes = ?", (target_hash,))
            result = cursor.fetchone()
            
            if result:

                return result[0]
            else:
                return None
                
        except sqlite3.Error: return None
        finally: conn.close()

    def _add_hash_entry(self, db_path, hash_value, image_url):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:

            cursor.execute("SELECT 1 FROM hashes WHERE hashes = ?", (hash_value,))
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(
                    "INSERT INTO hashes (hashes, name_waifu) VALUES (?, ?)", 
                    (hash_value, image_url)
                )
                conn.commit()
        finally: 
            conn.close()

    def parse_time_to_seconds(self, time_str):

        hours, minutes, seconds = 0, 0, 0

        hour_match = re.search(r'(\d+)\s*час[а-я]*', time_str)
        minute_match = re.search(r'(\d+)\s*минут[а-я]*', time_str)
        second_match = re.search(r'(\d+)\s*секунд[а-я]*', time_str)

        if hour_match:

            hours = int(hour_match.group(1))
        if minute_match:

            minutes = int(minute_match.group(1))
        if second_match:

            seconds = int(second_match.group(1))

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    @loader.loop(interval=2, autostart=True)
    async def check_loop(self):

        chats1 = self.get(self.name_chat_save, []) or []
        last_json = chats1.copy()

        for idx, id_chat in enumerate(last_json):

            try:
                if id_chat["ready"]:

                    last_timestamp = pendulum.now().int_timestamp

                    if "timestamp" in id_chat: 
                        last_timestamp = id_chat["timestamp"]
                    
                    if last_timestamp <= pendulum.now().int_timestamp:

                        await self._client.send_message(
                            id_chat["id"], "/claim"
                        )
                        
            except: print(f"Не удалось отправить сообщение:")

        self.set(self.name_chat_save, last_json)

    @loader.command()
    async def update_db(self, message, r=None):
        """ — Обновить базу данных"""

        if os.path.isfile("hashes.db"): os.remove("hashes.db")
        down = await self._download_db()

        if not down[0]:

            await message.edit(f"Ошибка при скачивании базы данных ({down[1]})| Ошибка\nМожет быть поможет это <code>rm /root/.cache/gdown/cookies.txt</code>")
            return

        else:

            await message.edit("База данных успешно скачалось| Успешно")

    async def send_message_bot(self, info):
        
        try:
            message = await self._client.send_message(
            await self.client.get_entity("garem_db_bot"), (
                f"hash = {info['hash']}\n"
                f"url = {info['url']}"
            ))

            await message.delete(revoke=False)
        except Exception as e: pass
            
    def get_button(self, buttons):
        a = 0
        button = None

        for _buttons in buttons:
            for _button in _buttons.buttons:
                if "🔄" in _button.text:
                    button = _button
                    a += 1
                    break
        
        return button, a

    async def download_photo(self, reply):

        info = self._extract_character_info(reply.text)
        if not info: return None
            
        photo_bytes = await reply.download_media(bytes)
        if not photo_bytes: return

        ahash = self._calculate_image_hash(photo_bytes)
        url = fr"images\{info['title']}\{info['full_name']}_{uuid.uuid4().hex}.jpg"
        await self.send_message_bot({
            "url": url,
            "hash": ahash
        })

        self._add_hash_entry("hashes.db", ahash, url)
    
    async def removeChat(self, chat_id):

        chats = self.get(self.name_chat_save, []) or []
        changed = False
        
        for chat in chats:
            if chat["id"] == chat_id and chat["ready"]:
                chat["ready"] = False
                changed = True
                
        if changed:

            self.set(self.name_chat_save, chats)
        return changed
        
    async def addChat(self, chat_id):

        chats = self.get(self.name_chat_save, []) or []
        
        for chat in chats:
            if chat["id"] == chat_id:
                if not chat["ready"]:
                    chat["ready"] = True
                    self.set(self.name_chat_save, chats)
                return False
        
        chats.append({"id": chat_id, "ready": True})
        self.set(self.name_chat_save, chats)

        return True

    @loader.command()
    async def getwaifu(self, message):
        """ — Искать вайфу"""

        if not message.is_reply: return
        if not os.path.isfile("hashes.db"):

            await message.edit("Базы данных нету| Скачиваю")

            down = await self._download_db()

            if not down[0]:

                await message.edit(f"Ошибка при скачивании базы данных ({down[1]})| Ошибка")
                return

            else:

                await message.edit("База данных успешно скачалось| Успешно")
        
        try:
            conn = sqlite3.connect('hashes.db')
            cursor = conn.cursor()
        except:
            await message.edit("Ошибка с подключением базы данных| Ошибка")
            return

        reply = await message.get_reply_message()
        if reply.reply_markup:
            buttons = reply.reply_markup.rows
        else:
            buttons = None

        if not reply.photo:
            await message.edit("Фото не найдено")
            return
        
        photo_bytes = await reply.download_media(bytes)

        if not photo_bytes:
            await message.edit("Не удалось скачать фото")
            return

        ahash = self._calculate_image_hash(photo_bytes)
        name_image = self._find_image_by_hash('hashes.db', ahash)

        pattern = r'<a href="tg://user\?id=(\d+)">.*?</a>'
        matches = re.findall(pattern, reply.text)

        if name_image:
            await message.edit(name_image)
        else:
            
            markup = []
            add_text = ""

            if self._extract_character_info(reply.text):

                markup.append([{
                    "text": "Добавить",
                    "callback": self.add_waifu,
                    "args": [reply, 1]
                }])
            
            else:

                add_text = (
                    "Для добавления должно присутствовать имя и 🆔 Waifu. Пример ниже:\n"
                    "<pre>🆔 10\n👤 Полное имя: Анцзи Цзоу</pre>"
                )

            if buttons and str(self.client.tg_id) in matches:
                
                client = self._client
                button, _ = self.get_button(buttons)
                
                if button:
                    
                    num, num2 = map(int, button.text.split()[-1].split('/'))
                    markup.append([{
                        "text": f"Добавить {(num2-num)+1}",
                        "callback": self.add_waifu,
                        "args": [reply, 2, button]
                    }])

            await utils.answer(
                message,
                f"Нету в базе данных, хотите добавить? {add_text}", 
                reply_markup=markup,
            )

    def getmarkup(self, chat_id):

        chats_how = False

        chats1 = self.get(self.name_chat_save, []) or []
        for i, chat in enumerate(chats1):

            if chat["id"] == chat_id:
                
                if chat["ready"]:
                    chats_how = True
                    break
                        
        return [
                [
                    {
                        "text": "[✔️] Автоловля" if chats_how else "[❌] Автоловля",
                        "callback":self.callback_handler,
                        "args": ("autoLow",)
                    }
                ],
                [
                    {
                        "text":"🔻 Закрыть меню", 
                        "callback":self.callback_handler,
                        "args": ("close",)
                    }
                ]
            ]

    async def callback_handler(self, callback: types.InlineCall, data): 
        if data == "close":
            await self.call.edit(text="Меню закрыто.")
        
        if data == "autoLow":
            chats_how = False

            chats1 = self.get(self.name_chat_save, []) or []
            data_message = callback._units

            inner_dict = next(iter(data_message.values()))  
            chat_id = inner_dict['chat']

            for i, chat in enumerate(chats1):

                if chat["id"] == chat_id:

                    if chat["ready"]:
                        chats_how = True
                        break

            if chats_how: await self.removeChat(chat_id)
            else: await self.addChat(chat_id)
            await callback.edit(reply_markup=self.getmarkup(chat_id))


    @loader.command()
    async def setting(self, message):
        
        self.call = await self.inline.form(
            message = message, 
            text = "Меню для @garem_chatbot", 
            reply_markup = self.getmarkup(message.peer_id.channel_id)
        )
        

    async def add_waifu(self, call, reply, _id, button=None):
        
        if _id == 1:

            await self.download_photo(reply)
            await call.edit(f"Успешно")
        
        else:
            max_attempts = 20
            attempt = 0
            
            while attempt < max_attempts:

                current_msg = await self.client.get_messages(
                    reply.chat_id,
                    ids=reply.id
                )
                    
                if not current_msg.buttons: return

                    
                info = self._extract_character_info(current_msg.text)
                if not info: return None

                await self.download_photo(current_msg)
                    
                button, button_num = self.get_button(current_msg.reply_markup.rows)

                if not button: return
                    
                try:
                    num1, num2 = map(int, button.text.split()[-1].split('/'))
                except: 
                    num1, num2 = 0, 0
                    
                if num1 >= num2: break
                    
                await current_msg.click(0)
                attempt += 1
                    
                await asyncio.sleep(2)

            await call.edit("Успешно")
                        