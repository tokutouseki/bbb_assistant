#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
崩坏3专属AI陪伴助手 - 交互式聊天客户端

使用方法:
1. 确保后端服务已启动: python -m src.main
2. 运行此脚本: python chat_client.py
3. 输入问题与AI对话
4. 输入 'exit' 或 'quit' 退出
5. 输入 'clear' 清空对话历史
6. 输入 'history' 查看对话历史
"""

import requests
import json
import sys
from typing import List, Dict, Any


class ChatClient:
    """聊天客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.chat_url = f"{base_url}/api/chat/completion"
        self.messages: List[Dict[str, str]] = []
        self.session = requests.Session()
    
    def send_message(self, user_message: str, game_scene: str = "main_menu") -> Dict[str, Any]:
        """发送消息给Agent"""
        # 添加用户消息到历史
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        payload = {
            "messages": self.messages,
            "game_scene": game_scene,
            "use_rag": True,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = self.session.post(
                self.chat_url,
                json=payload,
                headers=headers,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 添加助手响应到历史
                self.messages.append({
                    "role": "assistant",
                    "content": result["message"]["content"]
                })
                
                return result
            else:
                return {
                    "error": f"请求失败，状态码: {response.status_code}",
                    "message": {"content": f"请求失败: {response.text}"}
                }
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "message": {"content": f"网络请求失败: {e}"}
            }
    
    def clear_history(self):
        """清空对话历史"""
        self.messages = []
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.messages
    
    def format_tool_steps(self, tool_steps: List[Dict[str, Any]]) -> str:
        """格式化工具使用步骤"""
        if not tool_steps:
            return ""
        
        lines = ["\n📋 工具使用过程:"]
        for i, step in enumerate(tool_steps, 1):
            lines.append(f"\n  步骤{i}:")
            lines.append(f"    🔧 工具: {step.get('tool', '未知')}")
            if step.get('thought'):
                thought = step['thought'][:150] + "..." if len(step['thought']) > 150 else step['thought']
                lines.append(f"    💭 思考: {thought}")
            if step.get('output'):
                output = str(step['output'])[:200] + "..." if len(str(step['output'])) > 200 else step['output']
                lines.append(f"    📝 输出: {output}")
        
        return "\n".join(lines)
    
    def chat(self):
        """交互式聊天"""
        print("=" * 60)
        print("🎮 崩坏3专属AI陪伴助手 - 聊天客户端")
        print("=" * 60)
        print("提示: 输入 'exit' 或 'quit' 退出")
        print("      输入 'clear' 清空对话历史")
        print("      输入 'history' 查看对话历史")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n你: ")
                
                if user_input.lower() in ['exit', 'quit']:
                    print("👋 再见！")
                    break
                
                if user_input.lower() == 'clear':
                    self.clear_history()
                    print("✅ 对话历史已清空")
                    continue
                
                if user_input.lower() == 'history':
                    history = self.get_history()
                    if not history:
                        print("📭 对话历史为空")
                    else:
                        print("\n📜 对话历史:")
                        for msg in history:
                            role = "你" if msg['role'] == 'user' else "AI"
                            print(f"\n{role}: {msg['content'][:50]}...")
                    continue
                
                if not user_input.strip():
                    print("⚠️ 请输入有效内容")
                    continue
                
                print("\n🤖 AI正在思考...")
                
                result = self.send_message(user_input)
                
                if "error" in result:
                    print(f"❌ 错误: {result['error']}")
                    continue
                
                print(f"\n🤖 AI: {result['message']['content']}")
                
                processing_time = result.get('processing_time', 0)
                if processing_time > 0:
                    print(f"\n⏱️ 处理时间: {processing_time:.2f}秒")
                
                tool_steps = result.get('tool_steps', [])
                if tool_steps:
                    print(self.format_tool_steps(tool_steps))
                
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")


def main():
    """主函数"""
    client = ChatClient()
    
    try:
        # 测试连接
        response = requests.get(f"{client.base_url}/health", timeout=10)
        if response.status_code != 200:
            print("❌ 无法连接到后端服务")
            print("请确保服务已启动: python -m src.main")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ 无法连接到后端服务")
        print("请确保服务已启动: python -m src.main")
        sys.exit(1)
    
    client.chat()


if __name__ == "__main__":
    main()
