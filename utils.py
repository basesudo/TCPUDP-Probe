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
    """将十六进制字符串转换为字节"""
    # 移除所有空白字符和非十六进制字符
    hex_str = re.sub(r'[^0-9a-fA-F]', '', hex_str)
    if len(hex_str) % 2 != 0:
        hex_str = hex_str[:-1]  # 如果长度为奇数，移除最后一个字符
    return bytes.fromhex(hex_str)


def is_valid_hex(hex_str: str) -> bool:
    """检查字符串是否为有效的十六进制"""
    hex_str = re.sub(r'\s', '', hex_str)
    if len(hex_str) % 2 != 0:
        return False
    try:
        bytes.fromhex(hex_str)
        return True
    except ValueError:
        return False


def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def format_received_data(data: bytes, show_hex: bool = False) -> str:
    """格式化接收到的数据"""
    timestamp = get_timestamp()
    if show_hex:
        return f"[{timestamp}]\n{bytes_to_hex(data)}\n"
    else:
        try:
            text = data.decode('utf-8')
            return f"[{timestamp}] {text}\n"
        except UnicodeDecodeError:
            return f"[{timestamp}] [二进制数据]\n{bytes_to_hex(data)}\n"


def format_sent_data(data: bytes, show_hex: bool = False) -> str:
    """格式化发送的数据"""
    timestamp = get_timestamp()
    if show_hex:
        return f"[{timestamp}] [发送]\n{bytes_to_hex(data)}\n"
    else:
        try:
            text = data.decode('utf-8')
            return f"[{timestamp}] [发送] {text}\n"
        except UnicodeDecodeError:
            return f"[{timestamp}] [发送] [二进制数据]\n{bytes_to_hex(data)}\n"


class HistoryManager:
    """发送历史管理器"""
    def __init__(self, max_history: int = 50):
        self.history: List[str] = []
        self.max_history = max_history
    
    def add(self, data: str):
        """添加历史记录"""
        if data and data not in self.history:
            self.history.insert(0, data)
            if len(self.history) > self.max_history:
                self.history.pop()
    
    def get_all(self) -> List[str]:
        """获取所有历史记录"""
        return self.history.copy()
    
    def clear(self):
        """清空历史记录"""
        self.history.clear()
