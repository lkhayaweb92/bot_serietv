from telebot import types
import json
import datetime
import random
from model import Database, Utente, AchievementCategory, UserAchievement, Season, SeasonTier, UserSeasonProgress, Achievement, Collezionabili

class SagaPassHandler:
    def __init__(self, bot, message, user_id=None):
        self.bot = bot
        self.message = message
        self.chatid = user_id if user_id else message.chat.id
        self.PointsName = "Fagioli" # Standardize points name

    def handle_pass(self):
        """
        Shows the Saga Pass status (Season Progress).
        """
        session = Database().Session()
        try:
            active_season = session.query(Season).filter_by(active=True).first()
            if not active_season:
                self.bot.reply_to(self.message, "❄️ **Nessuna Stagione Attiva**\nIl Saga Pass è momentaneamente chiuso.")
                return

            prog = session.query(UserSeasonProgress).filter_by(user_id=self.chatid, season_id=active_season.id).first()
            
            s_lv = prog.season_level if prog else 1
            s_xp = prog.season_exp if prog else 0
            
            # Simple text calculation for next level (e.g. lv * 1000)
            next_lv_req = s_lv * 1000 
            
            msg = f"🎟️ **SAGA PASS: {active_season.nome}**\n"
            msg += f"🗓️ Termina il: {active_season.data_fine}\n\n"
            msg += f"🏅 **Il tuo Livello Stagione**: {s_lv}\n"
            msg += f"✨ **Esperienza**: {s_xp} / {next_lv_req}\n"
            
            bar_len = 10
            filled = int((s_xp / next_lv_req) * bar_len) if next_lv_req > 0 else 0
            filled = min(bar_len, filled)
            bar = "🟩" * filled + "⬜" * (bar_len - filled)
            
            msg += f"[{bar}]\n\n"
            
            # Preview Next Reward
            next_tier = session.query(SeasonTier).filter_by(season_id=active_season.id, livello=s_lv + 1).first()
            if next_tier:
                msg += f"🎁 **Prossima Ricompensa (Lv {s_lv + 1})**:\n"
                msg += f"🆓 **Free**: {next_tier.ricompensa_free_valore} ({next_tier.ricompensa_free_tipo})\n"
                if next_tier.ricompensa_premium_valore:
                    msg += f"🎫 **Pass**: {next_tier.ricompensa_premium_valore} ({next_tier.ricompensa_premium_tipo})\n"
            else:
                msg += "🏆 **Livello Massimo Raggiunto!**\n"

            msg += "\nContinua a completare Obiettivi e Raid per salire di livello e sbloccare ricompense uniche!"
            
            markup = types.InlineKeyboardMarkup()
            
            # Add Premium Purchase Button if not already premium
            if not prog or not prog.is_premium_pass:
                markup.add(types.InlineKeyboardButton("💎 Attiva Premium (1000 Fagioli)", callback_data="pass_buy_premium"))
            
            markup.add(types.InlineKeyboardButton("🎁 Ritira Ricompense", callback_data="pass_claim"))
            markup.add(types.InlineKeyboardButton("📜 Vedi Riscattati", callback_data="pass_history"))
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="profilo_menu"))
            
            self.bot.reply_to(self.message, msg, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error handle_pass: {e}")
            self.bot.reply_to(self.message, "Errore caricamento Saga Pass.")
        finally:
            session.close()

    def handle_pass_history(self, call):
        """
        Shows the list of redeemed rewards for the current season.
        """
        session = Database().Session()
        try:
            active_season = session.query(Season).filter_by(active=True).first()
            if not active_season:
                self.bot.answer_callback_query(call.id, "Nessuna stagione attiva.")
                return

            prog = session.query(UserSeasonProgress).filter_by(user_id=self.chatid, season_id=active_season.id).first()
            
            if not prog or not prog.claimed_tiers:
                self.bot.answer_callback_query(call.id, "Nessuna ricompensa riscattata.")
                return

            try:
                claimed_ids = json.loads(prog.claimed_tiers)
            except:
                claimed_ids = []

            if not claimed_ids:
                self.bot.answer_callback_query(call.id, "Nessuna ricompensa riscattata.")
                return

            # Fetch Tiers details
            tiers = session.query(SeasonTier).filter(SeasonTier.id.in_(claimed_ids)).order_by(SeasonTier.livello).all()
            
            msg = f"📜 **STORICO RICOMPENSE: {active_season.nome}**\n\n"
            
            for t in tiers:
                msg += f"✅ **Lv {t.livello}**:\n"
                msg += f"   • Free: {t.ricompensa_free_valore} {t.ricompensa_free_tipo}\n"
                if prog.is_premium_pass and t.ricompensa_premium_valore:
                    msg += f"   • Premium: {t.ricompensa_premium_valore} {t.ricompensa_premium_tipo}\n"
                msg += "\n"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⬅️ Indietro", callback_data="saga_pass_menu"))
            
            self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

        except Exception as e:
            print(f"Error handle_pass_history: {e}")
            self.bot.answer_callback_query(call.id, "Errore caricamento storico.")
        finally:
            session.close()

    def handle_claim(self, call):
        """
        Handles claiming available rewards.
        """
        session = Database().Session()
        try:
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                self.bot.answer_callback_query(call.id, "Stagione non attiva.")
                return

            progress = session.query(UserSeasonProgress).filter_by(user_id=self.chatid, season_id=season.id).first()
            if not progress:
                self.bot.answer_callback_query(call.id, "Nessun progresso trovato.")
                return

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
                self.bot.answer_callback_query(call.id, "Tutte le ricompense sono già state riscattate!")
                return

            utente = Utente().getUtente(self.chatid)
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
                    elif "pg" in val or "personaggio" in val:
                        char_name = t.ricompensa_free_valore.replace(" PG", "").replace(" Personaggio", "").strip()
                        if Utente().sblocca_pg(char_name, session, self.chatid):
                            awards_given.append(f"PG: {char_name}")

                
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
                    elif "pg" in val or "personaggio" in val:
                        char_name = t.ricompensa_premium_valore.replace(" PG", "").replace(" Personaggio", "").strip()
                        if Utente().sblocca_pg(char_name, session, self.chatid):
                            awards_given.append(f"PG Raro: {char_name}")
                
                claimed.append(str(t.id))

            progress.claimed_tiers = json.dumps(claimed)
            
            # Sync user stats to DB
            Database().update_user(self.chatid, {'points': utente.points, 'exp': utente.exp})
            session.commit()
            
            summary = ", ".join(awards_given) if awards_given else "Nulla di nuovo"
            self.bot.answer_callback_query(call.id, f"✅ Ricompense riscattate: {summary}", show_alert=True)
            
            # Refresh UI
            self.handle_pass()

        except Exception as e:
            print(f"Error in pass_claim: {e}")
            self.bot.answer_callback_query(call.id, "Errore nel riscatto.")
        finally:
            session.close()

    def handle_buy_premium(self, call):
        """
        Handles purchasing the premium pass.
        """
        COSTO_PASS = 1000
        utente = Utente().getUtente(self.chatid)
        if utente.points < COSTO_PASS:
            self.bot.answer_callback_query(call.id, f"❌ Ti servono {COSTO_PASS} fagioli!")
            return
            
        session = Database().Session()
        try:
            season = session.query(Season).filter_by(active=True).first()
            if not season:
                self.bot.answer_callback_query(call.id, "Stagione non attiva.")
                return
                
            progress = session.query(UserSeasonProgress).filter_by(user_id=self.chatid, season_id=season.id).first()
            if not progress:
                progress = UserSeasonProgress(user_id=self.chatid, season_id=season.id, season_exp=0, season_level=1)
                session.add(progress)
                session.flush()

            if not progress.is_premium_pass:
                Database().update_user(self.chatid, {'points': utente.points - COSTO_PASS})
                progress.is_premium_pass = True
                session.commit()
                self.bot.answer_callback_query(call.id, "💎 Pass Premium Sbloccato!", show_alert=True)
                self.handle_pass()
            else:
                self.bot.answer_callback_query(call.id, "Hai già il pass premium!")
        except Exception as e:
            print(f"Error in pass_buy: {e}")
        finally:
            session.close()

