# =====================================================================
#  Blender 多渲染器终极交互式配置脚本 (增强版)
#  新增噪波阈值、降噪采样设置及FFmpeg高级配置
# =====================================================================
import bpy
import os
import sys
import traceback
import gc

# =====================================================================
# 预设配置
# =====================================================================
DEFAULT_CONFIG = {
    "render_engine": "CYCLES",  # CYCLES 或 BLENDER_EEVEE
    "output_dir": "/workspace/out",
    "filename_prefix": "frame",
    "file_format": "PNG",
    "color_mode": "RGB",  # 已调整为新版兼容值
    "start_frame": 1,
    "end_frame": 10,
    "resolution_x": 1920,
    "resolution_y": 1080,
    "resolution_percent": 100,
    "samples": 64,
    "tile_size": 256,  # Cycles 分块大小
    "eevee_samples": 64,  # Eevee 采样
    "denoiser": "OPENIMAGEDENOISE",
    "device_type": "CUDA",
    "max_bounces": 6,
    "eevee_ambient_occlusion": True,  # Eevee 环境光遮蔽
    "eevee_bloom": True,  # Eevee 辉光效果
    "eevee_ssr": True,  # Eevee 屏幕空间反射
    "eevee_volumetric": True,  # Eevee 体积效果
    "noise_threshold": 0.01,  # 新增：噪波阈值
    "denoising_samples": 0,  # 新增：降噪采样
    "ffmpeg_format": "MPEG4",  # 新增：FFmpeg容器格式
    "ffmpeg_codec": "H264",  # 新增：FFmpeg编码格式
    "ffmpeg_quality": "MEDIUM"  # 新增：FFmpeg质量
}

# =====================================================================
# 交互函数
# =====================================================================

def print_header(title):
    """打印标题"""
    print("=" * 80)
    print(f"🚀🚀 {title}")
    print("=" * 80)

def get_user_input(prompt, default=None, value_type=str):
    """获取用户输入"""
    default_str = f" (默认: {default})" if default is not None else ""
    full_prompt = f"{prompt}{default_str}: "
    
    while True:
        try:
            user_input = input(full_prompt).strip()
            if not user_input and default is not None:
                return default
            return value_type(user_input)
        except ValueError:
            print(f"⚠️ 无效输入，请输入{value_type.__name__}类型值")

def select_from_options(prompt, options, default_index=1):
    """从选项中选择"""
    print("=" * 80)
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print("=" * 80)
    
    while True:
        choice = get_user_input("请选择", default=default_index, value_type=int)
        if 1 <= choice <= len(options):
            return options[choice - 1]
        print(f"⚠️ 无效选择，请输入1-{len(options)}之间的数字")

def get_device_info():
    """获取设备信息"""
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.get_devices()
    
    devices = []
    for device in prefs.devices:
        # 使用兼容性检查
        supported = True
        if hasattr(device, 'is_compatible'):
            supported = device.is_compatible
        
        devices.append({
            "name": device.name,
            "type": device.type,
            "supported": supported
        })
    
    return devices

def configure_render_mode():
    """配置渲染模式和基本参数"""
    print_header("渲染配置")
    
    # 选择配置模式
    mode = select_from_options("请选择配置模式:", 
                              ["使用Blend文件内置配置", 
                               "使用脚本内置配置", 
                               "自定义参数"])
    
    if "Blend" in mode:
        return "blend"
    elif "内置" in mode:
        return "default"
    else:
        return "custom"

def get_blend_config():
    """获取Blend文件配置"""
    scene = bpy.context.scene
    config = DEFAULT_CONFIG.copy()
    
    # 从场景获取配置
    config["render_engine"] = scene.render.engine
    config["output_dir"] = os.path.dirname(scene.render.filepath) or DEFAULT_CONFIG["output_dir"]
    config["filename_prefix"] = os.path.basename(scene.render.filepath).split("_")[0] or DEFAULT_CONFIG["filename_prefix"]
    config["file_format"] = scene.render.image_settings.file_format
    config["resolution_x"] = scene.render.resolution_x
    config["resolution_y"] = scene.render.resolution_y
    config["resolution_percent"] = scene.render.resolution_percentage
    
    # 渲染引擎特定配置
    if scene.render.engine == 'CYCLES':
        config["samples"] = scene.cycles.samples
        config["tile_size"] = scene.cycles.tile_size
        config["max_bounces"] = scene.cycles.max_bounces
        
        # 新增：噪波阈值和降噪采样
        config["noise_threshold"] = scene.cycles.noise_threshold
        config["denoising_samples"] = scene.cycles.denoising_samples
    
    elif scene.render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
        # 修复：使用新版API路径
        eevee_settings = scene.eevee
        
        config["eevee_samples"] = eevee_settings.taa_render_samples
        config["eevee_ambient_occlusion"] = eevee_settings.use_gtao
        config["eevee_bloom"] = eevee_settings.use_bloom
        config["eevee_ssr"] = eevee_settings.use_ssr
        config["eevee_volumetric"] = eevee_settings.use_volumetric
    
    # 新增：FFmpeg设置
    if config["file_format"] == "FFMPEG":
        config["ffmpeg_format"] = scene.render.ffmpeg.format
        config["ffmpeg_codec"] = scene.render.ffmpeg.codec
        config["ffmpeg_quality"] = scene.render.ffmpeg.quality
    
    print("✅ 使用Blend文件内置配置")
    return config

def get_default_config():
    """获取默认配置"""
    print("✅ 使用脚本内置配置")
    return DEFAULT_CONFIG.copy()

def get_custom_config():
    """获取自定义配置"""
    config = DEFAULT_CONFIG.copy()
    
    print_header("自定义配置")
    
    # 1. 基本参数
    config["output_dir"] = get_user_input("输出目录", DEFAULT_CONFIG["output_dir"])
    config["filename_prefix"] = get_user_input("文件名前缀", DEFAULT_CONFIG["filename_prefix"])
    
    # 2. 渲染引擎
    engines = ["Cycles (光线追踪)", "Eevee (实时渲染)", "Eevee Next (最新实时渲染)"]
    engine_choice = select_from_options("请选择渲染引擎:", engines)
    
    if "Cycles" in engine_choice:
        config["render_engine"] = "CYCLES"
    elif "Eevee Next" in engine_choice:
        config["render_engine"] = "BLENDER_EEVEE_NEXT"
    else:
        config["render_engine"] = "BLENDER_EEVEE"
    
    # 3. 输出格式
    file_formats = ["PNG", "JPEG", "EXR", "TIFF", "FFMPEG"]
    config["file_format"] = select_from_options("请选择文件格式:", file_formats)
    
    # 4. 帧范围
    config["start_frame"] = get_user_input("起始帧", DEFAULT_CONFIG["start_frame"], int)
    config["end_frame"] = get_user_input("结束帧", DEFAULT_CONFIG["end_frame"], int)
    
    # 5. 分辨率
    config["resolution_x"] = get_user_input("宽度", DEFAULT_CONFIG["resolution_x"], int)
    config["resolution_y"] = get_user_input("高度", DEFAULT_CONFIG["resolution_y"], int)
    config["resolution_percent"] = get_user_input("分辨率百分比", DEFAULT_CONFIG["resolution_percent"], int)
    
    # 6. 颜色模式（新增兼容性处理）
    color_modes = ["BW", "RGB", "RGBA"]  # 显式列出所有支持选项
    config["color_mode"] = select_from_options("请选择颜色模式:", color_modes)
    
    # 7. 渲染引擎特定配置
    if config["render_engine"] == "CYCLES":
        print_header("Cycles 配置")
        config["samples"] = get_user_input("采样数", DEFAULT_CONFIG["samples"], int)
        config["tile_size"] = get_user_input("分块大小 (tile size)", DEFAULT_CONFIG["tile_size"], int)
        config["max_bounces"] = get_user_input("最大光线反弹", DEFAULT_CONFIG["max_bounces"], int)
        
        # 新增：噪波阈值
        config["noise_threshold"] = get_user_input("噪波阈值 (0.01-0.1)", DEFAULT_CONFIG["noise_threshold"], float)
        
        # 新增：降噪采样
        config["denoising_samples"] = get_user_input("降噪采样 (0=使用所有采样)", DEFAULT_CONFIG["denoising_samples"], int)
        
        # 降噪器
        denoisers = ["OpenImageDenoise", "OptiX", "禁用降噪"]
        denoiser_choice = select_from_options("请选择降噪器:", denoisers)
        if "Open" in denoiser_choice:
            config["denoiser"] = "OPENIMAGEDENOISE"
        elif "Opti" in denoiser_choice:
            config["denoiser"] = "OPTIX"
        else:
            config["denoiser"] = "NONE"
        
        # 设备
        devices = get_device_info()
        device_options = [f"{d['name']} ({d['type']})" for d in devices]
        device_choice = select_from_options("请选择设备:", device_options)
        
        for device in devices:
            if f"{device['name']} ({device['type']})" == device_choice:
                config["device_type"] = device["type"]
                break
    
    else:  # Eevee 或 Eevee Next 配置
        print_header(f"{config['render_engine'].replace('BLENDER_', '').replace('_', ' ')} 配置")
        config["eevee_samples"] = get_user_input("采样数", DEFAULT_CONFIG["eevee_samples"], int)
        
        # Eevee 效果
        config["eevee_ambient_occlusion"] = select_from_options("启用环境光遮蔽?", ["是", "否"]) == "是"
        config["eevee_bloom"] = select_from_options("启用辉光效果?", ["是", "否"]) == "是"
        config["eevee_ssr"] = select_from_options("启用屏幕空间反射?", ["是", "否"]) == "是"
        config["eevee_volumetric"] = select_from_options("启用体积效果?", ["是", "否"]) == "是"
    
    # 新增：FFmpeg高级设置
    if config["file_format"] == "FFMPEG":
        print_header("FFmpeg 高级设置")
        
        # 容器格式
        formats = ["MPEG4", "AVI", "QUICKTIME", "DV", "H264", "XVID", "FLV", "MKV", "OGG", "WEBM"]
        config["ffmpeg_format"] = select_from_options("请选择容器格式:", formats)
        
        # 视频编码
        codecs = ["H264", "MPEG4", "MPEG2", "AV1", "VP9", "THEORA", "DNXHD", "PRORES", "FLASH", "FFV1"]
        config["ffmpeg_codec"] = select_from_options("请选择视频编码:", codecs)
        
        # 质量设置
        qualities = ["LOSSLESS", "PERC_LOSSLESS", "HIGH", "MEDIUM", "LOW"]
        config["ffmpeg_quality"] = select_from_options("请选择质量设置:", qualities)
    
    return config

# =====================================================================
# 修复设备类型枚举值问题
# =====================================================================

def apply_config(config):
    """应用渲染配置"""
    scene = bpy.context.scene
    prefs = bpy.context.preferences
    
    # 设置渲染引擎
    scene.render.engine = config["render_engine"]
    print(f"✅ 渲染引擎: {config['render_engine']}")
    
    # 通用设置
    scene.render.filepath = os.path.join(
        config["output_dir"], 
        f"{config['filename_prefix']}_####"
    )
    scene.render.image_settings.file_format = config["file_format"]
    
    # 新增颜色模式处理
    if config["file_format"] in ["PNG", "TIFF", "EXR"]:
        scene.render.image_settings.color_mode = config["color_mode"]
    else:
        scene.render.image_settings.color_mode = "RGB"
    
    scene.frame_start = config["start_frame"]
    scene.frame_end = config["end_frame"]
    scene.render.resolution_x = config["resolution_x"]
    scene.render.resolution_y = config["resolution_y"]
    scene.render.resolution_percentage = config["resolution_percent"]
    
    # 渲染引擎特定设置
    if config["render_engine"] == "CYCLES":
        # 设备设置
        if hasattr(prefs, "addons") and "cycles" in prefs.addons:
            cycles_prefs = prefs.addons["cycles"].preferences
            
            # 修复：处理设备类型映射
            device_type = config["device_type"]
            if device_type == "CPU":
                # 在 Blender 4.4.3 中，CPU 设备使用 "NONE" 作为设备类型
                cycles_prefs.compute_device_type = "NONE"
            else:
                cycles_prefs.compute_device_type = device_type
            
            # 刷新设备列表
            cycles_prefs.get_devices()
            
            # 启用选择的设备
            for device in cycles_prefs.devices:
                # 修复：CPU 设备特殊处理
                if device_type == "CPU":
                    device.use = device.type == "CPU"
                else:
                    device.use = device.type == device_type
        
        # Cycles 参数
        scene.cycles.samples = config["samples"]
        scene.cycles.tile_size = config["tile_size"]
        scene.cycles.max_bounces = config["max_bounces"]
        
        # 新增：噪波阈值
        scene.cycles.noise_threshold = config["noise_threshold"]
        
        # 新增：降噪采样
        scene.cycles.denoising_samples = config["denoising_samples"]
        
        # 降噪
        if config["denoiser"] != "NONE":
            scene.cycles.use_denoising = True
            scene.cycles.denoiser = config["denoiser"]
        else:
            scene.cycles.use_denoising = False
    
    else:  # Eevee 或 Eevee Next 设置
        # 修复：使用新版API路径
        eevee_settings = scene.eevee
        
        eevee_settings.taa_render_samples = config["eevee_samples"]
        eevee_settings.use_gtao = config["eevee_ambient_occlusion"]
        eevee_settings.use_bloom = config["eevee_bloom"]
        eevee_settings.use_ssr = config["eevee_ssr"]
        eevee_settings.use_volumetric = config["eevee_volumetric"]
    
       
    # 新增：FFmpeg设置
    if config["file_format"] == "FFMPEG":
        scene.render.ffmpeg.format = config["ffmpeg_format"]
        scene.render.ffmpeg.codec = config["ffmpeg_codec"]
        
        # 修复：处理质量设置
        # 在 Blender 4.4.3 中，quality 属性被移除了
        # 使用 constant_rate_factor 替代
        quality_map = {
            "LOSSLESS": 0,          # 无损
            "PERC_LOSSLESS": 18,    # 接近无损
            "HIGH": 20,             # 高质量
            "MEDIUM": 23,           # 中等质量
            "LOW": 28               # 低质量
        }
        
        # 设置 CRF 值
        scene.render.ffmpeg.constant_rate_factor = quality_map.get(
            config["ffmpeg_quality"], 23  # 默认中等质量
        )
    
    # 创建输出目录
    os.makedirs(config["output_dir"], exist_ok=True)
    
    return scene

# 在 print_config_summary 函数中修复字符串闭合问题
def print_config_summary(config):
    """打印配置摘要"""
    print("=" * 80)
    print("✅ 最终配置摘要:")
    print(f"  渲染引擎: {config['render_engine']}")
    print(f"  输出目录: {config['output_dir']}")
    print(f"  文件名前缀: {config['filename_prefix']}")
    print(f"  文件格式: {config['file_format']}")
    print(f"  帧范围: {config['start_frame']}-{config['end_frame']}")
    print(f"  分辨率: {config['resolution_x']}x{config['resolution_y']} ({config['resolution_percent']}%)")
    
    if config["render_engine"] == "CYCLES":
        print(f"  Cycles 采样: {config['samples']}")
        print(f"  分块大小 (tile size): {config['tile_size']}")  # 修复这里，确保字符串闭合
        print(f"  最大光线反弹: {config['max_bounces']}")
        print(f"  噪波阈值: {config['noise_threshold']}")
        print(f"  降噪采样: {config['denoising_samples']}")
        print(f"  降噪器: {config['denoiser']}")
        print(f"  设备类型: {config['device_type']}")
    else:
        engine_name = config['render_engine'].replace('BLENDER_', '').replace('_', ' ')
        print(f"  {engine_name} 采样: {config['eevee_samples']}")
        print(f"  环境光遮蔽: {'是' if config['eevee_ambient_occlusion'] else '否'}")
        print(f"  辉光效果: {'是' if config['eevee_bloom'] else '否'}")
        print(f"  屏幕空间反射: {'是' if config['eevee_ssr'] else '否'}")
        print(f"  体积效果: {'是' if config['eevee_volumetric'] else '否'}")
    
    # 新增：FFmpeg设置
    if config["file_format"] == "FFMPEG":
        print(f"  FFmpeg容器格式: {config['ffmpeg_format']}")
        print(f"  FFmpeg视频编码: {config['ffmpeg_codec']}")
        # 添加质量设置显示
        quality_map_str = {
            "LOSSLESS": "无损 (CRF=0)",
            "PERC_LOSSLESS": "接近无损 (CRF=18)",
            "HIGH": "高质量 (CRF=20)",
            "MEDIUM": "中等质量 (CRF=23)",
            "LOW": "低质量 (CRF=28)"
        }
        quality_str = quality_map_str.get(config["ffmpeg_quality"], "自定义")
        print(f"  FFmpeg质量设置: {quality_str}")
    
    print("=" * 80)

def fix_driver_issues():
    """修复驱动问题"""
    scene = bpy.context.scene
    try:
        if scene.animation_data and scene.animation_data.drivers:
            for fcurve in scene.animation_data.drivers:
                expr = fcurve.driver.expression
                if "sensor_height/tan(angle/2)/2" in expr:
                    # 使用更安全的表达式
                    new_expr = expr.replace(
                        "sensor_height/tan(angle/2)/2",
                        "sensor_height/(tan(angle/2)+0.0001)/2"
                    )
                    fcurve.driver.expression = new_expr
                    print("✅ 修复除零错误")
    except Exception as e:
        print(f"⚠️ 修复驱动错误失败: {e}")

def render_frames():
    """渲染帧序列"""
    scene = bpy.context.scene
    start = scene.frame_start
    end = scene.frame_end
    
    print(f"🔄🔄 开始渲染序列帧: {start}-{end}")
    
    # 渲染序列
    bpy.ops.render.render(animation=True)
    
    print("🎉🎉 渲染完成!")

# =====================================================================
# 主函数
# =====================================================================

def main():
    try:
        print_header("Blender 多渲染器终极配置")
        
        # 修复驱动问题
        fix_driver_issues()
        
        # 选择配置模式
        mode = configure_render_mode()
        
        # 获取配置
        if mode == "blend":
            config = get_blend_config()
        elif mode == "default":
            config = get_default_config()
        else:
            config = get_custom_config()
        
        # 应用配置
        scene = apply_config(config)
        
        # 打印配置摘要
        print_config_summary(config)
        
        # 确认开始渲染
        confirm = input("是否开始渲染? (y/n): ")
        if confirm.lower() == "y":
            render_frames()
            print("=" * 80)
            print(f"🎉🎉 渲染完成! 文件保存在: {bpy.path.abspath(scene.render.filepath)}")
            print("=" * 80)
        else:
            print("🚪🚪 退出程序")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌❌ 错误: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 强制垃圾回收
    gc.collect()
    main()