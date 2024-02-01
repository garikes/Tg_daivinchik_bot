import os
from random import shuffle

from config import settings
from telebot import telebot, types
from telebot.types import Message
from pymongo.mongo_client import MongoClient


uri = "mongodb+srv://tymursuprun:UaU5kZpBjiE8JPEa@politechcluster.zgxuh5s.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client.prof_bot
collection = db.users
photo_directory = "photos"

bot = telebot.TeleBot('6365214224:AAEqqCn4HEFGsPz3Bl6QhArrOzwc9X8B_PQ')


@bot.message_handler(commands=['start'])
def start(message: Message):
    bot_message_text = (f'Привіт, {message.from_user.first_name}. Вітаю тебе в боті для пошуку своєї половинки!\
      P.S: При винекнинні будь-яких помилок введи "Меню" для виходу до головного меню')
    bot.send_message(message.chat.id, bot_message_text)
    chat_id_in = False
    for current_profile in collection.find():
        if message.chat.id == current_profile['chat_id']:
            chat_id_in = True
    if chat_id_in is not True:
        bot_message_text = f'Ти тут вперше, тому давай познайомимося та створимо профіль.\n'
        bot.send_message(message.chat.id, bot_message_text)
        create_profile(message)
    else:
        profile(message)


def validate_input(input_text, expected_type, min_length=None, max_length=None):
    if input_text is None:
        return None
    input_value = input_text.strip()

    if expected_type == str:
        if min_length is not None and len(input_value) < min_length:
            return None

        if max_length is not None and len(input_value) > max_length:
            return None

    try:
        input_value = expected_type(input_value)
    except ValueError:
        return None

    return input_value


def profile_name(message, user):
    name = validate_input(message.text, str, max_length=40)
    if name is not None:
        user['name'] = name
        bot.send_message(message.chat.id, "Скільки тобі років?")
        bot.register_next_step_handler(message, profile_age, user=user)
    else:
        bot.send_message(message.chat.id, 'Некоректно введені дані. Спробуйте ще раз')
        bot.register_next_step_handler(message, profile_name, user=user)


def profile_age(message, user):
    age = validate_input(message.text, int, min_length=1, max_length=2)
    if age is not None and 14 <= age <= 30:
        user['age'] = age
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button_girl = types.KeyboardButton("Дівчина")
        button_boy = types.KeyboardButton("Хлопець")
        markup.row(button_girl, button_boy)
        bot.send_message(message.chat.id, f"Ти дівчина чи хлопець?", reply_markup=markup)
        bot.register_next_step_handler(message, profile_gender, user)
    else:
        bot.send_message(message.chat.id, 'Некоректно введені дані або не відповідає віковій групі. Спробуйте ще раз')
        bot.register_next_step_handler(message, profile_age, user)


def profile_gender(message, user):
    gender = validate_input(message.text, str)
    if gender is not None and gender in ['Дівчина', 'Хлопець']:
        user['gender'] = gender == 'Хлопець'
        bot.send_message(message.chat.id, 'Додай своє фото')
        bot.register_next_step_handler(message, profile_photo, user)
    else:
        bot.send_message(message.chat.id, 'Некоректно введені дані. Спробуйте ще раз')
        bot.register_next_step_handler(message, profile_gender, user)


def profile_photo(message, user):
    try:
        file_id = message.photo[-1].file_id
    except (TypeError, IndexError):
        bot.send_message(message.chat.id, 'Некоректно введені данні або не вибрано фото. Спробуйте ще раз')
        bot.register_next_step_handler(message, profile_photo, user)
        return

    file_info = bot.get_file(file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)
    user['photo_url'] = file_info.file_unique_id + ".png"

    photo_directory = 'photos'
    os.makedirs(photo_directory, exist_ok=True)

    file_path_on_disk = os.path.join(photo_directory, user['photo_url'])

    try:
        with open(file_path_on_disk, "wb") as f:
            f.write(downloaded_file)
    except Exception as e:
        bot.send_message(message.chat.id, f'Помилка при збереженні фото: {e}')
        bot.register_next_step_handler(message, profile_photo, user)
        return

    bot.send_message(message.chat.id, 'Тепер розкажи про себе детальніше, будь ласка. (До 1000 символів)')
    bot.register_next_step_handler(message, profile_description, user)


def profile_description(message, user):
    description = validate_input(message.text, str, max_length=1000, min_length=20)
    if description is not None:
        user['description'] = description
        user['chat_id'] = message.chat.id
        profile_username(message, user)
    else:
        bot.send_message(message.chat.id, 'Завеликий/замалий зміст. Спробуйте ще раз')
        bot.register_next_step_handler(message, profile_description, user)


def profile_username(message, user):
    username = message.from_user.username
    if username is not None:
        user['telegram_username'] = "@" + message.from_user.username

    else:
        bot.send_message(message.chat.id, "У твого профілю немає ім'я користувача. Встанови його в налаштуваннях,\
        інакше тобі не зможуть написати в особисті повідомлення")
        user['telegram_username'] = None
    collection.insert_one(user)
    profile(message)


def create_profile(message):
    user = {
        'chat_id': None,
        'name': None,
        'age': None,
        'gender': None,
        'description': None,
        'photo_url': None,
        'liked_by_id': [],
        'telegram_username': None
    }

    bot.send_message(message.chat.id, f"Розпочнімо з ім'я. Як тебе звати?")
    bot.register_next_step_handler(message, profile_name, user)


def profile(message):
    user = get_user_by_chat_id(message.chat.id)

    if user:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        bot.send_message(message.chat.id, 'Ось твій профіль:')

        photo_path = os.path.join(photo_directory, user['photo_url'])
        photo = open(photo_path, "rb") if os.path.exists(photo_path) else None

        caption = f"{user['name']}, {user['age']}, {user['description']}"

        if photo:
            bot.send_photo(message.chat.id, photo, caption=caption)
        else:
            bot.send_message(message.chat.id, 'Помилка: фото не знайдено.')

        button_profile_edit = types.KeyboardButton("Заповнити профіль заново")
        button_menu = types.KeyboardButton('Меню')
        markup.row(button_profile_edit)
        markup.row(button_menu)

        bot.send_message(message.chat.id, "Що робимо?", reply_markup=markup)
        bot.register_next_step_handler(message, button_click)
    else:
        bot.send_message(message.chat.id, 'Помилка: користувача не знайдено. Потрібна повторна реєстрація')
        create_profile(message)


def delete_profile(message):
    user_profile = get_user_by_chat_id(message.chat.id)

    if user_profile:
        photo_url = user_profile.get('photo_url')
        if photo_url:
            photo_path = os.path.join(photo_directory, photo_url)
            if os.path.exists(photo_path):
                os.remove(photo_path)
            else:
                bot.send_message(message.chat.id, 'Помилка: фото не знайдено.')

        collection.delete_one({'chat_id': message.chat.id})
        create_profile(message)
    else:
        bot.send_message(message.chat.id, 'Помилка: профіль користувача не знайдено.')


@bot.message_handler()
def button_click(message):
    action_handlers = {
        '/start': start,
        'Меню': menu,
        'Дивитися анкети': searching_profiles,
        'Мій профіль': profile,
        'Заповнити профіль заново': delete_profile,
        'Продивитися свої вподобайки': who_liked_you
    }

    action_text = message.text
    action_handler = action_handlers.get(action_text)

    if action_handler:
        action_handler(message)
    else:
        bot.send_message(message.chat.id, 'Невідома команда. Спробуйте ще раз.')


def menu(message):
    markup = create_menu_markup()
    bot_message_text = 'Що робимо?'
    bot.send_message(message.chat.id, bot_message_text, reply_markup=markup)
    bot.register_next_step_handler(message, button_click)


def create_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_searching_profiles = types.KeyboardButton('Дивитися анкети')
    button_profile = types.KeyboardButton('Мій профіль')
    button_like = types.KeyboardButton('Продивитися свої вподобайки')
    markup.row(button_searching_profiles, button_profile)
    markup.row(button_like)
    return markup


selected_profiles = []
current_profile_index = 0


def searching_profiles(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(option) for option in ['Дівчат', 'Хлопців', 'Усіх']]
    markup.row(*buttons)
    bot.send_message(message.chat.id, "Кого хочеш шукати?", reply_markup=markup)
    bot.register_next_step_handler(message, get_preference)


def get_preference(message):
    preference = message.text.strip()
    searching_filter = {'Дівчат': 0, 'Хлопців': 1}.get(preference, 3)
    select_from_db(message, searching_filter)


def select_from_db(message, searching_filter):
    global selected_profiles, current_profile_index
    query = {'chat_id': {"$ne": message.chat.id}}
    if searching_filter in [0, 1]:
        query['gender'] = searching_filter == 1
    selected_profiles = list(collection.find(query))
    shuffle(selected_profiles)
    current_profile_index = 0
    searching(message)


def searching(message):
    global current_profile_index
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(emoji) for emoji in ['👍', '👎', '🛑']]
    markup.row(*buttons)
    current_profile = selected_profiles[current_profile_index]
    caption = ", ".join([str(current_profile[key]) for key in ['name', 'age', 'description']])
    send_photo_with_markup(message, current_profile['photo_url'], caption, markup, user_reaction)


def user_reaction(message):
    global current_profile_index
    try:
        if message.text == '👍':
            like_profile(message)
            current_profile_index += 1
            searching(message)
        elif message.text == '👎':
            current_profile_index += 1
            searching(message)
        elif message.text == '🛑':
            menu(message)
        else:
            bot.send_message(message.chat.id, 'Немає такої реакції(')
    except IndexError:
        bot.send_message(message.chat.id, "На даний момент це все. Спробуйте ще раз пізніше")
        menu(message)


def send_photo_with_markup(message, photo_url, caption, markup, callback):
    bot.send_photo(message.chat.id, open(os.path.join(photo_directory, photo_url), "rb"),
                   caption=caption, reply_markup=markup)
    bot.register_next_step_handler(message, callback)


def like_profile(message):
    global selected_profiles, current_profile_index
    liked_user_id = selected_profiles[current_profile_index]['chat_id']
    query = {'chat_id': liked_user_id}
    like_list = [message.chat.id]
    if message.chat.id not in [profile_id['chat_id'] for profile_id in collection.find(query)]:
        current = {'chat_id': liked_user_id, 'liked_by_id': selected_profiles[current_profile_index]['liked_by_id']}
        new_like_by_id = {"$set": {"liked_by_id": like_list}}
        collection.update_one(current, new_like_by_id)


def get_user_by_chat_id(chat_id):
    query = {'chat_id': chat_id}
    return collection.find_one(query)

selected_like_profiles = []
current_like_profile_index = 0


def who_liked_you(message):
    global selected_like_profiles, current_like_profile_index
    liked_by_id = get_user_by_chat_id(message.chat.id).get('liked_by_id')
    if liked_by_id:
        match len(liked_by_id):
            case 1:
                bot_message_text = f'Вас вподобала 1 людина'
            case 2, 3, 4:
                bot_message_text = f'Вас вподобали {len(liked_by_id)} людини'
            case range(5, 100):
                bot_message_text = f'Вас вподобали {len(liked_by_id)} людей'
        bot.send_message(message.chat.id, bot_message_text)
        for current_profile_id in liked_by_id:
            query = {'chat_id': current_profile_id}
            current_profile = collection.find_one(query)
            selected_like_profiles.append(current_profile)
        printing_profile(message)
    else:
        bot.send_message(message.chat.id, 'На жаль, поки тут нікого немає. Спробуйте і ви комусь поставити вподобайку!')
        menu(message)
def printing_profile(message):
    global selected_like_profiles, current_like_profile_index
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(emoji) for emoji in ['👍', '👎', '🛑']]
    markup.row(*buttons)
    current_profile = selected_like_profiles[current_like_profile_index]
    caption = ", ".join([str(current_profile[key]) for key in ['name', 'age', 'description']])
    send_photo_with_markup(message, current_profile['photo_url'], caption, markup, user_like_reaction)


def set_liked_by_id(message):
    global selected_like_profiles, current_like_profile_index
    current = {'chat_id': message.chat.id}
    new_like_by_id = {"$set": {"liked_by_id": selected_like_profiles}}
    collection.update_one(current, new_like_by_id)


def user_like_reaction(message):
    global selected_like_profiles, current_like_profile_index
    try:
        if message.text == '👍':
            name = selected_like_profiles[current_like_profile_index].get('name')
            telegram_username = selected_like_profiles[current_like_profile_index].get('telegram_username')
            mutual_like_message = f'Ви взаємно лайкнулися з {name}! Ось його аккаунт:{telegram_username}.\
                    Тепер ви можете написати одне одному. ✉️'
            if telegram_username is None:
                mutual_like_message= (f"Ви взаємно лайкнулися з {name}! На жаль, ваш партнер не має ім'я користувача.\
            Ви можете зачекати, поки він сам вам напише")
            bot.send_message(message.chat.id, mutual_like_message)

            name = get_user_by_chat_id(message.chat.id).get('name')
            telegram_username = get_user_by_chat_id(message.chat.id).get('telegram_username')
            mutual_like_message = f'Ви взаємно лайкнулися з {name}! Ось його аккаунт:{telegram_username}.\
                                Тепер ви можете написати одне одному. ✉️'
            if telegram_username is None:
                mutual_like_message= (f"Ви взаємно лайкнулися з {name}! На жаль, ваш партнер не має ім'я користувача.\
            Ви можете зачекати, поки він сам вам напише")
            bot.send_message(selected_like_profiles[current_like_profile_index].get('chat_id'), mutual_like_message)

            selected_like_profiles.pop(current_like_profile_index)
            set_liked_by_id(message)
            printing_profile(message)
        elif message.text == '👎':
            selected_like_profiles.pop(current_like_profile_index)
            set_liked_by_id(message)
            printing_profile(message)
        elif message.text == '🛑':
            set_liked_by_id(message)
            menu(message)
        else:
            bot.send_message(message.chat.id, 'Введіть ще раз, бо немає такої реакції(')
            bot.register_next_step_handler(message, user_like_reaction)
    except IndexError:
        bot.send_message(message.chat.id, "На даний момент це все. Спробуйте ще раз пізніше")
        menu(message)


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    print('Bot start')
    bot.polling(none_stop=True)

