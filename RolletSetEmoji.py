from hikkatl.tl.functions.messages import SendMediaRequest
from hikkatl.tl.types import InputMediaDice, MessageMediaDice, Message

from hikka import loader

SLOT_COMBINATIONS = {
    1: "Bar Bar Bar",
    2: "🍒 Bar Bar",
    3: "🍋 Bar Bar",
    4: "7️⃣ Bar Bar",
    5: "Bar 🍒 Bar",
    6: "🍒 🍒 Bar",
    7: "🍋 🍒 Bar",
    8: "7️⃣ 🍒 Bar",
    9: "Bar 🍋 Bar",
    10: "🍒 🍋 Bar",
    11: "🍋 🍋 Bar",
    12: "7️⃣ 🍋 Bar",
    13: "Bar 7️⃣ Bar",
    14: "🍒 7️⃣ Bar",
    15: "🍋 7️⃣ Bar",
    16: "7️⃣ 7️⃣ Bar",
    17: "Bar Bar 🍒",
    18: "🍒 Bar 🍒",
    19: "🍋 Bar 🍒",
    20: "7️⃣ Bar 🍒",
    21: "Bar 🍒 🍒",
    22: "🍒 🍒 🍒",
    23: "🍋 🍒 🍒",
    24: "7️⃣ 🍒 🍒",
    25: "Bar 🍋 🍒",
    26: "🍒 🍋 🍒",
    27: "🍋 🍋 🍒",
    28: "7️⃣ 🍋 🍒",
    29: "Bar 7️⃣ 🍒",
    30: "🍒 7️⃣ 🍒",
    31: "🍋 7️⃣ 🍒",
    32: "7️⃣ 7️⃣ 🍒",
    33: "Bar Bar 🍋",
    34: "🍒 Bar 🍋",
    35: "🍋 Bar 🍋",
    36: "7️⃣ Bar 🍋",
    37: "Bar 🍒 🍋",
    38: "🍒 🍒 🍋",
    39: "🍋 🍒 🍋",
    40: "7️⃣ 🍒 🍋",
    41: "Bar 🍋 🍋",
    42: "🍒 🍋 🍋",
    43: "🍋 🍋 🍋",
    44: "7️⃣ 🍋 🍋",
    45: "Bar 7️⃣ 🍋",
    46: "🍒 7️⃣ 🍋",
    47: "🍋 7️⃣ 🍋",
    48: "7️⃣ 7️⃣ 🍋",
    49: "Bar Bar 7️⃣",
    50: "🍒 Bar 7️⃣",
    51: "🍋 Bar 7️⃣",
    52: "7️⃣ Bar 7️⃣",
    53: "Bar 🍒 7️⃣",
    54: "🍒 🍒 7️⃣",
    55: "🍋 🍒 7️⃣",
    56: "7️⃣ 🍒 7️⃣",
    57: "Bar 🍋 7️⃣",
    58: "🍒 🍋 7️⃣",
    59: "🍋 🍋 7️⃣",
    60: "7️⃣ 🍋 7️⃣",
    61: "Bar 7️⃣ 7️⃣",
    62: "🍒 7️⃣ 7️⃣",
    63: "🍋 7️⃣ 7️⃣",
    64: "7️⃣ 7️⃣ 7️⃣"
}

SLOT_COMBINATIONS_CLEAN = {}
for key, value in SLOT_COMBINATIONS.items():
    SLOT_COMBINATIONS_CLEAN[key] = value.replace(" ", "")

@loader.tds
class DiceCollectorMod(loader.Module):
    
    strings = {
        "name": "RolletSetEmoji"
    }

    def __init__(self):

        self.is_running = False

    async def getemcmd(self, message):

        reply = await message.get_reply_message()
        
        if not reply:return None
        if not isinstance(reply.media, MessageMediaDice): return None
            
        combination = SLOT_COMBINATIONS_CLEAN.get(reply.media.value, "Неизвестная комбинация")
        
        await message.edit(combination)
        return combination

    async def set_emojicmd(self, message):

        if self.is_running: return
            
        args = message.text.split()
        if len(args) < 2: return
        
        target_text = " ".join(args[1:])
        self.target_emoji_clean = target_text.replace(" ", "")
        
        self.is_running = True
        await message.delete()

        while self.is_running:

            try:
                result = await message.client(
                    SendMediaRequest(
                        peer=await message.get_input_chat(),
                        media=InputMediaDice(emoticon="🎰"),
                        message="",
                    )
                )
                
                sent_message = None
                for update in result.updates:

                    if hasattr(update, 'message') and isinstance(update.message, Message):

                        sent_message = update.message
                        break
                
                if sent_message and isinstance(sent_message.media, MessageMediaDice):

                    dice_value = sent_message.media.value
                    combination_clean = SLOT_COMBINATIONS_CLEAN.get(dice_value, "")
                                        
                    if combination_clean == self.target_emoji_clean:

                        self.is_running = False
                        break
                                
            except:

                self.is_running = False
                break

    async def stopcmd(self, message):
        if self.is_running:
            self.is_running = False
            await message.edit("Остановлено")