#!/usr/bin/python3
#coding=utf-8

import sys
import re
import os



def read_file_to_list(file):
    pat_dict = {'URL': r'\[Url(.*)\]:(.*)',  
                'TITLE': r'\[Title(.*)\]:(.*)',
                'SUMMARY': r'\[Summary(.*)\]:(.*)',
                'TUWEN':  r'\[tuwen-Summary(.*)\]:(.*)',
                'DOCID': r'\[DocID(.*)\]:(.*)',
                'QUERY': r'\[Query (.*)\]:(.*)'}

    lists = []
    node = {}
    with open(file, 'r', encoding='gbk', errors='ignore') as f:
        for line in f.readlines():
            # line --> node
            for key in pat_dict:
                p = re.search(pat_dict[key], line)
                if p:
                    #print("key:%s, value:%s" % (key, p.group(2))) 
                    if key == 'DOCID':
                       if node != {}: 
                           lists.append(node)
                           node = {}
                       node[key] = p.group(2)
                    else:
                       node[key] = p.group(2)
                    #print("key:%s, value:%s" %(key, node[key]))
                    break
        #append the last node
        lists.append(node)   

    return lists


def cmp_lists(list1, list2, out_list1, out_list2):
    for i in range(len(list1)):
        same = True
        for key in ['DOCID', 'URL', 'TITLE', 'SUMMARY', 'TUWEN', 'QUERY']:
            if key not in list1[i] and key not in list2[i]:
                continue
            elif key not in list1[i] or key not in list2[i]:
                same = False
                break
            else:
                if list1[i][key] != list2[i][key]:
                    same = False
                    break
        # output diff to file
        if not same:
            out_list1.append(list1[i])
            out_list2.append(list2[i])


def gen_diff(infile1, infile2, out_list1, out_list2):
    if not os.path.exists(infile1):
        print("%s not exist" % infile1)
        return -1    
    if not os.path.exists(infile2):
        print("%s not exist" % infile2)
        return -1
    try:
        node_list1 = read_file_to_list(infile1)  
        node_list2 = read_file_to_list(infile2)                   
        cmp_lists(node_list1, node_list2, out_list1, out_list2)        
        return 0       
    except Exception as err:
        return -1
        

if __name__ == '__main__':
    infile1 = '/search/odin/daemon/summary/base_src/WebSummary/err'   
    infile2 = '/search/odin/daemon/summary/test_src/WebSummary/err'
    outfile1 = "/search/odin/daemon/summary/base_diff"  
    outfile2 = "/search/odin/daemon/summary/test_diff"
    gen_diff(infile1, infile2, outfile1, outfile2)
    
    