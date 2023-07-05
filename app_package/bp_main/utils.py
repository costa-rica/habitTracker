from ht_models import dict_sess, dict_engine, text, dict_base, Users, \
    Habits, UserHabitAssociations,UserHabitDays


def create_list_of_recorded_habits(formDict):
    habit_id_list = []

    for key,value in formDict.items():
        if key[:8] == 'checkbox':
            print("Key selected: ", key[9:])
            habit_id_list.append(key[9:])
    
    return habit_id_list