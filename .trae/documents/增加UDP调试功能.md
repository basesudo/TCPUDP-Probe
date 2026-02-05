## 实现方案

### 1. 新增UDP网络类 (network.py)
- UDPClient: UDP客户端，支持发送/接收、广播模式
- UDPServer: UDP服务器，支持多客户端数据接收

### 2. 更新桌面版GUI (gui.py)
- 连接模式增加UDP客户端/UDP服务器选项
- UDP客户端界面：目标IP、端口、本地绑定端口、广播选项
- UDP服务器界面：监听端口、客户端列表

### 3. 更新Web版
- web_server.py: 添加UDP事件处理
- templates/index.html: 添加UDP模式选项

### 4. 配置文件
- UDP连接历史保存到config.json

## 任务列表
1. 创建UDPClient和UDPServer类
2. 更新gui.py添加UDP界面
3. 更新web_server.py添加UDP支持
4. 更新前端HTML添加UDP选项
5. 测试验证UDP功能

## 界面设计
UDP客户端：目标IP、端口、本地端口、广播选项
UDP服务器：监听端口、显示数据来源列表