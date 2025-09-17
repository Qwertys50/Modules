from hikkatl.types import Message

from hikkatl.tl.functions.channels import JoinChannelRequest

from hikkatl.errors import InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError, FloodWaitError
from hikkatl.events import NewMessage

from hikkatl.tl.types import KeyboardButtonUrl

from urllib.parse import urlparse, parse_qs
from hikka import loader

import asyncio
from telethon.tl.functions.messages import ImportChatInviteRequest

@loader.tds
class StarsovEarnByPass(loader.Module):

    strings = {
        "name": "StarsovEarnByPass"
    }

    async def client_ready(self, client, db):

        self.client = client
        self.db = db
        self.client.add_event_handler(
            self.on_message,
            NewMessage()
        )

    async def process_url_button(self, button, message_my):

        url = button.button.url
        try:
            if "t.me/" not in url:
                return False
            
            if "t.me/+" in url:

                invite_hash = url.split("t.me/+")[1]

                try:

                    await self.client(ImportChatInviteRequest(invite_hash))
                    await message_my.edit(f"Принял инвайт: {url}")
                    return True
                
                except InviteHashExpiredError:

                    await message_my.edit("Инвайт-ссылка истекла")
                    return False
                
                except InviteHashInvalidError:

                    await message_my.edit("Неверная инвайт-ссылка")
                    return False
                
                except UserAlreadyParticipantError:

                    await message_my.edit("Уже состою в этом чате")
                    return True
                except FloodWaitError as e:

                    wait_time = e.seconds
                    await message_my.edit(f"Слишком много запросов. Ждем {wait_time} секунд...")
                    await asyncio.sleep(wait_time)

                    return await self.process_url_button(button, message_my)
                
                except Exception as e:

                    await message_my.edit(f"Ошибка при присоединении: {str(e)}")
                    return False
            
            entity_info = await self.client.get_entity(url)
            
            if entity_info.__class__.__name__ == 'Channel':

                await self.client(JoinChannelRequest(entity_info))
                await message_my.edit(f"Подписался на канал: {url}")

                return True
            
            elif entity_info.__class__.__name__ == 'User' and entity_info.bot:

                if '?' in url:
                    query = parse_qs(urlparse(url).query)
                    start_param = query.get('start', [None])[0]
                    command = f"/start {start_param}" if start_param else "/start"
                else:

                    command = "/start"
                
                await self._client.send_message(
                await self.client.get_entity(entity_info.username), (
                    "/start"
                ))

                await message_my.edit(f"Отправил {command} боту: {url}")
                return True
            
            else:

                await message_my.edit("Это не канал и не бот")
                return False
            
        except Exception as e:
            
            await message_my.edit(f"Ошибка обработки URL: {str(e)}")
            return False

    async def process_callback_button(self, button, message_my):
        try:

            await button.click()
            await message_my.edit("Отправил заявку в канал/группу.")
            return True
        except Exception as e:

            await message_my.edit(f"Ошибка отправки заявки: {str(e)}")
            return False

    async def analyze_button(self, message: Message, message_my):

        if not message.buttons:
            await message_my.edit("Нет кнопок в сообщении.")
            return 

        first_row = message.buttons[0]
        first_button = first_row[0]
        second_button = first_row[1] if len(first_row) > 1 else None
        

        if isinstance(first_button.button, KeyboardButtonUrl):
            await self.process_url_button(first_button, message_my)
        elif hasattr(first_button.button, 'data'):
            await self.process_callback_button(first_button, message_my)
        else:

            await message_my.edit("Неизвестный тип кнопки.")
            return
        
        if second_button:
            await self.analyze_button_second(second_button, message_my, message)

    async def analyze_button_second(self, button, message_my, message_reply):
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
                        else:
                            
                            await message_my.edit("Нажми сам подтвердить")

                else:

                    await message_my.edit("Нажми сам подтвердить")

        except Exception as e:

            await message_my.edit(f"Ошибка при обработке второй кнопки: {str(e)}")

    async def on_message(self, message):  

        user_id = message.sender_id
        if user_id != 7974361539: return

        if "Подпишитесь на" not in message.text: return

        _message = await self.client.send_message(7974361539, "Обрабатываю...", reply_to=message.id)
        await self.sebcmd(_message)

    @loader.loop(interval=60*30, autostart=True)
    async def check_loop(self):
            
        await self._client.send_message(
        await self.client.get_entity("StarsovEarnBot"), (
            f"💎 Задания"
        ))

    @loader.command()
    async def get_url(self, message):

        full_text = message.text
        url_part = full_text[9:].strip()
        
        if url_part.startswith('<a href="'):

            try:

                url = url_part.split('"')[1]
            except IndexError:
                await message.edit("Неверный формат URL в HTML-ссылке")
                return
            
        else:
            url = url_part.split()[0]
        
        try:
            await self.client.get_entity(url)
            
        except Exception as e: pass

    @loader.command()
    async def sebcmd(self, message: Message):

        reply = await message.get_reply_message()

        if not reply:
            await message.edit("🔎 Нужен реплай на сообщение с кнопками.")
            return
        
        await self.analyze_button(reply, message)