import socket  # 导入 socket 模块
from threading import Thread, Lock
import time
import os
import sys
import sched

# 404 connection established
# 407 Android success, send command
# 405 details
# 406 send device list of the Rasp
# 408 target not exist
# 409 command sent
# 连接成功后服务器发送404信号，表示连接成功
# 客户端收到404信号后发送用户验证码
# 所有通信均需通过完整性验证，检查末尾的$。
# 安卓用户先发送A作为用户验证，然后发送自身情况，以六位指令控制物联网
# 物联网用户先发送R作为用户验证，然后发送自身情况，应该包含自己控制的设备数量
# detail应包括设备名，以，分割
#六位指令从左到右，包括两位自己识别号，一位gate识别号，两位target识别号，还有一位操作识别号

# ADDRESS = ('192.168.0.105', 8712)
# ADDRESS = ('192.168.31.245', 8712)
ADDRESS = ('172.16.0.16', 8712)
# ADDRESS = ('192.168.1.8', 8712)
g_socket_server = None  # listening socket

g_conn_detail_A = {}  # connection information

g_conn_detail_R = {}  # connection information

g_conn_pool = []  # connection pool

device_pool = []  # device pool

command_on = None

dict_clients = {'R':"Raspbarry_client", 'A':"Android_client"}

lock = Lock()

command = {'0': 'turn on', '1': 'turn off'}

# target = "1.0,2.0"
target = ""

def init():
    """
    init server
    """
    global g_socket_server
    g_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 socket 对象
    g_socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    g_socket_server.bind(ADDRESS)
    g_socket_server.listen(5)  # max number of users for waiting
    print("server start, wait for connection")

def accept_client():
    """
    accept connection
    """
    while True:
        try:
            client, _ = g_socket_server.accept()  # wait
            # join thread pool
            g_conn_pool.append(client)
            # one thread one client
            thread = Thread(target=client_classify, args=(client,))
            # setDaemon
            thread.setDaemon(True)
            thread.start()
        except ConnectionAbortedError:
            print("client offline")

def complete(words):
    words = str(words)
    if(words.endswith('$')):
        return True, str(words[:-1])
    else:
        return False, words

def suffix(words):
    words = str(words) + str("$") + str("\n")
    # return words.encode(encoding='utf8')
    return words.encode()

def no_complete(client):
    try:
        client.sendall(suffix('fail'))
    except OSError:
        pass


def detail(client, type):
    global target
    index = len(g_conn_detail_A) + len(g_conn_detail_R)
    client.sendall(suffix("405"))
    com, information = complete(client.recv(1024).decode(encoding='utf8'))
    if len(information) == 0:
        # client.close()
        # delete a connection
        g_conn_pool.remove(client)
        print("a client offline")
    if(com is True):
        print('com is True')
        information = str(information)
        information = information.split(',')
        print('inf')
        print(information)
        if(information[-1]=='end'):
            print('information[-1]==end')
            i = 'index=' + str(index)
            information.insert(0,i)
            if(type == 'A'):
                temporary = {str(index-len(g_conn_detail_R)): information}
                g_conn_detail_A.update(temporary)
            if(type == 'R'):
                temporary = {str(index - len(g_conn_detail_A)): information}
                g_conn_detail_R.update(temporary)
                if (target == ""):
                    target = str((int(len(information) - 5) / 2))
                else:
                    target = target + "," + str((len(information) - 5) / 2)
                print("target")
                print(target)
            temporary.clear()
            print('g_conn_detail')
            print(len(g_conn_detail_A))
            print(len(g_conn_detail_R))
            print(g_conn_detail_A)
            print(g_conn_detail_R)
            if(type ==  'A'):
                return len(g_conn_detail_A) - 1
            if(type == 'R'):
                return len(g_conn_detail_R) - 1
            return 0
    else:
        pass

def client_classify(client):
    """
    massage pressing and client classify
    """
    print("成功连接")
    # client.sendall(suffix("404"))
    client.sendall(suffix("404"))
    try:
        while True:
            com, report = complete(client.recv(1024).decode(encoding='utf8'))
            if len(report) == 0:
                # client.close()
                # delete a connection
                # g_conn_pool.remove(client)
                print("a client offline")
                break
            print(com)
            print(report)
            try:
                print("user auth:" + dict_clients[report])
                if(com is False):
                    no_complete(client)
                    pass
                break
            except KeyError:
                pass
        if report == "A":
            Android(client)
        if report == "R":
            device_pool.append(client)
            g_conn_pool.remove(client)
            Rasp(client)
        if len(report) == 0:
            # client.close()
            # delete a connection
            g_conn_pool.remove(client)
            print("a client offline")
    except ConnectionAbortedError:
        print("client" + dict_clients[report] + "offline")

def Android(client):
    index = detail(client, 'A')
    send = Thread(target=Android_send, args=(client, index,))
    recv = Thread(target=Android_recv, args=(client, index,))
    recv.start()
    send.start()

def Android_send(client, index):
    client.sendall(suffix(target))

def Android_recv(client, index):
    while True:
        com, report = complete(client.recv(1024).decode(encoding='utf8'))
        if (len(report) == 0 or report == "000"):
            print("length is 0")
            string_index = str(index)
            g_conn_detail_A.pop(string_index)
            # client.close()
            # delete a connection
            g_conn_pool.remove(client)
            print("a client offline")
        if(com is not True):
            no_complete(client)
            pass
        print(len(report)) # six digits int, 0-1 which device emits the command;  2-4 which target the command wanna --
                           # -- control; 5 what the command is, turn on or off?
        print(report)
        device_number = report[0:2]
        Rasp_number = report[2:3]
        target_number = report[3:5]
        command_set = report[5:6]
        time.sleep(1)
        try:
            log = 'device:' + str(device_number) + ' ' + str(command[str(command_set)]) + ' target ' + str(target_number)
        except KeyError:
            break
        print(log)
        print('R_number')
        print(Rasp_number)
        if(int(Rasp_number)<=len(device_pool)):
            device_pool[int(Rasp_number)-1].sendall(suffix(str(target_number)+str(command_set)))
            client.sendall(suffix(report))  # test only
            # client.sendall(suffix("409")) #command sent
        else:
            pass
            # client.sendall(suffix("408")) #target not exist



def Rasp(client):
    index = detail(client, 'R')
    send = Thread(target=Rasp_send, args=(client,index,))
    recv = Thread(target=Rasp_recv, args=(client,index,))
    send.start()
    recv.start()

def Rasp_send(client,index):
    client.sendall(suffix("Rasp_send"))


def Rasp_recv(client,index):
    string_index = str(index)
    while True:
        words = ""
        words = client.recv(1024).decode(encoding='utf8')
        if len(words) == 0:
            g_conn_detail_R.pop(string_index)
            # client.close()
            # delete a connection
            g_conn_pool.remove(client)
        com, report = complete(words)
        print('wait')
        # time.sleep(20)


if __name__ == '__main__':
    init()
    # create a thread for accept
    thread = Thread(target=accept_client)
    thread.setDaemon(True)
    thread.start()
    print("server is working")
    # while True:
    #     input()
    # # main logic
    while True:
        cmd = input("""--------------------------
input 1 : users available
input 2 : transmit command 
input 3 : shutdown
""")
        if cmd == '1':
            print("--------------------------")
            print("len(g_conn_pool：", len(g_conn_pool))
            print("g_conn_pool：", g_conn_pool)
            print("len(device_pool)：", len(device_pool))
            print("device_pool：", device_pool)
            print(target)
        elif cmd == '2':
            print("--------------------------")
            index, msg = input("input command：").split(",")
            g_conn_pool[int(index)].sendall(suffix(msg))
        elif cmd == '3':
            print("--------------------------")
            index, msg = input("input command：").split(",")
            device_pool[int(index)].sendall(suffix(msg))
        elif cmd == "4":
            exit()
