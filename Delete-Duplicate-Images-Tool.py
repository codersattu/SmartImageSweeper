###Developed by Abhishek Satpathy (www.abhisat.com)
import os
import queue
import threading
from datetime import datetime
from tkinter import Tk, filedialog, messagebox, Toplevel, Label
from tkinter.ttk import Progressbar

import cv2
import imagehash
from PIL import Image


# Updated this function because:
# This(below) is a pixel-perfect hash, so even tiny differences in Compression of Angles, Noise, Minor edits, will make the hash completely different, meaning images won’t be detected as duplicates.
# For my folder of 8 images, only 2 was good to be saved, but it was showing no duplicates.
def get_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            return str(imagehash.phash(img))  # perceptual hash
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

# This function will calculate the blur score according to the Laplacian Rule
def calculate_blur(image_path):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0
        return cv2.Laplacian(img, cv2.CV_64F).var()
    except Exception as e:
        print(f"Error calculating blur for {image_path}: {e}")
        return 0

# This function will cache the score of images
def get_best_image(images):
    blur_scores = {img: calculate_blur(img) for img in images}
    return max(blur_scores, key=blur_scores.get)


from imagehash import phash

def delete_duplicate_images(folder_path, progress_queue):
    hash_to_files = []
    deleted = []

    all_files = []
    for path, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                all_files.append(os.path.join(path, file))

    total = len(all_files)

    for idx, file_path in enumerate(all_files, 1):
        try:
            with Image.open(file_path) as img:
                current_hash = phash(img)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        found_similar = False
        for existing_hash, file_list in hash_to_files:
            if current_hash - existing_hash <= 25:  # Hamming distance threshold (For similar but not same images)
                file_list.append(file_path)
                found_similar = True
                break

        if not found_similar:
            hash_to_files.append((current_hash, [file_path]))

        progress_queue.put((idx, total))

    for _, duplicates in hash_to_files:
        if len(duplicates) > 1:
            best_image = get_best_image(duplicates)
            for img in duplicates:
                if img != best_image:
                    try:
                        os.remove(img)
                        deleted.append(img)
                        print(f"Deleted: {img}")
                    except Exception as e:
                        print(f"Failed to delete {img}: {e}")
            print(f"Kept: {best_image}\n")

    print(f"\nTotal duplicates deleted: {len(deleted)}")
    progress_queue.put(("done", deleted))



def write_log(deleted_files, log_folder):
    if not deleted_files:
        return
    log_path = os.path.join(log_folder, "deleted_images_log.txt")
    with open(log_path, "a") as f:
        f.write(f"\n--- Log generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        for file in deleted_files:
            f.write(file + "\n")
        f.write("--- End of log ---\n\n")

def show_progress_window(folder_path):
    progress_window = Toplevel()
    progress_window.title("Processing Images")
    progress_window.geometry("400x100")
    progress_window.resizable(False, False)

    label = Label(progress_window, text="Starting...", font=("Arial", 12))
    label.pack(pady=10)

    progress = Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=5)

    progress_queue = queue.Queue()

    # Updated this function because it was getting stuck after processing as it was not stopping after detecting completion
    def update_progress():
        while not progress_queue.empty():
            data = progress_queue.get_nowait()
            if isinstance(data, tuple):
                if data[0] == "done":
                    deleted_files = data[1]
                    write_log(deleted_files, folder_path)
                    if deleted_files:
                        messagebox.showinfo("Done",
                                            f"Deleted {len(deleted_files)} duplicate images.\nLog saved in folder.")
                    else:
                        messagebox.showinfo("Done", "No duplicate images found.")
                    progress_window.destroy()
                    root.quit()
                    return  # Exit the loop and stop calling after()
                else:
                    current, total = data
                    percent = int((current / total) * 100)
                    progress["value"] = percent
                    label.config(text=f"Processing {current}/{total} images...")

        # Only continue the loop if "done" wasn't found yet
        progress_window.after(100, update_progress)

    threading.Thread(target=delete_duplicate_images, args=(folder_path, progress_queue), daemon=True).start()
    update_progress()

def select_folder_and_process():
    folder_path = filedialog.askdirectory(title="Select Folder with Images")
    if not folder_path:
        return
    show_progress_window(folder_path)

if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    select_folder_and_process()
    root.mainloop()
###Developed by Abhishek Satpathy (www.abhisat.com)