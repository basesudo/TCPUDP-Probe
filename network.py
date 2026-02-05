import socket
import psutil
import threading
import time
from typing import List, Tuple, Optional, Callable


class NetworkInterface:
    """网络接口信息"""
    def __init__(self, name: str, ip: str, is_ipv4: bool = True):
        self.name = name
        self.ip = ip
        self.is_ipv4 = is_ipv4
    
    def __str__(self):
        return f"{self.name} ({self.ip})"
    
    def __repr__(self):
        return self.__str__()


def get_network_interfaces() -> List[NetworkInterface]:
    """获取所有网络接口信息"""
    interfaces = []
    stats = psutil.net_if_addrs()
    
    for name, addrs in stats.items():
        for addr in addrs:
            # 只获取IPv4地址
            if addr.family == socket.AF_INET:
                interfaces.append(NetworkInterface(name, addr.address))
    
    return interfaces


class TCPClient:
    """TCP客户端"""
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.receive_thread: Optional[threading.Thread] = None
        self.on_data_received: Optional[Callable[[bytes], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.running = False
    
    def connect(self, target_ip: str, target_port: int, source_ip: str = "0.0.0.0") -> bool:
        """连接到服务器，可指定源IP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            
            # 绑定源IP（如果指定了具体IP而不是0.0.0.0）
            if source_ip and source_ip != "0.0.0.0":
                self.socket.bind((source_ip, 0))
            
            self.socket.connect((target_ip, target_port))
            self.connected = True
            self.running = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self.connected or not self.socket:
            return False
        try:
            self.socket.sendall(data)
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            self.connected = False
            return False
    
    def _receive_loop(self):
        """接收数据循环"""
        while self.running and self.connected:
            try:
                self.socket.settimeout(0.5)
                data = self.socket.recv(4096)
                if data:
                    if self.on_data_received:
                        self.on_data_received(data)
                else:
                    # 连接关闭
                    self.connected = False
                    if self.on_disconnected:
                        self.on_disconnected()
                    break
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接收错误: {e}")
                    self.connected = False
                    if self.on_disconnected:
                        self.on_disconnected()
                break


class TCPServer:
    """TCP服务器"""
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.clients: List[socket.socket] = []
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.on_client_connected: Optional[Callable[[str, int], None]] = None
        self.on_client_disconnected: Optional[Callable[[str, int], None]] = None
        self.on_data_received: Optional[Callable[[str, int, bytes], None]] = None
        self.client_threads: dict = {}
    
    def start(self, bind_ip: str, port: int) -> bool:
        """启动服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((bind_ip, port))
            self.socket.listen(5)
            self.running = True
            
            # 启动监听线程
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            
            return True
        except Exception as e:
            print(f"启动服务器失败: {e}")
            return False
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # 关闭服务器socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_to_client(self, client_addr: Tuple[str, int], data: bytes) -> bool:
        """向指定客户端发送数据"""
        for client in self.clients:
            try:
                addr = client.getpeername()
                if addr == client_addr:
                    client.sendall(data)
                    return True
            except:
                pass
        return False
    
    def broadcast(self, data: bytes):
        """向所有客户端广播数据"""
        disconnected = []
        for client in self.clients:
            try:
                client.sendall(data)
            except:
                disconnected.append(client)
        
        # 移除断开的客户端
        for client in disconnected:
            if client in self.clients:
                self.clients.remove(client)
    
    def _listen_loop(self):
        """监听连接循环"""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                client, addr = self.socket.accept()
                
                if not self.running:
                    client.close()
                    break
                
                self.clients.append(client)
                
                if self.on_client_connected:
                    self.on_client_connected(addr[0], addr[1])
                
                # 为每个客户端启动接收线程
                client_thread = threading.Thread(
                    target=self._client_receive_loop,
                    args=(client, addr),
                    daemon=True
                )
                client_thread.start()
                self.client_threads[addr] = client_thread
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"监听错误: {e}")
                break
    
    def _client_receive_loop(self, client: socket.socket, addr: Tuple[str, int]):
        """客户端接收循环"""
        while self.running:
            try:
                client.settimeout(0.5)
                data = client.recv(4096)
                if data:
                    if self.on_data_received:
                        self.on_data_received(addr[0], addr[1], data)
                else:
                    # 客户端断开
                    break
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"客户端接收错误: {e}")
                break
        
        # 清理客户端
        if client in self.clients:
            self.clients.remove(client)
        try:
            client.close()
        except:
            pass
        
        if self.on_client_disconnected:
            self.on_client_disconnected(addr[0], addr[1])


class UDPClient:
    """UDP客户端"""
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.receive_thread: Optional[threading.Thread] = None
        self.on_data_received: Optional[Callable[[str, int, bytes], None]] = None
        self.running = False
        self.target_addr: Optional[Tuple[str, int]] = None
    
    def connect(self, target_ip: str, target_port: int, local_port: int = 0, broadcast: bool = False) -> bool:
        """创建UDP socket，可指定本地端口和广播模式"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 启用广播
            if broadcast:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # 绑定本地端口
            if local_port > 0:
                self.socket.bind(("0.0.0.0", local_port))
            
            self.target_addr = (target_ip, target_port)
            self.connected = True
            self.running = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"UDP创建失败: {e}")
            return False
    
    def disconnect(self):
        """关闭连接"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send(self, data: bytes, target_ip: str = None, target_port: int = None) -> bool:
        """发送数据"""
        if not self.socket:
            return False
        try:
            if target_ip and target_port:
                self.socket.sendto(data, (target_ip, target_port))
            elif self.target_addr:
                self.socket.sendto(data, self.target_addr)
            else:
                return False
            return True
        except Exception as e:
            print(f"UDP发送失败: {e}")
            return False
    
    def _receive_loop(self):
        """接收数据循环"""
        while self.running:
            try:
                self.socket.settimeout(0.5)
                data, addr = self.socket.recvfrom(4096)
                if data and self.on_data_received:
                    self.on_data_received(addr[0], addr[1], data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP接收错误: {e}")
                break


class UDPServer:
    """UDP服务器"""
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.on_data_received: Optional[Callable[[str, int, bytes], None]] = None
        self.clients: dict = {}  # 记录客户端地址和最后活跃时间
    
    def start(self, bind_ip: str, port: int) -> bool:
        """启动UDP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((bind_ip, port))
            self.running = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"启动UDP服务器失败: {e}")
            return False
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_to(self, ip: str, port: int, data: bytes) -> bool:
        """向指定地址发送数据"""
        if not self.socket:
            return False
        try:
            self.socket.sendto(data, (ip, port))
            return True
        except Exception as e:
            print(f"UDP发送失败: {e}")
            return False
    
    def broadcast(self, data: bytes, port: int):
        """广播数据到指定端口"""
        if not self.socket:
            return
        try:
            # 创建广播socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, ("<broadcast>", port))
            sock.close()
        except Exception as e:
            print(f"UDP广播失败: {e}")
    
    def get_clients(self) -> List[Tuple[str, int]]:
        """获取已连接的客户端列表"""
        # 清理超时的客户端（5分钟未活跃）
        current_time = time.time()
        timeout = 300  # 5分钟
        self.clients = {addr: t for addr, t in self.clients.items() if current_time - t < timeout}
        return list(self.clients.keys())
    
    def _receive_loop(self):
        """接收数据循环"""
        while self.running:
            try:
                self.socket.settimeout(0.5)
                data, addr = self.socket.recvfrom(4096)
                if data:
                    # 记录客户端
                    self.clients[addr] = time.time()
                    if self.on_data_received:
                        self.on_data_received(addr[0], addr[1], data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP服务器接收错误: {e}")
                break
