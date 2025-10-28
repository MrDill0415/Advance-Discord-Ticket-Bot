# bot.py
import discord
from discord.ext import commands
import asyncio
import io
from datetime import datetime
import threading
import uvicorn
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# ---------------- CONFIG ----------------
MAIN_GUILD_ID = 1234567812345678 #GUILD ID
MAIN_TICKET_CHANNEL_ID = 1234567812345678 #WHERE PEOPLE USE THE COMMAND !TICKET
SUPPORT_GUILD_ID = 1234567812345678 #STAFF/SUPPORT GUILD ID
SUPPORT_TICKET_CATEGORY_ID = 1234567812345678 #THE CATEGORY TICKETS GET CREATED IN
SUPPORT_STAFF_ROLE_ID = 1234567812345678 #ROLE ON WHICH THE SUPPORT CAN VIEW THE TICKETS
TRANSCRIPTS_CHANNEL_ID = 1234567812345678 #CHANNEL WHERE TRANSCRIPTS GET SAVED
CALL_TRANSCRIPTS_CHANNEL_ID = 1234567812345678 #CHANNEL WHERE VC TRANSCRIPTS GET SAVED
TICKET_CHANNEL_PREFIX = "ticket-"

WAITING_VC_ID = 1234567812345678 #THE CALL THAT PEOPLE JOIN ONCE THEY CLICK JOIN CALL IN DMS.

DEFAULT_TICKET_MESSAGE = "🎟️ Your ticket has been created! Send messages here to talk to staff."

# ---------------- SETUP ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.dm_messages = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_tickets = {}  # user_id -> ticket_channel_id

# ---------------- HELPERS ----------------
def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")

async def generate_ticket_transcript(channel: discord.TextChannel):
    messages = [m async for m in channel.history(limit=None, oldest_first=True)]
    lines = []
    for msg in messages:
        ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"[{ts}] {msg.author} ({msg.author.id})\n")
        if msg.content:
            lines.append(f"  {msg.content}\n")
        for att in msg.attachments:
            lines.append(f"  📎 Attachment: {att.filename} ({att.url})\n")
    b = io.BytesIO("".join(lines).encode("utf-8"))
    fname = f"transcript-{channel.name}-{now_str()}.txt"
    return discord.File(b, filename=fname)

# ---------------- VIEWS ----------------
class UserTicketDMView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🗑️ Close Ticket", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Are you sure you want to close this ticket?", ephemeral=True)
        confirm_view = ConfirmCloseView(self.user_id)
        await interaction.user.send("Please confirm ticket closure:", view=confirm_view)

    @discord.ui.button(label="🎧 Join Call", style=discord.ButtonStyle.primary)
    async def join_call_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_guild = bot.get_guild(1234567812345678) #SUPPORT GUILD ID
        if not support_guild:
            await interaction.response.send_message("❌ Could not find the support server.", ephemeral=True)
            return

        vc = support_guild.get_channel(1234567812345678) #SUPPORT VC ID
        if not vc:
            await interaction.response.send_message("❌ Could not find the waiting voice channel.", ephemeral=True)
            return

        try:
            invite = await vc.create_invite(max_age=3600, max_uses=1, unique=True, reason="Support ticket join")
            await interaction.response.send_message(
                f"🎧 Click here to join the support call: {invite.url}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not create invite: {e}", ephemeral=True)

    @discord.ui.button(label="📢 Notify Staff", style=discord.ButtonStyle.secondary)
    async def notify_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.user_id in active_tickets:
            support_guild = bot.get_guild(SUPPORT_GUILD_ID)
            ticket_channel = support_guild.get_channel(active_tickets[self.user_id])
            staff_role = discord.utils.get(support_guild.roles, id=SUPPORT_STAFF_ROLE_ID)
            mention = staff_role.mention if staff_role else "Support Team"
            if ticket_channel:
                await ticket_channel.send(f"📢 {mention} User requested staff attention!")
                await interaction.response.send_message("✅ Staff notified!", ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await finalize_close(self.user_id)
        await interaction.response.send_message("✅ Ticket closed.", ephemeral=True)
        self.stop()

# ---------------- TICKET CREATION ----------------
@bot.command()
async def ticket(ctx):
    if ctx.guild is None or ctx.guild.id != MAIN_GUILD_ID or ctx.channel.id != MAIN_TICKET_CHANNEL_ID:
        await ctx.send("❌ Use this command in the designated channel only.")
        return

    if ctx.author.id in active_tickets:
        await ctx.send("You already have an open ticket. Check your DMs.")
        try:
            await ctx.author.send("You already have an open ticket. Send messages here to talk to staff.")
        except:
            pass
        return

    support_guild = bot.get_guild(SUPPORT_GUILD_ID)
    category = discord.utils.get(support_guild.categories, id=SUPPORT_TICKET_CATEGORY_ID)
    staff_role = discord.utils.get(support_guild.roles, id=SUPPORT_STAFF_ROLE_ID)

    overwrites = {
        support_guild.default_role: discord.PermissionOverwrite(read_messages=False),
        support_guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
    }

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=False,
            read_message_history=True
        )

    safe_name = ctx.author.name.replace(" ", "-").lower()[:20]
    channel_name = f"{TICKET_CHANNEL_PREFIX}{safe_name}-{ctx.author.discriminator}"
    ticket_channel = await support_guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket created by {ctx.author}"
    )

    active_tickets[ctx.author.id] = ticket_channel.id

    try:
        await ctx.author.send(DEFAULT_TICKET_MESSAGE, view=UserTicketDMView(ctx.author.id))
    except discord.Forbidden:
        await ctx.send("❌ Could not DM you. Enable DMs from server members.")

    mention = staff_role.mention if staff_role else "Support Team"
    await ticket_channel.send(
        f"📩 New ticket opened by **{ctx.author}** ({ctx.author.id})\n{mention}",
        view=StaffTicketView(ctx.author.id)
    )
    await ctx.send("✅ Ticket created! Check your DMs.")

# ---------------- STAFF TICKET VIEW ----------------
class StaffTicketView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.claimed_by = None

    async def _has_permission(self, interaction: discord.Interaction):
        support_guild = bot.get_guild(SUPPORT_GUILD_ID)
        mod_roles = [r for r in support_guild.roles if any(k in r.name.lower() for k in ["mod", "admin", "owner"])]
        is_mod = any(r in interaction.user.roles for r in mod_roles)
        return (
            interaction.user.id == self.claimed_by or
            interaction.user.id == self.user_id or
            is_mod
        )

    @discord.ui.button(label="🎫 Claim Ticket", style=discord.ButtonStyle.success)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_guild = bot.get_guild(SUPPORT_GUILD_ID)
        staff_role = discord.utils.get(support_guild.roles, id=SUPPORT_STAFF_ROLE_ID)
        channel = interaction.channel

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only support staff can claim tickets.", ephemeral=True)
            return

        if self.claimed_by:
            await interaction.response.send_message("⚠️ This ticket is already claimed.", ephemeral=True)
            return

        self.claimed_by = interaction.user.id
        button.disabled = True

        overwrites = channel.overwrites

        if staff_role in overwrites:
            overwrites[staff_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                read_message_history=True
            )

        overwrites[interaction.user] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            read_message_history=True
        )

        try:
            user = await bot.fetch_user(self.user_id)
            overwrites[user] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                read_message_history=True
            )
        except:
            pass

        await channel.edit(overwrites=overwrites)
        await channel.edit(topic=f"Claimed by {interaction.user.name} ({interaction.user.id})")

        await interaction.response.edit_message(
            content=f"🎫 Ticket claimed by {interaction.user.mention}",
            view=self
        )
        await channel.send(f"✅ {interaction.user.mention} has claimed this ticket. Other staff can only view messages.")

        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(f"💬 Your ticket has been picked up by **{interaction.user.name}**. They'll assist you shortly!")
        except:
            pass

    @discord.ui.button(label="🗑️ Close Ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_permission(interaction):
            await interaction.response.send_message("❌ You don't have permission to close this ticket.", ephemeral=True)
            return

        await finalize_close(self.user_id)
        await interaction.response.send_message("✅ Ticket closed successfully.", ephemeral=True)

# ---------------- MESSAGE RELAY ----------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # DM -> Ticket
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in active_tickets:
            support_guild = bot.get_guild(SUPPORT_GUILD_ID)
            ticket_channel = support_guild.get_channel(active_tickets[message.author.id])
            if ticket_channel:
                await ticket_channel.send(f"**{message.author}:** {message.content}")
                for att in message.attachments:
                    await ticket_channel.send(att.url)
        else:
            await message.channel.send("❌ You don't have an open ticket. Use `!ticket` in the main server.")
        return

    # Ticket -> DM
    if message.guild and message.guild.id == SUPPORT_GUILD_ID:
        if message.channel.category_id == SUPPORT_TICKET_CATEGORY_ID:
            owner_id = next((uid for uid, cid in active_tickets.items() if cid == message.channel.id), None)
            if owner_id:
                user = await bot.fetch_user(owner_id)
                try:
                    await user.send(f"**{message.author} (Staff):** {message.content}")
                    for att in message.attachments:
                        await user.send(att.url)
                except discord.Forbidden:
                    await message.channel.send("⚠️ Cannot DM user; they may have DMs disabled.")

    await bot.process_commands(message)

# ---------------- FINALIZE CLOSE ----------------
async def finalize_close(user_id: int):
    if user_id not in active_tickets:
        return
    support_guild = bot.get_guild(SUPPORT_GUILD_ID)
    ticket_channel = support_guild.get_channel(active_tickets[user_id])
    if ticket_channel:
        try:
            user = await bot.fetch_user(user_id)
            await user.send("✅ Your ticket has been closed.")
        except:
            pass

        transcripts_chan = bot.get_channel(TRANSCRIPTS_CHANNEL_ID)
        if transcripts_chan:
            f = await generate_ticket_transcript(ticket_channel)
            topic = ticket_channel.topic or "No claimer info"
            await transcripts_chan.send(f"📄 Transcript for {ticket_channel.name} ({topic})", file=f)

        await ticket_channel.delete(reason="Ticket closed")

    if user_id in active_tickets:
        del active_tickets[user_id]

# ---------------- FASTAPI GUI ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

gui_ticket_message = DEFAULT_TICKET_MESSAGE

@app.get("/", response_class=HTMLResponse)
async def gui():
    support_guild = bot.get_guild(SUPPORT_GUILD_ID)
    ticket_options = ""
    for uid, cid in active_tickets.items():
        ticket_chan = support_guild.get_channel(cid)
        if ticket_chan:
            ticket_options += f'<option value="{uid}">{ticket_chan.name}</option>'

    html = f"""
    <html>
    <head>
        <title>Ticket Bot GUI</title>
        <style>
            body {{ background-color: black; color: purple; font-family: monospace; padding: 20px; }}
            input, select, button {{ padding: 8px; margin: 5px; }}
            label {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Edit Default Ticket Message</h2>
        <input type="text" id="ticket_message" value="{gui_ticket_message}" style="width: 400px;">
        <button onclick="updateMessage()">Save</button>

        <h2>Rename Ticket</h2>
        <select id="rename_select">{ticket_options}</select>
        <input type="text" id="rename_input" placeholder="New ticket name">
        <button onclick="renameTicket()">Rename</button>

        <h2>AI Reply</h2>
        <select id="ai_select">{ticket_options}</select>
        <button onclick="aiReply()">Send AI Reply</button>

        <script>
            async function updateMessage() {{
                let msg = document.getElementById('ticket_message').value;
                await fetch('/edit-ticket-message', {{
                    method:'POST',
                    body: new URLSearchParams({{ message: msg }})
                }});
                alert('Default message updated');
            }}

            async function renameTicket() {{
                let user_id = document.getElementById('rename_select').value;
                let new_name = document.getElementById('rename_input').value;
                let res = await fetch(`/rename-ticket/${{user_id}}`, {{
                    method:'POST',
                    body: new URLSearchParams({{ new_name: new_name }})
                }});
                let data = await res.json();
                alert(data.status === 'ok' ? 'Ticket renamed!' : 'Error renaming ticket');
            }}

            async function aiReply() {{
                let user_id = document.getElementById('ai_select').value;
                let res = await fetch(`/ai-reply/${{user_id}}`, {{ method: 'POST' }});
                let data = await res.json();
                alert(data.status === 'ok' ? 'AI reply sent!' : 'Error sending AI reply');
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.post("/edit-ticket-message")
async def edit_ticket_message(message: str = Form(...)):
    global gui_ticket_message
    gui_ticket_message = message
    return {"status": "ok"}

@app.post("/rename-ticket/{user_id}")
async def rename_ticket(user_id: int, new_name: str = Form(...)):
    if user_id in active_tickets:
        support_guild = bot.get_guild(SUPPORT_GUILD_ID)
        chan = support_guild.get_channel(active_tickets[user_id])
        if chan:
            await chan.edit(name=new_name)
            return {"status": "ok"}
    return {"status": "failed"}

@app.post("/ai-reply/{user_id}")
async def ai_reply(user_id: int):
    if user_id in active_tickets:
        support_guild = bot.get_guild(SUPPORT_GUILD_ID)
        ticket_chan = support_guild.get_channel(active_tickets[user_id])
        if ticket_chan:
            await ticket_chan.send("🤖 AI: We'll be right there to assist you!")
            return {"status": "ok"}
    return {"status": "failed"}

def start_web_gui():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# ---------------- BOT READY ----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    threading.Thread(target=start_web_gui, daemon=True).start()

# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    bot.run("BOT TOKEN") #PUT YOUR BOT TOKEN INSIDE THE "BOT TOKEN"