
# FFmpeg Video Splitter GUI (v1.1)

A robust, cross-platform Python application built with CustomTkinter and FFmpeg, designed to split large video files into multiple segments based on a maximum file size constraint.

This tool is particularly useful for preparing video content for platforms with strict file size limits (e.g., specific note-taking applications or old file systems).

## ✨ Features (Release 1.1)

-   **Size-Based Splitting:** Automatically calculates segmentation points based on a maximum output file size (e.g., 200 MB), enforcing the limit via video re-encoding.
    
-   **Robust Error Handling:** Uses modal popups to display detailed error messages (including FFmpeg console output details) for `TimeoutExpired`, codec issues, and file errors.
    
-   **Multithreading:** Runs the CPU-intensive FFmpeg process in a background thread to prevent the UI from freezing ("Not Responding").
    
-   **Customizable Timeout:** User-definable processing timeout (in minutes) for each segment, accommodating differences in hardware performance.
    
-   **Non-Overwriting Logic:** Automatically assigns a unique batch version prefix (e.g., `_v01`, `_v02`) to prevent accidental overwriting of previous splits.
    
-   **Clean UI:** Modern, centered GUI using CustomTkinter for an attractive user experience.
    

## 🛠️ Requirements

1.  **Python 3.x**
    
2.  **FFmpeg & FFprobe:** The core video processing utilities.
    
3.  **Required Python Libraries:**
    

### Installation of Dependencies

Install the necessary Python libraries:

```
pip install customtkinter

```

### FFmpeg Setup (Crucial!)

For the script to work, the `ffmpeg.exe` and `ffprobe.exe` executables **MUST** be placed in the **same folder** as the Python script (`ffmpeg_splitter_gui_v1_1.py`).

Download the static builds for Windows from the official FFmpeg website.

## 🚀 How to Run

1.  Save the Python code as `ffmpeg_splitter_gui_v1_1.py`.
    
2.  Place `ffmpeg.exe` and `ffprobe.exe` in the same directory.
    
3.  Execute the script from your terminal:
    

```
python ffmpeg_splitter_gui_v1_1.py

```

## 📋 Usage Instructions

1.  **Select File:** Click "Browse" to select your large video file. The file's details (Size, Duration, Bitrate) will be displayed.
    
2.  **Configure Parameters:**
    
    -   **Max Segment Size (MB):** Set the maximum desired size for each output file (Default: 200).
        
    -   **Processing Timeout (Minutes):** Set the maximum time FFmpeg has to complete each segment (Default: 60 min).
        
3.  **Start Splitting:** Click "START SPLITTING".
    
4.  **Completion:** Upon success, a confirmation popup will appear, and the resulting segmented files (e.g., `video_file_v01_part01.mp4`) will be saved in the original video's directory.
    

**License:** MIT **Author:** adolfotrinca
