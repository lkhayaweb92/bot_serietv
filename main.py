from telebot import types
from settings import *
from sqlalchemy         import create_engine
from model import Livello, Utente, Abbonamento, Database, GiocoUtente,Collezionabili, use_dragon_balls_logic
import Points
from telebot import util
import schedule,time,threading
import datetime
import random
import re

@bot.message_handler(content_types=['left_chat_member'])
def esciDalGruppo(message):
    chatid = message.left_chat_member.id
    try:
        username = message.left_chat_member.username
        name = message.left_chat_member.first_name
        label = f"@{username}" if username else name
        
        Database().delete_user_complete(chatid)
        bot.send_message(CANALE_LOG, f"L'utente {label} ({chatid}) è uscito dal gruppo. Tutti i suoi dati (punti, premium, inventario) sono stati eliminati definitivamente.")
    except Exception as e:
        print('Errore ',str(e))

def compact_db_job():
    if datetime.date.today().day != 1:
        return

    try:
        count = Database().compact_user_ids()
        bot.send_message(CANALE_LOG, f"AUTO-CLEAN: Database compattato con successo. {count} utenti ri-indicizzati.")
    except Exception as e:
        try: bot.send_message(CANALE_LOG, f"AUTO-CLEAN ERROR: {str(e)}")
        except: pass

@bot.message_handler(content_types=['new_chat_members'])
def newmember(message):
    punti = Points.Points()
    punti.welcome(message)

@bot.message_handler(commands=['start'])
def start(message):
    punti_check = Points.Points().checkBeforeAll(message)
    if punti_check[0] is None:
        return
    
    Points.Points().welcome(message)
    # The start menu will be shown by handle_all_commands
    # but we can explicitly show it for start too
    bot.reply_to(message, "Cosa vuoi fare?", reply_markup=Database().startMarkup(punti_check[0]))
    handle_all_messages(message)

class BotCommands:
    def __init__(self, message, bot):
        self.bot = bot
        self.message = message
        self.comandi_privati = {
            "👤 Scegli il personaggio": self.handle_choose_character_v2,
            
            "Compra abbonamento Premium (1 mese)": self.handle_buy_premium,
            "✖️ Disattiva rinnovo automatico": self.handle_disattiva_abbonamento_premium,
            "✅ Attiva rinnovo automatico": self.handle_attiva_abbonamento_premium,
            "classifica": self.handle_classifica,
            "nome in game": self.handle_nome_in_game,
            "compro un altro mese": self.handle_buy_another_month,
            "ℹ️ info": self.handle_info,
            "📦 Inventario": self.handle_inventario,
            "🧪 Negozio Pozioni": self.handle_negozio_pozioni,
            "🧪 Pozione Rigenerante": self.handle_buy_potion,
            "🧪 Pozione Aura": self.handle_buy_potion,
            "📊 ALLOCAZIONE STATISTICHE": self.handle_stats_menu,
            "Indietro": self.handle_back,  
        }

        self.comandi_admin = {
            "addLivello": self.handle_add_livello,
            "+": self.handle_plus_minus,
            "-": self.handle_plus_minus,
            "restore": self.handle_restore,
            "backup": self.handle_backup,
            "extra": self.handle_backup_all,
            "checkPremium":self.handle_checkScadenzaPremiumToAll,
            "broadcast": self.handle_broadcast,
            "compatta": self.handle_compatta,
            
        }
        self.comandi_generici = {
            "!dona": self.handle_dona,
            "/me": self.handle_me,
            "!status": self.handle_status,
            "!classifica": self.handle_classifica,
            "!stats": self.handle_stats,
            "!livell": self.handle_livell,
            "album": self.handle_album,
            "!inventario": self.handle_inventario,
            "/inventario": self.handle_inventario,
            "!negozio_pozioni": self.handle_negozio_pozioni,
            "/negozio_pozioni": self.handle_negozio_pozioni,
            
        }
        try:
            self.chatid = message.from_user.id
        except Exception as e:
            self.chatid = message.chat.id
    
    def handle_private_command(self):
        message = self.message
        if hasattr(message.forward_from_chat,'id'):
            buy1game(message)
        else:
            for command in self.comandi_privati.items():
                if command[0].lower() in message.text.lower():
                    command[1]()
                    break
    def handle_admin_command(self):
        message = self.message
        for command in self.comandi_admin.items():
            if command[0].lower() in message.text.lower():
                command[1]()
                break
    def handle_generic_command(self):
        message = self.message
        for command in self.comandi_generici.items():
            if command[0].lower() in message.text.lower():
                command[1]()
                break

    def handle_negozio_pozioni(self):
        pozioni = [
            {"nome": "Pozione Rigenerante Piccola", "prezzo": 100, "effetto": "Rigenera 100 punti"},
            {"nome": "Pozione Rigenerante Media", "prezzo": 200, "effetto": "Rigenera 200 punti"},
            {"nome": "Pozione Rigenerante Grande", "prezzo": 500, "effetto": "Rigenera 500 punti"},
            {"nome": "Pozione Rigenerante Enorme", "prezzo": 1000, "effetto": "Rigenera 1000 punti"},
            {"nome": "Pozione Aura Piccola", "prezzo": 100, "effetto": "Rigenera 100 punti"},
            {"nome": "Pozione Aura Media", "prezzo": 200, "effetto": "Rigenera 200 punti"},
            {"nome": "Pozione Aura Grande", "prezzo": 500, "effetto": "Rigenera 500 punti"},
            {"nome": "Pozione Aura Enorme", "prezzo": 1000, "effetto": "Rigenera 1000 punti"},
        ]

        if not pozioni:
            msg = "Il negozio è vuoto, prova più tardi"
        else:
            msg = "🛒 Negozio Pozioni 🛒\n\n"
            for p in pozioni:
                msg += (
                    f"🧪 {p['nome']}\n"
                    f"💰 Prezzo: {p['prezzo']} fagioli\n"
                    f"✨ Effetto: {p['effetto']}\n\n"
                )

        keyboard = Database().negozioPozioniMarkup(self.chatid)

        self.bot.send_message(
            self.chatid,
            msg,
            reply_markup=keyboard
        )

    def handle_buy_potion(self):
        import datetime
        from model import DailyShop
        
        # 0. Identify Potion
        pozioni = {
            "Piccola": {"costo": 100, "vita": 100},
            "Media":   {"costo": 200, "vita": 200},
            "Grande":  {"costo": 500, "vita": 500},
            "Enorme":  {"costo": 1000, "vita": 1000},
        }
        
        tipo_pozione = None
        for tipo in pozioni:
            if tipo in self.message.text:
                tipo_pozione = tipo
                break
        
        if not tipo_pozione:
            self.bot.reply_to(self.message, "Tipo di pozione non riconosciuto.")
            return

        costo = pozioni[tipo_pozione]["costo"]
        vita_extra = pozioni[tipo_pozione]["vita"]
        utente = Utente().getUtente(self.chatid)
        
        # 1. Check Daily Limit
        session = Database().Session()
        oggi = datetime.date.today()
        # Filter by user, date, AND potion type
        # Extract full name from message or logic?
        # Message text IS the potion name e.g. "🧪 Pozione Rigenerante Piccola"
        full_potion_name = self.message.text.replace("🧪 ", "") # Remove emoji if present
        
        daily_shop = session.query(DailyShop).filter_by(id_utente=self.chatid, data=oggi, tipo_pozione=full_potion_name).first()
        
        if not daily_shop:
            daily_shop = DailyShop(id_utente=self.chatid, data=oggi, tipo_pozione=full_potion_name, pozioni_rimanenti=10)
            session.add(daily_shop)
            session.commit()
            
        if daily_shop.pozioni_rimanenti <= 0:
            self.bot.reply_to(self.message, f"⛔️ Hai terminato le {full_potion_name} per oggi (10/10)!", reply_markup=Database().negozioPozioniMarkup(self.chatid))
            session.close()
            return
            
        # 2. Check Funds
        if utente.points < costo:
            self.bot.reply_to(self.message, f"❌ Non hai abbastanza {PointsName}! Ti servono {costo} fagioli.", reply_markup=Database().negozioPozioniMarkup(self.chatid))
            session.close()
            return

        # 3. Execute Purchase
        try:
            # Deduct points
            Database().update_user(self.chatid, {'points': utente.points - costo})
            
            # Add to Inventory
            # Format: 'Pozione {Type} {Size}'
            if "Rigenerante" in self.message.text:
                category = "Rigenerante"
            elif "Aura" in self.message.text:
                category = "Aura"
            else:
                category = "Rigenerante" # Fallback

            nome_oggetto = f"Pozione {category} {tipo_pozione}"
            Collezionabili().CreateCollezionabile(self.chatid, nome_oggetto, 1)
            
            # Decrement Stock
            daily_shop.pozioni_rimanenti -= 1
            session.commit()
            
            # Confirm
            msg = f"✅ Hai acquistato una {nome_oggetto}!\n"
            msg += f"📦 È stata aggiunta al tuo inventario.\n"
            msg += f"💰 Costo: {costo}\n"
            msg += f"📦 Pozioni rimanenti oggi: {daily_shop.pozioni_rimanenti}"
            
            utente_updated = Utente().getUtente(self.chatid)
            self.bot.reply_to(self.message, msg + "\n\n" + Utente().infoUser(utente_updated), reply_markup=Database().negozioPozioniMarkup(self.chatid))
            
        except Exception as e:
            session.rollback()
            print(f"Errore acquisto pozione: {e}")
            self.bot.reply_to(self.message, "Errore durante l'acquisto, contatta un admin.")
        finally:
            session.close()

    def handle_info(self):
        try:
            utente = Utente().getUtente(self.chatid)
            msg = Utente().infoUser(utente)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📊 ALLOCAZIONE STATISTICHE", callback_data="stat_menu"))
            
            # Send message with markdown for bold stats
            self.bot.reply_to(self.message, msg, parse_mode='markdown', reply_markup=markup)
        except Exception as e:
            print(f"ERROR in handle_info: {e}")
            # Fallback without markdown
            self.bot.reply_to(self.message, msg, reply_markup=markup)

    def handle_stats_menu(self):
        utente = Utente().getUtente(self.chatid)
        
        # Calculate Points
        total_points = utente.livello * 2
        used_points = (utente.stat_vita + utente.stat_aura + utente.stat_danno + 
                       utente.stat_velocita + utente.stat_resistenza + utente.stat_crit_rate)
        available_points = total_points - used_points

        msg = "📊 ALLOCAZIONE STATISTICHE\n\n"
        msg += f"🎯 Punti Totali: {total_points} (Livello {utente.livello})\n"
        msg += f"✅ Punti Usati: {used_points}\n"
        msg += f"🆓 Punti Disponibili: {available_points}\n\n"
        msg += "Allocati:\n"
        msg += f"❤️ Vita: {utente.stat_vita} (+{utente.stat_vita * 10} HP)\n"
        msg += f"💙 Aura: {utente.stat_aura} (+{utente.stat_aura * 5} MP)\n"
        msg += f"⚔️ Danno: {utente.stat_danno} (+{utente.stat_danno * 2} DMG)\n"
        msg += f"⚡️ Velocità: {utente.stat_velocita} (+{utente.stat_velocita})\n"
        msg += f"🛡️ Resistenza: {utente.stat_resistenza} (+{utente.stat_resistenza}%)\n"
        msg += f"🎯 Crit Rate: {utente.stat_crit_rate} (+{utente.stat_crit_rate}% / Max 75%)\n\n"
        
        if available_points > 0:
            msg += f"💡 Hai {available_points} punto/i da allocare"
        else:
            msg += "✨ Tutti i punti sono stati allocati!"

        # Inline Keyboard
        markup = types.InlineKeyboardMarkup()
        if available_points > 0:
            markup.row(
                types.InlineKeyboardButton("❤️ +1", callback_data="stat_add_vita"),
                types.InlineKeyboardButton("💙 +1", callback_data="stat_add_aura")
            )
            markup.row(
                types.InlineKeyboardButton("⚔️ +1", callback_data="stat_add_danno"),
                types.InlineKeyboardButton("⚡️ +1", callback_data="stat_add_velocita")
            )
            markup.row(
                types.InlineKeyboardButton("🛡️ +1", callback_data="stat_add_resistenza"),
                types.InlineKeyboardButton("🎯 +1", callback_data="stat_add_crit_rate")
            )
        
        markup.add(types.InlineKeyboardButton("🔄 Reset Statistiche (500 Fagioli)", callback_data="stat_reset"))

        self.bot.send_message(self.chatid, msg, reply_markup=markup)

    def handle_back(self):
        utente = Utente().getUtente(self.chatid)
        self.bot.reply_to(self.message, "Torna al menu principale", reply_markup=Database().startMarkup(utente))

    def handle_inventario(self):
        inventario = Collezionabili().getInventarioUtente(self.chatid)
        msg = "📦 Inventario 📦\n\n"
        if inventario:
            for oggetto in inventario:
                if oggetto.oggetto not in ['TNT']:
                    if "Sfera del Drago" in oggetto.oggetto:
                        icon = "🐉"
                    elif oggetto.oggetto == "Nitro":
                        icon = "🚀"
                    elif oggetto.oggetto == "Cassa":
                        icon = "📦"
                    else:
                        icon = "🧷"
                    
                    msg += f"{icon} {oggetto.oggetto}"
                    if oggetto.quantita > 1:
                        msg += f" ({oggetto.quantita})"
                    msg += "\n"
        else:
            msg = "Il tuo inventario è vuoto, partecipa attivamente nel gruppo per trovare oggetti preziosi"
        

        keyboard = Database().startMarkup(Utente().getUtente(self.chatid))
        
        reply_markup = None
        if inventario:
            # Check if there's at least one usable item
            has_usable_items = any(o.oggetto in ['Nitro', 'Cassa', 'TNT'] for o in inventario)
            if has_usable_items:
                reply_markup = types.InlineKeyboardMarkup()
                reply_markup.add(types.InlineKeyboardButton("🎁 Usa Oggetto", callback_data="use_item_list"))
        
        self.bot.reply_to(self.message, msg, reply_markup=reply_markup if reply_markup else keyboard)
        # If we sent inline keyboard, we still need to make sure the user has the reply keyboard
        if reply_markup:
            self.bot.send_message(self.chatid, "Scegli cosa fare dal menu sopra.", reply_markup=keyboard)
        
        # Display Dragon Ball Stickers
        if inventario:
            try:
                for oggetto in inventario:
                    if 'La Sfera del Drago' in oggetto.oggetto:
                        # Extract info
                        # Format example: "La Sfera del Drago Shenron 4 stelle"
                        match = re.search(r'La Sfera del Drago (\w+) (\d+)', oggetto.oggetto)
                        if match:
                            drago_type = match.group(1) # Shenron or Porunga
                            star_num = match.group(2)
                            
                            # Handle filename mapping (Fixing typo "Shernon" in files)
                            file_prefix = "Shernon" if drago_type == "Shenron" else drago_type
                            filename = f"Stickers/{file_prefix}_{star_num}.webp"
                            
                            try:
                                with open(filename, 'rb') as sticker:
                                    self.bot.send_sticker(self.chatid, sticker)
                            except Exception as e:
                                print(f"Sticker not found: {filename} - {e}")
            except Exception as e:
                print(f"Error displaying stickers: {e}")
        
        # Check for Dragon Balls
        can_summon_shenron = Collezionabili().checkShenron(self.chatid)
        can_summon_porunga = Collezionabili().checkPorunga(self.chatid)
        
        if can_summon_shenron or can_summon_porunga:
            markup = types.InlineKeyboardMarkup()
            if can_summon_shenron:
                markup.add(types.InlineKeyboardButton("🐉 Evoca Shenron 🐉", callback_data="evoca_shenron"))
            if can_summon_porunga:
                markup.add(types.InlineKeyboardButton("🐲 Evoca Porunga 🐲", callback_data="evoca_porunga"))
            
            self.bot.send_message(self.chatid, "✨ Hai riunito le Sfere del Drago! ✨", reply_markup=markup)
    def handle_broadcast(self):
        message = self.message
        # Ottieni il messaggio da inviare
        messaggio = message.text.split('/broadcast')[1]

        # Invia il messaggio a tutti gli utenti del bot
        for utente in Utente().getUsers():
            try:
                msg = messaggio.replace('{nome_utente}',utente.nome)
                self.bot.send_message(utente.id_telegram, msg,parse_mode='markdown')
            except Exception as e:
                print("ERRORE",str(e))
        # Invia un messaggio di conferma all'utente che ha inviato il comando
        self.bot.reply_to(message, 'Messaggio inviato a tutti gli utenti')

    def handle_me(self):
        message = self.message
        chat_id = message.chat.id
        utente = Utente().getUtente(self.chatid)
        if not utente:
            self.bot.reply_to(message, "Utente non trovato.")
            return

        selectedLevel = Livello().infoLivelloByID(utente.livello_selezionato)
        info_text = Utente().infoUser(utente)
        
        if selectedLevel and selectedLevel.link_img:
            try:
                # Use message.chat.id instead of self.chatid to support groups
                self.bot.send_photo(chat_id, selectedLevel.link_img, caption=info_text, parse_mode='markdown', reply_to_message_id=message.message_id)
            except Exception as e:
                print(f"Errore nell'invio della foto: {e}")
                self.bot.reply_to(message, info_text, parse_mode='markdown')
        else:
            self.bot.reply_to(message, info_text, parse_mode='markdown')

    def handle_status(self):
        message = self.message
        try:
            target = message.text.split()[1]
            utente = Utente().getUtente(target)
            if utente:
                self.bot.reply_to(self.message, Utente().infoUser(utente),parse_mode='markdown')
            else:
                self.bot.reply_to(self.message, "Utente non trovato.")
        except IndexError:
            self.bot.reply_to(self.message, "Usa: !status @username")

    def handle_classifica(self):
        Points.Points().writeClassifica(self.message)

    def handle_stats(self):
        message = self.message
        self.bot.reply_to(self.message, Points.Points().wumpaStats(),parse_mode='markdown')

    def handle_premium(self):
        message = self.message
        self.bot.send_message(self.chatid, Points.Points().inviaUtentiPremium(message),parse_mode='markdown')

    def handle_livell(self,limite=40):
        message = self.message
        livelli_normali = Livello().getLevels(premium=0)
        livelli_premium = Livello().getLevels(premium=1)

        messaggi = [
            "Livelli disponibili",
            "Livelli disponibili solo per gli Utenti Premium",
        ]

        for livelli, messaggio in zip([livelli_normali, livelli_premium], messaggi):
            messaggio_completa = ""
            for lv in livelli[:limite]:
                messaggio_completa += f"*[{lv.livello}]* {lv.nome}({lv.link_img})\t [{lv.saga}]💪 {lv.exp_to_lv} exp.\n"

            self.bot.reply_to(message, messaggio_completa, parse_mode="markdown")
            
    def handle_album(self):
        message = self.message
        self.bot.reply_to(message, Points.Points().album(),parse_mode='markdown')
        
    def handle_dona(self):
        #!dona 10 @user
        #/dona 5 @utente
        message = self.message
        comando = message.text.replace('/','').replace('!','')
        punti = Points.Points()
        utenteSorgente = Utente().getUtente(self.chatid)
        tokenize = comando.split()
        points = int(tokenize[1])
        utenteTarget = Utente().getUtente(tokenize[2])
       
        messaggio = punti.donaPoints(utenteSorgente,utenteTarget,points)
        self.bot.reply_to(message,messaggio+'\n\n'+Utente().infoUser(utenteTarget),parse_mode='markdown')
        

    
    def handle_checkScadenzaPremiumToAll(self):
        Points.Points().checkScadenzaPremiumToAll()

    def handle_compatta(self):
        try:
            count = Database().compact_user_ids()
            self.bot.reply_to(self.message, f"✅ Database compattato! {count} utenti ri-indicizzati con ID consecutivi.")
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore durante la compattazione: {str(e)}")

    def handle_restore(self):
        msg = self.bot.reply_to(self.message,'Inviami il db')
        self.bot.register_next_step_handler(msg,Points.Points().restore)
        

    def handle_backup(self):
        Points.Points().backup()

    def handle_add_livello(self):
        message = self.message
        comandi = message.text
        comandi = comandi.split('/addLivello')[1:]
        for comando in comandi:
            parametri = comando.split(";")
            livello = int(parametri[1])
            nome = parametri[2]
            exp_to_lvl = int(parametri[3])
            link_img = parametri[4]
            saga = parametri[5]
            lv_premium = parametri[6]
            Livello().addLivello(livello,nome,exp_to_lvl,link_img,saga,lv_premium)

    def handle_plus_minus(self):
        message = self.message
        utente = Utente().getUtente(self.chatid) 
        self.bot.reply_to(message,Points.Points().addPointsToUsers(utente,message))

    def handle_buy_another_month(self):
        utenteSorgente = Utente().getUtente(self.chatid)
        Abbonamento().buyPremiumExtra(utenteSorgente)



    def handle_attiva_abbonamento_premium(self):
        message = self.message
        abbonamento = Abbonamento()
        utenteSorgente = Utente().getUtente(self.chatid)
        abbonamento.attiva_abbonamento(utenteSorgente)
        utenteSorgente = Utente().getUtente(utenteSorgente.id_telegram)
        self.bot.reply_to(message, 'Abbonamento attivato, il giorno '+str(utenteSorgente.scadenza_premium)[:10]+' si rinnoverà al costo di '+str(abbonamento.COSTO_MANTENIMENTO)+' '+PointsName,reply_markup=Database().startMarkup(utenteSorgente))
        
    def handle_disattiva_abbonamento_premium(self):
        message = self.message
        abbonamento = Abbonamento()
        utenteSorgente = Utente().getUtente(self.chatid)
        abbonamento.stop_abbonamento(utenteSorgente)
        utenteSorgente = Utente().getUtente(utenteSorgente.id_telegram)
        self.bot.reply_to(message, 'Abbonamento annullato, sarà comunque valido fino al '+str(utenteSorgente.scadenza_premium)[:10],reply_markup=Database().startMarkup(utenteSorgente))
    
    def handle_nome_in_game(self):
        message = self.message
        utente = Utente().getUtente(self.chatid)
        giochiutente = GiocoUtente().getGiochiUtente(utente.id_telegram)
        keyboard = types.InlineKeyboardMarkup()

        for giocoutente in giochiutente:
            remove_button = types.InlineKeyboardButton(f"❌ {giocoutente.piattaforma} {giocoutente.nome}", callback_data=f"remove_namegame_{giocoutente.id_telegram}_{giocoutente.piattaforma}_{giocoutente.nome}")
            keyboard.add(remove_button)

        add_button = types.InlineKeyboardButton("➕ Aggiungi Nome in Game", callback_data="add_namegame")
        keyboard.add(add_button)
        self.bot.reply_to(message, "Cosa vuoi fare?", reply_markup=keyboard)
    
    def handle_backup_all(self):
        message = self.message
        def backup_all(from_chat, to_chat,until_message=9999):
            messageid = 1
            condition = True
            while (condition and messageid<until_message):
                try:
                    condition = bot.copy_message(to_chat,from_chat, messageid)
                except Exception as e:
                    errore = str(e)
                    if "Too Many Requests" in errore:
                        seconds = int(errore.split()[17])
                        time.sleep(seconds)
                        messageid-=1
                messageid+=1

        #backup_all(PREMIUM_CHANNELS['ps1'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['psp'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['horror'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['hot'],PREMIUM_CHANNELS['tutto'],352)
        #backup_all(PREMIUM_CHANNELS['big_games'],PREMIUM_CHANNELS['tutto'],622)
        #backup_album(PREMIUM_CHANNELS['ps1'],CANALE_LOG)
        bot.reply_to(message, "Ho finito i backup")


    def handle_classifica(self):
        Points.Points().writeClassifica(self.message)

    def handle_buy_premium(self):
        abbonamento = Abbonamento()
        utente = Utente().getUtente(self.chatid)
        abbonamento.buyPremium(utente)

    def handle_choose_character_v2(self):
        # Handle character selection (v2 fixed)
        message = self.message
        utente = Utente().getUtente(self.chatid)
        punti = Points.Points()
        is_premium = '🎖' in message.text
        livelli_disponibili = Livello().listaLivelliPremium() if is_premium else Livello().listaLivelliNormali()
        markup = types.ReplyKeyboardMarkup()
        for livello in livelli_disponibili:
            markup.add(f"{livello.nome}{'🔓' if utente.livello < livello.livello else ''}")
        msg = bot.reply_to(message, "Seleziona il tuo personaggio", reply_markup=markup)
        self.bot.register_next_step_handler(msg, punti.setCharacter)

    def handle_all_commands(self):
        message = self.message
        utente = Utente().getUtente(self.chatid)
        if message.chat.type == "private":
            self.handle_private_command()
        if utente and Utente().isAdmin(utente):
            self.handle_admin_command()
        
        self.handle_generic_command()
    

@bot.message_handler(content_types=['audio', 'photo', 'voice', 'video', 'document', 'text', 'location', 'contact', 'sticker'])
def handle_all_messages(message):
    punti_check = Points.Points().checkBeforeAll(message)
    if punti_check[0] is None:
        return
    
    bothandler = BotCommands(message,bot)
    bothandler.handle_all_commands()

# Gestione delle query inline
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    user_id = call.from_user.id
    utente = Utente().getUtente(user_id)
    
    #remove_namegame_{giocoutente.id_telegram}_{giocoutente.piattaforma}_{giocoutente.nome}
    #add_namegame

    action = call.data

    if action == "stat_menu":
        # Calculate Points
        total_points = utente.livello * 2
        used_points = (utente.stat_vita + utente.stat_aura + utente.stat_danno + 
                       utente.stat_velocita + utente.stat_resistenza + utente.stat_crit_rate)
        available_points = total_points - used_points

        msg = "📊 ALLOCAZIONE STATISTICHE\n\n"
        msg += f"🎯 Punti Totali: {total_points} (Livello {utente.livello})\n"
        msg += f"✅ Punti Usati: {used_points}\n"
        msg += f"🆓 Punti Disponibili: {available_points}\n\n"
        msg += "Allocati:\n"
        msg += f"❤️ Vita: {utente.stat_vita} (+{utente.stat_vita * 10} HP)\n"
        msg += f"💙 Aura: {utente.stat_aura} (+{utente.stat_aura * 5} MP)\n"
        msg += f"⚔️ Danno: {utente.stat_danno} (+{utente.stat_danno * 2} DMG)\n"
        msg += f"⚡️ Velocità: {utente.stat_velocita} (+{utente.stat_velocita})\n"
        msg += f"🛡️ Resistenza: {utente.stat_resistenza} (+{utente.stat_resistenza}%)\n"
        msg += f"🎯 Crit Rate: {utente.stat_crit_rate} (+{utente.stat_crit_rate}% / Max 75%)\n\n"
        
        if available_points > 0:
            msg += f"💡 Hai {available_points} punto/i da allocare"
        else:
            msg += "✨ Tutti i punti sono stati allocati!"

        # Inline Keyboard
        markup = types.InlineKeyboardMarkup()
        if available_points > 0:
            markup.row(
                types.InlineKeyboardButton("❤️ +1", callback_data="stat_add_vita"),
                types.InlineKeyboardButton("💙 +1", callback_data="stat_add_aura")
            )
            markup.row(
                types.InlineKeyboardButton("⚔️ +1", callback_data="stat_add_danno"),
                types.InlineKeyboardButton("⚡️ +1", callback_data="stat_add_velocita")
            )
            markup.row(
                types.InlineKeyboardButton("🛡️ +1", callback_data="stat_add_resistenza"),
                types.InlineKeyboardButton("🎯 +1", callback_data="stat_add_crit_rate")
            )
        
        markup.add(types.InlineKeyboardButton("🔄 Reset Statistiche (500 Fagioli)", callback_data="stat_reset"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("stat_add_"):
        stat_name = action.replace("stat_add_", "")
        
        # Calculate Points
        total_points = utente.livello * 2
        used_points = (utente.stat_vita + utente.stat_aura + utente.stat_danno + 
                       utente.stat_velocita + utente.stat_resistenza + utente.stat_crit_rate)
        available_points = total_points - used_points
        
        if available_points > 0:
            # Check Crit Rate Cap
            if stat_name == "crit_rate" and getattr(utente, f"stat_{stat_name}") >= 75:
                bot.answer_callback_query(call.id, "Hai raggiunto il limite massimo per Crit Rate (75%)!")
                return
                
            # Update DB
            new_val = getattr(utente, f"stat_{stat_name}") + 1
            updates = {f"stat_{stat_name}": new_val}
            
            Database().update_user(user_id, updates)
            
            # Refresh User Data
            utente = Utente().getUtente(user_id)
            used_points += 1
            available_points -= 1
            
            # Reconstruct Message
            msg = "📊 ALLOCAZIONE STATISTICHE\n\n"
            msg += f"🎯 Punti Totali: {total_points} (Livello {utente.livello})\n"
            msg += f"✅ Punti Usati: {used_points}\n"
            msg += f"🆓 Punti Disponibili: {available_points}\n\n"
            msg += "Allocati:\n"
            msg += f"❤️ Vita: {utente.stat_vita} (+{utente.stat_vita * 10} HP)\n"
            msg += f"💙 Aura: {utente.stat_aura} (+{utente.stat_aura * 5} MP)\n"
            msg += f"⚔️ Danno: {utente.stat_danno} (+{utente.stat_danno * 2} DMG)\n"
            msg += f"⚡️ Velocità: {utente.stat_velocita} (+{utente.stat_velocita})\n"
            msg += f"🛡️ Resistenza: {utente.stat_resistenza} (+{utente.stat_resistenza}%)\n"
            msg += f"🎯 Crit Rate: {utente.stat_crit_rate} (+{utente.stat_crit_rate}% / Max 75%)\n\n"
            
            if available_points > 0:
                msg += f"💡 Hai {available_points} punto/i da allocare"
            else:
                msg += "✨ Tutti i punti sono stati allocati!"

            # Inline Keyboard
            markup = types.InlineKeyboardMarkup()
            if available_points > 0:
                markup.row(
                    types.InlineKeyboardButton("❤️ +1", callback_data="stat_add_vita"),
                    types.InlineKeyboardButton("💙 +1", callback_data="stat_add_aura")
                )
                markup.row(
                    types.InlineKeyboardButton("⚔️ +1", callback_data="stat_add_danno"),
                    types.InlineKeyboardButton("⚡️ +1", callback_data="stat_add_velocita")
                )
                markup.row(
                    types.InlineKeyboardButton("🛡️ +1", callback_data="stat_add_resistenza"),
                    types.InlineKeyboardButton("🎯 +1", callback_data="stat_add_crit_rate")
                )
            markup.add(types.InlineKeyboardButton("🔄 Reset Statistiche (500 Fagioli)", callback_data="stat_reset"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "Non hai punti disponibili!")

    elif action == "stat_reset":
        costo_reset = 500
        if utente.points >= costo_reset:
            # Reset Stats
            Database().update_user(user_id, {
                'points': utente.points - costo_reset,
                'stat_vita': 0, 'stat_aura': 0, 'stat_danno': 0,
                'stat_velocita': 0, 'stat_resistenza': 0, 'stat_crit_rate': 0
            })
            
            # Refresh User Data
            utente = Utente().getUtente(user_id)
            bot.answer_callback_query(call.id, "Statistiche resettate!")
            
            # Reconstruct Message (Fresh Reset)
            total_points = utente.livello * 2
            used_points = 0
            available_points = total_points

            msg = "📊 ALLOCAZIONE STATISTICHE\n\n"
            msg += f"🎯 Punti Totali: {total_points} (Livello {utente.livello})\n"
            msg += f"✅ Punti Usati: {used_points}\n"
            msg += f"🆓 Punti Disponibili: {available_points}\n\n"
            msg += "Allocati:\n"
            msg += f"❤️ Vita: {utente.stat_vita} (+0 HP)\n"
            msg += f"💙 Aura: {utente.stat_aura} (+0 MP)\n"
            msg += f"⚔️ Danno: {utente.stat_danno} (+0 DMG)\n"
            msg += f"⚡️ Velocità: {utente.stat_velocita} (+0)\n"
            msg += f"🛡️ Resistenza: {utente.stat_resistenza} (+0%)\n"
            msg += f"🎯 Crit Rate: {utente.stat_crit_rate} (+0%)\n\n"
            msg += f"💡 Hai {available_points} punto/i da allocare"

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("❤️ +1", callback_data="stat_add_vita"),
                types.InlineKeyboardButton("💙 +1", callback_data="stat_add_aura")
            )
            markup.row(
                types.InlineKeyboardButton("⚔️ +1", callback_data="stat_add_danno"),
                types.InlineKeyboardButton("⚡️ +1", callback_data="stat_add_velocita")
            )
            markup.row(
                types.InlineKeyboardButton("🛡️ +1", callback_data="stat_add_resistenza"),
                types.InlineKeyboardButton("🎯 +1", callback_data="stat_add_crit_rate")
            )
            markup.add(types.InlineKeyboardButton("🔄 Reset Statistiche (500 Fagioli)", callback_data="stat_reset"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
             bot.answer_callback_query(call.id, f"Non hai abbastanza Fagioli! Te ne servono {costo_reset}.")

    elif action == "evoca_shenron":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 10000 Fagioli Zen", callback_data="shenron_fagioli"))
        markup.add(types.InlineKeyboardButton("💪 5000 XP", callback_data="shenron_xp"))
        bot.edit_message_text("🐉 Ciedimi un desiderio, e io te lo esaudirò! Scegline UNO:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "shenron_fagioli":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            Database().update_user(user_id, {'points': utente.points + 10000})
            bot.edit_message_text("🐉 Il tuo desiderio è stato esaudito! Hai ricevuto 10000 Fagioli Zen. Addio!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Error in shenron_fagioli: {e}")
            bot.send_message(call.message.chat.id, f"Errore: {e}")

    elif action == "shenron_xp":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            Database().update_user(user_id, {'exp': utente.exp + 5000})
            bot.edit_message_text("🐉 Il tuo desiderio è stato esaudito! Hai ricevuto 5000 XP. Addio!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Error in shenron_xp: {e}")
            bot.send_message(call.message.chat.id, f"Errore: {e}")

    elif action == "evoca_porunga":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("💰 5000 Fagioli Zen", callback_data="porunga_step1_fagioli"))
        markup.row(types.InlineKeyboardButton("💪 2500 XP", callback_data="porunga_step1_xp"))
        bot.edit_message_text("🐲 IO SONO PORUNGA! POSSO ESAUDIRE 3 DESIDERI!\n\n1° Desiderio: Scegli tra Fagioli o XP.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("porunga_step1_"):
        scelta = action.split("_")[2]
        if scelta == "fagioli":
            Database().update_user(user_id, {'points': utente.points + 5000})
            msg_conf = "Hai scelto i Fagioli!"
        else:
            Database().update_user(user_id, {'exp': utente.exp + 2500})
            msg_conf = "Hai scelto l'XP!"
        
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🧨 Piazza Cassa TNT", callback_data="porunga_step2_tnt"))
        markup.row(types.InlineKeyboardButton("💥 Piazza Nitro (x2)", callback_data="porunga_step2_nitro"))
        
        bot.edit_message_text(f"🐲 {msg_conf} TI RIMANGONO 2 DESIDERI!\n\n2° Desiderio: Scegli cosa piazzare.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("porunga_step2_"):
        scelta = action.split("_")[2]
        if scelta == "tnt":
            # Piazza TNT nel gruppo - invia lo sticker e avvia il timer
            try:
                sti = open('Stickers/TNT.webp', 'rb')
                bot.send_sticker(Tecnologia_GRUPPO, sti)
                sti.close()
                bot.send_message(Tecnologia_GRUPPO, f"💣 Qualcuno ha piazzato una Cassa TNT tramite Porunga! Il prossimo che scrive la calpesterà!")
                Collezionabili().armaTrappola(Tecnologia_GRUPPO, 'TNT', user_id)
                msg_conf = "Hai piazzato una Cassa TNT nel gruppo!"
            except Exception as e:
                print(f"Errore piazzamento TNT: {e}")
                msg_conf = "Errore nel piazzare la TNT!"
        else:
            # Piazza 2 Nitro nel gruppo
            try:
                for i in range(2):
                    sti = open('Stickers/Nitro.webp', 'rb')
                    bot.send_sticker(Tecnologia_GRUPPO, sti)
                    sti.close()
                bot.send_message(Tecnologia_GRUPPO, f"💥 Qualcuno ha piazzato 2 Casse Nitro tramite Porunga! I prossimi 2 che scrivono le calpesteranno!")
                Collezionabili().armaTrappola(Tecnologia_GRUPPO, 'Nitro', user_id)
                Collezionabili().armaTrappola(Tecnologia_GRUPPO, 'Nitro', user_id)
                msg_conf = "Hai piazzato 2 Nitro nel gruppo!"
            except Exception as e:
                print(f"Errore piazzamento Nitro: {e}")
                msg_conf = "Errore nel piazzare le Nitro!"

        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🎁 Cassa Wumpa (1-1000 Fagioli)", callback_data="porunga_step3_wumpa"))
        markup.row(types.InlineKeyboardButton("💥 3 Casse Nitro (Inventario)", callback_data="porunga_step3_nitro"))
        
        bot.edit_message_text(f"🐲 {msg_conf} TI RIMANE 1 DESIDERIO!\n\n3° Desiderio: Scegli la tua ricompensa finale.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("porunga_step3_"):
        scelta = action.split("_")[2]
        try:
            if scelta == "wumpa":
                regalo = random.randint(1, 1000)
                Database().update_user(user_id, {'points': utente.points + regalo})
                msg_final = f"🐲 Hai scelto la Cassa Wumpa e hai trovato {regalo} {PointsName}! I TUOI DESIDERI SONO STATI ESAUDITI! ADDIO!"
            else:
                Collezionabili().CreateCollezionabile(user_id, 'Nitro', 3)
                msg_final = "🐲 Hai scelto 3 Nitro! Sono state aggiunte al tuo inventario. I TUOI DESIDERI SONO STATI ESAUDITI! ADDIO!"
            
            use_dragon_balls_logic(user_id, 'Porunga')
            bot.edit_message_text(msg_final, call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Errore nel 3° desiderio: {e}")
            bot.edit_message_text(f"🐲 Errore nell'esaudire il desiderio: {e}", call.message.chat.id, call.message.message_id)

    elif action == "use_item_list":
        inventario = Collezionabili().getInventarioUtente(user_id)
        if not inventario:
            bot.answer_callback_query(call.id, "Il tuo inventario è vuoto.")
            return
            
        markup = types.InlineKeyboardMarkup()
        for oggetto in inventario:
            # Only allow using certain items for now
            if oggetto.oggetto in ['Nitro', 'Cassa', 'TNT'] or 'Pozione' in oggetto.oggetto:
                markup.add(types.InlineKeyboardButton(f"🎁 Usa {oggetto.oggetto} ({int(oggetto.quantita)})", callback_data=f"use_item_{oggetto.oggetto}"))
        
        if len(markup.keyboard) == 0:
            bot.answer_callback_query(call.id, "Non hai oggetti utilizzabili al momento.")
            return

        bot.edit_message_text("Seleziona l'oggetto da usare:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action.startswith("use_item_"):
        item_name = action.replace("use_item_", "")
        try:
            # Verifica se l'utente ha ancora l'oggetto
            item = Collezionabili().getItemByUser(user_id, item_name)
            if not item or item.quantita <= 0:
                bot.answer_callback_query(call.id, "Non hai più questo oggetto.")
                return

            # Effetto dell'oggetto nel gruppo principale
            chat_to_send = Tecnologia_GRUPPO
            
            if item_name == 'Nitro':
                sti = open('Stickers/Nitro.webp', 'rb')
                bot.send_sticker(chat_to_send, sti)
                sti.close()
                bot.send_message(chat_to_send, f"💥 Qualcuno ha piazzato una Cassa Nitro dall'inventario! Attenti!")
                Collezionabili().armaTrappola(chat_to_send, 'Nitro', user_id)
            elif item_name == 'Cassa':
                sti = open('Stickers/Wumpa_create.webp', 'rb')
                bot.send_sticker(chat_to_send, sti)
                sti.close()
                bot.send_message(chat_to_send, f"📦 {utente.nome} ha piazzato una Cassa Wumpa dall'inventario! Chi la prenderà?")
                Collezionabili().armaTrappola(chat_to_send, 'Cassa', user_id)
            elif item_name == 'TNT':
                sti = open('Stickers/TNT.webp', 'rb')
                bot.send_sticker(chat_to_send, sti)
                sti.close()
                bot.send_message(chat_to_send, f"💣 Qualcuno ha piazzato una Cassa TNT dall'inventario! Scappate!")
                Collezionabili().armaTrappola(chat_to_send, 'TNT', user_id)
            elif 'La Sfera del Drago' in item_name:
                bot.answer_callback_query(call.id, "Usa il comando 'Sfera' o evoca il Drago dall'inventario se le hai tutte!")
                return
            elif 'Pozione' in item_name:
                # Calculate Heal Amount
                heal_amount = 0
                if 'Piccola' in item_name: heal_amount = 100
                elif 'Media' in item_name: heal_amount = 200
                elif 'Grande' in item_name: heal_amount = 500
                elif 'Enorme' in item_name: heal_amount = 1000
                
                if 'Aura' in item_name:
                    # Logic for Aura
                    MAX_AURA = 60 + (utente.stat_aura * 5)
                    # Use persisted aura value or default to MAX if not set (though migration set it to 60)
                    current_aura = utente.aura if utente.aura is not None else MAX_AURA 
                    
                    if current_aura >= MAX_AURA:
                        bot.answer_callback_query(call.id, "Hai già l'aura al massimo!")
                        return

                    new_aura = min(MAX_AURA, current_aura + heal_amount)
                    Database().update_user(user_id, {'aura': new_aura})
                    
                    msg_text = f"🧪 Hai bevuto {item_name}!\n💙 Aura ripristinata: {new_aura}/{MAX_AURA}"

                else:
                    # Logic for Health (Default/Rigenerante)
                    MAX_VITA = 50 + (utente.stat_vita * 10)
                    current_vita = utente.vita if utente.vita is not None else MAX_VITA
                    
                    if current_vita >= MAX_VITA:
                        bot.answer_callback_query(call.id, "Hai già la vita al massimo!")
                        return

                    new_vita = min(MAX_VITA, current_vita + heal_amount)
                    Database().update_user(user_id, {'vita': new_vita})
                    msg_text = f"🧪 Hai bevuto {item_name}!\n❤️ Vita ripristinata: {new_vita}/{MAX_VITA}"
                
                Collezionabili().usaOggetto(user_id, item_name)
                bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id)
                bot.answer_callback_query(call.id, "Slurp!")
                return
            
            # Consuma l'oggetto
            Collezionabili().usaOggetto(user_id, item_name)
            
            bot.edit_message_text(f"Hai usato {item_name}! L'effetto è stato attivato nel gruppo.", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, f"{item_name} usato!")
            
        except Exception as e:
            print(f"Errore nell'uso dell'oggetto: {e}")
            bot.answer_callback_query(call.id, "Errore durante l'uso dell'oggetto.")

    elif action.startswith("remove_namegame_"):
        parametri = action.replace('remove_namegame_','').split('_')
        id_telegram = parametri[0]
        piattaforma = parametri[1]
        nome = parametri[2]
        GiocoUtente().delPiattaformaUtente(id_telegram,piattaforma,nome)
        bot.send_message(user_id,'Piattaforma eliminata',reply_markup=Database().startMarkup(utente))

    elif action.startswith("add_namegame"):
        msg = bot.send_message(user_id,'Scrivimi la piattaforma (spazio) nome utente, esempio "Steam alan.bimbati"')
        bot.register_next_step_handler(msg, addnamegame)
    

def addnamegame(message):
    chatid = message.chat.id
    utente = Utente().getUtente(chatid)
    piattaforma,nomegioco = message.text.split()
    GiocoUtente().CreateGiocoUtente(chatid,piattaforma,nomegioco) 
    bot.reply_to(message,'Piattaforma e gioco aggiunti',reply_markup=Database().startMarkup(utente))

def extract_link_data(message):
    if not message:
        return None, None
    
    text = message.caption if message.caption else ""
    pattern = r't\.me/(?:c/|)([\w\d_]+)/(\d+)'
    
    # 1. Check Entities (Hyperlinks)
    if message.caption_entities:
        for entity in message.caption_entities:
            if entity.type == 'text_link':
                match = re.search(pattern, entity.url)
                if match: 
                    chat_id_str, msg_id = match.group(1), int(match.group(2))
                    return (int("-100" + chat_id_str) if chat_id_str.isdigit() else "@" + chat_id_str), msg_id
            elif entity.type == 'url':
                offset = entity.offset
                length = entity.length
                url_text = text[offset:offset+length]
                match = re.search(pattern, url_text)
                if match:
                    chat_id_str, msg_id = match.group(1), int(match.group(2))
                    return (int("-100" + chat_id_str) if chat_id_str.isdigit() else "@" + chat_id_str), msg_id

    # 2. Check Raw Text
    match = re.search(pattern, text)
    if match:
        chat_id_str, msg_id = match.group(1), int(match.group(2))
        return (int("-100" + chat_id_str) if chat_id_str.isdigit() else "@" + chat_id_str), msg_id
    
    return None, None

def sendFileGame(chatid, from_chat, messageid):
    max_deep = 300
    tmp = 0
    # First message target for type check
    first_msg = None
    try:
        # We MUST forward at least once to see what it is
        first_msg = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
        if first_msg.content_type == 'sticker': return 1
    except:
        return -1

    current_type = first_msg.content_type
    messageid += 1
    tmp += 1

    # Keep forwarding while it's the SAME type or compatible
    while tmp <= max_deep:
        try:
            msg = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
            if msg.content_type == 'sticker':
                break
            if current_type != 'photo' and msg.content_type == 'photo':
                break
        except:
            break
        messageid += 1
        tmp += 1
    return 1

def isPremiumChannel(from_chat):
    premium = False
    for i in PREMIUM_CHANNELS:
        if from_chat == int(PREMIUM_CHANNELS[i]):
            premium = True
            break
    return premium

def isMiscellaniaChannel(from_chat):
    premium = False
    for i in MISCELLANIA:
        if from_chat==int(MISCELLANIA[i]): premium = True
    return premium

def buy1game(message):

    punti = Points.Points()
    chatid = message.chat.id
    utenteSorgente  = Utente().getUtente(chatid)
    from_chat =  message.forward_from_chat.id

    if from_chat is not None:
        if isPremiumChannel(from_chat):
            costo = 0 if utenteSorgente.premium == 1 else 50
        elif isMiscellaniaChannel(from_chat):
            costo = 5
        else:
            costo = 15

        messageid = message.forward_from_message_id
        
        if message.content_type=='photo':
            if costo == 0:
                # OPTION B: Link Trick
                link_chat, link_msg = extract_link_data(message)
                if link_chat:
                    status = sendFileGame(chatid, link_chat, link_msg)
                else:
                    status = sendFileGame(chatid,from_chat,messageid)
                
                if status == -1:
                    bot.reply_to(message,"C'è un problema con questo gioco, contatta un admin")
            elif utenteSorgente.points>=costo:
                status = sendFileGame(chatid,from_chat,messageid)
                if status == -1:
                    bot.reply_to(message,"C'è un problema con questo gioco, contatta un admin")
                Database().update_user(chatid, {'points':utenteSorgente.points-costo})
                bot.reply_to(message, "Hai mangiato "+str(costo)+" "+PointsName+"\n\n"+Utente().infoUser(utenteSorgente),parse_mode='markdown')
            else:
                bot.reply_to(message, "Mi dispiace, ti servono "+str(costo)+" "+PointsName+" per comprare questo gioco"+"\n\n"+Utente().infoUser(utenteSorgente),parse_mode='markdown')
        
        #bot.send_message(CANALE_LOG,"L'utente "+utenteSorgente.username+" ha acquistato da "+message.forward_from_chat.title+" https://t.me/c/"+str(from_chat)[4:]+"/"+str(messageid))

#bot.infinity_polling()

def inviaLivelli(limite):
    livelli_normali = Livello().getLevels(premium=0)
    livelli_premium = Livello().getLevels(premium=1)

    messaggio_normali = 'Livelli disponibili\n\n'
    for lv in livelli_normali[:limite]:
        messaggio_normali += '*[' + str(lv.livello) + ']* [' + lv.nome + '](' + lv.link_img + ')\t [' + lv.saga + ']💪 ' + str(lv.exp_to_lv) + ' exp.\n'

    messaggio_premium = 'Livelli disponibili solo per gli Utenti Premium\n\n'
    for lv in livelli_premium[:limite]:
        messaggio_premium += '*[' + str(lv.livello) + ']* [' + lv.nome + '](' + lv.link_img + ')\t [' + lv.saga + ']💪 ' + str(lv.exp_to_lv) + ' exp.\n'

    bot.send_message(Tecnologia_GRUPPO, messaggio_normali, parse_mode='markdown')
    bot.send_message(Tecnologia_GRUPPO, messaggio_premium, parse_mode='markdown')


def backup():
    doc = open('dbz.db', 'rb')
    bot.send_document(CANALE_LOG, doc, caption="Arseniolupin #database #backup")
    doc.close()

def send_album():
    punti = Points.Points()
    msg = punti.album()
    bot.send_message(Tecnologia_GRUPPO, msg,parse_mode='markdown' )

# Funzione per avviare il programma di promemoria
def start_reminder_program():
    # Imposta l'orario di esecuzione del promemoria
    schedule.every().day.at("09:00").do(backup)
    schedule.every().day.at("15:00").do(send_album)
    # Compattazione mensile degli ID (check interno per il primo del mese)
    schedule.every().day.at("00:00").do(compact_db_job)
    
    #schedule.every().day.at("20:00").do(inviaLivelli, 40)
    #schedule.every().monday.at("12:00").do(inviaUtentiPremium)

    # Avvia il loop per eseguire il programma di promemoria
    while True:
        schedule.run_pending()
        time.sleep(1)

# Thread per il polling del bot
def bot_polling_thread():
    bot.infinity_polling()

# Avvio del programma
if __name__ == "__main__":
    # Creazione e avvio del thread per il polling del bot
    polling_thread = threading.Thread(target=bot_polling_thread)
    polling_thread.start()

    # Avvio del programma di promemoria nel thread principale
    start_reminder_program()
