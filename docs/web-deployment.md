# TCP调试工具 - Web版部署运行指南

## 简介

TCP调试工具Web版基于Flask + Socket.IO构建，提供浏览器访问的TCP调试功能。支持客户端/服务器模式、十六进制收发、历史记录等功能。

## 环境要求

- Python 3.8+
- 依赖包：
  - flask
  - flask-socketio
  - psutil

## 安装依赖

```bash
pip install flask flask-socketio psutil
```

## 启动Web服务

### 方式一：直接运行

```bash
python web_server.py
```

启动后显示：
```
==================================================
TCP调试工具 - Web版本
==================================================
访问地址: http://localhost:5000
按 Ctrl+C 停止服务
==================================================
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.x.x:5000
```

### 方式二：指定端口运行

修改 `web_server.py` 最后一行：
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=False)  # 使用8080端口
```

## 访问方式

### 本机访问

浏览器访问：
```
http://localhost:5000
```
或
```
http://127.0.0.1:5000
```

### 局域网访问

**1. 查看本机IP地址**

Windows:
```cmd
ipconfig
```

找到IPv4地址，例如：`192.168.1.100`

**2. 其他设备访问**

在同一局域网的电脑/手机/平板上，浏览器访问：
```
http://192.168.1.100:5000
```
（将IP替换为你的实际IP）

## 防火墙配置

如果局域网设备无法访问，需要配置Windows防火墙：

### 方法1：命令行（推荐）

以管理员身份运行PowerShell：
```powershell
# 添加入站规则允许5000端口
netsh advfirewall firewall add rule name="TCP Tool Web" dir=in action=allow protocol=tcp localport=5000

# 如果需要删除规则
netsh advfirewall firewall delete rule name="TCP Tool Web"
```

### 方法2：图形界面

1. 打开"Windows Defender 防火墙"
2. 点击"高级设置"
3. 点击"入站规则" → "新建规则"
4. 选择"端口" → "下一步"
5. 选择"TCP"，输入端口"5000" → "下一步"
6. 选择"允许连接" → "下一步"
7. 勾选所有配置文件 → "下一步"
8. 输入规则名称"TCP Tool Web" → "完成"

## 生产环境部署

### 使用Gunicorn（Linux/Mac）

```bash
# 安装gunicorn
pip install gunicorn

# 运行
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 0.0.0.0:5000 web_server:app
```

### 使用Waitress（Windows推荐）

```bash
# 安装waitress
pip install waitress

# 修改web_server.py，将最后一行改为：
from waitress import serve
serve(app, host='0.0.0.0', port=5000)
```

### 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 后台运行

### Windows - 使用NSSM

```cmd
# 下载nssm: https://nssm.cc/download
# 安装服务
nssm install TCPToolWeb "C:\Python39\python.exe" "C:\path\to\web_server.py"

# 启动服务
nssm start TCPToolWeb
```

### Linux - 使用Systemd

创建服务文件 `/etc/systemd/system/tcp-tool-web.service`：

```ini
[Unit]
Description=TCP Tool Web
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/tcp-tool
ExecStart=/usr/bin/python3 /path/to/tcp-tool/web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable tcp-tool-web
sudo systemctl start tcp-tool-web
```

## 常见问题

### Q: 启动时报错"Address already in use"

端口被占用，更换端口：
```python
socketio.run(app, host='0.0.0.0', port=8080)  # 改用8080端口
```

### Q: 局域网设备无法访问

1. 检查防火墙设置（见上文）
2. 确认服务器监听 `0.0.0.0` 而非 `127.0.0.1`
3. 检查网络连通性：`ping 服务器IP`

### Q: WebSocket连接失败

1. 检查浏览器控制台错误信息
2. 确认没有代理软件拦截
3. 尝试使用不同的浏览器

### Q: 如何修改默认端口

编辑 `web_server.py`，修改最后一行：
```python
socketio.run(app, host='0.0.0.0', port=你想要的端口, debug=False)
```

## 配置文件

Web版和桌面版共用 `config.json` 配置文件：

```json
{
  "connection_history": [
    ["192.168.1.100", 8080]
  ],
  "send_history": [
    {"data": "Hello", "remark": "测试消息"}
  ]
}
```

配置文件位于程序同目录，自动保存连接历史和发送历史。

## 功能对比

| 功能 | 桌面版 | Web版 |
|-----|-------|-------|
| 客户端模式 | ✅ | ✅ |
| 服务器模式 | ✅ | ✅ |
| 十六进制收发 | ✅ | ✅ |
| 连接历史 | ✅ | ✅ |
| 发送历史+备注 | ✅ | ✅ |
| 多客户端管理 | ✅ | 基础支持 |
| 跨平台访问 | ❌ | ✅ |
| 多人同时使用 | ❌ | ✅ |

## 安全提示

⚠️ **注意**：Web版默认无身份验证，建议：

1. 仅在受信任的局域网内使用
2. 不要暴露在公网
3. 如需公网访问，建议：
   - 添加HTTP Basic认证
   - 使用VPN/内网穿透工具
   - 配置Nginx反向代理+SSL

## 内网穿透（可选）

如需从外网访问，可使用内网穿透工具：

### ngrok
```bash
ngrok http 5000
```

### 花生壳
下载客户端并配置映射。

### FRP
自行搭建FRP服务器进行内网穿透。
