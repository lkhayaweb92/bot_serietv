import re
import time
from telebot import types
from settings import ALBUM, MISCELLANIA, PREMIUM_CHANNELS, REQUIRED_CHANNEL_ID, PointsName
from model import Database, Utente, UserSeasonProgress, Season

class ChannelDownloader:
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message
        self.chat_id = message.chat.id
        self.user_id = message.from_user.id
        
        # Collect all valid source channel IDs
        self.valid_channels = []
        for d in [ALBUM, MISCELLANIA, PREMIUM_CHANNELS]:
            self.valid_channels.extend(list(d.values()))

    def extract_link_info(self, message):
        """
        Robustly extracts channel and message ID from t.me/c/ links.
        Checks: Text, Caption, Text-Link Entities, and Inline Buttons.
        Guaranteed to take the LAST numeric part as message ID.
        """
        raw_sources = []
        
        # 1. Text and Caption
        if message.text: raw_sources.append(message.text)
        if message.caption: raw_sources.append(message.caption)
        
        # 2. Text Link Entities (Hyperlinks)
        entities = (message.entities or []) + (message.caption_entities or [])
        for ent in entities:
            if ent.type == 'text_link' and ent.url:
                raw_sources.append(ent.url)
        
        # 3. Inline Buttons
        if hasattr(message, 'reply_markup') and message.reply_markup:
            if hasattr(message.reply_markup, 'inline_keyboard'):
                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if hasattr(btn, 'url') and btn.url:
                            raw_sources.append(btn.url)

        # Process found strings
        for s in raw_sources:
            if "t.me/c/" in s:
                # Find the start of the path
                match = re.search(r"t\.me/c/(\d+)(.+)", s)
                if match:
                    channel_id = f"-100{match.group(1)}"
                    # Find all numbers in the tail
                    nums = re.findall(r"(\d+)", match.group(2))
                    if nums:
                        return channel_id, int(nums[-1])
            
        return None, None

    def get_user_premium_status(self):
        """Checks if the user has an active Premium Season Pass."""
        session = Database().Session()
        try:
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                return False
            prog = session.query(UserSeasonProgress).filter_by(user_id=self.user_id, season_id=season.id).first()
            return prog.is_premium_pass if prog else False
        finally:
            session.close()

    def get_channel_cost(self, chat_id):
        """Returns the cost associated with a channel ID."""
        s_id = str(chat_id)
        if s_id in PREMIUM_CHANNELS.values():
            return 50
        if s_id in ALBUM.values():
            return 15
        if s_id in MISCELLANIA.values():
            return 5
        return 0

    def handle_forward(self):
        """
        Processes a forwarded message or a message with a link.
        Deduct points and starts sequential download.
        """
        import traceback
        try:
            source_id = None
            start_msg_id = None
            is_redirection = False
            
            forward_source_id = str(self.message.forward_from_chat.id) if self.message.forward_from_chat else None

            # 1. Check for Link first (Direct paste, caption, or button)
            link_channel, link_msg = self.extract_link_info(self.message)
            
            if link_channel:
                source_id = link_channel
                start_msg_id = link_msg
                is_redirection = True
                print(f"[ChannelDownloader] Link found! Target: {source_id}, Msg: {start_msg_id}")
            elif forward_source_id:
                source_id = forward_source_id
                start_msg_id = self.message.forward_from_message_id
                print(f"[ChannelDownloader] Forward found! Source: {source_id}, Msg: {start_msg_id}")

            if not source_id or not start_msg_id:
                return False

            # 2. Verify source channel
            if source_id not in self.valid_channels:
                print(f"[ChannelDownloader] Unknown/Unauthorized source: {source_id}")
                return False

            # --- Access verification ---
            try:
                source_int_id = int(source_id)
                self.bot.get_chat(source_int_id)
            except Exception as e_access:
                print(f"[ChannelDownloader] Access error for {source_id}: {e_access}")
                self.bot.reply_to(self.message, f"❌ **Accesso Negato.**\nNon ho i permessi per accedere al canale sorgente (`{source_id}`).\nAssicurati che io sia stato aggiunto come amministratore.")
                return True

            # 3. Calculate Cost (Max between entry point and destination)
            is_premium_user = self.get_user_premium_status()
            
            if is_premium_user:
                cost = 0
            else:
                # Cost of where the message came from (if forwarded)
                cost_of_entry = self.get_channel_cost(forward_source_id) if forward_source_id else 0
                # Cost of where the link points to
                cost_of_destination = self.get_channel_cost(source_id)
                # Take the HIGHER price
                cost = max(cost_of_entry, cost_of_destination)

            print(f"[ChannelDownloader] User: {self.user_id}, Premium: {is_premium_user}, Entry: {forward_source_id}, Dest: {source_id}, Final Cost: {cost}")

            # 4. Check Points
            utente = Utente().getUtente(self.user_id)
            if not utente:
                print(f"[ChannelDownloader] User not found in DB: {self.user_id}")
                return False
                
            if utente.points < cost:
                self.bot.reply_to(self.message, f"❌ Ti servono {cost} {PointsName} per scaricare questa serie!\nAttualmente ne hai: {utente.points}")
                return True

            # 5. Deduct and confirm BEFORE sending any files
            if cost > 0:
                Database().update_user(self.user_id, {'points': utente.points - cost})
                self.bot.send_message(self.chat_id, f"📂 **Download avviato!** Pagato: {cost} {PointsName}.")
            else:
                self.bot.send_message(self.chat_id, "💎 **Download Premium/Gratuito** avviato!")

            # 6. Pre-check: Try to forward the first message
            start_index = 0 if is_redirection else 1
            target_preview_id = start_msg_id + start_index
            try:
                self.bot.forward_message(self.chat_id, source_int_id, target_preview_id)
            except Exception as e_start:
                err_msg = str(e_start)
                print(f"[ChannelDownloader] Pre-check failed at {target_preview_id}: {err_msg}")
                self.bot.reply_to(self.message, f"⚠️ **Contenuto non trovato.**\nNon riesco a trovare l'episodio (ID `{target_preview_id}`) nel canale.\nDettaglio: `{err_msg}`")
                return True

            # 7. Start loop for remaining messages
            self.loop_and_forward(source_int_id, start_msg_id, start_index + 1)
            return True

        except Exception as e:
            full_error = traceback.format_exc()
            print(f"[ERROR] ChannelDownloader crash:\n{full_error}")
            self.bot.reply_to(self.message, f"🚨 **Errore Interno (Crash)**\nSi è verificato un errore imprevisto.\n\n`{str(e)}`")
            return True

    def loop_and_forward(self, source_chat_id, start_id, start_index=1):
        """
        Sequentially forwards messages.
        """
        MAX_MESSAGES = 200 
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 3 
        
        for i in range(start_index, MAX_MESSAGES + start_index):
            next_id = start_id + i
            try:
                # Use forward_message to get the full Message object (needed for content_type check)
                msg = self.bot.forward_message(self.chat_id, source_chat_id, next_id)
                consecutive_errors = 0
                
                if msg.content_type == 'sticker':
                    self.bot.delete_message(self.chat_id, msg.message_id)
                    self.bot.send_message(self.chat_id, "🏁 **Fine della serie!**")
                    break
                
                time.sleep(0.3)
                
            except Exception as e:
                err_msg = str(e)
                print(f"Error at {next_id}: {err_msg}")
                
                if "message to forward not found" in err_msg:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        self.bot.send_message(self.chat_id, "✅ **Caricamento completato.**")
                        break
                    continue 
                else:
                    self.bot.send_message(self.chat_id, f"🛑 **Interrotto:** `{err_msg}`")
                    break
