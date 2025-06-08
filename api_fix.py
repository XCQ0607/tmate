#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 用户配置（可修改）
USER_NAME = "xcq"  # 自定义session名称，默认为"tmate_session"，可使用任意字母数字组合
CUSTOM_ID = "tmate"  # 自定义ID，用于设置上传后的URL路径，默认为"tmate"，留空则由系统自动生成随机ID
PASSWORD = "tmate"  # 设置密码保护，用于限制他人访问上传的SSH信息，默认为"tmate"，留空则不设密码
# EXPIRES_IN = 86400  # 过期时间（秒），默认注释掉表示永久保存，取消注释后默认24小时后过期

# 系统配置（一般不需要修改）
TMATE_URL = "https://github.com/zhumengkang/agsb/raw/main/tmate"  # tmate可执行文件的下载地址
XBIN_API = "https://xbin.pages.dev/api/paste"  # xbin粘贴板API地址，用于上传SSH连接信息
USER_HOME = None  # 用户主目录路径，程序运行时会自动设置，存储临时文件和输出结果的位置
SSH_INFO_FILE = "ssh.txt"  # SSH信息保存的文件名，默认为"ssh.txt"，保存在用户主目录下

import os
import sys
import subprocess
import time
import threading
import signal
from pathlib import Path
import requests
from datetime import datetime

USER_HOME = Path.home()

class TmateManager:
    def __init__(self, session_name=USER_NAME):
        self.tmate_path = USER_HOME / "tmate"
        self.ssh_info_path = USER_HOME / SSH_INFO_FILE
        self.tmate_process = None
        self.session_info = {}
        self.session_name = session_name
        
    def download_tmate(self):
        """下载tmate文件到用户目录"""
        print("正在下载tmate...")
        try:
            response = requests.get(TMATE_URL, stream=True)
            response.raise_for_status()
            
            with open(self.tmate_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 给tmate添加执行权限
            os.chmod(self.tmate_path, 0o755)
            print(f"✓ tmate已下载到: {self.tmate_path}")
            print(f"✓ 已添加执行权限 (chmod 755)")
            
            # 验证文件是否可执行
            if os.access(self.tmate_path, os.X_OK):
                print("✓ 执行权限验证成功")
            else:
                print("✗ 执行权限验证失败")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ 下载tmate失败: {e}")
            return False
    
    def start_tmate(self):
        """启动tmate并获取会话信息"""
        print(f"正在启动tmate会话: {self.session_name}...")
        try:
            # 启动tmate进程 - 分离模式，后台运行
            session_args = [str(self.tmate_path), "-S", "/tmp/tmate.sock", "new-session", "-d"]
            
            # 如果提供了会话名称，添加到参数中
            if self.session_name:
                session_args.extend(["-s", self.session_name])
                
            self.tmate_process = subprocess.Popen(
                session_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # 创建新进程组，脱离父进程
            )
            
            # 等待tmate启动
            time.sleep(5)
            
            # 获取会话信息
            self.get_session_info()
            
            # 验证tmate是否在运行
            try:
                result = subprocess.run(
                    [str(self.tmate_path), "-S", "/tmp/tmate.sock", "list-sessions"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    print("✓ Tmate后台进程验证成功")
                    return True
                else:
                    print("✗ Tmate后台进程验证失败")
                    return False
            except Exception as e:
                print(f"✗ 验证tmate进程失败: {e}")
                return False
            
        except Exception as e:
            print(f"✗ 启动tmate失败: {e}")
            return False
    
    def get_session_info(self):
        """获取tmate会话信息"""
        try:
            # 获取只读web会话
            result = subprocess.run(
                [str(self.tmate_path), "-S", "/tmp/tmate.sock", "display", "-p", "#{tmate_web_ro}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.session_info['web_ro'] = result.stdout.strip()
            
            # 获取只读SSH会话
            result = subprocess.run(
                [str(self.tmate_path), "-S", "/tmp/tmate.sock", "display", "-p", "#{tmate_ssh_ro}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.session_info['ssh_ro'] = result.stdout.strip()
            
            # 获取可写web会话
            result = subprocess.run(
                [str(self.tmate_path), "-S", "/tmp/tmate.sock", "display", "-p", "#{tmate_web}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.session_info['web_rw'] = result.stdout.strip()
            
            # 获取可写SSH会话
            result = subprocess.run(
                [str(self.tmate_path), "-S", "/tmp/tmate.sock", "display", "-p", "#{tmate_ssh}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.session_info['ssh_rw'] = result.stdout.strip()
                
            # 显示会话信息
            if self.session_info:
                print("\n✓ Tmate会话已创建:")
                if 'web_ro' in self.session_info:
                    print(f"  只读Web会话: {self.session_info['web_ro']}")
                if 'ssh_ro' in self.session_info:
                    print(f"  只读SSH会话: {self.session_info['ssh_ro']}")
                if 'web_rw' in self.session_info:
                    print(f"  可写Web会话: {self.session_info['web_rw']}")
                if 'ssh_rw' in self.session_info:
                    print(f"  可写SSH会话: {self.session_info['ssh_rw']}")
            else:
                print("✗ 未能获取到会话信息")
                
        except Exception as e:
            print(f"✗ 获取会话信息失败: {e}")
    
    def save_ssh_info(self):
        """保存SSH信息到文件"""
        try:
            content = f"""Tmate SSH 会话信息
创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
会话名称: {self.session_name}

"""
            
            if 'web_ro' in self.session_info:
                content += f"web session read only: {self.session_info['web_ro']}\n"
            if 'ssh_ro' in self.session_info:
                content += f"ssh session read only: {self.session_info['ssh_ro']}\n"
            if 'web_rw' in self.session_info:
                content += f"web session: {self.session_info['web_rw']}\n"
            if 'ssh_rw' in self.session_info:
                content += f"ssh session: {self.session_info['ssh_rw']}\n"
            
            with open(self.ssh_info_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ SSH信息已保存到: {self.ssh_info_path}")
            return True
            
        except Exception as e:
            print(f"✗ 保存SSH信息失败: {e}")
            return False
    
    def upload_to_api(self):
        """上传SSH信息到xbin API"""
        try:
            if not self.ssh_info_path.exists():
                print("✗ SSH信息文件不存在")
                return False
            
            print("正在上传SSH信息到API...")
            
            # 读取文件内容
            with open(self.ssh_info_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 准备API请求数据
            data = {
                "content": content
            }
            
            # 添加过期时间参数(如果定义了的话)
            if 'EXPIRES_IN' in globals() and EXPIRES_IN is not None:
                data["expiresIn"] = EXPIRES_IN
            
            # 添加可选参数
            if CUSTOM_ID:
                data["customId"] = CUSTOM_ID
            if PASSWORD:
                data["password"] = PASSWORD
                
            # 发送请求到xbin API
            headers = {"Content-Type": "application/json"}
            response = requests.post(XBIN_API, json=data, headers=headers)
            
            # 处理响应
            if response.status_code == 200:
                # 成功创建新粘贴板
                return self._handle_success_response(response)
            elif response.status_code == 409 and CUSTOM_ID:
                # 自定义ID已存在，尝试更新现有粘贴板
                print(f"⚠ 自定义ID '{CUSTOM_ID}' 已被占用，尝试更新现有粘贴板...")
                
                # 构建更新API请求URL
                update_url = f"{XBIN_API}/{CUSTOM_ID}"
                
                # 准备更新请求数据
                update_data = {
                    "content": content
                }
                
                # 添加密码（如果有）
                if PASSWORD:
                    update_data["password"] = PASSWORD
                
                # 发送PUT请求更新内容
                update_response = requests.put(update_url, json=update_data, headers=headers)
                
                if update_response.status_code == 200:
                    print("✓ 成功更新现有粘贴板内容")
                    # 构造与POST请求成功相似的响应
                    mock_response = {
                        "success": True,
                        "id": CUSTOM_ID,
                        "url": f"https://xbin.pages.dev/{CUSTOM_ID}"
                    }
                    return self._handle_success_data(mock_response)
                else:
                    # 如果更新也失败，打印详细错误
                    print(f"✗ 更新现有粘贴板失败，状态码: {update_response.status_code}")
                    try:
                        error = update_response.json().get('error', '未知错误')
                        print(f"  错误信息: {error}")
                    except:
                        pass
                    return False
            else:
                print(f"✗ 上传失败，状态码: {response.status_code}")
                try:
                    error = response.json().get('error', '未知错误')
                    print(f"  错误信息: {error}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"✗ 上传到API失败: {e}")
            return False
    
    def _handle_success_response(self, response):
        """处理成功的API响应"""
        try:
            result = response.json()
            return self._handle_success_data(result)
        except Exception as e:
            print(f"✗ 解析API响应失败: {e}")
            return False
    
    def _handle_success_data(self, result):
        """处理成功的响应数据"""
        if result.get('success') or result.get('url'):
            url = result.get('url', '')
            paste_id = result.get('id', '')
            print(f"✓ SSH信息上传成功!")
            print(f"  访问URL: {url}")
            print(f"  粘贴板ID: {paste_id}")
            
            # 保存URL到文件
            url_file = USER_HOME / "ssh_upload_url.txt"
            with open(url_file, 'w') as f:
                f.write(f"URL: {url}\nID: {paste_id}\n")
                if PASSWORD:
                    f.write(f"密码: {PASSWORD}\n")
                if 'EXPIRES_IN' in globals() and EXPIRES_IN is not None:
                    expire_time = datetime.now().timestamp() + EXPIRES_IN
                    expire_str = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"过期时间: {expire_str}\n")
                    
            print(f"  URL信息已保存到: {url_file}")
            return True
        else:
            print(f"✗ API返回错误: {result}")
            return False
    
    def cleanup(self):
        """清理资源 - 不终止tmate会话"""
        # 注意：这里不清理tmate进程，让它在后台继续运行
        print("✓ Python脚本资源清理完成（tmate会话保持运行）")

def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到退出信号，正在清理...")
    if hasattr(signal_handler, 'manager'):
        signal_handler.manager.cleanup()
    sys.exit(0)

def main():
    manager = TmateManager(USER_NAME)
    
    # 只在主线程中注册信号处理器
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal_handler.manager = manager  # 保存引用用于信号处理
    except ValueError:
        # 如果不在主线程中（如Streamlit环境），跳过信号处理器注册
        print("⚠ 检测到非主线程环境，跳过信号处理器注册")
    
    try:
        print("=== Tmate SSH 会话管理器 ===")
        print(f"会话名称: {USER_NAME}")
        
        # 检查并安装依赖
        try:
            import requests
        except ImportError:
            print("检测到未安装requests库，正在安装...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            import requests
            print("✓ requests库安装成功")
        
        # 1. 下载tmate
        if not manager.download_tmate():
            return False
        
        # 2. 启动tmate
        if not manager.start_tmate():
            return False
        
        # 3. 保存SSH信息
        if not manager.save_ssh_info():
            return False
        
        # 4. 上传到API
        if not manager.upload_to_api():
            return False
        
        print("\n=== 所有操作完成 ===")
        print("✓ Tmate会话已在后台运行")
        print(f"✓ 会话信息已保存到: {manager.ssh_info_path}")
        print(f"✓ 上传URL已保存到: {USER_HOME}/ssh_upload_url.txt")
        print("\n🎉 脚本执行完成！")
        print("📍 Tmate会话将继续在后台运行，可以直接使用SSH连接")
        print("📍 如需停止tmate会话，请执行: pkill -f tmate")
        print("📍 查看tmate进程状态: ps aux | grep tmate")
        
        return True
            
    except Exception as e:
        print(f"✗ 程序执行出错: {e}")
        return False
    finally:
        manager.cleanup()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)