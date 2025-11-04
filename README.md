# Photoborderwatermark

A Python tool for adding borders and watermarks to photos with EXIF metadata information.

## 📋 Description

Photoborderwatermark is a Python utility that reads EXIF data from your photos and adds professional-looking borders with embedded camera information. Perfect for photographers who want to showcase their camera settings and equipment details directly on their images.

## ✨ Features

- **EXIF Data Extraction**: Automatically extracts camera metadata from photos
- **Smart Formatting**: Displays camera brand, model, lens, and shooting parameters
- **Parameter Display**: Shows focal length, aperture (F-number), shutter speed, ISO, and capture date
- **GPS Support**: Handles GPS information if available in EXIF data
- **Batch Processing**: Process multiple images at once
- **Error Handling**: Gracefully handles missing or incomplete EXIF data

## 🛠️ Technology Stack

- **Python**: 99.9%
- **Batch Scripts**: 0.1%

## 📦 Dependencies

```python
from PIL import Image, ImageFilter, ImageDraw, ImageFont
```

Required packages:
- Pillow (PIL)

Install dependencies:
```bash
pip install Pillow
```

## 🚀 Usage

### Basic Usage

Run the script with image files:

```bash
python main2.py image1.jpg image2.jpg
```

### Batch Processing

Use the provided batch file to process all JPG files in a directory:

```bash
compile.bat
```

Or manually:
```bash
python main2.py *.jpg
```

## 📸 EXIF Information Handled

The tool extracts and displays the following information:
- **Camera Brand** (Make)
- **Camera Model**
- **Lens Model**
- **Focal Length** (mm)
- **Aperture** (F-number)
- **Shutter Speed** (exposure time)
- **ISO Sensitivity**
- **Capture Date & Time**
- **GPS Data** (if available)

## 📁 Project Structure

```
Photoborderwatermark/
├── main1.py          # Version 1 of the watermark tool
├── main2.py          # Version 2 of the watermark tool (latest)
├── compile.bat       # Batch processing script for Windows
└── README.md         # This file
```

## 💡 Example Output

The tool will format EXIF data into a readable format, such as:
- Brand: Canon
- Model: EOS R5
- Lens: RF 24-70mm F2.8L IS USM
- Parameters: 50mm, F2.8, 1/500s, ISO 200
- Date: 2025-11-03 15:44:46

## ⚠️ Error Handling

If EXIF data is missing or incomplete, the tool will display default values:
- "未知品牌" (Unknown Brand)
- "未知型号" (Unknown Model)
- "未知镜头" (Unknown Lens)
- "参数未知" (Unknown Parameters)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📝 License

This project is open source and available under standard licensing terms.

## 👤 Author

**liulc-tech-star**
- GitHub: [@liulc-tech-star](https://github.com/liulc-tech-star)

## 🔗 Repository

[https://github.com/liulc-tech-star/Photoborderwatermark](https://github.com/liulc-tech-star/Photoborderwatermark)

---

*Made with ❤️ for photographers who love to share their camera settings*
