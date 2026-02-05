import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional, Tuple
import json
import os
import sys

from network import get_network_interfaces, NetworkInterface, TCPClient, TCPServer, UDPClient, UDPServer
from utils import (
    bytes_to_hex, hex_to_bytes, is_valid_hex,
    format_received_data, format_sent_data, HistoryManager, HistoryItem
)

# 获取程序运行目录（支持打包后的exe）
def get_app_dir():
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的exe运行
        return os.path.dirname(sys.executable)
    else:
        # 直接运行py文件
        return os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(get_app_dir(), "config.json")


class TCPToolGUI:
    """TCP调试工具GUI"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TCP/UDP 调试工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 网络组件
        self.interfaces: list[NetworkInterface] = []
        self.tcp_client = TCPClient()
        self.tcp_server = TCPServer()
        self.udp_client = UDPClient()
        self.udp_server = UDPServer()
        
        # 状态
        self.is_server_mode = False
        self.protocol_mode = tk.StringVar(value="TCP")  # TCP/UDP
        self.show_hex = tk.BooleanVar(value=True)
        self.show_binary = tk.BooleanVar(value=False)  # 二进制显示
        self.send_hex = tk.BooleanVar(value=True)
        self.selected_client: Optional[Tuple[str, int]] = None
        self.history_manager = HistoryManager()
        self.connection_history: list[tuple[str, int]] = []  # 连接历史 (ip, port)
        self.udp_connection_history: list[tuple[str, int]] = []  # UDP连接历史
        
        # 设置回调
        self.tcp_client.on_data_received = self._on_client_data
        self.tcp_client.on_disconnected = self._on_client_disconnected
        self.tcp_server.on_client_connected = self._on_server_client_connected
        self.tcp_server.on_client_disconnected = self._on_server_client_disconnected
        self.tcp_server.on_data_received = self._on_server_data
        self.udp_client.on_data_received = self._on_udp_client_data
        self.udp_server.on_data_received = self._on_udp_server_data
        
        # 加载配置
        self._load_config()
        
        self._create_widgets()
        self._refresh_interfaces()
        
        # 更新连接历史显示
        self._update_connection_history_combo()
        
        # 更新发送历史显示
        self._update_history_combo()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # ===== 顶部控制区 =====
        control_frame = ttk.LabelFrame(main_frame, text="网络配置", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # 网卡选择
        ttk.Label(control_frame, text="网卡/IP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.interface_combo = ttk.Combobox(control_frame, state="readonly", width=40)
        self.interface_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(control_frame, text="刷新", command=self._refresh_interfaces).grid(row=0, column=2, padx=(0, 10))
        
        # 协议选择
        ttk.Label(control_frame, text="协议:").grid(row=0, column=3, padx=(20, 5))
        ttk.Radiobutton(control_frame, text="TCP", variable=self.protocol_mode,
                       value="TCP", command=self._on_protocol_change).grid(row=0, column=4, padx=(0, 5))
        ttk.Radiobutton(control_frame, text="UDP", variable=self.protocol_mode,
                       value="UDP", command=self._on_protocol_change).grid(row=0, column=5, padx=(0, 20))
        
        # 模式选择
        self.mode_var = tk.StringVar(value="client")
        ttk.Radiobutton(control_frame, text="客户端模式", variable=self.mode_var, 
                       value="client", command=self._on_mode_change).grid(row=0, column=6, padx=(0, 10))
        ttk.Radiobutton(control_frame, text="服务器模式", variable=self.mode_var,
                       value="server", command=self._on_mode_change).grid(row=0, column=7)
        
        # ===== 连接配置区 =====
        self.config_frame = ttk.LabelFrame(main_frame, text="连接配置", padding="10")
        self.config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.config_frame.columnconfigure(1, weight=1)
        
        # 客户端模式配置
        self.client_config_frame = ttk.Frame(self.config_frame)
        self.client_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 历史连接选择
        ttk.Label(self.client_config_frame, text="历史:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.conn_history_combo = ttk.Combobox(self.client_config_frame, state="readonly", width=35)
        self.conn_history_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.conn_history_combo.bind('<<ComboboxSelected>>', self._on_connection_history_select)
        ttk.Button(self.client_config_frame, text="备注", width=4, command=self._add_connection_remark).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(self.client_config_frame, text="删除", width=4, command=self._delete_connection_history_item).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(self.client_config_frame, text="目标IP:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.target_ip_entry = ttk.Entry(self.client_config_frame, width=20)
        self.target_ip_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 0), sticky=(tk.W, tk.E))
        self.target_ip_entry.insert(0, "127.0.0.1")
        
        ttk.Label(self.client_config_frame, text="端口:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.target_port_entry = ttk.Entry(self.client_config_frame, width=8)
        self.target_port_entry.grid(row=1, column=3, padx=(0, 10), pady=(5, 0), sticky=tk.W)
        self.target_port_entry.insert(0, "8080")
        
        # 自动保存复选框（默认勾选）
        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.client_config_frame, text="自动保存", variable=self.auto_save_var).grid(row=1, column=4, padx=(0, 10), pady=(5, 0))
        
        self.connect_btn = ttk.Button(self.client_config_frame, text="连接", command=self._toggle_client_connection)
        self.connect_btn.grid(row=1, column=5, padx=(0, 10), pady=(5, 0))
        
        self.client_status_label = ttk.Label(self.client_config_frame, text="未连接", foreground="red")
        self.client_status_label.grid(row=1, column=6, pady=(5, 0))
        
        # 服务器模式配置
        self.server_config_frame = ttk.Frame(self.config_frame)
        # 默认隐藏
        
        ttk.Label(self.server_config_frame, text="监听端口:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.listen_port_entry = ttk.Entry(self.server_config_frame, width=8)
        self.listen_port_entry.grid(row=0, column=1, padx=(0, 10))
        self.listen_port_entry.insert(0, "8080")
        
        self.start_server_btn = ttk.Button(self.server_config_frame, text="启动服务器", command=self._toggle_server)
        self.start_server_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.server_status_label = ttk.Label(self.server_config_frame, text="未启动", foreground="red")
        self.server_status_label.grid(row=0, column=3)
        
        # 客户端列表（服务器模式）
        self.client_list_frame = ttk.LabelFrame(self.server_config_frame, text="已连接客户端", padding="5")
        self.client_list_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.client_listbox = tk.Listbox(self.client_list_frame, height=3)
        self.client_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.client_listbox.bind('<<ListboxSelect>>', self._on_client_select)
        
        client_scrollbar = ttk.Scrollbar(self.client_list_frame, orient=tk.VERTICAL, command=self.client_listbox.yview)
        client_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.client_listbox.config(yscrollcommand=client_scrollbar.set)
        
        # ===== 数据区 =====
        # 接收区
        receive_frame = ttk.LabelFrame(main_frame, text="接收数据", padding="10")
        receive_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        receive_frame.columnconfigure(0, weight=1)
        receive_frame.rowconfigure(0, weight=1)
        
        self.receive_text = scrolledtext.ScrolledText(receive_frame, wrap=tk.WORD, height=20)
        self.receive_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        receive_btn_frame = ttk.Frame(receive_frame)
        receive_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Checkbutton(receive_btn_frame, text="十六进制显示", variable=self.show_hex).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(receive_btn_frame, text="二进制显示", variable=self.show_binary).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(receive_btn_frame, text="清空", command=self._clear_receive).pack(side=tk.LEFT)
        ttk.Button(receive_btn_frame, text="保存", command=self._save_receive).pack(side=tk.LEFT, padx=(5, 0))
        
        # 发送区
        send_frame = ttk.LabelFrame(main_frame, text="发送数据", padding="10")
        send_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        send_frame.columnconfigure(0, weight=1)
        send_frame.rowconfigure(0, weight=1)
        
        self.send_text = scrolledtext.ScrolledText(send_frame, wrap=tk.WORD, height=10)
        self.send_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 历史记录
        history_frame = ttk.Frame(send_frame)
        history_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(history_frame, text="历史:").pack(side=tk.LEFT, padx=(0, 5))
        self.history_combo = ttk.Combobox(history_frame, state="readonly", width=28)
        self.history_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.history_combo.bind('<<ComboboxSelected>>', self._on_history_select)
        ttk.Button(history_frame, text="备注", width=4, command=self._add_remark).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_frame, text="删除", width=4, command=self._delete_history_item).pack(side=tk.LEFT, padx=(0, 5))
        
        send_btn_frame = ttk.Frame(send_frame)
        send_btn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Checkbutton(send_btn_frame, text="十六进制发送", variable=self.send_hex).pack(side=tk.LEFT, padx=(0, 10))
        # 保存到历史复选框（默认不勾选）
        self.save_to_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(send_btn_frame, text="保存到历史", variable=self.save_to_history_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(send_btn_frame, text="发送", command=self._send_data).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(send_btn_frame, text="清空", command=self._clear_send).pack(side=tk.LEFT)
    
    def _refresh_interfaces(self):
        """刷新网卡列表"""
        self.interfaces = get_network_interfaces()
        interface_names = [str(iface) for iface in self.interfaces]
        self.interface_combo['values'] = interface_names
        if interface_names:
            self.interface_combo.current(0)
    
    def _get_selected_interface(self) -> Optional[NetworkInterface]:
        """获取选中的网卡"""
        idx = self.interface_combo.current()
        if idx >= 0 and idx < len(self.interfaces):
            return self.interfaces[idx]
        return None
    
    def _on_mode_change(self):
        """模式切换"""
        mode = self.mode_var.get()
        self.is_server_mode = (mode == "server")
        protocol = self.protocol_mode.get()
        
        # 更新按钮命令
        if protocol == "TCP":
            self.connect_btn.config(command=self._toggle_client_connection)
            self.start_server_btn.config(command=self._toggle_server)
        else:  # UDP
            self.connect_btn.config(command=self._toggle_udp_connection)
            self.start_server_btn.config(command=self._toggle_udp_server)
        
        if self.is_server_mode:
            self.client_config_frame.grid_remove()
            self.server_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
            # 断开客户端连接
            if protocol == "TCP" and self.tcp_client.connected:
                self._toggle_client_connection()
            elif protocol == "UDP" and self.udp_client.connected:
                self._toggle_udp_connection()
        else:
            self.server_config_frame.grid_remove()
            self.client_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
            # 停止服务器
            if protocol == "TCP" and self.tcp_server.running:
                self._toggle_server()
            elif protocol == "UDP" and self.udp_server.running:
                self._toggle_udp_server()
    
    def _toggle_client_connection(self, skip_save: bool = False):
        """切换客户端连接状态"""
        if self.tcp_client.connected:
            self.tcp_client.disconnect()
            self.connect_btn.config(text="连接")
            self.client_status_label.config(text="未连接", foreground="red")
        else:
            iface = self._get_selected_interface()
            if not iface:
                messagebox.showerror("错误", "请选择网卡")
                return
            
            target_ip = self.target_ip_entry.get().strip()
            try:
                target_port = int(self.target_port_entry.get().strip())
            except ValueError:
                messagebox.showerror("错误", "端口必须是数字")
                return
            
            if self.tcp_client.connect(target_ip, target_port, iface.ip):
                self.connect_btn.config(text="断开")
                self.client_status_label.config(text="已连接", foreground="green")
                # 如果勾选了自动保存且不是跳过保存模式，保存连接
                if self.auto_save_var.get() and not skip_save:
                    self._save_connection()
            else:
                messagebox.showerror("错误", "连接失败")
    
    def _toggle_server(self):
        """切换服务器状态"""
        if self.tcp_server.running:
            self.tcp_server.stop()
            self.start_server_btn.config(text="启动服务器")
            self.server_status_label.config(text="未启动", foreground="red")
            self.client_listbox.delete(0, tk.END)
        else:
            iface = self._get_selected_interface()
            if not iface:
                messagebox.showerror("错误", "请选择网卡")
                return
            
            try:
                port = int(self.listen_port_entry.get().strip())
            except ValueError:
                messagebox.showerror("错误", "端口必须是数字")
                return
            
            if self.tcp_server.start(iface.ip, port):
                self.start_server_btn.config(text="停止服务器")
                self.server_status_label.config(text=f"运行中 ({iface.ip}:{port})", foreground="green")
            else:
                messagebox.showerror("错误", "启动服务器失败")
    
    def _on_client_data(self, data: bytes):
        """客户端接收到数据"""
        self.root.after(0, lambda: self._append_receive(data, from_server=False))
    
    def _on_client_disconnected(self):
        """客户端断开连接"""
        self.root.after(0, lambda: self._update_client_status(False))
    
    def _on_server_client_connected(self, ip: str, port: int):
        """服务器有客户端连接"""
        self.root.after(0, lambda: self._add_client(ip, port))
    
    def _on_server_client_disconnected(self, ip: str, port: int):
        """服务器客户端断开"""
        self.root.after(0, lambda: self._remove_client(ip, port))
    
    def _on_server_data(self, ip: str, port: int, data: bytes):
        """服务器接收到数据"""
        self.root.after(0, lambda: self._append_receive(data, from_server=True, client_addr=(ip, port)))
    
    def _update_client_status(self, connected: bool):
        """更新客户端连接状态"""
        if connected:
            self.connect_btn.config(text="断开")
            self.client_status_label.config(text="已连接", foreground="green")
        else:
            self.connect_btn.config(text="连接")
            self.client_status_label.config(text="未连接", foreground="red")
    
    def _add_client(self, ip: str, port: int):
        """添加客户端到列表"""
        client_str = f"{ip}:{port}"
        self.client_listbox.insert(tk.END, client_str)
    
    def _remove_client(self, ip: str, port: int):
        """从列表移除客户端"""
        client_str = f"{ip}:{port}"
        for i in range(self.client_listbox.size()):
            if self.client_listbox.get(i) == client_str:
                self.client_listbox.delete(i)
                break
    
    def _on_client_select(self, event):
        """选择客户端"""
        selection = self.client_listbox.curselection()
        if selection:
            client_str = self.client_listbox.get(selection[0])
            ip, port = client_str.rsplit(":", 1)
            self.selected_client = (ip, int(port))
    
    def _save_connection(self):
        """保存当前连接配置到历史"""
        ip = self.target_ip_entry.get().strip()
        port_str = self.target_port_entry.get().strip()
        
        if not ip or not port_str:
            messagebox.showwarning("提示", "请先填写目标IP和端口")
            return
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
        
        # 根据协议选择历史列表
        is_udp = self.protocol_mode.get() == "UDP"
        history_list = self.udp_connection_history if is_udp else self.connection_history
        
        # 检查是否已存在（按IP和端口匹配）
        existing_idx = -1
        for i, item in enumerate(history_list):
            if item["ip"] == ip and item["port"] == port:
                existing_idx = i
                break
        
        if existing_idx >= 0:
            # 如果已存在，移到开头（保留原有备注）
            existing_item = history_list.pop(existing_idx)
            history_list.insert(0, existing_item)
        else:
            # 新连接，添加到开头
            history_list.insert(0, {"ip": ip, "port": port, "remark": ""})
        
        # 限制历史数量
        if len(history_list) > 20:
            history_list[:] = history_list[:20]
        
        self._update_connection_history_combo()
        
        # 保存到配置文件
        self._save_config()
    
    def _update_connection_history_combo(self):
        """更新连接历史下拉框"""
        is_udp = self.protocol_mode.get() == "UDP"
        history_list = self.udp_connection_history if is_udp else self.connection_history
        history_names = []
        for item in history_list:
            if item.get("remark"):
                history_names.append(f"[{item['remark']}] {item['ip']}:{item['port']}")
            else:
                history_names.append(f"{item['ip']}:{item['port']}")
        self.conn_history_combo['values'] = history_names
    
    def _load_config(self):
        """从配置文件加载连接历史"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 加载TCP连接历史（支持新旧两种格式）
                    saved_history = config.get('connection_history', [])
                    self.connection_history = []
                    for item in saved_history:
                        if isinstance(item, dict):
                            # 新格式: {"ip": ip, "port": port, "remark": remark}
                            self.connection_history.append({
                                "ip": item["ip"],
                                "port": int(item["port"]),
                                "remark": item.get("remark", "")
                            })
                        elif isinstance(item, (list, tuple)) and len(item) == 2:
                            # 旧格式: [ip, port]
                            self.connection_history.append({
                                "ip": item[0],
                                "port": int(item[1]),
                                "remark": ""
                            })
                    # 加载UDP连接历史（支持新旧两种格式）
                    udp_history = config.get('udp_connection_history', [])
                    self.udp_connection_history = []
                    for item in udp_history:
                        if isinstance(item, dict):
                            # 新格式
                            self.udp_connection_history.append({
                                "ip": item["ip"],
                                "port": int(item["port"]),
                                "remark": item.get("remark", "")
                            })
                        elif isinstance(item, (list, tuple)) and len(item) == 2:
                            # 旧格式
                            self.udp_connection_history.append({
                                "ip": item[0],
                                "port": int(item[1]),
                                "remark": ""
                            })
                    # 加载发送历史
                    send_history = config.get('send_history', [])
                    self.history_manager.from_list(send_history)
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            config = {
                'connection_history': self.connection_history,
                'udp_connection_history': self.udp_connection_history,
                'send_history': self.history_manager.to_list()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _on_connection_history_select(self, event):
        """选择历史连接并自动连接"""
        idx = self.conn_history_combo.current()
        history_list = self.udp_connection_history if self.protocol_mode.get() == "UDP" else self.connection_history
        
        if idx >= 0 and idx < len(history_list):
            item = history_list[idx]
            ip = item["ip"]
            port = item["port"]
            
            # 如果当前已连接，弹出确认框
            protocol = self.protocol_mode.get()
            is_connected = (protocol == "TCP" and self.tcp_client.connected) or (protocol == "UDP" and self.udp_client.connected)
            
            if is_connected:
                current_ip = self.target_ip_entry.get().strip()
                current_port = self.target_port_entry.get().strip()
                if messagebox.askyesno("确认切换", f"当前已连接到 {current_ip}:{current_port}\n是否断开并连接到 {ip}:{port}?"):
                    # 断开当前连接
                    if protocol == "TCP":
                        self._toggle_client_connection()
                    else:
                        self._toggle_udp_connection()
                else:
                    return
            
            self.target_ip_entry.delete(0, tk.END)
            self.target_ip_entry.insert(0, ip)
            self.target_port_entry.delete(0, tk.END)
            self.target_port_entry.insert(0, str(port))
            
            # 自动连接（跳过保存，因为是从历史记录中选择的）
            if protocol == "TCP":
                self._toggle_client_connection(skip_save=True)
            else:
                self._toggle_udp_connection(skip_save=True)
    
    def _add_connection_remark(self):
        """为连接历史添加备注"""
        idx = self.conn_history_combo.current()
        if idx < 0:
            messagebox.showwarning("提示", "请先选择一条历史记录")
            return
        
        history_list = self.udp_connection_history if self.protocol_mode.get() == "UDP" else self.connection_history
        if idx >= len(history_list):
            return
        
        item = history_list[idx]
        current_remark = item.get("remark", "")
        
        # 弹出输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加备注")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text=f"为 {item['ip']}:{item['port']} 添加备注:").pack(pady=(10, 5))
        
        remark_entry = ttk.Entry(dialog, width=35)
        remark_entry.pack(pady=5)
        remark_entry.insert(0, current_remark)
        remark_entry.select_range(0, tk.END)
        remark_entry.focus()
        
        def save_remark():
            remark = remark_entry.get().strip()
            item["remark"] = remark
            self._update_connection_history_combo()
            self._save_config()
            dialog.destroy()
        
        def on_enter(event):
            save_remark()
        
        remark_entry.bind('<Return>', on_enter)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=save_remark).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _delete_connection_history_item(self):
        """删除选中的连接历史记录"""
        idx = self.conn_history_combo.current()
        if idx < 0:
            messagebox.showwarning("提示", "请先选择一条历史记录")
            return
        
        history_list = self.udp_connection_history if self.protocol_mode.get() == "UDP" else self.connection_history
        if idx >= len(history_list):
            return
        
        item = history_list[idx]
        if messagebox.askyesno("确认删除", f"确定要删除连接 {item['ip']}:{item['port']} 吗？"):
            history_list.pop(idx)
            self._update_connection_history_combo()
            self._save_config()
            # 清空输入框
            self.target_ip_entry.delete(0, tk.END)
            self.target_port_entry.delete(0, tk.END)
    
    def _append_receive(self, data: bytes, from_server: bool = False, client_addr: Optional[Tuple[str, int]] = None):
        """追加接收数据到显示区"""
        show_hex = self.show_hex.get()
        
        if from_server and client_addr:
            prefix = f"[来自 {client_addr[0]}:{client_addr[1]}] "
            self.receive_text.insert(tk.END, prefix)
        
        formatted = format_received_data(data, show_hex, self.show_binary.get())
        self.receive_text.insert(tk.END, formatted)
        self.receive_text.see(tk.END)
    
    def _send_data(self):
        """发送数据"""
        data_str = self.send_text.get("1.0", tk.END).strip()
        if not data_str:
            return
        
        # 如果勾选了保存到历史
        if self.save_to_history_var.get():
            self.history_manager.add(data_str)
            self._update_history_combo()
            self._save_config()
        
        # 转换数据
        if self.send_hex.get():
            if not is_valid_hex(data_str):
                messagebox.showerror("错误", "无效的十六进制数据")
                return
            data = hex_to_bytes(data_str)
        else:
            data = data_str.encode('utf-8')
        
        # 发送
        success = False
        protocol = self.protocol_mode.get()
        
        if protocol == "TCP":
            if self.is_server_mode:
                if self.selected_client:
                    success = self.tcp_server.send_to_client(self.selected_client, data)
                else:
                    self.tcp_server.broadcast(data)
                    success = True
            else:
                success = self.tcp_client.send(data)
        else:  # UDP
            if self.is_server_mode:
                if self.selected_client:
                    success = self.udp_server.send_to(self.selected_client[0], self.selected_client[1], data)
                else:
                    messagebox.showwarning("提示", "UDP服务器模式需要选择客户端")
                    return
            else:
                success = self.udp_client.send(data)
        
        if success:
            formatted = format_sent_data(data, self.show_hex.get(), self.show_binary.get())
            self.receive_text.insert(tk.END, formatted)
            self.receive_text.see(tk.END)
        else:
            messagebox.showerror("错误", "发送失败")
    
    def _send_and_save(self):
        """发送并保存到历史"""
        self._send_data(save_to_history=True)
    
    def _update_history_combo(self):
        """更新历史记录下拉框"""
        self.history_combo['values'] = self.history_manager.get_display_names()
    
    def _on_history_select(self, event):
        """选择历史记录"""
        idx = self.history_combo.current()
        item = self.history_manager.get_item(idx)
        if item:
            self.send_text.delete("1.0", tk.END)
            self.send_text.insert("1.0", item.data)
    
    def _add_remark(self):
        """为选中的历史记录添加备注"""
        idx = self.history_combo.current()
        if idx < 0:
            messagebox.showwarning("提示", "请先选择一条历史记录")
            return
        
        item = self.history_manager.get_item(idx)
        if not item:
            return
        
        # 弹出输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加备注")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="备注:").pack(pady=(10, 5))
        remark_entry = ttk.Entry(dialog, width=35)
        remark_entry.pack(pady=(0, 10))
        remark_entry.insert(0, item.remark)
        
        def save_remark():
            remark = remark_entry.get().strip()
            item.remark = remark
            self._update_history_combo()
            self._save_config()
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="确定", command=save_remark).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def _delete_history_item(self):
        """删除选中的发送历史记录"""
        idx = self.history_combo.current()
        if idx < 0:
            messagebox.showwarning("提示", "请先选择一条历史记录")
            return
        
        if messagebox.askyesno("确认删除", "确定要删除这条历史记录吗？"):
            self.history_manager.delete_item(idx)
            self._update_history_combo()
            self._save_config()
            # 清空发送区
            self.send_text.delete("1.0", tk.END)
    
    def _clear_receive(self):
        """清空接收区"""
        self.receive_text.delete("1.0", tk.END)
    
    def _clear_send(self):
        """清空发送区"""
        self.send_text.delete("1.0", tk.END)
    
    def _save_receive(self):
        """保存接收数据"""
        from tkinter import filedialog
        content = self.receive_text.get("1.0", tk.END)
        if not content.strip():
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def on_close(self):
        """关闭窗口"""
        self.tcp_client.disconnect()
        self.tcp_server.stop()
        self.udp_client.disconnect()
        self.udp_server.stop()
        self.root.destroy()
    
    # ===== UDP相关方法 =====
    
    def _on_protocol_change(self):
        """协议切换"""
        self._on_mode_change()
    
    def _on_udp_client_data(self, ip: str, port: int, data: bytes):
        """UDP客户端接收数据"""
        show_hex = self.show_hex.get()
        formatted = format_received_data(data, show_hex, self.show_binary.get())
        self.receive_text.insert(tk.END, f"[来自 {ip}:{port}]\n{formatted}")
        self.receive_text.see(tk.END)
    
    def _on_udp_server_data(self, ip: str, port: int, data: bytes):
        """UDP服务器接收数据"""
        show_hex = self.show_hex.get()
        formatted = format_received_data(data, show_hex, self.show_binary.get())
        self.receive_text.insert(tk.END, f"[来自 {ip}:{port}]\n{formatted}")
        self.receive_text.see(tk.END)
        
        # 更新客户端列表
        client_addr = f"{ip}:{port}"
        if client_addr not in self.client_listbox.get(0, tk.END):
            self.client_listbox.insert(tk.END, client_addr)
    
    def _toggle_udp_connection(self, skip_save: bool = False):
        """切换UDP连接"""
        if self.udp_client.connected:
            self.udp_client.disconnect()
            self.connect_btn.config(text="连接")
            self.client_status_label.config(text="未连接", foreground="red")
        else:
            ip = self.target_ip_entry.get().strip()
            port_str = self.target_port_entry.get().strip()
            
            if not ip or not port_str:
                messagebox.showwarning("提示", "请填写目标IP和端口")
                return
            
            try:
                port = int(port_str)
            except ValueError:
                messagebox.showerror("错误", "端口必须是数字")
                return
            
            # 获取本地端口和广播选项
            local_port = 0
            broadcast = False
            
            if self.udp_client.connect(ip, port, local_port, broadcast):
                self.connect_btn.config(text="断开")
                self.client_status_label.config(text="已连接", foreground="green")
                # 如果勾选了自动保存且不是跳过保存模式，保存连接
                if self.auto_save_var.get() and not skip_save:
                    self._save_connection()
            else:
                messagebox.showerror("错误", "UDP连接失败")
    
    def _toggle_udp_server(self):
        """切换UDP服务器"""
        if self.udp_server.running:
            self.udp_server.stop()
            self.start_server_btn.config(text="启动服务器")
            self.server_status_label.config(text="未启动", foreground="red")
            self.client_listbox.delete(0, tk.END)
        else:
            bind_ip = self.interface_combo.get().split("(")[-1].rstrip(")") if "(" in self.interface_combo.get() else "0.0.0.0"
            port_str = self.listen_port_entry.get().strip()
            
            if not port_str:
                messagebox.showwarning("提示", "请填写监听端口")
                return
            
            try:
                port = int(port_str)
            except ValueError:
                messagebox.showerror("错误", "端口必须是数字")
                return
            
            if self.udp_server.start(bind_ip, port):
                self.start_server_btn.config(text="停止服务器")
                self.server_status_label.config(text="运行中", foreground="green")
            else:
                messagebox.showerror("错误", "启动UDP服务器失败")
