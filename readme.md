## SSR LINUX GUI
简易版的在linux下的ssr图形化界面

* 订阅ssr地址生成配置文件
* 后台运行

## 安装使用
#### 安装
确保系统环境安装了`appindicator3`
在apt包管理工具的Linux发行版可以使用以下命令安装
```
sudo apt install gir1.2-appindicator3-0.1
```


```
git clone https://github.com/Baloneo/ssr-gtk.git
cd ssr-git
chmod +x ./install.sh
./install.sh
```
安装好之后的在你的软件列表能找到

#### 卸载
退出软件,执行下面命令
```
git clone https://github.com/Baloneo/ssr-gtk.git
cd ssr-git
chmod +x ./uninstall.sh
./uninstall.sh
```

#### 节点配置文件
默认会将配置文件的读写放在`~/.config/ssr-gtk/ssr`文件夹下 可以将自己的配置文件放置此目录 注意在每一次设置的时候都会清空此文件夹

![界面](https://raw.githubusercontent.com/Baloneo/ssr-gtk/master/01.png)
