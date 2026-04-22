import discord
from discord import app_commands
import aiohttp
import asyncio

DISCORD_TOKEN = "secret"
LLM_API = "http://192.168.22.154:8000/v1/chat/completions"

AVAILABLE_MODELS = [
    "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M",
    "Qwen3.6-35B-A3B-UD-Q5_K_XL.gguf",
    "Qwen3VL-8B-Uncensored-HauhauCS-Balanced",
]

current_model = AVAILABLE_MODELS[0]

# 🧠 paměť: (guild_id, user_id)
memory = {}

# 📥 fronta
queue = asyncio.Queue()


class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(worker())


bot = MyBot()


@bot.event
async def on_ready():
    print(f"Bot běží jako {bot.user}")


# 🔎 autocomplete modelů
async def model_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=m, value=m)
        for m in AVAILABLE_MODELS
        if current.lower() in m.lower()
    ][:25]


# 📌 /model
@bot.tree.command(name="model", description="Změní model")
@app_commands.autocomplete(new_model=model_autocomplete)
async def model(interaction: discord.Interaction, new_model: str):
    global current_model

    if new_model not in AVAILABLE_MODELS:
        await interaction.response.send_message("❌ Neplatný model", ephemeral=True)
        return

    current_model = new_model
    await interaction.response.send_message(f"✅ Model: `{current_model}`", ephemeral=True)


# 🧹 reset paměti
@bot.tree.command(name="reset", description="Smaže paměť")
async def reset(interaction: discord.Interaction):
    key = (interaction.guild_id, interaction.user.id)
    memory.pop(key, None)
    await interaction.response.send_message("🧠 Paměť smazána", ephemeral=True)


# 💬 /ask
@bot.tree.command(name="ask", description="Zeptej se AI")
@app_commands.describe(prompt="Co chceš vědět?")
async def ask(interaction: discord.Interaction, prompt: str):
    thinking = await interaction.response.send_message("⏳ Přemýšlím...", ephemeral=False)

    await queue.put((interaction, prompt))


# ⚙️ worker (zpracování fronty)
async def worker():
    await bot.wait_until_ready()

    while True:
        interaction, prompt = await queue.get()

        try:
            key = (interaction.guild_id or 0, interaction.user.id)

            if key not in memory:
                memory[key] = [
                    {
                        "role": "system",
                        "content": "Na konci odpovědi napiš krátkou vtipnou poznámku o držení těla."
                    }
                ]

            memory[key].append({"role": "user", "content": prompt})
            memory[key] = memory[key][-10:]

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": current_model,
                    "messages": memory[key],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }

                async with session.post(LLM_API, json=payload) as resp:
                    data = await resp.json()
                    reply = data["choices"][0]["message"]["content"]

            memory[key].append({"role": "assistant", "content": reply})

            if len(reply) > 2000:
                reply = reply[:1997] + "..."

            await interaction.followup.send(reply)

        except Exception as e:
            await interaction.followup.send(f"❌ Chyba: {e}")

        queue.task_done()


bot.run(DISCORD_TOKEN)
