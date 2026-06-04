# Photo Border Watermark Studio

一个给照片添加边框和 EXIF 参数水印的小工具。现在支持桌面控制台和命令行两种方式：双击新版 exe 可以打开可视化控制台，选择照片、预览效果、调整参数并批量导出。

## 主要功能

- 自动读取 EXIF 信息：品牌、型号、镜头、焦距、光圈、快门、ISO、拍摄时间
- 两种边框样式：
  - `blur`：虚化背景边框，支持圆角、阴影、背景模糊强度
  - `white`：底部白色信息条，清爽直接
- 桌面控制台：
  - 选择单张/多张照片或整个文件夹
  - 选择输出目录
  - 实时预览当前照片效果
  - 可展开“外观参数”分组，调整边框比例、圆角弧度、阴影、背景虚化、文字阴影、底部底纹、JPG 质量
  - 可展开“水印内容”分组，勾选品牌、机型、参数、镜头、拍摄时间、自定义标题/副标题，最终水印最多显示两行
  - 可自定义标题和副标题
- 命令行批处理：适合自动化和大批量处理
- 高质量输出：JPG 默认 95 质量，PNG 低压缩
- 自动处理 EXIF Orientation，竖图/横图方向会自动校正

## 文件结构

```text
PhotoBorderwatermark-main/
├── main.py                         # 启动器：无参数打开控制台，有参数走命令行批处理
├── photo_processor.py              # 图片处理核心
├── studio_app.py                   # 桌面控制台界面
├── dist/
│   └── PhotoBorderWatermarkStudio.exe
├── output/                         # 示例输出
└── README.md
```

## 快速使用

### 双击控制台版 exe

直接打开：

```powershell
dist\PhotoBorderWatermarkStudio.exe
```

打开后可以在左侧选择照片、调参数，右侧会显示预览。点“开始处理”后，成品会保存到设置的输出目录。

### 用 Python 打开控制台

```powershell
python main.py
```

### 命令行批处理

```powershell
python main.py DSC06840.JPG
python main.py --style white --output output *.jpg
python main.py --style blur --border 9 --corner 42 --shadow 10 --include-lens *.jpg
```

常用参数：

- `--style {blur,white}`：边框样式
- `--output output`：输出目录
- `--border 10`：边框比例，单位百分比
- `--corner 34`：圆角大小
- `--shadow 10`：阴影偏移
- `--shadow-blur 22`：阴影模糊半径
- `--shadow-opacity 110`：阴影深度
- `--blur-radius 40`：背景虚化强度
- `--font-scale 32`：文字大小比例，单位百分比
- `--text-spacing 14`：水印文字行距
- `--caption-backdrop 0`：水印底部底纹透明度，默认关闭
- `--text-shadow 150`：文字阴影透明度
- `--quality 95`：JPG 输出质量
- `--hide-brand`：不显示品牌
- `--hide-model`：不显示机型
- `--hide-params`：不显示拍摄参数
- `--include-lens`：显示镜头
- `--include-datetime`：显示拍摄时间
- `--hide-title`：不显示自定义标题
- `--hide-subtitle`：不显示自定义副标题
- `--title "自定义标题"`：自定义第一行文字
- `--subtitle "自定义副标题"`：自定义第二行文字

查看完整参数：

```powershell
python main.py --help
```

## 安装依赖

源码运行需要 Pillow：

```powershell
pip install Pillow
```

桌面控制台使用 Python 标准库 `tkinter`，Windows Python 通常自带。

## 重新打包 exe

```powershell
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name PhotoBorderWatermarkStudio main.py
```

打包结果在：

```text
dist\PhotoBorderWatermarkStudio.exe
```

## 输出说明

处理后的图片文件名格式：

```text
原文件名_样式.扩展名
```

例如：

```text
DSC06840_blur.JPG
DSC06840_white.JPG
```

## 注意事项

- 当前支持 JPG、JPEG、PNG。
- 大尺寸照片处理会占用较多内存，批量很多时建议分批处理。
- 程序会优先使用 Windows 中文字体，找不到时会退回可用字体。
- 虚化边框样式默认不再加底部深色底纹；需要时在“外观参数”里调高“底部底纹”即可。
- 水印内容固定最多两行；勾选很多字段时会自动合并到两行里，并自动缩小字号适配宽度。
- `dist\PhotoBorderWatermarkStudio.exe` 是新版控制台版；目录里的旧 `main.exe` 仍保留，没有覆盖。

## 作者

liulc-tech-star
