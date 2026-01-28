from telebot import types
from settings import *
from sqlalchemy         import create_engine
from model import Livello, Utente, Abbonamento, Database,Collezionabili, use_dragon_balls_logic, Season, SeasonTier, UserSeasonProgress, BossTemplate, ActiveRaid, RaidParticipant, spawn_random_seasonal_boss, boss_auto_attack_job, process_season_end, check_season_expiry
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
    def __init__(self, message, bot):
        self.bot = bot
        self.message = message
        self.comandi_privati = {
            "👤 Scegli il personaggio": self.handle_choose_character_v2,
            "Compra abbonamento Premium (1 mese)": self.handle_buy_premium,
            "✖️ Disattiva rinnovo automatico": self.handle_disattiva_abbonamento_premium,
            "✅ Attiva rinnovo automatico": self.handle_attiva_abbonamento_premium,
            "compro un altro mese": self.handle_buy_another_month,
            "🎖 Compra abbonamento Premium (1 mese)": self.handle_buy_premium,
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
        }
        self.comandi_generici = {
            "!dona": self.handle_dona,
            "/dona": self.handle_dona,
            "/me": self.handle_me,
            "!status": self.handle_status,
            "!stats": self.handle_stats,
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
        }
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

    def handle_negozio_pozioni(self):
        pozioni = [
            {"nome": "Pozione Rigenerante Piccola", "prezzo": 100, "effetto": "Rigenera il 25% della Vita"},
            {"nome": "Pozione Rigenerante Media", "prezzo": 200, "effetto": "Rigenera il 50% della Vita"},
            {"nome": "Pozione Rigenerante Grande", "prezzo": 500, "effetto": "Rigenera il 75% della Vita"},
            {"nome": "Pozione Rigenerante Enorme", "prezzo": 1000, "effetto": "Rigenera il 100% della Vita"},
            {"nome": "Pozione Aura Piccola", "prezzo": 100, "effetto": "Rigenera il 25% dell'Aura"},
            {"nome": "Pozione Aura Grande", "prezzo": 500, "effetto": "Rigenera il 75% dell'Aura"},
            {"nome": "Pozione Aura Enorme", "prezzo": 1000, "effetto": "Rigenera il 100% dell'Aura"},
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
            msg = "🛒 Negozio 🛒\n\n"
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
                msg += f"📅 Inizio: {s.data_inizio}\n\n"

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

    def handle_saga(self):
        try:
            args = self.message.text.split()
            session = Database().Session()
            if len(args) == 1:
                # List all distinct sagas
                sagas = session.query(BossTemplate.saga).filter(BossTemplate.saga != None).distinct().all()
                
                msg = "📜 **SAGHE DISPONIBILI** 📜\n\n"
                if sagas:
                    for s in sagas:
                        if s[0]: msg += f"🔹 {s[0]}\n"
                    msg += "\nUsa `!saga [Nome]` per vedere i nemici di una saga specifica."
                else:
                    msg = "Nessuna saga trovata nel database."
                self.bot.reply_to(self.message, msg, parse_mode='Markdown')
            else:
                # List bosses in specific saga
                search = " ".join(args[1:]).strip()
                bosses = session.query(BossTemplate).filter(BossTemplate.saga.ilike(f"%{search}%")).all()
                if bosses:
                    msg = f"🎴 **NEMICI: {search.upper()}** 🎴\n\n"
                    for b in bosses:
                        msg += f"🆔 `{b.id}` | 👾 **{b.nome}**\n❤️ Vita: {b.hp_max} | ⚔️ Atk: {b.atk}\n\n"
                    msg += f"💡 Usa `/set_boss_img [ID]` (rispondendo a una foto) per impostarne l'immagine."
                else:
                    msg = f"Nessun nemico trovato per la saga: {search}"
                self.bot.reply_to(self.message, msg, parse_mode='Markdown')
            session.close()
        except Exception as e:
            print(f"Error in handle_saga: {e}")
            self.bot.reply_to(self.message, f"❌ Errore durante la ricerca della saga: {e}")

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
        from model import DailyShop, Collezionabili
        
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

        self.bot.send_message(self.chatid, msg, reply_markup=markup)

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

    def handle_status(self):
        message = self.message
        self.bot.reply_to(message, Points.Points().wumpaStats(),parse_mode='markdown')

    def handle_pass(self):
        # /pass command
        user_id = self.message.from_user.id
        session = Database().Session()
        try:
            # 1. Get active season
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                self.bot.reply_to(self.message, "📭 Non c'è nessuna Stagione attiva al momento.")
                return

            # 2. Get user progress
            progress = session.query(UserSeasonProgress).filter_by(user_id=user_id, season_id=season.id).first()
            if not progress:
                progress = UserSeasonProgress(user_id=user_id, season_id=season.id, season_exp=0, season_level=1)
                session.add(progress)
                session.flush()

            # 3. Get Tiers
            tiers = session.query(SeasonTier).filter_by(season_id=season.id).order_by(SeasonTier.livello.asc()).all()
            
            # 4. Build UI
            msg = f"🎟️ **SEASON PASS: {season.nome}** 🎟️\n\n"
            msg += f"📊 **Il Tuo Progresso**:\n"
            msg += f"⭐ Livello: {progress.season_level}\n"
            msg += f"✨ XP Stagionale: {progress.season_exp}\n"
            if progress.is_premium_pass:
                msg += "💎 **PASS PREMIUM ATTIVO**\n"
            else:
                msg += "⚪️ Pass Gratuito\n"
            
            msg += "\n📜 **Livelli e Ricompense**:\n"
            
            # Show a few levels around current
            start_idx = max(0, progress.season_level - 2)
            end_idx = min(len(tiers), progress.season_level + 3)
            
            import json
            claimed = json.loads(progress.claimed_tiers)

            for tier in tiers[start_idx:end_idx]:
                status = "✅" if str(tier.id) in claimed else ("⭐" if tier.livello <= progress.season_level else "🔒")
                msg += f"{status} **Liv. {tier.livello}** ({tier.exp_richiesta} XP)\n"
                msg += f"   🎁 Free: {tier.ricompensa_free_valore}\n"
                msg += f"   💎 Prem: {tier.ricompensa_premium_valore}\n"

            msg += f"\n_Visualizzati i livelli {start_idx+1}-{end_idx} su {len(tiers)}_"

            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("🎁 Riscatta Premi", callback_data="pass_claim"))
            if not progress.is_premium_pass:
                markup.row(types.InlineKeyboardButton("💎 Sblocca Premium (1000 Fagioli)", callback_data="pass_buy_premium"))
            
            self.bot.reply_to(self.message, msg, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in handle_pass: {e}")
            self.bot.reply_to(self.message, "❌ Errore nel caricamento del Pass.")
        finally:
            session.close()

    def handle_me(self):
        message = self.message
        chat_id = message.chat.id
        utente = Utente().getUtente(self.chatid)
        if not utente:
            self.bot.reply_to(message, "Utente non trovato.")
            return

        selectedLevel = Livello().infoLivelloByID(utente.livello_selezionato)
        info_text = Utente().infoUser(utente)
        
        if selectedLevel:
            img_to_send = selectedLevel.link_img_adult if (utente.stadio_crescita == 'adulto' and selectedLevel.link_img_adult) else selectedLevel.link_img
            
            if img_to_send:
                try:
                    # Use message.chat.id instead of self.chatid to support groups
                    self.bot.send_photo(chat_id, img_to_send, caption=info_text, parse_mode='markdown', reply_to_message_id=message.message_id)
                except Exception as e:
                    print(f"Errore nell'invio della foto: {e}")
                    self.bot.reply_to(message, info_text, parse_mode='markdown')
            else:
                self.bot.reply_to(message, info_text, parse_mode='markdown')

    def handle_cresci(self):
        """Allows a character to grow from Child to Adult if milestones are met."""
        message = self.message
        session = Database().Session()
        try:
            utente = session.query(Utente).filter_by(id_telegram=self.chatid).first()
            if not utente:
                self.bot.reply_to(message, "Utente non trovato.")
                return

            can_grow, reason = utente.verifica_crescita()
            if not can_grow:
                self.bot.reply_to(message, f"⚠️ **Crescita non disponibile**\n\n{reason}")
                return

            # Execute Growth
            if utente.applica_crescita(session):
                session.commit()
                
                # Dynamic Growth Message
                msg = f"🌟 **IL POTERE SI RISVEGLIA!** 🌟\n\n"
                msg += f"Complimenti {utente.nome}, sei diventato un **ADULTO**! 👨🏻\n\n"
                msg += f"✨ **Bonus Statistiche Ottenuti**:\n"
                msg += f"❤️ +100 HP\n"
                msg += f"💙 +25 Aura\n"
                msg += f"⚔️ +4 Danno Base\n\n"
                msg += f"Il tuo potenziale è ora sbloccato. Continua ad allenarti!"
                
                self.bot.reply_to(message, msg)
                
                # Logic for Unlocking NEW Characters upon Growth
                # Example: If Goku grows, unlock Goku (Adult) in collection
                # We'll assume the character list eventually has an "Adult" version
                # For now, we just ensure the CURRENT name is in the collection
                utente.sblocca_pg(utente.nome, session, self.chatid)
                
                # Redirect to Info to see new stats
                self.handle_me()
            else:
                self.bot.reply_to(message, "Errore durante il processo di crescita.")

        except Exception as e:
            session.rollback()
            print(f"Error in handle_cresci: {e}")
            self.bot.reply_to(message, "Errore tecnico durante la crescita.")
        finally:
            session.close()

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
        
        # FIX: Use from_user.id (sender) not self.chatid (which is group ID in groups)
        sender_id = message.from_user.id
        utenteSorgente = Utente().getUtente(sender_id)
        
        tokenize = comando.split()
        if len(tokenize) < 3:
            self.bot.reply_to(message, "⚠️ Formato errato.\nUsa: `/dona 100 @utente` oppure `/dona @utente 100`", parse_mode='markdown')
            return

        arg1 = tokenize[1]
        arg2 = tokenize[2]
        
        points = 0
        target_input = ""
        
        # Determine which arg is points (digits)
        if arg1.isdigit():
            points = int(arg1)
            target_input = arg2
        elif arg2.isdigit():
            points = int(arg2)
            target_input = arg1
        else:
            self.bot.reply_to(message, "⚠️ Devi specificare una quantità valida.\nEsempio: `/dona 100 @utente`", parse_mode='markdown')
            return
            
        utenteTarget = Utente().getUtente(target_input)
        
        if not utenteSorgente:
            self.bot.reply_to(message, "❌ Errore: Mittente non trovato nel database.")
            return
        if not utenteTarget:
            self.bot.reply_to(message, f"❌ Errore: Destinatario {target_input} non trovato.")
            return

        messaggio = Utente().donaPoints(utenteSorgente,utenteTarget,points)
        self.bot.reply_to(message,messaggio+'\n\n'+Utente().infoUser(utenteTarget),parse_mode='markdown')
        

    
    def handle_checkScadenzaPremiumToAll(self):
        Points.Points().checkScadenzaPremiumToAll()

    def handle_compatta(self):
        try:
            count = Database().compact_user_ids()
            self.bot.reply_to(self.message, f"✅ Database compattato! {count} utenti ri-indicizzati con ID consecutivi.")
        except Exception as e:
            self.bot.reply_to(self.message, f"❌ Errore durante la compattazione: {str(e)}")

    def handle_reset_me(self):
        """Allows a user to completely reset their account."""
        message = self.message
        args = message.text.split()
        
        if len(args) < 2 or args[1] != "CONFERMO":
            self.bot.reply_to(message, "⚠️ **ATTENZIONE**: Questo comando cancellerà TUTTI i tuoi progressi (Livello, Oggetti, Statistiche) e non si può annullare.\n\nPer procedere scrivi: `/reset_me CONFERMO`", parse_mode='Markdown')
            return
            
        try:
            # FIX: Use from_user.id for the user invoking the command
            user_id = message.from_user.id
            Database().delete_user_complete(user_id)
            self.bot.reply_to(message, "♻️ **Account Resettato!**\n\nI tuoi dati sono stati cancellati. Al prossimo messaggio verrai registrato come un nuovo utente e riceverai un nuovo personaggio starter!")
        except Exception as e:
            print(f"Error resetting user {user_id}: {e}")
            self.bot.reply_to(message, "❌ Errore durante il reset.")

    def handle_evoca(self):
        can_summon_shenron = Collezionabili().checkShenron(self.chatid)
        can_summon_porunga = Collezionabili().checkPorunga(self.chatid)
        
        if can_summon_shenron or can_summon_porunga:
            markup = types.InlineKeyboardMarkup()
            if can_summon_shenron:
                markup.add(types.InlineKeyboardButton("🐉 Evoca Shenron 🐉", callback_data="evoca_shenron"))
            if can_summon_porunga:
                markup.add(types.InlineKeyboardButton("🐲 Evoca Porunga 🐲", callback_data="evoca_porunga"))
            
            self.bot.reply_to(self.message, "✨ Hai riunito le Sfere del Drago! ✨\nCerca di scegliere saggiamente il tuo desiderio...", reply_markup=markup)
        else:
            self.bot.reply_to(self.message, "❌ Non hai ancora riunito tutte le 7 Sfere del Drago di un tipo (Shenron o Porunga)!\n\nContinua a cercarle nel gruppo usando il Radar Cercasfere!")

    def handle_scambia_sfera(self):
        # Syntax: /scambia_sfera "La Sfera del Drago Shenron 1" @username
        text = self.message.text
        match = re.search(r'/scambia_sfera ["\'](.*?)["\']\s+(@\w+)', text)
        if not match:
            # Try without quotes for simpler names
            match = re.search(r'/scambia_sfera\s+(.*?)\s+(@\w+)', text)
        
        if not match:
            self.bot.reply_to(self.message, "⚠️ Formato errato. Usa: `/scambia_sfera \"Nome Sfera\" @username`", parse_mode='markdown')
            return

        sphere_name = match.group(1).strip()
        target_username = match.group(2).strip().replace("@", "")

        if "Sfera del Drago" not in sphere_name:
            self.bot.reply_to(self.message, "⚠️ Puoi scambiare solo le Sfere del Drago!")
            return

        session = Database().Session()
        try:
            # 1. Check sender's sphere
            sphere = session.query(Collezionabili).filter_by(id_telegram=str(self.chatid), oggetto=sphere_name, data_utilizzo=None).first()
            if not sphere:
                self.bot.reply_to(self.message, f"❌ Non possiedi {sphere_name} nel tuo inventario.")
                return

            # 2. Get target user
            target_user = session.query(Utente).filter_by(username=target_username).first()
            
            if not target_user:
                self.bot.reply_to(self.message, f"❌ Utente @{target_username} non trovato nel database.")
                return
            
            if str(target_user.id_telegram) == str(self.chatid):
                self.bot.reply_to(self.message, "🤔 Non puoi scambiare una sfera con te stesso!")
                return

            # 3. Transfer
            sphere.id_telegram = str(target_user.id_telegram)
            session.commit()

            self.bot.reply_to(self.message, f"✅ Hai scambiato **{sphere_name}** con @{target_username}!", parse_mode='markdown')
            try:
                self.bot.send_message(target_user.id_telegram, f"🎁 {Utente().getUsernameAtLeastName(Utente().getUtente(self.chatid))} ti ha inviato **{sphere_name}**!", parse_mode='markdown')
            except: pass

        except Exception as e:
            session.rollback()
            print(f"Error in handle_scambia_sfera: {e}")
            self.bot.reply_to(self.message, "❌ Errore durante lo scambio.")
        finally:
            session.close()

    def handle_restore(self):
        msg = self.bot.reply_to(self.message,'Inviami il db')
        self.bot.register_next_step_handler(msg,Points.Points().restore)
        

    def handle_backup(self):
        Points.Points().backup()

    def handle_add_livello(self):
        message = self.message
        comandi = message.text
        comandi = comandi.split('/addLivello')[1:]
        session = Database().Session()
        try:
            for comando in comandi:
                parametri = comando.split(";")
                livello = int(parametri[1])
                nome = parametri[2]
                exp_to_lvl = int(parametri[3])
                link_img = parametri[4]
                saga = parametri[5]
                lv_premium = int(parametri[6])
                skill_name = parametri[7] if len(parametri) > 7 else "Attacco Speciale"
                multiplier = float(parametri[8]) if len(parametri) > 8 else 3.0
                cost = int(parametri[9]) if len(parametri) > 9 else 60
                link_img_adult = parametri[10] if len(parametri) > 10 else None
                is_starter = (parametri[11].lower() == 'true') if len(parametri) > 11 else False
                
                # Update Livello model call
                exist = session.query(Livello).filter_by(livello=livello, lv_premium=lv_premium, nome=nome).first()
                if exist is None:
                    new_lv = Livello(
                        livello=livello, nome=nome, exp_to_lv=exp_to_lvl, 
                        link_img=link_img, link_img_adult=link_img_adult, saga=saga, lv_premium=lv_premium,
                        skill_name=skill_name, skill_multiplier=multiplier, skill_aura_cost=cost,
                        is_starter=is_starter
                    )
                    session.add(new_lv)
                else:
                    exist.nome = nome
                    exist.exp_to_lv = exp_to_lvl
                    exist.link_img = link_img
                    exist.link_img_adult = link_img_adult
                    exist.saga = saga
                    exist.skill_name = skill_name
                    exist.skill_multiplier = multiplier
                    exist.skill_aura_cost = cost
                    exist.is_starter = is_starter
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in handle_add_livello: {e}")
        finally:
            session.close()

    def handle_set_adult_img(self):
        """Admin command to set adult variant image: /set_adult_img CharacterName;ImageUrl"""
        message = self.message
        try:
            parametri = message.text.split('/set_adult_img')[1].strip()
            char_name, adult_url = [p.strip() for p in parametri.split(';')]
            
            session = Database().Session()
            try:
                # Find the level by name
                lv_obj = session.query(Livello).filter_by(nome=char_name).first()
                if lv_obj:
                    lv_obj.link_img_adult = adult_url
                    session.commit()
                    self.bot.reply_to(message, f"✅ Immagine Adulta per **{char_name}** aggiornata!\n🔗 Link: {adult_url}")
                else:
                    self.bot.reply_to(message, f"❌ Personaggio '{char_name}' non trovato.")
            except Exception as e:
                session.rollback()
                print(f"Error in set_adult_img DB: {e}")
                self.bot.reply_to(message, "❌ Errore durante l'aggiornamento del DB.")
            finally:
                session.close()
                
        except Exception as e:
            self.bot.reply_to(message, "⚠️ **Formato errato**\nUsa: `/set_adult_img NomePersonaggio;LinkImmagine`")

    def handle_set_img(self):
        """Admin command to set base variant image: /set_img CharacterName;ImageUrl"""
        message = self.message
        try:
            # Handle both /set_img and /set_image
            cmd = "/set_image" if "/set_image" in message.text else "/set_img"
            parametri = message.text.split(cmd)[1].strip()
            char_name, url = [p.strip() for p in parametri.split(';')]
            
            session = Database().Session()
            try:
                # Find the level by name
                lv_obj = session.query(Livello).filter_by(nome=char_name).first()
                if lv_obj:
                    lv_obj.link_img = url
                    session.commit()
                    self.bot.reply_to(message, f"✅ Immagine Base per **{char_name}** aggiornata!\n🔗 Link: {url}")
                else:
                    self.bot.reply_to(message, f"❌ Personaggio '{char_name}' non trovato.")
            except Exception as e:
                session.rollback()
                print(f"Error in set_img DB: {e}")
                self.bot.reply_to(message, "❌ Errore durante l'aggiornamento del DB.")
            finally:
                session.close()
                
        except Exception as e:
            self.bot.reply_to(message, "⚠️ **Formato errato**\nUsa: `/set_img NomePersonaggio;LinkImmagine`")

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



    def handle_buy_premium(self):
        abbonamento = Abbonamento()
        utente = Utente().getUtente(self.chatid)
        abbonamento.buyPremium(utente)

    def handle_choose_character_v2(self):
        # Handle character selection (v2 fixed to use Collection)
        message = self.message
        utente = Utente().getUtente(self.chatid)
        punti = Points.Points()
        
        # Only show levels for characters the user actually owns
        livelli_disponibili = Livello().listaLivelliSbloccati(utente)
        
        markup = types.ReplyKeyboardMarkup()
        # Group by Name to avoid spamming every level (show highest reached or selection)
        seen_chars = set()
        for livello in livelli_disponibili:
            if livello.nome not in seen_chars:
                markup.add(f"{livello.nome}")
                seen_chars.add(livello.nome)
                
        msg = bot.reply_to(message, "Seleziona il tuo guerriero dalla tua collezione:", reply_markup=markup)
        self.bot.register_next_step_handler(msg, punti.setCharacter)

    def handle_kamehouse(self):
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
            markup.add(types.InlineKeyboardButton("🚪 Esci dalla Kame House", callback_data="leave_kamehouse"))
            
            try:
                self.bot.send_photo(self.chatid, img_kame, caption=msg, parse_mode='Markdown', reply_markup=markup)
            except Exception as e_img:
                print(f"Error sending Kame House photo: {e_img}")
                self.bot.send_message(self.chatid, msg, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error in handle_kamehouse: {e}")
            self.bot.reply_to(self.message, "Errore durante l'accesso alla Kame House.")
        finally:
            session.close()

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

    if action == "leave_kamehouse":
        Database().update_user(user_id, {'is_resting': False})
        bot.answer_callback_query(call.id, "Hai lasciato la Kame House!")
        bot.edit_message_caption("Hai lasciato la Kame House! Sei pronto a tornare all'avventura.", call.message.chat.id, call.message.message_id)
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

        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "trigger_growth":
        BotCommands(call.message, bot).handle_cresci()
        
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
            
            # Growth Button
            can_grow, _ = utente.verifica_crescita()
            if can_grow:
                markup.add(types.InlineKeyboardButton("🌟 CRESCI (Disponibile!)", callback_data="trigger_growth"))

            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
             bot.answer_callback_query(call.id, f"Non hai abbastanza Fagioli! Te ne servono {costo_reset}.")

    elif action == "evoca_shenron":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 Fagioli Zen (300-500)", callback_data="shenron_fagioli"))
        markup.add(types.InlineKeyboardButton("💪 EXP (300-500)", callback_data="shenron_xp"))
        bot.edit_message_text("🐉 Ciedimi un desiderio, e io te lo esaudirò! Scegline UNO:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "shenron_fagioli":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            regalo = random.randint(300, 500)
            Database().update_user(user_id, {'points': utente.points + regalo})
            bot.edit_message_text(f"🐉 Il tuo desiderio è stato esaudito! Hai ricevuto {regalo} Fagioli Zen. Addio!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Error in shenron_fagioli: {e}")
            bot.send_message(call.message.chat.id, f"Errore: {e}")

    elif action == "shenron_xp":
        try:
            use_dragon_balls_logic(user_id, 'Shenron')
            regalo = random.randint(300, 500)
            Database().update_user(user_id, {'exp': utente.exp + regalo})
            bot.edit_message_text(f"🐉 Il tuo desiderio è stato esaudito! Hai ricevuto {regalo} XP. Addio!", call.message.chat.id, call.message.message_id)
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
                
                if found:
                    # Logic same as automatic radar: pick a sphere and set state
                    try:
                        with open('items.csv', 'r', encoding='latin-1') as f:
                            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('nome,')]
                            items_list = [l.split(',') for l in lines]
                            spheres = [it[0] for it in items_list if it[0].startswith("La Sfera del Drago")]
                            if spheres:
                                target_sphere = random.choice(spheres)
                                # The drop is still global, but the ALERT is private!
                                Collezionabili.pending_radar_drop[Tecnologia_GRUPPO] = target_sphere
                                # bot.send_message(Tecnologia_GRUPPO, ...) # BRO: Private only!
                                bot.edit_message_text(f"📟 **Radar**: Segnale rilevato! Corri nel gruppo!\n🔋 Batterie residue: {cariche_rimanenti}", call.message.chat.id, call.message.message_id)
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
        session = Database().Session()
        try:
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                bot.answer_callback_query(call.id, "Stagione non attiva.")
                return

            progress = session.query(UserSeasonProgress).filter_by(user_id=user_id, season_id=season.id).first()
            if not progress:
                bot.answer_callback_query(call.id, "Nessun progresso trovato.")
                return

            import json
            try:
                claimed = json.loads(progress.claimed_tiers)
            except:
                claimed = []
            
            # Find tiers the user has reached but not claimed
            tiers = session.query(SeasonTier).filter(
                SeasonTier.season_id == season.id,
                SeasonTier.livello <= progress.season_level
            ).all()

            unclaimed_tiers = [t for t in tiers if str(t.id) not in claimed]
            
            if not unclaimed_tiers:
                bot.answer_callback_query(call.id, "Tutte le ricompense sono già state riscattate!")
                return

            awards_given = []
            for t in unclaimed_tiers:
                # 1. Free Reward
                if t.ricompensa_free_valore:
                    val = t.ricompensa_free_valore.lower()
                    if "fagioli" in val:
                        try:
                            pts = int(val.split()[0])
                            utente.points += pts
                            awards_given.append(f"{pts} Fagioli")
                        except: pass
                    elif "exp" in val:
                        try:
                            xp = int(val.split()[0])
                            utente.exp += xp
                            awards_given.append(f"{xp} XP")
                        except: pass
                
                # 2. Premium Reward (Only if user is premium)
                if progress.is_premium_pass and t.ricompensa_premium_valore:
                    val = t.ricompensa_premium_valore.lower()
                    if "fagioli" in val:
                        try:
                            pts = int(val.split()[0])
                            utente.points += pts
                            awards_given.append(f"{pts} Fagioli (Prem)")
                        except: pass
                    elif "exp" in val:
                        try:
                            xp = int(val.split()[0])
                            utente.exp += xp
                            awards_given.append(f"{xp} XP (Prem)")
                        except: pass
                
                claimed.append(str(t.id))

            progress.claimed_tiers = json.dumps(claimed)
            
            # Sync user stats to DB
            Database().update_user(user_id, {'points': utente.points, 'exp': utente.exp})
            session.commit()
            
            summary = ", ".join(awards_given) if awards_given else "Nulla di nuovo"
            bot.answer_callback_query(call.id, f"✅ Ricompense riscattate: {summary}", show_alert=True)
            
            # Refresh UI
            BotCommands(call.message, bot).handle_pass()

        except Exception as e:
            print(f"Error in pass_claim: {e}")
            bot.answer_callback_query(call.id, "Errore nel riscatto.")
        finally:
            session.close()

    elif action == "pass_buy_premium":
        COSTO_PASS = 1000
        if utente.points < COSTO_PASS:
            bot.answer_callback_query(call.id, f"❌ Ti servono {COSTO_PASS} fagioli!")
            return
            
        session = Database().Session()
        try:
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                bot.answer_callback_query(call.id, "Stagione non attiva.")
                return
                
            progress = session.query(UserSeasonProgress).filter_by(user_id=user_id, season_id=season.id).first()
            if not progress:
                progress = UserSeasonProgress(user_id=user_id, season_id=season.id, season_exp=0, season_level=1)
                session.add(progress)
                session.flush()

            if not progress.is_premium_pass:
                Database().update_user(user_id, {'points': utente.points - COSTO_PASS})
                progress.is_premium_pass = True
                session.commit()
                bot.answer_callback_query(call.id, "💎 Pass Premium Sbloccato!", show_alert=True)
                BotCommands(call.message, bot).handle_pass()
            else:
                bot.answer_callback_query(call.id, "Hai già il pass premium!")
        except Exception as e:
            print(f"Error in pass_buy: {e}")
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
