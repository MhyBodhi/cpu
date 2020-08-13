import sys
sys.path.append(".")
import time
import os
import argparse
import signal
from multiprocessing import Process,Queue
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

def convertformat(args):
    sampling_time = args.i.strip()
    print("sampling_time",sampling_time)
    if sampling_time.endswith("s"):
        t = float(sampling_time[0:-1])
    elif sampling_time.endswith("m"):
        t = float(sampling_time[0:-1]) * 60
    elif sampling_time.endswith("h"):
        t = float(sampling_time[0:-1]) * 60 * 60
    elif sampling_time.endswith("d"):
        t = float(sampling_time[0:-1]) * 60 * 60 * 24
    return t

def handler(signum, frame):
    signalreport()

def signalreport():
    global x,y,args,signal_end_time
    signal_end_time = time.time()
    if args.disableshow:
        p2.terminate() 
    save.generating_curves(x,y)
    sys.exit()

def gettemp(q,t,args):
    global x,y,signal_start_time,start_time,end_time,report_path,statistical_timestamps
    x = []
    y = []
    #记录真实获取到温度时的时间戳，注意这里不是简单的加采样频率时间，程序自身获取数据时有一定的时间消耗
    statistical_timestamps = []
    start = 0
    sampling_time = convertformat(args)
    sampling_frequency = float(args.i.strip()[0:-1])
    signal.signal(signal.SIGINT,handler)
    start_time = time.time()
    signal_start_time = start_time
    #当前函数运行状态
    current_fun_status = 1
    if t:
        end_time = start_time + t
    else:
        end_time = None
    #创建生成结果的存储文件夹
    if end_time:
        file_path = "@".join(regex.findall(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time)))[0]) + "---" + "@".join(regex.findall(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time)))[0])
        report_path = r"./reports/{}".format(file_path)
        os.mkdir(report_path)
    else:
        report_path = r"./reports/{}".format("@".join(regex.findall(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(start_time)))[0]))
        os.mkdir(report_path)
    while True:
        if end_time:
            if time.time() <= end_time:
                if t < 10:
                    print("请至少测试10秒")
                    return
                while True:
                    res = os.popen("cat /sys/class/thermal/thermal_zone0/temp")
                    temp = res.readline().strip()
                    if temp:
                        statistical_timestamps.append(time.time())
                        res.close()
                        break
                yield temp
                x.append(float(start))
                y.append(float(temp)/1000)
                # 向display进程传递数据
                if args.disableshow:
                    q.put((statistical_timestamps, x, y,sampling_time,current_fun_status))
                time.sleep(sampling_time)
                start += sampling_frequency

                #每隔30次生成报告
                if len(x)==30:
                    save.generating_curves(x,y)
                    x.clear()
                    y.clear()
                    statistical_timestamps.clear()

            else:
                # 向display进程传递数据
                if args.disableshow:
                    current_fun_status = 0
                    q.put((statistical_timestamps, x, y, sampling_time, current_fun_status))
                save.generating_curves(x,y)
                print("成功....")
                break
        else:
            while True:
                res = os.popen("cat /sys/class/thermal/thermal_zone0/temp")
                temp = res.readline().strip()
                if temp:
                    statistical_timestamps.append(time.time())
                    res.close()
                    break
            yield temp
            x.append(float(start))
            y.append(float(temp)/1000)
            # 向display进程传递数据
            if args.disableshow:
                q.put((statistical_timestamps, x, y, sampling_time, current_fun_status))
            time.sleep(sampling_time)
            start += sampling_frequency
            if len(x) == 30:
                save.generating_curves(x, y)
                x.clear()
                y.clear()
                statistical_timestamps.clear()

class DisplaySave:

    def __init__(self,q,args):
        self.q = q
        self.args = args
    def init(self):
        plt.rcParams['font.family'] = ['STFangsong']

        self.xmajorLocator = MultipleLocator(float(self.args.i.strip()[0:-1]))
        # xminorLocator = MultipleLocator(1)  # 将x轴次刻度标签设置为1的倍数
        self.fig, self.ax = plt.subplots()
        self.fig.text(0.01,0.92,"绿色:温度在65以下",color="green",verticalalignment='bottom',fontsize=7,fontweight="heavy")
        self.fig.text(0.01,0.95,"洋红:温度在65至74之间",color="magenta",verticalalignment='bottom',fontsize=7,fontweight="heavy")
        self.fig.text(0.01,0.98,"红色:温度在74以上",color="red",verticalalignment='bottom',fontsize=7,fontweight="heavy")
        # 定义Y轴刻度
        self.y_range = ['%d' % i for i in np.linspace(1, 100, 50)]
        self.y_num = [eval(oo) for oo in self.y_range]
        self.y_ticks = ["%d$^\circ$C" % i for i in self.y_num]
        plt.yticks(self.y_num, self.y_ticks, color="black")
        self.ax.xaxis.set_major_locator(self.xmajorLocator)
        # 设置主刻度标签的位置,标签文本的格式
        plt.grid(linestyle="-", axis="y")

        self.ax.grid(True, which='major', axis='x', linewidth=0.5, linestyle=':', color='0.5')  # x坐标轴的网格使用主刻度
        # 设置图表标题，并给坐标轴添加标签
        plt.title("CPU温度走势图", fontsize=30, color="black")
        plt.xlabel("采样频率:%s/次（每隔多久采集一次），注意与实际采集到数据时系统时间的区分)" % (self.args.i.strip()), fontsize=20, color="black")
        plt.ylabel("CPU温度", fontsize=20, color="black")
        self.fig.set_figwidth(20)
        self.fig.tight_layout()
        plt.gcf().autofmt_xdate()
        # 设置坐标轴刻度标记的大小
        plt.tick_params(axis='both', labelsize=10)

    def generating_curves(self,x, y):

        global signal_start_time, signal_end_time, start_time, end_time, report_path, statistical_timestamps
        matplotlib.use("SVG")
        self.init()
        x_ticks = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report_time)) for report_time in
                   statistical_timestamps]
        plt.xticks(x, x_ticks, color="black")
        # 设置线宽
        plt.plot(x, y, color="blue", linewidth=1, label="CPU温度走势")
        for i, j in zip(x, y):
            if j > 74:
                color = "red"
            elif 65 <= j <= 74:
                color = "magenta"
            else:
                color = "green"
            plt.text(i, j, "%.1f$^\circ$C" % j, ha='left', va='bottom', fontsize=8, color=color)
        # 设置图例格式
        plt.legend(loc=1, borderaxespad=0.)
        try:
            plt.savefig(report_path + "/{}.svg".format(
                " ".join(regex.findall(x_ticks[0])[0]) + "---" + " ".join(regex.findall(x_ticks[-1])[0])), dpi=1200,
                        format='svg')
        except:
            pass
        # plt.show()
    def displaylive(self):
        self.init()
        while True:
            try:
                self.data = self.q.get(False)
                #判断gettemp函数状态
                if not self.data[-1]:
                    plt.close()
                    break
            except:
                continue
            self.statistical_timestamps = self.data[0]
            self.x = self.data[1]
            #判断是否是空列表
            if self.x==[]:
                break
            self.y = self.data[2]
            self.sampling_time = self.data[3]
            self.ax.set(xlim=(min(self.x),max(self.x)),ylim=(min(self.y),max(self.y)))
            self.x_ticks = [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report_time)) for report_time in self.statistical_timestamps]
            plt.xticks(self.x, self.x_ticks, color="black",rotation=45)
            plt.plot(self.x,self.y, color="blue", linewidth=1, label="CPU温度走势")
            for i,j in zip(self.x,self.y):
                if j > 74:
                    color = "red"
                elif 65 <= j <= 74:
                    color = "magenta"
                else:
                    color = "green"
                plt.text(i,j,"%.1f$^\circ$C"%j,ha='left',va='bottom',fontsize=8,color=color)
            plt.pause(0.01)

if __name__ == '__main__':
    import re
    regex = re.compile("(.*?)\s+(.*?):(.*?):(.*)")
    q = Queue()
    if not os.path.exists("./reports"):
        os.mkdir("./reports")
    signal_end_time = None
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", help="Test duration,The unit is Days, hours, minutes or seconds.eg 10m 10h 10d")
    parser.add_argument("-i", default="3s", help="Specify how often to count.eg 30s 1m 1h ...")
    parser.add_argument("-noshow","--disableshow",action='store_false', default=True, help="whether or not enable real-time display")
    args = parser.parse_args()
    if args.t:
        test_time = args.t.strip()
    else:
        test_time = None
    if test_time:
        if test_time.endswith("s"):
            t = float(test_time[0:-1])
        elif test_time.endswith("m"):
            t = float(test_time[0:-1])*60
        elif test_time.endswith("h"):
            t = float(test_time[0:-1])*60*60
        elif test_time.endswith("d"):
            t = float(test_time[0:-1])*60*60*24
    else:
        t = None
    #
    if args.disableshow:
        display = DisplaySave(q,args)
        p2 = Process(target=display.displaylive)
        p2.start()
    save = DisplaySave(q,args)

    print("start...")
    print("t %ss"%t)
    temps = gettemp(q,t,args)
    for temp in temps:
        # print("温度",float(temp)/1000)
        pass
    if args.disableshow:
        p2.join()
    print("main结束")
