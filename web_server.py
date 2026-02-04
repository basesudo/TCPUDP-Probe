"""
TCP调试工具 - Web版本
使用Flask + SocketIO提供Web服务
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
import os
from typing import Optional, Tuple

from network import get_network_interfaces, NetworkInterface, TCPClient, TCPServer
from utils import (
    bytes_to_hex, hex_to_bytes, is_valid_hex,
    format_received_data, format_sent_data, HistoryManager
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tcp-tool-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 全局状态
class AppState:
    def __init__(self):
        self.tcp_client = TCPClient()
        self.tcp_server = TCPServer()
        self.connection_history: list[tuple[str, int]] = []
        self.history_manager = HistoryManager()
        self.current_client_sid: Optional[str] = None
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置网络回调"""
        self.tcp_client.on_data_received = self._on_client_data
        self.tcp_client.on_disconnected = self._on_client_disconnected
        self.tcp_server.on_client_connected = self._on_server_client_connected
        self.tcp_server.on_client_disconnected = self._on_server_client_disconnected
        self.tcp_server.on_data_received = self._on_server_data
    
    def _on_client_data(self, data: bytes):
        """客户端接收到数据"""
        formatted = format_received_data(data, show_hex=True)
        socketio.emit('receive_data', {'data': formatted, 'hex': bytes_to_hex(data)}, room=self.current_client_sid)
    
    def _on_client_disconnected(self):
        """客户端断开连接"""
        socketio.emit('connection_status', {'connected': False, 'mode': 'client'}, room=self.current_client_sid)
    
    def _on_server_client_connected(self, ip: str, port: int):
        """服务器有客户端连接"""
        socketio.emit('server_client_connected', {'ip': ip, 'port': port}, room=self.current_client_sid)
    
    def _on_server_client_disconnected(self, ip: str, port: int):
        """服务器客户端断开"""
        socketio.emit('server_client_disconnected', {'ip': ip, 'port': port}, room=self.current_client_sid)
    
    def _on_server_data(self, ip: str, port: int, data: bytes):
        """服务器接收到数据"""
        formatted = format_received_data(data, show_hex=True)
        socketio.emit('receive_data', {
            'data': formatted, 
            'hex': bytes_to_hex(data),
            'from': f"{ip}:{port}"
        }, room=self.current_client_sid)

# 全局状态实例
app_state = AppState()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    app_state.current_client_sid = request.sid
    # 发送网卡列表
    interfaces = get_network_interfaces()
    interface_list = [{'name': iface.name, 'ip': iface.ip} for iface in interfaces]
    emit('interfaces', interface_list)
    
    # 加载并发送配置
    _load_config()
    emit('connection_history', app_state.connection_history)
    emit('send_history', app_state.history_manager.to_list())
    
    # 发送当前连接状态
    emit('connection_status', {
        'connected': app_state.tcp_client.connected,
        'mode': 'client' if app_state.tcp_client.connected else None
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    app_state.current_client_sid = None

@socketio.on('get_interfaces')
def handle_get_interfaces():
    """获取网卡列表"""
    interfaces = get_network_interfaces()
    interface_list = [{'name': iface.name, 'ip': iface.ip} for iface in interfaces]
    emit('interfaces', interface_list)

@socketio.on('client_connect')
def handle_client_connect(data):
    """客户端连接"""
    ip = data.get('ip')
    port = data.get('port')
    source_ip = data.get('source_ip', '0.0.0.0')
    
    if app_state.tcp_client.connect(ip, port, source_ip):
        emit('connection_status', {'connected': True, 'mode': 'client', 'target': f"{ip}:{port}"})
    else:
        emit('error', {'message': '连接失败'})

@socketio.on('client_disconnect')
def handle_client_disconnect():
    """客户端断开"""
    app_state.tcp_client.disconnect()
    emit('connection_status', {'connected': False, 'mode': 'client'})

@socketio.on('server_start')
def handle_server_start(data):
    """启动服务器"""
    bind_ip = data.get('bind_ip', '0.0.0.0')
    port = data.get('port')
    
    if app_state.tcp_server.start(bind_ip, port):
        emit('server_status', {'running': True, 'address': f"{bind_ip}:{port}"})
    else:
        emit('error', {'message': '启动服务器失败'})

@socketio.on('server_stop')
def handle_server_stop():
    """停止服务器"""
    app_state.tcp_server.stop()
    emit('server_status', {'running': False})

@socketio.on('send_data')
def handle_send_data(data):
    """发送数据"""
    data_str = data.get('data', '')
    is_hex = data.get('is_hex', True)
    save_history = data.get('save_history', False)
    target_client = data.get('target_client')
    
    # 转换数据
    if is_hex:
        if not is_valid_hex(data_str):
            emit('error', {'message': '无效的十六进制数据'})
            return
        send_bytes = hex_to_bytes(data_str)
    else:
        send_bytes = data_str.encode('utf-8')
    
    # 发送
    success = False
    if app_state.tcp_client.connected:
        success = app_state.tcp_client.send(send_bytes)
    elif app_state.tcp_server.running:
        if target_client:
            client_addr = tuple(target_client)
            success = app_state.tcp_server.send_to_client(client_addr, send_bytes)
        else:
            app_state.tcp_server.broadcast(send_bytes)
            success = True
    
    if success:
        formatted = format_sent_data(send_bytes, show_hex=True)
        emit('send_success', {'data': formatted})
        
        # 保存到历史
        if save_history:
            app_state.history_manager.add(data_str)
            _save_config()
            emit('send_history', app_state.history_manager.to_list())
    else:
        emit('error', {'message': '发送失败'})

@socketio.on('save_connection')
def handle_save_connection(data):
    """保存连接配置"""
    ip = data.get('ip')
    port = data.get('port')
    
    conn = (ip, port)
    if conn in app_state.connection_history:
        app_state.connection_history.remove(conn)
    
    app_state.connection_history.insert(0, conn)
    if len(app_state.connection_history) > 20:
        app_state.connection_history = app_state.connection_history[:20]
    
    _save_config()
    emit('connection_history', app_state.connection_history)

@socketio.on('update_remark')
def handle_update_remark(data):
    """更新备注"""
    index = data.get('index')
    remark = data.get('remark', '')
    
    item = app_state.history_manager.get_item(index)
    if item:
        item.remark = remark
        _save_config()
        emit('send_history', app_state.history_manager.to_list())

def _load_config():
    """加载配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 加载连接历史
                saved_history = config.get('connection_history', [])
                app_state.connection_history = []
                for item in saved_history:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        app_state.connection_history.append((item[0], int(item[1])))
                # 加载发送历史
                send_history = config.get('send_history', [])
                app_state.history_manager.from_list(send_history)
    except Exception as e:
        print(f"加载配置失败: {e}")

def _save_config():
    """保存配置"""
    try:
        config = {
            'connection_history': app_state.connection_history,
            'send_history': app_state.history_manager.to_list()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("TCP调试工具 - Web版本")
    print("=" * 50)
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
