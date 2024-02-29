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
        "Pasqua": {
        "nome":                 "Pasqua",
        "periodo_inizio":       "20240331",
        "periodo_fine":         "20240331",
        "COSTO_PREMIUM":        125,
        "COSTO_MANTENIMENTO":   25
    },
        "Carnevale": {
        "nome":                 "Carnevale",
        "periodo_inizio":       "20240208",
        "periodo_fine":         "20240213",
        "COSTO_PREMIUM":        100,
        "COSTO_MANTENIMENTO":   25
    },
}

CANALE_LOG          =    '-1001804087701'
TEST                =    1

TEST_TOKEN      = '6194032742:AAFuNWnqrN9nx2rHDkcMgwgArQsMcEAKhkE'
SerieTv_TOKEN     = '6858809839:AAHqvl4ai2IYdVHfj1JhWOc9_k4IcfSjUa8'

TEST_GRUPPO     = -1002054513012
Tecnologia_GRUPPO    = -1001685235351

if TEST:
    BOT_TOKEN       = TEST_TOKEN
    Tecnologia_GRUPPO    = TEST_GRUPPO
else:
    BOT_TOKEN       = SerieTv_TOKEN
    Tecnologia_GRUPPO    = Tecnologia_GRUPPO

PointsName = 'Fagioli Zen 🫘'

PREMIUM_CHANNELS = {
    'SerieCartoonUniverse'       :    '-1001607428774',
    'SerieUniverse'       :    '-1001369506956',
    'tutto'     :    '-1002129338782'
}

ALBUM = {
    'Catalogo SerieCartoonUniverse'    :    '-1001884425320',
    'Serie'    :    '-1001884425320',
}

MISCELLANIA = {
    'Movie'     :    '-1001483847400',
    'Libri'     :    '-1001395413398'
}


from telebot import TeleBot
from telebot import types
bot = TeleBot(BOT_TOKEN, threaded=False)
hideBoard = types.ReplyKeyboardRemove()  
