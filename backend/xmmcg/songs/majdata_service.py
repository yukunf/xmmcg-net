"""
Majdata.net API 集成服务
处理与 Majdata.net 的交互，包括登录和谱面上传
"""

import logging
import os
import tempfile
from typing import Optional, Dict
from django.core.files.uploadedfile import InMemoryUploadedFile
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MajdataService:
    """Majdata.net API服务类"""
    
    _session: Optional[requests.Session] = None
    _is_authenticated = False
    
    @classmethod
    def get_session(cls) -> Optional[requests.Session]:
        """
        获取已认证的 Majdata.net session
        如果session不存在或未认证，会自动尝试登录
        
        Returns:
            requests.Session 或 None（登录失败时）
        """
        # 如果session已存在且已认证，直接返回
        if cls._session and cls._is_authenticated:
            return cls._session
        
        # 尝试登录
        return cls._login()
    
    @classmethod
    def _login(cls) -> Optional[requests.Session]:
        """
        执行 Majdata.net 登录
        
        Returns:
            requests.Session 或 None（登录失败时）
        """
        try:
            # 创建新session
            cls._session = requests.Session()
            
            # 准备登录数据
            login_data = {
                "username": settings.MAJDATA_USERNAME,
                "password": settings.MAJDATA_PASSWD_HASHED
            }
            
            # 发送登录请求
            response = cls._session.post(
                settings.MAJDATA_LOGIN_URL,
                data=login_data,
                timeout=10
            )
            
            # 检查HTTP响应状态
            if response.status_code != 200:
                logger.error(f"Majdata.net 登录失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                cls._is_authenticated = False
                return None
            
            # 验证响应内容
            # Majdata.net API 成功时返回 {"code":114514,"message":"ok"}
            try:
                result = response.json()
                # 检查 message 是否为 "ok" 或 code 是否为 114514
                if result.get('message') != 'ok' and result.get('code') != 114514:
                    logger.error(f"Majdata.net 登录失败: {result.get('message', '未知错误')}")
                    cls._is_authenticated = False
                    return None
            except ValueError:
                # 如果响应不是JSON，只要状态码是200就认为成功
                logger.warning("Majdata.net 登录响应不是JSON格式，但状态码为200")
            
            # 登录成功
            cls._is_authenticated = True
            logger.info("✅ Majdata.net 登录成功")
            
            # 记录cookies（用于调试）
            if cls._session.cookies:
                logger.debug(f"获得的cookies: {dict(cls._session.cookies)}")
            
            return cls._session
            
        except requests.Timeout:
            logger.error("Majdata.net 登录超时")
            cls._is_authenticated = False
            return None
        except requests.RequestException as e:
            logger.error(f"Majdata.net 登录请求错误: {e}")
            cls._is_authenticated = False
            return None
        except Exception as e:
            logger.error(f"Majdata.net 登录未知错误: {e}")
            cls._is_authenticated = False
            return None
    
    @classmethod
    def upload_chart(cls, chart_data: dict) -> Optional[dict]:
        """
        上传谱面到 Majdata.net
        
        Args:
            chart_data: 谱面数据字典，包含以下字段：
                - maidata_content: maidata.txt文件内容（字符串）
                - audio_file: 音频文件对象（Django UploadedFile 或文件路径）
                - cover_file: 封面图片对象（可选）
                - video_file: 背景视频对象（可选）
                - is_part_chart: 是否为半成品谱面（可选，默认False）
                - folder_name: 用于日志的文件夹名称（可选）
                
        Returns:
            上传结果字典，包含谱面URL等信息；失败时返回None
        """
        session = cls.get_session()
        if not session:
            logger.error("无法获取Majdata.net session，上传失败")
            return None
        
        folder_name = chart_data.get('folder_name', 'Chart')
        
        try:
            # 处理 maidata.txt 内容
            maidata_content = chart_data.get('maidata_content', '')
            is_part_chart = chart_data.get('is_part_chart', False)
            
            logger.info(f"[{folder_name}] ===== Maidata 处理开始 =====")
            logger.info(f"[{folder_name}] is_part_chart: {is_part_chart}")
            logger.info(f"[{folder_name}] 修改前 maidata 长度: {len(maidata_content)} chars")
            
            # 检查修改前的标题
            title_before = [line for line in maidata_content.split('\n') if line.startswith('&title=')]
            if title_before:
                logger.info(f"[{folder_name}] 修改前标题: {title_before[0]}")
            
            # 根据是否为半成品谱面修改 maidata.txt 内容
            if is_part_chart:
                logger.info(f"[{folder_name}] 开始调用 _modify_maidata_for_part_chart...")
                maidata_modified = cls._modify_maidata_for_part_chart(maidata_content)
                logger.info(f"[{folder_name}] 修改后的内容长度: {len(maidata_modified)} chars")
                
                # 检查修改是否成功
                if maidata_modified != maidata_content:
                    logger.info(f"[{folder_name}] ✓ Maidata 内容已修改")
                    maidata_content = maidata_modified
                else:
                    logger.warning(f"[{folder_name}] ✗ Maidata 内容未改变（可能标题已有标记或未找到标题行）")
                
                # 检查修改后的标题（使用 in 而不是 startswith，处理可能的行尾符问题）
                title_after = [line.strip() for line in maidata_content.split('\n') if '&title=' in line]
                if title_after:
                    logger.info(f"[{folder_name}] 修改后标题: {title_after[0]}")
            else:
                logger.info(f"[{folder_name}] is_part_chart=False，跳过修改")
            
            logger.info(f"[{folder_name}] 最终 maidata 长度: {len(maidata_content)} chars")
            logger.info(f"[{folder_name}] ===== Maidata 处理结束 =====")
            
            # 准备上传文件（使用 formfiles 字段，按照固定顺序）
            form_files = []
            
            # 1. maidata.txt（必需）
            if maidata_content:
                form_files.append((
                    "formfiles",
                    ("maidata.txt", maidata_content.encode('utf-8'), "text/plain")
                ))
            else:
                logger.error(f"[{folder_name}] 缺少 maidata.txt 内容")
                return None
            
            # 2. 封面图片 bg.png/bg.jpg（必需）
            cover_file = chart_data.get('cover_file')
            if cover_file:
                cover_name, cover_data, cover_mime = cls._prepare_file(
                    cover_file, ['bg.png', 'bg.jpg'], 'image'
                )
                form_files.append(("formfiles", (cover_name, cover_data, cover_mime)))
            else:
                logger.error(f"[{folder_name}] 缺少封面图片")
                return None
            
            # 3. 音频文件 track.mp3（必需）
            audio_file = chart_data.get('audio_file')
            if audio_file:
                audio_name, audio_data, audio_mime = cls._prepare_file(
                    audio_file, ['track.mp3'], 'audio'
                )
                form_files.append(("formfiles", (audio_name, audio_data, audio_mime)))
            else:
                logger.error(f"[{folder_name}] 缺少音频文件")
                return None
            
            # 4. 背景视频 bg.mp4/pv.mp4（可选）
            video_file = chart_data.get('video_file')
            if video_file:
                try:
                    video_name, video_data, video_mime = cls._prepare_file(
                        video_file, ['bg.mp4', 'pv.mp4'], 'video'
                    )
                    form_files.append(("formfiles", (video_name, video_data, video_mime)))
                except Exception as e:
                    logger.warning(f"[{folder_name}] 视频文件处理失败（跳过）: {e}")
            
            # 发送上传请求
            logger.info(f"⬆️ 正在上传到 Majdata.net: {folder_name}")
            
            response = session.post(
                settings.MAJDATA_UPLOAD_URL,
                files=form_files,
                timeout=120  # 上传大文件可能需要较长时间
            )
            
            # 关闭所有文件句柄
            for _, (_, file_obj, _) in form_files:
                if hasattr(file_obj, 'close') and not isinstance(file_obj, bytes):
                    try:
                        file_obj.close()
                    except:
                        pass
            
            if response.status_code == 200:
                logger.info(f"✅ [{folder_name}] 上传成功: {response.text}")
                try:
                    return response.json()
                except ValueError:
                    # 如果响应不是JSON，返回文本
                    return {'success': True, 'message': response.text}
            else:
                logger.error(f"❌ [{folder_name}] 上传失败 (状态码 {response.status_code}): {response.text}")
                return None
                
        except requests.Timeout:
            logger.error(f"[{folder_name}] Majdata.net 上传超时")
            return None
        except requests.RequestException as e:
            logger.error(f"[{folder_name}] Majdata.net 上传请求错误: {e}")
            return None
        except Exception as e:
            logger.error(f"[{folder_name}] Majdata.net 上传未知错误: {e}")
            return None
    
    @staticmethod
    def _prepare_file(file_obj, preferred_names: list, file_type: str):
        """
        准备文件用于上传
        
        Args:
            file_obj: Django UploadedFile 对象或文件路径字符串
            preferred_names: 优先使用的文件名列表（如 ['bg.png', 'bg.jpg']）
            file_type: 文件类型（'image', 'audio', 'video'）
            
        Returns:
            (filename, file_data, mime_type) 元组
        """
        # 如果是文件路径字符串
        if isinstance(file_obj, str):
            if not os.path.exists(file_obj):
                raise FileNotFoundError(f"文件不存在: {file_obj}")
            
            # 确定文件名
            original_name = os.path.basename(file_obj)
            ext = os.path.splitext(original_name)[1]
            
            # 从优先列表中选择匹配的文件名
            filename = preferred_names[0]  # 默认使用第一个
            for name in preferred_names:
                if name.endswith(ext):
                    filename = name
                    break
            
            # 读取文件内容
            with open(file_obj, 'rb') as f:
                file_data = f.read()
        
        # 如果是 Django UploadedFile
        elif hasattr(file_obj, 'read'):
            # 确定文件扩展名
            original_name = getattr(file_obj, 'name', '')
            ext = os.path.splitext(original_name)[1] if original_name else ''
            
            # 从优先列表中选择匹配的文件名
            filename = preferred_names[0]  # 默认使用第一个
            for name in preferred_names:
                if name.endswith(ext):
                    filename = name
                    break
            
            # 读取文件内容
            file_obj.seek(0)  # 确保从头读取
            file_data = file_obj.read()
        
        else:
            raise ValueError(f"不支持的文件对象类型: {type(file_obj)}")
        
        # 确定 MIME 类型
        mime_type = MajdataService._get_mime_type(filename, file_type)
        
        return filename, file_data, mime_type
    
    @staticmethod
    def _get_mime_type(filename: str, file_type: str) -> str:
        """根据文件名和类型确定 MIME 类型"""
        if filename.endswith('.txt'):
            return 'text/plain'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            return 'image/jpeg'
        elif filename.endswith('.png'):
            return 'image/png'
        elif filename.endswith('.mp3'):
            return 'audio/mpeg'
        elif filename.endswith('.mp4'):
            return 'video/mp4'
        else:
            # 根据类型返回通用 MIME
            if file_type == 'image':
                return 'image/jpeg'
            elif file_type == 'audio':
                return 'audio/mpeg'
            elif file_type == 'video':
                return 'video/mp4'
            else:
                return 'application/octet-stream'
    
    @staticmethod
    def _modify_maidata_for_part_chart(maidata_content: str) -> str:
        """
        根据谱面是否为半成品修改 maidata.txt 内容
        在标题最前面添加 [谱面碎片] 标记
        
        例如：
        &title=14平米にスーベニア
        修改为：
        &title=[谱面碎片]14平米にスーベニア
        
        Args:
            maidata_content: 原始 maidata.txt 内容
            
        Returns:
            修改后的 maidata.txt 内容
        """
        if not maidata_content:
            return maidata_content
        
        # 处理不同的行尾符（Windows \r\n 和 Unix \n）
        # 先统一为 \n，处理后再恢复原始格式
        original_line_ending = '\r\n' if '\r\n' in maidata_content else '\n'
        
        # 移除 UTF-8 BOM（如果存在）
        if maidata_content.startswith('\ufeff'):
            maidata_content = maidata_content[1:]
        
        # 使用通用换行符分割
        lines = maidata_content.splitlines()
        modified_lines = []
        modified = False
        
        for line in lines:
            # 查找标题行（移除可能的空格）
            if line.strip().startswith('&title='):
                # 提取 &title= 之前的内容（可能有空格）
                prefix_match = line[:line.find('&title=')]
                title_part = line[line.find('&title='):]  # 获取 &title=... 部分
                
                # 提取标题内容
                title_content = title_part[7:]  # 去掉 '&title=' 部分
                
                # 检查是否已经有 [谱面碎片] 标记，避免重复添加
                if not title_content.startswith('[谱面碎片]'):
                    modified_lines.append(f'{prefix_match}&title=[谱面碎片]{title_content}')
                    modified = True
                else:
                    # 已有标记，不重复添加
                    modified_lines.append(line)
            else:
                # 其他行保持不变
                modified_lines.append(line)
        
        result = original_line_ending.join(modified_lines)
        
        # 如果内容被修改，长度会改变，这里记录一下以供调试
        if modified:
            logger.debug(f"_modify_maidata_for_part_chart: 成功修改 maidata，长度从 {len(maidata_content)} 改为 {len(result)}")
        else:
            logger.warning(f"_modify_maidata_for_part_chart: 未找到标题行或标题已有标记")
        
        return result
    
    @classmethod
    def reset_session(cls):
        """重置session，下次调用时会重新登录"""
        cls._session = None
        cls._is_authenticated = False
        logger.info("Majdata.net session 已重置")
