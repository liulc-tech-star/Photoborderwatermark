# Photoborderwatermark

一个用于给照片添加边框并在底部显示 EXIF 信息（相机品牌、参数等）的 Python 小工具。

## 简介

此工具会从照片中读取 EXIF 元数据（如相机品牌、机型、镜头、焦距、光圈、快门、ISO、拍摄时间），并把这些信息以艺术化的方式添加到底部白框或虚化边框上，支持批量处理。

## 主要功能

- 自动读取并格式化 EXIF 信息（品牌、型号、镜头、参数、拍摄时间）
- 两种边框样式：虚化四周背景（默认）或底部白色信息条
- 支持圆角和阴影（虚化模式）以增强视觉效果
- 批量处理（支持通配符如 *.jpg）
- 对缺失或不完整的 EXIF 做容错处理，使用默认占位文本

## 依赖

需要安装 Pillow（PIL）：

```powershell
pip install Pillow
```

## 仓库中的脚本

当前仓库主要脚本：

```
Photoborderwatermark/
├── main.py           # 主脚本（包含命令行参数，用于处理图片）
├── main_merged.py    # 合并版脚本（功能相同/类似，可作为参考）
├── compile.bat       # Windows 批处理示例（可用于批量调用脚本）
├── output/           # 默认输出目录（处理后图片保存位置）
└── README.md         # 本文件
```

说明：仓库中存在 `main.py` 和 `main_merged.py` 两个实现，通常直接运行 `main.py` 即可（两者功能基本一致，命令行参数相同）。

## 使用方法（示例）

1) 对单张图片使用虚化边框（默认）：

```powershell
python main.py photo.jpg
```

2) 对多张图片批量处理（当前目录下所有 JPG）：

```powershell
python main.py *.jpg
```

3) 使用白色底框（底部信息条）并指定输出目录：

```powershell
python main.py --style white --output my_output photo.jpg
```

4) 可选参数说明：

- `--style` : 边框样式，`blur`（虚化）或 `white`（底部白框），默认 `blur`
- `--output`: 输出目录，默认 `output`
- `--corner`: 圆角半径（仅 `blur` 模式生效），例如 `--corner 30`
- `--shadow`: 阴影偏移（仅 `blur` 模式生效），例如 `--shadow 8`

示例（组合）：

```powershell
python main.py --style blur --corner 40 --shadow 10 --output output *.jpg
```

## EXIF 信息（程序会尝试提取）

- 相机品牌（Make）
- 相机型号（Model）
- 镜头信息（LensModel / Lens）
- 焦距（FocalLength）
- 光圈（FNumber）
- 快门（ExposureTime）
- ISO（ISOSpeedRatings）
- 拍摄时间（DateTimeOriginal / DateTimeDigitized）
- GPS（如可用）

当 EXIF 缺失或字段不完整时，工具会使用中文占位文本（例如 “未知品牌”、“未知型号” 等）。

## 使用建议与注意事项

- Windows 系统下脚本默认使用系统字体路径（示例中使用 `C:\Windows\Fonts\arial.ttf`），若系统中没有该字体或路径不同，请在脚本中修改为可用字体路径。
- 处理大尺寸图片时内存占用会较高，必要时先缩小图片或在更大内存的机器上运行。

## 运行验证（本地）

可按上面的示例命令运行脚本，处理成功后将在 `output`（或 `--output` 指定目录）中看到新增的文件，文件名通常在原名后加了样式后缀（如 `_blur` 或 `_white`）。

## 贡献与许可

欢迎提交问题和合并请求。项目为开源，可根据需要在仓库中添加 LICENSE 文件以明确许可条款。

## 作者

liulc-tech-star

---

如需我将 README 也保留英文版或添加更多示例（例如处理 PNG、保存质量参数、CI 集成），告诉我我会再补充。
