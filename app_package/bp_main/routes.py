from flask import Blueprint
from flask import render_template, request, flash, redirect, send_from_directory, \
    current_app
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask_login import current_user
from ht_models import dict_sess, dict_engine, text, dict_base, Users, \
    Habits, UserHabitAssociations,UserHabitDays
from flask_login import login_required, login_user, logout_user, current_user
from app_package.bp_main.utils import create_list_of_recorded_habits, \
    get_user_habit_day_exists, remove_table_name_from_df, create_user_habits_wb
import pandas as pd


bp_main = Blueprint('bp_main', __name__)
sess_users = dict_sess['sess_users']
engine_users = dict_engine['engine_users']
Base_users = dict_base['Base_users']

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_bp_main = logging.getLogger(__name__)
logger_bp_main.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','main_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_bp_main.addHandler(file_handler)
logger_bp_main.addHandler(stream_handler)


@bp_main.route("/", methods=["GET","POST"])
def home():
    logger_bp_main.info(f"-- in home page route --")

    return render_template('main/home.html')


@bp_main.route("/log", methods=["GET","POST"])
@login_required
def log():
    logger_bp_main.info(f"-- in log page route --")
    today_date = datetime.now().strftime("%Y-%m-%d")
    user_habits = sess_users.query(UserHabitAssociations).filter_by(users_table_id=current_user.id).all()
    user_habits_list = []

    if len(user_habits) > 0:
        print("-- what is user_habits: ", user_habits)
        print("-- what is user_habits[0].habits: ", user_habits[0].habits)

        user_habits_list=[(i.habits.id, i.habits.habit_name) for i in user_habits]
        print("user_habits_list: ", user_habits_list)
        
    # if current_user.is_authenticated:
    #     print(current_user)

    #Make list of User Habit Days for Table

    # user_habit_days = [i for i in sess_users.query(UserHabitDays).filter_by(user_id=current_user.id).all()]
    # UserHabitDays(id: 1, habit_id: 1, user_id: 1, date: 2023-07-05 00:00:00)
    user_habit_days = [(i.id, 
                        i.habit_id, 
                        sess_users.query(Habits).filter_by(id=i.habit_id).first().habit_name, 
                        i.date.strftime("%Y-%m-%d")) for i in sess_users.query(
                        UserHabitDays).filter_by(user_id=current_user.id).all()]
    # (1, 'Read', '2023-07-05')
    column_names = ['Habit', 'Date','']
    print("user_habit_days: ", user_habit_days)


    if request.method == 'POST':
        if len(user_habits) > 0:
            formDict = request.form.to_dict()
            print("formDict: ", formDict)


            if formDict.get('delete_habit'):
                # print("FormDict: ", formDict.get('delete_habit'))
                logger_bp_main.info(f"-- removing habit UserHabitDay Id: {formDict.get('delete_habit')} --")
                sess_users.query(UserHabitDays).filter_by(id=formDict.get('delete_habit')).delete()
                sess_users.commit()
                return redirect(request.url)
            
            logger_bp_main.info(f"* Adding *")
            form_habit_id_list = create_list_of_recorded_habits(formDict)

            date_str = formDict.get('habit_date')
            print(f"What does habit_date look like: {date_str}")

            date_datetime = datetime.strptime(date_str, '%Y-%m-%d')

            # user_habits_list: [[habit_id, habit_name]]
            for habit in user_habits_list:
                # print("habit: ", habit[0], habit[1])
                # if user (has habit and its checked from the form) AND (no habit in that day)
                print("habit[0] ", str(habit[0]))
                print("form_habit_id_list ", form_habit_id_list)
                user_habit_day_exists = get_user_habit_day_exists(current_user.id, str(habit[0]), date_datetime)
                print("not user_habit_day_exists ", not user_habit_day_exists)
                if (str(habit[0]) in form_habit_id_list) and (not user_habit_day_exists) :
                    print("-- adding habit --")
                    new_log = UserHabitDays(user_id = current_user.id, habit_id= habit[0], date=date_datetime)
                    sess_users.add(new_log)
                    sess_users.commit()

                elif not (str(habit[0]) in form_habit_id_list):
                    print("-- removing habit --")
                    sess_users.query(UserHabitDays).filter_by(user_id=current_user.id, habit_id=habit[0], date=date_datetime).delete()
                    sess_users.commit()
            # for habit_id in habit_id_list:

            #     new_log = UserHabitDays(user_id = current_user.id, habit_id= habit_id, date=date_datetime)
            #     sess_users.add(new_log)
            #     sess_users.commit()

            #     logger_bp_main.info(f"-- habit_id: {habit_id} added --")
            flash('added habit', 'success')
            return redirect(request.url)
        

    return render_template('main/log.html', today_date = today_date, user_habits_list=user_habits_list,
                           column_names=column_names, user_habit_days=user_habit_days)

@bp_main.route('/user_habits', methods = ['GET', 'POST'])
@login_required
def user_habits():
    logger_bp_main.info(f"-- admin_page route --")

    # Make list of current user's habits
    user_associated_habits_list = sess_users.query(
        UserHabitAssociations).filter_by(users_table_id=current_user.id).all()
    user_habits_list = [(i.habits.id, i.habits.habit_name) for i in user_associated_habits_list]

    # Make list of habit's stored in db, but not by current_user (for add new habit dropdown)
    non_user_habits = sess_users.query(
        UserHabitAssociations).filter(UserHabitAssociations.users_table_id!=current_user.id).all()
    non_user_habits =  set([i.habits.habit_name for i in non_user_habits])



    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('formDict:::', formDict)
        if formDict.get('new_habit'):
            logger_bp_main.info(f"-- new_habit detected --")
            habit_name = formDict.get('new_habit')

            #check if habit already exits
            exiting_habits = sess_users.query(Habits).all()
            exiting_habits_lower_case = [i.habit_name.lower() for i in exiting_habits]
            if habit_name.lower() in exiting_habits_lower_case:
                new_habit = sess_users.query(Habits).filter_by(habit_name=habit_name).first()
            else:
                # Append new Habit to Habit table
                new_habit = Habits(habit_name=formDict.get('new_habit'))
                sess_users.add(new_habit)
                sess_users.commit()
            # Append to UserHabitAssociations Table
            new_user_habit_assoc = UserHabitAssociations(users_table_id=current_user.id, habits_table_id=new_habit.id)
            sess_users.add(new_user_habit_assoc)
            sess_users.commit()
            
            logger_bp_main.info(f"-- new_habit created: {new_habit.id}, for user_id: {current_user.id} --")
            flash(f'{habit_name} has been added!', 'success')
        if formDict.get('btn_delete_habit'):
            logger_bp_main.info(f"-- delete_habit detected --")
            habit_id  = formDict.get('habit_id')
            habit_name = formDict.get('habit_name')
            habit_name = sess_users.query(Habits).filter_by(id=habit_id).first().habit_name
            
            sess_users.query(UserHabitDays).filter_by(habit_id= habit_id).delete()
            sess_users.query(UserHabitAssociations).filter_by(users_table_id=current_user.id,habits_table_id= habit_id).delete()
            sess_users.query(Habits).filter_by(id=habit_id).delete()
            sess_users.commit()

            flash(f'{habit_name} has been deleted!', 'success')
        return redirect(request.url)
    
    return render_template('main/user_habits.html', user_habits_list=user_habits_list,
                            non_user_habits=non_user_habits)

@bp_main.route("/download_user_history", methods=["GET","POST"])
@login_required
def download_user_history():
    logger_bp_main.info(f"-- in download_user_history route --")
    metadata = Base_users.metadata

    table_name = 'user_habit_days'
    base_query = sess_users.query(metadata.tables[table_name])
    df_uhd = pd.read_sql(text(str(base_query)), engine_users.connect())
    df_uhd = remove_table_name_from_df(df_uhd, table_name)

    table_name = 'habits'
    base_query = sess_users.query(metadata.tables[table_name])
    df_h = pd.read_sql(text(str(base_query)), engine_users.connect())
    df_h = remove_table_name_from_df(df_h, table_name)

    df_uhd = df_uhd[df_uhd.user_id==current_user.id]

    # merge UserHabitDays with Habits on the appropriate id columns
    df_merged = pd.merge(df_uhd, df_h, left_on='habit_id', right_on='id', suffixes=('_uhd', '_h'))

    # Then, create a new dataframe with just the columns you're interested in
    df_for_download = df_merged[['habit_name', 'date']]

    filename = f"user{current_user.id}_habits_days.xlsx"
    path_and_filename = os.path.join(current_app.config['DIR_DB_AUXILARY_USER_HABITS_DOWNLOADS'], filename)

    wb = create_user_habits_wb(df_for_download)
    wb.save(filename=path_and_filename)

    # user_df.to_excel(os.path.join(current_app.config['DIR_DB_AUXILARY_USER_HABITS_DOWNLOADS'], filename))
    return send_from_directory(os.path.join(current_app.config['DIR_DB_AUXILARY_USER_HABITS_DOWNLOADS']),filename, as_attachment=True)
    

# Custom static data
@bp_main.route('/<db_root_dir_name>/<image_filename>')
def custom_static(db_root_dir_name, image_filename):
    
    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'), 'auxilary', \
        db_root_dir_name), image_filename)

