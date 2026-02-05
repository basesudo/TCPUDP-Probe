import re
from datetime import datetime
from typing import List


def bytes_to_hex(data: bytes, bytes_per_line: int = 16) -> str:
    """将字节转换为十六进制字符串"""
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{i:04X}  {hex_part:<{bytes_per_line * 3}}  {ascii_part}')
    return '\n'.join(lines)


def hex_to_bytes(hex_str: str) -> bytes:
    """将十六进制字符串转换为字节
    支持格式:
    - 标准格式: "56 39 39 47 30 30 30 38 0D"
    - 带h后缀: "56h 39h 39h 47h 30h 30h 30h 38h 0Dh"
    - 连续格式: "56393947303030380D"
    - 0x前缀: "0x56 0x39 0x39"
    """
    # 先尝试解析带h/H后缀的格式 (如 56h 39H)
    h_pattern = re.findall(r'([0-9a-fA-F]{1,2})[hH]', hex_str)
    if h_pattern:
        # 如果匹配到h后缀格式，使用这种解析
        hex_bytes = []
        for h in h_pattern:
            if len(h) == 1:
                h = '0' + h
            hex_bytes.append(h)
        return bytes.fromhex(''.join(hex_bytes))
    
    # 移除所有空白字符、0x前缀和非十六进制字符
    hex_str = re.sub(r'0x|0X', '', hex_str)  # 移除0x前缀
    hex_str = re.sub(r'[^0-9a-fA-F]', '', hex_str)  # 只保留十六进制字符
    
    if len(hex_str) % 2 != 0:
        hex_str = hex_str[:-1]  # 如果长度为奇数，移除最后一个字符
    
    if not hex_str:
        return b''
    
    return bytes.fromhex(hex_str)


def is_valid_hex(hex_str: str) -> bool:
    """检查字符串是否为有效的十六进制
    支持格式:
    - 标准格式: "56 39 39 47"
    - 带h后缀: "56h 39h 39h 47h"
    - 连续格式: "56393947"
    - 0x前缀: "0x56 0x39"
    """
    if not hex_str or not hex_str.strip():
        return False
    
    # 检查是否是带h/H后缀的格式
    h_pattern = re.findall(r'([0-9a-fA-F]{1,2})[hH]', hex_str)
    if h_pattern:
        return len(h_pattern) > 0
    
    # 移除所有空白字符、0x前缀
    hex_clean = re.sub(r'0x|0X', '', hex_str)
    hex_clean = re.sub(r'\s', '', hex_clean)
    
    if len(hex_clean) % 2 != 0:
        return False
    
    if not hex_clean:
        return False
    
    try:
        bytes.fromhex(hex_clean)
        return True
    except ValueError:
        return False


def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def bytes_to_binary(data: bytes, bytes_per_line: int = 8) -> str:
    """将字节转换为二进制字符串"""
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        # 二进制表示
        binary_part = ' '.join(f'{b:08b}' for b in chunk)
        # 十六进制表示（作为参考）
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f'{i:04X}  {binary_part}  |  {hex_part}')
    return '\n'.join(lines)


def format_received_data(data: bytes, show_hex: bool = False, show_binary: bool = False) -> str:
    """格式化接收到的数据"""
    timestamp = get_timestamp()
    if show_binary:
        return f"[{timestamp}] [二进制]\n{bytes_to_binary(data)}\n"
    elif show_hex:
        return f"[{timestamp}]\n{bytes_to_hex(data)}\n"
    else:
        try:
            text = data.decode('utf-8')
            return f"[{timestamp}] {text}\n"
        except UnicodeDecodeError:
            return f"[{timestamp}] [二进制数据]\n{bytes_to_hex(data)}\n"


def format_sent_data(data: bytes, show_hex: bool = False, show_binary: bool = False) -> str:
    """格式化发送的数据"""
    timestamp = get_timestamp()
    if show_binary:
        return f"[{timestamp}] [发送] [二进制]\n{bytes_to_binary(data)}\n"
    elif show_hex:
        return f"[{timestamp}] [发送]\n{bytes_to_hex(data)}\n"
    else:
        try:
            text = data.decode('utf-8')
            return f"[{timestamp}] [发送] {text}\n"
        except UnicodeDecodeError:
            return f"[{timestamp}] [发送] [二进制数据]\n{bytes_to_hex(data)}\n"


class HistoryItem:
    """历史记录项"""
    def __init__(self, data: str, remark: str = ""):
        self.data = data
        self.remark = remark
    
    def __str__(self):
        if self.remark:
            return f"[{self.remark}] {self.data[:30]}{'...' if len(self.data) > 30 else ''}"
        return self.data[:50] + ('...' if len(self.data) > 50 else '')
    
    def to_dict(self) -> dict:
        return {"data": self.data, "remark": self.remark}
    
    @classmethod
    def from_dict(cls, d: dict) -> "HistoryItem":
        return cls(d.get("data", ""), d.get("remark", ""))


class HistoryManager:
    """发送历史管理器"""
    def __init__(self, max_history: int = 50):
        self.history: List[HistoryItem] = []
        self.max_history = max_history
    
    def add(self, data: str, remark: str = ""):
        """添加历史记录"""
        if not data:
            return
        # 检查是否已存在相同数据
        for item in self.history:
            if item.data == data:
                # 更新备注
                if remark:
                    item.remark = remark
                # 移到最前面
                self.history.remove(item)
                self.history.insert(0, item)
                return
        
        # 添加新记录
        self.history.insert(0, HistoryItem(data, remark))
        if len(self.history) > self.max_history:
            self.history.pop()
    
    def get_all(self) -> List[HistoryItem]:
        """获取所有历史记录"""
        return self.history.copy()
    
    def get_display_names(self) -> List[str]:
        """获取显示名称列表"""
        return [str(item) for item in self.history]
    
    def get_item(self, index: int) -> Optional[HistoryItem]:
        """获取指定索引的历史记录"""
        if 0 <= index < len(self.history):
            return self.history[index]
        return None
    
    def delete_item(self, index: int) -> bool:
        """删除指定索引的历史记录"""
        if 0 <= index < len(self.history):
            self.history.pop(index)
            return True
        return False
    
    def clear(self):
        """清空历史记录"""
        self.history.clear()
    
    def to_list(self) -> List[dict]:
        """转换为列表（用于序列化）"""
        return [item.to_dict() for item in self.history]
    
    def from_list(self, data: List[dict]):
        """从列表加载"""
        self.history = []
        for item in data:
            if isinstance(item, dict) and "data" in item:
                self.history.append(HistoryItem.from_dict(item))
        # 限制数量
        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]
