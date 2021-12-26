#!/usr/bin/env python 
# coding=UTF-8
# @Time     : 2020-09-12 16:00
# @Author   : huxiaodan
# @FileName : switchover.py
# @Software : PyCharm
# @email    : huxd8@lenovo.com

import sys
from optparse import OptionParser 
import os
import re
from subprocess import Popen, PIPE
import time, logging,subprocess

logger = logging.getLogger()
logger.setLevel(logging.INFO)
rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
log_name =rq + '.log'
logfile = log_name
fh = logging.FileHandler(logfile, mode='w')
fh.setLevel(logging.DEBUG)   
formatter = logging.Formatter("auto_swithover_debug: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

#脚本使用方法
#nohup python switchover.py -s <devdb1> -d <orcl_st> -S <oracle> -D <oracle> &


'''
switchover切换步骤：
1、备库取消实时日志应用
recover managed standby database cancel;
2、将主库设置为standby，并启动到mount状态
alter database commit to switchover to physical standby with session shutdown;
startup mount
3、将备库转为主库，并打开open状态
alter database recover managed standby database disconnect from session;
alter database commit to switchover to primary with session shutdown;
alter database open;
4、将现在备库打开，并启动实时日志应用
alter database open;
recover managed standby database using current logfile disconnect from session;
'''

#定义命令运行方式
def cmd_parse_args(argv):
	usage = "usage: %prog [options] arg1 arg2"
	parser = OptionParser(usage=usage)
	parser.add_option("-s","--sourcetnsname",action="store",dest="sourcetnsname",metavar="sourcetnsname",help="sourceDB tnsname")
	parser.add_option("-d","--desttnsname",action="store",dest="desttnsname",metavar="desttnsname",help="destinationDB tnsname")
	parser.add_option("-S","--sourcepwd",action="store",dest="sourcepwd",metavar="sourcepwd",help="sourceDB password")
	parser.add_option("-D","--destpwd",action="store",dest="destpwd",metavar="destpwd",help="destinationDB password")

	(options,args) = parser.parse_args(args=argv[1:])
	return (options,args)

#检查主备数据库
def checkMasterSlave(sourcetnsname,desttnsname,sourcepwd,destpwd):
	logging.info('---------------------------------------------------')
	logging.info('检查主备库---开始')
	sql = '''
	set timing off
	set feedback off
	set pages 0
	select database_role from v$database;
	'''
	Proc1 = Popen(["sqlplus","-s","sys/" + sourcepwd + "@" + sourcetnsname,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc1.stdin.write(sql)
	(out1,err1) = Proc1.communicate()
	Proc2 = Popen(["sqlplus","-s","sys/" + destpwd + "@" + desttnsname,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc2.stdin.write(sql)
	(out2,err2) = Proc2.communicate()
	if Proc1.returncode != 0 or Proc2.returncode != 0:
		logger.info('检查主备库时报错')
	else:
		logger.info('检查主备库成功')
	if Proc1.returncode != 0 or Proc2.returncode != 0:
		logger.info(err1)
		logger.info(err2)
		sys.exit(Proc1.returncode)
	logging.info('检查主备库---结束')
	logging.info('---------------------------------------------------')
	key1="PRIMARY"
	key2="PHYSICAL STANDBY"
	ptns=ppwd=stns=spwd=''
	if key1 in out1 and key2 in out2:
		ptns=sourcetnsname
		ppwd=sourcepwd
		stns=desttnsname
		spwd=destpwd
	elif key1 in out2 and key2 in out1:
		ptns=desttnsname
		ppwd=destpwd
		stns=sourcetnsname
		spwd=sourcepwd
	return (ptns,stns,ppwd,spwd)

#检查主备库switchover_status状态
def checkMasterSlaveStatus(ptns,stns,ppwd,spwd):
	logging.info('检查主备数据库switchover状态---开始')	
	sql = '''
	set timing off
	set feedback off
	set pages 0
	select switchover_status from v$database;
	'''
	Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc1.stdin.write(sql)
	(out1,err1) = Proc1.communicate()
	if Proc1.returncode != 0:
		logger.info('检查主库switchover状态时报错')
	else:
		logger.info('检查主库switchover状态时成功')
	if Proc1.returncode != 0:
		logger.info(err1)
		sys.exit(Proc1.returncode)
	Proc2 = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc2.stdin.write(sql)
	(out2,err2) = Proc2.communicate()
	if Proc2.returncode != 0:
		logger.info('检查备库switchover状态时报错')
	else:
		logger.info('检查备库switchover状态时成功')
	if Proc2.returncode != 0:
		logger.info(err2)
		sys.exit(Proc2.returncode)
	logging.info('主库的状态：%s' % out1)
	logging.info('备库的状态：%s' % out2)
	logging.info('检查主备数据库状态---结束')
	logging.info('---------------------------------------------------')
	return (out1,out2)

#主备库实例数判断
def checkMasterSlaveInstcount(ptns,stns,ppwd,spwd):
	logging.info('检查主库实例数---开始')	
	sql = '''
	set timing off
	set feedback off
	set pages 0
	select count(instance_name) from gv$instance;
	'''

	Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc1.stdin.write(sql)
	(out1,err1) = Proc1.communicate()
	if Proc1.returncode != 0:
		logger.info('检查主库实例数时报错')
	else:
		logger.info('检查主库实例数成功')	
	if Proc1.returncode != 0:
		logger.info(err1)
		sys.exit(Proc1.returncode)
	else:
		logger.info(out1)
	logging.info('检查主库实例数---结束')	
	logging.info('检查备库实例数---开始')	
	Proc2 = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc2.stdin.write(sql)
	(out2,err2) = Proc2.communicate()
	if Proc2.returncode != 0:
		logger.info('检查备库实例数时报错')
	else:
		logger.info('检查备库实例数成功')
	if Proc2.returncode != 0:
		logger.info(err2)
		sys.exit(Proc2.returncode)
	else:
		logger.info(out2)
	logging.info('检查备库实例数---结束')	
	logging.info('---------------------------------------------------')
	pinst_count=sinst_count=0
	new_out1 = int(re.findall("\d+",out1)[0])
	new_out2 = int(re.findall("\d+",out2)[0])
	if new_out1 == 1:
		pinst_count=1
	elif new_out1 == 2:
		pinst_count=2
	if new_out2 == 1:
		sinst_count=1
	elif new_out2 == 2:
		sinst_count=2
	return (pinst_count,sinst_count)

#检查备库是否有GAP
def checkStandbyDbGap(stns,spwd):
	logging.info('检查备库是否有GAP---开始')
	sql='''
	set timing off
	set feedback off
	set pages 0
	select count(*) from v$archive_gap;
	'''
	Proc = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc.stdin.write(sql)
	(out,err) = Proc.communicate()
	if Proc.returncode != 0:
		logger.info('检查备库是否有GAP操作失败')
	else:
		logger.info('检查备库是否有GAP操作成功')	
	if Proc.returncode != 0:
		logger.info(err)
		sys.exit(Proc.returncode)
	else:
		logger.info(out)
	logging.info('检查备库是否有GAP---结束')
	logging.info('---------------------------------------------------')
	new_out = re.findall("\d+",out)[0]
	return int(new_out)

#备库取消实时日志应用
def cancelLogRealtimeApply(ptns,stns,ppwd,spwd):
	logging.info('取消备库实时日志应用---开始')
	sql='''
	recover managed standby database cancel;
	'''
	Proc = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
	Proc.stdin.write(sql)
	(out,err) = Proc.communicate()
	if Proc.returncode != 0:
		logger.info('取消备库实时日志应用时报错')
	else:
		logger.info('取消备库实时日志应用成功')	
	if Proc.returncode != 0:
		logger.info(err)
		sys.exit(Proc.returncode)
	else:
		logger.info(out)
	logging.info('取消备库实时日志应用---结束')
	logging.info('---------------------------------------------------')

#将主库设置为standby，并启动到mount状态
def changeMasterToStandbyMount(ptns,stns,ppwd,spwd,pinst_count,sinst_count):
	if pinst_count==2:
		logging.info('将主库设置为standby，并启动到mount状态---开始')
		sql1='''
		alter database commit to switchover to physical standby with session shutdown;
		startup mount;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将主库设置为standby，并启动到mount状态时报错')
		else:
			logger.info('将主库设置为standby，并启动到mount状态时成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将主库设置为standby，并启动到mount状态---结束')

		logging.info('将对端数据库启动到mount状态---开始')
		new_ptns=ptns.strip('1')+'2'
		sql2='''
		startup mount;
		'''
		Proc2 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + new_ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc2.stdin.write(sql2)
		(out2,err2) = Proc2.communicate()
		if Proc2.returncode != 0:
			logger.info('将对端数据库启动到mount状态时报错')
		else:
			logger.info('将对端数据库启动到mount状态成功')	
		if Proc2.returncode != 0:
			logger.info(err2)
			sys.exit(Proc2.returncode)
		else:
			logger.info(out2)
		logging.info('将对端数据库启动到mount状态---结束')
		logging.info('---------------------------------------------------')

	elif pinst_count==1:
		logging.info('将主库设置为standby，并启动到mount状态---开始')
		sql1='''
		alter database commit to switchover to physical standby with session shutdown;
		startup mount;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将主库设置为standby，并启动到mount状态时报错')
		else:
			logger.info('将主库设置为standby，并启动到mount状态成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将主库设置为standby，并启动到mount状态---结束')
		logging.info('---------------------------------------------------')

#将备库转为主库，并打开open状态
def changeStandbyToMasterOpen(ptns,stns,ppwd,spwd,pinst_count,sinst_count):
	if sinst_count==1:
		logging.info('将备库转为主库，并打开open状态---开始')
		sql1='''
		alter database recover managed standby database disconnect from session;
		alter database commit to switchover to primary with session shutdown;
		alter database open;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将备库转为主库，并打开open状态时报错')
		else:
			logger.info('将备库转为主库，并打开open状态成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将备库转为主库，并打开open状态---结束')
		logging.info('---------------------------------------------------')

	elif sinst_count==2:
		logging.info('将备库转为主库，并打开open状态---开始')
		sql1='''
		alter database recover managed standby database disconnect from session;
		alter database commit to switchover to primary with session shutdown;
		alter database open;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + spwd + "@" + stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将备库转为主库，并打开open状态时报错')
		else:
			logger.info('将备库转为主库，并打开open状态时成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将备库转为主库，并打开open状态---结束')

		logging.info('将对端数据库open---开始')
		new_stns=stns.strip('1')+'2'
		sql2='''
		alter database open;
		'''
		Proc2 = Popen(["sqlplus","-s","sys/" + spwd + "@" + new_stns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc2.stdin.write(sql2)
		(out2,err2) = Proc2.communicate()
		if Proc2.returncode != 0:
			logger.info('将对端数据库open时报错')
		else:
			logger.info('将对端数据库open时成功')	
		if Proc2.returncode != 0:
			logger.info(err2)
			sys.exit(Proc2.returncode)
		else:
			logger.info(out2)
		logging.info('将对端数据库open---结束')
		logging.info('---------------------------------------------------')

#将现在备库打开，并启动实时日志应用
def openNewStandby(ptns,stns,ppwd,spwd,pinst_count,sinst_count):
	if pinst_count==1:
		logging.info('将现在备库打开，并启动实时日志应用---开始')
		sql1='''
		alter database open;
		recover managed standby database using current logfile disconnect from session;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将现在备库打开，并启动实时日志应用时报错')
		else:
			logger.info('将现在备库打开，并启动实时日志应用成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将现在备库打开，并启动实时日志应用---结束')
		logging.info('---------------------------------------------------')

	elif pinst_count==2:
		logging.info('将现在备库打开，并启动实时日志应用---开始')
		sql1='''
		alter database open;
		recover managed standby database using current logfile disconnect from session;
		'''
		Proc1 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc1.stdin.write(sql1)
		(out1,err1) = Proc1.communicate()
		if Proc1.returncode != 0:
			logger.info('将现在备库打开，并启动实时日志应用时报错')
		else:
			logger.info('将现在备库打开，并启动实时日志应用成功')	
		if Proc1.returncode != 0:
			logger.info(err1)
			sys.exit(Proc1.returncode)
		else:
			logger.info(out1)
		logging.info('将现在备库打开，并启动实时日志应用---结束')

		logging.info('将对端数据库open---开始')
		new_ptns=ptns.strip('1')+'2'
		sql2='''
		alter database open;
		'''
		Proc2 = Popen(["sqlplus","-s","sys/" + ppwd + "@" + new_ptns,"as","sysdba"],stdin=PIPE,stdout=PIPE,stderr=PIPE)
		Proc2.stdin.write(sql2)
		(out2,err2) = Proc2.communicate()
		if Proc2.returncode != 0:
			logger.info('将对端数据库open时报错')
		else:
			logger.info('将对端数据库open成功')	
		if Proc2.returncode != 0:
			logger.info(err2)
			sys.exit(Proc2.returncode)
		else:
			logger.info(out2)
		logging.info('将对端数据库open---结束')
		logging.info('---------------------------------------------------')

#主函数
def main(argv):
	(options,args)=cmd_parse_args(argv)
	sourcetnsname = options.sourcetnsname
	desttnsname = options.desttnsname
	sourcepwd = options.sourcepwd
	destpwd = options.destpwd
	(ptns,stns,ppwd,spwd)=checkMasterSlave(sourcetnsname,desttnsname,sourcepwd,destpwd)
	(pinst_count,sinst_count)=checkMasterSlaveInstcount(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd)
	(p_status,s_status)=checkMasterSlaveStatus(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd)
	gap_count=checkStandbyDbGap(stns=stns,spwd=spwd)
	if gap_count == 0:
		if ('TO STANDBY' in p_status and 'TO PRIMARY' in s_status) or \
		('TO STANDBY' in p_status and 'SESSIONS ACTIVE' in s_status) or \
		('TO STANDBY' in p_status and 'NOT ALLOWED' in s_status) or \
		('SESSIONS ACTIVE' in p_status and 'TO PRIMARY' in s_status) or \
		('SESSIONS ACTIVE' in p_status and 'SESSIONS ACTIVE' in s_status) or \
		('SESSIONS ACTIVE' in p_status and 'NOT ALLOWED' in s_status):
			cancelLogRealtimeApply(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd)
			changeMasterToStandbyMount(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd,pinst_count=pinst_count,sinst_count=sinst_count)
			changeStandbyToMasterOpen(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd,pinst_count=pinst_count,sinst_count=sinst_count)
			openNewStandby(ptns=ptns,stns=stns,ppwd=ppwd,spwd=spwd,pinst_count=pinst_count,sinst_count=sinst_count)
		else:
			logging.info('当前主备库switchover状态不允许switchover切换操作')
			sys.exit(0)	
	else:
		logging.info('当前主备库之间有GAP，主备switchover操作不允许')
		sys.exit(0)

if __name__ == "__main__":
	main(sys.argv)