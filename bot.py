import discord
import aiohttp

DISCORD_TOKEN = "secret"
LLM_API = "http://192.168.22.154:8000/v1/chat/completions"
CHANNEL_NAME = "chat_s_ai"

AVAILABLE_MODELS = [
    "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M",
    "Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P",
    "Qwen3VL-8B-Uncensored-HauhauCS-Balanced",
]

current_model = AVAILABLE_MODELS[0]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot přihlášen jako {client.user}, model: {current_model}")

@client.event
async def on_message(message):
    global current_model

    if message.author == client.user:
        return
    if message.channel.name != CHANNEL_NAME:
        return

    # /models - vypíše dostupné modely
    if message.content.strip() == "/models":
        models_list = "\n".join(f"{i+1}. `{m}`" for i, m in enumerate(AVAILABLE_MODELS))
        await message.channel.send(f"**Dostupné modely:**\n{models_list}\n\nAktuální: `{current_model}`")
        return

    # /model - zobrazí nebo změní model
    if message.content.startswith("/model"):
        parts = message.content.split(" ", 1)
        if len(parts) < 2 or parts[1].strip() == "":
            await message.channel.send(f"Aktuální model: `{current_model}`")
        else:
            new_model = parts[1].strip()
            if new_model not in AVAILABLE_MODELS:
                models_list = "\n".join(f"- `{m}`" for m in AVAILABLE_MODELS)
                await message.channel.send(f"❌ Model `{new_model}` neexistuje. Dostupné modely:\n{models_list}")
            else:
                current_model = new_model
                await message.channel.send(f"✅ Model změněn na: `{current_model}`")
        return

    async with message.channel.typing():
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": current_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Na konci každé odpovědi napiš krátkou, vtipnou připomínku aby si uživatel sedl nebo stál rovně. Pokaždé ji formuluj trochu jinak."
                    },
                    {"role": "user", "content": message.content}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            async with session.post(LLM_API, json=payload) as resp:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"]

    if len(reply) > 2000:
        reply = reply[:1997] + "..."

    await message.channel.send(reply)

client.run(DISCORD_TOKEN)
