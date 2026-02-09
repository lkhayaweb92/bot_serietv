from telebot import types
from settings import *
from sqlalchemy         import create_engine
from model import Livello, Utente, Database, Collezionabili, use_dragon_balls_logic, Season, SeasonTier, UserSeasonProgress, BossTemplate, ActiveRaid, RaidParticipant, spawn_random_seasonal_boss, boss_auto_attack_job, process_season_end, check_season_expiry, check_raid_start_job, DailyShop, AchievementCategory, Achievement, UserAchievement, UserCharacter, MarketListing
from saga_pass.saga_pass import SagaPassHandler
from channel_downloader.channel_downloader import ChannelDownloader
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
    # 1. Season Lifecycle Check (Daily)
    try:
        check_season_expiry()
    except Exception as e:
        print(f"Season Cycle Error: {e}")

    # 2. Database Compaction (Monthly - 1st day)
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
    def __init__(self, message, bot, user_id=None):
        self.bot = bot
        self.message = message
        # ... comandi mappings cut for brevity in thought but should be included in actual replacement ...
        # (I will include the full dicts to avoid breaking things)
        self.comandi_privati = {
            "👤 Scegli il personaggio": self.handle_choose_character_v2,
            "🏆 Obiettivi Saga": self.handle_saga,
            "📖 Saga Pass": self.handle_pass,
            "ℹ️ info": self.handle_info,
            "🎒 Inventario": self.handle_inventario,
            "🛒 Negozio": self.handle_negozio_pozioni,
            "🧪 Pozione Rigenerante": self.handle_buy_potion,
            "🧪 Pozione Aura": self.handle_buy_potion,
            "📟 Radar Cercasfere": self.handle_buy_radar,
            "🔋 Cariche Radar": self.handle_buy_radar,
            "📊 ALLOCAZIONE STATISTICHE": self.handle_stats_menu,
            "🐢 Kame House": self.handle_kamehouse,
            "Indietro": self.handle_back,
            "🏪 Mercato": self.handle_mercato,
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
            "spawn_boss": self.handle_spawn_boss,
            "season_start": self.handle_season_start,
            "season_addtier": self.handle_season_addtier,
            "set_boss_img": self.handle_set_boss_img,
            "add_boss": self.handle_add_boss,
            "add_saga_boss": self.handle_add_saga_boss,
            "add_mob": self.handle_add_mob,
            "add_mob_adv": self.handle_add_mob_adv,
            "edit_boss": self.handle_edit_boss,
            "set_boss_flag": self.handle_set_boss_flag,
            "set_lv": self.handle_set_lv,
            "season_list": self.handle_season_list,
            "season_set": self.handle_season_set,
            "spawn_random": self.handle_spawn_random,
            "boss_list": self.handle_boss_list,
            "kill_raid": self.handle_kill_raid,
            "set_adult_img": self.handle_set_adult_img,
            "set_img": self.handle_set_img,
            "set_image": self.handle_set_img,
            "set_saga_active": self.handle_set_saga_active_admin, # DEBUG ONLY
        }
        self.comandi_generici = {
            "!dona": self.handle_dona,
            "/dona": self.handle_dona,
            "/me": self.handle_me,
            "!status": self.handle_status,
            "!stats": self.handle_status,
            "!livell": self.handle_livell,
            "!inventario": self.handle_inventario,
            "/inventario": self.handle_inventario,
            "!negozio_pozioni": self.handle_negozio_pozioni,
            "/negozio_pozioni": self.handle_negozio_pozioni,
            "!pass": self.handle_pass,
            "/pass": self.handle_pass,
            "!saga": self.handle_saga,
            "/saga": self.handle_saga,
            "/cresci": self.handle_cresci,
            "/reset_me": self.handle_reset_me,
            "/evoca": self.handle_evoca,
            "/scambia_sfera": self.handle_scambia_sfera,
            "/scambia": self.handle_scambia,
            "/mercato": self.handle_mercato,
            "!mercato": self.handle_mercato,
        }
        
        self.target_id = message.chat.id
        
        if user_id:
            self.chatid = user_id
        else:
            try:
                self.chatid = message.from_user.id
            except Exception as e:
                self.chatid = message.chat.id
    
    def handle_private_command(self):
        message = self.message
        for command, handler in self.comandi_privati.items():
            if message.text.lower().startswith(command.lower()):
                handler()
                break
    def handle_admin_command(self):
        message = self.message
        msg_text = message.text.lower()
        for command, handler in self.comandi_admin.items():
            cmd_lower = command.lower()
            if msg_text.startswith(cmd_lower) or msg_text.startswith("/" + cmd_lower) or msg_text.startswith("!" + cmd_lower):
                handler()
                break
    def handle_generic_command(self):
        message = self.message
        msg_text = message.text.lower()
        for command, handler in self.comandi_generici.items():
            cmd_lower = command.lower()
            if msg_text.startswith(cmd_lower) or msg_text.startswith("/" + cmd_lower) or msg_text.startswith("!" + cmd_lower):
                handler()
                break

    def _get_potion_price(self, size, level):
        """Calculates scaling price: Price = Base + (Level * Factor)"""
        scaling = {
            "Piccola": {"base": 30, "factor": 5},
            "Media":   {"base": 60, "factor": 10},
            "Grande":  {"base": 150, "factor": 25},
            "Enorme":  {"base": 300, "factor": 50},
        }
        config = scaling.get(size, {"base": 100, "factor": 10}) # Fallback
        return config["base"] + (level * config["factor"])

    def handle_negozio_pozioni(self):
        utente = Utente().getUtente(self.chatid)
        lv = utente.livello if utente else 1

        pozioni = [
            {"nome": "Pozione Rigenerante Piccola", "prezzo": self._get_potion_price("Piccola", lv), "effetto": "Rigenera il 25% della Vita"},
            {"nome": "Pozione Rigenerante Media", "prezzo": self._get_potion_price("Media", lv), "effetto": "Rigenera il 50% della Vita"},
            {"nome": "Pozione Rigenerante Grande", "prezzo": self._get_potion_price("Grande", lv), "effetto": "Rigenera il 75% della Vita"},
            {"nome": "Pozione Rigenerante Enorme", "prezzo": self._get_potion_price("Enorme", lv), "effetto": "Rigenera il 100% della Vita"},
            {"nome": "Pozione Aura Piccola", "prezzo": self._get_potion_price("Piccola", lv), "effetto": "Rigenera il 25% dell'Aura"},
            {"nome": "Pozione Aura Grande", "prezzo": self._get_potion_price("Grande", lv), "effetto": "Rigenera il 75% dell'Aura"},
            {"nome": "Pozione Aura Enorme", "prezzo": self._get_potion_price("Enorme", lv), "effetto": "Rigenera il 100% dell'Aura"},
        ]

        # Dynamic Radar Text
        radar = Collezionabili().getItemByUser(self.chatid, "Radar Cercasfere")
        if radar:
            pozioni.append({"nome": "Cariche Radar", "prezzo": 1000, "effetto": "+10 Cariche (Personal 24h, Global 48h Stock)"})
        else:
            pozioni.append({"nome": "Radar Cercasfere", "prezzo": 1500, "effetto": "Ottieni il Radar (Personal 24h, Global 48h Stock)"})

        if not pozioni:
            msg = "Il negozio è vuoto, prova più tardi"
        else:
            msg = f"🛒 **Negozio (Lv. Account {lv})** 🛒\n\n"
            for p in pozioni:
                msg += (
                    f"🧪 {p['nome']}\n"
                    f"💰 Prezzo: {p['prezzo']} fagioli\n"
                    f"✨ Effetto: {p['effetto']}\n\n"
                )

        keyboard = Database().negozioPozioniMarkup(self.chatid)

        self.bot.send_message(
            self.target_id,
            msg,
            reply_markup=keyboard
        )

    def handle_spawn_boss(self):
        # Format: spawn_boss [boss_id]
        args = self.message.text.split()
        boss_id = 1
        if len(args) > 1 and args[1].isdigit():
            boss_id = int(args[1])
        
        session = Database().Session()
        try:
            # Check active raid
            active_raid = session.query(ActiveRaid).filter_by(active=True, chat_id=Tecnologia_GRUPPO).first()
            if active_raid:
                session.close()
                self.bot.reply_to(self.message, "C'è già un Raid attivo!")
                return

            # Fetch Boss Template
            boss = session.get(BossTemplate, boss_id)
            if not boss:
                session.close()
                self.bot.reply_to(self.message, "Boss non trovato.")
                return

            # Create Raid
            raid = ActiveRaid(
                boss_id=boss.id,
                hp_current=boss.hp_max,
                hp_max=boss.hp_max,
                chat_id=Tecnologia_GRUPPO,
                active=True,
                last_log="🐉 Il Boss sta osservando i nemici..."
            )
            session.add(raid)
            session.flush() # Get ID

            # Prepare Message
            msg_text = f"⚠️ **BOSS RAID: {boss.nome}** ⚠️\n"
            msg_text += f"❤️ Vita: {boss.hp_max}/{boss.hp_max}\n"
            msg_text += f"⚔️ Attacco: {boss.atk}\n\n"
            msg_text += f"📜 **Ultima Azione**:\n{raid.last_log}\n\n"
            msg_text += "Preparatevi alla battaglia!"
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"raid_atk_{raid.id}"),
                types.InlineKeyboardButton("✨ Attacco Speciale (60 Aura)", callback_data=f"raid_spc_{raid.id}")
            )

            # Send Message (Image or Text)
            if boss.image_url:
                try:
                    sent_msg = self.bot.send_photo(Tecnologia_GRUPPO, boss.image_url, caption=msg_text, parse_mode='Markdown', reply_markup=markup)
                except:
                    sent_msg = self.bot.send_message(Tecnologia_GRUPPO, msg_text, parse_mode='Markdown', reply_markup=markup)
            else:
                sent_msg = self.bot.send_message(Tecnologia_GRUPPO, msg_text, parse_mode='Markdown', reply_markup=markup)

            # Save Message ID
            raid.message_id = sent_msg.message_id
            session.commit()
            bot.reply_to(self.message, f"✅ Boss {boss.nome} spawnato con successo nel gruppo!")

        except Exception as e:
            print(f"Error spawning boss: {e}")
            bot.reply_to(self.message, f"❌ Errore durante lo spawn: {e}")
        finally:
            session.close()

    def handle_spawn_random(self):
        # !spawn_random
        try:
            # Check active raid
            session = Database().Session()
            active_raid = session.query(ActiveRaid).filter_by(active=True, chat_id=Tecnologia_GRUPPO).first()
            session.close()

            if active_raid:
                self.bot.reply_to(self.message, "⚠️ C'è già un Raid attivo nel gruppo!")
                return

            spawn_random_seasonal_boss(only_boss=False) # Spawns a Mob
            self.bot.reply_to(self.message, "✅ Spawn casuale stagionale attivato!")
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore durante lo spawn casuale: {e}")

    def handle_season_start(self):
        # !season_start [numero] "[nome]" [giorni]
        # Example: !season_start 1 "Saga di Pilaf" 30
        try:
            cmd = "!season_start" if "!" in self.message.text else "/season_start"
            raw_text = self.message.text.replace(f"{cmd} ", "")
            
            # Using regex to properly catch quoted names
            import re
            match = re.search(r'(\d+)\s+"([^"]+)"(?:\s+(\d+))?', raw_text)
            
            if not match:
                bot.reply_to(self.message, f"Usa: `{cmd} [numero] \"[nome]\" [giorni_durata]`\nEsempio: `!season_start 1 \"Saga di Pilaf\" 30`", parse_mode='Markdown')
                return

            num = int(match.group(1))
            nome = match.group(2)
            days = int(match.group(3)) if match.group(3) else None

            session = Database().Session()
            # Deactivate others
            session.query(Season).update({Season.active: False})
            
            new_season = Season(
                numero=num, 
                nome=nome, 
                active=True, 
                data_inizio=datetime.date.today()
            )
            if days:
                new_season.data_fine = datetime.date.today() + datetime.timedelta(days=days)
            
            session.add(new_season)
            session.commit()
            
            msg = f"✅ **STAGIONE ATTIVATA** ✅\n\n📌 **{nome}** (Stagione {num})\n🆔 Database ID: `{new_season.id}`"
            if days:
                msg += f"\n📅 Scadenza: {new_season.data_fine} ({days} giorni)"
            
            msg += f"\n\n💡 I boss con `season_id={new_season.id}` verranno spawnati prioritariamente. Se vuoi usare i boss attuali (ID 1), assicurati di creare la Stagione con ID 1 o aggiorna i boss nel DB."
            
            bot.reply_to(self.message, msg, parse_mode='Markdown')
            session.close()
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore durante l'avvio: {e}")

    def handle_season_addtier(self):
        # /season_addtier [season_id] [lvl] [xp] [free_rew] [prem_rew]
        # Example: /season_addtier 1 1 1000 100_fagioli 1_capsula
        args = self.message.text.split()
        if len(args) < 6:
             bot.reply_to(self.message, "Usa: /season_addtier [s_id] [lvl] [xp] [free] [prem]")
             return
        
        try:
            s_id = int(args[1])
            lvl = int(args[2])
            xp = int(args[3])
            free = args[4]
            prem = args[5]

            session = Database().Session()
            tier = SeasonTier(
                season_id=s_id,
                livello=lvl,
                exp_richiesta=xp,
                ricompensa_free_tipo="GENERIC", # Simplified for now
                ricompensa_free_valore=free,
                ricompensa_premium_tipo="GENERIC",
                ricompensa_premium_valore=prem
            )
            session.add(tier)
            session.commit()
            bot.reply_to(self.message, f"✅ Livello {lvl} aggiunto alla Stagione {s_id}.")
            session.close()
        except Exception as e:
             bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_season_list(self):
        session = Database().Session()
        try:
            seasons = session.query(Season).all()
            if not seasons:
                self.bot.reply_to(self.message, "📭 Nessuna stagione configurata.")
                return

            msg = "🏆 **LISTA STAGIONI** 🏆\n\n"
            for s in seasons:
                status = "✅ ATTIVA" if s.active else "❌ Inattiva"
                msg += f"🆔 `{s.id}` | {status}\n📌 **{s.nome}** (Stagione {s.numero})\n"
                msg += f"📅 Inizio: {s.data_inizio}\n"
                if s.data_fine:
                     msg += f"🏁 Fine: {s.data_fine}\n"
                msg += "\n"

            msg += "Usa `!season_set [ID]` per attivarne una."
            self.bot.reply_to(self.message, msg, parse_mode='Markdown')
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore: {e}")
        finally:
            session.close()

    def handle_season_set(self):
        # !season_set [id] [days]
        try:
            parts = self.message.text.split()
            if len(parts) < 2:
                self.bot.reply_to(self.message, "Usa: `!season_set [ID] [giorni_durata]`")
                return

            target_id = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else None
            
            session = Database().Session()
            
            # 1. Deactivate all
            session.query(Season).update({Season.active: False})
            
            # 2. Activate target
            target = session.query(Season).filter_by(id=target_id).first()
            if not target:
                self.bot.reply_to(self.message, f"❌ Stagione ID {target_id} non trovata.")
                session.close()
                return

            target.active = True
            target.data_inizio = datetime.date.today()
            if days:
                target.data_fine = datetime.date.today() + datetime.timedelta(days=days)
            else:
                target.data_fine = None

            session.commit()
            
            msg = f"✅ Stagione **{target.nome}** (ID: {target_id}) attivata correttamente!"
            if days:
                msg += f"\n📅 Durata: {days} giorni (Termina il {target.data_fine})"
            
            self.bot.reply_to(self.message, msg, parse_mode='Markdown')
            session.close()
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_set_boss_img(self):
        # Usage: Reply to an image with /set_boss_img [boss_id]
        if not self.message.reply_to_message or not self.message.reply_to_message.photo:
            bot.reply_to(self.message, "⚠️ Devi rispondere a un'immagine!")
            return

        boss_id = 1
        args = self.message.text.split()
        if len(args) > 1 and args[1].isdigit():
            boss_id = int(args[1])
            
        file_id = self.message.reply_to_message.photo[-1].file_id
        
        session = Database().Session()
        try:
            boss = session.get(BossTemplate, boss_id)
            if boss:
                boss.image_url = file_id
                session.commit()
                bot.reply_to(self.message, f"✅ Immagine del Boss {boss.nome} (ID {boss_id}) aggiornata!")
            else:
                bot.reply_to(self.message, "❌ Boss non trovato.")
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")
        finally:
            session.close()

    def handle_boss_list(self):
        # !boss_list
        session = Database().Session()
        try:
            active_season = session.query(Season).filter_by(active=True).first()
            if not active_season:
                self.bot.reply_to(self.message, "📭 Nessuna stagione attiva. Usa `!season_list` per attivarne una.")
                return

            # Filter by matching saga name
            bosses = session.query(BossTemplate).filter(BossTemplate.saga == active_season.nome).all()
            
            # Fallback to season_id
            if not bosses:
                bosses = session.query(BossTemplate).filter_by(season_id=active_season.id).all()
            if not bosses:
                self.bot.reply_to(self.message, f"🎴 Nessun boss trovato per la stagione {active_season.nome}.")
                return

            msg = f"👾 **BOSS DELLA STAGIONE: {active_season.nome}** 👾\n\n"
            for b in bosses:
                status_img = "🖼️" if b.image_url else "📝 (No Img)"
                msg += f"🆔 `{b.id}` | {status_img} **{b.nome}**\n"
            
            msg += "\n💡 Per impostare un'immagine, rispondi a una foto con `/set_boss_img [ID]`"
            self.bot.reply_to(self.message, msg, parse_mode='Markdown')
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore: {e}")
        finally:
            session.close()

    def handle_kill_raid(self):
        # !kill_raid
        session = Database().Session()
        try:
            raid = session.query(ActiveRaid).filter_by(active=True, chat_id=Tecnologia_GRUPPO).first()
            if not raid:
                self.bot.reply_to(self.message, "❌ Non c'è nessun Raid attivo nel gruppo.")
                return

            boss = session.get(BossTemplate, raid.boss_id)
            
            # 1. Kill the Boss
            raid.active = False
            raid.hp_current = 0
            
            # 2. Loot Distribution
            participants = session.query(RaidParticipant).filter_by(raid_id=raid.id).all()
            total_raid_dmg = sum(p.dmg_total for p in participants)
            
            loot_msg = f"💀 **{boss.nome} è stato ELIMINATO dall'Admin!** 💀\n\n💰 Ricompense (proporzionali ai danni fatti):\n"
            
            if total_raid_dmg > 0:
                for p in participants:
                    share = p.dmg_total / total_raid_dmg
                    xp_gain = int(boss.xp_reward_total * share)
                    pts_gain = int(boss.points_reward_total * share)
                    
                    p_user = session.query(Utente).filter_by(id_telegram=p.user_id).first()
                    if p_user:
                        p_user.exp += xp_gain
                        p_user.points += pts_gain
                        loot_msg += f"👤 {p_user.nome}: {p.dmg_total} dmg -> {xp_gain} XP, {pts_gain} {PointsName}\n"
                        
                        # Add Season EXP
                        active_season = session.query(Season).filter_by(active=True).first()
                        if active_season:
                            prog = session.query(UserSeasonProgress).filter_by(user_id=p.user_id, season_id=active_season.id).first()
                            if not prog:
                                prog = UserSeasonProgress(user_id=p.user_id, season_id=active_season.id, season_exp=0, season_level=1)
                                session.add(prog)
                                session.flush()
                            prog.season_exp += xp_gain
                
                # Loot message will be sent after the visual UI update below
                pass
            else:
                bot.send_message(raid.chat_id, f"💀 Il Boss {boss.nome} è stato rimosso dall'Admin. Nessun premio assegnato (0 danni totali).")

            # 3. Update Group UI (Delete Old, Send Brand New Final Message)
            try:
                bot.delete_message(raid.chat_id, raid.message_id)
            except: pass

            blocks = 10
            bar = "⬜️" * blocks
            msg_text = f"⚠️ **BOSS RAID: {boss.nome}** ⚠️\n"
            msg_text += f"❤️ Vita: [{bar}] 0/{raid.hp_max}\n"
            msg_text += f"\n❌ **SCONFITTO (Intervento Admin)**"
            
            try:
                if boss.image_url:
                    try:
                        bot.send_photo(raid.chat_id, boss.image_url, caption=msg_text, parse_mode='Markdown')
                    except:
                        bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown')
                else:
                    bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown')
            except: pass

            # 4. Send Loot Message LAST (if any)
            if total_raid_dmg > 0 and 'loot_msg' in locals():
                bot.send_message(raid.chat_id, loot_msg)

            session.commit()
            bot.reply_to(self.message, "✅ Raid terminato con successo!")

        except Exception as e:
            print(f"Error killing raid: {e}")
            self.bot.reply_to(self.message, f"❌ Errore tecnico: {e}")
        finally:
            session.close()

    def handle_add_boss(self):
        # /add_boss [HP] [ATK] [XP] [POINTS] [NOME...]
        # Example: /add_boss 5000 150 1000 500 Cell Perfetto
        args = self.message.text.split()
        if len(args) < 6:
            bot.reply_to(self.message, "Usa: `/add_boss [HP] [ATK] [XP] [POINTS] [NOME]`", parse_mode='Markdown')
            return
        
        try:
            hp = int(args[1])
            atk = int(args[2])
            xp = int(args[3])
            points = int(args[4])
            nome = " ".join(args[5:]) # Everything else is the name
            
            session = Database().Session()
            new_boss = BossTemplate(
                nome=nome,
                hp_max=hp,
                atk=atk,
                xp_reward_total=xp,
                points_reward_total=points,
                image_url=None, # Set later with /set_boss_img
                is_boss=True
            )
            session.add(new_boss)
            session.commit()
            
            bot.reply_to(self.message, f"✅ Boss **{nome}** aggiunto con ID: **{new_boss.id}**\n\nOra rispondi a una sua foto con `/set_boss_img {new_boss.id}` per completarlo!")
            session.close()
            
        except ValueError:
            bot.reply_to(self.message, "⚠️ I primi 4 valori devono essere numeri!")
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_add_saga_boss(self):
        # /add_saga_boss [LV] [SAGA] [NOME...]
        args = self.message.text.split()
        if len(args) < 4:
            bot.reply_to(self.message, "Usa: `/add_saga_boss [LV] [SAGA] [NOME]`", parse_mode='Markdown')
            return
        
        try:
            lv = int(args[1])
            saga = args[2].replace("_", " ") 
            nome = " ".join(args[3:])
            
            session = Database().Session()
            
            # Auto-detect elite from name
            is_elite = "(elite)" in nome.lower()
            
            new_boss = BossTemplate(
                nome=nome,
                saga=saga,
                livello=lv,
                is_boss=True,
                is_elite=is_elite
            )
            new_boss.calculate_and_sync_stats() # Auto calc stats
            session.add(new_boss)
            session.commit()
            
            bot.reply_to(self.message, f"✅ Boss **{nome}** (Livello {lv}) aggiunto alla saga **{saga}** con ID: **{new_boss.id}**")
            session.close()
            
        except ValueError:
            bot.reply_to(self.message, "⚠️ I primi 4 valori devono essere numeri!")
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_add_mob(self):
        # /add_mob [LV] [SAGA] [NOME...]
        args = self.message.text.split()
        if len(args) < 4:
            bot.reply_to(self.message, "Usa: `/add_mob [LV] [SAGA] [NOME]`", parse_mode='Markdown')
            return
        
        try:
            lv = int(args[1])
            saga = args[2].replace("_", " ") 
            nome = " ".join(args[3:])
            
            session = Database().Session()
            
            # Auto-detect elite from name
            is_elite = "(elite)" in nome.lower()
            
            new_boss = BossTemplate(
                nome=nome,
                saga=saga,
                livello=lv,
                is_boss=False, # It's a Mob
                is_elite=is_elite
            )
            new_boss.calculate_and_sync_stats() # Auto calc stats
            session.add(new_boss)
            session.commit()
            
            bot.reply_to(self.message, f"✅ Mob **{nome}** (Livello {lv}) aggiunto alla saga **{saga}** con ID: **{new_boss.id}**")
            session.close()
        except ValueError:
             bot.reply_to(self.message, "⚠️ Il livello deve essere un numero!")
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_add_mob_adv(self):
        # /add_mob_adv [LV] [HP_B] [HP_P] [ATK_B] [ATK_P] [XP_B] [XP_P] [PTS_B] [PTS_P] [SAGA] [NOME...]
        args = self.message.text.split()
        if len(args) < 12:
            bot.reply_to(self.message, "Usa: `/add_mob_adv [LV] [HP_B] [HP_P] [ATK_B] [ATK_P] [XP_B] [XP_P] [PTS_B] [PTS_P] [SAGA] [NOME]`", parse_mode='Markdown')
            return
        try:
            lv = int(args[1]); hp_b = int(args[2]); hp_p = int(args[3])
            atk_b = int(args[4]); atk_p = int(args[5])
            xp_b = int(args[6]); xp_p = int(args[7])
            pts_b = int(args[8]); pts_p = int(args[9])
            saga = args[10].replace("_", " ")
            nome = " ".join(args[11:])

            session = Database().Session()
            new_mob = BossTemplate(
                nome=nome, saga=saga, livello=lv,
                hp_base=hp_b, hp_per_lv=hp_p,
                atk_base=atk_b, atk_per_lv=atk_p,
                xp_base=xp_b, xp_per_lv=xp_p,
                points_base=pts_b, points_per_lv=pts_p,
                is_boss=False
            )
            new_mob.calculate_and_sync_stats()
            session.add(new_mob)
            session.commit()
            bot.reply_to(self.message, f"✅ Mob Avanzato **{nome}** (Livello {lv}) creato con successo!")
            session.close()
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_set_boss_flag(self):
        # /set_boss_flag [ID] [1/0]
        args = self.message.text.split()
        if len(args) < 3:
            bot.reply_to(self.message, "Usa: `/set_boss_flag [ID] [1 per Boss, 0 per Mob]`")
            return
        
        try:
            b_id = int(args[1])
            val = int(args[2]) == 1
            
            session = Database().Session()
            boss = session.get(BossTemplate, b_id)
            if boss:
                boss.is_boss = val
                session.commit()
                label = "BOSS" if val else "MOB"
                bot.reply_to(self.message, f"✅ Nemico {boss.nome} (ID {b_id}) impostato come **{label}**.")
            else:
                bot.reply_to(self.message, "❌ Nemico non trovato.")
            session.close()
        except:
            bot.reply_to(self.message, "❌ Errore nei parametri.")

    def handle_set_lv(self):
        # /set_lv [ID] [LV]
        args = self.message.text.split()
        if len(args) < 3:
            bot.reply_to(self.message, "Usa: `/set_lv [ID] [Livello]`")
            return
        try:
            b_id = int(args[1])
            new_lv = int(args[2])
            session = Database().Session()
            boss = session.get(BossTemplate, b_id)
            if boss:
                boss.livello = new_lv
                boss.calculate_and_sync_stats()
                session.commit()
                bot.reply_to(self.message, f"📈 **{boss.nome}** aggiornato al Livello **{new_lv}**!\n❤️ HP: {boss.hp_max} | ⚔️ ATK: {boss.atk} | ✨ XP: {boss.xp_reward_total} | 💰 {PointsName}: {boss.points_reward_total}")
            else:
                bot.reply_to(self.message, "❌ Nemico non trovato.")
            session.close()
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_edit_boss(self):
        # /edit_boss [ID] [HP] [ATK] [XP] [POINTS]
        args = self.message.text.split()
        if len(args) < 4:
            bot.reply_to(self.message, "Usa: `/edit_boss [ID] [Nuovi HP] [Nuovo ATK] [XP (opz)] [PUNTI (opz)]`", parse_mode='Markdown')
            return
        
        try:
            b_id = int(args[1])
            new_hp = int(args[2])
            new_atk = int(args[3])
            new_xp = int(args[4]) if len(args) > 4 else None
            new_pts = int(args[5]) if len(args) > 5 else None
            
            session = Database().Session()
            boss = session.get(BossTemplate, b_id)
            if boss:
                boss.hp_max = new_hp
                boss.atk = new_atk
                if new_xp is not None: boss.xp_reward_total = new_xp
                if new_pts is not None: boss.points_reward_total = new_pts
                
                session.commit()
                
                msg = f"✅ Nemico **{boss.nome}** (ID {b_id}) aggiornato!\n❤️ Nuovi HP: {new_hp}\n⚔️ Nuovo ATK: {new_atk}"
                if new_xp is not None: msg += f"\n✨ Nuovo Premio XP: {new_xp}"
                if new_pts is not None: msg += f"\n💰 Nuovo Premio {PointsName}: {new_pts}"
                
                bot.reply_to(self.message, msg, parse_mode='Markdown')
            else:
                bot.reply_to(self.message, "❌ Nemico non trovato.")
            session.close()
        except ValueError:
            bot.reply_to(self.message, "⚠️ Tutti i valori devono essere numeri!")
        except Exception as e:
            bot.reply_to(self.message, f"❌ Errore: {e}")



    def handle_buy_potion(self):
        import datetime
        
        # 0. Identify Potion
        tipo_pozione = None
        for tipo in ["Piccola", "Media", "Grande", "Enorme"]:
            if tipo in self.message.text:
                tipo_pozione = tipo
                break
        
        if not tipo_pozione:
            self.bot.reply_to(self.message, "Tipo di pozione non riconosciuto.")
            return

        utente = Utente().getUtente(self.chatid)
        lv = utente.livello if utente else 1
        costo = self._get_potion_price(tipo_pozione, lv)
        
        # Potion stats (Vita/Aura restored)
        pozioni_stats = {
            "Piccola": 100, "Media": 200, "Grande": 500, "Enorme": 1000
        }
        vita_extra = pozioni_stats[tipo_pozione]
        
        # 1. Check Global Daily Stock (id_utente = 0 for shared stock)
        session = Database().Session()
        oggi = datetime.date.today()
        # Message text IS the potion name e.g. "🧪 Pozione Rigenerante Piccola"
        full_potion_name = self.message.text.replace("🧪 ", "") # Remove emoji if present
        
        # Use id_utente=0 for GLOBAL shared stock
        daily_shop = session.query(DailyShop).filter_by(id_utente=0, data=oggi, tipo_pozione=full_potion_name).first()
        
        if not daily_shop:
            # Initialize Global Stock (10 for everyone combined)
            daily_shop = DailyShop(id_utente=0, data=oggi, tipo_pozione=full_potion_name, pozioni_rimanenti=10)
            session.add(daily_shop)
            session.commit()
            
        if daily_shop.pozioni_rimanenti <= 0:
            self.bot.reply_to(self.message, f"⛔️ Le scorte di {full_potion_name} sono esaurite per oggi!", reply_markup=Database().negozioPozioniMarkup(self.chatid))
            session.close()
            return
            
        # 2. Check Funds
        if utente.points < costo:
            self.bot.reply_to(self.message, f"❌ Non hai abbastanza {PointsName}! Ti servono {costo} fagioli.", reply_markup=Database().negozioPozioniMarkup(self.chatid))
            session.close()
            return

        # 3. Execute Purchase
        try:
            # Deduct points and save to database
            new_points = utente.points - costo
            Database().update_user(self.chatid, {'points': new_points})
            
            # Update local object for the final info display
            utente.points = new_points
            
            # Add to Inventory
            # Format: 'Pozione {Type} {Size}'
            if "Rigenerante" in self.message.text:
                category = "Rigenerante"
            elif "Aura" in self.message.text:
                category = "Aura"
            else:
                category = "Rigenerante" # Fallback

            nome_oggetto = f"Pozione {category} {tipo_pozione}"
            
            # Use local session to create collectible to avoid locks
            new_item = Collezionabili(
                id_telegram=str(self.chatid),
                oggetto=nome_oggetto,
                quantita=1,
                data_acquisizione=datetime.datetime.now()
            )
            session.add(new_item)
            
            # Decrement Stock
            daily_shop.pozioni_rimanenti -= 1
            session.commit()
            
            # Confirm
            msg = f"✅ Hai acquistato una {nome_oggetto}!\n"
            msg += f"🎒 È stata aggiunta al tuo inventario.\n"
            msg += f"💰 Costo: {costo}\n"
            msg += f"📦 Scorte globali rimanenti: {daily_shop.pozioni_rimanenti}"
            
            self.bot.reply_to(self.message, msg + "\n\n" + Utente().infoUser(utente), reply_markup=Database().negozioPozioniMarkup(self.chatid))
            
        except Exception as e:
            session.rollback()
            print(f"Errore acquisto pozione: {e}")
            self.bot.reply_to(self.message, "Errore durante l'acquisto, contatta un admin.")
        finally:
            session.close()

    def handle_buy_radar(self):
        
        session = Database().Session()
        now = datetime.datetime.now()
        oggi = datetime.date.today()
        
        try:
            # 0. Fetch User within this session
            utente = session.query(Utente).filter_by(id_telegram=self.chatid).first()
            if not utente:
                self.bot.reply_to(self.message, "Utente non trovato.")
                return

            # Fetch the actual object (Radar Cercasfere) for current user within this session
            radar = session.query(Collezionabili).filter_by(id_telegram=str(self.chatid), oggetto="Radar Cercasfere", data_utilizzo=None).first()
            
            # --- 1. Personal Cooldown (24h) ---
            if utente.last_radar_purchase:
                diff = now - utente.last_radar_purchase
                if diff.total_seconds() < 24 * 3600:
                    hours_left = int(24 - (diff.total_seconds() / 3600))
                    self.bot.reply_to(self.message, f"⏳ Sei in cooldown personale! Potrai acquistare di nuovo tra circa {hours_left} ore.")
                    return

            # --- 2. Determine Item Type ---
            if not radar:
                costo = 1500
                full_name = "Radar Cercasfere"
                charges_to_add = 5
            else:
                costo = 1000
                full_name = "Cariche Radar"
                charges_to_add = 10

            # --- 3. Global Stock Check (2-Day Cycle / 48h) ---
            daily = session.query(DailyShop).filter_by(id_utente=0, tipo_pozione=full_name).order_by(DailyShop.data.desc()).first()
            
            if not daily or (oggi - daily.data).days >= 2:
                daily = DailyShop(id_utente=0, data=oggi, tipo_pozione=full_name, pozioni_rimanenti=10)
                session.add(daily)
                session.flush()

            if daily.pozioni_rimanenti <= 0:
                days_since_start = (oggi - daily.data).days
                days_left = 2 - days_since_start
                self.bot.reply_to(self.message, f"⛔️ Le scorte globali di {full_name} sono esaurite!\nTorna tra circa {days_left} giorno/i per il rifornimento.")
                return

            # --- 4. Funds Check ---
            if utente.points < costo:
                self.bot.reply_to(self.message, f"❌ Non hai abbastanza {PointsName}! Ti servono {costo} fagioli.")
                return

            # --- 5. Finalize Purchase ---
            # Update user directly on the object fetched with the session
            utente.points -= costo
            utente.last_radar_purchase = now
            
            if not radar:
                # First purchase: Create new collectible
                # We use the internal logic but bypass the separate session if possible
                # However, CreateCollezionabile creates its own session. 
                # Let's do it manually here to stay in the same session.
                new_item = Collezionabili(
                    id_telegram=str(self.chatid),
                    oggetto="Radar Cercasfere",
                    quantita=1,
                    cariche=5,
                    data_acquisizione=datetime.datetime.now()
                )
                session.add(new_item)
                msg = f"📟 **Radar Cercasfere** ottenuto con **5 cariche**!"
            else:
                # Refill: Update existing object
                radar.cariche += 10
                msg = f"🔋 **Ricarica Effettuata**! +10 cariche (Totale: {radar.cariche})."
            
            daily.pozioni_rimanenti -= 1
            session.commit()
            
            final_msg = f"✅ {msg}\n💰 Costo: {costo} fagioli\n📦 Scorte globali rimanenti: {daily.pozioni_rimanenti}\n⏳ Prossimo acquisto disponibile tra 24 ore."
            self.bot.reply_to(self.message, final_msg, parse_mode='Markdown', reply_markup=Database().negozioPozioniMarkup(self.chatid))

        except Exception as e:
            session.rollback()
            print(f"Errore gestione radar: {e}")
            self.bot.reply_to(self.message, "Errore tecnico durante l'operazione.")
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

        # Growth Button
        can_grow, _ = utente.verifica_crescita()
        if can_grow:
            markup.add(types.InlineKeyboardButton("🌟 CRESCI (Disponibile!)", callback_data="trigger_growth"))

        self.bot.send_message(self.target_id, msg, reply_markup=markup)

    def handle_back(self):
        utente = Utente().getUtente(self.chatid)
        self.bot.reply_to(self.message, "Torna al menu principale", reply_markup=Database().startMarkup(utente))

    def handle_inventario(self):
        inventario = Collezionabili().getInventarioUtente(self.chatid)
        msg = "🎒 Inventario 🎒\n\n"
        if inventario:
            for oggetto in inventario:
                if oggetto.oggetto not in ['TNT']:
                    if "Sfera del Drago" in oggetto.oggetto:
                        icon = "🐉"
                    elif oggetto.oggetto == "Nitro":
                        icon = "🚀"
                    elif oggetto.oggetto == "Cassa":
                        icon = "📦"
                    elif "Pozione" in oggetto.oggetto:
                        icon = "🧪"
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
            has_usable_items = any(o.oggetto in ['Nitro', 'Cassa', 'TNT'] or "Pozione" in o.oggetto for o in inventario)
            if has_usable_items:
                reply_markup = types.InlineKeyboardMarkup()
                reply_markup.add(types.InlineKeyboardButton("🎁 Usa Oggetto", callback_data="use_item_list"))
        
        self.bot.reply_to(self.message, msg, reply_markup=reply_markup if reply_markup else keyboard)
        # If we sent inline keyboard, we still need to make sure the user has the reply keyboard
        if reply_markup:
            self.bot.send_message(self.target_id, "Scegli cosa fare dal menu sopra.", reply_markup=keyboard)
        
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
                                    self.bot.send_sticker(self.target_id, sticker)
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
            
            self.bot.send_message(self.target_id, "🔮 Hai riunito le Sfere del Drago! 🔮", reply_markup=markup)
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

    def handle_status(self):
        utente = Utente().getUtente(self.chatid)
        msg, img_url = Utente().get_visual_status(utente)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 ALLOCAZIONE STATISTICHE", callback_data="stat_menu"))
        
        if img_url:
            try:
                self.bot.send_photo(self.target_id, img_url, caption=msg, parse_mode='Markdown', reply_markup=markup)
            except Exception as e:
                print(f"Error sending photo in handle_status: {e}")
                self.bot.send_message(self.target_id, msg, parse_mode='Markdown', reply_markup=markup)
        else:
            self.bot.send_message(self.target_id, msg, parse_mode='Markdown', reply_markup=markup)

    def handle_stats(self):
        """Alias for handle_status."""
        self.handle_status()

    
    
    def handle_set_saga_active_admin(self):
        # /set_saga_active "Saga di Freezer"
        # Usage: Force set active saga logic for testing
        pass

    def handle_set_saga_active(self, call, cat_id):
        user_id = call.from_user.id
        session = Database().Session()
        try:
            import json
            
            category = session.get(AchievementCategory, cat_id)
            if not category:
                self.bot.answer_callback_query(call.id, "Saga non trovata.")
                return

            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not utente: return

            # Validation (Already done in UI, but double check)
            # ... (threshold check logic could be repeated here for security)
            
            # Update misc_data
            misc = {}
            if utente.misc_data:
                try: misc = json.loads(utente.misc_data)
                except: pass
            
            misc["active_saga_override"] = category.nome
            utente.misc_data = json.dumps(misc)
            session.commit()
            
            self.bot.answer_callback_query(call.id, f"Saga impostata: {category.nome}")
            
            # Refresh formatting? Or just alert.
            # Let's refresh to show the "📍" icon update
            self.handle_saga(call)
            
        except Exception as e:
            print(f"Error set active: {e}")
            self.bot.answer_callback_query(call.id, "Errore durante il cambio saga.")
        finally:
            session.close()

    def handle_saga(self, call=None):
        # /saga command - Show categories
        # Supports call=CallbackQuery for "Back" button to edit message
        user_id = self.chatid
        if call:
            user_id = call.from_user.id
            
        session = Database().Session()
        try:
            import json

            categories = session.query(AchievementCategory).all() # Should order by something? ID is chronological usually
            if not categories:
                if call:
                    self.bot.answer_callback_query(call.id, "📭 Nessun obiettivo saga configurato.")
                else:
                    self.bot.reply_to(self.message, "📭 Nessun obiettivo saga configurato.")
                return
            
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not utente: return # Should not happen

            # 1. Determine User Saga State
            # Map Levels to Sagas (Approximate)
            # 1-19: Earth Sagas (1, 2, 3)
            # 20-25: Saiyan (4)
            # 26-35: Freezer (5)
            # 36-39: Garlic (6)
            # 40-49: Androids (7)
            # 50-54: 4 Galaxies (8)
            # 55-59: High School (9)
            # 60-70: Majin Bu (10)
            
            # Sagas ID map (Assuming add_all_sagas inserted them sequentially or check via Name)
            # Better to use name-based mapping or dynamic check
            
            # Simple Logic: Saga is unlocked if (User Lv >= Saga Min Lv) OR (User Lv is High enough to have passed it)
            # We can hardcode the threshold for now as defined in Plan
            saga_thresholds = {
                "Saga di Pilaf": 1,
                "Saga del 21° Torneo Tenkaichi": 5,
                "Saga del Red Ribbon": 10,
                "Saga di Karin": 15,
                "Saga del 22° Torneo Tenkaichi": 20,
                "Saga del Grande Mago Piccolo": 25,
                "Saga del 23° Torneo Tenkaichi": 30,
                "Saga dei Saiyan": 35,
                "Saga di Freezer": 45,
                "Saga di Garlic Jr.": 50,
                "Saga degli Androidi": 55,
                "Saga di Cell": 60,
                "Saga del Torneo delle Quattro Galassie": 65,
                "Saga della High School": 70,
                "Saga di Majin Bu": 75,
                # GT Sagas
                "Saga delle Sfere Nere": 85,
                "Saga di Baby": 90,
                "Saga di Super 17": 95,
                "Saga dei Draghi Malvagi": 100,
                # DBS Sagas
                "Saga della Battaglia degli Dei": 105,
                "Saga della Resurrezione di 'F'": 110,
                "Saga dell'Universo 6": 115,
                "Saga di Trunks del Futuro": 120,
                "Saga della Sopravvivenza dell'Universo": 125,
                "Saga di Broly": 130,
                "Saga dei Prigionieri della Pattuglia Galattica": 135,
                "Saga di Granolah, il sopravvissuto": 140,
                "Saga dei Supereroi": 145
            }
            
            # Get User Active Saga Override
            active_override = None
            if utente.misc_data:
                try:
                    misc = json.loads(utente.misc_data)
                    active_override = misc.get("active_saga_override") 
                except: pass

            # Sort categories by threshold to ensure correct display order
            categories = sorted(categories, key=lambda c: saga_thresholds.get(c.nome, 999))

            msg = "🏆 **I TUOI OBIETTIVI SAGA**\n\n"
            msg += f"Livello Attuale: {utente.livello}\n"
            if active_override:
                msg += f"🔖 **Saga Selezionata**: {active_override}\n"
            msg += "\nSeleziona una saga per vedere gli obiettivi o impostarla come attiva:\n"
            
            markup = types.InlineKeyboardMarkup()
            
            # Filter Sagas
            first_locked_shown = False
            for cat in categories:
                threshold = saga_thresholds.get(cat.nome, 999)
                is_unlocked = utente.livello >= threshold
                
                status_icon = "🔒"
                if is_unlocked:
                    status_icon = "✅"
                    if active_override == cat.nome:
                         status_icon = "📍" # Current Selected
                
                # Show only unlocked or next one?
                # Show all but locked ones have "locked" behavior or just symbol
                # User wants to see them but maybe not interact deeply if locked? 
                # Let's show all but mark them.

                if is_unlocked:
                    markup.add(types.InlineKeyboardButton(f"{status_icon} {cat.nome}", callback_data=f"saga_detail_{cat.id}"))
                elif not first_locked_shown:
                    # Show the first locked saga as Preview
                    markup.add(types.InlineKeyboardButton(f"🔒 {cat.nome} (Anteprima)", callback_data=f"saga_detail_{cat.id}"))
                    first_locked_shown = True
            
            if len(markup.keyboard) == 0:
                 markup.add(types.InlineKeyboardButton("🔒 Nessuna Saga Sbloccata (Livello troppo basso)", callback_data="none"))

            if call:
                 self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
            else:
                 self.bot.reply_to(self.message, msg, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in handle_saga: {e}")
            self.bot.reply_to(self.message, "Errore caricamento saghe.")
        finally:
            session.close()

    def handle_saga_detail(self, call, cat_id):
        # Handles the "inner" view of a saga
        # Options: "View Objectives" | "Set as Active"
        session = Database().Session()
        try:
            category = session.get(AchievementCategory, cat_id)
            if not category: return
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📜 Vedi Obiettivi", callback_data=f"saga_cat_{cat_id}"))
            
            # --- Activation Protection ---
            # 1. Check Threshold again
            user_id = call.from_user.id
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            
            # Hardcoded Thresholds re-import or redefine (Simplified: fetch from somewhere or re-define)
            # Re-defining locally for safety and speed (Optimally should be in a shared config/method)
            saga_thresholds = {
                "Saga di Pilaf": 1,
                "Saga del 21° Torneo Tenkaichi": 5,
                "Saga del Red Ribbon": 10,
                "Saga di Karin": 15,
                "Saga del 22° Torneo Tenkaichi": 20,
                "Saga del Grande Mago Piccolo": 25,
                "Saga del 23° Torneo Tenkaichi": 30,
                "Saga dei Saiyan": 35,
                "Saga di Freezer": 45,
                "Saga di Garlic Jr.": 50,
                "Saga degli Androidi": 55,
                "Saga di Cell": 60,
                "Saga del Torneo delle Quattro Galassie": 65,
                "Saga della High School": 70,
                "Saga di Majin Bu": 75,
                # GT Sagas
                "Saga delle Sfere Nere": 85,
                "Saga di Baby": 90,
                "Saga di Super 17": 95,
                "Saga dei Draghi Malvagi": 100,
                # DBS Sagas
                "Saga della Battaglia degli Dei": 105,
                "Saga della Resurrezione di 'F'": 110,
                "Saga dell'Universo 6": 115,
                "Saga di Trunks del Futuro": 120,
                "Saga della Sopravvivenza dell'Universo": 125,
                "Saga di Broly": 130,
                "Saga dei Prigionieri della Pattuglia Galattica": 135,
                "Saga di Granolah, il sopravvissuto": 140,
                "Saga dei Supereroi": 145
            }
            
            threshold = saga_thresholds.get(category.nome, 999)
            is_unlocked = utente.livello >= threshold
            is_admin = Utente().isAdmin(utente)
            
            # Show "Set Active" ONLY if Admin (Users follow auto-progression)
            if is_admin:
                markup.add(types.InlineKeyboardButton("📌 Imposta come Saga Attiva (Admin)", callback_data=f"saga_set_active_{cat_id}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="saga_back"))
            
            msg = f"**{category.nome}**\n\n{category.descrizione}\n\nCosa vuoi fare?"
            self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
            
            
        except Exception as e:
            print(e)
            pass
        finally:
            session.close()

    def handle_choose_character_v2(self, call=None):
        """
        Shows the character selection menu.
        Filters characters based on User's Collection (UserCharacter table).
        """
        session = Database().Session()
        try:
            user_id = self.chatid
            if call:
                user_id = call.from_user.id

            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not utente:
                return

            # Join Livello with UserCharacter to get only unlocked characters
            unlocked_livelli = session.query(Livello).join(
                UserCharacter, UserCharacter.character_name == Livello.nome
            ).filter(UserCharacter.user_id == user_id).order_by(Livello.livello).all()
            
            # Fallback: If for some reason collection is empty (shouldn't be), show Level 1 starters
            if not unlocked_livelli:
                unlocked_livelli = session.query(Livello).filter(Livello.is_starter == True).all()

            markup = types.InlineKeyboardMarkup()
            row = []
            
            for lv in unlocked_livelli:
                btn_text = f"{lv.nome}"
                if utente.livello_selezionato == lv.id:
                    btn_text = f"✅ {lv.nome}"
                    
                button = types.InlineKeyboardButton(btn_text, callback_data=f"set_char_{lv.id}")
                row.append(button)
                
                if len(row) == 2:
                    markup.row(*row)
                    row = []

            if row:
                markup.row(*row)
                
            markup.row(types.InlineKeyboardButton("⬅️ Indietro", callback_data="main_menu"))

            msg_text = "👤 **Scegli il tuo Personaggio**\nSeleziona il guerriero con cui vuoi combattere:"
            
            if call:
                self.bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
            else:
                self.bot.reply_to(self.message, msg_text, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error handle_choose_character_v2: {e}")
            if call:
                self.bot.answer_callback_query(call.id, "Errore caricamento personaggi.")
            else:
                self.bot.reply_to(self.message, "Errore nel caricamento dei personaggi.")
        finally:
            session.close()

    def handle_pass(self):
        SagaPassHandler(self.bot, self.message, self.chatid).handle_pass()

    def handle_kamehouse(self):
        """Interactive Kame House menu with recovery info and sub-menus."""
        session = Database().Session()
        try:
            utente = session.query(Utente).filter_by(id_telegram=self.chatid).first()
            if not utente:
                self.bot.reply_to(self.message, "Utente non trovato.")
                return

            img_kame = "https://mir-s3-cdn-cf.behance.net/project_modules/1400/dd0c0a69578469.5b864c07b31c9.jpg"
            
            max_vita = 50 + ((utente.stat_vita or 0) * 10)
            max_aura = 60 + ((utente.stat_aura or 0) * 5)
            
            if not utente.is_resting:
                utente.is_resting = True
                session.commit()
                msg = "🐢 **BENVENUTO ALLA KAME HOUSE!** 🐢\n\n"
                msg += "Maestro Muten ti ha accolto! Qui puoi riposare e recuperare le tue forze.\n\n"
                msg += f"❤️ **Vita**: {utente.vita}/{max_vita}\n"
                msg += f"💙 **Aura**: {utente.aura}/{max_aura}\n\n"
                msg += "⏱ _Recupererai 2 HP e 2 Aura ogni minuto._"
            else:
                msg = "🏠 **SEI NELLA KAME HOUSE** 🏠\n\n"
                msg += "Ti stai riposando beatamente...\n\n"
                msg += f"❤️ **Vita**: {utente.vita}/{max_vita}\n"
                msg += f"💙 **Aura**: {utente.aura}/{max_aura}\n\n"
                msg += "😴 _Torna tra poco per vedere i progressi!_"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🤝 Scambia Sfere", callback_data="trade_start"))
            markup.add(types.InlineKeyboardButton("🚪 Esci dalla Kame House", callback_data="leave_kamehouse"))
            
            try:
                self.bot.send_photo(self.target_id, img_kame, caption=msg, parse_mode='Markdown', reply_markup=markup)
            except Exception as e_img:
                print(f"Error sending Kame House photo: {e_img}")
                self.bot.send_message(self.target_id, msg, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in handle_kamehouse: {e}")
            self.bot.reply_to(self.message, "Errore durante l'accesso alla Kame House.")
        finally:
            session.close()

    def handle_scambia_sfera(self):
        """Directly gifts a specific Dragon Ball to another user via command."""
        session = Database().Session()
        try:
            # Command format: /gift @user Sfera 1
            text = self.message.text
            parts = text.split()
            if len(parts) < 3:
                self.bot.reply_to(self.message, "⚠️ Uso: `/scambia_sfera @username NomeSfera`\n(es: `/scambia_sfera @lupin Shenron 1`)")
                return

            target_username = parts[1]
            sphere_query = " ".join(parts[2:])

            # Find target
            if not target_username.startswith("@"): target_username = "@" + target_username
            target = session.query(Utente).filter(Utente.username.ilike(target_username)).first()
            if not target:
                self.bot.reply_to(self.message, f"❌ Utente {target_username} non trovato.")
                return

            # Find sphere in sender inventory
            sphere_item = session.query(Collezionabili).filter(
                Collezionabili.id_telegram == str(self.chatid),
                Collezionabili.oggetto.ilike(f"%{sphere_query}%"),
                Collezionabili.data_utilizzo == None
            ).first()

            if not sphere_item:
                self.bot.reply_to(self.message, f"❌ Non possiedi '{sphere_query}'.")
                return

            # Transfer
            sphere_item.id_telegram = str(target.id_telegram)
            session.commit()
            self.bot.reply_to(self.message, f"🎁 Hai regalato **{sphere_item.oggetto}** a {target.username}!")
            try:
                self.bot.send_message(target.id_telegram, f"🎁 Hai ricevuto **{sphere_item.oggetto}** da {self.message.from_user.first_name}!")
            except: pass

        except Exception as e:
            print(f"Error in handle_scambia_sfera: {e}")
            self.bot.reply_to(self.message, "❌ Errore durante il regalo.")
        finally:
            session.close()

    def handle_scambia(self, target_username=None):
        """Interactive trading: prompts for sphere selection if users are in Kame House."""
        session = Database().Session()
        try:
            utente_sender = session.query(Utente).filter_by(id_telegram=self.chatid).first()
            if not utente_sender or not utente_sender.is_resting:
                self.bot.reply_to(self.message, "⚠️ Puoi scambiare sfere solo se sei all'interno della **Kame House**!", parse_mode='Markdown')
                return

            # Identify target
            target_user = None
            if self.message.reply_to_message:
                target_user = session.query(Utente).filter_by(id_telegram=self.message.reply_to_message.from_user.id).first()
            elif target_username:
                if not target_username.startswith("@"):
                    target_username = "@" + target_username
                target_user = session.query(Utente).filter(Utente.username.ilike(target_username)).first()
            
            if not target_user:
                if not target_username:
                    msg = self.bot.reply_to(self.message, "🤝 Con chi vuoi scambiare? Rispondi a un suo messaggio o scrivi il suo @username:")
                    self.bot.register_next_step_handler(msg, self._handle_scambia_step2)
                    return
                else:
                    self.bot.reply_to(self.message, f"❌ Utente {target_username} non trovato.")
                    return

            if not target_user.is_resting:
                self.bot.reply_to(self.message, f"⚠️ {target_user.username} non è nella Kame House! Entrambi dovete essere lì per scambiare.")
                return

            if str(target_user.id_telegram) == str(self.chatid):
                self.bot.reply_to(self.message, "🤔 Non puoi scambiare con te stesso!")
                return

            spheres = session.query(Collezionabili).filter(
                Collezionabili.id_telegram == str(self.chatid),
                Collezionabili.oggetto.like('La Sfera del Drago%'),
                Collezionabili.data_utilizzo == None
            ).all()

            if not spheres:
                self.bot.reply_to(self.message, "❌ Non hai Sfere del Drago da scambiare!")
                return

            markup = types.InlineKeyboardMarkup()
            unique_spheres = {}
            for s in spheres:
                unique_spheres[s.oggetto] = unique_spheres.get(s.oggetto, 0) + 1
            
            tradeable_found = False
            for s_name, count in unique_spheres.items():
                if count >= 2:
                    tradeable_found = True
                    short_name = s_name.replace("La Sfera del Drago ", "")
                    code = "SH" if "Shenron" in s_name else "PO"
                    code += s_name[-1]
                    markup.add(types.InlineKeyboardButton(f"🎁 {short_name} (doppia x{count})", callback_data=f"tr_sel|{code}|{target_user.id_telegram}"))
            
            if not tradeable_found:
                self.bot.reply_to(self.message, "❌ Non hai **doppioni** di Sfere del Drago da scambiare (devi averne almeno 2 dello stesso tipo)!", parse_mode='Markdown')
                return

            markup.add(types.InlineKeyboardButton("❌ Annulla", callback_data="tr_den"))
            self.bot.reply_to(self.message, f"🤝 **PROPOSTA SCAMBIO PER {target_user.username}**\n\nSeleziona il **doppione** che vuoi offrire:", parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in handle_scambia: {e}")
            self.bot.reply_to(self.message, "❌ Errore tecnico durante lo scambio.")
        finally:
            session.close()

    def _handle_scambia_step2(self, message):
        self.message = message
        text = message.text.strip()
        if text.startswith("@"):
            self.handle_scambia(target_username=text)
        else:
            self.bot.reply_to(message, "⚠️ Devi specificare l'username con @ (es: @lupin).")

    # --- Market System ---
    def handle_mercato(self):
        """Main menu for the Market."""
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("💰 Vendi Oggetto", callback_data="market_sell_start"))
        markup.row(types.InlineKeyboardButton("📉 Vedi Offerte (Compra)", callback_data="market_buy_list"))
        markup.row(types.InlineKeyboardButton("📦 Le Mie Vendite", callback_data="market_manage"))
        markup.row(types.InlineKeyboardButton("⬅️ Indietro", callback_data="main_menu"))
        
        msg = "🏪 **MERCATO GLOBALE** 🏪\n\n"
        msg += "Benvenuto al mercato! Qui puoi vendere i tuoi oggetti o fare affari comprando da altri giocatori.\n"
        msg += "Scegli cosa vuoi fare:"
        
        self.bot.reply_to(self.message, msg, parse_mode='Markdown', reply_markup=markup)

    def handle_mercato_sell_start(self, call):
        """Step 1 Selling: Show Inventory to pick item."""
        user_id = call.from_user.id
        session = Database().Session()
        try:
            # Get valid items
            items = session.query(Collezionabili).filter(
                Collezionabili.id_telegram == str(user_id),
                Collezionabili.data_utilizzo == None
            ).all()
            
            if not items:
                self.bot.answer_callback_query(call.id, "Il tuo inventario è vuoto!", show_alert=True)
                return

            # Group by name
            item_counts = {}
            for i in items:
                item_counts[i.oggetto] = item_counts.get(i.oggetto, 0) + 1
            
            markup = types.InlineKeyboardMarkup()
            for name, count in item_counts.items():
                # Use a short code or just the name if unique enough. ID is better but we are grouping.
                # We'll pass the name. Ensure name doesn't break callback length limit (64 chars).
                short_name = name[:30] 
                markup.add(types.InlineKeyboardButton(f"{short_name} (x{count})", callback_data=f"mkt_sell_sel|{short_name}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="market_menu"))
            
            self.bot.edit_message_text("💰 **VENDITA OGGETTO**\nScegli cosa vuoi vendere:", 
                                     call.message.chat.id, call.message.message_id, 
                                     parse_mode='Markdown', reply_markup=markup)
        finally:
            session.close()

    def handle_mercato_buy_list(self, call):
        """Show active listings."""
        session = Database().Session()
        try:
            listings = session.query(MarketListing).filter_by(is_active=True).order_by(MarketListing.timestamp.desc()).limit(20).all()
            
            if not listings:
                self.bot.answer_callback_query(call.id, "Nessuna offerta nel mercato al momento.")
                # Don't return, allow seeing empty list or back button
            
            markup = types.InlineKeyboardMarkup()
            for l in listings:
                seller = session.query(Utente).filter_by(id_telegram=l.seller_id).first()
                seller_name = seller.username if seller and seller.username else (seller.nome if seller else "Utente")
                btn_text = f"{l.item_name} - {l.price} 🥔 ({seller_name})"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"mkt_buy_confirm|{l.id}"))
                
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="market_menu"))
            self.bot.edit_message_text("📉 **OFFERTE DI MERCATO**\nClicca su un oggetto per acquistarlo:", 
                                     call.message.chat.id, call.message.message_id, 
                                     parse_mode='Markdown', reply_markup=markup)
        finally:
            session.close()

    def handle_mercato_manage(self, call):
        """Manage own listings (remove them)."""
        user_id = call.from_user.id
        session = Database().Session()
        try:
            my_listings = session.query(MarketListing).filter_by(seller_id=user_id, is_active=True).all()
            
            markup = types.InlineKeyboardMarkup()
            if not my_listings:
                markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="market_menu"))
                self.bot.edit_message_text("📦 **LE TUE VENDITE**\nNon hai oggetti in vendita.", 
                                         call.message.chat.id, call.message.message_id, 
                                         parse_mode='Markdown', reply_markup=markup)
                return

            for l in my_listings:
                markup.add(types.InlineKeyboardButton(f"❌ RITIRA: {l.item_name} ({l.price})", callback_data=f"mkt_remove|{l.id}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="market_menu"))
            self.bot.edit_message_text("📦 **LE TUE VENDITE**\nClicca per ritirare un oggetto dal mercato:", 
                                     call.message.chat.id, call.message.message_id, 
                                     parse_mode='Markdown', reply_markup=markup)
        finally:
            session.close()

    def handle_mercato_sell_price(self, message, item_name):
        """Step 2 Selling: Set Price and Create Listing."""
        try:
            price = int(message.text.strip())
            if price <= 0:
                self.bot.reply_to(message, "⚠️ Il prezzo deve essere maggiore di 0.")
                return
            if price > 1000000:
                 self.bot.reply_to(message, "⚠️ Prezzo troppo alto!")
                 return
        except ValueError:
            self.bot.reply_to(message, "⚠️ Devi inserire un numero valido.")
            return

        user_id = self.chatid
        session = Database().Session()
        try:
            # 1. Verify item ownership again (Critical)
            item = session.query(Collezionabili).filter(
                Collezionabili.id_telegram == str(user_id),
                Collezionabili.oggetto.like(f"{item_name}%"), # Loose match or specific? partial match from button
                Collezionabili.data_utilizzo == None
            ).first()
            
            if not item:
                self.bot.reply_to(message, "❌ Non possiedi più questo oggetto.")
                return

            # 2. Create Listing
            # We want to store the FULL name, so we use item.oggetto
            listing = MarketListing(
                seller_id=user_id,
                item_name=item.oggetto,
                price=price
            )
            session.add(listing)
            
            # 3. Remove from Inventory (Delete row)
            session.delete(item)
            session.commit()
            
            self.bot.reply_to(message, f"✅ Oggetto **{item.oggetto}** messo in vendita per {price} Fagioli!")
            
        except Exception as e:
            print(f"Error selling item: {e}")
            self.bot.reply_to(message, "❌ Errore durante la vendita.")
        finally:
            session.close()

    def handle_mercato_buy_confirm(self, call, listing_id):
        """Execute Purchase."""
        user_id = self.chatid
        session = Database().Session()
        try:
            listing = session.get(MarketListing, listing_id)
            if not listing or not listing.is_active:
                self.bot.answer_callback_query(call.id, "❌ Offerta non più disponibile.")
                # Refresh list
                self.handle_mercato_buy_list(call)
                return

            if listing.seller_id == user_id:
                self.bot.answer_callback_query(call.id, "🤔 È il tuo oggetto!")
                return

            buyer = session.query(Utente).filter_by(id_telegram=user_id).first()
            
            if buyer.points < listing.price:
                self.bot.answer_callback_query(call.id, f"❌ Non hai abbastanza Fagioli! (Te ne mancano {listing.price - buyer.points})", show_alert=True)
                return

            # Execute Transaction
            # 1. Deduct from Buyer
            buyer.points -= listing.price
            
            # 2. Add to Seller
            seller = session.query(Utente).filter_by(id_telegram=listing.seller_id).first()
            if seller:
                seller.points += listing.price
                # Notify Seller
                try:
                    self.bot.send_message(listing.seller_id, f"💰 **Hai venduto un oggetto!**\n\nQualcuno ha comprato **{listing.item_name}** per {listing.price} Fagioli!")
                except: pass
            
            # 3. Add Item to Buyer Inventory
            new_item = Collezionabili(
                id_telegram=str(user_id),
                oggetto=listing.item_name
            )
            session.add(new_item)
            
            # 4. Remove Listing (Delete row or mark inactive? Plan said delete/archive. Let's delete to keep table clean)
            session.delete(listing)
            
            session.commit()
            
            self.bot.answer_callback_query(call.id, f"✅ Acquistato {listing.item_name}!", show_alert=True)
            self.handle_mercato_buy_list(call) # Refresh
            
        except Exception as e:
            print(f"Error buying market item: {e}")
            session.rollback()
            self.bot.answer_callback_query(call.id, "❌ Errore durante l'acquisto.")
        finally:
            session.close()

    def handle_mercato_remove(self, call, listing_id):
        """Remove listing and return item to inventory."""
        user_id = self.chatid
        session = Database().Session()
        try:
            listing = session.get(MarketListing, listing_id)
            if not listing or not listing.is_active:
                self.bot.answer_callback_query(call.id, "Offerta non trovata.")
                self.handle_mercato_manage(call)
                return
            
            if listing.seller_id != user_id:
                self.bot.answer_callback_query(call.id, "Non puoi rimuovere questa offerta.")
                return

            # Return Item
            returned_item = Collezionabili(
                id_telegram=str(user_id),
                oggetto=listing.item_name
            )
            session.add(returned_item)
            
            # Delete Listing
            session.delete(listing)
            session.commit()
            
            self.bot.answer_callback_query(call.id, "✅ Offerta ritirata. Oggetto tornato nell'inventario.")
            self.handle_mercato_manage(call)
            
        except Exception as e:
            print(f"Error removing listing: {e}")
            self.bot.answer_callback_query(call.id, "Errore durante la rimozione.")
        finally:
            session.close()

    # --- Missing Admin Handlers Restoration ---

    def handle_add_livello(self):
        # /addLivello <user_id> <amount>
        try:
            parts = self.message.text.split()
            if len(parts) < 3:
                self.bot.reply_to(self.message, "Usage: /addLivello <user_id> <amount>")
                return
            
            target_id = int(parts[1])
            amount = int(parts[2])
            
            session = Database().Session()
            user = session.query(Utente).filter_by(id_telegram=target_id).first()
            if user:
                user.livello += amount
                session.commit()
                self.bot.reply_to(self.message, f"Aggiunti {amount} livelli a {user.nome}.")
            else:
                self.bot.reply_to(self.message, "Utente non trovato.")
            session.close()
        except Exception as e:
            self.bot.reply_to(self.message, f"Error: {e}")

    def handle_restore(self):
        """Fully restores the user's life and aura."""
        session = Database().Session()
        try:
            utente = session.query(Utente).filter_by(id_telegram=self.chatid).first()
            if utente:
                max_vita = 50 + ((utente.stat_vita or 0) * 10)
                max_aura = 60 + ((utente.stat_aura or 0) * 5)
                utente.vita = max_vita
                utente.aura = max_aura
                session.commit()
                self.bot.reply_to(self.message, f"✅ Statistiche ripristinate per {utente.nome}!")
        except Exception as e:
            print(f"Error handle_restore: {e}")
            self.bot.reply_to(self.message, "❌ Errore durante il ripristino.")
        finally:
            session.close()

    
    # --- Other Missing Handlers (Placeholder/Basic Impl) ---
    
    def handle_set_adult_img(self):
        # /set_adult_img <boss_id> <url>
        self.bot.reply_to(self.message, "Feature 'set_adult_img' temporaneamente disabilitata/WIP.")

    def handle_set_img(self):
        # /set_img <boss_id> <url>
        self.handle_set_adult_img()


    # --- Generic Handlers ---

    def handle_dona(self):
        # /dona <amount> (in reply) OR /dona <username> <amount>
        try:
            args = self.message.text.split()
            if len(args) < 2:
                self.bot.reply_to(self.message, "Usa: `/dona [quantità]` rispondendo a un messaggio, oppure `/dona @username [quantità]`", parse_mode='Markdown')
                return

            target = None
            amount = 0

            # Case A: Reply
            if self.message.reply_to_message:
                if len(args) >= 2:
                    if args[1].isdigit():
                        amount = int(args[1])
                        target_id = self.message.reply_to_message.from_user.id
                        target = Utente().getUtente(target_id)
                    else:
                        self.bot.reply_to(self.message, "La quantità deve essere un numero.")
                        return
            
            # Case B: Username argument
            else:
                if len(args) >= 3:
                    target_name = args[1]
                    if args[2].isdigit():
                        amount = int(args[2])
                        target = Utente().getUtente(target_name)
                    else:
                        self.bot.reply_to(self.message, "La quantità deve essere un numero.")
                        return
                else:
                    self.bot.reply_to(self.message, "Specificare utente e quantità.")
                    return

            if not target:
                self.bot.reply_to(self.message, "Utente non trovato.")
                return

            if amount <= 0:
                self.bot.reply_to(self.message, "La quantità deve essere positiva.")
                return

            # Execute
            sorgente = Utente().getUtente(self.chatid)
            msg = Database().donaPoints(sorgente, target, amount)
            self.bot.reply_to(self.message, msg)

        except Exception as e:
            self.bot.reply_to(self.message, f"Errore: {e}")

    def handle_me(self):
        # /me check personal status
        self.handle_status()

    def handle_livell(self):
        # !livell -> Shows level info?
        pass

    def handle_cresci(self):
        # /cresci -> Grow up?
        self.bot.reply_to(self.message, "Devi salire di livello per crescere!")

    def handle_reset_me(self):
        # /reset_me (Danger zone)
        try:
            # Check confirmation? Or just do it. Code says "ELIMINA...".
            chatid = self.chatid
            Database().delete_user_complete(chatid)
            self.bot.reply_to(self.message, "☢️ **ACCOUNT RESETTATO** ☢️\n\nIl tuo personaggio è stato cancellato.\nDigita /start per ricominciare una nuova avventura!")
        except Exception as e:
            self.bot.reply_to(self.message, f"Errore durante il reset: {e}")

    def handle_evoca(self):
        # /evoca (Shenron?)
        self.bot.reply_to(self.message, "Usa il Radar per trovare le sfere!")

    def handle_plus_minus(self):
        """Adds or removes points/exp for admins."""
        try:
            from Points import Points
            self.bot.reply_to(self.message, Points().addPointsToUsers(Utente().getUtente(self.chatid), self.message))
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore: {e}")

    def handle_backup(self):
        """Trigger a manual database backup."""
        try:
            from main import backup
            backup()
            self.bot.reply_to(self.message, "✅ Backup completato.")
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore backup: {e}")

    def handle_backup_all(self):
        """Alias for backup."""
        self.handle_backup()

    def handle_checkScadenzaPremiumToAll(self):
        """Placeholder for removed premium system check."""
        self.bot.reply_to(self.message, "Sistema Premium rimosso (Saga Pass attivo).")

    def handle_compatta(self):
        """Placeholder for database maintenance."""
        self.bot.reply_to(self.message, "Compattamento DB non necessario al momento.")

    def handle_all_commands(self):
        """Entry point for all bot commands, checking permissions and routing."""
        message = self.message

        # 1. Check for Channel Download (Forward or Link)
        downloader = ChannelDownloader(self.bot, message)
        link_channel, _ = downloader.extract_link_info(message)
        
        if message.forward_from_chat or link_channel:
            if downloader.handle_forward():
                return

        # 2. Safety Fix: Ignore messages without text (stickers, photos, etc.) unless they were forwards handled above
        if not message.text:
            return

        utente = Utente().getUtente(self.chatid)
        
        if message.chat.type == "private":
            self.handle_private_command()
            
        if utente and Utente().isAdmin(utente):
            self.handle_admin_command()
        
        self.handle_generic_command()


    
    # ----------------------------------------


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
        msg += "\n\nLa stagione è ora **CHIUSA**. \n♻️ **IL CICLO RICOMINCIA!** Una nuova stagione sta per iniziare..."
        
        bot.send_message(Tecnologia_GRUPPO, msg, parse_mode='Markdown')
        
        # 2. Deactivate Old Season
        season.active = False
        session.add(season)
        
        # 3. AUTO-RESTART: Create New Season
        today = datetime.date.today()
        next_month = today + datetime.timedelta(days=30)
        new_season_num = season.numero + 1
        
        new_season = Season(
            numero=new_season_num,
            nome=f"Stagione {new_season_num} - Ciclo Temporale",
            data_inizio=today,
            data_fine=next_month,
            active=True
        )
        session.add(new_season)
        session.flush() # Get ID
        
        # Clone Tiers from previous season (Optional but good for consistency)
        old_tiers = session.query(SeasonTier).filter_by(season_id=season.id).all()
        for t in old_tiers:
            new_tier = SeasonTier(
                season_id=new_season.id,
                livello=t.livello,
                exp_richiesta=t.exp_richiesta,
                ricompensa_free_valore=t.ricompensa_free_valore,
                ricompensa_premium_valore=t.ricompensa_premium_valore
            )
            session.add(new_tier)
        
        session.commit()
        
        # Announce New Season
        welcome_msg = f"🌟 **NUOVA STAGIONE INIZIATA!** 🌟\n\n"
        welcome_msg += f"Benvenuti nella **{new_season.nome}**!\n"
        welcome_msg += f"📅 Scadenza: {new_season.data_fine}\n\n"
        welcome_msg += "Tutti i Pass Saga sono stati resettati. Riuscirete a completare tutte le Saghe di nuovo?\n"
        welcome_msg += "Combattete, livellate e conquistate i premi!"
        
        bot.send_message(Tecnologia_GRUPPO, welcome_msg, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error processing season end: {e}")
    finally:
        session.close()

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

    if action == "leave_kamehouse":
        Database().update_user(user_id, {'is_resting': False})
        bot.answer_callback_query(call.id, "Hai lasciato la Kame House!")
        msg_l = "Hai lasciato la Kame House! Sei pronto a tornare all'avventura."
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_l, call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(msg_l, call.message.chat.id, call.message.message_id)
        return

    elif action == "market_menu":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("💰 Vendi Oggetto", callback_data="market_sell_start"))
        markup.row(types.InlineKeyboardButton("📉 Vedi Offerte (Compra)", callback_data="market_buy_list"))
        markup.row(types.InlineKeyboardButton("📦 Le Mie Vendite", callback_data="market_manage"))
        
        msg = "🏪 **MERCATO GLOBALE** 🏪\n\n"
        msg += "Benvenuto al mercato! Qui puoi vendere i tuoi oggetti o fare affari comprando da altri giocatori.\n"
        msg += "Scegli cosa vuoi fare:"
        
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        return

    elif action == "market_sell_start":
        BotCommands(call.message, bot, user_id=user_id).handle_mercato_sell_start(call)
        return

    elif action == "market_buy_list":
        BotCommands(call.message, bot, user_id=user_id).handle_mercato_buy_list(call)
        return

    elif action == "market_manage":
        BotCommands(call.message, bot, user_id=user_id).handle_mercato_manage(call)
        return

    elif action.startswith("mkt_sell_sel|"):
        item_name = action.split("|")[1]
        msg = bot.edit_message_text(f"💰 **VENDITA: {item_name}**\n\nScrivi il prezzo in Fagioli (es: 100):", 
                                  call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: BotCommands(m, bot, user_id=user_id).handle_mercato_sell_price(m, item_name))
        return

    elif action.startswith("mkt_buy_confirm|"):
        listing_id = int(action.split("|")[1])
        BotCommands(call.message, bot, user_id=user_id).handle_mercato_buy_confirm(call, listing_id)
        return

    elif action.startswith("mkt_remove|"):
        listing_id = int(action.split("|")[1])
        BotCommands(call.message, bot, user_id=user_id).handle_mercato_remove(call, listing_id)
        return

    elif action == "main_menu":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    elif action.startswith("tr_den"):
        # tr_den|optional_partner_id|optional_reason_code
        # reason codes: 1=no_items, 0=manual_cancel
        parts = action.split("|")
        partner_id = parts[1] if len(parts) > 1 else None
        reason = parts[2] if len(parts) > 2 else "0"

        msg_d = "❌ Scambio annullato."
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_d, call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(msg_d, call.message.chat.id, call.message.message_id)
        if partner_id:
            msg = "❌ Lo scambio è stato annullato."
            if reason == "1":
                msg = "❌ Lo scambio è stato annullato perché l'utente non ha doppioni da scambiare."
            try: bot.send_message(partner_id, msg)
            except: pass
        return

    elif action == "trade_start":
        # Initial trigger from button
        msg = bot.send_message(call.message.chat.id, "🤝 Con chi vuoi scambiare? Scrivi il suo @username:")
        bot.register_next_step_handler(msg, lambda m: BotCommands(m, bot).handle_scambia(target_username=m.text))
        return

    elif action.startswith("tr_sel|"):
        # tr_sel|codeA|targetId (Initiator offered Sphere A)
        _, codeA, targetId = action.split("|")
        target_user = Utente().getUtente(targetId)
        
        if not target_user or not target_user.is_resting:
            bot.answer_callback_query(call.id, "⚠️ L'utente non è più nella Kame House!")
            return

        nameA = ("La Sfera del Drago Shenron " if codeA.startswith("SH") else "La Sfera del Drago Porunga ") + codeA[-1]
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 OFFRI SFERA IN CAMBIO", callback_data=f"tr_off|{codeA}|{user_id}"))
        markup.add(types.InlineKeyboardButton("❌ RIFIUTA", callback_data=f"tr_den|{user_id}"))
        
        try:
            bot.send_message(targetId, f"🤝 **PROPOSTA DI SCAMBIO**\n\n{utente.username} ti offre:\n✨ **{nameA}**\n\nCosa vorresti dargli in cambio?", parse_mode='Markdown', reply_markup=markup)
            msg_s = f"⏳ Proposta inviata a {target_user.username}. In attesa della sua scelta..."
            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg_s, call.message.chat.id, call.message.message_id)
            else:
                bot.edit_message_text(msg_s, call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Impossibile contattare l'utente.")
        return

    elif action.startswith("tr_off|"):
        # tr_off|codeA|initiatorId (Recipient deciding what to offer back)
        _, codeA, initiatorId = action.split("|")
        
        session = Database().Session()
        spheres = session.query(Collezionabili).filter(
            Collezionabili.id_telegram == str(user_id),
            Collezionabili.oggetto.like('La Sfera del Drago%'),
            Collezionabili.data_utilizzo == None
        ).all()
        session.close()

        if not spheres:
            bot.answer_callback_query(call.id, "❌ Non hai sfere da scambiare!")
            return

        markup = types.InlineKeyboardMarkup()
        unique_spheres = {}
        for s in spheres: unique_spheres[s.oggetto] = unique_spheres.get(s.oggetto, 0) + 1
        
        tradeable_found = False
        for s_name, count in unique_spheres.items():
            if count >= 2:
                tradeable_found = True
                codeB = ("SH" if "Shenron" in s_name else "PO") + s_name[-1]
                short_name = s_name.replace("La Sfera del Drago ", "")
                markup.add(types.InlineKeyboardButton(f"🎁 {short_name} (doppia x{count})", callback_data=f"tr_rev|{codeA}|{codeB}|{initiatorId}"))
        
        if not tradeable_found:
            msg_tf = "❌ Non hai **doppioni** di sfere da dare in cambio. Scambio annullato."
            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg_tf, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            else:
                bot.edit_message_text(msg_tf, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            try: bot.send_message(initiatorId, f"❌ {utente.username} non ha doppioni da scambiare. Scambio annullato.")
            except: pass
            return

        markup.add(types.InlineKeyboardButton("❌ Annulla", callback_data=f"tr_den|{initiatorId}"))
        msg_sel = "✨ Scegli il **doppione** da dare in cambio:"
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_sel, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.edit_message_text(msg_sel, call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    elif action.startswith("tr_rev|"):
        # tr_rev|codeA|codeB|initiatorId (Recipient selection done, Initiator must confirm)
        _, codeA, codeB, initiatorId = action.split("|")
        initiator = Utente().getUtente(initiatorId)

        if not initiator or not initiator.is_resting:
            bot.answer_callback_query(call.id, "⚠️ L'utente non è più nella Kame House!")
            return

        nameA = ("La Sfera del Drago Shenron " if codeA.startswith("SH") else "La Sfera del Drago Porunga ") + codeA[-1]
        nameB = ("La Sfera del Drago Shenron " if codeB.startswith("SH") else "La Sfera del Drago Porunga ") + codeB[-1]

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ ACCETTA SCAMBIO", callback_data=f"tr_fin|{codeA}|{codeB}|{user_id}"))
        markup.add(types.InlineKeyboardButton("❌ RIFIUTA", callback_data=f"tr_den|{user_id}"))

        try:
            bot.send_message(initiatorId, f"🤝 **CONTROFFERTA DI SCAMBIO**\n\n{utente.username} propone questo scambio:\n\nTu dai: **{nameA}**\nRicevi: **{nameB}**\n\nAccetti?", parse_mode='Markdown', reply_markup=markup)
            msg_conf = f"⏳ Proposta inviata a {initiator.username}. In attesa di conferma finale..."
            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg_conf, call.message.chat.id, call.message.message_id)
            else:
                bot.edit_message_text(msg_conf, call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Impossibile contattare l'utente.")
        return

    elif action.startswith("tr_fin|"):
        # tr_fin|codeA|codeB|recipientId (Final step: Execution)
        _, codeA, codeB, recipientId = action.split("|")
        recipient = Utente().getUtente(recipientId)
        
        if not utente.is_resting or not recipient or not recipient.is_resting:
            bot.answer_callback_query(call.id, "⚠️ Entrambi dovete essere nella Kame House!")
            return

        nameA = ("La Sfera del Drago Shenron " if codeA.startswith("SH") else "La Sfera del Drago Porunga ") + codeA[-1]
        nameB = ("La Sfera del Drago Shenron " if codeB.startswith("SH") else "La Sfera del Drago Porunga ") + codeB[-1]

        session = Database().Session()
        try:
            # Get sphere A from initiator (user_id)
            sphereA = session.query(Collezionabili).filter_by(id_telegram=str(user_id), oggetto=nameA, data_utilizzo=None).first()
            # Get sphere B from recipient (recipientId)
            sphereB = session.query(Collezionabili).filter_by(id_telegram=str(recipientId), oggetto=nameB, data_utilizzo=None).first()
            
            if sphereA and sphereB:
                # Execute Swap
                sphereA.id_telegram = str(recipientId)
                sphereB.id_telegram = str(user_id)
                session.commit()
                
                msg_f = f"✅ Scambio completato!\nHai dato: **{nameA}**\nHai ricevuto: **{nameB}**"
                if call.message.content_type == 'photo':
                    bot.edit_message_caption(msg_f, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                else:
                    bot.edit_message_text(msg_f, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                try:
                    bot.send_message(recipientId, f"✅ Scambio completato con {utente.username}!\nHai dato: **{nameB}**\nHai ricevuto: **{nameA}**", parse_mode='Markdown')
                except: pass
            else:
                msg_err = "❌ Errore: una o entrambe le sfere non sono più disponibili."
                if call.message.content_type == 'photo':
                    bot.edit_message_caption(msg_err, call.message.chat.id, call.message.message_id)
                else:
                    bot.edit_message_text(msg_err, call.message.chat.id, call.message.message_id)
        except Exception as e:
            session.rollback()
            bot.answer_callback_query(call.id, f"Errore: {e}")
        finally:
            session.close()
        return

    elif action.startswith("saga_detail_"):
        cat_id = int(action.replace("saga_detail_", ""))
        BotCommands(call.message, bot, user_id=user_id).handle_saga_detail(call, cat_id)
        return

    elif action.startswith("saga_set_active_"):
        cat_id = int(action.replace("saga_set_active_", ""))
        BotCommands(call.message, bot, user_id=user_id).handle_set_saga_active(call, cat_id)
        return

    elif action.startswith("saga_cat_"):
        cat_id = int(action.replace("saga_cat_", ""))
        session = Database().Session()
        try:
            category = session.get(AchievementCategory, cat_id)
            if not category:
                bot.answer_callback_query(call.id, "Categoria non trovata.")
                return

            achievements = session.query(Achievement).filter_by(category_id=cat_id).order_by(Achievement.n_ordine.asc()).all()
            user_achievements = {ua.achievement_id: ua for ua in session.query(UserAchievement).filter_by(user_id=user_id).all()}

            msg = f"{category.icona or '🏆'} **{category.nome.upper()}**\n"
            msg += f"{category.descrizione}\n\n"

            def get_bar(current, total):
                blocks = 10
                filled = int(round(blocks * min(current / total, 1.0)))
                return "■" * filled + "□" * (blocks - filled)

            # Get user for live stats
            utente = Utente().getUtente(user_id)

            for ach in achievements:
                ua = user_achievements.get(ach.id)
                
                # Check for Level Reach Updates (Lazy Load)
                if ach.tipo == "level_reach":
                        req_lv = int(ach.requisito_valore) if ach.requisito_valore.isdigit() else 0
                        if req_lv > 0:
                            current_lv = utente.livello
                            is_completed = current_lv >= req_lv
                            current_prog = 100.0 if is_completed else (current_lv / req_lv) * 100.0
                            
                            if is_completed:
                                if not ua:
                                    ua = UserAchievement(user_id=user_id, achievement_id=ach.id, completato=True, progresso_attuale=100.0)
                                    session.add(ua)
                                    session.commit()
                                    user_achievements[ach.id] = ua
                                elif not ua.completato:
                                    ua.completato = True
                                    ua.progresso_attuale = 100.0
                                    session.commit()
                            else:
                                if not ua:
                                    ua = UserAchievement(user_id=user_id, achievement_id=ach.id, completato=False, progresso_attuale=current_prog)
                                    session.add(ua)
                                    session.commit()
                                    user_achievements[ach.id] = ua
                                elif abs((ua.progresso_attuale or 0.0) - current_prog) > 1.0:
                                    ua.progresso_attuale = current_prog
                                    session.commit()

                # --- NEW: Lazy Load for Character Collection & Boss Kills ---
                if not ua or not ua.completato:
                    if ach.tipo == "collect_pg":
                        char_to_find = ach.requisito_valore
                        has_char = session.query(UserCharacter).filter_by(user_id=user_id, character_name=char_to_find).first()
                        if has_char:
                            if not ua:
                                ua = UserAchievement(user_id=user_id, achievement_id=ach.id, completato=True, progresso_attuale=100.0)
                                session.add(ua)
                            else:
                                ua.completato = True
                                ua.progresso_attuale = 100.0
                            session.commit()
                            user_achievements[ach.id] = ua
                    
                    elif ach.tipo == "boss_kill":
                        # For boss kills, we can't easily check history if it wasn't tracked,
                        # but we can at least ensure future logic works or manually credit if suspected.
                        # For now, just ensure the UI reflects the requirement clearly.
                        pass

                status_icon = "✅" if ua and ua.completato else "🔒"
                msg += f"{status_icon} **{ach.nome}**\n"
                msg += f"_{ach.descrizione}_\n"
                
                # Progress bar if not completed
                if not ua or not ua.completato:
                    prog_percent = ua.progresso_attuale if ua else 0.0
                    msg += f" {get_bar(prog_percent, 100.0)} {int(prog_percent)}%\n"
                    
                    if ach.tipo == "level_reach":
                        req_lv = int(ach.requisito_valore) if ach.requisito_valore.isdigit() else 0
                        msg += f" 📈 Progresso: {utente.livello}/{req_lv}\n"
                    elif ach.tipo == "collect_pg":
                        msg += f" 👤 Obiettivo: Sblocca {ach.requisito_valore}\n"
                    elif ach.tipo == "boss_kill":
                        msg += f" ⚔️ Obiettivo: Sconfiggi {ach.requisito_valore}\n"
                else:
                    msg += " ✨ *Completato!*\n"
                
                # Reward claim button or status
                msg += "\n"

            markup = types.InlineKeyboardMarkup()
            # Check for claimable rewards
            for ach in achievements:
                ua = user_achievements.get(ach.id)
                if ua and ua.completato and not ua.data_completamento: # Needs logic for data_completamento as "claimed"
                    markup.add(types.InlineKeyboardButton(f"🎁 Riscatta: {ach.nome}", callback_data=f"saga_claim_{ach.id}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Torna alle Saghe", callback_data="saga_back"))

            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in saga_cat: {e}")
            bot.answer_callback_query(call.id, "Errore caricamento obiettivi.")
        finally:
            session.close()
        return

    elif action == "saga_back":
        BotCommands(call.message, bot, user_id=user_id).handle_saga(call=call)
        return

    elif action.startswith("saga_claim_"):
        ach_id = int(action.replace("saga_claim_", ""))
        session = Database().Session()
        utente = Utente().getUtente(user_id) # Fix: define utente
        try:
            ach = session.get(Achievement, ach_id)
            ua = session.query(UserAchievement).filter_by(user_id=user_id, achievement_id=ach_id).first()

            if ua and ua.completato and not ua.data_completamento:
                # Grant Reward
                reward_msg = ""
                if ach.premio_tipo == "fagioli":
                    pts = int(ach.premio_valore)
                    utente.points += pts
                    reward_msg = f"{pts} Fagioli"
                elif ach.premio_tipo == "exp":
                    xp = int(ach.premio_valore)
                    utente.exp += xp
                    reward_msg = f"{xp} XP"
                elif ach.premio_tipo == "pg":
                    char_name = ach.premio_valore
                    Utente().sblocca_pg(char_name, session, user_id)
                    reward_msg = f"Personaggio: {char_name}"

                ua.data_completamento = datetime.datetime.now()
                Database().update_user(user_id, {'points': utente.points, 'exp': utente.exp})
                session.commit()

                bot.answer_callback_query(call.id, f"✅ Ricompensa riscattata: {reward_msg}!", show_alert=True)
                # Refresh UI
                call.data = f"saga_cat_{ach.category_id}"
                handle_inline_buttons(call)
            else:
                bot.answer_callback_query(call.id, "Ricompensa non disponibile.")
        except Exception as e:
            print(f"Error claiming achievement: {e}")
            bot.answer_callback_query(call.id, "Errore nel riscatto.")
        finally:
            session.close()
        return

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
        
        # Growth Button
        can_grow, _ = utente.verifica_crescita()
        if can_grow:
            markup.add(types.InlineKeyboardButton("🌟 CRESCI (Disponibile!)", callback_data="trigger_growth"))

        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif action == "trigger_growth":
        BotCommands(call.message, bot, user_id=user_id).handle_cresci()
        
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
            
            # Growth Button
            can_grow, _ = utente.verifica_crescita()
            if can_grow:
                markup.add(types.InlineKeyboardButton("🌟 CRESCI (Disponibile!)", callback_data="trigger_growth"))

            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
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
            
            # Growth Button
            can_grow, _ = utente.verifica_crescita()
            if can_grow:
                markup.add(types.InlineKeyboardButton("🌟 CRESCI (Disponibile!)", callback_data="trigger_growth"))

            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            else:
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        else:
             bot.answer_callback_query(call.id, f"Non hai abbastanza Fagioli! Te ne servono {costo_reset}.")

    elif action == "evoca_shenron":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 Fagioli Zen (300-500)", callback_data="shenron_fagioli"))
        markup.add(types.InlineKeyboardButton("💪 EXP (300-500)", callback_data="shenron_xp"))
        msg_shenron = "🐉 Chiedimi un desiderio, e io te lo esaudirò! Scegline UNO:"
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_shenron, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.edit_message_text(msg_shenron, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "shenron_fagioli":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            regalo = random.randint(300, 500)
            Database().update_user(user_id, {'points': utente.points + regalo})
            msg_f = f"🐉 Il tuo desiderio è stato esaudito! Hai ricevuto {regalo} Fagioli Zen. Addio!"
            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg_f, call.message.chat.id, call.message.message_id)
            else:
                bot.edit_message_text(msg_f, call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Error in shenron_fagioli: {e}")
            bot.send_message(call.message.chat.id, f"Errore: {e}")

    elif action == "shenron_xp":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            regalo = random.randint(300, 500)
            Database().update_user(user_id, {'exp': utente.exp + regalo})
            msg_x = f"🐉 Il tuo desiderio è stato esaudito! Hai ricevuto {regalo} XP. Addio!"
            if call.message.content_type == 'photo':
                bot.edit_message_caption(msg_x, call.message.chat.id, call.message.message_id)
            else:
                bot.edit_message_text(msg_x, call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Error in shenron_xp: {e}")
            bot.send_message(call.message.chat.id, f"Errore: {e}")

    elif action == "evoca_porunga":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("💰 5000 Fagioli Zen", callback_data="porunga_step1_fagioli"))
        markup.row(types.InlineKeyboardButton("💪 2500 XP", callback_data="porunga_step1_xp"))
        msg_p = "🐲 IO SONO PORUNGA! POSSO ESAUDIRE 3 DESIDERI!\n\n1° Desiderio: Scegli tra Fagioli o XP."
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_p, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.edit_message_text(msg_p, call.message.chat.id, call.message.message_id, reply_markup=markup)

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
        
        msg_p2 = f"🐲 {msg_conf} TI RIMANGONO 2 DESIDERI!\n\n2° Desiderio: Scegli cosa piazzare."
        if call.message.content_type == 'photo':
            bot.edit_message_caption(msg_p2, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.edit_message_text(msg_p2, call.message.chat.id, call.message.message_id, reply_markup=markup)

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
            if oggetto.oggetto in ['Nitro', 'Cassa', 'TNT', 'Radar Cercasfere'] or 'Pozione' in oggetto.oggetto:
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
            elif item_name == 'Radar Cercasfere':
                # Fetch full item to get charges
                session = Database().Session()
                radar = session.query(Collezionabili).filter_by(id_telegram=str(user_id), oggetto=item_name, data_utilizzo=None).first()
                
                if not radar:
                    bot.answer_callback_query(call.id, "Oggetto non trovato.")
                    session.close()
                    return

                if radar.cariche <= 0:
                    bot.answer_callback_query(call.id, "Il Radar è scarico! Ricaricalo al negozio.")
                    session.close()
                    return

                # Consume 1 charge
                radar.cariche -= 1
                cariche_rimanenti = radar.cariche
                
                # Roll for Success (60% chance)
                found = random.randint(1, 100) <= 60
                
                # Determine Active Saga for Drops
                # Logic: If user selected a specific saga -> Only that saga logic applies
                # Default: Current Max Saga
                import json
                active_saga_name = None
                if utente.misc_data:
                    try:
                        misc = json.loads(utente.misc_data)
                        active_saga_name = misc.get("active_saga_override") # e.g. "Saga di Freezer"
                    except: pass
                
                # --- CUSTOM DROP LOGIC BASED ON SAGA ---
                # Default Drop list (Earth Balls)
                drop_filter = "Shenron"
                
                # If Active Saga is Namek/Frieza -> Porunga
                if active_saga_name == "Saga di Freezer" or active_saga_name == "Saga di Garlic Jr.": 
                    drop_filter = "Porunga"
                
                # TODO: Add more specific logic for other sagas if needed
                # For now: Earth = Shenron, Namek = Porunga

                if found:
                    # Logic same as automatic radar: pick a sphere and set state
                    try:
                        with open('items.csv', 'r', encoding='latin-1') as f:
                            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('nome,')]
                            items_list = [l.split(',') for l in lines]
                            # Filter by Saga Type
                            spheres = [it[0] for it in items_list if it[0].startswith("La Sfera del Drago") and drop_filter in it[0]]
                            
                            # Fallback if list empty (e.g. no Porunga balls defined yet)
                            if not spheres:
                                spheres = [it[0] for it in items_list if it[0].startswith("La Sfera del Drago")]

                            if spheres:
                                target_sphere = random.choice(spheres)
                                # The drop is still global, but the ALERT is private!
                                Collezionabili.pending_radar_drop[Tecnologia_GRUPPO] = target_sphere
                                # bot.send_message(Tecnologia_GRUPPO, ...) # BRO: Private only!
                                bot.edit_message_text(f"📟 **Radar ({drop_filter})**: Segnale rilevato! Corri nel gruppo!\n🔋 Batterie residue: {cariche_rimanenti}", call.message.chat.id, call.message.message_id)
                    except:
                            bot.edit_message_text(f"📟 **Radar**: Errore durante la scansione.", call.message.chat.id, call.message.message_id)
                    else:
                        bot.edit_message_text(f"📟 **Radar**: Nessun segnale rilevato in quest'area...\n🔋 Batterie residue: {cariche_rimanenti}", call.message.chat.id, call.message.message_id)

                # Update or delete (REMOVED: Radar is permanent)
                if radar.cariche <= 0:
                    bot.send_message(user_id, "🪫 Il tuo Radar si è scaricato! Vai al negozio per ricaricarlo.")
                
                session.commit()
                session.close()
                bot.answer_callback_query(call.id, "Radar utilizzato!")
                return
            elif 'La Sfera del Drago' in item_name:
                bot.answer_callback_query(call.id, "Usa il comando 'Sfera' o evoca il Drago dall'inventario se le hai tutte!")
                return

            elif 'Pozione' in item_name:
                # Calculate Heal Amount
                percentage = 0
                if 'Piccola' in item_name: percentage = 0.25
                elif 'Media' in item_name: percentage = 0.50
                elif 'Grande' in item_name: percentage = 0.75
                elif 'Enorme' in item_name: percentage = 1.0
                
                if 'Aura' in item_name:
                    # Logic for Aura
                    MAX_AURA = 60 + (utente.stat_aura * 5)
                    current_aura = utente.aura if utente.aura is not None else MAX_AURA 
                    
                    if current_aura >= MAX_AURA:
                        bot.answer_callback_query(call.id, "Hai già l'aura al massimo!")
                        return

                    heal_amount = int(MAX_AURA * percentage)
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

                    heal_amount = int(MAX_VITA * percentage)
                    new_vita = min(MAX_VITA, current_vita + heal_amount)
                    Database().update_user(user_id, {'vita': new_vita})
                    msg_text = f"🧪 Hai bevuto {item_name}!\n❤️ Vita ripristinata: {new_vita}/{MAX_VITA}"
                
                Collezionabili().usaOggetto(user_id, item_name)
                bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id)
                bot.answer_callback_query(call.id, "Slurp!")
                return
            
            # Consuma l'oggetto (Solo per oggetti di gruppo che arrivano qui)
            Collezionabili().usaOggetto(user_id, item_name)
            bot.edit_message_text(f"Hai usato {item_name}! L'effetto è stato attivato nel gruppo.", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, f"{item_name} usato!")
            
        except Exception as e:
            print(f"Errore nell'uso dell'oggetto: {e}")
            bot.answer_callback_query(call.id, "Errore durante l'uso dell'oggetto.")

    elif action == "pass_claim":
        SagaPassHandler(bot, call.message, user_id=user_id).handle_claim(call)
        return

    elif action == "pass_buy_premium":
        SagaPassHandler(bot, call.message, user_id=user_id).handle_buy_premium(call)
        return

    elif action == "pass_history":
        SagaPassHandler(bot, call.message, user_id=user_id).handle_pass_history(call)
        return

    elif action == "saga_pass_menu":
        SagaPassHandler(bot, call.message, user_id=user_id).handle_pass()
        return

    elif action.startswith("raid_join_"):
        raid_id = int(action.split("_")[2])
        session = Database().Session()
        try:
            raid = session.get(ActiveRaid, raid_id)
            if not raid or not raid.active:
                bot.answer_callback_query(call.id, "Raid scaduto o terminato.")
                return
            
            if raid.status != 'RECRUITING':
                bot.answer_callback_query(call.id, "Le iscrizioni sono chiuse! La battaglia è iniziata.")
                return

            existing = session.query(RaidParticipant).filter_by(raid_id=raid_id, user_id=user_id).first()
            if existing:
                bot.answer_callback_query(call.id, "Sei già iscritto!")
                return
            
            # Join logic
            p = RaidParticipant(raid_id=raid_id, user_id=user_id, last_attack_time=datetime.datetime.min)
            session.add(p)
            session.commit()
            
            count = session.query(RaidParticipant).filter_by(raid_id=raid_id).count()
            
            # Update Button with count
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton(f"✍️ Iscriviti ({count} Partecipanti)", callback_data=f"raid_join_{raid.id}"))
            
            try:
                bot.edit_message_reply_markup(raid.chat_id, raid.message_id, reply_markup=markup)
            except: pass
            
            bot.answer_callback_query(call.id, "✅ Iscrizione confermata! Preparati.", show_alert=True)
            
        except Exception as e:
            print(f"Error raid join: {e}")
        finally:
            session.close()

    elif action.startswith("raid_"):
        # raid_atk_{id} or raid_spc_{id}
        parts = action.split("_")
        mode = parts[1] # atk or spc
        raid_id = int(parts[2])

        session = Database().Session()
        try:
            raid = session.get(ActiveRaid, raid_id)
            if not raid or not raid.active:
                bot.answer_callback_query(call.id, "Il Raid è terminato o non esiste.")
                return

            boss = session.get(BossTemplate, raid.boss_id)
            
            # Fetch live user object from the SAME session
            utente_live = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not utente_live:
                bot.answer_callback_query(call.id, "Errore: utente non trovato.")
                return

            # 0. Health Check
            if (utente_live.vita or 0) <= 0:
                bot.answer_callback_query(call.id, "💀 Sei K.O.! Devi recuperare vita per combattere.", show_alert=True)
                return
                
            # 0.1 Kame House Check
            if utente_live.is_resting:
                bot.answer_callback_query(call.id, "🐢 Sei nella Kame House! Devi uscire per combattere.", show_alert=True)
                return

            # 1. Cooldown Check
            participant = session.query(RaidParticipant).filter_by(raid_id=raid_id, user_id=user_id).first()
            now = datetime.datetime.now()
            
            if not participant:
                participant = RaidParticipant(raid_id=raid_id, user_id=user_id, last_attack_time=datetime.datetime.min)
                session.add(participant)
                session.flush()

            if (now - participant.last_attack_time).total_seconds() < 60:
                remaining = 60 - int((now - participant.last_attack_time).total_seconds())
                bot.answer_callback_query(call.id, f"💤 Devi riposare! Aspetta {remaining}s.")
                return

            # 2. Attack Cost & Dmg
            stat_danno = utente_live.stat_danno or 0
            stat_aura = utente_live.stat_aura or 0
            stat_crit = utente_live.stat_crit_rate or 0
            
            # Fetch Skill info from selected level
            selected_lv = session.query(Livello).filter_by(id=utente_live.livello_selezionato).first()
            
            skill_name = selected_lv.skill_name if selected_lv else "Attacco Speciale"
            multiplier = selected_lv.skill_multiplier if selected_lv else 3.0
            costo_aura = selected_lv.skill_aura_cost if selected_lv else 60
            
            dmg_base = 10 + (stat_danno * 2) # Base dmg calc (10 + stat*2)
            attack_name = "Attacco"
            crit = False
            
            if mode == "spc":
                current_aura = utente_live.aura if utente_live.aura is not None else (60 + stat_aura * 5)
                if current_aura < costo_aura:
                    bot.answer_callback_query(call.id, f"❌ Aura insufficiente! Serve {costo_aura}.")
                    return
                # Consume Aura
                utente_live.aura = (utente_live.aura if utente_live.aura is not None else (60 + stat_aura * 5)) - costo_aura
                
                # Special Multiplier scales with Aura stat
                aura_multiplier = multiplier + (stat_aura * 0.05)
                dmg_base *= aura_multiplier
                attack_name = skill_name
            
            elif mode == "spc2":
                # Level Check
                unlock_lv = selected_lv.skill2_unlock_lv or 30
                if utente_live.livello < unlock_lv:
                    bot.answer_callback_query(call.id, f"🔒 Ti serve il livello {unlock_lv} per questa mossa!", show_alert=True)
                    return
                
                s2_cost = selected_lv.skill2_aura_cost or 100
                current_aura = utente_live.aura if utente_live.aura is not None else (60 + stat_aura * 5)
                if current_aura < s2_cost:
                    bot.answer_callback_query(call.id, f"❌ Aura insufficiente! Serve {s2_cost}.")
                    return
                
                # Consume Aura
                utente_live.aura = (utente_live.aura if utente_live.aura is not None else (60 + stat_aura * 5)) - s2_cost
                
                # Skill 2 Multiplier + Aura Stat bonus
                s2_base_mult = selected_lv.skill2_multiplier or 4.5
                s2_mult = s2_base_mult + (stat_aura * 0.05)
                
                if utente_live.stadio_crescita == 'adulto':
                    s2_mult *= 1.5
                
                dmg_base *= s2_mult
                attack_name = selected_lv.skill2_name or "Mossa Finale"

            # Crit Check
            crit_chance = stat_crit # e.g. 50 = 50%
            if random.randint(1, 100) <= crit_chance:
                dmg_base *= 2
                crit = True
                attack_name += " CRITICO"

            final_dmg = int(dmg_base)
            
            # 3. Apply Damage
            raid.hp_current = max(0, raid.hp_current - final_dmg)
            participant.dmg_total += final_dmg
            participant.last_attack_time = now
            
            log_msg = f"⚔️ {utente_live.nome} ha usato {attack_name}!\n💥 Danni: {final_dmg}"
            
            # 4. Check Death & Loot
            is_boss_dead = False
            if raid.hp_current <= 0:
                is_boss_dead = True
                raid.active = False
                raid.hp_current = 0
                
                total_raid_dmg = sum(p.dmg_total for p in session.query(RaidParticipant).filter_by(raid_id=raid.id).all())
                loot_msg = f"💀 **{boss.nome} è stato SCONFITTO!** 💀\n\n💰 Ricompense:\n"
                
                participants = session.query(RaidParticipant).filter_by(raid_id=raid.id).all()
                for p in participants:
                    share = p.dmg_total / total_raid_dmg if total_raid_dmg > 0 else 0
                    xp_gain = int(boss.xp_reward_total * share)
                    pts_gain = int(boss.points_reward_total * share)
                    
                    p_user = session.query(Utente).filter_by(id_telegram=p.user_id).first()
                    if p_user:
                        p_user.exp += xp_gain
                        p_user.points += pts_gain
                        loot_msg += f"👤 {p_user.nome}: {p.dmg_total} dmg -> {xp_gain} XP, {pts_gain} {PointsName}\n"
                        
                        active_season = session.query(Season).filter_by(active=True).first()
                        if active_season:
                            prog = session.query(UserSeasonProgress).filter_by(user_id=p.user_id, season_id=active_season.id).first()
                            if not prog:
                                prog = UserSeasonProgress(user_id=p.user_id, season_id=active_season.id, season_exp=0, season_level=1)
                                session.add(prog)
                                session.flush()
                            prog.season_exp += xp_gain
                
                # --- NEW: Achievement Boss Kill Check (Solo Fight Requirement) ---
                # Find achievements related to this boss
                target_achievements = session.query(Achievement).filter_by(tipo="boss_kill", requisito_valore=boss.nome).all()
                if target_achievements and len(participants) == 1:
                    p = participants[0] # The only participant
                    for ach in target_achievements:
                        ua = session.query(UserAchievement).filter_by(user_id=p.user_id, achievement_id=ach.id).first()
                        if not ua:
                            ua = UserAchievement(user_id=p.user_id, achievement_id=ach.id)
                            session.add(ua)
                        if not ua.completato:
                            ua.completato = True
                            ua.progresso_attuale = 1.0
                session.commit()
                
                # loot_msg stored to be sent after UI update
                pass
            
            # 5. Boss Retaliation (20% chance) - ONLY if boss still alive
            elif random.randint(1, 100) <= 20:
                # 5.1 Calculate Advanced Retaliation (Consistent with auto-attack)
                is_special = random.randint(1, 100) <= 15
                is_crit = random.randint(1, 100) <= 10
                
                boss_attack_name = "un colpo fisico"
                dmg_mult = 1.0
                
                if is_special:
                    boss_attack_name = random.choice([
                        "un'onda energetica", "un attacco d'aura", 
                        "un colpo brutale", "una tecnica rapida"
                    ])
                    dmg_mult = 1.5
                    
                final_boss_dmg = int(boss.atk * dmg_mult)
                
                if is_crit:
                    final_boss_dmg *= 2
                    boss_attack_name += " **CRITICO**"

                # --- NEWBIE PROTECTION (LV < 10) ---
                if utente_live.livello < 10:
                    max_hp = 50 + ((utente_live.stat_vita or 0) * 10)
                    damage_cap = int(max_hp * 0.33)
                    if final_boss_dmg > damage_cap:
                        final_boss_dmg = damage_cap

                utente_live.vita = max(0, utente_live.vita - final_boss_dmg)
                log_msg += f"\n⚠️ Il Boss ha contrattaccato con {boss_attack_name}! -{final_boss_dmg} HP a {utente_live.nome}"
            
            # Persist changes BEFORE updating UI
            session.commit()
            bot.answer_callback_query(call.id, f"Hai inflitto {final_dmg} danni!")
                
            # 6. Update UI (Delete Old, Send New)
            raid.last_log = log_msg
            
            # --- 6.1 Delete Old Message ---
            try:
                bot.delete_message(raid.chat_id, raid.message_id)
            except Exception as e_del:
                if "message to delete not found" not in str(e_del):
                    print(f"Raid Delete Error: {e_del}")

            # --- 6.2 Construct New Message ---
            blocks = 10
            filled = int(round(blocks * raid.hp_current / raid.hp_max))
            bar = "🟥" * filled + "⬜️" * (blocks - filled)
            
            msg_text = f"⚠️ **BOSS RAID: {boss.nome}** ⚠️\n"
            msg_text += f"❤️ Vita: [{bar}] {raid.hp_current}/{raid.hp_max}\n"
            msg_text += f"\n📜 **Ultima Azione**:\n{raid.last_log}"
            
            if is_boss_dead:
                msg_text += "\n\n❌ **SCONFITTO**"

            # --- 6.3 Send New & Update ID ---
            try:
                is_boss_dead = raid.hp_current <= 0 # Re-check status for message sequencing
                markup = None
                if not is_boss_dead:
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"raid_atk_{raid.id}"),
                        types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"raid_spc_{raid.id}")
                    )
                
                if boss.image_url:
                    try:
                        sent = bot.send_photo(raid.chat_id, boss.image_url, caption=msg_text, parse_mode='Markdown', reply_markup=markup)
                    except:
                        sent = bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)
                else:
                    sent = bot.send_message(raid.chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)
                
                raid.message_id = sent.message_id

                # --- 6.4 Send Loot Message LAST (if boss defeated) ---
                if is_boss_dead and 'loot_msg' in locals():
                    bot.send_message(raid.chat_id, loot_msg)

            except Exception as e_send:
                print(f"Raid Repost Error: {e_send}")

            session.commit()

        except Exception as e:
            print(f"Error in raid action: {e}")
            bot.answer_callback_query(call.id, "Errore generico raid")
        finally:
            session.close()
        return

    elif action == "main_menu":
        BotCommands(call.message, bot, user_id=user_id).handle_info()
        # Note: handle_info currently sends a NEW message. 
        # If we want to edit, we'd need to refactor it. 
        # But for now, let's at least make it work.
        return

    elif action.startswith("set_char_"):
        char_id = int(action.replace("set_char_", ""))
        session = Database().Session()
        try:
            char = session.get(Livello, char_id)
            if char:
                Database().update_user(user_id, {'livello_selezionato': char_id})
                bot.answer_callback_query(call.id, f"Hai selezionato: {char.nome}!")
                # Refresh Menu
                BotCommands(call.message, bot, user_id=user_id).handle_choose_character_v2(call=call)
            else:
                bot.answer_callback_query(call.id, "Personaggio non trovato.")
        except Exception as e:
            print(f"Error setting character: {e}")
            bot.answer_callback_query(call.id, "Errore nella selezione.")
        finally:
            session.close()
        return

def aura_drain_job():
    """Background job to drain aura from transformed players."""
    session = Database().Session()
    try:
        # Fetch all users who are currently in a transformation
        transformed_users = session.query(Utente).join(
            Livello, Utente.livello_selezionato == Livello.id
        ).filter(Livello.is_transformation == True).all()

        for u in transformed_users:
            char = session.get(Livello, u.livello_selezionato)
            if not char: continue

            drain = char.aura_drain_rate or 1 # Default 1 if somehow 0
            curr_aura = u.aura if u.aura is not None else 60
            
            u.aura = max(0, curr_aura - drain)
            
            # Check for reversion
            if u.aura == 0:
                base_char_id = char.base_form_id or 11 # Revert to Goku Bambino as safe fallback
                u.livello_selezionato = base_char_id
                
                # Fetch base name for message
                base_char = session.get(Livello, base_char_id)
                base_name = base_char.nome if base_char else "Forma Base"
                
                try:
                    bot.send_message(u.id_telegram, f"⚠️ **AURA ESAURITA!**\nLa trasformazione **{char.nome}** si è sciolta. Sei tornato a **{base_name}**.")
                except: pass
        
        session.commit()
    except Exception as e:
        print(f"Error in aura_drain_job: {e}")
        session.rollback()
    finally:
        session.close()

def kamehouse_regen_job():
    """Background job to heal players in Kame House."""
    session = Database().Session()
    try:
        resting_users = session.query(Utente).filter_by(is_resting=True).all()
        for u in resting_users:
            max_vita = 50 + ((u.stat_vita or 0) * 10)
            max_aura = 60 + ((u.stat_aura or 0) * 5)
            
            # Use explicit current values or defaults
            curr_vita = u.vita if u.vita is not None else 50
            curr_aura = u.aura if u.aura is not None else 60
            
            # Apply regen (+2 per minute)
            if curr_vita < max_vita:
                u.vita = min(max_vita, curr_vita + 2)
            
            if curr_aura < max_aura:
                u.aura = min(max_aura, curr_aura + 2)
            
            # If full, kick out
            if (u.vita or 0) >= max_vita and (u.aura or 0) >= max_aura:
                u.is_resting = False
                try:
                    bot.send_message(u.id_telegram, "☀️ **Ti sei riposato a sufficienza!**\nSei tornato in piena forma e hai lasciato la Kame House. Buona fortuna!")
                except: pass
            
            # Notification every 10 minutes (only if still resting)
            elif datetime.datetime.now().minute % 10 == 0:
                 try:
                    msg_upd = f"🏠 **Aggiornamento Kame House**\n"
                    msg_upd += f"Stai riposando...\n\n"
                    msg_upd += f"❤️ **Vita**: {int(u.vita)}/{max_vita}\n"
                    msg_upd += f"💙 **Aura**: {int(u.aura)}/{max_aura}"
                    bot.send_message(u.id_telegram, msg_upd, parse_mode='Markdown')
                 except Exception as e_notify:
                     print(f"Error notifying kame house user: {e_notify}")
            
        session.commit()
    except Exception as e:
        print(f"Error in kamehouse_regen: {e}")
        session.rollback()
    finally:
        session.close()

def backup():
    doc = open('dbz.db', 'rb')
    bot.send_document(CANALE_LOG, doc, caption="Arseniolupin #database #backup")
    doc.close()

# Funzione per avviare il programma di promemoria
def start_reminder_program():
    # Imposta l'orario di esecuzione del promemoria
    schedule.every().day.at("09:00").do(backup)
    # Compattazione mensile degli ID (check interno per il primo del mese)
    schedule.every().day.at("00:00").do(compact_db_job)
    
    # Spawn Boss ogni 4 ore per ravvivare il gruppo (solo Boss di saga)
    schedule.every(4).hours.do(spawn_random_seasonal_boss, only_boss=True)
    
    # Contrattacco Boss ogni 60 secondi
    schedule.every(60).seconds.do(boss_auto_attack_job)
    
    # Rigenerazione Kame House ogni 60 secondi
    schedule.every(60).seconds.do(kamehouse_regen_job)
    
    # Check Inizio Raid (Iscrizioni) ogni 1 minuto
    schedule.every(1).minutes.do(check_raid_start_job)

    # Consumo Aura Trasformazioni ogni 60 secondi
    schedule.every(60).seconds.do(aura_drain_job)
    
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
    try:
        # Creazione e avvio del thread per il polling del bot
        polling_thread = threading.Thread(target=bot_polling_thread)
        polling_thread.daemon = True # Make it a daemon so it dies with the main thread
        polling_thread.start()

        # Avvio del programma di promemoria nel thread principale
        start_reminder_program()
    except KeyboardInterrupt:
        print("\n🛑 Bot fermato manualmente (Ctrl+C).")
    except Exception as e:
        print(f"\n❌ Errore fatale all'avvio: {e}")
