# -*- coding: utf-8 -*-
"""
Created on Tue Jul  3 13:13:02 2018

@author: jeremyh2
"""

#List of libraries needed, will automatically install if not present
try:
    import requests
except:
    import pip
    pip.main(['install', 'requests'])
    import requests

try:
    import pandas as pd
except:
    import pip
    pip.main(['install', 'pandas'])
    import pandas as pd

try:
    import json
except:
    import pip
    pip.main(['install', 'json'])
    import json

'''
Helper function that gets Canvas course information.
Parameters:
    course_id: ID of Canvas course
    token: User-generated API token
    url: URL of Canvas instance
Returns:
    Course object (JSON)
'''
def get_course_info(course_id, token, url):

    courseInfo =  requests.get(url + '/api/v1/courses/' + str(course_id) + '?include[]=course_image',
                               headers =  {'Authorization': 'Bearer ' + token})
    info = json.loads(courseInfo.text)
    #print(info[u'image_download_url'])
    return info

'''
Helper function that gets a list of courses associated with a blueprint course.
Parameters:
    blue_id: Blueprint course ID on Canvas
    token: User-generated API token
    url: URL of Canvas instance
'''
def get_associated_courses(blue_id, token, url):
    courseInfo =  requests.get(url + '/api/v1/courses/' + str(blue_id) + '/blueprint_templates/' + 'default' + '/associated_courses',
                               headers =  {'Authorization': 'Bearer ' + token})
    CI_table = pd.read_json(courseInfo.text)
    
    #grabs and concats pages
    while courseInfo.links['current']['url'] != courseInfo.links['last']['url']:
        courseInfo =  requests.get(courseInfo.links['next']['url'],
                     headers= {'Authorization': 'Bearer ' + token})
        CI_sub_table = pd.read_json(courseInfo.text)
        CI_table= pd.concat([CI_table, CI_sub_table], sort=True)
        CI_table= CI_table.reset_index(drop=True)

    return CI_table

def paginate_list(sub_list, token):
    json_list = pd.read_json(sub_list.text)
    
    while sub_list.links['current']['url'] != sub_list.links['last']['url']:
        sub_list =  requests.get(sub_list.links['next']['url'],
                     headers= {'Authorization': 'Bearer ' + token})
        admin_sub_table = pd.read_json(sub_list.text)
        json_list= pd.concat([json_list, admin_sub_table], sort=True)
        json_list=json_list.reset_index(drop=True)
    
    return json_list

def print_subaccount_tree(account_id, spaces, token, url):
    sub_list = requests.get(url + '/api/v1/accounts/{}/sub_accounts'.format(account_id),
                            headers = {'Authorization': 'Bearer ' + token})
    
    json_list = paginate_list(sub_list, token)
    
    for index, subaccount in json_list.iterrows():
        
        for x in range(spaces):
            print(" ", end="")
        
        print(subaccount['name'])
        child_id = str(subaccount['id'])
        print_subaccount_tree(child_id, spaces + 1, token, url)
