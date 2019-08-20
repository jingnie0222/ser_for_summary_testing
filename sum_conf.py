#!/usr/bin/python3
#coding=utf-8

import os

#status：任务的状态（0:未开始；1:已分配；2正在运行；3:出错停止；4:已完成；5:任务取消；6:准备取消）

testcache_path = "/search/odin/daemon/self_testing/testcache"

###拉取线上data和conf的机器
online_host = "rsync.query001.web.djt.ted"
online_path = "/search/odin/daemon/norm_onsum01"
symbolic_link_path = "/search/odin/daemon/data_agent/data/base/"

###本机ip
local_ip = os.popen("sogou-host -a | head -1").read().replace('\n', '')


###数据库相关配置
database_host = "10.144.96.115"
database_db = "summary_test"
database_table = "TestSummary_testsummary"
database_user = "root"
database_pass = "lzxg@webqa"


#需要以 "/" 结束
root_path="/search/odin/daemon/summary/"

test_src = "test_src/"
base_src = "base_src/"
gcov_src = "gcov_src/"

test_data = "test_data/"
base_data = "base_data/"

test_conf = "test_conf/"
base_conf = "base_conf/"



log_file = os.path.join(testcache_path, "log/autorun.log")
