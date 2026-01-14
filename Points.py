from sqlalchemy.sql import functions
from sqlalchemy         import create_engine, false, null, true
from sqlalchemy         import update
from sqlalchemy         import desc,asc
from sqlalchemy.orm     import sessionmaker
from model import Utente,Domenica,Steam,Admin,Livello,Database,Abbonamento,Collezionabili, create_table
import datetime
from settings import *
import datetime
from dateutil.relativedelta import relativedelta
import random

class Points:    
    def __init__(self):
        engine = create_engine('sqlite:///dbz.db')
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def classifica(self):   
        session = self.Session()
        utenti = session.query(Utente).order_by(desc(Utente.livello),desc(Utente.points),desc(Utente.premium)).all()
        session.close()
        return utenti
        
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
        numPremium = session.query(functions.sum(Utente.premium)).scalar() or 0
        abbonamentiAttivi = session.query(functions.sum(Utente.abbonamento_attivo)).scalar() or 0
        numUsers = session.query(functions.count(Utente.id)).scalar() or 0
        session.close()
        
        msg = "📊 *Statistiche Globali*\n\n"
        msg += f"🍏 Totale {PointsName}: {wumpaSupply}\n"
        msg += f"📈 Max {PointsName}: {wumpaMax}\n"
        msg += f"📉 Min {PointsName}: {wumpaMin}\n"
        msg += f"👥 Utenti Totali: {numUsers}\n"
        msg += f"🎖 Utenti Premium: {numPremium}\n"
        msg += f"✅ Abbonamenti Attivi: {abbonamentiAttivi}\n"
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

    def writeClassifica(self,message):
        utenti = self.classifica()
        messaggio = ''
        for i in range(20):
            if len(utenti)>i:
                messaggio += f'\n*[{str(i+1)}]* {Utente().infoUser(utenti[i])} \n'
        bot.reply_to(message, messaggio, parse_mode='markdown')

    def setCharacter(self,message):
        utente = Utente().getUtente(message.chat.id)  
        # Pulisci il nome del personaggio da emoji come 🔓 e spazi extra
        char_name = message.text.replace('🔓', '').strip()
        selectedLevel = Livello().GetLevelByNameLevel(char_name)
        if selectedLevel:
            Livello().setSelectedLevel(utente,selectedLevel.livello,selectedLevel.lv_premium)
            bot.reply_to(message, f"Personaggio {char_name} selezionato!\n\n{Utente().infoUser(utente)}",parse_mode='markdown',reply_markup=Database.startMarkup(Database,utente))
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

    def donaPoints(self,utenteSorgente,utenteTarget,points):
        points = int(points)
        if points>0:
            if int(utenteSorgente.points)>=points:
                Utente().addPoints(utenteTarget,points)
                Utente().addPoints(utenteSorgente,points*-1)
                return utenteSorgente.username+" ha donato "+str(points)+ " "+PointsName+ " a "+utenteTarget.username+ "! ❤️"
            else:
                return PointsName+" non sufficienti"
        else:
            return "Non posso donare "+PointsName+" negativi"

    def checkBeforeAll(self,message):
        utente = Utente()
        utente.checkUtente(message)

        if message.chat.type == "group" or message.chat.type == "supergroup":
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
        elif message.chat.type == 'private':
            chatid = message.chat.id
        utenteSorgente = utente.getUtente(chatid)
        Abbonamento().checkScadenzaPremium(utenteSorgente)
        Livello().checkUpdateLevel(utenteSorgente,message)
        utenteSorgente = Utente().getUtente(chatid)

        return utenteSorgente,chatid

    def album(self):
        answer = ''
        answer += 'Inoltrami un gioco dagli album per acquistarlo.'+'\n\n'
        answer += '1️⃣ [PS1](t.me/): Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '2️⃣ [PS2](t.me/): Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '3️⃣ [PS3](t.me/) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '4️⃣ [PS4](t.me/) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '📲 [PSP](t.me/) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '💻 [PC](https://t.me/) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '🐶 [Nintendo](t.me/) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '📽 [Cinema](t.me/) Costa 5 '+PointsName+' per film'+'\n'
        answer += '🎖 [Premium](t.me/) Costa 0 '+PointsName+', canale esclusivo agli utenti Premium.'+'\n\n'
        answer += '[Come guadagnare Frutti Wumpa?](https://t.me/)'+'\n'
        answer += '[Cosa puoi fare con i Frutti Wumpa?](https://t.me/)'
        return answer

    def welcome(self,message):
        bot.reply_to(message,self.album(),parse_mode='markdown')
        alreadyExist = Utente.checkUtente(Utente,message)
        if alreadyExist == False:
            bot.reply_to(message, 'Benvenuto su aRsenioLupin! Per te 50 '+PointsName+'!', reply_markup=hideBoard)
    
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
        parts       = message.text.split()
        op          = parts[0][0]
        points      = parts[0][1:]
        points = int(points) if op == '+' else -int(points)
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
