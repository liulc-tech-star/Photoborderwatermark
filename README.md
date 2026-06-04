# Photo Border Watermark Studio

给照片添加边框和 EXIF 参数水印的 Windows 小工具。支持桌面控制台和命令行两种使用方式：双击 `PhotoBorderWatermarkStudio.exe` 可以进入可视化界面，也可以用 `python main.py` 批量处理图片。

## 功能概览

- 自动读取 EXIF：相机品牌、型号、镜头、焦距、光圈、快门、ISO、拍摄时间。
- 两种输出样式：
  - `blur`：虚化背景边框，支持圆角、阴影、背景模糊、文字阴影。
  - `white`：照片底部添加白色信息栏，适合简洁展示。
- 桌面控制台：
  - 选择单张、多张照片，或导入整个文件夹。
  - 实时预览当前参数下的效果。
  - 科技感折叠面板，集中调整外观参数和水印内容。
  - 鼠标滚轮支持左侧控制栏滚动，列表和日志区域也能自然滚动。
  - 状态日志和进度条位于右下角底部信息区，不遮挡照片预览。
- 命令行批处理：适合自动化处理大量照片。
- 自动修正 EXIF Orientation，竖图和横图方向会按拍摄方向显示。
- JPG 默认高质量输出，PNG 使用低压缩输出。

## 当前文件结构

```text
PhotoBorderwatermark-main/
├── PhotoBorderWatermarkStudio.exe   # 已打包好的桌面版程序
├── main.py                          # 启动器：无图片参数打开桌面控制台，有图片参数走命令行
├── photo_processor.py               # 图片处理、EXIF、水印和保存逻辑
├── studio_app.py                    # Tkinter 桌面控制台界面
├── PhotoBorderWatermarkStudio.spec  # PyInstaller 打包配置
├── DSC06840.JPG                     # 示例照片
├── DSC07002.JPG                     # 示例照片
└── README.md
```

运行或打包后可能会生成 `output/`、`build/`、`dist/`、`__pycache__/` 等目录，它们不是核心源码。

## 快速使用

### 方式一：双击 exe

直接双击根目录下的：

```powershell
PhotoBorderWatermarkStudio.exe
```

打开后：

1. 在左侧选择照片或添加文件夹。
2. 选择输出目录。
3. 选择 `虚化边框` 或 `白色底框`。
4. 展开 `外观参数` 调整边框、圆角、阴影、模糊、字体和 JPG 质量。
5. 展开 `水印内容` 选择要显示的 EXIF 字段，并填写自定义标题/副标题。
6. 点击 `开始处理`，右下角状态区会显示进度和日志。

### 方式二：用 Python 打开控制台

```powershell
python main.py
```

也可以显式指定打开桌面控制台：

```powershell
python main.py --studio
```

### 方式三：命令行批处理

```powershell
python main.py DSC06840.JPG
python main.py --style white --output output *.jpg
python main.py --style blur --border 9 --corner 42 --shadow 10 --include-lens *.jpg
```

输入参数可以是图片路径、文件夹或通配符。支持的图片格式为 JPG、JPEG、PNG。

## 水印内容规则

水印最多显示两行，会自动缩小字号以适配宽度。

第一行顺序：

```text
自定义标题 | 自定义副标题 | 品牌 机型
```

第二行顺序：

```text
拍摄参数 | 镜头 | 拍摄时间
```

如果某个字段未勾选、为空，或 EXIF 中不存在对应信息，会自动跳过。

## 命令行参数

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--style {blur,white}` | 边框样式，默认 `blur` |
| `--output output` | 输出目录，默认 `output` |
| `--border 10` | 边框比例，单位百分比 |
| `--corner 34` | 圆角大小，仅 `blur` 样式明显 |
| `--shadow 10` | 阴影偏移 |
| `--shadow-blur 22` | 阴影模糊半径 |
| `--shadow-opacity 110` | 阴影不透明度，范围 0-255 |
| `--blur-radius 40` | 背景虚化强度 |
| `--font-scale 32` | 字体大小比例，单位百分比 |
| `--text-spacing 14` | 水印文字行距 |
| `--caption-backdrop 0` | 底部底纹透明度，默认关闭 |
| `--text-shadow 150` | 文字阴影透明度 |
| `--quality 95` | JPG 输出质量 |
| `--include-lens` | 显示镜头信息 |
| `--include-datetime` | 显示拍摄时间 |
| `--title "主标题"` | 自定义标题 |
| `--subtitle "副标题"` | 自定义副标题 |

隐藏字段：

```powershell
--hide-brand
--hide-model
--hide-params
--hide-title
--hide-subtitle
```

查看完整参数：

```powershell
python main.py --help
```

## 输出说明

默认输出目录为 `output`。生成文件命名规则：

```text
原文件名_样式.扩展名
```

示例：

```text
DSC06840_blur.JPG
DSC06840_white.JPG
```

## 开发运行

源码运行依赖 Pillow：

```powershell
pip install Pillow
```

桌面界面使用 Python 标准库 `tkinter`，Windows 版 Python 通常自带。

启动桌面界面：

```powershell
python main.py
```

运行一次命令行处理：

```powershell
python main.py --style blur --output output DSC06840.JPG
```

## 打包 exe

安装 PyInstaller：

```powershell
pip install pyinstaller
```

使用当前 spec 文件打包：

```powershell
python -m PyInstaller PhotoBorderWatermarkStudio.spec
```

打包结果默认在：

```text
dist\PhotoBorderWatermarkStudio.exe
```

如果需要把新版 exe 放到项目根目录，可以在关闭旧程序后复制：

```powershell
Copy-Item .\dist\PhotoBorderWatermarkStudio.exe .\PhotoBorderWatermarkStudio.exe -Force
```

## 注意事项

- 大尺寸照片处理会占用较多内存，批量很多时建议分批处理。
- 程序会优先使用 Windows 中文字体，找不到时会回退到可用字体。
- 如果照片没有 EXIF，水印会自动跳过缺失字段或显示默认信息。
- `blur` 样式默认关闭底部深色底纹；需要更强文字对比时可调高 `底部底纹`。
- 覆盖 exe 前请先关闭正在运行的 `PhotoBorderWatermarkStudio.exe`，否则 Windows 会锁定文件导致打包或复制失败。

## 作者

liulc-tech-star
