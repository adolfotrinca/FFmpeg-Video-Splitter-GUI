# --- RELEASE INFORMATION ---
# Version: 1.1 (English Stable)
# Date: October 2025
# Features: GUI, Threading, Variable Timeout, Modal Error Handling, Centering, No Overwriting.
# ---------------------------

import subprocess
import os
import math
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
import time 
import re

# --- GLOBAL VARIABLES AND EXECUTABLE CONFIGURATION ---

# Dynamically determine the path to the script folder
SCRIPT_DIR = os.path.dirname(sys.argv[0])

# NOTE: FFmpeg and FFprobe EXECUTABLES MUST BE IN THE SAME FOLDER AS THE PYTHON SCRIPT
FFMPEG_EXE = os.path.join(SCRIPT_DIR, "ffmpeg.exe")
FFPROBE_EXE = os.path.join(SCRIPT_DIR, "ffprobe.exe")

# Working H.264 encoding parameters (Windows/VLC compatibility)
# FIX: Corrected "libx64" to "libx264"
FFMPEG_ARGS = ["-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "128k"]

# Default maximum desired segment size in bytes (200 MB)
MAX_SIZE_DEFAULT_BYTES = 209715200

# --- UTILITY FUNCTIONS ---

def _format_seconds(seconds):
    """Converts a number of seconds to HH:MM:SS or MM:SS format."""
    seconds = int(seconds)
    if seconds >= 3600:
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    else:
        return time.strftime('%M:%S', time.gmtime(seconds))

def _format_bytes(size_bytes):
    """Converts bytes into a readable format (KB, MB, GB)."""
    if size_bytes is None or size_bytes == 0:
        return "N/A"
    size_name = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# --- MODAL INFO/ERROR POPUP CLASS ---

class InfoToplevel(ctk.CTkToplevel):
    def __init__(self, master, title="Application Information", text_content=""):
        super().__init__(master)
        
        INFO_WIDTH = 500
        INFO_HEIGHT = 450  # Increased height to accommodate all text and the Close button
        self.title(title)
        
        # Center the popup window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - INFO_WIDTH / 2)
        center_y = int(screen_height / 2 - INFO_HEIGHT / 2)
        self.geometry(f'{INFO_WIDTH}x{INFO_HEIGHT}+{center_x}+{center_y}')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Ensure text label expands

        label = ctk.CTkLabel(self, text=text_content, justify="left", wraplength=450)
        label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Ensure the Close button is always present
        close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_button.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Make popup modal (blocks the main window)
        self.transient(self.master) 
        self.grab_set() 
        self.master.wait_window(self)

# --- MAIN APPLICATION CLASS ---

class VideoSplitterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # FIX for Windows/DPI scaling issues
        try:
            ctk.deactivate_automatic_dpi_awareness()
        except AttributeError:
            pass

        # Window Configuration
        self.title("FFmpeg Video Splitter for NotebookLM")
        self._set_geometry_center(600, 630) 
        ctk.set_appearance_mode("System")  
        ctk.set_default_color_theme("blue")
        
        # State Variables
        self.input_file = ctk.StringVar()
        self.max_size_mb = ctk.StringVar(value="200") 
        self.timeout_minutes = ctk.StringVar(value="60") # Default timeout 60 minutes
        self.current_thread = None
        self.info_window = None 
        self.batch_prefix = "" 
        
        # Initialize UI
        self._setup_ui()
        
        # Handle clean exit
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _set_geometry_center(self, width, height):
        """Calculates the position to center the window on the screen."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def _on_closing(self):
        """Called when the user attempts to close the window."""
        if self.current_thread and self.current_thread.is_alive():
            print("Warning: Interrupting splitting thread.")
        self.quit()
        self.destroy()
        sys.exit(0)
        
    def _show_info(self):
        """Displays the application information window (modal)."""
        info_text = (
            "🎥 FFmpeg Video Splitter for NotebookLM 💾\n\n"
            "This tool uses FFmpeg to split a large video file into smaller "
            "segments, each with a user-defined maximum size.\n\n"
            f"Default Max Size: {MAX_SIZE_DEFAULT_BYTES / (1024*1024):.0f} MB.\n\n"
            "**HOW IT WORKS:**\n"
            "1. Maximum size is enforced by FFmpeg through video re-encoding (which is CPU-intensive).\n"
            "2. After each segment, the script measures the actual duration and resumes the next segment from that precise point.\n"
            "3. Overwriting existing files is prevented using an automatic batch suffix (e.g., `_v01`).\n\n"
            "**PROCESSING TIMEOUT:**\n"
            "The timeout sets the maximum time (in minutes) FFmpeg is allowed to spend processing each individual segment.\n\n"
            "**ESSENTIAL REQUIREMENTS:**\n"
            f"The **ffmpeg.exe** and **ffprobe.exe** executables must be copied\n "
            f"into the **SAME FOLDER** as this Python script ({os.path.basename(FFMPEG_EXE)}).\n"
            "**STATUS MESSAGES:**\n"
            "Critical errors will be displayed in a modal popup."
        )
        InfoToplevel(self, title="Application Information", text_content=info_text)

    def _show_error_popup(self, error_message, success=False):
        """Displays the critical error message or success message in a modal popup."""
        if success:
            error_title = "✅ SPLITTING COMPLETE"
        else:
            error_title = "❌ CRITICAL PROCESSING ERROR"
        InfoToplevel(self, title=error_title, text_content=error_message)


    def _setup_ui(self):
        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(8, weight=1)

        # 1. Header (Title and Info Button)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(header_frame, text="✂️ FFmpeg Video Splitter 💾", 
                                   font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, sticky="w")
        
        info_button = ctk.CTkButton(header_frame, text="Info", width=70, command=self._show_info)
        info_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # 2. File Selection
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        file_frame.columnconfigure(0, weight=4)
        file_frame.columnconfigure(1, weight=1)

        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.input_file, placeholder_text="Select video file...")
        self.file_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        file_button = ctk.CTkButton(file_frame, text="Browse", command=self._select_file)
        file_button.grid(row=0, column=1, padx=(5, 10), pady=10)

        # 3. Maximum Size (MB)
        size_frame = ctk.CTkFrame(self)
        size_frame.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        size_frame.columnconfigure(0, weight=1)
        size_frame.columnconfigure(1, weight=1)
        
        size_label = ctk.CTkLabel(size_frame, text="Max Segment Size (MB):")
        size_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.size_entry = ctk.CTkEntry(size_frame, textvariable=self.max_size_mb, width=100)
        self.size_entry.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # 4. Timeout (Minutes)
        timeout_frame = ctk.CTkFrame(self)
        timeout_frame.grid(row=3, column=0, padx=20, pady=(5, 10), sticky="ew")
        timeout_frame.columnconfigure(0, weight=1)
        timeout_frame.columnconfigure(1, weight=1)
        
        timeout_label = ctk.CTkLabel(timeout_frame, text="Processing Timeout (Minutes):")
        timeout_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.timeout_entry = ctk.CTkEntry(timeout_frame, textvariable=self.timeout_minutes, width=100)
        self.timeout_entry.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # 5. START Button
        self.start_button = ctk.CTkButton(self, text="START SPLITTING", command=self._start_splitting, 
                                          font=ctk.CTkFont(size=16, weight="bold"), height=40)
        self.start_button.grid(row=4, column=0, padx=20, pady=(20, 10), sticky="ew")

        # 6. Summary Label (Permanent)
        self.summary_label = ctk.CTkLabel(self, text="File details...", justify="left", height=60, anchor="nw")
        self.summary_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="ew")
        
        # 7. Progress and Status Label
        self.progress_label = ctk.CTkLabel(self, text="Waiting...", justify="left")
        self.progress_label.grid(row=6, column=0, padx=20, pady=(5, 5), sticky="w")

        # 8. Progress Bar
        self.progressbar = ctk.CTkProgressBar(self, mode="determinate")
        self.progressbar.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progressbar.set(0) 

        # 9. Bottom Controls (Exit)
        bottom_controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_controls_frame.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="se")
        
        self.exit_button = ctk.CTkButton(bottom_controls_frame, text="Exit", width=100, command=self._on_closing)
        self.exit_button.pack(side="right")

    # --- GUI UTILITY METHODS ---
    
    def _select_file(self):
        """Opens the file dialog for file selection."""
        file_path = filedialog.askopenfilename(
            defaultextension=".mp4",
            filetypes=[("Video files", "*.mp4;*.mkv;*.avi"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file.set(file_path)
            self._reset_ui()
            self._update_summary_info(file_path)

    def _reset_ui(self):
        """Resets UI elements to initial state."""
        self.summary_label.configure(text="File details...", text_color="white")
        self.progress_label.configure(text="Waiting...", text_color="white")
        self.progressbar.set(0)
        self.progressbar.stop()
        self.start_button.configure(state="normal", text="START SPLITTING")
        self.exit_button.configure(state="normal")
        
    # --- FFPROBE/FFMPEG METHODS ---
    
    def _execute_ffprobe(self, command_args, timeout=15):
        """Executes ffprobe and handles errors."""
        try:
            result = subprocess.run(
                command_args, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=timeout
            )
            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(f"FFprobe not found. Ensure {os.path.basename(FFPROBE_EXE)} is in {SCRIPT_DIR}.")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FFprobe did not respond within {timeout} seconds.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFprobe Error ({e.returncode}): Analysis failed. Details: {e.stderr.strip()[:500]}")

    def _get_file_info(self, input_file):
        """Gets duration, size, and bitrate of the file."""
        duration = 0
        file_size = None
        bitrate = None
        
        # Use a short timeout for file analysis (15 seconds)
        duration_str = self._execute_ffprobe([
            FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", input_file
        ])
        
        duration = math.ceil(float(duration_str))
        file_size = os.path.getsize(input_file)
        
        if duration > 0 and file_size > 0:
            bitrate = (file_size * 8) / duration / 1000 # Kbps

        return duration, file_size, bitrate
            
    def _update_summary_info(self, input_file):
        """Updates the summary label after file selection."""
        try:
            # Start indeterminate animation during initial calculation
            self.progressbar.configure(mode="indeterminate")
            self.progressbar.start()
            self.progress_label.configure(text="Calculating file info...", text_color="white")

            total_duration, size_bytes, bitrate_kbps = self._get_file_info(input_file)
            
            self.progressbar.stop()
            self.progressbar.configure(mode="determinate")
            
            size_human = _format_bytes(size_bytes)
            bitrate_human = f"{bitrate_kbps:.0f} Kbps" if bitrate_kbps else "N/A"
            duration_human = _format_seconds(total_duration)
            
            self.summary_label.configure(
                text=(
                    f"Total Duration: {duration_human}\n"
                    f"Original Size: {size_human} ({bitrate_human})"
                ),
                text_color="white"
            )
            self.progress_label.configure(text="Ready for splitting.", text_color="white")
            
        except Exception as e:
            self.summary_label.configure(text="File details...", text_color="red")
            self.progress_label.configure(text=f"❌ Info Error: {e}", text_color="red")
            self.start_button.configure(state="disabled")

    # --- THREADING AND SPLITTING LOGIC ---
    
    def _find_unique_batch_prefix(self, filename_base, output_directory):
        """Finds the next unused batch prefix (e.g., _v01, _v02)."""
        max_version = 0
        
        # Regex to find files with pattern *_{number}_partXX
        # Search for all files in the output directory
        
        pattern = re.compile(rf'^{re.escape(os.path.basename(filename_base))}_v(\d+)_part\d{{2}}{re.escape(os.path.splitext(self.input_file.get())[1])}$')
        
        try:
            for item in os.listdir(output_directory):
                match = pattern.match(item)
                if match:
                    version = int(match.group(1))
                    if version > max_version:
                        max_version = version
        except FileNotFoundError:
            # Output folder does not exist (unlikely here), use v01
            pass
        except Exception:
            # In case of reading error, use v01 for safety
            pass
            
        new_version = max_version + 1
        return f"_v{new_version:02d}"

    def _start_splitting(self):
        """Prepares and starts the splitting thread."""
        
        self.start_button.configure(state="disabled", text="PROCESSING...")
        self.exit_button.configure(state="disabled")
        self.progressbar.set(0)
        self.progressbar.stop()
        
        input_file = self.input_file.get()
        
        try:
            max_size_mb = float(self.max_size_mb.get())
            if max_size_mb <= 0: raise ValueError
        except ValueError:
            self._update_gui(f"❌ Error: Enter a valid Size (MB) (> 0).", final_error=True)
            return

        try:
            timeout_min = float(self.timeout_minutes.get())
            if timeout_min <= 0: raise ValueError
            # Convert minutes to seconds for FFmpeg
            ffmpeg_timeout = int(timeout_min * 60)
        except ValueError:
            self._update_gui(f"❌ Error: Enter a valid Timeout (Minutes) (> 0).", final_error=True)
            return

        # Start processing on a separate thread
        self.current_thread = threading.Thread(
            target=self._splitting_thread_task, 
            args=(input_file, max_size_mb, ffmpeg_timeout)
        )
        self.current_thread.start()

    def _splitting_thread_task(self, input_file, max_size_mb, ffmpeg_timeout):
        """Contains all splitting logic to be run in the background thread."""
        
        segments_created = 0
        i = 1 # Current segment counter
        
        try:
            # 1. Calculate Total Duration
            total_duration, _, _ = self._get_file_info(input_file)
            if total_duration == 0: return 

            MAX_SIZE = int(max_size_mb * 1024 * 1024)
            start_time_dt = datetime.now()
            start_time_str = start_time_dt.strftime("%H:%M:%S")

            # Update Summary with start time
            self.after(0, lambda: self.summary_label.configure(text=f"Start Time: {start_time_str} | {self.summary_label.cget('text')}"))
            
            # Initialize loop variables
            filename_base, file_extension = os.path.splitext(input_file)
            output_directory = os.path.dirname(os.path.abspath(input_file))
            start_time = 0
            
            # --- FIND UNIQUE BATCH PREFIX ---
            batch_prefix = self._find_unique_batch_prefix(filename_base, output_directory)
            # ----------------------------------------

            while start_time < total_duration:
                # Use batch prefix for file naming
                output_file = f"{filename_base}{batch_prefix}_part{i:02d}{file_extension}"
                
                # Segment status message
                formatted_start_time = _format_seconds(start_time)
                self._update_gui(f"Processing Segment {i}: Start {formatted_start_time}", mode="indeterminate")

                command = [
                    FFMPEG_EXE,
                    "-i", input_file,
                    "-ss", str(start_time),
                    *FFMPEG_ARGS, 
                    "-fs", str(MAX_SIZE),
                    "-map", "0",
                    "-n", # Prevent overwriting
                    output_file
                ]
                
                # FFmpeg Execution
                ffmpeg_error_output = None 
                try:
                    # Use the user-provided timeout
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=ffmpeg_timeout)
                except subprocess.TimeoutExpired as e:
                    # Catch specific timeout error and raise a readable error
                    error_message = f"Timeout: Segment {i} processing exceeded the {ffmpeg_timeout/60:.0f} minute limit."
                    raise RuntimeError(error_message)
                except subprocess.CalledProcessError as e:
                    ffmpeg_error_output = e.stderr.decode('utf-8', errors='ignore').strip()
                    error_message = f"FFmpeg (Segment {i}) failed. Code: {e.returncode}. Details: {ffmpeg_error_output[:500]}..."
                    raise RuntimeError(error_message)
                except Exception as e:
                    error_message = f"FFmpeg (Segment {i}) system error: {e.__class__.__name__} - {str(e)}"
                    raise RuntimeError(error_message)

                
                # Integrity checks and advancement
                self.after(0, lambda: self.progressbar.stop() and self.progressbar.configure(mode="determinate"))

                if not os.path.exists(output_file) or os.path.getsize(output_file) < 1024:
                    raise RuntimeError(f"File {output_file} is empty/corrupted. Aborting.")
                
                segments_created += 1 # SEGMENT SUCCESSFULLY CREATED
                
                # Measure time and update start point
                duration_seconds, error = self._get_duration(output_file)
                if duration_seconds == 0 and error:
                    raise RuntimeError(f"Could not measure segment {i} duration. {error}")
                if duration_seconds == 0: break # End of file
                    
                start_time += duration_seconds
                
                # Update progress bar
                progress_value = min(1.0, start_time / total_duration)
                self._update_gui(progress_value=progress_value)
                
                # Exit condition (end of the original file based on size)
                actual_size = os.path.getsize(output_file)
                if actual_size < MAX_SIZE * 0.99:
                    break
                
                i += 1
            
            # Final success message
            final_message = f"✅ Splitting complete! Created {segments_created} segments. Prefix: {batch_prefix}\nFiles saved in: {output_directory}"
            
            # Show Success Popup
            self.after(0, lambda: self._show_error_popup(final_message, success=True)) # Use the error popup structure for success
            
            # Update final GUI status (without repeating the directory path in the status label)
            self._update_gui(f"✅ Splitting complete! Created {segments_created} segments. Prefix: {batch_prefix}", final_dir=output_directory, progress_value=1.0)

        except RuntimeError as e:
            # Catch all critical errors (RuntimeError) raised
            self._update_gui(text=f"Processing Error", final_error=True)
            self.after(0, lambda err=str(e): self._show_error_popup(f"VIDEO PROCESSING ERROR:\n\n{err}"))
        except Exception as e:
            # Catch generic Python errors (system)
            self._update_gui(text=f"System Error", final_error=True)
            self.after(0, lambda err=str(e): self._show_error_popup(f"GENERIC SYSTEM ERROR:\n\nType: {e.__class__.__name__}\nMessage: {err}"))

        finally:
            # Ensure buttons are re-enabled at the end
            self.after(0, lambda: self.start_button.configure(state="normal", text="START SPLITTING"))
            self.after(0, lambda: self.exit_button.configure(state="normal"))
            self.after(0, lambda: self.progressbar.stop())


    def _get_duration(self, file_path):
        """Gets the video duration in seconds using FFprobe (called from background thread)."""
        # FFprobe timeout is fixed at 15 seconds as analysis is quick
        try:
            duration_str = self._execute_ffprobe([
                FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ])
            return math.ceil(float(duration_str)), None
        except Exception as e:
            # Catch and return the error for thread handling
            return 0, str(e)


    def _update_gui(self, text=None, progress_value=None, mode=None, final_dir=None, final_error=False):
        """Updates GUI elements in a thread-safe manner."""
        
        # Helper function for updating
        def update():
            # Progress bar mode management
            if mode == "indeterminate":
                self.progressbar.configure(mode="indeterminate")
                self.progressbar.start()
            elif mode == "determinate":
                self.progressbar.configure(mode="determinate")
                self.progressbar.stop()
            
            if progress_value is not None:
                self.progressbar.set(progress_value)
            
            if text is not None:
                # Only display text in the status label if it's not a critical error (which uses the popup)
                if final_error:
                     self.progress_label.configure(text=text, text_color="#FF4040") 
                elif final_dir:
                    self.progress_label.configure(text=f"{text}\nFiles saved in: {final_dir}", text_color="white")
                else:
                    self.progress_label.configure(text=text, text_color="white") 

        # Execute the update function on the main thread
        self.after(0, update)


if __name__ == "__main__":
    # print("Script avviato. Inizializzazione GUI...") 
    app = VideoSplitterApp()
    app.mainloop()
