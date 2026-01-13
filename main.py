from telebot import types
from settings import *
from sqlalchemy         import create_engine
from model import Livello, Steam,Utente, Abbonamento, Database, GiocoUtente,Collezionabili, use_dragon_balls_logic
import Points
from telebot import util
import schedule,time,threading
import datetime

@bot.message_handler(content_types=['left_chat_member'])
def esciDalGruppo(message):
    chatid = message.left_chat_member.id
    try:
        Database().update_user(chatid,{'points':0})
        bot.send_message(CANALE_LOG, f"I punti dell'utente {Utente().getUsernameAtLeastName()} sono stati azzerati perchè è uscito dal gruppo.")
    except Exception as e:
        print('Errore ',str(e))

@bot.message_handler(content_types=['new_chat_members'])
def newmember(message):
    punti = Points.Points()
    punti.welcome(message)

@bot.message_handler(commands=['start'])
def start(message):
    punti = Points.Points()
    punti.welcome(message)
    bot.reply_to(message, "Cosa vuoi fare?", reply_markup=Database().startMarkup(Utente().getUtente(message.chat.id)))
    any(message)

class BotCommands:
    def __init__(self, message, bot):
        self.bot = bot
        self.message = message
        self.comandi_privati = {
            "🎫 Compra un gioco steam": self.handle_buy_steam_game,
            "👤 Scegli il personaggio": self.handle_choose_character,
            
            "Compra abbonamento Premium (1 mese)": self.handle_buy_premium,
            "✖️ Disattiva rinnovo automatico": self.handle_disattiva_abbonamento_premium,
            "✅ Attiva rinnovo automatico": self.handle_attiva_abbonamento_premium,
            "classifica": self.handle_classifica,
            "nome in game": self.handle_nome_in_game,
            "compro un altro mese": self.handle_buy_another_month,
            "info": self.handle_info,
            "📦 Inventario": self.handle_inventario,
            
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

    def handle_inventario(self):
        inventario = Collezionabili().getInventarioUtente(self.chatid)
        msg = "📦 Inventario 📦\n\n"
        if inventario:
            for oggetto in inventario:
                msg += f"🧷 {oggetto.oggetto}"
                if oggetto.quantita > 1:
                    msg += f" ({oggetto.quantita})"
                msg += "\n"
        else:
            msg = "Il tuo inventario è vuoto, partecipa attivamente nel gruppo per trovare oggetti preziosi"
        

        self.bot.reply_to(self.message,msg,reply_markup=Database().startMarkup(Utente().getUtente(self.chatid)))
        
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
        utente = Utente().getUtente(self.chatid)
        self.bot.reply_to(message, Utente().infoUser(utente),parse_mode='markdown')

    def handle_status(self):
        message = self.message
        utente = Utente().getUtente(message.text.split()[1])
        self.bot.reply_to(self.message, Utente().infoUser(utente),parse_mode='markdown')

    def handle_classifica(self):
        message = self.message
        self.bot.send_message(self.chatid, Points.Points().writeClassifica(message),parse_mode='markdown')

    def handle_stats(self):
        message = self.message
        self.bot.send_message(self.chatid, Points.Points().wumpaStats(message),parse_mode='markdown')

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

    def handle_buy_steam_game(self):
        message = self.message
        risposta = ''
        risposta += '50 🍑 = 🥉 Bronze Coin: 10% probabilità TITOLONE casuale\n'
        risposta += '100 🍑 = 🥈 Silver Coin: 50% TITOLONE casuale\n'
        risposta += '150 🍑 = 🥇 Gold Coin: 100% TITOLONE casuale\n'
        risposta += '200 🍑 = 🎖 Platinum Coin: TITOLONE a scelta della lista, visibile solo con l\'acquisto del suddetto Coin\n' 
        msg = bot.reply_to(message,risposta,reply_markup=Steam().steamMarkup())
        self.bot.register_next_step_handler(msg, Steam().steamCtutoin)

    def handle_info(self):
        message = self.message
        utenteSorgente = Utente().getUtente(self.chatid)
        abbonamento = Abbonamento()
        punti = Points.Points()
        messaggio = f"\n\n*Gestione Abbonamento Premium*\nCosto di attivazione (primo mese): {abbonamento.COSTO_PREMIUM} {PointsName}"
        messaggio += f"\nRinnovo Abbonamento (+1 mese): {abbonamento.COSTO_MANTENIMENTO} {PointsName}\n👥[Link al gruppo](https://t.me/+VtiCEsByTGqN94pv)\n@aROMadivideogiochi\n\n"
        self.bot.reply_to(message,punti.album(),reply_markup=Database().startMarkup(utenteSorgente),parse_mode='markdown')
        self.bot.reply_to(message,messaggio,reply_markup=Database().startMarkup(utenteSorgente),parse_mode='markdown')
        self.bot.reply_to(message,Utente().infoUser(utenteSorgente),reply_markup=Database().startMarkup(utenteSorgente),parse_mode='markdown')

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

        #backup_all(PREMIUM_CHANNELS['pc'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['nintendo'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['ps4'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['ps3'],PREMIUM_CHANNELS['tutto'])
        #backup_all(PREMIUM_CHANNELS['ps2'],PREMIUM_CHANNELS['tutto'])
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

    def handle_choose_character(self):
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
    

@bot.message_handler(content_types=util.content_type_media)
def any(message):
    Points.Points().checkBeforeAll(message)
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

    if action == "evoca_shenron":
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
                bot.send_message(Tecnologia_GRUPPO, f"💣 {utente.username if utente.username else utente.nome} ha piazzato una Cassa TNT tramite Porunga! Il prossimo che scrive la calpesterà!")
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
                bot.send_message(Tecnologia_GRUPPO, f"💥 {utente.username if utente.username else utente.nome} ha piazzato 2 Casse Nitro tramite Porunga! I prossimi 2 che scrivono le calpesteranno!")
                msg_conf = "Hai piazzato 2 Nitro nel gruppo!"
            except Exception as e:
                print(f"Errore piazzamento Nitro: {e}")
                msg_conf = "Errore nel piazzare le Nitro!"

        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🎁 Accetta 3° Desiderio", callback_data="porunga_step3"))
        
        bot.edit_message_text(f"🐲 {msg_conf} TI RIMANE 1 DESIDERIO!\n\n3° Desiderio: Piazza Nitro x3 e Wumpa.", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "porunga_step3":
        # 3rd Wish: Nitro x3 and Wumpa (Cassa?)
        try:
            # Piazza 3 Nitro nel gruppo
            for i in range(3):
                sti = open('Stickers/Nitro.webp', 'rb')
                bot.send_sticker(Tecnologia_GRUPPO, sti)
                sti.close()
            
            # Piazza 1 Cassa Wumpa nel gruppo
            sti = open('Stickers/Wumpa_create.webp', 'rb')
            bot.send_sticker(Tecnologia_GRUPPO, sti)
            sti.close()
            
            bot.send_message(Tecnologia_GRUPPO, f"🐲 {utente.username if utente.username else utente.nome} ha piazzato 3 Casse Nitro e 1 Cassa Wumpa tramite Porunga! I prossimi che scrivono le calpesteranno!")
            
            use_dragon_balls_logic(user_id, 'Porunga')
            bot.edit_message_text("🐲 I TUOI DESIDERI SONO STATI ESAUDITI! ADDIO!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Errore nel 3° desiderio: {e}")
            bot.edit_message_text(f"🐲 Errore nell'esaudire il desiderio: {e}", call.message.chat.id, call.message.message_id)

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

def sendFileGame(chatid,from_chat,messageid):
    content_type = 'photo'
    max_deep = 300
    tmp = 0
    while content_type != 'sticker' and content_type=='photo' and tmp<=max_deep:
        try:
            message = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
            content_type = message.content_type
        except:
            pass
        messageid += 1
        tmp +=1
    tmp = 0
    while content_type != 'sticker' and content_type!='photo' and tmp<=max_deep:
        try:
            message = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
            content_type = message.content_type
        except:
            pass
        messageid += 1
        tmp +=1

def isPremiumChannel(from_chat):
    premium = False
    if from_chat==int(PREMIUM_CHANNELS['tutto']): premium= True
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
        costo = 5 if isMiscellaniaChannel(from_chat) else 15
        messageid = message.forward_from_message_id
        
        if message.content_type=='photo':
            if  utenteSorgente.premium==1 and (isPremiumChannel(from_chat) or isMiscellaniaChannel(from_chat)):
                status = sendFileGame(chatid,from_chat,messageid)
                if status == -1:
                    bot.reply_to(message,"C'è un problema con questo gioco, contatta un admin")
            #elif utenteSorgente.premium==0 and (isPremiumChannel(from_chat)):
                #bot.reply_to(message, "Mi dispiace, solo gli Utenti Premium possono acquistare questo gioco"+'\n\n'+Utente().infoUser(utenteSorgente),parse_mode='markdown')
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
