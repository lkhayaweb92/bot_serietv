from sqlalchemy.sql import functions
from sqlalchemy         import create_engine, false, null, true
from sqlalchemy         import update
from sqlalchemy         import desc,asc
from sqlalchemy.orm     import sessionmaker
from model import Utente,Domenica,Admin,Livello,Database,Collezionabili, create_table, spawn_random_seasonal_boss
import datetime
from settings import *
import datetime
from dateutil.relativedelta import relativedelta
import random

class Points:    
    def __init__(self):
        engine = create_engine('sqlite:///dbz.db', connect_args={'timeout': 30})
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def deleteAccount(self,chatid):
        session = self.Session()
        utente = session.query(Utente).filter_by(id_telegram = chatid).first()  
        session.delete(utente)
        session.commit()

    def wumpaStats(self):
        session = self.Session()
        wumpaSupply = session.query(functions.sum(Utente.points)).scalar() or 0
        wumpaMax = session.query(functions.max(Utente.points)).scalar() or 0
        wumpaMin = session.query(functions.min(Utente.points)).scalar() or 0
        numUsers = session.query(functions.count(Utente.id)).scalar() or 0
        session.close()
        
        msg = "📊 *Statistiche Globali*\n\n"
        msg += f"🍏 Totale {PointsName}: {wumpaSupply}\n"
        msg += f"📈 Max {PointsName}: {wumpaMax}\n"
        msg += f"📉 Min {PointsName}: {wumpaMin}\n"
        msg += f"👥 Utenti Totali: {numUsers}\n"
        msg += f"👥 Utenti Totali: {numUsers}\n"
        return msg

    def getRank(self, utente):
        session = self.Session()
        # Calcolo posizione in classifica
        rank = session.query(Utente).filter(
            (Utente.livello > utente.livello) |
            ((Utente.livello == utente.livello) & (Utente.points > utente.points)) |
            ((Utente.livello == utente.livello) & (Utente.points == utente.points) & (Utente.premium > utente.premium))
        ).count() + 1
        session.close()
        return rank


    def addAdmin(self,utente):
        session = self.Session()
        chatid = utente.id_telegram
        
        exist = session.query(Admin).filter_by(id_telegram = utente.id_telegram).first()
        if exist is None:
            try:
                admin = Admin()
                admin.id_telegram     = chatid
                session.add(admin)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return True
        else:
            return False

    def backup(self):
        doc = open('dbz.db', 'rb')
        bot.send_document(CANALE_LOG, doc, caption="ArsenioLupin #database #backup")
        doc.close()
    
    def restore(self,message):
        try:
            if message.document.file_name=='dbz.db':
                f = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(f.file_path)
                with open('dbz.db', 'wb') as new_file:
                    new_file.write(downloaded_file)
                bot.reply_to(message, "Database ripristinato")
        except:
            bot.reply_to(message, "Il db non è corretto")

    def setCharacter(self,message):
        utente = Utente().getUtente(message.chat.id)  
        # Pulisci il nome del personaggio da emoji come 🔓 e spazi extra
        char_name = message.text.replace('🔓', '').strip()
        # Find highest level achieved for THIS character name
        selectedLevel = Livello().GetLevelByNameLevel(char_name)
        if selectedLevel:
            Livello().setSelectedLevel(utente,selectedLevel.livello,selectedLevel.lv_premium, char_name=char_name)
            bot.reply_to(message, f"Guerriero {char_name} selezionato!\n\n{Utente().infoUser(utente)}",parse_mode='markdown',reply_markup=Database.startMarkup(Database,utente))
        else:
            bot.reply_to(message, "Personaggio non trovato.")
        #bot.send_message(CANALE_LOG, "L' utente "+Utente().getUsernameAtLeastName(utente)+" ha selezionato il personaggio "+ message.text +"\n\n"+Utente().infoUser(utente),parse_mode='markdown',reply_markup=Database.startMarkup(Database,utente))

    
    def purgeSymbols(self,message):
        if message.text is not None:
            if message.text[0] == '!' or message.text[0] == '/':
                return message.text[1:]
            else:
                return message.text
        else:
            return ""

    # donaPoints is now handled in Utente class in model.py

    def isMember(self, chatid):
        try:
            member = bot.get_chat_member(REQUIRED_CHANNEL_ID, chatid)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except Exception as e:
            print(f"Errore isMember: {e}")
        return False

    def checkBeforeAll(self,message):
        utente = Utente()
        # utente.checkUtente(message) <- MOVED DOWN

        if message.chat.type == "group" or message.chat.type == "supergroup":
            utente.checkUtente(message) # Create user if interacting in group
            chatid = message.from_user.id
            utenteSorgente = Utente().getUtente(chatid)

            Database().checkIsSunday(utenteSorgente,message)
            utente.checkTNT(message,utenteSorgente)

            ############## GRUPPO ###################
            if message.chat.id == Tecnologia_GRUPPO:
                trap_triggered = Collezionabili().checkTrappole(message)
                if not trap_triggered:
                    utente.addRandomExp(utenteSorgente,message)
                    #utente.checkCasse(utenteSorgente,message)
                    Collezionabili().maybeDrop(message)
                    
                    # --- BOSS SPAWN CHANCE (15%) ---
                    if random.randint(1, 100) <= 15:
                        spawn_random_seasonal_boss(only_boss=False)
        elif message.chat.type == 'private':
            chatid = message.chat.id
            # Membership Check for Private Chat
            if not self.isMember(chatid):
                msg = f"⚠️ *Accesso Negato*\n\nPer usare il bot e scaricare le serie, devi prima unirti al nostro canale ufficiale!\n\n👉 [CLICCA QUI PER UNIRTI]({REQUIRED_CHANNEL_LINK})\n\nDopo esserti unito, scrivi /start per attivare il bot!"
                bot.send_message(chatid, msg, parse_mode='markdown', disable_web_page_preview=True)
                return None, None # Stop execution if not member
            
            # If member, NOW create/update user
            utente.checkUtente(message)

        utenteSorgente = utente.getUtente(chatid)
        if not utenteSorgente: return None, None # Safety check


        Livello().checkUpdateLevel(utenteSorgente,message)
        utenteSorgente = Utente().getUtente(chatid)

        return utenteSorgente,chatid


    def welcome(self,message):
        chatid = message.chat.id if message.chat.type == 'private' else message.from_user.id
        
        # In private chat, only welcome if member
        if message.chat.type == 'private' and not self.isMember(chatid):
            return # checkBeforeAll handles the message

        Utente.checkUtente(Utente,message)
        
        # Check if user is "new" (Stats at default values)
        utente = Utente().getUtente(chatid)
        if utente:
            if utente.points == 0 and utente.exp == 0 and utente.livello == 1:
                Utente().addPoints(utente, 50)
                bot.reply_to(message, f'🌟 Benvenuto ufficiale! Per te **50 {PointsName}** come bonus di benvenuto nel canale!', parse_mode='markdown', reply_markup=hideBoard)
    
    def isValidUsername(self,username):
        if username[0]=='@':
            return true
        else:
            return false

    def addPointsToUsers(self,utente, message):
        # Verifica che l'utente che richiede l'operazione sia un amministratore
        if not Utente().isAdmin(utente):
            return "Solo gli amministratori possono aggiungere o rimuovere punti"

        # Split del comando in parti, separando l'operazione (+ o -) dai nomi degli utenti
        parts = message.text.split()
        if not parts: return "Comando vuoto"
        
        token = parts[0]
        op = token[0]
        points_str = token[1:]
        
        if op not in ['+', '-'] or not points_str.isdigit():
            return "⚠️ Formato errato. Usa: `+100 @utente` o `-50 @utente`"
            
        points = int(points_str) if op == '+' else -int(points_str)
        usernames = [username for username in parts[1:] if username.startswith('@')]
        # Verifica che il comando sia ben formato
        answer = ''
        if len(usernames) == 0:
            answer += "Comando non valido: specificare almeno un utente\n"
        else:
            # Aggiungi o rimuovi i punti per ogni utente
            for username in usernames:
                try:
                    utente = Utente().getUtente(username)
                    risposta = 'Complimenti! Hai ottenuto {} {}' if op == '+' else 'Hai mangiato {} deliziosi {}!'
                    Utente().addPoints(utente, points)
                    answer += username+': '+risposta.format(str(points), PointsName)+'\n'
                except Exception as e:
                    answer += f'Errore Telegram: {str(e)}\n'
                    answer +=  'Comando non valido: username ({}) non trovato\n'.format(username)
                try:
                    bot.send_message(utente.id_telegram, risposta.format(str(points), PointsName)+Utente().infoUser(utente),parse_mode='markdown')
                except Exception as e:
                    bot.reply_to(message, risposta.format(str(points), PointsName)+Utente().infoUser(utente),parse_mode='markdown')

        if answer == '': answer='nulla da fare'
        return answer
