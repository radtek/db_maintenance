#!/usr/bin/python
# encoding = UTF-8

import os
import sys
import random
import datetime
from subprocess import Popen, PIPE

BASE_PATH = '/oracle/home/dbscripts/hwm/hwm_scripts/'
LOG_FILE_BASE = '/oracle/home/dbscripts/hwm/hwm_logs/'

class GenHwmScript(object):
    def __init__(self,user,tabname):
        self.user = user
        self.tabname = tabname

    def first(self):
        dt1 = str(random.randint(1,100))
        dt2 = datetime.date.today().strftime('%m%d')
        script_path = BASE_PATH + dt2 + '/'
        logfile_path = LOG_FILE_BASE + dt2 + '/'
        if not os.path.exists(script_path):
            os.system('mkdir -p {0}'.format(script_path))
        if not os.path.exists(logfile_path):
            os.system('mkdir -p {0}'.format(logfile_path))
        script_name =  dt1 + '_hwm_' + self.tabname + '.sql'
        row1 = 'set timing on\n'
        row2 = 'set time on\n'
        row3 = 'set echo on\n'
        row4 = 'col segment_name format a28;\n'
        row5 = "alter session set nls_date_format='yyyy-mm-dd hh24:mi:ss';\n"
        row6 = 'select  sysdate from dual;\n'
        row7 = 'define fil=/oracle/home/dbscripts/hwm/hwm_logs/' + dt2 + '/' + dt1 + '-Table_Hwm_' + self.tabname + '.log\n'
        row8 = 'prompt Table_Hwm Spooling to &fil\n'
        row9 = 'spool &fil\n'
        row10 = 'prompt ' + dt1 + '_hwm_' + self.tabname + ' Table_Hwm start ========================================================================================\n'
        row11 = 'select sysdate from dual;\n'
        row12 = 'set timing on\n'
        row13 = 'whenever oserror exit 1;\n'
        row14 = 'whenever sqlerror exit 1;\n'
        row15 = 'alter session force parallel ddl parallel 16;\n'
        row16 = 'alter session force parallel dml parallel 16;\n'
        row17 = 'alter session force parallel query parallel 16;\n'
        row18 = 'select ' + "'" + self.tabname + "'" + ' table_name,count(*) table_count from ' + self.user + '.' + self.tabname + ';\n'
        row19 = 'select owner,table_name,blocks,empty_blocks,num_rows,avg_row_len,round(num_rows*avg_row_len/1024/1024/1024) "Estimate_Size(GB)",last_analyzed from dba_tables where table_name=' \
                + "'" + self.tabname + "'" + ';\n'
        row20 = 'select segment_name,segment_type,blocks,round(BYTES / 1024 / 1024 / 1024,2) "Actual_Size(GB)" FROM dba_segments WHERE segment_name=' \
                + "'" + self.tabname + "'" + ';\n'
        row21 = 'alter table ' + self.user + '.' + self.tabname + ' move;\n'

        row_list = []
        row_list.append(row1);row_list.append(row2);row_list.append(row3);row_list.append(row4);row_list.append(row5);row_list.append(row6)\
        ;row_list.append(row7);row_list.append(row8);row_list.append(row9);row_list.append(row10);row_list.append(row11);row_list.append(row12)\
        ;row_list.append(row13);row_list.append(row14);row_list.append(row15);row_list.append(row16);row_list.append(row17);row_list.append(row18)\
        ;row_list.append(row19);row_list.append(row20);row_list.append(row21)
        file_name = script_path + script_name
        with open(file_name,mode='w+') as f:
            f.writelines(row_list)
        return file_name,dt1

    def second(self,file_name):
        sql1 = '''
            set linesize 1000
            set head off
            set feedback off
            select 'alter index '||owner||'.'||index_name||' rebuild tablespace '||tablespace_name||' parallel 16;'
            from dba_indexes
            where owner='{0}'
            and table_name='{1}';
            '''.format(self.user,self.tabname)
        sql2 = '''
            set linesize 1000
            set head off
            set feedback off
            select 'alter index '||owner||'.'||index_name||' noparallel;'
            from dba_indexes
            where owner='{0}'
            and table_name='{1}';
            '''.format(self.user,self.tabname)
        Proc = Popen(["sqlplus","-s","/","as","sysdba"], stdin=PIPE, stdout=PIPE,stderr=PIPE)
        Proc.stdin.write(sql1)
        (out, err) = Proc.communicate()
        if Proc.returncode != 0:
            sys.exit(Proc.returncode)
        with open(file_name, mode='a+') as f:
            f.write(out.strip() + '\n')
        Proc = Popen(["sqlplus", "-s", "/", "as", "sysdba"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        Proc.stdin.write(sql2)
        (out, err) = Proc.communicate()
        if Proc.returncode != 0:
            sys.exit(Proc.returncode)
        else:
            pass
        with open(file_name, mode='a+') as f:
            f.write(out.strip() + '\n')

    def third(self,file_name,dt1):
        row1 = 'select ' + "'" + self.tabname + "'" + ' table_name,count(*) table_count from ' + self.user + '.' + self.tabname + ';\n'
        row2 = 'select owner,table_name,blocks,empty_blocks,num_rows,avg_row_len,round(num_rows*avg_row_len/1024/1024/1024) "Estimate_Size(GB)",last_analyzed from dba_tables where table_name=' \
                + "'" + self.tabname + "'" + ';\n'
        row3 = 'select segment_name,segment_type,blocks,round(BYTES / 1024 / 1024 / 1024,2) "Actual_Size(GB)" FROM dba_segments WHERE segment_name=' \
                + "'" + self.tabname + "'" + ';\n'
        row4 = 'set timing on\n'
        row5 = 'EXEC sys.dbms_stats.gather_table_stats(ownname=>' + "'" + self.user + "'" + ',tabname=>' + "'" + self.tabname + "'" \
                + ",estimate_percent => 100,method_opt => 'FOR ALL INDEXED COLUMNS',degree => 16,CASCADE => TRUE);\n"
        row6 = 'select owner,table_name,blocks,empty_blocks,num_rows,avg_row_len,round(num_rows*avg_row_len/1024/1024/1024) "Estimate_Size(GB)",last_analyzed from dba_tables where table_name=' \
                + "'" + self.tabname + "'" + ';\n'
        row7 = 'select sysdate from dual;\n'
        row8 = 'prompt ' + dt1 + '_hwm_' + self.tabname + ' Table_Hwm end =======================================================================================\n'
        row9 = 'spool off;\n'
        row10 = 'exit\n'
        row_list = []
        row_list.append(row1);row_list.append(row2);row_list.append(row3);row_list.append(row4);row_list.append(row5);row_list.append(row6) \
            ;row_list.append(row7);row_list.append(row8);row_list.append(row9);row_list.append(row10)
        with open(file_name, mode='a+') as f:
            f.writelines(row_list)

if __name__ == '__main__':
    user = sys.argv[1]
    tabname = sys.argv[2]
    obj = GenHwmScript(user,tabname)
    file_name,dt1 = obj.first()
    obj.second(file_name)
    obj.third(file_name,dt1)
