#!/usr/bin/python
# -*- coding:UTF-8 -*-

# python sw.py catlbpm101 catlbpm catlbpmdr

import sys
import os
import re
from subprocess import Popen, PIPE
import logging.config
import ConfigParser

# 日志配置
logging.config.fileConfig('logger.conf')
logger = logging.getLogger('logger1')

# 导入配置
config = ConfigParser.ConfigParser(allow_no_value=True)
config.read('setup.conf')

# SQL语句
CHKDB_SQL = '''
set timing off
set feedback off
set pages 0
select database_role from v$database;
'''

CHK_STBY_CASC_SQL = '''
set timing off
set feedback off
set pages 0
select value from v$parameter where name='{0}';
'''

LOG_APPLY_CANCEL = '''
set timing off
set feedback off
set pages 0
recover managed standby database cancel;
'''

PRI_TO_STBY = '''
set timing off
set feedback off
set pages 0
alter database commit to switchover to physical standby with session shutdown;
startup mount;
'''

STBY_TO_PRI = '''
set timing off
set feedback off
set pages 0
alter database recover managed standby database disconnect from session;
alter database commit to switchover to primary with session shutdown;
alter database open;
'''

LOG_APPLY = '''
set timing off
set feedback off
set pages 0
alter database open;
recover managed standby database using current logfile disconnect from session;
'''

# 操作数据库函数
def db_oper(user, pwd, tns, sql):
    Proc = Popen(["sqlplus", "-s", user + "/" + pwd + "@" + tns, "as", "sysdba"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    Proc.stdin.write(sql)
    (out, err) = Proc.communicate()
    return Proc.returncode, out, err


# 检查数据库角色函数
def check_db_role(db_info):
    if len(db_info) <= 2:
        logger.info('运行脚本时，请输入正确的参数！')
        sys.exit(0)
    logger.info('------------------------数据库角色检查开始-------------------------------')
    pridb = ''
    stby_list = []
    for db in db_info:
        user = config.get(db, 'user')
        pwd = config.get(db, 'pwd')
        tns = config.get(db, 'tns')
        code, out, err = db_oper(user, pwd, tns, CHKDB_SQL)
        if code != 0:
            logger.info('{0}数据库角色检查---操作失败！'.format(db))
            logger.info(err)
            sys.exit(code)
        else:
            logger.info('{0}数据库角色检查---操作成功！'.format(db))
        if out.strip() == 'PRIMARY':
            pridb = db
        if out.strip() == 'PHYSICAL STANDBY':
            stby_list.append(db)
    logger.info('------------------------数据库角色检查结束-------------------------------\n')
    return pridb, stby_list

# 检查备库的级联备库函数
def stby_cascade_role(pridb, stby_list):
    logger.info('------------------------备库的级联备库检查开始---------------------------')
    if len(stby_list) <= 1:
        logger.info('该环境不存在两个备库，无法执行switchover操作！')
        sys.exit(0)
    db_dict = {}
    db_dict['primary']=''
    db_dict['standby']=''
    db_dict['standby_cascade']=''
    # 检查参数log_archive_dest_2和log_archive_dest_3
    for stby_db in stby_list:
        user = config.get(stby_db, 'user')
        pwd = config.get(stby_db, 'pwd')
        tns = config.get(stby_db, 'tns')
        code1, out1, err1 = db_oper(user, pwd, tns, CHK_STBY_CASC_SQL.format('log_archive_dest_2'))
        if code1 != 0:
            logger.info('log_archive_dest_2参数检查---操作失败！')
            logger.info(err1)
            sys.exit(code1)
        else:
            logger.info('log_archive_dest_2参数检查---操作成功！')
        
        code2, out2, err2 = db_oper(user, pwd, tns, CHK_STBY_CASC_SQL.format('log_archive_dest_3'))
        if code2 != 0:
            logger.info('log_archive_dest_3参数检查---操作失败！')
            logger.info(err2)
            sys.exit(code2)
        else:
            logger.info('log_archive_dest_3参数检查---操作成功！')

        if out1.strip() != '':
            count_1 = 0
            query1 = re.search("\(.*?\)", out1.strip())
            valid_for1 = query1.group().lstrip('(').rstrip(')').split(',')
            db_unique_name1 = out1.strip().split(' ')[-1].split('=')[1]
            for i in range(len(valid_for1)):
                if valid_for1[i] == 'STANDBY_ROLE':
                    count_1 += 1
                    break
            if count_1 > 0:
                db_dict['primary']=pridb
                db_dict['standby']=stby_db
                db_dict['standby_cascade']=db_unique_name1      

        if out2.strip() != '':
            count_2 = 0
            query2 = re.search("\(.*?\)", out2.strip())
            valid_for2 = query2.group().lstrip('(').rstrip(')').split(',')
            db_unique_name2 = out2.strip().split(' ')[-1].split('=')[1]
            for j in range(len(valid_for2)):
                if valid_for2[j] == 'STANDBY_ROLE':
                    count_2 += 1
                    break
            if count_2 > 0:
                db_dict['primary']=pridb
                db_dict['standby']=stby_db
                db_dict['standby_cascade']=db_unique_name2

        if out1.strip() == '' and  out2.strip() == '':
            logger.info('log_archive_dest_2和log_archive_dest_3参数都为空，参数错误！')
            sys.exit(0)

    if db_dict['primary'] == '' and db_dict['standby'] == '' and db_dict['standby_cascade'] == '':
        logger.info('数据库集合的关系如下：')
        logger.info('主库：{0}'.format(pridb))
        logger.info('备库：{0}'.format(stby_list))
        db_dict['primary']=pridb
        db_dict['standby']=stby_list
        db_dict['standby_cascade']=None
        return db_dict

    logger.info('数据库集合的关系如下：')
    logger.info('主库：{0}'.format(db_dict['primary']))
    logger.info('备库：{0}'.format(db_dict['standby']))
    logger.info('级联备库：{0}'.format(db_dict['standby_cascade']))
    logger.info('------------------------备库的级联备库检查结束---------------------------\n')
    return db_dict

# 主备切换函数
def switchover(user_pri,pwd_pri,tns_pri,user_stb,pwd_stb,tns_stb,pri_name,stb_name):
    logger.info('------------------------主备切换开始---------------------------')
    # 备库取消日志应用
    code, out, err = db_oper(user_stb, pwd_stb, tns_stb, LOG_APPLY_CANCEL)
    if code != 0:
        logger.info('备库{0}取消日志应用---操作失败！'.format(stb_name))
        logger.info(err)
        sys.exit(code)
    else:
        logger.info('备库{0}取消日志应用---操作成功！'.format(stb_name))

    # 将主库设置为standby，并启动到mount状态
    code, out, err = db_oper(user_pri, pwd_pri, tns_pri, PRI_TO_STBY)
    if code != 0:
        logger.info('主库{0}设置为standby，并启动到mount状态---操作失败！'.format(pri_name))
        logger.info(err)
        sys.exit(code)
    else:
        logger.info('主库{0}设置为standby，并启动到mount状态---操作成功！'.format(pri_name))

    # 将备库转为主库，并打开open状态
    code, out, err = db_oper(user_stb, pwd_stb, tns_stb, STBY_TO_PRI)
    if code != 0:
        logger.info('备库{0}转为主库，并打开open状态---操作失败！'.format(stb_name))
        logger.info(err)
        sys.exit(code)
    else:
        logger.info('备库{0}转为主库，并打开open状态---操作成功！'.format(stb_name))

    # 将新的备库打开，并启动实时日志应用
    code, out, err = db_oper(user_pri, pwd_pri, tns_pri, LOG_APPLY)
    if code != 0:
        logger.info('将新的备库{0}打开，并启动实时日志应用---操作失败！'.format(pri_name))
        logger.info(err)
        sys.exit(code)
    else:
        logger.info('将新的备库{0}打开，并启动实时日志应用---操作成功！'.format(pri_name))
    logger.info('------------------------主备切换结束---------------------------\n')

# B节点修改参数
class DbModify(object):
    @staticmethod
    def modify_1(user_b,pwd_b,tns_b,tns_1,tns_2,tns_3,db_unique_name):
        logger.info('------------------------参数修改开始-------------------------------')
        sql = '''
        set timing off
        set feedback off
        set pages 0
        alter system set fal_server={0},{1};
        alter system set log_archive_dest_3='service={2} lgwr async valid_for=(online_logfiles,primary_role) db_unique_name={3}';
        '''.format(tns_1,tns_2,tns_3,db_unique_name)
        code, out, err = db_oper(user_b, pwd_b, tns_b, sql)
        if code != 0:
            logger.info('修改参数---操作失败！')
            logger.info(err)
            sys.exit(code)
        else:
            logger.info('修改参数---操作成功！')
        logger.info('------------------------参数修改结束-------------------------------\n')
    
    @staticmethod
    def modify_2(user_b,pwd_b,tns_b,tns_1,tns_2,db_unique_name):
        logger.info('------------------------参数修改开始-------------------------------')
        sql = '''
        set timing off
        set feedback off
        set pages 0
        alter system set fal_server={0};
        alter system set log_archive_dest_2='service={1} lgwr async valid_for=(ALL_LOGFILES,STANDBY_ROLE) db_unique_name={2}';
        '''.format(tns_1,tns_2,db_unique_name)
        code, out, err = db_oper(user_b, pwd_b, tns_b, sql)
        if code != 0:
            logger.info('修改参数---操作失败！')
            logger.info(err)
            sys.exit(code)
        else:
            logger.info('修改参数---操作成功！')
        logger.info('------------------------参数修改结束-------------------------------\n')

    @staticmethod
    def modify_3(user_b,pwd_b,tns_b,tns_1,tns_2,db_unique_name):
        logger.info('------------------------参数修改开始-------------------------------')
        sql = '''
        set timing off
        set feedback off
        set pages 0
        alter system set fal_server={0};
        alter system set log_archive_dest_3='service={1} lgwr async valid_for=(ALL_LOGFILES,STANDBY_ROLE) db_unique_name={2}';
        '''.format(tns_1,tns_2,db_unique_name)
        code, out, err = db_oper(user_b, pwd_b, tns_b, sql)
        if code != 0:
            logger.info('修改参数---操作失败！')
            logger.info(err)
            sys.exit(code)
        else:
            logger.info('修改参数---操作成功！')
        logger.info('------------------------参数修改结束-------------------------------\n')

    @staticmethod
    def modify_4(user_b,pwd_b,tns_b,tns_1,db_unique_name):
        logger.info('------------------------参数修改开始-------------------------------')
        sql = '''
        set timing off
        set feedback off
        set pages 0
        alter system set log_archive_dest_2='service={0} lgwr async valid_for=(online_logfiles,primary_role) db_unique_name={1}';
        '''.format(tns_1,db_unique_name)
        code, out, err = db_oper(user_b, pwd_b, tns_b, sql)
        if code != 0:
            logger.info('修改参数---操作失败！')
            logger.info(err)
            sys.exit(code)
        else:
            logger.info('修改参数---操作成功！')
        logger.info('------------------------参数修改结束-------------------------------\n')


def main():
    # 主备库角色确认和分类
    db_list = sys.argv[1:]
    pridb, stby_list = check_db_role(db_list)

    # 主库、备库、级联备库确认
    db_dict = stby_cascade_role(pridb, stby_list)

    # 主备切换和修改参数
    tag = config.get(db_dict['primary'], 'tag')
    if db_dict['standby_cascade'] is not None and tag == 'A':
        a = db_dict['primary']
        b = db_dict['standby']
        c = db_dict['standby_cascade']
        user_a = config.get(a, 'user')
        pwd_a = config.get(a, 'pwd')
        tns_a = config.get(a, 'tns')
        user_b = config.get(b, 'user')
        pwd_b = config.get(b, 'pwd')
        tns_b = config.get(b, 'tns')
        user_c = config.get(c, 'user')
        pwd_c = config.get(c, 'pwd')
        tns_c = config.get(c, 'tns')
        logger.info('主库{0}--->备库{1}'.format(a,b))
        switchover(user_a,pwd_a,tns_a,user_b,pwd_b,tns_b,a,b)
        DbModify.modify_1(user_b,pwd_b,tns_b,tns_a,tns_c,tns_c,c)

    if db_dict['standby_cascade'] is not None and tag == 'C':
        a = db_dict['primary']
        b = db_dict['standby']
        c = db_dict['standby_cascade']
        user_a = config.get(a, 'user')
        pwd_a = config.get(a, 'pwd')
        tns_a = config.get(a, 'tns')
        user_b = config.get(b, 'user')
        pwd_b = config.get(b, 'pwd')
        tns_b = config.get(b, 'tns')
        user_c = config.get(c, 'user')
        pwd_c = config.get(c, 'pwd')
        tns_c = config.get(c, 'tns')
        logger.info('主库{0}--->备库{1}'.format(a,b))
        switchover(user_a,pwd_a,tns_a,user_b,pwd_b,tns_b,a,b)
        DbModify.modify_4(user_b,pwd_b,tns_b,tns_c,c)
        DbModify.modify_1(user_b,pwd_b,tns_b,tns_c,tns_a,tns_a,a)

    if db_dict['standby_cascade'] is None and tag == 'B':
        db = raw_input('请选择你要切换的备库{0}:'.format(db_dict['standby']))
        db_name = db.strip().strip("'")
        if db_name in db_dict['standby']:
            a = db_dict['standby']
            b = db_dict['primary']
            user_b = config.get(b, 'user')
            pwd_b = config.get(b, 'pwd')
            tns_b = config.get(b, 'tns')
            if config.get(db_name, 'tag') == 'A':
                user_a = config.get(db_name, 'user')
                pwd_a = config.get(db_name, 'pwd')
                tns_a = config.get(db_name, 'tns')
                a.remove(db_name)
                user_c = config.get(a[0], 'user')
                pwd_c = config.get(a[0], 'pwd')
                tns_c = config.get(a[0], 'tns')
                logger.info('主库{0}--->备库{1}'.format(b,db_name))
                switchover(user_b,pwd_b,tns_b,user_a,pwd_a,tns_a,b,db_name)
                DbModify.modify_3(user_b,pwd_b,tns_b,tns_a,tns_c,a[0])
            if config.get(db_name, 'tag') == 'C':
                user_c = config.get(db_name, 'user')
                pwd_c = config.get(db_name, 'pwd')
                tns_c = config.get(db_name, 'tns')
                a.remove(db_name)
                user_a = config.get(a[0], 'user')
                pwd_a = config.get(a[0], 'pwd')
                tns_a = config.get(a[0], 'tns')
                logger.info('主库{0}--->备库{1}'.format(b,db_name))
                switchover(user_b,pwd_b,tns_b,user_c,pwd_c,tns_c,b,db_name)
                DbModify.modify_2(user_b,pwd_b,tns_b,tns_a,tns_a,a[0])
        else:
            logger.info('请选择正确的备库，谢谢！')
            sys.exit(0)

if __name__ == '__main__':
    main()

