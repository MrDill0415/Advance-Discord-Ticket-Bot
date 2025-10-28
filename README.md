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
   
2.Install dependencies
  pip install -r requirements.txt
  
3.Edit configuration constants in bot.py
  Replace the *_ID values with your own Discord server, channel, and role IDs.
(These control where tickets are created, where transcripts are sent, and which roles have staff permissions.)
   THERE WILL BE # NEXT TO EVERYTHING YOU NEED TO REPLACE

4.Run The Bot
  python bot.py

📄 Ticket Transcripts

When a ticket is closed:
A text transcript is automatically generated.
The transcript is uploaded to your configured transcripts channel.
Messages and attachments are logged in chronological order.

🤖 Example Workflow
A user types !ticket in your main server.
A private ticket channel is created in your support guild.
Messages between the user’s DM and the staff channel are synced in real time.
Staff can claim, close, and log tickets seamlessly.

🧩 Future Improvements
Persistent database for ticket logs
Web-based authentication and access control
Custom AI support responses
Multi-language support

🪪 License
This project is open source under the MIT License.
💜 Created with discord.py + FastAPI
  Developed by MrDill0415
  🔗 https://github.com/MrDill0415/Advance-Discord-Ticket-Bot
