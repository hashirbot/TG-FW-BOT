import asyncio
import json
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Replace these with your actual values
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
phone_number = os.getenv('PHONE_NUMBER')
data_file = 'forwarder_data.json'

# Initialize the Telegram client for the bot
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.source_chat_id = None
        self.destination_channel_id = None
        self.start_message_id = None
        self.batch_size = 1000
        self.sleep_time = 1200
        self.delay_between_messages = 1  # default delay between messages in seconds
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)
        self.total_messages_forwarded = 0
        self.forwarding_active = False
        self.last_message_id = self._load_last_message_id()

    async def list_chats(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self._authorize()
        dialogs = await self.client.get_dialogs()
        response = "List of groups:\n"
        for dialog in dialogs:
            response += f"Chat ID: {dialog.id}, Title: {dialog.title}\n"
        return response

    async def forward_messages_to_channel(self, event):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self._authorize()

        self.forwarding_active = True
        await bot.send_message(event.sender_id, "Forwarding process started.")

        batch_count = 0
        async for message in self.client.iter_messages(self.source_chat_id, min_id=self.start_message_id, reverse=True):
            if not self.forwarding_active:
                await bot.send_message(event.sender_id, "Forwarding process stopped.")
                break
            try:
                await self.client.send_message(self.destination_channel_id, message)
                self.total_messages_forwarded += 1
                self.last_message_id = message.id
                batch_count += 1
                if batch_count >= self.batch_size:
                    await asyncio.sleep(self.sleep_time)
                    batch_count = 0
                else:
                    await asyncio.sleep(self.delay_between_messages)
            except Exception as e:
                if 'A wait of' in str(e):
                    wait_time = int(str(e).split('A wait of ')[1].split(' seconds')[0])
                    await bot.send_message(event.sender_id, f"Rate limit reached. Waiting for {wait_time} seconds.")
                    await asyncio.sleep(wait_time)
                    batch_count = 0
                continue
        self.forwarding_active = False
        self._save_last_message_id()
        return f"Total messages forwarded: {self.total_messages_forwarded}"

    async def _authorize(self):
        try:
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))
        except SessionPasswordNeededError:
            await self.client.sign_in(password=input('Enter your password: '))

    def _save_last_message_id(self):
        with open(data_file, 'w') as f:
            json.dump({'last_message_id': self.last_message_id}, f)

    def _load_last_message_id(self):
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
                return data.get('last_message_id', None)
        except FileNotFoundError:
            return None

forwarder = TelegramForwarder(api_id, api_hash, phone_number)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Welcome to the Telegram Forwarder Bot! Use /setsource, /setdest, /setstartid, /setbatchsize, /setsleeptime, /setdelay, /listchats, /forward, /stop, /resume, and /stats to configure and manage forwarding messages.")

@bot.on(events.NewMessage(pattern='/setsource'))
async def set_source(event):
    try:
        source_chat_id = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setsource <source_chat_id>")
        return
    forwarder.source_chat_id = source_chat_id
    await event.reply(f"Source chat ID set to: {source_chat_id}")

@bot.on(events.NewMessage(pattern='/setdest'))
async def set_dest(event):
    try:
        destination_channel_id = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setdest <destination_channel_id>")
        return
    forwarder.destination_channel_id = destination_channel_id
    await event.reply(f"Destination channel ID set to: {destination_channel_id}")

@bot.on(events.NewMessage(pattern='/setstartid'))
async def set_start_id(event):
    try:
        start_message_id = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setstartid <start_message_id>")
        return
    forwarder.start_message_id = start_message_id
    await event.reply(f"Start message ID set to: {start_message_id}")

@bot.on(events.NewMessage(pattern='/setbatchsize'))
async def set_batch_size(event):
    try:
        batch_size = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setbatchsize <batch_size>")
        return
    forwarder.batch_size = batch_size
    await event.reply(f"Batch size set to: {batch_size}")

@bot.on(events.NewMessage(pattern='/setsleeptime'))
async def set_sleep_time(event):
    try:
        sleep_time = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setsleeptime <sleep_time_in_seconds>")
        return
    forwarder.sleep_time = sleep_time
    await event.reply(f"Sleep time set to: {sleep_time} seconds")

@bot.on(events.NewMessage(pattern='/setdelay'))
async def set_delay(event):
    try:
        delay = int(event.raw_text.split()[1])
    except (IndexError, ValueError):
        await event.reply("Usage: /setdelay <delay_between_messages_in_seconds>")
        return
    forwarder.delay_between_messages = delay
    await event.reply(f"Delay between messages set to: {delay} seconds")

@bot.on(events.NewMessage(pattern='/listchats'))
async def list_chats(event):
    response = await forwarder.list_chats()
    await event.reply(response)

@bot.on(events.NewMessage(pattern='/forward'))
async def forward(event):
    if not forwarder.source_chat_id or not forwarder.destination_channel_id:
        await event.reply("Please set both source and destination chat IDs using /setsource and /setdest.")
        return
    response = await forwarder.forward_messages_to_channel(event)
    await event.reply(response)

@bot.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    forwarder.forwarding_active = False
    forwarder._save_last_message_id()  # Save the last message ID when stopping
    await event.reply("Forwarding process has been stopped.")

@bot.on(events.NewMessage(pattern='/resume'))
async def resume(event):
    if not forwarder.source_chat_id or not forwarder.destination_channel_id:
        await event.reply("Please set both source and destination chat IDs using /setsource and /setdest.")
        return
    if forwarder.last_message_id is None:
        await event.reply("No last message ID found. Forwarding has not been started or no messages have been forwarded yet.")
        return
    response = await forwarder.forward_messages_to_channel(event)
    await event.reply(response)

@bot.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    await event.reply(f"Total messages forwarded: {forwarder.total_messages_forwarded}")

if __name__ == "__main__":
    bot.start()
    bot.run_until_disconnected()
