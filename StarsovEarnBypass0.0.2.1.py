from hikkatl.types import Message

from hikkatl.tl.functions.channels import JoinChannelRequest
from hikkatl.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest, ImportChatInviteRequest, \
    TranslateTextRequest

from hikkatl.errors import InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError, FloodWaitError
from hikkatl.events import NewMessage

from hikkatl.tl.types import KeyboardButtonUrl, Channel, InputPeerChannel, DialogFilter, InputPeerChat, InputPeerUser

from urllib.parse import urlparse, urlunparse
from hikka import loader

import asyncio
import emoji

@loader.tds
class StarsovEarnByPass(loader.Module):

    strings = {
        "name": "StarsovEarnByPass"
    }

    async def client_ready(self, client, db):

        self.client = client
        self.db = db

        self.channels = await self.all_channel()
        self.last_channel_id_news = 0

        if hasattr(self, "_event_handler"):
            self.client.remove_event_handler(self._event_handler)
        
        self._event_handler = self.on_message
        self.client.add_event_handler(
            self._event_handler,
            NewMessage()
        )

    async def on_unload(self):
        if hasattr(self, "_event_handler"):

            self.client.remove_event_handler(self._event_handler)


    async def all_channel(self):
        
        channels = []

        async for dialog in self.client.iter_dialogs():
            if isinstance(dialog.entity, Channel):

                entity = dialog.entity
                channels.append(entity.id)

        return channels

    def clean_telegram_url(self, url):

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)

        clean_path = parsed.path.split('/')[1]
        clean_url = urlunparse((parsed.scheme, parsed.netloc, clean_path, '', '', ''))
        return clean_url
    
    async def process_url_button(self, button, message_my = None):

        url = button.button.url

        try:
            if "t.me/" not in url: return False
            
            if "t.me/+" in url:

                invite_hash = url.split("t.me/+")[1]

                try:

                    await self.client(ImportChatInviteRequest(invite_hash))
                    if message_my: await message_my.edit(f"Принял инвайт: {url}")

                    return True
                
                except InviteHashExpiredError:
                    
                    if message_my: await message_my.edit("Инвайт-ссылка истекла")

                    return False
                
                except InviteHashInvalidError:

                    if message_my: await message_my.edit("Неверная инвайт-ссылка")
                    return False
                
                except UserAlreadyParticipantError:

                    if message_my: await message_my.edit("Уже состою в этом чате")
                    return True
                except FloodWaitError as e:

                    wait_time = e.seconds
                    if message_my: await message_my.edit(f"Слишком много запросов. Ждем {wait_time} секунд...")
                    await asyncio.sleep(wait_time)

                    return await self.process_url_button(button, message_my)
                
                except Exception as e:

                    if message_my: await message_my.edit(f"Ошибка при присоединении: {str(e)}")
                    return False
            
            try:
                entity_info = await self.client.get_entity(url)
            except:
                url = self.clean_telegram_url(url)
                entity_info = await self.client.get_entity(url)

            if entity_info.__class__.__name__ == 'Channel':

                await self.client(JoinChannelRequest(entity_info))
                if message_my: await message_my.edit(f"Подписался на канал: {url}")

                return True
            
            elif entity_info.__class__.__name__ == 'User' and entity_info.bot:
                
                try:
                    await self._client.send_message(
                        entity_info.username, (
                        "/start"
                    ))

                    if message_my: await message_my.edit(f"Отправил /start боту: {entity_info.username}")
                    return True
                except:
                    if message_my: await message_my.edit("Не удалось отправить сообщение - скипаю")
                    return False
            
            else:

                if message_my: await message_my.edit("Это не канал и не бот")
                return False
            
        except Exception as e:
            
            if message_my: await message_my.edit(f"Ошибка обработки URL: {str(e)}")
            return False

    async def analyze_button(self, message: Message, message_my = None):

        if not message.buttons and message_my:
            await message_my.edit("Нет кнопок в сообщении.")
            return 

        first_row = message.buttons[0]
        first_button = first_row[0]
        second_button = first_row[1] if len(first_row) > 1 else None
        
        await self.process_url_button(first_button, message_my)

        if second_button:
            await self.analyze_button_second(second_button,message, message_my)

    async def analyze_button_second(self, button,message_reply, message_my = None):
        try:

            if isinstance(button.button, KeyboardButtonUrl): 
                return
            
            elif hasattr(button.button, 'data'):
                if "Подтвердить" in button.button.text:

                    max_attempts = 5
                    attempt = 0
                    message_deleted = False

                    while attempt < max_attempts and not message_deleted:

                        attempt += 1
                        await button.click()

                        try:
                            await self.client.get_messages(
                                entity=message_reply.peer_id,
                                ids=[message_reply.id]
                            )
                        except Exception:
                            message_deleted = True
                            return

                        await asyncio.sleep(10)
                        
                    await asyncio.sleep(10)
                    if not message_deleted:

                        if len(message_reply.buttons) > 1 and len(message_reply.buttons[1]) > 0:

                            third_button = message_reply.buttons[1][0]
                            await third_button.click()

        except Exception as e:

            if message_my: await message_my.edit(f"Ошибка при обработке второй кнопки: {str(e)}")

    #------------------заменяет все слова на эмодзи если это возможно и выводит все---------------

    def extract_and_replace_fruit_emojis(self, text):
        words = text.split()
        found_emojis = []
        
        for i, word in enumerate(words):
            cleaned_word = word.lower().strip(".,!?")
            emoji_code = f":{cleaned_word}:"
            emojized = emoji.emojize(emoji_code, language='alias')
            
            if emojized != emoji_code:
                found_emojis.append(emojized)
                words[i] = emojized
        
        return found_emojis
    
    #-----------------скипает капчу-----------------

    async def robot_bypass(self, message):
        try:

            if message.is_private:
                peer = InputPeerUser(message.sender_id, message.sender.access_hash)
            elif message.is_group:
                peer = InputPeerChat(message.chat_id)
            elif message.is_channel:
                peer = InputPeerChannel(message.chat_id, message.chat.access_hash)
            else:
                return "⚠️ Unsupported chat type"

            translated = await self.client(TranslateTextRequest(
                to_lang="en",
                peer=peer,
                id=[message.id]
            ))

            if translated and hasattr(translated, 'result'):
                return translated.result[0].text
            return "⚠️ Translation failed"

        except Exception as e:
            print(f"Translation error: {e}")
            return f"⚠️ Error: {str(e)}"
        
    #------------находит кнопку по +-тексту-------------

    async def find_button_by_text(self, text, message):

        for row_idx, row in enumerate(message.reply_markup.rows):
            for i, button in enumerate(row.buttons):
                button_text = getattr(button, "text", "")

                if text.lower() in button_text.lower():
                    return (row_idx+i, button)
        return (None, None)
    
    #--------типо обработчик сообщений, чего вы еще хотели?--------------
    
    async def on_message(self, message):  

        user_id = message.sender_id
        if user_id != 7974361539: return

        if "дождитесь прогрузки ссылки" in message.text or \
            "Дай буст" in message.text or \
            "Добавьте бота в группу" in message.text:

            third_button = message.buttons[1][0]
            await third_button.click()
            return
        
        if "Подпишитесь на" in message.text:
            
            await self.sebcmd(message)

            
        if "Подпишись на" in message.text:
            
            await self.sebcmd(message)

        if "Проверка на робота" in message.text:
            text_translate = await self.robot_bypass(message)
            if not text_translate: return

            emoji_find = self.extract_and_replace_fruit_emojis(text_translate.splitlines()[-1])
            if not emoji_find: return

            for emoji in emoji_find:

                row, _ = await self.find_button_by_text(emoji, message)
                if not row: continue

                await message.click(row)
                break


    #---------Фигня которая добавляет канал в папку, и не больше....---------------
    async def add_channel_folder(self, channel_id):
        
        entity = await self.client.get_entity(channel_id)
        peer_channel = InputPeerChannel(entity.id, entity.access_hash)

        folders = await self.client(GetDialogFiltersRequest())
        trash_folder = next(
            (f for f in folders if isinstance(f, DialogFilter) and f.title == "МУСОР"),
            None
        )

        if not trash_folder:
            trash_folder = DialogFilter(
                id=123,
                title="МУСОР",
                include_peers=[peer_channel],
                pinned_peers=[],
                exclude_peers=[]
            )
        else:
            if peer_channel not in trash_folder.include_peers:
                trash_folder.include_peers.append(peer_channel)

        await self.client(UpdateDialogFilterRequest(
            id=trash_folder.id,
            filter=trash_folder,
        ))

    #------------в раз 20с просто берет и проверяет из какого канала ты вышел и зашел---------
    #------------при заходе просто берет и добавляет в папку----------------------------------

    @loader.loop(interval=20, autostart=True)
    async def get_new_channel(self):
            
        get_all_channel = await self.all_channel()
        for id1 in get_all_channel:

            if id1 not in self.channels:

                self.channels = get_all_channel
                await self.add_channel_folder(id1)

        for id1 in self.channels.copy(): 
            if id1 not in get_all_channel:

                self.channels.remove(id1)

    #---------берет и отслеживает новые соо в канале, нужно для активации чеков...----------
    #---------пс, скоро будет настройки и эт можно будет отключить--------------------------

    @loader.loop(interval=10, autostart=True)
    async def check_new_message(self):

        channel = await self.client.get_entity("StarsovEarn")
        messages = await self.client.get_messages(channel, limit=10)
        
        if not messages: return
        
        new_messages = []
        current_ids = {msg.id for msg in messages}

        if not hasattr(self, "last_channel_message_ids"):
            self.last_channel_message_ids = {msg.id for msg in messages}
            return
    
        for msg in messages:
            if msg.id not in self.last_channel_message_ids:
                new_messages.append(msg)
        
        self.last_channel_message_ids = current_ids
        
        for msg in new_messages:
            await self.is1(msg)

    #-----------в раз 30 минут будет писать StarSovEaenBot, чтоб ты зарабатывал свои звездочки--------

    @loader.loop(interval=60*30, autostart=True)
    async def check_loop(self):
            
        await self._client.send_message(
        await self.client.get_entity("StarsovEarnBot"), (
            f"💎 Задания"
        ))

    #----------проверят, является ли это сообщение чеком---------------

    async def is1(self, message: Message):

        if not message.reply_markup: return

        first_row = message.reply_markup.rows[0].buttons[0]

        if "StarsovEarn" in first_row.url:

            code = first_row.url.split('start=')[1]
                        
            await self._client.send_message(
                await self.client.get_entity("StarsovEarnBot"), (
                f"/start {code}"
            ))

    #------------не обращай внимание-------------

    @loader.command()
    async def sebcmd(self, message: Message):

        if message.from_id == 7974361539:

            await self.analyze_button(message)
            return

        reply = await message.get_reply_message()

        if not reply:
            await message.edit("🔎 Нужен реплай на сообщение с кнопками.")
            return
        
        await self.analyze_button(reply, message)
