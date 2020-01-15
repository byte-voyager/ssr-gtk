#!/usr/bin/env python3
import gi
import os
import signal
import threading
import subprocess
import builtins
import base64
import json
import urllib.request
import shutil

from typing import Text

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator

config_template = {
    "remarks": "",
    "server": "0.0.0.0",
    "server_ipv6": "::",
    "server_port": 8388,
    "local_address": "127.0.0.1",
    "local_port": 1080,
    "password": "m",
    "method": "aes-128-ctr",
    "protocol": "auth_aes128_md5",
    "protocol_param": "",
    "obfs": "tls1.2_ticket_auth_compatible",
    "obfs_param": "",
    "speed_limit_per_con": 0,
    "speed_limit_per_user": 0,
    "additional_ports": {},
    "additional_ports_only": False,
    "timeout": 120,
    "udp_timeout": 60,
    "dns_ipv6": False,
    "connect_verbose_info": 0,
    "redirect": "",
    "fast_open": False,
}

alias = {
    'obfsparam': 'obfs_param',
    'protoparam': 'protocol_param',
}


HOME = os.getenv("HOME")
LOGO_ICON_PATH = "/opt/ssr-gtk/logo.png"

STATE = {
    "CUR_SSR_PROC_ID": -1,
}

signal.signal(signal.SIGINT, signal.SIG_DFL)


class SSR(object):
    JSON_FILES_PATH = os.getenv('HOME') + '/.config/ssr-gtk/ssr/'

    @staticmethod
    def get_ssr_names():
        return os.listdir(SSR.JSON_FILES_PATH)

    @staticmethod
    def stop_ssr():
        if STATE['CUR_SSR_PROC_ID'] != -1:
            try:
                print('killing ', STATE['CUR_SSR_PROC_ID'])
                os.kill(STATE['CUR_SSR_PROC_ID'], signal.SIGKILL)
            except Exception:
                pass
        else:
            print('kill cur_subproc_id >>>', STATE['CUR_SSR_PROC_ID'])

    @staticmethod
    def decode_base64(context):
        """解码"""
        text = context.replace("-", "+").replace("_", "/")
        text = bytes(text, encoding="utf-8")
        missing_padding = 4 - len(text) % 4

        if missing_padding:
            text += b'=' * missing_padding
            try:
                return str(base64.decodebytes(text), encoding="utf-8")
            except Exception as e:
                print(e)
                return ""

    @staticmethod
    def ssrline2json(text: Text):
        """将一行行的ssr解码为json"""
        format_ssr_url = text[6:]
        try:
            server, server_port, protocol, method, obfs, other = SSR.decode_base64(format_ssr_url).split(":")
            password_base64, param_base64 = other.split("/?")
            password = SSR.decode_base64(password_base64)
            params = param_base64.split("&")
            for param in params:
                k, v = param.split("=", 1)
                if v:
                    v = SSR.decode_base64(v)
                    if k in alias and alias[k] in config_template:
                        config_template[alias[k]] = v
                    else:
                        config_template[k] = v

            remarks_base64 = str(base64.b64encode(config_template['remarks'].encode('utf-8')), "utf-8")
            config_template.update({
                'server': server,
                'server_port': int(server_port),
                'protocol': protocol,
                'method': method,
                'obfs': obfs,
                'password': password,
                'remarks_base64': remarks_base64,
                'enable': True,
            })
            return config_template
        except builtins.ValueError:
            pass
        except ValueError:
            pass

    @staticmethod
    def save_ssr_json_file(url, save_dir):
        """保存ssr json数据到本地"""
        try:
            shutil.rmtree(save_dir)
            os.mkdir(save_dir)
        except Exception as e:
            print(e)

        # 1 根据url得到base64编码数据
        try:
            print('start fetch ssr node data')
            user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
            headers = {"User-Agent": user_agent}
            req = urllib.request.Request(url, headers=headers)
            web = urllib.request.urlopen(req, timeout=10)
            print('start read ssr node data')
            web_data = web.read()
            print('start decode ssr node data')
            web_data = web_data.decode("utf-8")
        except Exception as e:
            return False, str(e)
        # 2 解码
        web_decode_data = SSR.decode_base64(web_data)
        # 3 遍历 保存到文件
        web_line_data = web_decode_data.splitlines()
        for line in web_line_data:
            json_data = SSR.ssrline2json(line)
            file_name = json_data.get("remarks", "no_name").replace("/", "-") + ".json"
            file_abs_name = os.path.join(save_dir, file_name)
            with open(file_abs_name, "w") as f:
                f.write(json.dumps(json_data, ensure_ascii=False))
                print(file_name, "已经保存")
        return True, ""

    @staticmethod
    def start_ssr(ssr_name, cb_show_msg, cb_stop):
        """在子线程中启动ssr进程"""
        if STATE['CUR_SSR_PROC_ID'] != -1:
            print('ssr running')
            return
        cb_show_msg("正在开启ssr {}".format(ssr_name))

        def run(name):
            print('start listing file ', name)
            p = subprocess.Popen(
                ["/opt/ssr-gtk/ssr-local", "-c", HOME + "/.config/ssr-gtk/ssr/{}".format(name)],
                shell=False,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            STATE['CUR_SSR_PROC_ID'] = p.pid
            while p.poll() is None:
                line = p.stderr.readline()
                line = line.strip()
                line = line.decode('utf-8')
                print('line >>>', line)
                cb_show_msg(line)

            STATE['CUR_SSR_PROC_ID'] = -1
            msg = "ssr进程已经终止 {}".format(p.returncode)
            cb_show_msg(msg)
            cb_stop()
            print(msg)

        t = threading.Thread(target=run, args=(ssr_name,))
        t.daemon = False
        t.start()


class SettingWindow(Gtk.Window):

    def on_ok_btn_clicked(self, *args):
        url = self.entry.get_text()
        with open(os.path.join(HOME, ".config/ssr-gtk/config.txt"), "w") as f:
            f.write(url)
            ok, msg = SSR.save_ssr_json_file(url, SSR.JSON_FILES_PATH)
            if not ok:
                self.label_msg.set_text(msg)
            else:
                self.label_msg.set_text("更新节点列表到本地成功 请关闭当前窗口后刷新节点列表")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("设置SSR节点信息")
        self.set_default_size(380, 50)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  # 垂直的盒子把水平占满

        self.entry = Gtk.Entry()
        with open(os.path.join(HOME, ".config/ssr-gtk/config.txt"), "a+") as f:
            f.seek(0)
            old_url = f.readline()
            print("old_url", old_url)
        self.entry.set_text(old_url or "设置ssr订阅地址")
        self.vbox.pack_start(self.entry, False, False, 0)

        # 在一个水平的容器添加两个元素 vv_box 用来占用所有的左边空余空间 button使用剩下的必须空间大小
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # vv_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.label_msg = Gtk.Label("节点文件存储在 ~/.config/ssr-gtk/ssr/")
        self.label_msg.set_selectable(True)
        self.button_ok = Gtk.Button("确认")
        self.button_ok.connect("clicked", self.on_ok_btn_clicked)
        hbox.pack_start(self.label_msg, True, True, 0)
        hbox.pack_start(self.button_ok, False, False, 0)
        self.vbox.pack_start(hbox, False, False, 0)

        self.add(self.vbox)

        self.present()
        self.show_all()


class AppWindow(Gtk.Window):

    def on_refresh_btn_clicked(self, *args):
        # 停止当前节点 更新文件列表缓存
        SSR.stop_ssr()
        self.on_ssr_stop()
        self.scroll_box.remove(self.listbox)
        self.init_ssr_names()

        self.cur_active_index = -1
        for switch in self.switchs:
            switch.destroy()
        self.switchs.clear()

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        # 更新self.ssr_names
        for index, name in enumerate(self.ssr_names):
            row1 = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

            label1 = Gtk.Label("［{0}］{1}".format(index, name), xalign=0.01)
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.pack_start(label1, False, True, 0)
            hbox.pack_start(vbox, True, True, 0)

            switch = Gtk.Switch()
            hbox.pack_start(switch, False, False, 0)
            switch.connect('notify::active', self.on_switch_clicked, "{}".format(name))
            self.switchs.append(switch)
            row1.add(hbox)
            self.listbox.add(row1)
        self.scroll_box.add(self.listbox)
        self.show_all()
        self.show_dialog("刷新列表成功")
        self.update_msg("刷新列表成功")

    def on_ssr_stop(self):
        if self.cur_active_index != -1:
            self.switchs[self.cur_active_index].set_active(False)

    def start_ssr(self, name):
        SSR.start_ssr(name, cb_show_msg=self.update_msg, cb_stop=self.on_ssr_stop)

    def show_dialog(self, msg):
        dialog = Gtk.MessageDialog(transient_for=self,
                                   modal=True,
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK,
                                   text='Message')
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()

    def create_header_bar(self):
        hb = Gtk.HeaderBar()
        hb.set_decoration_layout("menu:minimize,maximize,close")
        hb.set_title("酸酸乳")
        hb.set_show_close_button(True)
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.connect("clicked", self.on_refresh_btn_clicked)
        hb.pack_start(refresh_btn)
        settings_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        settings_btn.connect("clicked", self.on_setting_btn_clicked)
        hb.pack_start(settings_btn)
        return hb

    def on_setting_btn_clicked(self, *args):
        """TODO: 弹窗设置ssr的订阅地址"""
        SettingWindow()
        print("on_setting_btn_clicked called")

    def switch_open(self, clicked_index, name):
        if self.cur_active_index != -1:
            if clicked_index == self.cur_active_index:
                print('相同')
            else:
                self.switchs[self.cur_active_index].set_active(False)
        self.cur_active_index = clicked_index
        # 开启ssr进程
        self.start_ssr(name)

    def switch_close(self):
        SSR.stop_ssr()

    def update_content(self):
        pass

    def on_switch_clicked(self, switch, gparam, name):
        # self.hide()
        # return
        clicked_index = self.ssr_names.index(name)
        if switch.get_active():
            self.switch_open(clicked_index, name)
        else:
            self.switch_close()

    def create_content(self):
        self.init_ssr_names()

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        for index, name in enumerate(self.ssr_names):
            row1 = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)  # 水平的盒子把垂直占满

            label1 = Gtk.Label("［{0}］{1}".format(index, name), xalign=0.01)
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  # 垂直的盒子把水平占满 而且又只有一个子child
            vbox.pack_start(label1, False, False, 0)
            hbox.pack_start(vbox, True, True, 0)

            switch = Gtk.Switch()
            hbox.pack_start(switch, False, False, 0)
            switch.connect('notify::active', self.on_switch_clicked, "{}".format(name))
            self.switchs.append(switch)
            row1.add(hbox)

            self.listbox.add(row1)

        self.scroll_box = Gtk.ScrolledWindow()
        self.scroll_box.set_min_content_height(500)
        self.scroll_box.set_min_content_width(500)
        self.scroll_box.add(self.listbox)
        self.content_box.pack_start(self.scroll_box, True, True, 0)

        self.label = Gtk.Label(label="ready...", xalign=0.01)
        self.content_box.pack_end(self.label, True, True, 0)

        if self.cur_active_index != -1:
            self.switchs[self.cur_active_index].set_active(True)

    def update_msg(self, msg):
        self.label.set_text(msg)

    def init_ssr_names(self):
        self.ssr_names = SSR.get_ssr_names()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listbox = None
        self.label = None
        self.scroll_box = None
        self.cur_active_index = -1
        self.ssr_names = []
        self.switchs = []
        self.cur_subproc_id = -1
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_resizable(False)
        self.add(self.content_box)
        self.set_titlebar(self.create_header_bar())
        self.create_content()
        self.connect('delete-event', self.on_quit)

    def on_quit(self, *args):
        print('window hide')
        self.hide()
        return True


def show_window(menu, window):
    window.present()


def quit_app(*args):
    SSR.stop_ssr()
    Gtk.main_quit()


def build_menu(window):
    menu = Gtk.Menu()
    item_show = Gtk.MenuItem(label='show main window')
    item_show.connect('activate', show_window, window)
    item_quit = Gtk.MenuItem(label='exit')
    item_quit.connect('activate', quit_app)
    menu.append(item_show)
    menu.append(item_quit)
    menu.show_all()
    return menu


def main():
    window = AppWindow(application=None, title="酸酸乳")
    window.show_all()
    window.set_icon_from_file(LOGO_ICON_PATH)
    indicator = appindicator.Indicator.new("APPINDICATOR_ID",
                                           LOGO_ICON_PATH,
                                           appindicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu(window))
    window.present()
    Gtk.main()


if __name__ == '__main__':
    main()
