
import logging
from telegram import Update,  ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import json
import smtplib
import json
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import gspread
import random

class JeevesBot:
    def __init__(self):
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
    )
        config = json.load(open('config.json'))
        self.token = config['telegram_token']
        self.gsheets_cred_file = config['gsheets_cred_file']

    def startbot(self):
        application = ApplicationBuilder().token(self.token).build()
        start_handler = CommandHandler('start', self.start)
        start_handler = CommandHandler('list', self.read_sheet)
        application.add_handler(start_handler)

        #echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.echo)
        #application.add_handler(echo_handler)
        application.run_polling()

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

    async def read_sheet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        actions = ['add','complete','print']
        users = ['paul','michelle'] 
        #get the user who sent the message
        added_by = update.message.from_user.first_name
        text = update.message.text

        try:
            text = text.split(',')
            action = text[0].strip().lower()
            action = action.replace('/list ','')
            user = text[1].strip().lower()
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not see a valid command. Please try again.\n\nsample command: /list add,michelle,walk the dog')
            return
        
        item = ''

        random_examples = [
            'add,michelle,walk the dog',
            'add,paul,do the dishes',
            'complete,michelle,walk the dog',
            'complete,paul,do the dishes',
            'print,michelle',
            'print,paul'
            ]
        example = random.choice(random_examples)
       
        #get the action from the message
        if action not in actions:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not see a valid action to take. Please try again.')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Valid actions are: {}'.format(actions))
            await context.bot.send_message(chat_id=update.effective_chat.id, text='sample command: /list {}'.format(example))

            return
            
        if user not in users:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not see a valid user. Please try again.')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Valid users are: {}'.format(users))
            await context.bot.send_message(chat_id=update.effective_chat.id, text='sample command: /list {}'.format(example))
            return            
            
        if action == 'add' or action == 'remove' or action == 'complete':
            try:
                item = text[2]
            except:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not see an item to add to the list. Please try again.')
                await context.bot.send_message(chat_id=update.effective_chat.id, text='sample command: /list {}'.format(example))
                return
        
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.gsheets_cred_file, scope)
        gc = gspread.authorize(credentials)
        wkb = gc.open('family_lists')

        sheet = wkb.worksheet(user + 's_list')
        sheets = [sheet]

        #if the first row is empty, then we need to add the headers
        for sheet in sheets:
            if sheet.acell('a1').value == '' or sheet.acell('a1').value == None:
                sheet.update_acell('a1','id')
                sheet.update_acell('b1','added_by')
                sheet.update_acell('c1','item')
                sheet.update_acell('d1','completed')
                sheet.update_acell('e1','completed by')
                sheet.update_acell('f1','completed at')
        
        if action == 'add':
            #get the first empty row
            row = 0
            while True:
                row = row + 1
                if sheet.acell('a' + str(row)).value == '' or sheet.acell('a' + str(row)).value == None:
                    last_row = row - 1
                    break
           
            #add the item to the list
            # assign a unique id to the item
            current_ids = []
            for x in range(2,last_row + 1):
                current_ids.append(sheet.acell('a' + str(x)).value)
            
            while True:
                id = random.randrange(1,99999)
                if id not in current_ids:
                    break
            
            sheet.update_acell('a' + str(last_row + 1),id)
            sheet.update_acell('b' + str(last_row + 1),added_by)
            sheet.update_acell('c' + str(last_row + 1),item)
            sheet.update_acell('d' + str(last_row + 1),'FALSE')

            await context.bot.send_message(chat_id=update.effective_chat.id, text='I added {} to {}s list'.format(item,user.title()))
        
        if action == 'complete':
            #get the list of items
            list = sheet.get_all_values()
            #remove the header row
            list.pop(0)
            #get the list of items that are not completed
            list = [x for x in list if x[3] == 'FALSE']
            #get the item that matches the item we want to complete - there should only be one - if it doesnt exist, then we have a problem
            fixitem = [x for x in list if x[0] == item]
            if len(fixitem) == 0:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not see item with the ID number {} on {}s list. Please try again.'.format(item,user.title()))
                await context.bot.send_message(chat_id=update.effective_chat.id, text='you can get the ID number from the /list print,user command')
                return


            #get the row number
            row = 0
            while True:
                row = row + 1
                if sheet.acell('a' + str(row)).value == fixitem[0][0]:
                    break

            #update the item
            sheet.update_acell('d' + str(row),'TRUE')
            sheet.update_acell('e' + str(row),added_by)
            sheet.update_acell('f' + str(row),datetime.datetime.now().strftime('%m/%d/%Y %H:%M'))
            await context.bot.send_message(chat_id=update.effective_chat.id, text='I marked {} as complete on {}s list'.format(fixitem[0][2],user.title()))

        if action == 'print':
            #get the list of items
            list = sheet.get_all_values()
            #remove the header row
            list.pop(0)
            #get the list of items that are not completed
            list = [x for x in list if x[3] == 'FALSE']
            #if there are no items, then tell the user
            if len(list) == 0:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='{}s list is empty'.format(user.title()))
                return
            #if there are items, then print them
            else:
                msg = '{}s list:\n'.format(user)
                for item in list:
                    msg = msg + '{} - {}\n'.format(item[0],item[2])
                await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)



    #COMMANDS 
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

    async def meds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="take your meds!")


jeeves = JeevesBot()
jeeves.startbot()

