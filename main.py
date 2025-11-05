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
            
            # 解析EXIF标签(将数字标签转换为可读名称)
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
            
            # 特殊处理GPS信息(如果有的话)
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
    
    # 提取相机品牌(去除可能的空格)
    brand = exif_data.get("Make", "未知品牌").strip()
    
    # 提取相机型号
    model = exif_data.get("Model", "未知型号").strip()
    
    # 提取镜头型号(不同相机厂商标签可能不同，这里兼容常见标签)
    lens = exif_data.get("LensModel", exif_data.get("Lens", "未知镜头")).strip()
    
    # 提取焦距(单位:mm)- 显示为整数
    focal_length = exif_data.get("FocalLength")
    if focal_length:
        if isinstance(focal_length, tuple):
            focal_length = f"{int(focal_length[0]/focal_length[1])}mm"
        else:
            focal_length = f"{int(focal_length)}mm"
    else:
        focal_length = "未知焦距"
    
    # 提取光圈值(F值)
    f_number = exif_data.get("FNumber")
    if isinstance(f_number, tuple):
        f_number = f"F{f_number[0]/f_number[1]:.1f}"
    else:
        f_number = f"F{f_number}" if f_number else "未知光圈"
    
    # 提取快门速度(单位:秒)
    exposure_time = exif_data.get("ExposureTime")
    if exposure_time:
        # 转换为Fraction对象(兼容tuple和其他格式)
        if isinstance(exposure_time, tuple):
            frac = fractions.Fraction(exposure_time[0], exposure_time[1])
        elif isinstance(exposure_time, fractions.Fraction):
            frac = exposure_time
        else:
            frac = fractions.Fraction(exposure_time).limit_denominator()
        
        # 始终显示为分数格式
        if frac.numerator < frac.denominator:
            # 小于1秒:显示为分数(如1/100s)
            exposure_time = f"{frac.numerator}/{frac.denominator}"
        else:
            # 大于等于1秒:也显示为分数(如2/1s 或直接显示秒数)
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
    
    # 提取拍摄时间(优先用原始时间，无则用修改时间)
    datetime_original = exif_data.get("DateTimeOriginal", "")
    datetime_digitized = exif_data.get("DateTimeDigitized", "")
    shoot_time = datetime_original or datetime_digitized
    if shoot_time:
        # 格式化时间(如2025:10:31 22:40:15 → 2025.10.31 22:40:15)
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
    # 绘制圆角矩形(白色区域为保留部分)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    
    # 创建输出图片
    output = Image.new('RGBA', img.size, (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    return output

def add_shadow(img, shadow_offset=10, shadow_blur=15, shadow_opacity=128):
    """给图片添加阴影效果
    
    参数:
        img: 输入图片(RGBA格式)
        shadow_offset: 阴影偏移量(像素)，默认10
        shadow_blur: 阴影模糊半径(像素)，默认15
        shadow_opacity: 阴影不透明度(0-255)，默认128(半透明)
    """
    # 创建足够大的画布来容纳阴影
    shadow_margin = shadow_blur + shadow_offset
    canvas_size = (img.width + shadow_margin * 2, img.height + shadow_margin * 2)
    
    # 创建阴影层(黑色)
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

def add_border_and_auto_text(image_path, output_path, 
                             border_style='blur',  # 新增参数:'blur'=虚化边框, 'white'=白色底框
                             corner_radius=30, 
                             shadow_offset=8, shadow_blur=20, shadow_opacity=100):
    """自动读取图片参数,添加边框和文字
    
    参数:
        image_path: 输入图片路径
        output_path: 输出图片路径
        border_style: 边框样式，'blur'=虚化边框(四周), 'white'=白色底框(仅底部)
        corner_radius: 圆角半径(像素)，默认30。设为0则无圆角(仅blur模式有效)
        shadow_offset: 阴影偏移量(像素)，默认8。设为0则无阴影(仅blur模式有效)
        shadow_blur: 阴影模糊半径(像素)，默认20(仅blur模式有效)
        shadow_opacity: 阴影不透明度(0-255)，默认100(仅blur模式有效)
    """
    # 1. 读取并解析EXIF信息
    exif_data = get_exif_data(image_path)
    params = format_exif_params(exif_data)
    
    # 2. 打开原始图片并处理方向
    with Image.open(image_path) as img:
        # 根据EXIF中的Orientation信息自动旋转图片到正确方向
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        
        # 3. 定义边框宽度
        border_width = max(30, int(min(width, height) * 0.1))  # 最小30px
        
        if border_style == 'white':
            # ========== 白色底框模式 ==========
            new_width = width  # 左右不加边框
            new_height = height + border_width  # 只在底部加边框
            
            # 创建白色背景画布
            background = Image.new('RGB', (new_width, new_height), (255, 255, 255))
            
            # 将原图直接粘贴到白色背景上(顶部对齐，无圆角和阴影)
            new_img = background
            new_img.paste(img, (0, 0))  # 左上角对齐粘贴
            
            # 文字颜色为黑色
            text_color = 'black'
            
        else:  # border_style == 'blur'
            # ========== 虚化边框模式 ==========
            new_width = width + 2 * border_width
            new_height = height + 2 * border_width
            
            # 将原图放大并模糊作为背景
            background = img.copy()
            background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 对背景进行高斯模糊(虚化效果)
            blur_radius = max(20, border_width // 3)
            background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            # 给原图添加圆角
            if corner_radius > 0:
                img_with_corners = add_rounded_corners(img, corner_radius)
            else:
                img_with_corners = img.convert('RGBA')
            
            # 添加阴影效果
            if shadow_offset > 0:
                img_with_shadow = add_shadow(img_with_corners, shadow_offset, shadow_blur, shadow_opacity)
                shadow_margin = shadow_blur + shadow_offset
                new_width_with_shadow = new_width + shadow_margin * 2
                new_height_with_shadow = new_height + shadow_margin * 2
                background = background.resize((new_width_with_shadow, new_height_with_shadow), Image.Resampling.LANCZOS)
                background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                new_img = background.convert('RGB')
                new_img.paste(img_with_shadow, (border_width, border_width), img_with_shadow)
                new_width = new_width_with_shadow
                new_height = new_height_with_shadow
            else:
                new_img = background.convert('RGB')
                if corner_radius > 0:
                    new_img.paste(img_with_corners, (border_width, border_width), img_with_corners)
                else:
                    new_img.paste(img, (border_width, border_width))
            
            # 文字颜色为白色
            text_color = 'white'
        
        # 4. 添加自动读取的文字标注
        draw = ImageDraw.Draw(new_img)
        font_size = max(20, int(border_width * 0.3))
        print(f"边框样式: {border_style}, 边框宽度: {border_width}px, 字体大小: {font_size}px")
        
        font = ImageFont.truetype('C:\\Windows\\Fonts\\arial.ttf', font_size)

        # 底部边框的居中位置
        text_x_position = new_width // 2
        text_y_position = new_height - border_width // 2
        
        # 底部居中:第一行品牌+型号，第二行参数
        bottom_text = f"{params['brand']} {params['model']}\n{params['params']}"
        
        draw.text(
            (text_x_position, text_y_position),
            bottom_text,
            font=font,
            fill=text_color,
            anchor='mm',
            align='center',
            spacing=15
        )
        
        # 5. 保存图片(高质量)
        file_ext = os.path.splitext(output_path)[1].lower()
        if file_ext in ['.jpg', '.jpeg']:
            new_img.save(output_path, quality=95, subsampling=0)
        elif file_ext == '.png':
            new_img.save(output_path, compress_level=1)
        else:
            new_img.save(output_path)
        return new_img

# ------------------- 批量处理功能 -------------------
def process_images(input_patterns, output_dir="output", 
                   border_style='blur',  # 新增参数
                   corner_radius=30, 
                   shadow_offset=8, shadow_blur=20, shadow_opacity=100):
    """批量处理图片
    
    参数:
        input_patterns: 输入图片路径或通配符模式(可以是单个文件或列表)
        output_dir: 输出目录，默认为"output"
        border_style: 边框样式，'blur'=虚化边框, 'white'=白色底框
        其他参数同add_border_and_auto_text
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
        matched_files = glob.glob(pattern)
        if matched_files:
            image_files.extend(matched_files)
        else:
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
            filename = os.path.basename(input_path)
            name_without_ext = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            
            # 生成输出文件名(添加边框样式后缀)
            output_filename = f"{name_without_ext}_{border_style}{ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"[{i}/{len(image_files)}] 处理中: {filename}")
            
            # 处理图片
            result = add_border_and_auto_text(
                input_path,
                output_path,
                border_style=border_style,
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
    """
    使用说明:
    
    1. 虚化边框模式(默认):
       python main_merged.py image.jpg
       python main_merged.py *.jpg
    
    2. 白色底框模式:
       python main_merged.py --style white image.jpg
       python main_merged.py --style white *.jpg
    
    3. 指定输出目录:
       python main_merged.py --output my_output image.jpg
    
    4. 组合使用:
       python main_merged.py --style white --output my_output *.jpg
    
    参数说明:
    --style: 边框样式，blur(虚化边框)或 white(白色底框)，默认blur
    --output: 输出目录，默认为 output
    --corner: 圆角大小(仅blur模式)，默认30
    --shadow: 阴影偏移(仅blur模式)，默认8
    """
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    # 默认参数
    border_style = 'blur'
    output_dir = 'output'
    corner_radius = 30
    shadow_offset = 8
    shadow_blur = 20
    shadow_opacity = 100
    input_patterns = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--style' and i + 1 < len(args):
            border_style = args[i + 1]
            i += 2
        elif arg == '--output' and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif arg == '--corner' and i + 1 < len(args):
            corner_radius = int(args[i + 1])
            i += 2
        elif arg == '--shadow' and i + 1 < len(args):
            shadow_offset = int(args[i + 1])
            i += 2
        else:
            input_patterns.append(arg)
            i += 1
    
    if input_patterns:
        print(f"命令行模式: 边框样式={border_style}, 输出目录={output_dir}")
        process_images(
            input_patterns,
            output_dir=output_dir,
            border_style=border_style,
            corner_radius=corner_radius,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
            shadow_opacity=shadow_opacity
        )
    else:
        print("=" * 60)
        print("图片边框水印工具 - 合并版")
        print("=" * 60)
        print("\n使用方法:")
        print("\n1. 虚化边框模式(默认):")
        print("   python main_merged.py image.jpg")
        print("   python main_merged.py *.jpg")
        print("\n2. 白色底框模式:")
        print("   python main_merged.py --style white image.jpg")
        print("   python main_merged.py --style white *.jpg")
        print("\n3. 指定输出目录:")
        print("   python main_merged.py --output my_output image.jpg")
        print("\n4. 组合使用:")
        print("   python main_merged.py --style white --output my_output *.jpg")
        print("\n参数说明:")
        print("  --style  : 边框样式，blur(虚化边框)或 white(白色底框)，默认blur")
        print("  --output : 输出目录，默认为 output")
        print("  --corner : 圆角大小(仅blur模式)，默认30")
        print("  --shadow : 阴影偏移(仅blur模式)，默认8")
        print("=" * 60)