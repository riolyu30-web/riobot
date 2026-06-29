import subprocess
import shutil
import os
from pathlib import Path
import imageio_ffmpeg

def generate_video(data: dict, output_path: str):
    """
    通过模板注入和 HyperFrames CLI 生成视频
    """
    # 1. 准备工作目录并复制模板
    base_dir = Path(__file__).parent.absolute()
    work_dir = base_dir / "tmp_build_4"
    template_dir = base_dir / "templates" / "my-video"
    
    if work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except Exception as e:
            print(f"Warning: Failed to rmtree {work_dir}: {e}")
            work_dir = base_dir / "tmp_build_8"
        
    shutil.copytree(template_dir, work_dir, dirs_exist_ok=True)
    print(f"[*] 模板已复制到临时目录: {work_dir}")

    # 2. 将数据注入到 HTML 模板中
    index_file = work_dir / "index.html"
    html = index_file.read_text(encoding="utf-8")
    
    # 替换占位符
    html = html.replace("{{USER_NAME}}", data.get("name", "User"))
    html = html.replace("{{REVENUE}}", f"${data.get('revenue', 0):,.0f}")
    
    index_file.write_text(html, encoding="utf-8")
    print(f"[*] 数据注入完成: {data}")

    # 3. 调用 HyperFrames 命令行进行渲染
    print("[*] 正在通过 HyperFrames 渲染视频，这可能需要一些时间...")
    
    try:
        # 获取 imageio_ffmpeg 提供的 ffmpeg 路径，并将其添加到环境变量 PATH 中
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        
        env = os.environ.copy()
        # 确保 ffmpeg 所在的目录在 PATH 中优先
        env["PATH"] = f"{ffmpeg_dir}{os.pathsep}{env.get('PATH', '')}"
        
        # 很多 Node.js 工具调用子进程时还需要 FFMPEG_PATH 环境变量
        env["FFMPEG_PATH"] = ffmpeg_exe
        
        # 将 imageio_ffmpeg 提供的二进制文件在本地目录建立一个名为 ffmpeg.exe 的硬链接/复制
        # 因为很多工具强制通过 "ffmpeg" 这个名字去查找
        local_ffmpeg = Path(ffmpeg_dir) / "ffmpeg.exe"
        if not local_ffmpeg.exists() and ffmpeg_exe != str(local_ffmpeg):
            try:
                shutil.copy2(ffmpeg_exe, local_ffmpeg)
            except Exception as e:
                print(f"Warning: Failed to copy ffmpeg: {e}")
                
        # 调试：打印注入后的 PATH 和 ffmpeg 检查
        print(f"[*] ffmpeg_exe path: {ffmpeg_exe}")
        
        # 使用 npx 运行 hyperframes render
        result = subprocess.run([
            "npx", "-y", "hyperframes", "render",
            "--output", str(Path(output_path).absolute()),
            "--fps", "30"
        ], cwd=str(work_dir), shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        if result.returncode == 0:
            print(f"[+] 视频渲染成功！已保存至: {output_path}")
        else:
            print(f"[-] 视频渲染失败，返回码: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"[-] 视频渲染失败，错误信息: {e}")
    finally:
        # 清理临时目录
        if work_dir.exists():
            try:
                shutil.rmtree(work_dir)
            except Exception as e:
                print(f"Warning: Failed to rmtree {work_dir}: {e}")

if __name__ == "__main__":
    import traceback
    try:
        # 测试数据
        mock_data = {
            "name": "Trae Developer",
            "revenue": 128500
        }
        
        output_video = "output_rising.mp4"
        generate_video(mock_data, output_video)
    except Exception as e:
        print("Fatal error:")
        traceback.print_exc()
