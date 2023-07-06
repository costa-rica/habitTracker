from ht_models import dict_sess, dict_engine, text, dict_base, Users, \
    Habits, UserHabitAssociations,UserHabitDays

sess_users = dict_sess['sess_users']

def create_list_of_recorded_habits(formDict):
    habit_id_list = []

    for key,value in formDict.items():
        if key[:8] == 'checkbox':
            print("Key selected: ", key[9:])
            habit_id_list.append(key[9:])
    
    return habit_id_list

def userHabitDayExists(user_id, habit_id, date):
    user_habit_day = sess_users.query(UserHabitDays).filter_by(
        user_id=user_id, habit_id = habit_id, date = date
    ).all()
    print('- in userHabitDayExists -')
    print("user_habit_day: ", user_habit_day)
    if len(user_habit_day) > 0:
        return True
    else:
        return False