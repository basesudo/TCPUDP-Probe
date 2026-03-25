"""
TCP调试工具 - 调试版本打包脚本（带控制台输出）
"""

import os
import sys
import shutil
import subprocess


def clean_build():
    """清理之前的构建文件"""
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name} 目录...")
            shutil.rmtree(dir_name)
    
    # 清理spec文件
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            print(f"删除 {file}...")
            os.remove(file)


def build_gui_debug():
    """打包桌面版（调试版本，带控制台）"""
    print("\n" + "="*50)
    print("正在打包桌面版调试版本 (带控制台输出)...")
    print("="*50 + "\n")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=TCP调试工具-桌面版-调试',
        '--onefile',
        '--console',  # 带控制台，可以看到print输出
        '--icon=NONE',
        '--add-data', 'config.json;.',
        '--hidden-import', 'psutil',
        '--hidden-import', 'socket',
        '--hidden-import', 'threading',
        '--hidden-import', 'tkinter',
        'main.py'
    ]
    
    subprocess.run(cmd, check=True)
    print("\n桌面版调试版本打包完成！")


def main():
    """主函数"""
    print("TCP调试工具 - 调试版本打包脚本")
    print("="*50)
    
    # 清理旧构建
    clean_build()
    
    try:
        # 打包桌面版调试版本
        build_gui_debug()
        
        print("\n" + "="*50)
        print("打包任务完成！")
        print("="*50)
        print("\n输出文件位置:")
        print("  - dist/TCP调试工具-桌面版-调试.exe")
        print("\n运行时会显示控制台窗口，可以看到调试输出信息。")
        
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
