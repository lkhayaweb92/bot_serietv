from ast import Str
from datetime import date
from sqlite3 import Timestamp
from sqlalchemy                 import create_engine, Column, Table, ForeignKey, MetaData
from sqlalchemy.orm             import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy                 import (Integer, String, Date, DateTime, Float, Boolean, Text, text)
from sqlalchemy.orm     import sessionmaker
from sqlalchemy         import desc,asc
from settings           import *
from telebot            import types
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
#import pandas as pd

Base = declarative_base()

tento_oggetto={}

livelli = [0, 300, 800, 1500, 1725, 2335, 2500, 2980, 3760, 4300, 4575, 5525, 6510, 7630, 8785, 10075, 11400, 12860, 14355, 15985, 17650, 19450, 21285, 23255, 25260, 27400, 29575,
31885, 34230, 36710, 39225, 41875, 44560, 47380, 50235, 53225, 56250, 59410, 62605, 65935,70000,75000,80000,85000,90000,95000,100000,105000]


class DailyShop(Base):
    __tablename__ = "dailyshop"
    id = Column(Integer, primary_key=True)
    id_utente = Column('id_utente', Integer)
    data = Column('data', Date)
    tipo_pozione = Column('tipo_pozione', String) # New column
    pozioni_rimanenti = Column('pozioni_rimanenti', Integer, default=10)

class Database:
    def __init__(self):
        engine = create_engine('sqlite:///dbz.db')
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def startMarkup(self,utente=None):
        markup = types.ReplyKeyboardMarkup()

        #markup.add('Compra 1 gioco')
        #markup.add('Cosa puoi fare con i Frutti Wumpa?')
        #markup.add('Come guadagno Frutti Wumpa?')
        markup.add('ℹ️ info','🎮 Nome in Game','📦 Inventario','🧪 Negozio Pozioni')
        if utente is not None:
            if utente.premium==1:
                markup.add('👤 Scegli il personaggio','👤 Scegli il personaggio 🎖')
                markup.add('🎖 Compro un altro mese')
                if utente.abbonamento_attivo==1:
                    markup.add('✖️ Disattiva rinnovo automatico')
                else:
                    
                    markup.add('✅ Attiva rinnovo automatico')
            else:
                markup.add('👤 Scegli il personaggio')
                markup.add('🎖 Compra abbonamento Premium (1 mese)')
        markup.add('📄 Classifica')

        return markup

    def negozioPozioniMarkup(self, user_id=None):
        markup = types.ReplyKeyboardMarkup()
        
        all_potions = [
            '🧪 Pozione Rigenerante Piccola', '🧪 Pozione Rigenerante Media',
            '🧪 Pozione Rigenerante Grande', '🧪 Pozione Rigenerante Enorme',
            '🧪 Pozione Aura Piccola', '🧪 Pozione Aura Media',
            '🧪 Pozione Aura Grande', '🧪 Pozione Aura Enorme'
        ]

        if user_id:
            import datetime
            session = self.Session()
            oggi = datetime.date.today()
            # Fetch all daily records for this user today
            shops = session.query(DailyShop).filter_by(id_utente=user_id, data=oggi).all()
            session.close()

            # Create a set of exhausted "clean" potion names
            exhausted = {s.tipo_pozione for s in shops if s.pozioni_rimanenti <= 0}
            
            # Filter available potions (compare stripped name with DB name)
            available_potions = [p for p in all_potions if p.replace("🧪 ", "") not in exhausted]
        else:
            available_potions = all_potions

        # Add buttons in rows of 2
        for i in range(0, len(available_potions), 2):
            if i + 1 < len(available_potions):
                markup.add(available_potions[i], available_potions[i+1])
            else:
                markup.add(available_potions[i])

        markup.add('Indietro')
        return markup

    def isSunday(self,utente):
        session = self.Session()
        chatid = utente.id_telegram
        oggi = datetime.datetime.today().date()
        if oggi.strftime('%A')=='Sunday':
            exist = session.query(Domenica).filter_by(utente = chatid).first()
            if exist is None:
                try:
                    domenica = Domenica()
                    domenica.last_day   = oggi
                    domenica.utente     = chatid
                    session.add(domenica)
                    session.commit()
                    Database().update_user(chatid,{'points':utente.points+1})
                except:
                    session.rollback()
                    raise
                finally:
                    session.close()
                return True
            elif exist.last_day!=oggi:
                Database().update_domenica(chatid,{'last_day':oggi})
                Database().update_user(chatid,{'points':utente.points+1})
                return True
            else:
                return False
    
    def checkIsSunday(self,utenteSorgente,message):
        nome = Utente().getUsernameAtLeastName(utenteSorgente)
        if (self.isSunday(utenteSorgente)):
            bot.reply_to(message, 'Buona domenica '+nome+'! Per te 1 '+PointsName+'!\n\n'+Utente().infoUser(utenteSorgente), parse_mode='markdown',reply_markup=hideBoard)


    def update_table_entry(self, table_class, filter_column, filter_value, update_dict):
        session = self.Session()
        table_entry = session.query(table_class).filter_by(**{filter_column: filter_value}).first()
        for key, value in update_dict.items():
            setattr(table_entry, key, value)
        session.commit()
        session.close()

    def update_user(self, chatid, kwargs):
        self.update_table_entry(Utente, "id_telegram", chatid, kwargs)

    def update_domenica(self, chatid, kwargs):
        self.update_table_entry(Domenica, "utente", chatid, kwargs)
    


    def update_livello(self, id, kwargs):
        self.update_table_entry(Livello, "id", id, kwargs) 
    
    def update_gameuser(self, chatid, kwargs):
        self.update_table_entry(GiocoUtente, "id_telegram", chatid, kwargs) 

    def delete_user_complete(self, chatid):
        session = self.Session()
        try:
            # Delete from Utente
            session.query(Utente).filter_by(id_telegram=chatid).delete()
            # Delete from Collezionabili (inventory)
            session.query(Collezionabili).filter_by(id_telegram=str(chatid)).delete()
            # Delete from GiocoUtente (games)
            session.query(GiocoUtente).filter_by(id_telegram=chatid).delete()
            # Delete from Domenica (bonus)
            session.query(Domenica).filter_by(utente=chatid).delete()
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def compact_user_ids(self):
        session = self.Session()
        try:
            # 1. Backup all users
            users = session.query(Utente).order_by(Utente.id).all()
            user_data = []
            for u in users:
                user_data.append({
                    'id_telegram': u.id_telegram,
                    'nome': u.nome,
                    'cognome': u.cognome,
                    'username': u.username,
                    'exp': u.exp,
                    'points': u.points,
                    'livello': u.livello,
                    'vita': u.vita,
                    'premium': u.premium,
                    'livello_selezionato': u.livello_selezionato,
                    'start_tnt': u.start_tnt,
                    'end_tnt': u.end_tnt,
                    'scadenza_premium': u.scadenza_premium,
                    'abbonamento_attivo': u.abbonamento_attivo
                })

            # 2. Clear table
            session.query(Utente).delete()
            
            # 3. Re-insert
            for data in user_data:
                new_u = Utente()
                for key, value in data.items():
                    setattr(new_u, key, value)
                session.add(new_u)
            
            session.commit()
            return len(user_data)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

def create_table(engine):
    Base.metadata.create_all(engine)

class GiocoUtente(Base):
    __tablename__ = "giocoutente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer)
    piattaforma = Column('piattaforma', String)
    nome        = Column('nome', String)

    def CreateGiocoUtente(self,id_telegram,piattaforma,nomegioco):
        session = Database().Session()
        exist = session.query(GiocoUtente).filter_by(id_telegram = id_telegram,piattaforma=piattaforma).first()
        if exist is None:
            try:
                giocoutente = GiocoUtente()
                giocoutente.id_telegram     = id_telegram
                giocoutente.piattaforma     = piattaforma
                giocoutente.nome            = nomegioco
                session.add(giocoutente)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return False
        else:
            Database().update_gameuser(id_telegram,{'piattaforma':piattaforma,'gioco':nomegioco})
        return True

    def getGiochiUtente(self, id_telegram):
        session = Database().Session()
        giochiutente = session.query(GiocoUtente).filter_by(id_telegram=id_telegram).all()
        session.close()
        return giochiutente

    def delPiattaformaUtente(self,id_telegram,piattaforma,nome):
        session = Database().Session()
        giocoutente = session.query(GiocoUtente).filter_by(id_telegram=id_telegram,piattaforma=piattaforma,nome=nome).first()
        print(giocoutente.id_telegram,giocoutente.piattaforma,giocoutente.nome)
        session.delete(giocoutente)
        session.commit()
        session.close()      

class Utente(Base):
    __tablename__ = "utente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer, unique=True)
    nome  = Column('nome', String(32))
    cognome = Column('cognome', String(32))
    username = Column('username', String(32), unique=True)
    exp = Column('exp', Integer)
    points = Column('money', Integer)
    livello = Column('livello', Integer)
    vita = Column('vita', Integer)
    premium = Column('premium', Integer)
    livello_selezionato = Column('livello_selezionato',Integer)
    start_tnt = Column('start_tnt',DateTime)
    end_tnt = Column('end_tnt',DateTime)
    scadenza_premium = Column('scadenza_premium',DateTime)
    abbonamento_attivo =  Column('abbonamento_attivo',Integer)
    
    # New Stats
    stat_vita = Column('stat_vita', Integer, default=0)
    stat_aura = Column('stat_aura', Integer, default=0)
    stat_danno = Column('stat_danno', Integer, default=0)
    stat_velocita = Column('stat_velocita', Integer, default=0)
    stat_resistenza = Column('stat_resistenza', Integer, default=0)
    stat_crit_rate = Column('stat_crit_rate', Integer, default=0)
    
    # New Current Aura
    aura = Column('aura', Integer, default=60)

    def CreateUser(self,id_telegram,username,name,last_name):

        session = Database().Session()
        exist = session.query(Utente).filter_by(id_telegram = id_telegram).first()
        if exist is None:
            try:
                utente = Utente()
                utente.username     = username
                utente.nome         = name
                utente.id_telegram  = id_telegram
                utente.cognome      = last_name
                utente.vita         = 50
                utente.aura         = 60
                utente.exp          = 0
                utente.livello      = 1
                utente.points       = 0
                utente.premium      = 0
                utente.livello_selezionato = 1
                utente.start_tnt = datetime.datetime.now()+relativedelta(month=1)
                utente.end_tnt = datetime.datetime.now()
                utente.scadenza_premium = datetime.datetime.now()
                utente.abbonamento_attivo = 0
                session.add(utente)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return False
        elif exist.username!=username:
            Database().update_user(id_telegram,{'username':username,'nome':name,'cognome':last_name})
        return True

    def getUtente(self, target):
        session = Database().Session()
        utente = None
        target = str(target)

        if target.startswith('@'):
            utente = session.query(Utente).filter_by(username=target).first()
        else:
            chatid = int(target) if target.isdigit() else None
            if chatid is not None:
                utente = session.query(Utente).filter_by(id_telegram=chatid).first()

        session.close()
        return utente
    
    def checkUtente(self, message):
        if message.chat.type == "group" or message.chat.type == "supergroup":
            chatid =        message.from_user.id
            username =      '@'+message.from_user.username
            name =          message.from_user.first_name
            last_name =     message.from_user.last_name
        elif message.chat.type == 'private':
            chatid = message.chat.id
            username = '@'+str(message.chat.username)
            name = message.chat.first_name
            last_name = message.chat.last_name
        Utente.CreateUser(Utente,id_telegram=chatid,username=username,name=name,last_name=last_name)
    
    def isAdmin(self,utente):
        session = Database().Session()
        if utente:
            exist = session.query(Admin).filter_by(id_telegram = utente.id_telegram).first()
            return False if exist is None else True
        else:
            return False
    
    def getUsers(self):
        session = Database().Session()
        users = session.query(Utente).all()
        print('N. utenti: ',len(users))
        return users

    def getUsernameAtLeastName(self,utente):
        if utente is not None:
            if utente.username is None:
                nome = utente.nome
            else: 
                nome = utente.username
            return nome
        else:
            return "Nessun nome"

    def infoUser(self, utenteSorgente):
        if not utenteSorgente:
            return "L'utente non esiste"

        utente = Utente().getUtente(utenteSorgente.id_telegram)
        if not utente:
            return "L'utente non è registrato"
            
        infoLv = Livello().infoLivello(utente.livello)
        selectedLevel = Livello().infoLivelloByID(utente.livello_selezionato)
        giochiutente = GiocoUtente().getGiochiUtente(utente.id_telegram)
        
        # New: get Rank
        import Points
        rank = Points.Points().getRank(utente)

        nome_utente = utente.nome if utente.username is None else utente.username
        answer = f"🎖 Utente Premium\n" if utente.premium == 1 else ''
        answer += f"✅ Abbonamento attivo (fino al {str(utente.scadenza_premium)[:11]})\n" if utente.abbonamento_attivo == 1 else ''

        answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
        try:
            max_vita = 50 + ((utente.stat_vita or 0) * 10)
            max_aura = 60 + ((utente.stat_aura or 0) * 5)
            
            # Formatta la visualizzazione Vita (es. 50/50)
            current_vita = utente.vita if utente.vita is not None else 50
            answer += f"❤️ *Vita*: {current_vita}/{max_vita}\n"
            
            # Aura attualmente è sempre al massimo (non c'è consumo)
            current_aura = utente.aura if utente.aura is not None else 60
            answer += f"💙 *Aura*: {current_aura}/{max_aura}\n"
            answer += f"⚔️ *Danno*: {(utente.stat_danno or 0) * 2}\n"
            answer += f"⚡️ *Velocità*: {(utente.stat_velocita or 0)}\n"
            answer += f"🛡️ *Resistenza*: {(utente.stat_resistenza or 0)}% (MAX 75%)\n"
            answer += f"🎯 *Crit Rate*: {(utente.stat_crit_rate or 0)}%\n"
        except Exception as e:
            print(f"ERROR calculating stats in infoUser: {e}")
            answer += "\n(Errore visualizzazione statistiche)\n"
        
        answer += f"🏆 *Posizione*: {rank}°\n"
        
        # Exp display
        next_exp = 0
        infoNextLv = Livello().infoLivello(utente.livello + 1)
        if infoNextLv:
            next_exp = infoNextLv.exp_to_lv
        elif utente.livello < len(livelli):
            next_exp = livelli[utente.livello]
            
        if next_exp > 0:
            answer += f"*💪🏻 Exp*: {utente.exp}/{next_exp}\n"
        else:
            answer += f"*💪🏻 Exp*: {utente.exp}\n"
            
        # Character/Level display
        if selectedLevel:
            answer += f"*🎖 Lv. *{utente.livello} [{selectedLevel.nome}]({selectedLevel.link_img})\n"
            answer += f"*👥 Saga: *{selectedLevel.saga}\n"
        else:
            answer += f"*🎖 Lv. *{utente.livello}\n"

        if giochiutente:
            answer += '\n\n👾 Nome in Game 👾\n'
            answer += '\n'.join(f"*🎮 {giocoutente.piattaforma}:* `{giocoutente.nome}`" for giocoutente in giochiutente)

        return answer

    def addRandomExp(self,user,message):
        exp = random.randint(1,5)
        self.addExp(user,exp)
 
    def addExp(self,utente,exp):
        Database().update_user(utente.id_telegram,{'exp':utente.exp+exp})

    def addPoints(self, utente, points):  
        try: 
            Database().update_user(utente.id_telegram,{'points':int(utente.points) + int(points)})
        except Exception as e:
            print(e)
            Database().update_table_entry(Utente, "username", utente.username, {'points':int(utente.points) + int(points)})

    def donaPoints(self,utenteSorgente,utenteTarget,points):
        points = int(points)
        if points>0:
            if int(utenteSorgente.points)>=points:
                self.addPoints(utenteTarget,points)
                self.addPoints(utenteSorgente,points*-1)
                return utenteSorgente.username+" ha donato "+str(points)+ " "+PointsName+ " a "+utenteTarget.username+ "! ❤️"
            else:
                return PointsName+" non sufficienti"
        else:
            return "Non posso donare "+PointsName+" negativi"
    ########################### CASSE WUMPA
    def tnt_end(self,utente):
        timestamp = datetime.datetime.now() 
        Database().update_user(utente.id_telegram,{
            'end_tnt':timestamp,
            }
        )


    def isTntExploded(self,utente):
        session = Database().Session()
        self.tnt_end(utente)
        tnt =  session.query(Utente).filter_by(id_telegram=utente.id_telegram).first()
        if tnt.end_tnt is not None and tnt.start_tnt is not None:
            difftime = tnt.end_tnt-tnt.start_tnt
            res = False,difftime
            if difftime.seconds>3:
                res = True,difftime
            else:
                res = False,difftime

        else:
            res = False,None
        Database().update_user(utente.id_telegram,{
            'start_tnt':None,
            'end_tnt': None
            }
        )
        return res
    """
    def tnt_start(self,utente,message):
        sti = open('Stickers/TNT.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        bot.reply_to(message, "💣 Ops!... Hai calpestato una Cassa TNT! Scrivi entro 3 secondi per evitarla!")

        timestamp = datetime.datetime.now()
        Database().update_user(utente.id_telegram,{
            'start_tnt':timestamp,
            'end_tnt': None
            }
        )
    
    
        
    def nitroExploded(self,utente,message):
        sti = open('Stickers/Nitro.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        exp_persi = random.randint(1,50)*-1
        wumpa_persi = random.randint(1,5)*-1
        #punti.addExp(utenteSorgente,exp_persi)
        self.addPoints(utente,wumpa_persi)
        bot.reply_to(message, "💥 Ops!... Hai calpestato una Cassa Nitro! Hai perso "+str(wumpa_persi)+" "+PointsName+"! \n\n"+Utente().infoUser(utente),parse_mode='markdown')

    def cassaWumpa(self,utente,message):
        sti = open('Stickers/Wumpa_create.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        wumpa_extra = random.randint(1,5)
        #exp_extra = random.randint(1,50)
        #punti.addExp(utenteSorgente,exp_extra)
        self.addPoints(utente,wumpa_extra)
        bot.reply_to(message, "📦 Hai trovato una cassa con "+str(wumpa_extra)+" "+PointsName+"!\n\n"+Utente().infoUser(utente),parse_mode='markdown')
    """
    def checkTNT(self,message,utente):
        chatid = message.from_user.id
        utente = Utente().getUtente(chatid)
        exploded,intime=Utente().isTntExploded(utente)
        if exploded:
            utente  = Utente().getUtente(chatid)
            exp_persi = random.randint(1,25)*-1
            wumpa_persi = random.randint(1,5)*-1
            #self.addExp(utente,exp_persi) 
            self.addPoints(utente,wumpa_persi)
            bot.reply_to(message,'💥 TNT esplosa!!! (Ci hai messo '+str(intime.seconds)+') secondi per evitarla e hai perso '+str(wumpa_persi)+' '+PointsName+'!'+'\n\n'+Utente().infoUser(utente),parse_mode='markdown')
        elif exploded==False:
            if intime is not None:
                bot.reply_to(message,'🎉 TNT evitata!!!! (Ci hai messo '+str(intime.seconds)+') secondi'+'\n\n'+Utente().infoUser(utente),parse_mode='markdown')



    
class Domenica(Base):
    __tablename__ = "domenica"
    id = Column(Integer, primary_key=True)
    last_day = Column('last_day', Date)
    utente = Column('utente', Integer, unique=True)

class Trappola(Base):
    __tablename__ = "trappole"
    id = Column(Integer, primary_key=True)
    idgruppo = Column('id_gruppo', Integer)
    tipo = Column('tipo', String)
    data_piazzamento = Column('data_piazzamento', DateTime)
    id_utente = Column('id_utente', Integer)



class NomiGiochi(Base):
    __tablename__ = "nomigiochi"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)
    id_nintendo = Column('id_nintendo',String(256))
    id_ps = Column('id_ps',String(256))
    id_xbox = Column('id_xbox',String(256))
    id_steam = Column('id_steam',String(256))

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)

class Livello(Base):
    __tablename__ = "livello"
    id = Column('id',Integer, primary_key=True)
    livello = Column('livello',Integer)
    exp_to_lv = Column('exp_to_lv',Integer)
    nome  = Column('nome', String(32))
    link_img = Column('link_img',String(128))
    saga = Column('saga',String(128))
    lv_premium = Column('lv_premium',Integer)

    def getLvByExp(self, exp):
        lv = 0
        for exp_to_lvl in livelli:
            if exp >= exp_to_lvl:
                lv = lv + 1
        return lv
    
    def addLivello(self, lvl, nome, exp_to_lv, link_img, saga, lv_premium):
        session = Database().Session()
        exist = session.query(Livello).filter_by(livello=lvl, lv_premium=lv_premium).first()
        if exist is None:
            try:
                livello = Livello()
                livello.livello = lvl
                livello.nome = nome
                livello.exp_to_lv = exp_to_lv
                livello.link_img = link_img
                livello.saga = saga
                livello.lv_premium = lv_premium
                session.add(livello)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return True
        else:
            Database().update_livello(exist.id, {'nome': nome, 'exp_to_lv': exp_to_lv, 'link_img': link_img, 'saga': saga, 'lv_premium': lv_premium})
            return False

    def infoLivello(self, livello):
        session = Database().Session()
        livello = session.query(Livello).filter_by(livello=livello).first()
        return livello

    def infoLivelloByID(self, livelloid):
        session = Database().Session()
        livello = session.query(Livello).filter_by(id=livelloid).first()
        return livello

    def getLevels(self):
        session = Database().Session()
        lvs = session.query(Livello).order_by(asc(Livello.livello)).all()
        session.close()
        return lvs

    def getLevels(self, premium=None):
        session = Database().Session()
        if premium is None:
            lvs = session.query(Livello).order_by(asc(Livello.livello)).all()
        elif premium:
            lvs = session.query(Livello).filter_by(lv_premium=1).order_by(asc(Livello.livello)).all()
        else:
            lvs = session.query(Livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        session.close()
        return lvs

    def getLevelPremium(self, lv):
        session = Database().Session()
        lvs = session.query(Livello).filter_by(livello=lv, lv_premium=1).first()
        return lvs
    
    def getLevel(self, lv):
        session = Database().Session()
        lvs = session.query(Livello).filter_by(livello=lv, lv_premium=0).first()
        return lvs

    def GetLevelByNameLevel(self,nameLevel):
        session = Database().Session()
        livello = session.query(Livello).filter_by(nome = nameLevel).first()
        return livello 

    def setSelectedLevel(self,utente,level,lv_premium):
        session = Database().Session()
        livello = session.query(Livello).filter_by(livello = level,lv_premium=lv_premium).first()
        Database().update_user(utente.id_telegram,{'livello_selezionato':livello.id})

    def listaLivelliDisponibili(self,utente):
        livelloAttuale = utente.livello
        session = Database().Session()
        if utente.premium==1:
            livelli = session.query(Livello).filter(Livello.livello<utente.livello).order_by(asc(Livello.livello)).all()
        else:
            livelli = session.query(Livello).filter(Livello.livello<utente.livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        return livelli
    
    def listaLivelliNormali(self):
        session = Database().Session()
        livelli = session.query(Livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        return livelli

    def listaLivelliPremium(self):
        session = Database().Session()
        livelli = session.query(Livello).filter_by(lv_premium=1).order_by(asc(Livello.livello)).all()
        return livelli

    def checkUpdateLevel(self,utenteSorgente,message):
        lv = Livello().getLvByExp(utenteSorgente.exp)
        if lv>utenteSorgente.livello:
            Database().update_user(utenteSorgente.id_telegram,{'livello':lv})
            lvObj = Livello().getLevel(lv)
            lbPremiumObj = Livello().getLevelPremium(lv)
            
            if lvObj and lvObj.link_img:
                try:
                    # Invia la foto del personaggio sbloccato come complimento nel gruppo
                    msg_text = f"Complimenti! 🎉 Sei passato al livello {lv}! Hai sbloccato il personaggio [{lvObj.nome}]({lvObj.link_img}) 🎉\n\n{Utente().infoUser(utenteSorgente)}"
                    bot.send_photo(message.chat.id, lvObj.link_img, caption=msg_text, parse_mode='markdown', reply_to_message_id=message.message_id)
                except Exception as e:
                    print(f"Errore invio foto level up: {e}")
                    bot.reply_to(message, f"Complimenti! 🎉 Sei passato al livello {lv}! Hai sbloccato il personaggio [{lvObj.nome}]({lvObj.link_img}) 🎉\n\n{Utente().infoUser(utenteSorgente)}", parse_mode='markdown')
            else:
                bot.reply_to(message, f"Complimenti! 🎉 Sei passato al livello {lv}! 🎉\n\n{Utente().infoUser(utenteSorgente)}", parse_mode='markdown')

            if lbPremiumObj:
                if lbPremiumObj.link_img:
                    try:
                        bot.send_photo(message.chat.id, lbPremiumObj.link_img, caption=f"È anche disponibile il personaggio [{lbPremiumObj.nome}]({lbPremiumObj.link_img}) per gli utenti Premium!", parse_mode='markdown')
                    except:
                        bot.reply_to(message, f"È anche disponibile il personaggio [{lbPremiumObj.nome}]({lbPremiumObj.link_img}), puoi attivarlo scrivendo a @aROMaGameBot!", parse_mode='markdown')
                else:
                    bot.reply_to(message, f"È anche disponibile il personaggio {lbPremiumObj.nome}, puoi attivarlo scrivendo a @aROMaGameBot!", parse_mode='markdown')
            if lv % 5== 0:
                if lv==5:
                    add = 40
                elif lv==10:
                    add = 60
                elif lv==15:
                    add = 80
                elif lv==20:
                    add = 100
                elif lv==25:
                    add = 120
                elif lv==30:
                    add = 150
                elif lv==35:
                    add = 200
                elif lv==40:
                    add = 250
                else:
                    add = 250
                Utente().addPoints(utenteSorgente,add)
                bot.reply_to(message,f"Complimenti per questo traguardo! Per te {str(add)} {PointsName}! 🎉\n\n{Utente().infoUser(utenteSorgente)}",parse_mode='markdown')

class GiocoAroma(Base):
    __tablename__ = 'giocoaroma'
    id = Column('id',Integer, primary_key=True)
    titolo = Column('nome',String)
    descrizione = Column('descrizione',String)
    link = Column('link',String)
    from_chat = Column('from_chat',String)
    messageid = Column('messageid',Integer)

import datetime
from dateutil.relativedelta import relativedelta

class Abbonamento:

    def __init__(self):
        self.bot = bot
        self.CANALE_LOG = CANALE_LOG
        self.PointsName = PointsName
        self.COSTO_PREMIUM       =    250
        self.COSTO_MANTENIMENTO  =    50
        self.PROMO = ""

        # CHECK PROMO
        oggi = datetime.date.today()

        for promozione in PROMOZIONI:
            periodo_inizio = datetime.datetime.strptime(PROMOZIONI[promozione]["periodo_inizio"], "%Y%m%d").date()
            periodo_fine = datetime.datetime.strptime(PROMOZIONI[promozione]["periodo_fine"], "%Y%m%d").date()
            if oggi >= periodo_inizio and oggi <= periodo_fine:
                self.COSTO_PREMIUM       = PROMOZIONI[promozione]["COSTO_PREMIUM"]
                self.COSTO_MANTENIMENTO  = PROMOZIONI[promozione]["COSTO_MANTENIMENTO"]
                self.PROMO               = PROMOZIONI[promozione]["nome"]

    def stop_abbonamento(self, utente):
        Database().update_user(utente.id_telegram, {'abbonamento_attivo': 0})
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha interrotto l'abbonamento #Premium")

    def attiva_abbonamento(self, utente):
        Database().update_user(utente.id_telegram, {'abbonamento_attivo': 1})
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha attivato l'abbonamento #Premium")

    def stop_premium(self, utente):
        Database().update_user(utente.id_telegram, {'premium': 0})
        Livello().setSelectedLevel(utente, utente.livello, 0)
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} non è più #Premium")

    def rinnova_premium(self, utente):
        scadenza = datetime.datetime.now() + relativedelta(months=+1)
        Database().update_user(utente.id_telegram, {
            'points': utente.points - self.COSTO_MANTENIMENTO,
            'premium': 1,
            'abbonamento_attivo': 1,
            'scadenza_premium': scadenza
        })
        utente = Utente().getUtente(utente.id_telegram)
        self.bot.send_message(
            utente.id_telegram,
            f"Il tuo abbonamento è stato correttamente rinnovato mangiando {self.COSTO_MANTENIMENTO} {self.PointsName}\n\n{Utente().infoUser(utente)}",
            parse_mode='markdown'
            ,reply_markup=Database().startMarkup(utente)
        )
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha rinnovato l'abbonamento #Premium"+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')

    def buyPremium(self, utente):
        scadenza = datetime.datetime.now()+relativedelta(months=+1)
        rinnovo = "\n\nOgni prossimo mese costerà solo "+str(self.COSTO_MANTENIMENTO)+" "+self.PointsName
        if utente.premium==1:
            self.attiva_abbonamento(utente)
            self.bot.send_message(utente.id_telegram, "Sei già Utente Premium fino al "+str(utente.scadenza_premium)[:10]+rinnovo+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        elif utente.premium==0 and utente.points>=self.COSTO_PREMIUM:
            items = {
                'points': utente.points-self.COSTO_PREMIUM,
                'premium': 1,
                'abbonamento_attivo':1,
                'scadenza_premium':scadenza
            }
            Database().update_user(utente.id_telegram,items)
            self.bot.send_message(utente.id_telegram, "Complimenti! Sei ora un Utente Premium fino al "+str(utente.scadenza_premium)[:10]+rinnovo+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        else:
            messaggio =  f"Mi dispiace, ti servono {self.COSTO_PREMIUM} {self.PointsName} {Utente().infoUser(utente)}"
            self.bot.send_message(utente.id_telegram,messaggio,reply_markup=Database().startMarkup(utente),parse_mode='markdown')

    def buyPremiumExtra(self, utente):
        rinnovo = "\n\nOgni prossimo mese costerà solo " + str(self.COSTO_MANTENIMENTO) + " " + self.PointsName
        if utente.premium == 1 and utente.points>=self.COSTO_MANTENIMENTO:
            items = {
                'points': utente.points - self.COSTO_MANTENIMENTO,
                'premium': 1,
                'abbonamento_attivo': 1,
                'scadenza_premium': utente.scadenza_premium + relativedelta(months=+1)
            }
            Database().update_user(utente.id_telegram, items)       
            utente = Utente().getUtente(utente.id_telegram)     
            self.bot.send_message(utente.id_telegram, "Hai rinnovato anticipatamente il costo dell'abbonamento, è quindi valido fino al " + str(utente.scadenza_premium)[:10] + rinnovo+Utente().infoUser(utente), reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        else:
            self.bot.send_message(utente.id_telegram, f"Devi avere {str(self.COSTO_MANTENIMENTO)} {PointsName}", reply_markup=Database().startMarkup(utente))

    def checkScadenzaPremium(self,utente):
        oggi = datetime.datetime.now()
        try:
            if oggi>utente.scadenza_premium:
                if utente.abbonamento_attivo==0 and utente.premium==1:
                    self.stop_premium(utente)
                elif utente.abbonamento_attivo==1:
                    if utente.points>=self.COSTO_MANTENIMENTO:
                        self.rinnova_premium(utente)
                    else:
                        self.stop_premium(utente)
                        self.stop_abbonamentoPremium(utente)
        except Exception as e:
            print(str(e))
    
    def checkScadenzaPremiumToAll(self):
        listaUtenti = Utente().getUsers()
        for utente in listaUtenti:
            self.checkScadenzaPremium(utente)
    
    def listaPremium(self):
        session = Database().Session()
        listaPremium = session.query(Utente).filter_by(premium=1).order_by(Utente.points.desc()).all()
        return listaPremium

class Collezionabili(Base):
    __tablename__ = "collezionabili"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_telegram = Column(String, nullable=False)
    oggetto = Column(String, nullable=False)
    data_acquisizione = Column(DateTime, nullable=False)
    quantita = Column(Integer, nullable=False)
    data_utilizzo = Column(DateTime, nullable=True)


    def CreateCollezionabile(self,id_telegram,item, quantita=1):
        session = Database().Session()
        try:
            collezionabile = Collezionabili()
            collezionabile.id_telegram         = id_telegram
            collezionabile.oggetto             = item
            collezionabile.data_acquisizione   = datetime.datetime.today()
            collezionabile.quantita            = quantita
            collezionabile.data_utilizzo       = None
            print(collezionabile.id_telegram)
            session.add(collezionabile)
            session.commit()
            return True
        except:
            session.rollback()
            return False
        finally:
            session.close()

    def getInventarioUtente(self,id_telegram):
        session = Database().Session()
        from sqlalchemy import func

        inventario = session.query(
            Collezionabili.oggetto,
            func.sum(Collezionabili.quantita).label('quantita')
        ).filter_by(
            id_telegram=str(id_telegram), 
            data_utilizzo=None
        ).group_by(
            Collezionabili.oggetto
        ).order_by(
            Collezionabili.oggetto
        ).all()
        session.close()
        return inventario

    def getItemByUser(self,id_telegram,nome_oggetto):
        session = Database().Session()
        from sqlalchemy import func

        oggetto = session.query(
            Collezionabili.oggetto,
            func.sum(Collezionabili.quantita).label('quantita')
        ).filter_by(
            id_telegram=str(id_telegram), 
            oggetto=nome_oggetto,
            data_utilizzo=None
        ).group_by(
            Collezionabili.oggetto
        ).order_by(
            Collezionabili.oggetto
        ).first()
        session.close()
        return oggetto
    
    def usaOggetto(self,id_telegram,oggetto):
        session = Database().Session()
        # Prendi il primo disponibile (non ancora usato)
        collezionabile = session.query(Collezionabili).filter_by(id_telegram=str(id_telegram), oggetto=oggetto, data_utilizzo=None).first()
        if collezionabile:
            if collezionabile.quantita > 1:
                collezionabile.quantita -= 1
            else:
                collezionabile.data_utilizzo = datetime.datetime.now()
            session.commit()
            print(f'{id_telegram} ha usato {oggetto}')
        session.close()

    def armaTrappola(self, id_gruppo, tipo, id_utente):
        session = Database().Session()
        try:
            trappola = Trappola()
            trappola.idgruppo = id_gruppo
            trappola.tipo = tipo
            trappola.id_utente = id_utente
            trappola.data_piazzamento = datetime.datetime.now()
            session.add(trappola)
            session.commit()
            print(f"Trappola {tipo} armata nel gruppo {id_gruppo} da {id_utente}")
        except Exception as e:
            session.rollback()
            print(f"Errore armamento trappola: {e}")
        finally:
            session.close()

    def checkTrappole(self, message):
        id_gruppo = message.chat.id
        session = Database().Session()
        # Prendi la trappola più vecchia piazzata nel gruppo
        trappola = session.query(Trappola).filter_by(idgruppo=id_gruppo).order_by(Trappola.data_piazzamento.asc()).first()
        session.close()
        
        if trappola:
            # Check owner
            id_telegram = message.from_user.id
            utente = Utente().getUtente(id_telegram)
            
            if trappola.id_utente == id_telegram and trappola.tipo == 'Nitro':
                session.close() # Close session before returning
                return False

            # Eliminiamo la trappola prima di scatenare l'effetto per evitare loop
            session = Database().Session()
            session.delete(session.query(Trappola).filter_by(id=trappola.id).first())
            session.commit()
            session.close()
            
            # Scateniamo l'effetto
            
            if trappola.tipo == 'Nitro':
                self.nitroExploded(utente, message)
            elif trappola.tipo == 'TNT':
                self.tnt_start(utente, message)
            elif trappola.tipo == 'Cassa':
                self.cassaWumpa(utente, message)
            return True
        return False
    """
    #pandas
    def maybeDrop(self,message):
        if message.chat.type == "group" or message.chat.type == "supergroup":   
            id_telegram = message.from_user.id
            items = pd.read_csv('items.csv')
            indice_oggetto = random.randint(0,len(items)-1)
            tento_oggetto = items.iloc[indice_oggetto]
            oggetto = self.getItemByUser(id_telegram,tento_oggetto['nome'])
            quantita = random.randint(1,tento_oggetto['massimo_numero_per_drop'])
            if oggetto:
                if oggetto.oggetto==tento_oggetto['nome']:
                    quantita+=1
                    if oggetto.quantita==int(tento_oggetto['max_per_persona']):
                        return 0

            culo = random.randint(1,tento_oggetto['rarita'])
            if culo==tento_oggetto['rarita']:
                self.CreateCollezionabile(id_telegram,tento_oggetto['nome'],quantita)
                sti = open(f"Stickers/{tento_oggetto['sticker']}", 'rb')
                bot.send_sticker(message.chat.id, sti)
                self.triggerDrop(message,tento_oggetto)
                return True
            return False
    """
    def maybeDrop(self, message):
        if message.chat.type == "group" or message.chat.type == "supergroup":
            id_telegram = message.from_user.id
            try:
                with open('items.csv', 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    # Skip header if present (assuming first line is header 'nome,rarita...')
                    if lines and lines[0].startswith('nome,'):
                        lines = lines[1:]
                    
                    items = [line.split(',') for line in lines]
            except Exception as e:
                print(f"Error reading items.csv: {e}")
                return False

            if not items:
                return False

            indice_oggetto = random.randint(0, len(items) - 1)
            obj = items[indice_oggetto]
            
            # Ensure we have enough columns
            if len(obj) < 5:
                return False

            tento_oggetto = {}
            try:
                tento_oggetto['nome'] = obj[0]
                tento_oggetto['rarita'] = int(obj[1])
                tento_oggetto['massimo_numero_per_drop'] = int(obj[2])
                tento_oggetto['max_per_persona'] = int(obj[3])
                tento_oggetto['sticker'] = obj[4].strip() # Remove any remaining whitespace
            except ValueError:
                # Handle cases where integer conversion fails
                return False

            oggetto = self.getItemByUser(id_telegram, tento_oggetto['nome'])
            quantita = random.randint(1, tento_oggetto['massimo_numero_per_drop'])
            
            if oggetto:
                if oggetto.oggetto == tento_oggetto['nome']:
                    # Logic: if user already has max items, don't drop
                    if oggetto.quantita >= tento_oggetto['max_per_persona']:
                        return False
                    
                    # Prevent going over max
                    if oggetto.quantita + quantita > tento_oggetto['max_per_persona']:
                        quantita = tento_oggetto['max_per_persona'] - oggetto.quantita

            culo = random.randint(1, tento_oggetto['rarita'])
            if culo == tento_oggetto['rarita']:
                try:
                    sti = open(f"Stickers/{tento_oggetto['sticker']}", 'rb')
                    bot.send_sticker(message.chat.id, sti)
                    sti.close() # Close the file
                    self.triggerDrop(message, tento_oggetto, quantita)
                    return True
                except FileNotFoundError:
                    print(f"Sticker not found: Stickers/{tento_oggetto['sticker']}")
                    return False
            return False

                    
    def tnt_start(self, utente, message):
        bot.reply_to(message, "💣 Ops!... Hai calpestato una Cassa TNT! Scrivi entro 3 secondi per evitarla!")

        timestamp = datetime.datetime.now()
        Database().update_user(utente.id_telegram,{
            'start_tnt':timestamp,
            'end_tnt': None
            }
        )

    def nitroExploded(self, utente, message):
        wumpa_persi = random.randint(1,5)*-1
        Utente().addPoints(utente,wumpa_persi)
        bot.reply_to(message, "💥 Ops!... Hai calpestato una Cassa Nitro! Hai perso "+str(wumpa_persi)+" "+PointsName+"! \n\n"+Utente().infoUser(utente),parse_mode='markdown')

    def cassaWumpa(self, utente, message):
        wumpa_extra = random.randint(1,5)
        Utente().addPoints(utente,wumpa_extra)
        bot.reply_to(message, "📦 Hai trovato una cassa con "+str(wumpa_extra)+" "+PointsName+"!\n\n"+Utente().infoUser(utente),parse_mode='markdown')

    def triggerDrop(self,message,oggetto,quantita):
        id_telegram = message.from_user.id
        utente = Utente().getUtente(id_telegram)
        
        def drago(utente,message):
            pass

        if oggetto['nome']=='TNT':
            self.tnt_start(utente,message)
        elif oggetto['nome']=='Nitro':
            self.nitroExploded(utente,message)
        elif oggetto['nome']=='Cassa':
            self.cassaWumpa(utente,message)
        elif 'La sfera del Drago' in oggetto['nome']:
            drago(utente,message)
        else:
            self.CreateCollezionabile(id_telegram,oggetto['nome'],quantita)
            bot.reply_to(message,f"Complimenti! Hai ottenuto {oggetto['nome']}")
            

    def checkShenron(self, id_telegram):
        session = Database().Session()
        count = session.query(Collezionabili).filter(
            Collezionabili.id_telegram == id_telegram,
            Collezionabili.oggetto.like('La Sfera del Drago Shenron%'),
            Collezionabili.data_utilizzo == None
        ).group_by(Collezionabili.oggetto).count()
        session.close()
        return count >= 7

    def checkPorunga(self, id_telegram):
        session = Database().Session()
        count = session.query(Collezionabili).filter(
            Collezionabili.id_telegram == id_telegram,
            Collezionabili.oggetto.like('La Sfera del Drago Porunga%'),
            Collezionabili.data_utilizzo == None
        ).group_by(Collezionabili.oggetto).count()
        session.close()
        return count >= 7

    def useDragonBalls(self, id_telegram, drago_type):
        session = Database().Session()
        balls = session.query(Collezionabili).filter(
            Collezionabili.id_telegram == id_telegram,
            Collezionabili.oggetto.like(f'La Sfera del Drago {drago_type}%'),
            Collezionabili.data_utilizzo == None
        ).all()
        
        consumed_counts = {}
        for ball in balls:
            if ball.oggetto not in consumed_counts:
                ball.data_utilizzo = datetime.datetime.now()
                consumed_counts[ball.oggetto] = True
                
        session.commit()
        session.close()

def use_dragon_balls_logic(id_telegram, drago_type):
    try:
        session = Database().Session()
        balls = session.query(Collezionabili).filter(
            Collezionabili.id_telegram == id_telegram,
            Collezionabili.oggetto.like(f'La Sfera del Drago {drago_type}%'),
            Collezionabili.data_utilizzo == None
        ).all()
        
        consumed_counts = {}
        for ball in balls:
            if ball.oggetto not in consumed_counts:
                ball.data_utilizzo = datetime.datetime.now()
                consumed_counts[ball.oggetto] = True
                
        session.commit()
    except Exception as e:
        print(f"Error in use_dragon_balls_logic: {e}")
    finally:
        session.close()
