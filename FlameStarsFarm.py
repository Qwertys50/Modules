import re
import asyncio
import time

from hikkatl.events import NewMessage
from hikka import loader, utils


@loader.tds
class FlameStarsFarm(loader.Module):

    strings = {
        "name": "FlameStarsFarm"
    }

    def __init__(self):
        self._event_handler = None
        self.click_times = {} 

    async def client_ready(self, client, db):

        self.client = client
        self.db = db

        if self._event_handler:
            self.client.remove_event_handler(self._event_handler)

        self._event_handler = self.client.add_event_handler(
            self.on_message,
            NewMessage()
        )

    def text_to_second(self, text: str) -> int:

        total_seconds = 0

        minute_match = re.search(r'(\d+)\s*мин', text)
        if minute_match:
            total_seconds += int(minute_match.group(1)) * 60

        second_match = re.search(r'(\d+)\s*сек', text)
        if second_match:
            total_seconds += int(second_match.group(1))

        return total_seconds

    async def on_message(self, event):

        message = event.message
        if not message or not message.sender_id:
            return

        user_id = message.sender_id
        if user_id != 7809543976:
            return

        try:
            if message.text and "Пожалуйста, решите пример:" in message.text:

                example = message.text.split(":")[1].strip()
                example = example.replace('=', '').strip()

                try:
                    result = eval(example)
                    mes = await utils.answer(message, f"{result}")
                    await asyncio.sleep(1)

                    await message.delete()
                    await mes.delete()
                except Exception as e: pass

            elif message.text and "Капча верна" in message.text:
                await asyncio.sleep(1)
                await message.delete()

        except: pass

    @loader.loop(interval=2, autostart=True)
    async def rr(self):

        try:
            reply = None
            async for msg in self.client.iter_messages(7809543976, limit=25):

                if msg.text and "Используй кнопки ниже для действий." in msg.text:
                    reply = msg
                    break

            if not reply:
                return

            if not hasattr(reply, 'buttons') or not reply.buttons:
                return

            try:
                button_index = 0

                if len(reply.buttons) <= button_index:
                    return

                current_time = time.time()
                last_click_time = self.click_times.get(reply.id, 0)
                
                if current_time - last_click_time >= 2:

                    click_result = await reply.click(button_index)
                    
                    if hasattr(click_result, 'message') and click_result.message:
                        result_text = click_result.message

                        if "Подождите" in result_text:

                            waiting_time = self.text_to_second(result_text)
                            self.click_times[reply.id] = current_time + waiting_time

                        else:

                            self.click_times[reply.id] = current_time

                    self._clean_old_entries()

            except Exception as e: pass

        except Exception as e: pass

    def _clean_old_entries(self):

        current_time = time.time()
        keys_to_remove = []
        
        for msg_id, click_time in self.click_times.items():
            if current_time - click_time > 3600:
                keys_to_remove.append(msg_id)
        
        for key in keys_to_remove:
            del self.click_times[key]

    async def on_unload(self):

        if self._event_handler:
            self.client.remove_event_handler(self._event_handler)