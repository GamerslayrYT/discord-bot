import os
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if DISCORD_TOKEN is None or GROQ_API_KEY is None:
    raise ValueError("Missing environment variables!")

groq_client = Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

conversations = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    # 1. Ignore messages from the bot itself
    # We add 'or not bot.user' to satisfy the type checker
    if message.author == bot.user or bot.user is None:
        return

    # 2. Check if it's a DM or a Mention
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # We've already checked 'bot.user is None' above, 
    # so Python now knows 'bot.user' is safe to use here.
    is_mentioned = bot.user.mentioned_in(message)

    if is_dm or is_mentioned:
        # Clean the message text
        bot_id = bot.user.id
        clean_content = message.content.replace(f'<@{bot_id}>', '').replace(f'<@!{bot_id}>', '').strip()
        
        if not clean_content and is_dm:
            await message.channel.send("I'm here! How can I help?")
            return

        user_id = message.author.id
        
        # Memory Management
        if user_id not in conversations:
            conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant donesnt respond in huge messages."}]
        
        conversations[user_id].append({"role": "user", "content": clean_content})
        
        # Keep context window short (last 10 messages)
        if len(conversations[user_id]) > 11: 
            conversations[user_id] = [conversations[user_id][0]] + conversations[user_id][-10:]

        async with message.channel.typing():
            try:
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=conversations[user_id],
                )
                
                response = completion.choices[0].message.content or ""
                conversations[user_id].append({"role": "assistant", "content": response})
                
                if len(response) > 2000:
                    # In DMs, use send(); in servers, use reply()
                    if is_dm:
                        await message.channel.send(response[:1997] + "...")
                    else:
                        await message.reply(response[:1997] + "...")
                elif response:
                    if is_dm:
                        await message.channel.send(response)
                    else:
                        await message.reply(response)
                    
            except Exception as e:
                await message.channel.send(f"⚠️ Error: {str(e)}")

    # Process commands like !reset
    await bot.process_commands(message)
@bot.command()
async def reset(ctx):
    user_id = ctx.author.id
    if user_id in conversations:
        del conversations[user_id]
    await ctx.send("Memory wiped! 🧠💨")



bot.run(DISCORD_TOKEN)