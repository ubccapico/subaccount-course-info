# -*- coding: utf-8 -*-
"""
Created on Thu Jul  5 14:15:25 2018

@author: jeremyh2
"""

#List of libraries needed, will automatically install if not present
from lib.canvas_blueprint import paginate_list
from lib.canvas_blueprint import get_associated_courses
from tqdm import tqdm
import pandas as pd
import re, getpass, json, requests

'''
Request the list of users for a course depending on requested type
Parameters:
    token: Canvas API token
    url: Canvas version URL
    course: ID of desired course
    user_type: type of user to find (ta, teacher, student)
Returns:
    A pandas dataframe that represents a list of people with that user_type
'''
def get_users(token, url, course, user_type):
    payload = {'enrollment_type[]': user_type}
    user_list = requests.get(url + '/api/v1/courses/{}/users'.format(course),
                             headers = {'Authorization': 'Bearer ' + token},
                             params = payload)
    user_list = paginate_list(user_list, token)
    return user_list

'''
Checks if there is a syllabus download link in 'Syllabus' Tab for course
Paramters:
    syllabus_body: The body of the syllabus
Returns:
    String signifying result, True, False
'''
def syllabus_presence(syllabus_body):

    list_here = re.findall(r'(title=\"(.*?).pdf\" href=\"(.*?)\")', syllabus_body)
    url_list = re.findall(r'(href=\"(.*?)\")', syllabus_body)

    length = len(list_here)
    url_length = len(url_list)

    if length != 0 and length == url_length:
        return 'True'
    else:
        if url_length != 0:
            return 'Link Present, possible syllabus'
        else:
            return 'False'

'''
Matches each course with its blueprint
Parameters:
    token: Canvas API token
    url: Canvas URL
    dataframe: Original dataframe to edit
    master: Master subaccount to look under for blueprints
Returns:
    A pandas dataframe with blueprint urls of each course added
'''
def find_blueprints(token, url, dataframe, master):
    master_list = requests.get(url + '/api/v1/accounts/{}/courses'.format(master),
                               headers = {'Authorization': 'Bearer ' + token})
    
    if not master_list.ok:
        print("Request failed... Aborting.")
        return dataframe
    
    returned_list = paginate_list(master_list, token)
    modified_table = dataframe
    
    print("Connecting Blueprints...")
    with tqdm(total = len(returned_list.index)) as pbar:
        for idx, course in returned_list.iterrows():
            pbar.update(1)
            course_is_blueprint = course['blueprint']
    
            if course_is_blueprint is True:
                c_id = course['id']
                blueprint_child = get_associated_courses(c_id, token, url)
     
                for index, child_courses in blueprint_child.iterrows():
    
                    if ((dataframe['Course ID'] == child_courses['id']).any()):
    
                        data_index = dataframe.loc[dataframe['Course ID'] == child_courses['id']].index.values.astype(int)[0]
    
                        course_url = 'https://canvas.ubc.ca/courses/{}'.format(c_id)
                        modified_table.at[data_index, 'Blueprint URL'] = course_url
                    else:
                        pass

    return modified_table

'''
Get courses in a subaccount (those blueprint associated or those not)
Params:
    account_id: Subaccount ID to look through
    token: Canvas API token
    url: Canvas url
    payload: True or False, whether we want blueprint associated child courses, or non-associated
Returns:
    Pandas dataframe list of courses
'''
def get_blueprint_associated_courses(account_id, token, url, payload):
    returned_list = None

    if payload is True:
        print('\nPlease wait. Finding blueprint associated courses...')
        payload_tbp = {'blueprint_associated': True}
        course_list_req_tbp = requests.get(url + '/api/v1/accounts/{}/courses?include[]=total_students&include[]=teachers&include[]=term&include[]=syllabus_body'.format(account_id),
                                       headers = {'Authorization': 'Bearer ' + token}, params = payload_tbp)

        returned_list = paginate_list(course_list_req_tbp, token)
    elif payload is False:
        print('\nPlease wait. Finding non-blueprint associated courses...')
        payload_tbf = {'blueprint_associated': False}
        course_list_req_tbf = requests.get(url + '/api/v1/accounts/{}/courses?include[]=total_students&include[]=teachers&include[]=term&include[]=syllabus_body'.format(account_id),
                                       headers = {'Authorization': 'Bearer ' + token}, params = payload_tbf)

        returned_list = paginate_list(course_list_req_tbf, token)

    return returned_list

'''
Creation of the result database
Params:
    dataframe: Original pandas dataframe/list of classes
    master: Master subaccount to look for bluepritns under
    input_term: Desired school term to look under (e.g. 2018W1)
Returns:
    A pandas dataframe with 'Account ID', 'Blueprint Associated', 'Blueprint URL' 'Course ID', 'Course URL', 'Course Name', 'Course Code', 'Instructors',
    'Enrolments', 'TA list', 'Observors', 'Published?', 'Term', & 'Syllabus Present?' for each course (each row is a course).
'''
def clean_up_dataframe(dataframe, master, input_term):

    course_list = dataframe

    course_list = course_list.sort_values(by='id')
    course_list = course_list [['account_id','Blueprint Associated','id','name','course_code', 'teachers','total_students',
                                'workflow_state','term','syllabus_body']]
    course_list.columns = ['Account ID', 'Blueprint Associated', 'Course ID', 'Course Name', 'Course Code', 'Instructors',
                           'Enrolments', 'Published?', 'Term', 'Syllabus Present?']
    course_list.insert(loc=2, column='Blueprint URL', value=None)
    course_list.insert(loc=4, column='Course URL', value=None)
    course_list.insert(loc=8, column='TA List', value=None)
    course_list.insert(loc=8, column='Observers', value=None)
    course_list['Comments'] = None

    course_list = course_list.reset_index(drop=True)
    for index, course in course_list.iterrows():

        course_term = course['Term']
        course_term_name = course_term['name']
        course_list.at[index, 'Term'] = course_term_name.upper()

    print('')

    if input_term.upper() != 'ALL':
        course_list = course_list[course_list.Term == input_term.upper()]

    course_list = course_list.reset_index(drop = True)

    length = len(course_list.index)
    start = length
    print("Getting course info...")
    with tqdm(total = length) as pbar_course:
        for index, course in course_list.iterrows():
            pbar_course.update(1)
            
            current_index = length - start
            start-=1
            if course['Term'].upper() != input_term.upper() and input_term.upper() != 'ALL':
                continue
    
            listed_inst = ""
            for teacher in course['Instructors']:
                listed_inst = listed_inst + teacher['display_name'] + ", "
    
            #print('Fetching Instructors for {}...'.format(course['Course Name']))
            listed_inst = listed_inst[:-2]
            course_list.at[current_index, 'Instructors'] = listed_inst
    
            #print('Fetching Course URLs for {}...'.format(course['Course Name']))
            course_id = course['Course ID']
            course_url = 'https://canvas.ubc.ca/courses/{}'.format(course_id)
            course_list.at[current_index, 'Course URL'] = course_url
    
            #print('Fetching TAs for {}...'.format(course['Course Name']))
            course_TAs = get_users(token, url, course_id, 'ta')
            TA_list = ''
            for index, users in course_TAs.iterrows():
                TA_list = TA_list + '{}, '.format(users['name'])
            course_list.at[current_index, 'TA List'] = TA_list[:-2]
    
            #print('Fetching Observers for {}...'.format(course['Course Name']))
            course_obs = get_users(token, url, course_id, 'observer')
            obs_list = ''
            for index, users in course_obs.iterrows():
                obs_list = obs_list + '{}, '.format(users['name'])
            course_list.at[current_index, 'Observers'] = obs_list[:-2]
    
            #print('Finding Syllabus for {}...'.format(course['Course Name']))
            temp = course.to_json(orient='index')
            temp = json.loads(temp)
            syllabus_body = str(temp[u'Syllabus Present?'])
            course_list.at[current_index, 'Syllabus Present?'] = syllabus_presence(syllabus_body)
    
    print('\nFinding All Blueprint Child Courses...')
    course_list = find_blueprints(token, url, course_list, master)

    return course_list

'''
Get raw info of all classes under a subaccount
Params:
    account_id: Subaccount ID
    token: Canvas API token
    url: Canvas URL
    master_id: Master Account ID to look for blueprints under
Returns:
    Prints to CSV, named {enteredTerm}.csv
'''
def get_subaccount_classes(account_id, token, url, master_id):

    print('\nGetting courses...')
    course_list_tbp = None
    try:
        course_list_tbp = get_blueprint_associated_courses(account_id, token, url, True)
        course_list_tbp['Blueprint Associated'] = True
    except:
        course_list_tbp = None
        print("No courses associated with a blueprint.")

    course_list_tbf = None
    try:
        course_list_tbf = get_blueprint_associated_courses(account_id, token, url, False)
        course_list_tbf['Blueprint Associated'] = False
    except:
        course_list_tbp = None
        print("No courses not associated with a blueprint.")

    course_list = None
    if course_list_tbp is not None and course_list_tbf is not None:
        course_list = pd.concat([course_list_tbp, course_list_tbf], sort=True, ignore_index=True)
    elif course_list_tbf is not None:
        course_list = course_list_tbf
    elif course_list_tbp is not None:
        course_list = course_list_tbp
    else:
        course_list = None

    if course_list is not None:
        input_term = input('Enter desired term (e.g. 2018W1) or ALL (for all terms): ')

        course_list = clean_up_dataframe(course_list, master_id, input_term)
        course_list.to_csv ('Account {} - {} Courses.csv'.format(account_id, input_term), index=False)

    return course_list

if __name__ == "__main__":
    token = getpass.getpass("Please enter your token here: ")
    url = 'https://ubc.instructure.com'
    master_id = input("Master Subaccount ID (for blueprints) to look through: ")
    account_id = input("Chosen Subaccount ID (ccontaining ourses you are intereseted in) to get \
                       raw data for: ")

    course_list = get_subaccount_classes(account_id, token, url, master_id)
