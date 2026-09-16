"""
discordBot.py

Discord front-end for FacultyTwin.

Why this exists: the grant proposal promises a "Discord-integrated chatbot...
deployed in Discord where undergraduates already congregate." The existing
app only exposed a raw WebSocket endpoint (see main.py), so there was no
actual Discord surface. This module adds one, reusing the same knowledge
base, sentiment/wellbeing pipeline, and Ollama call that main.py's
websocket_endpoint already uses -- so behavior stays consistent whether a
student talks to the bot via the web widget or via Discord.

Recommended: don't run this file directly. Set DISCORD_BOT_TOKEN and start
`python main.py` (or `python run_chatbot.py`) -- main.py's startup event
launches this bot inside the same process, so it shares the live
knowledge_base/chat_history/wellbeing_flags objects with the web widget.

Standalone mode (`python discordBot.py`) is still supported as a fallback,
but note it runs as its own process: `from main import ...` below will
re-execute main.py fresh, so this bot gets its own empty knowledge base and
chat history, separate from any main.py server you're running elsewhere.
Only use standalone mode if that separation is actually what you want.

Requires:
    pip install discord.py
    DISCORD_BOT_TOKEN environment variable (see README.md)
"""

import os
import datetime
import discord
from discord.ext import commands
import ollama

# Reuse the already-initialized knowledge base, wellbeing monitor, and
# in-memory stores from main.py rather than duplicating them.
from main import (
    knowledge_base,
    wellbeing_monitor,
    chat_history,
    student_interactions,
    wellbeing_flags,
)
import nudgeEngine

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def _log_interaction(student_id: str, message: str, msg_type: str, wellbeing_score: float = None):
    interaction = {
        "timestamp": datetime.datetime.now().isoformat(),
        "student_id": student_id,
        "message": message,
        "type": msg_type,
        "channel": "discord",
    }
    if wellbeing_score is not None:
        interaction["wellbeing_score"] = wellbeing_score

    student_interactions.setdefault(student_id, []).append(interaction)
    chat_history.append(interaction)


async def generate_reply(student_id: str, user_message: str) -> dict:
    """Shared logic: analyze wellbeing, retrieve context, call the model."""
    wellbeing_analysis = wellbeing_monitor.analyze_message(user_message, student_id)

    relevant_docs = knowledge_base.search_similar(user_message)
    context = "\n".join([doc["content"] for doc in relevant_docs[:2]])

    prompt = f"""You are a helpful academic assistant for undergraduate students in C++ programming and algorithms courses.

Context from course materials:
{context}

Student question: {user_message}

Please provide a helpful, encouraging response. If the question is about course content, use the context provided. If it's about programming, provide clear explanations and examples. Always be supportive and understanding of student stress.

Response:"""

    try:
        response = ollama.generate(model="llama3.1:8b", prompt=prompt, stream=False)
        bot_response = response["response"]
    except Exception:
        bot_response = "I'm sorry, I'm having trouble processing your request right now. Please try again or contact your instructor."

    return {
        "response": bot_response,
        "wellbeing_score": wellbeing_analysis["wellbeing_score"],
        "flagged": wellbeing_analysis["flag_for_review"],
    }


@bot.event
async def on_ready():
    print(f"✅ FacultyTwin Discord bot logged in as {bot.user}")
    # Start the deadline-nudge background loop (see nudgeEngine.py)
    nudgeEngine.start_nudge_loop(bot)


@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Usage: !ask <question>"""
    student_id = f"discord:{ctx.author.id}"
    _log_interaction(student_id, question, "user")

    async with ctx.typing():
        result = await generate_reply(student_id, question)

    _log_interaction(student_id, result["response"], "bot", result["wellbeing_score"])

    await ctx.reply(result["response"])

    if result["flagged"]:
        # Don't expose the flag in the public channel -- just log it.
        # A real deployment would route this to wellbeing_flags reviewers,
        # not post it publicly.
        print(f"⚠️  WELLBEING FLAG (Discord): {student_id} scored {result['wellbeing_score']:.1f}")


@bot.command(name="subscribe_nudges")
async def subscribe_nudges(ctx):
    """Opt in to deadline reminder DMs (see nudgeEngine.py)."""
    student_id = f"discord:{ctx.author.id}"
    nudgeEngine.subscribe(student_id, ctx.author.id)
    await ctx.reply("You're subscribed to deadline reminders. Use `!unsubscribe_nudges` to opt out anytime.")


@bot.command(name="unsubscribe_nudges")
async def unsubscribe_nudges(ctx):
    student_id = f"discord:{ctx.author.id}"
    nudgeEngine.unsubscribe(student_id)
    await ctx.reply("You've been unsubscribed from deadline reminders.")


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise SystemExit(
            "DISCORD_BOT_TOKEN is not set. Create a bot at "
            "https://discord.com/developers/applications, enable the "
            "'Message Content Intent', and export the token before running."
        )
    bot.run(DISCORD_BOT_TOKEN)