#!/usr/bin/python3
#coding=utf-8

import subprocess
import pymysql
import time
import os
from sum_conf import *

database_host="10.144.96.115"
database_db="summary_test"
database_table="TestSummary_testsummary"
database_user="root"
database_pass="lzxg@webqa"

#当前机器的IP(10.134.96.64)
local_ip = os.popen("sogou-host -a | head -1").read().replace('\n', '')

log_fd = open(log_file, 'w')

def get_running_id():
    sql = "SELECT id FROM %s where status=2 and runningIP='%s' limit 1" % (database_table,local_ip)
    cursor.execute(sql)
    data = cursor.fetchone()
    db.commit()
    if data is not None:
        return data[0]
    return -1
    
def get_my_id():
    sql = "SELECT id FROM %s where status=1 and runningIP='%s' limit 1" % (database_table,local_ip)
    cursor.execute(sql)
    data = cursor.fetchone()
    db.commit()
    if data is not None:
        return data[0]
    return -1

def get_cancel_id():
    sql = "SELECT id FROM %s where status=6 and runningIP='%s' limit 1" % (database_table,local_ip)
    cursor.execute(sql)
    data = cursor.fetchone()
    db.commit()
    if data is not None:
        return data[0]
    return -1


def main():

    task_list = {}
    while True:      
        time.sleep(2)
        running_id = get_running_id()
        print("running_id:%d" % running_id)
        if running_id != -1:
            continue
                
        #检查子进程是否结束，不为None表示进程结束       
        for k in list(task_list.keys()):
            if task_list[k].poll != None:
                del task_list[k]
            
        mission_id = get_my_id()
        if mission_id != -1:
            child = subprocess.Popen(['/usr/local/bin/python3', 'test_summary_runner.py','%d' % mission_id], shell = False, stdout = log_fd, stderr = log_fd, cwd=testsummary_path)
            task_list[mission_id] = child

        cancel_id = get_cancel_id()
        print("cancel_id:%d" % cancel_id)
        if cancel_id == -1:
            continue
        if cancel_id in task_list:
            task_list[cancel_id].send_signal(10)
        else:
            sql = "UPDATE %s set status = 5 WHERE id = %d" % (database_table,cancel_id)
            cursor.execute(sql)
            try:
                db.commit() 
            except:            
                db.rollback()
           

if __name__ == '__main__':
    db = pymysql.connect(database_host, database_user, database_pass ,database_db, charset="utf8")
    cursor = db.cursor()
    main()


