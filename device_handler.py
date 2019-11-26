# -*- coding: UTF-8 -*-
#!/usr/bin/python

#public module
import re, telnetlib, time, socket

class CommandSender(object):
	def __init__(self,devip,username,password):
		self.devip = devip
		#时延告警存放空间
		self.rtt_alarm = []
		#登陆设备，返回telnet实例
		self.tn = self.login(username,password)

	#Low level api
	def login(self,username,password):
		'''设备登陆，返回实例
		'''
		tn = None
		try:
			tn = telnetlib.Telnet(self.devip ,port = 23, timeout = 3)
			
			#如果用户名提示符不是username则报错
			prompt = tn.read_until(b'name:', timeout = 4).decode('ascii')
			if re.search('(name:)', prompt) == None:
				tn.close()
				print('Error: No username prompt')
			
			else:
				tn.write(username.encode('ascii') + b'\n')
				tn.read_until(b'word:')
				tn.write(password.encode('ascii') + b'\n')
				res = tn.read_until(b'#').decode('ascii')
				#当用户名或密码错误时返回' '
				
				if res == ' ':
					tn.close()
					print('Error: Authentication failed')
				
				#正常执行返回tn实例
				else:
					#得到设备名					
					tn.write(b'terminal length 0\n')
					res = tn.read_until(b'#').decode('ascii')
					self.hostname = re.search('(\S+)#', res).group(1)
					return tn
		
		#超时异常		
		except socket.timeout:
			print('Error: Telnet timeout')
			return None

	def islogin(self):
		'''判断login是否成功
		'''
		if self.tn != None:
			try:
				res = self.SendCommand('')
				host = re.search('(\S+)#', res)
				if host:
					if host.group(1) == self.hostname:
						return True
					else:
						return False
				else:
					return False
			except Exception:
				return False
	
	def SendCommand(self, command):
		'''推送命令得到结果
		'''
		self.tn.write(command.encode('ascii') + b'\n')
		return (self.tn.read_until(b'#').decode('ascii'))

	def close(self):
		'''关闭telnet连接
		'''
		self.tn.close()

	#High level api
	def GetBw(self, interface):
		'''得到接口速率,Mbps
		'''
		intput_rate = 0
		output_rate = 0

		res = self.SendCommand('show interface ' + interface)		
		#对于以太网子接口无法从show interface中找到输入和输出速率
		if re.search('input rate (\d+)', res):
			intput_rate = int(re.search('input rate (\d+)', res).group(1))/1000000
			output_rate = int(re.search('output rate (\d+)', res).group(1))/1000000

		return (intput_rate, output_rate)	

	def GetInterface(self, dstip):
		'''得到地址的出接口
		'''
		interface = None

		res = self.SendCommand('show ip route ' + dstip)
		_interface = re.search('via (\S+\d)', res)		
		#查找到目标地址的出接口
		if _interface:
			interface = _interface.group(1)

		return interface

	def RttAlarm(self,threshold,rttnow,rttstable,dev,interface):
		'''时延告警,返回处理字段
		threshold:告警阈值, rttnow:当前时延平均值 rttstable:10日时延稳定值
		0：无告警 1：时延抖动告警 2：时延持续增大告警 3：时延持续增大告警解除
		'''
		alarm_flag = 0
		count = self.rtt_alarm.count((dev,interface))
		
		#当前值超过阈值
		if rttnow > rttstable + threshold:
			if count <= 9:
				self.rtt_alarm.append((dev,interface))
				#连续出现3次触发抖动告警
				if count == 2:
					alarm_flag = 1
				#连续出现10次触发时延增大告警
				elif count == 9:
					alarm_flag = 2
					self.rtt_dump = False
					for i in range(2):
						self.rtt_alarm.append((dev,interface))
			else:
				if self.rtt_dump:
					for i in range(2):
						self.rtt_alarm.append((dev,interface))	
					self.rtt_dump = False					

		#当前值小于阈值
		else:
			if (count > 0) and (count <= 10):
				while self.rtt_alarm.count((dev,interface)) != 0:
					self.rtt_alarm.pop(self.rtt_alarm.index((dev,interface)))
				if count == 10:
					alarm_flag = 3
			elif count >= 11:
				self.rtt_alarm.pop(self.rtt_alarm.index((dev,interface)))
				self.rtt_dump = True

		return alarm_flag

	def TestPing(self, dstip):
		'''只ping三个包
		'''
		res = self.SendCommand('ping ' + dstip +' repeat 3 timeout 1')
		ping_res = int(re.search('Success rate is (\d+)',res).group(1))
		if ping_res >0:
			return True
		else:
			return False		

	def Ping(self,dstip,repeat='100'):
		'''正常ping操作
		'''
		#print(time.strftime("%Y-%m-%d %H:%M:%S") + ' run ping '+ dstip)
		ping_res = self.SendCommand(' '.join(['ping',dstip,'repeat',repeat,'timeout 1']))

		#ping成功百分比
		result = int(re.search('Success rate is (\d+)', ping_res).group(1))
		if result>0:
			round_trip = re.search('round-trip min/avg/max = (\S+)',ping_res).group(1)
		else:
			round_trip = '0/0/0'

		#分解rtt得到最低，平均，最高时延
		rtt = re.search('(\d+)/(\d+)/(\d+)', round_trip)
		rttmin, rttavg, rttmax = int(rtt.group(1)), int(rtt.group(2)), int(rtt.group(3))

		#返回结果，rtt最小，平均，最大值，以及ping执行完成的时间
		return(result,rttmin,rttavg,rttmax,time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))		

	def ExPing(self,dstip,test = True):
		'''执行ping操作
		testping 是否在正式ping之前 (True/False)
		'''
		res = None
		if test:
			test_success = self.TestPing(dstip)
		else:
			test_success = True

		if test_success:
			res = self.Ping(dstip)
		else:
			res = (0,0,0,0,time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

		#res -> (result,rttmin,rttavg,rttmax,time)
		return res

if __name__ == '__main__':
	cs = CommandSender('10.24.254.141')
	res = cs.SendCommand('')
	_host = re.search('(\S+)#', res)
	if _host:
		if _host.group(1) == cs.hostname:
			print('yes')
