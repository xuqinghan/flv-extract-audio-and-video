import threading

class Parser(threading.Thread):
    def __init__(self, ):
        super().__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter

    def run(self):
        print ("开始解码线程：" )
        print_time(self.name, self.counter, 5)
        
        print ("退出线程：" + self.name)