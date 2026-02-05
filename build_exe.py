"""
TCP调试工具 - 打包脚本
使用PyInstaller打包成exe可执行文件
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


def build_gui():
    """打包桌面版"""
    print("\n" + "="*50)
    print("正在打包桌面版 (GUI)...")
    print("="*50 + "\n")
    
    cmd = [
        'pyinstaller',
        '--name=TCP调试工具-桌面版',
        '--onefile',
        '--windowed',
        '--icon=NONE',
        '--add-data', 'config.json;.',
        '--hidden-import', 'psutil',
        '--hidden-import', 'socket',
        '--hidden-import', 'threading',
        '--hidden-import', 'tkinter',
        'main.py'
    ]
    
    subprocess.run(cmd, check=True)
    print("\n桌面版打包完成！")


def build_web():
    """打包Web版"""
    print("\n" + "="*50)
    print("正在打包Web版 (Server)...")
    print("="*50 + "\n")
    
    cmd = [
        'pyinstaller',
        '--name=TCP调试工具-Web版',
        '--onefile',
        '--console',
        '--icon=NONE',
        '--add-data', 'templates;templates',
        '--add-data', 'config.json;.',
        '--hidden-import', 'psutil',
        '--hidden-import', 'flask',
        '--hidden-import', 'flask_socketio',
        '--hidden-import', 'engineio',
        '--hidden-import', 'socketio',
        'web_server.py'
    ]
    
    subprocess.run(cmd, check=True)
    print("\nWeb版打包完成！")


def copy_to_dist():
    """复制额外文件到dist目录"""
    print("\n" + "="*50)
    print("复制文档文件...")
    print("="*50 + "\n")
    
    # 创建docs目录
    if not os.path.exists('dist/docs'):
        os.makedirs('dist/docs')
    
    # 复制文档
    if os.path.exists('docs'):
        for file in os.listdir('docs'):
            src = os.path.join('docs', file)
            dst = os.path.join('dist/docs', file)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"复制: {src} -> {dst}")
    
    print("\n文件复制完成！")


def main():
    """主函数"""
    print("TCP调试工具 - EXE打包脚本")
    print("="*50)
    
    # 清理旧构建
    clean_build()
    
    try:
        # 打包桌面版
        build_gui()
        
        # 打包Web版
        build_web()
        
        # 复制文档
        copy_to_dist()
        
        print("\n" + "="*50)
        print("所有打包任务完成！")
        print("="*50)
        print("\n输出文件位置:")
        print("  - dist/TCP调试工具-桌面版.exe")
        print("  - dist/TCP调试工具-Web版.exe")
        print("  - dist/docs/ (文档目录)")
        print("\n可以直接将dist目录复制到其他电脑使用！")
        
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
