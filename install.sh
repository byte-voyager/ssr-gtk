#!/bin/bash

mkdir -p ~/.config/ssr-gtk/ssr

sudo mkdir -p /opt/ssr-gtk/ssr

sudo cp ./ssr-gtk-logo.png /opt/ssr-gtk/logo.png
sudo cp ./ssr-local /opt/ssr-gtk/ssr-local
sudo cp ./main.py /opt/ssr-gtk/ssr-gtk
sudo cp ./ssr-gtk.desktop /usr/share/applications/ssr-gtk.desktop

sudo chmod +x /opt/ssr-gtk/ssr-gtk
sudo chmod +x /opt/ssr-gtk/ssr-local

echo "success"
