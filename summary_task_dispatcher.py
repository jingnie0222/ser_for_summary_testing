#!/usr/bin/python3
import pymysql
import time

database_host="10.144.96.115"
database_db="summary_test"
database_table="TestSummary_testsummary"
database_user="root"
database_pass="lzxg@webqa"

server_nodes=['10.134.96.64']


def check_new_task():
    cursor.execute("SELECT id FROM %s where status=0 ORDER BY create_time limit 1" % database_table)
    data = cursor.fetchone()
    db.commit()
    if data == None:
        return -1
    return data[0]

def get_node():
    cursor.execute("select runningIP from %s where status=2 or status=1" % database_table)
    data = cursor.fetchall()
    print("get_node", data)
    db.commit()
    used_ip = []
    for ip in data:
        used_ip.append(ip[0])
    for node in server_nodes:
        if node not in used_ip:
            return node
    return ""

    
def do_mission(mission_id, ip):
    sql = "UPDATE %s set runningIP='%s', status=1 where id=%d" % (database_table, ip, mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except:
        db.rollback()
        return 1
    return 0

def main():

    while True:       
        mission_id = check_new_task()
        print('mission_id: %d' % mission_id)
        if mission_id == -1:
           time.sleep(1)
           continue
        ip = get_node()
        if not ip:
            time.sleep(5)
            print("new task %d, but all servers are busy" % mission_id)
            continue
        print("task %d will run on %s" % (mission_id, ip))
        print("return:%d" % do_mission(mission_id, ip))
        
        time.sleep(2)

if __name__ == '__main__':
    db = pymysql.connect(database_host, database_user, database_pass, database_db,  charset="utf8")
    cursor = db.cursor()
    main()
