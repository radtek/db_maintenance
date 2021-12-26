#!/usr/bin/python
# encoding = UTF-8

import os

file_name = '/oracle/home/gen_compress_scripts/tab.txt'
script_name = 'gen_compress_script.py'
cmd_file_name = '/oracle/home/gen_compress_scripts/gen_compress_cmd.sh'

class GenCmd(object):
    @staticmethod
    def gencmd():
        with open(file_name,'r') as f:
            res_list = []
            current_line = f.readline()
            while current_line:
                tmp_list = current_line.split(',')
                cmd = 'python ' + script_name + ' ' + tmp_list[0].strip() + ' ' + tmp_list[1].strip() + '\n'
                res_list.append(cmd)
                current_line = f.readline()
        with open(cmd_file_name,'w+') as f:
            f.writelines(res_list)
        os.system('chmod +x {0}'.format(cmd_file_name))

if __name__ == '__main__':
    GenCmd.gencmd()