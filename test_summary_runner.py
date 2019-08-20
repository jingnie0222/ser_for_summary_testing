#!/usr/bin/python3
#coding=utf-8

import os
import sys
import pymysql
import time
import asycommands
import pexpect
from sum_conf import *

###### global  ######
db = pymysql.connect(database_host, database_user, database_pass ,database_db, charset="utf8")
cursor = db.cursor()

mission_id = int(sys.argv[1])
###### global  ######


def get_now_time():
    timeArray = time.localtime()
    return  time.strftime("%Y-%m-%d %H:%M:%S", timeArray)

def get_task_info():
    sql = "SELECT testsvn, basesvn, testitem, newconfip, newconfuser, newconfpassw, newconfpath, newdataip, newdatauser, newdatapassw, newdatapath FROM %s where id='%d'" % (database_table, mission_id)
    cursor.execute(sql)
    data = cursor.fetchone()
    db.commit()
    sql = "UPDATE %s set start_time='%s', status = 2 where id=%d" % (database_table, get_now_time() ,mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as err:
        db.rollback()
        print("[get_task_info]:%s" % err)
    return data
    
def set_status(stat):
    sql = "UPDATE %s set status=%d, end_time='%s' where id=%d;" % (database_table, stat, get_now_time(), mission_id)
    cursor.execute(sql)
    try:
        db.commit()
    except Exception as err:
        db.rollback()
        print("[set_status:%s] % err")
        
    if (stat != 1):
        #clean_proc()
        pass
        
def clean_proc():
    os.popen('killall -9 memcached lt-memdb_daemon sggp lt-webcached')
    time.sleep(3)

    return
    
def update_errorlog(log):
    time_str = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
    log = log.replace("'", "\\'")
    sql = "UPDATE %s set errorlog=CONCAT(errorlog, '[%s] %s') where id=%d;" % (database_table, time_str, log, mission_id)
    print(sql)
    cursor.execute(sql)
    data = cursor.fetchone()
    try:
        db.commit()
    except Exception as err:
        print('[update_errorlog:%s]' % err)
    return data

def sync_ol_to_local(rsync_type):

    if rsync_type == 'data':
        base_path = root_path + base_data
        test_path = root_path + test_data
        os.popen('rm -rf %s' % test_path)
    if rsync_type == 'conf':
        base_path = root_path + base_conf
        test_path = root_path + test_conf
        os.popen('rm -rf %s' % test_path)

    if os.path.exists(base_path) == False:
        print("save ol_%s's path not exists, mkdir -p" % rsync_type)
        update_errorlog("ol_%s path not exists, mkdir -p\n" % rsync_type)
        os.popen("mkdir -p " + base_path)

    update_errorlog("start rsync ol_%s to local\n" % rsync_type)

    #对路径格式做一定的容错处理
    rsync_path = online_path
    if  rsync_path[0] == "/":
        rsync_path = rsync_path[1:]
    if (rsync_path[-1] != "/"):
        rsync_path = rsync_path + "/"
    rsync_path = rsync_path + rsync_type + "/"
    
    arg = "%s::odin/%s" % (online_host, rsync_path)
    
    arg2 = base_path
    if base_path[-1] != "/":
        arg2 = base_path + "/"

    stdlog = ""
    errlog = ""
    
    asycmd = asycommands.TrAsyCommands(timeout=30*60)
    for iotype, line in asycmd.execute_with_data(['rsync', '-ravl', arg, arg2], shell=False):
        if iotype == 1:
            stdlog += line + '\n'
            print("[sync_ol_to_local] stdlog:%s" % line)
        elif iotype == 2:
            errlog += line + '\n'
            print("[sync_ol_to_local] errlog:%s" % line)
            
    if (asycmd.return_code() != 0):
        update_errorlog("rsync ol_%s to local Error\n" % rsync_type)
        update_errorlog(errlog)
        return -1
        
    update_errorlog("rsync ol_%s to local Success\n" % rsync_type)
    
    #拷贝norm_onsum01/data/base下的软链文件
    if rsync_type == 'data':
    
        if os.path.exists(symbolic_link_path) == False:
            print("save symbolic_link path not exists, mkdir -p")
            update_errorlog("symbolic_link path not exists, mkdir -p\n")
            os.popen("mkdir -p " + symbolic_link_path)
            
        for iotype, line in asycmd.execute_with_data(['rsync', '-ravlu', 'rsync.query001.web.djt.ted::odin/search/odin/daemon/data_agent/data/base/', '/search/odin/daemon/data_agent/data/base/'], shell=False):
            if iotype == 1:
                stdlog += line + '\n'
                #print("[sync_ol_to_local] stdlog:%s", line)
            elif iotype == 2:
                errlog += line + '\n'
                #print("[sync_ol_to_local] errlog:%s", line)
    
        if (asycmd.return_code() != 0):
            update_errorlog("rsync symbolic link file to local Error\n")
            update_errorlog(errlog)
            return -1
            
        update_errorlog("rsync symbolic link file to local Success\n")
     
     
    #处理conf下多余的文件
    if rsync_type == 'conf':
        os.popen("rm -rf " + base_path + "/{1.djt,1.gd,gd,js,1.tc}")
    
    
    #copy test_data or test_conf
    try:
        os.popen('cp -r  %s %s' %(base_path, test_path))
        update_errorlog("copy test_%s Success\n" % rsync_type)
    except Exception as err:
        update_errorlog("copy test_%s Error:%s\n" % (rsync_type,err))
        return -1
            
    return 0


def scp_new_test_env(scp_type, ip, user, passw, datapath):
    if scp_type == 'data':
        local_path = root_path + test_data
    if scp_type == 'conf':
        local_path = root_path + test_conf
        
    cmdline = 'scp -r %s@%s:%s/* %s/' %(user, ip, datapath, local_path)
    update_errorlog("cmdline: %s\n" % cmdline)
    update_errorlog("passwd: %s\n" % passw)
    update_errorlog("datapath: %s\n" % datapath)

    update_errorlog("try scp new_test_%s to local\n" % scp_type)
    
    pat_list = [r'assword:', r'yes/no', 'please try again', pexpect.EOF, pexpect.TIMEOUT]
    
    try:
        child = pexpect.spawn(cmdline, timeout=1800)       
    except Exception as err:
        update_errorlog("[scp_new_test_env]:[%s] %s\n" %(scp_type, err))
        return -1
    
    except_result = child.expect(pat_list)
    #expect最后返回0表示匹配到了所需的关键字, 如果后面的匹配关键字是一个列表的话，就会返回一个数字表示匹配到了列表中第几个关键字，从 0 开始计算;
    #关键字一旦匹配，就会返回0表示匹配成功，但是如果一直匹配不到呢？默认是会一直等下去，但是如果设置了 timeout 的话就会超时
        
    if except_result == 0:
        child.sendline(passw)
        except_result = child.expect(pat_list)
        
    elif except_result == 1:
        child.sendline('yes')
        except_result = child.expect(pat_list)  
        
    elif except_result == 3 or except_result == 4:
        update_errorlog("[scp_new_test_env] eof or timeout\n")
        return -1
      
    if except_result == 1:
        child.sendline(passw)
        except_result = child.expect(pat_list)
        
    elif except_result == 2:
        update_errorlog("[scp_new_test_env] username or passwd wrong\n")
        return -1
        
    elif except_result == 3:
        return 0
    
    elif except_result == 4:
        update_errorlog("[scp_new_test_env] timeout\n")
        return -1 
        
    if except_result == 3:
        return 0 


def main():

    ### get task info
    (testsvn, basesvn, testitem, newconfip, newconfuser, newconfpassw, newconfpath, newdataip, newdatauser, newdatapassw, newdatapath) = get_task_info()
    print(testsvn, basesvn, testitem, newconfip, newconfuser, newconfpassw, newconfpath, newdataip, newdatauser, newdatapassw, newdatapath)
    
    ### rsync ol_data to local
    ret_sync_ol_data = sync_ol_to_local('data')
    if ret_sync_ol_data != 0:
        update_errorlog("sync_ol_data_to_local Error, pls check\n")
        set_status(3)
        return -1
    
    ### rsync conf to local
    ret_sync_ol_conf = sync_ol_to_local('conf')
    if ret_sync_ol_conf != 0:
        update_errorlog("sync_ol_conf_to_local Error, pls check\n")
        set_status(3)
        return -1
    
    
    ### scp test_data to local
    if (newdataip != "" and newdatauser != "" and newdatapassw != "" and newdatapath != ""):
        update_errorlog("start try scp new_test_data to local")
        ret = scp_new_test_env('data', newdataip, newdatauser, newdatapassw, newdatapath)
        if ret != 0:
            update_errorlog("scp new_test_data Error, pls check\n")
            set_status(3)
            return -1
            
    update_errorlog("scp new_test_data OK\n")            
    
    ### scp test_conf to local
    if (newconfip != "" and newconfuser != "" and newconfpassw != "" and newconfpath != ""):
        update_errorlog("start try scp new_test_conf to local")
        ret = scp_new_test_env('conf', newconfip, newconfuser, newconfpassw, newconfpath)
        if ret != 0:               
            update_errorlog("scp new_test_conf Error, pls check\n")
            set_status(3)
            return -1
    
    update_errorlog("scp new_test_conf OK\n")
    



    
        

if __name__ == "__main__":
    main()