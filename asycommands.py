# -*- coding:utf-8 -*-
import subprocess
import threading
import errno
import select
import re
import sys


class TrAsyCommands(object):
    """
    异步命令执行器,适合执行输出数据较多的命令

    默认超时时间为30秒

    **作者:tulianghui**
    """
    # 日志记录器
    _NEW_LINE = '\n'

    def __init__(self, timeout=30, err_pattners=None):
        self._timeout = timeout
        self._timer = None
        self._proc = None
        self._is_finshed = False
        self._return_code = 1
        # 保存出错信息
        self._err_outs = []

        # 当在标出输出中出现这些模式是也保存到_err_outs中

        if err_pattners is None:
            err_pattners = []

        self._err_patters = [re.compile(p) for p in err_pattners]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proc:
            self._proc.stderr.close()
            self._proc.stdout.close()
            self._return_code = self._proc.returncode
            del self._proc

    def _new_proc(self, args, bufsize, stdout, stderr, cwd, shell):
        """
        get instance of popen
        return if is validate command
        """
        if isinstance(args, str):
            shell = True

        try:
            print(args)
            
            self._proc = subprocess.Popen(args=args, bufsize=bufsize, stderr=stderr, stdout=stdout, cwd=cwd, shell=shell)
            if self._timeout > 0:               
                self._timer = threading.Timer(self._timeout, self.stop)              
                self._timer.start()
                

        except WindowsError as e:
            return False

        except OSError as e:
            return False

        return True

    def _wait(self):
        if self._proc:
            self._proc.wait()
            if (self._return_code != -1):
                self._return_code = self._proc.returncode

        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _call_callback(self, call_func=None, args=None):
        if call_func:call_func(*args)

    def stop(self):
        """停止命令的执行"""
        if self._proc and not self._is_finshed:
            self._proc.terminate()
            self._is_finshed = True

            #删除定时器
            if self._timer:
                self._timer.cancel()
            self._timer = None
            #等待结束
            self._wait()
            self._return_code = -1

    def return_code(self):
        """返回执行子进程退出状态码"""
        return self._return_code

    def error_msg(self):
        """返回执行过程中的错误消息"""
        return '\n'.join(self._err_outs)

    def execute_with_data(self, args, bufsize=40960, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, shell=True, call_func=None, call_args=None):
        """
        执行命令并且返回命令输出数据的生成器

        生成器返回tuple(iotype:stdout或stderr, line)

        :param args: 建议为list,此时shell设置为False, 当为str时,shell设置为True
        :param bufsize: 缓存大小
        :param stdout: 通过PIPE返回
        :param stderr: 通过PIPE返回
        :param cwd: 如不为None,执行命令前将切换到此目录
        :param shell: If shell is True, it is recommended to pass args as a string rather than as a sequence
        :param call_func: 回调函数
        :param call_args: 回调函数参数
        :return: 生成器

        :example:

        >>> asycmd = TrAsyCommands()
        >>> for iotype, line in asycmd.execute_with_data(['ping', '-c' '10','www.baidu.com'], shell=False):
        >>>        print iotype, line

        """
        if not self._new_proc(args=args, bufsize=bufsize, stdout=stdout, stderr=stderr, cwd=cwd, shell=shell):
            return

        read_set = []
        read_set = [i for i in(self._proc.stdout, self._proc.stderr) if i is not None]
        for i in read_set:i.flush()
        _flag = 0
        while not self._is_finshed and read_set:
            try:
                readablelist, writablelist, exceptionlist = select.select(read_set, [], read_set, 0)
            except KeyboardInterrupt:
                self._is_finshed = True
                break
            except select.error as se:
                #Interrupted system call
                if se.args[0] == errno.EINTR:
                    continue
                else:
                    break

            # select 超时
            if not readablelist and not writablelist and not exceptionlist:
                continue

            # stdout
            if self._proc.stdout in readablelist:
                line = self._proc.stdout.readline()
                # 遇到EOF,返回空字符串
                if line == b'':
                    read_set.remove(self._proc.stdout)
                    #sys.stdout.write('stdout break \n')
                    #sys.stdout.flush()
                    #break
                else:
                    line = line.decode().strip(self._NEW_LINE)
                    # 删除控制台格式控制
                    # 需要命令执行结果数据时通过生成器返回
                    yield 1, line

            # stderr
            if self._proc.stderr in readablelist:
                line = self._proc.stderr.readline()
                # 遇到EOF,返回空字符串
                if line == b'':
                    read_set.remove(self._proc.stderr) 
                    #print 'stderr:','line=',line,'len=',len(line)
                    #sys.stdout.write('stderr break \n')
                    #sys.stdout.flush()
                else:
                    line = line.decode().strip(self._NEW_LINE)
                    # 删除控制台格式控制
                    self._err_outs.append(line)

                    # 需要命令执行结果数据时通过生成器返回
                    yield 2, line

        # 等待进程结束
        self._wait()

        #调用回调函数
        self._call_callback(call_func, call_args)

    def execute_without_data(self, args, bufsize=40960, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None, shell=True, call_func=None, call_args=None):
        """
        执行命令,并将输出读出丢掉(防止pipe阻塞),不会向上层返回执行中的输出数据.

        Popen(['/bin/sh', '-c', args[0], args[1], ...])

        :param args:
        :param bufsize:
        :param stdout:
        :param stderr:
        :param cwd:
        :param shell: On Unix with shell=True, the shell defaults to /bin/sh
        :param call_func:
        :param call_args:
        :return:
        """
        if not self._new_proc(args=args, bufsize=bufsize, stdout=stdout, stderr=stderr, cwd=cwd, shell=shell):
            return

        read_set = [self._proc.stdout, self._proc.stderr]
        for i in read_set:i.flush()

        # 读走管道的数据
        while not self._is_finshed and read_set:
            try:
                readablelist, writablelist, exceptionlist = select.select(read_set, [], read_set, 0.1)

            except select.error as se:
                # Interrupted system call
                if se.args[0] == errno.EINTR:
                    continue
                else:
                    break

            # 超时
            if not readablelist and not exceptionlist:
                continue

            if self._proc.stdout in readablelist:
                line = self._proc.stdout.readline()
                # 遇到EOF,返回空字符串
                if line == '':
                    break

                line = line.decode().strip(self._NEW_LINE)
                # 删除控制台格式控制

                # 满足错误模式的，也加入出错信息中
                for p in self._err_patters:
                    if p.search(line):
                        self._err_outs.append(line)
                        break

            if self._proc.stderr in readablelist:
                line = self._proc.stderr.readline()
                # 遇到EOF,返回空字符串
                if line == '':
                    break

                line = line.decode().strip(self._NEW_LINE)
                # 删除控制台格式控制
                self._err_outs.append(line)

        # 等待进程结束
        self._wait()

        # 调用回调函数
        self._call_callback(call_func, call_args)




