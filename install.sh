#!/bin/bash
cat > /etc/apt/sources.list<<MHY
deb http://zhangchao-2:igentwva@archive.kylinos.cn/kylin/KYLIN-ALL 4.0.2sp2 main restricted universe multiverse
deb http://archive.kylinos.cn/kylin/KYLIN-ALL 4.0.2sp2-desktop main restricted universe multiverse
MHY
test -e ~/.pip/pip.conf
if [ $? -ne 0 ];then
mkdir ~/.pip
cat > ~/.pip/pip.conf <<-MHY
[global]
timeout = 6000
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn	
MHY
fi
sudo apt -y update
sudo apt -y install python3-pip
sudo python3 -m pip install --upgrade pip
sudo apt -y install python3-matplotlib
