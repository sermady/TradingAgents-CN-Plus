# -*- coding: utf-8 -*-
"""消息清理工具模块"""
from langchain_core.messages import AIMessage, RemoveMessage


def create_msg_delete():
    """创建消息删除函数"""

    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility

        注意：在并行执行模式下，多个分析师会同时调用此函数。
        为了避免重复删除导致的错误，我们使用一个标记机制确保只执行一次清理。
        """
        from langgraph.graph import END

        messages = state.get("messages", [])

        # 检查是否已经清理过（通过检查最后一个消息是否是占位符）
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            if hasattr(last_msg, "content") and last_msg.content == "__MSG_CLEARED__":
                # 已经清理过了，直接返回空更新
                return {"messages": []}

        # 收集需要删除的消息ID
        removal_operations = []
        seen_ids = set()

        for m in messages:
            if hasattr(m, "id") and m.id and m.id not in seen_ids:
                removal_operations.append(RemoveMessage(id=m.id))
                seen_ids.add(m.id)

        # 添加标记消息表示已清理（而不是 HumanMessage）
        # 使用 AIMessage 作为标记，避免干扰后续流程
        marker_message = AIMessage(content="__MSG_CLEARED__", id="msg_cleared_marker")

        return {"messages": removal_operations + [marker_message]}

    return delete_messages
