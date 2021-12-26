# -*- coding:utf-8 -*-
#!/usr/bin/python

from bs4 import BeautifulSoup
import re

awr_path = r'D:\project\dboper\awr_handle\awr_1.html'
f = open(file=awr_path,mode='r',encoding='gbk')
handle = f.read()
soup = BeautifulSoup(handle,'lxml')

# awr报告总览
title1 = "awr报告总览\n"
granfa = soup.find('table',summary="This table displays snapshot information").find('td',text='Begin Snap:').next_sibling
begin_time = '开始时间：{0}\n'.format(granfa.next_sibling.text.strip())
granfa = soup.find('table',summary="This table displays snapshot information").find('td',text='End Snap:').next_sibling
end_time = '结束时间：{0}\n'.format(granfa.next_sibling.text.strip())
granfa = soup.find('table',summary="This table displays snapshot information").find('td',text='Elapsed:').next_sibling
elapsed_time_float = re.search('[0-9]*\.[0-9]*',format(granfa.next_sibling.text.strip())).group()
elapsed_time = '完成时间：{0}\n'.format(granfa.next_sibling.text.strip())
granfa = soup.find('table',summary="This table displays snapshot information").find('td',text='DB Time:').next_sibling
db_time_float = re.search('[0-9]*\.[0-9]*',format(granfa.next_sibling.text.strip())).group()
db_time = '数据库时间：{0}\n'.format(granfa.next_sibling.text.strip())
load_data = float(db_time_float)/float(elapsed_time_float)
load_time = '数据库负载：{0}\n\n'.format(str(round(load_data)))
summary = title1 + begin_time + end_time + elapsed_time + db_time + load_time

# TOP 10等待事件
title2 = 'TOP 10等待事件\n'
title2_1 = '(Event)       (% DB time)\n'
granfa1 = soup.find('table',summary="This table displays top 10 wait events by total wait time").find_all('td',scope='row')
tmp_list = []
for i in granfa1:
    tmp_list.append(i.text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip())
event ='\n'.join(tmp_list) + '\n\n'
top10_event = title2 + title2_1 + event

# 消耗时间最长的前三条语句
title3 = '完成时间最长的sql语句：\n'
granfa = soup.find('table',summary="This table displays top SQL by elapsed time").find_all('td',scope='row')

tmp_list = []
for i in granfa:
    tmp_list.append(i.find('a').text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() + '\n\n')

slow_sql_1 = tmp_list[0] + tmp_list[1] + tmp_list[2]

# 最消耗CPU的前三条语句
title4 = '最消耗CPU的sql语句：\n'
granfa = soup.find('table',summary="This table displays top SQL by CPU time").find_all('td',scope='row')

tmp_list = []
for i in granfa:
    tmp_list.append(i.find('a').text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() + '\n\n')

slow_sql_2 = tmp_list[0] + tmp_list[1] + tmp_list[2]

# 最消耗IO等待时间的前三条语句
title5 = '最消耗IO等待时间的sql语句：\n'
granfa = soup.find('table',summary="This table displays top SQL by user I/O time").find_all('td',scope='row')

tmp_list = []
for i in granfa:
    tmp_list.append(i.find('a').text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() + '\n\n')

slow_sql_3 = tmp_list[0] + tmp_list[1] + tmp_list[2]

# 最消耗IO等待时间的前三条语句
title5 = '最消耗IO等待时间的sql语句：\n'
granfa = soup.find('table',summary="This table displays top SQL by user I/O time").find_all('td',scope='row')

tmp_list = []
for i in granfa:
    tmp_list.append(i.find('a').text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() + '\n\n')

slow_sql_3 = tmp_list[0] + tmp_list[1] + tmp_list[2]

# 最消耗集群等待时间的前三条语句
title6 = '最消耗集群等待时间的sql语句：\n'
granfa = soup.find('table',summary="This table displays top SQL by cluster wait time").find_all('td',scope='row')

tmp_list = []
for i in granfa:
    tmp_list.append(i.find('a').text.strip() + ' ---> ' + i.next_sibling.next_sibling.next_sibling.next_sibling.text.strip() + '\n\n')

slow_sql_4 = tmp_list[0] + tmp_list[1] + tmp_list[2]

total_str = summary + top10_event + title3 + slow_sql_1 + title4 + slow_sql_2 + title5 + slow_sql_3 + title6 + slow_sql_4

print(total_str)