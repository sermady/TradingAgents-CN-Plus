# -*- coding: utf-8 -*-
"""
会话状态管理
处理Streamlit会话初始化、前端缓存恢复等功能
"""

import json
import time
from typing import Optional

import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')


def initialize_session_state():
    """初始化会话状态"""
    # 初始化认证相关状态
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None

    # 初始化分析相关状态
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    if 'last_analysis_time' not in st.session_state:
        st.session_state.last_analysis_time = None
    if 'current_analysis_id' not in st.session_state:
        st.session_state.current_analysis_id = None
    if 'form_config' not in st.session_state:
        st.session_state.form_config = None

    # 尝试从最新完成的分析中恢复结果
    _restore_analysis_results()

    # 使用cookie管理器恢复分析ID（优先级：session state > cookie > Redis/文件）
    _restore_persistent_analysis_id()

    # 恢复表单配置
    _restore_form_config()


def _restore_analysis_results():
    """尝试从最新的分析中恢复结果"""
    if st.session_state.analysis_results:
        return  # 已有结果，无需恢复

    try:
        from web.utils.async_progress_tracker import get_latest_analysis_id, get_progress_by_id
        from web.utils.analysis_runner import format_analysis_results

        latest_id = get_latest_analysis_id()
        if latest_id:
            progress_data = get_progress_by_id(latest_id)
            if (progress_data and
                progress_data.get('status') == 'completed' and
                'raw_results' in progress_data):

                # 恢复分析结果
                raw_results = progress_data['raw_results']
                formatted_results = format_analysis_results(raw_results)

                if formatted_results:
                    st.session_state.analysis_results = formatted_results
                    st.session_state.current_analysis_id = latest_id
                    # 检查分析状态
                    analysis_status = progress_data.get('status', 'completed')
                    st.session_state.analysis_running = (analysis_status == 'running')
                    # 恢复股票信息
                    if 'stock_symbol' in raw_results:
                        st.session_state.last_stock_symbol = raw_results.get('stock_symbol', '')
                    if 'market_type' in raw_results:
                        st.session_state.last_market_type = raw_results.get('market_type', '')
                    logger.info(f"📊 [结果恢复] 从分析 {latest_id} 恢复结果，状态: {analysis_status}")

    except Exception as e:
        logger.warning(f"⚠️ [结果恢复] 恢复失败: {e}")


def _restore_persistent_analysis_id():
    """从持久化存储恢复分析ID"""
    try:
        from web.utils.smart_session_manager import get_persistent_analysis_id

        persistent_analysis_id = get_persistent_analysis_id()
        if persistent_analysis_id:
            # 使用线程检测来检查分析状态
            from web.utils.thread_tracker import check_analysis_status
            actual_status = check_analysis_status(persistent_analysis_id)

            # 只在状态变化时记录日志，避免重复
            current_session_status = st.session_state.get('last_logged_status')
            if current_session_status != actual_status:
                logger.info(f"📊 [状态检查] 分析 {persistent_analysis_id} 实际状态: {actual_status}")
                st.session_state.last_logged_status = actual_status

            if actual_status == 'running':
                st.session_state.analysis_running = True
                st.session_state.current_analysis_id = persistent_analysis_id
            elif actual_status in ['completed', 'failed']:
                st.session_state.analysis_running = False
                st.session_state.current_analysis_id = persistent_analysis_id
            else:  # not_found
                logger.warning(f"📊 [状态检查] 分析 {persistent_analysis_id} 未找到，清理状态")
                st.session_state.analysis_running = False
                st.session_state.current_analysis_id = None
    except Exception as e:
        # 如果恢复失败，保持默认值
        logger.warning(f"⚠️ [状态恢复] 恢复分析状态失败: {e}")
        st.session_state.analysis_running = False
        st.session_state.current_analysis_id = None


def _restore_form_config():
    """恢复表单配置"""
    try:
        from web.utils.smart_session_manager import smart_session_manager
        session_data = smart_session_manager.load_analysis_state()

        if session_data and 'form_config' in session_data:
            st.session_state.form_config = session_data['form_config']
            # 只在没有分析运行时记录日志，避免重复
            if not st.session_state.get('analysis_running', False):
                logger.info("📊 [配置恢复] 表单配置已恢复")
    except Exception as e:
        logger.warning(f"⚠️ [配置恢复] 表单配置恢复失败: {e}")


def check_frontend_auth_cache():
    """检查前端缓存并尝试恢复登录状态"""
    from web.utils.auth_manager import auth_manager

    logger.info("🔍 开始检查前端缓存恢复")
    logger.info(f"📊 当前认证状态: {st.session_state.get('authenticated', False)}")
    logger.info(f"🔗 URL参数: {dict(st.query_params)}")

    # 如果已经认证，确保状态同步
    if st.session_state.get('authenticated', False):
        # 确保auth_manager也知道用户已认证
        if not auth_manager.is_authenticated() and st.session_state.get('user_info'):
            logger.info("🔄 同步认证状态到auth_manager")
            try:
                auth_manager.login_user(
                    st.session_state.user_info,
                    st.session_state.get('login_time', time.time())
                )
                logger.info("✅ 认证状态同步成功")
            except Exception as e:
                logger.warning(f"⚠️ 认证状态同步失败: {e}")
        else:
            logger.info("✅ 用户已认证，跳过缓存检查")
        return

    # 检查URL参数中是否有恢复信息
    try:
        import base64
        restore_data = st.query_params.get('restore_auth')

        if restore_data:
            logger.info("📥 发现URL中的恢复参数，开始恢复登录状态")
            # 解码认证数据
            auth_data = json.loads(base64.b64decode(restore_data).decode())

            # 兼容旧格式（直接是用户信息）和新格式（包含loginTime）
            if 'userInfo' in auth_data:
                user_info = auth_data['userInfo']
                # 使用当前时间作为新的登录时间，避免超时问题
                # 因为前端已经验证了lastActivity没有超时
                login_time = time.time()
            else:
                # 旧格式兼容
                user_info = auth_data
                login_time = time.time()

            logger.info(f"✅ 成功解码用户信息: {user_info.get('username', 'Unknown')}")
            logger.info(f"🕐 使用当前时间作为登录时间: {login_time}")

            # 恢复登录状态
            if auth_manager.restore_from_cache(user_info, login_time):
                # 清除URL参数
                del st.query_params['restore_auth']
                logger.info(f"✅ 从前端缓存成功恢复用户 {user_info['username']} 的登录状态")
                logger.info("🧹 已清除URL恢复参数")
                # 立即重新运行以应用恢复的状态
                logger.info("🔄 触发页面重新运行")
                st.rerun()
            else:
                logger.error("❌ 恢复登录状态失败")
                # 恢复失败，清除URL参数
                del st.query_params['restore_auth']
        else:
            # 如果没有URL参数，注入前端检查脚本
            logger.info("📝 没有URL恢复参数，注入前端检查脚本")
            _inject_frontend_cache_check()
    except Exception as e:
        logger.warning(f"⚠️ 处理前端缓存恢复失败: {e}")
        # 如果恢复失败，清除可能损坏的URL参数
        if 'restore_auth' in st.query_params:
            del st.query_params['restore_auth']


def _inject_frontend_cache_check():
    """注入前端缓存检查脚本"""
    logger.info("📝 准备注入前端缓存检查脚本")

    # 如果已经注入过，不重复注入
    if st.session_state.get('cache_script_injected', False):
        logger.info("⚠️ 前端脚本已注入，跳过重复注入")
        return

    # 标记已注入
    st.session_state.cache_script_injected = True
    logger.info("✅ 标记前端脚本已注入")

    cache_check_js = """
    <script>
    // 前端缓存检查和恢复
    function checkAndRestoreAuth() {
        console.log('🚀 开始执行前端缓存检查');
        console.log('📍 当前URL:', window.location.href);

        try {
            // 检查URL中是否已经有restore_auth参数
            const currentUrl = new URL(window.location.href);
            if (currentUrl.searchParams.has('restore_auth')) {
                console.log('🔄 URL中已有restore_auth参数，跳过前端检查');
                return;
            }

            const authData = localStorage.getItem('tradingagents_auth');
            console.log('🔍 检查localStorage中的认证数据:', authData ? '存在' : '不存在');

            if (!authData) {
                console.log('🔍 前端缓存中没有登录状态');
                return;
            }

            const data = JSON.parse(authData);
            console.log('📊 解析的认证数据:', data);

            // 验证数据结构
            if (!data.userInfo || !data.userInfo.username) {
                console.log('❌ 认证数据结构无效，清除缓存');
                localStorage.removeItem('tradingagents_auth');
                return;
            }

            const now = Date.now();
            const timeout = 10 * 60 * 1000; // 10分钟
            const timeSinceLastActivity = now - data.lastActivity;

            console.log('⏰ 时间检查:', {
                now: new Date(now).toLocaleString(),
                lastActivity: new Date(data.lastActivity).toLocaleString(),
                timeSinceLastActivity: Math.round(timeSinceLastActivity / 1000) + '秒',
                timeout: Math.round(timeout / 1000) + '秒'
            });

            // 检查是否超时
            if (timeSinceLastActivity > timeout) {
                localStorage.removeItem('tradingagents_auth');
                console.log('⏰ 登录状态已过期，自动清除');
                return;
            }

            // 更新最后活动时间
            data.lastActivity = now;
            localStorage.setItem('tradingagents_auth', JSON.stringify(data));
            console.log('🔄 更新最后活动时间');

            console.log('✅ 从前端缓存恢复登录状态:', data.userInfo.username);

            // 保留现有的URL参数，只添加restore_auth参数
            // 传递完整的认证数据，包括原始登录时间
            const restoreData = {
                userInfo: data.userInfo,
                loginTime: data.loginTime
            };
            const restoreParam = btoa(JSON.stringify(restoreData));
            console.log('📦 生成恢复参数:', restoreParam);

            // 保留所有现有参数
            const existingParams = new URLSearchParams(currentUrl.search);
            existingParams.set('restore_auth', restoreParam);

            // 构建新URL，保留现有参数
            const newUrl = currentUrl.origin + currentUrl.pathname + '?' + existingParams.toString();
            console.log('🔗 准备跳转到:', newUrl);
            console.log('📋 保留的URL参数:', Object.fromEntries(existingParams));

            window.location.href = newUrl;

        } catch (e) {
            console.error('❌ 前端缓存恢复失败:', e);
            localStorage.removeItem('tradingagents_auth');
        }
    }

    // 延迟执行，确保页面完全加载
    console.log('⏱️ 设置1000ms延迟执行前端缓存检查');
    setTimeout(checkAndRestoreAuth, 1000);
    </script>
    """

    st.components.v1.html(cache_check_js, height=0)
