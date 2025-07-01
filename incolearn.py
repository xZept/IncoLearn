import telepot

token = '8074096606:AAEUzypSnMyVarj4bb3NA0jU0rSFqeHjCAc'
TelegramBot = telepot.Bot(token)
print(TelegramBot.getUpdates(980643064_1))
