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


class UserCharacter(Base):
    __tablename__ = "user_character"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('utente.id_Telegram'))
    character_name = Column(String(32))

class DailyShop(Base):
    __tablename__ = "dailyshop"
    id = Column(Integer, primary_key=True)
    id_utente = Column('id_utente', Integer)
    data = Column('data', Date)
    tipo_pozione = Column('tipo_pozione', String) # New column
    pozioni_rimanenti = Column('pozioni_rimanenti', Integer, default=10)

class AchievementCategory(Base):
    __tablename__ = "achievement_category"
    id = Column(Integer, primary_key=True)
    nome = Column(String(64), unique=True) # e.g., "Saga di Pilaf"
    descrizione = Column(String(256))
    icona = Column(String(8)) # e.g., "🐉"

class Achievement(Base):
    __tablename__ = "achievement"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('achievement_category.id'))
    nome = Column(String(128))
    descrizione = Column(String(512))
    tipo = Column(String(32)) # e.g., "boss_kill", "level_reach", "collect_pg"
    requisito_valore = Column(String(128)) # e.g., "Re Pilaf" or "50"
    premio_tipo = Column(String(32)) # e.g., "fagioli", "pg", "exp"
    premio_valore = Column(String(128))
    punti_achievement = Column(Integer, default=10) # For progression bar
    n_ordine = Column(Integer, default=0)

class UserAchievement(Base):
    __tablename__ = "user_achievement"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('utente.id_Telegram'))
    achievement_id = Column(Integer, ForeignKey('achievement.id'))
    completato = Column(Boolean, default=False)
    progresso_attuale = Column(Float, default=0.0)
    data_completamento = Column(DateTime)

class Database:
    def __init__(self):
        engine = create_engine('sqlite:///dbz.db', connect_args={'timeout': 30})
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def startMarkup(self,utente=None):
        markup = types.ReplyKeyboardMarkup()

        markup.add('ℹ️ info','🎒 Inventario','🛒 Negozio')
        if utente is not None:
            markup.add('👤 Scegli il personaggio', '🐢 Kame House')
            markup.add('🏆 Obiettivi Saga', '📖 Saga Pass')
        return markup

    def negozioPozioniMarkup(self, user_id=None):
        markup = types.ReplyKeyboardMarkup()
        
        all_potions = [
            '🧪 Pozione Rigenerante Piccola', '🧪 Pozione Rigenerante Media',
            '🧪 Pozione Rigenerante Grande', '🧪 Pozione Rigenerante Enorme',
            '🧪 Pozione Aura Piccola', '🧪 Pozione Aura Media',
            '🧪 Pozione Aura Grande', '🧪 Pozione Aura Enorme',
        ]

        if user_id: 
            # 1. Check Personal Cooldown (12h)
            from model import Utente
            utente = Utente().getUtente(user_id)
            import datetime
            now = datetime.datetime.now()
            
            show_radar = True
            if utente and utente.last_radar_purchase:
                diff = now - utente.last_radar_purchase
                if diff.total_seconds() < 24 * 3600:
                    show_radar = False
            
            # 2. Add Button if not in cooldown
            if show_radar:
                radar = Collezionabili().getItemByUser(user_id, 'Radar Cercasfere')
                if radar:
                    all_potions.append('🔋 Cariche Radar')
                else:
                    all_potions.append('📟 Radar Cercasfere')

            import datetime
            session = self.Session()
            oggi = datetime.date.today()
            
            # 1. Potion Stock (Daily)
            shops_daily = session.query(DailyShop).filter_by(id_utente=0, data=oggi).all()
            exhausted = {s.tipo_pozione for s in shops_daily if s.pozioni_rimanenti <= 0}
            
            # 2. Radar Stock (2-Day Cycle)
            for r_type in ["Radar Cercasfere", "Cariche Radar"]:
                latest_r = session.query(DailyShop).filter_by(id_utente=0, tipo_pozione=r_type).order_by(DailyShop.data.desc()).first()
                if latest_r:
                    # If within 2 days and exhausted
                    if (oggi - latest_r.data).days < 2 and latest_r.pozioni_rimanenti <= 0:
                        exhausted.add(r_type)

            session.close()
            
            # Filter available potions
            available_potions = []
            for p in all_potions:
                clean_name = p.replace("🧪 ", "").replace("📟 ", "").replace("🔋 ", "")
                if clean_name not in exhausted:
                    available_potions.append(p)
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
    

    def delete_user_complete(self, chatid):
        session = self.Session()
        try:
            # Delete from Utente
            session.query(Utente).filter_by(id_telegram=chatid).delete()
            # Delete from Collezionabili (inventory)
            session.query(Collezionabili).filter_by(id_telegram=str(chatid)).delete()
            # Delete from Domenica (bonus)
            session.query(Domenica).filter_by(utente=chatid).delete()
            # Delete from UserCharacter (collection)
            session.query(UserCharacter).filter_by(user_id=chatid).delete()
            # Delete from UserSeasonProgress
            session.query(UserSeasonProgress).filter_by(user_id=chatid).delete()
            # Delete from RaidParticipant (optional, but good for clean slate)
            session.query(RaidParticipant).filter_by(user_id=chatid).delete()
            
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
    last_radar_purchase = Column('last_radar_purchase', DateTime) # For 12h cooldown
    
    # New Stats
    stat_vita = Column('stat_vita', Integer, default=0)
    stat_aura = Column('stat_aura', Integer, default=0)
    stat_danno = Column('stat_danno', Integer, default=0)
    stat_velocita = Column('stat_velocita', Integer, default=0)
    stat_resistenza = Column('stat_resistenza', Integer, default=0)
    stat_crit_rate = Column('stat_crit_rate', Integer, default=0)
    
    # New Current Aura
    aura = Column('aura', Integer, default=60)
    
    # Character Growth System
    stadio_crescita = Column('stadio_crescita', String, default='bambino')
    data_crescita = Column('data_crescita', DateTime)
    
    # Kame House Resting System
    is_resting = Column('is_resting', Boolean, default=False)

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
                utente.stadio_crescita = 'bambino'
                session.add(utente)
                session.commit()
                
                # Assign Random Starter Character
                self.assegna_pg_casuale(self, id_telegram, session)
                
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

    def assegna_pg_casuale(self, id_telegram, session):
        """Selects a random starter character and adds it to the user's collection."""
        # Get all starter characters (Lv 1, is_starter=True)
        starter_lvs = session.query(Livello).filter_by(livello=1, is_starter=True).all()
        
        if not starter_lvs:
            # Fallback if no starters are marked
            starter_lvs = session.query(Livello).filter_by(livello=1).all()
            
        if starter_lvs:
            chosen = random.choice(starter_lvs)
            self.sblocca_pg(self, chosen.nome, session, id_telegram)
            # Set as initial selected level
            session.query(Utente).filter_by(id_telegram=id_telegram).update({'livello_selezionato': chosen.id})
            session.commit()

    def sblocca_pg(self, char_name, session, id_telegram):
        """Adds a character to the user's unlocked collection."""
        exist = session.query(UserCharacter).filter_by(user_id=id_telegram, character_name=char_name).first()
        if not exist:
            new_char = UserCharacter(user_id=id_telegram, character_name=char_name)
            session.add(new_char)
            session.commit()
            return True
        return False

    def verifica_crescita(self):
        """Checks if the character meets growth milestones."""
        if self.stadio_crescita == 'adulto':
            return False, "Sei già adulto!"
        
        # Conditions: LV 15 for Premium, 20 for Normal
        min_lv = 15 if self.premium == 1 else 20
        
        if self.livello >= min_lv:
            return True, "Puoi crescere!"
        else:
            return False, f"Ti serve il livello {min_lv} per diventare adulto."

    def applica_crescita(self, session):
        """Applies growth bonuses and status."""
        if self.stadio_crescita == 'adulto':
            return False
            
        self.stadio_crescita = 'adulto'
        self.data_crescita = datetime.datetime.now()
        
        # Apply One-Time Growth Bonuses (Permanent)
        # Note: We update base stats (or equivalents) directly on the object.
        # These will be factored into calculate stats via infoUser formulas eventually.
        # For now, let's just push them to the user record.
        
        # +100 Max HP (conceptually) -> We'll add it to stat_vita equivalents in calculations
        # But wait, existing system uses stat_vita * 10. 
        # Let's just grant a block of stats.
        self.stat_vita += 10 # +100 HP
        self.stat_aura += 5  # +25 Aura
        self.stat_danno += 2 # +4 DMG
        
        return True
    
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
        
        # New: get Rank
        import Points
        rank = Points.Points().getRank(utente)

        nome_utente = utente.nome if utente.username is None else utente.username
        answer = ''

        
        # Growth Stage Display
        emoji = "👨🏻" if utente.stadio_crescita == 'adulto' else "👦🏻"
        stage_name = utente.stadio_crescita.capitalize()
        answer += f"{emoji} **Stadio**: {stage_name}\n"
        if utente.is_resting:
            answer += "💤 **Stato**: In riposo alla Kame House\n"

        # Character Name display
        char_label = f"**{selectedLevel.nome}**" if selectedLevel else "**Guerriero**"
        answer += f"👤 {char_label} ({nome_utente}): {utente.points} {PointsName}\n"
        try:
            max_vita = 50 + ((utente.stat_vita or 0) * 10)
            max_aura = 60 + ((utente.stat_aura or 0) * 5)
            
            # Formatta la visualizzazione Vita (es. 50/50)
            current_vita = utente.vita if utente.vita is not None else 50
            answer += f"❤️ *Vita*: {current_vita}/{max_vita}\n"
            
            # Aura attualmente è sempre al massimo (non c'è consumo)
            current_aura = utente.aura if utente.aura is not None else 60
            answer += f"💙 *Aura*: {current_aura}/{max_aura}\n"
            answer += f"⚔️ *Danno*: {10 + (utente.stat_danno or 0) * 2}\n"
            answer += f"⚡️ *Velocità*: {(utente.stat_velocita or 0)}\n"
            answer += f"🛡️ *Resistenza*: {(utente.stat_resistenza or 0)}% (MAX 75%)\n"
            
            # DODGE DISPLAY
            dodge_chance = min(40, (utente.stat_velocita or 0) * 2)
            answer += f"💨 *Schivata*: {dodge_chance}%\n"
            
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
            
            # Display Skill
            skill_name = selectedLevel.skill_name or "Attacco Speciale"
            multiplier = selectedLevel.skill_multiplier or 3.0
            
            # Adult Bonus: Skills are 50% more powerful
            if utente.stadio_crescita == 'adulto':
                multiplier *= 1.5
                
            cost = selectedLevel.skill_aura_cost or 60
            skill_dmg = int((10 + (utente.stat_danno or 0) * 2) * multiplier) # Base (10 + stat*2) * Multiplier
            
            answer += f"\n✨ **Abilità**:\n"
            answer += f"🟣 {skill_name}: {skill_dmg} DMG, {cost} Aura\n"
            
            # Display Second Skill if Level >= 30
            if utente.livello >= (selectedLevel.skill2_unlock_lv or 30):
                s2_name = selectedLevel.skill2_name or "Mossa Finale"
                s2_mult = selectedLevel.skill2_multiplier or 4.5
                if utente.stadio_crescita == 'adulto':
                    s2_mult *= 1.5
                s2_dmg = int((10 + (utente.stat_danno or 0) * 2) * s2_mult)
                s2_cost = selectedLevel.skill2_aura_cost or 100
                answer += f"🔥 {s2_name}: {s2_dmg} DMG, {s2_cost} Aura\n"
        else:
            answer += f"*🎖 Lv. *{utente.livello}\n"


        return answer

    def addRandomExp(self,user,message):
        exp = random.randint(1,5)
        self.addExp(user,exp)
 
    def addExp(self,utente,exp):
        Database().update_user(utente.id_telegram,{'exp':utente.exp+exp})
        self.addSeasonExp(utente.id_telegram, exp)

    def addSeasonExp(self, user_id, exp):
        session = Database().Session()
        try:
            # 1. Get Active Season
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                return

            # 2. Get User Progress
            progress = session.query(UserSeasonProgress).filter_by(user_id=user_id, season_id=season.id).first()
            if not progress:
                progress = UserSeasonProgress(user_id=user_id, season_id=season.id, season_exp=0, season_level=1)
                session.add(progress)
                session.flush()

            progress.season_exp += exp
            
            # 3. Check Level Up
            # Find the tier requirement for the NEXT level
            next_tier = session.query(SeasonTier).filter_by(season_id=season.id, livello=progress.season_level + 1).first()
            while next_tier and progress.season_exp >= next_tier.exp_richiesta:
                progress.season_level += 1
                # Check for even higher levels (in case of massive XP gain)
                next_tier = session.query(SeasonTier).filter_by(season_id=season.id, livello=progress.season_level + 1).first()
            
            session.commit()
        except Exception as e:
            print(f"Error adding Season XP: {e}")
            session.rollback()
        finally:
            session.close()

    def addPoints(self, utente, points):  
        try: 
            current_points = int(utente.points or 0)
            new_points = current_points + int(points)
            Database().update_user(utente.id_telegram,{'points': new_points})
        except Exception as e:
            print(f"Error in addPoints (ID): {e}")
            current_points = int(utente.points or 0)
            Database().update_table_entry(Utente, "username", utente.username, {'points': current_points + int(points)})

    def donaPoints(self, utenteSorgente, utenteTarget, points):
        points = int(points)
        if points <= 0:
            return "Non posso donare " + PointsName + " negativi o zero"
        
        # Ensure we have fresh data for points
        sorgente_pts = int(utenteSorgente.points or 0)
        
        if sorgente_pts >= points:
            self.addPoints(utenteTarget, points)
            self.addPoints(utenteSorgente, -points)
            return f"{utenteSorgente.username or utenteSorgente.nome} ha donato {points} {PointsName} a {utenteTarget.username or utenteTarget.nome}! ❤️"
        else:
            return f"{PointsName} non sufficienti (Hai: {sorgente_pts})"
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
    link_img_adult = Column('link_img_adult', String(128)) # Adult variant
    saga = Column('saga',String(128))
    lv_premium = Column('lv_premium',Integer)
    is_starter = Column('is_starter', Boolean, default=False) # For random assignment
    is_elite = Column('is_elite', Boolean, default=False)     # Unused for now but good for tiers
    skill_name = Column(String(64), default="Attacco Speciale")
    skill_multiplier = Column(Float, default=3.0)
    skill_aura_cost = Column(Integer, default=60)
    
    # Second Skill (Phase 2)
    skill2_name = Column(String(64), default="Mossa Finale")
    skill2_multiplier = Column(Float, default=4.5)
    skill2_aura_cost = Column(Integer, default=100)
    skill2_unlock_lv = Column(Integer, default=30)

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
                livello.link_img_adult = None 
                livello.saga = saga
                livello.lv_premium = lv_premium
                livello.is_starter = False # Default
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

    def setSelectedLevel(self,utente,level_num,lv_premium, char_name=None):
        session = Database().Session()
        query = session.query(Livello).filter_by(livello=level_num, lv_premium=lv_premium)
        if char_name:
            query = query.filter_by(nome=char_name)
        
        livello = query.first()
        if livello:
            Database().update_user(utente.id_telegram,{'livello_selezionato':livello.id})
        session.close()

    def listaLivelliSbloccati(self, utente):
        """Returns only levels that correspond to characters in the user's collection."""
        session = Database().Session()
        # Get character names in collection
        collection = session.query(UserCharacter).filter_by(user_id=utente.id_telegram).all()
        char_names = [c.character_name for c in collection]
        
        # Get levels for these characters that the user has reached
        livelli = session.query(Livello).filter(
            Livello.nome.in_(char_names),
            Livello.livello <= utente.livello
        ).order_by(asc(Livello.livello)).all()
        
        session.close()
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
        
        if lv > utenteSorgente.livello:
            vecchio_livello = utenteSorgente.livello
            # Update DB with new level immediately
            Database().update_user(utenteSorgente.id_telegram, {'livello': lv})
            
            # Loop through ALL levels gained (e.g. 5 -> 8 means we check 6, 7, 8)
            session = Database().Session()
            try:
                for i in range(vecchio_livello + 1, lv + 1):
                    lvObj = session.query(Livello).filter_by(livello=i).first()
                    lbPremiumObj = session.query(Livello).filter_by(livello=i, lv_premium=1).first()
                    
                    # 1. Standard Character Unlock
                    if lvObj and lvObj.link_img:
                        Utente().sblocca_pg(lvObj.nome, session, utenteSorgente.id_telegram)
                        if i == lv: # Only send photo for the FINAL level reached to avoid spam
                            try:
                                msg_text = f"Complimenti! 🎉 Sei passato al livello {lv}! Hai sbloccato il personaggio [{lvObj.nome}]({lvObj.link_img}) 🎉\n\n{Utente().infoUser(utenteSorgente)}"
                                bot.send_photo(message.chat.id, lvObj.link_img, caption=msg_text, parse_mode='markdown', reply_to_message_id=message.message_id)
                            except:
                                bot.reply_to(message, f"Complimenti! 🎉 Sei passato al livello {lv}! Hai sbloccato il personaggio [{lvObj.nome}]({lvObj.link_img}) 🎉\n\n{Utente().infoUser(utenteSorgente)}", parse_mode='markdown')
                        else:
                            # Just unlock silently or log? Maybe notify if it's a huge jump?
                            # For now silently unlock intermediate ones
                            pass

                    if lbPremiumObj:
                        # NEW LOGIC: Premium Characters are NOT unlocked automatically anymore.
                        # They are now part of the Season Pass rewards.
                        pass

                    # 3. Points Reward (Every 5 levels)
                    if i % 5 == 0:
                        add = 0
                        if i==5: add = 40
                        elif i==10: add = 60
                        elif i==15: add = 80
                        elif i==20: add = 100
                        elif i==25: add = 120
                        elif i==30: add = 150
                        elif i==35: add = 200
                        elif i==40: add = 250
                        else: add = 250
                        
                        Utente().addPoints(utenteSorgente, add)
                        if i == lv:
                            bot.reply_to(message, f"Complimenti per il traguardo del Lv {i}! Per te {str(add)} {PointsName}! 🎉", parse_mode='markdown')
            
                session.commit()
            except Exception as e:
                print(f"Error in checkUpdateLevel loop: {e}")
                session.rollback()
            finally:
                session.close()

class GiocoAroma(Base):
    __tablename__ = 'giocoaroma'
    id = Column('id',Integer, primary_key=True)
    titolo = Column('nome',String)
    descrizione = Column('descrizione',String)
    link = Column('link',String)
    from_chat = Column('from_chat',String)
    messageid = Column('messageid',Integer)

import datetime


class Collezionabili(Base):
    __tablename__ = "collezionabili"
    
    # Global state for Dragon Radar events
    pending_radar_drop = {} # {chat_id: sphere_name}

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_telegram = Column(String, nullable=False)
    oggetto = Column(String, nullable=False)
    data_acquisizione = Column(DateTime, nullable=False)
    quantita = Column(Integer, nullable=False)
    cariche = Column(Integer, default=0) # New column for Radar
    data_utilizzo = Column(DateTime, nullable=True)


    def CreateCollezionabile(self,id_telegram,item, quantita=1, cariche=0):
        session = Database().Session()
        try:
            collezionabile = Collezionabili()
            collezionabile.id_telegram         = id_telegram
            collezionabile.oggetto             = item
            collezionabile.data_acquisizione   = datetime.datetime.today()
            collezionabile.quantita            = quantita
            collezionabile.cariche             = cariche
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
            
            if trappola.id_utente == id_telegram and trappola.tipo in ['Nitro', 'TNT']:
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
            items = pd.read_csv('items.csv', encoding='latin-1')
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
            chat_id = message.chat.id
            id_telegram = message.from_user.id
            
            # --- 1. Check for Pending Radar Drop ---
            if chat_id in Collezionabili.pending_radar_drop:
                sphere_name = Collezionabili.pending_radar_drop.pop(chat_id)
                try:
                    with open('items.csv', 'r', encoding='latin-1') as f:
                        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('nome,')]
                        for l in lines:
                            parts = l.split(',')
                            if parts[0] == sphere_name:
                                sticker = parts[4].strip()
                                # Drop it!
                                self.CreateCollezionabile(id_telegram, sphere_name, 1)
                                try:
                                    bot.send_sticker(chat_id, open(f"Stickers/{sticker}", 'rb'))
                                    bot.reply_to(message, "✨ Hai trovato: Sfera del Drago!")
                                    # Private notification
                                    try:
                                        bot.send_message(id_telegram, f"✨ Hai trovato: {sphere_name}!")
                                    except: pass
                                except: pass
                                return True
                except: pass

            # --- 2. Radar Trigger Chance (REMOVED: Now manual item) ---
            # Random automatic radar is disabled.

            # --- 3. Normal Drop Logic ---
            try:
                with open('items.csv', 'r', encoding='latin-1') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    # Skip header if present
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
                tento_oggetto['sticker'] = obj[4].strip() 
            except ValueError:
                return False

            oggetto = self.getItemByUser(id_telegram, tento_oggetto['nome'])
            quantita = random.randint(1, tento_oggetto['massimo_numero_per_drop'])
            
            if oggetto:
                if oggetto.oggetto == tento_oggetto['nome']:
                    if oggetto.quantita >= tento_oggetto['max_per_persona']:
                        return False
                    
                    if oggetto.quantita + quantita > tento_oggetto['max_per_persona']:
                        quantita = tento_oggetto['max_per_persona'] - oggetto.quantita

            culo = random.randint(1, tento_oggetto['rarita'])
            if culo == tento_oggetto['rarita']:
                try:
                    ch = 10 if 'Radar' in tento_oggetto['nome'] else 0
                    # self.CreateCollezionabile(id_telegram, tento_oggetto['nome'], quantita, cariche=ch) # MOVED to triggerDrop
                    
                    sti = open(f"Stickers/{tento_oggetto['sticker']}", 'rb')
                    bot.send_sticker(message.chat.id, sti)
                    sti.close() 
                    self.triggerDrop(message, tento_oggetto, quantita, cariche=ch)
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

    def triggerDrop(self,message,oggetto,quantita, **kwargs):
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
        elif 'La Sfera del Drago' in oggetto['nome']:
            self.CreateCollezionabile(id_telegram,oggetto['nome'],quantita)
            bot.reply_to(message,f"✨ Hai trovato: {oggetto['nome']}!")
            drago(utente,message)
        else:
            self.CreateCollezionabile(id_telegram,oggetto['nome'],quantita, cariche=kwargs.get('cariche', 0))
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

class Season(Base):
    __tablename__ = 'season'
    id = Column(Integer, primary_key=True)
    numero = Column(Integer)
    nome = Column(String)
    data_inizio = Column(Date)
    data_fine = Column(Date)
    active = Column(Boolean, default=False)

class SeasonTier(Base):
    __tablename__ = 'season_tier'
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('season.id'))
    livello = Column(Integer)
    exp_richiesta = Column(Integer)
    ricompensa_free_tipo = Column(String)
    ricompensa_free_valore = Column(String)
    ricompensa_premium_tipo = Column(String)
    ricompensa_premium_valore = Column(String)

class UserSeasonProgress(Base):
    __tablename__ = 'user_season_progress'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('utente.id_Telegram'))
    season_id = Column(Integer, ForeignKey('season.id'))
    season_exp = Column(Integer, default=0)
    season_level = Column(Integer, default=1)
    is_premium_pass = Column(Boolean, default=False)
    claimed_tiers = Column(String, default="[]") # JSON list of claimed tier IDs

class BossTemplate(Base):
    __tablename__ = 'boss_template'
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    image_url = Column(String)
    hp_max = Column(Integer)
    atk = Column(Integer)
    xp_reward_total = Column(Integer)
    points_reward_total = Column(Integer)
    season_id = Column(Integer, default=1) # Linked to Season
    saga = Column(String) # Linked to a specific saga (e.g. "Saga di Pilaf")
    is_boss = Column(Boolean, default=False)

    # --- LEVELING & SCALING ---
    livello = Column(Integer, default=1)
    hp_base = Column(Integer, default=100)
    hp_per_lv = Column(Integer, default=30)
    atk_base = Column(Integer, default=10)
    atk_per_lv = Column(Integer, default=4)
    xp_base = Column(Integer, default=50)
    xp_per_lv = Column(Integer, default=20)
    points_base = Column(Integer, default=20)
    points_per_lv = Column(Integer, default=10)
    is_elite = Column(Boolean, default=False)

    def calculate_and_sync_stats(self):
        """
        Calculates HP, ATK, and XP based on current level and base/growth values.
        If is_elite is True, stats are significantly boosted.
        """
        # Base formulas
        h = (self.hp_base or 100) + ((self.livello or 1) * (self.hp_per_lv or 30))
        a = (self.atk_base or 10) + ((self.livello or 1) * (self.atk_per_lv or 4))
        x = (self.xp_base or 50) + ((self.livello or 1) * (self.xp_per_lv or 20))
        p = (self.points_base or 20) + ((self.livello or 1) * (self.points_per_lv or 10))

        # Elite Multipliers
        if self.is_elite:
            h = int(h * 2.5)  # 2.5x HP
            a = int(a * 2.5)  # 2.5x ATK
            x = int(x * 2.0)  # 2.0x XP Reward
            p = int(p * 2.0)  # 2.0x Points Reward

        self.hp_max = h
        self.atk = a
        self.xp_reward_total = x
        self.points_reward_total = p

class ActiveRaid(Base):
    __tablename__ = 'active_raid'
    id = Column(Integer, primary_key=True)
    boss_id = Column(Integer, ForeignKey('boss_template.id'))
    hp_current = Column(Integer)
    hp_max = Column(Integer)
    chat_id = Column(Integer)
    message_id = Column(Integer)
    active = Column(Boolean, default=True)
    last_log = Column(Text)

class RaidParticipant(Base):
    __tablename__ = 'raid_participant'
    id = Column(Integer, primary_key=True)
    raid_id = Column(Integer, ForeignKey('active_raid.id'))
    user_id = Column(Integer, ForeignKey('utente.id_Telegram'))
    dmg_total = Column(Integer, default=0)
    last_attack_time = Column(DateTime)


def spawn_random_seasonal_boss(only_boss=False):
    """Selects and spawns a random boss or mob for the current active season."""
    session = Database().Session()
    try:
        # 1. Get Active Season
        active_season = session.query(Season).filter_by(active=True).first()
        
        bosses = []
        if active_season:
            # Find eligible templates (matching saga name and boss/mob flag)
            bosses = session.query(BossTemplate).filter(
                BossTemplate.saga == active_season.nome, 
                BossTemplate.is_boss == only_boss
            ).all()
            
            # Fallback: if no match by name, try season_id
            if not bosses:
                bosses = session.query(BossTemplate).filter_by(season_id=active_season.id, is_boss=only_boss).all()
        else:
            print("No active season found. Using general/fallback pool.")

        if not bosses:
            # Fallback 1: Default Season (ID=1)
            bosses = session.query(BossTemplate).filter_by(season_id=1, is_boss=only_boss).all()
            
        if not bosses:
            # Fallback 2: Any available matching type
            bosses = session.query(BossTemplate).filter_by(is_boss=only_boss).all()

        if not bosses:
            print("No bosses available in database.")
            return

        boss = random.choice(bosses)

        # 3. Check for active raid
        existing_raid = session.query(ActiveRaid).filter_by(active=True, chat_id=Tecnologia_GRUPPO).first()
        if existing_raid:
            print(f"Raid already active: {existing_raid.id}")
            return

        # 4. Spawn logic
        raid = ActiveRaid(
            boss_id=boss.id,
            hp_current=boss.hp_max,
            hp_max=boss.hp_max,
            chat_id=Tecnologia_GRUPPO,
            active=True,
            last_log="🐉 Il Boss sta osservando i nemici..."
        )
        session.add(raid)
        session.flush()

        msg_text = f"🔥 **UN NEMICO È APPARSO!** 🔥\n\n"
        msg_text += f"Un guerriero selvatico è apparso nel gruppo!\n\n"
        
        elite_tag = " [ELITE] 🌟" if boss.is_elite else ""
        msg_text += f"👾 **Boss**: {boss.nome}{elite_tag}\n"
        msg_text += f"📊 **Livello**: {boss.livello}\n"
        msg_text += f"❤️ **Salute**: {boss.hp_max}/{boss.hp_max} HP\n"
        msg_text += f"⚔️ **Danno**: {boss.atk}\n\n"
        msg_text += f"📜 **Ultima Azione**:\n{raid.last_log}\n\n"
        msg_text += "⚔️ Sconfiggilo per ottenere ricompense!"
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"raid_atk_{raid.id}"),
            types.InlineKeyboardButton("✨ Speciale", callback_data=f"raid_spc_{raid.id}"),
            types.InlineKeyboardButton("🔥 Finale", callback_data=f"raid_spc2_{raid.id}")
        )

        if boss.image_url:
            try:
                sent_msg = bot.send_photo(Tecnologia_GRUPPO, boss.image_url, caption=msg_text, parse_mode='Markdown', reply_markup=markup)
            except:
                sent_msg = bot.send_message(Tecnologia_GRUPPO, msg_text, parse_mode='Markdown', reply_markup=markup)
        else:
            sent_msg = bot.send_message(Tecnologia_GRUPPO, msg_text, parse_mode='Markdown', reply_markup=markup)

        raid.message_id = sent_msg.message_id
        session.commit()
        print(f"Spawned Seasonal Boss: {boss.nome}")

    except Exception as e:
        print(f"Error in auto-spawn: {e}")
    finally:
        session.close()

def boss_auto_attack_job():
    """Background task: Boss attacks a random player in the group every 60s."""
    session = Database().Session()
    try:
        # 1. Find Active Raid
        raid = session.query(ActiveRaid).filter_by(active=True, chat_id=Tecnologia_GRUPPO).first()
        if not raid:
            return

        boss = session.get(BossTemplate, raid.boss_id)
        if not boss:
            return

        # 2. Pick Target (Alive participants only)
        target_id = None
        participants = session.query(RaidParticipant).filter_by(raid_id=raid.id).all()
        alive_ids = []
        
        for p in participants:
            u = session.query(Utente).filter_by(id_telegram=p.user_id).first()
            if u and (u.vita or 0) > 0 and not u.is_resting:
                alive_ids.append(p.user_id)
        
        if alive_ids:
            target_id = random.choice(alive_ids)
        else:
            # Fallback: Random user who has played (XP > 0) AND is alive AND NOT resting
            active_users = session.query(Utente).filter(Utente.exp > 0, Utente.vita > 0, Utente.is_resting == False).all()
            if active_users:
                target_id = random.choice(active_users).id_telegram

        if not target_id:
            return

        target = session.query(Utente).filter_by(id_telegram=target_id).first()
        if not target:
            return

        # 3. Calculate Damage & Multipliers
        base_dmg = boss.atk
        is_special = random.randint(1, 100) <= 15
        is_crit = random.randint(1, 100) <= 10
        
        attack_name = "un attacco fisico"
        dmg_mult = 1.0
        
        if is_special:
            attack_name = random.choice([
                "un'onda energetica", "un colpo a tradimento", 
                "un raggio micidiale", "una tecnica segreta"
            ])
            dmg_mult *= 1.5
            
        # 4. Dodge/Parry Logic
        dodge_chance = min(40, (target.stat_velocita or 0) * 2)
        rolled_dodge = random.randint(1, 100) <= dodge_chance
        
        final_dmg = int(base_dmg * dmg_mult)
        if is_crit:
            final_dmg *= 2
            attack_name += " **CRITICO**"

        dodge_msg = ""
        if rolled_dodge:
            # 50% chance to dodge completely, 50% to parry (reduce 50%)
            if random.random() < 0.5:
                final_dmg = 0
                dodge_msg = f"\n💨 **{target.nome}** ha schivato l'attacco!"
            else:
                final_dmg = int(final_dmg * 0.5)
                dodge_msg = f"\n🛡️ **{target.nome}** ha parato il colpo, dimezzando i danni!"

        # --- CLUMSY ATTACK (Lore-friendly for Lv < 5) ---
        if target.livello < 5 and final_dmg > 0 and random.random() < 0.5:
             final_dmg = 0
             clumsy_action = random.choice([
                 "inciampa sui propri piedi",
                 "scivola su una buccia di banana",
                 "si distrae guardando una farfalla",
                 "starnutisce e manca il bersaglio",
                 "si dimentica cosa stava facendo"
             ])
             dodge_msg += f"\n🌀 **{boss.nome}** {clumsy_action}! **{target.nome}** è salvo!"

        # --- NEWBIE PROTECTION (LV < 10) ---
        # Cap damage to 33% of MAX HP to prevent one-shots
        if target.livello < 10:
            max_hp = 50 + ((target.stat_vita or 0) * 10)
            damage_cap = int(max_hp * 0.33)
            
            if final_dmg > damage_cap:
                final_dmg = damage_cap
                # Optional: Add visual hint of protection?
                # For now kept silent to just make them survive

        # Apply Damage
        target.vita = max(0, target.vita - final_dmg)
        
        # --- 5. Construct Log ---
        log_msg = f"👾 **{boss.nome}** lancia {attack_name}!\n💥 **{target.nome}** ha subito **{final_dmg}** danni!{dodge_msg}"
        if target.vita <= 0:
            log_msg += f"\n💀 **{target.nome}** è andato K.O.!"
        
        raid.last_log = log_msg

        # --- 6. Update UI (Delete Old, Send New) ---
        try:
            bot.delete_message(raid.chat_id, raid.message_id)
        except: pass

        blocks = 10
        filled = int(round(blocks * raid.hp_current / raid.hp_max))
        bar = "🟥" * filled + "⬜️" * (blocks - filled)
        
        msg_text = f"⚠️ **BOSS RAID: {boss.nome}** ⚠️\n"
        msg_text += f"❤️ Vita: [{bar}] {raid.hp_current}/{raid.hp_max}\n"
        msg_text += f"\n📜 **Ultima Azione**:\n{raid.last_log}"

        try:
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"raid_atk_{raid.id}"),
                types.InlineKeyboardButton("✨ Speciale", callback_data=f"raid_spc_{raid.id}"),
                types.InlineKeyboardButton("🔥 Finale", callback_data=f"raid_spc2_{raid.id}")
            )
            
            if boss.image_url:
                try:
                    sent = bot.send_photo(raid.chat_id, boss.image_url, caption=msg_text, parse_mode='Markdown', reply_markup=markup)
                except:
                    sent = bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)
            else:
                sent = bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)
            
            raid.message_id = sent.message_id
        except Exception as e_send:
            print(f"Boss Turn Repost Error: {e_send}")

        session.commit()

    except Exception as e:
        print(f"Error in boss auto-attack: {e}")
    finally:
        session.close()

def process_season_end(season):
    """Calculates top players and announces end of season."""
    session = Database().Session()
    try:
        # 1. Fetch Top 3
        top_players = session.query(UserSeasonProgress).filter_by(season_id=season.id).order_by(UserSeasonProgress.season_exp.desc()).limit(3).all()
        
        msg = f"🏆 **FINE STAGIONE: {season.nome}** 🏆\n\n"
        msg += "Il tempo è scaduto! Ecco i guerrieri più valorosi di questa stagione che ricevono i premi automatici:\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        rewards = [5000, 2500, 1000] # Standard rewards
        
        for i, prog in enumerate(top_players):
            user = session.query(Utente).filter_by(id_telegram=prog.user_id).first()
            if user:
                premio = rewards[i] if i < len(rewards) else 0
                user.points += premio
                msg += f"{medals[i]} **{user.nome}** - {prog.season_exp} XP (+{premio} {PointsName})\n"
            else:
                msg += f"{medals[i]} **Guerriero {prog.user_id}** - {prog.season_exp} XP\n"
        
        if not top_players:
            msg += "Nessun gurreiro ha partecipato a questa stagione... che peccato!\n"
            
        msg += "\n🎉 Complimenti ai vincitori! I premi sono stati accreditati automaticamente sui vostri account."
        msg += "\n\nLa stagione è ora **CHIUSA**. Restate sintonizzati per la prossima!"
        
        bot.send_message(Tecnologia_GRUPPO, msg, parse_mode='Markdown')
        
        # 2. Deactivate
        season.active = False
        session.add(season)
        session.commit()
    except Exception as e:
        print(f"Error processing season end: {e}")
    finally:
        session.close()

def check_season_expiry():
    """Checks if the active season has reached its end date."""
    session = Database().Session()
    try:
        active_season = session.query(Season).filter_by(active=True).first()
        if active_season and active_season.data_fine:
            if datetime.date.today() >= active_season.data_fine:
                print(f"Season {active_season.id} expired. Ending it...")
                process_season_end(active_season)
    except Exception as e:
        print(f"Error checking season expiry: {e}")
    finally:
        session.close()

def calculate_and_sync_saga_progress(user_id):
    import datetime
    session = Database().Session()
    try:
        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not utente:
            return 0
            
        achievements = session.query(Achievement).all()
        if not achievements:
            return 0
            
        newly_completed = 0
        
        for ach in achievements:
            user_ach = session.query(UserAchievement).filter_by(user_id=user_id, achievement_id=ach.id).first()
            if user_ach and user_ach.completato:
                continue
                
            completed = False
            progress = 0.0
            
            try:
                if ach.tipo == "boss_kill":
                    # Check if user participated in a raid against this boss
                    count = session.query(RaidParticipant).join(ActiveRaid, RaidParticipant.raid_id == ActiveRaid.id)\
                        .join(BossTemplate, ActiveRaid.boss_id == BossTemplate.id)\
                        .filter(RaidParticipant.user_id == user_id)\
                        .filter(BossTemplate.nome == ach.requisito_valore)\
                        .count()
                        
                    if count > 0:
                        completed = True
                        progress = 100.0
                        
                elif ach.tipo == "level_reach":
                    req_lv = int(ach.requisito_valore) if ach.requisito_valore.isdigit() else 999
                    if utente.livello >= req_lv:
                        completed = True
                        progress = 100.0
                    else:
                         progress = (utente.livello / req_lv) * 100.0
                         
                elif ach.tipo == "collect_pg":
                    has_char = session.query(UserCharacter).filter_by(
                        user_id=user_id, 
                        character_name=ach.requisito_valore
                    ).first()
                    
                    if has_char:
                        completed = True
                        progress = 100.0
            except Exception as e:
                print(f"Error checking achievement {ach.id} for user {user_id}: {e}")
                continue

            if completed:
                if not user_ach:
                    user_ach = UserAchievement(
                        user_id=user_id, 
                        achievement_id=ach.id,
                        completato=True,
                        progresso_attuale=100.0,
                        data_completamento=datetime.datetime.now()
                    )
                    session.add(user_ach)
                else:
                    user_ach.completato = True
                    user_ach.progresso_attuale = 100.0
                    user_ach.data_completamento = datetime.datetime.now()
                newly_completed += 1
                
            elif progress > 0:
                if not user_ach:
                     user_ach = UserAchievement(
                        user_id=user_id,
                        achievement_id=ach.id,
                        completato=False,
                        progresso_attuale=progress,
                        data_completamento=None
                     )
                     session.add(user_ach)
                elif not user_ach.completato:
                     user_ach.progresso_attuale = progress

        session.commit()
        return newly_completed
        
    except Exception as e:
        print(f"Error in calculate_and_sync_saga_progress: {e}")
        session.rollback()
        return 0
    finally:
        session.close()
