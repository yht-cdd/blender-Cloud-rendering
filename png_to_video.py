import os
import subprocess
import sys

def print_header(title):
    """打印标题"""
    print("=" * 80)
    print(f"🚀 {title}")
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

def ensure_file_extension(filename, default_extension=".mp4"):
    """确保文件名有正确的扩展名"""
    if not any(filename.lower().endswith(ext) for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]):
        return filename + default_extension
    return filename

def create_video_from_pngs():
    """交互式创建视频"""
    print_header("PNG序列转视频工具")
    
    # 1. 获取输入文件夹
    print("\n📂 步骤1: 选择PNG序列文件夹")
    input_folder = get_user_input("请输入PNG序列文件夹路径")
    
    # 验证文件夹是否存在
    if not os.path.exists(input_folder):
        print(f"❌ 错误: 文件夹不存在: {input_folder}")
        return False
    
    # 2. 获取输出文件路径
    print("\n📁 步骤2: 设置输出视频文件")
    output_file = get_user_input("请输入输出视频文件路径 (如: output.mp4)", "output.mp4")
    
    # 确保文件名有扩展名
    output_file = ensure_file_extension(output_file)
    
    # 3. 设置帧率
    print("\n⏱️ 步骤3: 设置视频帧率")
    frame_rate = get_user_input("请输入视频帧率 (FPS)", 24, int)
    
    # 4. 选择编码器
    print("\n🔧 步骤4: 选择视频编码器")
    codecs = ["H.264 (通用)", "H.265 (高效)", "VP9 (WebM)", "ProRes (专业编辑)"]
    codec_choice = select_from_options("请选择视频编码器:", codecs)
    
    codec_map = {
        "H.264 (通用)": "libx264",
        "H.265 (高效)": "libx265",
        "VP9 (WebM)": "libvpx-vp9",
        "ProRes (专业编辑)": "prores"
    }
    codec = codec_map.get(codec_choice, "libx264")
    
    # 5. 选择质量预设
    print("\n🎨 步骤5: 选择视频质量")
    quality_options = ["超高质量 (文件大)", "高质量", "中等质量", "低质量 (文件小)"]
    quality_choice = select_from_options("请选择视频质量:", quality_options, 2)
    
    quality_map = {
        "超高质量 (文件大)": {"preset": "slow", "crf": 18},
        "高质量": {"preset": "medium", "crf": 20},
        "中等质量": {"preset": "fast", "crf": 23},
        "低质量 (文件小)": {"preset": "ultrafast", "crf": 28}
    }
    quality_settings = quality_map.get(quality_choice, {"preset": "medium", "crf": 23})
    
    # 6. 确认设置
    print("\n✅ 最终设置:")
    print(f"  输入文件夹: {input_folder}")
    print(f"  输出文件: {output_file}")
    print(f"  帧率: {frame_rate} FPS")
    print(f"  编码器: {codec_choice}")
    print(f"  质量: {quality_choice}")
    
    confirm = get_user_input("\n是否开始创建视频? (y/n)", "y")
    if confirm.lower() != "y":
        print("🚪 操作取消")
        return False
    
    # 7. 执行转换
    print("\n🔄 开始创建视频...")
    
    try:
        # 构建输入文件模式
        input_pattern = os.path.join(input_folder, "*.png")
        
        # 构建 FFmpeg 命令
        command = [
            "ffmpeg",
            "-y",  # 覆盖已存在文件
            "-framerate", str(frame_rate),
            "-pattern_type", "glob",
            "-i", input_pattern,
            "-c:v", codec,
            "-preset", quality_settings["preset"],
            "-crf", str(quality_settings["crf"]),
            "-pix_fmt", "yuv420p",  # 确保兼容性
            "-r", str(frame_rate),  # 输出帧率
            "-movflags", "+faststart"  # 网络优化
        ]
        
        # 特殊编码器设置
        if codec == "libvpx-vp9":
            command.extend(["-b:v", "0"])  # VP9需要这个参数
        elif codec == "prores":
            command.extend(["-profile:v", "3"])  # ProRes HQ
        
        # 添加输出文件路径
        command.append(output_file)
        
        # 打印执行的命令
        print("🚀 执行命令:", " ".join(command))
        
        # 运行 FFmpeg 命令
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n🎉 视频创建成功: {output_file}")
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"📏 文件大小: {file_size:.2f} MB")
            return True
        else:
            print("\n❌ FFmpeg 执行失败:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        return False

def main():
    """主函数"""
    try:
        # 检查是否安装了FFmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("❌ 错误: FFmpeg 未安装")
            print("请先安装 FFmpeg:")
            print("  Ubuntu/Debian: sudo apt install ffmpeg")
            print("  macOS: brew install ffmpeg")
            print("  Windows: 从 https://ffmpeg.org/download.html 下载")
            return
        
        # 运行转换过程
        success = create_video_from_pngs()
        
        if success:
            print("\n✅ 处理完成!")
        else:
            print("\n❌ 处理失败")
        
        # 询问是否再次运行
        restart = get_user_input("\n是否要创建另一个视频? (y/n)", "n")
        if restart.lower() == "y":
            main()
        else:
            print("\n👋 感谢使用PNG序列转视频工具!")
    
    except KeyboardInterrupt:
        print("\n🚪 用户中断操作")
        sys.exit(0)

if __name__ == "__main__":
    print_header("PNG序列转视频工具")
    print("只需几步即可将PNG序列转换为视频文件")
    print("=" * 80)
    main()