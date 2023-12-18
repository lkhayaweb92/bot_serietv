PROMOZIONI = {
    "Halloween":    {
        "nome":                 "Halloween",
        "periodo_inizio":       "20231030",
        "periodo_fine":         "20231105",
        "COSTO_PREMIUM":        150,
        "COSTO_MANTENIMENTO":   25

    },
    "Natale": {
        "nome":                 "Natale",
        "periodo_inizio":       "20231224",
        "periodo_fine":         "20240108",
        "COSTO_PREMIUM":        100,
        "COSTO_MANTENIMENTO":   25
    },
    "SanValentino": {
        "nome":                 "SanValentino",
        "periodo_inizio":       "20240214",
        "periodo_fine":         "20240214",
        "COSTO_PREMIUM":        125,
        "COSTO_MANTENIMENTO":   25
    },    
}

CANALE_LOG          = '-1001804087701'
TEST                =    1

TEST_TOKEN      = 'TEST_TOKEN'
SerieTv_TOKEN     = 'ORIGINAL_TOKEN'

TEST_GRUPPO     = -1001721979634
SerieTv_Gruppo    = -1001457029650

if TEST:
    BOT_TOKEN       = TEST_TOKEN
    GRUPPO_SerieTv    = TEST_GRUPPO
else:
    BOT_TOKEN       = SerieTv_TOKEN
    GRUPPO_SerieTv    = SerieTv_Gruppo

PointsName = 'Fagioli di Balzar 🫘'

PREMIUM_CHANNELS = {
    'premiumtv'       :    '-1001187652609'
}

ALBUM = {
    'SerieAnime'     :    '-1001884425320',
    'SerieTV'        :    '-1001831830011'
}

MISCELLANIA = {
    'Movie'     :    '-1001483847400',
    'Guide'     :    '-1001458426171',
    'Wallpaper' :    '-1001293777327',
}


from telebot import TeleBot
from telebot import types
bot = TeleBot(BOT_TOKEN, threaded=False)
hideBoard = types.ReplyKeyboardRemove()  