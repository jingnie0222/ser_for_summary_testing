#!/usr/bin/python3
#encoding: utf-8
#pysvn test package

import os
import time
import subprocess

class SvnPackage:

    username = None
    password = None
    errorlog = None
    stdlog = None
    
    def __init__(self, in_username, in_password):
        self.username = in_username
        self.password = in_password

    def svn_info(self, localpath):
        return self._do_svn('info', localpath)

    def get_errlog(self):
        return self.errorlog

    def get_stdlog(self):
        return self.stdlog
        
    def svn_up(self, localpath):
        return self._do_svn('up', localpath)
        
    def svn_sw(self, svnurl_to, localpath):
        return self._do_svn('sw', svnurl_to + " " + localpath)
        
    def svn_co(self, svnurl, localpath):
        try:
            return self._do_svn('co', svnurl + " " + localpath )
        except Exception as e:
            print("[svn_co]:%s" % e)
            return -1
            
    def svn_diff(self, oldcode, newcode):
        if (self._do_svn("diff", "--diff-cmd=diff -x -U0 " + oldcode + " " + newcode) == 0):
            return self.get_stdlog()
        return self.get_errlog()

    def _svn_diff_analy(self, diff_rs, printrs = False):
        
        #installize saving area
        diffFiles = {}
        buffer_svndiffile = SvnDiffFile(".")
        buffer_svndiffcodeblock = SvnDiffCodeBlock(".")
        
        #establish some switches
        indexname = ""
        linecount = 0
        pickstatus = 0 #need to pick codes. 1 means picking
        do_nothing = False
        
        #diff_rs is lines readed by svn_diff.
        for line in diff_rs:
            line = line.strip()
            #print (line)
            if(len(line) <= 0):
                continue
            if("Index: " in line):
                indexname = line.split(" ")[1]
                pickstatus = 0 #reset pickstatus.
                print("built SvnDiffCodeBlock:%s" % indexname)
                diffFiles.update ({indexname : buffer_svndiffile})
                #reset buffer SvnDiffFile
                buffer_svndiffile = SvnDiffFile(indexname)
            elif(line == "==================================================================="):
                linecount = linecount+1
            elif(line.find("---") == 0):
                do_nothing = True
            elif(line.find("+++") == 0):
                do_nothing = True
            elif(line.find("@@ ") == 0):
                #found a diff chapter...
                tmp = line.split(" ")
                substr = tmp[1]
                addstr = tmp[2]
                pickstatus = 1
                
                #get offset & linenum from this line.
                lineinfo = self._svn_diff_get_all_startline_and_offset(line)
                buffer_svndiffcodeblock.posoffset = lineinfo.get("posoffset")
                buffer_svndiffcodeblock.suboffset = lineinfo.get("suboffset")
                buffer_svndiffcodeblock.poslinenum = lineinfo.get("poslinenum")
                buffer_svndiffcodeblock.sublinenum = lineinfo.get("sublinenum")
                
                #save buffer_svndiffcodeblock to current SvnDiffFile
                if(buffer_svndiffcodeblock.isFilled):
                    buffer_svndiffile.appenddiffblock(buffer_svndiffcodeblock)
                #reset buffer_svndiffcodeblock
                buffer_svndiffcodeblock = SvnDiffCodeBlock(indexname)
            elif(pickstatus > 0):
                content = self._svn_diff_get_diffcontent(line)
                if(line[:1] == "+"):
                    buffer_svndiffcodeblock.appendpos(content)
                elif(line[:1] == "-"):
                    buffer_svndiffcodeblock.appendsub(content)
        print("loop task end.")
        
        if(printrs):
            for k,v in diffFiles.items():
                #print "block check:" + k + " diffblock_len:" + str(len(v.diffblocks))
                print("block check:%s, diffblock_len:%s" % (k, str(len(v.diffblocks))) )
                for svn_block in v.diffblocks:
                    #print "block codepath: " + svn_block.codepath
                    print("block codepath:%s" % svn_block.codepath)
                    print("block postdata below:")
                    print(svn_block.posdata)
    
    def _svn_diff_get_all_startline_and_offset(self, str):
        #str like this: @@ -1834,0 +1835 @@
        str = str[3:-3]
        data = str.split(" ")
        if(len(data) < 2):
            return False
        rssub = self._svn_diff_get_startline_and_offset(data[0])
        rspos = self._svn_diff_get_startline_and_offset(data[1])
        return {"posoffset" : rspos.get("offset"), "poslinenum" : rspos.get("linenum"), "suboffset" : rssub.get("offset"), "sublinenum" : rssub.get("linenum")}
        
    def _svn_diff_get_startline_and_offset(self,str):
        offset = 0
        str = str.replace("+","").replace("-","")
        data = str.split(",")
        linenum = str
        if(len(data) == 2):
            offset = data[1]
            linenum = data[0]
        return {"offset": offset, "linenum": linenum}
    
    def _svn_diff_get_diffcontent(self,str):
        return str[1:].strip()
        
    def _do_svn(self, cmd_type, parm, timeout = 60):
        command = "svn " + cmd_type + " " + parm + " --username '" + self.username + "' --password '" + self.password + "'"
        #rs = os.popen(command).readlines()
        tc = subprocess.Popen("echo tc", shell = True, stdout = subprocess.PIPE)
        tc.wait()
        #child = subprocess.Popen(command, shell = True, stdin = tc.stdout, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        child = subprocess.Popen(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        run_time = 0
        while child.poll() == None:
            if (run_time >= timeout):
                self.errorlog = "time out: %d" % timeout
                return -1
            run_time += 1
            time.sleep(1)
        self.errorlog = child.stderr.read().decode('gbk')
        self.stdlog = child.stdout.read().decode('gbk')
        print("errorlog:%s" % self.errorlog)
        print("stdlog:%s" % self.stdlog)
        return child.returncode
 
class SvnDiffFile:

    codepath = None
    diffblocks = []
    isFilled = False
    
    def __init__(self, cp):
        self.codepath = cp
        
    def appenddiffblock(self, diffblock):
        self.diffblocks.append(diffblock)
        self.isFilled = True
    
class SvnDiffCodeBlock:

    codepath = None
    #codepath such as "WebCache/CWebCacheFilter.cpp"
    posdata = []
    subdata = []
    posoffset = 0
    poslinenum = 0
    suboffset = 0
    sublinenum = 0
    isFilled = False
    
    def __init__(self, cp):
        self.codepath = cp
    
    def appendpos(self, data):
        #print ("block add " + data + "to appendpos...")
        self.posdata.append(data)
        self.isFilled = True
    
    def appendsub(self, data):
        self.subdata.append(data)
        self.isFilled = True
