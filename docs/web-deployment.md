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

## 重要说明：网卡IP获取

### 局域网访问时的网卡显示

当其他设备通过 `http://你的IP:5000` 访问Web版时：

⚠️ **页面上显示的网卡列表是服务器（你的电脑）的网卡，不是访问者的网卡。**

```
访问者电脑 (192.168.1.50) 
    ↓ 访问 http://192.168.1.100:5000
    ↓
服务器 (192.168.1.100) - 显示的是这台电脑的网卡
```

### 为什么这样设计

Web版的"网卡选择"用于控制服务器端的网络行为：
- **客户端模式**：选择从哪个网卡发起TCP连接
- **服务器模式**：选择在哪个网卡上监听端口

### 访问者的IP能获取吗

可以获取访问者的**IP地址**，但**无法获取网卡列表**：

```python
from flask import request

# 获取访问者的IP（如 192.168.1.50）
visitor_ip = request.remote_addr
```

**限制原因**：
1. 浏览器安全策略禁止JavaScript获取用户网卡信息
2. 隐私保护要求

### 如果访问者需要使用自己的网卡

每台电脑需要运行自己的Web服务器：
1. 在访问者的电脑上安装Python环境
2. 复制项目文件到该电脑
3. 运行 `python web_server.py`
4. 访问 `http://localhost:5000`

## 数据流向说明

### TCP通信的实际路径

当访问者通过浏览器使用TCP调试功能时：

```
访问者浏览器 (192.168.1.50)
    ↓ 点击"发送"按钮
    WebSocket 发送数据到服务器
    ↓
服务器 (192.168.1.100)
    ↓ 服务器上的TCP客户端/服务器
    通过服务器的网卡发送TCP数据
    ↓
目标设备 (如 192.168.1.200:8080)
```

### 关键点

| 组件 | 所在位置 | 功能 |
|-----|---------|------|
| Web界面 | 访问者的浏览器 | 提供操作界面 |
| TCP连接 | 服务器 | 实际的网络通信 |
| 网卡 | 服务器 | 发送/接收数据 |
| 数据收发 | 服务器 | 执行TCP操作 |

### 实际应用场景

**场景1：访问者调试远程设备**
```
访问者(办公室) → 服务器(机房) → 目标设备(生产线)
              Web界面操作    服务器网卡实际通信
```

**场景2：多人共享一台调试服务器**
```
访问者A ─┐
访问者B ─┼→ 服务器 → 目标设备
访问者C ─┘   (共用服务器的网卡)
```

### 优势与限制

**优势：**
- ✅ **集中管理** - 一台服务器可以服务多人
- ✅ **远程调试** - 访问者无需安装任何软件
- ✅ **统一出口** - 所有TCP流量从服务器发出，便于管理

**限制：**
- ⚠️ **网络位置固定** - TCP连接只能从服务器发起
- ⚠️ **无法使用访问者本地网卡** - 如访问者想用自己的电脑直连设备，需要在自己电脑上运行Web服务器

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
