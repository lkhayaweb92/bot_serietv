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

CANALE_LOG          =    '-1001804087701'
TEST                =    1

TEST_TOKEN      = 'TEST_TOKEN'
SerieTv_TOKEN     = 'ORIGINAL_TOKEN'

TEST_GRUPPO     = -4129882736
Tecnologia_GRUPPO    = -1001685235351

if TEST:
    BOT_TOKEN       = TEST_TOKEN
    Tecnologia_GRUPPO    = TEST_GRUPPO
else:
    BOT_TOKEN       = SerieTv_TOKEN
    Tecnologia_GRUPPO    = AROMA_GRUPPO

PointsName = 'Fagioli Zen 🫘'

PREMIUM_CHANNELS = {
    'ps1'       :    '-1001187652609',
    'ps2'       :    '-1001369506956',
    'ps3'       :    '-1001407069920',
    'ps4'       :    '-1001738986067',
    'pc'        :    '-1001148989565',
    'psp'       :    '-1001497940192',
    'nintendo'  :    '-1001199307271',
    'big_games' :    '-1001238395413',
    'horror'    :    '-1001298605336',
    'hot'       :    '-1001475722596',
    'tutto'     :    '-1001835474623'
}

ALBUM = {
    'newps2'    :    '-1001889106515',
    'newps3'    :    '-1001854528728',
    'newps4'    :    '-1001636502550',
    'newpsp'    :    '-1001672257356'
}

MISCELLANIA = {
    'Serie'    :    '-1001884425320',
    'Movie'     :    '-1001483847400',
    'Libri'     :    '-1001395413398'
}


from telebot import TeleBot
from telebot import types
bot = TeleBot(BOT_TOKEN, threaded=False)
hideBoard = types.ReplyKeyboardRemove()  
