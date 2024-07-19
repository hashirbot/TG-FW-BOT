import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel
import time

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)

    async def list_chats(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self._authorize()
        dialogs = await self.client.get_dialogs()
        with open(f"chats_of_{self.phone_number}.txt", "w") as chats_file:
            for dialog in dialogs:
                print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
                chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title}\n")
        print("List of groups printed successfully!")

    async def forward_messages_to_channel(self, source_chat_id, destination_channel_id, start_message_id=None, batch_size=1000, sleep_time=1200):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self._authorize()
        total_messages = 0
        batch_count = 0
        async for message in self.client.iter_messages(source_chat_id, min_id=start_message_id, reverse=True):
            try:
                await self.client.send_message(destination_channel_id, message)
                print(f"Forwarded message ID {message.id}")
                total_messages += 1
                batch_count += 1
                if batch_count >= batch_size:
                    print(f"Batch of {batch_size} messages forwarded. Sleeping for {sleep_time} seconds.")
                    time.sleep(sleep_time)
                    batch_count = 0
            except Exception as e:
                print(f"Error forwarding message {message.id}: {e}")
                continue
        print(f"Total messages forwarded: {total_messages}")

    async def _authorize(self):
        try:
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))
        except SessionPasswordNeededError:
            await self.client.sign_in(password=input('Enter your password: '))

def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            api_id = lines[0].strip()
            api_hash = lines[1].strip()
            phone_number = lines[2].strip()
            return api_id, api_hash, phone_number
    except FileNotFoundError:
        print("Credentials file not found.")
        return None, None, None

def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    api_id, api_hash, phone_number = read_credentials()
    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        write_credentials(api_id, api_hash, phone_number)
    forwarder = TelegramForwarder(api_id, api_hash, phone_number)
    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")
    choice = input("Enter your choice: ")
    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        source_chat_id = input("Enter the source chat ID or link: ")
        destination_channel_id = input("Enter the destination channel ID or link: ")
        source_chat_id = int(source_chat_id) if source_chat_id.isdigit() else source_chat_id
        destination_channel_id = int(destination_channel_id) if destination_channel_id.isdigit() else destination_channel_id
        start_message_id = input("Enter the starting message ID (or leave blank to start from the beginning): ")
        start_message_id = int(start_message_id) if start_message_id.isdigit() else None
        await forwarder.forward_messages_to_channel(source_chat_id, destination_channel_id, start_message_id=start_message_id)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())

