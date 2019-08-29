#!/usr/bin/python3
#coding=utf-8

import os
import sys
import pymysql
import time
import asycommands
import pexpect
import svnpkg
import subprocess
import psutil
import myconfigparser
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
    #print(sql)
    cursor.execute(sql)
    data = cursor.fetchone()
    try:
        db.commit()
    except Exception as err:
        print('[update_errorlog:%s]' % err)
    return data

def get_proc_status(pid):
    try:
        p = psutil.Process(pid)
    except:
        return -1
    if (p.status() == "running"):
        return 0
    elif (p.status() == "sleeping"):
        return 1
    return 2
    

def wait_to_die(pid, interval):
    while get_proc_status(pid) != -1:
        time.sleep(interval)
        if (interval > 10):
            interval = interval/2


def modify_config(file, sec, key, value):
#修改file配置文件中，sec下的配置项为key的value
    if not os.path.exists(file):
        update_errorlog("[modify_config] file:%s is not exist\n" % file)
        return -1
    try:
        cf = myconfigparser.MyConfigParser()
        cf.read(file)
        if sec and key and value:
            key = '"' + key + '"'
            value = '"' + value + '"'
            cf.set(sec, key, value)
            with open(file, 'w') as f:
                cf.write(f, space_around_delimiters=False)
        return 0
    except Exception as err:
        update_errorlog("[modify_config]:%s" % err)
        return -1
            

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
      
    if except_result == 0:
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
    else:
        return -1


def checkcode_env(path, svn):
    #print("path:%s" % path)   
    if os.path.exists(path) == False:
        update_errorlog("%s not exists, mkdir -p\n" % path)
        os.popen("mkdir -p " + path)

    update_errorlog("start check code: %s\n" % path)

    mysvn = svnpkg.SvnPackage("qa_svnreader", "New$oGou4U!")

    for line in svn.split("\n"):
        line = line.strip()
        pos = line.find('=')
        key = line[0:pos]
        value = line[pos+1:]
        print("value:%s" % value)
        if (value.find('http://') != 0):
            update_errorlog("url format error: %s\n" % line)
            return -1
        key_path = os.path.join(path, key)

        url = ""
        if (mysvn.svn_info(key_path) != 0):
        #no path, then checkout
            ret = mysvn.svn_co(value, key_path)
            if (ret != 0):
                update_errorlog("[checkcode_env]check %s error:%s\n" % (key, mysvn.get_errlog()))
                return 1
            else:
                mysvn.svn_info(key_path)
                for log_line in mysvn.get_stdlog().split('\n'):
                    if (log_line.find("URL:") == 0):
                        url = log_line.split(' ')[1]
                        break          
                update_errorlog("check OK %s -> %s\n" % (key, url))
        else:
        #path exists, then switch
            ret = mysvn.svn_sw(value, key_path)
            if (ret != 0):
                update_errorlog("[checkcode_env]svn sw %s error:%s\n" % (key, mysvn.get_errlog()))
                return 1
            else:
                mysvn.svn_info(key_path)
                for log_line in mysvn.get_stdlog().split('\n'):
                    if (log_line.find("URL:") == 0):
                        url = log_line.split(' ')[1]
                        break
                update_errorlog("check OK %s -> %s\n" % (key, url))
                
    update_errorlog("code checkout Success\n")
    return 0


def make_env(path):
    asycmd = asycommands.TrAsyCommands(timeout=300)
    make_log = ""
    for iotype, line in asycmd.execute_with_data(['make', '-j'], shell=False, cwd = path):
        if iotype == 2:
            make_log += line + "\n"
            
    if (asycmd.return_code() != 0):#timeout or error, then try again
        make_log = ""
        for iotype, line in asycmd.execute_with_data(['make', '-j'], shell=False, cwd = path):
            if iotype == 2:
                make_log += line + "\n"
    if (asycmd.return_code() != 0):
        update_errorlog(make_log)
        return -1
    update_errorlog("Make Success\n")
    return 0


def lanch(path, start_script, port, log):
# rules: start_script must put pid in `PID` file: echo $! > PID
# return a tuple(retcode, pid)

    pid = -1
    asycmd = asycommands.TrAsyCommands(timeout=30)
    #asycmd_list.append(asycmd)
    child = subprocess.Popen(['/bin/sh', start_script], shell=False, cwd = path, stderr = subprocess.PIPE)
    child.wait()
    
    if (child.returncode != 0):
        log.append(child.stderr.read())
        print("start_time=%d, pid=%s" % (-1, pid))
        return (-1, pid)
        
    for iotype, line in asycmd.execute_with_data(['/bin/cat', path + "/PID"], shell=False):
        if (iotype == 1 and line != ""):
            try:
                pid = int(line)
            except:
                continue
    if (pid == -1):
        print("start_time=%d, pid=%s" % (-2, pid))
        return (-2, pid)
        
    proc = None
    try:
        proc = psutil.Process(pid)
    except:
        log.append("process %d is not alive" % pid)
        print("start_time=%d, pid=%s" % (-3, pid))
        return (-3, pid)
    
    #启动压力工具时，port参数为-1，因为压力工具没有监听端口
    if port == -1:
        return (0, pid)
    
    #通过判断进程的端口号是否在监听，来判断进程是否存活
    is_alive = True
    start_time = 0
    #proc_list.append(pid)
    while is_alive:
        try:
            conn_list = proc.connections()
        except:
            is_alive = False
            break
            
        listened = False
        for conn in conn_list:
            #lquery的端口号状态为None，其余一般都是LISTEN
            if conn.status == "LISTEN" or conn.status == "NONE" and conn.laddr[1] == port:
                listened = True
                break
        if listened:
            break
        time.sleep(1)
        start_time += 1
        
    if not is_alive:
        log.append("process start failed:%s" % path)
        #proc_list.remove(pid)
        print("start_time=%d, pid=%s" % (-3, pid))
        return (-3, pid)
        
    return (start_time, pid)


def check_lanch(path, start_script, port, err_name):
    log = []
    if (path == ""):
        return 0
    log_file = path + err_name
    asycmd = asycommands.TrAsyCommands(timeout=30)
    #asycmd_list.append(asycmd)

    (ret, pid) = lanch(path, start_script, port, log)
    if (ret < 0):
        time.sleep(0.5)
        up_log = ""
        for line in log:
            up_log += "%s\n" % line
        update_errorlog("%s\n" % up_log)
        
        up_log = ""
        for iotype, line in asycmd.execute_with_data(['/bin/tail', '-50', log_file], shell=False):
            up_log += line + '\n'
        update_errorlog("%s\n" % up_log)
    return ret, pid 


def prepare_symbolic_link(desc_path):
    #在Websummary目录下对data、conf、start.sh进行软链
    try:
           
        if os.path.exists(desc_path + 'data') == True:
            os.popen("rm -rf %s" % desc_path + 'data')               
        if os.path.exists(desc_path + 'conf') == True:
            os.popen("rm -rf %s" % desc_path + 'conf')       
        if os.path.exists(desc_path + 'start.sh') == True:
            os.popen("rm -rf %s" % desc_path + 'start.sh')
        
        #对base环境创建软链
        if 'base_src' in desc_path:
            os.popen("ln -s %s %s" % (root_path + base_data, desc_path + 'data'))
            os.popen("ln -s %s %s" % (root_path + base_conf, desc_path + 'conf'))
            os.popen("ln -s %s %s" % (root_path + base_script, desc_path + 'start.sh'))
            return 0
        
        #对test环境创建软链        
        if 'test_src' in desc_path:
            os.popen("ln -s %s %s" % (root_path + test_data, desc_path + 'data'))
            os.popen("ln -s %s %s" % (root_path + test_conf, desc_path + 'conf'))
            os.popen("ln -s %s %s" % (root_path + test_script, desc_path + 'start.sh'))
            return 0
            
    except Exception as err:
        update_errorlog("[prepare_symbolic_link]:%s" % err)
        return -1


def get_perf_res(log_file, result):
    if os.path.exists(log_file) == False:
        result.append(log_file + " is not exists")
        return -1
    asycmd = asycommands.TrAsyCommands(timeout=180)
    #asycmd_list.append(asycmd)
    for iotype, line in asycmd.execute_with_data(['/bin/awk', '-f' , perf_tool, log_file], shell=False):
        result.append(line)
    return asycmd.return_code()        


def performance(base_path, test_path, load_path, press_path, err_name = "err"):  

    #修改配置文件的监听端口、备库配置、缓存大小等配置
    base_cf = root_path + base_conf + "norm_onsum01.cfg"
    test_cf = root_path + test_conf + "norm_onsum01.cfg"
    
    try:
        modify_config(base_cf, 'Summary\DBstandby', 'db01', '10.11.12.13:4567')
        modify_config(base_cf, 'Summary\SummaryNetwork', 'ListenAddress', ':18018')
        modify_config(base_cf, 'Summary\Summary', 'LruSummaryReqCacheSize', 'dword:0000000a')
        modify_config(base_cf, 'Summary\Summary', 'LfuSummaryReqCacheSize', 'dword:0000000a')
    except Exception as err:
        update_errorlog("modify config:%s error\n" % base_cf)
        set_status(3)
        return -1
        
    try:    
        modify_config(test_cf, 'Summary\DBstandby', 'db01', '10.11.12.13:4567')
        modify_config(test_cf, 'Summary\SummaryNetwork', 'ListenAddress', ':19018')
        modify_config(test_cf, 'Summary\Summary', 'LruSummaryReqCacheSize', 'dword:0000000a')
        modify_config(test_cf, 'Summary\Summary', 'LfuSummaryReqCacheSize', 'dword:0000000a')
    except Exception as err:
        update_errorlog("modify config:%s error\n" % test_cf)
        set_status(3)
        return -1

    #启动base summary
    ret, pid = check_lanch(base_path, "start.sh", 18018, err_name)
    if ret < 0:
        update_errorlog("Base Summary start failed")
        return -1        
    update_errorlog("Base Summary start ok, use %d s\n" % ret)
    
    #启动test summary
    ret, pid  = check_lanch(test_path, "start.sh", 19018, err_name)
    if ret < 0:
        update_errorlog("Test Summary start failed")
        return -1        
    update_errorlog("Test Summary start ok, use %d s\n" % ret)
    
    #启动负载工具
    ret, pid  = check_lanch(load_path, "start.sh", -1, err_name)
    if ret < 0:
        update_errorlog("Load Tool start failed")
        return -1        
    update_errorlog("Load Tool start ok, use %d s\n" % ret)
    
    #启动压力工具1
    press_err_name1 = err_name + "1"  #err1
    ret, tool1_pid  = check_lanch(press_path, "start1.sh", -1, press_err_name1)
    if ret < 0:
        update_errorlog("Press Tool 1 start failed")
        return -1        
    update_errorlog("Press Tool 1 start ok, use %d s\n" % ret)
    
    #启动压力工具2
    press_err_name2 = err_name + "2"  #err2
    ret, tool2_pid = check_lanch(press_path, "start2.sh", -1, press_err_name2)
    if ret < 0:
        update_errorlog("Press Tool 2 start failed")
        return -1        
    update_errorlog("Press Tool 2 start ok, use %d s\n" % ret)
    
    update_errorlog("performance start, about 20min")
    
    #等待压力结束   
    wait_to_die(tool1_pid, 10)
    update_errorlog("Press Tool1 stoped\n")
    
    wait_to_die(tool2_pid, 10)
    update_errorlog("Press Tool2 stoped\n")
    
    #统计性能结果
    perf_res = []
    ret = get_perf_res(base_path + err_name, perf_res)
    if ret != 0:
        update_errorlog("base performance statistics error")
        return -1
    base_perf_str = ""
    for line in perf_res:
        base_perf_str += line + "\n"
    sql = "UPDATE %s set performance_base='%s' where id=%d;" % (database_table, base_perf_str, mission_id)
    cursor.execute(sql)
    db.commit()
    update_errorlog("base summary statistics ok")
    
    perf_res = []
    ret = get_perf_res(test_path + err_name, perf_res)
    if ret != 0:
        update_errorlog("test performance statistics error")
        return -1
    test_perf_str = ""
    for line in perf_res:
        test_perf_str += line + "\n"
    sql = "UPDATE %s set performance_test='%s' where id=%d;" % (database_table, test_perf_str, mission_id)
    cursor.execute(sql)
    db.commit()
    update_errorlog("test summary statistics ok")


def main():
    '''
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
        update_errorlog("start try scp new_test_data to local\n")
        ret = scp_new_test_env('data', newdataip, newdatauser, newdatapassw, newdatapath)
        if ret != 0:
            update_errorlog("scp new_test_data Error, pls check\n")
            set_status(3)
            return -1
            
        update_errorlog("scp new_test_data OK\n")            
    
    ### scp test_conf to local
    if (newconfip != "" and newconfuser != "" and newconfpassw != "" and newconfpath != ""):
        update_errorlog("start try scp new_test_conf to local\n")
        ret = scp_new_test_env('conf', newconfip, newconfuser, newconfpassw, newconfpath)
        if ret != 0:               
            update_errorlog("scp new_test_conf Error, pls check\n")
            set_status(3)
            return -1
    
        update_errorlog("scp new_test_conf OK\n")
    
   
    ### check base code and compile
    base_code_path = root_path + base_src
    
    ret = checkcode_env(base_code_path, basesvn)
    if ret != 0:
        update_errorlog("check base code Error, pls check\n")
        set_status(3)
        return -1        
    update_errorlog("check base code OK\n") 
    
    ret = make_env(base_code_path)
    if ret != 0:
       update_errorlog("compile base code Error, pls check\n") 
       set_status(3)
       return -1
    update_errorlog("compile base code OK\n") 
    
          
    ### check test code and compile
    test_code_path = root_path + test_src
    ret = checkcode_env(test_code_path, testsvn)
    if ret != 0:
        update_errorlog("check test code Error, pls check\n")
        set_status(3)
        return -1            
    update_errorlog("check test code OK\n") 
    
    ret = make_env(test_code_path)
    if ret != 0:
       update_errorlog("compile test code Error, pls check\n") 
       set_status(3)
       return -1
    update_errorlog("compile test code OK\n") 
    '''
    
    ### create symbolic link for base env 
    base_env = root_path + base_src + 'WebSummary/'
    print("base env:%s" % base_env)
    ret = prepare_symbolic_link(base_env) 
    if ret != 0:
        update_errorlog("prepare symbolic link for %s Error\n" % base_env)
        set_status(3)
        return -1
    update_errorlog("prepare symbolic link for %s Success\n" % base_env)
    
    ### create symbolic link for test env 
    test_env = root_path + test_src + 'WebSummary/'
    ret = prepare_symbolic_link(test_env) 
    if ret != 0:
        update_errorlog("prepare symbolic link for %s Error\n" % test_env)
        set_status(3)
        return -1
    update_errorlog("prepare symbolic link for %s Success\n" % test_env)
     
    ### start performance
    load_path = root_path + load_tool
    press_path = root_path + press_tool
    ret = performance(base_env, test_env, load_path, press_path)
        
    
   
        

if __name__ == "__main__":
    main()