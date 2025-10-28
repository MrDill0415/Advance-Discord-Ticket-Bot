# 🎟️ MrDills Advance Ticket Bot

A powerful and customizable **Discord support ticket bot** built using **discord.py** and **FastAPI**.  
Designed for multi-server setups — the bot connects your main Discord server with a private support guild for staff communication.

> 🧠 Built and maintained by [**MrDill0415**](https://github.com/MrDill0415)

---

## 🚀 Features

- 📨 **DM ↔ Channel Relay** – Users chat privately in DMs, and staff see messages in ticket channels.
- 🎫 **Claim System** – Only one staff member can reply; others have view-only access.
- 🗑️ **Close Confirmation** – Users confirm before closing; transcripts are automatically generated and sent to the transcript channel.
- 🎧 **Join Call Button** – Users can request and receive temporary voice call invites directly in DMs.
- 📢 **Notify Staff Button** – Users can alert support staff for urgent help.
- 🌐 **FastAPI Web Dashboard**  
  - Edit the default ticket message  
  - Rename tickets in real time  
  - Send quick AI-style auto replies  

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **discord.py**
- **FastAPI**
- **Uvicorn**
- **asyncio**

---

## ⚙️ Setup

1. **Clone this repository:**
   ```bash
   git clone https://github.com/MrDill0415/Advance-Discord-Ticket-Bot.git
   cd Advance-Discord-Ticket-Bot
   
2. Install Dependencies.
  pip install -r requirements.txt

3.Edit configuration constants in bot.py.
  Replace the *_ID values with your own Discord server, channel, and role IDs.
(These control where tickets are created, where transcripts are sent, and which roles have staff permissions.)

4. Run the Bot!
   bash
   python bot.py
