import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

"""
# Welcome to Streamlit!

Edit `/streamlit_app.py` to customize this app to your heart's desire :heart:.
If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).

In the meantime, below is an example of what you can do with just a few lines of code:
"""

num_points = st.slider("Number of points in spiral", 1, 10000, 1100)
num_turns = st.slider("Number of turns in spiral", 1, 300, 31)

indices = np.linspace(0, 1, num_points)
theta = 2 * np.pi * num_turns * indices
radius = indices

x = radius * np.cos(theta)
y = radius * np.sin(theta)

df = pd.DataFrame({
    "x": x,
    "y": y,
    "idx": indices,
    "rand": np.random.randn(num_points),
})

st.altair_chart(alt.Chart(df, height=700, width=700)
    .mark_point(filled=True)
    .encode(
        x=alt.X("x", axis=None),
        y=alt.Y("y", axis=None),
        color=alt.Color("idx", legend=None, scale=alt.Scale()),
        size=alt.Size("rand", legend=None, scale=alt.Scale(range=[1, 150])),
    ))


import sys
import os, threading, re, aiogram, json, asyncio, time, datetime, pytz, requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import Union
from aiogram import Bot, executor, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import Message
from aiogram.dispatcher.filters import Command
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates

notes_cd = CallbackData("notes_cd", "level", "name")
schedule_cd = CallbackData('schedule', 'level', "day", "teacher")

# For hosting
token = st.secrets["bot_token"]
chat_id = st.secrets["chat_id"]
json_file_id = st.secrets["file_id"]
group = st.secrets["group"]

# For pc
# token = "5783086993:AAFLKFGONK05U1Ok6ezn28k-4DmCx0uzip0"
# chat_id = "-1001889480017"
# json_file_id = "BQACAgIAAxkBAAEBLehk6xxWQW9GicYGv9U4gCbo8MuiXwAC8DQAAhBHWUsk1LgdtexkQjAE"
# group = "КН-21"

course = int(group.split("-")[1][0])

logger.add("my_log.log")

user_id_owner = "887748629"
bot = Bot(token=token, parse_mode='html')
dp = Dispatcher(bot)

commands = [
    types.BotCommand(command="/schedule", description="Розклад занять"),
    types.BotCommand(command="/notes", description="Посилання до викладачів"),
    types.BotCommand(command="/link", description="Посилання на сайт з розкладом"),
]


def schedule_callback(level="0", day="0", teacher="0"):
    return schedule_cd.new(level=level, day=day, teacher=teacher)


def notes_callback(level="0", name="0"):
    return notes_cd.new(level=level, name=name)


data = None
schedule_dt = None
notes_dt = None
schedule_update = None
table_name = None

audiences_correct = ["Zoom", "google meet"]

skip_notifications = []


class ParseSchedule:
    def __init__(self) -> None:
        self.days = ("Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя")
        self.times = ("09:00", "10:15", "11:30", "12:45", "14:00", "15:15")
        self.black_list = (r"ст\.\викл\.", r"викл\.", r"доц\.", r"к\.ю\.н.", r"пр\.", r"л\.", r"залік\.", r"іспит\.", r"проф\.", r"\асист\.", r"\.")
        self.incorrect_names = {
            r"ІТ-продуктівдоц.Сушинський\sО.Є": "ІТ-продуктів доц. Сушинський О.Є",
            r"данихдоц.Сушинський\sО.Є": "даних доц. Сушинський О.Є",
            r"доц\.": "",
            r"викл.Анісімович\sО.": "викл. Анісімович О.З",
            r"данихпроф.Сушинський\sО.Є": "даних проф. Сушинський О.Є",
            r"ІТ-продуктівпроф.Сушинський\sО.Є": "IT-продуктів проф. Сушинський О.Є",
            r"Тонковид Т\.": "Тонковид Т.А",
        }
        self.schedule = []
        self.monday = []; self.tuesday = []; self.wednesday = []; self.thurday = []; self.friday = []; self.saturday = []; self.sunday = []
        self.days_dict = {
            "Понеділок": self.monday,
            "Вівторок": self.tuesday,
            "Середа": self.wednesday,
            "Четвер": self.thurday,
            "П'ятниця": self.friday,
            "Субота": self.saturday,
            "Неділя": self.sunday
        }
        self.current_day = None
        self.url = "https://docs.google.com/spreadsheets/u/2/d/e/2PACX-1vR4URBmFzf1WBbTEEboR_q31FhA5XxJ0hjA64eUhBKmccvxPUR_03r9D4OXqg7pgMyXQLj9HCdo_NLD/pubhtml#"
        self.response = requests.get(url=self.url)
        self.soup = BeautifulSoup(self.response.text, "lxml")

    def get_schedule_id(self) -> str:
        try:
            logger.info("Getting schedule_id")
            ids = self.soup.find("ul", {"id": "sheet-menu"}).find_all_next("li")
            ids.reverse()
            for _id in ids:
                id_table = _id.get("id").replace("sheet-button-", "")
                text = _id.find_next("a").text.strip()
                if text[-6::].strip() != "заочн.": 
                    result_classes = re.match(r"(^(2(\s|)курс(\s|)|(Б|б)акалаври(\s||\s\s))\d{2}.\d{2}(\.-|\-))(\d{2}.\d{2})", text)
                    if result_classes:
                        global table_name
                        table_name = text
                        logger.info(f"Returning {id_table}")
                        return id_table
                    # result_classes = re.match(r"(^2(\s|)курс(\s|)\d{2}.\d{2}(\.-|\-))(\d{2}.\d{2})", text)
                    # if result_classes:
                    #     table_name = text
                    #     return id_table
        except Exception as err:
            logger.exception(err)
            return None

    def check_name(self, name, audience):
        try:
            logger.info(f"Checking name[{name}]")

            # If the regular definition is triggered, False will be returned
            status_pair = re.search(r"(classroom|Вебінар|початок)", name)
            if status_pair:
                return [False]
            if audience.strip() == "classroom":
                return [False]

            name = name.strip()
            name = re.sub(r"\s+", " ", name)

            # fixing an incorrectly written name
            for k, n in self.incorrect_names.items():
                name = re.sub(k, n, name)

            name_split = name.split(" ") 

            init = f"{name_split[-1][0]}.{name_split[-1][2]}"
            teacher = f"{name_split[-2]}.{init}"

            if teacher[0:2].strip() == "пр" and teacher[2].isupper(): # checking teacher name for correct found
                teacher = teacher[2::].lower()
            else:
                teacher = teacher.lower()

            # Adding a teacher name with initialisers to remove them from the pair name
            text = f"{name_split[-2]} {init}."
            text_2 = f"{name_split[-2]} {init}"
            black_list = [text, text_2]
            black_list.extend(self.black_list)
            for bl in black_list:
                name = re.sub(bl, "", name)
            logger.info(f"Returning {[True, name.strip(), teacher.strip()]}")
            return [True, name.strip(), teacher.strip()]
        except Exception as err:
            logger.exception(err)
            return [False]
        
    @staticmethod
    def check_date(date):
        logger.info("Checking date..")
        check = False

        try:
            check = True
            int(date.split(".")[1])
        except:   
            check = False

        months = {
            "січня": "01",
            "лютого": "02",
            "березня": "03",
            "квітня": "04",
            "травня": "05",
            "червня": "06",
            "липня": "07",
            "серпня": "08",
            "вересня": "09",
            "жовтня": "10",
            "листопада": "11",
            "грудня": "12",
            "серпнявересня": "08",
        }

        if not re.match(r"^\d\d\s", date.strip()):
            date = date.strip()
            day = date[0:2]
            date = date[2::].split(" ")
            month = months[date[0]]
            year = date[1]
            dt = f"{day}.{month}.{year}"
            return dt 

        if check:
            return date

        date = date.strip().split(" ")

        day = date[0]
        month = months[date[1]]
        year = date[2]
        dt = f"{day}.{month}.{year}"
        return dt

    def reformated_classes(self):
        try:
            logger.info("Reformating classes..")
            id_schedule = self.get_schedule_id()
            if id_schedule:
                classes_list = []
                id_par = 0 # Column number where is correct group
                all_classes = self.soup.find("div", {"id": id_schedule}).find_next("tbody")
                for classes in all_classes:
                    id_th = classes.find("th").get("id")
                    if id_th:
                        id_th = int(id_th[-2::].replace("R", ""))
                        
                        # Searching correct column..
                        if id_th == 1:
                            names = classes.find_all("td")
                            for name in names:
                                text = name.text.strip()[0:5]
                                if text == group:
                                    break
                                id_par += 1
    
                        classes_list.append(classes) if id_th > 1 else None
                    else:
                        logger.warning(f"id_th is none [{id_th}]")
                logger.info(f"Returning classes_list len({len(classes_list)})")
                return [classes_list, id_par]
            else:
                return None
        except Exception as err:
            logger.exception(err)
            return None

    def add_classes(self):
        try:
            # logger.info(f"Adding classes")
            classes_data = self.reformated_classes()
            classes_list = classes_data[0]
            id_par = classes_data[1]
            if classes_list:
                for classes in classes_list:
                    date = None
                    weekday = None
                    id_th = int(classes.find("th").get("id")[-2::].replace("R", ""))
                    all_td = classes.find_all("td")
                    text = all_td[0].text[0:5]
                    day_in_schedule = all_td[0].text 
                    if day_in_schedule in self.days:
                        date = self.check_date(all_td[1].text)
                        logger.info(f"Returned {date}")
                        weekday = all_td[0].text
                        current_day = weekday
                        self.schedule.append({
                            "date": '-'.join(reversed(date.split('.'))),
                            "day": weekday,
                            "clases": self.days_dict[current_day]
                        })
                        id_par_1 = id_par + course
                        if all_td[id_par_1].text:
                            checked_name = self.check_name(all_td[id_par_1].text, all_td[id_par_1 + 2].text) # return [bool, str, str]
                            if checked_name[0]:
                                audience = all_td[id_par_1 + 2].text.replace("ауд.", "")
                                if not audience:
                                    audience = "Z|G"
                                self.days_dict[current_day].append({
                                    "time": all_td[2].text[0:5],
                                    "name": f"{checked_name[1]} {all_td[id_par_1 + 1].text}.",
                                    "audience": audience,
                                    "teacher": checked_name[2]
                                })
                                # logger.info(f"Added [{current_day}]{self.days_dict[current_day]}")
                    elif text in self.times:
                        id_par_2 = id_par - course
                        if all_td[id_par_2].text:
                            checked_name = self.check_name(all_td[id_par_2].text, all_td[id_par_2 + 2].text) # return [bool, str, str]
                            if checked_name[0]:
                                audience = all_td[id_par_2 + 2].text.replace("ауд.", "")
                                if not audience:
                                    audience = "Z|G"
                                self.days_dict[current_day].append({
                                    "time": all_td[0].text[0:5],
                                    "name": f"{checked_name[1]} {all_td[id_par_2 + 1].text}.",
                                    "audience": audience,
                                    "teacher": checked_name[2]
                                })
                                # logger.info(f"Added [{current_day}]{self.days_dict[current_day]}")
                # test schedule
                # date = "03.09.2023"
                # weekday = "Неділя"
                # self.schedule.append({
                #     "date": '-'.join(reversed(date.split('.'))),
                #     "day": weekday,
                #     "clases": self.days_dict[weekday]
                # })
                # self.days_dict[weekday].append({
                #     "time": "03:26",
                #     "name": f"Групова динаміка і комунікації л.",
                #     "audience": f"308",
                #     "teacher": "гущак.о.м"
                # })
        except Exception as err:
            logger.exception(err)
            return False

    def get_schedule(self):
        try:
            self.add_classes()
            new_schedule = []
            schedule_dict = {}
            for sch in self.schedule:
                if sch["clases"]:
                    new_schedule.append(sch)
            schedule_dict["schedule"] = new_schedule
            return [True, schedule_dict]
        except:
            return [False]


async def check_schedule(old_schedule: dict, new_schedule:dict) -> list:
    """
        BETA Function for checking edited in schedule.
    """
    if old_schedule != new_schedule:
        changes = []
        for old, new in zip(old_schedule, new_schedule):
            day = old["day"]
            old_classes = old["clases"]
            new_classes = new["clases"]
            if old_classes != new_classes:
                for old_c, new_c in zip(old_classes, new_classes):
                    changed_time = False
                    changed_name = False

                    old_time = old_c["time"]
                    old_name = old_c["name"]
                    old_audience = old_c["audience"]
                    old_teacher = old_c["teacher"]

                    new_time = new_c["time"]
                    new_name = new_c["name"]
                    new_audience = new_c["audience"]
                    new_teacher = new_c["teacher"]

                    if old_time != new_time:
                        changed_time = True
                    if old_name != new_name:
                        changed_name = True

                    if not changed_time and not changed_name:
                        if old_audience != new_audience:
                            changes.append(f"[{day}][{new_name}]\nЗмінено аудиторію з {old_audience} на {new_audience}")
                        if old_teacher != new_teacher:
                            changes.append(f"[{day}][{new_name}]\nЗмінено викладача з {old_teacher} на {new_teacher}")
        return [True, changes]
    else:
        return [False]
            

async def load_schedule():
    bot = Bot(token=token, parse_mode='html')
    while True:
        global schedule_dt, schedule_update
        try:
            parse = ParseSchedule()
            now = datetime.datetime.now()
            kiev_timezone = pytz.timezone('Europe/Kiev')
            kiev_datetime = now.astimezone(kiev_timezone)
            kiev_date = kiev_datetime.strftime('%d.%m.%Y')
            kiev_time = kiev_datetime.strftime('%H:%M:%S')
            if os.path.exists("schedule.json"):   
                parse_result = parse.get_schedule()
                if parse_result[0]:
                    with open("schedule.json", "r", encoding="utf-8") as f:
                        old_schedule = json.load(f)["schedule"]
                        new_schedule = parse_result[1]["schedule"]
                        info_schedule = await check_schedule(old_schedule, new_schedule)
                        if info_schedule[0]:
                            changes = "\n\n".join(info_schedule[1])

                            with open("schedule.json", "w", encoding="utf-8") as f:
                                schedule_dt = new_schedule
                                schedule_update = f"Перевірено:\n{kiev_time}|{kiev_date}"
                                json.dump(parse_result[1], f, ensure_ascii=False, indent=4)
                            await bot.send_message(chat_id=user_id_owner, text="Файл schedule.json оновлено!")
                            await bot.send_message(chat_id=user_id_owner, text=f'Розклад змінено: \n{changes}')
                        else:
                            schedule_update = f"Перевірено:\n{kiev_time}|{kiev_date}"
                            schedule_dt = new_schedule
            else:
                parse_result = parse.get_schedule()
                if parse_result[0]:
                    with open("schedule.json", "w", encoding="utf-8") as f:
                        schedule_update = f"Перевірено:\n{kiev_time}|{kiev_date}"
                        schedule_dt = parse_result[1]["schedule"]
                        json.dump(parse_result[1], f, ensure_ascii=False, indent=4)
                    await bot.send_message(chat_id=user_id_owner, text="Файл schedule.json завантажено!")
            await asyncio.sleep(1800) # 1800
        except Exception as err:
            await bot.send_message(chat_id=user_id_owner, text=f"[ERROR] {err}")
            
            
async def load_notes():
    try:
        global notes_dt
        if os.path.exists("notes.json"):
            os.remove("notes.json")
        file_info = await bot.get_file(json_file_id)
        file_path = file_info.file_path
        file = await bot.download_file(file_path)
        with open("notes.json", "wb") as f:
            f.write(file.read())
        with open("notes.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        notes_dt = data["notes"]
        await bot.send_message(chat_id=user_id_owner, text="Файл notes.json завантажено!")
    except aiogram.utils.exceptions.BadRequest as err:
        await bot.send_message(chat_id=user_id_owner, text=f"Помилка завантаження notes.json файла\nERROR: {err}")


def get_keyboard(buttons:list):
    markup = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        markup.insert(InlineKeyboardButton(text=btn["text_btn"], url=btn["url_btn"]))
    return markup


def get_notes(name):
    data_dt = {}
    buttons = []
    for nt in notes_dt:
        if nt["name"].strip() == name.strip():
            remove_list = []
            tx_list = nt["text"].split("\n")
            for tx in tx_list:
                match_url = re.match(r"^\[(.*?)\]\(buttonurl:\/\/(.*?)\)$", tx)
                sm_indexes = [match.start() for match in re.finditer('`', tx)]
                if len(sm_indexes) == 2 and sm_indexes[0] < sm_indexes[1]:
                    index = tx_list.index(tx)
                    text = f"{tx[:sm_indexes[0]]}<code>{tx[sm_indexes[0]+1:sm_indexes[1]]}</code>{tx[sm_indexes[1]+1:]}"
                    tx_list[index] = text
                    
                if match_url:
                    url_btn = match_url.group(2)
                    match_url_s = re.match(r"^(http:\/\/|https:\/\/.*?)$", url_btn)
                    if not match_url_s:
                        url_btn = f"http://{url_btn}"
                    buttons.append({
                        "text_btn": match_url.group(1),
                        "url_btn": url_btn
                    })
                    remove_list.append(tx)
            for rm in remove_list:
                tx_list.remove(rm)
                data_dt["text"] = "\n".join(tx_list)
        
    data_dt["buttons"] = buttons
    return data_dt


def check_skip(day, time):
    for skip in skip_notifications:
        if skip["day"] == day:
            if skip["time"] == time:
                return True


async def main_schedule():
    LEVEL = 0
    markup = InlineKeyboardMarkup(row_width=1)
    for sh in schedule_dt:
        markup.insert(InlineKeyboardButton(text=sh["day"], callback_data=schedule_callback(level="1", day=sh["day"])))
    return markup


async def show_schedule_keyboard(day):
    LEVEL = 1
    markup = InlineKeyboardMarkup(row_width=1)
    for sh in schedule_dt:
        if sh["day"] == day:
            for cl in sh["clases"]:
                string_split = cl["name"].replace(".", "").split(" ")
                l_pr = string_split[-1]
                name = " ".join(string_split[0:-1])

                audience= cl["audience"].strip()
                city_aud = ""

                try:
                    int(audience[0])
                    city_aud = get_notes(cl["teacher"])["text"][0]
                except:
                    audience = audience[0]
   
                if not check_skip(sh["day"], cl["time"]):
                    text = f'[{cl["time"]}][{l_pr}][{city_aud}{audience}] {name}'
                    markup.insert(InlineKeyboardButton(text=text, callback_data=schedule_callback(level="2", teacher=cl["teacher"], day=day)))
    markup.row(InlineKeyboardButton(text="Назад", callback_data=schedule_callback(level="0")))
    return markup


async def show_note_keyboard(buttons, day):
    LEVEL = 2
    markup = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        markup.insert(InlineKeyboardButton(text=btn["text_btn"], url=btn["url_btn"]))
    markup.row(InlineKeyboardButton(text="Назад", callback_data=schedule_callback(level="1", day=day)))
    return markup


@dp.message_handler(Command("file_id"))
async def give_file_id(msg: Message):
    if int(msg.from_user.id) == int(user_id_owner): 
        await msg.answer(text=f"FILE_ID: <code>{msg.reply_to_message.document.file_id}</code>")


@dp.message_handler(Command('get_files'))
async def send_files(msg: types.Message):
        if int(msg.from_user.id) == int(user_id_owner): 
            with open("schedule.json", "rb") as file:
                schedule = file.read()
            with open("notes.json", "rb") as file:
                notes = file.read()
            file_id = (await bot.send_document(user_id_owner, schedule)).document.file_id
            file_id_1 = (await bot.send_document(user_id_owner, notes)).document.file_id
            await bot.send_message(user_id_owner, f"File ID: <code>{file_id}</code>")
            await bot.send_message(user_id_owner, f"File ID: <code>{file_id_1}</code>")


@dp.message_handler(Command("time"))
async def get_last_update(msg: Message):
    await msg.reply(schedule_update)


@dp.message_handler(Command("off"))
async def show_schedule(msg: Message):
    if int(msg.from_user.id) == int(user_id_owner):
        sys.exit()


@dp.message_handler(Command("link"))
async def give_link(msg: Message):
    await msg.reply("https://docs.google.com/spreadsheets/u/2/d/e/2PACX-1vR4URBmFzf1WBbTEEboR_q31FhA5XxJ0hjA64eUhBKmccvxPUR_03r9D4OXqg7pgMyXQLj9HCdo_NLD/pubhtml#")


@dp.message_handler(Command("log"))
async def get_logs(msg:Message):
    if int(msg.from_user.id) == int(user_id_owner):
        await bot.send_document(chat_id=user_id_owner, document=open("./my_log.log", "rb"))


# Керування тимчасовим видаленням із розкладу пари
@dp.message_handler(Command("add_skip"))
async def add_skip_clases(msg: Message):
    if int(msg.from_user.id) == int(user_id_owner): 
        global skip_notifications
        text = msg.get_args().split(" ")
        skip_notifications.append({"day": text[0], "time": text[1]})
        await msg.reply(skip_notifications)

        
@dp.message_handler(Command("get_skips"))
async def get_skips(msg: Message):
    await msg.reply(skip_notifications)


@dp.message_handler(Command("clear_skips"))
async def clear_skips(msg: Message):
    if int(msg.from_user.id) == int(user_id_owner): 
        global skip_notifications
        skip_notifications.clear()
        await msg.reply(skip_notifications)

@dp.message_handler(Command("del_skip"))
async def del_skip(msg: Message):
    if int(msg.from_user.id) == int(user_id_owner): 
        global skip_notifications
        text = msg.get_args().split(" ")
        skip_notifications.remove({"day": text[0], "time": text[1]})
        await msg.reply(skip_notifications)


@dp.message_handler(Command("audience"))
async def give_help_au(msg:Message):
    await msg.reply("Z - Zoom\ng - Google Meet\nМістоЧисло - номер кабінету для проведення очної пари (К - Київ, Л - Львів)")

@dp.message_handler(Command("schedule"))
async def give_mm(msg: Message):
    await schedule_st_panel(msg)

    
async def schedule_st_panel(msg: Union[Message, CallbackQuery], **kwargs):
    markup = await main_schedule()
    if markup["inline_keyboard"]:
        if isinstance(msg, Message):
            await msg.answer(text=f"Розклад занять\n{table_name}", reply_markup=markup)
        elif isinstance(msg, CallbackQuery):
            call = msg
            await call.message.edit_text(text=f"Розклад занять\n{table_name}")
            await call.message.edit_reply_markup(markup)
    else:
        await msg.answer("Розкладу поки немає у таблиці")


async def show_schedule(call: CallbackQuery, **kwargs):
    day = kwargs["day"]
    markup = await show_schedule_keyboard(day=day)
    await call.message.edit_text(text=f"Розклад занять\n{day}")
    await call.message.edit_reply_markup(markup)


async def show_note(call: CallbackQuery, **kwargs):
    try:
        teacher = kwargs["teacher"]
        day = kwargs["day"]
        notes = get_notes(teacher)
        # print(teacher, notes)
        markup = await show_note_keyboard(notes["buttons"], day)
        await call.message.edit_text(text=notes["text"])
        await call.message.edit_reply_markup(markup)
    except KeyError as err:
        await dp.bot.answer_callback_query(call.id, text=f'Викладача "{kwargs["teacher"]}" не найдено в базі бота.')
        await show_schedule(call=call, day=day)
        logger.warning(f"Teacher: {kwargs['teacher']} not found!")
        logger.error(err)


async def get_notes_keyboard():
    LEVEL = 0
    markup = InlineKeyboardMarkup(row_width=1)
    for nt in notes_dt:
        name = nt["name"]
        markup.insert(InlineKeyboardButton(text=name, callback_data=notes_callback(level="1", name=name)))
    return markup


async def get_note_keyboard(buttons):
    LEVEL = 1 
    markup = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        markup.insert(InlineKeyboardButton(text=btn["text_btn"], url=btn["url_btn"]))
    markup.row(InlineKeyboardButton(text="Назад", callback_data=notes_callback(level="0")))
    return markup


@dp.message_handler(Command("notes", prefixes="#/!"))
async def notes_all(msg: Message):
    await notes_st(msg)


async def notes_st(msg: Union[Message, CallbackQuery], **kwargs):
    markup = await get_notes_keyboard()
    if isinstance(msg, Message):
        await msg.reply(text=f"Усі посилання", reply_markup=markup)
    elif isinstance(msg, CallbackQuery):
        call = msg
        await call.message.edit_text(f"Усі посилання")
        await call.message.edit_reply_markup(markup)


async def show_note_link(call: CallbackQuery, **kwargs):
    teacher = kwargs["name"]
    notes = get_notes(teacher)
    markup = await get_note_keyboard(notes["buttons"])
    await call.message.edit_text(notes["text"])
    await call.message.edit_reply_markup(markup)

    
async def schedule_controller():
    bot = Bot(token=token, parse_mode='html')
    while True:
        now = datetime.datetime.now()
        kiev_timezone = pytz.timezone('Europe/Kiev')
        kiev_datetime = now.astimezone(kiev_timezone)
        kiev_date = kiev_datetime.strftime('%Y-%m-%d')
        kiev_time = kiev_datetime.strftime('%H:%M:%S')
        kiev_date_split = kiev_date.split('-')
        kiev_time_split = kiev_time.split(":")
        year = kiev_date_split[0]
        month = kiev_date_split[1]
        day = kiev_date_split[2]
        hour = kiev_time_split[0]
        minute = kiev_time_split[1]
        second = kiev_time_split[2] 
        if not schedule_dt:
            await asyncio.sleep(20)
        for sh in schedule_dt:
            if sh["date"] == f"{year}-{month}-{day}":
                for i in sh["clases"]:
                    time_s = f"{hour}:{minute}"
                    tm = i["time"]
                    time_obj = datetime.datetime.strptime(tm, '%H:%M') - datetime.timedelta(minutes=5)
                    n_tm = time_obj.strftime('%H:%M')
                    audience = i['audience']

                    try:
                        audience = int(audience)
                    except:
                        if not audience in audiences_correct:
                            audience = "Невизначено"
                    para = i["name"]
                    teather = i["teacher"]
                    if not check_skip(sh["day"], i["time"]):
                        if n_tm == time_s:
                            text = get_notes(teather)
                            markup = get_keyboard(text["buttons"])
                            text = f"Початок пари [{para}] о {tm}\nАудиторія: {audience}\n\n" + text["text"]
                            await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
                            await asyncio.sleep(55)
        await asyncio.sleep(10)

@dp.callback_query_handler(notes_cd.filter())
async def controller_notes(call: CallbackQuery, callback_data: dict):
    level = callback_data["level"]
    name = callback_data["name"]
    actions = {
        "0": notes_st,
        "1": show_note_link,
    }
    current_func = actions[level]
    if call.message.chat.type in (types.ChatType.GROUP, types.ChatType.SUPERGROUP):
        await asyncio.sleep(0.5)
    try:
        await current_func(
            call,
            level=level,
            name=name,
        )
    except aiogram.utils.exceptions.RetryAfter as err:
        await dp.bot.answer_callback_query(call.id, text=f'Виникла помилка!\n{err}')


@dp.callback_query_handler(schedule_cd.filter())
async def controller_main(call: CallbackQuery, callback_data: dict):
    level = callback_data["level"]
    day = callback_data["day"]
    teacher = callback_data["teacher"]
    actions = {
        "0": schedule_st_panel,
        "1": show_schedule,
        "2": show_note,
    }
    current_func = actions[level]
    if call.message.chat.type in (types.ChatType.GROUP, types.ChatType.SUPERGROUP):
        await asyncio.sleep(0.8)
    try:
        await current_func(
            call,
            day=day,
            teacher=teacher,
        )
    except aiogram.utils.exceptions.RetryAfter as err:
        time_sl = int(str(err).split(" ")[-2])
        logger.warning(err)
        await dp.bot.answer_callback_query(call.id, text=f'Забагато спроб переходу!\nЗачекайте {time_sl} секунд(-и)')
        await asyncio.sleep(time_sl)
        current_func = actions["0"]
        await current_func(
            call,
            day=day,
            teacher=teacher
        )


def main():
    asyncio.run(schedule_controller())

def checking_schedule():
    asyncio.run(load_schedule())

async def on_startup(dp):
    await bot.set_my_commands(commands)
    await load_notes()
    threading.Thread(target=main, daemon=True).start()
    threading.Thread(target=checking_schedule, daemon=True).start()



async def start_app():
    try:
        await dp.start_polling()
    except TerminatedByOtherGetUpdates:
        print("EROROR")
        sys.exit()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(start_app())

    loop.close()
  

