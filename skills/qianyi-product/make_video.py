# 导入os模块，用于处理文件路径和创建目录
import os
# 导入sys模块，用于获取命令行中传入的参数
import sys
# 导入cv2模块，用于读取视频和提取帧图像（需要安装opencv-python）
import cv2

# 定义提取视频帧的函数，接收一个视频路径参数
def extract_frames(video_path):
    # 检查传入的视频文件路径在文件系统中是否存在
    if not os.path.exists(video_path):
        # 如果文件不存在，则打印一条错误信息提示用户
        print("错误：视频文件不存在！")
        # 直接退出函数，不再向下执行
        return
    
    # 获取当前脚本文件所在的绝对目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 在当前脚本所在目录下构造一个名为"videos"的输出目录路径
    output_dir = os.path.join(current_dir, "videos")
    
    # 判断该输出目录是否已经存在
    if not os.path.exists(output_dir):
        # 如果目录不存在，则调用os.makedirs方法递归创建该目录
        os.makedirs(output_dir)
    
    # 使用cv2.VideoCapture类打开指定的视频文件
    cap = cv2.VideoCapture(video_path)
    
    # 检查视频对象是否成功初始化并打开
    if not cap.isOpened():
        # 如果未成功打开，则打印错误提示信息
        print("错误：无法打开视频文件！")
        # 退出当前函数
        return
    
    # 从视频流中获取视频的帧率属性（每秒显示的帧数）
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # 计算半秒（0.5秒）对应的帧数，使用四舍五入并转换为整数
    interval = int(round(fps * 0.5))
    
    # 预防帧率获取异常导致间隔小于等于0的情况
    if interval <= 0:
        # 如果异常，则将半秒间隔强制设为15帧（假设默认30fps）
        interval = 15
    
    # 初始化读取视频的帧计数器，从0开始
    frame_count = 0
    
    # 初始化成功保存的截图计数器，从0开始
    saved_count = 0
    
    # 开启一个无限循环，用于逐帧读取视频数据
    while True:
        # 读取下一帧视频，ret表示读取是否成功，frame是具体的图像数据矩阵
        ret, frame = cap.read()
        
        # 判断读取结果是否为失败（通常代表已经读取到视频末尾）
        if not ret:
            # 如果是，则跳出无限循环
            break
        
        # 判断当前的帧索引是否是半秒帧数的整数倍，这代表正好经过了0.5秒的时间
        if frame_count % interval == 0:
            # 构造截图的保存文件名，使用格式化字符串将数字补零为4位数
            filename = f"screenshot_{saved_count:04d}.jpg"
            
            # 使用os.path.join拼接输出目录和文件名，得到最终的完整保存路径
            save_path = os.path.join(output_dir, filename)
            
            # 调用cv2.imwrite将这一帧图像矩阵写入到指定路径保存为JPEG图片
            cv2.imwrite(save_path, frame)
            
            # 在控制台打印已成功保存的图片绝对路径
            print(f"已保存: {save_path}")
            
            # 将成功保存图片的计数器加一
            saved_count += 1
            
        # 将读取视频帧的计数器加一，准备下一次循环读取下一帧
        frame_count += 1
        
    # 循环结束后，释放视频捕获对象的系统资源
    cap.release()
    
    # 打印提示信息，告知用户所有截图均已提取完毕
    print(f"提取完成，共保存 {saved_count} 张截图。")

# 检查当前脚本文件是否被直接作为主程序运行
if __name__ == "__main__":
    # 判断命令行参数列表的长度是否小于2（sys.argv[0]是脚本名，至少需要一个额外参数）
    if len(sys.argv) < 2:
        # 如果没有提供视频路径，则提示用户正确的命令行运行方式
        print("用法: python make_video.py <视频绝对路径>")
    # 如果提供了足够的参数
    else:
        # 获取命令行中传入的第一个参数，作为目标视频的绝对路径
        video_abs_path = sys.argv[1]
        # 调用定义好的extract_frames函数开始处理该视频文件
        extract_frames(video_abs_path)
