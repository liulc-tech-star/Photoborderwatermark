from PIL import Image, ImageFilter, ImageDraw, ImageFont
from PIL.ExifTags import TAGS, GPSTAGS
import fractions
import datetime
import sys
import os
import glob

def get_exif_data(image_path):
    """从图片中提取并解析EXIF信息"""
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()  # 获取原始EXIF数据
            if not exif:
                return None  # 无EXIF信息
            
            # 解析EXIF标签（将数字标签转换为可读名称）
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
            
            # 特殊处理GPS信息（如果有的话）
            if 'GPSInfo' in exif_data:
                gps_info = {}
                for key in exif_data['GPSInfo']:
                    decode = GPSTAGS.get(key, key)
                    gps_info[decode] = exif_data['GPSInfo'][key]
                exif_data['GPSInfo'] = gps_info
    except Exception as e:
        print(f"读取EXIF失败:{e}")
        return None
    return exif_data

def format_exif_params(exif_data):
    """格式化EXIF信息为需要的参数文本"""
    if not exif_data:
        return {
            "brand": "未知品牌",
            "model": "未知型号",
            "lens": "未知镜头",
            "params": "参数未知",
            "datetime": "拍摄时间未知"
        }
    
    # 提取相机品牌（去除可能的空格）
    brand = exif_data.get("Make", "未知品牌").strip()
    
    # 提取相机型号
    model = exif_data.get("Model", "未知型号").strip()
    
    # 提取镜头型号（不同相机厂商标签可能不同，这里兼容常见标签）
    lens = exif_data.get("LensModel", exif_data.get("Lens", "未知镜头")).strip()
    
    # 提取焦距（单位：mm）- 显示为整数
    focal_length = exif_data.get("FocalLength")
    if focal_length:
        if isinstance(focal_length, tuple):
            focal_length = f"{int(focal_length[0]/focal_length[1])}mm"
        else:
            focal_length = f"{int(focal_length)}mm"
    else:
        focal_length = "未知焦距"
    
    # 提取光圈值（F值）
    f_number = exif_data.get("FNumber")
    if isinstance(f_number, tuple):
        f_number = f"F{f_number[0]/f_number[1]:.1f}"
    else:
        f_number = f"F{f_number}" if f_number else "未知光圈"
    
    # 提取快门速度（单位：秒）
    exposure_time = exif_data.get("ExposureTime")
    if exposure_time:
        # 转换为Fraction对象（兼容tuple和其他格式）
        if isinstance(exposure_time, tuple):
            frac = fractions.Fraction(exposure_time[0], exposure_time[1])
        elif isinstance(exposure_time, fractions.Fraction):
            frac = exposure_time
        else:
            frac = fractions.Fraction(exposure_time).limit_denominator()
        
        # 始终显示为分数格式
        if frac.numerator < frac.denominator:
            # 小于1秒：显示为分数（如1/100s）
            exposure_time = f"{frac.numerator}/{frac.denominator}"
        else:
            # 大于等于1秒：也显示为分数（如2/1s 或直接显示秒数）
            if frac.denominator == 1:
                exposure_time = f"{frac.numerator}"
            else:
                exposure_time = f"{frac.numerator}/{frac.denominator}"
    else:
        exposure_time = "未知快门"
    
    # 提取ISO
    iso = exif_data.get("ISOSpeedRatings", "未知ISO")
    
    # 合并拍摄参数文本
    params = f"{focal_length}  {f_number}  {exposure_time}  ISO{iso}"
    
    # 提取拍摄时间（优先用原始时间，无则用修改时间）
    datetime_original = exif_data.get("DateTimeOriginal", "")
    datetime_digitized = exif_data.get("DateTimeDigitized", "")
    shoot_time = datetime_original or datetime_digitized
    if shoot_time:
        # 格式化时间（如2025:10:31 22:40:15 → 2025.10.31 22:40:15）
        shoot_time = shoot_time.replace(":", ".", 2)
    else:
        shoot_time = "拍摄时间未知"
    
    return {
        "brand": brand,
        "model": model,
        "lens": lens,
        "params": params,
        "datetime": shoot_time
    }

def add_rounded_corners(img, radius):
    """给图片添加圆角"""
    # 创建一个圆角遮罩
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    # 绘制圆角矩形（白色区域为保留部分）
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    
    # 创建输出图片
    output = Image.new('RGBA', img.size, (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    return output

def add_shadow(img, shadow_offset=10, shadow_blur=15, shadow_opacity=128):
    """给图片添加阴影效果
    
    参数:
        img: 输入图片（RGBA格式）
        shadow_offset: 阴影偏移量（像素），默认10
        shadow_blur: 阴影模糊半径（像素），默认15
        shadow_opacity: 阴影不透明度（0-255），默认128（半透明）
    """
    # 创建足够大的画布来容纳阴影
    shadow_margin = shadow_blur + shadow_offset
    canvas_size = (img.width + shadow_margin * 2, img.height + shadow_margin * 2)
    
    # 创建阴影层（黑色）
    shadow = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    
    # 在阴影层上绘制半透明黑色矩形
    shadow_pos = (shadow_margin + shadow_offset, shadow_margin + shadow_offset, 
                  shadow_margin + shadow_offset + img.width, 
                  shadow_margin + shadow_offset + img.height)
    shadow_draw.rectangle(shadow_pos, fill=(0, 0, 0, shadow_opacity))
    
    # 模糊阴影
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    
    # 将原图粘贴到阴影上方
    shadow.paste(img, (shadow_margin, shadow_margin), img)
    
    return shadow

def add_vignette_border_and_auto_text(image_path, output_path, corner_radius=30, 
                                      shadow_offset=8, shadow_blur=20, shadow_opacity=100):
    """自动读取图片参数,添加虚化边框和文字
    
    参数:
        image_path: 输入图片路径
        output_path: 输出图片路径
        corner_radius: 圆角半径（像素），默认30。设为0则无圆角
        shadow_offset: 阴影偏移量（像素），默认8。设为0则无阴影
        shadow_blur: 阴影模糊半径（像素），默认20
        shadow_opacity: 阴影不透明度（0-255），默认100
    """
    # 1. 读取并解析EXIF信息
    exif_data = get_exif_data(image_path)
    params = format_exif_params(exif_data)
    
    # 2. 打开原始图片并处理方向
    with Image.open(image_path) as img:
        # 根据EXIF中的Orientation信息自动旋转图片到正确方向
        # 使用ImageOps.exif_transpose自动处理方向
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        
        # 3. 定义边框宽度（只保留下边框）
        border_width = max(30, int(min(width, height) * 0.1))  # 最小30px，最大为图片短边的10%
        new_width = width  # 左右不加边框
        new_height = height + border_width  # 只在底部加边框
        
        # 4. 创建白色背景画布
        background = Image.new('RGB', (new_width, new_height), (255, 255, 255))  # 白色背景
        
        # 6. 将原图直接粘贴到白色背景上（顶部对齐，无圆角和阴影）
        new_img = background
        new_img.paste(img, (0, 0))  # 左上角对齐粘贴
        
        # 8. 添加自动读取的文字标注（在白色下边框上）
        draw = ImageDraw.Draw(new_img)
        # 字体大小自适应边框宽度
        font_size = max(20, int(border_width * 0.3))  # 最小20px
        print(f"边框宽度: {border_width}px, 字体大小: {font_size}px")  # 调试信息
        
        font = ImageFont.truetype('C:\\Windows\\Fonts\\arial.ttf', font_size)  # 使用完整路径

        # 底部边框的上下左右居中位置
        # X轴：画布宽度的一半（水平居中）
        text_x_position = new_width // 2
        # Y轴：底部边框的中心位置
        # 底部边框的起始位置是 (new_height - border_width)
        # 底部边框的结束位置是 new_height
        # 中心位置是两者的平均值
        text_y_position = new_height - border_width // 2
        
        # 底部居中：第一行品牌+型号，第二行参数
        bottom_text = f"{params['brand']} {params['model']}\n{params['params']}"
        
        draw.text(
            (text_x_position, text_y_position),
            bottom_text,
            font=font,
            fill='black',  # 白色背景上使用黑色文字
            anchor='mm',  # 完全居中对齐（middle-middle）
            align='center',  # 多行文字居中
            spacing=15 # 行间距
        )
        
        # 9. 保存图片（高质量）
        # 根据文件扩展名判断格式
        file_ext = os.path.splitext(output_path)[1].lower()
        if file_ext in ['.jpg', '.jpeg']:
            # JPEG格式：使用最高质量，保留更多细节
            new_img.save(output_path, quality=95, subsampling=0)
        elif file_ext == '.png':
            # PNG格式：无损压缩
            new_img.save(output_path, compress_level=1)
        else:
            # 其他格式：使用默认设置
            new_img.save(output_path)
        return new_img

# ------------------- 批量处理功能 -------------------
def process_images(input_patterns, output_dir="output", corner_radius=30, 
                   shadow_offset=8, shadow_blur=20, shadow_opacity=100):
    """批量处理图片
    
    参数:
        input_patterns: 输入图片路径或通配符模式（可以是单个文件或列表）
        output_dir: 输出目录，默认为"output"
        其他参数同add_vignette_border_and_auto_text
    """
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 如果是单个字符串，转换为列表
    if isinstance(input_patterns, str):
        input_patterns = [input_patterns]
    
    # 收集所有要处理的图片文件
    image_files = []
    for pattern in input_patterns:
        # 支持通配符（如 *.jpg）
        matched_files = glob.glob(pattern)
        if matched_files:
            image_files.extend(matched_files)
        else:
            # 如果没有匹配到，可能是单个文件路径
            if os.path.exists(pattern):
                image_files.append(pattern)
            else:
                print(f"警告: 未找到文件 '{pattern}'")
    
    if not image_files:
        print("错误: 没有找到要处理的图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件待处理\n")
    
    # 处理每个图片
    success_count = 0
    for i, input_path in enumerate(image_files, 1):
        try:
            # 获取文件名（不含路径和扩展名）
            filename = os.path.basename(input_path)
            name_without_ext = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            
            # 生成输出文件名（添加_processed后缀）
            output_filename = f"{name_without_ext}_processed{ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"[{i}/{len(image_files)}] 处理中: {filename}")
            
            # 处理图片
            result = add_vignette_border_and_auto_text(
                input_path,
                output_path,
                corner_radius=corner_radius,
                shadow_offset=shadow_offset,
                shadow_blur=shadow_blur,
                shadow_opacity=shadow_opacity
            )
            
            print(f"    ✓ 已保存到: {output_path}\n")
            success_count += 1
            
        except Exception as e:
            print(f"    ✗ 处理失败: {e}\n")
    
    print(f"处理完成! 成功: {success_count}/{len(image_files)}")

# ------------------- 命令行调用 -------------------
if __name__ == "__main__":
    # 参数说明：
    # corner_radius: 圆角大小（0=无圆角, 30=默认, 50=更圆）
    # shadow_offset: 阴影偏移（0=无阴影, 8=默认, 15=更明显）
    # shadow_blur: 阴影模糊度（默认20）
    # shadow_opacity: 阴影透明度（0-255, 默认100）
    
    if len(sys.argv) > 1:
        # 命令行模式：使用命令行参数
        input_patterns = sys.argv[1:]  # 所有参数都作为输入文件/模式
        print(f"命令行模式: 处理 {input_patterns}")
        process_images(
            input_patterns,
            output_dir="output",
            corner_radius=30,
            shadow_offset=8,
            shadow_blur=20,
            shadow_opacity=100
        )
    else:
        # 默认模式：处理当前目录下的示例图片
        print("默认模式: 请提供图片路径作为参数")
        print("\n使用方法:")
        print("  单个文件:   python test.py image.jpg")
        print("  多个文件:   python test.py image1.jpg image2.jpg image3.jpg")
        print("  通配符:     python test.py *.jpg")
        print("  混合使用:   python test.py photo*.jpg aaa.jpg bbb.jpg")
        print("\n或者在代码中修改这里进行测试:")
        
