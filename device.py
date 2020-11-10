import socket
import numpy as np
import psutil
import time
import os
from threading import Thread, Lock
import sys
from RPi import GPIO


class super_user:
    def __init__(self):
        self.detail = ['leng=4,', 'type=IoT-master,', 'name=Raspberry,']
        self.status_temp = [0, 0, 0]
        input_pin = [17,27,22] #左从上往下 6，7, 8
        output_pin = [13, 19, 26]  # 左从下往上 4，3，2
        self.output_map = {"00":26, "01":19,"02":13}
        output_active = []  # 左从下往上 4，3，2
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(input_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if (GPIO.input(17) < 0.5):
            output_active.append(output_pin[0])
            self.detail.append("device1=LED,")
            self.detail.append("status=off,")
            self.status_temp[0] = 1
        if (GPIO.input(27) < 0.5):
            output_active.append(output_pin[0])
            self.detail.append("device2=LED,")
            self.detail.append("status=off,")
            self.status_temp[1] = 1
        if (GPIO.input(22) < 0.5):
            output_active.append(output_pin[0])
            self.detail.append("device3=LED,")
            self.detail.append("status=off,")
            self.status_temp[2] = 1
        self.detail.append("end")
        print("detail")
        print(detail)
        self.ADDR = ('192.168.31.245', 8712)
        self.status = {}
        print(self.ADDR)
        thread = Thread(target=self.connection)
        thread.setDaemon(True)
        thread.start()
        threads = Thread(target=self.refresh)
        threads.start()

    def connection(self):
        self.s = socket.socket()  # Instantiate
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # Heartbeating
        try:
            self.s.connect(self.ADDR)
            print('success')
            receive = Thread(target=self.recv)
            self.sendall = Thread(target=self.send)
            # receive.setDaemon(True)
            # self.sendall.setDaemon(True)
            receive.start()
            while True:
                if(receive.isAlive()):
                    sync = time.localtime()
                    time.sleep(10)
                else:
                    break
        except ConnectionRefusedError:
            text = 'connect to' + str(self.ADDR) + 'again'
            print(text)
            p1 = psutil.Process(os.getpid())
            print(" 该进程CPU占用率: " + (str)(p1.cpu_percent(None)) + "%")
            print(" 该进程memory占用率: %.3f%%" % (p1.memory_percent()))
            self.connection()
            time.sleep(10)

    def complete(self, words):
        words = str(words)
        words = words[2:-3]
        print(words)
        if (words.endswith("$")):
            return True, str(words[:-1])
        else:
            return False, words

    def suffix(self, words):
        words = words + '$'
        return words.encode(encoding='utf8')

    def no_complete(self, client):
        client.sendall(suffix('fail'))

    def recv(self):
        while True:
            try:
                print("receive")
                com, report = self.complete(self.s.recv(1024))
                print(com)
                print(report)
            except ConnectionResetError:
                text = 'connect to' + str(self.ADDR) + 'again'
                print(text)
                self.connection()
                time.sleep(10)
            print(report)
            if(com is True):
                if(report=="fail"):
                    print('fail')
                if(report=="404"):
                    print('yes')
                    time.sleep(0.5)
                    self.s.sendall(self.suffix('R'))
                    continue
                if(report=='405'):
                    print('detail')
                    information = ''
                    for i in self.detail:
                        information = information + i
                        if(i=='end'):
                            flag = True
                            print(information)
                            print(type(information))
                    if(flag is True):
                        print('flag is True')
                        self.s.sendall(self.suffix(information))
                        continue
                    else:
                        pass
                if(report.isnumeric()):
                    command = int(report)
                    if(0<=command<40): #三个device
                        target = report[0:-1]
                        activity = int(report[2:3])
                        if(self.status.__contains__(target)):
                            temporary = {target:activity}
                            self.status.update(temporary)
                            print(self.status)
                            GPIO.output(self.output_map[target],activity)
                            print("changed")
                        else:
                            self.s.sendall(self.suffix('500')) #设备不存在
                    else:
                        # pass
                        self.s.sendall(self.suffix('500'))  # 设备不存在


    def refresh(self):
        local_target = "000"
        while(True):
            count = 0
            flag = False
            for i in self.status_temp:
                if (count < 10):
                    keys = "0" + str(count)
                else:
                    keys = str(count)
                if(i is not 0):
                    temp_dict = {keys:0}
                    if(not keys in self.status):
                        flag = True
                        self.status.update(temp_dict)
                        local_target = self.modify_string(local_target,"1",count)
                else:
                    if ( keys in self.status):
                        self.status.pop(keys)
                        flag = True
                        local_target = self.modify_string(local_target,"0",count)
                count += 1
            if(flag):
                print("self.status")
                print(self.status)
                print("self.status_temp")
                print(self.status_temp)
                print("t:" + local_target)
                try:
                    self.s.sendall(self.suffix("t:" + local_target))
                except AttributeError:
                    pass
            time.sleep(5)


    def send(self,command):
        if(command is None):
            time.sleep(10)
            pass
        self.s.sendall(self.suffix(str(command)))


    def inputs(self):
        while True:
            cmd = input("- - - - - - -"
                        "input: 'send' "
                        "input: status_temp array number + space + value to change status_temp array")
            if cmd == "send":
                cmd = input("input command")
                thread = Thread(target=self.send(cmd))
                thread.start()
            array = cmd.split(" ")
            print(array)
            self.status_temp[int(array[0])] = int(array[1])

user = super_user()
thread = Thread(target=input())
thread.start()

