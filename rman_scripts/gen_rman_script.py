#!/usr/bin/python
# encoding = UTF-8

'''
How to use?
for example:
python gen_rman_script.py -S branchnbumaster -C whllemdb1 -c 4 -d /oradata/supportdb -t 2021-10-12_12:00:00
'''

from optparse import OptionParser
from subprocess import Popen, PIPE
import sys
import os

class GenRmanScript(object):
    def __init__(self,argv):
        usage = "usage: %prog [options] arg"
        parser = OptionParser(usage)

        parser.add_option('-S', '--nbuserver', dest='nbuserver', action='store',
                          metavar="nbuserver", help='nbuserver [-S nbuserver]')

        parser.add_option('-C', '--nbuclient', dest='nbuclient', action='store',
                          metavar="nbuclient", help='nbuclient [-C nbuclient]')

        parser.add_option('-c', '--channel', dest='channel', action='store',
                          metavar="channel", help='channel [-c channel]')

        parser.add_option('-d', '--restore_dir', dest='restore_dir', action='store',
                          metavar="restore_dir", help='restore_dir [-d restore_dir]')

        parser.add_option('-t', '--restore_time', dest='restore_time', action='store',
                          metavar="restore_time", help='restore_time [-t YYYY-mm-dd HH24:mi:ss]')
        (self.options, self.args) = parser.parse_args(args=argv[1:])

    def genrmanscript(self):
        str1 = """
run{
# allocate channel\n
"""
        str2 = ''
        for i in range(int(self.options.channel)):
            str2 += 'allocate channel ch' + str(i) + " type 'sbt_tape';\n"
        str3 = "send 'nb_ora_serv={0}, nb_ora_client={1}';\n\n".format(self.options.nbuserver,self.options.nbuclient)
        str4 = '# rename database datafile\n'
        sql_1 = """
        set head off pages 0 feed off echo off verify off
        set lines 800
        select 'SET NEWNAME FOR DATAFILE ' || FILE# || ' TO ''' || '{0}/datafile/' || substr(name,instr(name,'/',-1)+1) || ''';' from v$datafile;
        """.format(self.options.restore_dir)
        Proc = Popen(["sqlplus", "-s", "/", "as", "sysdba"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        Proc.stdin.write(sql_1)
        (out, err) = Proc.communicate()
        if Proc.returncode != 0:
            sys.exit(Proc.returncode)
        str5 = out + '\n\n'
        str6 = '# rename database tempfile\n'
        sql_2 = """
        set head off pages 0 feed off echo off verify off
        set lines 800
        select 'SET NEWNAME FOR TEMPFILE ' || FILE# || ' TO ''' || '{0}/tempfile/' || substr(name,instr(name,'/',-1)+1) || ''';' from v$tempfile;
        """.format(self.options.restore_dir)
        Proc = Popen(["sqlplus", "-s", "/", "as", "sysdba"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        Proc.stdin.write(sql_2)
        (out, err) = Proc.communicate()
        if Proc.returncode != 0:
            sys.exit(Proc.returncode)
        str7 = out + '\n\n'
        str8 = '# rename database redo log name\n'
        sql_3 = """
        set head off pages 0 feed off echo off verify off
        set lines 3000
        select 'alter database rename file '''|| member ||''' '||chr(10)|| ' TO ''' || '{0}/onlinelog/' || substr(member,instr(member,'/',-1)+1) || ''';' from v$logfile;
        """.format(self.options.restore_dir)
        Proc = Popen(["sqlplus", "-s", "/", "as", "sysdba"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        Proc.stdin.write(sql_3)
        (out, err) = Proc.communicate()
        temp_list = []
        new_out = out.split(';')
        for i in new_out:
            if i != '\n\n':
                temp_list.append('SQL "' + i.strip('\n').strip('\n\n').replace("'","''") + ' ";')
        str9 = '\n'.join(temp_list) + '\n\n'
        str10 = '# set target time for all operations in the RUN block\n'
        str11 = 'set until time= "to_date(' + "'" + self.options.restore_time.split('_')[0] + ' ' + self.options.restore_time.split('_')[1] + "'" + ",'yyyy-mm-dd hh24:mi:ss')" + '";\n\n'
        str12 = """
restore database;

SWITCH DATAFILE ALL;
switch TEMPFILE ALL;

recover database;\n
"""
        str13 = ''
        for i in range(int(self.options.channel)):
            str13 += 'release channel ch' + str(i) + ";\n"
        str14 = """
}
"""
        new_str = str1 + str2 + str3 + str4 + str5 + str6 + str7 + str8 + str9 + str10 + str11 + str12 + str13 + str14
        script = os.getcwd() + '/restore.rman'
        with open(script,'w') as f:
            f.write(new_str)

if __name__ == '__main__':
    obj = GenRmanScript(sys.argv)
    obj.genrmanscript()
