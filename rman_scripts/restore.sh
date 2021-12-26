#!/bin/bash
export ORACLE_BASE=/oracle/app/oracle
export ORACLE_HOME=$ORACLE_BASE/product/11.2.0.4/db_1
export ORACLE_SID=supportdb
cmd=/oracle/home/rman_restore/restore_supportdb.rman
logfile=/oracle/home/rman_restore/restore.log

/oracle/app/oracle/product/11.2.0.4/db_1/bin/rman target /  cmdfile=$cmd log=$logfile 
