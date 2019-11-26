#!/usr/bin/python3
#version 0.1 得到设备的接口ip信息，输出到txt

#public module
import os
import re
from openpyxl import Workbook

#privite module
from device_handler import CommandSender
from threading import Thread

def read_txt(path):
	'''读取txt，返回字典信息{'dev_ip':[interface]}
	'''
	res = {}
	with open(path, 'r') as file:
		info = [line.strip().split() for line in file if line.strip() != '']
	for i in info:
		dev_ip = i[0]
		interface = i[1]
		if res.get(dev_ip):
			res[dev_ip].append(interface)
		else:
			res[dev_ip]=[interface]
	return res

def write_txt(path, data):
	'''读取data信息，写入path
	形参：
	path：写入文件路径
	data 列表
	'''
	with open(path, 'w') as file:
		for i in data:
			file.write(i+'\n')

def write_xls(path,data):
	'''写入excel，将按列存储的数据按行写入
	形参：
	path：存储文件路径 str
	data：三元列表数据 data
	'''
	wb = Workbook()
	ws = wb.active

	for one_dev in data:
		for line_num in range(len(one_dev[0])):
			one_line = [i[line_num] for i in one_dev]
			ws.append(one_line)
	
	wb.save(path)



def one_device_search(dev_ip,interfaces,expressions,not_found_return,output):
	'''从一台设备查询接口信息
	形参：
	dev_ip:设备的管理地址 str
	interfaces：需要查询的接口列表 list
	expressions:查询的正则表达式列表 如['load-interval (\d+)','service-policy output (\S+)']
	not_found_return：查询不到时的返回值列表 如['not_found_interval','not_found_qps']
	output: 存放返回值，list
	'''
	cs = CommandSender(dev_ip)
	if cs.islogin():
		commands = [' '.join(['show run interface', interface]) for interface in interfaces]
		commands_return = [cs.SendCommand(command) for command in commands]
		cs.close()
		
		res  = [[dev_ip for i in interfaces], interfaces]
		for i in range(len(expressions)):
			res.append([find_sth(command_return, expressions[i], not_found_return[i]) for command_return in commands_return])

		output.append(res)


def find_sth(find_from, expression, not_found_return):
	'''从命令返回中提取所需信息
	'''
	res = re.search(expression, find_from)
	if res:
		return res.group(1)
	else:
		return not_found_return

if __name__ == '__main__':
	path = r'D:\softerware backup\python\run once\get_ip'
	input_info = read_txt(os.path.join(path, 'input.txt'))
	output= []
	#查询表达式
	expressions = ['description (\S+)','ip address (\S+)','ip address \S+ (\S+)','service-policy output (\S+)']
	#查询为空返回值
	not_found_return = ['not_found_description','not_found_address','not_found_mask','not_found_QOS']		
	threads = [Thread(target=one_device_search, args=(dev_ip, input_info[dev_ip], expressions, not_found_return, output)) for dev_ip in input_info]
	for i in threads:
		i.start()
	for i in threads:
		i.join()

#	print(output)
	write_xls(os.path.join(path, 'output.xlsx'), output)

