
from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, \
    abort, session, Response, current_app, send_from_directory, make_response
import bcrypt
from flask_login import login_required, login_user, logout_user, current_user
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from ht_models import dict_sess, dict_engine, text, dict_base, Users, \
    Habits, UserHabitDays
from app_package.bp_users.utils import send_reset_email, send_confirm_email, \
    userPermission
from app_package.bp_admin.utils import formatExcelHeader, \
    load_database_util, fix_recalls_wb_util, fix_investigations_wb_util
import pandas as pd
import shutil
from datetime import datetime
import openpyxl


import zipfile



#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_bp_admin = logging.getLogger(__name__)
logger_bp_admin.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','bp_admin.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_bp_admin.addHandler(file_handler)
logger_bp_admin.addHandler(stream_handler)


salt = bcrypt.gensalt()


bp_admin = Blueprint('bp_admin', __name__)
sess_users = dict_sess['sess_users']

@bp_admin.before_request
def before_request():
    logger_bp_admin.info(f"-- ***** in before_request route --")
    ###### TEMPORARILY_DOWN: redirects to under construction page ########
    if os.environ.get('TEMPORARILY_DOWN') == '1':
        if request.url != request.url_root + url_for('bp_main.temporarily_down')[1:]:
            # logger_bp_users.info("*** (logger_bp_users) Redirected ")
            logger_bp_admin.info(f'- request.referrer: {request.referrer}')
            logger_bp_admin.info(f'- request.url: {request.url}')
            return redirect(url_for('bp_main.temporarily_down'))


#### Replaced by user_habits page #####

# @bp_admin.route('/admin_page', methods = ['GET', 'POST'])
# @login_required
# def admin_page():
#     logger_bp_admin.info(f"-- admin_page route --")
#     users_list=[i.email for i in sess_users.query(Users).all()]
#     habits_list=[(i.id, i.habit_name) for i in sess_users.query(Habits).all()]
    
#     # with open(os.path.join(current_app.config['DIR_DB_FILES_UTILITY'],'added_users.txt')) as json_file:
#     #     get_users_dict=json.load(json_file)
#     #     json_file.close()
#     # get_users_list=list(get_users.keys())
#     if request.method == 'POST':
#         formDict = request.form.to_dict()
#         print('formDict:::', formDict)
#         if formDict.get('new_habit'):
#             logger_bp_admin.info(f"-- new_habit detected --")
#             habit_name = formDict.get('new_habit')
#             new_habit = Habits(habit_name=formDict.get('new_habit'))
#             sess_users.add(new_habit)
#             sess_users.commit()
#             flash(f'{habit_name} has been added!', 'success')
#         if formDict.get('btn_delete_habit'):
#             logger_bp_admin.info(f"-- delete_habit detected --")
#             habit_id  = formDict.get('habit_id')
#             habit_name = formDict.get('habit_name')
#             habit_name = sess_users.query(Habits).filter_by(id=habit_id).first().habit_name
#             sess_users.query(Habits).filter_by(id=habit_id).delete()
#             sess_users.query(UserHabitDays).filter_by(habit_id= habit_id).delete()
#             sess_users.commit()


#             flash(f'{habit_name} has been deleted!', 'success')
#         return redirect(request.url)
#     return render_template('admin/admin_habits.html', habits_list=habits_list)
#     # return render_template('admin/admin.html', users_list=get_users_dict)




@bp_admin.route('/database_page', methods=["GET","POST"])
@login_required
def database_page():
    tableNamesList=['investigations','tracking_inv','recalls','tracking_re','user']
    # tableNamesList= db.engine.table_names()
    legend='Database downloads'
    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('formDict::::', formDict)

        if formDict.get('build_workbook')=="True":
            
            #check if os.listdir(current_app.config['DIR_DB_FILES_DATABASE']), if no create:
            if not os.path.exists(current_app.config['DIR_DB_FILES_DATABASE']):
                # print('There is not database folder found???')
                os.mkdir(current_app.config['DIR_DB_FILES_DATABASE'])
            
            for file in os.listdir(current_app.config['DIR_DB_FILES_DATABASE']):
                os.remove(os.path.join(current_app.config['DIR_DB_FILES_DATABASE'], file))

            
            timeStamp = datetime.now().strftime("%y%m%d_%H%M%S")
            workbook_name=f"database_tables{timeStamp}.xlsx"
            print('reportName:::', workbook_name)
            excelObj=pd.ExcelWriter(os.path.join(current_app.config['DIR_DB_FILES_DATABASE'], workbook_name),
                date_format='yyyy/mm/dd', datetime_format='yyyy/mm/dd')
            workbook=excelObj.book
            
            dictKeyList=[i for i in list(formDict.keys()) if i in tableNamesList]
            dfDictionary={h : pd.read_sql_table(h, db.engine) for h in dictKeyList}
            for name, df in dfDictionary.items():
                if len(df)>900000:
                    flash(f'Too many rows in {name} table', 'warning')
                    return render_template('database.html',legend=legend, tableNamesList=tableNamesList)
                df.to_excel(excelObj,sheet_name=name, index=False)
                worksheet=excelObj.sheets[name]
                start_row=0
                formatExcelHeader(workbook,worksheet, df, start_row)
                print(name, ' table added to workbook')
                # if name=='dmrs':
                    # dmrDateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                    # worksheet.set_column(1,1, 15, dmrDateFormat)
                
            print('path of reports:::',os.path.join(current_app.config['DIR_DB_FILES_DATABASE'],str(workbook_name)))
            excelObj.close()
            print('excel object close')
            # return send_from_directory(current_app.config['DIR_DB_FILES_DATABASE'],workbook_name, as_attachment=True)
            return redirect(url_for('users.database_page'))

        elif formDict.get('download_db_workbook'):
            return redirect(url_for('users.download_db_workbook'))

        elif formDict.get('uploadFileButton'):
            # print('****uploadFileButton****')
            logger_bp_admin.info("* upload excel file to ")
            formDict = request.form.to_dict()
            filesDict = request.files.to_dict()
            # print('formDict:::',formDict)
            # print('filesDict:::', filesDict)
            
            
            if not os.path.exists(current_app.config['DIR_DB_FILES_TEMPORARY']):
                os.mkdir(current_app.config['DIR_DB_FILES_TEMPORARY'])
            
            file_type=formDict.get('file_type')
            uploadData=request.files['fileUpload']
            uploadFileName=uploadData.filename
            uploadData.save(os.path.join(current_app.config['DIR_DB_FILES_TEMPORARY'], uploadFileName))
            if file_type=="excel":
                wb = openpyxl.load_workbook(uploadData)
                sheetNames=json.dumps(wb.sheetnames)
                tableNamesList=json.dumps(tableNamesList)

                return redirect(url_for('bp_admin.database_upload',legend=legend,tableNamesList=tableNamesList,
                    sheetNames=sheetNames, uploadFileName=uploadFileName,file_type=file_type))
            return redirect(url_for('bp_admin.database_upload',legend=legend,uploadFileName=uploadFileName,
                file_type=file_type))
            # return redirect(url_for('users.database_page'))
        elif formDict.get('btn_database_delete') and formDict.get('database_delete_verify') == 'delete':
            logger_bp_admin.info("* Delete database")

            
            sess_users.query(Investigations).delete()
            sess_users.query(Tracking_inv).delete()
            sess_users.query(Saved_queries_inv).delete()
            sess_users.query(Recalls).delete()
            sess_users.query(Tracking_re).delete()
            sess_users.query(Saved_queries_re).delete()
            sess_users.commit()

            logger_bp_admin.info(f"- database (except users table) deleted by: {current_user.email}")
            flash("Data tables (except for users table) successfully deleted", "warning")
            return redirect(request.url)

    return render_template('admin/database_page.html', legend=legend, tableNamesList=tableNamesList)



@bp_admin.route("/download_db_workbook", methods=["GET","POST"])
@login_required
def download_db_workbook():
    # workbook_name=request.args.get('workbook_name')
    workbook_name = os.listdir(current_app.config['DIR_DB_FILES_DATABASE'])[0]
    print('file:::', os.path.join(current_app.root_path, 'static','files_database'),workbook_name)
    file_path = r'D:\OneDrive\Documents\professional\20210610kmDashboard2.0\fileShareApp\static\files_database\\'
    
    return send_from_directory(os.path.join(current_app.config['DIR_DB_FILES_DATABASE']),workbook_name, as_attachment=True)


@bp_admin.route('/database_upload', methods=["GET","POST"])
@login_required
def database_upload():
    logger_bp_admin.info("- in database_upload route")
    file_type=request.args.get('file_type')
    if file_type=='excel':
        tableNamesList=json.loads(request.args['tableNamesList'])
        sheetNames=json.loads(request.args['sheetNames'])
    uploadFileName=request.args.get('uploadFileName')
    legend='Upload Data File to Database'
    # uploadFlag=True
    limit_upload_flag='checked'
    
    if request.method == 'POST':
        
        formDict = request.form.to_dict()
        # print('formDict::::', formDict)
        if formDict.get('appendExcel'):
            
            uploaded_file=os.path.join(current_app.config['DIR_DB_FILES_TEMPORARY'], uploadFileName)
            # print('uploaded_file::::',uploaded_file)
            if file_type=='excel':
                logger_bp_admin.info("- in file_type=='excel'")
                sheet_upload_status = []
                for sheet in sheetNames:
                    logger_bp_admin.info(f"- in sheet: {sheet}")
                    sheetUpload=pd.read_excel(uploaded_file,engine='openpyxl',sheet_name=sheet)
                    if sheet=='user':
                        existing_emails=[i[0] for i in sess_users.query(Users.email).all()]
                        sheetUpload=pd.read_excel(uploaded_file,engine='openpyxl',sheet_name='user')
                        sheetUpload=sheetUpload[~sheetUpload['email'].isin(existing_emails)]

                    elif formDict.get(sheet) in ['investigations','recalls']:
                        sheetUpload['date_updated']=datetime.now()
                        if formDict.get(sheet) =='recalls':
                            sheetUpload=fix_recalls_wb_util(sheetUpload,uploadFileName)
                        elif formDict.get(sheet) =='investigations':
                            sheetUpload=fix_investigations_wb_util(sheetUpload)

                    try:
                        if sheet == 'user':
                            sheetUpload.to_sql('users',con=engine, if_exists='append', index=False)
                        elif sheet == 'recalls':
                            sheetUpload["CONSEQUENCE_DEFECT"] = sheetUpload["CONSEQUENCE_DEFCT"]
                            sheetUpload.drop(['CONSEQUENCE_DEFCT'], axis=1, inplace = True)
                            sheetUpload.to_sql(formDict.get(sheet),con=engine, if_exists='append', index=False)
                        else:
                            sheetUpload.to_sql(formDict.get(sheet),con=engine, if_exists='append', index=False)
                    
                        # df_update.to_sql(table_name, con=engine, if_exists='append', index=False)
                        # print('upload SUCCESS!: ', sheet)
                        logger_bp_admin.info(f"upload SUCCESS!:: {sheet}")
                        sheet_upload_status.append(f"{sheet}: success")
                    except IndexError:
                        logger_bp_admin.info(f"except IndexError:: {IndexError}")
                        # return redirect(url_for('bp_admin.database_page',legend=legend,
                        #     tableNamesList=tableNamesList, sheetNames=sheetNames))
                        sheet_upload_status.append(f"{sheet}: fail")
                    except:
                        logger_bp_admin.info(f"except another error:: {sheet}")
                        # os.remove(os.path.join(current_app.config['DIR_DB_FILES_TEMPORARY'], uploadFileName))
                        sheet_upload_status.append(f"{sheet}: fail")

                        # flash(f"""Problem uploading {sheet} table. Check for 1)uniquness with id or RECORD_ID 2)date columns
                        #     are in a date format in excel.""", 'warning')
                        # return redirect(url_for('bp_admin.database_page',legend=legend,
                        #     tableNamesList=tableNamesList, sheetNames=sheetNames))
                    #clear files_temp folder
                for file in os.listdir(current_app.config['DIR_DB_FILES_TEMPORARY']):
                    os.remove(os.path.join(current_app.config['DIR_DB_FILES_TEMPORARY'], file))
                status_message =""
                for sheet_message in sheet_upload_status:
                    status_message = status_message +sheet_message + ",\n"
                flash(f'Table sheet status: {status_message}', 'info')
                return redirect(url_for('bp_admin.database_page',legend=legend,
                    tableNamesList=tableNamesList, sheetNames=sheetNames))

                
            elif file_type=='text':
                zipfile.ZipFile(uploaded_file).extractall(path=current_app.config['DIR_DB_FILES_TEMPORARY'])
                
                
                text_file_name=[x for x in os.listdir(current_app.config['DIR_DB_FILES_TEMPORARY']) if x[-4:]=='.txt'][0]
                limit_upload_flag=formDict.get('limit_upload_flag')
                
                flash_message=load_database_util(text_file_name, limit_upload_flag)
                
                
                
                for file in os.listdir(current_app.config['DIR_DB_FILES_TEMPORARY']):
                    os.remove(os.path.join(current_app.config['DIR_DB_FILES_TEMPORARY'], file))

                    
                flash(flash_message[0], flash_message[1])

                return redirect(url_for('bp_admin.database_page',legend=legend))

    
    if file_type=='excel':
        return render_template('admin/database_upload.html',legend=legend,tableNamesList=tableNamesList,
                    sheetNames=sheetNames, uploadFileName=uploadFileName,
                    # uploadFlag=uploadFlag,
                    file_type=file_type)
    else:
        return render_template('admin/database_upload.html',legend=legend,
                    uploadFileName=uploadFileName,
                    # uploadFlag=uploadFlag,
                    file_type=file_type,limit_upload_flag=limit_upload_flag)



# @bp_admin.route("/delete_habit/<id>", methods=["GET","POST"])
# @login_required
# def delete_habit(id):
#     logger_bp_admin.info(f"-- delete_habit route, id: {id} --")
#     habit_name = sess_users.query(Habits).filter_by(id=id).first().habit_name
#     sess_users.query(Habits).filter_by(id=id).delete()
#     sess_users.query(UserHabitDays).filter_by(habits_table_id= id).delete()
#     sess_users.commit()

#     flash(f'{habit_name} has been deleted!', 'success')
#     return redirect(request.referrer)

@bp_admin.route("/delete_user/<email>", methods=["GET","POST"])
@login_required
def delete_user(email):
    print('did we get here????', email)
    with open(os.path.join(current_app.config['DIR_DB_FILES_UTILITY'],'added_users.txt')) as json_file:
        get_users_dict=json.load(json_file)
        json_file.close()
    
    del get_users_dict[email]
    
    added_users_file=os.path.join(current_app.config['DIR_DB_FILES_UTILITY'], 'added_users.txt')
    with open(added_users_file, 'w') as json_file:
        json.dump(get_users_dict, json_file)
        
    if len(sess.query(User).filter_by(email=email).all())>0:
        sess_users.query(User).filter_by(email=email).delete()
        sess_users.commit()
    
    
    
    flash(f'{email} has been deleted!', 'success')
    return redirect(url_for('users.admin'))

